"""Chronological baseline checks and immutable first pre-match AI picks."""
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .analysis import Match, MatchAnalysis, load_archive, poisson_baseline
from .files import PUBLIC, STATE
from .leagues import league_config, league_path

TARGET = 0.38
OUTCOMES = ('H', 'D', 'A')


def outcome(match: Match) -> str:
    return 'H' if match.homeGoals > match.awayGoals else 'A' if match.homeGoals < match.awayGoals else 'D'


def accuracy(correct: int, total: int) -> dict:
    if not total:
        return {'samples': 0, 'correct': 0, 'hitRate': None, 'interval95': None, 'meetsPointTarget': None}
    rate, z = correct / total, 1.959963984540054
    denominator = 1 + z * z / total
    centre = (rate + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return {'samples': total, 'correct': correct, 'hitRate': rate,
            'interval95': [max(0, centre - radius), min(1, centre + radius)], 'meetsPointTarget': rate >= TARGET}


def baseline_backtest(matches: list[Match], season: str, competition: str = '英超') -> dict:
    complete = { (row.id if competition == '欧冠' else (row.season, row.home, row.away)): row for row in matches
                 if row.competition == competition and row.finished and row.homeGoals is not None and row.awayGoals is not None }
    history = sorted(complete.values(), key=lambda row: (row.date, row.id))
    candidates = [row for row in history if row.season == season]
    correct = home_correct = majority_correct = count = 0
    brier = log_loss = 0.0
    dates = []
    confusion = {actual: {predicted: 0 for predicted in OUTCOMES} for actual in OUTCOMES}
    for fixture in candidates:
        prior = [row for row in history if row.date < fixture.date]
        model = poisson_baseline(prior, fixture.model_copy(update={
            'homeGoals': None, 'awayGoals': None, 'finished': False, 'started': False}))
        if model is None:
            continue
        values = [model.probabilities.home, model.probabilities.draw, model.probabilities.away]
        pick = OUTCOMES[max(range(3), key=lambda index: values[index])]
        actual = outcome(fixture)
        frequencies = Counter(outcome(row) for row in prior[-380:])
        majority = max(OUTCOMES, key=lambda label: frequencies[label])
        correct += pick == actual
        home_correct += actual == 'H'
        majority_correct += majority == actual
        count += 1
        dates.append(fixture.date)
        confusion[actual][pick] += 1
        brier += sum((value - (label == actual)) ** 2 for label, value in zip(OUTCOMES, values))
        log_loss -= math.log(max(values[OUTCOMES.index(actual)], 1e-15))
    return {**accuracy(correct, count), 'season': season, 'dateFrom': min(dates) if dates else None,
            'dateTo': max(dates) if dates else None, 'skipped': len(candidates) - count,
            'brierScore': brier / count if count else None, 'logLoss': log_loss / count if count else None,
            'alwaysHomeHitRate': home_correct / count if count else None,
            'priorMajorityHitRate': majority_correct / count if count else None,
            'confusion': confusion, 'method': '逐场使用比赛日期之前的资料；参数固定，不用测试赛果调参。'}


class Forecast(BaseModel):
    model_config = ConfigDict(frozen=True)
    league: str = 'epl'
    fixtureId: str
    season: str
    home: str
    away: str
    kickoff: str
    generatedAt: str
    snapshotAt: str
    pick: Literal['H', 'D', 'A']
    model: str
    rulesVersion: str
    analysis: dict | None = None


def record_forecast(report: MatchAnalysis, pick: str, model: str, rules_version: str, generated_at: str, league: str = 'epl', analysis: dict | None = None) -> bool:
    fixture = report.match
    if fixture is None or not fixture.kickoff:
        return False
    kickoff = datetime.fromisoformat(fixture.kickoff.replace('Z', '+00:00'))
    generated = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
    if generated.tzinfo is None or kickoff.tzinfo is None:
        return False
    if generated >= kickoff or fixture.finished or fixture.started:
        return False
    identity = fixture.id if league == 'ucl' else f'{fixture.season}|{fixture.home}|{fixture.away}'
    key = hashlib.sha256(identity.encode()).hexdigest()
    folder = league_path(STATE, league) / 'forecasts'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / f'{key}.json'
    forecast = Forecast(league=league, fixtureId=fixture.id, season=fixture.season, home=fixture.home, away=fixture.away,
                        kickoff=fixture.kickoff, generatedAt=generated_at, snapshotAt=report.dataUpdatedAt,
                        pick=pick, model=model, rulesVersion=rules_version, analysis=analysis)
    try:
        with path.open('x', encoding='utf-8') as destination:
            path.chmod(0o600)
            destination.write(forecast.model_dump_json())
    except FileExistsError:
        return False
    return True


def prospective_results(matches: list[Match], league: str = 'epl') -> dict:
    config = league_config(league)
    fixtures = {(row.id if league == 'ucl' else (row.season, row.home, row.away)): row for row in matches if row.competition == config.competition}
    correct = settled = recorded = invalid = 0
    for path in (league_path(STATE, league) / 'forecasts').glob('*.json'):
        try:
            forecast = Forecast.model_validate_json(path.read_text(encoding='utf-8'))
            if forecast.league != league:
                continue
            generated = datetime.fromisoformat(forecast.generatedAt.replace('Z', '+00:00'))
            kickoff = datetime.fromisoformat(forecast.kickoff.replace('Z', '+00:00'))
            if generated.tzinfo is None or kickoff.tzinfo is None or generated >= kickoff:
                invalid += 1
                continue
        except (OSError, ValueError):
            invalid += 1
            continue
        recorded += 1
        identity = forecast.fixtureId if league == 'ucl' else (forecast.season, forecast.home, forecast.away)
        fixture = fixtures.get(identity)
        if fixture and fixture.finished and fixture.homeGoals is not None and fixture.awayGoals is not None:
            settled += 1
            correct += forecast.pick == outcome(fixture)
    return {**accuracy(correct, settled), 'recorded': recorded, 'pending': recorded - settled, 'invalid': invalid,
            'method': '每场仅统计首次赛前生成的胜平负选择；同场更新保留首次记录，确认完赛后结算。'}


@lru_cache(maxsize=8)
def _cached_baseline(league: str, catalogue_stamp: int, live_stamp: int) -> dict:
    archive, _ = load_archive(league)
    return baseline_backtest(archive.matches, archive.season, league_config(league).competition)


def evaluation_status(league: str = 'epl') -> dict:
    archive, _ = load_archive(league)
    folder = league_path(PUBLIC, league)
    live_path = folder / 'live.json'
    baseline = _cached_baseline(league, (folder / 'data.json').stat().st_mtime_ns,
                                live_path.stat().st_mtime_ns if live_path.exists() else 0)
    return {'target': TARGET, 'market': '90 分钟胜／平／负（含补时）', 'baseline': baseline,
            'ai': prospective_results(archive.matches, league), 'updatedAt': datetime.now(timezone.utc).isoformat()}
