import test from 'node:test';
import assert from 'node:assert/strict';
import {settleLine,matchSettlement,selectQuote,quotesForMatch,filterVenue,settlementSummary} from '../public/settlement.mjs';
const quote=(market,line,phase='closing')=>({market,line,phase,provider:'市场平均',kind:'aggregate',prices:market==='asian-handicap'?{H:1.9,A:1.9}:{O:1.9,U:1.9}});
const match={id:'one',date:'2026-01-01',home:'A',away:'B',finished:true,homeGoals:1,awayGoals:0};
test('quarter lines split negative and positive handicaps correctly',()=>{
  assert.equal(settleLine(1,-0.75),0.5);assert.equal(settleLine(1,-1.25),-0.5);
  assert.equal(settleLine(0,0.25),0.5);assert.equal(settleLine(0,-0.25),-0.5);
  assert.equal(settleLine(2,-2),0);assert.equal(settleLine(1,-0.5),1);
  assert.equal(settleLine(0,-0.2),null);assert.equal(settleLine(0,null),null);
});
test('home and away perspectives invert the result and the line',()=>{
  const rows=[quote('asian-handicap',-0.75),quote('total-goals',1.25)];
  const a=matchSettlement(match,'A',rows),b=matchSettlement(match,'B',rows);
  assert.equal(a.handicap.result,0.5);assert.equal(b.handicap.result,-0.5);assert.equal(b.handicap.line,0.75);
  assert.equal(a.total.over,-0.5);assert.equal(a.total.under,0.5);
});
test('all quarter total outcomes and null unfinished scores',()=>{
  assert.equal(settleLine(3,-2.75),0.5);assert.equal(settleLine(2,-2.25),-0.5);
  for(const bad of [{finished:false},{homeGoals:null},{provisional:true},{scoreScope:'含加时赛'}])assert.equal(matchSettlement({...match,...bad},'A',[quote('asian-handicap',0)]).handicap,null);
});
test('closing beats opening and a live-only quote is not a prematch settlement line',()=>{
  assert.equal(selectQuote([quote('asian-handicap',0,'opening'),quote('asian-handicap',-0.5)],'asian-handicap').line,-0.5);
  assert.equal(selectQuote([quote('asian-handicap',0,'latest')],'asian-handicap'),null);
  assert.equal(selectQuote([{...quote('asian-handicap',0),inPlay:true}],'asian-handicap'),null);
});
test('aliases, home-away filters and denominator exclude missing lines',()=>{
  const snapshot={matches:{old:[quote('asian-handicap',-0.75),quote('total-goals',2.5)]}};
  const a={...match,aliases:['old']},b={...match,id:'two',home:'B',away:'A'};
  assert.equal(quotesForMatch(snapshot,a).length,2);assert.equal(filterVenue([a,b],'A','home').length,1);assert.equal(filterVenue([a,b],'A','away')[0].id,'two');
  const s=settlementSummary([a,b],'A',snapshot);assert.equal(s.finished,2);assert.equal(s.handicap,1);assert.equal(s.halfWins,1);assert.equal(s.under,1);
});
