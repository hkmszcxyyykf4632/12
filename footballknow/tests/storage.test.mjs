import test from 'node:test';
import assert from 'node:assert/strict';

const storage=new Map();
globalThis.localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)};
const state=await import('../public/personal-store.mjs');

test('corrupt personal records remain untouched and can be exported',()=>{
  storage.set(state.STORAGE_KEY,'{broken');state.reloadStore();
  assert.ok(state.storeProblem);
  assert.throws(()=>state.commit({version:1,odds:[],bets:[]}));
  assert.equal(storage.get(state.STORAGE_KEY),'{broken');
  storage.clear();state.reloadStore();
});

test('auto settlement accepts one confirmed alias and rejects ambiguous matches',()=>{
  const bet={id:'test',home:'A',away:'B',date:'2026-01-01',source:'manual',matchId:'old',stake:10000,oddsMilli:2100,selection:'H',result:null};
  state.commit({version:1,odds:[],bets:[bet]});
  assert.equal(state.reconcile([{id:'new',aliases:['old'],finished:false,result:null}]),false);
  assert.equal(state.reconcile([{id:'one',aliases:['old'],finished:true,result:'H'},{id:'two',aliases:['old'],finished:true,result:'A'}]),false);
  assert.equal(state.reconcile([{id:'new',aliases:['old'],finished:true,result:'H'}]),true);
  assert.equal(state.store.bets[0].result,'H');
  assert.equal(state.store.bets[0].oddsMilli,2100);
});
