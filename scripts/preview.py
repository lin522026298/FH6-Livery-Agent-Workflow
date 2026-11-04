"""Discover and call the portable native previewer; verify requested output artifacts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

PRESETS = ['left', 'right', 'front', 'rear', 'top', 'front-left', 'front-right']


def executable(explicit=None):
    selected = explicit or os.environ.get('FH6_PREVIEW_EXE')
    local_config = Path(__file__).resolve().parents[1] / 'installation.json'
    if not selected and local_config.is_file():
        selected = json.loads(local_config.read_text('utf-8-sig')).get('executable')
    if selected:
        path = Path(selected).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'FH6Preview executable not found: {path}')
        return path
    on_path = shutil.which('FH6Preview.exe')
    if on_path:
        return Path(on_path).resolve()
    configured_root = os.environ.get('FH6_TOOLS_ROOT')
    roots = [Path(configured_root).expanduser()] if configured_root else [Path.cwd(), Path(__file__).resolve().parents[2]]
    candidates = []
    for root in roots:
        direct = root / 'FH6Preview.exe'
        if direct.is_file():
            return direct.resolve()
        candidates.extend(root.glob('FH6-Background-Preview-v*-win-x64/FH6Preview.exe'))
    def version(path):
        match = re.search(r'-v(\d+)\.(\d+)\.(\d+)-win-x64$', path.parent.name)
        return tuple(map(int, match.groups())) if match else (0, 0, 0)
    candidates = sorted((p for p in candidates if p.is_file()), key=version)
    if not candidates:
        raise ValueError('Portable FH6Preview not found; specify --exe or FH6_PREVIEW_EXE / FH6_TOOLS_ROOT')
    return candidates[-1].resolve()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-install', action='store_true')
    parser.add_argument('--exe')
    for name in ['input', 'game', 'output', 'views', 'camera-file', 'cache-dir']:
        parser.add_argument('--' + name)
    parser.add_argument('--view', action='append', default=[])
    parser.add_argument('--size', default='1600x1000')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--texture-scale', type=int, choices=[1, 2, 4], default=4)
    for name in ['fov', 'margin', 'zoom']:
        parser.add_argument('--' + name, type=float)
    parser.add_argument('--allow-crop', action='store_true')
    args = parser.parse_args()
    try:
        if sys.platform != 'win32':
            raise ValueError('This portable renderer requires Windows x64 with desktop OpenGL 3.3')
        exe = executable(args.exe)
        flags = subprocess.CREATE_NO_WINDOW
        if args.check_install:
            p = subprocess.run([str(exe), '--version'], capture_output=True, timeout=15,
                               shell=False, creationflags=flags)
            if p.returncode:
                sys.stderr.buffer.write(p.stderr)
                return p.returncode
            print(json.dumps({'executable': str(exe), 'version': p.stdout.decode('utf-8', 'replace').strip(),
                              'agent_guide': str(exe.parent / 'AGENT_GUIDE.md')}, ensure_ascii=False))
            return 0
        if not all([args.input, args.game, args.output]):
            parser.error('--input --game --output are required unless --check-install is used')
        source, game, output = [Path(p).expanduser().resolve() for p in (args.input, args.game, args.output)]
        command = [str(exe), '--background', '--input', str(source), '--game', str(game),
                   '--output', str(output), '--size', args.size, '--timeout', str(args.timeout),
                   '--texture-scale', str(args.texture_scale)]
        if args.views is not None:
            command += ['--views', args.views]
        for view in args.view:
            command += ['--view', view]
        if args.camera_file:
            command += ['--camera-file', str(Path(args.camera_file).expanduser().resolve())]
        cache = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else output.parent / '.fh6-preview-cache'
        command += ['--cache-dir', str(cache)]
        for name in ['fov', 'margin', 'zoom']:
            if getattr(args, name) is not None:
                command += ['--' + name, str(getattr(args, name))]
        if args.allow_crop:
            command.append('--allow-crop')
        proc = subprocess.run(command, shell=False, creationflags=flags, capture_output=True,
                              timeout=max(1, args.timeout) + 15)
        if proc.returncode:
            sys.stderr.buffer.write(proc.stderr)
            print(json.dumps({'status': 'failed', 'exit_code': proc.returncode,
                              'output': str(output)}, ensure_ascii=False))
            return proc.returncode
        manifest_path = output / 'manifest.json'
        manifest = json.loads(manifest_path.read_text('utf-8'))
        if manifest.get('status') != 'success' or manifest.get('exit_code') != 0:
            raise ValueError('Process exited 0 without a confirmed success manifest')
        actual_input = source / 'C_livery' if source.is_dir() else source
        if digest(actual_input) != manifest['input_sha256']:
            raise ValueError('Input SHA-256 does not match manifest')
        size = tuple(map(int, args.size.lower().split('x')))
        expected = {name: size for name in args.views.split(',') if name} if args.views is not None else {}
        for view in args.view:
            expected[view.split(':')[0]] = size
        if args.camera_file:
            for camera in json.loads(Path(args.camera_file).read_text('utf-8-sig')):
                expected[camera['name']] = (camera.get('width', size[0]), camera.get('height', size[1]))
        if args.views is None and not args.view and not args.camera_file:
            expected = {name: size for name in PRESETS}
        views = manifest.get('views', [])
        if len(views) != len(expected) or {v['name'] for v in views} != set(expected):
            raise ValueError('Exported camera set differs from request')
        if {p.name for p in output.glob('*.png')} != {name + '.png' for name in expected}:
            raise ValueError('PNG file set differs from request')
        verified = []
        for view in views:
            if view['file'] != view['name'] + '.png' or not re.fullmatch(r'[A-Za-z0-9_-]+\.png', view['file']):
                raise ValueError('Unexpected PNG filename in manifest')
            path = output / view['file']
            data = path.read_bytes()
            if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
                raise ValueError(f'Invalid PNG: {path}')
            dimensions = struct.unpack('>II', data[16:24])
            if dimensions != expected[view['name']] or dimensions != (view['width'], view['height']):
                raise ValueError(f'PNG dimensions differ from request: {path}')
            if hashlib.sha256(data).hexdigest() != view['sha256']:
                raise ValueError(f'PNG SHA-256 mismatch: {path}')
            verified.append({'name': view['name'], 'path': str(path), 'size': dimensions,
                             'yaw': view['yaw_deg'], 'pitch': view['pitch_deg']})
        print(json.dumps({'status': 'success', 'manifest': str(manifest_path), 'cache': str(cache), 'views': verified},
                         ensure_ascii=False, indent=2))
        return 0
    except subprocess.TimeoutExpired:
        print(json.dumps({'status': 'failed', 'exit_code': 124, 'error': 'outer process timeout'}))
        return 124
    except (ValueError, OSError, KeyError, TypeError, struct.error) as error:
        print(json.dumps({'status': 'failed', 'exit_code': 8, 'error': str(error)}, ensure_ascii=False))
        return 8


if __name__ == '__main__':
    sys.exit(main())
