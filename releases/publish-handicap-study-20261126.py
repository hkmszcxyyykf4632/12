"""Publish only the reviewed static research page; never restart collection workers."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.request import urlopen

ROOT = Path('/opt/footballknow')
BACKUP_ROOT = Path('/var/backups/footballknow')
ORDER = ['public/research/shallow-handicap.json', 'public/handicap-study.css',
         'public/handicap-study.mjs', 'public/app.js', 'public/index.html']
PREFIX = 'https://raw.githubusercontent.com/hkmszcxyyykf4632/12/'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def replace_file(target, raw, stat):
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.handicap-study-', delete=False) as f:
        f.write(raw)
        tmp = Path(f.name)
    try:
        tmp.chmod(stat.st_mode & 0o777 if stat else 0o644)
        if stat: os.chown(tmp, stat.st_uid, stat.st_gid)
        os.replace(tmp, target)
    finally:
        if tmp.exists(): tmp.unlink()


def publish(args):
    if not re.fullmatch('[0-9a-f]{40}', args.revision): raise ValueError('A pinned revision is required')
    manifest = json.loads(Path(args.manifest).read_text())
    items = {x['path']: x for x in manifest['files']}
    assert set(items) == set(ORDER) and len(manifest['files']) == len(ORDER)
    staged = []
    for name in ORDER:
        item = items[name]
        target = ROOT / name
        assert target.resolve().is_relative_to((ROOT/'public').resolve()) and not target.is_symlink()
        before = target.read_bytes() if target.exists() else None
        size = item['bytes']
        assert 0 < size < 2_000_000
        with urlopen(PREFIX+args.revision+'/footballknow/'+name, timeout=30) as response:
            raw = response.read(size+1)
        assert len(raw)==size and sha(raw)==item['sha256'], 'Staged checksum mismatch: '+name
        if before == raw: continue
        expected = item['previousSha256']
        normalized = sha(before.replace(bytes([13,10]), bytes([10]))) if before is not None else None
        valid_old = expected is None and before is None
        valid_old = valid_old or (before is not None and expected in (sha(before), normalized))
        assert valid_old, 'Unexpected live version: '+name
        if name.endswith('.json'):
            report=json.loads(raw)
            assert report['version']=='closing-shallow-handicap-v1' and report['all']['summary']['n']==2450
            assert [x['summary']['n'] for x in report['seasons']]==[882,794,774]
        staged.append((name,target,raw,before,target.stat() if target.exists() else None))
    if args.check_only:
        print(json.dumps({'status':'verified', 'filesToChange':len(staged), 'revision':args.revision}));return
    if not staged:
        print('FENGYI_HANDICAP_STUDY_ALREADY_CURRENT');return
    backup=BACKUP_ROOT/('handicap-study-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir(parents=True, mode=0o700)
    for name,target,raw,before,stat in staged:
        if before is not None:
            destination=backup/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,destination)
    (backup/'release.json').write_text(json.dumps({'revision':args.revision,'files':manifest['files']}))
    applied=[]
    try:
        for name,target,raw,before,stat in staged:
            assert (target.read_bytes() if target.exists() else None)==before, 'File changed during staging: '+name
            target.parent.mkdir(parents=True,exist_ok=True)
            replace_file(target,raw,stat);applied.append((target,before,stat))
        for name in ORDER:
            with urlopen('http://127.0.0.1:8765/'+name.removeprefix('public/'),timeout=15) as response:
                content=response.read(items[name]['bytes']+1)
            assert sha(content)==items[name]['sha256'], 'Live HTTP verification failed: '+name
    except Exception:
        for target,before,stat in reversed(applied):
            if before is None: target.unlink(missing_ok=True)
            else: replace_file(target,before,stat)
        raise
    print(json.dumps({'status':'published','revision':args.revision,'files':len(staged),'backup':str(backup)}))
    print('FENGYI_HANDICAP_STUDY_PUBLISHED')


def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--manifest',required=True)
    p.add_argument('--check-only',action='store_true');args=p.parse_args()
    with open('/var/lock/fengyi-handicap-study.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        publish(args)


if __name__=='__main__': main()
