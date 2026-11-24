"""Apply only reviewed recommendation files, preserving live data and rollback copies."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from urllib.request import urlopen

ROOT=Path('/opt/footballknow')
PREFIX='https://raw.githubusercontent.com/hkmszcxyyykf4632/12/'
ALLOWED={'football/recommendations.py','football/racing_analysis.py','public/recommendations.mjs',
         'public/recommendation-video.mjs','public/editorial.css','public/media/recommendation-videos.json'}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def run(*args):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=90).stdout.strip()
def write(path,raw,metadata=None):
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.fengyi-release-',delete=False) as f:
        f.write(raw); temporary=Path(f.name)
    temporary.chmod(metadata.st_mode&0o777 if metadata else 0o644)
    if metadata: os.chown(temporary,metadata.st_uid,metadata.st_gid)
    os.replace(temporary,path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--manifest',required=True);p.add_argument('--forecast',action='store_true');args=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',args.revision)
    manifest=json.loads(Path(args.manifest).read_text())
    base=PREFIX+args.revision+'/'
    staged=[]
    for item in manifest['files']:
        path=item['path']
        assert path in ALLOWED or re.fullmatch(r'public/media/videos/fengyi-racing-20261125-[a-z0-9-]+\.(mp4|jpg)',path)
        target=ROOT/path
        current=target.read_bytes() if target.exists() else None
        assert (sha(current) if current is not None else None)==item['previousSha256'],'Unexpected deployed file: '+path
        with urlopen(base+'footballknow/'+path,timeout=60) as response:raw=response.read(item['bytes']+1)
        assert len(raw)==item['bytes'] and sha(raw)==item['sha256'],'Download mismatch: '+path
        if path.endswith('.py'):compile(raw,path,'exec')
        staged.append((path,target,raw,current,target.stat() if target.exists() else None))
    backup=Path('/var/backups/footballknow/recommendation-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));backup.mkdir(parents=True,mode=0o700)
    for path,target,raw,current,stat in staged:
        if current is not None:
            saved=backup/path;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
    run('systemctl','stop','footballknow-worker')
    try:
        for path,target,raw,current,stat in staged:
            assert (target.read_bytes() if target.exists() else None)==current,'Changed during staging: '+path
            target.parent.mkdir(parents=True,exist_ok=True);write(target,raw,stat)
        run('systemctl','restart','footballknow-web')
        for n in range(20):
            try:
                with urlopen('http://127.0.0.1:8765/api/recommendations',timeout=10) as r:json.load(r)
                break
            except Exception:
                if n==19:raise
                time.sleep(1)
    except Exception:
        for path,target,raw,current,stat in reversed(staged):
            if current is not None:write(target,current,stat)
            elif target.exists():target.unlink()
        run('systemctl','restart','footballknow-web')
        raise
    finally:
        run('systemctl','start','footballknow-worker')
    if args.forecast:
        with tempfile.TemporaryDirectory(prefix='fengyi-reviewed-') as scratch:
            os.chmod(scratch,0o755)
            paths=[]
            for name in ['publish_forecast.py','reviewed-forecast.json']:
                with urlopen(base+'media-projects/fengyi-racing-20261125/'+name,timeout=30) as r:raw=r.read(200000)
                assert sha(raw)==manifest['forecast'][name]
                path=Path(scratch)/name;path.write_bytes(raw);path.chmod(0o644);paths.append(str(path))
            print(run('runuser','-u','footballknow','--','env','FOOTBALL_STATE_DIR=/var/lib/footballknow','PYTHONPATH='+str(ROOT),
                'PYTHONDONTWRITEBYTECODE=1',str(ROOT/'.venv/bin/python'),*paths))
    print(json.dumps({'revision':args.revision,'backup':str(backup),'files':len(staged)},ensure_ascii=False))
    print('FENGYI_RECOMMENDATION_UPDATED')
if __name__=='__main__': main()

