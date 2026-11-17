import json
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

import worker
from football import finance, stock_analysis, sync_control
from football.rankings import leaders_from_facts


def test_pause_persists_and_corruption_stops_grabbing(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_control, 'STATE', tmp_path)
    assert sync_control.read_control()['enabled'] is True
    sync_control.set_control(False, 'admin01')
    assert sync_control.read_control()['enabled'] is False
    assert json.loads((tmp_path / 'sync-control.json').read_text())['changedBy'] == 'admin01'
    (tmp_path / 'sync-control.json').write_text('broken')
    assert sync_control.read_control()['enabled'] is False
    sync_control.set_control(True, 'admin02')
    assert sync_control.read_control()['enabled'] is True


def test_pause_terminates_an_active_child_and_resume_runs():
    worker.PAUSED.clear()
    worker.STOP.clear()
    timer = threading.Timer(.25, worker.PAUSED.set)
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(worker.SyncPaused):
            worker.run_script('-c "import time; time.sleep(30)"')
        assert time.monotonic() - started < 5
        with pytest.raises(worker.SyncPaused):
            worker.run_script('-c "print(123)"')
    finally:
        timer.cancel()
        worker.PAUSED.clear()
    assert worker.run_script('-c "print(123)"') == '123'
    assert worker.max_workers({}) == 2
    assert worker.max_workers({'FOOTBALL_SYNC_WORKERS': '999'}) == 8


def test_market_price_parser_does_not_invent_missing_prices():
    parts = [''] * 40
    for key, value in {1: '腾讯控股', 2: '00700', 3: '379', 4: '390.4', 5: '386.6',
                       30: '2026/11/17 10:43:45', 31: '-11.4', 32: '-2.92', 33: '386.6', 34: '376.8'}.items():
        parts[key] = value
    raw = 'v_hk00700="' + '~'.join(parts) + '";'
    parsed = finance.parse_tencent(raw, {'00700'}, '2026-11-17T03:00:00+00:00')
    assert parsed['00700']['price'] == 379
    assert parsed['00700']['currency'] == 'HKD'
    assert parsed['00700']['changePercent'] == -2.92
    assert finance.parse_tencent(raw, {'00005'}, '2026-11-17T03:00:00+00:00') == {}
    assert finance.parse_tencent(raw, {'00700'}, '2026-11-16T03:00:00+00:00') == {}
    assert finance.number(None) is None and finance.number(False) is None and finance.number(0) == 0


def test_financial_nested_reports_validate_identity(monkeypatch):
    monkeypatch.setattr(finance, 'request', lambda url: json.dumps({'success': True, 'result': {
        'pages': 1, 'data': [{'REPORT_LIST': [{'SECUCODE': '00700.HK', 'CURRENCY': '人民币'}]}]}}))
    result = finance.em_report('00700', 'metadata')
    assert result[0]['REPORT_LIST'][0]['CURRENCY'] == '人民币'
    with pytest.raises(ValueError, match='identity'):
        finance.em_report('00005', 'metadata')


def bars():
    return {'bars': [{'date': (datetime(2026, 1, 1) + timedelta(days=i)).date().isoformat(),
                      'adjustedClose': 100 + i, 'close': 100 + i} for i in range(80)]}


def test_forecast_scoring_uses_first_close_after_publication_and_full_horizon():
    record = {'issued_at': '2026-01-02T10:00:00+00:00', 'content': '{"week":"up","quarter":"up"}'}
    pending = stock_analysis.outcome(record, 'week', bars(), datetime(2026, 1, 8, tzinfo=timezone.utc))
    assert pending is None, 'current-day incomplete candle cannot settle a forecast'
    result = stock_analysis.outcome(record, 'week', bars(), datetime(2026, 1, 9, tzinfo=timezone.utc))
    assert result['baseDate'] == '2026-01-03'
    assert result['targetDate'] == '2026-01-08'
    assert result['correct'] is True
    assert result['return'] == pytest.approx(107 / 102 - 1)
    assert stock_analysis.outcome(record, 'quarter', bars(), datetime(2026, 2, 1, tzinfo=timezone.utc)) is None


def test_forecast_ledger_counts_all_and_no_fabricated_initial_accuracy(tmp_path, monkeypatch):
    monkeypatch.setattr(stock_analysis, 'STATE', tmp_path)
    with stock_analysis.connect() as connection:
        assert stock_analysis.evaluation(connection)['week']['successRate'] is None
        for i in range(2):
            connection.execute('INSERT INTO forecasts(code,day,version,issued_at,model,snapshot_hash,content) VALUES (?,?,?,?,?,?,?)',
                ('00700', str(i), 'v1', '2026-01-01T00:00:00+00:00', 'test', 'hash', '{"week":"up","quarter":"flat"}'))
        connection.execute('INSERT INTO outcomes VALUES (1,"week","2026-01-01","2026-01-08",0.1,"up",1,"2026-01-09")')
        assert stock_analysis.evaluation(connection)['week'] == {
            'published': 2, 'evaluated': 1, 'correct': 1, 'pending': 1, 'successRate': 1,
            'alwaysUpRate': 1, 'sessions': 5, 'threshold': .01}
        with pytest.raises(Exception):
            connection.execute('INSERT INTO forecasts(code,day,version,issued_at,model,snapshot_hash,content) VALUES (?,?,?,?,?,?,?)',
                ('00700', '0', 'v1', 'now', 'test', 'hash', '{}'))


def test_partial_player_rankings_keep_coverage_and_ties():
    catalogue = {'season': '2026/27', 'teams': [{'id': 1, 'name': 'A', 'cn': '甲'}]}
    facts = {'league': 'seriea', 'season': '2026/27', 'coveredMatches': 1, 'targetMatches': 2,
             'updatedAt': '2026-11-17T00:00:00+00:00', 'teams': {}, 'players': [
                 {'espnId': str(i), 'team': 'A', 'name': str(i), 'goals': 2, 'assists': 1, 'appearances': 1} for i in [1, 2]]}
    result = leaders_from_facts(catalogue, facts, 'seriea')
    assert [p['rank'] for p in result['boards']['scorers']] == [1, 1]
    assert result['coveredMatches'] == 1 and result['targetMatches'] == 2
    assert '非官方' in result['providerCadence']
