from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Event

import pytest

import worker
from football import football_forecasts as ff
from football.files import publish
from test_football_forecasts import AT, content, fixture, research, sandbox


@pytest.mark.parametrize('minutes,expected', [(121, 0), (120, 1), (119, 1)])
def test_final_checks_start_at_two_hours(sandbox, monkeypatch, minutes, expected):
    row = fixture(minutes / 60)
    row['quotes'].append({**row['quotes'][0], 'phase': 'opening', 'line': -.5})
    publish(ff.PUBLIC / 'daily-football.json', {'matches': [row]})
    assert ff.generate(row, 'initial')
    calls = []
    monkeypatch.setattr(ff, 'generate', lambda row, stage: calls.append(stage) or True)
    assert ff.refresh()['checked'] == expected
    assert calls == (['final'] if expected else [])
    assert ff.status(row)['finalCheckAt'] == (AT + timedelta(minutes=minutes - 120)).isoformat()


def test_unconfirmed_lineups_at_two_hours_do_not_call_model(sandbox, monkeypatch):
    row = fixture(2)
    monkeypatch.setattr(ff, 'research_row', lambda row: research(row, False))
    monkeypatch.setattr(ff, 'build_prediction', lambda *args: pytest.fail('unconfirmed lineup cannot reach model'))
    assert not ff.generate(row, 'final')
    value = ff.status(row)['stages']['final']
    assert value['report'] is None
    assert value['retryAt'] == (AT + timedelta(seconds=60)).isoformat()


def test_failed_initial_does_not_block_fresh_confirmed_final(sandbox, monkeypatch):
    def failure(*args):
        raise OSError('provider unavailable')
    monkeypatch.setattr(ff, 'build_prediction', failure)
    assert not ff.generate(sandbox, 'initial')
    monkeypatch.setattr(ff, 'build_prediction', lambda *args: content())
    assert ff.refresh()['generated'] == 1
    value = ff.status(sandbox)
    assert value['stages']['initial']['report'] is None
    assert value['stages']['final']['report']['lineupsConfirmed'] is True


def test_waiting_earliest_final_yields_to_unchecked_final(sandbox, monkeypatch):
    rows = [deepcopy(sandbox) for _ in range(3)]
    for index, row in enumerate(rows):
        row['id'] = str(123 + index)
    publish(ff.PUBLIC / 'daily-football.json', {'matches': rows})
    for row in rows:
        assert ff.generate(row, 'initial')
    ff.defer(rows[0], 'final', '等待双方正式首发及最新资料')
    monkeypatch.setattr(ff, 'now', lambda: AT + timedelta(seconds=61))
    calls = []
    monkeypatch.setattr(ff, 'generate', lambda row, stage: calls.append((row['id'], stage)) or False)
    assert ff.refresh()['checked'] == 2
    assert calls == [('124', 'final'), ('125', 'final')]


def test_final_failure_retries_once_per_minute_and_claim_still_locks(sandbox, monkeypatch):
    calls = []
    def failure(*args):
        calls.append(1)
        raise OSError('provider unavailable')
    monkeypatch.setattr(ff, 'build_prediction', failure)
    for minute in range(4):
        monkeypatch.setattr(ff, 'now', lambda minute=minute: AT + timedelta(minutes=minute))
        assert not ff.generate(sandbox, 'final')
        assert not ff.generate(sandbox, 'final')
        assert len(calls) == minute + 1
        assert ff.status(sandbox)['stages']['final']['retryAt'] == (AT + timedelta(minutes=minute + 1)).isoformat()
    later = AT + timedelta(minutes=4)
    assert ff.claim(sandbox, 'final', later)
    assert not ff.claim(sandbox, 'final', later + timedelta(minutes=1))


def test_dedicated_forecast_runs_while_shared_worker_is_occupied(monkeypatch):
    jobs = worker.job_table({})
    jobs['daily-football'].due = 10
    release = Event()
    monkeypatch.setattr(worker, 'run_job', lambda *args: 'forecast checked')
    monkeypatch.setattr(worker, 'PAUSED', Event())
    monkeypatch.setattr(worker, 'STOP', Event())
    monkeypatch.setattr(worker, 'max_workers', lambda: 2)
    with ThreadPoolExecutor(max_workers=1) as shared, ThreadPoolExecutor(max_workers=1) as dedicated:
        background = shared.submit(release.wait, 5)
        jobs['live'].future = background
        try:
            assert worker.dispatch_forecast(jobs, dedicated, 1, AT)
            assert jobs['football-forecasts'].future.result(timeout=1) == 'forecast checked'
            assert not background.done()
            assert not worker.dispatch_forecast(jobs, dedicated, 2, AT)
        finally:
            release.set()


