from datetime import datetime,timezone,timedelta
from pathlib import Path
from football import football_rounds as rounds
from football.files import publish

def test_missing_next_round_is_not_starved_by_active_old_rounds(tmp_path,monkeypatch):
    monkeypatch.setattr(rounds,'PUBLIC',tmp_path)
    at=datetime.now(timezone.utc)
    year=at.year if at.month>=7 else at.year-1
    season=f'{year}/{str(year+1)[-2:]}'
    saved=[{'id':str(i),'league':league,'season':season,'round':number,'home':'Old home','away':'Old away','date':(at-timedelta(days=2)).date().isoformat(),'status':'FT','source':'https://example.com/round'} for i,(league,number) in enumerate([('epl',12),('laliga',13),('seriea',12)])]
    publish(tmp_path/'football-rounds.json',{'records':saved,'checked':{}})
    publish(tmp_path/'daily-football.json',{'matches':[{'id':'999','league':'laliga','kickoff':(at+timedelta(days=1)).isoformat(),'state':'scheduled','teams':{'home':{'name':'New home'},'away':{'name':'New away'}}}]})
    urls=[]
    monkeypatch.setattr(rounds,'fetch_json',lambda url:(urls.append(url) or {'events':[]}))
    rounds.refresh(limit=1)
    assert len(urls)==1 and 'id=4335&r=14&' in urls[0]
    assert rounds.load(tmp_path/'football-rounds.json')['records']==saved
