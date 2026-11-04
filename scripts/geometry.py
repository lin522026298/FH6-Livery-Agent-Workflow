"""Read native mask coordinates and observe an owned offscreen renderer's meshes."""
from pathlib import Path
import argparse, hashlib, json, os, struct, threading, zipfile
import xml.etree.ElementTree as ET
import numpy as np
import cv2
from PIL import Image
import core as c
from livery import profile


def surface(blob):
    u16 = lambda o: struct.unpack_from('<H', blob, o)[0]
    u32 = lambda o: struct.unpack_from('<I', blob, o)[0]
    if u32(0) != 0x47727562:
        raise ValueError('Unknown swatchbin header')
    count, start = (u32(16), 20) if blob[4] > 1 or (blob[4] == 1 and blob[5] >= 1) else (u16(6), 16)
    for i in range(count):
        head = start + i * 24
        if u32(head) != 0x54584342:
            continue
        n, meta, data = u16(head + 6), u32(head + 8), u32(head + 12)
        length = u32(head + 20) or u32(head + 16)
        for j in range(n):
            record = meta + j * 8
            if u32(record) == 0x54584348:
                tex = record + u16(record + 6)
                break
        else:
            raise ValueError('No TXCH record')
        width, height = u32(tex + 24), u32(tex + 28)
        packed, trans, slices = u16(tex + 36), u32(tex + 40), u32(tex + 56)
        if packed >> 14:
            raise ValueError('Unsupported packed mask')
        encoding = trans - 2 if trans > 1 else u32(tex + slices)
        raw = blob[data:data + length]
        if encoding in (19, 20):
            image = np.frombuffer(raw, np.uint8, count=width * height).reshape(height, width).copy()
        elif encoding in (3, 4):
            blocks = np.frombuffer(raw, np.uint8, count=((width + 3) // 4) * ((height + 3) // 4) * 8).reshape(-1, 8)
            a, b = blocks[:, 0].astype(np.uint16), blocks[:, 1].astype(np.uint16)
            table = np.zeros((len(blocks), 8), np.uint8); table[:, 0] = a; table[:, 1] = b
            for k in range(1, 7):
                low = ((5 - k) * a + k * b) // 5 if k < 5 else (0 if k == 5 else 255)
                table[:, k + 1] = np.where(a > b, ((7 - k) * a + k * b) // 7, low)
            bits = (blocks[:, 2:].astype(np.uint64) << (np.arange(6, dtype=np.uint64) * 8)).sum(1)
            index = ((bits[:, None] >> (np.arange(16, dtype=np.uint64) * 3)) & 7).astype(np.uint8)
            image = table[np.arange(len(blocks))[:, None], index].reshape((height + 3) // 4, (width + 3) // 4, 4, 4).transpose(0, 2, 1, 3).reshape(((height + 3) // 4) * 4, ((width + 3) // 4) * 4)[:height, :width].copy()
        else:
            raise ValueError(f'Unsupported mask encoding {encoding}')
        return image, dict(width=width, height=height, encoding=encoding)
    raise ValueError('No TXCB block')


def atlas_to_native(attributes, slot):
    matrix = np.array([[1., 0., -float(attributes['xorigin'])],
                       [0., 1., -float(attributes['yorigin'])], [0., 0., 1.]])
    if slot == 5:
        matrix = matrix[[1, 0, 2]]
    signs = (-1, 1) if slot == 5 else (-1, -1) if slot == 4 else (1, 1)
    return np.diag([*signs, 1.]) @ matrix


def masks(config, car_id, output):
    out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=False)
    cars = c.read(config['carsCatalog']); info = cars[str(car_id)]
    model = Path(config['gameContent']) / 'media/Cars' / (info['model'] + '.zip')
    records = []
    with zipfile.ZipFile(model) as archive:
        names = {n.lower(): n for n in archive.namelist()}
        xml = archive.read(names['liverymasks/masks.xml'])
        (out / 'Masks.xml').write_bytes(xml); root = ET.fromstring(xml)
        yy, xx = np.indices((1024, 1024), dtype='float32')
        for slot, face in enumerate(c.NAMES):
            element = root.find(face)
            if element is None or element.attrib.get('valid') != 'true':
                records.append(dict(slot=slot, name=face, available=False)); continue
            key = 'liverymasks/' + element.tag.lower() + '.swatchbin'
            if key not in names:
                raise ValueError('XML declares a valid face but its mask is missing: ' + face)
            blob = archive.read(names[key]); im, fmt = surface(blob)
            # Glass_Right uses the same atlas flip convention as Right.
            matrix = atlas_to_native(element.attrib, 4 if slot == 10 else slot)
            inverse = np.linalg.inv(matrix)
            nx, ny = xx - 512, 512 - yy
            ax = inverse[0, 0] * nx + inverse[0, 1] * ny + inverse[0, 2]
            ay = inverse[1, 0] * nx + inverse[1, 1] * ny + inverse[1, 2]
            alpha = cv2.remap(im, ((ax + 1024) * im.shape[1] / 2048 - .5).astype('float32'),
                              ((512 - ay) * im.shape[0] / 1024 - .5).astype('float32'),
                              cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            Image.fromarray(alpha).save(out / (face + '_permission.png'))
            Image.fromarray(im).save(out / (face + '_atlas.png'))
            y, x = np.where(alpha >= 128)
            records.append(dict(slot=slot, name=face, available=bool(len(x)), xml=element.attrib,
                                atlasToNative=matrix.tolist(), texture=fmt,
                                maskSha256=hashlib.sha256(blob).hexdigest(),
                                boundsPx=[int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1] if len(x) else None,
                                maskPath=str(out / (face + '_permission.png'))))
    c.dump(dict(carId=car_id, carInfo=info, model=str(model), modelSha256=c.sha(model),
                faces=records, observation='Permission masks only; visible geometry and occlusion are separate.'), out / 'geometry.json')
    colors = {name: [45 + (i * 63) % 170, 55 + (i * 91) % 170, 45 + (i * 43) % 180]
              for i, name in enumerate(c.NAMES) if records[i]['available']}
    c.save(c.blank(car_id, 'Native projection colors — diagnostic only', colors), out / 'projection-diagnostic.3so')
    print(json.dumps(dict(geometry=str(out / 'geometry.json'), diagnostic=str(out / 'projection-diagnostic.3so')), ensure_ascii=False))


def capture(config, project, output):
    import frida
    source = Path(project).resolve(strict=True); initial_sha = c.sha(source)
    out = Path(output).resolve(); out.mkdir(parents=True, exist_ok=False)
    data_dir = out / 'mesh'; data_dir.mkdir(); temporary = out / 'temp'; temporary.mkdir()
    exe = Path(config['previewExe']).resolve(strict=True)
    if config.get('previewSha256') and c.sha(exe) != config['previewSha256']:
        raise ValueError('Offscreen observation protocol is version-bound: EXE differs')
    args = [str(exe), '--background', '--input', str(source), '--game', config['gameContent'],
            '--output', str(out / 'renderer'), '--views', 'left,right,front,rear,top',
            '--size', '1280x800', '--timeout', '120', '--cache-dir', str(out / 'cache')]
    device = frida.get_local_device(); done = threading.Event(); records = []; errors = []
    env = os.environ.copy(); env['TEMP'] = str(temporary); env['TMP'] = str(temporary)
    pid = device.spawn(args, envp=env, cwd=str(exe.parent), stdio='pipe')
    session = device.attach(pid); session.on('detached', lambda *args: done.set())

    def message(msg, binary):
        if msg['type'] != 'send':
            errors.append(msg); return
        row = msg['payload']
        if binary:
            base = 'mesh-' + str(row['sequence']).zfill(3)
            vertex = data_dir / (base + '.vertices.bin'); index = data_dir / (base + '.indices.bin')
            vertex.write_bytes(binary[:row['vertexBytes']]); index.write_bytes(binary[row['vertexBytes']:])
            row.update(vertexFile=str(vertex), indexFile=str(index), vertexSha256=c.sha(vertex), indexSha256=c.sha(index))
        records.append(row)

    script = session.create_script((Path(__file__).parent / 'capture_native.js').read_text('utf8'))
    script.on('message', message)
    try:
        script.load(); device.resume(pid)
        if not done.wait(145):
            device.kill(pid)
            raise RuntimeError('Owned offscreen observation timed out')
    finally:
        try:
            session.detach()
        except frida.InvalidOperationError:
            pass
    manifest = c.read(out / 'renderer/manifest.json')
    meshes = [r for r in records if r.get('kind') == 'mesh']
    c.dump(dict(source=str(source), sourceSha256=initial_sha, ownedPid=pid,
                records=records, errors=errors, existingUserProcessAttached=False), out / 'meshes.json')
    if errors or any(r.get('kind') == 'missing-required-mesh-buffer' for r in records) or not meshes or manifest['status'] != 'success' or manifest['exit_code'] != 0 or c.sha(source) != initial_sha:
        raise RuntimeError('Native mesh observation failed; inspect retained evidence')
    print(json.dumps(dict(meshes=len(meshes), meshRecord=str(out / 'meshes.json'),
                          permission='Only newly spawned offscreen renderer was observed.'), ensure_ascii=False))


def fields(geometry_file, meshes_file, face, output):
    info = c.read(geometry_file); rec = next(r for r in info['faces'] if r['name'] == face and r['available'])
    records = c.read(meshes_file)['records']; attributes = rec['xml']; matrix = np.array(rec['atlasToNative'])
    world_map = np.zeros((1024, 1024, 3), 'float32'); normal_map = world_map.copy()
    hit = np.zeros((1024, 1024), np.uint8); triangles = 0
    for mesh in records:
        if mesh.get('kind') != 'mesh' or not mesh['allowedSides'] & (1 << rec['slot']):
            continue
        if c.sha(mesh['vertexFile']) != mesh['vertexSha256'] or c.sha(mesh['indexFile']) != mesh['indexSha256']:
            raise ValueError('Mesh buffers changed')
        vertices = np.fromfile(mesh['vertexFile'], '<f4').reshape(-1, 10).astype(float)
        ix = np.fromfile(mesh['indexFile'], '<u4' if mesh['indexType'] == 0x1405 else '<u2').reshape(-1, 3)
        uv = vertices[:, 6:8] * mesh['uvScale']
        atlas = np.c_[uv[:, 0] * 2048 - 1024, 512 - uv[:, 1] * 1024, np.ones(len(vertices))]
        center = atlas[ix].mean(1)
        valid = ((center[:, 0] >= float(attributes['left'])) & (center[:, 0] <= float(attributes['right'])) &
                 (center[:, 1] >= float(attributes['top'])) & (center[:, 1] <= float(attributes['bottom'])))
        native = atlas @ matrix.T; pixel = np.c_[native[:, 0] + 512, 512 - native[:, 1]]
        model = np.array(mesh['model']).reshape(4, 4, order='F')
        world = (np.c_[vertices[:, :3], np.ones(len(vertices))] @ model.T)[:, :3]
        normals = vertices[:, 3:6] @ np.linalg.inv(model[:3, :3])
        normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
        for tri in ix[valid]:
            pts = pixel[tri]; basis = np.c_[pts, np.ones(3)]
            if abs(np.linalg.det(basis)) < .01:
                continue
            x0, y0 = np.maximum(0, np.floor(pts.min(0)).astype(int))
            x1, y1 = np.minimum(1024, np.ceil(pts.max(0)).astype(int) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
            cv2.fillConvexPoly(mask, np.rint((pts - [x0, y0]) * 256).astype('int32'), 1, shift=8)
            yy, xx = np.where(mask); xx += x0; yy += y0
            coords = np.c_[xx, yy, np.ones(len(xx))]
            world_map[yy, xx] = coords @ np.linalg.solve(basis, world[tri])
            normal_map[yy, xx] = coords @ np.linalg.solve(basis, normals[tri])
            hit[yy, xx] = 1; triangles += 1
    permission = np.array(Image.open(rec['maskPath']).convert('L')) >= 128
    visible = permission & (hit > 0)
    if not visible.any():
        raise ValueError('No real UV triangles overlap the permission mask')
    out = Path(output).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise FileExistsError(out)
    np.savez_compressed(out, world=world_map, normal=normal_map, hit=hit, visible=visible)
    Image.fromarray(visible.astype('uint8') * 255).save(out.with_suffix('.visible.png'))
    c.dump(dict(face=face, triangles=triangles, geometrySha256=c.sha(geometry_file),
                meshesSha256=c.sha(meshes_file), visiblePixels=int(visible.sum()),
                permissionPixels=int(permission.sum()), interpolation='Indexed triangle barycentric field; no large-area extrapolation.',
                occlusion='Actual exterior visibility still requires rendered inspection.'), out.with_suffix('.json'))
    print(json.dumps(dict(face=face, fields=str(out), triangles=triangles, visiblePixels=int(visible.sum())), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--profile')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('masks'); p.add_argument('--car-id', type=int, required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('capture'); p.add_argument('--input', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('fields'); p.add_argument('--geometry', required=True); p.add_argument('--meshes', required=True); p.add_argument('--face', choices=c.NAMES, required=True); p.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'masks':
        masks(profile(args.profile), args.car_id, args.output)
    elif args.command == 'capture':
        capture(profile(args.profile), args.input, args.output)
    else:
        fields(args.geometry, args.meshes, args.face, args.output)


if __name__ == '__main__':
    main()
