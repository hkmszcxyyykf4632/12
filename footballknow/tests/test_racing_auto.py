from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sqlite3
import sys
import time
import copy
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


def quoted_card(cards):
    rows, _ = cards
    race = copy.deepcopy(rows[0])
    race['source'] += '?racedate=2026%2F11%2F22&Racecourse=ST&RaceNo=1'
    race['pools'] = [{'type': 'WIN', 'checkedAt': '2026-11-21T16:29:00+00:00',
                     'sourceUpdatedAt': '2026-11-21T16:28:00+00:00',
                     'quotes': [{'combination': '1', 'value': '1.0'}]}]
    return race


def test_market_input_keeps_one_point_zero_binds_horse_and_marks_retained_quotes(cards):
    race = quoted_card(cards)
    race['pools'][0].update(quoteRetained=True, checkedAt='2026-11-21T16:20:00+00:00', sourceUpdatedAt='2026-11-21T16:19:00+00:00')
    value = analysis.market_snapshot(race, AT)
    pool = value['pools'][0]
    assert value['status'] == 'available' and value['missingPools'] == ['PLA', 'QIN']
    assert pool['retained'] and pool['stale']
    assert pool['quotes'] == [{'combination': '1', 'value': '1.0', 'horses': [
        {'id': race['entries'][0]['id'], 'number': '1', 'name': race['entries'][0]['name']}]}]


@pytest.mark.parametrize('invalid', ['future-source', 'future-check', 'after-off', 'wrong-pool-race',
                                     'wrong-card-source', 'wrong-date', 'unknown-horse', 'withdrawn', 'no-timezone', 'non-numeric'])
def test_market_input_rejects_unattributable_or_future_quotes(cards, invalid):
    race = quoted_card(cards)
    pool = race['pools'][0]
    if invalid == 'future-source':
        pool['sourceUpdatedAt'] = '2026-11-21T16:31:00+00:00'
    elif invalid == 'future-check':
        pool['checkedAt'] = '2026-11-21T16:31:00+00:00'
    elif invalid == 'after-off':
        race['offTime'] = AT.isoformat()
    elif invalid == 'wrong-pool-race':
        pool['raceId'] = '2026-11-22-ST-2'
    elif invalid == 'wrong-card-source':
        race['source'] = race['source'].replace('RaceNo=1', 'RaceNo=2')
    elif invalid == 'wrong-date':
        race['date'] = '2026-11-23'
    elif invalid == 'unknown-horse':
        pool['quotes'][0]['combination'] = '9'
    elif invalid == 'withdrawn':
        race['entries'][0]['withdrawn'] = True
    elif invalid == 'no-timezone':
        pool['checkedAt'] = '2026-11-21T16:29:00'
    else:
        pool['quotes'][0]['value'] = 'NaN'
    assert analysis.market_snapshot(race, AT)['pools'] == []


def test_future_generation_passes_only_verified_market_input_and_saves_snapshot(cards, monkeypatch):
    _, calls = cards
    race = quoted_card(cards)
    race['entries'][0]['winOdds'] = 99
    publish(analysis.FOLDER / 'races' / (race['id'] + '.json'), race)
    original = analysis.request_json

    def response(rules, context, tokens):
        value = original(rules, context, tokens)
        value['summary'][1] = '已有保存的独赢报价；没有完整赔率走势，不能推断资金流。'
        return value

    monkeypatch.setattr(analysis, 'request_json', response)
    report = analysis.generate(race['id'], 'pre')['reports']['pre']
    assert calls[0]['marketSnapshot']['status'] == 'available'
    assert calls[0]['race']['pools'] == report['marketSnapshot']['pools']
    assert 'winOdds' not in calls[0]['race']['entries'][0]


@pytest.mark.parametrize('claim', ['暂无赛前独赢赔率', '暫無賽前獨贏賠率', '没有独赢赔率', '沒有獨贏賠率'])
def test_false_missing_odds_claim_gets_one_bounded_model_correction(cards, monkeypatch, claim):
    race = quoted_card(cards)
    replies = []

    def response(rules, context, tokens):
        replies.append(context)
        return {'summary': ['首选以已提供资料为依据。', claim if len(replies) == 1 else '已有独赢保存报价，没有完整赔率走势。'],
                'pick': race['entries'][0]['id'], 'shortlist': [race['entries'][0]['id']],
                'details': [{'title': '资料', 'text': '保留来源报价，不推断资金流。'}]}

    monkeypatch.setattr(analysis, 'request_json', response)
    context = {'phase': 'pre', 'marketSnapshot': analysis.market_snapshot(race, AT)}
    result = analysis.model_report(context, race, 'pre')
    assert len(replies) == 2 and '已有经身份及时间核对' in replies[1]['validationIssue']
    assert '已有独赢' in result['summary'][1]
    bad = copy.deepcopy(result)
    bad['details'][0]['text'] = claim
    with pytest.raises(ValueError, match='独赢报价'):
        analysis.validate_factual_claims(bad, context)


