"""Native full-livery export and authorized file-only installation; never starts apps."""
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import argparse, copy, json, math, shutil, struct, sys
from PIL import Image
import core as c
from livery import profile


def dependencies(config):
    sys.path.insert(0, str(Path(config['workbenchSource']).resolve(strict=True)))


def export(config, source, seed_path, output, name=None, thumbnail=None):
    dependencies(config)
    from fh6_livery_workbench.container_codec import inspect_livery, unwrap_container, wrap_container
    from fh6_livery_workbench.header_codec import HeaderMetadata, build_header, parse_header
    from fh6_livery_workbench.staging import stage_export
    import native_encoder as encoder
    source = Path(source).resolve(strict=True); original_sha = c.sha(source)
    doc = c.load(source); proof = c.inspect(doc)
    if not doc.get('is_livery'):
        raise ValueError('Export requires a whole livery')
    if any(doc.get(k) for k in ['source_dec_prefix', 'source_header', 'source_folder']):
        raise ValueError('Source-backed editor projects require a validated source-preserving export route')
    # visible=false may only reflect which editor panel was selected; keep ALL
    # native panel shapes, matching the offscreen renderer's documented semantics.
    work = copy.deepcopy(doc)
    for node in c.walk(work['root']):
        node['visible'] = True
        if node.get('mask', False) or node.get('opacity', 1) != 1:
            raise ValueError('Masks/group opacity need a separately validated export route')
    seed_path = Path(seed_path).resolve(strict=True)
    header_seed = parse_header(seed_path.read_bytes())
    if header_seed.published:
        raise ValueError('Use an authorized private identity seed, not another creator share')
    root = Path(output).resolve(); root.mkdir(parents=True, exist_ok=False)
    initial = root / 'native-export'; initial.mkdir()
    counts = [r['used'] for r in proof['sections']]
    emitted = []
    original_artwork = encoder.artwork

    def checked(node, adj, lead, bare):
        out = original_artwork(node, adj, lead, bare)
        row = struct.unpack('<H6f4B', out[-30:])
        if row[0] != node['visual']['shape_id'] or list(row[-4:]) != node['color'] or not all(math.isfinite(v) for v in row[1:7]):
            raise ValueError('Native row mismatch')
        emitted.append(node['id'])
        return out

    encoder.artwork = checked
    encoder.attach(work['root']); geometry, actual = encoder.gyvl(work)
    if actual != counts or len(emitted) != proof['layers']:
        raise ValueError('Native section/layer count mismatch')
    raw = b'vlrc' + struct.pack('<5IH', 2, 0, 0, doc['car_id'], 0, 0)
    raw += b'yrvl' + struct.pack('<I', 19) + header_seed.creator_tag + struct.pack('<I', 1) + b'\0'
    raw += struct.pack('<I', len(geometry)) + geometry
    raw += b'yrvl' + struct.pack('<12I', *counts, 0) + encoder.descriptors(work) + b'yrvl' + struct.pack('<I', 0)
    payload = wrap_container(raw)
    if unwrap_container(payload) != raw:
        raise ValueError('Container round-trip mismatch')
    now = datetime.now(); final_name = name or doc['name']
    header = HeaderMetadata(name=final_name, year=now.year, month=now.month, day=now.day,
                            creator_name=header_seed.creator_name, creator_tag=header_seed.creator_tag,
                            type_value=proof['layers'], car_id=doc['car_id'])
    (initial / 'C_livery').write_bytes(payload); (initial / 'header').write_bytes(build_header(header))
    if thumbnail:
        im = Image.open(thumbnail).convert('RGB'); im.thumbnail((512, 512), Image.Resampling.LANCZOS)
        im.save(initial / 'bigThumb.webp', 'WEBP', quality=92)
    seed = SimpleNamespace(header=header_seed, base=seed_path.parent.name,
                           save_root=SimpleNamespace(platform='pgs', path=seed_path.parent))
    ready = stage_export(initial, seed, root, final_name=final_name)
    info = inspect_livery((ready / 'C_livery').read_bytes())
    result_header = parse_header((ready / 'header').read_bytes())
    result_raw = unwrap_container((ready / 'C_livery').read_bytes())
    stats = info.gyvl_offset + struct.unpack_from('<I', result_raw, info.gyvl_offset - 4)[0]
    if (info.car_id != doc['car_id'] or result_header.car_id != doc['car_id'] or
            result_header.type_value != proof['layers'] or info.source_state != 0 or result_header.published or
            list(struct.unpack_from('<11I', result_raw, stats + 4)) != counts or
            result_raw[info.gyvl_offset:] != raw[info.gyvl_offset:]):
        raise ValueError('Final native export readback failed')
    if c.sha(source) != original_sha:
        raise ValueError('Source changed during export')
    receipt = dict(status='NATIVE_EXPORT_VERIFIED_NOT_INSTALLED', ready=str(ready),
                   source=str(source), sourceSha256=original_sha, sourceUnchanged=True,
                   carId=doc['car_id'], layers=proof['layers'], sectionCounts=counts,
                   seedHeaderSha256=c.sha(seed_path), emittedRecords=len(emitted),
                   files={p.name: c.sha(p) for p in ready.iterdir() if p.is_file() and p.name != 'workbench-ready.json'},
                   appStarted=False, keyboardMouseUsed=False)
    c.dump(receipt, root / 'export-receipt.json')
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


