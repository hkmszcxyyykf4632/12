"""Independent, dated pre-match references when the live source is unavailable."""
import csv
import hashlib
import io
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from .files import STATE, USER_AGENT, publish
from .match_details import canonical
from .match_research import load, streak
from .market_odds import historical_markets
from .motivation import dt

FIXTURES = 'https://football-data.co.uk/fixtures.csv'
DIVISIONS = {'700': ('E0', 'epl'), '740': ('SP1', 'laliga'), '730': ('I1', 'seriea'),
             '720': ('D1', 'bundesliga'), '710': ('F1', 'ligue1')}
ALIASES = {'spurs': 'tottenham', 'ipswichtown': 'ipswich', 'coventrycity': 'coventry',
           'lehavreac': 'lehavre', 'parissaintgermain': 'parissg', 'asmonaco': 'monaco',
           'ajauxerre': 'auxerre', 'stadebrestois29': 'brest'}


def team_key(name, league):
    value = canonical(name, league)
    return ALIASES.get(value, value)


def csv_snapshot(url, at):
    path = STATE / 'forecast-reference' / (hashlib.sha256(url.encode()).hexdigest() + '.json')
    old = load(path)
    stamp = dt(old.get('fetchedAt'))
    if stamp and timedelta(0) <= at - stamp < timedelta(minutes=5):
        return old
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/csv'})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
        modified = response.headers.get('Last-Modified')
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('Reference file exceeds size limit')
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    if not rows or not {'Div', 'Date', 'HomeTeam', 'AwayTeam'}.issubset(rows[0]):
        raise ValueError('Reference columns missing')
    published = parsedate_to_datetime(modified).astimezone(timezone.utc).isoformat() if modified else None
    result = {'source': url, 'fetchedAt': at.isoformat(), 'sourceUpdatedAt': published, 'rows': rows}
    publish(path, result)
    return result


def kickoff(record):
    value = datetime.strptime(record['Date'] + ' ' + record['Time'], '%d/%m/%Y %H:%M')
    return value.replace(tzinfo=ZoneInfo('Europe/London')).astimezone(timezone.utc)


def match_fixture(row, snapshot, at):
    division, league = DIVISIONS[str(row['competitionId'])]
    fetched, published = dt(snapshot.get('fetchedAt')), dt(snapshot.get('sourceUpdatedAt'))
    if (not fetched or not published or not timedelta(0) <= at - fetched <= timedelta(minutes=10)
            or not timedelta(0) <= at - published <= timedelta(days=7)):
        raise ValueError('Reference publication time unavailable or stale')
    choices = []
    for record in snapshot['rows']:
        try:
            if (record.get('Div') == division and kickoff(record) == dt(row['kickoff'])
                    and all(team_key(record[k], league) == team_key(row['teams'][s]['name'], league)
                            for s, k in [('home', 'HomeTeam'), ('away', 'AwayTeam')])
                    and not any(record.get(k) for k in ['FTHG', 'FTAG', 'FTR'])):
                choices.append(record)
        except (ValueError, KeyError, TypeError):
            continue
    if len(choices) != 1 or not at < dt(row['kickoff']):
        raise ValueError('Reference fixture is not a unique matching future event')
    return choices[0]


def history(records, own_name, league, cutoff, source):
    rows = {}
    division = next(d for d, l in DIVISIONS.values() if l == league)
    for record in records:
        try:
            if record.get('Div') != division:
                continue
            date = kickoff(record)
            home, away = record['HomeTeam'], record['AwayTeam']
            sides = [s for s, name in [('home', home), ('away', away)] if team_key(name, league) == team_key(own_name, league)]
            if len(sides) != 1 or date >= cutoff:
                continue
            goals = [int(record[k]) for k in ['FTHG', 'FTAG']]
            if not all(0 <= n <= 20 for n in goals) or record.get('FTR') != ('H' if goals[0] > goals[1] else 'A' if goals[0] < goals[1] else 'D'):
                continue
            side = sides[0]
            own, other = goals if side == 'home' else goals[::-1]
            key = (date.isoformat(), home, away)
            rows[key] = {'date': date.isoformat(), 'homeAway': side, 'opponent': away if side == 'home' else home,
                         'goalsFor': own, 'goalsAgainst': other, 'result': 'W' if own > other else 'L' if own < other else 'D',
                         'competition': record['Div'], 'scope': '90分钟含补时', 'source': source}
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(rows.values(), key=lambda r: r['date'], reverse=True)[:10]


def initial_reference(row, at):
    fixture_file = csv_snapshot(FIXTURES, at)
    record = match_fixture(row, fixture_file, at)
    division, league = DIVISIONS[str(row['competitionId'])]
    start = dt(row['kickoff']).year - int(dt(row['kickoff']).month < 7)
    sources, teams = [], {}
    for year in [start, start - 1]:
        url = f'https://football-data.co.uk/mmz4281/{year % 100:02}{(year + 1) % 100:02}/{division}.csv'
        saved = csv_snapshot(url, at)
        sources.append({k: saved[k] for k in ['source', 'fetchedAt', 'sourceUpdatedAt']})
        for side in ['home', 'away']:
            own = row['teams'][side]
            rows = history(saved['rows'], own['name'], league, min(at, dt(row['kickoff'])), url)
            older = teams.get(side, {}).get('form', {}).get('matches', [])
            combined = sorted(older + rows, key=lambda r: r['date'], reverse=True)[:10]
            teams[side] = {'teamId': own['id'], 'name': own['label'], 'form': streak(combined),
                           'lineup': {'confirmed': False, 'players': []}, 'comparisons': {},
                           'errors': ['备用来源仅含联赛往绩；正式首发、伤停和天气待核对']}
        if all(len(t['form']['matches']) >= 10 for t in teams.values()):
            break
    quotes = [q for q in historical_markets(record, FIXTURES, fixture_file['fetchedAt'])
              if q['market'] == 'asian-handicap' and q['phase'] == 'preclosing']
    quotes.sort(key=lambda q: (q['provider'] != 'Bet365', q['provider'] != '市场平均', q['provider']))
    quote = {**quotes[0], 'sourceUpdatedAt': fixture_file['sourceUpdatedAt'],
             'timing': '赛前参考报价，非即时盘口；文件更新时间不是逐笔报价时间'} if quotes else None
    research = {'eventId': row['id'], 'kickoff': row['kickoff'], 'teams': teams,
                'pregame': {'capturedAt': fixture_file['fetchedAt']}, 'source': FIXTURES,
                'weather': {'status': '备用来源不含赛前天气'}, 'historySources': sources}
    return {'research': research, 'quote': quote, 'source': FIXTURES,
            'checkedAt': fixture_file['fetchedAt'], 'sourceUpdatedAt': fixture_file['sourceUpdatedAt'],
            'note': '即时来源未更新，本版按已核对赛程、联赛往绩及赛前参考报价生成；报价非即时，正式首发待确认。'}
