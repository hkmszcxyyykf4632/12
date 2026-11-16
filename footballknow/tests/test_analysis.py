import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import SecretStr, ValidationError

from football import ai, evaluation
from football.analysis import Club, Match, MatchAnalysis, Probability


def report_at(kickoff):
    return MatchAnalysis(generatedAt='2026-11-15T00:00:00+00:00', dataUpdatedAt='2026-11-14T23:00:00+00:00',
                         liveUpdatedAt=None, team=Club(id=1, name='A', cn='甲队'), checklist=[],
                         match=Match(id='fixture-1', date=kickoff[:10], kickoff=kickoff, home='A', away='B',
                                     season='2026/27', competition='英超', finished=False))


def content():
    return {'pick':'H', 'summary':['主队是本场的首选方向。','主客场数据支持这一判断，关键球员首发情况值得留意。'],
            'details':[{'title':'关键资料', 'text':'主队主场样本与客队客场样本分别计算。'}]}


def test_short_output_contract_and_legacy_cache():
    valid=content()
    assert len(ai.AnalysisContent.model_validate(valid).summary)==2
    for changes in [{'summary':['只有一段']}, {'summary':['段落']*4}, {'summary':['字'*241,'另一段']},
                    {'summary':['第一行\n第二行','另一段']}, {'pick':'HD'}, {'details':[]}, {'thoughts':'private'}]:
        with pytest.raises(ValidationError):
            ai.AnalysisContent.model_validate({**valid, **changes})
    legacy=ai.AIResult(teamId=1,fixtureId='old',generatedAt='2026-01-01',snapshotAt='2026-01-01',
                       model='old-model',rulesVersion='old',text='历史文字')
    assert legacy.summary==[] and legacy.details==[] and legacy.pick is None
    assert 10000<=len(ai.analysis_rules())<=16000


def test_accuracy_empty_and_wilson_interval():
    assert evaluation.accuracy(0,0)['hitRate'] is None
    measured=evaluation.accuracy(38,100)
    assert measured['meetsPointTarget'] is True
    assert measured['interval95'][0]<0.38<measured['interval95'][1]
    assert evaluation.accuracy(0,10)['interval95'][0]==0
    assert evaluation.accuracy(10,10)['interval95'][1]==pytest.approx(1)


def test_backtest_blinds_scores_excludes_future_and_deduplicates(monkeypatch):
    rows=[Match(id=str(i),date=f'2026-10-{i+1:02}',home=f'A{i}',away=f'B{i}',homeGoals=2,awayGoals=1,
                finished=True,competition='英超',season='2025/26') for i in range(20)]
    rows.extend(Match(id=f'test{i}',date=f'2026-11-0{i+1}',home=f'C{i}',away=f'D{i}',homeGoals=h,awayGoals=a,
                      finished=True,competition='英超',season='2026/27') for i,(h,a) in enumerate([(2,1),(1,1),(0,1)]))
    seen=[]
    def baseline(prior,fixture):
        assert fixture.homeGoals is None and fixture.awayGoals is None and not fixture.finished
        assert all(row.date<fixture.date for row in prior)
        seen.append((fixture.id,len(prior)))
        return SimpleNamespace(probabilities=Probability(home=0.6,draw=0.25,away=0.15))
    monkeypatch.setattr(evaluation,'poisson_baseline',baseline)
    measured=evaluation.baseline_backtest(rows+[rows[-1]],'2026/27')
    assert measured['samples']==3 and measured['correct']==1
    assert measured['hitRate']==pytest.approx(1/3)
    assert measured['alwaysHomeHitRate']==measured['priorMajorityHitRate']==pytest.approx(1/3)
    assert seen==[('test0',20),('test1',21),('test2',22)]
    assert measured['brierScore']>0 and measured['logLoss']>0


