import {validMarket,PHASE_NAMES,MARKET_NAMES} from './markets-core.mjs';
import {quotesForMatch} from './settlement.mjs';
const usable=q=>validMarket(q)&&['asian-handicap','total-goals','90-minute-1x2'].includes(q.market)&&!q.manual&&!q.inPlay;
const latest=rows=>rows.slice().sort((a,b)=>String(b.fetchedAt).localeCompare(String(a.fetchedAt)))[0];
const median=values=>{const a=values.slice().sort((x,y)=>x-y),n=Math.floor(a.length/2);return a.length%2?a[n]:(a[n-1]+a[n])/2;};
export const quotePhase=q=>q.lastPregame?'赛前最后记录':PHASE_NAMES[q.phase];
export const lineText=n=>n===0?'平手':n<0?'让 '+Math.abs(n)+' 球':'受让 '+n+' 球';
export const alertValue=(alert,value)=>alert.measure==='price'?Number(value).toFixed(2):alert.market==='total-goals'?value+' 球':lineText(value);
export const alertSubject=alert=>MARKET_NAMES[alert.market||'asian-handicap']+(alert.selection?' · '+({H:alert.market==='90-minute-1x2'?'主胜':'主队',D:'平局',A:alert.market==='90-minute-1x2'?'客胜':'客队',O:'大球',U:'小球'})[alert.selection]:alert.market==='asian-handicap'?' · 主队':'')+(alert.measure==='price'&&alert.market!=='90-minute-1x2'?'（'+(alert.market==='total-goals'?alert.current.line+' 球':lineText(alert.current.line))+'）':'');

function compare(reference,current,basis,samples,historical,lineThreshold,priceThreshold){
  const base={market:current.market,provider:current.provider,current,basis,samples,sampleCount:samples.length};
  if(current.market!=='90-minute-1x2'){
    const change=current.line-reference.line,flip=current.market==='asian-handicap'&&current.line*reference.line<0;
    if(Math.abs(change)>=lineThreshold||flip)return [{...base,measure:'line',from:reference.line,to:current.line,change,
      type:historical?'交锋盘口异常':flip?'让受方向反转':current.market==='total-goals'?'大小球变盘':change<0?'本场升盘':'本场退盘',
      severity:Math.abs(change)/lineThreshold}];
    if(current.line!==reference.line)return [];
  }
  return Object.keys(current.prices).flatMap(selection=>{
    const from=reference.prices[selection],to=current.prices[selection],change=(to-from)/from;
    if(!Number.isFinite(change)||Math.abs(change)<priceThreshold)return [];
    return [{...base,measure:'price',selection,from,to,change,type:(historical?'交锋赔率':'本场赔率')+(change<0?'明显下降':'明显上升'),severity:Math.abs(change)/priceThreshold}];
  });
}

export function handicapAlerts(match,feed,lineThreshold=.5,priceThreshold=.15){
  const quotes=(match.quotes||quotesForMatch(feed?.markets,match)).filter(usable),alerts=[],groups=new Map();
  for(const q of quotes){const key=[q.market,q.provider,q.via].join('|');groups.set(key,[...(groups.get(key)||[]),q]);}
  for(const rows of groups.values()){
    const current=latest(rows.filter(q=>q.phase===(match.finished?'closing':'latest')))||latest(rows.filter(q=>q.phase==='latest'&&q.lastPregame))||latest(rows.filter(q=>q.phase==='opening'||q.phase==='preclosing'));
    if(!current)continue;
    const opening=latest(rows.filter(q=>q.phase==='opening'))||latest(rows.filter(q=>q.phase==='preclosing'));
    if(opening&&current!==opening)alerts.push(...compare(opening,current,quotePhase(opening)+' → '+quotePhase(current),
      [{date:match.date||match.day,quote:opening}],false,lineThreshold,priceThreshold));
    const samples=[],seen=new Set();
    const history=(feed?.data?.matches||[]).filter(m=>m.finished&&m.home===match.home&&m.away===match.away&&m.competition===match.competition
      &&Date.parse(m.kickoff||m.date)<Date.parse(match.kickoff||match.date)).sort((a,b)=>b.date.localeCompare(a.date));
    for(const prior of history){
      const key=prior.date+'|'+prior.home+'|'+prior.away;if(seen.has(key))continue;seen.add(key);
      const compatible=quotesForMatch(feed.markets,prior).filter(q=>usable(q)&&q.market===current.market&&q.provider===current.provider&&q.via===current.via);
      const quote=latest(compatible.filter(q=>q.phase==='closing'))||latest(compatible.filter(q=>q.phase==='preclosing'));
      if(quote)samples.push({date:prior.date,quote});if(samples.length===5)break;
    }
    if(samples.length>=2){
      const line=current.market==='90-minute-1x2'?null:median(samples.map(s=>s.quote.line));
      const basis='同一主客场、同一赛事，最近'+samples.length+'次报价中位数 → 本场'+quotePhase(current);
      if(line!==null&&line!==current.line){
        alerts.push(...compare({line,prices:{}},current,basis,samples,true,lineThreshold,priceThreshold));
      }else{
        const sameLine=samples.filter(s=>current.market==='90-minute-1x2'||s.quote.line===current.line);
        if(sameLine.length>=2){
          const prices=Object.fromEntries(Object.keys(current.prices).map(k=>[k,median(sameLine.map(s=>s.quote.prices[k]))]));
          alerts.push(...compare({line,prices},current,'同主客场、同赛事、同盘口，最近'+sameLine.length+'次报价中位数 → 本场'+quotePhase(current),sameLine,true,lineThreshold,priceThreshold));
        }
      }
    }
  }
  return alerts.sort((a,b)=>b.severity-a.severity);
}
