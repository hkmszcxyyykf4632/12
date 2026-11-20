"""Dated workout observations and class-boundary facts, never inferred intent."""
import math
import re
import threading
from datetime import date, datetime, timedelta, timezone

from .files import STATE, publish
from .motivation import digest, dt
from .racing import FOLDER, HK, get_race, load
from .sync_control import read_control

METHOD = 'workout-preparation-v1'
LOCK = threading.Lock()
POLICY = 'https://www.hkjc.com/chinese/racinginfo/handicap_policy.asp'


def numeric(value):
    try:
        result = float(value)
        return result if not isinstance(value, bool) and math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def race_class(value):
    value = str(value or '').strip()
    if value in {'1', '2', '3', '4', '5'}:
        return int(value)
    match = re.fullmatch(r'第([一二三四五1-5])班', value)
    return ('一二三四五'.index(match[1]) + 1 if match[1] in '一二三四五' else int(match[1])) if match else None


def category(value):
    value = str(value or '')
    if value in {'出賽', '出赛'}:
        return 'race'
    if value in {'試閘', '试闸'}:
        return 'trial'
    if value == '快操':
        return 'fast'
    if re.search(r'游水|游泳|跑步機|跑步机|水中', value):
        return 'recovery'
    if re.search(r'踱步|慢操|慢跑', value):
        return 'easy'
    return 'other'


