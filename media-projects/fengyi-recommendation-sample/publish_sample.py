"""Publish only the checked MP4, poster and one catalogue entry on the existing server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument('--revision', required=True)
args = parser.parse_args()
assert re.fullmatch(r'[0-9a-f]{40}', args.revision), 'A pinned Git commit is required'
root = Path('/opt/footballknow').resolve()
assert (root / 'football/videos.py').is_file()
manifest = json.loads(Path(__file__).with_name('release-manifest.json').read_text(encoding='utf-8'))
base = f'https://raw.githubusercontent.com/hkmszcxyyykf4632/12/{args.revision}/footballknow/public/media/videos/'
output = root / 'public/media/videos'
output.mkdir(parents=True, exist_ok=True)
assert output.resolve().is_relative_to(root / 'public')
with tempfile.TemporaryDirectory(prefix='fengyi-video-') as scratch:
    staged = []
    for item in manifest['files']:
        name = item['name']
        assert name in {'fengyi-recommendation-bologna-20261122-3d-v1.mp4', 'fengyi-recommendation-bologna-20261122-3d-v1.jpg'}
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
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup = Path('/var/backups/footballknow') / ('video-catalogue-' + stamp)
backup.mkdir(mode=0o700, parents=True, exist_ok=False)
if state.exists():
    shutil.copy2(state, backup / 'videos.json')
else:
    (backup / 'catalogue-did-not-exist').write_text('No prior video catalogue', encoding='utf-8')
value = {
    'title': manifest['title'], 'description': manifest['description'], 'category': manifest['category'],
    'url': 'https://inwesting.shop/media/videos/fengyi-recommendation-bologna-20261122-3d-v1.mp4',
    'poster': 'https://inwesting.shop/media/videos/fengyi-recommendation-bologna-20261122-3d-v1.jpg', 'published': True,
}
code = '''import json,sys
from football import videos
value=videos.VideoInput(**json.loads(sys.argv[1]))
rows=videos.catalogue(True)['videos']
old=next((r for r in rows if r['url']==value.url),None)
row=videos.save(value,old['id'] if old else None)
after=videos.catalogue(True)['videos']
assert {r['id'] for r in rows}.issubset({r['id'] for r in after})
print(json.dumps({'id':row['id'],'url':row['url'],'published':row['published'],'catalogueCount':len(after)}))
'''
result = subprocess.run(['runuser', '-u', 'footballknow', '--', 'env', 'FOOTBALL_STATE_DIR=/var/lib/footballknow', 'PYTHONDONTWRITEBYTECODE=1', str(root / '.venv/bin/python'), '-c', code, json.dumps(value)], cwd=root, text=True, capture_output=True, check=True)
print(result.stdout.strip())
with urlopen('http://127.0.0.1:8765/api/videos', timeout=20) as response:
    assert any(r['url'] == value['url'] for r in json.load(response)['videos'])
request = Request('http://127.0.0.1:8765/media/videos/fengyi-recommendation-bologna-20261122-3d-v1.mp4', headers={'Range': 'bytes=0-63'})
with urlopen(request, timeout=20) as response:
    assert response.status == 206 and len(response.read(65)) == 64
print(json.dumps({'backup': str(backup), 'revision': args.revision, 'rangePlayback': True}))
print('FENGYI_RECOMMENDATION_VIDEO_PUBLISHED')
