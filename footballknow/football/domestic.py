"""Serie A and Bundesliga feeds, with explicit club identities and complete seasons."""
import re
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .files import PUBLIC, fetch_text, publish, read_json
from .history import HistorySnapshot, SourceStatus, collect_managers
from .laliga import historical_rows, squad
from .leagues import league_config, league_path
from .names import PlayerName, refresh_names
from .name_rosters import refresh_club_names
from .ucl import event_row, fetch_json
from .ucl_history import club_aliases, club_transfers, normalized

BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer'
CONFIG = {
    'seriea': {'code': 'ita.1', 'lower': 'ita.2', 'csv': ('I1', 'I2'), 'count': 20, 'article': 'Serie_A'},
    'bundesliga': {'code': 'ger.1', 'lower': 'ger.2', 'csv': ('D1', 'D2'), 'count': 18, 'article': 'Bundesliga'},
}
# ESPN identity: historical CSV name, Chinese name, article, alternative source names.
CLUBS = {
    103: ('Milan', 'AC米兰', 'AC Milan', ('AC Milan',)),
    104: ('Roma', '罗马', 'AS Roma', ('AS Roma',)),
    105: ('Atalanta', '亚特兰大', 'Atalanta BC', ()),
    107: ('Bologna', '博洛尼亚', 'Bologna FC 1909', ()),
    2925: ('Cagliari', '卡利亚里', 'Cagliari Calcio', ()),
    2572: ('Como', '科莫', 'Como 1907', ()),
    109: ('Fiorentina', '佛罗伦萨', 'ACF Fiorentina', ()),
    4057: ('Frosinone', '弗罗西诺内', 'Frosinone Calcio', ()),
    3263: ('Genoa', '热那亚', 'Genoa CFC', ()),
    110: ('Inter', '国际米兰', 'Inter Milan', ('Internazionale',)),
    111: ('Juventus', '尤文图斯', 'Juventus FC', ()),
    112: ('Lazio', '拉齐奥', 'SS Lazio', ()),
    113: ('Lecce', '莱切', 'US Lecce', ()),
    4007: ('Monza', '蒙扎', 'AC Monza', ()),
    114: ('Napoli', '那不勒斯', 'SSC Napoli', ()),
    115: ('Parma', '帕尔马', 'Parma Calcio 1913', ()),
    3997: ('Sassuolo', '萨索洛', 'US Sassuolo Calcio', ()),
    239: ('Torino', '都灵', 'Torino FC', ()),
    118: ('Udinese', '乌迪内斯', 'Udinese Calcio', ()),
    17530: ('Venezia', '威尼斯', 'Venezia FC', ()),
    598: ('Union Berlin', '柏林联合', '1. FC Union Berlin', ('1. FC Union Berlin',)),
    131: ('Leverkusen', '勒沃库森', 'Bayer 04 Leverkusen', ('Bayer Leverkusen',)),
    132: ('Bayern Munich', '拜仁慕尼黑', 'FC Bayern Munich', ('Bayern München',)),
    124: ('Dortmund', '多特蒙德', 'Borussia Dortmund', ('Borussia Dortmund',)),
    268: ("M'gladbach", '门兴格拉德巴赫', 'Borussia Mönchengladbach', ('Borussia Monchengladbach',)),
    125: ('Ein Frankfurt', '法兰克福', 'Eintracht Frankfurt', ('Eintracht Frankfurt',)),
    3841: ('Augsburg', '奥格斯堡', 'FC Augsburg', ('FC Augsburg',)),
    122: ('FC Koln', '科隆', '1. FC Köln', ('FC Cologne', 'FC Köln', 'Cologne')),
    127: ('Hamburg', '汉堡', 'Hamburger SV', ('Hamburg SV',)),
    2950: ('Mainz', '美因茨', '1. FSV Mainz 05', ('Mainz 05',)),
    11420: ('RB Leipzig', 'RB莱比锡', 'RB Leipzig', ()),
    126: ('Freiburg', '弗赖堡', 'SC Freiburg', ('SC Freiburg',)),
    3307: ('Paderborn', '帕德博恩', 'SC Paderborn 07', ('SC Paderborn 07',)),
    10388: ('Elversberg', '艾禾斯堡', 'SV Elversberg', ('SV Elversberg',)),
    133: ('Schalke 04', '沙尔克04', 'FC Schalke 04', ('Schalke',)),
    7911: ('Hoffenheim', '霍芬海姆', 'TSG 1899 Hoffenheim', ('TSG Hoffenheim',)),
    134: ('Stuttgart', '斯图加特', 'VfB Stuttgart', ('VfB Stuttgart',)),
    137: ('Werder Bremen', '云达不来梅', 'SV Werder Bremen', ()),
}
ALIASES = {normalized(alias): row[0] for row in CLUBS.values() for alias in (row[0], row[2], *row[3])}


