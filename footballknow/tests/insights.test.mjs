import test from 'node:test';
import assert from 'node:assert/strict';
import {impliedProbabilities,seasonStats,leadMatch,countdownText,comparisonRows,describeJob,statusSummary} from '../public/insights.mjs';

test('odds convert to margin-free probabilities and reject incomplete quotes', () => {
  const p=impliedProbabilities({H:2,D:4,A:4});
  assert.deepEqual([p.H,p.D,p.A,p.margin],[0.5,0.25,0.25,0]);
  const market=impliedProbabilities({H:1.9,D:3.5,A:4.2});
  assert.ok(Math.abs(market.H+market.D+market.A-1)<1e-12&&market.margin>0.04&&market.margin<0.06);
  assert.equal(impliedProbabilities({H:2,D:1,A:4}),null);
  assert.equal(impliedProbabilities({H:2,D:3}),null);
  assert.equal(impliedProbabilities(undefined),null);
});

test('season figures count only confirmed results of the chosen competition', () => {
  const now=Date.parse('2026-11-16T12:00:00');
  const row=(extra)=>({competition:'英超',season:'2026/27',finished:false,started:false,kickoff:'2026-12-01T12:00:00',...extra});
  const matches=[row({finished:true,started:true,homeGoals:2,awayGoals:1,result:'H'}),row({finished:true,started:true,homeGoals:0,awayGoals:0,result:'D'}),
    row({started:true,homeGoals:1,awayGoals:0,kickoff:'2026-11-16T11:30:00'}),row({kickoff:'2026-11-16T20:00:00'}),row({}),
    row({competition:'英冠',finished:true,homeGoals:5,awayGoals:5,result:'D'}),row({season:'2025/26',finished:true,homeGoals:5,awayGoals:0,result:'H'})];
  const s=seasonStats(matches,'英超','2026/27',now);
  assert.deepEqual([s.total,s.played,s.goals,s.average,s.home,s.draw,s.away,s.live,s.today],[5,2,3,1.5,1,1,0,1,2]);
  assert.equal(leadMatch(matches,'英超','2026/27',now).homeGoals,1,'a match in play leads');
  assert.equal(leadMatch(matches.filter(m=>!m.started||m.finished),'英超','2026/27',now).kickoff,'2026-11-16T20:00:00');
  assert.equal(leadMatch([], '英超','2026/27',now),null);
});

test('countdown wording', () => {
  const now=Date.parse('2026-11-16T12:00:00Z');
  assert.equal(countdownText('2026-11-18T15:00:00Z',now),'2 天 3 小时');
  assert.equal(countdownText('2026-11-16T14:05:00Z',now),'2 小时 5 分钟');
  assert.equal(countdownText('2026-11-16T12:00:20Z',now),'1 分钟');
  assert.equal(countdownText('2026-11-16T11:00:00Z',now),'');
});

test('comparison marks the better side per metric', () => {
  const a={rank:1,points:27,played:10,wins:9,draws:0,losses:1,goalsFor:15,goalsAgainst:5,goalDifference:10,cleanSheets:7};
  const b={rank:4,points:20,played:10,wins:6,draws:2,losses:2,goalsFor:20,goalsAgainst:9,goalDifference:11};
  const rows=Object.fromEntries(comparisonRows(a,b).map(r=>[r.label,r]));
  assert.equal(rows['排名'].lead,'left');assert.equal(rows['进球'].lead,'right');assert.equal(rows['失球'].lead,'left');
  assert.equal(rows['已赛'].lead,'');assert.equal(rows['零封'],undefined,'a figure missing on one side is not compared');
  assert.equal(rows['场均进球'].right,2);assert.equal(rows['进球'].leftShare,0.75);
});

test('job names and overall sync health', () => {
  assert.deepEqual(describeJob('live'),{league:'英超',label:'比分与赛程',group:'比分与赛程'});
  assert.deepEqual(describeJob('ucl-leaders','rankings'),{league:'欧冠',label:'射手、助攻与纪律榜',group:'积分与球员榜'});
  assert.equal(describeJob('laliga-live').league,'西甲');
  assert.equal(describeJob('odds-official-checks').league,'全部赛事');
  const now=Date.parse('2026-11-16T12:00:00Z'),heartbeat='2026-11-16T11:59:30Z';
  const jobs={a:{ok:true},b:{ok:false},c:{ok:null}};
  assert.equal(statusSummary({running:true,heartbeat,jobs},now).level,'warn');
  assert.equal(statusSummary({running:true,heartbeat,jobs:{a:{ok:true}}},now).text,'全部 1 项同步正常');
  assert.equal(statusSummary({running:true,heartbeat:'2026-11-16T11:00:00Z',jobs},now).level,'down');
  assert.equal(statusSummary(undefined,now).level,'down');
});
