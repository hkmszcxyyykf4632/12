export const finite=value=>typeof value==='number'&&Number.isFinite(value);
export const figure=(value,digits=2)=>finite(value)?value.toLocaleString('zh-CN',{maximumFractionDigits:digits,minimumFractionDigits:digits}):'—';
export const signed=(value,digits=2)=>finite(value)?(value>0?'+':'')+figure(value,digits):'—';
export const direction=value=>!finite(value)||value===0?'neutral':value>0?'positive':'negative';
export const forecastLabel={up:'上涨',flat:'横盘',down:'下跌'};
export function validQuotes(value){return value?.version===1&&value.quotes&&typeof value.quotes==='object'&&Object.values(value.quotes).every(q=>finite(q.price)&&q.price>0&&(Number.isFinite(Date.parse(q.quotedAt))||Number.isFinite(Date.parse(q.barAt))&&Number.isFinite(Date.parse(q.fetchedAt))));}
export function chartPoints(bars,limit=90){
  const rows=(bars||[]).filter(b=>finite(b.close)&&b.close>0&&typeof b.date==='string').slice(-limit);
  if(rows.length<2)return null;
  const low=Math.min(...rows.map(b=>b.close)),high=Math.max(...rows.map(b=>b.close)),range=high-low||high*.01||1;
  const points=rows.map((b,i)=>[30+i/(rows.length-1)*710,25+(high-b.close)/range*165]);
  return {rows,low,high,points:points.map(p=>p.map(n=>n.toFixed(2)).join(',')).join(' ')};
}
export function rateText(stats){return stats?.evaluated>0&&finite(stats.successRate)?figure(stats.successRate*100,1)+'%':'等待到期验证';}
export function financialRows(financials,kind,date){return (financials?.statements?.[kind]||[]).filter(row=>row.date===date);}
export const financialUnit=row=>/每股/.test(row?.name||'')?'元/股':'亿元';
export function financialAmount(row){return finite(row?.amount)?financialUnit(row)==='元/股'?figure(row.amount,4):figure(row.amount/1e8,2):'—';}
export const primaryStockSectors=['地产','金融','博彩','科技'];
export const sectorOrder=['地产','金融','博彩','科技','消费','医疗保健','工业制造','能源资源','电讯公用','旅游酒店','传媒娱乐','建筑工程','商业服务','交通运输','农业产品','综合企业','待分类'];
export const stockSector=row=>row?.industryUpdatedAt&&row.sector&&row.sector!=='未分类'?row.sector:'待分类';
export function industryGroups(stocks){
  const counts=new Map();for(const row of stocks||[]){const key=stockSector(row);counts.set(key,(counts.get(key)||0)+1);}
  return [...counts].sort(([a],[b])=>{const order=x=>sectorOrder.includes(x)?sectorOrder.indexOf(x):sectorOrder.length-1;return order(a)-order(b)||a.localeCompare(b,'zh-CN');});
}
export function filterStocks(stocks,{scope='all',sector='all',query='',quotes={}}={}){
  const term=query.trim().toLowerCase();
  return (stocks||[]).filter(r=>(scope==='all'||scope==='hsi'&&r.isHsi||scope==='main'&&r.board==='主板'||scope==='gem'&&r.board==='GEM'||scope==='reit'&&r.category==='Real Estate Investment Trusts')&&(sector==='all'||(sector==='其它'?![...primaryStockSectors,'待分类'].includes(stockSector(r)):stockSector(r)===sector))&&(!term||[r.code,r.name,r.englishName,quotes[r.code]?.name].filter(Boolean).join(' ').toLowerCase().includes(term)));
}
