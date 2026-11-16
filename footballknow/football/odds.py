"""Provenance-preserving 90-minute quotes; homepage checks are not quote feeds."""
import csv
import io
import math
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from .files import PUBLIC, STATE, fetch_text, publish, read_json
from .odds_history import append_history
from .leagues import league_path, league_config

PROVIDERS = {
    'B365': ('Bet365', 'https://www.bet365.com/hub/en-gb/football'),
    'BFD': ('Betfred', 'https://www.betfred.com/sports/football'),
    'BV': ('BetVictor', 'https://www.betvictor.com/en-gb/sports/240'),
    'BW': ('bwin', 'https://www.bwin.com/en/sports/football-4'),
    'PP': ('Paddy Power', 'https://www.paddypower.com/football'),
    'BFE': ('Betfair Exchange', 'https://www.betfair.com/exchange/plus/en/football-betting-1/3'),
    'PS': ('Pinnacle', 'https://www.pinnacle.com/en/soccer/'),
    'WH': ('William Hill', 'https://sports.williamhill.com/betting/en-gb/football'),
}


def decimal(value):
    try:
        number = float(value)
        return number if not isinstance(value, bool) and math.isfinite(number) and 1 < number <= 10000 else None
    except (TypeError, ValueError):
        return None


def american(value):
    try:
        value = float(value)
        return decimal(1 + value / 100 if value >= 100 else 1 + 100 / abs(value) if value <= -100 else 0)
    except (TypeError, ValueError):
        return None


def historical_odds(row, source, fetched_at=None):
    result = []
    for code, (provider, official) in {'Avg': ('市场平均', ''), **PROVIDERS}.items():
        for ending, phase in [('C', '收盘'), ('', '赛前')]:
            values = {k: decimal(row.get(code + ending + k)) for k in ['H', 'D', 'A']}
            if not all(values.values()):
                continue
            result.append({'provider': provider, 'label': f'{provider} · {phase} · Football-Data',
                           'kind': 'aggregate' if code == 'Avg' else 'exchange' if code == 'BFE' else 'bookmaker',
                           'market': '90-minute-1x2', 'phase': phase, 'source': source, 'officialUrl': official,
                           'via': 'Football-Data', 'fetchedAt': fetched_at, **values})
    return result


def espn_odds(raw, event_id, fetched_at):
    rows, seen = [], set()
    game = raw.get('header', {}).get('competitions', [{}])[0]
    sides = {c['homeAway']: str(c['id']) for c in game.get('competitors', [])}
    if set(sides) != {'home', 'away'} or str(raw.get('header', {}).get('id')) != str(event_id):
        return []
    for quote in raw.get('odds', []) or raw.get('pickcenter', []):
        provider = quote.get('provider', {}).get('name')
        if not provider or provider in seen:
            continue
        if any(str(quote.get(k + 'TeamOdds', {}).get('team', {}).get('id', '')) != sides[k] for k in ['home', 'away']):
            continue
        home, away, draw = quote.get('homeTeamOdds', {}), quote.get('awayTeamOdds', {}), quote.get('drawOdds', {})
        values = {'H': decimal(home.get('odds', {}).get('value')), 'D': decimal(draw.get('value')),
                  'A': decimal(away.get('odds', {}).get('value'))}
        if not all(values.values()):
            values = {'H': american(home.get('moneyLine')), 'D': american(draw.get('moneyLine')),
                      'A': american(away.get('moneyLine'))}
        if not all(values.values()):
            continue
        seen.add(provider)
        rows.append({'provider': provider, 'label': f'{provider} · ESPN采集快照', 'via': 'ESPN',
                     'kind': 'bookmaker', 'market': '90-minute-1x2', 'phase': '采集快照',
                     'source': f'https://www.espn.com/soccer/odds/_/gameId/{event_id}',
                     'fetchedAt': fetched_at, **{k: round(v, 4) for k, v in values.items()}})
    return rows


def refresh_official_checks():
    def check(item):
        code, (name, url) = item
        try:
            html = fetch_text(url)
            status, message = 'page-only', '官网页面可连接；尚未接入可核对的直接报价接口。'
            if len(html) < 200:
                status, message = 'unavailable', '本次未取得完整官网页面。'
        except urllib.error.HTTPError as error:
            status, message = 'restricted', f'官网返回 HTTP {error.code}，本站未取得直接报价。'
        except (OSError, ValueError):
            status, message = 'unavailable', '本次官网连接未成功。'
        return {'code': code, 'name': name, 'url': url, 'status': status, 'message': message,
                'directFeed': False, 'historicalVia': 'Football-Data（按赛事和赛季字段覆盖）',
                'checkedAt': datetime.now(timezone.utc).isoformat()}
    with ThreadPoolExecutor(max_workers=3) as pool:
        sources = list(pool.map(check, PROVIDERS.items()))
    snapshot = {'version': 1, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'sources': sources,
                'meaning': '官网连接检查与实际报价采集分开记录；同一聚合数据源不等于多家官网独立核验。'}
    publish(PUBLIC / 'odds-sources.json', snapshot)
    return snapshot


