"""Verify bundled native authoring tools against their module/CLI contract."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
vendor=ROOT/"vendor/workbench-src"
sys.path.insert(0,str(vendor))
from fh6_livery_workbench.cli import _parser

def main():
    m=json.loads((vendor/"distribution.json").read_text())
    package=vendor/"fh6_livery_workbench"
    actual={p.name for p in package.iterdir() if p.is_file()}
    assert actual == set(m["modules"]),"Native module manifest mismatch"
    for name,digest in m["files"].items():
        assert hashlib.sha256((package/name).read_bytes()).hexdigest() == digest,name
    sub=next(a for a in _parser()._actions if hasattr(a,"choices") and isinstance(a.choices,dict))
    assert set(sub.choices) == set(m["commands"]),"Native command contract mismatch"
    print(json.dumps(dict(status="NATIVE_TOOLS_VERIFIED",version=m["version"],modules=len(actual))))

if __name__ == "__main__":main()
