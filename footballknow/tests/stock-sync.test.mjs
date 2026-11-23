import test from 'node:test';
import assert from 'node:assert/strict';
import {createFollowingSync} from '../public/stock-sync.mjs';
import {STOCK_FOLLOWING_KEY,readStockFollowing,toggleStockFollowing,readFollowingRecord} from '../public/stock-following.mjs';
const storage=codes=>{const m=new Map([[STOCK_FOLLOWING_KEY,JSON.stringify({version:1,codes})]]);return {getItem:k=>m.get(k)||null,setItem:(k,v)=>m.set(k,v)};};
function server(){
 let counter=0;const lists=new Map(),pairs=new Map();
 function device(){let group=++counter;const device='device'+group;lists.set(group,{codes:new Set(),seen:new Set()});let fail=false,hook=null;
 const state=()=>({id:'list'+group,device,codes:[...lists.get(group).codes].sort(),devices:2,revision:1});
 return {fail:()=>fail=true,hook:f=>hook=f,remove:code=>lists.get(group).codes.delete(code),request:async(path,options={})=>{
  const list=lists.get(group);
  if(path.endsWith('/pair')){pairs.set('TEST-CODE-PAIR',group);return {code:'TEST-CODE-PAIR'};}
  if(path.endsWith('/join')){const target=pairs.get(options.body.code);if(!target)throw Error('bad code');for(const c of list.codes)lists.get(target).codes.add(c);for(const i of list.seen)lists.get(target).seen.add(i);group=target;return state();}
  if(options.method==='POST'){
   for(const c of options.body.changes){if(list.seen.has(c.id))continue;list.seen.add(c.id);if(c.following)list.codes.add(c.code);else list.codes.delete(c.code);}
   if(hook){const f=hook;hook=null;f();}if(fail){fail=false;throw Error('connection lost after commit');}
  }
  return state();
 }};}
 return {device};
}
test('legacy device lists merge and later removal propagates without replacing other stocks',async()=>{
 const cloud=server(),a=cloud.device(),b=cloud.device(),sa=storage(['00700','00005']),sb=storage(['00001']);
 const ca=createFollowingSync({storage:sa,request:a.request}),cb=createFollowingSync({storage:sb,request:b.request});
 await ca.sync();await cb.sync();await cb.join((await ca.pair()).code);await ca.sync();
 assert.deepEqual(readStockFollowing(sa).codes,['00001','00005','00700']);
 assert.deepEqual(readStockFollowing(sb).codes,['00001','00005','00700']);
 toggleStockFollowing('00700',sb);toggleStockFollowing('600000',sb);await cb.sync();await ca.sync();
 assert.deepEqual(readStockFollowing(sa).codes,['00001','00005','600000']);
});
test('offline accepted writes are retry safe and never erase unsent changes',async()=>{
 const remote=server().device(),saved=storage(['00700']),sync=createFollowingSync({storage:saved,request:remote.request});
 remote.fail();await assert.rejects(sync.sync());assert.equal(readStockFollowing(saved).codes[0],'00700');assert.ok(readFollowingRecord(saved).cloud.pending.length);
 remote.remove('00700');toggleStockFollowing('00005',saved);await sync.sync();
 assert.deepEqual(readStockFollowing(saved).codes,['00005']);assert.equal(readFollowingRecord(saved).cloud.pending.length,0);
 remote.hook(()=>toggleStockFollowing('600000',saved));toggleStockFollowing('00001',saved);await sync.sync();
 assert.deepEqual(readStockFollowing(saved).codes,['00001','00005','600000']);
});
test('repeated refresh does not rewrite unchanged browser state or create another migration',async()=>{
 const remote=server().device(),saved=storage(['00005']);let writes=0;const set=saved.setItem;saved.setItem=(...v)=>{writes++;set(...v);};
 const sync=createFollowingSync({storage:saved,request:remote.request});await sync.sync();const first=writes;await sync.sync();assert.equal(writes,first);
});
test('malformed saved lists remain untouched and are never uploaded',async()=>{
 const saved=storage([]);saved.setItem(STOCK_FOLLOWING_KEY,'bad');let posts=0;
 const sync=createFollowingSync({storage:saved,request:async()=>{posts++;return {id:'x',device:'x',codes:[]};}});
 await assert.rejects(sync.sync());assert.equal(saved.getItem(STOCK_FOLLOWING_KEY),'bad');assert.equal(posts,1);
});
