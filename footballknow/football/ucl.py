"""Champions League coverage with stable event identities and 90-minute scores."""
import csv
import io
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .files import PUBLIC, publish, read_json, fetch_text
from .laliga import squad, historical_rows
from .history import CLUB_ALIASES
from .leagues import league_path
from .live import LiveSnapshot

ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions'
STANDINGS = 'https://site.api.espn.com/apis/v2/sports/soccer/uefa.champions/standings'
OFFICIAL = 'https://www.uefa.com/uefachampionsleague/fixtures-results/'
# ESPN identity, Chinese name, English article, domestic competition.
CLUBS = {
    887: ('雅典AEK', 'AEK Athens F.C.', 'gre.1'),
    104: ('罗马', 'AS Roma', 'ita.1'),
    359: ('阿森纳', 'Arsenal F.C.', 'eng.1'),
    362: ('阿斯顿维拉', 'Aston Villa F.C.', 'eng.1'),
    1068: ('马德里竞技', 'Atlético Madrid', 'esp.1'),
    83: ('巴塞罗那', 'FC Barcelona', 'esp.1'),
    132: ('拜仁慕尼黑', 'FC Bayern Munich', 'ger.1'),
    2980: ('博德闪耀', 'FK Bodø/Glimt', 'nor.1'),
    124: ('多特蒙德', 'Borussia Dortmund', 'ger.1'),
    570: ('布鲁日', 'Club Brugge KV', 'bel.1'),
    2572: ('科莫', 'Como 1907', 'ita.1'),
    437: ('波尔图', 'FC Porto', 'por.1'),
    436: ('费内巴切', 'Fenerbahçe S.K. (football)', 'tur.1'),
    142: ('费耶诺德', 'Feyenoord', 'ned.1'),
    432: ('加拉塔萨雷', 'Galatasaray S.K. (football)', 'tur.1'),
    110: ('国际米兰', 'Inter Milan', 'ita.1'),
    4411: ('林茨', 'LASK', 'aut.1'),
    175: ('朗斯', 'RC Lens', 'fra.1'),
    166: ('里尔', 'Lille OSC', 'fra.1'),
    364: ('利物浦', 'Liverpool F.C.', 'eng.1'),
    382: ('曼城', 'Manchester City F.C.', 'eng.1'),
    360: ('曼联', 'Manchester United F.C.', 'eng.1'),
    114: ('那不勒斯', 'SSC Napoli', 'ita.1'),
    148: ('埃因霍温', 'PSV Eindhoven', 'ned.1'),
    160: ('巴黎圣日耳曼', 'Paris Saint-Germain FC', 'fra.1'),
    11420: ('RB莱比锡', 'RB Leipzig', 'ger.1'),
    244: ('皇家贝蒂斯', 'Real Betis', 'esp.1'),
    86: ('皇家马德里', 'Real Madrid CF', 'esp.1'),
    21922: ('萨巴赫', 'Sabah FC (Azerbaijan)', 'aze.1'),
    493: ('顿涅茨克矿工', 'FC Shakhtar Donetsk', 'ukr.1'),
    494: ('布拉格斯拉维亚', 'SK Slavia Prague', 'cze.1'),
    521: ('布拉迪斯拉发', 'ŠK Slovan Bratislava', 'svk.1'),
    2250: ('葡萄牙体育', 'Sporting CP', 'por.1'),
    134: ('斯图加特', 'VfB Stuttgart', 'ger.1'),
    510: ('维京', 'Viking FK', 'nor.1'),
    102: ('比利亚雷亚尔', 'Villarreal CF', 'esp.1'),
}
COMPETITIONS = {'eng.1': '英超', 'esp.1': '西甲', 'ger.1': '德甲', 'ita.1': '意甲',
    'fra.1': '法甲', 'ned.1': '荷甲', 'por.1': '葡超', 'tur.1': '土超', 'bel.1': '比甲',
    'aut.1': '奥甲', 'nor.1': '挪超', 'gre.1': '希超', 'ukr.1': '乌超',
    'cze.1': '捷甲', 'svk.1': '斯洛伐克超', 'aze.1': '阿塞超', 'uefa.champions': '欧冠',
    'uefa.europa': '欧联', 'uefa.europa.conf': '欧协联'}
STAGES = {'league-phase': '联赛阶段', 'group-stage': '小组赛',
    'knockout-round-playoffs': '淘汰赛附加赛', 'round-of-16': '十六强',
    'quarterfinals': '四分之一决赛', 'semifinals': '半决赛', 'final': '决赛'}


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise OSError('ESPN response exceeds size limit')
    return json.loads(raw)


