import test from 'node:test';
import assert from 'node:assert/strict';
import {replayUrl} from '../public/racing-replay.mjs';
const race={date:'2026-11-14',course:'ST',raceNo:1,status:'finished'};
test('replay points to official Chinese video for the exact completed race',()=>{
  const u=new URL(replayUrl(race));assert.equal(u.hostname,'racing.hkjc.com');assert.equal(u.searchParams.get('date'),'20261114');assert.equal(u.searchParams.get('no'),'01');assert.equal(u.searchParams.get('lang'),'chi');
});
test('future cancelled and invalid races have no replay link',()=>{
  for(const change of [{status:'scheduled'},{status:'cancelled'},{raceNo:99},{date:'2026-02-30'},{date:'invalid'},{course:'XX'}])assert.equal(replayUrl({...race,...change}),'');
});
