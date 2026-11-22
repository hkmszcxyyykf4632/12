"""Small public meeting snapshots: runners, live placings and WIN / PLA / QIN pools."""
import re

from .files import publish
from .hkjc_public import query
from .racing import BASE, FOLDER, HORSE_ID, load, now, number, race_url

TYPES = {'WIN', 'PLA', 'QIN', 'QPL'}


def combination(value):
    bits = str(value).split(',')
    if not bits or any(not re.fullmatch(r'\d{1,2}', bit) for bit in bits):
        return None
    return ','.join(str(n) for n in sorted(int(bit) for bit in bits))


def merge_pool(old, pool, checked):
    quotes = []
    previous = {n['combination']: n for n in old.get('quotes', [])}
    for node in pool.get('oddsNodes', []):
        comb = combination(node.get('combString'))
        if not comb:
            continue
        quote = str(node.get('oddsValue') or '')
        prior = previous.get(comb, {})
        numeric = number(quote)
        first = prior.get('first')
        if first is None and numeric is not None and numeric > 0:
            first = quote
        quotes.append({'combination': comb, 'value': quote, 'first': first,
                       'firstAt': prior.get('firstAt') or (checked if first else None),
                       'previous': prior.get('value') if prior.get('value') != quote else prior.get('previous'),
                       'favourite': bool(node.get('hotFavourite'))})
    return {'type': pool['oddsType'], 'status': pool.get('status'), 'sellStatus': pool.get('sellStatus'),
            'sourceUpdatedAt': pool.get('oddsLastUpdateTime') if quotes else old.get('sourceUpdatedAt'), 'checkedAt': checked,
            'quotes': quotes or old.get('quotes', []), 'quoteRetained': not bool(quotes) and bool(old.get('quotes'))}


def normalize_race(meeting, raw, old):
    day, course = meeting['date'], meeting['venueCode']
    if course not in {'ST', 'HV'} or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('不是香港本地赛马日。')
    ident = f"{day}-{course}-{int(raw['no'])}"
    if old and old.get('id') != ident:
        raise ValueError('赛果与排位身份不符。')
    entries = []
    old_entries = {h['id']: h for h in old.get('entries', [])}
    for runner in raw.get('runners', []):
        horse = runner.get('horse') or {}
        horse_id = horse.get('id', '')
        if not HORSE_ID.fullmatch(horse_id) or not str(runner.get('no') or '').isdigit():
            continue
        status = str(runner.get('status', '')).upper()
        if status in {'RESERVED', 'STANDBY', 'SCRATCHEDRESERVED'}:
            continue
        existing = old_entries.get(horse_id, {})
        result = number(runner.get('finalPosition'))
        result = int(result) if result is not None and result > 0 else existing.get('place')
        entry = {**existing, 'id': horse_id, 'brand': horse.get('code'), 'name': runner.get('name_ch'),
                 'number': str(runner['no']), 'draw': runner.get('barrierDrawNumber'),
                 'rating': number(runner.get('currentRating')), 'weight': number(runner.get('handicapWeight')),
                 'bodyWeight': number(runner.get('currentWeight')), 'equipment': runner.get('gearInfo'),
                 'recent': runner.get('last6run'), 'withdrawn': 'SCRATCH' in status,
                 'place': result, 'position': (str(result) + (' DH' if runner.get('deadHeat') else '')) if result else existing.get('position', ''),
                 'winOdds': number(runner.get('winOdds')) or existing.get('winOdds')}
        for kind in ['jockey', 'trainer']:
            person = runner.get(kind) or {}
            entry[kind] = {'id': person.get('code'), 'name': person.get('name_ch'),
                           'source': BASE + kind + 'profile?' + kind + 'id=' + (person.get('code') or '')}
        entries.append(entry)
    if not entries or len({h['id'] for h in entries}) != len(entries):
        raise ValueError('即时出赛名单不完整。')
    source_status = str(raw.get('status', '')).upper()
    has_winner = any(h.get('place') == 1 for h in entries)
    official = bool(old.get('resultOfficial'))
    status = 'finished' if official else 'provisional' if has_winner else 'cancelled' if 'ABANDON' in source_status or 'CANCEL' in source_status else 'scheduled'
    return {**old, 'id': ident, 'date': day, 'course': course, 'courseName': '沙田' if course == 'ST' else '跑马地',
            'raceNo': int(raw['no']), 'name': raw.get('raceName_ch'), 'offTime': raw.get('postTime'),
            'distance': raw.get('distance'), 'class': raw.get('raceClass_ch'), 'going': raw.get('go_ch'),
            'track': ' '.join(filter(None, [(raw.get('raceTrack') or {}).get('description_ch'), (raw.get('raceCourse') or {}).get('description_ch')])),
            'status': status, 'sourceStatus': source_status, 'resultOfficial': official,
            'entries': entries, 'source': race_url(ident, official), 'liveCheckedAt': now(), 'updatedAt': now()}


