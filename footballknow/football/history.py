"""Collect dated transfer and managerial tables with row-level source links."""
import hashlib
import re
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from typing import Final

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict, Field

from .files import PUBLIC, fetch_text, publish
from .live import Catalogue
from .leagues import league_path

CLUB_ALIASES: Final = {'Manchester City':'Man City', 'Manchester United':'Man Utd',
    'Brighton & Hove Albion':'Brighton', 'Brighton and Hove Albion':'Brighton',
    'Tottenham Hotspur':'Spurs', 'Tottenham':'Spurs', 'Nottingham Forest':"Nott'm Forest",
    'Leeds United':'Leeds', 'Newcastle United':'Newcastle', 'AFC Bournemouth':'Bournemouth',
    'Alavés':'Alaves', 'Deportivo Alavés':'Alaves', 'Athletic Bilbao':'Ath Bilbao', 'Athletic Club':'Ath Bilbao',
    'Atlético Madrid':'Ath Madrid', 'Atlético de Madrid':'Ath Madrid', 'FC Barcelona':'Barcelona',
    'Real Betis':'Betis', 'Celta Vigo':'Celta', 'Celta de Vigo':'Celta', 'Deportivo La Coruña':'La Coruna',
    'Deportivo de La Coruña':'La Coruna', 'Deportivo A Coruña':'La Coruna', 'Deportivo':'La Coruna',
    'Espanyol':'Espanol', 'RCD Espanyol':'Espanol', 'Málaga':'Malaga', 'Racing Santander':'Santander',
    'Racing de Santander':'Santander', 'Rayo Vallecano':'Vallecano', 'Real Sociedad':'Sociedad',
    'Real Madrid CF':'Real Madrid', 'CA Osasuna':'Osasuna', 'Villarreal CF':'Villarreal',
    'Valencia CF':'Valencia', 'Sevilla FC':'Sevilla', 'Elche CF':'Elche', 'Levante UD':'Levante', 'Getafe CF':'Getafe'}


