import test from 'node:test';
import assert from 'node:assert/strict';
import {kellyRows,priceMovement,matchDetailMatches} from '../public/insights.mjs';

test('Kelly comparisons use distinct providers within the same price phase', () => {
  const quote=(provider,phase,H=2)=>({provider,phase,H,D:4,A:4});
  assert.deepEqual(kellyRows([quote('A','赛前'),quote('A','收盘')]),[]);
  assert.deepEqual(kellyRows([quote('A','赛前'),quote('A','赛前',1.8)]),[]);
  const rows=kellyRows([quote('A','赛前'),quote('A','收盘',1.8),quote('B','赛前')]);
  assert.deepEqual(rows.map(r=>r.provider),['A · 赛前','B · 赛前']);
  assert.ok(rows.every(r=>r.H===1&&r.D===1&&r.A===1));
});

test('price movements do not mix opening, closing or different feeds', () => {
  const rows=[{provider:'A',phase:'收盘',via:'Feed',H:1.9},{provider:'A',phase:'赛前',via:'Feed',H:2.1},
    {provider:'A',phase:'收盘',via:'Feed',H:1.8},{provider:'A',phase:'收盘',via:'Other',H:2}];
  assert.deepEqual(priceMovement(rows).map(m=>[m.opening.H,m.latest.H,m.points.length]),[[1.9,1.8,2],[2.1,2.1,1],[2,2,1]]);
});

test('a match page rejects another fixture, league or lineup', () => {
  const match={id:'m1',home:'Man Utd',away:'Aston Villa'};
  const detail={matchId:'m1',league:'epl',status:'available',home:match.home,away:match.away,
    lineups:{home:{name:match.home},away:{name:match.away}}};
  assert.equal(matchDetailMatches(detail,match,'epl'),true);
  assert.equal(matchDetailMatches({...detail,matchId:'m2'},match,'epl'),false);
  assert.equal(matchDetailMatches({...detail,league:'laliga'},match,'epl'),false);
  assert.equal(matchDetailMatches({...detail,lineups:{home:{name:'Chelsea'},away:{name:'Hull'}}},match,'epl'),false);
  assert.equal(matchDetailMatches({matchId:'m1',league:'epl',status:'unavailable'},match,'epl'),true);
});
