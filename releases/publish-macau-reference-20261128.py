"""Pinned, scoped release with checksum preconditions, backup and service rollback."""
import argparse, fcntl, hashlib, json, os, re, shutil, sqlite3, subprocess, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
ROOT=Path('/opt/footballknow')
PREFIX='https://raw.githubusercontent.com/hkmszcxyyykf4632/12/'
FILES=['football/odds_reference.py', 'football/odds_signals.py', 'football/odds_forecast.py', 'football/football_forecasts.py']
sha=lambda b:hashlib.sha256(b).hexdigest()
def service(action):
    subprocess.run(['systemctl',action,'footballknow-web.service','footballknow-worker.service'],check=True,timeout=650)
def replace(target,raw,stat):
    with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as f:
        f.write(raw);temp=Path(f.name)
    temp.chmod(stat.st_mode&0o777 if stat else 0o644)
    owner=stat or (ROOT/'football').stat()
    os.chown(temp,owner.st_uid,owner.st_gid)
    os.replace(temp,target)
def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--manifest',required=True);p.add_argument('--check-only',action='store_true');a=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',a.revision)
    assert 'inwesting.shop' in Path('/etc/caddy/Caddyfile').read_text()
    items=json.loads(Path(a.manifest).read_text())['files'];assert {v['path'] for v in items}==set(FILES) and len(items)==len(FILES)
    staged=[]
    for item in items:
        name=item['path'];target=ROOT/name
        assert target.resolve().is_relative_to(ROOT.resolve()) and not target.is_symlink()
        old=target.read_bytes() if target.exists() else None
        with urlopen(PREFIX+a.revision+'/footballknow/'+name,timeout=40) as r:raw=r.read(2000001)
        assert len(raw)==item['bytes'] and sha(raw)==item['sha256'], 'New checksum: '+name
        if name.endswith('.py'):compile(raw,name,'exec')
        if old==raw:continue
        expected=item['previousSha256']
        assert (old is None and expected is None) or (old is not None and expected in (sha(old),sha(old.replace(b'\r\n',b'\n')))), 'Live version differs: '+name
        staged.append((target,raw,old,target.stat() if target.exists() else None))
    if a.check_only:
        print(json.dumps({'status':'verified','files':len(staged),'revision':a.revision}));return
    backup=Path('/var/backups/footballknow')/('macau-reference-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True,mode=0o700)
    for target,raw,old,stat in staged:
        if old is not None:
            dest=backup/target.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,dest)
    for name in ['football-forecasts.sqlite3','recommendations.sqlite3','odds-observations.sqlite3']:
        src=Path('/var/lib/footballknow')/name
        if src.exists():
            with sqlite3.connect(src) as source,sqlite3.connect(backup/name) as dest:source.backup(dest)
    (backup/'manifest.json').write_text(json.dumps(items))
    applied=[]
    service('stop')
    try:
        for target,raw,old,stat in staged:
            assert (target.read_bytes() if target.exists() else None)==old
            replace(target,raw,stat);applied.append((target,old,stat))
        subprocess.run([str(ROOT/'.venv/bin/python'),'-c','from football import odds_reference,odds_signals,odds_forecast,football_forecasts; import server'],cwd=ROOT,check=True,timeout=60,env={**os.environ,'FOOTBALL_STATE_DIR':'/var/lib/footballknow','PYTHONDONTWRITEBYTECODE':'1'})
        service('start')
        for attempt in range(20):
            try:
                with urlopen('http://127.0.0.1:8765/api/football-forecasts?compact=true',timeout=15) as r:assert r.status==200
                break
            except OSError:
                if attempt==19:raise
                time.sleep(1)
        for item in items:
            if item['path'].startswith('public/'):
                with urlopen('http://127.0.0.1:8765/'+item['path'][7:],timeout=15) as r:assert sha(r.read())==item['sha256']
    except Exception:
        service('stop')
        for target,old,stat in reversed(applied):
            if old is None:target.unlink(missing_ok=True)
            else:replace(target,old,stat)
        service('start');raise
    print(json.dumps({'status':'published','revision':a.revision,'files':len(staged),'backup':str(backup)}))
    print('FENGYI_MACAU_REFERENCE_PUBLISHED')
if __name__=='__main__':
    with open('/var/lock/fengyi-macau-reference.lock','w') as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
