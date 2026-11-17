"""On-demand official workouts and per-horse sectionals, with bounded source work."""
import re
import threading
import time
from datetime import datetime

from bs4 import BeautifulSoup

from .files import fetch_text, publish
from .racing import BASE, FOLDER, HK, HORSE_ID, RACE_ID, age, horse_identity, load, now, text
from .sync_control import read_control

LOCK = threading.Lock()
ACTIVE = set()
ATTEMPTS = {}


def parse_workouts(html, ident):
    soup = BeautifulSoup(html, 'html.parser')
    brand = ident.rsplit('_', 1)[-1]
    if not re.search(r'\(' + re.escape(brand) + r'\)', text(soup.select_one('.horseProfile .title_text'))):
        raise ValueError('晨操资料的马匹身份不符。')
    table = next((t for t in soup.select('table.table_bd') if '晨操類別' in text(t.find('thead'))), None)
    if table is None:
        raise ValueError('晨操表格尚未完整提供。')
    records, seen = [], set()
    for row in table.select('tbody tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) != 5:
            continue
        values = [text(c) for c in cells]
        try:
            date = datetime.strptime(values[0], '%d/%m/%Y').date()
        except ValueError:
            continue
        if date > datetime.now(HK).date() or tuple(values) in seen:
            continue
        seen.add(tuple(values))
        detail = values[3]
        distance = re.search(r'(?<!\d)(\d{3,4})\s*(?:M\b|米)', detail, re.I)
        timing = re.findall(r'\((\d+(?:[.:]\d+)+)\)', detail)
        riders = re.findall(r'\(([^\d()][^()]*)\)', detail)
        records.append({'date': date.isoformat(), 'type': values[1], 'track': values[2],
                        'details': detail, 'equipment': values[4] or None,
                        'distance': int(distance[1]) if distance else None,
                        'publishedTime': timing[-1] if timing else None,
                        'rider': riders[-1].strip() if riders else None})
    records.sort(key=lambda r: r['date'], reverse=True)
    return {'horseId': ident, 'records': records, 'fetchedAt': now(),
            'source': BASE + 'trackworkresult?horseid=' + ident}


def parse_sectionals(html, ident):
    match = RACE_ID.fullmatch(ident)
    if not match or not 1 <= int(match[3]) <= 12:
        raise ValueError('分段赛事编号不正确。')
    date = datetime.fromisoformat(match[1]).strftime('%d/%m/%Y')
    course = '沙田' if match[2] == 'ST' else '跑馬地'
    soup = BeautifulSoup(html, 'html.parser')
    body = text(soup)
    if not re.search(r'賽事日期\s*:\s*' + re.escape(date) + r'\s*,\s*' + course, body):
        raise ValueError('分段时间的日期或马场不符。')
    selected = soup.select_one('img[src$="racecard_rt_' + str(int(match[3])) + '_o.gif"]')
    table = soup.select_one('table.race_table')
    if selected is None or table is None:
        raise ValueError('分段时间的场次不符。')
    distance_match = re.search(r'第\s*' + str(int(match[3])) + r'\s*場\s+.{0,90}?-\s*(\d{3,4})米', body)
    distance = int(distance_match[1]) if distance_match else None
    rows = []
    for row in table.select('tbody > tr'):
        cells = row.find_all('td', recursive=False)
        horse = horse_identity(row)
        if len(cells) != 10 or not horse:
            continue
        splits = []
        for cell in cells[3:9]:
            timing = cell.find_all('p', recursive=False)
            if len(timing) < 2:
                continue
            value = re.match(r'^\s*(\d+\.\d+)', text(timing[1]))
            position = text(timing[0].find('span'))
            if not value:
                continue
            splits.append({'seconds': float(value[1]), 'position': int(position) if position.isdigit() else None,
                           'margin': text(timing[0].find('i')) or None,
                           'sub200': [float(text(s)) for s in timing[1].select('.color_blue2 > span')
                                      if re.fullmatch(r'\d+\.\d+', text(s))]})
        if splits and distance and 0 < distance - 400 * (len(splits) - 1) <= 400:
            for i, split in enumerate(splits):
                split['metres'] = distance - 400 * (len(splits) - 1) if i == 0 else 400
        rows.append({'horseId': horse['id'], 'name': horse['name'], 'position': text(cells[0]),
                     'splits': splits, 'finishTime': text(cells[-1])})
    if not rows or len({r['horseId'] for r in rows}) != len(rows):
        raise ValueError('分段时间尚未完整提供。')
    for row in rows:
        row['fieldSize'] = len(rows)
    return {'raceId': ident, 'date': match[1], 'course': course, 'distance': distance, 'horses': rows,
            'fetchedAt': now(), 'source': BASE + 'displaysectionaltime?racedate=' + date + '&RaceNo=' + match[3]}


def refresh(ident):
    path = FOLDER / 'research' / (ident + '.json')
    previous = load(path)
    value = {**previous, 'horseId': ident, 'errors': []}
    try:
        if not read_control()['enabled']:
            return
        if age(value.get('workouts', {}).get('fetchedAt')) >= 86400:
            try:
                value['workouts'] = parse_workouts(fetch_text(BASE + 'trackworkresult?horseid=' + ident), ident)
            except (OSError, ValueError) as error:
                value['errors'].append('晨操暂未更新：' + str(error)[:150])
        records = load(FOLDER / 'horses' / (ident + '.json')).get('records', [])
        recent = sorted((r for r in records if r.get('raceId') and not r.get('withdrawn')),
                        key=lambda r: r['date'], reverse=True)[:3]
        sectionals = []
        prior_rows = {r['raceId']: r for r in previous.get('sectionals', [])}
        for record in recent:
            race_id = record['raceId']
            cache = FOLDER / 'sectionals' / (race_id + '.json')
            race = load(cache)
            if age(race.get('fetchedAt')) >= 30 * 86400 and read_control()['enabled']:
                try:
                    parts = RACE_ID.fullmatch(race_id)
                    if parts is None:
                        continue
                    date = datetime.fromisoformat(parts[1]).strftime('%d/%m/%Y')
                    url = BASE + 'displaysectionaltime?racedate=' + date + '&RaceNo=' + parts[3]
                    race = parse_sectionals(fetch_text(url), race_id)
                    publish(cache, race)
                except (OSError, ValueError) as error:
                    value['errors'].append(record['date'] + ' 分段暂未更新：' + str(error)[:100])
            horse = next((h for h in race.get('horses', []) if h['horseId'] == ident), None)
            if horse:
                sectionals.append({**horse, **{k: race.get(k) for k in ['raceId', 'date', 'course', 'distance', 'source', 'fetchedAt']}})
            elif race_id in prior_rows:
                sectionals.append(prior_rows[race_id])
        value['sectionals'] = sectionals
        value['checkedAt'] = now()
        publish(path, value)
    finally:
        with LOCK:
            ACTIVE.discard(ident)


def get_research(ident):
    if not HORSE_ID.fullmatch(ident) or not (FOLDER / 'horses' / (ident + '.json')).is_file():
        raise LookupError('马匹档案尚未收录。')
    cached = load(FOLDER / 'research' / (ident + '.json'))
    if not read_control()['enabled']:
        return {**cached, 'horseId': ident, 'paused': True, 'message': '同步已暂停，显示最近保存的晨操与分段资料。'}
    if age(cached.get('checkedAt')) < (300 if cached.get('errors') else 86400):
        return cached
    with LOCK:
        if ident in ACTIVE:
            return {**cached, 'horseId': ident, 'pending': True}
        if len(ACTIVE) >= 2:
            return {**cached, 'horseId': ident, 'pending': True, 'message': '正在读取其他马匹资料，稍后自动重试。'}
        if time.monotonic() - ATTEMPTS.get(ident, -float('inf')) < 300:
            return {**cached, 'horseId': ident, 'message': '来源暂未更新，保留已收录资料。'}
        ATTEMPTS[ident] = time.monotonic()
        ACTIVE.add(ident)
        threading.Thread(target=refresh, args=(ident,), daemon=True).start()
    return {**cached, 'horseId': ident, 'pending': True}
