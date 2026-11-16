import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';

const root = new URL('../public/', import.meta.url);
const snapshots = Object.fromEntries(await Promise.all(['data','live','names','history','standings','rankings','odds','odds-sources'].map(async name => [name,JSON.parse(await readFile(new URL(`${name}.json`,root),'utf8'))])));
const tick = () => new Promise(resolve => setTimeout(resolve,20));

test('club search, manual odds, locked simulation, two-step settlement and backup restoration', async () => {
  const dom = new JSDOM(await readFile(new URL('index.html',root),'utf8'), {url:'http://localhost:8765/'});
  const w = dom.window;
  let loggedIn=false, configured=false, storedKey='', delayAnalysis=false, releaseAnalysis;
  w.scrollTo = () => {};
  w.HTMLElement.prototype.scrollIntoView = () => {};
  Object.assign(globalThis,{window:w,document:w.document,location:w.location,localStorage:w.localStorage,
    FormData:w.FormData,matchMedia:()=>({matches:true}),CSS:{escape:value=>value}});
  globalThis.fetch = async (path,options={}) => {
    const key = String(path).replace(/^\.\//,'').replace('.json','');
    let body=snapshots[key];
    if(String(path).startsWith('/api/match?'))body={status:'available',duration:90,lineups:{home:{name:'Arsenal',formation:'4-3-3',players:[{espnId:'test',name:'<img src=x onerror=alert(1)>',position:'DM',starter:true,played:true,minutes:90,minutesEstimated:true}]}},statistics:[],events:[],updatedAt:new Date().toISOString()};
    else if(path==='/api/auth/me')body={authenticated:loggedIn,username:loggedIn?'admin01':null};
    else if(path==='/api/auth/login'){loggedIn=true;body={authenticated:true,username:'admin01'};}
    else if(path==='/api/auth/logout'){loggedIn=false;body={ok:true};}
    else if(path==='/api/ai/settings') {
      if(options.method==='PUT'){const incoming=JSON.parse(options.body);assert.deepEqual(Object.keys(incoming),['apiKey']);storedKey=incoming.apiKey;configured=true;}
      body={baseUrl:'https://api.deepseek.com',model:'deepseek-flash',configured};
    }
    else if(path==='/api/analysis/rules')body=options.method==='PUT'?{ok:true}:{text:'只使用有来源的比赛资料，区分事实、计算、推断与缺失信息。'.repeat(5)};
    else if(path==='/api/status')body={running:true,heartbeat:new Date().toISOString(),jobs:{live:{ok:true,lastSuccess:new Date().toISOString()}}};
    else if(String(path).startsWith('/api/analysis/')) {
      if(delayAnalysis)await new Promise(resolve=>{releaseAnalysis=resolve;});
      const club=snapshots.data.teams.find(row=>row.id===Number(String(path).split('/').pop()));
      const fixture=snapshots.live.matches.find(row=>row.home===club.name&&!row.finished);
      const form=team=>({team,matches:20,wins:10,draws:5,losses:5,scored:30,conceded:20});
      body=options.method==='POST'?{generatedAt:new Date().toISOString(),model:'test-model',rulesVersion:'test-rules',pick:'H',summary:['主队是本场的首选方向。','两队近期进失球与主客场差异支持这一判断，首发确定后可更新。'],details:[{title:'数据依据',text:'<img src=x onerror=alert(1)> 详细数据摘要'}]}:{report:{team:club,match:fixture,dataUpdatedAt:snapshots.data.updatedAt,liveUpdatedAt:snapshots.live.updatedAt,
        homeForm:form(fixture.home),awayForm:form(fixture.away),unavailablePlayers:[],checklist:['先检查资料时间与样本。'],
        baseline:{probabilities:{home:0.4,draw:0.3,away:0.3},homeGoalMean:1.4,awayGoalMean:1.1,homeSample:20,awaySample:20,leagueSample:380,scorelines:[['1:1',0.14]],limitations:['未训练的测试基线']}},
        ai:{generatedAt:new Date().toISOString(),model:'test-model',rulesVersion:'test-rules',text:'<img src=x onerror=alert(1)> 分析原文'},aiMatchesNext:false};
    }
    if(body===undefined)throw new Error(`Unexpected network request: ${path}`);
    return {ok:true,status:200,json:async()=>structuredClone(body)};
  };
  const field = (id,value) => {const element=w.document.getElementById(id);element.value=value;element.dispatchEvent(new w.Event('input',{bubbles:true}));return element;};
  const route = async path => {w.location.hash=path;await tick();};
  const click = selector => w.document.querySelector(selector).click();
  const saved = () => JSON.parse(w.localStorage.getItem('footballknow.personal.v1'));
  try {
    const application=await import('../public/app.js');
    await tick();
    const {localized}=await import('../public/football-components.mjs');
    assert.ok(snapshots.data.players.every(player=>localized(player)?.mandarin&&localized(player)?.cantonese));
    await route('#/rankings');
    assert.equal(w.document.querySelectorAll('#rank-content tbody tr').length,20);
    click('[data-board="players"]');
    const playerSearch=field('rank-search','no-such-player');playerSearch.focus();
    application.updateView();
    assert.equal(w.document.querySelectorAll('#rank-content tbody tr').length,0);
    assert.equal(w.document.activeElement,playerSearch,'polling preserves focused filters');
    field('rank-search','');
    assert.equal(w.document.querySelectorAll('#rank-content tbody tr').length,snapshots.rankings.boards.scorers.length);
    await route('#/following');
    click('[data-follow]');await tick();
    assert.equal(JSON.parse(w.localStorage.getItem('footballknow-followed-v1-epl')).length,1);
    await route('#/matches');
    const matchStatus=w.document.querySelector('#match-status');matchStatus.value='finished';matchStatus.dispatchEvent(new w.Event('change'));
    assert.ok(w.document.querySelectorAll('.match-list-row').length>0);
    const detailLink=w.document.querySelector('.match-result').getAttribute('href');
    await route(detailLink);await tick();
    assert.ok(w.document.querySelector('.lineup-pitch'));
    assert.equal(w.document.querySelector('#match-detail-body img'),null,'lineup names are escaped');
    assert.equal(w.document.querySelectorAll('.pitch-line')[2].querySelectorAll('.pitch-player').length,1,'defensive midfield stays in midfield');
    await route('#/teams');
    assert.equal(w.document.querySelectorAll('[data-team-search]').length,20);
    field('team-search','zz-no-club');
    assert.equal(w.document.querySelectorAll('[data-team-search]:not(.hidden)').length,0);
    field('team-search','曼联');
    assert.equal(w.document.querySelectorAll('[data-team-search]:not(.hidden)').length,1);
    const club = snapshots.data.teams.find(row=>row.name==='Man Utd');
    await route(`#/team/${club.id}`);
    assert.equal(w.document.querySelectorAll('#matches-table tbody tr').length,20);
    assert.ok(w.document.querySelectorAll('[data-player]').length>20);
    const translated=snapshots.data.players.find(p=>p.team===club.id&&snapshots.names.names[String(p.code)]);
    field('player-search',snapshots.names.names[String(translated.code)].cantonese);
    assert.equal(w.document.querySelectorAll('[data-player]:not(.hidden)').length,1);
    application.updateView();
    assert.equal(w.document.querySelectorAll('[data-player]:not(.hidden)').length,1,'polling retains player filters');
    assert.ok(w.document.querySelector('#transfers-section'));
    assert.ok(w.document.querySelector('#managers-section'));
    await route('#/simulator');
    field('home','测试主队');field('away','测试客队');field('match-date','2020-01-02');
    field('odds-H','2.10');field('odds-D','3.20');field('odds-A','4.00');
    application.updateView();
    assert.equal(w.document.querySelector('#home').value,'测试主队','background update preserves unsaved input');
    click('#save-odds');
    assert.equal(saved().odds.length,1);
    field('stake','100');
    w.document.querySelector('#bet-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
    await tick();
    assert.equal(saved().bets[0].oddsMilli,2100);
    assert.equal(saved().bets[0].result,null);
    const select=w.document.querySelector('[data-settle-value]');
    select.value='H';click('[data-settle]');
    assert.equal(saved().bets[0].result,null);
    select.value='A';click('[data-settle]');
    assert.equal(saved().bets[0].result,null,'changing result requires a new confirmation');
    click('[data-settle]');
    assert.equal(saved().bets[0].result,'A');
    click('[data-use-odds]');await tick();field('odds-H','9.00');click('#save-odds');
    assert.equal(saved().odds[0].H,9);
    assert.equal(saved().bets[0].oddsMilli,2100,'saved quote edits never change locked bets');
    await route('#/records');
    const input=w.document.querySelector('#import-data');
    Object.defineProperty(input,'files',{value:[{size:60,text:async()=>JSON.stringify({version:1,bets:[],odds:[]})}]});
    input.dispatchEvent(new w.Event('change'));await tick();
    assert.equal(saved().bets.length,1,'import waits for inline confirmation');
    click('#cancel-import');assert.equal(saved().bets.length,1);
    input.dispatchEvent(new w.Event('change'));await tick();click('#confirm-import');
    assert.equal(saved().bets.length,0);
    await route('#/sources');
    assert.match(w.document.querySelector('#main').textContent,/未接入实时赔率/);
    await route(`#/analysis/${club.id}`);await tick();
    assert.equal(w.document.querySelectorAll('.probability').length,3);
    assert.equal(w.document.querySelector('#analysis-details').open,false);
    assert.equal(w.document.querySelectorAll('#ai-answer .analysis-summary p').length,2);
    assert.match(w.document.querySelector('#ai-answer').textContent,/本地数据简报/);
    assert.doesNotMatch(w.document.querySelector('#ai-answer').textContent,/分析原文/);
    assert.match(w.document.querySelector('#ai-detail-answer').textContent,/之前比赛/);
    assert.equal(w.document.querySelectorAll('#ai-answer img').length,0);
    assert.match(w.document.querySelector('.ai-answer').textContent,/<img/);
    click('#analysis-details > summary');
    assert.equal(w.document.querySelector('#analysis-details').open,true);
    await route('#/teams');
    delayAnalysis=true;await route(`#/analysis/${club.id}`);
    await route('#/teams');releaseAnalysis();await tick();delayAnalysis=false;
    assert.equal(w.document.querySelectorAll('[data-team-search]').length,20,'late analysis response cannot replace a newer route');
    await route('#/admin');await tick();
    field('admin-username','admin01');field('admin-password','test-secret');
    w.document.querySelector('#login-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();
    assert.ok(w.document.querySelector('#ai-settings-form'));
    assert.equal(w.document.querySelector('#rules-text').maxLength,16000);
    assert.equal(w.document.querySelectorAll('#ai-settings-form input').length,1,'DeepSeek needs only an API key');
    assert.ok(w.document.querySelector('#ai-key').required);
    field('ai-key','private-api-sentinel');
    w.document.querySelector('#ai-settings-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();
    assert.equal(storedKey,'private-api-sentinel');
    assert.equal(w.document.querySelector('#ai-key').value,'');
    assert.equal(w.document.querySelector('#ai-key').required,false);
    assert.ok(!w.document.body.innerHTML.includes('private-api-sentinel'));
    assert.ok(![...Array(w.localStorage.length)].map((_,i)=>w.localStorage.getItem(w.localStorage.key(i))).join('').includes('private-api-sentinel'));
    field('rules-text','尚未保存的分析规范。'.repeat(10));application.updateView();
    assert.equal(w.document.querySelector('#rules-text').value,'尚未保存的分析规范。'.repeat(10));
    await route(`#/analysis/${club.id}`);await tick();
    click('#analysis-details > summary');click('#generate-analysis');await tick();
    assert.equal(w.document.querySelector('#analysis-details').open,true,'generation retains disclosure state');
    assert.equal(w.document.querySelectorAll('#ai-answer .analysis-summary p').length,2);
    assert.match(w.document.querySelector('#ai-answer').textContent,/主队是本场的首选方向/);
    assert.doesNotMatch(w.document.querySelector('#ai-answer').textContent,/详细数据/);
    assert.match(w.document.querySelector('#ai-detail-answer').textContent,/详细数据摘要/);
    assert.equal(w.document.querySelectorAll('#ai-detail-answer img').length,0);
    await route('#/admin');await tick();click('#sign-out');await tick();assert.ok(w.document.querySelector('#login-form'));
  } finally {w.dispatchEvent(new w.Event('pagehide'));w.close();}
});
