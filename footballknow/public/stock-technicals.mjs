import {finite} from './finance-core.mjs';

const validDate=value=>typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value))&&new Date(value).toISOString().slice(0,10)===value;
export function technicalSeries(bars){
  const days=new Map();
  for(const bar of Array.isArray(bars)?bars:[]){
    if(!validDate(bar?.date))continue;
    const close=finite(bar.close)&&bar.close>0?bar.close:null;
    const candle=close!==null&&[bar.open,bar.high,bar.low].every(v=>finite(v)&&v>0)&&bar.low<=Math.min(bar.open,close)&&bar.high>=Math.max(bar.open,close);
    days.set(bar.date,{date:bar.date,close,open:candle?bar.open:null,high:candle?bar.high:null,low:candle?bar.low:null,candle,
      volume:finite(bar.volume)&&bar.volume>=0?bar.volume:null,ma5:null,ma10:null});
  }
  const rows=[...days.values()].sort((a,b)=>a.date.localeCompare(b.date));
  for(let i=0;i<rows.length;i++)for(const period of [5,10]){
    const sample=rows.slice(Math.max(0,i-period+1),i+1);
    if(sample.length===period&&sample.every(row=>row.close!==null))rows[i]['ma'+period]=sample.reduce((sum,row)=>sum+row.close,0)/period;
  }
  return rows;
}

export function technicalWindow(bars,range=90){
  const all=technicalSeries(bars);
  if(!all.length)return [];
  const days=range===260?365:range===30?30:90,cutoff=Date.parse(all.at(-1).date)-(days-1)*86400000;
  return all.filter(row=>Date.parse(row.date)>=cutoff);
}

export function technicalScale(rows){
  const prices=rows.flatMap(row=>[row.low,row.high,row.close,row.ma5,row.ma10]).filter(v=>finite(v)&&v>0);
  if(!prices.length)return null;
  const min=Math.min(...prices),max=Math.max(...prices),padding=(max-min||max*.02||1)*.08;
  return {low:Math.max(0,min-padding),high:max+padding,volumeMax:Math.max(0,...rows.map(row=>row.volume??0))};
}

export function volumeUnit(history){return history?.volumeUnit||(history?.provider==='Yahoo Finance'?'股':'来源单位');}
