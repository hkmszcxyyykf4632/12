"""Publish verified recommendation media without restarting services or changing forecasts."""
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
from urllib.request import Request, urlopen


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def atomic(path, raw, metadata=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.video-release-', delete=False) as handle:
        handle.write(raw)
        temporary = Path(handle.name)
    try:
        temporary.chmod((metadata.st_mode & 0o777) if metadata else 0o644)
        if metadata:
            os.chown(temporary, metadata.st_uid, metadata.st_gid)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def identity(row):
    return row['event'], row['stage'], row.get('issuedAt', '')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'[0-9a-f]{40}', args.revision)
    manifest = json.loads(Path(args.manifest).read_text())
    assert manifest['site'] == 'https://inwesting.shop'
    root = Path('/opt/footballknow')
    state = Path('/var/lib/footballknow/videos.json')
    index = root / 'public/media/recommendation-videos.json'
    assert root.is_dir() and 'inwesting.shop' in Path('/etc/caddy/Caddyfile').read_text()
    with urlopen('http://127.0.0.1:8765/api/recommendations', timeout=30) as response:
        recommendations = json.load(response)['records']
    now = datetime.now(timezone.utc)
    selected, skipped = [], []
    for entry in manifest['entries']:
        if entry['event'] in manifest.get('publicationHolds', {}):
            skipped.append({'event': entry['event'], 'reason': manifest['publicationHolds'][entry['event']]['reason']})
            continue
        candidate = next((row for row in recommendations if identity(row) == identity(entry)), None)
        assert candidate, 'Original recommendation is missing: ' + entry['event']
        receipt = candidate['receipt']
        for key in ['asianSide', 'line', 'scoreCandidates']:
            assert entry[key] == receipt[key], 'Recommendation binding changed: ' + key
        assert entry['receiptIdentity'] == candidate['identity']
        assert entry['kickoff'] == candidate['kickoff']
        kickoff = datetime.fromisoformat(candidate['kickoff'].replace('Z', '+00:00'))
        if kickoff <= now or receipt['status'] != 'pending':
            skipped.append({'event': entry['event'], 'reason': 'Already started or no longer pending'})
        else:
            selected.append(entry)
    assert selected, 'No future pending recommendations remain; do not publish retrospectively.'
    wanted = {entry[key].removeprefix('/') for entry in selected for key in ['url', 'poster']}
    files = [row for row in manifest['files'] if row['path'].removeprefix('public/') in wanted]
    assert len(files) == len(wanted)
    before_index = index.read_bytes()
    before_catalogue = state.read_bytes()
    old_index = json.loads(before_index)
    catalogue = json.loads(before_catalogue)
    old_ids = {row['id'] for row in catalogue['videos']}
    stamp = now.isoformat()
    worker_pid = subprocess.check_output(['systemctl', 'show', '-p', 'MainPID', '--value', 'footballknow-worker'], text=True).strip()
    backup = Path('/var/backups/footballknow') / ('recommendation-videos-' + now.strftime('%Y%m%dT%H%M%SZ'))
    base = f'https://raw.githubusercontent.com/hkmszcxyyykf4632/12/{args.revision}/footballknow/'
    with tempfile.TemporaryDirectory(prefix='fengyi-recommendation-videos-') as scratch:
        staged = []
        for item in files:
            relative = item['path']
            assert re.fullmatch(r'public/media/videos/fengyi-football-[0-9]{8}-[a-z0-9-]+-local-v1\.(mp4|jpg)', relative)
            assert 0 < item['bytes'] <= 30_000_000
            assert re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
            target = root / relative
            if target.exists():
                assert digest(target.read_bytes()) == item['sha256'], 'A different version already exists: ' + relative
            with urlopen(base + relative, timeout=90) as response:
                raw = response.read(item['bytes'] + 1)
            assert len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'Media download differs: ' + relative
            local = Path(scratch) / Path(relative).name
            local.write_bytes(raw)
            staged.append((target, local))
        backup.mkdir(parents=True, mode=0o700)
        (backup / 'recommendation-videos.json').write_bytes(before_index)
        (backup / 'videos.json').write_bytes(before_catalogue)
        index_stat, state_stat = index.stat(), state.stat()
        ready_at = datetime.now(timezone.utc)
        skipped.extend({'event': e['event'], 'reason': 'Started during staging'} for e in selected if datetime.fromisoformat(e['kickoff'].replace('Z', '+00:00')) <= ready_at)
        selected = [e for e in selected if datetime.fromisoformat(e['kickoff'].replace('Z', '+00:00')) > ready_at]
        assert selected, 'All matches started during staging'
        existing = {identity(row): row for row in old_index['videos']}
        additions = []
        for entry in selected:
            key = identity(entry)
            if key in existing:
                assert existing[key]['url'] == entry['url'], 'Refusing to overwrite another published video'
            else:
                additions.append({**entry, 'videoPublishedAt': stamp})
        next_index = {**old_index, 'updatedAt': stamp, 'videos': old_index['videos'] + additions}
        for entry in selected:
            ident = 'fengyi-' + entry['event'] + '-' + entry['receiptIdentity'][:8]
            url = manifest['site'] + entry['url']
            if ident in old_ids:
                assert next(row for row in catalogue['videos'] if row['id'] == ident)['url'] == url
                continue
            catalogue['videos'].append({
                'id': ident, 'title': entry['title'], 'description': entry['description'],
                'category': 'football', 'url': url, 'streamUrl': url,
                'poster': manifest['site'] + entry['poster'], 'published': True,
                'createdAt': stamp, 'updatedAt': stamp, 'publishedAt': stamp,
                'playback': {'kind': 'file', 'url': url},
            })
        catalogue['updatedAt'] = stamp
        catalogue['version'] = 1
        written = []
        try:
            assert index.read_bytes() == before_index and state.read_bytes() == before_catalogue, 'Publication records changed during staging; retry safely.'
            for target, local in staged:
                if not target.exists():
                    atomic(target, local.read_bytes())
                    written.append(target)
            atomic(state, encoded(catalogue), state_stat)
            atomic(index, encoded(next_index), index_stat)
            for entry in selected:
                request = Request('http://127.0.0.1:8765' + entry['url'], headers={'Range': 'bytes=0-63'})
                with urlopen(request, timeout=10) as response:
                    assert response.status == 206 and len(response.read(65)) == 64
            with urlopen('http://127.0.0.1:8765/api/videos', timeout=20) as response:
                public_ids = {row['id'] for row in json.load(response)['videos']}
            assert all('fengyi-' + e['event'] + '-' + e['receiptIdentity'][:8] in public_ids for e in selected)
            assert subprocess.check_output(['systemctl', 'show', '-p', 'MainPID', '--value', 'footballknow-worker'], text=True).strip() == worker_pid
        except Exception:
            atomic(index, before_index, index_stat)
            atomic(state, before_catalogue, state_stat)
            for path in written:
                path.unlink(missing_ok=True)
            raise
    report = {'revision': args.revision, 'publishedAt': stamp, 'publishedEvents': [e['event'] for e in selected],
              'skipped': skipped, 'backup': str(backup), 'workerNotRestarted': True, 'forecastsUnchanged': True}
    (backup / 'result.json').write_bytes(encoded(report))
    atomic(root / 'public/media/recommendation-video-release.json', encoded(report))
    print(json.dumps(report, ensure_ascii=False))
    print('FENGYI_RECOMMENDATION_VIDEOS_PUBLISHED')


if __name__ == '__main__':
    main()
