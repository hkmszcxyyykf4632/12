import json
from datetime import datetime, timezone

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from pydantic import SecretStr

import server
from football import ai, auth, history, live, names, sync_control, stock_analysis
from football.analysis import Match, poisson_baseline
from football.name_rosters import roster_names
from sync_data import validate_feed


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(auth,'STATE',tmp_path)
    monkeypatch.setattr(ai,'STATE',tmp_path)
    monkeypatch.setattr(sync_control,'STATE',tmp_path)
    monkeypatch.setattr(stock_analysis,'STATE',tmp_path)
    monkeypatch.delenv('FOOTBALL_PRODUCTION',raising=False)
    salt='ab'*16
    seed={'users':[{'username':name,'salt':salt,'password_hash':auth.password_hash('test-pass-long-123',salt)} for name in ['admin01','admin02']]}
    (tmp_path/'admin-seed.json').write_text(json.dumps(seed),encoding='utf-8')
    with TestClient(server.app,base_url='http://testserver',headers={'Origin':'http://testserver'}) as session:
        yield session


def sign_in(client, username='admin01'):
    response=client.post('/api/auth/login',json={'username':username,'password':'test-pass-long-123'})
    assert response.status_code==200
    return response


def test_two_accounts_sessions_and_private_routes(client):
    assert client.get('/api/ai/settings').status_code==401
    assert client.put('/api/analysis/rules',json={'text':'a'*100}).status_code==401
    assert client.get('/state/admin-seed.json').status_code==404
    for username in ['admin01','admin02']:
        response=sign_in(client,username)
        assert 'HttpOnly' in response.headers['set-cookie']
        assert 'SameSite=strict' in response.headers['set-cookie']
        assert client.get('/api/auth/me').json()['username']==username
        assert client.post('/api/auth/logout').status_code==200
        assert client.get('/api/auth/me').json()['authenticated'] is False


def test_origin_password_change_and_secret_redaction(client):
    assert client.post('/api/auth/login',headers={'Origin':'https://other.example'},json={}).status_code==403
    sign_in(client)
    invalid=client.put('/api/ai/settings',json={'baseUrl':'x'*501,'apiKey':'private-sentinel'})
    assert invalid.status_code==422 and 'private-sentinel' not in invalid.text
    assert client.post('/api/auth/password',json={'current':'test-pass-long-123','replacement':'new-pass-long-456'}).status_code==200
    assert client.get('/api/auth/me').json()['authenticated'] is False
    assert client.post('/api/auth/login',json={'username':'admin01','password':'test-pass-long-123'}).status_code==401
    assert client.post('/api/auth/login',json={'username':'admin01','password':'new-pass-long-456'}).status_code==200


def test_ai_key_never_read_back_and_local_addresses_rejected(client,monkeypatch):
    sign_in(client)
    monkeypatch.setattr(ai.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('8.8.8.8',443))])
    response=client.put('/api/ai/settings',json={'baseUrl':'https://example.com/v1','model':'model-name','apiKey':'private-sentinel'})
    assert response.status_code==200
    assert response.json()['configured'] is True
    assert 'private-sentinel' not in response.text
    assert 'apiKey' not in client.get('/api/ai/settings').json()
    assert client.put('/api/ai/settings',json={'baseUrl':'https://other.example/v1','model':'x','apiKey':''}).status_code==400
    monkeypatch.setattr(ai.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError):ai.endpoint_for('https://localhost/v1')
    with pytest.raises(ValueError):ai.endpoint_for('http://example.com/v1')


def test_login_limit_bounds_unknown_names(client):
    for index in range(11):
        assert client.post('/api/auth/login',json={'username':f'unknown{index}','password':'wrong'}).status_code==401
    with auth.database() as connection:
        assert connection.execute('SELECT count(*) FROM login_attempts').fetchone()[0]==1
    assert sign_in(client).status_code==200


def test_deepseek_only_requires_key_and_preserves_it_when_blank(client,monkeypatch):
    sign_in(client)
    initial=client.get('/api/ai/settings').json()
    assert initial=={'baseUrl':'https://api.deepseek.com','model':'deepseek-flash','configured':False}
    monkeypatch.setattr(ai.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('8.8.8.8',443))])
    saved=client.put('/api/ai/settings',json={'apiKey':'deepseek-private-sentinel'})
    assert saved.status_code==200 and saved.json()['configured'] is True
    assert saved.json()['baseUrl']=='https://api.deepseek.com'
    assert saved.json()['model']=='deepseek-flash'
    assert 'deepseek-private-sentinel' not in saved.text
    assert client.put('/api/ai/settings',json={'apiKey':''}).status_code==200
    assert ai.settings().apiKey.get_secret_value()=='deepseek-private-sentinel'