def canonical_name(name):
    return ALIASES.get(normalized(name), name)


def current_clubs(league):
    config = CONFIG[league]
    url = f'{BASE}/{config["code"]}/teams?limit=100'
    source = fetch_json(url)['sports'][0]['leagues'][0]
    year = int(source['season']['year'])
    table = fetch_json(f'https://site.api.espn.com/apis/v2/sports/soccer/{config["code"]}/standings?season={year}')
    tables = [c['standings'] for c in table.get('children', []) if c.get('standings', {}).get('season') == year]
    if len(tables) != 1 or len(tables[0].get('entries', [])) != config['count']:
        raise OSError('Current domestic table is incomplete')
    active = {int(r['team']['id']) for r in tables[0]['entries']}
    teams = []
    for entry in source['teams']:
        row = entry['team']
        code = int(row['id'])
        if code not in active:
            continue
        if code not in CLUBS:
            raise OSError('New club needs a verified source-name mapping')
        name, cn, article, _ = CLUBS[code]
        color = '#' + row.get('color', '164d3d')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color) or color.lower() in {'#ffffff', '#ffff00'}:
            color = '#47564d'
        teams.append({'id': code, 'code': code, 'espnId': code, 'name': name, 'cn': cn,
                      'short': row['abbreviation'], 'color': color, 'article': article,
                      'domestic': config['code'], 'source': url})
    if len(teams) != config['count'] or {t['id'] for t in teams} != active:
        raise OSError('Club identities do not match the current table')
    return f'{year}/{str(year + 1)[2:]}', teams


def refresh_catalogue(league):
    config, label = CONFIG[league], league_config(league)
    folder = league_path(PUBLIC, league)
    season, teams = current_clubs(league)
    previous = read_json(folder / 'data.json') if (folder / 'data.json').exists() else {}
    stamp = datetime.now(timezone.utc).isoformat()
    warnings, players, matches = [], [], []
    sources = [{'name': f'ESPN · {label.competition}本赛季球队', 'url': teams[0]['source'], 'fetchedAt': stamp}]
    endpoint = f'{BASE}/{config["code"]}'
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [(team, pool.submit(squad, team, season, endpoint)) for team in teams]
        for team, future in futures:
            url = f'{endpoint}/teams/{team["id"]}/roster'
            try:
                players += future.result()
                sources.append({'name': f'ESPN · {team["cn"]}球员', 'url': url, 'fetchedAt': stamp})
            except (OSError, ValueError, KeyError):
                retained = [p for p in previous.get('players', []) if p['team'] == team['id']]
                if previous.get('season') != season or not retained:
                    raise OSError(f'Roster unavailable: {team["name"]}') from None
                players += retained
                sources += [s for s in previous.get('sources', []) if s['url'] == url]
                warnings.append(f'{team["cn"]}球员资料沿用上次快照')
    if len({p['code'] for p in players}) != len(players):
        raise OSError('Duplicate player identities in domestic rosters')
    clubs, year = {t['name'] for t in teams}, int(season[:4])
    for y in [year, year - 1]:
        for division, competition in zip(config['csv'], (label.competition, label.lower)):
            url = f'https://www.football-data.co.uk/mmz4281/{y % 100:02}{(y + 1) % 100:02}/{division}.csv'
            try:
                matches += historical_rows(fetch_text(url), url, y, competition, clubs)
                sources.append({'name': f'{y} {competition} · 赛果与历史赔率', 'url': url, 'fetchedAt': stamp})
            except (OSError, ValueError):
                matches += [m for m in previous.get('matches', []) if m.get('source') == url]
                sources += [s for s in previous.get('sources', []) if s['url'] == url]
                warnings.append(f'{y} {competition}历史资料未更新')
    if any(sum(t['name'] in (m['home'], m['away']) for m in matches) < 20 for t in teams):
        raise OSError('Fewer than twenty historical matches for a current club')
    result = {'version': 1, 'league': league, 'competition': label.competition, 'season': season,
              'updatedAt': stamp, 'teams': teams, 'players': players,
              'matches': sorted(matches, key=lambda m: (m['date'], m['id']), reverse=True),
              'warnings': warnings, 'sources': sources,
              'scope': f'最近二十场已完成{label.competition}与{label.lower}联赛，可跨赛季；球员为 ESPN 收录名单。'}
    publish(folder / 'data.json', result)
    return result


