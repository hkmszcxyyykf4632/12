"""Fetch attributed public football data and atomically publish a static snapshot."""
import argparse
import concurrent.futures
import csv
import datetime as dt
import io
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
FPL = 'https://fantasy.premierleague.com/api/'
NAMES = {
    'Arsenal': ('阿森纳', '#b72932'), 'Aston Villa': ('阿斯顿维拉', '#762c48'),
    'Bournemouth': ('伯恩茅斯', '#ba3035'), 'Brentford': ('布伦特福德', '#b52b32'),
    'Brighton': ('布莱顿', '#2469a9'), 'Chelsea': ('切尔西', '#2254a2'),
    'Coventry City': ('考文垂', '#347c9c'), 'Crystal Palace': ('水晶宫', '#275999'),
    'Everton': ('埃弗顿', '#2455a4'), 'Fulham': ('富勒姆', '#353b40'),
    'Hull City': ('赫尔城', '#9a640b'), 'Ipswich Town': ('伊普斯维奇', '#315b99'),
    'Leeds': ('利兹联', '#735d17'), 'Liverpool': ('利物浦', '#b22b30'),
    'Man City': ('曼城', '#347d9c'), 'Man Utd': ('曼联', '#b32930'),
    'Newcastle': ('纽卡斯尔联', '#383d40'), "Nott'm Forest": ('诺丁汉森林', '#b42d35'),
    'Spurs': ('托特纳姆热刺', '#353b5b'), 'Sunderland': ('桑德兰', '#b6343a'),
    'Burnley': ('伯恩利', '#772d48'), 'Wolves': ('狼队', '#936910'),
    'West Ham': ('西汉姆联', '#762d49'), 'Leicester': ('莱斯特城', '#24559a'),
    'Southampton': ('南安普敦', '#a52b35'),
}
ALIASES = {'Tottenham': 'Spurs', "Nott'm Forest": "Nott'm Forest", 'Coventry': 'Coventry City',
           'Hull': 'Hull City', 'Ipswich': 'Ipswich Town', 'Leeds United': 'Leeds',
           'Manchester City': 'Man City', 'Manchester United': 'Man Utd', 'Man United': 'Man Utd',
           'Nottingham Forest': "Nott'm Forest"}

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'FootballKnow/1.0 (football statistics)', 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read().decode('utf-8-sig')

def team_name(name):
    return ALIASES.get(name, name)

def match_id(date, home, away):
    return date + '|' + home + '|' + away

def positive(value):
    try:
        number = float(value)
        return number if 1 < number <= 10000 else None
    except (TypeError, ValueError):
        return None

