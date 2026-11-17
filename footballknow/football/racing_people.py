"""Official season standings and profile portraits, without guessing missing statistics."""
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .files import fetch_text, publish
from .hkjc_public import query
from .racing import BASE, FOLDER, age, load, now, number
from .sync_control import read_control

COUNTS = ['numFirst', 'numSecond', 'numThird', 'numFourth', 'numFifth']


def ranking_rows(rows):
    people = []
    for item in rows:
        stats = next((s for s in item.get('ssnStat', []) if s.get('ven') == 'ALL'), None)
        if not stats:
            continue
        dead = next((s for s in item.get('dhStat', []) if s.get('ven') == 'ALL'), {})
        counts = {k: int(stats.get(k) or 0) for k in COUNTS + ['numStarts']}
        if counts['numFirst'] > counts['numStarts'] or any(v < 0 for v in counts.values()):
            raise ValueError('骑练统计不一致。')
        people.append({'id': item['code'], 'name': item['name_ch'], 'nameEn': item['name_en'],
                       'status': item['status'], 'visiting': item.get('visitingIndex') in ('Y', True),
                       **counts, 'prize': number(stats.get('stakeWon')), 'deadHeats': dead})
    def order(p):
        values = []
        for k in COUNTS:
            values.extend([-p[k], int(p['deadHeats'].get(k) or 0)])
        return (*values, p['numStarts'], p['nameEn'].upper())
    people.sort(key=order)
    active = [p for p in people if p['status'] == 'Active' and not p['visiting']]
    other = [p for p in people if p not in active and p['numStarts'] > 0]
    return [{**p, 'rank': i + 1, 'section': 'current'} for i, p in enumerate(active)] + [
        {**p, 'rank': None, 'section': 'other'} for p in other]


def person_photo(html, kind, ident):
    folder = 'TrainerProfile' if kind == 'trainers' else 'JockeyProfile'
    for img in BeautifulSoup(html, 'html.parser').select('img[src]'):
        url = urljoin('https://racing.hkjc.com/', img['src'])
        parts = urlsplit(url)
        if parts.scheme == 'https' and parts.hostname in {'consvc.hkjc.com', 'racing.hkjc.com'} and re.search(
                r'/JockeyTrainersProfile/' + folder + '/' + re.escape(ident) + r'\.(?:jpg|png)$', parts.path, re.I):
            return {'url': url, 'source': BASE + ('trainerprofile?trainerid=' if kind == 'trainers' else 'jockeyprofile?jockeyid=') + ident}
    return None


def sync_people():
    seasons = query('seasons', {'locSim': 'LOCAL'})['racingSeasonPeriod']
    season = max(seasons, key=lambda s: s['startDate'])['code']
    last = query('last', {'venueCodes': ['ST', 'HV', 'CH']}).get('lastMeeting') or {}
    prior = load(FOLDER / 'people.json')
    result = {'season': season, 'asOf': last.get('date') if last.get('season') == season else None, 'updatedAt': now()}
    for kind, field in [('trainers', 'trainerStat'), ('jockeys', 'jockeyStat')]:
        rows = ranking_rows(query(kind, {'season': season})[field])
        if len(rows) < 10:
            raise ValueError('骑练榜尚未完整发布。')
        old = {p['id']: p for p in prior.get(kind, [])}
        for p in rows:
            saved = old.get(p['id'], {})
            p.update(photo=saved.get('photo'), photoCheckedAt=saved.get('photoCheckedAt'))
            if age(p['photoCheckedAt']) > 7 * 86400 and read_control()['enabled']:
                source = BASE + ('trainerprofile?trainerid=' if kind == 'trainers' else 'jockeyprofile?jockeyid=') + p['id']
                try:
                    p['photo'] = person_photo(fetch_text(source), kind, p['id'])
                    p['photoCheckedAt'] = now()
                except (OSError, ValueError):
                    pass
        result[kind] = rows
    publish(FOLDER / 'people.json', result)
    from .horse_directory import build_directory
    build_directory()
    return len(result['jockeys']) + len(result['trainers'])
