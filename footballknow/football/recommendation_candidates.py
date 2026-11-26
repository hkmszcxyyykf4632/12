"""Rank only validated, saved pre-event reports; ranking is not calibrated probability."""
import json
import math
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, JsonValue
from .files import STATE, PUBLIC
from .football_forecasts import settlement, identity, pregame, INITIAL_WINDOW
from .match_research import load
from .football_statistics import read_statistics as football_statistics
from .racing_statistics import read_statistics as racing_statistics
from .motivation import dt


class Candidate(BaseModel):
    model_config = ConfigDict(frozen=True)
    domain: Literal['football', 'racing']
    group: str
    event: str
    identity: str
    stage: str
    issuedAt: AwareDatetime
    kickoff: AwareDatetime
    priority: float
    reasons: list[str]
    summary: list[str]
    receipt: dict[str, JsonValue]


def rows(path: Path, query: str) -> list[sqlite3.Row]:
    if not path.is_file():
        return []
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        return db.execute(query).fetchall()


def football_candidates(at: datetime) -> list[Candidate]:
    saved_rows = rows(STATE / 'football-forecasts.sqlite3', 'SELECT * FROM forecasts')
    seen = {r['identity'] for r in saved_rows if r['stage'] == 'initial'}
    seen.update(r['identity'] for r in rows(STATE / 'football-forecasts.sqlite3', "SELECT * FROM attempts WHERE stage='initial' AND message != '正在核对资料并生成预测'"))
    # Finish a first pass over available fixtures before locking this round's top three.
    if any(pregame(m, at) and dt(m['kickoff']) - at <= INITIAL_WINDOW and identity(m) not in seen for m in load(PUBLIC / 'daily-football.json').get('matches', [])):
        return []
    receipts = {(r.identity, r.stage): r for r in football_statistics().records}
    chosen: dict[str, Candidate] = {}
    for saved in saved_rows:
        r = receipts.get((saved['identity'], saved['stage']))
        if not r or r.status != 'pending' or not at < r.kickoff or not r.round or not r.season:
            continue
        if r.asianSide == 'pass' or r.line is None or r.asianPrice is None:
            continue
        report = json.loads(saved['content'])
        if report.get('model') != 'fengyi-odds-change-v1' or not report.get('oddsSignal'):
            continue
        base = report.get('baseline', {})
        samples = base.get('samples', {})
        count = min(samples.get('home', 0), samples.get('away', 0))
        xg = base.get('expectedGoals', [])
        if not base.get('available') or count < 3 or len(xg) != 2 or any(type(n) not in (int, float) or not math.isfinite(n) or not 0 < n <= 5 for n in xg):
            continue
        if settlement(r.score, r.line, r.asianSide) not in {'赢盘', '赢半', '走盘'}:
            continue
        edge = 0.0
        for home in range(16):
            for away in range(16):
                weight = math.exp(-sum(xg)) * xg[0] ** home * xg[1] ** away / math.factorial(home) / math.factorial(away)
                value = {'赢盘': 1, '赢半': .5, '走盘': 0, '输半': -.5, '输盘': -1}[settlement((home, away), r.line, r.asianSide)]
                edge += weight * value
        confirmed = report.get('lineupsConfirmed') is True
        same = list(r.score) == (base.get('leadingScores') or [None])[0]
        signal = report['oddsSignal']
        strength = min(20, abs(signal.get('lineChange', 0)) * 10 + max((signal.get('weightChangesPP') or {'x': 0}).values()))
        priority = strength + (10 if abs(r.line) <= .5 else 0) + min(count, 10) * 2 + 20 * confirmed + 25 * edge + 5 * same
        reasons = [f'双方至少{count}场赛前往绩可核对', '已核对同来源赔率变化，半球以内优先研究', '正式首发已核对' if confirmed else '首发尚未确认，保留阵容变化风险', '比分与统计基线一致' if same else '比分含模型调整，需结合原文依据']
        candidate = Candidate(domain='football', group=f'{r.league}|{r.season}|{r.round}', event=r.eventId,
            identity=r.identity, stage=r.stage, issuedAt=r.issuedAt, kickoff=r.kickoff,
            priority=round(priority, 4), reasons=reasons, summary=report.get('summary', []), receipt=r.model_dump(mode='json'))
        previous = chosen.get(r.eventId)
        if previous is None or (candidate.stage == 'final', candidate.issuedAt) > (previous.stage == 'final', previous.issuedAt):
            chosen[r.eventId] = candidate
    return list(chosen.values())


def racing_candidates(at: datetime) -> list[Candidate]:
    receipts = {r.raceId: r for r in racing_statistics().records}
    result = []
    for saved in rows(STATE / 'racing-analysis.sqlite3', "SELECT * FROM reports WHERE phase='pre'"):
        r = receipts.get(saved['race_id'])
        if not r or r.status != 'pending' or any(h.withdrawn for h in r.runners):
            continue
        report = json.loads(saved['content'])
        market = report.get('marketSnapshot', {})
        off = dt(market.get('offTime'))
        coverage = report.get('profileCoverage', {})
        available, total = coverage.get('available', 0), coverage.get('total', 0)
        if not off or not r.issuedAt <= at < off or not total or available / total < .5:
            continue
        pool = next((p for p in market.get('pools', []) if p.get('type') == 'WIN'), {})
        quotes = pool.get('quotes', [])
        prices = [(q, float(q['value'])) for q in quotes if str(q.get('value', '')).replace('.', '', 1).isdigit()]
        prices = [(q, v) for q, v in prices if math.isfinite(v) and v >= 1]
        pick = next((v for q, v in prices if any(h.get('id') == r.pick for h in q.get('horses', []))), None)
        if pick is None:
            continue
        runners = report.get('preparationSnapshot', {}).get('runners', [])
        preparation = next((h for h in runners if h.get('horseId', h.get('id')) == r.pick), {})
        known = preparation.get('known') is True
        support = (1 / pick) / sum(1 / v for _, v in prices)
        fresh = not pool.get('stale') and not pool.get('retained')
        priority = 50 * min(available / total, 1) + 20 * support + 20 * known + 10 * fresh
        reasons = [f'本场{available}/{total}匹具备马匹资料', f'首选已保存独赢报价{pick:g}倍（当时快照）', '首选晨操资料可核对' if known else '晨操证据不完整，降低排序权重', '报价为发布时核对值' if fresh else '报价曾有延迟，降低排序权重']
        result.append(Candidate(domain='racing', group=r.day, event=r.raceId, identity=r.raceId, stage='pre',
            issuedAt=r.issuedAt, kickoff=off, priority=round(priority, 4), reasons=reasons,
            summary=report.get('summary', []), receipt=r.model_dump(mode='json')))
    return result
