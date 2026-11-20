import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
const dom=new JSDOM('<main id="main"></main>',{url:'https://example.test/'});
globalThis.document=dom.window.document;
const {forecastsHtml,forecastMatches}=await import('../public/football-forecasts.mjs');
const {dailyRows}=await import('../public/daily-core.mjs');
const row={id:'123',dailyId:'123',competitionId:'710',kickoff:'2026-11-21T16:00:00Z',day:'2026-11-22',teams:{home:{id:'1',label:'甲'},away:{id:'2',label:'乙'}}};
const now=Date.parse('2026-11-21T08:00:00Z');
const value={supported:true,eventId:'123',kickoff:row.kickoff,teams:{home:'1',away:'2'},stages:{initial:{report:null,message:'等待到点'},final:{report:null,message:'等待双方正式首发'}}};

test('both fixed slots appear before prediction exists including Ligue 1',()=>{
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
test('five major league filter includes France and excludes Champions League',()=>{
  const matches=[row,{...row,id:'124',competitionId:'775',league:'ucl'}];
  assert.deepEqual(dailyRows({matches},[],{date:'2026-11-22',competition:'major',now}).map(m=>m.dailyId),['123']);
});
