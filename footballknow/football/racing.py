"""HKJC public race facts, with identity checks and bounded cache refreshes."""
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup

from .files import PUBLIC, fetch_text, publish, read_json
from .sync_control import read_control

BASE = 'https://racing.hkjc.com/zh-hk/local/information/'
FOLDER = PUBLIC / 'racing'
HK = timezone(timedelta(hours=8))
HORSE_ID = re.compile(r'HK_\d{4}_[A-Z]\d{3}')
RACE_ID = re.compile(r'(\d{4}-\d{2}-\d{2})-(ST|HV)-(\d{1,2})')
LOCK = threading.Lock()
ATTEMPTS = {}


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    try:
        return read_json(path)
    except (OSError, ValueError):
        return {}


def text(node):
    return node.get_text(' ', strip=True) if node else ''


def number(value):
    try:
        return float(str(value).replace(',', '').replace('$', ''))
    except ValueError:
        return None


def placing(value):
    match = re.match(r'^\s*(\d+)(?:\s|$)', value)
    return int(match[1]) if match else None


def age(stamp):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds()
    except (TypeError, ValueError):
        return float('inf')


def official(href):
    url = urljoin(BASE, href or '')
    p = urlsplit(url)
    return url if p.scheme == 'https' and p.hostname == 'racing.hkjc.com' else None


def horse_identity(node):
    for a in node.select('a[href]'):
        params = {k.lower(): v[0] for k, v in parse_qs(urlsplit(a['href']).query).items()}
        ident = params.get('horseid', '')
        if HORSE_ID.fullmatch(ident) and official(a['href']):
            return {'id': ident, 'name': text(a), 'brand': ident.rsplit('_', 1)[-1], 'source': official(a['href'])}
    return None


def race_url(ident, result=False):
    match = RACE_ID.fullmatch(ident)
    if not match or not 1 <= int(match[3]) <= 12:
        raise LookupError('比赛编号不正确。')
    datetime.fromisoformat(match[1])
    return BASE + ('localresults' if result else 'racecard') + '?' + urlencode({
        'racedate': match[1].replace('-', '/'), 'Racecourse': match[2], 'RaceNo': match[3]})


