"""Task-scoped blank/inspect/fit/assemble CLI. Run --help; never controls the UI."""
from pathlib import Path
import argparse, copy, json, os, shutil, subprocess, time
import numpy as np
from PIL import Image
import core as c


def profile_file(path=None):
    if path: return Path(path)
    if os.environ.get('LIVERY_PROFILE'): return Path(os.environ['LIVERY_PROFILE'])
    local = c.ROOT / '.local/installation.json'
    return local if local.is_file() else c.ROOT / 'installation.json'


def profile(path):
    path = profile_file(path)
    result = c.read(path)
    result.setdefault('workbenchSource', str(c.ROOT / 'vendor/workbench-src'))
    return result


def fit(spec_path, config):
    spec = c.read(spec_path)
    source = Path(spec['input']).resolve(strict=True)
    out = Path(spec['output']).resolve()
    if source == out or source.is_relative_to(out):
        raise ValueError('Output must not contain the input source')
    out.mkdir(parents=True, exist_ok=False)
    work = out / 'work'; work.mkdir()
    im = np.array(Image.open(source).convert('RGBA')); h, w = im.shape[:2]
    if w * h > 16_777_216:
        raise ValueError('Review resolution and RAM before fitting this large input')
    fg = im[:, :, 3] >= spec.get('alphaThreshold', 128)
    if spec.get('foregroundMask'):
        mask = np.array(Image.open(spec['foregroundMask']).convert('L'))
        if mask.shape != fg.shape:
            raise ValueError('Foreground mask dimensions differ from actual input')
        fg &= mask >= 128
    weights = fg.astype('float32')
    if spec.get('weights'):
        raw = np.array(Image.open(spec['weights']))
        if raw.shape != fg.shape:
            raise ValueError('Weights dimensions differ from actual input')
        maxval = 65535 if raw.dtype.itemsize >= 2 else 255
        weights *= raw.astype('float32') / maxval * float(spec.get('maxWeight', 12))
    if not fg.any() or not np.isfinite(weights).all() or weights.max() <= 0:
        raise ValueError('Empty or invalid design weights')
    if weights.max() > 32:
        raise ValueError('Review unstable very high weights before production')
    budget = int(spec['budget'])
    protected = c.load(spec['protected'])['root']['children'] if spec.get('protected') else []
    protected_count = sum(c.count(n) for n in protected)
    fit_budget = budget - protected_count
    if not 1 <= fit_budget <= 3000:
        raise ValueError('Invalid budget after native protected features')
    seed = '-'
    if spec.get('seedDat'):
        shutil.copy2(spec['seedDat'], work / 'seed.dat'); seed = 'seed.dat'
    frozen = int(spec.get('frozenSeedCount', 0))
    if frozen:
        if seed == '-':
            raise ValueError('Frozen prefix requires a seed')
        (work / 'frozen-seed-count.txt').write_text(str(frozen))
    for data, name in [(im[:, :, :3].astype('float32'), 'target.rgb'),
                       (fg.astype('uint8'), 'foreground.bin'), (weights, 'weights.bin')]:
        data.tofile(work / name)
    base = np.array(spec.get('baseColor', [21, 44, 52]), 'float32')
    np.broadcast_to(base, (h, w, 3)).copy().tofile(work / 'base_seed.rgb')
    np.full((h, w), spec.get('baseAlpha', 0), 'float32').tofile(work / 'base_seed.alpha')
    (work / 'dimensions.txt').write_text(f'{w} {h}')
    shutil.copy2(c.ASSETS / 'templates.dat', work / 'templates.dat')
    for flag in ['detail-search.txt', 'crescent-search.txt']:
        (work / flag).write_text('enabled')
    executable = Path(config['optimizer']).resolve(strict=True)
    if config.get('optimizerSha256') and c.sha(executable) != config['optimizerSha256']:
        raise ValueError('Optimizer differs from verified profile')
    params = dict(spec, resolvedInput=str(source), inputSha256=c.sha(source),
                  inputSize=[w, h], actualFitBudget=fit_budget,
                  protectedLayers=protected_count, maxActualWeight=float(weights.max()),
                  optimizer=str(executable), optimizerSha256=c.sha(executable))
    c.dump(params, out / 'parameters.json')
    shutil.copy2(source, out / 'actual-input.png')
    Image.fromarray(fg.astype('uint8') * 255).save(out / 'actual-domain.png')
    Image.fromarray(np.rint(weights / weights.max() * 65535).astype('uint16')).save(out / 'actual-weights16.png')
    command = [str(executable), str(fit_budget), 'result.dat', seed,
               str(spec.get('passes', 6)), str(spec.get('recycles', 2))]
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0)
    started = time.monotonic()
    with (work / 'fit.log').open('w') as log:
        process = subprocess.run(command, cwd=work, shell=False, stdout=log,
                                 stderr=subprocess.STDOUT, creationflags=flags,
                                 timeout=spec.get('timeoutSeconds', 14400))
    if process.returncode:
        raise RuntimeError(f'Optimizer exit {process.returncode}; inspect fit.log')
    if frozen:
        result = np.loadtxt(work / 'result.dat', skiprows=1, ndmin=2)
        prior = np.loadtxt(work / 'seed.dat', skiprows=1, ndmin=2)
        if not np.array_equal(result[:frozen], prior[:frozen]):
            raise ValueError('Frozen native prefix changed')
    nodes = c.from_dat(work / 'result.dat', w, h)
    doc = c.project(nodes + copy.deepcopy(protected), spec.get('name', out.name))
    if c.count(doc['root']) != budget:
        raise ValueError('Actual final layer count differs from budget')
    c.save(doc, out / 'result.3so')
    c.render(doc, w, h, ss=int(spec.get('supersample', 1))).save(out / 'native.png')
    c.dump(nodes, out / 'native-nodes.json')
    c.dump(dict(status='TECHNICAL_PASS_REQUIRES_VISUAL_REVIEW', layers=budget,
                seconds=time.monotonic() - started, output=str(out / 'result.3so'),
                outputSha256=c.sha(out / 'result.3so'), frozenRowsVerified=frozen), out / 'result.json')
    buffers = [work / n for n in ['target.rgb', 'foreground.bin', 'weights.bin', 'base_seed.rgb', 'base_seed.alpha']]
    c.dump(dict(kind='owned-regenerable-fit-buffers', root=str(out),
                files=[dict(path=str(p), bytes=p.stat().st_size, sha256=c.sha(p)) for p in buffers],
                retained=['actual-input.png', 'actual-domain.png', 'actual-weights16.png', 'parameters.json',
                          'work/result.dat', 'result.3so', 'native.png', 'native-nodes.json', 'result.json'],
                cleanupRequires='Task accepted, no fitting process uses these files; validate absolute paths and use PowerShell Remove-Item -LiteralPath.'), out / 'cleanup-plan.json')
    print(json.dumps(c.read(out / 'result.json'), ensure_ascii=False), flush=True)


