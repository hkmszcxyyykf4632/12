"""Cache-only pace scenarios, with a pre-off snapshot and separate actual results."""
import re
import threading
from datetime import datetime, timedelta, timezone

from .files import STATE, publish
from .motivation import digest, dt
from .racing import FOLDER, get_race, load
from .sync_control import read_control

LOCK = threading.Lock()
METHOD = 'pace-scenario-v1'
STYLES = ['放头', '跟前', '居中', '后追']


def positions(record):
    value = str(record.get('running') or '').strip()
    if not re.fullmatch(r'\d+(?:\s+\d+)+', value) or record.get('withdrawn'):
        return []
    points = [int(x) for x in value.split()]
    return points if all(0 < p <= 24 for p in points) else []


def style(position):
    return '放头' if position <= 1.8 else '跟前' if position <= 4 else '居中' if position <= 8 else '后追'


def runner_profile(entry, race, horse):
    history = sorted((r for r in horse.get('records', []) if r.get('date', '') < race['date']
                      and re.fullmatch(r'\d{4}-\d{2}-\d{2}', r.get('date', ''))), key=lambda r: r['date'], reverse=True)
    records, seen = [], set()
    for r in history:
        key = r.get('raceId') or (r['date'], r.get('raceNo'))
        p = positions(r)
        if key in seen or not p or r.get('place') != p[-1]:
            continue
        seen.add(key)
        records.append(r)
        if len(records) == 6:
            break
    evidence = []
    for i, r in enumerate(records):
        p = positions(r)
        surface = r.get('surface') or ''
        same_surface = bool(surface and surface in (race.get('track') or ''))
        similar = same_surface and r.get('course') == race.get('courseName') and isinstance(r.get('distance'), (int, float)) and abs(r['distance'] - (race.get('distance') or 0)) <= 400
        weight = (6 - i) * (2 if similar else 1)
        evidence.append({'date': r['date'], 'raceId': r.get('raceId'), 'course': r.get('course'),
                         'distance': r.get('distance'), 'running': r['running'], 'early': p[0],
                         'lateGain': p[-2] - p[-1], 'weight': weight, 'similar': similar, 'source': r.get('source')})
    total = sum(r['weight'] for r in evidence)
    early = sum(r['early'] * r['weight'] for r in evidence) / total if total else None
    gain = sum(r['lateGain'] * r['weight'] for r in evidence) / total if total else None
    known = len(evidence) >= 2
    draw = int(entry['draw']) if str(entry.get('draw', '')).isdigit() else None
    return {'id': entry['id'], 'name': entry['name'], 'number': entry['number'], 'draw': draw,
            'style': style(early) if known else '资料不足', 'earlyPosition': round(early, 2) if known else None,
            'lateGain': round(gain, 2) if known else None, 'samples': len(evidence),
            'confidence': '较完整' if len(evidence) >= 5 else '样本较少' if known else '暂不推演跑位',
            'evidence': evidence, 'source': horse.get('source') or entry.get('source'),
            'profileUpdatedAt': horse.get('updatedAt')}


def build(race, at):
    runners = [runner_profile(e, race, load(FOLDER / 'horses' / (e['id'] + '.json')))
               for e in race['entries'] if not e.get('withdrawn')]
    known = [r for r in runners if r['earlyPosition'] is not None]
    leaders = [r for r in known if r['style'] == '放头']
    forward = [r for r in known if r['style'] in {'放头', '跟前'}]
    enough = len(known) >= max(2, (len(runners) + 1) // 2)
    pace = ('fast' if len(leaders) >= 2 or len(forward) >= max(4, len(runners) // 2)
            else 'slow' if len(forward) <= 2 else 'normal') if enough else 'unknown'
    return {'version': METHOD, 'raceId': race['id'], 'offTime': race.get('offTime'), 'date': race['date'],
            'generatedAt': at.isoformat(), 'runners': runners, 'expectedPace': pace,
            'coverage': {'known': len(known), 'total': len(runners)},
            'summary': f'{len(leaders)} 匹近期常见放头，{len(forward)} 匹偏向前置；已收录走位足以分析 {len(known)}/{len(runners)} 匹。',
            'method': '取本场之前最近六次有效沿途走位，近期权重6至1，同场、同跑道类型且途程差不超过400米权重加倍；按首个记录点推演早段位置，末段追前位数描述后劲。至少两次记录才归类。',
            'limits': '首个记录点不一定是400米；图中距离和速度仅作跑法示意。没有分段基准时不计算真实速度、完成时间或胜率。'}


def verified(saved, race):
    return bool(saved and dt(saved.get('offTime')) and saved.get('version') == METHOD and saved.get('raceId') == race['id']
                and dt(saved.get('offTime')) == dt(race.get('offTime')) and dt(saved.get('generatedAt'))
                and dt(saved['generatedAt']) < dt(saved['offTime'])
                and saved.get('hash') == digest({k: v for k, v in saved.items() if k != 'hash'}))


def review(snapshot, race, saved_before):
    rows = []
    for r in snapshot['runners']:
        actual = next((e for e in race['entries'] if e['id'] == r['id']), {})
        p = positions(actual)
        actual_style = style(p[0]) if p else None
        checked = saved_before and actual_style is not None and r['earlyPosition'] is not None and not actual.get('withdrawn')
        rows.append({'id': r['id'], 'predicted': r['style'], 'actual': actual_style,
                     'running': actual.get('running'), 'place': actual.get('place'), 'withdrawn': bool(actual.get('withdrawn')),
                     'matched': r['style'] == actual_style if checked else None})
    checked = [r for r in rows if r['matched'] is not None]
    return {'available': race.get('resultOfficial') is True and race.get('status') == 'finished',
            'hasPregame': saved_before, 'checked': len(checked), 'matched': sum(r['matched'] for r in checked), 'runners': rows}


def simulation(ident):
    race = get_race(ident)
    if race.get('status') == 'cancelled':
        return {'raceId': ident, 'status': 'cancelled', 'message': '本场取消，不运行模拟。'}
    at = datetime.now(timezone.utc)
    before = bool(dt(race.get('offTime')) and at < dt(race['offTime']) and race.get('status') == 'scheduled')
    path = STATE / 'racing-pace' / (ident + '.json')
    with LOCK:
        saved = load(path)
        valid = verified(saved, race)
        roster = {(e['id'], str(e.get('draw'))) for e in race['entries'] if not e.get('withdrawn')}
        old_roster = {(e['id'], str(e.get('draw'))) for e in saved.get('runners', [])}
        fresh = valid and at - dt(saved['generatedAt']) < timedelta(minutes=5) and roster == old_roster
        if before and read_control()['enabled'] and not fresh:
            saved = build(race, at)
            saved['hash'] = digest(saved)
            publish(path, saved)
            valid = True
        snapshot = saved if valid else build(race, at)
    return {**snapshot, 'status': 'pregame' if before else 'saved' if valid else 'retrospective',
            'hasPregame': valid, 'paused': not read_control()['enabled'],
            'withdrawnIds': [e['id'] for e in race['entries'] if e.get('withdrawn')],
            'review': review(snapshot, race, valid)}
