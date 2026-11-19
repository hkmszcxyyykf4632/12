import test from 'node:test';
import assert from 'node:assert/strict';
import {replayUrl,recordRace,recordReplayUrl} from '../public/racing-replay.mjs';
const race={date:'2026-11-14',course:'ST',raceNo:1,status:'finished'};
test('replay points to official Chinese video for the exact completed race',()=>{
  const u=new URL(replayUrl(race));assert.equal(u.hostname,'racing.hkjc.com');assert.equal(u.searchParams.get('date'),'20261114');assert.equal(u.searchParams.get('no'),'01');assert.equal(u.searchParams.get('lang'),'chi');
});
test('future cancelled and invalid races have no replay link',()=>{
  for(const change of [{status:'scheduled'},{status:'cancelled'},{raceNo:99},{date:'2026-02-30'},{date:'invalid'},{course:'XX'}])assert.equal(replayUrl({...race,...change}),'');
});

test('a horse past run links to the replay of that exact race',()=>{
  const run={date:'2026-06-24',raceId:'2026-06-24-HV-1',raceNo:'1',withdrawn:false,course:'跑马地'};
  assert.deepEqual(recordRace(run,'2026-11-17'),{date:'2026-06-24',course:'HV',raceNo:1,status:'finished'});
  const u=new URL(recordReplayUrl(run,'2026-11-17'));assert.equal(u.searchParams.get('date'),'20260624');assert.equal(u.searchParams.get('no'),'01');
  assert.equal(new URL(recordReplayUrl({...run,raceId:'2026-06-24-ST-11',raceNo:'11'},'2026-11-17')).searchParams.get('no'),'11');
});
test('withdrawn, overseas, future and mismatched past runs have no replay',()=>{
  const run={date:'2026-06-24',raceId:'2026-06-24-HV-1',withdrawn:false};
  for(const change of [{withdrawn:true},{raceId:null},{raceId:''},{raceId:'2026-06-24-SEOUL-1'},{raceId:'2026-06-25-HV-1'},{raceId:'2026-06-24-HV-13'},{raceId:'2026-06-24-HV-1; x'}])assert.equal(recordReplayUrl({...run,...change},'2026-11-17'),'',JSON.stringify(change));
  assert.equal(recordReplayUrl(run,'2026-06-23'),'');assert.equal(recordReplayUrl(undefined),'');
});
