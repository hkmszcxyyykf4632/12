from datetime import datetime, timezone

import pytest
from football.market_reference import rate_changes, parse_bis, parse_taiwan, normalize_rankings


def test_basis_points_and_unchanged_dates_keep_last_change():
    r = rate_changes([('2026-01-01', .25), ('2026-01-02', 0), ('2026-01-03', 0)])
    assert r['rate'] == 0 and r['changeBp'] == -25
    assert r['changedAt'] == '2026-01-02' and r['asOf'] == '2026-01-03'


def test_official_rate_units_future_dates_and_taiwan_table():
    header = 'REF_AREA,FREQ,UNIT_MEASURE,UNIT_MULT,TIME_PERIOD,OBS_VALUE,SOURCE_REF,COMPILATION\n'
    r = parse_bis(header + 'US,D,368,0,2026-01-01,4,Fed,midpoint\nUS,D,368,0,2026-01-02,3.75,Fed,midpoint\nUS,D,368,0,2028-01-01,9,Fed,future', '2026-01-03T00:00:00+00:00')
    assert r['USD']['rate'] == 3.75 and r['USD']['changeBp'] == -25
    assert not parse_bis(header + 'US,D,368,3,2026-01-01,4,Fed,badunit', '2026-01-03')
    html = '<table><tr><td>2024/3/22</td><td>2</td><td>2.375</td><td>4.25</td></tr><tr><td>2023/3/24</td><td>1.875</td><td>2.25</td><td>4.125</td></tr></table>'
    t = parse_taiwan(html, '2026-11-17T00:00:00+00:00')
    assert t['rate'] == 2 and t['changeBp'] == 12.5 and t['changedAt'] == '2024-03-22'


def test_rankings_reject_wrong_identity_currency_future_and_reversed_range():
    cat = [{'code': '00700', 'name': '腾讯', 'currency': 'HKD'}]
    epoch = datetime(2026, 11, 17, 8, tzinfo=timezone.utc).timestamp()
    row = {'s': 'HKEX:700', 'd': ['700', 100, 2, 101, 99, 200, 50, 1000, 'HKD', 'stock', epoch]}
    r = normalize_rankings({'data': [row]}, cat, '2026-11-17T09:00:00+00:00')[0]
    assert r['high52'] == 200 and r['low52'] == 50 and r['tradeDate'] == '2026-11-17'
    for index, bad in [(0, '5'), (8, 'USD'), (10, epoch + 86400)]:
        values = row['d'].copy(); values[index] = bad
        assert not normalize_rankings({'data': [{'s': row['s'], 'd': values}]}, cat, '2026-11-17T09:00:00+00:00')
    row['d'][5:7] = [50, 200]
    r = normalize_rankings({'data': [row]}, cat, '2026-11-17T09:00:00+00:00')[0]
    assert r['high52'] is None and r['low52'] is None