def test_poisson_normalizes_and_excludes_future_scores():
    fixture=Match(id='next',date='2026-11-20',home='A',away='B',finished=False,competition='英超',season='2026/27')
    rows=[Match(id=str(i),date=f'2026-10-{i+1:02}',home='A' if i%2 else 'C',away='B',homeGoals=2,awayGoals=1,finished=True,competition='英超',season='2026/27') for i in range(25)]
    baseline=poisson_baseline(rows,fixture)
    assert baseline is not None
    assert sum(baseline.probabilities.model_dump().values())==pytest.approx(1)
    later=rows[0].model_copy(update={'date':'2026-11-21','homeGoals':20})
    assert poisson_baseline(rows+[later],fixture)==baseline
    assert poisson_baseline(rows[:5],fixture) is None


def test_complete_live_fixture_feed_and_provisional_results():
    catalogue=live.Catalogue(season='2026/27',teams=[live.Team(id=i,name=f'Team{i}') for i in range(1,21)])
    rows=[live.Fixture(id=n,team_h=h,team_a=a) for n,(h,a) in enumerate((h,a) for h in range(1,21) for a in range(1,21) if h!=a)]
    rows[0]=rows[0].model_copy(update={'started':True,'finished_provisional':True,'team_h_score':2,'team_a_score':1})
    snapshot=live.build_snapshot(rows,catalogue)
    assert snapshot.matches[0].result is None
    assert snapshot.matches[0].started and snapshot.matches[0].provisional
    rows[0]=rows[0].model_copy(update={'finished':True})
    assert live.build_snapshot(rows,catalogue).matches[0].result=='H'
    with pytest.raises(OSError):live.build_snapshot(rows[:379],catalogue)


def test_history_expands_inherited_cells_and_accepts_plural_manager_header(monkeypatch):
    markup='<table class="wikitable"><tr><th>Team</th><th>Outgoing manager</th><th>Manner of departure</th><th>Date of vacancy</th><th>Incoming manager(s)</th><th>Date of appointment</th></tr><tr><td rowspan="2">Arsenal</td><td>A</td><td>Resigned</td><td>1 June 2026</td><td>B (interim)</td><td>2 June 2026</td></tr><tr><td>B</td><td>End of interim spell</td><td>5 June 2026</td><td>C</td><td>6 June 2026</td></tr></table>'
    monkeypatch.setattr(history,'fetch_text',lambda url:markup)
    rows=history.collect_managers('https://example.com/history',{'Arsenal'})
    assert len(rows)==2 and rows[1].team=='Arsenal'
    assert rows[0].joinedAt=='2026-06-02' and '(interim)' in rows[0].incoming


def test_translation_match_handles_nonbreaking_spaces():
    player=names.Player(id=1,code=2,first_name='Example',second_name='Player',web_name='Player',birth_date='2000-05-30')
    page=names.WikiPage(title='Example Player',extract='Footballer born 30\u00a0May 2000.')
    assert names.birth_matches(player,page)
    assert not names.birth_matches(player,page.model_copy(update={'extract':'born 31 May 2000'}))


def test_roster_names_ignore_navigation_and_read_exact_english_identity():
    markup='<table><tr><td><span class="ilh-all" data-lang-code="en" data-foreign-title="James Hill (footballer, born 2002)"><span class="ilh-page">占士·希爾</span></span></td></tr></table><table class="navbox-inner"><tr><td><span class="ilh-all" data-lang-code="en" data-foreign-title="Another Person"><span class="ilh-page">導覽簡稱</span></span></td></tr></table>'
    assert roster_names(markup)=={'jameshill':'占士·希爾'}


@pytest.mark.parametrize('origin', ['https://footballknow.art', 'https://www.footballknow.art', 'https://inwesting.shop', 'https://www.inwesting.shop'])
def test_production_rejects_insecure_origin_and_sets_secure_cookie(client,monkeypatch,origin):
    monkeypatch.setenv('FOOTBALL_PRODUCTION','1')
    monkeypatch.delenv('FOOTBALL_ALLOWED_ORIGINS',raising=False)
    payload={'username':'admin01','password':'test-pass-long-123'}
    for rejected in ['http://footballknow.art', 'http://inwesting.shop', 'https://inwesting.shop.evil.example', 'https://tripitaka.shop']:
        assert client.post('/api/auth/login',json=payload,headers={'Origin':rejected}).status_code==403
    response=client.post('/api/auth/login',json=payload,headers={'Origin':origin})
    assert response.status_code==200 and 'Secure' in response.headers['set-cookie']


