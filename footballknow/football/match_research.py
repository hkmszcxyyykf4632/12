"""Identity-checked lineups, previous opponents and pre-kickoff research snapshots."""
import json
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .files import PUBLIC, STATE, fetch_text, publish
from .motivation import dt, digest
from .match_weather import forecast
from .sync_control import read_control
from .leagues import LEAGUES, league_path

BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer/all'
LOCK = threading.Lock()


def load(path):
    try:
        return json.loads(path.read_text('utf-8'))
    except (OSError, ValueError):
        return {}


def cached_json(url, path, seconds, at):
    old = load(path)
    if dt(old.get('updatedAt')) and timedelta(0) <= at - dt(old['updatedAt']) < timedelta(seconds=seconds):
        return old.get('raw', {})
    try:
        raw = json.loads(fetch_text(url))
    except (OSError, ValueError):
        if isinstance(old.get('raw'), dict) and old['raw']:
            return {**old['raw'], '_cachedSourceAt': old.get('updatedAt')}
        raise
    publish(path, {'updatedAt': at.isoformat(), 'raw': raw})
    return raw


def game_of(raw, ident, expected=None):
    if str(raw.get('header', {}).get('id')) != str(ident):
        raise ValueError('Summary event mismatch')
    game = raw['header']['competitions'][0]
    sides = {c['homeAway']: str(c['team']['id']) for c in game['competitors']}
    if set(sides) != {'home', 'away'} or len(set(sides.values())) != 2 or not dt(game.get('date')):
        raise ValueError('Summary teams missing')
    if expected and (any(sides[s] != expected['teams'][s]['id'] for s in sides) or dt(game['date']) != dt(expected['kickoff'])):
        raise ValueError('Summary opponent or kickoff mismatch')
    return game


def name_key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)).lower() if c.isalnum() and not unicodedata.combining(c))


def club_translations(league, team_name):
    if league not in LEAGUES:
        return {}
    folder = league_path(PUBLIC, league)
    catalogue, translated = load(folder / 'data.json'), load(folder / 'names.json').get('names', {})
    team_ids = {t['id'] for t in catalogue.get('teams', []) if t['name'] == team_name}
    choices = {}
    for player in catalogue.get('players', []):
        if player.get('team') not in team_ids:
            continue
        entry = translated.get(str(player.get('code')))
        if not entry:
            continue
        value = {k: entry.get(k) for k in ['mandarin', 'cantonese', 'mandarinSource', 'cantoneseSource']}
        for name in [entry.get('english'), (player.get('first_name', '') + ' ' + player.get('second_name', '')).strip()]:
            if name:
                choices.setdefault(name_key(name), []).append(value)
    return {k: rows[0] for k, rows in choices.items() if all(r == rows[0] for r in rows)}


def lineup(raw, team_id, translations=None):
    rows = [r for r in raw.get('rosters', []) if str(r.get('team', {}).get('id')) == team_id]
    if len(rows) != 1:
        return {'confirmed': False, 'players': [], 'formation': ''}
    row = rows[0]
    players = [{'id': str(p['athlete']['id']), 'name': p['athlete'].get('displayName', ''),
                'position': (p.get('position') or {}).get('abbreviation', ''), 'shirt': p.get('jersey', '')}
               for p in row.get('roster', []) if p.get('starter') is True and p.get('athlete', {}).get('id')]
    for player in players:
        player.update((translations or {}).get(name_key(player['name']), {}))
    confirmed = len(players) == len({p['id'] for p in players}) == 11
    return {'confirmed': confirmed, 'players': players if confirmed else [], 'formation': row.get('formation', '')}


def lineup_diff(current, previous):
    if not current.get('confirmed') or not previous.get('confirmed'):
        return {'status': '名单尚未完整确认'}
    old, new = ({p['id']: p for p in r['players']} for r in (previous, current))
    return {'status': 'available', 'retained': len(old.keys() & new.keys()),
            'in': [p for k, p in new.items() if k not in old], 'out': [p for k, p in old.items() if k not in new],
            'previousFormation': previous['formation'], 'formation': current['formation']}


def schedule(team_id, season, at):
    raw = cached_json(f'{BASE}/teams/{team_id}/schedule?season={season}',
                      STATE / 'team-schedules' / f'{team_id}-{season}.json', 21600, at)
    if str(raw.get('team', {}).get('id')) != team_id or not isinstance(raw.get('events'), list):
        raise ValueError('Schedule team mismatch')
    return raw['events']


