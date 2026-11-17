"""La Liga official fixtures, ESPN rosters and attributed historical results."""
import csv
import io
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from .files import PUBLIC, fetch_text, publish, read_json
from .leagues import league_path
from .live import LiveSnapshot

CLUBS_URL = 'https://www.laliga.com/laliga-easports/clubes'
RESULTS_URL = 'https://www.laliga.com/laliga-easports/resultados'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1'
# Official slug, historical-result name, Chinese name, ESPN id, English Wikipedia article.
CLUBS = {
    'athletic-club': ('Ath Bilbao', '毕尔巴鄂竞技', 93, 'Athletic Bilbao'),
    'atletico-de-madrid': ('Ath Madrid', '马德里竞技', 1068, 'Atlético Madrid'),
    'c-a-osasuna': ('Osasuna', '奥萨苏纳', 97, 'CA Osasuna'),
    'rc-celta': ('Celta', '塞尔塔', 85, 'RC Celta de Vigo'),
    'd-alaves': ('Alaves', '阿拉维斯', 96, 'Deportivo Alavés'),
    'elche-c-f': ('Elche', '埃尔切', 3751, 'Elche CF'),
    'fc-barcelona': ('Barcelona', '巴塞罗那', 83, 'FC Barcelona'),
    'getafe-cf': ('Getafe', '赫塔费', 2922, 'Getafe CF'),
    'levante-ud': ('Levante', '莱万特', 1538, 'Levante UD'),
    'malaga-cf': ('Malaga', '马拉加', 99, 'Málaga CF'),
    'r-racing-club': ('Santander', '桑坦德竞技', 87, 'Racing de Santander'),
    'rayo-vallecano': ('Vallecano', '巴列卡诺', 101, 'Rayo Vallecano'),
    'rc-deportivo': ('La Coruna', '拉科鲁尼亚', 90, 'Deportivo de La Coruña'),
    'rcd-espanyol': ('Espanol', '西班牙人', 88, 'RCD Espanyol'),
    'real-betis': ('Betis', '皇家贝蒂斯', 244, 'Real Betis'),
    'real-madrid': ('Real Madrid', '皇家马德里', 86, 'Real Madrid CF'),
    'real-sociedad': ('Sociedad', '皇家社会', 89, 'Real Sociedad'),
    'sevilla-fc': ('Sevilla', '塞维利亚', 243, 'Sevilla FC'),
    'valencia-cf': ('Valencia', '瓦伦西亚', 94, 'Valencia CF'),
    'villarreal-cf': ('Villarreal', '比利亚雷亚尔', 102, 'Villarreal CF'),
    'girona-fc': ('Girona', '赫罗纳', 9812, 'Girona FC'),
    'rcd-mallorca': ('Mallorca', '马略卡', 84, 'RCD Mallorca'),
    'real-oviedo': ('Oviedo', '皇家奥维耶多', 92, 'Real Oviedo'),
}


def page_data(url: str) -> dict:
    node = BeautifulSoup(fetch_text(url), 'html.parser').find('script', id='__NEXT_DATA__')
    if node is None:
        raise OSError('Official page data missing')
    data = json.loads(node.string or '')['props']['pageProps']
    if data.get('statusCode', 200) != 200:
        raise OSError('Official page not available')
    return data


def official_teams() -> tuple[str, list[dict]]:
    data = page_data(CLUBS_URL)
    year = int(data['season'])
    teams = []
    for row in data['teams']:
        if row['slug'] not in CLUBS:
            raise OSError('A new club needs an explicit source-name mapping')
        name, cn, espn_id, article = CLUBS[row['slug']]
        color = row.get('color', '#164d3d')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            color = '#164d3d'
        if color.lower() in {'#ffffff', '#ffff00'}:
            color = '#47564d'
        teams.append({'id': row['id'], 'code': row['id'], 'name': name, 'cn': cn,
                      'short': row['shortname'], 'color': color, 'slug': row['slug'],
                      'espnId': espn_id, 'article': article, 'source': CLUBS_URL})
    if len(teams) != 20 or len({row['id'] for row in teams}) != 20:
        raise OSError('Expected twenty distinct official La Liga clubs')
    return f'{year}/{str(year + 1)[2:]}', teams


