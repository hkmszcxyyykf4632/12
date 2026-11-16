import copy
import pytest
from football.rankings import parse_standings, match_breakdowns, parse_scoring


def catalogue():
    return {'season': '2026/27', 'teams': [{'id': n, 'espnId': n, 'name': name, 'cn': name, 'short': name, 'color': '#164d3d'} for n, name in [(1,'Alpha'),(2,'Beta')]], 'players': [], 'matches': []}


def table():
    rows = []
    for n, name, win, gf, ga in [(1,'Alpha',1,2,0),(2,'Beta',0,0,2)]:
        values = dict(rank=n,gamesPlayed=1,wins=win,ties=0,losses=1-win,pointsFor=gf,pointsAgainst=ga,pointDifferential=gf-ga,points=win*3)
        rows.append({'team': {'id': str(n), 'displayName': name}, 'stats': [{'name': k, 'value': v} for k,v in values.items()]})
    return {'season': {'year': 2026}, 'children': [{'name': 'League', 'standings': {'season': 2026, 'entries': rows}}]}


def test_official_order_and_points_adjustment_are_retained():
    raw = table()
    next(s for s in raw['children'][0]['standings']['entries'][0]['stats'] if s['name']=='points')['value'] = 2
    rows = parse_standings(raw,catalogue(),'epl')
    assert rows[0]['teamId'] == 1 and rows[0]['pointsAdjustment'] == -1


def test_wrong_season_duplicate_and_inconsistent_records_rejected():
    for mutate in [lambda r: r['season'].update(year=2025),
                   lambda r: r['children'][0]['standings']['entries'].pop(),
                   lambda r: r['children'][0]['standings']['entries'][1].update(team={'id':'1','displayName':'Alpha'})]:
        raw=table();mutate(raw)
        with pytest.raises(ValueError):parse_standings(raw,catalogue(),'epl')


def test_partial_results_do_not_publish_home_away_tables():
    data=catalogue();rows=parse_standings(table(),data,'epl')
    assert match_breakdowns(data,{},rows,'epl')['tables']=={}
    data['matches']=[dict(id='m1',date='2026-09-01',home='Alpha',away='Beta',season='2026/27',competition='英超',finished=True,homeGoals=2,awayGoals=0)]
    result=match_breakdowns(data,{},rows,'epl')
    assert result['complete'] and result['tables']['home'][0]['points']==3
    assert rows[0]['cleanSheets']==1
    data['matches'][0]['provisional']=True
    assert not match_breakdowns(data,{},rows,'epl')['complete']


def test_ucl_phase_is_not_a_domestic_table():
    raw=table()
    with pytest.raises(ValueError):parse_standings(raw,catalogue(),'ucl')
    raw['children'][0]['name']='League Phase'
    assert parse_standings(raw,catalogue(),'ucl')[0]['zone']=='champions'
