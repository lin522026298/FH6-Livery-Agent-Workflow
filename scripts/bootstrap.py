"""Portable, task-scoped setup. Standard library only; no model API key needed."""
from pathlib import Path, PurePosixPath
import argparse, ctypes, hashlib, json, os, re, shutil, stat, subprocess, sys, time, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

def read(path): return json.loads(Path(path).read_text('utf-8-sig'))
def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024 * 1024): result.update(block)
    return result.hexdigest()

def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
    os.replace(temporary, path)

def safe_extract(archive, target):
    target = Path(target).resolve(); target.mkdir(parents=True, exist_ok=False)
    seen = set()
    with zipfile.ZipFile(archive) as source:
        if sum(item.file_size for item in source.infolist()) > 2_000_000_000:
            raise ValueError('Archive exceeds installation size bound')
        for entry in source.infolist():
            name = entry.filename.replace('\\', '/')
            parts = PurePosixPath(name)
            if (parts.is_absolute() or '..' in parts.parts or ':' in name or
                    stat.S_ISLNK(entry.external_attr >> 16) or name.lower() in seen):
                raise ValueError('Unsafe or duplicate archive path')
            seen.add(name.lower())
            out = target.joinpath(*parts.parts).resolve()
            if not out.is_relative_to(target): raise ValueError('Archive path escapes destination')
        for entry in source.infolist():
            parts = PurePosixPath(entry.filename.replace('\\', '/'))
            out = target.joinpath(*parts.parts)
            if entry.is_dir(): out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with source.open(entry) as src, out.open('xb') as dest: shutil.copyfileobj(src, dest)

def download(spec, output):
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    digest = spec.get('sha256')
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
        raise ValueError('Release asset is not pinned to a verified SHA-256')
    if output.is_file() and sha(output) == digest: return output
    part = output.with_name(output.name + '.part')
    for attempt in range(3):
        try:
            request = urllib.request.Request(spec['url'], headers={'User-Agent':'FH6-Livery-Agent-Workflow'})
            with urllib.request.urlopen(request, timeout=45) as response, part.open('wb') as dest:
                shutil.copyfileobj(response, dest, length=1024 * 1024)
            if sha(part) != digest: raise ValueError('Downloaded release asset SHA-256 mismatch')
            os.replace(part, output); return output
        except (OSError, ValueError):
            if attempt == 2: raise
            time.sleep(attempt + 1)

def install_archive(name, spec, tools, wanted):
    target = tools / (name + '-' + spec['version'])
    marker = target / 'livery-agent-install.json'
    if marker.is_file():
        info = read(marker); exe = target / info['executable']
        if info['archiveSha256'] != spec['sha256'] or sha(exe) != info['exeSha256']:
            raise ValueError('Installed tool differs from verified release; choose a fresh tools root')
        return exe
    if target.exists(): raise ValueError('Incomplete existing installation; preserve it and choose a fresh tools root')
    archive = download(spec, tools / 'downloads' / (name + '-' + spec['version'] + '.zip'))
    safe_extract(archive, target)
    hits = list(target.rglob(wanted))
    if len(hits) != 1: raise ValueError('Release does not contain a unique ' + wanted)
    exe = hits[0]
    dump(marker, dict(archiveSha256=spec['sha256'], executable=exe.relative_to(target).as_posix(), exeSha256=sha(exe)))
    return exe

def content_directory(path):
    path = Path(path).expanduser()
    for candidate in [path, path / 'Content']:
        if (candidate / 'media/Cars').is_dir(): return candidate.resolve()
    return None

def discover_games():
    candidates = []
    for key in ['FH6_GAME_CONTENT','FORZA_GAME_CONTENT']:
        if os.environ.get(key): candidates.append(Path(os.environ[key]))
    if sys.platform == 'win32':
        bits = ctypes.windll.kernel32.GetLogicalDrives()
        candidates += [Path(chr(65+i)+':/XboxGames/Forza Horizon 6/Content') for i in range(26) if bits & (1 << i)]
        import winreg
        for branch in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                with winreg.OpenKey(branch, r'Software\Valve\Steam') as key:
                    candidates.append(Path(winreg.QueryValueEx(key,'SteamPath')[0]))
            except OSError: pass
    for variable in ['ProgramFiles(x86)','ProgramFiles']:
        if os.environ.get(variable): candidates.append(Path(os.environ[variable]) / 'Steam')
    steam_roots = list(candidates)
    for steam in steam_roots:
        library = steam / 'steamapps/libraryfolders.vdf'
        if library.is_file():
            for item in re.findall(r'"path"\s+"([^"]+)"', library.read_text('utf8',errors='replace')):
                candidates.append(Path(item.replace('\\\\','\\')))
    candidates += [p / 'steamapps/common/Forza Horizon 6' for p in list(candidates)]
    found = set()
    for candidate in candidates:
        try:
            path = content_directory(candidate)
            if path: found.add(str(path))
        except OSError: continue
    return sorted(found)