def history_rows(events, team_id, before):
    result = {}
    for event in events:
        try:
            game = event['competitions'][0]
            date = dt(game.get('date') or event.get('date'))
            if not date or date >= before or not game.get('status', {}).get('type', {}).get('completed'):
                continue
            sides = {s['homeAway']: s for s in game['competitors']}
            side = next(s for s, c in sides.items() if str(c['team']['id']) == team_id)
            other = 'away' if side == 'home' else 'home'
            def score(c):
                raw = c.get('score')
                return float(raw.get('value')) if isinstance(raw, dict) else float(raw)
            own, against = score(sides[side]), score(sides[other])
            if not all(v.is_integer() and 0 <= v <= 99 for v in [own, against]):
                continue
            ident = str(event['id'])
            if not re.fullmatch(r'\d{1,16}', ident):
                continue
            result[ident] = {'id': ident, 'date': date.isoformat(), 'homeAway': side,
                'opponentId': str(sides[other]['team']['id']), 'opponent': sides[other]['team'].get('displayName', ''),
                'goalsFor': int(own), 'goalsAgainst': int(against), 'result': 'W' if own > against else 'L' if own < against else 'D',
                'competition': (event.get('seasonType') or {}).get('name', ''),
                'scope': '来源完场比分（杯赛可能含加时；不含点球大战比分）',
                'source': 'https://www.espn.com/soccer/match/_/gameId/' + ident}
        except (ValueError, TypeError, KeyError, StopIteration, IndexError):
            continue
    return sorted(result.values(), key=lambda row: row['date'], reverse=True)


def streak(rows):
    if not rows:
        return {'matches': [], 'summary': '近期赛果暂未收录'}
    recent = rows[:10]
    count, outcome = 0, rows[0]['result']
    for row in rows:
        if row['result'] != outcome:
            break
        count += 1
    text = {'W': '胜', 'L': '负', 'D': '平'}[outcome]
    return {'matches': recent, 'run': count, 'outcome': outcome, 'bounded': count == len(rows),
        'summary': f'已收录比赛中连续{count}{text}；近{len(recent)}场{sum(r["result"] == "W" for r in recent)}胜、{sum(r["result"] == "D" for r in recent)}平、{sum(r["result"] == "L" for r in recent)}负，进{sum(r["goalsFor"] for r in recent)}球、失{sum(r["goalsAgainst"] for r in recent)}球。',
        'interpretation': '连胜需结合对手与主客场，不能直接外推下一场；连败需区分失球增多、赛程强度与伤停。下表逐场列出样本，未覆盖的赛事不计入。'}


def prior_lineup(reference, team_id, at, translations=None):
    if not reference:
        return {'status': '未收录此前比赛'}
    try:
        if not reference.get('id'):
            from .match_details import resolve_event
            event_id = resolve_event(reference['catalogueMatch'], reference['catalogueLeague'])
            if not event_id:
                return {'status': '此前比赛阵容暂未取得', 'match': reference}
            reference = {**reference, 'id': event_id}
        raw = cached_json(f'{BASE}/summary?event={reference["id"]}', STATE / 'match-summaries' / (reference['id'] + '.json'), 604800, at)
        game = game_of(raw, reference['id'])
        ids = {str(c['team']['id']) for c in game['competitors']}
        same_time = (dt(game['date']).date() == dt(reference['date']).date()) if reference.get('dateOnly') else dt(game['date']) == dt(reference['date'])
        if ids != {team_id, reference['opponentId']} or not same_time:
            raise ValueError('Previous match identity mismatch')
        return {'status': 'available', 'match': reference, 'lineup': lineup(raw, team_id, translations)}
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return {'status': '此前比赛阵容暂未取得', 'match': reference}


