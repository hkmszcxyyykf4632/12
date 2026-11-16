"""Verified match identities, attributed lineups and bounded incremental backfill."""
import hashlib
import http.client
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .files import PUBLIC, STATE, publish, read_json
from .match_facts import build_facts
from .leagues import league_config, league_path
from .rankings import COMPETITIONS, EPL_NAMES, normalize, player_code
from .ucl import fetch_json

BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer'
SPANISH_NAMES = {'Athletic Club': 'Ath Bilbao', 'Athletic Bilbao': 'Ath Bilbao', 'Atlético Madrid': 'Ath Madrid',
                 'Atletico Madrid': 'Ath Madrid', 'Celta Vigo': 'Celta', 'Alavés': 'Alaves', 'Espanyol': 'Espanol',
                 'Racing Santander': 'Santander', 'Racing de Santander': 'Santander', 'Deportivo La Coruña': 'La Coruna',
                 'Deportivo La Coruna': 'La Coruna', 'Real Betis': 'Betis', 'Real Sociedad': 'Sociedad',
                 'Rayo Vallecano': 'Vallecano', 'Real Oviedo': 'Oviedo'}
LOCKS = [threading.Lock() for _ in range(32)]
EVENT_TYPES = {'goal': '进球', 'penalty---scored': '点球进球', 'own-goal': '乌龙球',
               'yellow-card': '黄牌', 'red-card': '红牌', 'yellow-red-card': '两黄变红',
               'substitution': '换人', 'penalty---missed': '点球未进'}


def now():
    return datetime.now(timezone.utc)


def fresh(value, seconds):
    try:
        return 0 <= (now() - datetime.fromisoformat(value['updatedAt'])).total_seconds() < seconds
    except (KeyError, TypeError, ValueError):
        return False


def match_catalogue(league):
    folder = league_path(PUBLIC, league)
    data = read_json(folder / 'data.json')
    live = read_json(folder / 'live.json') if (folder / 'live.json').exists() else {}
    merged = {m['id']: m for m in data['matches']}
    for m in live.get('matches', []):
        if league != 'ucl':
            for key, old in list(merged.items()):
                if (old['home'], old['away'], old['season'], old['competition']) == (m['home'], m['away'], m['season'], m['competition']):
                    del merged[key]
        merged[m['id']] = m
    return data, sorted(merged.values(), key=lambda m: (m['date'], m.get('kickoff') or ''), reverse=True)


def canonical(name, league):
    return normalize(EPL_NAMES.get(name, name) if league == 'epl' else SPANISH_NAMES.get(name, name) if league == 'laliga' else name)


def resolve_event(match, league, fetch_missing=True):
    if re.fullmatch(r'espn:\d+', match['id']):
        return match['id'].split(':')[1]
    competition = COMPETITIONS[league]
    if match['competition'] == league_config(league).lower:
        competition = {'epl': 'eng.2', 'laliga': 'esp.2'}.get(league, competition)
    key = f'{competition}-{match["date"]}'
    path = STATE / 'event-index' / f'{key}.json'
    saved = read_json(path) if path.exists() else {}
    if not fresh(saved, 21600):
        if not fetch_missing:
            return None
        source = f'{BASE}/{competition}/scoreboard?dates={match["date"].replace("-", "")}&limit=1000'
        raw = fetch_json(source)
        events = []
        for event in raw.get('events', []):
            sides = {c['homeAway']: c['team']['displayName'] for c in event['competitions'][0]['competitors']}
            if set(sides) == {'home', 'away'}:
                events.append({'id': str(event['id']), 'date': event['date'][:10], **sides})
        saved = {'updatedAt': now().isoformat(), 'events': events}
        publish(path, saved)
    candidates = [e for e in saved.get('events', []) if e['date'] == match['date']
                  and all(canonical(e[k], league) == canonical(match[k], league) for k in ('home', 'away'))]
    return candidates[0]['id'] if len(candidates) == 1 else None


def minute(clock):
    found = re.match(r'^(\d+)', str(clock or ''))
    return int(found[1]) if found else None