def squad(team: dict, season: str, endpoint: str = ESPN) -> list[dict]:
    url = f'{endpoint}/teams/{team["espnId"]}/roster'
    # This public endpoint accepts the standard urllib request headers.
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise OSError('Roster response too large')
    data = json.loads(raw)
    if str(data.get('season', {}).get('year')) != season[:4] or str(data.get('team', {}).get('id')) != str(team['espnId']):
        raise OSError('Roster season or club does not match')
    players = []
    for person in data.get('athletes', []):
        stats = {s['name']: s.get('value') for category in person.get('statistics', {}).get('splits', {}).get('categories', [])
                 for s in category.get('stats', [])}
        position = person.get('position', {}).get('abbreviation', '')
        pos = {'G': 1, 'GK': 1, 'D': 2, 'M': 3, 'F': 4}.get(position, 0)
        injuries = person.get('injuries', [])
        news = '；'.join(str(item.get('shortComment') or item.get('details', {}).get('detail') or
                             item.get('details', {}).get('type') or item.get('status') or '伤停资料待更新') for item in injuries)
        first = person.get('firstName') or person['displayName']
        last = person.get('lastName') or ''
        players.append({'id': int(person['id']), 'code': int(person['id']), 'team': team['id'],
                        'first_name': first, 'second_name': last, 'web_name': person['displayName'],
                        'known_name': person.get('fullName') or person['displayName'],
                        'photoUrl': (person.get('headshot') or {}).get('href'),
                        'birth_date': (person.get('dateOfBirth') or '')[:10] or None,
                        'squad_number': person.get('jersey'), 'country': person.get('citizenship', ''),
                        'position': pos, 'minutes': stats.get('minutesPlayed'),
                        'goals_scored': stats.get('totalGoals'), 'assists': stats.get('goalAssists'),
                        'status': 'i' if injuries else 'unreported', 'news': news, 'source': url})
    if len(players) < 11 or len({p['id'] for p in players}) != len(players):
        raise OSError('Incomplete club roster')
    return players


def historical_rows(raw: str, url: str, year: int, competition: str, clubs: set[str]) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw))
    if not {'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR'}.issubset(reader.fieldnames or []):
        raise OSError('Historical result columns missing')
    rows = []
    for row in reader:
        if row.get('FTR') not in {'H', 'D', 'A'} or not {row.get('HomeTeam'), row.get('AwayTeam')} & clubs:
            continue
        if not row.get('FTHG', '').isdigit() or not row.get('FTAG', '').isdigit():
            continue
        try:
            date = datetime.strptime(row['Date'], '%d/%m/%Y').date().isoformat()
        except ValueError:
            date = datetime.strptime(row['Date'], '%d/%m/%y').date().isoformat()
        if date > datetime.now(timezone.utc).date().isoformat():
            continue
        odds = []
        for prefix, label in [('AvgC', '市场平均 · 收盘'), ('Avg', '市场平均 · 赛前'),
                              ('B365C', 'Bet365 · 收盘'), ('B365', 'Bet365 · 赛前')]:
            try:
                values = {outcome: float(row.get(prefix + outcome) or 0) for outcome in ['H', 'D', 'A']}
                if all(1 < value <= 10000 for value in values.values()):
                    odds.append({'label': label, **values})
            except ValueError:
                pass
        home, away = row['HomeTeam'], row['AwayTeam']
        rows.append({'id': f'{date}|{home}|{away}', 'date': date, 'home': home, 'away': away,
                     'homeGoals': int(row['FTHG']), 'awayGoals': int(row['FTAG']), 'result': row['FTR'],
                     'finished': True, 'competition': competition, 'season': f'{year}/{str(year + 1)[2:]}',
                     'odds': odds, 'source': url})
    return rows


def refresh_catalogue() -> dict:
    folder = league_path(PUBLIC, 'laliga')
    season, teams = official_teams()
    previous = read_json(folder / 'data.json') if (folder / 'data.json').exists() else {}
    now = datetime.now(timezone.utc).isoformat()
    warnings, players, matches = [], [], []
    sources = [{'name': 'LALIGA 官方 · 本赛季球队', 'url': CLUBS_URL, 'fetchedAt': now}]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [(team, pool.submit(squad, team, season)) for team in teams]
        for team, future in tasks:
            url = f'{ESPN}/teams/{team["espnId"]}/roster'
            try:
                players += future.result()
                sources.append({'name': f'ESPN · {team["cn"]}球员', 'url': url, 'fetchedAt': now})
            except (OSError, ValueError, KeyError):
                retained = [p for p in previous.get('players', []) if p['team'] == team['id']]
                if previous.get('season') != season or not retained:
                    raise OSError('A roster is unavailable; retaining the previous catalogue') from None
                players += retained
                sources += [s for s in previous.get('sources', []) if s['url'] == url]
                warnings.append(f'{team["cn"]}球员资料沿用上次快照')
    if len({p['code'] for p in players}) != len(players):
        raise OSError('Roster contains duplicate player identities')
    clubs = {t['name'] for t in teams}
    year = int(season[:4])
    for y in [year, year - 1]:
        for code, competition in [('SP1', '西甲'), ('SP2', '西乙')]:
            url = f'https://www.football-data.co.uk/mmz4281/{y % 100:02}{(y + 1) % 100:02}/{code}.csv'
            try:
                matches += historical_rows(fetch_text(url), url, y, competition, clubs)
                sources.append({'name': f'{y} {competition} · 赛果与历史赔率', 'url': url, 'fetchedAt': now})
            except (OSError, ValueError):
                matches += [row for row in previous.get('matches', []) if row.get('source') == url]
                sources += [s for s in previous.get('sources', []) if s['url'] == url]
                warnings.append(f'{y} {competition}历史资料未更新')
    if any(sum(t['name'] in (m['home'], m['away']) for m in matches) < 20 for t in teams):
        raise OSError('Insufficient historical coverage for a current club')
    snapshot = {'version': 1, 'league': 'laliga', 'competition': '西甲', 'season': season,
                'updatedAt': now, 'teams': teams, 'players': players,
                'matches': sorted(matches, key=lambda m: (m['date'], m['id']), reverse=True),
                'warnings': warnings, 'sources': sources,
                'scope': '最近二十场已完成西甲与西乙联赛，可跨赛季；球员为 ESPN 收录名单，未提供的统计留空。'}
    publish(folder / 'data.json', snapshot)
    return snapshot


