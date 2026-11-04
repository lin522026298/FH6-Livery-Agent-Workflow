"""Portable native-template project helpers; no previous artwork is loaded."""
from pathlib import Path
import copy, gzip, hashlib, json, math, struct, uuid
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
NAMES = ['Front', 'Back', 'Top', 'Left', 'Right', 'Wing', 'Glass_Front',
         'Glass_Back', 'Glass_Top', 'Glass_Left', 'Glass_Right']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def dump(value, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def load(path):
    doc = json.loads(gzip.decompress(Path(path).read_bytes()))
    if doc.get('format') not in ('fls_editor_project', 'fh6_editor_project'):
        raise ValueError('Not an FLS project')
    if doc.get('version') not in (3, 4):
        raise ValueError('Unsupported project version')
    return doc


def save(doc, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(doc, ensure_ascii=False,
                                              separators=(',', ':'), allow_nan=False).encode(), mtime=0))
    if load(path) != doc:
        raise ValueError('Project round-trip mismatch')


def walk(node):
    yield node
    for child in node.get('children', []):
        yield from walk(child)


def count(node):
    return sum(n.get('kind') == 'shape' for n in walk(node))


def tf(x=0, y=0, sx=1, sy=1, rotation=0, skew=0):
    return dict(x=float(x), y=float(y), scale_x=float(sx), scale_y=float(sy),
                rotation=float(rotation), skew=float(skew))


def matrix(t):
    r = math.radians(t.get('rotation', 0)); c, s = math.cos(r), math.sin(r)
    return np.array([[c, -s, t.get('x', 0)], [s, c, t.get('y', 0)], [0, 0, 1.]]) @ np.array(
        [[1., t.get('skew', 0), 0], [0, 1., 0], [0, 0, 1.]]) @ np.diag(
        [t.get('scale_x', 1), t.get('scale_y', 1), 1.])


def group(children, name, transform=None):
    return dict(kind='group', id='group-' + uuid.uuid4().hex, name=name,
                transform=transform or tf(), opacity=1., visible=True, locked=False,
                is_livery_section=False, livery_section_slot=-1, debug={}, children=children)


def shape(sid, transform, color, name='Native shape'):
    return dict(kind='shape', id='shape-' + uuid.uuid4().hex, name=name,
                transform=transform, opacity=1., visible=True, locked=False, mask=False,
                color=list(map(int, color)), visual=dict(kind='vector', shape_id=int(sid)),
                debug=dict(source_shape=0, abs_offset=0, marker='', flags=0,
                           source_logo_id=0, has_source_transform=False))


def project(children, name, car_id=None, creator=''):
    root = group(children, 'Root')
    result = dict(format='fls_editor_project', version=3, name=name, is_livery=car_id is not None,
                  source_folder='', source_dec_prefix='', source_header='', root=root,
                  horizontal_guidelines=[], vertical_guidelines=[], color_swatches=[])
    if car_id is not None:
        result.update(car_id=int(car_id), livery_paint=normalize_paint(dict(materials=[])),
                      header_metadata=dict(name=name, car_id=int(car_id), creator_name=creator,
                                           type_value=count(root), description='', published=False))
    return result


def normalize_paint(paint):
    """Materialize the exact native export defaults, including axle fallbacks.

    Empty .3so paint state and a native table full of disabled entries can
    display different default wheels/glass in the reference renderer. Make
    that table explicit in new authoring projects before visual acceptance.
    """
    import native_encoder
    table = native_encoder.descriptors({'livery_paint': paint})
    length = struct.unpack_from('<H', table, 6)[0]
    fmt = '<QB?4B?4BII'; size = struct.calcsize(fmt); rows = []
    for i in range(length):
        row = struct.unpack_from(fmt, table, 14 + i * size)
        rows.append(dict(material_hash='0x' + format(row[0], '016X'),
                         primary=dict(enabled=bool(row[2]), bgra=list(row[3:7])),
                         secondary=dict(enabled=bool(row[7]), bgra=list(row[8:12])),
                         manufacturer_selector=row[12], finish=row[13]))
    return dict(materials=rows)


def blank(car_id, name, colors=None):
    sections = []
    for slot, face in enumerate(NAMES):
        children = []
        if colors and face in colors:
            rgb = colors[face]
            children = [shape(101, tf(sx=1100 / 128, sy=1100 / 128), rgb[2::-1] + [255], 'Projection diagnostic')]
        node = group(children, face)
        node.update(is_livery_section=True, livery_section_slot=slot)
        sections.append(node)
    return project(sections, name, car_id)


