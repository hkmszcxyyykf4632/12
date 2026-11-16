"""Publish all current-season EPL fixtures without inventing live clocks."""
from datetime import datetime, timezone
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from .files import PUBLIC, fetch_text, publish

FIXTURES_URL: Final = 'https://fantasy.premierleague.com/api/fixtures/'


class Fixture(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    event: int | None = None
    kickoff_time: datetime | None = None
    team_h: int
    team_a: int
    team_h_score: int | None = Field(default=None, ge=0, le=99)
    team_a_score: int | None = Field(default=None, ge=0, le=99)
    started: bool | None = None
    finished: bool = False
    finished_provisional: bool = False


class Team(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    name: str


class Catalogue(BaseModel):
    model_config = ConfigDict(frozen=True)
    season: str
    teams: list[Team]


class LiveMatch(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    fixtureId: int
    date: str
    kickoff: str | None
    home: str
    away: str
    homeGoals: int | None
    awayGoals: int | None
    started: bool
    finished: bool
    provisional: bool
    result: str | None
    competition: str = '英超'
    season: str
    source: str = FIXTURES_URL
    phase: str = ''
    neutral: bool = False
    scoreScope: str = '90 分钟含补时'


class LiveSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: int = 1
    league: str = 'epl'
    competition: str = '英超'
    updatedAt: str
    refreshSeconds: int = 60
    source: str = FIXTURES_URL
    season: str
    matches: list[LiveMatch]


def build_snapshot(fixtures: list[Fixture], catalogue: Catalogue) -> LiveSnapshot:
    names = {team.id: team.name for team in catalogue.teams}
    pairs = {(row.team_h, row.team_a) for row in fixtures}
    if len(names) != 20 or len(fixtures) != 380 or len(pairs) != 380 or len({row.id for row in fixtures}) != 380:
        raise OSError('Incomplete fixture feed; previous live snapshot retained')
    matches = []
    for row in fixtures:
        if row.team_h not in names or row.team_a not in names or row.team_h == row.team_a:
            raise OSError('Fixture teams do not match the current catalogue')
        home, away = names[row.team_h], names[row.team_a]
        kickoff = row.kickoff_time.isoformat() if row.kickoff_time else None
        date = kickoff[:10] if kickoff else ''
        scored = row.team_h_score is not None and row.team_a_score is not None
        done = row.finished and scored
        result = None
        if row.finished and row.team_h_score is not None and row.team_a_score is not None:
            result = 'D' if row.team_h_score == row.team_a_score else 'H' if row.team_h_score > row.team_a_score else 'A'
        matches.append(LiveMatch(
            id=f'{date}|{home}|{away}', fixtureId=row.id, date=date, kickoff=kickoff,
            home=home, away=away, homeGoals=row.team_h_score, awayGoals=row.team_a_score,
            started=bool(row.started), finished=bool(done), provisional=row.finished_provisional and not done,
            result=result, season=catalogue.season,
        ))
    return LiveSnapshot(updatedAt=datetime.now(timezone.utc).isoformat(), season=catalogue.season, matches=matches)


def refresh_live() -> LiveSnapshot:
    catalogue = Catalogue.model_validate_json((PUBLIC / 'data.json').read_text(encoding='utf-8'))
    fixtures = TypeAdapter(list[Fixture]).validate_json(fetch_text(FIXTURES_URL))
    snapshot = build_snapshot(fixtures, catalogue)
    publish(PUBLIC / 'live.json', snapshot.model_dump(mode='json'))
    return snapshot
