from concurrent.futures import Future
from datetime import datetime, timezone

import worker


def test_live_data_is_frequent_and_profile_work_is_bounded():
    jobs = worker.job_table({})
    assert len(jobs) == 82
    assert jobs['football-rounds'].status.intervalSeconds == 300
    assert jobs["stock-forecasts"].status.intervalSeconds == 120
    assert jobs["racing-forecasts"].status.intervalSeconds == 300
    assert jobs['evidence-reviews'].status.intervalSeconds == 300
    assert jobs['finance-backfill'].status.intervalSeconds == 300
    assert jobs['racing-research'].status.intervalSeconds == 300
    assert jobs['football-forecasts'].status.intervalSeconds == 60
    assert jobs['daily-research'].status.intervalSeconds == 300
    assert jobs['finance-cn'].status.intervalSeconds == 300
    assert jobs['finance-us'].status.intervalSeconds == 300
    assert jobs['finance-volume'].status.intervalSeconds == 300
    assert jobs['daily-football'].status.intervalSeconds == 60
    assert jobs['racing-live'].status.intervalSeconds == 60
    assert jobs['racing-people'].status.intervalSeconds == 1800
    assert jobs['racing-directory'].status.intervalSeconds == 86400
    assert jobs['portal-news'].status.intervalSeconds == 300
    assert jobs['laliga-photos'].status.intervalSeconds == 3600
    assert jobs['racing-meetings'].status.intervalSeconds == 300
    assert jobs['racing-horses'].status.intervalSeconds == 600
    assert jobs['finance-catalogue'].status.intervalSeconds == 86400
    assert jobs['finance-evaluation'].status.intervalSeconds == 120
    assert {job.status.intervalSeconds for job in jobs.values()} == {60, 120, 300, 600, 900, 1800, 3600, 21600, 86400}
    assert {job.status.group for job in jobs.values()} == {'scores', 'catalogue', 'history', 'names', 'rankings', 'lineups', 'odds', 'news', 'profiles', 'finance', 'racing'}


def test_cadence_can_be_lengthened_but_not_dropped_below_the_floor():
    assert worker.sync_seconds({'FOOTBALL_SYNC_SECONDS': '120'}) == 120
    assert worker.sync_seconds({'FOOTBALL_SYNC_SECONDS': '5'}) == worker.MINIMUM_SECONDS
    assert worker.sync_seconds({'FOOTBALL_SYNC_SECONDS': 'fast'}) == 60
    jobs = worker.job_table({'FOOTBALL_SYNC_OVERRIDES': 'names=3600, unknown=5,odds-official-checks=86400,live=1'})
    assert jobs['names'].status.intervalSeconds == 3600
    assert jobs['odds-official-checks'].status.intervalSeconds == 86400
    assert jobs['live'].status.intervalSeconds == worker.MINIMUM_SECONDS
    assert jobs['ucl-live'].status.intervalSeconds == 900


def test_repeated_failures_wait_longer_and_recover():
    assert [worker.retry_delay(60, n) for n in range(6)] == [60, 60, 120, 240, 480, 900]
    assert worker.retry_delay(3600, 4) == 3600


def finished(result=None, error=None):
    future = Future()
    future.set_exception(error) if error else future.set_result(result)
    return future


def test_next_start_is_measured_from_the_previous_start():
    stamp = datetime(2026, 11, 16, tzinfo=timezone.utc)
    job = worker.Job('x.py', worker.JobStatus(intervalSeconds=60), started=100.0, future=finished('done'))
    worker.settle(job, 'x', 105.0, stamp)
    assert job.due == 160.0 and job.status.ok and job.status.lastDurationMs == 5000
    assert job.status.nextAttempt == '2026-11-16T00:00:55+00:00'
    slow = worker.Job('x.py', worker.JobStatus(intervalSeconds=60), started=100.0, future=finished('done'))
    worker.settle(slow, 'x', 190.0, stamp)
    assert slow.due == 190.0, 'a run longer than the interval restarts at once, without overlap'


