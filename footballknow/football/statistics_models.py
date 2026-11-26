"""Validated, public receipts for cumulative prediction statistics."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra='ignore')


Goal = Annotated[int, Field(strict=True, ge=0, le=30)]


class Team(Frozen):
    id: str
    name: str = ''
    label: str = ''
    goals: Goal | None = None


class Fixture(Frozen):
    id: str
    competitionId: str
    kickoff: AwareDatetime
    teams: dict[str, Team]
    state: str = 'scheduled'
    started: bool = False
    finished: bool = False
    scoreScope: str = ''
    source: str = ''


class FootballReport(Frozen):
    issuedAt: AwareDatetime
    stage: Literal['initial', 'final']
    score: tuple[Goal, Goal]
    scoreCandidates: list[tuple[Goal, Goal]] = Field(default_factory=list, max_length=2)
    asianSide: Literal['H', 'A', 'pass']
    quote: dict[str, JsonValue] | None = None
    snapshotHash: str


class FootballSnapshot(Frozen):
    capturedAt: AwareDatetime
    match: Fixture


class FootballReceipt(Frozen):
    identity: str
    eventId: str
    matchId: str = ''
    league: str
    kickoff: datetime
    day: str
    home: str
    away: str
    season: str = ''
    round: str = ''
    roundSource: str = ''
    roundComplete: bool = False
    homeName: str
    awayName: str
    stage: str
    issuedAt: datetime
    score: tuple[int, int]
    scoreCandidates: list[tuple[int, int]] = Field(default_factory=list)
    scorePrices: dict[str, float] = Field(default_factory=dict)
    asianSide: str
    line: float | None = None
    asianPrice: float | None = None
    scorePrice: float | None = None
    scoreQuoteAt: str = ''
    scoreProvider: str = ''
    scoreSource: str = ''
    provider: str = ''
    quoteAt: str = ''
    status: str = 'pending'
    reason: str = ''
    actual: tuple[int, int] | None = None
    exactHit: bool | None = None
    resultHit: bool | None = None
    asianResult: str = 'pending'
    source: str = ''


class Runner(Frozen):
    id: str
    number: str | int = ''
    name: str = ''
    withdrawn: bool = False
    place: int | None = None
    position: str = ''


class Dividend(Frozen):
    type: str
    combination: str
    amount: float | None = Field(default=None, allow_inf_nan=False, ge=0)
    display: str = ''
    unit: float = Field(default=10, gt=0, allow_inf_nan=False)


class Race(Frozen):
    id: str
    date: str
    course: str
    courseName: str = ''
    raceNo: int
    offTime: AwareDatetime | None = None
    status: str
    resultOfficial: bool = False
    entries: list[Runner]
    dividends: list[Dividend] = Field(default_factory=list)
    source: str = ''


class RacingReport(Frozen):
    runnerSnapshot: list[Runner] = Field(default_factory=list)
    pick: str
    shortlist: list[str] = Field(min_length=1, max_length=3)
    marketSnapshot: dict[str, JsonValue] = Field(default_factory=dict)


class Ticket(Frozen):
    combination: str
    status: Literal['hit', 'miss', 'refund', 'pending']
    dividend: float | None = None
    multiple: float | None = None


class PoolReceipt(Frozen):
    type: str
    tickets: list[Ticket]


class RacingReceipt(Frozen):
    meetingComplete: bool = False
    raceId: str
    day: str
    course: str
    courseName: str
    raceNo: int
    issuedAt: datetime
    status: str
    reason: str = ''
    pick: str
    runners: list[Runner]
    pools: list[PoolReceipt]
    source: str = ''


class Statistics(Frozen):
    updatedAt: datetime
    records: list[FootballReceipt] | list[RacingReceipt]
    unreadable: int = 0