def test_source_error_pages_cannot_replace_historical_data():
    with pytest.raises(ValueError):validate_feed('2026-E0','<html>Temporarily unavailable</html>')
    with pytest.raises(ValueError):validate_feed('fixtures','[]')
    header='Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n'
    assert validate_feed('2026-E0',header)==header


def test_health_reports_synchronizer_heartbeat_and_snapshots_revalidate(client,tmp_path,monkeypatch):
    public=tmp_path/'public';public.mkdir()
    monkeypatch.setattr(server,'PUBLIC',public)
    assert client.get('/api/health').status_code==503
    (public/'sync-status.json').write_text(json.dumps({'running':True,'heartbeat':datetime.now(timezone.utc).isoformat(),'syncSeconds':60,'summary':{'total':25,'ok':25,'failed':0,'pending':0}}),encoding='utf-8')
    response=client.get('/api/health')
    assert response.status_code==200 and response.json()['status']=='ok' and response.json()['syncSeconds']==60
    assert response.headers['cache-control']=='no-store'
    assert client.get('/standings.json').headers['cache-control']=='no-cache'
    monkeypatch.setenv('FOOTBALL_ALLOWED_ORIGINS','https://client.example')
    assert server.allowed_origins()=={'https://client.example'}


def test_admin_sync_switch_requires_login_and_remembers_state(client):
    assert client.get('/api/sync/control').status_code == 401
    assert client.put('/api/sync/control', json={'enabled': False}).status_code == 401
    sign_in(client)
    assert client.put('/api/sync/control', json={'enabled': 'false'}).status_code == 422
    assert client.put('/api/sync/control', json={'enabled': False}, headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.put('/api/sync/control', json={'enabled': False}).json()['enabled'] is False
    assert client.get('/api/sync/control').json()['enabled'] is False
    assert client.get('/sync-control.json').status_code == 404
    assert client.put('/api/sync/control', json={'enabled': True}).json()['enabled'] is True


def test_paused_match_does_not_trigger_network(client, monkeypatch):
    sign_in(client)
    client.put('/api/sync/control', json={'enabled': False})
    calls = []
    monkeypatch.setattr(server, 'get_detail', lambda *args, **kwargs: calls.append(kwargs) or None)
    assert client.get('/api/match?match_id=example').status_code == 503
    assert calls == [{'fetch_missing': False}]


def test_stock_analysis_public_get_is_unrated_and_post_requires_admin(client):
    result = client.get('/api/stocks/00700/analysis')
    assert result.status_code == 200 and result.json()['evaluation']['week']['successRate'] is None
    assert client.post('/api/stocks/00700/analysis').status_code == 401
    assert client.get('/api/stocks/abc/analysis').status_code == 404


def test_video_admin_drafts_and_publication(client, tmp_path, monkeypatch):
    from football import videos
    monkeypatch.setattr(videos, 'PATH', tmp_path / 'videos.json')
    draft = {'title': 'Research video', 'url': 'https://example.com/research.mp4', 'published': False}
    assert client.get('/api/admin/videos').status_code == 401
    assert client.post('/api/admin/videos', json=draft).status_code == 401
    assert client.get('/api/videos').json()['videos'] == []
    sign_in(client)
    assert client.post('/api/admin/videos', json=draft, headers={'Origin': 'https://evil.example'}).status_code == 403
    saved = client.post('/api/admin/videos', json=draft)
    assert saved.status_code == 200
    ident = saved.json()['id']
    assert client.get('/api/videos').json()['videos'] == []
    assert len(client.get('/api/admin/videos').json()['videos']) == 1
    assert client.put('/api/admin/videos/' + ident, json={**draft, 'published': True}).status_code == 200
    assert client.get('/api/videos').json()['videos'][0]['id'] == ident
    assert client.put('/api/admin/videos/' + ident, json=draft).status_code == 200
    assert client.get('/api/videos').json()['videos'] == []
    assert client.post('/api/admin/videos', json={**draft, 'url': 'javascript:alert(1)'}).status_code == 422