def current_clubs() -> tuple[str, list[dict]]:
    league = fetch_json(ESPN + '/teams?limit=100')['sports'][0]['leagues'][0]
    year = int(league['season']['year'])
    table = fetch_json(f'{STANDINGS}?season={year}')
    phases = [g['standings'] for g in table.get('children', [])
              if g.get('name') == 'League Phase' and g.get('standings', {}).get('season') == year]
    if len(phases) != 1 or len(phases[0].get('entries', [])) != 36:
        raise OSError('Current Champions League phase table is incomplete')
    active = {int(row['team']['id']) for row in phases[0]['entries']}
    teams = []
    for entry in league['teams']:
        row = entry['team']
        code = int(row['id'])
        if code not in active:
            continue
        if code not in CLUBS:
            raise OSError('New Champions League club needs an explicit name mapping')
        cn, article, domestic = CLUBS[code]
        color = '#' + row.get('color', '164d3d')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color) or color.lower() in {'#ffffff', '#ffff00'}:
            color = '#47564d'
        teams.append({'id': code, 'code': code, 'espnId': code, 'name': row['displayName'],
                      'cn': cn, 'short': row['abbreviation'], 'color': color,
                      'article': article, 'domestic': domestic, 'source': ESPN + '/teams?limit=100'})
    if {t['id'] for t in teams} != active or len(teams) != 36:
        raise OSError('Expected 36 distinct league-phase clubs')
    return f'{year}/{str(year + 1)[2:]}', teams


def score_value(value) -> int | None:
    if isinstance(value, dict):
        value = value.get('value')
    try:
        number = float(value)
        return int(number) if number.is_integer() and 0 <= number <= 99 and not isinstance(value, bool) else None
    except (TypeError, ValueError):
        return None


def regulation_scores(competition: dict, status: dict) -> tuple[int | None, int | None]:
    sides = {row['homeAway']: row for row in competition['competitors']}
    scores = tuple(score_value(sides[key].get('score')) for key in ('home', 'away'))
    extra = status.get('period', 0) > 2 or any(word in status.get('type', {}).get('name', '') for word in ('AET', 'PENALT'))
    if not extra or None in scores:
        return scores
    halves = [row.get('linescores', [])[:2] for row in (sides['home'], sides['away'])]
    if all(len(rows) == 2 and all(score_value(row) is not None for row in rows) for rows in halves):
        return tuple(sum(score_value(row) for row in rows) for rows in halves)
    # Only reconstruct regulation time when the complete goal timeline reconciles
    # with the match score. Shoot-outs and two-leg aggregate totals are excluded.
    goals = [row for row in competition.get('details', []) if row.get('scoringPlay') and not row.get('shootout')]
    total, normal = Counter(), Counter()
    for goal in goals:
        team = str(goal.get('team', {}).get('id', ''))
        minute = goal.get('clock', {}).get('value')
        value = score_value(goal.get('scoreValue', 1))
        if minute is None or value is None:
            return None, None
        total[team] += value
        display_clock = str(goal.get('clock', {}).get('displayValue', ''))
        if minute <= 5400 or re.match(r"^90['’]?\s*\+", display_clock):
            normal[team] += value
    ids = [str(sides[key]['id']) for key in ('home', 'away')]
    if tuple(total[key] for key in ids) != scores:
        return None, None
    return tuple(normal[key] for key in ids)


def odds_rows(competition: dict) -> list[dict]:
    found = []
    for row in competition.get('odds', []) or []:
        if not isinstance(row, dict):
            continue
        try:
            values = {'H': float(row['homeTeamOdds']['odds']['value']),
                      'D': float(row['drawOdds']['value']), 'A': float(row['awayTeamOdds']['odds']['value'])}
            if all(1 < v <= 10000 for v in values.values()):
                found.append({'label': f'ESPN · {row.get("provider", {}).get("name", "来源赔率")} · 采集快照', **values})
        except (KeyError, TypeError, ValueError):
            continue
    return found


