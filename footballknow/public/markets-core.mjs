export const MARKET_NAMES={'90-minute-1x2':'90分钟胜平负','asian-handicap':'亚洲让球盘','total-goals':'大小球','correct-score':'比分赔率'};
export const PHASE_NAMES={opening:'开始赔率',preclosing:'赛前早期报价',latest:'最新赔率',closing:'最后赔率'};
export const SELECTIONS={H:'主队',D:'平局',A:'客队',O:'大球',U:'小球'};
export function validMarket(q){
  if(!q||!MARKET_NAMES[q.market]||!PHASE_NAMES[q.phase]||typeof q.provider!=='string'||!q.provider.trim()||!q.prices)return false;
  const keys=Object.keys(q.prices);
  if(!keys.length||!keys.every(k=>typeof q.prices[k]==='number'&&Number.isFinite(q.prices[k])&&q.prices[k]>1&&q.prices[k]<=10000))return false;
  const expected=q.market==='90-minute-1x2'?['H','D','A']:q.market==='asian-handicap'?['H','A']:q.market==='total-goals'?['O','U']:null;
  if(expected&&(keys.length!==expected.length||!expected.every(k=>keys.includes(k))))return false;
  if(!expected&&!keys.every(k=>/^\d{1,2}:\d{1,2}$/.test(k)))return false;
  if(['asian-handicap','total-goals'].includes(q.market)&&(!Number.isFinite(q.line)||Math.abs(q.line)>20||Math.round(q.line*4)!==q.line*4||q.market==='total-goals'&&q.line<0))return false;
  return true;
}
export function marketComparisons(quotes){
  const groups=new Map();
  for(const q of quotes.filter(validMarket)){
    const key=[q.provider,q.market,q.via||'',q.manual?'manual':'source'].join('|'),group=groups.get(key)||[];
    group.push(q);groups.set(key,group);
  }
  return [...groups.values()].flatMap(rows=>{
    const opening=rows.find(q=>q.phase==='opening')||rows.find(q=>q.phase==='preclosing');
    const closing=rows.find(q=>q.phase==='closing')||rows.find(q=>q.phase==='latest');
    if(!opening||!closing)return [];
    return [{provider:opening.provider,market:opening.market,opening,closing,sameLine:opening.line===closing.line,
      changes:Object.keys(opening.prices).filter(k=>Number.isFinite(closing.prices[k])).map(k=>({key:k,from:opening.prices[k],to:closing.prices[k],percent:(closing.prices[k]/opening.prices[k]-1)*100}))}];
  });
}
export function movementSummary(quotes){
  const rows=marketComparisons(quotes);
  if(!rows.length)return ['还没有同一机构、同一盘口的两个报价时点，暂时不能比较变化。'];
  const preferred=rows.filter(r=>r.provider==='市场平均'),sample=preferred.length?preferred:rows.slice(0,3);
  return sample.map(r=>{
    const base=r.provider+'的'+MARKET_NAMES[r.market]+'，'+PHASE_NAMES[r.opening.phase]+'至'+PHASE_NAMES[r.closing.phase];
    if(!r.sameLine)return base+'从 '+r.opening.line+' 调整到 '+r.closing.line+'。盘口条件已变，两个赔率不作同条件涨跌比较。';
    const changes=r.changes.map(c=>(SELECTIONS[c.key]||c.key)+' '+c.from.toFixed(2)+' → '+c.to.toFixed(2)+'（'+(c.percent>0?'+':'')+c.percent.toFixed(1)+'%）').join('，');
    return base+'：'+changes+'。'+(r.market==='90-minute-1x2'?'赔率下降对应未去水隐含概率上升，不能单凭变化确定赛果。':'变化只表示该盘口报价调整。');
  });
}
export function manualMarket(input){
  const q={...input,provider:String(input.provider||'').trim(),manual:true,via:'手动录入',fetchedAt:new Date().toISOString()};
  if(!validMarket(q)||q.provider.length>80)throw new Error('请核对盘口、机构和十进制赔率（大于1）。');
  if(!Number.isFinite(Date.parse(q.quotedAt))||Date.parse(q.quotedAt)>Date.now()+60000)throw new Error('请填写已经发生的报价时间。');
  return q;
}
