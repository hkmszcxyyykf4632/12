from copy import deepcopy
import pytest
from football.score_reconciliation import reconcile


@pytest.fixture
def fixture():
    match = dict(id='local', season='2026/27', competition='英超', home='Man City', away='Fulham',
                 kickoff='2026-11-21T12:30:00Z', date='2026-11-21', started=False, finished=False)
    catalogue = dict(season='2026/27', teams=[dict(name='Man City', cn='曼城'), dict(name='Fulham', cn='富勒姆')])
    daily = dict(id='123', league='epl', season=2026, kickoff=match['kickoff'], updatedAt='2026-11-21T14:30:00Z',
                 started=True, finished=True, state='finished', scoreScope='90分钟含补时',
                 teams=dict(home=dict(id='382', name='Manchester City', label='曼城', goals=1),
                            away=dict(id='370', name='Fulham', label='富勒姆', goals=1)))
    return match, catalogue, daily


def test_confirmed_daily_final_wins_over_provisional_feed(fixture):
    match, catalogue, daily = fixture
    row = reconcile([match], catalogue, {'matches': [daily]}, 'epl', '2026-11-22T00:00:00Z')[0]
    assert row['finished'] and row['result'] == 'D' and row['id'] == 'local' and row['dailyId'] == '123'
    assert row['scoreUpdatedAt'] == daily['updatedAt']


@pytest.mark.parametrize('key,value', [('kickoff', '2026-11-22T12:30:00Z'), ('league', 'ucl'), ('season', 2025), ('scoreScope', '含加时')])
def test_rejects_incompatible_results(fixture, key, value):
    match, catalogue, daily = fixture
    daily[key] = value
    assert not reconcile([match], catalogue, {'matches': [daily]}, 'epl')[0]['finished']


def test_missing_score_and_duplicate_identity_do_not_settle(fixture):
    match, catalogue, daily = fixture
    assert not reconcile([match], catalogue, {'matches': [daily, daily]}, 'epl')[0]['finished']
    daily['teams']['home']['goals'] = None
    assert not reconcile([match], catalogue, {'matches': [daily]}, 'epl')[0]['finished']


def test_final_never_regresses_but_accepts_score_correction(fixture):
    match, catalogue, daily = fixture
    final = reconcile([match], catalogue, {'matches': [daily]}, 'epl')[0]
    stale = {**daily, 'finished': False, 'started': False, 'updatedAt': '2026-11-22T00:00:00Z'}
    assert reconcile([final], catalogue, {'matches': [stale]}, 'epl')[0]['finished']
    daily['updatedAt'] = '2026-11-21T16:00:00Z'
    daily['teams']['home']['goals'] = 2
    assert reconcile([final], catalogue, {'matches': [daily]}, 'epl')[0]['result'] == 'H'


def test_catalogue_and_analysis_share_confirmed_results(tmp_path, monkeypatch, fixture):
    import json
    from football import analysis, match_details
    match, catalogue, daily = fixture
    catalogue.update(updatedAt='2026-11-22T00:00:00Z', players=[], matches=[match])
    catalogue['teams'] = [{**t, 'id': i + 1} for i, t in enumerate(catalogue['teams'])]
    (tmp_path / 'data.json').write_text(json.dumps(catalogue), encoding='utf-8')
    live = dict(updatedAt=catalogue['updatedAt'], season='2026/27', matches=[{**match, 'started': True, 'provisional': True}])
    (tmp_path / 'live.json').write_text(json.dumps(live), encoding='utf-8')
    (tmp_path / 'daily-football.json').write_text(json.dumps({'matches': [daily]}), encoding='utf-8')
    monkeypatch.setattr(analysis, 'PUBLIC', tmp_path)
    _, rows = match_details.match_catalogue('epl', tmp_path)
    archive, _ = analysis.load_archive('epl')
    assert rows[0]['finished'] and rows[0]['homeGoals'] == rows[0]['awayGoals'] == 1
    assert archive.matches[0].finished and archive.matches[0].homeGoals == 1