def event_row(event: dict, url: str, *, competition: str = '欧冠', names: dict | None = None) -> dict:
    game = event['competitions'][0]
    sides = {row['homeAway']: row for row in game['competitors']}
    if set(sides) != {'home', 'away'}:
        raise OSError('Fixture has incomplete competitors')
    status = game.get('status') or event.get('status') or {}
    state = status.get('type', {})
    completed = bool(state.get('completed'))
    cancelled = any(word in state.get('name', '') for word in ('POSTPONED', 'CANCELED', 'CANCELLED', 'ABANDONED'))
    home, away = [((names or {}).get(int(sides[key]['id'])) or sides[key]['team']['displayName']) for key in ('home', 'away')]
    hg, ag = regulation_scores(game, status)
    done = completed and not cancelled and hg is not None and ag is not None
    year = int(event['season']['year'])
    slug = event.get('season', {}).get('slug') or event.get('seasonType', {}).get('name', '')
    phase = STAGES.get(slug, {'League Phase':'联赛阶段', 'Round of 16':'十六强', 'Quarterfinals':'四分之一决赛',
                            'Semifinals':'半决赛', 'Final':'决赛', 'Knockout Round Playoffs':'淘汰赛附加赛'}.get(slug, slug))
    date = event['date'][:10]
    kickoff = event['date'] if event.get('timeValid', game.get('timeValid', True)) and not cancelled else None
    display_season = event['season'].get('displayName', '')
    season = str(year) if competition != '欧冠' and re.match(r'^\d{4} ', display_season) else f'{year}/{str(year + 1)[2:]}'
    return {'id': f'espn:{event["id"]}', 'fixtureId': int(event['id']), 'date': date, 'kickoff': kickoff,
            'home': home, 'away': away, 'homeGoals': hg, 'awayGoals': ag,
            'started': not cancelled and state.get('state') in {'in', 'post'}, 'finished': bool(done),
            'completed': completed, 'provisional': completed and not done and not cancelled,
            'result': ('H' if hg > ag else 'A' if ag > hg else 'D') if done else None,
            'competition': competition, 'season': season,
            'source': url, 'phase': phase, 'neutral': bool(game.get('neutralSite')),
            'scoreScope': '90 分钟含补时', 'status': state.get('name', ''),
            'fullTimeScore': [score_value(sides[k].get('score')) for k in ('home', 'away')],
            'odds': odds_rows(game)}


def annual_matches(year: int, names: dict) -> tuple[str, list[dict]]:
    url = f'{ESPN}/scoreboard?dates={year}&limit=1000'
    data = fetch_json(url)
    events = data.get('events')
    if not isinstance(events, list) or len(events) >= 1000:
        raise OSError('Champions League calendar response incomplete')
    return url, [event_row(e, url, names=names) for e in events]


def validate_schedule(rows: list[dict], teams: list[dict], season: str) -> None:
    members = {t['name'] for t in teams}
    if len({r['fixtureId'] for r in rows}) != len(rows) or any(
            r['season'] != season or r['competition'] != '欧冠' or r['home'] not in members
            or r['away'] not in members or r['home'] == r['away'] for r in rows):
        raise OSError('Champions League fixtures do not match the current participants')
    phase = [r for r in rows if r.get('phase') == '联赛阶段']
    counts = Counter(team for r in phase for team in (r['home'], r['away']))
    if len(phase) != 144 or set(counts) != members or any(v != 8 for v in counts.values()):
        raise OSError('Expected complete 144-match, eight-per-club league phase')


def club_recent(team: dict, year: int, names: dict) -> tuple[list[dict], list[dict]]:
    matches, sources = [], []
    for y in [year, year - 1, year - 2, year - 3]:
        if y <= year - 2 and len(matches) >= 20:
            break
        url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{team["id"]}/schedule?season={y}'
        data = fetch_json(url)
        if str(data.get('team', {}).get('id')) != str(team['id']):
            raise OSError('Team history identity mismatch')
        for event in data.get('events', []):
            game = event['competitions'][0]
            score = game['competitors'][0].get('score', {})
            ref = score.get('$ref', '') if isinstance(score, dict) else ''
            code = re.search(r'/leagues/([^/]+)/', ref)
            key = code.group(1) if code else ''
            label = event.get('season', {}).get('displayName', '')
            if 'friendly' in key.lower() or 'friendly' in label.lower() or 'gamper' in label.lower():
                continue
            # Current and previous Champions League results come from the full
            # scoreboard, which has the goal timeline required for extra time.
            if key == 'uefa.champions':
                continue
            row = event_row(event, url, competition=COMPETITIONS.get(key, label or '其他正式赛事'), names=names)
            if row['finished']:
                matches.append(row)
        sources.append({'name': f'ESPN · {team["cn"]} {y} 正式比赛', 'url': url,
                        'fetchedAt': datetime.now(timezone.utc).isoformat()})
    return matches, sources


