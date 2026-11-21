from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from football import racing_analysis as analysis
from football.files import publish


AT = datetime(2026, 11, 21, 16, 30, tzinfo=timezone.utc)


@pytest.fixture
def cards(tmp_path, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return AT.astimezone(tz) if tz else AT.replace(tzinfo=None)

    monkeypatch.setattr(analysis, 'datetime', Clock)
    monkeypatch.setattr(analysis, 'now', lambda: AT.isoformat())
    monkeypatch.setattr(analysis, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(analysis, 'FOLDER', tmp_path / 'racing')
    monkeypatch.setattr(analysis, 'read_control', lambda: {'enabled': True})
    monkeypatch.setattr(analysis, 'settings', lambda: SimpleNamespace(model='test-model'))
    monkeypatch.setattr(analysis, 'get_race', lambda ident: analysis.load(analysis.FOLDER / 'races' / (ident + '.json')))
    monkeypatch.setattr(analysis, 'assessment', lambda ident: {'runners': []})
    monkeypatch.setattr(analysis, 'simulation', lambda ident: {'status': 'insufficient'})
    monkeypatch.setattr(analysis, 'method_memory', lambda *args: {})
    rows = []
    for number in range(1, 4):
        race = {'id': f'2026-11-22-ST-{number}', 'date': '2026-11-22', 'raceNo': number,
                'status': 'scheduled', 'offTime': f'2026-11-22T0{number + 4}:00:00+00:00',
                'source': 'https://racing.hkjc.com/zh-hk/local/information/racecard',
                'entries': [{'id': f'HK_2023_J00{number}', 'name': f'测试马{number}', 'number': str(number)}]}
        publish(analysis.FOLDER / 'races' / (race['id'] + '.json'), race)
        publish(analysis.FOLDER / 'horses' / (race['entries'][0]['id'] + '.json'),
                {'profile': {'age': 4}, 'records': [], 'source': race['source']})
        rows.append(race)
    calls = []

    def response(rules, context, tokens):
        calls.append(context)
        horse = context['race']['entries'][0]['id']
        return {'summary': ['依据已提供的排位与档案作条件判断。', '没有即时赔率，暂不能比较赔率优势。'],
                'pick': horse, 'shortlist': [horse], 'details': [{'title': '资料范围', 'text': '仅使用已提供的来源，缺项保持未知。'}]}

    monkeypatch.setattr(analysis, 'request_json', response)
    return rows, calls


def test_automatic_batch_publishes_public_reports_without_admin_and_never_regenerates(cards):
    rows, calls = cards
    first = analysis.sync_forecasts('2026-11-22', limit=12)
    assert first['generated'] == first['attempted'] == 3 and first['failed'] == []
    reports = [analysis.public_status(r['id'])['reports']['pre'] for r in rows]
    assert all(r['issuedAt'] == AT.isoformat() and r['snapshotHash'] for r in reports)
    assert all('没有即时赔率' in r['summary'][1] for r in reports)
    assert all('pools' not in c['race'] and 'winOdds' not in c['race']['entries'][0] for c in calls)
    again = analysis.sync_forecasts('2026-11-22', limit=12)
    assert again['existing'] == 3 and again['attempted'] == again['generated'] == 0
    assert len(calls) == 3
    assert [analysis.public_status(r['id'])['reports']['pre'] for r in rows] == reports


def test_batch_uses_hong_kong_dates_and_bounded_fair_retry(cards, monkeypatch):
    rows, calls = cards
    original = analysis.request_json

    def response(rules, context, tokens):
        if context['race']['id'] == rows[0]['id']:
            raise ValueError('来源档案缺项')
        return original(rules, context, tokens)

    monkeypatch.setattr(analysis, 'request_json', response)
    first = analysis.sync_forecasts(limit=2)
    assert first['attempted'] == 2 and first['generated'] == 1
    assert first['failed'] == [{'raceId': rows[0]['id'], 'message': '来源档案缺项'}]
    second = analysis.sync_forecasts(limit=1)
    assert second['published'][0]['raceId'] == rows[2]['id']
    assert len(calls) == 2


def test_global_pause_blocks_batch_and_mid_request_publication(cards, monkeypatch):
    rows, calls = cards
    monkeypatch.setattr(analysis, 'read_control', lambda: {'enabled': False})
    assert analysis.sync_forecasts()['paused'] is True
    assert calls == []
    with pytest.raises(ValueError, match='暂停'):
        analysis.generate(rows[0]['id'], 'pre')
    monkeypatch.setattr(analysis, 'read_control', lambda: {'enabled': True})
    original = analysis.request_json

    def pause(rules, context, tokens):
        value = original(rules, context, tokens)
        monkeypatch.setattr(analysis, 'read_control', lambda: {'enabled': False})
        return value

    monkeypatch.setattr(analysis, 'request_json', pause)
    result = analysis.sync_forecasts(limit=3)
    assert result['generated'] == 0 and result['attempted'] == 1 and result['paused']
    assert '未发布' in result['failed'][0]['message']
    assert analysis.public_status(rows[0]['id'])['reports'] == {}


def test_batch_skips_closed_races_and_reports_exact_profile_shortage(cards):
    rows, calls = cards
    rows[0]['status'] = 'cancelled'
    rows[1]['offTime'] = AT.isoformat()
    for race in rows[:2]:
        publish(analysis.FOLDER / 'races' / (race['id'] + '.json'), race)
    publish(analysis.FOLDER / 'horses' / (rows[2]['entries'][0]['id'] + '.json'), {})
    result = analysis.sync_forecasts(limit=12)
    assert result['generated'] == 0 and result['attempted'] == 1 and calls == []
    failures = {r['raceId']: r['message'] for r in result['failed']}
    assert '开赛' in failures[rows[1]['id']]
    assert '已有 0/1 匹，需要至少 1 匹' in failures[rows[2]['id']]
    assert rows[0]['id'] not in failures


@pytest.mark.parametrize('status', ['cancelled', 'provisional', 'finished', 'running'])
def test_pre_forecast_requires_scheduled_status(cards, status):
    rows, _ = cards
    with pytest.raises(ValueError, match='开赛'):
        analysis.check_phase({**rows[0], 'status': status}, 'pre', AT)


def test_automatic_batch_reentry_is_rejected(cards):
    _, calls = cards
    analysis.FORECAST_LOCK.acquire()
    try:
        assert analysis.sync_forecasts()['busy'] is True
        assert calls == []
    finally:
        analysis.FORECAST_LOCK.release()


@pytest.mark.parametrize('release', ['normal', 'abrupt-exit'])
def test_independent_process_batches_exclude_concurrent_generation_and_release_lock(cards, tmp_path, release):
    script = '''
import json, os, sys
from datetime import datetime
from pathlib import Path
from football import racing_analysis as analysis
root, mode = Path(sys.argv[1]), sys.argv[2]
analysis.STATE, analysis.FOLDER = root / 'state', root / 'racing'
analysis.read_control = lambda: {'enabled': True}
def generate(ident, phase):
    with (root / 'model-calls.txt').open('a') as stream:
        stream.write(str(os.getpid()) + '\\n')
    if mode == 'hold':
        (root / 'ready.txt').write_text(str(os.getpid()))
        if sys.stdin.readline().strip() == 'terminate':
            os._exit(23)
    return {'reports': {'pre': {'issuedAt': '2026-11-21T16:30:00+00:00'}}}
analysis.generate = generate
result = analysis.sync_forecasts('2026-11-22', limit=1, at=datetime.fromisoformat('2026-11-21T16:30:00+00:00'))
print(json.dumps({'pid': os.getpid(), 'result': result}))
'''
    command = [sys.executable, '-c', script, str(tmp_path)]
    cwd = Path(__file__).resolve().parents[1]
    holder = subprocess.Popen([*command, 'hold'], cwd=cwd, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / 'ready.txt').exists() and time.monotonic() < deadline:
            if holder.poll() is not None:
                pytest.fail(holder.communicate()[1])
            time.sleep(.02)
        assert (tmp_path / 'ready.txt').exists(), 'First process did not acquire the batch lock'
        holder_pid = int((tmp_path / 'ready.txt').read_text())
        blocked = subprocess.run([*command, 'probe'], cwd=cwd, capture_output=True, text=True, timeout=10, check=True)
        competing = json.loads(blocked.stdout)
        assert competing['pid'] != holder_pid
        assert competing['result']['busy'] is True and competing['result']['attempted'] == 0
        assert (tmp_path / 'model-calls.txt').read_text().splitlines() == [str(holder_pid)]
        if release == 'abrupt-exit':
            holder.communicate(input='terminate\n', timeout=10)
            assert holder.returncode == 23
        else:
            output, errors = holder.communicate(input='continue\n', timeout=10)
            assert holder.returncode == 0, errors
            assert json.loads(output)['result']['generated'] == 1
        retry = subprocess.run([*command, 'probe'], cwd=cwd, capture_output=True, text=True, timeout=10, check=True)
        resumed = json.loads(retry.stdout)
        assert resumed['result']['generated'] == 1 and not resumed['result'].get('busy')
        assert (tmp_path / 'model-calls.txt').read_text().splitlines() == [str(holder_pid), str(resumed['pid'])]
        (tmp_path / 'process-contention.json').write_text(json.dumps({
            'release': release, 'holderPid': holder_pid, 'blocked': competing, 'afterRelease': resumed,
            'concurrentGenerationCalls': 1, 'modelCallsAfterRelease': 2}, indent=2))
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.communicate(timeout=10)
