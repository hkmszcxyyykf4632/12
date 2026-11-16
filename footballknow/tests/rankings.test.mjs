import test from 'node:test';
import assert from 'node:assert/strict';
import {validTable,validLeaders,metricRows,loadFollowing,headToHead} from '../public/rankings-core.mjs';

test('tables reject cross-competition data and inconsistent counts',()=>{
 const data={season:'2026/27',teams:[{id:1}]};
 const value={version:1,league:'epl',season:data.season,updatedAt:'2026-11-16T00:00:00Z',entries:[{teamId:1,rank:1,played:1,wins:1,draws:0,losses:0,goalsFor:2,goalsAgainst:0,goalDifference:2,points:3}]};
 assert.ok(validTable(value,data,'epl'));assert.equal(validTable(value,data,'ucl'),false);
 value.entries[0].played=2;assert.equal(validTable(value,data,'epl'),false);
});
test('team metrics do not mix an older discipline sample into goals per game',()=>{
 const table={entries:[{teamId:1,cn:'A',played:10,goalsFor:20},{teamId:2,cn:'B',played:8,goalsFor:16}]};
 const leaders={discipline:[{teamId:1,played:9,yellowCards:10}]};
 const rows=metricRows(table,leaders,'goalsPerGame');assert.equal(rows[0].value,2);assert.equal(rows[1].rank,1);
 assert.equal(metricRows(table,leaders,'yellowCards')[0].played,9);
});
test('follows stay within the selected league and h2h excludes future games',()=>{
 const storage={getItem:key=>key.endsWith('ucl')?'[1,999]':'[2]'};
 assert.deepEqual(loadFollowing(storage,'ucl',[{id:1}]),[1]);
 assert.deepEqual(loadFollowing(storage,'epl',[{id:1}]),[]);
 const games=[{id:1,home:'A',away:'B',date:'2026-01-01',finished:true},{id:2,home:'B',away:'A',date:'2026-12-01',finished:true}];
 assert.deepEqual(headToHead(games,'A','B','2026-11-01').map(m=>m.id),[1]);
});
