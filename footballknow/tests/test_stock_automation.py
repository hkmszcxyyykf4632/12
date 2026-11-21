from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from football import stock_analysis, stock_automation, reviews, evidence_reviews
from football.files import publish


AT = datetime(2026, 11, 23, 2, tzinfo=timezone.utc)


@pytest.fixture
def automatic_env(tmp_path, monkeypatch):
    state, folder = tmp_path / 'state', tmp_path / 'finance'
    watched = ['00700', '600000']
    items = {'00700': {'code': '00700', 'currency': 'HKD'},
             '600000': {'code': '600000', 'market': 'cn', 'currency': 'CNY'},
             '00005': {'code': '00005', 'currency': 'HKD'}}
    enabled = {'enabled': True}
    calls = []
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return AT.astimezone(tz) if tz else AT.replace(tzinfo=None)
    for module in [stock_analysis, stock_automation]:
        monkeypatch.setattr(module, 'STATE', state)
        monkeypatch.setattr(module, 'FOLDER', folder)
        monkeypatch.setattr(module, 'stock', lambda code: items.get(code))
    monkeypatch.setattr(stock_analysis, 'datetime', Clock)
    monkeypatch.setattr(stock_analysis, 'now', lambda: (AT + timedelta(seconds=30)).isoformat())
    monkeypatch.setattr(stock_automation, 'read_control', lambda: enabled)
    monkeypatch.setattr(stock_automation, 'watched_codes', lambda: list(watched))
    monkeypatch.setattr(reviews, 'watched_codes', lambda: list(watched))
    monkeypatch.setattr(stock_analysis.ai, 'settings', lambda: SimpleNamespace(apiKey=SecretStr('test'), model='test'))
    monkeypatch.setattr(evidence_reviews, 'method_memory', lambda *args: [])
    quotes = {}
    for code, item in items.items():
        quote = {'code': code, 'price': 100, 'currency': item['currency'], 'fetchedAt': AT.isoformat(),
                 'source': 'https://example.test/' + code}
        quote.update({'quotedAt': None, 'barAt': (AT - timedelta(minutes=30)).isoformat()} if len(code) == 6
                     else {'quotedAt': (AT - timedelta(minutes=5)).isoformat()})
        quotes[code] = quote
        bars = [{'date': (AT - timedelta(days=i)).date().isoformat(), 'adjustedClose': 100 + i}
                for i in range(70, 0, -1) if (AT - timedelta(days=i)).weekday() < 5]
        publish(folder / 'history' / (code + '.json'), {'code': code, 'currency': item['currency'], 'updatedAt': AT.isoformat(),
                                                     'source': quote['source'], 'bars': bars})
    publish(folder / 'quotes.json', {'quotes': {code: q for code, q in quotes.items() if len(code) == 5}})
    publish(folder / 'cn-quotes.json', {'quotes': {'600000': quotes['600000']}})
    monkeypatch.setattr(stock_automation, 'viewed_quotes', lambda codes: {'quotes': {c: quotes[c] for c in codes}})
    def reply(rules, context, tokens):
        calls.append(context)
        return {'summary': ['短期取向与已核对数据。', '中期条件与风险。'], 'week': 'up', 'quarter': 'flat',
                'details': [{'title': '已完成交易日', 'text': '使用已完成的复权收盘资料。'}]}
    monkeypatch.setattr(stock_analysis, 'request_json', reply)
    return SimpleNamespace(state=state, folder=folder, watched=watched, enabled=enabled, quotes=quotes, calls=calls)


def test_only_watched_stocks_publish_automatically_once_and_are_publicly_readable(automatic_env):
    env = automatic_env
    assert stock_automation.refresh(AT) == {'generated': 1, 'code': '00700'}
    assert stock_automation.refresh(AT) == {'generated': 1, 'code': '600000'}
    assert stock_automation.refresh(AT) == {'generated': 0}
    assert len(env.calls) == 2
    assert stock_analysis.public_status('00005')['latest'] is None
    latest = stock_analysis.public_status('00700')['latest']
    assert latest['publicationMode'] == 'watched-stock-automatic'
    assert latest['issuedAt'] == (AT + timedelta(seconds=30)).isoformat()
    assert latest['tradingReceipt']['quotedAt'] == env.quotes['00700']['quotedAt']
    assert latest['week'] == 'up' and latest['quarter'] == 'flat'
    assert latest['outcomes'] == {}
    assert all(bar['date'] < '2026-11-23' for bar in env.calls[0]['prices'])
    assert stock_analysis.public_status('00700')['evaluation']['week']['successRate'] is None


@pytest.mark.parametrize('moment', [datetime(2026, 11, 21, 2, tzinfo=timezone.utc),
                                     datetime(2026, 11, 23, 1, tzinfo=timezone.utc),
                                     datetime(2026, 11, 23, 8, tzinfo=timezone.utc)])
def test_weekends_preopen_and_after_close_do_not_publish(automatic_env, moment):
    assert stock_automation.refresh(moment)['generated'] == 0
    assert automatic_env.calls == []


