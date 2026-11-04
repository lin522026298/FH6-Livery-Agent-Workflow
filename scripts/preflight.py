"""Read-only installed-tool inspection; does not start FLS, preview, or the game."""
from pathlib import Path
import argparse, hashlib, importlib.metadata, json, sys
from livery import profile_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); args.profile = profile_file(args.profile)
    config = json.loads(args.profile.read_text('utf-8-sig'))
    config.setdefault('workbenchSource', str(Path(__file__).resolve().parents[1] / 'vendor/workbench-src'))
    checks = []
    for name in ['optimizer', 'previewExe', 'flsExe', 'carsCatalog', 'gameContent', 'workbenchSource']:
        path = Path(config[name]); exists = bool(config[name]) and path.exists()
        if name == 'gameContent': exists = exists and (path / 'media/Cars').is_dir()
        row = dict(tool=name, path=str(path), exists=exists)
        if exists and path.is_file():
            row.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            key = {'optimizer': 'optimizerSha256', 'previewExe': 'previewSha256', 'flsExe': 'flsSha256'}.get(name)
            if key and config.get(key):
                row['matchesConfiguredHash'] = row['sha256'] == config[key]
        checks.append(row)
    packages = {}
    for name in ['numpy', 'Pillow', 'opencv-python-headless', 'frida']:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    ok = all(r['exists'] and r.get('matchesConfiguredHash', True) for r in checks) and all(packages.values())
    result = dict(status='DEPENDENCIES_READY' if ok else 'MISSING_OR_CHANGED_DEPENDENCIES',
                  python=sys.executable, profile=str(args.profile.resolve()), checks=checks, packages=packages,
                  appStarted=False, artworkLoaded=False, inputUsed=False)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with args.output.open('x', encoding='utf8') as stream:
            stream.write(text)
    print(text)
    return 0 if ok else 2


if __name__ == '__main__':
    raise SystemExit(main())
