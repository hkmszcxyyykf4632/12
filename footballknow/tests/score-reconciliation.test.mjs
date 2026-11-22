import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcileDailyMatches} from '../public/score-reconciliation.mjs';
import {mergeMatches} from '../public/live-core.mjs';
const kickoff='2026-11-21T12:30:00Z';
const m={id:'local',season:'2026/27',competition:'英超',home:'Man City',away:'Fulham',kickoff,date:'2026-11-21',started:false,finished:false,homeGoals:null,awayGoals:null};
const archive={season:'2026/27',teams:[{name:'Man City',cn:'曼城'},{name:'Fulham',cn:'富勒姆'}],matches:[m]};
const g={id:'123',league:'epl',season:2026,kickoff,updatedAt:'2026-11-21T14:30:00Z',started:true,finished:true,state:'finished',status:'已完场',scoreScope:'90分钟含补时',teams:{home:{id:'382',name:'Manchester City',label:'曼城',goals:1},away:{id:'370',name:'Fulham',label:'富勒姆',goals:1}}};
const merge=(match=m,row=g)=>reconcileDailyMatches([match],archive,{matches:[row]},'epl','2026-11-21T15:00:00Z')[0];
test('verified daily final updates a pending club fixture despite a newer provisional feed',()=>{
 const result=merge();assert.equal(result.finished,true);assert.equal(result.result,'D');assert.equal(result.id,'local');assert.equal(result.dailyId,'123');assert.equal(result.scoreUpdatedAt,g.updatedAt);
});
test('kickoff, competition, season and both opponents must agree',()=>{
 for(const row of [{...g,kickoff:'2026-11-22T12:30:00Z'},{...g,league:'ucl'},{...g,season:2025},{...g,teams:{home:g.teams.away,away:g.teams.home}}])assert.equal(merge(m,row).finished,false);
 assert.equal(reconcileDailyMatches([m],archive,{matches:[g,g]},'epl')[0].finished,false);
});
test('unconfirmed, extra-time or missing scores never become settled finals',()=>{
 for(const row of [{...g,scoreScope:'含加时'},{...g,teams:{...g.teams,home:{...g.teams.home,goals:null}}}])assert.equal(merge(m,row).finished,false);
});
test('a final survives stale scheduled data and newer finals can correct scores',()=>{
 const final=merge();assert.equal(merge(final,{...g,started:false,finished:false,state:'scheduled',updatedAt:'2026-11-22T12:00:00Z'}).finished,true);
 const corrected=merge(final,{...g,updatedAt:'2026-11-21T16:00:00Z',teams:{...g.teams,home:{...g.teams.home,goals:2}}});assert.equal(corrected.result,'H');
 const rows=mergeMatches({...archive,matches:[final]},{season:archive.season,updatedAt:'2026-11-22T12:00:00Z',matches:[m]});assert.equal(rows[0].finished,true);
});