def parse_player(raw, club, catalogue, completed, duration):
    person = raw['athlete']
    plays = raw.get('plays', [])
    substitutions = [p.get('clock', {}).get('displayValue', '') for p in plays if p.get('substitution')]
    red = next((p.get('clock', {}).get('displayValue', '') for p in plays if p.get('redCard')), None)
    stats = {s['name']: s.get('value') for s in raw.get('stats', [])}
    starter = raw.get('starter') is True
    played = starter or raw.get('subbedIn') is True or stats.get('appearances') == 1
    entered = substitutions[0] if raw.get('subbedIn') and substitutions else None
    left = substitutions[-1] if raw.get('subbedOut') and substitutions else red
    minutes = stats.get('minutesPlayed', stats.get('minutes'))
    estimated = False
    if minutes is None and completed:
        start = 0 if starter else minute(entered)
        end = minute(left) if left else duration if not raw.get('subbedOut') and not stats.get('redCards') else None
        if not played:
            minutes = 0
        elif start is not None and end is not None and 0 <= start <= end:
            minutes, estimated = max(0, min(duration, end) - min(duration, start)), True
    return {'espnId': str(person['id']), 'name': person.get('displayName', person.get('fullName', '')),
            'playerCode': player_code({'uid': f'a:{person["id"]}', 'name': person.get('displayName', '')}, club, catalogue) if club else None,
            'shirt': str(raw.get('jersey', '')), 'position': raw.get('position', {}).get('abbreviation', ''),
            'formationPlace': str(raw.get('formationPlace', '')), 'starter': starter, 'played': played,
            'minutes': minutes, 'minutesEstimated': estimated, 'entered': entered, 'left': left,
            'replaces': str(raw.get('subbedInFor', {}).get('athlete', {}).get('id', '')),
            'goals': stats.get('totalGoals'), 'assists': stats.get('goalAssists'),
            'yellowCards': stats.get('yellowCards'), 'redCards': stats.get('redCards')}


def parse_detail(raw, match, catalogue, league, event_id):
    if str(raw.get('header', {}).get('id')) != str(event_id):
        raise ValueError('Match identity mismatch')
    game = raw['header']['competitions'][0]
    competitors = {c['homeAway']: c for c in game['competitors']}
    if set(competitors) != {'home', 'away'} or game['date'][:10] != match['date']:
        raise ValueError('Match date or competitors mismatch')
    for side, competitor in competitors.items():
        if canonical(competitor['team']['displayName'], league) != canonical(match[side], league):
            raise ValueError('Match club mismatch')
    completed = game.get('status', {}).get('type', {}).get('completed') is True
    extra = any(e.get('period', {}).get('number', 0) in (3, 4) for e in raw.get('keyEvents', []))
    duration = 120 if extra else 90
    sides = {}
    for row in raw.get('rosters', []):
        side = row.get('homeAway')
        if side not in competitors or str(row['team']['id']) != str(competitors[side]['id']):
            raise ValueError('Roster club mismatch')
        club = next((t for t in catalogue['teams'] if t['name'] == match[side]), None)
        players = [parse_player(p, club, catalogue, completed, duration) for p in row.get('roster', [])]
        if len({p['espnId'] for p in players}) != len(players):
            raise ValueError('Duplicate lineup player')
        sides[side] = {'teamId': club['id'] if club else None, 'name': match[side],
                       'formation': row.get('formation', ''), 'players': players,
                       'confirmed': sum(p['starter'] for p in players) == 11}
    statistics = []
    for row in raw.get('boxscore', {}).get('teams', []):
        side = next((k for k, c in competitors.items() if str(c['id']) == str(row['team']['id'])), None)
        if side:
            statistics.append({'side': side, 'values': {s['name']: s['displayValue'] for s in row.get('statistics', [])}})
    events = []
    for event in raw.get('keyEvents', []):
        kind = event.get('type', {}).get('type', '')
        if kind not in EVENT_TYPES or event.get('shootout'):
            continue
        events.append({'type': kind, 'label': EVENT_TYPES[kind], 'clock': event.get('clock', {}).get('displayValue', ''),
                       'period': event.get('period', {}).get('number'),
                       'side': next((k for k, c in competitors.items() if str(c['id']) == str(event.get('team', {}).get('id'))), ''),
                       'players': [{'espnId': str(p['athlete']['id']), 'name': p['athlete'].get('displayName', '')} for p in event.get('participants', [])]})
    venue = raw.get('gameInfo', {}).get('venue', {})
    return {'version': 1, 'league': league, 'matchId': match['id'], 'eventId': str(event_id),
            'date': match['date'], 'home': match['home'], 'away': match['away'], 'completed': completed,
            'updatedAt': now().isoformat(), 'source': f'https://www.espn.com/soccer/lineups/_/gameId/{event_id}',
            'status': 'available' if all(sides.get(k, {}).get('confirmed') for k in ('home', 'away')) else 'pending',
            'lineups': sides, 'statistics': statistics, 'events': events, 'duration': duration,
            'minutesBasis': '未提供官方分钟数时，按换人及红牌分钟估算，不计补时；加时另计。',
            'venue': venue.get('fullName', ''), 'attendance': raw.get('gameInfo', {}).get('attendance')}