def runner(entry, horse, research, at, race=None):
    # Same-day records have no reliable publication time in the source table.
    end = at.astimezone(HK).date() - timedelta(days=1)
    if race and day(race.get('date')):
        end = min(end, day(race['date']) - timedelta(days=1))
    history_end = end
    workouts = research.get('workouts') or {}
    identity_ok = workouts.get('horseId', entry['id']) == entry['id']
    fetched = dt(workouts.get('fetchedAt'))
    if identity_ok and fetched and fetched <= at:
        end = min(end, fetched.astimezone(HK).date() - timedelta(days=1))
    start, week = end - timedelta(days=20), end - timedelta(days=6)
    raw = workouts.get('records', []) if identity_ok else []
    rows, seen = [], set()
    for r in raw:
        observed = day(r.get('date'))
        key = tuple(str(r.get(k) or '') for k in ['date', 'type', 'track', 'details', 'equipment'])
        kind = category(r.get('type'))
        if not observed or not start <= observed <= end or key in seen or kind == 'race':
            continue
        seen.add(key)
        rows.append({**{k: r.get(k) for k in ['date', 'type', 'track', 'details', 'distance', 'publishedTime', 'rider']}, 'category': kind})
    rows.sort(key=lambda r: r['date'], reverse=True)
    recent = [r for r in rows if day(r['date']) >= week]
    prior = [r for r in rows if day(r['date']) < week]
    counts = lambda records: {kind: sum(r['category'] == kind for r in records) for kind in ['fast', 'trial', 'easy', 'recovery', 'other']}
    latest_counts, baseline = counts(recent), counts(prior)
    days7, days14 = len({r['date'] for r in recent}), len({r['date'] for r in prior})
    quality7 = latest_counts['fast'] + latest_counts['trial']
    quality14 = baseline['fast'] + baseline['trial']
    fresh = bool(fetched and timedelta(0) <= at - fetched <= timedelta(hours=48))
    covered = any(day(r.get('date')) and day(r['date']) <= start for r in raw)
    known = bool(identity_ok and fresh and covered and rows and not latest_counts['other'] and not baseline['other'])
    records = sorted((r for r in horse.get('records', []) if day(r.get('date')) and day(r['date']) <= history_end
                      and not r.get('withdrawn')), key=lambda r: r['date'], reverse=True)
    history, starts_seen = [], set()
    for r in records:
        key = r.get('raceId') or (r['date'], r.get('raceNo'))
        if key not in starts_seen:
            history.append(r)
            starts_seen.add(key)
    rest = (history_end - day(history[0]['date'])).days + 1 if history else None
    label, tone = '资料不足', 'muted'
    if known:
        if days7 >= 4 and quality7 >= 1 and quality7 >= quality14 / 2 + 1:
            label, tone = '近期加紧备战', 'positive'
        elif days7 >= 5 and quality7 >= 2:
            label, tone = '备战较积极', 'positive'
        elif days14 >= 6 and days7 <= days14 / 4 and quality7 == 0:
            label, tone = ('赛后调整期', 'muted') if rest is not None and rest <= 7 else ('近期操练减少', 'attention')
        else:
            label = '维持常规操练'
    evidence = [f'最近7天已收录{days7}个操练日：快操{latest_counts["fast"]}次、试闸{latest_counts["trial"]}次、舒缓操练{latest_counts["easy"]}次、恢复类{latest_counts["recovery"]}次。',
                f'此前14天已收录{days14}个操练日，快操及试闸合计{quality14}次，折合每周{quality14 / 2:g}次；最近7天为{quality7}次。']
    alternatives = []
    if not fresh:
        alternatives.append('晨操资料尚未更新至最近48小时，不把缺记录当作少操练。')
    if not covered:
        alternatives.append('已收录记录不足以覆盖完整21天，暂不判断训练增减。')
    if latest_counts['other'] or baseline['other']:
        alternatives.append('部分操练类别尚未归类，暂不比较训练强度。')
    if rest is not None:
        alternatives.append(f'截至{history_end.isoformat()}次日，距上次出赛约{rest}天。' + ('刚赛后减少快操可属于恢复安排。' if rest <= 7 else '休赛较长，试闸也可能用于恢复适赛状态。' if rest >= 60 else ''))
    if latest_counts['recovery']:
        alternatives.append('游泳、跑步机等单独统计，不能据此推断伤病。')
    rating = numeric(entry.get('rating'))
    current_class = race_class((race or {}).get('class'))
    rating_source = (race or {}).get('source')
    if race is None:
        rating = numeric((horse.get('profile') or {}).get('現時評分'))
        current_class = race_class(history[0].get('class')) if history else None
        rating_source = horse.get('source')
    timeline = [{k: r.get(k) for k in ['date', 'rating', 'class', 'place', 'source']} for r in history[:3] if numeric(r.get('rating')) is not None]
    delta = rating - numeric(timeline[-1]['rating']) if rating is not None and timeline else None
    threshold = {1: 100, 2: 80, 3: 60, 4: 40}.get(current_class)
    gap = rating - threshold if rating is not None and threshold is not None else None
    boundary_label = ('已在第五班' if current_class == 5 else '班次或评分待核对' if gap is None else
                      '已达低一班评分范围' if gap <= 0 else '接近低一班上限' if gap <= 3 else '距低一班仍有差距')
    watch = bool(gap is not None and 0 < gap <= 3 and delta is not None and delta < 0)
    conclusion = ('已是第五班，标准班次中没有更低一班。' if current_class == 5 else
                  '评分或班次记录不足，暂不判断降班趋势。' if gap is None or delta is None else
                  '评分下调且接近下一班上限，列入降班观察。' if watch else
                  '目前已达到低一班标准评分范围，可留意下一次实际编班。' if gap is not None and gap <= 0 else
                  '未同时出现评分下调和接近下一班上限的信号。')
    if watch and label == '近期操练减少':
        conclusion += '同时出现操练减少，需结合休整、伤患公告及后续出赛安排核对。'
    return {'id': entry['id'], 'name': entry.get('name') or horse.get('name'), 'number': entry.get('number'),
            'activity': label, 'tone': tone, 'known': known, 'window': {'from': start.isoformat(), 'to': end.isoformat()},
            'days7': days7, 'days14': days14, 'counts7': latest_counts, 'counts14': baseline,
            'evidence': evidence, 'alternatives': alternatives, 'workouts': rows[:60],
            'source': workouts.get('source') if identity_ok else None, 'fetchedAt': workouts.get('fetchedAt'),
            'classWatch': {'label': boundary_label, 'watch': watch, 'rating': rating, 'class': current_class,
                           'basis': '本场班次' if race else '最近一次出赛班次', 'nextClass': current_class + 1 if threshold else None,
                           'threshold': threshold, 'gap': gap, 'change': delta, 'history': timeline,
                           'source': rating_source, 'policy': POLICY, 'summary': conclusion,
                           'intent': '公开晨操与评分不能确认是否有意减分，后续只核对实际评分及编班变化。'}}