def sync_live_racing():
    payload = query('meetings', {})
    count = 0
    for meeting in payload.get('raceMeetings', []):
        if meeting.get('venueCode') not in {'ST', 'HV'}:
            continue
        day, venue = meeting['date'], meeting['venueCode']
        variables = {'date': day, 'venueCode': venue, 'oddsTypes': sorted(TYPES), 'raceNo': 0}
        pools = query('pools', variables).get('raceMeetings', [])
        all_pools = [p for m in pools for p in m.get('pmPools', [])]
        meeting_prefix = meeting['id']
        if any(not p.get('id', '').startswith(meeting_prefix) for p in all_pools):
            raise ValueError('赔率返回的赛马日与排位不符。')
        payouts = query('results', {'date': day, 'venueCode': venue, 'foOddsTypes': [],
                        'foFilter': None, 'resultOddsType': sorted(TYPES)}).get('raceMeetings', [])
        if any(m.get('id') != meeting_prefix for m in payouts):
            raise ValueError('派彩返回的赛马日不符。')
        for raw in meeting.get('races', []):
            path = FOLDER / 'races' / f"{day}-{venue}-{raw['no']}.json"
            old = load(path)
            race = normalize_race(meeting, raw, old)
            previous = {p['type']: p for p in old.get('pools', [])}
            current = {p['oddsType']: merge_pool(previous.get(p['oddsType'], {}), p, now()) for p in all_pools
                       if p['oddsType'] in TYPES and p.get('leg', {}).get('races') == [raw['no']]}
            race['pools'] = [current.get(kind) or {**previous[kind], 'quoteRetained': True}
                             for kind in ['WIN', 'PLA', 'QIN', 'QPL'] if kind in current or kind in previous]
            divs = [{'type': p['oddsType'], 'combination': combination(d['winComb']) or d['winComb'],
                     'amount': number(d['div']), 'display': str(d['div']), 'unit': 10, 'currency': 'HKD'}
                    for m in payouts for p in m.get('resPools', []) if p.get('leg', {}).get('races') == [raw['no']]
                    for d in p.get('dividends', [])]
            if divs:
                race.update(dividends=divs, resultOfficial=True)
                if any(h.get('place') == 1 for h in race['entries']):
                    race['status'] = 'finished'
            publish(path, race)
            count += 1
    races = [load(path) for path in (FOLDER / 'races').glob('*.json')]
    prior = load(FOLDER / 'meetings.json')
    publish(FOLDER / 'meetings.json', {**prior, 'liveCheckedAt': now(), 'races': [
        {k: v for k, v in r.items() if k not in {'entries', 'pools'}} | {'runners': len(r['entries'])}
        for r in sorted(races, key=lambda r: r.get('id', '')) if r.get('entries') or r.get('status') == 'cancelled']})
    return count