def test_new_forecast_cannot_claim_no_saved_forecast_but_post_review_can(cards):
    rows, _ = cards
    report = analysis.generate(rows[0]['id'], 'pre')['reports']['pre']
    report['summary'] = ['本站未保存本場賽前預測。', '资料仍待更新。']
    with pytest.raises(ValueError, match='当前正在发布'):
        analysis.validate_factual_claims(report, {'phase': 'pre'})
    assert analysis.validate_factual_claims(report, {'phase': 'post'}) == report


def test_append_only_correction_preserves_original_row_and_original_preparation(cards, monkeypatch, tmp_path):
    rows, calls = cards
    ident = rows[0]['id']
    preparation = {'runners': [{'id': rows[0]['entries'][0]['id'], 'name': '测试马1', 'activity': '维持常规操练', 'known': True}]}
    monkeypatch.setattr(analysis, 'assessment', lambda value: copy.deepcopy(preparation))
    original = analysis.generate(ident, 'pre')['reports']['pre']
    with analysis.connect() as db:
        before = dict(db.execute("SELECT * FROM reports WHERE race_id=? AND phase='pre'", (ident,)).fetchone())
    race = quoted_card(cards)
    publish(analysis.FOLDER / 'races' / (ident + '.json'), race)
    class CorrectionClock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = AT + timedelta(minutes=10)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    monkeypatch.setattr(analysis, 'datetime', CorrectionClock)
    monkeypatch.setattr(analysis, 'assessment', lambda value: pytest.fail('Must not replace historical preparation'))
    corrected = analysis.append_fact_amendment(ident, '核对赔率及晨操分类。')['reports']['pre']
    assert len(calls) == 1
    assert {k: v for k, v in corrected.items() if k != 'amendments'} == original
    amendment = corrected['amendments'][0]
    assert amendment['marketSnapshot']['pools'][0]['quotes'][0]['value'] == '1.0'
    assert amendment['preparationSnapshot'] == preparation
    assert amendment['originalReportHash'] and amendment['issuedAt'] == (AT + timedelta(minutes=10)).isoformat()
    assert original['issuedAt'] == AT.isoformat()
    assert len(analysis.append_fact_amendment(ident, '核对赔率及晨操分类。')['reports']['pre']['amendments']) == 1
    with analysis.connect() as db:
        after = dict(db.execute("SELECT * FROM reports WHERE race_id=? AND phase='pre'", (ident,)).fetchone())
    assert before == after
    assert 'amendments' not in analysis.public_status(rows[1]['id'])['reports'].get('pre', {})
    (tmp_path / 'append-only-proof.json').write_text(json.dumps({'originalBefore': before, 'originalAfter': after,
                                                               'amendment': amendment}, ensure_ascii=False), encoding='utf-8')


def test_correction_requires_saved_forecast_and_stops_at_off_time_or_pause(cards, monkeypatch):
    rows, _ = cards
    with pytest.raises(ValueError, match='没有已保存'):
        analysis.append_fact_amendment(rows[0]['id'], '事实更正')
    analysis.generate(rows[0]['id'], 'pre')
    monkeypatch.setattr(analysis, 'read_control', lambda: {'enabled': False})
    with pytest.raises(ValueError, match='暂停'):
        analysis.append_fact_amendment(rows[0]['id'], '事实更正')
    monkeypatch.setattr(analysis, 'read_control', lambda: {'enabled': True})
    rows[0]['offTime'] = AT.isoformat()
    publish(analysis.FOLDER / 'races' / (rows[0]['id'] + '.json'), rows[0])
    with pytest.raises(ValueError, match='开赛'):
        analysis.append_fact_amendment(rows[0]['id'], '事实更正')


def test_legacy_missing_preparation_remains_missing_in_correction(cards, monkeypatch):
    rows, _ = cards
    ident = rows[0]['id']
    content = {'summary': ['旧版赛前判断。', '旧版没有保存晨操快照。'], 'pick': rows[0]['entries'][0]['id'],
               'shortlist': [rows[0]['entries'][0]['id']], 'details': []}
    with analysis.connect() as db:
        db.execute('INSERT INTO reports VALUES (?,?,?,?,?,?)',
                   (ident, 'pre', AT.isoformat(), 'legacy-model', 'legacy-hash', json.dumps(content)))
    monkeypatch.setattr(analysis, 'assessment', lambda value: pytest.fail('Do not invent historical preparation'))
    correction = analysis.append_fact_amendment(ident, '仅核对可取得的事实。')['reports']['pre']['amendments'][0]
    assert correction['preparationSnapshot'] is None


def test_fact_amendment_database_rejects_update_and_delete(cards):
    rows, _ = cards
    ident = rows[0]['id']
    analysis.generate(ident, 'pre')
    correction = analysis.append_fact_amendment(ident, '保留可审计的事实更正。')['reports']['pre']['amendments'][0]
    with analysis.connect() as db:
        with pytest.raises(sqlite3.IntegrityError, match='append-only'):
            db.execute('UPDATE fact_amendments SET reason=? WHERE id=?', ('改写历史', correction['id']))
        with pytest.raises(sqlite3.IntegrityError, match='append-only'):
            db.execute('DELETE FROM fact_amendments WHERE id=?', (correction['id'],))
    assert analysis.public_status(ident)['reports']['pre']['amendments'] == [correction]
