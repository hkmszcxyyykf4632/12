import test from 'node:test';
import assert from 'node:assert/strict';
import {STOCK_FOLLOWING_KEY,readStockFollowing,toggleStockFollowing} from '../public/stock-following.mjs';

function storage(){const rows=new Map([['footballknow.personal.v1','football records']]);return {rows,getItem:key=>rows.get(key)??null,setItem:(key,value)=>rows.set(key,value)};}
test('stock follows survive a fresh read, merge the latest list and can be removed',()=>{
  const saved=storage();
  assert.deepEqual(readStockFollowing(saved).codes,[]);
  assert.equal(toggleStockFollowing('00700',saved).following,true);
  toggleStockFollowing('00005',saved);
  assert.deepEqual(readStockFollowing(saved).codes,['00700','00005']);
  assert.equal(toggleStockFollowing('00700',saved).following,false);
  assert.deepEqual(readStockFollowing(saved).codes,['00005']);
  assert.equal(saved.getItem('footballknow.personal.v1'),'football records');
});
test('invalid or inaccessible storage is never overwritten or reported as saved',()=>{
  for(const raw of ['broken',JSON.stringify({version:1,codes:['00700','00700']}),JSON.stringify({version:1,codes:['<script>']})]){
    const saved=storage();saved.setItem(STOCK_FOLLOWING_KEY,raw);
    assert.ok(readStockFollowing(saved).problem);
    assert.throws(()=>toggleStockFollowing('00700',saved));
    assert.equal(saved.getItem(STOCK_FOLLOWING_KEY),raw);
  }
  assert.throws(()=>toggleStockFollowing('../secret',storage()),/代码/);
  assert.throws(()=>toggleStockFollowing('00700',{getItem:()=>null,setItem:()=>{throw Error('QuotaExceeded');}}),/未保存/);
});
