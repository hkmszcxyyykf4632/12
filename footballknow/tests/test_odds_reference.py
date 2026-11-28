from copy import deepcopy
from datetime import timedelta

from football import football_forecasts as ff, odds_signals as signals
from football.odds_forecast import build
from football.odds_reference import preferred
from test_football_forecasts import AT, sandbox


def macau_quotes(row, unchanged=False):
    return [{**deepcopy(q), 'provider': '澳门彩票有限公司', 'source': 'https://www.macau-slot.com/content/soccer/',
             'via': 'macau-slot', 'line': -.5 if unchanged else q['line'],
             'fetchedAt': (AT-timedelta(minutes=1)).isoformat()} for q in row['quotes']]


def test_macau_has_priority_even_when_secondary_quote_is_newer(sandbox):
    sandbox['quotes'] += macau_quotes(sandbox)
    result = signals.analyse(sandbox, AT)
    assert preferred(result['primary']['after'])
    assert result['referencePolicy']['usingPreferred']
    assert preferred(ff.quote_for(sandbox, AT))
    assert all(preferred(c['after']) for c in result['changes'])


def test_unchanged_macau_does_not_borrow_secondary_movement(sandbox):
    sandbox['quotes'] += macau_quotes(sandbox, unchanged=True)
    result = signals.analyse(sandbox, AT)
    assert not result['eligible']
    assert result['referencePolicy']['usingPreferred']


def test_macau_latest_cannot_borrow_draftkings_opening(sandbox):
    current = macau_quotes(sandbox)[0]
    sandbox['quotes'].append(current)
    result = signals.analyse(sandbox, AT)
    assert not result['eligible']


def test_stale_macau_keeps_actual_secondary_provider_and_disclosure(sandbox, monkeypatch):
    old = macau_quotes(sandbox)
    for q in old: q['fetchedAt'] = (AT-timedelta(minutes=16)).isoformat()
    sandbox['quotes'] += old
    result = signals.analyse(sandbox, AT)
    assert not result['referencePolicy']['usingPreferred']
    assert result['primary']['provider'] == 'Example'
    assert '不能代表澳门盘' in result['referencePolicy']['note']
    monkeypatch.setattr(ff, 'build_prediction', build)
    assert ff.generate(sandbox, 'initial')
    report = ff.status(sandbox)['stages']['initial']['report']
    assert report['quote']['provider'] == 'Example'
    assert '不能代表澳门盘' in report['details'][0]['text']
    assert not report['oddsReference']['usingPreferred']


def test_non_asian_signal_requires_same_provider_and_feed(sandbox):
    quote = sandbox['quotes'][0]
    assert ff.quote_for(sandbox, AT, {**quote, 'provider': 'Macau Slot'}) is None
    assert ff.quote_for(sandbox, AT, {**quote, 'via': 'other'}) is None
    assert ff.quote_for(sandbox, AT, quote) == quote


def test_provider_matching_does_not_relabel_averages():
    assert preferred({'provider': 'Macau-Slot'})
    assert preferred({'provider': '澳門彩票有限公司'})
    assert not preferred({'provider': '澳门市场平均'})
    assert not preferred({'provider': 'DraftKings'})
