from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from football import football_forecasts as ff
from football.files import publish

AT = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)


def fixture(hours=1):
    return {'id': '123', 'competitionId': '700', 'kickoff': (AT+timedelta(hours=hours)).isoformat(),
            'state': 'scheduled', 'started': False, 'finished': False, 'scoreScope': '90分钟含补时',
            'teams': {s: {'id': str(i), 'label': s, 'name': s, 'goals': None} for i, s in enumerate(['home', 'away'], 1)},
            'updatedAt': AT.isoformat(), 'source': 'https://example.test/match',
            'quotes': [{'market': 'asian-handicap', 'phase': 'latest', 'inPlay': False, 'line': -.75,
                        'prices': {'H': 1.9, 'A': 1.95}, 'provider': 'Example', 'fetchedAt': AT.isoformat(), 'source': 'https://example.test/odds'}]}


def research(row, confirmed=True):
    return {'eventId': row['id'], 'kickoff': row['kickoff'], 'pregame': {'capturedAt': AT.isoformat()},
            'teams': {s: {'teamId': t['id'], 'lineup': {'confirmed': confirmed,
                      'players': [{'id': f'{s}{i}'} for i in range(11)] if confirmed else []},
                      'form': {'matches': [{'date': (AT-timedelta(days=i+2)).isoformat(), 'goalsFor': 2,
                      'goalsAgainst': 1, 'homeAway': s} for i in range(8)]}} for s, t in row['teams'].items()}}


def content():
    return {'score': [2, 1], 'asianSide': 'H', 'summary': ['主队让球方向。', '近期进球较稳定，首发变化另核对。'],
            'details': [{'title': '近况', 'text': '依据已收录赛前往绩。'}]}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    row = fixture()
    row['quotes'].append({**row['quotes'][0], 'phase': 'opening', 'line': -.5})
    monkeypatch.setattr(ff, 'STATE', tmp_path/'state')
    monkeypatch.setattr(ff.odds_signals, 'STATE', tmp_path/'state')
    monkeypatch.setattr(ff, 'PUBLIC', tmp_path/'public')
    monkeypatch.setattr(ff, 'now', lambda: AT)
    monkeypatch.setattr(ff, 'read_control', lambda: {'enabled': True})
    monkeypatch.setattr(ff, 'research_row', lambda r: research(r))
    monkeypatch.setattr(ff, 'build_prediction', lambda *args: content())
    publish(ff.PUBLIC/'daily-football.json', {'matches': [row]})
    return row


def test_immutable_stages_and_independent_postmatch_results(sandbox):
    row = sandbox
    assert ff.generate(row, 'initial')
    assert not ff.generate(row, 'initial')
    assert ff.generate(row, 'final')
    value = ff.status(row)
    assert all(value['stages'][s]['report']['issuedAt'] == AT.isoformat() for s in ['initial', 'final'])
    row.update(state='finished', finished=True, started=True)
    row['teams']['home']['goals'], row['teams']['away']['goals'] = 2, 1
    value = ff.status(row, AT+timedelta(hours=3))
    assert value['stages']['initial']['report']['review']['asianResult'] == '赢半'
    assert value['stages']['final']['report']['review']['exactScore'] is True
    assert not ff.generate(row, 'initial')


@pytest.mark.parametrize('fault', ['ten_players', 'duplicate', 'wrong_team', 'wrong_event', 'rescheduled', 'old', 'future', 'stale_message', 'unconfirmed'])
def test_final_requires_fresh_confirmed_matching_eleven(sandbox, monkeypatch, fault):
    r = research(sandbox)
    if fault == 'ten_players': r['teams']['home']['lineup']['players'].pop()
    if fault == 'duplicate': r['teams']['home']['lineup']['players'][1] = r['teams']['home']['lineup']['players'][0]
    if fault == 'wrong_team': r['teams']['away']['teamId'] = 'x'
    if fault == 'wrong_event': r['eventId'] = '456'
    if fault == 'rescheduled': r['kickoff'] = (AT+timedelta(hours=2)).isoformat()
    if fault == 'old': r['pregame']['capturedAt'] = (AT-timedelta(minutes=11)).isoformat()
    if fault == 'future': r['pregame']['capturedAt'] = (AT+timedelta(seconds=1)).isoformat()
    if fault == 'stale_message': r['message'] = 'cached source'
    if fault == 'unconfirmed': r['teams']['home']['lineup']['confirmed'] = False
    monkeypatch.setattr(ff, 'research_row', lambda row: r)
    monkeypatch.setattr(ff, 'build_prediction', lambda *args: pytest.fail('must not call model'))
    assert not ff.generate(sandbox, 'final')


