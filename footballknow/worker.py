"""Independent refresh jobs on one shared cadence; failures retain the last published files.

Every dataset is checked every SYNC_SECONDS (60 by default). A job that needs longer than
one interval starts again as soon as it finishes; it never overlaps itself. A source that
keeps failing is retried with a growing pause so a refusal is not answered with more load.
"""
import logging
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from football.changelog import diff_live, merge_log
from football.files import PUBLIC, ROOT, publish, read_json
from football.leagues import league_path

LOG = logging.getLogger('football.sync')
STOP = threading.Event()
DEFAULT_SECONDS = 60
MINIMUM_SECONDS = 30
BACKOFF_CEILING = 900
LEAGUES = ['epl', 'laliga', 'ucl']

# name, script, group shown on the status page
JOBS: list[tuple[str, str, str]] = [
    ('live', 'sync_live.py', 'scores'), ('catalogue', 'sync_data.py', 'catalogue'),
    ('history', 'sync_history.py', 'history'), ('names', 'sync_names.py', 'names'),
    ('laliga-live', 'sync_laliga.py live', 'scores'), ('laliga-catalogue', 'sync_laliga.py catalogue', 'catalogue'),
    ('laliga-history', 'sync_laliga.py history', 'history'), ('laliga-names', 'sync_laliga.py names', 'names'),
    ('ucl-live', 'sync_ucl.py live', 'scores'), ('ucl-catalogue', 'sync_ucl.py catalogue', 'catalogue'),
    ('ucl-history', 'sync_ucl.py history', 'history'), ('ucl-names', 'sync_ucl.py names', 'names'),
    *[(f'{league}-{kind}', f'sync_rankings.py {league} {kind}', 'rankings')
      for league in LEAGUES for kind in ['standings', 'leaders']],
    *[(f'{league}-lineups', f'sync_match_details.py {league}', 'lineups') for league in LEAGUES],
    *[(f'{league}-odds', f'sync_odds.py {league}', 'odds') for league in LEAGUES],
    ('odds-official-checks', 'sync_odds.py sources', 'odds'),
]


class JobStatus(BaseModel):
    intervalSeconds: int
    group: str = ''
    running: bool = False
    lastAttempt: str | None = None
    lastSuccess: str | None = None
    nextAttempt: str | None = None
    lastDurationMs: int | None = None
    runs: int = 0
    failures: int = 0
    consecutiveFailures: int = 0
    ok: bool | None = None
    message: str = '等待首次同步'


@dataclass
class Job:
    script: str
    status: JobStatus
    due: float = 0
    started: float = 0
    future: Future[str] | None = None


def sync_seconds(environ: dict[str, str] | None = None) -> int:
    """The shared cadence; FOOTBALL_SYNC_SECONDS may lengthen it, never below the floor."""
    raw = (environ if environ is not None else os.environ).get('FOOTBALL_SYNC_SECONDS', '')
    return max(MINIMUM_SECONDS, int(raw)) if raw.isdigit() else DEFAULT_SECONDS


def interval_overrides(environ: dict[str, str] | None = None) -> dict[str, int]:
    """Per-job exceptions, e.g. FOOTBALL_SYNC_OVERRIDES="names=3600,odds-official-checks=86400"."""
    raw = (environ if environ is not None else os.environ).get('FOOTBALL_SYNC_OVERRIDES', '')
    known = {name for name, _, _ in JOBS}
    result = {}
    for item in raw.split(','):
        name, _, seconds = item.strip().partition('=')
        if name in known and seconds.isdigit():
            result[name] = max(MINIMUM_SECONDS, int(seconds))
    return result


def job_table(environ: dict[str, str] | None = None) -> dict[str, Job]:
    base, overrides = sync_seconds(environ), interval_overrides(environ)
    return {name: Job(script, JobStatus(intervalSeconds=overrides.get(name, base), group=group))
            for name, script, group in JOBS}


