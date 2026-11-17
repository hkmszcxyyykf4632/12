import pytest
from football.match_details import parse_player, parse_detail, canonical, lineup_context
from football.odds import historical_odds, espn_odds, american
from types import SimpleNamespace


def person(**changes):
    return {'athlete': {'id':'100','displayName':'Sample Player'}, 'starter':True,'subbedIn':False,'subbedOut':False,'stats':[],**changes}


def test_substitution_minutes_and_missing_red_card_time():
    raw=person(subbedOut=True,plays=[{'substitution':True,'clock':{'displayValue':"61'"}}])
    assert parse_player(raw,None,{},True,90)['minutes']==61
    raw=person(starter=False,subbedIn=True,plays=[{'substitution':True,'clock':{'displayValue':"90'+3'"}}])
    result=parse_player(raw,None,{},True,90)
    assert result['played'] and result['minutes']==0 and result['minutesEstimated']
    raw=person(stats=[{'name':'redCards','value':1}])
    assert parse_player(raw,None,{},True,90)['minutes'] is None
    assert parse_player(person(),None,{},False,90)['minutes'] is None
    assert parse_player(person(starter=False),None,{},True,90)['minutes']==0


def test_source_identity_cannot_be_swapped():
    match={'id':'espn:1','date':'2026-10-01','home':'Arsenal','away':'Chelsea'}
    raw={'header':{'id':'1','competitions':[{'date':'2026-10-01T20:00Z','competitors':[
        {'id':'359','homeAway':'home','team':{'displayName':'Chelsea'}},
        {'id':'363','homeAway':'away','team':{'displayName':'Arsenal'}}]}]}}
    with pytest.raises(ValueError):parse_detail(raw,match,{'teams':[]},'epl','1')
    assert canonical('Athletic Club','laliga')==canonical('Ath Bilbao','laliga')
    assert canonical('Manchester City','epl')==canonical('Man City','epl')


def test_lineup_context_excludes_future_and_reports_coverage(monkeypatch):
    monkeypatch.setattr('football.match_details.match_catalogue',lambda league: ({},[]))
    monkeypatch.setattr('football.match_details.detail_for_match',lambda m,*a: {'source':'https://www.espn.com/', 'lineups':{'home':{'confirmed':True,'formation':'4-4-2','players':[{'espnId':'1','name':'P','starter':True,'played':True,'minutes':60,'minutesEstimated':True}]}}})
    fixture=SimpleNamespace(date='2026-11-20',kickoff='2026-11-20T20:00Z')
    old=dict(id='old',date='2026-11-18',home='A',away='B',finished=True,competition='英超')
    future={**old,'date':'2026-11-21'}
    result=lineup_context('epl',fixture,{'A':[old,future]})['A']
    assert result['coveredMatches']==1 and result['requestedMatches']==2
    assert result['players'][0]['minutes7Days']==60 and result['players'][0]['estimatedSamples']==1


def test_historical_companies_are_distinct_and_partial_quotes_excluded():
    raw={'B365H':'2','B365D':'3','B365A':'4','BFDH':'2.1','BFDD':'3.1','BFDA':'4.1','BVH':'2.2','BVD':'3.2'}
    quotes=historical_odds(raw,'https://www.football-data.co.uk/sample.csv')
    assert {q['provider'] for q in quotes}=={'Bet365','Betfred'}
    assert all(q['via']=='Football-Data' and q['market']=='90-minute-1x2' for q in quotes)


def test_american_and_decimal_odds_are_not_confused():
    assert american(-200)==1.5 and american(400)==5 and american(0) is None
    raw={'header':{'id':'9','competitions':[{'competitors':[{'id':'1','homeAway':'home'},{'id':'2','homeAway':'away'}]}]},'odds':[{'provider':{'name':'Sample'},'homeTeamOdds':{'team':{'id':'1'},'moneyLine':-200},'awayTeamOdds':{'team':{'id':'2'},'moneyLine':400},'drawOdds':{'moneyLine':300}}]}
    assert espn_odds(raw,'9','2026-11-01T00:00:00Z')[0]['D']==4
    raw['odds'][0]['homeTeamOdds']['team']['id']='2'
    assert espn_odds(raw,'9','2026-11-01T00:00:00Z')==[]
def test_live_lineups_and_recent_results_refresh_promptly():
    from datetime import datetime, timezone
    from football.match_details import cache_seconds
    date = datetime.now(timezone.utc).date().isoformat()
    assert cache_seconds({'date': date, 'started': True, 'finished': False}, {'status': 'available'}) == 60
    assert cache_seconds({'date': date, 'finished': True}, {'status': 'available', 'completed': True}) == 1800
    assert cache_seconds({'date': '2020-01-01', 'finished': True}, {'status': 'available', 'completed': True}) == 604800


def test_same_birth_date_does_not_confuse_twin_names():
    from football.names import Player, WikiPage, birth_matches
    jack = Player(id=1, code=1, first_name='Jack', second_name='Fletcher', web_name='J.Fletcher', birth_date='2007-03-19')
    assert not birth_matches(jack, WikiPage(title='Tyler Fletcher', extract='Tyler Fletcher (born 19 March 2007) is a footballer.'))
    assert birth_matches(jack, WikiPage(title='Jack Fletcher', extract='Jack Fletcher (born 19 March 2007) is a footballer.'))

