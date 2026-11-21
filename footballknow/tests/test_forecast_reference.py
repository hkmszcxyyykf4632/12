from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from football import forecast_reference as ref
from football import football_forecasts as ff
from test_football_forecasts import research, sandbox

AT = datetime(2026, 11, 21, 4, tzinfo=timezone.utc)


def row():
    return {'id': '123', 'competitionId': '700', 'kickoff': '2026-11-21T12:30:00+00:00',
            'teams': {'home': {'id': '1', 'name': 'Manchester City', 'label': '曼城'},
                      'away': {'id': '2', 'name': 'Fulham', 'label': '富勒姆'}}}


def snapshot():
    return {'fetchedAt': AT.isoformat(), 'sourceUpdatedAt': (AT-timedelta(hours=18)).isoformat(),
            'source': ref.FIXTURES, 'rows': [{'Div': 'E0', 'Date': '21/11/2026', 'Time': '12:30',
            'HomeTeam': 'Man City', 'AwayTeam': 'Fulham', 'AHh': '-1.5', 'B365AHH': '2', 'B365AHA': '1.85'}]}


@pytest.mark.parametrize('fault', ['opponent', 'time', 'duplicate', 'finished', 'old', 'future'])
def test_reference_rejects_mismatched_or_undated_fixtures(fault):
    saved = snapshot()
    if fault == 'opponent': saved['rows'][0]['AwayTeam'] = 'Chelsea'
    if fault == 'time': saved['rows'][0]['Time'] = '15:00'
    if fault == 'duplicate': saved['rows'].append(deepcopy(saved['rows'][0]))
    if fault == 'finished': saved['rows'][0]['FTR'] = 'H'
    if fault == 'old': saved['sourceUpdatedAt'] = (AT-timedelta(days=8)).isoformat()
    if fault == 'future': saved['sourceUpdatedAt'] = (AT+timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError): ref.match_fixture(row(), saved, AT)


def test_aliases_and_british_summer_time_are_explicit():
    assert ref.team_key('Spurs', 'epl') == ref.team_key('Tottenham', 'epl')
    assert ref.team_key('Ipswich Town', 'epl') == ref.team_key('Ipswich', 'epl')
    assert ref.team_key('Coventry City', 'epl') == ref.team_key('Coventry', 'epl')
    assert ref.kickoff({'Date': '21/08/2026', 'Time': '15:00'}).hour == 14


def test_reference_preserves_file_time_and_never_claims_live_lineups(monkeypatch):
    base = snapshot()
    games = []
    for name in ['Man City', 'Fulham']:
        for day in range(1, 11):
            games.append({'Div': 'E0', 'Date': f'{day:02}/11/2026', 'Time': '15:00',
                          'HomeTeam': name, 'AwayTeam': 'Chelsea', 'FTHG': '2', 'FTAG': '1', 'FTR': 'H'})
    monkeypatch.setattr(ref, 'csv_snapshot', lambda url, at: base if url == ref.FIXTURES else {**base, 'source': url, 'rows': games})
    result = ref.initial_reference(row(), AT)
    assert result['quote']['phase'] == 'preclosing'
    assert result['quote']['sourceUpdatedAt'] == base['sourceUpdatedAt']
    assert result['quote']['quotedAt'] is None
    assert len(result['research']['teams']['home']['form']['matches']) == 10
    assert not result['research']['teams']['home']['lineup']['confirmed']


def test_history_excludes_future_wrong_division_and_result_mismatch():
    good = {'Div': 'E0', 'Date': '10/11/2026', 'Time': '15:00', 'HomeTeam': 'Man City', 'AwayTeam': 'Fulham',
            'FTHG': '2', 'FTAG': '1', 'FTR': 'H'}
    rows = [good, {**good, 'Date': '22/11/2026'}, {**good, 'Div': 'E1'}, {**good, 'FTR': 'A'}]
    assert len(ref.history(rows, 'Manchester City', 'epl', AT, ref.FIXTURES)) == 1


def test_initial_uses_dated_reference_but_final_still_requires_live_source(sandbox, monkeypatch):
    from test_football_forecasts import AT as clock
    sandbox['updatedAt'] = (clock-timedelta(days=1)).isoformat()
    evidence = {'research': research(sandbox, False), 'quote': {**sandbox['quotes'][0], 'phase': 'preclosing'},
                'source': ref.FIXTURES, 'sourceUpdatedAt': sandbox['updatedAt'], 'checkedAt': clock.isoformat(), 'note': '赛前参考'}
    calls = []
    monkeypatch.setattr(ff, 'initial_reference', lambda r, at: calls.append(r['id']) or evidence)
    assert ff.generate(sandbox, 'initial')
    assert ff.status(sandbox)['stages']['initial']['report']['reference']['source'] == ref.FIXTURES
    assert not ff.generate(sandbox, 'final')
    assert calls == ['123']