def test_forecast_lane_respects_pause_and_due_time(monkeypatch):
    jobs = worker.job_table({})
    monkeypatch.setattr(worker, 'PAUSED', Event())
    monkeypatch.setattr(worker, 'STOP', Event())
    with ThreadPoolExecutor(max_workers=1) as dedicated:
        worker.PAUSED.set()
        assert not worker.dispatch_forecast(jobs, dedicated, 1, AT)
        worker.PAUSED.clear()
        jobs['football-forecasts'].due = 10
        jobs['daily-football'].due = 10
        assert not worker.dispatch_forecast(jobs, dedicated, 1, AT)


def test_single_worker_budget_does_not_start_forecast_while_another_job_runs(monkeypatch):
    jobs = worker.job_table({})
    monkeypatch.setattr(worker, 'max_workers', lambda: 1)
    monkeypatch.setattr(worker, 'PAUSED', Event())
    monkeypatch.setattr(worker, 'STOP', Event())
    jobs['daily-football'].future = Future()
    with ThreadPoolExecutor(max_workers=1) as dedicated:
        assert not worker.dispatch_forecast(jobs, dedicated, 1, AT)
    assert worker.snapshot(jobs, True, AT.isoformat())['maxConcurrentJobs'] == 1


def test_worker_failure_does_not_add_fifteen_minute_forecast_backoff():
    job = worker.job_table({})['football-forecasts']
    for _ in range(5):
        job.future = Future()
        job.future.set_exception(OSError('process failed'))
        worker.settle(job, 'football-forecasts', 1, AT)
        assert job.due == 60


@pytest.mark.parametrize('competition,accepted', [('700', True), ('740', True), ('730', True), ('720', True), ('775', True), ('710', False)])
def test_forecast_scope_is_four_leagues_and_champions_league(sandbox, monkeypatch, competition, accepted):
    row = deepcopy(sandbox)
    row['competitionId'] = competition
    publish(ff.PUBLIC / 'daily-football.json', {'matches': [row]})
    calls = []
    monkeypatch.setattr(ff, 'generate', lambda row, stage: calls.append(stage) or True)
    assert ff.supported(row) is accepted
    assert ff.refresh()['checked'] == int(accepted)
    assert calls == (['initial'] if accepted else [])


def test_priority_lane_refreshes_daily_before_forecast_even_after_daily_failure(monkeypatch):
    jobs = worker.job_table({})
    monkeypatch.setattr(worker, 'max_workers', lambda: 2)
    monkeypatch.setattr(worker, 'PAUSED', Event())
    monkeypatch.setattr(worker, 'STOP', Event())
    calls = []
    def run(script, *args):
        calls.append(script)
        if script == 'sync_daily_football.py':
            raise OSError('score source unavailable')
        return 'forecast checked'
    monkeypatch.setattr(worker, 'run_job', run)
    with ThreadPoolExecutor(max_workers=1) as dedicated:
        assert worker.dispatch_forecast(jobs, dedicated, 1, AT)
        with pytest.raises(OSError):
            jobs['daily-football'].future.result(timeout=1)
        assert jobs['football-forecasts'].future is None
        worker.settle(jobs['daily-football'], 'daily-football', 100, AT)
        assert jobs['daily-football'].due == 100
        assert worker.dispatch_forecast(jobs, dedicated, 101, AT)
        assert jobs['football-forecasts'].future.result(timeout=1) == 'forecast checked'
        assert calls == ['sync_daily_football.py', 'sync_football_forecasts.py']


def test_champions_league_result_uses_ucl_catalogue(monkeypatch):
    from football import match_details, match_centre_research
    row = fixture()
    row['competitionId'] = '775'
    seen = []
    def catalogue(league):
        seen.append(league)
        return None, [{'finished': True, 'homeGoals': 2, 'awayGoals': 0}]
    monkeypatch.setattr(match_details, 'match_catalogue', catalogue)
    monkeypatch.setattr(match_centre_research, 'same_fixture', lambda *args: True)
    result = ff.resolved_result(row)
    assert seen == ['ucl']
    assert result['state'] == 'finished'