def refresh_odds(league):
    from .match_details import match_catalogue, resolve_event, parse_detail, canonical
    from .ucl import fetch_json
    import http.client
    catalogue, matches = match_catalogue(league)
    folder = league_path(PUBLIC, league)
    previous = read_json(folder / 'odds.json') if (folder / 'odds.json').exists() else {}
    quotes = previous.get('matches', {}) if previous.get('season') == catalogue['season'] else {}
    stamp = datetime.now(timezone.utc).isoformat()
    errors, feeds = [], []
    if league != 'ucl':
        year = int(catalogue['season'][:4])
        divisions = ['E0', 'E1'] if league == 'epl' else ['SP1', 'SP2']
        urls = [f'https://www.football-data.co.uk/mmz4281/{y%100:02}{(y+1)%100:02}/{division}.csv' for y in [year, year-1] for division in divisions]
        urls.append('https://www.football-data.co.uk/fixtures.csv')
        def collect(url):
            try:
                rows = list(csv.DictReader(io.StringIO(fetch_text(url))))
                if rows and not {'Date', 'HomeTeam', 'AwayTeam'}.issubset(rows[0]):
                    raise ValueError('Unrecognized odds feed')
                return url, rows
            except (OSError, ValueError):
                return url, None
        lookup = {(m['date'], canonical(m['home'], league), canonical(m['away'], league)): m for m in matches}
        with ThreadPoolExecutor(max_workers=3) as pool:
            for url, rows in pool.map(collect, urls):
                if rows is None:
                    errors.append(url)
                    continue
                feeds.append(url)
                for row in rows:
                    if row.get('Div') not in divisions:
                        continue
                    try:
                        date = datetime.strptime(row['Date'], '%d/%m/%Y').date().isoformat()
                    except (ValueError, KeyError):
                        continue
                    # Historical aliases match the site's archived identities.
                    from sync_data import team_name
                    home, away = (team_name(row[k]) if league == 'epl' else row[k] for k in ['HomeTeam','AwayTeam'])
                    match = lookup.get((date, canonical(home, league), canonical(away, league)))
                    if not match:
                        continue
                    result = historical_odds(row, url, stamp)
                    if result:
                        quotes[match['id']] = result
    for match in matches:
        event_id = match['id'].removeprefix('espn:') if match['id'].startswith('espn:') else None
        path = STATE / 'match-summaries' / f'{event_id}.json' if event_id else None
        if path and path.exists():
            saved = read_json(path)
            result = espn_odds(saved['raw'], event_id, saved['updatedAt'])
            if result:
                quotes[match['id']] = result
    horizon = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    upcoming = sorted([m for m in matches if m['competition'] == league_config(league).competition and not m.get('finished')
                       and not m.get('started') and m.get('kickoff') and stamp < m['kickoff'] < horizon], key=lambda m: m['kickoff'])[:40]
    def next_quote(match):
        try:
            event = resolve_event(match, league)
            if not event:
                return match['id'], None
            raw = fetch_json(f'https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={event}')
            parse_detail(raw, match, catalogue, league, event)
            return match['id'], espn_odds(raw, event, stamp)
        except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
            return match['id'], None
    with ThreadPoolExecutor(max_workers=4) as pool:
        for match_id, result in pool.map(next_quote, upcoming):
            if result is None:
                errors.append(match_id)
            elif result:
                quotes[match_id] = result
            else:
                # A successfully retrieved empty market is not an unchanged live quote.
                quotes.pop(match_id, None)
    known = {m['id'] for m in matches}
    quotes = {key: value for key, value in quotes.items() if key in known}
    snapshot = {'version': 1, 'league': league, 'season': catalogue['season'], 'updatedAt': stamp,
                'intervalSeconds': 300, 'matches': quotes, 'failedSources': errors, 'feeds': feeds,
                'providers': sorted({q['provider'] for values in quotes.values() for q in values if q.get('kind') != 'aggregate'}),
                'meaning': '90分钟胜平负；历史赔率经Football-Data收录，赛前快照经ESPN收录；报价不是官网直连接口。'}
    publish(folder / 'odds.json', snapshot)
    history_path = folder / 'odds-history.json'
    earlier = read_json(history_path) if history_path.exists() else {}
    recent = (datetime.now(timezone.utc) - timedelta(days=21)).date().isoformat()
    tracked = {m['id'] for m in upcoming} | {m['id'] for m in matches if m['id'] in earlier.get('matches', {}) and m['date'] >= recent}
    publish(history_path, {'version': 1, 'league': league, 'season': catalogue['season'], 'updatedAt': stamp,
                           'matches': append_history(earlier.get('matches') if earlier.get('season') == catalogue['season'] else {}, quotes, stamp, tracked)})
    return snapshot