def cache_seconds(match, cached):
    if cached and cached.get('status') == 'unavailable':
        return 21600
    if match.get('started') and not match.get('finished'):
        return 300
    if cached and cached.get('completed') and cached.get('status') == 'available':
        age = (now().date() - datetime.fromisoformat(match['date']).date()).days
        return 1800 if age <= 2 else 604800
    return 300 if match.get('started') or match.get('finished') else 3600


def detail_for_match(match, catalogue, league, fetch_missing=True):
    key = hashlib.sha256((league + '|' + match['id']).encode()).hexdigest()
    path = league_path(PUBLIC, league) / 'match-details' / f'{key[:24]}.json'
    previous = read_json(path) if path.exists() else None
    ttl = cache_seconds(match, previous)
    usable = previous and (previous.get('status') != 'unavailable' or previous.get('mappingVersion') == 3)
    if usable and fresh(previous, ttl) or not fetch_missing:
        return previous
    with LOCKS[int(key[:2], 16) % len(LOCKS)]:
        if path.exists():
            previous = read_json(path)
            if fresh(previous, ttl) and (previous.get('status') != 'unavailable' or previous.get('mappingVersion') == 3):
                return previous
        try:
            event_id = resolve_event(match, league)
            if not event_id:
                result = {'version': 1, 'mappingVersion': 3, 'league': league, 'matchId': match['id'], 'status': 'unavailable',
                          'updatedAt': now().isoformat(), 'lineups': {}, 'statistics': [], 'events': [],
                          'message': '暂未找到可核对的本场出场名单。'}
            else:
                raw_path = STATE / 'match-summaries' / f'{event_id}.json'
                saved = read_json(raw_path) if raw_path.exists() else {}
                if not fresh(saved, ttl):
                    saved = {'updatedAt': now().isoformat(), 'raw': fetch_json(f'{BASE}/all/summary?event={event_id}')}
                    publish(raw_path, saved)
                result = parse_detail(saved['raw'], match, catalogue, league, event_id)
            publish(path, result)
            return result
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            if previous:
                return {**previous, 'refreshFailed': True}
            raise


def get_detail(match_id, league, fetch_missing=True):
    catalogue, matches = match_catalogue(league)
    match = next((m for m in matches if m['id'] == match_id), None)
    if not match:
        raise LookupError('Unknown match')
    return detail_for_match(match, catalogue, league, fetch_missing)


