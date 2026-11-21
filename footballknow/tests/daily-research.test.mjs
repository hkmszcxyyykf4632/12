import test from 'node:test';
import assert from 'node:assert/strict';
import {handicapAlerts} from '../public/odds-alerts.mjs';
import {JSDOM} from 'jsdom';
import {dailyRows} from '../public/daily-core.mjs';

const quote=(phase,line,extra={})=>({market:'asian-handicap',provider:'Provider A',via:'Feed',phase,line,prices:{H:1.9,A:1.9},fetchedAt:'2026-11-20T01:00:00Z',...extra});

test('finished matches compare saved pregame prices without substituting live odds',()=>{
  const match={home:'City',away:'United',competition:'英超',date:'2026-11-21',finished:true,
    quotes:[quote('opening',0),quote('latest',-.5,{lastPregame:true}),quote('latest',-3,{inPlay:true})]};
  const alerts=handicapAlerts(match,null);
  assert.equal(alerts.length,1);
  assert.equal(alerts[0].to,-.5);
  assert.match(alerts[0].basis,/赛前最后记录/);
});

test('handicap alerts require comparable providers and exclude live and manual prices',()=>{
  const match={home:'City',away:'United',competition:'英超',date:'2026-11-21',quotes:[quote('opening',-.5),quote('latest',-1.5)]};
  assert.equal(handicapAlerts(match,null)[0].change,-1);
  for(const extra of [{provider:'Provider B'},{via:'Other'},{inPlay:true},{manual:true}]){
    assert.deepEqual(handicapAlerts({...match,quotes:[quote('opening',-.5),quote('latest',-1.5,extra)]},null),[]);
  }
});

test('historical handicap alerts keep home-away direction and require two samples',()=>{
  const match={home:'City',away:'United',competition:'英超',date:'2026-11-21',quotes:[quote('latest',-1.5)]};
  const old=[{id:'a',date:'2025-10-01',home:'City',away:'United',competition:'英超',finished:true},{id:'b',date:'2024-10-01',home:'City',away:'United',competition:'英超',finished:true}];
  const feed={data:{matches:old},markets:{matches:{a:[quote('closing',-.5)],b:[quote('closing',-.5)]}}};
  assert.equal(handicapAlerts(match,feed)[0].sampleCount,2);
  assert.deepEqual(handicapAlerts(match,{...feed,data:{matches:[old[0]]}}),[]);
  assert.deepEqual(handicapAlerts(match,{...feed,data:{matches:[old[0],{...old[1],home:'United',away:'City'}]}}),[]);
});

test('global fixtures sort chronologically within the Hong Kong calendar day',()=>{
  const row=(id,kickoff)=>({id,competitionId:'100',competition:'Test',kickoff,day:'2026-11-20',updatedAt:'2026-11-19T16:00:00Z',teams:{home:{id:'1',name:'H',label:'主'},away:{id:'2',name:'A',label:'客'}}});
  const result=dailyRows({matches:[row('2','2026-11-20T02:00:00Z'),row('1','2026-11-19T17:00:00Z')]},[],{date:'2026-11-20'});
  assert.deepEqual(result.map(r=>r.id),['1','2']);
  assert.equal(dailyRows({matches:result},[],{date:'2026-11-21'}).length,0);
});

test('matching Chinese labels merge source name aliases only at the exact kickoff',()=>{
  const local={id:'local-city',home:'Man City',away:'Fulham',kickoff:'2026-11-21T12:30:00Z',competition:'英超'};
  const feed={league:'epl',data:{teams:[{name:'Man City',cn:'曼城'},{name:'Fulham',cn:'富勒姆'}]},live:{matches:[local]}};
  const global={id:'123',league:'epl',kickoff:local.kickoff,day:'2026-11-21',teams:{home:{id:'1',name:'Manchester City',label:'曼城'},away:{id:'2',name:'Fulham',label:'富勒姆'}}};
  const options={date:'2026-11-21',now:Date.parse('2026-11-21T00:00:00Z')};
  const rows=dailyRows({matches:[global]},[feed],options);
  assert.equal(rows.length,1);
  assert.equal(rows[0].id,'local-city');
  assert.equal(rows[0].dailyId,'123');
  assert.equal(rows[0].home,'Man City');
  assert.equal(dailyRows({matches:[{...global,kickoff:'2026-11-21T13:30:00Z'}]},[feed],options).length,2);
});

