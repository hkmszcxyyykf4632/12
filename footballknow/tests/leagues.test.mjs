import test from 'node:test';
import assert from 'node:assert/strict';
import {leagueFromSearch} from '../public/league.mjs';
import {validLive} from '../public/live-core.mjs';

test('league links preserve selected league and restrict snapshot directories',()=>{
  const selected=leagueFromSearch('?league=laliga');
  assert.equal(selected.folder,'laliga/');
  assert.equal(leagueFromSearch('?league=../state').id,'epl');
  const url=new URL('#/team/4','https://footballknow.art/?league=laliga#/teams');
  assert.equal(url.search,'?league=laliga');
  assert.equal(new URL('./#/teams',url).search,'');
});

test('live snapshot must belong to the selected league',()=>{
  const teams=Array.from({length:20},(_,i)=>({name:'T'+i}));
  const matches=teams.flatMap(home=>teams.filter(away=>away!==home).map(away=>({
    id:home.name+'|'+away.name,home:home.name,away:away.name,season:'2026/27',
    competition:'西甲',started:false,finished:false,result:null
  })));
  const live={version:1,season:'2026/27',updatedAt:new Date().toISOString(),matches};
  assert.equal(validLive(live,{season:'2026/27',competition:'西甲',teams}),true);
  assert.equal(validLive(live,{season:'2026/27',competition:'英超',teams}),false);
  matches.pop();
  assert.equal(validLive(live,{season:'2026/27',competition:'西甲',teams}),false);
});
