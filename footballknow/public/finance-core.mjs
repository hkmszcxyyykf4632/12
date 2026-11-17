export const finite=value=>typeof value==='number'&&Number.isFinite(value);
export const figure=(value,digits=2)=>finite(value)?value.toLocaleString('zh-CN',{maximumFractionDigits:digits,minimumFractionDigits:digits}):'—';
export const signed=(value,digits=2)=>finite(value)?(value>0?'+':'')+figure(value,digits):'—';
export const direction=value=>!finite(value)||value===0?'neutral':value>0?'positive':'negative';
export const forecastLabel={up:'上涨',flat:'横盘',down:'下跌'};
export function validQuotes(value){return value?.version===1&&value.quotes&&typeof value.quotes==='object'&&Object.values(value.quotes).every(q=>finite(q.price)&&q.price>0&&Number.isFinite(Date.parse(q.quotedAt)));}
export function chartPoints(bars,limit=90){
  const rows=(bars||[]).filter(b=>finite(b.close)&&b.close>0&&typeof b.date==='string').slice(-limit);
  if(rows.length<2)return null;
  const low=Math.min(...rows.map(b=>b.close)),high=Math.max(...rows.map(b=>b.close)),range=high-low||high*.01||1;
  const points=rows.map((b,i)=>[30+i/(rows.length-1)*710,25+(high-b.close)/range*165]);
  return {rows,low,high,points:points.map(p=>p.map(n=>n.toFixed(2)).join(',')).join(' ')};
}
export function rateText(stats){return stats?.evaluated>0&&finite(stats.successRate)?figure(stats.successRate*100,1)+'%':'等待到期验证';}
export function financialRows(financials,kind,date){return (financials?.statements?.[kind]||[]).filter(row=>row.date===date);}
export function financialAmount(row){return finite(row?.amount)?figure(row.amount/1e8,2):'—';}
