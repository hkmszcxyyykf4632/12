"""Publish the reviewed reading files as a new culture release."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.request import urlopen, Request

ROOT=Path('/srv/jingzang')
FILES={'index.html','index.json','jingzang.js','recorded-reading.js','books/ysj.json'}
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--manifest',required=True);args=p.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',args.revision)
    m=json.loads(Path(args.manifest).read_text());current=ROOT/'current'
    assert current.is_symlink()
    previous=current.resolve(strict=True)
    assert previous.is_relative_to(ROOT/'releases')
    meta=json.loads((previous/'jingzang-release.json').read_text())
    assert meta['revision']==m['previousRevision'],'Culture release changed'
    assert {x['path'] for x in m['files']}==FILES
    caddy=Path('/etc/caddy/Caddyfile').read_bytes()
    staged={}
    for x in m['files']:
        path=x['path'];assert sha((previous/path).read_bytes())==x['previousSha256'],path
        url='https://raw.githubusercontent.com/hkmszcxyyykf4632/12/'+args.revision+'/footballknow/public/jingzang/'+path
        with urlopen(url,timeout=30) as r:raw=r.read(x['bytes']+1)
        assert len(raw)==x['bytes'] and sha(raw)==x['sha256'],path
        staged[path]=raw
    book=json.loads(staged['books/ysj.json']);assert len(book[0]['p'])==61
    assert b'id="reading-options"' in staged['jingzang.js']
    release=ROOT/'releases'/args.revision
    assert not release.exists()
    shutil.copytree(previous,release,symlinks=True)
    for path,raw in staged.items():
        target=release/path
        assert not target.is_symlink()
        target.write_bytes(raw)
        meta['files'][path]=sha(raw)
    meta.pop('archiveSha256',None)
    meta.update(revision=args.revision,previousRevision=m['previousRevision'],publishedAt=datetime.now(timezone.utc).isoformat())
    (release/'jingzang-release.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    link=ROOT/('pending-'+args.revision)
    assert not link.exists() and not link.is_symlink()
    assert current.resolve()==previous and Path('/etc/caddy/Caddyfile').read_bytes()==caddy
    link.symlink_to(release);os.replace(link,current)
    try:
        for path in ['jingzang.js','books/ysj.json']:
            with urlopen(Request('https://tripitaka.shop/'+path+'?reading='+args.revision,headers={'Cache-Control':'no-cache'}),timeout=30) as r:raw=r.read()
            assert sha(raw)==sha(staged[path]),'Public verification: '+path
    except Exception:
        link.symlink_to(previous);os.replace(link,current)
        raise
    print(json.dumps({'revision':args.revision,'previous':str(previous),'updatedFiles':sorted(staged),'caddyUnchanged':Path('/etc/caddy/Caddyfile').read_bytes()==caddy}))
    print('CULTURE_READING_UPDATED')
if __name__=='__main__':main()
