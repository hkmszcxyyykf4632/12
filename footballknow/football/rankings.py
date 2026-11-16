"""Attributed competition tables and player leaders with separate refresh clocks."""
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .files import PUBLIC, fetch_text, publish, read_json
from .leagues import league_config, league_path
from .ucl import fetch_json

COMPETITIONS = {'epl': 'eng.1', 'laliga': 'esp.1', 'ucl': 'uefa.champions'}
OFFICIAL_TABLES = {
    'epl': 'https://www.premierleague.com/en/tables',
    'laliga': 'https://www.laliga.com/en-GB/laliga-easports/standing',
    'ucl': 'https://www.uefa.com/uefachampionsleague/standings/',
}
EPL_NAMES = {
    'Brighton & Hove Albion': 'Brighton', 'Manchester City': 'Man City',
    'Manchester United': 'Man Utd', 'AFC Bournemouth': 'Bournemouth',
    'Leeds United': 'Leeds', 'Tottenham Hotspur': 'Spurs',
    'Newcastle United': 'Newcastle', 'Nottingham Forest': "Nott'm Forest",
}
ZONES = {
    'Champions League': ('champions', '欧冠席位区'),
    'Europa League': ('europe', '欧联席位区'),
    'Europa Conference League': ('europe', '欧协联席位区'),
    'Conference League': ('europe', '欧协联席位区'),
    'Relegation': ('relegation', '降级区'),
    'Qualifies for round of 16': ('champions', '直接晋级十六强区'),
    'Qualifies for knockout round play-offs': ('playoff', '淘汰赛附加赛区'),
    'Knockout Round Playoffs': ('playoff', '淘汰赛附加赛区'),
    'Eliminated': ('relegation', '淘汰区'),
}


def normalize(value: str) -> str:
    value = str(value).replace('ß', 'ss').replace('ø', 'o').replace('Ø', 'O')
    return ''.join(c for c in unicodedata.normalize('NFKD', value).lower() if c.isalnum())


