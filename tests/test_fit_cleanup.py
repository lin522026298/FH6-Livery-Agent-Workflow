from pathlib import Path
import hashlib,json,sys
import pytest
import cleanup_fit

def test_cleanup_retains_master_and_result_and_rejects_changed_buffers(tmp_path,monkeypatch):
    root=tmp_path/'fit';work=root/'work';work.mkdir(parents=True)
    files=[]
    for name in ['target.rgb','foreground.bin','weights.bin','base_seed.rgb','base_seed.alpha']:
        p=work/name;p.write_bytes(b'OWNED BUFFER');files.append(dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    master=root/'actual-input.png';master.write_bytes(b'PROTECTED INPUT')
    result=work/'result.dat';result.write_bytes(b'PROTECTED FINAL LAYERS')
    plan=root/'cleanup-plan.json';plan.write_text(json.dumps(dict(kind='owned-regenerable-fit-buffers',root=str(root),files=files)),encoding='utf8')
    changed=work/'target.rgb';changed.write_bytes(b'CHANGED')
    monkeypatch.setattr(sys,'argv',['cleanup_fit','--plan',str(plan),'--apply'])
    with pytest.raises(ValueError):cleanup_fit.main()
    assert all(Path(r['path']).exists() for r in files)
    changed.write_bytes(b'OWNED BUFFER');cleanup_fit.main()
    assert all(not Path(r['path']).exists() for r in files)
    assert master.read_bytes()==b'PROTECTED INPUT' and result.read_bytes()==b'PROTECTED FINAL LAYERS'