def parse_events(raw, catalogue, url):
    year, competition = int(catalogue['season'][:4]), catalogue['competition']
    names = {t['id']: t['name'] for t in catalogue['teams']}
    rows = []
    for event in raw.get('events', []):
        if event.get('season', {}).get('year') != year:
            continue
        row = event_row(event, url, competition=competition, names=names)
        row['season'], row['phase'] = catalogue['season'], ''
        status = event['competitions'][0].get('status') or event.get('status') or {}
        row['clock'] = status.get('displayClock') or None
        row['statusText'] = status.get('type', {}).get('shortDetail') or None
        rows.append(row)
    return rows


def validate_schedule(rows, catalogue, league):
    count = CONFIG[league]['count']
    names = {t['name'] for t in catalogue['teams']}
    expected = count * (count - 1)
    if len(names) != count or len(rows) != expected or len({r['id'] for r in rows}) != expected:
        raise OSError('Incomplete domestic season')
    pairs = set()
    appearances = Counter()
    for r in rows:
        if r['home'] not in names or r['away'] not in names or r['home'] == r['away']:
            raise OSError('Unexpected competitor in domestic season')
        if r['competition'] != catalogue['competition'] or r['season'] != catalogue['season']:
            raise OSError('Wrong competition or season')
        if r['finished'] and (not all(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 99
                                     for n in [r['homeGoals'], r['awayGoals']]) or r['result'] not in {'H', 'D', 'A'}):
            raise OSError('Invalid finished score')
        pairs.add((r['home'], r['away']))
        appearances.update([r['home'], r['away']])
    if len(pairs) != expected or any(n != 2 * (count - 1) for n in appearances.values()):
        raise OSError('Duplicate or missing home-away fixtures')


