import test from 'node:test';
import assert from 'node:assert/strict';
import {chartPoints,rateText,financialAmount} from '../public/finance-core.mjs';
import {validMarket,manualMarket,marketComparisons,movementSummary} from '../public/markets-core.mjs';
import {orderedEvents,opponentRecords,transferPattern} from '../public/research-core.mjs';
import {statusSummary} from '../public/insights.mjs';
import {readFile} from 'node:fs/promises';
import {competitionFeeds,combinedFixtures,fixtureTime} from '../public/competition-feed.mjs';

test('combined feed accepts the original EPL archive and all four named competitions',async()=>{
  const originalFetch=globalThis.fetch;
  globalThis.fetch=async url=>({ok:true,json:async()=>JSON.parse(await readFile(new URL('../public/'+String(url).replace(/^\.\//,''),import.meta.url),'utf8'))});
  try{
    const feeds=await competitionFeeds();
    assert.equal(feeds.length,5);
    assert.deepEqual(feeds.filter(f=>f.failed).map(f=>f.league),[]);
    const kickoff=feeds.find(f=>f.league==='epl').live.matches.find(m=>m.kickoff)?.kickoff;
    const rows=combinedFixtures(feeds,{state:'all',now:Date.parse(kickoff)});
    assert.ok(rows.some(m=>m.league==='epl'));
    assert.ok(rows.every((m,i)=>!i||fixtureTime(rows[i-1])<=fixtureTime(m)));
    assert.ok(rows.every(m=>Math.abs(fixtureTime(m)-Date.parse(kickoff))<=7*86400000));
  }finally{globalThis.fetch=originalFetch;}
});

test('financial displays distinguish absent values, zero and reporting units',()=>{
  assert.equal(financialAmount({amount:1.98909e11}),'1,989.09');
  assert.equal(financialAmount({amount:0}),'0.00');
  assert.equal(financialAmount({amount:null}),'—');
  assert.equal(rateText({evaluated:0,successRate:null}),'等待到期验证');
  assert.equal(rateText({evaluated:10,successRate:.4}),'40.0%');
  assert.equal(chartPoints([{date:'2026-01-01',close:null}]),null);
});

test('opening and closing comparison never mixes providers or treats early CSV odds as opening',()=>{
  const q={market:'asian-handicap',provider:'A',via:'CSV',line:-.5,prices:{H:1.8,A:2.1}};
  const rows=[{...q,phase:'preclosing'},{...q,phase:'closing',prices:{H:1.7,A:2.2}},{...q,provider:'B',phase:'latest'}];
  assert.equal(marketComparisons(rows).length,1);
  assert.match(movementSummary(rows)[0],/赛前早期报价/);
  assert.doesNotMatch(movementSummary(rows)[0],/开始赔率/);
  const changed=[rows[0],{...rows[1],line:-1}];
  assert.equal(marketComparisons(changed)[0].sameLine,false);
  assert.match(movementSummary(changed)[0],/盘口条件已变/);
});

test('manual correct-score records require a real score key and past quote time',()=>{
  const quote={market:'correct-score',provider:'Example',phase:'opening',quotedAt:'2026-01-01T00:00:00Z',prices:{'2:1':8.5}};
  assert.equal(manualMarket(quote).manual,true);
  assert.equal(validMarket({...quote,prices:{unknown:5}}),false);
  assert.throws(()=>manualMarket({...quote,quotedAt:'2099-01-01'}),/时间/);
  assert.equal(validMarket({market:'total-goals',provider:'Example',phase:'latest',line:2.6,prices:{O:2,U:2}}),false);
});

test('event order preserves periods and stoppage time',()=>{
  const events=[{clock:'46',period:2},{clock:'45+9',period:1},{clock:'45+2',period:1},{clock:'90+1',period:2}];
  assert.deepEqual(orderedEvents(events).map(e=>e.clock),['45+2','45+9','46','90+1']);
});

test('rivals require repeated confirmed games and transfer range belongs to the club',()=>{
  const make=(date,away,score)=>({home:'A',away,date,finished:true,season:'2026/27',competition:'Test',homeGoals:score,awayGoals:0});
  const matches=[make('2026-01-01','B',2),make('2026-02-01','B',1),make('2026-03-01','B',3),make('2026-01-02','C',9)];
  assert.equal(opponentRecords([...matches,matches[0]],'A').favourable[0].played,3);
  assert.equal(opponentRecords(matches,'A').favourable.length,1);
  const transfers=[{date:'2026-01-01',player:'P',fromTeam:'X',toTeam:'A',type:'自由转会'},{date:'2020-01-01',player:'Q',fromTeam:'Z',toTeam:'X',type:'转会'}];
  assert.equal(transferPattern(transfers,'A').first,'2026-01-01');
});

test('deliberately paused synchronization is explicitly labelled',()=>{
  const snapshot={running:true,paused:true,heartbeat:new Date().toISOString(),jobs:{one:{ok:true}}};
  assert.match(statusSummary(snapshot).text,/管理员已暂停/);
  assert.equal(statusSummary(snapshot).alive,true);
});
