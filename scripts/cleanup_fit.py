"""Remove only hash-verified, regenerable fit buffers listed by livery.py."""
from pathlib import Path
import argparse, json, os, stat, subprocess
import core as c

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True);p.add_argument('--apply',action='store_true');args=p.parse_args()
    plan=c.read(args.plan)
    if plan.get('kind')!='owned-regenerable-fit-buffers':raise ValueError('Unexpected plan')
    root=Path(plan['root']).resolve(strict=True)
    allowed={'target.rgb','foreground.bin','weights.bin','base_seed.rgb','base_seed.alpha'}
    files=[]
    for row in plan['files']:
        file=Path(row['path']);resolved=file.resolve(strict=True)
        if resolved!=file.absolute() or not resolved.is_relative_to(root/'work') or resolved.name not in allowed:raise ValueError('Buffer escaped exact task scope')
        for parent in (resolved,*resolved.parents):
            if stat.S_ISLNK(parent.lstat().st_mode) or getattr(parent.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Reparse point refused')
        if resolved.stat().st_size!=row['bytes'] or c.sha(resolved)!=row['sha256']:raise ValueError('Buffer changed; still in use or incorrect plan')
        files.append(str(resolved))
    if args.apply:
        if os.name=='nt':
            powershell=__import__('shutil').which('pwsh') or __import__('shutil').which('powershell.exe')
            subprocess.run([powershell,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(Path(__file__).with_name('cleanup_fit.ps1')),'-PlanPath',str(Path(args.plan).resolve())],check=True,shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        else:
            for path in files:Path(path).unlink()
    print(json.dumps(dict(status='REMOVED' if args.apply else 'VERIFIED_PLAN_ONLY',files=files,bytes=sum(r['bytes'] for r in plan['files'])),ensure_ascii=False))

if __name__=='__main__':main()
