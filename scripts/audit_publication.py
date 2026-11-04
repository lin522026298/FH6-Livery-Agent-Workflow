"""Bounded source/release privacy audit. Reports locations, never matched secrets."""
from pathlib import Path
import argparse, hashlib, json, re, subprocess, zipfile

ROOT=Path(__file__).resolve().parents[1]
RULES={
 'model-key':re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{24,}'),
 'github-credential':re.compile(r'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{24,}'),
 'private-key':re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
 'aws-access-id':re.compile(r'AKIA[0-9A-Z]{16}'),
 'embedded-url-credential':re.compile(r'https?://[^/\s:@]+:[^@\s]+@'),
 'personal-windows-home':re.compile(r'\b[A-Za-z]:[\\/]+Users[\\/]+(?!Public\b|Default\b|<user>)[^\\/\s<>]+',re.I),
}
FORBIDDEN={'installation.json','settings.local.json','C_livery','C_group','header','custom-before.json','custom-after.json'}

def violations(name,data):
    path=Path(name); findings=[]
    if path.name in FORBIDDEN or any(part in {'.local','.venv','.tools','workspace','.livery-save-backups'} for part in path.parts):
        findings.append(dict(path=name,line=None,kind='private-runtime-file'))
    if path.suffix.lower() in {'.3so','.rgb','.alpha','.npz','.exe','.dll','.zip','.bin'}:
        findings.append(dict(path=name,line=None,kind='runtime-or-user-binary-in-source'))
    try:text=data.decode('utf-8-sig')
    except UnicodeDecodeError:return findings+[dict(path=name,line=None,kind='unreviewed-binary')]
    for kind,pattern in RULES.items():
        for match in pattern.finditer(text):
            findings.append(dict(path=name,line=text.count('\n',0,match.start())+1,kind=kind))
    return findings

def candidates():
    if (ROOT/'.git').is_dir():
        result=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True)
        return sorted(set(x.decode('utf8') for x in result.stdout.split(b'\0') if x))
    return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and
            not any(part in {'.git','.local','.venv','__pycache__','.pytest_cache','build','dist'} for part in p.relative_to(ROOT).parts)]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');parser.add_argument('--archive')
    args=parser.parse_args();findings=[];files=[]
    if args.archive:
        with zipfile.ZipFile(args.archive) as z:
            for name in z.namelist():
                if name.endswith('/'):continue
                data=z.read(name);findings+=violations(name,data);files.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    else:
        for name in candidates():
            p=ROOT/name
            if p.is_symlink():findings.append(dict(path=name,line=None,kind='source-symlink'));continue
            data=p.read_bytes();findings+=violations(name,data);files.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    result=dict(status='PASS' if not findings else 'REVIEW_REQUIRED',scope='Exact candidate/tracked source or specified source archive',
                checkedFiles=len(files),findings=findings,files=files,matchedValuesPrinted=False)
    if args.output:
        p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:result[k] for k in ['status','checkedFiles','findings','matchedValuesPrinted']},ensure_ascii=False,indent=2))
    return 0 if not findings else 2

if __name__=='__main__':raise SystemExit(main())
