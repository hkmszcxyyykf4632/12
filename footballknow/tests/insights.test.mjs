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

import {teamSeason,ageOn,boardRows,kellyRows,priceMovement,matchAlerts,qualityReport,radarPoints,eventSentence} from '../public/insights.mjs';

test('team season record splits home and away', () => {
  const m=(home,away,hg,ag,extra={})=>({home,away,homeGoals:hg,awayGoals:ag,finished:true,competition:'英超',season:'2026/27',...extra});
  const r=teamSeason([m('A','B',2,0),m('C','A',1,1),m('A','D',0,3),m('A','E',5,0,{season:'2025/26'}),m('A','F',null,null),m('B','C',1,0)],'A','英超','2026/27');
  assert.deepEqual(r.all,{played:3,wins:1,draws:1,losses:1,goalsFor:3,goalsAgainst:4,cleanSheets:1,failedToScore:1});
  assert.deepEqual([r.home.played,r.home.wins,r.home.losses,r.away.played,r.away.draws],[2,1,1,1,1]);
});

test('age, ranked boards and radar geometry', () => {
  const now=Date.parse('2026-11-17T00:00:00');
  assert.equal(ageOn('2000-11-17',now),26);assert.equal(ageOn('2000-11-18',now),25);assert.equal(ageOn('',now),null);assert.equal(ageOn('1900-01-01',now),null);
  const rows=boardRows([{n:'a',v:5},{n:'b',v:7},{n:'c',v:5},{n:'d',v:0},{n:'e',v:null},{n:'f',v:'2.5'}],r=>r.v,{limit:4});
  assert.deepEqual(rows.map(r=>[r.row.n,r.rank]),[['b',1],['a',2],['c',2],['f',4]]);
  assert.equal(radarPoints([1,0.5,0,1],10),'10.0,0.0 15.0,10.0 10.0,10.0 0.0,10.0');
});

test('kelly index needs two bookmakers and price movement keeps opening and latest', () => {
  assert.deepEqual(kellyRows([{provider:'A',H:2,D:4,A:4}]),[]);
  const rows=kellyRows([{provider:'A',H:2,D:4,A:4},{provider:'B',H:2,D:4,A:4},{provider:'avg',kind:'aggregate',H:9,D:9,A:9}]);
  assert.equal(rows.length,2);assert.deepEqual([rows[0].H,rows[0].D,rows[0].A],[1,1,1]);
  const moves=priceMovement([{provider:'A',at:'1',H:2},{provider:'B',at:'1',H:3},{provider:'A',at:'2',H:1.8}]);
  assert.deepEqual(moves.map(m=>[m.provider,m.opening.H,m.latest.H,m.points.length]),[['A',2,1.8,2],['B',3,3,1]]);
});

test('alerts fire for followed clubs only', () => {
  const m=(id,extra)=>({id,home:'A',away:'B',started:false,finished:false,homeGoals:null,awayGoals:null,...extra});
  const kinds=(a,b,clubs=['A'])=>matchAlerts([a],[b],clubs).map(x=>x.kind);
  assert.deepEqual(kinds(m('1'),m('1',{started:true,homeGoals:0,awayGoals:0})),['start']);
  const live=m('1',{started:true,homeGoals:0,awayGoals:0});
  const goal=matchAlerts([live],[m('1',{started:true,homeGoals:0,awayGoals:1})],['A'],n=>n+'队')[0];
  assert.deepEqual([goal.kind,goal.title,goal.text],['goal','B队进球','A队 0 : 1 B队']);
  assert.deepEqual(kinds(live,m('1',{started:true,finished:true,homeGoals:0,awayGoals:0})),['final']);
  assert.deepEqual(kinds(live,m('1',{started:true,homeGoals:1,awayGoals:0}),['Z']),[]);
  assert.deepEqual(kinds(live,live),[]);assert.deepEqual(matchAlerts(null,[live],['A']),[]);
});

test('quality report counts coverage and flags suspicious records', () => {
  const now=Date.parse('2026-11-17T12:00:00Z');
  const base={competition:'英超',season:'2026/27',started:false,finished:false,kickoff:'2026-12-01T12:00:00Z'};
  const data={season:'2026/27',players:[{code:1,birth_date:'2000-01-01',country:'X',squad_number:9,minutes:10},{code:2,birth_date:'',country:'',squad_number:null,minutes:null}],
    matches:[{...base,id:'ok',date:'2026-09-01',home:'A',away:'B',finished:true,started:true,homeGoals:1,awayGoals:0,result:'H',odds:[{}]},
      {...base,id:'noscore',date:'2026-09-02',home:'A',away:'C',finished:true,started:true,homeGoals:null,awayGoals:null},
      {...base,id:'wrong',date:'2026-09-03',home:'B',away:'C',finished:true,started:true,homeGoals:0,awayGoals:2,result:'H'},
      {...base,id:'stuck',date:'2026-11-17',home:'C',away:'A',started:true,kickoff:'2026-11-17T05:00:00Z',homeGoals:0,awayGoals:0},
      {...base,id:'late',date:'2026-11-17',home:'B',away:'A',kickoff:'2026-11-17T08:00:00Z'},{...base,id:'future',date:'2026-12-01',home:'A',away:'B'}]};
  const report=qualityReport({data,names:{names:{1:{}}},facts:{coveredMatches:2,matches:{ok:{halfTime:[1,0]}}},competition:'英超',now});
  const field=label=>report.fields.find(f=>f.label.startsWith(label));
  assert.deepEqual([field('球员中文译名').filled,field('球员出生日期').filled,field('已完赛比赛的比分').filled,field('已完赛比赛的比分').total,field('可核对的半场比分').filled],[1,1,2,3,1]);
  assert.deepEqual(report.anomalies.map(a=>a.matchId),['noscore','wrong','stuck','late']);
});

test('event sentences are composed from structured fields', () => {
  assert.equal(eventSentence({type:'goal',players:[{name:'甲'},{name:'乙'}]}),'甲破门，乙助攻');
  assert.equal(eventSentence({type:'goal',players:[{name:'甲'}]}),'甲破门');
  assert.equal(eventSentence({type:'substitution',players:[{name:'甲'},{name:'乙'}]}),'甲上场，换下乙');
  assert.equal(eventSentence({type:'own-goal',players:[]}),'球员打入乌龙球');
  assert.equal(eventSentence({type:'unknown',label:'其他',players:[]}),'其他');
});