def inspect(doc, reserves=None):
    nodes = list(walk(doc['root'])); shapes = [n for n in nodes if n.get('kind') == 'shape']
    ids = [n['id'] for n in nodes if 'id' in n]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate node IDs')
    for node in shapes:
        if node['visual']['kind'] != 'vector':
            raise ValueError('Raster layers need a separately validated encoder')
        if len(node['color']) != 4 or any(type(x) is not int or not 0 <= x <= 255 for x in node['color']):
            raise ValueError('Invalid BGRA')
        if not all(math.isfinite(float(x)) for x in node.get('transform', {}).values()):
            raise ValueError('Nonfinite transform')
    result = dict(name=doc['name'], is_livery=doc.get('is_livery', False), layers=len(shapes))
    if result['is_livery']:
        slots = {s['livery_section_slot']: s for s in doc['root']['children'] if s.get('is_livery_section')}
        if set(slots) != set(range(11)):
            raise ValueError('Expected all eleven native section slots')
        counts = []
        for slot, name in enumerate(NAMES):
            used = count(slots[slot]); limit = 3000 if slot in (2, 3, 4) else 1000
            reserve = (reserves or {}).get(name, 0)
            if used + reserve > limit:
                raise ValueError(f'{name}: {used} + reserved {reserve} exceeds {limit}')
            counts.append(dict(face=name, slot=slot, used=used, limit=limit,
                               reserved=reserve, spare=limit - used))
        result.update(car_id=doc['car_id'], sections=counts)
    return result


def from_dat(path, width, height):
    templates = read(ASSETS / 'templates.json')
    lines = Path(path).read_text('utf8').splitlines()
    result = []
    for line in lines[1:]:
        if not line.strip():
            continue
        typ, x, y, w, h, rot, alpha, r, g, b = map(float, line.split())
        if alpha != 1 or typ != int(typ):
            raise ValueError('Only opaque baseline templates are supported here')
        t = templates[int(typ)]
        transform = tf(x - width / 2, height / 2 - y, w / t['size'][0],
                       h / t['size'][1], -math.degrees(rot) % 360)
        result.append(shape(100 + t['resource_index'], transform,
                            [round(b), round(g), round(r), 255]))
    if len(result) != int(lines[0]):
        raise ValueError('DAT row-count mismatch')
    return result


def render(doc, width, height, ss=1):
    """Diagnostic native triangle render, pixel Y down; no raster stand-ins."""
    geometry = read(ASSETS / 'geometry-basic.json')
    width, height = int(width), int(height)
    out = np.zeros((height * ss, width * ss, 4), np.float32)

    def draw(node, parent):
        m = parent @ matrix(node.get('transform', {}))
        if node.get('kind') != 'shape':
            for child in node.get('children', []):
                draw(child, m)
            return
        if node.get('mask'):
            raise ValueError('Mask preview requires the full FLS renderer')
        sid = str(node['visual']['shape_id'])
        if sid not in geometry:
            raise ValueError(f'{sid}: use full native renderer for this resource')
        g = geometry[sid]; v = np.array(g['vertices'], float)
        p = np.c_[v[:, :2], np.ones(len(v))] @ m.T
        p[:, 0] = (p[:, 0] + width / 2) * ss
        p[:, 1] = (height / 2 - p[:, 1]) * ss
        x0, y0 = np.maximum(0, np.floor(p[:, :2].min(0)).astype(int))
        x1, y1 = np.minimum([width * ss, height * ss], np.ceil(p[:, :2].max(0)).astype(int))
        if x1 <= x0 or y1 <= y0:
            return
        coverage = np.zeros((y1 - y0, x1 - x0), np.float32)
        for indices in g['triangles']:
            pts = p[indices, :2]
            lo = np.maximum([x0, y0], np.floor(pts.min(0)).astype(int))
            hi = np.minimum([x1, y1], np.ceil(pts.max(0)).astype(int))
            l, t = lo; r, b = hi
            if r <= l or b <= t:
                continue
            basis = np.c_[pts, np.ones(3)]
            if abs(np.linalg.det(basis)) < 1e-12:
                continue
            yy, xx = np.mgrid[t:b, l:r]
            weights = np.stack([xx + .5, yy + .5, np.ones_like(xx)], 2) @ np.linalg.inv(basis)
            va = v[indices, 2] if v.shape[1] > 2 else np.ones(3)
            cov = np.where((weights >= -1e-8).all(2), weights @ va, 0)
            region = coverage[t - y0:b - y0, l - x0:r - x0]
            np.maximum(region, cov, out=region)
        a = coverage[:, :, None] * node['color'][3] / 255
        dest = out[y0:y1, x0:x1]
        dest *= 1 - a
        dest[:, :, :3] += a * (np.array(node['color'][2::-1]) / 255)
        dest[:, :, 3:] += a

    draw(doc['root'], np.eye(3))
    alpha = out[:, :, 3:]
    rgb = np.divide(out[:, :, :3], alpha, out=np.zeros_like(out[:, :, :3]), where=alpha > 1e-8)
    result = Image.fromarray(np.rint(np.clip(np.concatenate([rgb, alpha], 2), 0, 1) * 255).astype('uint8'))
    return result.resize((width, height), Image.Resampling.LANCZOS) if ss != 1 else result