def test_initial_allowed_before_lineups_and_missing_odds_has_no_selection(sandbox, monkeypatch):
    sandbox['quotes'] = []
    monkeypatch.setattr(ff, 'research_row', lambda row: research(row, False))
    monkeypatch.setattr(ff, 'build_prediction', lambda *args: {**content(), 'asianSide': 'pass'})
    assert not ff.generate(sandbox, 'initial')
    assert ff.status(sandbox)['stages']['initial']['report'] is None
    with pytest.raises(ValueError): ff.validate(content(), None)


@pytest.mark.parametrize('fault', ['old', 'future', 'inplay', 'opening', 'bad_line', 'bad_price'])
def test_quote_requires_current_pregame_latest_source(fault):
    row = fixture()
    q = row['quotes'][0]
    if fault == 'old': q['fetchedAt'] = (AT-timedelta(minutes=16)).isoformat()
    if fault == 'future': q['fetchedAt'] = (AT+timedelta(minutes=1)).isoformat()
    if fault == 'inplay': q['inPlay'] = True
    if fault == 'opening': q['phase'] = 'opening'
    if fault == 'bad_line': q['line'] = .3
    if fault == 'bad_price': q['prices']['H'] = float('nan')
    assert ff.quote_for(row, AT) is None


def test_response_after_kickoff_or_changed_opponent_is_not_saved(sandbox, monkeypatch):
    def late(*args):
        monkeypatch.setattr(ff, 'now', lambda: AT+timedelta(hours=2))
        return content()
    monkeypatch.setattr(ff, 'build_prediction', late)
    assert not ff.generate(sandbox, 'initial')
    assert ff.status(sandbox)['stages']['initial']['report'] is None


def test_changed_identity_hides_old_reports(sandbox):
    assert ff.generate(sandbox, 'initial')
    changed = deepcopy(sandbox)
    changed['kickoff'] = (AT+timedelta(hours=4)).isoformat()
    assert ff.status(changed)['stages']['initial']['report'] is None
    changed = deepcopy(sandbox)
    changed['teams']['away']['id'] = '3'
    assert ff.status(changed)['stages']['initial']['report'] is None


def test_paused_no_fetch_or_model_and_resume_preserves_records(sandbox, monkeypatch):
    assert ff.generate(sandbox, 'initial')
    monkeypatch.setattr(ff, 'read_control', lambda: {'enabled': False})
    monkeypatch.setattr(ff, 'research_row', lambda r: pytest.fail('paused cannot fetch'))
    assert ff.refresh()['paused']
    assert not ff.generate(sandbox, 'final')
    assert ff.status(sandbox)['stages']['initial']['report']


def test_retry_cooldown_and_exception_body_never_public(sandbox, monkeypatch):
    calls = []
    def fail(*args):
        calls.append(1)
        raise ValueError('secret credential and provider body')
    monkeypatch.setattr(ff, 'build_prediction', fail)
    assert not ff.generate(sandbox, 'initial')
    assert not ff.generate(sandbox, 'initial')
    assert len(calls) == 1
    assert 'secret' not in str(ff.status(sandbox))


def test_timing_four_days_bootstrap_and_champions_league(sandbox, monkeypatch):
    row = fixture(97)
    row['competitionId'] = '775'
    publish(ff.PUBLIC/'daily-football.json', {'matches': [row]})
    calls = []
    monkeypatch.setattr(ff, 'generate', lambda r, stage: calls.append(stage) or True)
    assert ff.refresh()['checked'] == 0
    assert ff.refresh('2026-11-21')['generated'] == 0
    assert ff.refresh('2026-11-25')['generated'] == 1
    assert calls == ['initial']
    calls.clear()
    row['kickoff'] = (AT+timedelta(hours=96)).isoformat()
    publish(ff.PUBLIC/'daily-football.json', {'matches': [row]})
    assert ff.refresh()['generated'] == 1
    assert calls == ['initial']