def run(command, **kwargs):
    subprocess.run([str(x) for x in command], check=True, shell=False, creationflags=FLAGS, **kwargs)

def setup(args):
    if sys.platform != 'win32' and not args.synthetic_only:
        raise ValueError('Full vehicle preview and local-save workflow currently require Windows x64')
    tools = Path(args.tools_root).expanduser().resolve(); tools.mkdir(parents=True, exist_ok=True)
    workspace = Path(args.workspace).expanduser().resolve(); workspace.mkdir(parents=True, exist_ok=True)
    if workspace == ROOT or workspace.is_relative_to(ROOT):
        raise ValueError('Keep user projects outside the public repository')
    lock = read(ROOT / 'toolchain.lock.json')
    python = tools / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists(): run([args.uv, 'venv', '--python', lock['python'], tools / '.venv'])
    run([args.uv,'pip','install','--python',python,'-r',ROOT / ('requirements-dev.txt' if args.dev else 'requirements.txt')])
    spec = {}
    if args.optimizer:
        optimizer = Path(args.optimizer).resolve(strict=True)
        spec['optimizerOrigin'] = 'Explicit user/CI-provided source-built binary'
    else:
        optimizer = install_archive('optimizer', lock['optimizer'], tools, 'optimizer_seed.exe')
        spec['optimizerOrigin'] = lock['optimizer']['url']
    if args.synthetic_only:
        fls = preview = tools / 'not-installed-synthetic-only'
        catalog = tools / 'not-installed-synthetic-only.json'
        games = []
    else:
        fls = install_archive('fls',lock['fls'],tools,'ForzaLiveryStudio.exe')
        preview = install_archive('preview',lock['preview'],tools,'FH6Preview.exe')
        catalog = fls.parent / 'assets/cars/car_ids.json'
        if not catalog.is_file(): raise ValueError('FLS release is missing its vehicle catalog')
        games = [str(content_directory(args.game_content))] if args.game_content and content_directory(args.game_content) else discover_games()
    if args.game_content and not content_directory(args.game_content):
        raise ValueError('Specified path does not contain Content/media/Cars')
    game = games[0] if len(games) == 1 else ''
    config = dict(schema=1, runtimePython=str(python), optimizer=str(optimizer), optimizerSha256=sha(optimizer),
        previewExe=str(preview), flsExe=str(fls), carsCatalog=str(catalog), gameContent=game,
        workbenchSource=str(ROOT / 'vendor/workbench-src'), backupPolicyRoot=str(workspace),
        toolsRoot=str(tools), scope='Private local configuration; never publish')
    if not args.synthetic_only: config.update(previewSha256=sha(preview),flsSha256=sha(fls))
    profile = Path(args.profile).resolve() if args.profile else ROOT / '.local/installation.json'
    dump(profile, config)
    # A common root prevents each car/job keeping another full-save backup.
    sys.path.insert(0, str(ROOT / 'vendor/workbench-src'))
    from fh6_livery_workbench.backup_retention import initialize
    initialize(workspace)
    result = dict(status='READY' if game else 'TOOLS_READY_GAME_PATH_NEEDED', profile=str(profile),
        runtimePython=str(python), workspace=str(workspace), gameCandidates=games,
        modelApiKeyRequired=False, actualGameSaveWritten=False, realCustomWritten=False, foregroundInputUsed=False, **spec)
    if args.synthetic_only: result['status'] = 'SYNTHETIC_TOOLS_READY'
    if not args.no_self_test:
        output = tools / 'validation' / ('synthetic-' + str(time.time_ns()))
        run([python, ROOT / 'scripts/self_test.py','--profile',profile,'--output',output])
        if read(output / 'self-test.json')['status'] != 'SYNTHETIC_TECHNICAL_TESTS_PASS':
            raise ValueError('Synthetic tests failed')
        result.update(syntheticSelfTest='PASS', selfTest=str(output / 'self-test.json'))
    dump(ROOT / '.local/bootstrap-result.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uv', default=shutil.which('uv'))
    parser.add_argument('--tools-root', required=True); parser.add_argument('--workspace', required=True)
    parser.add_argument('--game-content'); parser.add_argument('--optimizer'); parser.add_argument('--profile')
    parser.add_argument('--dev',action='store_true'); parser.add_argument('--no-self-test',action='store_true')
    parser.add_argument('--synthetic-only',action='store_true')
    args = parser.parse_args()
    if not args.uv: parser.error('uv required; on Windows use bootstrap.ps1 to install its pinned portable build')
    setup(args)

if __name__ == '__main__': main()
