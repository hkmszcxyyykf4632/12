"""Attributed club transfers and domestic-league manager changes for UCL clubs."""
import hashlib
import re
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from .files import PUBLIC, fetch_text, publish, read_json
from .history import (HistorySnapshot, Transfer, SourceStatus, collect_managers,
                      table_rows, clean, parse_date, row_source, CLUB_ALIASES)
from .leagues import league_path
from .names import NameSnapshot, PlayerName, refresh_names
from .name_rosters import refresh_club_names

DIVISIONS = {'eng.1':'Premier_League', 'esp.1':'La_Liga', 'ger.1':'Bundesliga',
    'ita.1':'Serie_A', 'fra.1':'Ligue_1', 'por.1':'Primeira_Liga', 'ned.1':'Eredivisie',
    'tur.1':'Süper_Lig', 'bel.1':'Belgian_Pro_League', 'aut.1':'Austrian_Football_Bundesliga',
    'gre.1':'Super_League_Greece', 'ukr.1':'Ukrainian_Premier_League',
    'cze.1':'Czech_First_League', 'svk.1':'Slovak_First_Football_League',
    'aze.1':'Azerbaijan_Premier_League', 'nor.1':'Eliteserien'}
EXTRA_ALIASES = {'Manchester City':['Man City'], 'Manchester United':['Man Utd'],
    'Atlético Madrid':['Ath Madrid','Atlético de Madrid'], 'Real Betis':['Betis'],
    'Feyenoord Rotterdam':['Feyenoord'], 'Internazionale':['Inter','Inter Milan'],
    'FC Porto':['Porto'], 'Fenerbahce':['Fenerbahçe'], 'Bodo/Glimt':['Bodø/Glimt'],
    'Club Brugge':['Club Brugge KV'], 'LASK Linz':['LASK'], 'Lens':['RC Lens'],
    'Lille':['Lille OSC'], 'Napoli':['Napoli','SSC Napoli'], 'Slavia Prague':['Slavia Praha','Slavia Prague'],
    'Viking FK':['Viking'], 'Shakhtar Donetsk':['Shakhtar Donetsk'], 'Sabah FK':['Sabah'],
    'Slovan Bratislava':['Slovan Bratislava']}


