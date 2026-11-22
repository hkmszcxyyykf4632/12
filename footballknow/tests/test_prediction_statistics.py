import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pytest

from football import football_statistics as fs, racing_statistics as rs
from football.football_forecasts import identity
from football.motivation import digest
from football.statistics_models import Dividend


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(fs, 'STATE', tmp_path)
    monkeypatch.setattr(fs, 'PUBLIC', tmp_path)
    monkeypatch.setattr(fs, 'match_catalogue', lambda league: ({}, []))
    with closing(sqlite3.connect(tmp_path/'football-forecasts.sqlite3')) as db:
        db.execute('CREATE TABLE forecasts(identity TEXT,stage TEXT,event_id TEXT,issued_at TEXT,content TEXT,snapshot TEXT)')
        db.commit()
    return tmp_path


def save_football(folder, stage='initial', side='H', line=-.75, issued='2026-11-21T10:00:00Z'):
    row={'id':'123','competitionId':'700','kickoff':'2026-11-21T12:30:00Z','state':'scheduled',
         'scoreScope':'90分钟含补时','teams':{'home':{'id':'1','name':'Manchester City','label':'曼城'},'away':{'id':'2','name':'Fulham','label':'富咸'}}}
    snapshot={'capturedAt':'2026-11-21T09:59:00Z','match':row}
    report={'stage':stage,'issuedAt':issued,'score':[2,1],'asianSide':side,'snapshotHash':digest(snapshot),
            'quote':{'market':'asian-handicap','line':line,'fetchedAt':'2026-11-21T09:50:00Z','source':'https://example.test'}}
    with closing(sqlite3.connect(folder/'football-forecasts.sqlite3')) as db:
        db.execute('INSERT INTO forecasts VALUES(?,?,?,?,?,?)',(identity(row),stage,'123',issued,json.dumps(report),json.dumps(snapshot)))
        db.commit()
    return row


def result(row, score=(2,1), scope='90分钟含补时'):
    row=json.loads(json.dumps(row));row.update(finished=True,state='finished',scoreScope=scope)
    for side,goals in zip(['home','away'],score):row['teams'][side]['goals']=goals
    return row


def test_full_ledger_survives_daily_rollover_and_retains_both_stages(ledger,monkeypatch):
    save_football(ledger);save_football(ledger,'final')
    m={'id':'2026-11-21|Man City|Fulham','date':'2026-11-21','kickoff':'2026-11-21T12:30:00Z',
       'home':'Man City','away':'Fulham','finished':True,'homeGoals':2,'awayGoals':1,'scoreScope':'90 分钟含补时'}
    monkeypatch.setattr(fs,'match_catalogue',lambda league:({},[m]))
    rows=fs.read_statistics().records
    assert len(rows)==2 and all(r.status=='settled' for r in rows)
    assert all(r.exactHit and r.asianResult=='赢半' for r in rows)


@pytest.mark.parametrize('side,line,score,expected',[
    ('H',-.75,(2,1),'赢半'),('A',-.75,(2,1),'输半'),('H',-1,(2,1),'走盘'),
    ('A',-1.5,(2,1),'赢盘'),('H',.25,(0,0),'赢半'),('A',.25,(0,0),'输半')])
def test_saved_handicap_and_side_are_settled_not_current_price(ledger,side,line,score,expected):
    row=save_football(ledger,side=side,line=line)
    (ledger/'daily-football.json').write_text(json.dumps({'matches':[result(row,score)]}))
    assert fs.read_statistics().records[0].asianResult==expected


def test_late_prediction_excluded_and_extra_time_not_settled(ledger):
    row=save_football(ledger,issued='2026-11-21T12:30:00Z')
    save_football(ledger,'final')
    (ledger/'daily-football.json').write_text(json.dumps({'matches':[result(row,scope='含加时或点球阶段')]}))
    rows=fs.read_statistics().records
    assert {r.status for r in rows}=={'excluded','pending'}


def test_bad_hash_or_reassigned_kickoff_never_becomes_a_hit(ledger):
    row=save_football(ledger);row['kickoff']='2026-11-22T12:30:00Z'
    (ledger/'daily-football.json').write_text(json.dumps({'matches':[result(row)]}))
    assert fs.read_statistics().records[0].status=='excluded'


def test_three_horses_three_unordered_pairs_official_payout_and_dead_heat():
    payouts=[Dividend(type='QPL',combination=c,amount=a) for c,a in [('1,2',15),('1,3',20),('2,3',12)]]
    pool=rs.settle_pool('QPL',['1','2','3'],set(),payouts,True)
    assert len(pool.tickets)==3 and all(t.status=='hit' for t in pool.tickets)
    assert sum(t.dividend for t in pool.tickets)==47
    assert pool.tickets[0].multiple==1.5
    wins=[Dividend(type='WIN',combination='1',amount=110),Dividend(type='WIN',combination='2',amount=35)]
    assert [t.status for t in rs.settle_pool('WIN',['1','2','3'],set(),wins,True).tickets]==['hit','hit','miss']


