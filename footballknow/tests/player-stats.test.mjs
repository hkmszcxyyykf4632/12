import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
const dom=new JSDOM('<main id="main"></main>',{url:'http://localhost/?league=laliga'});
Object.assign(globalThis,{document:dom.window.document,window:dom.window,location:dom.window.location,localStorage:dom.window.localStorage});
const {playerStats,factRow}=await import('../public/player-stats.mjs');
test('a player profile opens before match facts have been published',()=>{
  const player={id:222375,code:'espn:222375',web_name:'Simón',minutes:null,goals_scored:null};
  assert.equal(factRow(player),null);
  const stats=playerStats(player);
  assert.equal(stats.appearances,null);
  assert.equal(stats.goals,null);
  assert.equal(stats.minutes,null);
});
