"""Package the source-built Windows optimizer and its corresponding source."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, zipfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',required=True);p.add_argument('--output',required=True);p.add_argument('--compiler',default='g++');args=p.parse_args()
    binary=Path(args.binary);source=ROOT/'scripts/optimizer_seed.cpp'
    compiler=subprocess.run([args.compiler,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
    info=dict(version=(ROOT/'VERSION').read_text('utf8').strip(),sourceRepository='https://github.com/lin522026298/FH6-Livery-Agent-Workflow',
        sourceCommit=os.environ.get('GITHUB_SHA','local-source-build'),source='optimizer_seed.cpp',sourceSha256=sha(source),binarySha256=sha(binary),
        compiler=compiler,flags=['-O3','-std=c++17','-static'],license='AGPL-3.0; retained original component notices')
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in [('optimizer_seed.exe',binary.read_bytes()),('optimizer_seed.cpp',source.read_bytes()),('LICENSE',(ROOT/'LICENSE').read_bytes()),('SOURCE.json',json.dumps(info,indent=2).encode())]:
            item=zipfile.ZipInfo(name,date_time=(2026,11,4,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
    print(json.dumps(dict(archive=str(out),sha256=sha(out),bytes=out.stat().st_size,sourceSha256=sha(source))))

if __name__=='__main__':main()
