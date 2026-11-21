import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
const dom=new JSDOM('<main id="main"></main>',{url:'https://example.test/'});
globalThis.document=dom.window.document;
const {forecastsHtml,forecastMatches}=await import('../public/football-forecasts.mjs');
const row={id:'123',dailyId:'123',competitionId:'700',kickoff:'2026-11-21T16:00:00Z',day:'2026-11-22',teams:{home:{id:'1',label:'甲'},away:{id:'2',label:'乙'}}};
const now=Date.parse('2026-11-21T08:00:00Z');
const value={supported:true,eventId:'123',kickoff:row.kickoff,teams:{home:'1',away:'2'},stages:{initial:{report:null,message:'等待到点'},final:{report:null,message:'等待双方正式首发'}}};

test('both fixed slots appear before prediction exists for supported competitions',()=>{
  document.querySelector('main').innerHTML=forecastsHtml(row,value,now);
  assert.equal(document.querySelectorAll('.forecast-card').length,2);
  assert.match(document.querySelector('main').textContent,/等待双方正式首发/);
});
test('reports retain their score timestamp handicap and escaped evidence',()=>{
  const r={score:[2,1],asianSide:'A',issuedAt:'2026-11-21T09:00:00Z',quote:{line:-.75,prices:{H:1.9,A:1.95},source:'javascript:alert(1)',provider:'样本',fetchedAt:'2026-11-21T09:00:00Z'},summary:['<img src=x>','依据'],details:[{title:'详情',text:'<script>alert(1)</script>'}],review:{status:'evaluated',text:'完场2:1；亚洲盘输半。'}};
  const v=structuredClone(value);v.stages.initial.report=r;
  document.querySelector('main').innerHTML=forecastsHtml(row,v,now);
  assert.match(document.querySelector('.forecast-result').textContent,/乙 受让 0.75 球/);
  assert.equal(document.querySelectorAll('img,script,a[href^="javascript"]').length,0);
  assert.match(document.querySelector('.forecast-review').textContent,/输半/);
});
test('rescheduling and opponent changes prevent stale report reuse',()=>{
  assert.equal(forecastMatches(value,row),true);
  assert.equal(forecastMatches(value,{...row,kickoff:'2026-11-22T16:00:00Z'}),false);
  assert.equal(forecastMatches(value,{...row,teams:{...row.teams,away:{id:'3'}}}),false);
});
test('forecast analysis scope is only Champions League and four major leagues',()=>{
  for(const competitionId of ['700','740','730','720','775'])assert.match(forecastsHtml({...row,competitionId},value,now),/forecast-card/);
  for(const competitionId of ['710','100','776'])assert.equal(forecastsHtml({...row,competitionId,league:'epl'},value,now),'');
  assert.match(forecastsHtml({...row,competitionId:undefined,league:'ucl'},value,now),/forecast-card/);
  assert.equal(forecastsHtml({...row,competitionId:undefined,league:'ligue1'},value,now),'');
});
test('dated fallback quotes are visibly distinguished from live quotes',()=>{
  const v=structuredClone(value);
  v.stages.initial.report={score:[2,1],asianSide:'pass',issuedAt:'2026-11-21T09:00:00Z',summary:['结论','依据'],details:[],reference:{sourceUpdatedAt:'2026-11-20T10:23:08Z',source:'https://www.football-data.co.uk/fixtures.csv'}};
  document.querySelector('main').innerHTML=forecastsHtml(row,v,now);
  assert.match(document.querySelector('.forecast-reference').textContent,/赛前参考版.*非即时盘口/);
  assert.equal(document.querySelector('.forecast-reference a').href,'https://www.football-data.co.uk/fixtures.csv');
});


test('both forecast stages keep conclusions visible with distinct stable disclosure keys',()=>{
  const v=structuredClone(value);
  for(const stage of ['initial','final'])v.stages[stage].report={score:[2,1],asianSide:'pass',issuedAt:'2026-11-21T09:00:00Z',summary:['简短结论'],details:[{title:'依据',text:'较长分析资料'}],review:{status:'evaluated',text:'赛果已确认',analysis:{dossier:{domain:'football'},summary:['复盘摘要'],drivers:[{title:'关键转折',explanation:'进球改变局势'}]}}};
  document.querySelector('main').innerHTML=forecastsHtml(row,v,now);
  const details=[...document.querySelectorAll('details[data-disclosure]')];
  assert.equal(details.length,16);assert.equal(new Set(details.map(node=>node.dataset.disclosure)).size,16);
  assert.ok(details.every(node=>!node.open));
  for(const stage of ['initial','final']){
    const basis=document.querySelector(`[data-disclosure="forecast-${stage}-basis"]`);
    assert.match(basis.textContent,/较长分析资料/);
    assert.equal(basis.closest('.forecast-card').querySelector('.forecast-result').closest('details'),null);
    assert.ok(document.querySelector(`[data-disclosure="forecast-${stage}-review-sources"]`));
  }
});


test('score scenario separates match winner from handicap result including quarter lines',()=>{
  for(const [line,asianSide,expected] of [[-1.5,'A','乙 受让 1.5 球：赢盘'],[-1.25,'A','乙 受让 1.25 球：半赢'],[-.75,'H','甲 让 0.75 球：半赢'],[-1.25,'H','甲 让 1.25 球：半输'],[-1,'H','甲 让 1 球：走盘']]){
    const v=structuredClone(value);
    v.stages.initial.report={score:[2,1],asianSide,quote:{line,prices:{H:1.9,A:1.9}},issuedAt:'2026-11-21T09:00:00Z',summary:[],details:[]};
    document.querySelector('main').innerHTML=forecastsHtml(row,v,now);
    const relationship=document.querySelector('.forecast-score-meaning').textContent;
    assert.match(relationship,/甲赢球/);assert.ok(relationship.includes(expected),relationship);
    assert.match(document.querySelector('.forecast-card').textContent,/全部比分概率与赔率/);
    assert.equal(v.stages.initial.report.asianSide,asianSide);
  }
});
