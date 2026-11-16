"""Independent scheduled refresh jobs; failures retain the last published files."""
import logging
import signal
import shlex
import subprocess
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic import BaseModel

from football.files import PUBLIC, ROOT, publish

LOG = logging.getLogger('football.sync')
STOP = threading.Event()


class JobStatus(BaseModel):
    intervalSeconds: int
    running: bool = False
    lastAttempt: str | None = None
    lastSuccess: str | None = None
    ok: bool | None = None
    message: str = '等待首次同步'


@dataclass
class Job:
    script: str
    status: JobStatus
    due: float = 0
    future: Future[str] | None = None


def run_job(script: str) -> str:
    result = subprocess.run([sys.executable, *shlex.split(script)], cwd=ROOT,
                            capture_output=True, text=True, encoding='utf-8', timeout=600,
                            check=False)
    if result.returncode:
        raise OSError('上游读取或解析失败；保留最近一次成功资料')
    return result.stdout.strip()[-300:] or '同步完成'


def stop_worker(signum: int, frame: object) -> None:
    STOP.set()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    jobs = {name:Job(script, JobStatus(intervalSeconds=interval)) for name,script,interval in [
        ('live','sync_live.py',60), ('catalogue','sync_data.py',3600),
        ('history','sync_history.py',3600), ('names','sync_names.py',86400),
        ('laliga-live','sync_laliga.py live',60), ('laliga-catalogue','sync_laliga.py catalogue',3600),
        ('laliga-history','sync_laliga.py history',3600), ('laliga-names','sync_laliga.py names',86400),
        ('ucl-live','sync_ucl.py live',60), ('ucl-catalogue','sync_ucl.py catalogue',3600),
        ('ucl-history','sync_ucl.py history',3600), ('ucl-names','sync_ucl.py names',86400),
        *[(f'{league}-{kind}', f'sync_rankings.py {league} {kind}', interval)
          for league in ['epl', 'laliga', 'ucl'] for kind, interval in [('standings', 60), ('leaders', 300)]],
        *[(f'{league}-lineups', f'sync_match_details.py {league}', 300) for league in ['epl','laliga','ucl']],
        *[(f'{league}-odds', f'sync_odds.py {league}', 300) for league in ['epl','laliga','ucl']],
        ('odds-official-checks','sync_odds.py sources',86400)]}
    with ThreadPoolExecutor(max_workers=25) as executor:
        while not STOP.is_set():
            now = datetime.now(timezone.utc).isoformat()
            for name, job in jobs.items():
                if job.future and job.future.done():
                    try:
                        job.status.message = job.future.result()
                        job.status.ok = True
                        job.status.lastSuccess = now
                        LOG.info('%s refreshed',name)
                    except (OSError, subprocess.TimeoutExpired):
                        job.status.ok = False
                        job.status.message = '同步失败，已保留上次资料；稍后自动重试'
                        LOG.warning('%s refresh failed',name)
                    job.status.running = False
                    job.future = None
                    job.due = time.monotonic() + (job.status.intervalSeconds if job.status.ok else min(300,job.status.intervalSeconds))
                if job.future is None and time.monotonic() >= job.due:
                    job.status.running = True
                    job.status.lastAttempt = now
                    job.future = executor.submit(run_job,job.script)
            publish(PUBLIC / 'sync-status.json', {'running':True,'heartbeat':now,
                    'jobs':{name:job.status.model_dump() for name,job in jobs.items()}})
            STOP.wait(5)
    publish(PUBLIC / 'sync-status.json', {'running':False,'heartbeat':datetime.now(timezone.utc).isoformat(),
            'jobs':{name:job.status.model_dump() for name,job in jobs.items()}})


if __name__ == '__main__':
    main()