test('alerts cover retreat, direction reversal and price movements with an unchanged line',()=>{
  const run=(a,b)=>handicapAlerts({quotes:[a,b]},null);
  assert.equal(run(quote('opening',-2),quote('latest',-1))[0].type,'本场退盘');
  assert.equal(run(quote('opening',-.25),quote('latest',.25))[0].type,'让受方向反转');
  const prices=run(quote('opening',-.75,{prices:{H:2.2,A:1.7}}),quote('latest',-.75,{prices:{H:1.6,A:2.4}}));
  assert.ok(prices.some(a=>a.measure==='price'&&a.selection==='H'&&a.change<-.25));
  assert.deepEqual(run(quote('opening',-.5,{prices:{H:2.2,A:1.7}}),quote('latest',-.75,{prices:{H:1.6,A:2.4}})),[]);
});

test('totals and three-way prices use their own market and selection',()=>{
  const total=(phase,line)=>quote(phase,line,{market:'total-goals',prices:{O:1.9,U:1.9}});
  assert.equal(handicapAlerts({quotes:[total('opening',2.5),total('latest',3.5)]},null)[0].market,'total-goals');
  const three=(phase,H)=>quote(phase,null,{market:'90-minute-1x2',prices:{H,D:3.4,A:4.5}});
  const result=handicapAlerts({quotes:[three('opening',3.2),three('latest',2.3)]},null);
  assert.equal(result.length,1);
  assert.equal(result[0].selection,'H');
  assert.equal(result[0].measure,'price');
});


test('legacy motivation shows objective facts by default and retains unsupported guesses only in closed audit',async()=>{
  globalThis.document=new JSDOM('<main id="main"></main>').window.document;
  const {motivationHtml,motivationSummary}=await import('../public/daily-research.mjs');
  const team={team:'曼城',tendency:'争胜优先',summary:'推测争取三分',drawAcceptance:'较低',confidence:'中低',loseIntent:'无法判断',evidence:[{title:'赛前积分形势',fact:'本队第2、24分；对手第12、12分',inference:'推测争胜'},{title:'来源所列近期战绩',fact:'5场：3胜、1平、1负'}],missing:['首发名单'],checks:[{label:'全场取胜'}]};
  const original={generatedAt:'2026-11-21T08:00:00Z',version:'intent-rules-1',hash:'abcdefghijklmnop',teams:{home:team,away:{...team,team:'富咸',tendency:'保平倾向',summary:'推测接受平局'}}};
  const before=JSON.stringify(original);
  assert.match(motivationSummary({motivation:{original}},'away'),/第2、24分/);
  assert.doesNotMatch(motivationSummary({motivation:{original}},'away'),/保平|接受平局/);
  const review={teams:{home:{summary:'2/2项赛前指标得到支持',checks:[{label:'取胜',observed:'2:1',passed:true}]}}};
  const document=new JSDOM(motivationHtml({motivation:{original,review}})).window.document;
  for(const detail of document.querySelectorAll('details'))assert.equal(detail.open,false);
  const visible=document.body.cloneNode(true);visible.querySelectorAll('details').forEach(node=>node.remove());
  assert.match(visible.textContent,/第2、24分/);assert.match(visible.textContent,/3胜、1平、1负/);
  assert.doesNotMatch(visible.textContent,/争胜优先|保平倾向|推测争取三分|2\/2项|原接受平局判断/);
  assert.match(document.querySelector('[data-disclosure="motivation-away-original"]').textContent,/保平倾向/);
  assert.match(document.querySelector('[data-disclosure="motivation-home-original"]').textContent,/2\/2项赛前指标得到支持/);
  assert.equal(JSON.stringify(original),before);
});

test('new motivation and absent snapshots use actual context and separate conditional scenarios from goals',async()=>{
  globalThis.document=new JSDOM('<main id="main"></main>').window.document;
  const {motivationHtml}=await import('../public/daily-research.mjs');
  const teams={home:{label:'曼城',form:'WWDWL'},away:{label:'富咸',form:'LWDLD'}};
  for(const original of [null,{version:'match-context-2',teams:{home:{team:'曼城',evidence:[{title:'赛前积分形势',fact:'本队第2、24分'}]},away:{team:'富咸',evidence:[]}}}]){
    const document=new JSDOM(motivationHtml({teams,motivation:{original,review:{teams:{home:{observations:[{label:'90分钟比分（本队在前）',observed:'2 : 1'}]}}}}})).window.document;
    assert.match(document.body.textContent,/比赛目标须有明确表态/);
    assert.match(document.body.textContent,/比分预测单独呈现/);
    assert.match(document.body.textContent,/2 : 1/);
    assert.equal(document.querySelector('[data-disclosure="motivation-home-original"]'),null);
    const scenarios=document.querySelector('[data-disclosure="motivation-home-scenarios"]');
    assert.equal(scenarios.open,false);assert.match(scenarios.textContent,/若比分落后/);
    assert.match(document.querySelectorAll('.intent-team')[1].textContent,/1胜、2平、2负/);
  }
});
