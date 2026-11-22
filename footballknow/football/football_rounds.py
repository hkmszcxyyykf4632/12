"""Source-attributed round numbers; postponed fixtures retain their original round."""
from datetime import datetime, timedelta, timezone
from typing import Final
from time import sleep

from pydantic import Field

from .files import PUBLIC, publish
from .match_details import canonical
from .match_research import load
from .statistics_models import Frozen
from .ucl import fetch_json

IDS: Final = {'epl': '4328', 'laliga': '4335', 'seriea': '4332', 'bundesliga': '4331', 'ucl': '4480'}
BASE: Final = 'https://www.thesportsdb.com/api/v1/json/123/eventsround.php'


class Event(Frozen):
    idEvent: str
    idLeague: str
    strSeason: str
    intRound: str
    strHomeTeam: str
    strAwayTeam: str
    dateEvent: str
    strTimestamp: str | None = None
    strStatus: str | None = None


class Response(Frozen):
    events: list[Event] | None = Field(default_factory=list)


class RoundEntry(Frozen):
    id: str
    league: str
    season: str
    round: int
    home: str
    away: str
    date: str
    status: str
    source: str


def refresh(limit: int = 3) -> int:
    """Bounded cached background collection. The web reader performs no requests."""
    path = PUBLIC / 'football-rounds.json'
    saved = load(path)
    records = {r['id']: r for r in saved.get('records', [])}
    checked = saved.get('checked', {})
    at = datetime.now(timezone.utc)
    year = at.year if at.month >= 7 else at.year - 1
    season = f'{year}-{year + 1}'
    candidates = []
    for league in IDS:
        maximum = 8 if league == 'ucl' else 34 if league == 'bundesliga' else 38
        for number in range(1, maximum + 1):
            key = f'{league}:{season}:{number}'
            stamp = checked.get(key)
            recent = datetime.fromisoformat(stamp) if stamp else None
            peers = [r for r in records.values() if r['league'] == league and r['round'] == number and r['season'].startswith(str(year))]
            active = any(abs((datetime.fromisoformat(r['date']).date() - at.date()).days) <= 7 for r in peers)
            if recent and at - recent < (timedelta(minutes=10) if active else timedelta(days=1)):
                continue
            candidates.append((0 if active else 1, bool(recent), abs(number - (5 if league == 'ucl' else 12)), key, league, number))
    count = 0
    for _, _, _, key, league, number in sorted(candidates)[:limit]:
        if count:
            sleep(2)
        source = f'{BASE}?id={IDS[league]}&r={number}&s={season}'
        value = Response.model_validate(fetch_json(source))
        for e in value.events or []:
            if e.idLeague != IDS[league] or e.strSeason != season or not e.intRound.isdigit() or int(e.intRound) != number:
                continue
            entry = RoundEntry(id=e.idEvent, league=league, season=season.replace('-', '/')[0:5]+season[-2:],
                round=number, home=e.strHomeTeam, away=e.strAwayTeam, date=e.dateEvent,
                status=e.strStatus or '', source=source)
            records[e.idEvent] = entry.model_dump()
        checked[key] = at.isoformat()
        count += 1
        publish(path, {'updatedAt': at.isoformat(), 'records': list(records.values()), 'checked': checked})
    return count


def round_info(league: str, home: str, away: str, kickoff: datetime, entries: list[RoundEntry]) -> tuple[str, str, str, bool]:
    """Match both team identities and the fixture date before assigning a round."""
    year = kickoff.year if kickoff.month >= 7 else kickoff.year - 1
    pairs = [r for r in entries if r.league == league and r.season.startswith(str(year))
        and canonical(r.home, league) == canonical(home, league)
        and canonical(r.away, league) == canonical(away, league)
        and (league != 'ucl' or r.date >= str(year) + '-09-01')]
    candidates = [r for r in pairs if abs((datetime.fromisoformat(r.date).date() - kickoff.date()).days) <= 3]
    if not candidates and len(pairs) == 1:
        candidates = pairs
    if len(candidates) != 1:
        return '', '', '', False
    row = candidates[0]
    # Qualification rounds share SportsDB numbers; September-onward league-phase fixtures are kept apart.
    peers = [r for r in entries if (r.league, r.season, r.round) == (row.league, row.season, row.round)
             and (league != 'ucl' or r.date >= row.season[:4] + '-09-01')]
    expected = 18 if league == 'ucl' else 9 if league == 'bundesliga' else 10
    complete = len(peers) == expected and all(r.status in {'FT', 'AET', 'PEN', 'Cancelled', 'CANC'} for r in peers)
    label = f'联赛阶段第{row.round}轮' if league == 'ucl' else f'第{row.round}轮'
    return row.season, label, row.source, complete