def test_missing_payout_provisional_and_refunds_are_not_misses():
    assert all(t.status=='pending' for t in rs.settle_pool('QPL',['1','2','3'],set(),[],True).tickets)
    dividends=[Dividend(type='WIN',combination='1',amount=110)]
    assert all(t.status=='pending' for t in rs.settle_pool('WIN',['1','2'],set(),dividends,False).tickets)
    pool=rs.settle_pool('QIN',['1','2','3'],{'2'},[Dividend(type='QIN',combination='1,3',amount=500)],True)
    assert [t.status for t in pool.tickets]==['refund','hit','refund']
    assert pool.tickets[1].multiple==50


def test_place_is_official_paid_list_not_assumed_top_three():
    pool=rs.settle_pool('PLA',['1','2','3'],set(),[Dividend(type='PLA',combination='1',amount=12),Dividend(type='PLA',combination='2',amount=18)],True)
    assert pool.tickets[2].status=='miss'


def test_racing_cancellation_refunds_original_shortlist(tmp_path,monkeypatch):
    monkeypatch.setattr(rs,'STATE',tmp_path);monkeypatch.setattr(rs,'FOLDER',tmp_path)
    (tmp_path/'races').mkdir()
    ident='2026-11-22-ST-1'
    report={'pick':'a','shortlist':['a','b','c'],'runnerSnapshot':[{'id':h,'number':n,'name':h} for n,h in enumerate('abc',1)],'marketSnapshot':{'raceId':ident,'offTime':'2026-11-22T05:00:00Z'}}
    with closing(sqlite3.connect(tmp_path/'racing-analysis.sqlite3')) as db:
        db.execute('CREATE TABLE reports(race_id TEXT,phase TEXT,issued_at TEXT,content TEXT)')
        db.execute('INSERT INTO reports VALUES(?,?,?,?)',(ident,'pre','2026-11-21T23:00:00Z',json.dumps(report)));db.commit()
    race={'id':ident,'date':'2026-11-22','course':'ST','raceNo':1,'status':'cancelled','entries':[]}
    (tmp_path/'races'/f'{ident}.json').write_text(json.dumps(race))
    receipt=rs.read_statistics().records[0]
    assert receipt.status=='void' and len(receipt.runners)==3
    assert len([t for p in receipt.pools for t in p.tickets])==12
    assert all(t.status=='refund' for p in receipt.pools for t in p.tickets)


def test_unpriced_correct_score_is_not_filled_with_later_quote(ledger):
    save_football(ledger)
    with closing(sqlite3.connect(ledger/'football-forecasts.sqlite3')) as db:
        row=db.execute('SELECT snapshot,content FROM forecasts').fetchone()
        snapshot,content=map(json.loads,row)
        snapshot['match']['quotes']=[{'market':'correct-score','prices':{'2:1':8.5},'source':'https://example.test','phase':'latest','fetchedAt':'2026-11-21T11:59:00Z'}]
        content['snapshotHash']=digest(snapshot)
        db.execute('UPDATE forecasts SET snapshot=?,content=?',(json.dumps(snapshot),json.dumps(content)));db.commit()
    assert fs.read_statistics().records[0].scorePrice is None


def test_round_number_survives_postponement_in_same_season():
    from football.football_rounds import RoundEntry,round_info
    entry=RoundEntry(id='1',league='epl',season='2026/27',round=11,home='Manchester City',away='Fulham',date='2026-12-20',status='NS',source='https://example.test')
    info=round_info('epl','Manchester City','Fulham',datetime(2026,11,21,tzinfo=timezone.utc),[entry])
    assert info[0]=='2026/27' and info[1]=='第11轮' and info[3] is False


def test_brief_uses_saved_evidence_and_does_not_request_a_model(tmp_path,monkeypatch):
    from football import review_briefs as brief
    monkeypatch.setattr(brief,'STATE',tmp_path)
    folder=tmp_path/'evidence-reviews'/'football'/'case';folder.mkdir(parents=True)
    payload={'generatedAt':'2026-11-22T08:00:00Z','summary':['末段被追平。'],'drivers':[{'explanation':'换人后失去前场接应。','evidenceIds':['f1']}],'lessons':[{'category':'unresolved','nextCheck':'核对换人后的射门记录。','evidenceIds':['f1']}],
      'evidenceSnapshot':{'domain':'football','identity':'epl:abc','original':{'stage':'final'},'facts':[{'id':'f1','sourceIds':['s1']}],'sources':[{'id':'s1','title':'赛事记录','url':'https://example.test/match'}]}}
    (folder/'revision.json').write_text(json.dumps(payload),encoding='utf-8')
    result=brief.read_briefs('football')
    assert len(result.records)==1 and result.records[0].identity=='epl:abc'
    assert result.records[0].sources[0].title=='赛事记录'
