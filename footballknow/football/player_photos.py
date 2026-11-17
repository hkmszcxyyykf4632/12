"""Free portrait images, matched by exact player name and date of birth."""
import json
import urllib.parse
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from .files import PUBLIC, fetch_text, publish
from .leagues import league_path
from .names import EN_API, Player, WikiPage, birth_matches, candidates
from .racing import age, load, now


def lookup(titles):
    params = {'action': 'query', 'titles': '|'.join(titles), 'prop': 'extracts|pageimages',
              'exintro': '1', 'explaintext': '1', 'exlimit': '20', 'piprop': 'thumbnail|name',
              'pithumbsize': '300', 'pilicense': 'free', 'redirects': '1', 'format': 'json', 'formatversion': '2', 'maxlag': '5'}
    return json.loads(fetch_text(EN_API + urllib.parse.urlencode(params))).get('query', {}).get('pages', [])


def credit(file):
    params = {'action': 'query', 'titles': 'File:' + file, 'prop': 'imageinfo', 'iiprop': 'extmetadata|url',
              'format': 'json', 'formatversion': '2', 'maxlag': '5'}
    pages = json.loads(fetch_text(EN_API + urllib.parse.urlencode(params))).get('query', {}).get('pages', [])
    info = next((p['imageinfo'][0] for p in pages if p.get('imageinfo')), {})
    meta = info.get('extmetadata', {})
    clean = lambda key: BeautifulSoup(meta.get(key, {}).get('value', ''), 'html.parser').get_text(' ', strip=True)
    license_name = clean('LicenseShortName')
    if not license_name or not info.get('descriptionurl'):
        return None
    return {'author': clean('Artist'), 'license': license_name, 'source': info['descriptionurl']}


def sync_player_photos(league, limit=60):
    folder = league_path(PUBLIC, league)
    catalogue = load(folder / 'data.json')
    old = load(folder / 'photos.json')
    photos, checked = old.get('photos', {}), old.get('checked', {})
    players = [Player.model_validate(p) for p in catalogue.get('players', []) if p.get('birth_date')]
    pending = sorted([p for p in players if age(checked.get(str(p.code))) > 30 * 86400], key=lambda p: checked.get(str(p.code), ''))[:limit]
    for start in range(0, len(pending), 5):
        chunk = pending[start:start + 5]
        titles = list(dict.fromkeys(t for p in chunk for t in candidates(p)[:3]))
        try:
            pages = lookup(titles)
        except (OSError, ValueError):
            continue
        for player in chunk:
            checked[str(player.code)] = now()
            for page in pages:
                if not page.get('thumbnail', {}).get('source') or not page.get('pageimage'):
                    continue
                if not birth_matches(player, WikiPage.model_validate(page)):
                    continue
                attribution = credit(page['pageimage'])
                if attribution:
                    photos[str(player.code)] = {'url': page['thumbnail']['source'], **attribution,
                           'name': player.known_name or player.web_name, 'birthDate': player.birth_date,
                           'article': 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(page['title']), 'checkedAt': now()}
                    break
        publish(folder / 'photos.json', {'updatedAt': now(), 'photos': photos, 'checked': checked})
    return len(photos)
