"""A transparent, untrained Poisson baseline with strictly pre-match inputs."""
import math
from datetime import datetime, timezone
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from .files import PUBLIC
from .leagues import league_config, league_path

METHOD: Final = 'poisson-shrinkage-v1'


class Match(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    date: str
    home: str
    away: str
    homeGoals: int | None = None
    awayGoals: int | None = None
    finished: bool
    started: bool = False
    competition: str
    season: str
    kickoff: str | None = None
    phase: str = ''
    neutral: bool = False
    source: str = ''
    scoreScope: str = '90 分钟含补时'


class Club(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    name: str
    cn: str


class SquadPlayer(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: int
    team: int
    web_name: str
    status: str
    news: str = ''
    minutes: int | None = None


class Archive(BaseModel):
    model_config = ConfigDict(frozen=True)
    competition: str = '英超'
    season: str
    updatedAt: str
    teams: list[Club]
    matches: list[Match]
    players: list[SquadPlayer]


class FormSummary(BaseModel):
    model_config = ConfigDict(frozen=True)
    team: str
    matches: int
    wins: int
    draws: int
    losses: int
    scored: int
    conceded: int
    scoreSample: int


class Probability(BaseModel):
    model_config = ConfigDict(frozen=True)
    home: float
    draw: float
    away: float


class Baseline(BaseModel):
    model_config = ConfigDict(frozen=True)
    method: str = METHOD
    homeGoalMean: float
    awayGoalMean: float
    probabilities: Probability
    homeSample: int
    awaySample: int
    leagueSample: int
    scorelines: list[tuple[str, float]]
    limitations: list[str]


class MatchAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)
    generatedAt: str
    dataUpdatedAt: str
    liveUpdatedAt: str | None
    team: Club
    match: Match | None
    homeForm: FormSummary | None = None
    awayForm: FormSummary | None = None
    baseline: Baseline | None = None
    unavailablePlayers: list[SquadPlayer] = Field(default_factory=list)
    checklist: list[str]


def load_archive(league: str = 'epl') -> tuple[Archive, str | None]:
    config = league_config(league)
    folder = league_path(PUBLIC, league)
    archive = Archive.model_validate_json((folder / 'data.json').read_text(encoding='utf-8'))
    from .match_details import match_catalogue
    _, rows = match_catalogue(league, PUBLIC)
    matches = [Match.model_validate(row) for row in rows]
    updated = max((row.get('scoreUpdatedAt') or row.get('updatedAt') or '' for row in rows), default='')
    return archive.model_copy(update={'matches': matches}), updated or archive.updatedAt


def goals(row: Match) -> tuple[int, int]:
    if row.homeGoals is None or row.awayGoals is None:
        raise ValueError('Finished match lacks a valid score')
    return row.homeGoals, row.awayGoals


def form_summary(rows: list[Match], club: str) -> FormSummary:
    recent = sorted([row for row in rows if club in (row.home, row.away)], key=lambda row:row.date, reverse=True)[:20]
    wins = draws = scored = conceded = 0
    for row in recent:
        home, away = goals(row)
        own, against = (home, away) if row.home == club else (away, home)
        scored += own
        conceded += against
        wins += own > against
        draws += own == against
    return FormSummary(team=club, matches=len(recent), wins=wins, draws=draws, losses=len(recent)-wins-draws,
                       scored=scored, conceded=conceded, scoreSample=len(recent))


def poisson_baseline(rows: list[Match], fixture: Match) -> Baseline | None:
    history = sorted([row for row in rows if row.finished and row.competition == fixture.competition and row.date < fixture.date], key=lambda row:row.date, reverse=True)
    if len(history) < 20:
        return None
    league = history[:380]
    avg_home = sum(goals(row)[0] for row in league) / len(league)
    avg_away = sum(goals(row)[1] for row in league) / len(league)
    home_rows = [row for row in history if row.home == fixture.home][:20]
    away_rows = [row for row in history if row.away == fixture.away][:20]
    home_attack = (sum(goals(row)[0] for row in home_rows) + 5 * avg_home) / (len(home_rows) + 5)
    home_defence = (sum(goals(row)[1] for row in home_rows) + 5 * avg_away) / (len(home_rows) + 5)
    away_attack = (sum(goals(row)[1] for row in away_rows) + 5 * avg_away) / (len(away_rows) + 5)
    away_defence = (sum(goals(row)[0] for row in away_rows) + 5 * avg_home) / (len(away_rows) + 5)
    home_mean = min(5.0, max(0.15, home_attack * away_defence / max(avg_home, 0.1)))
    away_mean = min(5.0, max(0.15, away_attack * home_defence / max(avg_away, 0.1)))
    if fixture.neutral:
        average = (avg_home + avg_away) / 2
        home_rows = [r for r in history if fixture.home in (r.home, r.away)][:20]
        away_rows = [r for r in history if fixture.away in (r.home, r.away)][:20]
        def strength(sample: list[Match], club: str) -> tuple[float, float]:
            pairs = [goals(r) if r.home == club else goals(r)[::-1] for r in sample]
            return tuple((sum(pair[i] for pair in pairs) + 5 * average) / (len(pairs) + 5) for i in (0, 1))
        ha, hd = strength(home_rows, fixture.home)
        aa, ad = strength(away_rows, fixture.away)
        home_mean = min(5.0, max(0.15, ha * ad / max(average, 0.1)))
        away_mean = min(5.0, max(0.15, aa * hd / max(average, 0.1)))
    grid = [(h, a, math.exp(-home_mean-away_mean) * home_mean**h * away_mean**a / math.factorial(h) / math.factorial(a))
            for h in range(21) for a in range(21)]
    mass = sum(row[2] for row in grid)
    probabilities = Probability(home=sum(p for h,a,p in grid if h>a)/mass,
                                draw=sum(p for h,a,p in grid if h==a)/mass,
                                away=sum(p for h,a,p in grid if h<a)/mass)
    limits = ['模型状态：固定参数的独立泊松基线。',
              f'按主客场各取最近至多 20 场{fixture.competition}；加入相当于 5 场同联赛样本均值的收缩量。',
              '对手强弱、红牌、首发、赛程与转会尚未纳入概率计算；人员情况单独列示。',
              '进球均值采用历史比分；概率校准状态：待独立赛季检验。']
    if min(len(home_rows), len(away_rows)) < 10:
        limits.append('至少一方主客场样本少于 10 场，结果对联赛平均假设较敏感。')
    if fixture.neutral:
        limits[1] = '中立场：双方各取最近至多20场同赛事比赛，以每队平均进球收缩，不加入主场优势。'
    if fixture.competition == '欧冠':
        limits.append('欧冠仅使用90分钟可核对比分；加时、点球及两回合总比分不参与胜平负计算。')
    return Baseline(homeGoalMean=home_mean, awayGoalMean=away_mean, probabilities=probabilities,
                    homeSample=len(home_rows), awaySample=len(away_rows), leagueSample=len(league),
                    scorelines=[(f'{h}:{a}', p/mass) for h,a,p in sorted(grid,key=lambda row:row[2],reverse=True)[:5]], limitations=limits)


def analyze_next(team_id: int, league: str = 'epl') -> MatchAnalysis:
    config = league_config(league)
    archive, live_time = load_archive(league)
    club = next((row for row in archive.teams if row.id == team_id), None)
    if club is None:
        raise LookupError('Team does not exist')
    now = datetime.now(timezone.utc)
    def future(row: Match) -> bool:
        return datetime.fromisoformat(row.kickoff.replace('Z','+00:00')) > now if row.kickoff else row.date > now.date().isoformat()
    upcoming = sorted([row for row in archive.matches if row.competition == config.competition and row.kickoff and not row.finished and not row.started and future(row) and club.name in (row.home,row.away)], key=lambda row:row.kickoff or row.date)
    fixture = upcoming[0] if upcoming else None
    checklist = ['先确认开赛时间、主客场和资料更新时间。', '只使用开赛前已知的比赛与人员资料，避免把赛后信息混入预测。',
                 f'比较近况时同时看对手、主客场与样本量；{config.lower}与{config.competition}不要直接混算。', '把伤停、转会与换帅作为有来源的事实，说明无法量化的影响。',
                 '将本地模型概率当作可检验的基线；AI 必须区分事实、计算结果和推断。', '记录赛前分析，赛后逐场复盘；校准前不要宣称准确率或稳定收益。']
    base = {'generatedAt':datetime.now(timezone.utc).isoformat(), 'dataUpdatedAt':archive.updatedAt,
            'liveUpdatedAt':live_time, 'team':club, 'match':fixture, 'checklist':checklist}
    if fixture is None:
        return MatchAnalysis(**base)
    prior = [row for row in archive.matches if row.finished and row.date < fixture.date]
    teams = {row.id for row in archive.teams if row.name in (fixture.home,fixture.away)}
    return MatchAnalysis(**base, homeForm=form_summary(prior,fixture.home), awayForm=form_summary(prior,fixture.away),
                         baseline=poisson_baseline(prior,fixture),
                         unavailablePlayers=[row for row in archive.players if row.team in teams and row.status not in {'a', 'unreported'}])
