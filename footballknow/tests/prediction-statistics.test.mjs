import test from 'node:test';
import assert from 'node:assert/strict';
import {footballSelection,footballTotals,poolTotals,poolAccuracy,paperTotals,celebrations,byRound} from '../public/prediction-stats-core.mjs';
const football=(id,hit=true,extra={})=>({identity:id,eventId:id,league:'epl',day:'2026-11-21',season:'2026/27',round:'第11轮',roundComplete:true,stage:'initial',issuedAt:'2026-11-21T10:00Z',status:'settled',exactHit:hit,resultHit:hit,asianResult:hit?'赢盘':'输盘',...extra});
const ticket=(combination,status,dividend)=>({combination,status,dividend,multiple:dividend/10});
const race={raceId:'2026-11-22-ST-1',day:'2026-11-22',courseName:'沙田',raceNo:1,status:'settled',runners:[{number:'1',name:'甲'},{number:'2',name:'乙'},{number:'3',name:'丙'}],pools:[{type:'WIN',tickets:[ticket('1','hit',110),ticket('2','miss',0),ticket('3','miss',0)]},{type:'PLA',tickets:[ticket('1','hit',20),ticket('2','hit',30),ticket('3','miss',0)]},...['QIN','QPL'].map(type=>({type,tickets:[ticket('1,2','hit',type==='QIN'?500:40),ticket('1,3','miss',0),ticket('2,3','miss',0)]}))]};
test('adopted selects confirmed final once; versions remain independently comparable',()=>{
 const rows=[football('a'),football('a',false,{stage:'final'}),football('b')];
 assert.equal(footballSelection(rows).length,2);assert.equal(footballTotals(footballSelection(rows)).exact,1);
 assert.equal(footballTotals(footballSelection(rows,'initial')).exact,2);
});
test('pushes passes pending and void do not inflate Asian hit denominator',()=>{
 const s=footballTotals(['赢盘','赢半','走盘','输半','输盘','unselected','unverified'].map((asianResult,i)=>football(String(i),true,{asianResult})).concat(football('p',false,{status:'pending'})));
 assert.equal(s.asianHits,2);assert.equal(s.asian,4);assert.equal(s.settled,7);assert.equal(s.pending,1);
});
test('simulation follows the fixed 660 stake and includes losing pairs',()=>{
 const t=paperTotals([race]);assert.equal(t.planned,660);assert.equal(t.stake,660);assert.equal(t.returns,2140);assert.equal(t.net,1480);
 const q=poolTotals([race],'QIN');assert.equal(q.hits,1);assert.equal(q.winningTickets,1);assert.equal(q.tickets,3);assert.equal(q.multiple,500/30);
});
test('pending stake not declared lost; withdrawals refunded and removed from denominator',()=>{
 const r=structuredClone(race);r.pools[0].tickets=[ticket('1','refund',10),ticket('2','pending',null),ticket('3','pending',null)];
 const t=paperTotals([r]);assert.equal(t.pending,200);assert.equal(t.refunds,100);assert.equal(t.stake,360);
});
test('homepage celebrations remain disabled even for winning high-dividend meetings',()=>{
 assert.deepEqual(celebrations([football('a')],[{...race,meetingComplete:true}]),[]);
 assert.equal(byRound([football('a'),football('b',true,{round:'第12轮'})]).length,2);
});
import {scopedRecords} from '../public/statistics-scope.mjs';
import {footballPaper,footballPaperTotals} from '../public/prediction-stats-core.mjs';
test('start at this round including already finished games; retain future seasons',()=>{
 const old=football('old',true,{round:'第10轮'}),current=football('now'),future=football('future',true,{season:'2027/28',round:'第1轮'});
 assert.deepEqual(scopedRecords([old,current,future,football('unknown',true,{round:''})],'football').map(r=>r.eventId),['now','future']);
 assert.equal(scopedRecords([{...race,day:'2026-11-18'},race],'racing').length,1);
});
test('new finals update a partial round without waiting for round closure',()=>{
 const before=[football('a'),football('b',false,{status:'pending'})],after=[football('a'),football('b',false)];
 assert.equal(footballTotals(before).settled,1);assert.equal(footballTotals(after).settled,2);
 assert.equal(footballTotals(after).exact,1);
});
test('football 100 handicap and 50 exact score use saved prices and quarter settlement',()=>{
 const r=football('a',true,{asianSide:'H',asianPrice:1.9,scorePrice:8.5,asianResult:'赢半'});
 const t=footballPaperTotals([r]);assert.equal(t.planned,150);assert.equal(t.stake,150);assert.equal(t.returns,570);assert.equal(t.net,420);
 assert.equal(footballPaper({...r,asianResult:'输半'})[0].returned,50);
 assert.equal(footballPaper({...r,asianResult:'走盘'})[0].returned,100);
 assert.equal(footballPaperTotals([{...r,status:'void'}]).refunds,150);
});
test('missing pregame prices cannot be used to fabricate money or losses',()=>{
 const r=football('x',false,{asianSide:'pass',scorePrice:null});
 const t=footballPaperTotals([r]);assert.equal(t.planned,50);assert.equal(t.stake,0);assert.equal(t.net,0);assert.equal(t.pending,50);assert.equal(t.unpriced,1);
});
test('win coverage is per race while place and pair hit rates count every valid selection',()=>{
 const a=structuredClone(race),b=structuredClone(race);b.raceNo=2;
 a.pools.find(p=>p.type==='PLA').tickets=[ticket('1','hit',11),ticket('2','miss',0),ticket('3','miss',0)];
 b.pools.find(p=>p.type==='PLA').tickets=[ticket('1','hit',11),ticket('2','hit',11),ticket('3','miss',0)];
 const one=poolAccuracy(poolTotals([a],'PLA'),'PLA'),two=poolAccuracy(poolTotals([b],'PLA'),'PLA'),all=poolTotals([a,b],'PLA');
 assert.deepEqual(one,{hits:1,total:3,unit:'匹',label:'位置逐匹命中率'});assert.equal((one.hits/one.total*100).toFixed(1),'33.3');assert.equal((two.hits/two.total*100).toFixed(1),'66.7');
 assert.deepEqual(poolAccuracy(all,'PLA'),{hits:3,total:6,unit:'匹',label:'位置逐匹命中率'});assert.equal(all.stake,600);assert.ok(Math.abs(all.returns-330)<1e-8);assert.ok(Math.abs(all.net+270)<1e-8);
 assert.deepEqual(poolAccuracy(poolTotals([a,b],'WIN'),'WIN'),{hits:2,total:2,unit:'场',label:'独赢场次命中率'});
 assert.equal(poolAccuracy(poolTotals([a,b],'QPL'),'QPL').total,6);
 a.pools.find(p=>p.type==='PLA').tickets[2]=ticket('3','refund',10);
 assert.equal(poolAccuracy(poolTotals([a],'PLA'),'PLA').total,2);
 assert.equal(poolAccuracy(poolTotals([{...a,status:'excluded'}],'PLA'),'PLA').total,0);
});