def historical_odds(matches: list[dict], year: int) -> list[dict]:
    def name_key(name):
        name = CLUB_ALIASES.get(name, name)
        key = re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', name).casefold())
        return {'internazionale':'inter', 'parissaintgermain':'parissg', 'asroma':'roma',
                'bayernmunich':'bayernmunich', 'feyenoordrotterdam':'feyenoord',
                'psveindhoven':'psv', 'fcporto':'porto', 'sportingcp':'sporting',
                'vfb stuttgart':'stuttgart', 'vfbstuttgart':'stuttgart', 'athleticclub':'athbilbao'}.get(key,key)
    index = {(m['date'], name_key(m['home']), name_key(m['away'])):m for m in matches if m['finished']}
    tasks = [(f'https://www.football-data.co.uk/mmz4281/{y%100:02}{(y+1)%100:02}/{code}.csv',y,label)
             for y in [year-1,year] for code,label in [('E0','英超'),('SP1','西甲'),('D1','德甲'),('I1','意甲'),
             ('F1','法甲'),('N1','荷甲'),('P1','葡超'),('B1','比甲'),('T1','土超'),('G1','希超')]]
    sources = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [(url,y,label,pool.submit(fetch_text,url)) for url,y,label in tasks]
        for url,y,label,future in futures:
            try:
                raw = future.result()
                clubs = {r.get('HomeTeam','') for r in csv.DictReader(io.StringIO(raw))}
                rows = historical_rows(raw,url,y,label,clubs)
                for row in rows:
                    target = index.get((row['date'],name_key(row['home']),name_key(row['away'])))
                    if target and target['competition']==label and (target['homeGoals'],target['awayGoals'])==(row['homeGoals'],row['awayGoals']) and row['odds']:
                        target['odds'],target['oddsSource'] = row['odds'],url
                sources.append({'name':f'Football-Data · {y} {label}历史赔率','url':url,'fetchedAt':datetime.now(timezone.utc).isoformat()})
            except (OSError,ValueError,KeyError):
                pass
    return sources


def scheduled_odds(team: dict, year: int, names: dict) -> tuple[str,list[dict]]:
    url = f'{ESPN}/teams/{team["id"]}/schedule?season={year}&fixture=true'
    data = fetch_json(url)
    if str(data.get('team',{}).get('id'))!=str(team['id']):
        raise OSError('Odds schedule team identity mismatch')
    return url,[event_row(e,url,names=names) for e in data.get('events',[])]