def parse_round(data: dict, catalogue: dict, url: str) -> list[dict]:
    if str(data.get('season')) != catalogue['season'][:4]:
        raise OSError('Fixture season does not match')
    teams = {t['id']: t['name'] for t in catalogue['teams']}
    rows = data.get('matches', [])
    if len(rows) != 10 or len({m['id'] for m in rows}) != 10:
        raise OSError('Incomplete official matchday')
    matches = []
    for row in rows:
        home, away = teams[row['home_team']['id']], teams[row['away_team']['id']]
        status = row['status']
        hg, ag = row.get('home_score'), row.get('away_score')
        scored = all(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 99 for n in (hg, ag))
        done = status == 'FullTime' and scored
        if status == 'FullTime' and not scored:
            raise OSError('Finished match has no valid score')
        kickoff = row.get('time') if status not in {'Postponed', 'Cancelled', 'Abandoned'} else None
        date = (row.get('date') or kickoff or '')[:10]
        matches.append({'id': f'{date}|{home}|{away}', 'fixtureId': row['id'], 'date': date,
                        'kickoff': kickoff, 'home': home, 'away': away,
                        'homeGoals': hg if scored else None, 'awayGoals': ag if scored else None,
                        'started': status in {'FirstHalf', 'HalfTime', 'SecondHalf', 'FullTime', 'Suspended', 'Abandoned', 'ExtraTime'},
                        'finished': bool(done), 'provisional': False,
                        'result': ('H' if hg > ag else 'A' if ag > hg else 'D') if done else None,
                        'competition': '西甲', 'season': catalogue['season'], 'source': url,
                        'round': int(data['gameweek']['week']), 'status': status})
    return matches


def refresh_laliga_live() -> dict:
    folder = league_path(PUBLIC, 'laliga')
    catalogue = read_json(folder / 'data.json')
    path = folder / 'live.json'
    now = datetime.now(timezone.utc)
    previous = read_json(path) if path.exists() else {}
    current = page_data(RESULTS_URL)
    current_rows = parse_round(current, catalogue, RESULTS_URL)
    season_slug = catalogue['season'].replace('/', '-')
    previous_full = previous.get('scheduleCheckedAt')
    full = previous.get('season') != catalogue['season'] or not previous_full or now - datetime.fromisoformat(previous_full) > timedelta(hours=1)
    rounds = set(range(1, 39)) if full else {m['round'] for m in previous.get('matches', [])
        if not m['finished'] and (m.get('started') or (m['date'] and m['date'] <= (now + timedelta(days=2)).date().isoformat()))}
    rounds.discard(int(current['gameweek']['week']))
    rows = [] if full else previous.get('matches', [])
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [(f'{RESULTS_URL}/{season_slug}/jornada-{week}',
                  pool.submit(page_data, f'{RESULTS_URL}/{season_slug}/jornada-{week}')) for week in sorted(rounds)]
        refreshed = current_rows[:]
        for url, future in tasks:
            refreshed += parse_round(future.result(), catalogue, url)
    by_id = {row['fixtureId']: row for row in rows}
    by_id.update({row['fixtureId']: row for row in refreshed})
    matches = list(by_id.values())
    if len(matches) != 380 or len({(m['home'], m['away']) for m in matches}) != 380:
        raise OSError('Incomplete season fixture coverage')
    snapshot = {'version': 1, 'league': 'laliga', 'competition': '西甲', 'season': catalogue['season'],
                'updatedAt': now.isoformat(), 'refreshSeconds': 60, 'source': RESULTS_URL,
                'scheduleCheckedAt': now.isoformat() if full else previous_full, 'matches': matches}
    LiveSnapshot.model_validate(snapshot)
    publish(path, snapshot)
    return snapshot
