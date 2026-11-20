"""Current stable membership, scored groups and owner index from public horse profiles."""
import re
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from .files import fetch_text, publish
from .racing import BASE, FOLDER, age, horse_identity, load, now, number, official, text
from .sync_control import read_control
from .horse_going import going_performance, METHOD as GOING_METHOD, SOURCE as GOING_SOURCE


def rating_class(value):
    rating = number(value)
    if rating is None or rating < 0:
        return None
    return 1 if rating > 100 else 2 if rating > 80 else 3 if rating > 60 else 4 if rating > 40 else 5


def parse_trainers(html):
    rows = {}
    for a in BeautifulSoup(html, 'html.parser').select('a[href]'):
        source = official(a['href'])
        if not source or not urlsplit(source).path.endswith('/listbystable'):
            continue
        ident = parse_qs(urlsplit(source).query).get('trainerid', [''])[0]
        if re.fullmatch(r'[A-Z]{1,5}', ident):
            rows[ident] = {'id': ident, 'name': text(a), 'source': source}
    if len(rows) < 15:
        raise ValueError('练马师目录未完整发布。')
    return list(rows.values())


def parse_stable(html, trainer):
    soup = BeautifulSoup(html, 'html.parser')
    heading = text(soup.select_one('.subheader'))
    if trainer['name'] not in heading:
        raise ValueError('马房与请求的练马师不符。')
    expected = re.search(r'總數\s*:\s*(\d+)', heading)
    rows = {}
    for a in soup.select('a[href]'):
        row = a.find_parent('tr')
        if not row:
            continue
        horse = horse_identity(row)
        if not horse:
            continue
        cells = row.find_all('td', recursive=False)
        rating = re.fullmatch(r'\s*\((\d+)\)\s*', text(cells[-1])) if len(cells) == 2 else None
        rows[horse['id']] = {**horse, 'trainer': trainer, 'rating': int(rating[1]) if rating else None}
    if not expected or len(rows) != int(expected[1]):
        raise ValueError('马房马匹数与来源总数不符。')
    return list(rows.values())


def build_directory():
    stable = load(FOLDER / 'stables.json')
    membership = {h['id']: h for h in stable.get('horses', [])}
    people = load(FOLDER / 'people.json')
    portraits = {p['id']: p for p in people.get('trainers', [])}
    horses = []
    for item in load(FOLDER / 'catalogue.json').get('horses', []):
        h = {**item, **membership.get(item['id'], {})}
        detail = load(FOLDER / 'horses' / (item['id'] + '.json'))
        profile = detail.get('profile', {})
        trainer = h.get('trainer') or detail.get('trainer') or {'name': profile.get('練馬師', '待更新'), 'id': ''}
        trainer = {**trainer, 'photo': portraits.get(trainer.get('id'), {}).get('photo')}
        rating = h.get('rating') if item['id'] in membership else number(profile.get('現時評分'))
        horses.append({**h, 'trainer': trainer, 'owner': profile.get('馬主') or None,
                       'rating': rating, 'classGroup': rating_class(rating), 'photo': detail.get('photo'),
                       'pedigree': detail.get('pedigree', {}),
                       'goingPerformance': going_performance(detail.get('records', [])),
                       'profileUpdatedAt': detail.get('updatedAt'), 'recordCount': len(detail.get('records', [])),
                       'recent': [r['position'] for r in detail.get('records', []) if not r.get('withdrawn')][:6]})
    if not horses:
        return 0
    publish(FOLDER / 'directory.json', {'horses': horses, 'updatedAt': now(), 'stableUpdatedAt': stable.get('updatedAt'),
            'goingMethod': GOING_METHOD, 'goingSource': GOING_SOURCE,
            'ownersKnown': sum(bool(h['owner']) for h in horses), 'source': BASE + 'selecthorse',
            'classMethod': '按现时评分分组：第一班 101 分以上、第二班 81–100、第三班 61–80、第四班 41–60、第五班 0–40。实际参赛班次以各场条件为准。'})
    return len(horses)


def sync_directory():
    old = load(FOLDER / 'stables.json')
    if age(old.get('updatedAt')) >= 86400:
        trainers = parse_trainers(fetch_text(BASE + 'selecthorse'))
        horses = []
        for trainer in trainers:
            if not read_control()['enabled']:
                return build_directory()
            horses.extend(parse_stable(fetch_text(trainer['source']), trainer))
        if len({h['id'] for h in horses}) != len(horses):
            raise ValueError('同一马匹出现在多个马房，保留原目录。')
        publish(FOLDER / 'stables.json', {'trainers': trainers, 'horses': horses, 'updatedAt': now()})
    return build_directory()