class Transfer(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    date: str
    window: str = ''
    endDate: str | None = None
    player: str
    fromTeam: str
    toTeam: str
    type: str
    fee: str
    source: str
    catalogueSource: str


class ManagerChange(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    team: str
    outgoing: str
    incoming: str
    leftAt: str | None
    joinedAt: str | None
    reason: str
    source: str
    catalogueSource: str


class SourceStatus(BaseModel):
    url: str
    checkedAt: str
    ok: bool


class HistorySnapshot(BaseModel):
    version: int = 1
    updatedAt: str
    season: str
    transfers: list[Transfer] = Field(default_factory=list)
    managers: list[ManagerChange] = Field(default_factory=list)
    sources: list[SourceStatus] = Field(default_factory=list)
    attribution: str = 'Wikipedia contributors, CC BY-SA 4.0; linked club announcements are preferred for each record'


def clean(cell: Tag) -> str:
    copy = BeautifulSoup(str(cell), 'html.parser')
    for footnote in copy.select('sup, .sortkey, .sortkey-sort, .flagicon'):
        footnote.decompose()
    return re.sub(r'\s+', ' ', copy.get_text(' ', strip=True)).strip()


def table_rows(table: Tag) -> list[list[Tag]]:
    """Expand rowspan/colspan so inherited dates remain attached to the right row."""
    rows = []
    carry: dict[int, tuple[Tag, int]] = {}
    for row in table.find_all('tr', recursive=False) or table.select(':scope > tbody > tr'):
        cells = row.find_all(['td', 'th'], recursive=False)
        expanded: dict[int, Tag] = {}
        following: dict[int, tuple[Tag, int]] = {}
        for column, (cell, remaining) in carry.items():
            expanded[column] = cell
            if remaining > 1:
                following[column] = (cell, remaining - 1)
        column = 0
        for cell in cells:
            while column in expanded:
                column += 1
            span = max(1, min(50, int(str(cell.get('colspan') or '1'))))
            remaining = max(1, int(str(cell.get('rowspan') or '1')))
            for position in range(column, column + span):
                expanded[position] = cell
                if remaining > 1:
                    following[position] = (cell, remaining - 1)
            column += span
        carry = following
        rows.append([expanded[index] for index in sorted(expanded)])
    return rows


def parse_date(text: str) -> str | None:
    match = re.search(r'\b\d{1,2} [A-Z][a-z]+ \d{4}\b', text)
    if match:
        return datetime.strptime(match.group(), '%d %B %Y').date().isoformat()
    return None


def row_source(cells: list[Tag], soup: BeautifulSoup, fallback: str) -> str:
    for cell in cells:
        for link in cell.select('sup.reference a[href]'):
            href = str(link.get('href', ''))
            target = soup.find(id=urllib.parse.unquote(href.removeprefix('#')))
            if isinstance(target, Tag):
                external = target.select_one('a.external[href^="https://"]')
                if external:
                    return str(external.get('href'))
    return fallback


def collect_transfers(url: str, clubs: set[str]) -> list[Transfer]:
    soup = BeautifulSoup(fetch_text(url), 'html.parser')
    found, recognized = [], False
    for table in soup.find_all('table', class_='wikitable'):
        rows = table_rows(table)
        if not rows:
            continue
        header = [clean(cell) for cell in rows[0]]
        if 'Player' not in header or 'Moving from' not in header or 'Moving to' not in header:
            continue
        recognized = True
        loan = 'Start date' in header
        for cells in rows[1:]:
            if len(cells) != len(header):
                continue
            values = dict(zip(header, (clean(cell) for cell in cells)))
            start = parse_date(values.get('Start date' if loan else 'Date', ''))
            origin = CLUB_ALIASES.get(values['Moving from'], values['Moving from'])
            destination = CLUB_ALIASES.get(values['Moving to'], values['Moving to'])
            if not start or not ({origin, destination} & clubs):
                continue
            fee = values.get('Fee', '')
            kind = '租借' if loan else '自由转会' if fee.lower() == 'free' else '转会'
            fee = '未公开' if not fee or 'undisclosed' in fee.lower() else '自由转会' if fee.lower() == 'free' else fee
            identity = '|'.join([start, values['Player'], origin, destination, kind])
            found.append(Transfer(id=hashlib.sha256(identity.encode()).hexdigest()[:20], date=start,
                endDate=parse_date(values.get('End date', '')), player=values['Player'],
                fromTeam=origin, toTeam=destination, type=kind, fee=fee,
                source=row_source(cells, soup, url), catalogueSource=url))
    if not recognized:
        raise OSError('Transfer table missing; retaining previous source records')
    return found


def collect_managers(url: str, clubs: set[str], aliases: dict | None = None) -> list[ManagerChange]:
    soup = BeautifulSoup(fetch_text(url), 'html.parser')
    found, recognized = [], False
    for table in soup.find_all('table', class_='wikitable'):
        rows = table_rows(table)
        if not rows:
            continue
        header = [clean(cell).replace('head coach', 'manager').replace('coach', 'manager').replace('manager(s)', 'manager') for cell in rows[0]]
        if 'Outgoing manager' not in header or 'Incoming manager' not in header:
            continue
        recognized = True
        for cells in rows[1:]:
            if len(cells) != len(header):
                continue
            values = dict(zip(header, (clean(cell) for cell in cells)))
            club = values.get('Team', values.get('Club', ''))
            club = (aliases or {}).get(club, (aliases or {}).get(CLUB_ALIASES.get(club, club), CLUB_ALIASES.get(club, club)))
            if club not in clubs:
                continue
            joined = parse_date(values.get('Date of appointment', ''))
            left = parse_date(values.get('Date of vacancy', ''))
            identity = '|'.join([club, values['Outgoing manager'], values['Incoming manager'], joined or '', left or ''])
            found.append(ManagerChange(id=hashlib.sha256(identity.encode()).hexdigest()[:20], team=club,
                outgoing=values['Outgoing manager'], incoming=values['Incoming manager'], leftAt=left, joinedAt=joined,
                reason=values.get('Manner of departure', ''), source=row_source(cells, soup, url), catalogueSource=url))
    if not recognized:
        raise OSError('Manager table missing; retaining previous source records')
    return found


def collect_spanish_transfers(url: str, clubs: set[str], window: str) -> list[Transfer]:
    soup = BeautifulSoup(fetch_text(url), 'html.parser')
    found, recognized = [], False
    for table in soup.find_all('table', class_='wikitable'):
        rows = table_rows(table)
        if not rows:
            continue
        header = [clean(cell) for cell in rows[0]]
        heading = table.find_previous(['h2', 'h3'])
        if 'Player' not in header or heading is None:
            continue
        label = re.sub(r'\[edit\]', '', heading.get_text(' ', strip=True)).strip()
        club = CLUB_ALIASES.get(label, label)
        if club not in clubs:
            continue
        recognized = True
        for cells in rows[1:]:
            if len(cells) != len(header):
                continue
            movement = re.match(r'^(.*?)\s*\((on loan |loan return )?(from|to) (.+?)\)', clean(cells[header.index('Player')]))
            if not movement:
                continue
            player, qualifier, direction, counterparty = movement.groups()
            counterparty = re.split(r',|;| later ', counterparty)[0].strip()
            counterparty = CLUB_ALIASES.get(counterparty, counterparty)
            origin, destination = (counterparty, club) if direction == 'from' else (club, counterparty)
            kind = '租借回归' if qualifier == 'loan return ' else '租借' if qualifier else '转会'
            identity = '|'.join([window, player.strip(), origin, destination, kind])
            found.append(Transfer(id=hashlib.sha256(identity.encode()).hexdigest()[:20],
                date='', window=window, player=player.strip(), fromTeam=origin, toTeam=destination,
                type=kind, fee='未公开', source=row_source(cells, soup, url), catalogueSource=url))
    if not recognized:
        raise OSError('Spanish transfer roster tables missing')
    return found


def refresh_history(league: str = 'epl') -> HistorySnapshot:
    folder = league_path(PUBLIC, league)
    catalogue = Catalogue.model_validate_json((folder / 'data.json').read_text(encoding='utf-8'))
    clubs = {team.name for team in catalogue.teams}
    year = int(catalogue.season[:4])
    now = datetime.now(timezone.utc)
    path = folder / 'history.json'
    snapshot = HistorySnapshot(updatedAt=now.isoformat(), season=catalogue.season)
    if path.exists():
        previous = HistorySnapshot.model_validate_json(path.read_text(encoding='utf-8'))
        snapshot.transfers, snapshot.managers = previous.transfers, previous.managers
    windows = [f'summer_{year-1}', f'winter_{year-1}%E2%80%93{str(year)[2:]}', f'summer_{year}']
    if now.month >= 9 or now.year > year:
        windows.append(f'winter_{year}%E2%80%93{str(year+1)[2:]}')
    tasks = [(f'https://en.wikipedia.org/wiki/List_of_English_football_transfers_{window}', 'transfers') for window in windows]
    tasks += [(f'https://en.wikipedia.org/wiki/{y}%E2%80%93{str(y + 1)[2:]}_{league}', 'managers')
              for y in [year - 1, year] for league in ['Premier_League', 'EFL_Championship']]
    if league == 'laliga':
        tasks = [(f'https://en.wikipedia.org/wiki/List_of_Spanish_football_transfers_summer_{y}', 'transfers') for y in [year - 1, year]]
        tasks += [(f'https://en.wikipedia.org/wiki/List_of_Spanish_football_transfers_winter_{year}', 'transfers')]
        if now.year > year:
            tasks += [(f'https://en.wikipedia.org/wiki/List_of_Spanish_football_transfers_winter_{year + 1}', 'transfers')]
        tasks += [(f'https://en.wikipedia.org/wiki/{y}%E2%80%93{str(y + 1)[2:]}_{division}', 'managers')
                  for y in [year - 1, year] for division in ['La_Liga', 'Segunda_Divisi%C3%B3n']]
    for url, kind in tasks:
        ok = False
        try:
            if kind == 'transfers':
                rows = collect_spanish_transfers(url, clubs, url.rsplit('_', 1)[-1] + (' 夏窗' if 'summer' in url else ' 冬窗')) if league == 'laliga' else collect_transfers(url, clubs)
                snapshot.transfers = [row for row in snapshot.transfers if row.catalogueSource != url] + rows
            else:
                changes = collect_managers(url, clubs)
                snapshot.managers = [row for row in snapshot.managers if row.catalogueSource != url] + changes
            ok = True
        except (OSError, urllib.error.URLError, ValueError):
            pass
        snapshot.sources.append(SourceStatus(url=url, checkedAt=now.isoformat(), ok=ok))
    snapshot.transfers = sorted({row.id:row for row in snapshot.transfers}.values(), key=lambda row:(row.window[:4] if row.window else row.date[:4], row.date, row.window), reverse=True)
    snapshot.managers = sorted({row.id:row for row in snapshot.managers}.values(), key=lambda row:row.joinedAt or row.leftAt or '', reverse=True)
    if not any(source.ok for source in snapshot.sources):
        raise OSError('No history source refreshed; retaining previous snapshot')
    publish(path, snapshot.model_dump(mode='json'))
    return snapshot
