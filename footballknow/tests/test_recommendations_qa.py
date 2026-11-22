import json
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from football import recommendations as rec, interactive_qa as qa
from football.recommendation_candidates import Candidate
from football.qa_context import Evidence

AT = datetime(2026, 11, 22, 8, tzinfo=timezone.utc)


def candidate(event, priority=1, domain='football', group='epl|2026/27|第11轮', offset=60):
    return Candidate(domain=domain, group=group, event=event, identity=event, stage='initial',
        issuedAt=AT-timedelta(hours=1), kickoff=AT+timedelta(minutes=offset), priority=priority,
        summary=['原推荐'], reasons=['封存依据'], receipt={'status':'pending','score':[2,1]})


def test_top_three_per_league_are_immutable_and_never_backfilled(tmp_path, monkeypatch):
    monkeypatch.setattr(rec,'STATE',tmp_path)
    choices=[candidate(str(i),i) for i in range(6)]
    choices += [candidate('late',99,offset=-1),candidate('other',2,group='laliga|2026/27|第13轮')]
    assert rec.publish_candidates(choices,AT)==4
    assert rec.publish_candidates([candidate('replacement',999)],AT)==0
    with sqlite3.connect(tmp_path/'recommendations.sqlite3') as db:
        saved={x[0] for x in db.execute('SELECT event FROM selections')}
        assert saved=={'3','4','5','other'}
        with pytest.raises(sqlite3.IntegrityError):db.execute("UPDATE selections SET event='new'")
        with pytest.raises(sqlite3.IntegrityError):db.execute('DELETE FROM selections')


def test_racing_one_per_day_and_wait_for_comparison_window(tmp_path, monkeypatch):
    monkeypatch.setattr(rec,'STATE',tmp_path)
    assert rec.publish_candidates([candidate('early',99,offset=180)],AT)==0
    choices=[candidate(str(i),i,'racing','2026-11-22') for i in range(4)]
    assert rec.publish_candidates(choices,AT)==1
    assert rec.publish_candidates([candidate('later',99,'racing','2026-11-22')],AT)==0


def test_read_never_substitutes_later_final_for_selected_initial(tmp_path,monkeypatch):
    monkeypatch.setattr(rec,'STATE',tmp_path)
    rec.publish_candidates([candidate('1')],AT)
    final=SimpleNamespace(identity='1',stage='final',issuedAt=AT,model_dump=lambda **kw:{'status':'settled','score':[4,0]})
    monkeypatch.setattr(rec,'football_statistics',lambda:SimpleNamespace(records=[final]))
    monkeypatch.setattr(rec,'racing_statistics',lambda:SimpleNamespace(records=[]))
    r=rec.read_recommendations()['records'][0]
    assert r['receipt']['status']=='excluded' and r['receipt']['score']==[2,1]


def test_quota_is_atomic_and_client_independent(tmp_path,monkeypatch):
    monkeypatch.setattr(qa,'STATE',tmp_path)
    for _ in range(6):qa.consume_quota('a',AT)
    with pytest.raises(qa.BusyError):qa.consume_quota('a',AT)
    qa.consume_quota('b',AT)
    qa.consume_quota('a',AT+timedelta(minutes=1))


def test_dialogue_and_only_real_source_links(tmp_path,monkeypatch):
    monkeypatch.setattr(qa,'STATE',tmp_path)
    monkeypatch.setattr(qa,'retrieve',lambda q:[Evidence(title='核对资料',url='https://example.test/source',updatedAt='2026-11-22',data={'x':1})])
    def model(rules,context,tokens):
        assert context['history'][0]['content']=='我刚才问的是亚洲盘'
        assert '没有即时联网工具' in rules
        return {'answer':['普通知识也可以回答。'],'sourceIds':[0,9,-1,0],'followups':['继续讨论什么？']}
    monkeypatch.setattr(qa,'request_json',model)
    question=qa.Question(question='那赢一球怎么算？',history=[qa.Turn(role='user',content='我刚才问的是亚洲盘')])
    answer=qa.ask(question,'a')
    assert len(answer['sources'])==1 and answer['sources'][0]['url']=='https://example.test/source'
    assert not list(tmp_path.glob('*conversation*'))


def test_ai_failure_releases_capacity(tmp_path,monkeypatch):
    monkeypatch.setattr(qa,'STATE',tmp_path);monkeypatch.setattr(qa,'retrieve',lambda q:[])
    def fail(*args):raise ValueError('provider failure')
    monkeypatch.setattr(qa,'request_json',fail)
    with pytest.raises(ValueError):qa.ask(qa.Question(question='测试'),'a')
    assert qa.ACTIVE.acquire(False)
    qa.ACTIVE.release()


def test_api_accepts_object_and_never_exposes_provider_error(monkeypatch):
    from fastapi.testclient import TestClient
    import server
    def fail(*args):raise ValueError('private-provider-detail')
    monkeypatch.setattr(qa,'ask',fail)
    client=TestClient(server.app)
    response=client.post('/api/ask',json={'question':'测试','history':[]},headers={'Origin':'http://testserver'})
    assert response.status_code==502 and 'private-provider-detail' not in response.text
    assert client.post('/api/ask',json={'question':'a'*1501},headers={'Origin':'http://testserver'}).status_code==422