def test_bounded_fairness_keeps_initials_running_while_finals_wait(sandbox, monkeypatch):
    assert ff.generate(sandbox, 'initial')
    row2 = deepcopy(sandbox)
    row2['id'] = '124'
    publish(ff.PUBLIC/'daily-football.json', {'matches': [sandbox, row2]})
    calls = []
    monkeypatch.setattr(ff, 'generate', lambda row, stage: calls.append(stage) or False)
    assert ff.refresh()['checked'] == 2
    assert calls == ['final', 'initial']


def test_first_install_near_kickoff_saves_initial_before_final(sandbox, monkeypatch):
    calls = []
    monkeypatch.setattr(ff, 'generate', lambda row, stage: calls.append(stage) or True)
    ff.refresh()
    assert calls == ['initial']


@pytest.mark.parametrize('score,line,side,result', [([1,0],-.75,'H','赢半'),([0,0],.25,'H','赢半'),
    ([0,0],-.25,'H','输半'),([1,0],-1,'H','走盘'),([1,0],-.75,'A','输半'),([0,2],.5,'A','赢盘')])
def test_quarter_line_settlement(score, line, side, result):
    assert ff.settlement(score, line, side) == result


def test_snapshot_not_public_and_index_retains_versions(sandbox):
    assert ff.generate(sandbox, 'initial')
    index = ff.read_index()
    assert index['matches']['123']['stages']['initial']['report']['score'] == [2,1]
    assert 'snapshot' not in str(index).replace('snapshotHash', '')


def test_baseline_ignores_future_and_missing_scores():
    r = research(fixture())
    r['teams']['home']['form']['matches'] += [{'date': (AT+timedelta(days=1)).isoformat(), 'goalsFor':20,'goalsAgainst':0}]
    result = ff.baseline(r, AT)
    assert result['samples']['home'] == 8
    assert result['expectedGoals'] == [1.5,1.5]
    r['teams']['away']['form']['matches'] = []
    assert not ff.baseline(r, AT)['available']


def test_compact_index_preserves_picks_without_mutating_full_review():
    value = {'supported': True, 'eventId': '123', 'teams': {'home': '1', 'away': '2'},
             'stages': {'final': {'message': 'saved', 'report': {'score': [2, 1], 'asianSide': 'H',
                        'issuedAt': AT.isoformat(), 'quote': {'line': -.5, 'prices': {'H': 1.9, 'A': 1.9}},
                        'summary': ['long analysis'], 'details': [{'text': 'evidence'}],
                        'review': {'status': 'evaluated', 'analysis': {'text': 'full postmatch evidence'}}}},
                        'initial': {'report': None}}}
    before = deepcopy(value)
    small = ff.compact_status(value)
    assert small['eventId'] == '123' and small['teams'] == value['teams']
    assert small['stages']['final']['report']['score'] == [2, 1]
    assert small['stages']['final']['report']['quote'] == {'line': -.5}
    assert small['stages']['final']['report']['review'] == {'status': 'evaluated'}
    assert 'details' not in small['stages']['final']['report']
    assert small['stages']['initial']['report'] is None and value == before


def test_compact_index_skips_detailed_dossiers_but_single_match_keeps_them(sandbox, monkeypatch):
    from football import reviews
    assert ff.generate(sandbox, 'initial')
    sandbox.update(state='finished', finished=True, started=True)
    sandbox['teams']['home']['goals'], sandbox['teams']['away']['goals'] = 2, 1
    publish(ff.PUBLIC/'daily-football.json', {'matches': [sandbox]})
    monkeypatch.setattr(ff, 'resolved_result', lambda row, catalogues=None: row)
    calls = []
    def dossier(row, report):
        calls.append(row['id'])
        return {'evidence': 'full postmatch dossier'}
    monkeypatch.setattr(reviews, 'football_forecast_review', dossier)
    compact = ff.read_index(compact=True)['matches']['123']['stages']['initial']['report']
    assert compact['review']['status'] == 'evaluated'
    assert compact['score'] == [2, 1] and compact['asianSide'] == 'H'
    assert calls == []
    full = ff.status(sandbox)['stages']['initial']['report']['review']
    assert full['analysis'] == {'evidence': 'full postmatch dossier'}
    assert full['exactScore'] is True and full['asianResult'] == '赢半'
    assert calls == ['123']