def refresh_details(league, limit=80):
    catalogue, matches = match_catalogue(league)
    chosen = {}
    for team in catalogue['teams']:
        for m in [m for m in matches if m.get('finished') and team['name'] in (m['home'], m['away'])][:20]:
            chosen[m['id']] = m
    for m in matches:
        if m.get('finished') and m['season'] == catalogue['season'] and m['competition'] == league_config(league).competition:
            chosen[m['id']] = m
        if m.get('kickoff') and m.get('started') and not m.get('finished'):
            chosen[m['id']] = m
    pending = [m for m in chosen.values() if not (cached := detail_for_match(m, catalogue, league, False)) or not fresh(cached, cache_seconds(m, cached)) or cached.get('status') == 'unavailable' and cached.get('mappingVersion') != 3]
    pending.sort(key=lambda m: m.get('date', ''), reverse=True)
    def fetch_one(match):
        try:
            return detail_for_match(match, catalogue, league)
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fetch_one, pending[:limit]))
    entries = {}
    for m in chosen.values():
        detail = detail_for_match(m, catalogue, league, False)
        if detail:
            entries[m['id']] = {'status': detail['status'], 'updatedAt': detail['updatedAt'], 'eventId': detail.get('eventId')}
    snapshot = {'version': 1, 'league': league, 'season': catalogue['season'], 'updatedAt': now().isoformat(),
                'intervalSeconds': 300, 'targetMatches': len(chosen), 'available': sum(e['status'] == 'available' for e in entries.values()),
                'entries': entries}
    publish(league_path(PUBLIC, league) / 'match-index.json', snapshot)
    competition = league_config(league).competition
    season_done = [m for m in matches if m.get('finished') and m['season'] == catalogue['season'] and m['competition'] == competition]
    pairs = [(m, d) for m in chosen.values() if m.get('finished') and (d := detail_for_match(m, catalogue, league, False))]
    publish(league_path(PUBLIC, league) / 'match-facts.json', build_facts(league, catalogue, competition, pairs, len(season_done)))
    return snapshot


def lineup_context(league, fixture, recent):
    catalogue, _ = match_catalogue(league)
    result = {}
    cutoff = datetime.fromisoformat((fixture.kickoff or fixture.date).replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
    for club, matches in recent.items():
        summaries, players, formations = [], {}, Counter()
        for match in matches:
            if match['date'] >= fixture.date or not match['finished']:
                continue
            detail = detail_for_match(match, catalogue, league, False)
            side = 'home' if match['home'] == club else 'away'
            lineup = (detail or {}).get('lineups', {}).get(side)
            if not lineup or not lineup.get('confirmed'):
                continue
            formations[lineup['formation']] += 1
            starters = [p['espnId'] for p in lineup['players'] if p['starter']]
            summaries.append({'matchId': match['id'], 'date': match['date'], 'competition': match['competition'],
                              'formation': lineup['formation'], 'starters': starters, 'source': detail['source']})
            played_at = datetime.fromisoformat((match.get('kickoff') or match['date']).replace('Z', '+00:00'))
            if played_at.tzinfo is None:
                played_at = played_at.replace(tzinfo=timezone.utc)
            days = (cutoff - played_at).total_seconds() / 86400
            for p in lineup['players']:
                target = players.setdefault(p['espnId'], {'name': p['name'], 'starts': 0, 'appearances': 0, 'knownMinutes': 0,
                                                          'minutes7Days': 0, 'minutes14Days': 0, 'minutesSamples': 0, 'estimatedSamples': 0})
                target['starts'] += int(p['starter'])
                target['appearances'] += int(p['played'])
                if p['minutes'] is not None and p['played']:
                    target['knownMinutes'] += p['minutes']
                    target['minutesSamples'] += 1
                    target['estimatedSamples'] += int(p['minutesEstimated'])
                    if days <= 7:
                        target['minutes7Days'] += p['minutes']
                    if days <= 14:
                        target['minutes14Days'] += p['minutes']
        overlap = len(set(summaries[0]['starters']) & set(summaries[1]['starters'])) if len(summaries) >= 2 else None
        result[club] = {'requestedMatches': len(matches), 'coveredMatches': len(summaries), 'formations': dict(formations),
                        'latestTwoStarterOverlap': overlap, 'matches': summaries,
                        'players': sorted(players.values(), key=lambda p: (-p['starts'], -p['appearances']))[:30],
                        'minutesBasis': '分钟可能由换人/红牌时间估算，不含补时；只计算已收录比赛，不能把未覆盖比赛视为休息。',
                        'rotationBasis': '最近两份已收录首发的重合人数；中间缺少名单时不代表相邻两场。'}
    return result


def next_lineup_evidence(league, fixture):
    if fixture is None:
        return {}
    _, matches = match_catalogue(league)
    recent = {club: [m for m in matches if m.get('finished') and m['date'] < fixture.date
                    and club in (m['home'], m['away'])][:20] for club in [fixture.home, fixture.away]}
    return lineup_context(league, fixture, recent)
