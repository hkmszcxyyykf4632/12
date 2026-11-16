import test from 'node:test';
import assert from 'node:assert/strict';
import {mergeMatches,freshness,validLive} from '../public/live-core.mjs';

test('postponed fixtures keep old record aliases and historical odds without crossing seasons',()=>{
  const archived={id:'2026-10-01|A|B',season:'2026/27',competition:'英超',home:'A',away:'B',date:'2026-10-01',odds:[{H:2.1,D:3.2,A:4}],source:'https://example.com/odds'};
  const older={...archived,id:'2025-10-01|A|B',season:'2025/26',date:'2025-10-01'};
  const archive={season:'2026/27',matches:[archived,older]};
  const row={...archived,id:'2026-11-01|A|B',date:'2026-11-01',source:'https://example.com/live',odds:undefined,finished:true,result:'H'};
  const first=mergeMatches(archive,{season:'2026/27',matches:[row]});
  const latest=first.find(m=>m.season==='2026/27');
  assert.deepEqual(latest.odds,archived.odds);
  assert.equal(latest.oddsSource,archived.source);
  assert.ok(latest.aliases.includes(archived.id));
  assert.ok(!latest.aliases.includes(older.id));
  const second=mergeMatches(archive,{season:'2026/27',matches:[{...row,id:'2026-11-02|A|B',date:'2026-11-02'}]},first);
  assert.ok(second[0].aliases.includes(row.id));
  assert.equal(second.length,2);
});

test('unavailable or old live snapshots are visibly stale',()=>{
  const now=Date.parse('2026-11-15T12:00:00Z');
  assert.equal(freshness(null,false,now).stale,true);
  assert.equal(freshness({updatedAt:'2026-11-15T11:56:00Z'},false,now).stale,true);
  assert.equal(freshness({updatedAt:'2026-11-15T11:59:30Z'},false,now).stale,false);
  assert.equal(freshness({updatedAt:'2026-11-15T11:59:30Z'},true,now).failed,true);
  assert.equal(validLive({version:1,season:'2026/27',updatedAt:new Date(now).toISOString(),matches:[]},{season:'2026/27',teams:[]}),false);
});
