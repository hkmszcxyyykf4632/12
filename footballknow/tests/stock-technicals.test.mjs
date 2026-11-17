import test from 'node:test';
import assert from 'node:assert/strict';
import {technicalSeries,technicalWindow,technicalScale,volumeUnit} from '../public/stock-technicals.mjs';

const rows=Array.from({length:45},(_,i)=>({date:new Date(Date.UTC(2026,0,i+1)).toISOString().slice(0,10),open:i+10,close:i+11,high:i+12,low:i+9,volume:i*100,adjustedClose:999}));
test('MA5 and MA10 use matching closing prices with no future data and full warm-up',()=>{
  const series=technicalSeries(rows);
  assert.equal(series[3].ma5,null);
  assert.equal(series[4].ma5,13);
  assert.equal(series[8].ma10,null);
  assert.equal(series[9].ma10,15.5);
  assert.equal(technicalWindow(rows,30)[0].ma10,technicalSeries(rows)[15].ma10);
  assert.equal(technicalWindow(rows,30).length,30);
  assert.deepEqual(technicalSeries(rows.slice(0,12)),series.slice(0,12));
});
test('missing prices break the average window; missing OHLC and volume are not fabricated',()=>{
  const input=rows.slice(0,12).map(row=>({...row}));input[5].close=null;input[10].open=null;input[11].low=1000;input[10].volume=null;
  const series=technicalSeries(input);
  assert.equal(series[9].ma5,null);
  assert.equal(series[10].ma5,19);
  assert.equal(series[10].candle,false);
  assert.equal(series[11].candle,false);
  assert.equal(series[0].volume,0);
  assert.equal(series[10].volume,null);
  assert.equal(technicalScale([]),null);
  assert.ok(technicalScale(series).high>technicalScale(series).low);
  assert.equal(volumeUnit({provider:'Yahoo Finance'}),'股');
  assert.equal(volumeUnit({provider:'unknown'}),'来源单位');
});
test('dates are ordered and deduplicated without accepting invalid calendar dates',()=>{
  const series=technicalSeries([rows[2],rows[0],rows[2],{...rows[1],date:'2026-02-30'}]);
  assert.deepEqual(series.map(row=>row.date),[rows[0].date,rows[2].date]);
});