def refresh_live(league, full=False):
    folder, config = league_path(PUBLIC, league), CONFIG[league]
    catalogue = read_json(folder / 'data.json')
    path = folder / 'live.json'
    previous = read_json(path) if path.exists() else {}
    now = datetime.now(timezone.utc)
    checked = previous.get('scheduleCheckedAt')
    full = full or previous.get('season') != catalogue['season'] or not checked or now - datetime.fromisoformat(checked) > timedelta(hours=1)
    year = int(catalogue['season'][:4])
    dates = {str(year), str(year + 1)} if full else {(now + timedelta(days=d)).strftime('%Y%m%d') for d in (-1, 0, 1)}
    if not full:
        dates.update(m['date'].replace('-', '') for m in previous['matches'] if m['started'] and not m['finished'] and m.get('date'))
    matches = {} if full else {m['id']: m for m in previous['matches']}
    urls = [f'{BASE}/{config["code"]}/scoreboard?dates={d}&limit=1000' for d in sorted(dates)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for url, raw in zip(urls, pool.map(fetch_json, urls)):
            matches.update({m['id']: m for m in parse_events(raw, catalogue, url)})
    rows = list(matches.values())
    validate_schedule(rows, catalogue, league)
    snapshot = {'version': 1, 'league': league, 'competition': catalogue['competition'], 'season': catalogue['season'],
                'updatedAt': now.isoformat(), 'refreshSeconds': 60, 'source': f'{BASE}/{config["code"]}/scoreboard',
                'scheduleCheckedAt': now.isoformat() if full else checked, 'matches': rows}
    publish(path, snapshot)
    return snapshot


def refresh_history(league):
    folder = league_path(PUBLIC, league)
    catalogue = read_json(folder / 'data.json')
    teams, year = catalogue['teams'], int(catalogue['season'][:4])
    aliases = club_aliases(teams)
    for t in teams:
        for alias in CLUBS[t['id']][3]:
            aliases[alias] = t['name']
    clubs = {t['name'] for t in teams}
    snapshot = HistorySnapshot(updatedAt=datetime.now(timezone.utc).isoformat(), season=catalogue['season'])
    path = folder / 'history.json'
    if path.exists():
        old = HistorySnapshot.model_validate(read_json(path))
        snapshot.transfers, snapshot.managers = old.transfers, old.managers
    tasks = []
    for y in (year - 1, year):
        season = f'{y}–{str(y + 1)[2:]}'
        for team in teams:
            title = f'{season}_{team["article"].replace(" ", "_")}_season'
            tasks.append(('transfers', 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(title), team['name']))
        title = f'{season}_{CONFIG[league]["article"]}'
        tasks.append(('managers', 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(title), ''))
    def collect(task):
        kind, url, club = task
        return club_transfers(url, club, aliases) if kind == 'transfers' else collect_managers(url, clubs, aliases)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [(task, pool.submit(collect, task)) for task in tasks]
        for (kind, url, _), future in futures:
            ok = False
            try:
                rows = future.result()
                setattr(snapshot, kind, [r for r in getattr(snapshot, kind) if r.catalogueSource != url] + rows)
                ok = True
            except (OSError, ValueError, KeyError):
                pass
            snapshot.sources.append(SourceStatus(url=url, checkedAt=datetime.now(timezone.utc).isoformat(), ok=ok))
    snapshot.transfers = sorted({r.id: r for r in snapshot.transfers if {r.fromTeam, r.toTeam} & clubs}.values(), key=lambda r: r.date or r.window, reverse=True)
    snapshot.managers = sorted({r.id: r for r in snapshot.managers if r.team in clubs}.values(), key=lambda r: r.joinedAt or r.leftAt or '', reverse=True)
    if not any(s.ok for s in snapshot.sources):
        raise OSError('No domestic club history source available')
    publish(path, snapshot.model_dump(mode='json'))
    return snapshot


def refresh_localized_names(league, full=False):
    folder = league_path(PUBLIC, league)
    catalogue = read_json(folder / 'data.json')
    snapshot = refresh_names(0, league)
    def identity(p):
        return normalized(p.get('known_name') or (p['first_name'] + ' ' + p['second_name'])), p.get('birth_date')
    targets = {identity(p): p for p in catalogue['players'] if p.get('birth_date')}
    for other in ('epl', 'laliga', 'ucl', 'seriea', 'bundesliga'):
        source = league_path(PUBLIC, other)
        if other == league or not (source / 'names.json').exists():
            continue
        data, names = read_json(source / 'data.json'), read_json(source / 'names.json')
        for p in data['players']:
            target, name = targets.get(identity(p)), names['names'].get(str(p['code']))
            if target and name:
                snapshot.names[str(target['code'])] = PlayerName.model_validate({**name, 'code': target['code']})
    publish(folder / 'names.json', snapshot.model_dump(mode='json'))
    refresh_club_names(league)
    return refresh_names(1500 if full else 60, league)
