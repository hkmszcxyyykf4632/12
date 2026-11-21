import test from 'node:test';
import assert from 'node:assert/strict';
import {dailyRows} from '../public/daily-core.mjs';

const kickoff='2026-11-21T01:00:00Z';
const fixture={id:'espn:123',season:'2026/27',competition:'德甲',date:'2026-11-21',kickoff,home:'Home',away:'Away',started:true,finished:true,homeGoals:1,awayGoals:1,result:'D',statusText:'FT'};
const feed=(match=fixture,updatedAt='2026-11-21T04:00:00Z')=>({league:'bundesliga',data:{teams:[{name:'Home',cn:'主队'},{name:'Away',cn:'客队'}],matches:[]},live:{updatedAt,matches:[match]}});
const global=(overrides={})=>({id:'123',league:'bundesliga',competitionId:'720',competition:'德甲',kickoff,day:'2026-11-21',state:'scheduled',status:'未开赛',started:false,finished:false,updatedAt:'2026-11-20T04:00:00Z',teams:{home:{id:'1',name:'Home',label:'主队',goals:null},away:{id:'2',name:'Away',label:'客队',goals:null}},...overrides});
const options={date:'2026-11-21',now:Date.parse('2026-11-21T04:01:00Z')};

test('newer league final replaces stale global scheduled score without duplicate cards',()=>{
  const [row,...rest]=dailyRows({matches:[global()]},[feed()],options);
  assert.equal(rest.length,0);
  assert.equal(row.state,'finished');
  assert.equal(row.status,'已完场');
  assert.deepEqual([row.homeGoals,row.awayGoals],[1,1]);
  assert.equal(row.teams.home.goals,1);
  assert.equal(row.dailyId,'123');
  assert.equal(row.updatedAt,'2026-11-21T04:00:00Z');
  assert.equal(row.delayed,false);
});

test('a newer global correction keeps its result instead of an older league score',()=>{
  const fresh=global({updatedAt:'2026-11-21T04:01:00Z',state:'finished',status:'已完场',started:true,finished:true});
  fresh.teams.home.goals=2;fresh.teams.away.goals=1;
  const [row]=dailyRows({matches:[fresh]},[feed()],options);
  assert.deepEqual([row.homeGoals,row.awayGoals],[2,1]);
  assert.equal(row.updatedAt,fresh.updatedAt);
});

test('selected date does not replace the real clock for feed freshness',()=>{
  const [row]=dailyRows({matches:[]},[feed(fixture,'2026-11-21T14:00:00Z')],{date:'2026-11-21',now:Date.parse('2026-11-21T14:10:00Z')});
  assert.equal(row.delayed,true);
});

test('a historical date still selects local fixtures independently of real now',()=>{
  const [row]=dailyRows({matches:[]},[feed()],{date:'2026-11-21',now:Date.parse('2026-12-15T04:00:00Z')});
  assert.equal(row.id,fixture.id);
  assert.equal(row.delayed,true);
});