def retry_delay(interval: int, consecutive_failures: int) -> int:
    """Seconds from one start to the next: the interval, doubled per repeated failure."""
    if consecutive_failures <= 1:
        return interval
    return max(interval, min(BACKOFF_CEILING, interval * 2 ** (consecutive_failures - 1)))


LIVE_JOBS = {'live': 'epl', 'laliga-live': 'laliga', 'ucl-live': 'ucl'}


def read_live(league: str) -> dict:
    try:
        return read_json(league_path(PUBLIC, league) / 'live.json')
    except (OSError, ValueError):
        return {}


def run_job(script: str, league: str | None = None) -> str:
    """Run one refresh; for score jobs, append what changed to the public change record."""
    before = read_live(league) if league else None
    message = run_script(script)
    if league:
        stamp = datetime.now(timezone.utc).isoformat()
        entries = diff_live(before, read_live(league), league, stamp)
        if entries:
            path = league_path(PUBLIC, league) / 'changes.json'
            try:
                previous = read_json(path) if path.exists() else {}
            except (OSError, ValueError):
                previous = {}
            publish(path, merge_log(previous, entries, stamp))
    return message


def run_script(script: str) -> str:
    result = subprocess.run([sys.executable, *shlex.split(script)], cwd=ROOT,
                            capture_output=True, text=True, encoding='utf-8', timeout=600,
                            check=False)
    if result.returncode:
        raise OSError('上游读取或解析失败；保留最近一次成功资料')
    return result.stdout.strip()[-300:] or '同步完成'


def settle(job: Job, name: str, clock: float, stamp: datetime) -> None:
    """Record a finished run and schedule the next start relative to this run's start."""
    status = job.status
    try:
        status.message = job.future.result()
        status.ok = True
        status.lastSuccess = stamp.isoformat()
        status.consecutiveFailures = 0
        LOG.info('%s refreshed', name)
    except (OSError, subprocess.TimeoutExpired):
        status.ok = False
        status.failures += 1
        status.consecutiveFailures += 1
        status.message = '同步失败，已保留上次资料；稍后自动重试'
        LOG.warning('%s refresh failed (%s in a row)', name, status.consecutiveFailures)
    status.running = False
    status.runs += 1
    status.lastDurationMs = round((clock - job.started) * 1000)
    job.future = None
    job.due = max(clock, job.started + retry_delay(status.intervalSeconds, status.consecutiveFailures))
    status.nextAttempt = (stamp + timedelta(seconds=job.due - clock)).isoformat()


def snapshot(jobs: dict[str, Job], running: bool, started_at: str) -> dict:
    states = [job.status for job in jobs.values()]
    return {'running': running, 'heartbeat': datetime.now(timezone.utc).isoformat(), 'startedAt': started_at,
            'syncSeconds': sync_seconds(),
            'summary': {'total': len(states), 'ok': sum(s.ok is True for s in states),
                        'failed': sum(s.ok is False for s in states), 'pending': sum(s.ok is None for s in states)},
            'jobs': {name: job.status.model_dump() for name, job in jobs.items()}}


def stop_worker(signum: int, frame: object) -> None:
    STOP.set()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    jobs = job_table()
    started_at = datetime.now(timezone.utc).isoformat()
    published = 0.0
    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        while not STOP.is_set():
            clock, stamp, changed = time.monotonic(), datetime.now(timezone.utc), False
            for name, job in jobs.items():
                if job.future and job.future.done():
                    settle(job, name, clock, stamp)
                    changed = True
                if job.future is None and clock >= job.due:
                    job.status.running = True
                    job.status.lastAttempt = stamp.isoformat()
                    job.started = clock
                    job.future = executor.submit(run_job, job.script, LIVE_JOBS.get(name))
                    changed = True
            if changed or clock - published >= 5:
                publish(PUBLIC / 'sync-status.json', snapshot(jobs, True, started_at))
                published = clock
            STOP.wait(1)
    publish(PUBLIC / 'sync-status.json', snapshot(jobs, False, started_at))


if __name__ == '__main__':
    main()