def install(config, ready, output, sandbox_root=None, authorized_note=None, project_root=None):
    dependencies(config)
    from fh6_livery_workbench.installer import backup_save, plan_install, execute_install, active_root
    from fh6_livery_workbench.save_scan import SaveRoot, discover_save_roots
    from fh6_livery_workbench.process_guard import require_game_closed
    from fh6_livery_workbench import backup_retention as retention
    out = Path(output).resolve()
    if sandbox_root:
        base = Path(sandbox_root).resolve(strict=True)
        marker = c.read(base / '.livery-workflow-sandbox.json')
        if marker.get('kind') != 'livery-workflow-isolated-import-test':
            raise ValueError('Sandbox marker missing')
        save = SaveRoot('pgs', 'workflow-sandbox', base / 'current/ContainersRoot')
        if not save.path.is_dir() or save.path.resolve().parent.parent != base:
            raise ValueError('Unexpected isolated sandbox boundary')
        if base.parent != out.parent:
            raise ValueError('Sandbox and install evidence must be siblings inside the same isolated experiment')
        for live in discover_save_roots():
            # A test marker must never turn an actual save/account tree into a
            # sandbox. Compare resolved paths without loading its artwork.
            protected = live.path.resolve(strict=True).parent.parent
            if base == protected or base.is_relative_to(protected) or protected.is_relative_to(base):
                raise ValueError('Sandbox overlaps a real game-save account')
    else:
        if not authorized_note:
            raise ValueError('Live install requires an explicit task-scoped authorization note')
        require_game_closed()
        roots = discover_save_roots()
        if len(roots) != 1 or roots[0].platform != 'pgs':
            raise ValueError('Resolve a unique supported active PGS root first; do not guess')
        save = roots[0]
    root = active_root(save); expected_root = root.resolve(strict=True)
    if root.name != 'ContainersRoot' or root != expected_root:
        raise ValueError('Unexpected save-root boundary')
    if any(p.is_symlink() or (getattr(p.stat(), 'st_file_attributes', 0) & 0x400) for p in root.rglob('*')):
        raise ValueError('Reparse point inside target save tree')
    out.mkdir(parents=True, exist_ok=False)

    def confined_call(function, *arguments, **keywords):
        if not sandbox_root:
            return function(*arguments, **keywords)
        # Only the fake root above is used. Running the user's game must not
        # block an isolated file test or cause us to request that it be closed.
        # The production guard is restored after each individual test call.
        from unittest.mock import patch
        if active_root(save) != root or root.parent.parent != base:
            raise ValueError('Isolated target changed')
        with patch('fh6_livery_workbench.installer.require_game_closed'):
            return function(*arguments, **keywords)

    # All cars and jobs share the explicit project policy. Synthetic exercises
    # always get their own scope, never the production profile's retention root.
    configured_root = project_root or config.get('backupPolicyRoot')
    policy = (base.parent if sandbox_root else retention.policy_root(
        out.parent / '.livery-import-anchor', Path(configured_root) if configured_root else None, source=root))
    backup = None
    try:
        backup = confined_call(backup_save, save, out / 'backup', policy_project=policy)
        before = c.read(backup)
        for row in before['files']:
            if c.sha(root / row['path']) != row['sha256']:
                raise ValueError('Save changed while backing up')
        plan = confined_call(plan_install, Path(ready).resolve(strict=True), save, backup)
        if plan.active_root != root or any(p.resolve().parent != root for p in plan.destinations):
            raise ValueError('Install target escaped exact root')
        c.dump(dict(plan.to_dict(), authorizedNote=authorized_note,
                    mode='isolated-sandbox' if sandbox_root else 'live-local-save'), out / 'install-plan.json')
        journal = confined_call(execute_install, plan, out / 'journal', confirmation='INSTALL', finalize_backup=False)
        if active_root(save) != root:
            raise ValueError('Active root changed')
        for row in before['files']:
            if c.sha(root / row['path']) != row['sha256']:
                raise ValueError('Prior save file changed')
        installed = root / plan.base
        for file, digest in plan.source_hashes.items():
            if c.sha(installed / file) != digest:
                raise ValueError('Installed file hash mismatch')
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        expected = {e['path'] for e in before['files']} | {plan.base + '/' + n for n in plan.source_hashes}
        if actual != expected:
            raise ValueError('Unexpected added/removed save files')
        if not sandbox_root:
            require_game_closed()
    except Exception as error:
        if backup is not None:
            retention.mark_incident(policy, f'Adapter import/readback failed: {error}', manifest=backup)
        raise
    receipt = dict(status='LOCAL_FILES_VERIFIED', mode='isolated-sandbox' if sandbox_root else 'live-local-save',
                   installed=str(installed), priorFilesPreserved=len(before['files']),
                   files=plan.source_hashes, backupManifest=str(backup), journal=str(journal), projectBackupPolicyRoot=str(policy),
                   gameStarted=False, flsStarted=False, foregroundInputUsed=False,
                   inGameInspection='User responsibility; not performed by this command')
    c.dump(receipt, out / 'pre-retention-readback.json')
    try:
        receipt['backupRetention'] = retention.finish_import(backup, journal)
    except Exception as error:
        receipt['backupRetention'] = dict(status='CLEANUP_DEFERRED_BACKUPS_RETAINED', error=str(error))
    c.dump(receipt, out / 'import-receipt.json')
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--profile')
    sub = p.add_subparsers(dest='command', required=True)
    e = sub.add_parser('export'); e.add_argument('--input', required=True); e.add_argument('--seed-header', required=True); e.add_argument('--output', required=True); e.add_argument('--name'); e.add_argument('--thumbnail')
    e = sub.add_parser('install'); e.add_argument('--ready', required=True); e.add_argument('--output', required=True); e.add_argument('--sandbox-root'); e.add_argument('--authorized-note'); e.add_argument('--project-root')
    args = p.parse_args(); config = profile(args.profile)
    if args.command == 'export':
        export(config, args.input, args.seed_header, args.output, args.name, args.thumbnail)
    else:
        install(config, args.ready, args.output, args.sandbox_root, args.authorized_note, args.project_root)


if __name__ == '__main__':
    main()