def race_links(soup, source):
    links = {}
    for a in soup.select('a[href]'):
        url = urljoin(source, a['href'])
        if urlsplit(url).path != urlsplit(source).path or not official(url):
            continue
        q = {k.lower(): v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        if q.get('racecourse') not in {'ST', 'HV'}:
            continue
        ident = q.get('racedate', '').replace('/', '-') + '-' + q['racecourse'] + '-' + q.get('raceno', '')
        if RACE_ID.fullmatch(ident):
            links[ident] = url
    return links


def linked_person(cell):
    a = cell.find('a', href=True)
    source = official(a['href']) if a else None
    params = {k.lower(): v[0] for k, v in parse_qs(urlsplit(source or '').query).items()}
    return {'name': text(cell), 'source': source, 'id': params.get('trainerid') or params.get('jockeyid')}


def parse_dividends(soup):
    payouts, kind = [], None
    for row in soup.select('.dividend_tab .position_left table tbody tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) == 3:
            kind = {'獨贏': 'WIN', '位置': 'PLA', '連贏': 'QIN'}.get(text(cells[0]))
        if kind and len(cells) in (2, 3):
            payouts.append({'type': kind, 'combination': text(cells[-2]), 'amount': number(text(cells[-1])),
                            'display': text(cells[-1]), 'unit': 10, 'currency': 'HKD'})
    return payouts


def parse_race(html, source, result=False, expected=None):
    soup = BeautifulSoup(html, 'html.parser')
    if result:
        info = soup.select_one('.race_tab')
        heading = text(info)
        date_text = next((str(t) for t in soup.find_all(string=True) if '賽事日期:' in str(t)), '')
        dm = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_text)
        if dm and '此場賽事宣佈取消' in text(soup):
            day = f'{dm[3]}-{dm[2]}-{dm[1]}'
            course = 'HV' if '跑馬地' in date_text else 'ST' if '沙田' in date_text else None
            params = {k.lower(): v[0] for k, v in parse_qs(urlsplit(source).query).items()}
            race_no = params.get('raceno', '')
            ident = f'{day}-{course}-{race_no}'
            if not course or not RACE_ID.fullmatch(ident) or expected and expected != ident:
                raise ValueError('取消场次与请求不符。')
            return {'id': ident, 'date': day, 'course': course, 'courseName': '沙田' if course == 'ST' else '跑马地',
                    'raceNo': int(race_no), 'name': '赛事取消', 'status': 'cancelled', 'cancellationOfficial': True,
                    'resultOfficial': False, 'entries': [], 'offTime': None, 'distance': None, 'track': '', 'class': '',
                    'dividends': [{'type': kind, 'combination': '—', 'amount': None, 'display': '退款', 'unit': 10, 'currency': 'HKD'} for kind in ['WIN', 'PLA', 'QIN']],
                    'source': source, 'updatedAt': now()}, race_links(soup, source)
        if not dm or info is None:
            raise ValueError('正式赛果尚未发布。')
        day = f'{dm[3]}-{dm[2]}-{dm[1]}'
        course = 'HV' if '跑馬地' in date_text else 'ST' if '沙田' in date_text else None
        rows = info.select('tbody tr')
        cells = [[text(c) for c in r.find_all('td', recursive=False)] for r in rows]
        name = cells[2][0] if len(cells) > 2 else ''
        going = cells[1][-1] if len(cells) > 1 else ''
        track = cells[2][-1] if len(cells) > 2 else ''
        class_name = cells[1][0].split(' - ')[0] if len(cells) > 1 else ''
        off = None
        table = soup.select_one('table.f_tac.table_bd.draggable')
    else:
        info = next((n for n in soup.select('div.f_fs13') if re.search(r'第\s*\d+\s*場\s*-', text(n)) and re.search(r'\d{4}年\d+月\d+日', text(n))), None)
        heading = text(info)
        dm = re.search(r'(\d{4})年(\d+)月(\d+)日.*?(\d{2}):(\d{2})', heading)
        if not dm:
            raise ValueError('排位表尚未发布。')
        day = f'{dm[1]}-{int(dm[2]):02}-{int(dm[3]):02}'
        off = datetime(int(dm[1]), int(dm[2]), int(dm[3]), int(dm[4]), int(dm[5]), tzinfo=HK).isoformat()
        course = 'HV' if '跑馬地' in heading else 'ST' if '沙田' in heading else None
        name = re.split(r'\d{4}年', re.sub(r'^第\s*\d+\s*場\s*-\s*', '', heading))[0].strip()
        parts = [p.strip() for p in info.stripped_strings] if info else []
        track = next((p for p in parts if '米' in p), '')
        going = track.rsplit(',', 1)[-1].strip()
        class_name = re.search(r'第[一二三四五六]班|新馬賽', heading)
        class_name = class_name[0] if class_name else ''
        table = soup.select_one('table.starter')
    rn, distance = re.search(r'第\s*(\d+)\s*場', heading), re.search(r'(\d{3,4})米', heading)
    if not rn or not course or table is None:
        raise ValueError('赛事来源结构不完整。')
    ident = f'{day}-{course}-{int(rn[1])}'
    if expected and ident != expected:
        raise ValueError('赛事日期、场地或场次与请求不符。')
    entries = []
    for tr in table.select('tr'):
        c = tr.find_all(['td', 'th'], recursive=False)
        horse = horse_identity(tr)
        if not horse or len(c) < (12 if result else 27):
            continue
        v = [text(x) for x in c]
        if result:
            entry = {**horse, 'number': v[1], 'position': v[0], 'place': placing(v[0]),
                     'jockey': linked_person(c[3]), 'trainer': linked_person(c[4]), 'weight': number(v[5]),
                     'bodyWeight': number(v[6]), 'draw': v[7], 'margin': v[8], 'running': v[9],
                     'finishTime': v[10], 'winOdds': number(v[11]), 'withdrawn': bool(re.search(r'退出|取消|WV|WX', v[0], re.I))}
        else:
            entry = {**horse, 'number': v[0], 'recent': v[1], 'weight': number(v[5]), 'draw': v[8],
                     'jockey': linked_person(c[6]), 'trainer': linked_person(c[9]), 'rating': number(v[11]),
                     'bodyWeight': number(v[13]), 'age': number(v[16]), 'sex': v[18], 'equipment': v[22],
                     'owner': v[23], 'sire': v[24], 'dam': v[25], 'importType': v[26],
                     'withdrawn': bool(re.search(r'退出|取消|Withdrawn', text(tr), re.I))}
        entries.append(entry)
    if not entries or len({e['id'] for e in entries}) != len(entries):
        raise ValueError('出赛马匹名单不完整或重复。')
    return {'id': ident, 'date': day, 'course': course, 'courseName': '沙田' if course == 'ST' else '跑马地',
            'raceNo': int(rn[1]), 'name': name, 'offTime': off, 'distance': int(distance[1]) if distance else None,
            'track': track, 'going': going, 'class': class_name, 'status': 'finished' if result else 'scheduled',
            'entries': entries, 'dividends': parse_dividends(soup) if result else [],
            'resultOfficial': result, 'source': race_url(ident, result), 'updatedAt': now()}, race_links(soup, source)


def suitability(records):
    groups = {k: defaultdict(list) for k in ['course', 'surface', 'distance', 'going']}
    for row in records:
        if row.get('withdrawn'):
            continue
        for key in groups:
            if row.get(key) is not None and row.get(key) != '':
                groups[key][str(row[key])].append(row)
    return {key: [{'label': label, 'starts': len(rows), 'wins': sum(r.get('place') == 1 for r in rows),
                   'top3': sum(r.get('place') is not None and 1 <= r['place'] <= 3 for r in rows),
                   'lowSample': len(rows) < 5} for label, rows in sorted(values.items())]
            for key, values in groups.items()}


def parse_horse(html, ident, complete=False):
    if not HORSE_ID.fullmatch(ident):
        raise LookupError('马匹编号不正确。')
    soup = BeautifulSoup(html, 'html.parser')
    title = text(soup.select_one('.title_text'))
    brand = ident.rsplit('_', 1)[-1]
    if not re.search(r'\(' + re.escape(brand) + r'\)', title):
        raise ValueError('马匹身份与请求不符。')
    profile = {}
    for table in soup.select('table.table_top_right'):
        for row in table.select('tr'):
            cells = row.find_all('td', recursive=False)
            if len(cells) == 3 and text(cells[0]) != '同父系馬':
                profile[text(cells[0]).replace('*', '')] = text(cells[2])
    photo = None
    for img in soup.select('img[src]'):
        candidate = official(img['src'])
        if candidate and re.search(r'/Horse_Images/[A-Z]/' + re.escape(brand) + r'_s\.jpg$', urlsplit(candidate).path, re.I):
            photo = {'url': candidate.replace('_s.jpg', '_l.jpg'), 'thumbnail': candidate, 'source': BASE + 'horse?horseid=' + ident}
            break
    trainer = next((linked_person(a.parent) for a in soup.select('a[href]') if 'trainerprofile?' in a['href'].lower()), None)
    records = []
    for row in soup.select('table.bigborder tr'):
        cells = row.find_all('td', recursive=False)
        if len(cells) != 19:
            continue
        v = [text(c) for c in cells]
        if not re.fullmatch(r'\d{2}/\d{2}/\d{2,4}', v[2]):
            continue
        date = datetime.strptime(v[2], '%d/%m/%y' if len(v[2]) == 8 else '%d/%m/%Y').date().isoformat()
        if date > datetime.now(HK).date().isoformat():
            continue
        anchor = cells[0].find('a', href=True)
        record_source = official(anchor['href']) if anchor else None
        query = {k.lower(): x[0] for k, x in parse_qs(urlsplit(record_source or '').query).items()}
        race_id = date + '-' + query.get('racecourse', '') + '-' + query.get('raceno', '')
        year = int(date[:4]) - (int(date[5:7]) < 8)
        records.append({'date': date, 'raceId': race_id if RACE_ID.fullmatch(race_id) else None,
                        'raceNo': query.get('raceno'), 'season': f'{year}/{str(year + 1)[2:]}',
                        'position': v[1], 'place': placing(v[1]),
                        'withdrawn': bool(re.search(r'退出|取消|WV|WX', v[1], re.I)),
                        'course': '跑马地' if '跑馬地' in v[3] else '沙田' if '沙田' in v[3] else v[3],
                        'surface': '草地' if '草地' in v[3] else '全天候跑道' if '全天候' in v[3] else v[3],
                        'track': v[3], 'distance': number(v[4]), 'going': v[5], 'class': v[6],
                        'draw': v[7], 'rating': number(v[8]), 'trainer': v[9], 'jockey': v[10], 'margin': v[11],
                        'winOdds': number(v[12]), 'weight': number(v[13]), 'running': v[14], 'finishTime': v[15],
                        'bodyWeight': number(v[16]), 'equipment': v[17], 'source': record_source})
    records.sort(key=lambda r: r['date'], reverse=True)
    return {'id': ident, 'brand': brand, 'name': re.sub(r'\s*\([^)]*\)\s*$', '', title),
            'profile': profile, 'pedigree': {'sire': profile.get('父系'), 'dam': profile.get('母系'), 'damsire': profile.get('外祖父')},
            'photo': photo, 'trainer': trainer, 'schemaVersion': 2 if complete else 1,
            'records': records, 'suitability': suitability(records),
            'coverage': '马会公开的历季香港往绩；生涯总战绩另列' if complete else '马会当前公开的近三季往绩；生涯总战绩另列',
            'source': BASE + 'horse?horseid=' + ident + ('&Option=1' if complete else ''), 'updatedAt': now()}


def horse_detail(ident):
    if not HORSE_ID.fullmatch(ident):
        raise LookupError('马匹编号不正确。')
    path = FOLDER / 'horses' / (ident + '.json')
    cached = load(path)
    if cached.get('schemaVersion') == 2 and age(cached.get('updatedAt')) < 86400:
        return cached
    if not read_control()['enabled']:
        return {**cached, 'id': ident, 'paused': True, 'message': '同步已暂停，显示最近保存的马匹资料。'}
    if time.monotonic() - ATTEMPTS.get(ident, -float('inf')) < 300:
        return {**cached, 'id': ident, 'message': '马会来源暂未更新，保留最近资料。'}
    if not LOCK.acquire(blocking=False):
        return {**cached, 'id': ident, 'pending': True}
    try:
        ATTEMPTS[ident] = time.monotonic()
        value = parse_horse(fetch_text(BASE + 'horse?horseid=' + ident + '&Option=1'), ident, complete=True)
        publish(path, value)
        return value
    except (OSError, ValueError):
        return {**cached, 'id': ident, 'message': '马匹档案暂时无法更新，稍后重试。'}
    finally:
        LOCK.release()


def get_race(ident):
    race_url(ident)
    value = load(FOLDER / 'races' / (ident + '.json'))
    if value.get('id') != ident:
        raise LookupError('本场尚未收录。')
    return value


def save_race(value):
    path = FOLDER / 'races' / (value['id'] + '.json')
    old = load(path)
    if old.get('status') in {'finished', 'cancelled'} and value['status'] not in {'finished', 'cancelled'}:
        return
    if value['status'] == 'finished' and old.get('offTime'):
        value['offTime'] = old['offTime']
    value = {**old, **value}
    publish(path, value)


def sync_catalogue():
    rows = {}
    for count in [0, 2, 3, 4]:
        soup = BeautifulSoup(fetch_text(BASE + 'selecthorsebychar?ordertype=' + str(count)), 'html.parser')
        for a in soup.select('a[href]'):
            item = horse_identity(a.parent)
            if item:
                rows[item['id']] = item
    if len(rows) < 1000:
        raise ValueError('马匹目录不完整，已保留原目录。')
    value = {'updatedAt': now(), 'horses': sorted(rows.values(), key=lambda r: r['brand']),
             'source': BASE + 'selecthorse', 'coverage': '马会按名称分类的现役马匹目录'}
    publish(FOLDER / 'catalogue.json', value)
    return len(rows)


def sync_meetings():
    failures, count = [], 0
    for result in [False, True]:
        source = BASE + ('localresults' if result else 'racecard')
        try:
            first, links = parse_race(fetch_text(source), source, result)
            save_race(first)
            count += 1
            prefix = first['id'].rsplit('-', 1)[0] + '-'
            for ident, url in sorted(links.items()):
                if not ident.startswith(prefix) or ident == first['id']:
                    continue
                prior = load(FOLDER / 'races' / (ident + '.json'))
                if result and (prior.get('cancellationOfficial') or prior.get('resultOfficial') and prior.get('dividends')) and age(prior.get('updatedAt')) < 86400:
                    continue
                try:
                    value, _ = parse_race(fetch_text(url), url, result, ident)
                    save_race(value)
                    count += 1
                except (OSError, ValueError) as error:
                    failures.append(ident + ': ' + str(error))
        except (OSError, ValueError) as error:
            failures.append(str(error))
    races = [load(p) for p in sorted((FOLDER / 'races').glob('*.json'))]
    races = [r for r in races if r.get('id')]
    if not races:
        raise ValueError('暂时未能获取香港赛事资料。')
    publish(FOLDER / 'meetings.json', {'updatedAt': now(), 'races': [{k: v for k, v in r.items() if k not in {'entries', 'pools'}} | {'runners': len(r['entries'])} for r in races],
                                      'failed': failures, 'source': BASE + 'fixture'})
    if failures:
        raise ValueError(f'已更新 {count} 场；{len(failures)} 项来源待重试')
    return count


def warm_profiles(limit=12):
    races = load(FOLDER / 'meetings.json').get('races', [])
    wanted = []
    for race in sorted(races, key=lambda r: (r['status'] == 'finished', r['date'], r['raceNo'])):
        if race['status'] != 'finished':
            wanted.extend(e['id'] for e in get_race(race['id'])['entries'])
    priority = set(wanted)
    wanted.extend(h['id'] for h in load(FOLDER / 'catalogue.json').get('horses', []))
    wanted = sorted(set(wanted), key=lambda ident: (ident not in priority, load(FOLDER / 'horses' / (ident + '.json')).get('updatedAt', '')))
    count = 0
    for ident in wanted:
        if count >= limit or not read_control()['enabled']:
            break
        cached = load(FOLDER / 'horses' / (ident + '.json'))
        if cached.get('schemaVersion') != 2 or age(cached.get('updatedAt')) > 86400:
            horse_detail(ident)
            count += 1
    from .horse_directory import build_directory
    build_directory()
    return count
