import test from 'node:test';
import assert from 'node:assert/strict';
import {handicapSeries} from '../public/handicap-trend.mjs';

const match=(id,date,home='A',away='B')=>({id,date,home,away,finished:true,season:'2026/27',competition:'英超',homeGoals:1,awayGoals:0});
const q=line=>({market:'asian-handicap',line,phase:'closing',provider:'市场平均',prices:{H:1.9,A:1.9}});
test('trend is chronological, preserves missing gaps and excludes duplicate and incomplete fixtures',()=>{
  const rows=[match('c','2026-03-01'),match('a','2026-01-01'),match('b','2026-02-01'),match('a','2026-01-01'),{...match('d','2026-04-01'),finished:false}];
  const r=handicapSeries(rows,'A',{matches:{a:[q(-.75)],c:[q(-1.25)]}});
  assert.deepEqual(r.map(x=>x.match.id),['a','b','c']);assert.deepEqual(r.map(x=>x.result),[.5,null,-.5]);
});
test('away chart reverses home handicap and half outcomes',()=>{
  const r=handicapSeries([match('a','2026-01-01','B','A'),match('b','2026-01-02')],'A',{matches:{a:[q(-.75)]}},{venue:'away'});
  assert.equal(r.length,1);assert.equal(r[0].line,.75);assert.equal(r[0].result,-.5);
});
test('scope limit counts finished fixtures, including missing prices, without promoting stale results',()=>{
  const rows=[match('a','2026-01-01'),{...match('b','2026-02-01'),season:'2025/26'},match('c','2026-03-01')];
  const r=handicapSeries(rows,'A',{matches:{}},{season:'2026/27',competition:'英超',limit:1});
  assert.equal(r[0].match.id,'c');assert.equal(r[0].result,null);
});
