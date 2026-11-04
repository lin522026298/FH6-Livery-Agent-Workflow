from pathlib import Path
import io, json, stat, zipfile
import pytest
import bootstrap
import audit_publication

@pytest.mark.parametrize('name',['../outside.txt','/absolute.txt','C:/outside.txt','safe/../../outside.txt'])
def test_extract_rejects_paths_outside_destination(tmp_path,name):
    archive=tmp_path/'input.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'fixture')
    with pytest.raises(ValueError):bootstrap.safe_extract(archive,tmp_path/'install')
    assert not (tmp_path/'outside.txt').exists()

def test_extract_rejects_symlinks_and_case_aliases(tmp_path):
    archive=tmp_path/'symlink.zip'
    with zipfile.ZipFile(archive,'w') as z:
        entry=zipfile.ZipInfo('link');entry.create_system=3;entry.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(entry,'outside')
    with pytest.raises(ValueError):bootstrap.safe_extract(archive,tmp_path/'symlink-install')
    archive=tmp_path/'duplicate.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('Tool.exe',b'a');z.writestr('tool.exe',b'b')
    with pytest.raises(ValueError):bootstrap.safe_extract(archive,tmp_path/'duplicate-install')

def test_extract_valid_archive_and_hash_checked_reuse(tmp_path,monkeypatch):
    archive=tmp_path/'good.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('portable/Tool.exe',b'SYNTHETIC EXECUTABLE NOT RUN')
    bootstrap.safe_extract(archive,tmp_path/'install')
    assert (tmp_path/'install/portable/Tool.exe').read_bytes()==b'SYNTHETIC EXECUTABLE NOT RUN'
    with pytest.raises(FileExistsError):bootstrap.safe_extract(archive,tmp_path/'install')
    spec=dict(sha256=bootstrap.sha(archive),url='https://example.invalid/not-used')
    assert bootstrap.download(spec,archive)==archive

def test_download_rejects_changed_content_before_publish(tmp_path,monkeypatch):
    monkeypatch.setattr(bootstrap.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(b'CHANGED RELEASE CONTENT'))
    monkeypatch.setattr(bootstrap.time,'sleep',lambda *a:None)
    output=tmp_path/'asset.zip'
    with pytest.raises(ValueError):bootstrap.download(dict(url='https://example.invalid/release',sha256='1'*64),output)
    assert not output.exists()

def test_game_content_discovery_uses_local_environment(tmp_path,monkeypatch):
    game=tmp_path/'Game/Content';(game/'media/Cars').mkdir(parents=True)
    monkeypatch.setenv('FH6_GAME_CONTENT',str(game));monkeypatch.delenv('FORZA_GAME_CONTENT',raising=False)
    monkeypatch.setattr(bootstrap.sys,'platform','linux')
    assert str(game.resolve()) in bootstrap.discover_games()
    assert bootstrap.content_directory(tmp_path/'Game')==game.resolve()
    assert bootstrap.content_directory(tmp_path/'missing') is None

def test_publication_audit_reports_locations_without_secret_values():
    fake='gh'+'p_'+'A'*32
    found=audit_publication.violations('example.txt',fake.encode())
    assert found and found[0]['kind']=='github-credential'
    assert fake not in json.dumps(found)
    assert audit_publication.violations('LICENSE',b'Ordinary public copyright notice')==[]
    assert audit_publication.violations('installation.json',b'{}')