def test_failures_back_off_then_reset_on_success():
    stamp = datetime(2026, 11, 16, tzinfo=timezone.utc)
    job = worker.Job('x.py', worker.JobStatus(intervalSeconds=60))
    for expected in [60, 120, 240]:
        job.started, job.future = 0.0, finished(error=OSError('refused'))
        worker.settle(job, 'x', 1.0, stamp)
        assert job.due == expected and job.status.ok is False
    job.started, job.future = 0.0, finished('ok')
    worker.settle(job, 'x', 1.0, stamp)
    assert job.due == 60 and job.status.consecutiveFailures == 0 and job.status.failures == 3 and job.status.runs == 4
    summary = worker.snapshot({'x': job}, True, stamp.isoformat())['summary']
    assert summary == {'total': 1, 'ok': 1, 'failed': 0, 'pending': 0}


def test_slow_catalogues_do_not_reenter_the_minute_queue():
    jobs = worker.job_table({})
    for name in ['names', 'laliga-names', 'ucl-names', 'seriea-names', 'bundesliga-names']:
        assert jobs[name].status.intervalSeconds == 86400
    assert jobs['history'].status.intervalSeconds == 21600
    assert jobs['ucl-catalogue'].status.intervalSeconds == 3600
    assert jobs['epl-odds'].status.intervalSeconds == 300
    assert jobs['live'].status.intervalSeconds == 900
    assert jobs['daily-football'].status.intervalSeconds == 60
    assert jobs['football-forecasts'].status.intervalSeconds == 60


def test_restart_preserves_fresh_work_but_not_stale_or_interrupted_work():
    stamp = datetime(2026, 11, 23, 7, 0, tzinfo=timezone.utc)
    jobs = worker.job_table({})
    recent = dict(intervalSeconds=60, lastAttempt='2026-11-23T06:30:00+00:00',
                  lastSuccess='2026-11-23T06:33:00+00:00', runs=4, ok=True)
    previous = {'jobs': {'names': recent, 'finance-backfill': recent,
                        'ucl-names': {**recent, 'running': True},
                        'daily-football': recent}}
    worker.restore_schedule(jobs, previous, 100, stamp)
    assert jobs['names'].due == 100 + 86400 - 1800
    assert jobs['names'].status.runs == 4
    assert jobs['finance-backfill'].due == 100
    assert jobs['ucl-names'].due == 100 and not jobs['ucl-names'].status.running
    assert jobs['ucl-names'].future is None
    assert jobs['daily-football'].due == 0


def test_restart_uses_current_override_and_retains_failure_backoff():
    stamp = datetime(2026, 11, 23, 7, 0, tzinfo=timezone.utc)
    jobs = worker.job_table({'FOOTBALL_SYNC_OVERRIDES': 'names=3600'})
    recent = dict(intervalSeconds=60, lastAttempt='2026-11-23T06:59:00+00:00', ok=False,
                  failures=2, consecutiveFailures=2)
    worker.restore_schedule(jobs, {'jobs': {'names': recent, 'finance-backfill': recent}}, 100, stamp)
    assert jobs['names'].due == 100 + 3600 - 60
    assert jobs['finance-backfill'].due == 100 + 600 - 60
    assert jobs['finance-backfill'].status.consecutiveFailures == 2


def test_bad_or_future_saved_schedule_does_not_delay_collection():
    stamp = datetime(2026, 11, 23, 7, 0, tzinfo=timezone.utc)
    jobs = worker.job_table({})
    for value in [None, [], {'jobs': []}, {'jobs': {'names': {}}},
                  {'jobs': {'names': {'lastAttempt': 'bad'}}},
                  {'jobs': {'names': {'lastAttempt': '2026-11-24T00:00:00+00:00'}}},
                  {'jobs': {'names': {'lastAttempt': '2026-11-23T06:59:00'}}}]:
        worker.restore_schedule(jobs, value, 100, stamp)
        assert jobs['names'].due == 0