def integer(value, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ValueError('Boolean is not a statistic')
    number = float(value)
    if not number.is_integer() or number < minimum:
        raise ValueError('Invalid count')
    return int(number)


def club_lookup(catalogue: dict, source_id: str, name: str) -> dict:
    by_id = [t for t in catalogue['teams'] if str(t.get('espnId', '')) == str(source_id)]
    if len(by_id) == 1:
        return by_id[0]
    canonical = EPL_NAMES.get(name, name)
    candidates = [t for t in catalogue['teams'] if normalize(t['name']) == normalize(canonical)]
    if len(candidates) != 1:
        raise ValueError(f'Unmapped source club: {name}')
    return candidates[0]


def parse_standings(raw: dict, catalogue: dict, league: str) -> list[dict]:
    year = int(catalogue['season'][:4])
    if raw.get('season', {}).get('year') != year:
        raise ValueError('Standings season mismatch')
    groups = raw.get('children', [])
    if league == 'ucl':
        groups = [g for g in groups if g.get('name') == 'League Phase']
    if len(groups) != 1 or groups[0].get('standings', {}).get('season') != year:
        raise ValueError('Unexpected competition phase')
    entries = groups[0]['standings']['entries']
    if len(entries) != len(catalogue['teams']):
        raise ValueError('Incomplete standings')
    rows = []
    fields = {'rank': 'rank', 'played': 'gamesPlayed', 'wins': 'wins', 'draws': 'ties',
              'losses': 'losses', 'goalsFor': 'pointsFor', 'goalsAgainst': 'pointsAgainst',
              'goalDifference': 'pointDifferential', 'points': 'points'}
    for entry in entries:
        team = club_lookup(catalogue, entry['team']['id'], entry['team']['displayName'])
        stats = {s['name']: s.get('value') for s in entry['stats']}
        row = {'teamId': team['id'], 'espnId': str(entry['team']['id']), 'name': team['name'],
               'cn': team['cn'], 'short': team['short'], 'color': team['color']}
        for key, source in fields.items():
            row[key] = integer(stats[source], -10000 if key in {'goalDifference', 'points'} else 0)
        if row['rank'] < 1 or row['rank'] > len(entries):
            raise ValueError('Invalid official rank')
        if row['played'] != row['wins'] + row['draws'] + row['losses']:
            raise ValueError('Incomplete W/D/L record')
        if row['goalDifference'] != row['goalsFor'] - row['goalsAgainst']:
            raise ValueError('Goal difference does not reconcile')
        row['pointsAdjustment'] = row['points'] - (3 * row['wins'] + row['draws'])
        row['zone'], row['zoneLabel'] = ZONES.get(entry.get('note', {}).get('description', ''), ('', ''))
        if league == 'ucl':
            row['zone'], row['zoneLabel'] = ('champions', '直接晋级十六强区') if row['rank'] <= 8 else (
                ('playoff', '淘汰赛附加赛区') if row['rank'] <= 24 else ('relegation', '淘汰区'))
        rows.append(row)
    if len({r['teamId'] for r in rows}) != len(rows):
        raise ValueError('Duplicate standings club')
    if sum(r['wins'] for r in rows) != sum(r['losses'] for r in rows):
        raise ValueError('Standings results do not reconcile')
    if sum(r['goalsFor'] for r in rows) != sum(r['goalsAgainst'] for r in rows):
        raise ValueError('Standings goals do not reconcile')
    return sorted(rows, key=lambda r: r['rank'])


def match_breakdowns(catalogue: dict, live: dict, rows: list[dict], league: str) -> dict:
    competition = league_config(league).competition
    merged = {}
    for match in catalogue.get('matches', []) + live.get('matches', []):
        if match.get('season') != catalogue['season'] or match.get('competition') != competition:
            continue
        if league == 'ucl' and match.get('phase') != '联赛阶段':
            continue
        key = match.get('id') if league == 'ucl' else (match.get('date'), match.get('home'), match.get('away'))
        merged[key] = match
    finished = [m for m in merged.values() if m.get('finished') and not m.get('provisional')
                and isinstance(m.get('homeGoals'), int) and isinstance(m.get('awayGoals'), int)]
    finished.sort(key=lambda m: (m['date'], m.get('kickoff') or '', str(m.get('id'))))
    splits = {'home': [], 'away': [], 'form': []}
    mismatches = []
    for row in rows:
        matches = [m for m in finished if row['name'] in [m['home'], m['away']]]
        totals = summarize(matches, row['name'])
        if any(totals[k] != row[k] for k in ['played', 'wins', 'draws', 'losses', 'goalsFor', 'goalsAgainst']):
            mismatches.append(row['teamId'])
        row['form'] = totals['form']
        row['cleanSheets'] = totals['cleanSheets'] if row['teamId'] not in mismatches else None
        for kind, chosen in [('home', [m for m in matches if m['home'] == row['name']]),
                             ('away', [m for m in matches if m['away'] == row['name']]),
                             ('form', matches[-5:])]:
            splits[kind].append({**{k: row[k] for k in ['teamId', 'name', 'cn', 'short', 'color']},
                                 **summarize(chosen, row['name'])})
    for table in splits.values():
        table.sort(key=lambda r: (-r['points'], -r['goalDifference'], -r['goalsFor'], r['name']))
        previous = None
        for i, row in enumerate(table):
            key = (row['points'], row['goalDifference'], row['goalsFor'])
            row['rank'] = i + 1 if key != previous else table[i - 1]['rank']
            previous = key
    return {'complete': not mismatches, 'unmatchedTeams': mismatches, 'matches': len(finished),
            'tables': splits if not mismatches else {}, 'basis': 'confirmed-results'}


def summarize(matches: list[dict], team: str) -> dict:
    result = dict(played=len(matches), wins=0, draws=0, losses=0, goalsFor=0, goalsAgainst=0, cleanSheets=0)
    form = []
    for match in matches:
        home = match['home'] == team
        scored, conceded = (match['homeGoals'], match['awayGoals']) if home else (match['awayGoals'], match['homeGoals'])
        outcome = 'W' if scored > conceded else 'D' if scored == conceded else 'L'
        result[{'W': 'wins', 'D': 'draws', 'L': 'losses'}[outcome]] += 1
        result['goalsFor'] += scored
        result['goalsAgainst'] += conceded
        result['cleanSheets'] += int(conceded == 0)
        form.append(outcome)
    result.update(points=result['wins'] * 3 + result['draws'],
                  goalDifference=result['goalsFor'] - result['goalsAgainst'], form=list(reversed(form[-5:])))
    return result


def refresh_standings(league: str) -> dict:
    folder = league_path(PUBLIC, league)
    catalogue = read_json(folder / 'data.json')
    source = f'https://site.api.espn.com/apis/v2/sports/soccer/{COMPETITIONS[league]}/standings?season={catalogue["season"][:4]}'
    rows = parse_standings(fetch_json(source), catalogue, league)
    live = read_json(folder / 'live.json') if (folder / 'live.json').exists() else {}
    breakdowns = match_breakdowns(catalogue, live, rows, league)
    snapshot = {'version': 1, 'league': league, 'season': catalogue['season'],
                'updatedAt': datetime.now(timezone.utc).isoformat(), 'intervalSeconds': 60,
                'phase': '联赛阶段' if league == 'ucl' else '联赛', 'provider': 'ESPN',
                'source': source, 'officialUrl': OFFICIAL_TABLES[league], 'entries': rows,
                'breakdowns': breakdowns}
    publish(folder / 'standings.json', snapshot)
    return snapshot


def statistics_data(html: str, league: str, season: str, view: str) -> dict:
    marker = "window['__espnfitt__']="
    start = html.find(marker)
    if start < 0:
        raise ValueError('Statistics data missing')
    embedded, _ = json.JSONDecoder().raw_decode(html[start + len(marker):].lstrip())
    stats = embedded['page']['content']['statistics']
    if str(stats.get('currentSeason')) != season[:4] or stats.get('league', {}).get('slug') != COMPETITIONS[league]:
        raise ValueError('Statistics competition or season mismatch')
    if stats.get('selectedView') != view or len(stats['tables']) != len(stats['tableRows']):
        raise ValueError('Statistics table shape changed')
    return stats


def player_code(person: dict, team: dict, catalogue: dict) -> int | None:
    source_id = person.get('uid', '').split(':')[-1]
    candidates = [p for p in catalogue['players'] if p['team'] == team['id']]
    by_id = [p for p in candidates if str(p['id']) == source_id and 'espn.com' in p.get('source', '')]
    if len(by_id) == 1:
        return by_id[0]['code']
    key = normalize(person['name'])
    matches = [p for p in candidates if any(normalize(n) == key for n in [
        p.get('known_name', ''), p.get('web_name', ''), p.get('first_name', '') + ' ' + p.get('second_name', '')])]
    if len(matches) == 1:
        return matches[0]['code']
    tokens = [normalize(t) for t in person['name'].split()]
    if len(tokens) >= 2:
        matches = [p for p in candidates if set(tokens).issubset({normalize(t) for t in (p.get('first_name', '') + ' ' + p.get('second_name', '')).split()})]
        if len(matches) == 1:
            return matches[0]['code']
    return None


def parse_scoring(stats: dict, catalogue: dict) -> dict:
    boards = {}
    for table, values in zip(stats['tables'], stats['tableRows']):
        headers = [h['type'] for h in table['headers']]
        metric = next((k for k in ['totalGoals', 'goalAssists'] if k in headers), None)
        if metric is None:
            continue
        rows = []
        for index, values_row in enumerate(values):
            if len(values_row) != len(headers):
                raise ValueError('Incomplete leader row')
            item = dict(zip(headers, values_row))
            person = item['athlete']
            source_team = item['team']
            identity = re.search(r'/id/(\d+)', source_team['href'])
            if not identity:
                raise ValueError('Leader club identity missing')
            team = club_lookup(catalogue, identity[1], source_team['name'])
            value = integer(item[metric]['value'])
            if rows and value > rows[-1]['value']:
                raise ValueError('Leader order changed')
            rows.append({'rank': index + 1 if not rows or value != rows[-1]['value'] else rows[-1]['rank'],
                         'espnId': person['uid'].split(':')[-1], 'name': person['name'],
                         'playerCode': player_code(person, team, catalogue), 'teamId': team['id'],
                         'teamName': team['cn'], 'appearances': integer(item['appearances']['value']),
                         'value': value, 'source': person['href']})
        if len({r['espnId'] for r in rows}) != len(rows):
            raise ValueError('Duplicate player leader')
        boards['scorers' if metric == 'totalGoals' else 'assists'] = rows
    if set(boards) != {'scorers', 'assists'}:
        raise ValueError('Missing player board')
    return boards


def parse_discipline(stats: dict, catalogue: dict) -> list[dict]:
    rows = []
    for table, values in zip(stats['tables'], stats['tableRows']):
        headers = [h['type'] for h in table['headers']]
        if not {'team', 'yellowCards', 'redCards', 'appearances'}.issubset(headers):
            continue
        for values_row in values:
            if len(values_row) != len(headers):
                raise ValueError('Incomplete discipline row')
            item = dict(zip(headers, values_row))
            source = item['team']
            team = club_lookup(catalogue, source['id'], source['name'])
            rows.append({'teamId': team['id'], 'name': team['cn'],
                         'played': integer(item['appearances']['value']),
                         'yellowCards': integer(item['yellowCards']['value']),
                         'redCards': integer(item['redCards']['value'])})
    if len(rows) != len(catalogue['teams']) or len({r['teamId'] for r in rows}) != len(rows):
        raise ValueError('Incomplete discipline table')
    return rows


def refresh_leaders(league: str) -> dict:
    folder = league_path(PUBLIC, league)
    catalogue = read_json(folder / 'data.json')
    base = f'https://www.espn.com/soccer/stats/_/league/{COMPETITIONS[league].upper()}/season/{catalogue["season"][:4]}'
    urls = [base + '/view/scoring', base + '/view/discipline']
    with ThreadPoolExecutor(max_workers=2) as pool:
        pages = list(pool.map(fetch_text, urls))
    scoring = statistics_data(pages[0], league, catalogue['season'], 'scoring')
    discipline = statistics_data(pages[1], league, catalogue['season'], 'discipline')
    boards = parse_scoring(scoring, catalogue)
    previous = read_json(folder / 'rankings.json') if (folder / 'rankings.json').exists() else {}
    if previous.get('season') == catalogue['season'] and any(previous.get('boards', {}).values()) and not all(boards.values()):
        raise ValueError('Unexpected empty player leaders; keep previous snapshot')
    snapshot = {'version': 1, 'league': league, 'season': catalogue['season'],
                'updatedAt': datetime.now(timezone.utc).isoformat(), 'intervalSeconds': 300,
                'provider': 'ESPN', 'providerCadence': '来源注明夜间更新，本站每5分钟检查。',
                'limit': 50, 'boards': boards, 'discipline': parse_discipline(discipline, catalogue),
                'sources': urls}
    publish(folder / 'rankings.json', snapshot)
    return snapshot
