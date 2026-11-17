import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from football import finance, market_sources, stock_service, stock_analysis


def test_asset_sources_keep_identity_delay_and_24h_basis():
    stamp = '2026-11-17T04:00:00+00:00'
    value = market_sources.parse_futures({'data': [
        {'s': 'COMEX:GC1!', 'd': ['GC1!', 'Gold Futures', 3900, 1.2, 'USD', 'delayed_streaming_600', 'futures']},
        {'s': 'NYMEX:CL1!', 'd': ['GC1!', 'wrong instrument', 80, 1, 'USD', 'streaming', 'futures']}]}, stamp)
    assert set(value) == {'gold'}
    assert value['gold']['quotedAt'] is None
    assert value['gold']['delaySeconds'] == 600
    btc = market_sources.parse_bitcoin({'price': '60000', 'time': '2026-11-17T03:59:00Z'}, {'open': '50000'}, stamp)
    assert btc['changePercent'] == pytest.approx(20)
    assert btc['changeBasis'] == '24 小时'
    with pytest.raises(ValueError):
        market_sources.parse_bitcoin({'price': '60000', 'time': '2026-11-18T03:59:00Z'}, {}, stamp)


def test_adjusted_history_rejects_mismatched_code_and_future_dates():
    payload = {'data': {'code': '00004', 'klines': ['2026-11-16,20,21,22,19,100', '2026-11-18,21,22,23,20,110']}}
    value = finance.normalize_em_history(payload, '00004', 'HKD', '2026-11-17T04:00:00+00:00')
    assert len(value['bars']) == 1
    assert value['bars'][0]['adjustedClose'] == 21
    with pytest.raises(ValueError, match='identity'):
        finance.normalize_em_history(payload, '00700', 'HKD', '2026-11-17T04:00:00+00:00')


def test_all_stock_details_respect_pause_and_global_fetch_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(stock_service, 'FOLDER', tmp_path)
    monkeypatch.setattr(stock_service, 'stock', lambda code: {'code': code, 'name': '非恒指股票'} if code == '00004' else None)
    monkeypatch.setattr(stock_service, 'read_control', lambda: {'enabled': False})
    monkeypatch.setattr(stock_service, 'refresh_company', lambda code: pytest.fail('Paused source must not be fetched'))
    assert stock_service.detail('00004', 'companies')['paused'] is True
    with pytest.raises(LookupError):
        stock_service.detail('../secret', 'companies')
    monkeypatch.setattr(stock_service, 'read_control', lambda: {'enabled': True})
    stock_service.DETAIL_LOCK.acquire()
    try:
        assert stock_service.detail('00004', 'companies')['pending'] is True
    finally:
        stock_service.DETAIL_LOCK.release()
    with pytest.raises(ValueError):
        stock_service.viewed_quotes(['../../secret'])


def test_forecast_accepts_line_wrapping_and_retains_cached_price_dates(tmp_path, monkeypatch):
    from football import reviews
    monkeypatch.setattr(reviews, 'watched_codes', lambda: ['00004'])
    monkeypatch.setattr(stock_analysis, 'STATE', tmp_path)
    monkeypatch.setattr(stock_analysis, 'stock', lambda code: {'code': code})
    monkeypatch.setattr(stock_analysis.ai, 'settings', lambda: SimpleNamespace(apiKey=SecretStr('test-key'), model='test'))
    stamp = datetime.now(timezone.utc)
    history = {'updatedAt': (stamp - timedelta(hours=2)).isoformat(), 'source': 'https://example.test/prices',
               'bars': [{'date': (stamp - timedelta(days=i)).date().isoformat(), 'adjustedClose': 100, 'close': 100} for i in range(50, 0, -1)]}
    monkeypatch.setattr(stock_analysis, 'load', lambda path: history if path.parent.name == 'history' else {})
    monkeypatch.setattr(stock_analysis, 'refresh_history', lambda code: (_ for _ in ()).throw(OSError('source offline')))
    def reply(rules, context, tokens):
        assert context['priceFreshness']['refreshFailed'] is True
        return {'summary': [' 短期\n观察。 ', '中期\r\n横盘。'], 'week': 'flat', 'quarter': 'flat', 'details': [{'title': '来源', 'text': '历史收盘'}]}
    monkeypatch.setattr(stock_analysis, 'request_json', reply)
    result = stock_analysis.generate('00004')
    assert result['latest']['summary'] == ['短期 观察。', '中期 横盘。']
    assert result['latest']['priceData']['refreshFailed'] is True
    assert result['evaluation']['week']['successRate'] is None