def test_pause_and_missing_key_do_not_fetch_or_publish(automatic_env, monkeypatch):
    env = automatic_env
    monkeypatch.setattr(stock_automation, 'viewed_quotes', lambda codes: pytest.fail('must not fetch'))
    env.enabled['enabled'] = False
    assert stock_automation.refresh(AT)['paused'] is True
    env.enabled['enabled'] = True
    monkeypatch.setattr(stock_analysis.ai, 'settings', lambda: SimpleNamespace(apiKey=SecretStr('')))
    assert stock_automation.refresh(AT)['generated'] == 0
    assert env.calls == []


@pytest.mark.parametrize('change', [
    {'quotedAt': '2026-11-20T08:00:00+00:00'},
    {'fetchedAt': '2026-11-20T02:00:00+00:00'},
    {'quotedAt': '2026-11-23T03:00:00+00:00'},
    {'code': '00005'}, {'price': 0}, {'currency': 'USD'},
])
def test_holiday_stale_future_and_wrong_identity_quotes_are_not_trade_day_evidence(automatic_env, change):
    quote = {**automatic_env.quotes['00700'], **change}
    with pytest.raises(ValueError):
        stock_automation.automatic_snapshot('00700', AT, quote)
    assert automatic_env.calls == []


def test_cn_daily_bar_is_day_evidence_but_never_claimed_as_tick_time(automatic_env):
    quote = automatic_env.quotes['600000']
    assert stock_automation.automatic_snapshot('600000', AT, quote)['quotedAt'] is None
    with pytest.raises(ValueError):
        stock_automation.automatic_snapshot('600000', AT, {**quote, 'barAt': '2026-11-20T01:30:00+00:00'})
    assert stock_automation.session_window('600000', AT.replace(hour=7)) is False
    assert stock_automation.session_window('00700', AT.replace(hour=7)) is True


@pytest.mark.parametrize('interrupt', ['pause', 'unfollow', 'close'])
def test_rechecks_pause_following_and_time_after_model_before_publishing(automatic_env, monkeypatch, interrupt):
    env = automatic_env
    original_reply = stock_analysis.request_json
    def reply(*args):
        value = original_reply(*args)
        if interrupt == 'pause':
            env.enabled['enabled'] = False
        elif interrupt == 'unfollow':
            env.watched.remove('00700')
        else:
            monkeypatch.setattr(stock_analysis, 'now', lambda: AT.replace(hour=8).isoformat())
        return value
    monkeypatch.setattr(stock_analysis, 'request_json', reply)
    assert stock_automation.refresh(AT)['generated'] == 0
    assert stock_analysis.public_status('00700')['latest'] is None


def test_failure_rotates_to_other_watched_stock_and_uses_cooldown(automatic_env, monkeypatch):
    env = automatic_env
    original_reply = stock_analysis.request_json
    def reply(rules, context, tokens):
        if context['stock']['code'] == '00700':
            raise ValueError('invalid response')
        return original_reply(rules, context, tokens)
    monkeypatch.setattr(stock_analysis, 'request_json', reply)
    assert stock_automation.refresh(AT) == {'generated': 0, 'checked': 1, 'code': '00700', 'message': '本股资料或分析暂不可用，稍后自动重试。'}
    assert stock_automation.refresh(AT) == {'generated': 1, 'code': '600000'}
    assert stock_automation.refresh(AT) == {'generated': 0}
    assert stock_analysis.public_status('00700')['latest'] is None


@pytest.mark.parametrize('problem', ['identity', 'too_few'])
def test_history_identity_or_insufficient_completed_prices_cannot_publish(automatic_env, monkeypatch, problem):
    env = automatic_env
    publish(env.folder / 'history' / '00700.json', {'code': '00005' if problem == 'identity' else '00700', 'updatedAt': AT.isoformat(), 'bars': []})
    monkeypatch.setattr(stock_analysis, 'refresh_history', lambda code: {'code': '00005', 'bars': []})
    assert stock_automation.refresh(AT)['generated'] == 0
    assert env.calls == []
    assert stock_analysis.public_status('00700')['latest'] is None


def test_quote_fetched_after_worker_start_is_checked_against_current_time(automatic_env, monkeypatch):
    env = automatic_env
    moments = iter([AT, AT + timedelta(seconds=2)])
    class AdvancingClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return next(moments)
    monkeypatch.setattr(stock_automation, 'datetime', AdvancingClock)
    refreshed = {**env.quotes['00700'], 'fetchedAt': (AT + timedelta(seconds=1)).isoformat()}
    monkeypatch.setattr(stock_automation, 'viewed_quotes', lambda codes: {'quotes': {'00700': refreshed}})
    generated = []
    def generate(code, automatic=False):
        generated.append(code)
        return {'latest': {'issuedAt': (AT + timedelta(seconds=3)).isoformat(), 'version': stock_analysis.VERSION}}
    monkeypatch.setattr(stock_analysis, 'generate', generate)
    assert stock_automation.refresh() == {'generated': 1, 'code': '00700'}
    assert generated == ['00700']
