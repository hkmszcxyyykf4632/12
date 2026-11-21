import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from football import reviews, evaluation, analysis, match_details, stock_analysis
from football.professional_prompts import professional_rules, protocol_metadata


def test_protocols_are_substantial_distinct_and_output_contract_is_last():
    metadata = protocol_metadata()
    assert len(metadata['projects']) == 6
    assert min(p['characters'] for p in metadata['projects']) >= 10000
    assert len({p['sha256'] for p in metadata['projects']}) == 6
    assert professional_rules('stocks', 'OUTPUT CONTRACT').endswith('OUTPUT CONTRACT')


def test_fixed_report_never_regenerates_and_uses_domain_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    calls = []
    def reply(rules, context, tokens):
        assert len(rules) > 10000 and '比特币' in rules
        calls.append(context)
        return {'summary': ['第一段结论。', '第二段依据。'], 'details': [{'title': '来源', 'text': '已给价格。'}]}
    monkeypatch.setattr(reviews, 'request_json', reply)
    a = reviews.report('crypto', 'bitcoin|day', {'price': 10}, True)
    b = reviews.report('crypto', 'bitcoin|day', {'price': 20}, True)
    assert a == b and len(calls) == 1
    assert reviews.report('crypto', 'not-created', {}, False) is None


def test_watchlist_scope_blocks_generation_before_ai(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    monkeypatch.setattr(reviews, 'stock', lambda c: {'code': c} if c == '00700' else None)
    with pytest.raises(ValueError, match='关注'):
        stock_analysis.generate('00700')
    reviews.save_watchlist(['00700', '00700'])
    assert reviews.watched_codes() == ['00700']
    reviews.require_watched('00700')
    with pytest.raises(ValueError):
        reviews.save_watchlist(['../../secret'])
    reviews.save_watchlist([])
    with pytest.raises(ValueError):
        reviews.require_watched('00700')


def test_close_data_requires_both_close_time_and_fresh_snapshot():
    history = {'updatedAt': '2026-11-17T07:00:00+00:00', 'bars': [
        {'date': '2026-11-16', 'adjustedClose': 100}, {'date': '2026-11-17', 'adjustedClose': 105},
        {'date': '2026-11-18', 'adjustedClose': 110}]}
    assert len(reviews.closed_bars(history, datetime(2026, 11, 17, 7, 30, tzinfo=timezone.utc))) == 1
    assert len(reviews.closed_bars(history, datetime(2026, 11, 17, 9, tzinfo=timezone.utc))) == 1
    history['updatedAt'] = '2026-11-17T08:20:00+00:00'
    assert len(reviews.closed_bars(history, datetime(2026, 11, 17, 9, tzinfo=timezone.utc))) == 2


def test_stock_daily_change_does_not_count_as_mature_prediction(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    monkeypatch.setattr(reviews, 'stock', lambda c: {'code': c})
    history = {'updatedAt': '2026-11-17T09:00:00+00:00', 'bars': [
        {'date': '2026-11-16', 'adjustedClose': 100}, {'date': '2026-11-17', 'adjustedClose': 110}]}
    monkeypatch.setattr(reviews, 'load', lambda p: history if p.parent.name == 'history' else {})
    original = {'id': 1, 'issuedAt': '2026-11-16T02:00:00+00:00', 'week': 'up', 'quarter': 'up'}
    monkeypatch.setattr(stock_analysis, 'public_status', lambda c: {'forecasts': [original]})
    result = reviews.stock_review('00700', at=datetime(2026, 11, 17, 10, tzinfo=timezone.utc))
    assert result['dailyReturn'] == pytest.approx(.1)
    assert result['outcomes']['week']['correct'] is None
    assert result['outcomes']['week']['status'] == '观察中'
    assert result['outcomes']['quarter']['status'] == '观察中'


def test_football_review_preserves_pre_match_content_and_no_retrospective_pick(tmp_path, monkeypatch):
    monkeypatch.setattr(reviews, 'STATE', tmp_path)
    monkeypatch.setattr(evaluation, 'STATE', tmp_path)
    match = analysis.Match(id='m1', date='2026-11-17', kickoff='2026-11-17T10:00:00+00:00',
                           home='A', away='B', season='2026/27', competition='英超', finished=False)
    fixture = analysis.MatchAnalysis(generatedAt='2026-11-16T10:00:00+00:00', dataUpdatedAt='2026-11-16T09:00:00+00:00',
                                    liveUpdatedAt=None, team=analysis.Club(id=1, name='A', cn='甲'), checklist=[], match=match)
    assert evaluation.record_forecast(fixture, 'H', 'm', 'v', fixture.generatedAt, analysis={'summary': ['固定原文一', '固定原文二']})
    assert not evaluation.record_forecast(fixture, 'A', 'm', 'v2', fixture.generatedAt, analysis={'summary': ['改写']})
    monkeypatch.setattr(analysis, 'load_archive', lambda league: (SimpleNamespace(matches=[match]), None))
    with pytest.raises(ValueError, match='未完场'):
        reviews.football_review('m1', generate=True)
    match = match.model_copy(update={'finished': True, 'homeGoals': 0, 'awayGoals': 1})
    monkeypatch.setattr(match_details, 'get_detail', lambda *args, **kwargs: None)
    result = reviews.football_review('m1')
    assert result['correct'] is False and result['original']['pick'] == 'H'
    assert result['original']['analysis']['summary'][0] == '固定原文一'
    assert result['review']['analysisStatus'] == 'limited'
    assert result['review']['drivers'] == []
