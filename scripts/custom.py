"""CAS-preserving FLS Custom merge in an actual process context or explicit test file."""
from pathlib import Path
import argparse, copy, json, os, subprocess
import core as c
from livery import profile


def decode(text):
    if not text.startswith('@ByteArray(') or not text.endswith(')'):
        raise ValueError('Expected Qt QByteArray serialized Custom groups')
    rows = json.loads(text[11:-1])
    if not isinstance(rows, list) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate or invalid Custom group IDs')
    return rows


def merge(before, jobs, replace_authorized=False):
    lookup = {r['id']: r for r in before}; added = []; replacements = {}; report = []
    new_ids = set()
    for job in jobs:
        file = Path(job['project']).resolve(strict=True); digest = c.sha(file)
        if job.get('sha256') and job['sha256'] != digest:
            raise ValueError('Input project hash mismatch')
        doc = c.load(file)
        if doc.get('is_livery'):
            raise ValueError('Custom expects independent decals, not whole liveries')
        c.inspect(doc)
        target_id = job.get('replaceId') or job.get('id') or 'custom_livery_' + digest[:24]
        if target_id in new_ids:
            raise ValueError('Jobs target duplicate IDs')
        new_ids.add(target_id)
        wrapper = copy.deepcopy(doc['root']); wrapper['name'] = job['name']
        row = dict(id=target_id, name=job['name'], clipboard=dict(root=c.group([wrapper], 'Project')))
        row['clipboard']['root']['id'] = '__root__'
        if job.get('replaceId'):
            if not replace_authorized or target_id not in lookup:
                raise ValueError('Exact existing replacement ID and task authorization are required')
            replacements[target_id] = row
        elif target_id in lookup:
            # Wrapper IDs are fresh, so compare source geometry/name rather than a
            # randomized outer project ID for an idempotent re-import.
            old = copy.deepcopy(lookup[target_id]); new = copy.deepcopy(row)
            old['clipboard']['root']['id'] = '__root__'; new['clipboard']['root']['id'] = '__root__'
            if old != new:
                raise ValueError('Same Custom ID has different content; do not silently overwrite')
        else:
            added.append(row)
        report.append(dict(id=target_id, name=row['name'], layers=c.count(doc['root']),
                           source=str(file), sourceSha256=digest, replacement=bool(job.get('replaceId'))))
    after = added + [replacements.get(r['id'], r) for r in before]
    for old in before:
        if old['id'] not in replacements and next(r for r in after if r['id'] == old['id']) != old:
            raise ValueError('An unrelated Custom item changed')
    return after, report, len(added), len(replacements)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--profile')
    p.add_argument('--jobs', required=True); p.add_argument('--output', required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--pid', type=int); group.add_argument('--sandbox-library')
    p.add_argument('--apply', action='store_true'); p.add_argument('--replace-authorized', action='store_true')
    args = p.parse_args(); config = profile(args.profile)
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=False)
    session = None; script = None; context = None
    try:
        if args.pid:
            if args.pid <= 0:
                raise ValueError('Invalid process ID')
            command = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(args.pid) + "' | Select-Object ProcessId,Name,ExecutablePath | ConvertTo-Json -Compress"
            raw_context = subprocess.check_output(['powershell', '-NoProfile', '-Command', command],
                                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            context = json.loads(raw_context.decode('utf-8-sig'))
            actual = Path(context['ExecutablePath']).resolve(strict=True)
            if context['Name'].lower() == 'forzaliverystudio.exe':
                if actual != Path(config['flsExe']).resolve(strict=True):
                    raise ValueError('Actual FLS process is not the configured 1.3.0 installation')
            elif context['Name'].lower() == 'explorer.exe':
                if actual != (Path(os.environ['WINDIR']) / 'explorer.exe').resolve(strict=True):
                    raise ValueError('Explorer context is not the Windows Explorer executable')
            else:
                raise ValueError('Only actual user FLS or explicit Explorer launch context is allowed')
            import frida
            session = frida.attach(args.pid)
            script = session.create_script((Path(__file__).parent / 'user_context_registry.js').read_text('utf8'))
            script.load(); raw = script.exports_sync.read()
            if raw['type'] != 1:
                raise ValueError('Unexpected registry serialization type')
            text = raw['text']
        else:
            library = Path(args.sandbox_library).resolve(strict=True)
            marker = c.read(library.parent / '.livery-workflow-sandbox.json')
            if marker.get('kind') != 'livery-workflow-isolated-custom-test':
                raise ValueError('Isolated Custom marker missing')
            text = library.read_text('utf8')
        before = decode(text)
        c.dump(before, out / 'custom-before.json')
        after, jobs, added, replaced = merge(before, c.read(args.jobs), args.replace_authorized)
        c.dump(after, out / 'custom-after-planned.json')
        encoded = '@ByteArray(' + json.dumps(after, ensure_ascii=True, separators=(',', ':')) + ')'
        if args.apply:
            if script:
                script.exports_sync.write(encoded, text)
                observed = decode(script.exports_sync.read()['text'])
            else:
                if library.read_text('utf8') != text:
                    raise ValueError('Sandbox library changed since read')
                library.write_text(encoded, 'utf8'); observed = decode(library.read_text('utf8'))
            if observed != after:
                raise ValueError('Readback in the writing context differs')
        receipt = dict(status='WRITTEN_RELOAD_AND_USER_VISIBILITY_PENDING' if args.apply and script else
                              'ISOLATED_CUSTOM_READBACK_PASS' if args.apply else 'DRY_RUN_ONLY',
                       context=context, mode='actual-user-process' if script else 'isolated-test-file',
                       before=len(before), added=added, replaced=replaced, after=len(after),
                       unchangedItems=len(before) - replaced, jobs=jobs, keyboardMouseUsed=False,
                       existingWindowClosed=False, userProjectWritten=False,
                       actualCardsVisuallyConfirmed=False)
        c.dump(receipt, out / 'custom-receipt.json')
        print(json.dumps(receipt, ensure_ascii=False), flush=True)
    finally:
        if session:
            session.detach()


if __name__ == '__main__':
    main()
