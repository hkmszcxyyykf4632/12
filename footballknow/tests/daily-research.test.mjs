import test from 'node:test';
import assert from 'node:assert/strict';
import {handicapAlerts} from '../public/odds-alerts.mjs';
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