def build(row, at):
    raw = cached_json(f'{BASE}/summary?event={row["id"]}', STATE / 'match-summaries' / (row['id'] + '.json'), 60 if row['started'] else 180, at)
    game = game_of(raw, row['id'], row)
    before = dt(row['kickoff'])
    teams = {}
    def side_research(side):
        own, opponent = row['teams'][side], row['teams']['away' if side == 'home' else 'home']
        translations = club_translations(row.get('league'), own['name'])
        current = lineup(raw, own['id'], translations)
        errors, events = [], []
        for season in [int(row.get('season') or before.year), int(row.get('season') or before.year) - 1]:
            try:
                events.extend(schedule(own['id'], season, at))
            except (OSError, ValueError, KeyError, TypeError):
                errors.append(f'{season}赛程读取失败')
            rows = history_rows(events, own['id'], before)
            if len(rows) >= 10 and any(r['opponentId'] == opponent['id'] for r in rows):
                break
        if errors:
            from .local_match_history import local_history
            local_rows = local_history(own['id'], before, load)
            merged = {(r['date'][:10], r['homeAway'], r['opponentId']): r for r in local_rows}
            merged.update({(r['date'][:10], r['homeAway'], r['opponentId']): r for r in rows})
            rows = sorted(merged.values(), key=lambda r: r['date'], reverse=True)
            if local_rows:
                errors.append('已补入本站收录的完场往绩，各场保留原始来源')
        prior = rows[0] if rows else None
        h2h = next((r for r in rows if r['opponentId'] == opponent['id']), None)
        comparisons = {}
        for key, reference in [('previous', prior), ('headToHead', h2h)]:
            previous = prior_lineup(reference, own['id'], at, translations)
            comparisons[key] = {**previous, 'difference': lineup_diff(current, previous.get('lineup', {}))}
        return side, {'name': own['label'], 'teamId': own['id'], 'lineup': current,
                      'comparisons': comparisons, 'form': streak(rows), 'errors': errors}
    with ThreadPoolExecutor(max_workers=2) as pool:
        teams.update(pool.map(side_research, ['home', 'away']))
    pre_path = STATE / 'daily-research-before' / (row['id'] + '.json')
    pre = load(pre_path)
    if pre and (pre.get('eventId') != row['id'] or pre.get('kickoff') != row['kickoff'] or
                pre.get('hash') != digest({k: v for k, v in pre.items() if k != 'hash'}) or not dt(pre.get('capturedAt')) or dt(pre['capturedAt']) >= before):
        pre = {}
    if not row['started'] and at < before and game.get('status', {}).get('type', {}).get('state') == 'pre' and not raw.get('_cachedSourceAt'):
        weather = forecast(raw.get('gameInfo', {}).get('venue') or row.get('venue', {}), before, at)
        pre = {'eventId': row['id'], 'kickoff': row['kickoff'], 'capturedAt': at.isoformat(), 'teams': teams, 'weather': weather}
        pre['hash'] = digest(pre)
        publish(pre_path, pre)
    else:
        weather = pre.get('weather') or {'status': '没有留存赛前天气预报'}
    return {'eventId': row['id'], 'kickoff': row['kickoff'], 'updatedAt': at.isoformat(), 'teams': teams, 'weather': weather,
            'message': f'本场来源暂未更新，阵容等资料沿用 {raw["_cachedSourceAt"]} 的来源快照。' if raw.get('_cachedSourceAt') else '',
            'source': row['source'], 'pregame': {'capturedAt': pre.get('capturedAt'), 'hash': pre.get('hash')},
            'review': {'status': '赛后对照' if row['finished'] else '待完场', 'score': [row['teams'][s]['goals'] for s in ['home', 'away']],
                       'summary': '赛前阵容和天气记录已保留，可与赛后比赛表现对照。天气预报不等于实测，也不能单独解释赛果。' if pre else '没有有效赛前补充分析记录，不补写事前判断。'},
            'method': '首发按来源明确标注且11人不重复才确认；对比上一场及最近同对手交锋，不将首发变化直接归因为伤停。'}


def research(ident):
    row = next((r for r in load(PUBLIC / 'daily-football.json').get('matches', []) if r.get('id') == ident), None)
    if not row or not re.fullmatch(r'\d{1,16}', ident):
        raise LookupError('未收录这场每日赛事')
    return research_row(row)


def research_row(row):
    ident = row['id']
    if not re.fullmatch(r'\d{1,16}', ident):
        raise LookupError('赛事编号不正确')
    path = PUBLIC / 'daily-research' / (ident + '.json')
    old = load(path)
    if old and (old.get('eventId') != ident or dt(old.get('kickoff')) != dt(row.get('kickoff')) or
                any(old.get('teams', {}).get(s, {}).get('teamId') != row['teams'][s]['id'] for s in ('home', 'away'))):
        old = {}
    at = datetime.now(timezone.utc)
    ttl = 120 if row['started'] and not row['finished'] else 300
    if dt(old.get('updatedAt')) and timedelta(0) <= at - dt(old['updatedAt']) < timedelta(seconds=ttl):
        return old
    if not read_control()['enabled']:
        return {**old, 'paused': True, 'message': '同步已暂停，显示已保存资料'}
    if not LOCK.acquire(blocking=False):
        return {**old, 'pending': True, 'message': '补充资料正在排队读取，请稍后重新打开'}
    try:
        result = build(row, at)
        publish(path, result)
        return result
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return {**old, 'message': '本场补充来源暂未更新，已保留最近资料'}
    finally:
        LOCK.release()


def refresh_research():
    if not read_control()['enabled']:
        return {'paused': True}
    at = datetime.now(timezone.utc)
    matches = load(PUBLIC / 'daily-football.json').get('matches', [])
    matches = [m for m in matches if dt(m.get('kickoff')) and at - timedelta(hours=4) < dt(m['kickoff']) < at + timedelta(hours=3)]
    matches.sort(key=lambda m: (load(PUBLIC / 'daily-research' / (m['id'] + '.json')).get('updatedAt', ''), m['kickoff']))
    results = [research(m['id']) for m in matches[:2]]
    return {'checked': len(results), 'available': sum(bool(r.get('teams')) for r in results)}