def refresh_catalogue() -> dict:
    folder = league_path(PUBLIC, 'ucl')
    season, teams = current_clubs()
    year = int(season[:4])
    names = {t['id']: t['name'] for t in teams}
    previous = read_json(folder / 'data.json') if (folder / 'data.json').exists() else {}
    now = datetime.now(timezone.utc).isoformat()
    players, matches, warnings = [], [], []
    sources = [{'name': 'ESPN · 欧冠本赛季参赛队', 'url': ESPN + '/teams?limit=100', 'fetchedAt': now},
               {'name': 'ESPN · 联赛阶段参赛名单核对', 'url': f'{STANDINGS}?season={year}', 'fetchedAt': now}]
    with ThreadPoolExecutor(max_workers=4) as pool:
        roster_tasks = [(team, pool.submit(squad, team, season, ESPN)) for team in teams]
        for team, future in roster_tasks:
            url = f'{ESPN}/teams/{team["id"]}/roster'
            try:
                players += future.result()
                sources.append({'name': f'ESPN · {team["cn"]}球员', 'url': url, 'fetchedAt': now})
            except (OSError, ValueError, KeyError):
                retained = [p for p in previous.get('players', []) if p['team'] == team['id']]
                if previous.get('season') != season or not retained:
                    raise OSError(f'{team["cn"]} roster unavailable; previous catalogue retained') from None
                players += retained
                sources += [s for s in previous.get('sources', []) if s['url'] == url]
                warnings.append(f'{team["cn"]}名单沿用上次快照')
        calendars = [pool.submit(annual_matches, y, names) for y in [year - 1, year, year + 1]]
        for task in calendars:
            url, rows = task.result()
            matches += rows
            sources.append({'name': 'ESPN · 欧冠赛程与赛果', 'url': url, 'fetchedAt': now})
        recent_tasks = [(team, pool.submit(club_recent, team, year, names)) for team in teams]
        for team, task in recent_tasks:
            try:
                rows, source_rows = task.result()
                matches += rows
                sources += source_rows
            except (OSError, ValueError, KeyError):
                retained = [r for r in previous.get('matches', []) if r['competition'] != '欧冠'
                            and team['name'] in (r['home'], r['away'])]
                matches += retained
                warnings.append(f'{team["cn"]}其他正式比赛资料待更新')
    if len({p['code'] for p in players}) != len(players):
        raise OSError('Duplicate player identities in the Champions League roster')
    by_id = {row['id']: row for row in matches}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(scheduled_odds,t,year,names) for t in teams]
        for future in futures:
            try:
                url, rows = future.result()
                for row in rows:
                    if row['id'] in by_id and row['odds']:
                        by_id[row['id']]['odds'] = row['odds']
                        by_id[row['id']]['oddsSource'] = url
                sources.append({'name':'ESPN · 欧冠赛前三项赔率快照','url':url,'fetchedAt':now})
            except (OSError,ValueError,KeyError):
                warnings.append('部分欧冠赔率来源暂未更新')
    matches = list(by_id.values())
    sources += historical_odds(matches,year)
    previous_odds = {m['id']:m for m in previous.get('matches',[]) if m.get('odds')}
    for row in matches:
        if not row['odds'] and row['id'] in previous_odds:
            row['odds'] = previous_odds[row['id']]['odds']
            row['oddsSource'] = previous_odds[row['id']].get('oddsSource')
    current = [r for r in matches if r['season'] == season and r['competition'] == '欧冠']
    validate_schedule(current, teams, season)
    snapshot = {'version': 1, 'league': 'ucl', 'competition': '欧冠', 'season': season,
                'updatedAt': now, 'teams': teams, 'players': players,
                'matches': sorted(matches, key=lambda r: (r['date'], r['id']), reverse=True),
                'warnings': warnings, 'sources': sources,
                'scope': '联赛阶段36队；最近20场已收录正式比赛，可跨赛事、赛季；比分与分析为90分钟，不含加时与点球。'}
    publish(folder / 'data.json', snapshot)
    return snapshot


def refresh_live() -> dict:
    folder = league_path(PUBLIC, 'ucl')
    catalogue = read_json(folder / 'data.json')
    path = folder / 'live.json'
    previous = read_json(path) if path.exists() else {}
    now = datetime.now(timezone.utc)
    year = int(catalogue['season'][:4])
    names = {t['id']: t['name'] for t in catalogue['teams']}
    checked = previous.get('scheduleCheckedAt')
    full = previous.get('season') != catalogue['season'] or not checked or now - datetime.fromisoformat(checked) > timedelta(hours=1)
    if full:
        with ThreadPoolExecutor(max_workers=2) as pool:
            rows = [row for _, batch in pool.map(lambda y: annual_matches(y, names), [year, year + 1]) for row in batch
                    if row['season'] == catalogue['season']]
    else:
        rows = previous.get('matches', [])
        dates = {(now + timedelta(days=d)).strftime('%Y%m%d') for d in [-1, 0, 1]}
        dates.update(r['date'].replace('-', '') for r in rows if r['started'] and not r['finished'])
        by_id = {r['fixtureId']: r for r in rows}
        with ThreadPoolExecutor(max_workers=3) as pool:
            urls = [f'{ESPN}/scoreboard?dates={date}&limit=1000' for date in sorted(dates)]
            for url, data in zip(urls, pool.map(fetch_json, urls)):
                for event in data.get('events', []):
                    row = event_row(event, url, names=names)
                    if row['season'] == catalogue['season']:
                        old = by_id.get(row['fixtureId'], {})
                        if not row.get('phase'):
                            row['phase'] = old.get('phase', '')
                        by_id[row['fixtureId']] = row
        rows = list(by_id.values())
    validate_schedule(rows, catalogue['teams'], catalogue['season'])
    snapshot = {'version': 1, 'league': 'ucl', 'competition': '欧冠', 'season': catalogue['season'],
                'updatedAt': now.isoformat(), 'refreshSeconds': 60, 'source': ESPN + '/scoreboard',
                'scheduleCheckedAt': now.isoformat() if full else checked, 'matches': rows}
    LiveSnapshot.model_validate(snapshot)
    publish(path, snapshot)
    return snapshot
