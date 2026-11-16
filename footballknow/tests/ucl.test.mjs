import test from 'node:test';
import assert from 'node:assert/strict';
import {validLive,mergeMatches} from '../public/live-core.mjs';
import {leagueFromSearch} from '../public/league.mjs';

test('UCL has 36 clubs and a complete phase plus future knockout fixtures',()=>{
  assert.equal(leagueFromSearch('?league=ucl').teamCount,36);
  const teams=Array.from({length:36},(_,i)=>({name:String(i)}));
  const matches=teams.flatMap((t,i)=>Array.from({length:4},(_,j)=>({id:`espn:${i*4+j}`,fixtureId:i*4+j,
    season:'2026/27',competition:'欧冠',home:t.name,away:String((i+j+1)%36),phase:'联赛阶段',
    started:false,finished:false,result:null})));
  const archive={league:'ucl',competition:'欧冠',season:'2026/27',teams,matches:[]};
  const live={version:1,season:'2026/27',updatedAt:new Date().toISOString(),matches};
  assert.equal(validLive(live,archive),true);
  matches.push({...matches[0],id:'espn:900',fixtureId:900,phase:'十六强'});
  assert.equal(validLive(live,archive),true);
  matches.shift();assert.equal(validLive(live,archive),false);
});

test('repeated opponents in league phase and knockouts remain separate',()=>{
  const a={id:'espn:1',fixtureId:1,date:'2026-11-01',season:'2026/27',competition:'欧冠',home:'A',away:'B',finished:true,homeGoals:2,awayGoals:0,odds:[]};
  const b={...a,id:'espn:2',fixtureId:2,date:'2027-03-01',finished:false,homeGoals:null,awayGoals:null};
  const archive={league:'ucl',season:'2026/27',matches:[a,b]};
  const merged=mergeMatches(archive,{season:'2026/27',matches:[{...b,homeGoals:1,awayGoals:1,finished:true}]});
  assert.equal(merged.length,2);
  assert.equal(merged.find(m=>m.id==='espn:1').homeGoals,2);
  assert.equal(merged.find(m=>m.id==='espn:2').homeGoals,1);
});