def assemble(spec_path):
    spec = c.read(spec_path)
    doc = c.blank(spec['carId'], spec['name'])
    doc['header_metadata']['creator_name'] = spec.get('creator', '')
    if spec.get('liveryPaint'):
        doc['livery_paint'] = c.normalize_paint(c.read(spec['liveryPaint']))
    for face, items in spec['sections'].items():
        slot = c.NAMES.index(face); children = []
        for item in items:
            if 'baseColor' in item:
                rgb = item['baseColor']
                children.append(c.group([c.shape(101, c.tf(sx=1100 / 128, sy=1100 / 128),
                                                              rgb[2::-1] + [255], 'One-layer base')], item.get('name', 'Base')))
            else:
                part = c.load(item['project'])
                if part.get('is_livery'):
                    raise ValueError('Assembly input should be an independent group, not a whole livery')
                part_root = copy.deepcopy(part['root'])
                for n in c.walk(part_root):
                    if 'id' in n:
                        n['id'] = 'assembly-' + __import__('uuid').uuid4().hex
                children.append(c.group([part_root], item['name'], item.get('transform')))
        doc['root']['children'][slot]['children'] = children
    doc['header_metadata']['type_value'] = c.count(doc['root'])
    proof = c.inspect(doc, spec.get('reserves'))
    output = Path(spec['output']).resolve()
    c.save(doc, output)
    c.dump(dict(proof, sourceSpec=str(Path(spec_path).resolve()), sourceSpecSha256=c.sha(spec_path),
                file=str(output), sha256=c.sha(output)), output.with_suffix('.inspection.json'))
    print(json.dumps(proof, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('inspect'); p.add_argument('input')
    p = sub.add_parser('blank'); p.add_argument('--car-id', type=int, required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('fit'); p.add_argument('spec')
    p = sub.add_parser('assemble'); p.add_argument('spec')
    p = sub.add_parser('render'); p.add_argument('input'); p.add_argument('--width', type=int, required=True); p.add_argument('--height', type=int, required=True); p.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'inspect':
        print(json.dumps(c.inspect(c.load(args.input)), ensure_ascii=False, indent=2))
    elif args.command == 'blank':
        c.save(c.blank(args.car_id, 'Blank projection project'), args.output)
    elif args.command == 'fit':
        fit(args.spec, profile(args.profile))
    elif args.command == 'assemble':
        assemble(args.spec)
    elif args.command == 'render':
        c.render(c.load(args.input), args.width, args.height, 2).save(args.output)


if __name__ == '__main__':
    main()
