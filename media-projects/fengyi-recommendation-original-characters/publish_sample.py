"""Replace the approved recommendation sample without changing other catalogue entries."""
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

parser = argparse.ArgumentParser()
parser.add_argument('--revision', required=True)
args = parser.parse_args()
assert re.fullmatch(r'[0-9a-f]{40}', args.revision), 'A pinned Git commit is required'
root = Path('/opt/footballknow').resolve()
assert (root / 'football/videos.py').is_file()
manifest = json.loads(Path(__file__).with_name('release-manifest.json').read_text(encoding='utf-8'))
ident = '1edbe78bf8154245ae46033233cdf629'
assert manifest['videoId'] == ident
stem = 'fengyi-recommendation-bologna-20261122-original-v3'
expected_names = {stem + '.mp4', stem + '.jpg'}
assert {f['name'] for f in manifest['files']} == expected_names
base = f'https://raw.githubusercontent.com/hkmszcxyyykf4632/12/{args.revision}/footballknow/public/media/videos/'
output = root / 'public/media/videos'
output.mkdir(parents=True, exist_ok=True)
assert output.resolve().is_relative_to(root / 'public')
with tempfile.TemporaryDirectory(prefix='fengyi-video-original-') as scratch:
    staged = []
    for item in manifest['files']:
        name = item['name']
        with urlopen(base + name, timeout=120) as response:
            raw = response.read(item['bytes'] + 1)
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'], name
        target = output / name
        if target.exists():
            assert hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256'], 'Existing different media: ' + name
        local = Path(scratch) / name
        local.write_bytes(raw)
        staged.append((local, target))
    for local, target in staged:
        with tempfile.NamedTemporaryFile(dir=output, prefix='.upload-', delete=False) as temp:
            temp.write(local.read_bytes())
            tmp = Path(temp.name)
        tmp.chmod(0o644)
        os.replace(tmp, target)

state = Path('/var/lib/footballknow/videos.json')
assert state.is_file(), 'Existing catalogue is required'
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = Path('/var/backups/footballknow') / ('video-original-characters-' + stamp)
backup.mkdir(mode=0o700, parents=True, exist_ok=False)
shutil.copy2(state, backup / 'videos.json')
value = {
    'title': manifest['title'], 'description': manifest['description'], 'category': manifest['category'],
    'url': 'https://inwesting.shop/media/videos/' + stem + '.mp4',
    'poster': 'https://inwesting.shop/media/videos/' + stem + '.jpg', 'published': True,
}
code = '''import json,sys
from football import videos
value=videos.VideoInput(**json.loads(sys.argv[1]))
ident=sys.argv[2]
rows=videos.catalogue(True)['videos']
old=next((r for r in rows if r['id']==ident),None)
assert old and old['url'] in {sys.argv[3],value.url}, 'Catalogue entry changed; inspect before replacement'
others={r['id']:r for r in rows if r['id']!=ident}
row=videos.save(value,ident)
after=videos.catalogue(True)['videos']
assert len(after)==len(rows)
assert {r['id']:r for r in after if r['id']!=ident}==others
assert row['createdAt']==old['createdAt'] and row['publishedAt']==old['publishedAt']
print(json.dumps({'id':row['id'],'url':row['url'],'published':row['published'],'catalogueCount':len(after),'unrelatedEntriesUnchanged':True}))
'''
result = subprocess.run([
    'runuser', '-u', 'footballknow', '--', 'env', 'FOOTBALL_STATE_DIR=/var/lib/footballknow',
    'PYTHONDONTWRITEBYTECODE=1', str(root / '.venv/bin/python'), '-c', code,
    json.dumps(value), ident, manifest['expectedPreviousUrl'],
], cwd=root, text=True, capture_output=True)
if result.returncode:
    raise RuntimeError(result.stderr.strip() or result.stdout.strip())
print(result.stdout.strip())
with urlopen('http://127.0.0.1:8765/api/videos', timeout=20) as response:
    current = next(r for r in json.load(response)['videos'] if r['id'] == ident)
    assert current['url'] == value['url'] and current['title'] == value['title']
request = Request('http://127.0.0.1:8765/media/videos/' + stem + '.mp4', headers={'Range': 'bytes=0-63'})
with urlopen(request, timeout=20) as response:
    assert response.status == 206 and len(response.read(65)) == 64
print(json.dumps({'backup': str(backup), 'revision': args.revision, 'rangePlayback': True}))
print('FENGYI_ORIGINAL_CHARACTERS_VIDEO_PUBLISHED')