def test_first_forecast_is_immutable_and_only_confirmed_results_settle(tmp_path,monkeypatch):
    monkeypatch.setattr(evaluation,'STATE',tmp_path)
    report=report_at('2026-11-20T20:00:00+00:00')
    assert evaluation.record_forecast(report,'H','model','v1','2026-11-19T10:00:00+00:00')
    assert not evaluation.record_forecast(report,'A','model','v2','2026-11-19T11:00:00+00:00')
    stored=json.loads(next((tmp_path/'forecasts').glob('*.json')).read_text())
    assert stored['pick']=='H' and stored['rulesVersion']=='v1'
    provisional=report.match.model_copy(update={'started':True,'homeGoals':2,'awayGoals':0})
    assert evaluation.prospective_results([provisional])['pending']==1
    settled=provisional.model_copy(update={'finished':True})
    measured=evaluation.prospective_results([settled,settled])
    assert measured['samples']==1 and measured['correct']==1 and measured['pending']==0
    assert not evaluation.record_forecast(report,'H','model','v1','2026-11-20T20:00:00+00:00')
    assert not evaluation.record_forecast(report,'H','model','v1','2026-11-19T10:00:00')


@pytest.mark.parametrize('reply,finish,accepted',[(content(),'stop',True), ({'pick':'H'},'stop',False),
                                               (content(),'length',False), ('   ','stop',False)])
def test_generation_sends_long_rules_and_accepts_only_complete_json(tmp_path,monkeypatch,reply,finish,accepted):
    monkeypatch.setattr(ai,'STATE',tmp_path)
    monkeypatch.setattr(evaluation,'STATE',tmp_path)
    kickoff=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    monkeypatch.setattr(ai,'analyze_next',lambda _,league='epl':report_at(kickoff))
    past=report_at('2026-01-01T20:00:00+00:00').match.model_copy(update={'finished':True,'homeGoals':2,'awayGoals':1})
    future=past.model_copy(update={'date':'2099-01-01'})
    monkeypatch.setattr(ai,'load_archive',lambda league='epl':(SimpleNamespace(matches=[past,future]),None))
    monkeypatch.setattr(ai,'evaluation_status',lambda league='epl':{'target':0.38,'ai':{'samples':0,'hitRate':None}})
    monkeypatch.setattr(ai,'settings',lambda:ai.AISettings(apiKey=SecretStr('test-private-key')))
    monkeypatch.setattr(ai,'endpoint_for',lambda _:ai.Endpoint('api.deepseek.com','/chat/completions','8.8.8.8'))
    sent={}
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):
            raw=reply if isinstance(reply,str) else json.dumps(reply,ensure_ascii=False)
            return json.dumps({'choices':[{'message':{'content':raw},'finish_reason':finish}]}).encode()
    class Connection:
        def __init__(self,*args,**kwargs):pass
        def request(self,method,path,body,headers):sent.update(json.loads(body))
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(ai.http.client,'HTTPSConnection',Connection)
    monkeypatch.setattr(ai.socket,'create_connection',lambda *a,**k:object())
    monkeypatch.setattr(ai.ssl,'create_default_context',lambda:SimpleNamespace(wrap_socket=lambda *a,**k:object()))
    if accepted:
        result=ai.generate_analysis(1)
        assert result.summary==reply['summary'] and result.details[0].title=='关键资料'
        assert result.text=='\n\n'.join(reply['summary'])
        assert ai.cached_analysis(1)==result
        assert len(list((tmp_path/'forecasts').glob('*.json')))==1
    else:
        with pytest.raises((ValueError,ValidationError)):ai.generate_analysis(1)
        assert ai.cached_analysis(1) is None
        assert not (tmp_path/'forecasts').exists()
    assert sent['response_format']=={'type':'json_object'}
    assert len(sent['messages'][0]['content'])>10000
    assert '90 分钟' in sent['messages'][0]['content']
    context=json.loads(sent['messages'][1]['content'].split('\n',1)[1])
    assert len(context['recentMatches']['A'])==len(context['recentMatches']['B'])==1
    assert context['recentMatches']['A'][0]['date']=='2026-01-01'
    assert context['recentMatchScope']['clubs']['A']['seasonCounts']=={'2026/27':1}
    assert '不是本赛季完整战绩' in context['recentMatchScope']['meaning']
    assert context['currentSeasonRecords']['A']['matches']==1
    assert context['currentSeasonRecords']['A']['wins']==1
    assert context['currentSeasonRecords']['B']['losses']==1
    assert '禁止推算或编写' in sent['messages'][0]['content']
    assert not ai.GENERATION_LOCK.locked()