def validate_feed(key, raw):
    if key == 'fixtures':
        fixtures = json.loads(raw)
        if not isinstance(fixtures, list) or len(fixtures) != 380:
            raise ValueError('Incomplete current-season fixture feed')
    else:
        fields = csv.DictReader(io.StringIO(raw)).fieldnames or []
        if not {'Date','HomeTeam','AwayTeam','FTHG','FTAG','FTR'}.issubset(fields):
            raise ValueError('Historical feed has no recognized result columns')
    return raw

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'public' / 'data.json'))
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    bootstrap = json.loads(fetch(FPL + 'bootstrap-static/'))
    events = bootstrap.get('events', [])
    first = min(e['deadline_time'] for e in events)
    year = int(first[:4])
    season = f'{year}/{str(year + 1)[2:]}'
    teams = []
    for team in bootstrap['teams']:
        cn, color = NAMES.get(team['name'], (team['name'], '#205e4b'))
        teams.append({'id': team['id'], 'code': team['code'], 'name': team['name'],
                      'cn': cn, 'short': team['short_name'], 'color': color})
    if len(teams) != 20 or len({t['name'] for t in teams}) != 20:
        raise ValueError('Expected twenty distinct Premier League teams; retaining previous snapshot.')
    by_id = {t['id']: t for t in teams}
    names = {t['name'] for t in teams}
    regions = {r['id']: r.get('name', '') for r in bootstrap.get('regions', [])}
    players = []
    for p in bootstrap['elements']:
        if p.get('removed') or p.get('team') not in by_id:
            continue
        players.append({k: p.get(k) for k in ['id', 'code', 'team', 'first_name', 'second_name', 'web_name', 'known_name', 'team_join_date',
            'birth_date', 'squad_number', 'minutes', 'goals_scored', 'assists', 'clean_sheets', 'status', 'news',
            # Season totals and availability the public feed already carries; absent keys stay None.
            'starts', 'yellow_cards', 'red_cards', 'saves', 'goals_conceded', 'own_goals', 'penalties_saved', 'penalties_missed',
            'expected_goals', 'expected_assists', 'expected_goal_involvements', 'expected_goals_conceded',
            'chance_of_playing_next_round', 'news_added']}
            | {'position': p['element_type'], 'country': regions.get(p.get('region'), '')})
    jobs = {'fixtures': FPL + 'fixtures/'}
    for y in [year, year - 1]:
        for league in ['E0', 'E1']:
            jobs[f'{y}-{league}'] = f'https://www.football-data.co.uk/mmz4281/{y % 100:02}{(y+1) % 100:02}/{league}.csv'
    responses, warnings, sources = {}, [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch, url): key for key, url in jobs.items()}
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                responses[key] = validate_feed(key, future.result())
                sources.append({'name': 'FPL 赛程' if key == 'fixtures' else key, 'url': jobs[key], 'fetchedAt': now.isoformat()})
            except (OSError, urllib.error.URLError, UnicodeError, ValueError) as error:
                warnings.append(f'{key}: {type(error).__name__}')
    matches = {}
    output = Path(args.output)
    if output.exists():
        previous = json.loads(output.read_text(encoding='utf-8'))
        failed_urls = {url for key,url in jobs.items() if key not in responses}
        for row in previous.get('matches', []):
            if row.get('source') in failed_urls and (row['home'] in names or row['away'] in names):
                matches[row['id']] = row
        sources += [source for source in previous.get('sources', []) if source.get('url') in failed_urls]
    for key, raw in responses.items():
        if key == 'fixtures':
            continue
        for row in csv.DictReader(io.StringIO(raw)):
            if not row.get('Date') or not row.get('HomeTeam'):
                continue
            home, away = team_name(row['HomeTeam']), team_name(row['AwayTeam'])
            if home not in names and away not in names:
                continue
            date = None
            for fmt in ['%d/%m/%Y', '%d/%m/%y']:
                try:
                    date = dt.datetime.strptime(row['Date'], fmt).date().isoformat()
                    break
                except ValueError:
                    pass
            if not date or date > now.date().isoformat():
                continue
            if row.get('FTR') not in ['H', 'D', 'A'] or not str(row.get('FTHG', '')).isdigit() or not str(row.get('FTAG', '')).isdigit():
                continue
            odds = []
            for prefix, label in [('AvgC', '市场平均 · 收盘'), ('Avg', '市场平均 · 赛前'),
                                  ('B365C', 'Bet365 · 收盘'), ('B365', 'Bet365 · 赛前')]:
                values = {r: positive(row.get(prefix + r)) for r in ['H', 'D', 'A']}
                if all(values.values()):
                    odds.append({'label': label, **values})
            ident = match_id(date, home, away)
            matches[ident] = {'id': ident, 'date': date, 'home': home, 'away': away,
                'homeGoals': int(row['FTHG']), 'awayGoals': int(row['FTAG']), 'result': row['FTR'],
                'competition': '英超' if key.endswith('E0') else '英冠', 'season': key[:4] + '/' + str(int(key[:4]) + 1)[2:],
                'odds': odds, 'source': jobs[key], 'finished': True}
    for fixture in json.loads(responses.get('fixtures', '[]')):
        if not fixture.get('kickoff_time') or fixture.get('team_h') not in by_id or fixture.get('team_a') not in by_id:
            continue
        date = fixture['kickoff_time'][:10]
        home, away = by_id[fixture['team_h']]['name'], by_id[fixture['team_a']]['name']
        ident = match_id(date, home, away)
        if ident in matches:
            continue
        hg, ag = fixture.get('team_h_score'), fixture.get('team_a_score')
        done = fixture.get('finished') is True and hg is not None and ag is not None
        matches[ident] = {'id': ident, 'date': date, 'kickoff': fixture['kickoff_time'], 'home': home, 'away': away,
            'homeGoals': hg if done else None, 'awayGoals': ag if done else None,
            'result': ('H' if hg > ag else 'A' if ag > hg else 'D') if done else None,
            'competition': '英超', 'season': season, 'odds': [], 'source': FPL + 'fixtures/', 'finished': done}
    ordered = sorted(matches.values(), key=lambda m: (m['date'], m['id']), reverse=True)
    if not players or not any(m['finished'] for m in ordered):
        raise ValueError('Incomplete upstream data; retaining previous snapshot.')
    snapshot = {'version': 1, 'season': season, 'updatedAt': now.isoformat(), 'teams': teams,
        'players': players, 'matches': ordered, 'warnings': warnings,
        'sources': [{'name': 'Premier League Fantasy · 球队与球员', 'url': FPL + 'bootstrap-static/', 'fetchedAt': now.isoformat()}] + sources,
        'scope': '最近二十场已完成联赛比赛（英超及英冠）；不包含杯赛。球员为 FPL 收录名单。'}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temporary.chmod(0o644)
    os.replace(temporary, output)
    print(json.dumps({'teams': len(teams), 'players': len(players), 'matches': len(ordered), 'season': season,
        'warnings': warnings, 'latestFinished': max(m['date'] for m in ordered if m['finished']),
        'recentCounts': {t['name']: min(20, sum(m['finished'] and t['name'] in [m['home'], m['away']] for m in ordered)) for t in teams}}, ensure_ascii=False))

if __name__ == '__main__':
    main()
