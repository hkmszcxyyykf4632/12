from concurrent.futures import Future
from datetime import datetime, timezone

import worker


def test_every_dataset_runs_on_the_sixty_second_cadence():
    jobs = worker.job_table({})
    assert len(jobs) == 25
    assert {job.status.intervalSeconds for job in jobs.values()} == {60}
    assert {job.status.group for job in jobs.values()} == {'scores', 'catalogue', 'history', 'names', 'rankings', 'lineups', 'odds'}


def test_cadence_can_be_lengthened_but_not_dropped_below_the_floor():
    assert worker.sync_seconds({'FOOTBALL_SYNC_SECONDS': '120'}) == 120
    assert worker.sync_seconds({'FOOTBALL_SYNC_SECONDS': '5'}) == worker.MINIMUM_SECONDS
    assert worker.sync_seconds({'FOOTBALL_SYNC_SECONDS': 'fast'}) == 60
    jobs = worker.job_table({'FOOTBALL_SYNC_OVERRIDES': 'names=3600, unknown=5,odds-official-checks=86400,live=1'})
    assert jobs['names'].status.intervalSeconds == 3600
    assert jobs['odds-official-checks'].status.intervalSeconds == 86400
    assert jobs['live'].status.intervalSeconds == worker.MINIMUM_SECONDS
    assert jobs['ucl-live'].status.intervalSeconds == 60


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
