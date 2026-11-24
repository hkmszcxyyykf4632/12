"""Publish the smaller playback file and direct-download controls with rollback."""
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
from urllib.request import Request, urlopen


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(*command):
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


def atomic_write(path, raw, metadata=None):
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.video-delivery-', delete=False) as handle:
        handle.write(raw)
        temporary = Path(handle.name)
    if metadata:
        os.chown(temporary, metadata.st_uid, metadata.st_gid)
        temporary.chmod(metadata.st_mode & 0o777)
    else:
        temporary.chmod(0o644)
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{40}', args.revision)
    manifest = json.loads(Path(__file__).with_name('delivery-manifest.json').read_text())
    root = Path('/opt/footballknow')
    caddy = Path('/etc/caddy/Caddyfile')
    state = Path('/var/lib/footballknow/videos.json')
    ident = manifest['videoId']
    before = json.loads(state.read_text())
    old = next(row for row in before['videos'] if row['id'] == ident)
    assert old['url'] == manifest['originalUrl'] and old['published']
    before_bytes = state.read_bytes()
    worker_pid = run('systemctl', 'show', '-p', 'MainPID', '--value', 'footballknow-worker')
    backup = Path('/var/backups/footballknow/video-delivery-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    base = f'https://raw.githubusercontent.com/hkmszcxyyykf4632/12/{args.revision}/footballknow/'
    with tempfile.TemporaryDirectory(prefix='fengyi-video-delivery-') as scratch:
        staged = []
        for item in manifest['files']:
            relative = item['path']
            assert relative in {'football/videos.py', 'public/videos-page.mjs', 'public/video-media.mjs',
                                'deploy/Caddyfile', 'public/media/videos/fengyi-recommendation-bologna-20261122-web-v4.mp4'}
            target = caddy if relative == 'deploy/Caddyfile' else root / relative
            expected = item['previousSha256']
            assert (digest(target.read_bytes()) if target.exists() else None) == expected, 'Deployed file changed: ' + relative
            with urlopen(base + relative, timeout=60) as response:
                raw = response.read(item['bytes'] + 1)
            assert len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'Download mismatch: ' + relative
            local = Path(scratch) / relative
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(raw)
            staged.append((item, local, target))
        run('caddy', 'validate', '--config', str(Path(scratch) / 'deploy/Caddyfile'), '--adapter', 'caddyfile')
        backup.mkdir(mode=0o700, parents=True, exist_ok=False)
        shutil.copy2(state, backup / 'videos.json')
        state_stat = state.stat()
        records = []
        for item, local, target in staged:
            stat = target.stat() if target.exists() else None
            saved = backup / item['path']
            if stat:
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            records.append((target, saved, stat))
        try:
            assert state.read_bytes() == before_bytes, 'Catalogue changed during preparation'
            for item, local, target in staged:
                atomic_write(target, local.read_bytes(), target.stat() if target.exists() else None)
            code = '''import json,sys
from football import videos
ident,expected,stream=sys.argv[1:]
rows=videos.catalogue(True)['videos']
old=next(r for r in rows if r['id']==ident)
assert old['url']==expected and old['published']
others={r['id']:r for r in rows if r['id']!=ident}
row=videos.save(videos.VideoInput(**{**old,'streamUrl':stream}),ident)
after=videos.catalogue(True)['videos']
assert {r['id']:r for r in after if r['id']!=ident}==others
assert row['createdAt']==old['createdAt'] and row['publishedAt']==old['publishedAt']
print(json.dumps({'videoId':ident,'catalogueCount':len(after),'unrelatedEntriesUnchanged':True}))
'''
            result = subprocess.run(['runuser', '-u', 'footballknow', '--', 'env',
                                     'FOOTBALL_STATE_DIR=/var/lib/footballknow', 'PYTHONDONTWRITEBYTECODE=1',
                                     str(root / '.venv/bin/python'), '-c', code, ident, manifest['originalUrl'], manifest['streamUrl']],
                                    cwd=root, check=True, capture_output=True, text=True)
            print(result.stdout.strip())
            run('systemctl', 'restart', 'footballknow-web')
            run('systemctl', 'reload', 'caddy')
            for attempt in range(20):
                try:
                    with urlopen('http://127.0.0.1:8765/api/videos', timeout=3) as response:
                        current = next(r for r in json.load(response)['videos'] if r['id'] == ident)
                    assert current['url'] == manifest['originalUrl'] and current['playback']['url'] == manifest['streamUrl']
                    break
                except Exception:
                    if attempt == 19:
                        raise
                    time.sleep(1)
            for video_url in [manifest['streamUrl'], manifest['originalUrl']]:
                request = Request(video_url + '?download=1', headers={'Range': 'bytes=0-63'})
                with urlopen(request, timeout=20) as response:
                    assert response.status == 206 and len(response.read()) == 64
                    assert response.headers.get('Content-Disposition') == 'attachment'
                    assert 'max-age=86400' in response.headers.get('Cache-Control', '')
            assert run('systemctl', 'show', '-p', 'MainPID', '--value', 'footballknow-worker') == worker_pid
        except Exception:
            for target, saved, stat in reversed(records):
                if stat:
                    atomic_write(target, saved.read_bytes(), stat)
                elif target.exists():
                    target.unlink()
            atomic_write(state, before_bytes, state_stat)
            run('systemctl', 'restart', 'footballknow-web')
            run('systemctl', 'reload', 'caddy')
            print('Rolled back; backup: ' + str(backup))
            raise
    report = {'revision': args.revision, 'backup': str(backup), 'videoId': ident,
              'streamUrl': manifest['streamUrl'], 'rangePlayback': True, 'attachmentDownload': True,
              'workerNotRestarted': True}
    (backup / 'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    print('FENGYI_VIDEO_DELIVERY_UPDATED')


if __name__ == '__main__':
    main()