def normalized(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', value).casefold())


def club_aliases(teams: list[dict]) -> dict[str, str]:
    aliases = {}
    for team in teams:
        article = re.sub(r' \([^)]*\)$', '', team['article'])
        for name in [team['name'], article, *EXTRA_ALIASES.get(team['name'], [])]:
            aliases[name] = team['name']
        for original, short in CLUB_ALIASES.items():
            if original in aliases or short in aliases:
                aliases[original] = aliases[short] = team['name']
    return aliases


def club_transfers(url: str, team: str, aliases: dict) -> list[Transfer]:
    soup = BeautifulSoup(fetch_text(url), 'html.parser')
    found, recognized = [], False
    canonical = {normalized(k): v for k, v in aliases.items()}
    for table in soup.find_all('table', class_='wikitable'):
        rows = table_rows(table)
        if not rows:
            continue
        header = [clean(c) for c in rows[0]]
        origin = next((h for h in header if h.lower() in {'from', 'transferred from', 'previous club', 'club from'}), None)
        destination = next((h for h in header if h.lower() in {'to', 'transferred to', 'new club', 'club to'}), None)
        if 'Player' not in header or not (origin or destination):
            continue
        heading = table.find_previous(['h2', 'h3', 'h4', 'h5'])
        section = heading.get_text(' ', strip=True).lower() if heading else ''
        recognized = True
        for cells in rows[1:]:
            if len(cells) != len(header):
                continue
            values = dict(zip(header, (clean(c) for c in cells)))
            player = values['Player']
            counterparty = values.get(origin or destination, '').strip()
            if not player or not counterparty or player == 'Player':
                continue
            counterparty = canonical.get(normalized(counterparty), counterparty)
            start = parse_date(values.get('Date', values.get('Transfer date', values.get('Date of transfer', ''))))
            fee = values.get('Fee', values.get('Transfer fee', ''))
            note = values.get('Notes', '')
            description = (section + ' ' + fee + ' ' + note).lower()
            kind = '租借回归' if any(s in section for s in ('return', 'ended')) else '租借' if 'loan' in description else '自由转会' if 'free' in fee.lower() else '转会'
            before, after = (counterparty, team) if origin else (team, counterparty)
            window = '' if start else urllib.parse.unquote(url.split('/')[-1]).split('_', 1)[0] + ' 赛季'
            identity = '|'.join([start or window, player, before, after, kind])
            found.append(Transfer(id=hashlib.sha256(identity.encode()).hexdigest()[:20], date=start or '',
                window=window, player=player, fromTeam=before, toTeam=after, type=kind,
                fee='未公开' if not fee or fee in {'—','–','N/a','N/A'} or 'undisclosed' in fee.lower() else '自由转会' if fee.lower() == 'free' else fee,
                source=row_source(cells, soup, url), catalogueSource=url))
    if not recognized:
        raise OSError('No supported transfer table in club season article')
    return found


def refresh_history() -> HistorySnapshot:
    folder = league_path(PUBLIC, 'ucl')
    catalogue = read_json(folder / 'data.json')
    teams, year = catalogue['teams'], int(catalogue['season'][:4])
    aliases = club_aliases(teams)
    clubs = {t['name'] for t in teams}
    snapshot = HistorySnapshot(updatedAt=datetime.now(timezone.utc).isoformat(), season=catalogue['season'])
    path = folder / 'history.json'
    if path.exists():
        old = HistorySnapshot.model_validate_json(path.read_text(encoding='utf-8'))
        snapshot.transfers, snapshot.managers = old.transfers, old.managers
    reused = set()
    for league in ['epl', 'laliga']:
        source_folder = league_path(PUBLIC, league)
        if not (source_folder / 'history.json').exists():
            continue
        data = read_json(source_folder / 'data.json')
        by_cn = {t['cn']: t['name'] for t in teams}
        mappings = {t['name']: by_cn[t['cn']] for t in data['teams'] if t['cn'] in by_cn}
        reused.update(mappings.values())
        existing = HistorySnapshot.model_validate_json((source_folder / 'history.json').read_text(encoding='utf-8'))
        for row in existing.transfers:
            if row.fromTeam in mappings or row.toTeam in mappings:
                snapshot.transfers.append(row.model_copy(update={'fromTeam': mappings.get(row.fromTeam, aliases.get(row.fromTeam, row.fromTeam)),
                    'toTeam': mappings.get(row.toTeam, aliases.get(row.toTeam, row.toTeam))}))
        for row in existing.managers:
            if row.team in mappings:
                snapshot.managers.append(row.model_copy(update={'team': mappings[row.team]}))
        snapshot.sources += existing.sources
    tasks = []
    for team in teams:
        if team['name'] in reused:
            continue
        article = re.sub(r' \(football\)$', '', team['article'])
        for y in [year - 1, year]:
            season = str(y) if team['domestic'] == 'nor.1' else f'{y}–{str(y+1)[2:]}'
            title = f'{season}_{article.replace(" ", "_")}_season'
            tasks.append(('transfers', 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(title), team['name']))
    for division in {t['domestic'] for t in teams} - {'eng.1','esp.1'}:
        for y in [year - 1, year]:
            season = str(y) if division == 'nor.1' else f'{y}–{str(y+1)[2:]}'
            title = f'{season}_{DIVISIONS[division]}'
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
                old_rows = getattr(snapshot, kind)
                setattr(snapshot, kind, [r for r in old_rows if r.catalogueSource != url] + rows)
                ok = True
            except (OSError, ValueError, KeyError):
                pass
            snapshot.sources.append(SourceStatus(url=url, checkedAt=datetime.now(timezone.utc).isoformat(), ok=ok))
    snapshot.transfers = sorted({r.id:r for r in snapshot.transfers if {r.fromTeam,r.toTeam}&clubs}.values(),
                               key=lambda r:r.date or r.window, reverse=True)
    snapshot.managers = sorted({r.id:r for r in snapshot.managers if r.team in clubs}.values(),
                              key=lambda r:r.joinedAt or r.leftAt or '', reverse=True)
    if not any(s.ok for s in snapshot.sources):
        raise OSError('No UCL club history source available')
    publish(path, snapshot.model_dump(mode='json'))
    return snapshot


def refresh_localized_names(full: bool = False) -> NameSnapshot:
    folder = league_path(PUBLIC, 'ucl')
    catalogue = read_json(folder / 'data.json')
    snapshot = refresh_names(0, 'ucl')
    def identity(player):
        return normalized(player.get('known_name') or (player['first_name']+' '+player['second_name'])), player.get('birth_date')
    players = {identity(p):p for p in catalogue['players'] if p.get('birth_date')}
    for league in ['epl','laliga']:
        other = league_path(PUBLIC, league)
        if not (other / 'names.json').exists():
            continue
        data, names = read_json(other / 'data.json'), read_json(other / 'names.json')
        for player in data['players']:
            target = players.get(identity(player))
            name = names['names'].get(str(player['code']))
            if target and name:
                snapshot.names[str(target['code'])] = PlayerName.model_validate({**name, 'code':target['code']})
    publish(folder / 'names.json', snapshot.model_dump(mode='json'))
    refresh_club_names('ucl')
    return refresh_names(1500 if full else 60, 'ucl')
