from copy import deepcopy
from datetime import date, timedelta

import pytest

from football.stock_review_evidence import build_dossier


def inputs(count=7):
    start = date(2026, 1, 1)
    bars = [{'date': (start + timedelta(days=i)).isoformat(), 'adjustedClose': 100 + i,
             'open': 150 + i, 'high': 160 + i, 'low': 140 + i, 'close': 155 + i,
             'volume': 1000} for i in range(count)]
    original = {'id': 41, 'code': '00700', 'issuedAt': '2026-01-01T09:00:00+00:00',
                'week': 'up', 'quarter': 'down', 'summary': ['固定原文']}
    history = {'code': '00700', 'symbol': '0700.HK', 'updatedAt': '2026-05-01T08:30:00+00:00',
               'source': 'https://example.test/00700', 'provider': 'test', 'bars': bars}
    result = {'code': '00700', 'close': bars[-1]}
    return original, history, bars, result


def build(data):
    return build_dossier('00700', *data)


def test_identity_and_original_are_preserved_without_mutation():
    data = inputs()
    before = deepcopy(data)
    dossier = build(data)
    assert dossier['identity'] == '00700|2026-01-07|41'
    assert dossier['original'] == data[0]
    assert data == before
    for index in (0, 1, 3):
        wrong = deepcopy(data)
        wrong[index]['code'] = '00005'
        with pytest.raises(ValueError, match='identity mismatch'):
            build(wrong)
    wrong = deepcopy(data)
    wrong[1]['symbol'] = '0005.HK'
    with pytest.raises(ValueError, match='symbol mismatch'):
        build(wrong)


def test_hk_issue_day_and_confirmed_cutoff_exclude_same_day_and_future():
    original, history, bars, result = inputs(10)
    original['issuedAt'] = '2026-01-01T20:00:00+00:00'
    result['close'] = bars[5]
    dossier = build((original, history, bars, result))
    prices = dossier['priceContext']
    assert prices['issuedDay'] == '2026-01-02'
    assert [row['date'] for row in prices['path']] == [bar['date'] for bar in bars[2:6]]
    assert prices['baselineDate'] == '2026-01-03'
    assert len(dossier['timeline']) == 4
    original['issuedAt'] = '2026-01-01T20:00:00'
    with pytest.raises(ValueError, match='timezone-aware'):
        build((original, history, bars, result))


@pytest.mark.parametrize('count,week_ready,quarter_ready', [(6, False, False), (7, True, False), (64, True, False), (65, True, True)])
def test_exact_five_and_sixtythree_session_maturity(count, week_ready, quarter_ready):
    prices = build(inputs(count))['priceContext']
    for horizon, ready, sessions in [('week', week_ready, 5), ('quarter', quarter_ready, 63)]:
        outcome = prices['horizons'][horizon]
        assert outcome['status'] == ('已到期' if ready else '观察中')
        assert outcome['requiredSessions'] == sessions
        if ready:
            assert outcome['return'] == pytest.approx((101 + sessions) / 101 - 1)
        else:
            assert outcome['return'] is None
        assert (outcome['correct'] is not None) == ready
    assert prices['periodReturn'] is not None


def test_adjusted_path_daily_return_and_drawdown_do_not_invent_adjusted_ohlc():
    data = inputs(4)
    for bar, value in zip(data[2], [90, 100, 120, 96]):
        bar['adjustedClose'] = value
    prices = build(data)['priceContext']
    assert prices['periodReturn'] == pytest.approx(-.04)
    assert prices['maxDrawdown'] == pytest.approx(-.2)
    assert prices['path'][0]['dailyReturn'] == pytest.approx(100 / 90 - 1)
    assert prices['path'][-1]['dailyReturn'] == pytest.approx(-.2)
    assert prices['path'][-1]['sourceOHLC']['close'] == 158
    assert prices['path'][-1]['adjustedClose'] == 96
    assert prices['horizons']['week']['correct'] is None


def test_volume_average_uses_twenty_prior_sessions_never_current_or_future():
    data = inputs(24)
    data[2][20]['volume'] = 3000
    data[2][21]['volume'] = 9000000
    data[3]['close'] = data[2][20]
    prices = build(data)['priceContext']
    assert prices['path'][-1]['prior20VolumeAverage'] == 1000
    assert prices['path'][-1]['volumeRatioToPrior20'] == 3
    assert prices['path'][-1]['volume'] == 3000
    assert prices['path'][0]['volumeRatioToPrior20'] is None
    assert prices['volumeUnit'].startswith('未知')
    data[1]['volumeUnit'] = '手（100股）'
    assert build(data)['priceContext']['volumeUnit'] == '手（100股）'


@pytest.mark.parametrize('invalid', [None, -1, float('nan'), float('inf'), True, '1000'])
def test_invalid_prior_volume_never_becomes_a_ratio(invalid):
    data = inputs(21)
    data[2][0]['volume'] = invalid
    assert build(data)['priceContext']['path'][-1]['volumeRatioToPrior20'] is None


def test_zero_volumes_are_valid_but_zero_baseline_cannot_be_divided():
    data = inputs(21)
    for bar in data[2]:
        bar['volume'] = 0
    last = build(data)['priceContext']['path'][-1]
    assert last['volume'] == 0 and last['prior20VolumeAverage'] == 0
    assert last['volumeRatioToPrior20'] is None


@pytest.mark.parametrize('invalid', [None, -1, float('nan'), float('inf'), True, '1000'])
def test_invalid_current_volume_stays_unknown(invalid):
    data = inputs(21)
    data[2][-1]['volume'] = invalid
    last = build(data)['priceContext']['path'][-1]
    assert last['volume'] is None
    assert last['volumeRatioToPrior20'] is None


def test_mainland_identity_and_available_units_are_preserved():
    original, history, bars, result = inputs()
    for item in (original, history, result):
        item['code'] = '600519'
    history.update(symbol='600519.SS', market='cn', volumeUnit='手（100股）')
    dossier = build_dossier('600519', original, history, bars, result)
    assert dossier['priceContext']['code'] == '600519'
    assert dossier['priceContext']['volumeUnit'] == '手（100股）'


def test_missing_prices_and_null_volume_are_explicit_and_unavailable_context_is_not_causal():
    data = inputs(8)
    data[2][2]['adjustedClose'] = None
    data[2][3]['adjustedClose'] = float('nan')
    data[2][-1]['volume'] = None
    dossier = build(data)
    assert len(dossier['priceContext']['path']) == 5
    assert dossier['priceContext']['horizons']['week']['status'] == '观察中'
    assert dossier['priceContext']['path'][-1]['volume'] is None
    gaps = '\n'.join(dossier['gaps'])
    for term in ['复权收盘', '基准指数历史', '首次公开时间', '抓取时间', '交易所日历', '单位未知']:
        assert term in gaps
    assert dossier['sources']
    assert all(fact['sourceIds'] for fact in dossier['facts'])


def test_duplicate_dates_rejected_and_no_postissue_price_has_no_invented_outcome():
    data = inputs(1)
    dossier = build(data)
    assert dossier['priceContext']['path'] == []
    assert dossier['priceContext']['periodReturn'] is None
    data[2].append(deepcopy(data[2][0]))
    with pytest.raises(ValueError, match='Duplicate'):
        build(data)
