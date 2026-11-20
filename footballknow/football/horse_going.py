"""Observed going performance; wet all-weather and soft turf stay separate."""
import re

GROUPS = {'yielding': '草地黏地', 'soft': '草地软 / 烂地', 'wet': '全天候湿泥地', 'firm': '草地好 / 快地', 'dry': '全天候干地'}
SOURCE = 'https://www.hkjc.com/chinese/easyform/easyform_guide_chi.htm'
METHOD = '场地表现较好：该组至少 5 次出赛，胜率不低于 20% 或前三率不低于 50%；少于 5 次只列往绩，不评为擅长。前三率按完成前三名计算，不等同于位置派彩。'


def going_group(record):
    value = str(record.get('going') or '').strip().upper().translate(str.maketrans('粘软烂湿', '黏軟爛濕'))
    value = re.sub(r'[地\s]', '', value).replace('至', '/').replace('-', '/')
    surface = record.get('surface')
    if surface == '草地':
        if value in {'好/黏', '黏', 'G/Y', 'Y', 'GOOD/YIELDING', 'YIELDING'}:
            return 'yielding'
        if value in {'黏/軟', '軟', '爛', '大爛', 'Y/S', 'S', 'H', 'YIELDING/SOFT', 'SOFT', 'HEAVY'}:
            return 'soft'
        if value in {'好', '好/快', '快', 'G', 'G/F', 'F', 'GOOD', 'GOOD/FIRM', 'FIRM'}:
            return 'firm'
    if surface == '全天候跑道':
        if value in {'濕快', '濕慢', '濕', '受天雨影響', 'WF', 'WS', 'WE', 'RA', 'WET/FAST', 'WET/SLOW'}:
            return 'wet'
        if value in {'好', '快', '慢', '封', '例常灑水', 'GD', 'FT', 'SL', 'SE'}:
            return 'dry'
    return None


def going_performance(records):
    rows = {key: {'group': key, 'label': label, 'starts': 0, 'wins': 0, 'top3': 0, 'lastDate': None, 'records': []} for key, label in GROUPS.items()}
    seen = set()
    for record in sorted(records, key=lambda r: str(r.get('date') or ''), reverse=True):
        key = going_group(record)
        identity = record.get('raceId') or (record.get('date'), record.get('course'), record.get('raceNo'))
        if not key or record.get('withdrawn') or identity in seen or not record.get('date'):
            continue
        seen.add(identity)
        row = rows[key]
        place = record.get('place')
        row['starts'] += 1
        row['wins'] += int(place == 1)
        row['top3'] += int(isinstance(place, int) and 1 <= place <= 3)
        row['lastDate'] = row['lastDate'] or record['date']
        if len(row['records']) < 5:
            row['records'].append({k: record.get(k) for k in ('date', 'course', 'going', 'distance', 'place', 'source')})
    for row in rows.values():
        n = row['starts']
        row['winRate'] = row['wins'] / n if n else None
        row['top3Rate'] = row['top3'] / n if n else None
        row['lowSample'] = n < 5
        row['strong'] = n >= 5 and (row['winRate'] >= .2 or row['top3Rate'] >= .5)
    return list(rows.values())
