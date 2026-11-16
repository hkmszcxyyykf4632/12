import json
from datetime import datetime, timedelta, timezone

import pytest

from football import analysis, evaluation, ucl, ucl_history
from football.analysis import Match, MatchAnalysis, Club
from football.leagues import league_path


def event():
    return {'id': '123', 'date': '2026-11-25T20:00Z', 'season': {'year': 2026, 'slug': 'round-of-16'},
            'competitions': [{'competitors': [
                {'id':'1','homeAway':'home','team':{'displayName':'A'},'score':'3','aggregateScore':8},
                {'id':'2','homeAway':'away','team':{'displayName':'B'},'score':'1','aggregateScore':9}],
                'status': {'period':4, 'type':{'name':'STATUS_FINAL_AET','state':'post','completed':True}},
                'details': [{'team':{'id':team},'clock':{'value':minute},'scoringPlay':True,'scoreValue':1}
                            for team, minute in [('1',100),('2',2500),('1',5400),('1',6500)]]}]}


def test_extra_time_uses_verified_regulation_score_not_aggregate():
    row = ucl.event_row(event(), 'https://example.org')
    assert (row['homeGoals'], row['awayGoals'], row['result']) == (2, 1, 'H')
    assert row['fullTimeScore'] == [3, 1]
    assert row['id'] == 'espn:123' and row['phase'] == '十六强'
    data = event()
    data['competitions'][0]['details'].pop()
    row = ucl.event_row(data, 'https://example.org')
    assert row['homeGoals'] is None and not row['finished'] and row['provisional']


def test_stoppage_time_and_only_complete_decimal_odds_are_kept():
    data = event()
    game = data['competitions'][0]
    game['details'][2]['clock'] = {'value':5700,'displayValue':"90'+5'"}
    valid = {'provider':{'name':'Example'},'homeTeamOdds':{'odds':{'value':2.5}},
             'drawOdds':{'value':3.4},'awayTeamOdds':{'odds':{'value':2.8}}}
    game['odds'] = [None, {'homeTeamOdds':{'moneyLine':-150}}, valid]
    row = ucl.event_row(data, 'https://example.org')
    assert row['homeGoals'] == 2 and row['awayGoals'] == 1
    assert len(row['odds']) == 1 and row['odds'][0]['H'] == 2.5


def test_penalty_shootout_does_not_change_draw_and_postponement_has_no_kickoff():
    data = event()
    game = data['competitions'][0]
    game['competitors'][0]['score'] = '1'
    game['status']['type']['name'] = 'STATUS_FINAL_PENALTIES'
    game['details'] = game['details'][:2] + [{'team':{'id':'1'},'clock':{'value':7200},
                                          'scoringPlay':True,'shootout':True,'scoreValue':1}]
    row = ucl.event_row(data, 'https://example.org')
    assert row['finished'] and row['result'] == 'D'
    game['status'] = {'type':{'name':'STATUS_POSTPONED','state':'pre','completed':False}}
    row = ucl.event_row(data, 'https://example.org')
    assert row['kickoff'] is None and not row['started'] and row['result'] is None


def league_phase():
    teams = [{'id':i,'name':str(i)} for i in range(36)]
    rows = [{'fixtureId':i*4+j,'season':'2026/27','competition':'欧冠','phase':'联赛阶段',
             'home':str(i),'away':str((i+j+1)%36)} for i in range(36) for j in range(4)]
    return teams, rows


def test_dynamic_knockout_schedule_keeps_complete_league_phase():
    teams, rows = league_phase()
    ucl.validate_schedule(rows, teams, '2026/27')
    rows.append({**rows[0], 'fixtureId':900, 'phase':'十六强'})
    ucl.validate_schedule(rows, teams, '2026/27')
    with pytest.raises(OSError):
        ucl.validate_schedule(rows[1:], teams, '2026/27')
    rows.append(rows[-1])
    with pytest.raises(OSError):
        ucl.validate_schedule(rows, teams, '2026/27')


def fixture(ident, date):
    return Match(id=ident, date=date[:10], kickoff=date, home='A', away='B', finished=False,
                 competition='欧冠', season='2026/27')


def test_repeated_pair_forecasts_are_independent_and_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, 'STATE', tmp_path)
    assert league_path(tmp_path, 'ucl') == tmp_path / 'ucl'
    dates = ['2026-12-01T20:00:00+00:00','2027-03-01T20:00:00+00:00']
    results = []
    for i, date in enumerate(dates):
        match = fixture(f'espn:{i}', date)
        report = MatchAnalysis(generatedAt='2026-11-16', dataUpdatedAt='2026-11-16', liveUpdatedAt=None,
            team=Club(id=1,name='A',cn='甲'), match=match, checklist=[])
        assert evaluation.record_forecast(report, 'H' if i == 0 else 'A', 'test', 'v1', '2026-11-16T01:00:00+00:00','ucl')
        assert not evaluation.record_forecast(report, 'D', 'test', 'v2', '2026-11-16T02:00:00+00:00','ucl')
        results.append(match.model_copy(update={'finished':True,'homeGoals':1 if i == 0 else 0,'awayGoals':0 if i == 0 else 1}))
    status = evaluation.prospective_results(results,'ucl')
    assert status['recorded'] == status['samples'] == status['correct'] == 2


def test_archive_preserves_repeated_pair_and_next_match_is_ucl(tmp_path, monkeypatch):
    folder = tmp_path / 'ucl'
    folder.mkdir()
    future = datetime.now(timezone.utc) + timedelta(days=20)
    first = fixture('espn:1',future.isoformat())
    second = fixture('espn:2',(future+timedelta(days=30)).isoformat())
    domestic = first.model_copy(update={'id':'domestic','competition':'英超','kickoff':(future-timedelta(days=10)).isoformat()})
    payload = {'competition':'欧冠','season':'2026/27','updatedAt':'2026-11-16',
               'teams':[{'id':1,'name':'A','cn':'甲'},{'id':2,'name':'B','cn':'乙'}],
               'players':[], 'matches':[r.model_dump() for r in [first,second,domestic]]}
    (folder/'data.json').write_text(json.dumps(payload))
    live = {'version':1,'competition':'欧冠','league':'ucl','season':'2026/27','updatedAt':'2026-11-16',
            'matches':[{**first.model_dump(),'fixtureId':1,'started':False,'provisional':False,'result':None}]}
    (folder/'live.json').write_text(json.dumps(live))
    monkeypatch.setattr(analysis,'PUBLIC',tmp_path)
    archive, _ = analysis.load_archive('ucl')
    assert {r.id for r in archive.matches} == {'espn:1','espn:2','domestic'}
    assert analysis.analyze_next(1,'ucl').match.id == 'espn:1'


def test_club_transfer_table_keeps_dates_and_loan_direction(monkeypatch):
    markup = '<h2>Transfers</h2><h3>Loans out</h3><table class="wikitable"><tr><th>Player</th><th>Transferred to</th><th>Fee</th><th>Date</th></tr><tr><td>Alex Smith</td><td>Other Club</td><td>Undisclosed</td><td>1 July 2026</td></tr></table>'
    monkeypatch.setattr(ucl_history,'fetch_text',lambda _:markup)
    rows = ucl_history.club_transfers('https://example.org/2026–27_A_season','A',{'Other Club':'B'})
    assert len(rows) == 1
    assert (rows[0].fromTeam,rows[0].toTeam,rows[0].type,rows[0].date,rows[0].fee) == ('A','B','租借','2026-07-01','未公开')
