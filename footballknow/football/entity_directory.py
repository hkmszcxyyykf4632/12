"""Read-only entity links and racing profiles built from published snapshots."""
import json
import re
import threading
import time
from urllib.parse import parse_qs, quote, urlsplit

from .files import PUBLIC
from .history import CLUB_ALIASES

LEAGUES = {'epl': '', 'laliga': 'laliga/', 'seriea': 'seriea/', 'bundesliga': 'bundesliga/', 'ucl': 'ucl/'}
_cache = {}
_lock = threading.RLock()


def _read(path):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def _cached(key, files, build):
    with _lock:
        prior = _cache.get(key)
        if prior and time.monotonic() - prior[0] < 30:
            return prior[2]
        signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file())
        value = prior[2] if prior and prior[1] == signature else build()
        _cache[key] = (time.monotonic(), signature, value)
        return value


def person_id(person, kind):
    if not isinstance(person, dict):
        return ''
    ident = str(person.get('id') or '')
    if not ident:
        ident = parse_qs(urlsplit(person.get('source') or '').query).get(kind + 'id', [''])[0]
    return ident if re.fullmatch(r'[A-Za-z0-9_-]{1,32}', ident) else ''


def person_href(kind, ident):
    return '#/racing-person/' + kind + '/' + quote(str(ident), safe='')


def _racing_data():
    folder = PUBLIC / 'racing'
    files = [folder / 'directory.json', folder / 'people.json', *sorted((folder / 'races').glob('*.json'))]
    return _cached('racing', files, lambda: (_read(files[0]), _read(files[1]), [_read(p) for p in files[2:]]))


def _people(directory, rankings, races):
    people = {}
    for kind in ('trainer', 'jockey'):
        for p in rankings.get(kind + 's', []):
            ident = person_id(p, kind)
            if ident:
                people[kind, ident] = p
    for row in [*directory.get('horses', []), *(h for r in races for h in r.get('entries', []))]:
        for kind in ('trainer', 'jockey'):
            p = row.get(kind) or {}
            ident = person_id(p, kind)
            if ident:
                people.setdefault((kind, ident), p)
    return people


def entity_index():
    directory, rankings, races = _racing_data()
    files = [PUBLIC / folder / 'data.json' for folder in LEAGUES.values()]
    def build():
        result, clubs = [], []
        for league, folder in LEAGUES.items():
            for t in _read(PUBLIC / folder / 'data.json').get('teams', []):
                same = next((c for c in clubs if (t.get('espnId') and c.get('espnId') == t['espnId']) or
                             (CLUB_ALIASES.get(t.get('name'), t.get('name')) == CLUB_ALIASES.get(c['english'], c['english']) and t.get('cn') == c['name'])), None)
                aliases = [str(v) for v in (t.get('cn'), t.get('name')) if v]
                target = {'league': league, 'id': str(t['id']), 'href': '?league=' + league + '#/team/' + str(t['id'])}
                if same:
                    same['aliases'] = sorted(set(same['aliases'] + aliases))
                    same['targets'].append(target)
                else:
                    clubs.append({'kind': 'team', 'id': league + ':' + str(t['id']), 'name': t.get('cn') or t['name'],
                                  'english': t['name'], 'espnId': t.get('espnId'), 'aliases': aliases,
                                  'href': target['href'], 'targets': [target]})
        result.extend(clubs)
        horses = {h['id']: h for h in directory.get('horses', []) if h.get('id')}
        for race in races:
            for h in race.get('entries', []):
                if h.get('id'):
                    horses.setdefault(h['id'], h)
        for ident, h in horses.items():
            if h.get('name'):
                result.append({'kind': 'horse', 'id': ident, 'name': h['name'], 'aliases': [h['name']], 'href': '#/horse/' + quote(ident, safe='')})
        for (kind, ident), p in _people(directory, rankings, races).items():
            result.append({'kind': kind, 'id': ident, 'name': p.get('name') or ident,
                           'aliases': [v for v in (p.get('name'), p.get('nameEn')) if v], 'href': person_href(kind, ident)})
        for name in sorted({h['owner'] for h in [*directory.get('horses', []), *(h for r in races for h in r.get('entries', []))] if h.get('owner')}):
            result.append({'kind': 'owner', 'id': name, 'name': name, 'aliases': [name], 'href': person_href('owner', name)})
        return {'entities': result, 'version': 1}
    race_files = [PUBLIC / 'racing' / 'directory.json', PUBLIC / 'racing' / 'people.json', *sorted((PUBLIC / 'racing/races').glob('*.json'))]
    return _cached('index', files + race_files, build)


def racing_person(kind, ident):
    if kind not in ('owner', 'trainer', 'jockey') or not ident or len(ident) > 200:
        raise LookupError('未找到这个人物档案。')
    directory, rankings, races = _racing_data()
    horses = directory.get('horses', [])
    people = _people(directory, rankings, races)
    person = {'id': ident, 'name': ident} if kind == 'owner' and any(h.get('owner') == ident for h in [*horses, *(h for r in races for h in r.get('entries', []))]) else people.get((kind, ident))
    if not person:
        raise LookupError('未找到这个人物档案。')
    associated = [h for h in horses if (h.get('owner') == ident if kind == 'owner' else person_id(h.get('trainer'), 'trainer') == ident if kind == 'trainer' else False)]
    entries = []
    for race in races:
        for h in race.get('entries', []):
            matches = h.get('owner') == ident if kind == 'owner' else person_id(h.get(kind), kind) == ident
            if not matches:
                continue
            entries.append({'race': {k: race.get(k) for k in ('id', 'date', 'raceNo', 'courseName', 'distance', 'status', 'resultOfficial')},
                            'horse': {k: h.get(k) for k in ('id', 'name', 'brand', 'number', 'draw', 'place', 'position', 'withdrawn', 'jockey', 'trainer', 'winOdds')}})
    entries.sort(key=lambda r: (r['race']['date'] or '', int(r['race']['raceNo'] or 0)), reverse=True)
    if kind == 'jockey':
        by_id = {h['id']: h for h in horses}
        associated = list({e['horse']['id']: by_id.get(e['horse']['id'], e['horse']) for e in entries if e['horse']['id']}.values())
    compact = [{k: h.get(k) for k in ('id', 'name', 'brand', 'rating', 'classGroup', 'owner', 'trainer', 'photo', 'recent')} for h in associated]
    return {'kind': kind, 'person': person, 'horses': compact, 'entries': entries,
            'season': rankings.get('season'), 'asOf': rankings.get('asOf'), 'updatedAt': rankings.get('updatedAt'),
            'directoryUpdatedAt': directory.get('updatedAt'), 'raceCount': len(races),
            'scope': '出赛记录限本站已收录场次；骑练赛季成绩采用马会排行榜。马匹关联按现役目录或该场出赛记录建立。'}
