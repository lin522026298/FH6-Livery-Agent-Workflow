"""Reproducible synthetic tests. Uses isolated files only, never live save/Custom."""
from pathlib import Path
import argparse, copy, json, shutil, subprocess, sys
from datetime import datetime, timedelta
import numpy as np
from PIL import Image
import core as c
from livery import profile, profile_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile'); p.add_argument('--output', required=True)
    args = p.parse_args(); config = profile(args.profile)
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=False)
    checks = {}; scripts = Path(__file__).parent
    profile_path = profile_file(args.profile).resolve()

    def run(script, *arguments, expected=0):
        command = [sys.executable, str(scripts / script), '--profile', str(profile_path), *map(str, arguments)]
        proc = subprocess.run(command, capture_output=True, text=True, encoding='utf8',
                              errors='replace', shell=False,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if (proc.returncode == 0) != (expected == 0):
            raise RuntimeError(f'{script}: exit={proc.returncode}\n{proc.stdout}\n{proc.stderr}')
        return proc

    nodes = [c.shape(101, c.tf(sx=.5, sy=.4), [30, 70, 110, 255], 'Rectangle'),
             c.shape(102, c.tf(-12, 7, .13, .09, 25), [210, 90, 40, 255], 'Ellipse'),
             c.shape(103, c.tf(17, -8, .13, .18, -19), [40, 190, 230, 255], 'Triangle')]
    doc = c.project(nodes, 'Synthetic native fixture')
    source = out / 'input'; source.mkdir(); c.save(doc, source / 'decal.3so')
    im = c.render(doc, 96, 80, 2); im.save(source / 'input.png')
    pixels = np.array(im)
    assert pixels[5, 5, 3] == 0 and pixels[40, 48, 3] == 255
    assert c.load(source / 'decal.3so') == doc
    checks['projectRoundTripAndTransparency'] = True

    bad = c.blank(3839, 'Overbudget negative fixture')
    bad['root']['children'][2]['children'] = [c.group([copy.deepcopy(nodes[0]) for _ in range(2901)], 'Oversized')]
    for i, n in enumerate(c.walk(bad['root'])):
        n['id'] = 'negative-' + str(i)
    try:
        c.inspect(bad, {'Top': 100})
    except ValueError as error:
        assert 'exceeds' in str(error)
    else:
        raise AssertionError('Budget reserve was ignored')
    checks['reserveIncludesAllLeaves'] = True

    dat = source / 'bad.dat'; dat.write_text('1\n0 10 10 8 8 0 .5 1 2 3\n')
    try:
        c.from_dat(dat, 96, 80)
    except ValueError:
        pass
    else:
        raise AssertionError('Unvalidated opacity was silently flattened')
    checks['unsupportedOpacityRejected'] = True

    fit_spec = dict(input=str(source / 'input.png'), output=str(out / 'fit'), budget=12,
                    passes=1, recycles=0, name='Synthetic twelve-layer test')
    c.dump(fit_spec, source / 'fit.json'); run('livery.py', 'fit', source / 'fit.json')
    assert c.count(c.load(out / 'fit/result.3so')['root']) == 12
    checks['actualTargetBudgetFit'] = True

    full = c.blank(3839, 'ISOLATED_WORKFLOW_SYNTHETIC')
    full['root']['children'][3]['children'] = [c.group(copy.deepcopy(nodes), 'Asymmetric group', c.tf(12, -20, .8, 1.1, 13, .12))]
    c.save(full, source / 'full.3so')
    sys.path.insert(0, str(Path(config['workbenchSource']).resolve()))
    from fh6_livery_workbench.header_codec import HeaderMetadata, build_header
    identity = out / 'identity'; identity.mkdir()
    (identity / 'header').write_bytes(build_header(HeaderMetadata(
        name='ISOLATED_TEST_IDENTITY', creator_name='Workflow Sandbox', creator_tag=b'SIMTEST1',
        car_id=3839, type_value=3, year=2026, month=11, day=4)))
    run('native.py', 'export', '--input', source / 'full.3so', '--seed-header', identity / 'header', '--output', out / 'export')
    exported = c.read(out / 'export/export-receipt.json')
    assert exported['layers'] == 3 and exported['sectionCounts'][3] == 3
    save = out / 'save-sandbox'; (save / 'current/ContainersRoot').mkdir(parents=True)
    c.dump({'kind': 'livery-workflow-isolated-import-test'}, save / '.livery-workflow-sandbox.json')
    sentinel = save / 'current/ContainersRoot/preserved-sentinel.bin'; sentinel.write_bytes(b'KEEP_ME_UNCHANGED')
    sentinel_sha = c.sha(sentinel)
    run('native.py', 'install', '--ready', exported['ready'], '--output', out / 'install', '--sandbox-root', save)
    assert c.sha(sentinel) == sentinel_sha
    receipt = c.read(out / 'install/import-receipt.json')
    assert Path(receipt['projectBackupPolicyRoot']) == out
    first_backup = Path(c.read(receipt['backupManifest'])['archive'])
    assert first_backup.is_file()
    # A second, distinct synthetic item exercises native PGS rotation, not
    # merely the lower-level Steam-shaped unit fixtures.
    original_ready = Path(exported['ready'])
    prefix, stamp = original_ready.name.rsplit('_', 1)
    second_stamp = (datetime.strptime(stamp, '%Y%m%d%H%M%S') + timedelta(seconds=1)).strftime('%Y%m%d%H%M%S')
    second_ready = out / 'second-ready' / (prefix + '_' + second_stamp)
    shutil.copytree(original_ready, second_ready)
    run('native.py', 'install', '--ready', second_ready, '--output', out / 'install-second', '--sandbox-root', save)
    second_receipt = c.read(out / 'install-second/import-receipt.json')
    assert second_receipt['backupRetention']['status'] == 'ROLLING_BACKUP_RETAINED'
    assert not first_backup.exists()
    assert len(list((out / '.livery-save-backups/archives').glob('*.zip'))) == 1
    assert c.sha(sentinel) == sentinel_sha
    checks['projectWideNativePgsBackupRotationAfterReadback'] = True
    run('native.py', 'install', '--ready', second_ready, '--output', out / 'collision', '--sandbox-root', save, expected=1)
    assert c.sha(sentinel) == sentinel_sha
    state = c.read(out / '.livery-save-backups/state.json')
    assert any(not event['resolved_at'] for event in state['incidents'])
    assert len(list((out / '.livery-save-backups/archives').glob('*.zip'))) == 2
    checks['failedNativeImportHoldsBothCompleteBackups'] = True
    checks['nativeExportSandboxInstallAndCollisionRefusal'] = True

    library = out / 'custom-sandbox'; library.mkdir()
    c.dump({'kind': 'livery-workflow-isolated-custom-test'}, library / '.livery-workflow-sandbox.json')
    old = dict(id='unrelated-preserve', name='Unrelated synthetic row', clipboard=dict(root=c.group([], 'Keep')))
    (library / 'library.txt').write_text('@ByteArray(' + json.dumps([old]) + ')', 'utf8')
    jobs = [dict(project=str(source / 'decal.3so'), name='Synthetic decal')]
    c.dump(jobs, source / 'jobs.json')
    for tag in ['append', 'idempotent']:
        run('custom.py', '--jobs', source / 'jobs.json', '--sandbox-library', library / 'library.txt', '--output', out / tag, '--apply')
    before = c.read(out / 'idempotent/custom-receipt.json')
    assert before['added'] == 0 and before['after'] == 2
    target_id = before['jobs'][0]['id']
    c.dump([dict(project=str(source / 'decal.3so'), name='Updated synthetic name', replaceId=target_id)], source / 'replace.json')
    run('custom.py', '--jobs', source / 'replace.json', '--sandbox-library', library / 'library.txt', '--output', out / 'replace', '--apply', '--replace-authorized')
    after = c.read(out / 'replace/custom-after-planned.json')
    assert len(after) == 2 and next(x for x in after if x['id'] == old['id']) == old
    assert next(x for x in after if x['id'] == target_id)['name'] == 'Updated synthetic name'
    checks['customAppendIdempotenceAndExactReplacement'] = True
    c.dump(dict(status='SYNTHETIC_TECHNICAL_TESTS_PASS', checks=checks,
                actualArtOrCarQualityTest=False, productionSaveWritten=False,
                realCustomWritten=False, gameStarted=False, flsStarted=False,
                foregroundInputUsed=False), out / 'self-test.json')
    print(json.dumps(c.read(out / 'self-test.json'), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