def review(snapshot, race, valid):
    rows = []
    for r in snapshot.get('runners', []):
        actual = next((e for e in race['entries'] if e['id'] == r['id']), None)
        horse = load(FOLDER / 'horses' / (r['id'] + '.json'))
        later = sorted((x for x in horse.get('records', []) if day(x.get('date')) and x['date'] > race['date']
                        and not x.get('withdrawn')), key=lambda x: x['date'])
        following = later[0] if later else {}
        old = r['classWatch']
        new_rating, new_class = numeric(following.get('rating')), race_class(following.get('class'))
        rows.append({'id': r['id'], 'name': r['name'], 'activity': r['activity'], 'watch': old['watch'],
                     'place': (actual or {}).get('place'), 'void': actual is None or bool(actual.get('withdrawn')),
                     'followingDate': following.get('date'), 'rating': new_rating, 'class': new_class,
                     'ratingChange': new_rating - old['rating'] if new_rating is not None and old['rating'] is not None else None,
                     'downClass': new_class > old['class'] if new_class and old['class'] else None,
                     'source': following.get('source')})
    return {'available': race.get('status') == 'finished' and race.get('resultOfficial') is True,
            'hasPregame': valid, 'runners': rows}


def assessment(ident, refresh=False):
    race = get_race(ident)
    at = datetime.now(timezone.utc)
    before = bool(race.get('status') == 'scheduled' and dt(race.get('offTime')) and at < dt(race['offTime']))
    if race.get('status') == 'cancelled':
        return {'raceId': ident, 'status': 'cancelled', 'runners': [], 'message': '赛事取消，不生成备战判断。'}
    paused = not read_control()['enabled']
    pending = False
    if refresh and before and not paused:
        from .horse_research import get_research
        for e in race['entries']:
            if not e.get('withdrawn') and (FOLDER / 'horses' / (e['id'] + '.json')).is_file():
                pending |= bool(get_research(e['id']).get('pending'))
    path = STATE / 'racing-preparation' / (ident + '.json')
    with LOCK:
        saved = load(path)
        valid = bool(saved and saved.get('version') == METHOD and saved.get('raceId') == ident and dt(saved.get('offTime'))
                     and dt(saved.get('offTime')) == dt(race.get('offTime')) and dt(saved.get('generatedAt'))
                     and dt(saved['generatedAt']) < dt(saved['offTime'])
                     and saved.get('hash') == digest({k: v for k, v in saved.items() if k != 'hash'}))
        if before or not valid:
            snapshot = {'version': METHOD, 'raceId': ident, 'date': race['date'], 'offTime': race.get('offTime'),
                        'generatedAt': at.isoformat(), 'runners': [runner(e, load(FOLDER / 'horses' / (e['id'] + '.json')),
                        load(FOLDER / 'research' / (e['id'] + '.json')), at, race) for e in race['entries'] if not e.get('withdrawn')]}
            if before and not paused:
                snapshot['hash'] = digest(snapshot)
                publish(path, snapshot)
                valid = True
        else:
            snapshot = saved
    return {**snapshot, 'status': 'pregame' if before else 'saved' if valid else 'retrospective',
            'hasPregame': valid, 'paused': paused, 'pending': pending,
            'withdrawnIds': [e['id'] for e in race['entries'] if e.get('withdrawn')],
            'review': review(snapshot, race, valid)}
