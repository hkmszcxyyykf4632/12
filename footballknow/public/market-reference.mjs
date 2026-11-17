import {esc,sourceLink} from './ui.mjs';
import {readStockFollowing} from './stock-following.mjs';

const num=(n,d=2)=>Number.isFinite(n)?n.toLocaleString('zh-CN',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
const date=v=>v?new Date(v).toLocaleString('zh-CN',{hour12:false}):'尚未提供';
export function range52(q){
  return `<section class="stock-range"><div><span>52 周最高价</span><strong>${num(q?.high52,3)}</strong></div><div><span>52 周最低价</span><strong>${num(q?.low52,3)}</strong></div><p class="note">${q?`${esc(q.currency)} · 交易日 ${esc(q.tradeDate)} · ${sourceLink(q.source,q.provider)} · 过去 52 周盘中高低位；上市不足一年时为现有历史范围。`:'52 周区间正在同步；缺少资料显示为 —。'}</p></section>`;
}
export function policyCells(rate,failed=[]){
  if(!rate)return '<td>—<small>利率资料待同步</small></td><td>—</td>';
  const stale=failed.includes(rate.currency)||(failed.includes('BIS')&&rate.provider?.startsWith('BIS'));
  return `<td><strong>${Number.isFinite(rate.rate)?num(rate.rate,3)+'%':'—'}</strong><small>${esc(rate.name)}</small>${rate.note?`<small>${esc(rate.note)}</small>`:''}</td><td>${Number.isFinite(rate.changeBp)?`${rate.changeBp>0?'加息':'减息'} ${num(Math.abs(rate.changeBp),2)} 基点`:'未提供变动'}<small>${esc(rate.changedAt||'')} ${rate.asOf?' · 资料截至 '+esc(rate.asOf):''}</small>${sourceLink(rate.source,rate.provider||'官方来源')}${stale?'<small>本次更新失败，保留上次资料</small>':''}</td>`;
}
export function dailyRanking(rows,tradeDate,mode='gainers',codes=null){
  return rows.filter(q=>q.tradeDate===tradeDate&&Number.isFinite(q.changePercent)&&q.volume>0&&(!codes||codes.includes(q.code))&&(mode==='losers'?q.changePercent<0:q.changePercent>0)).sort((a,b)=>(mode==='losers'?a.changePercent-b.changePercent:b.changePercent-a.changePercent)||a.code.localeCompare(b.code)).slice(0,50);
}
export function renderStockRankings(main){
  const controller=new AbortController();let data=null,mode='gainers',onlyFollowing=false;
  main.innerHTML='<div class="page-heading"><div><p class="eyebrow">香港市场</p><h1>每日涨跌榜</h1><p class="lede">同一交易日的涨幅、跌幅，以及 52 周高低位。</p></div><a class="button secondary" href="#/stock-following">我的关注</a></div><div class="toolbar"><div class="segmented"><button data-ranking="gainers" class="active">涨幅榜</button><button data-ranking="losers">跌幅榜</button></div><label><input id="rank-following" type="checkbox"> 只看关注股票</label><button id="rank-refresh" class="button secondary">重新读取</button></div><p class="note" id="rank-status" role="status">正在读取…</p><div id="rank-table"></div>';
  function paint(){
    if(!data||controller.signal.aborted)return;
    const rows=dailyRanking(data.rows,data.tradeDate,mode,onlyFollowing?readStockFollowing().codes:null);
    main.querySelector('#rank-status').textContent=`交易日 ${data.tradeDate} · 来源覆盖 ${data.rows.length} / ${data.requested} 只 · 采集 ${date(data.fetchedAt)} · 最多显示前 50 名`;
    main.querySelector('#rank-table').innerHTML=rows.length?`<div class="table-wrap"><table><thead><tr><th>排名</th><th>股票</th><th>现价 / 币种</th><th>涨跌幅</th><th>成交量（股）</th><th>52 周最高</th><th>52 周最低</th><th>交易日 / 来源</th></tr></thead><tbody>${rows.map((q,i)=>`<tr><td>${i+1}</td><th><a class="stock-name" href="#/stock/${q.code}">${esc(q.name)}</a><small>${q.code}</small></th><td>${num(q.price,3)}<small>${esc(q.currency)}</small></td><td class="${q.changePercent>0?'market-rise':'market-fall'}">${q.changePercent>0?'+':''}${num(q.changePercent)}%</td><td>${num(q.volume,0)}</td><td>${num(q.high52,3)}</td><td>${num(q.low52,3)}</td><td>${esc(q.tradeDate)}<small>${sourceLink(q.source,q.provider)}</small></td></tr>`).join('')}</tbody></table></div><p class="note">${esc(data.method)} 排行资料每 10 分钟检查；未成交、停牌或报价日期不一致的股票不进入本日排行。</p>`:'<div class="empty">这个范围没有符合条件的股票。</div>';
  }
  async function load(){
    const button=main.querySelector('#rank-refresh');button.disabled=true;
    try{const r=await fetch('./finance/stock-rankings.json',{cache:'no-cache',signal:controller.signal});if(!r.ok)throw Error('排行资料尚未同步');data=await r.json();if(!Array.isArray(data.rows))throw Error('排行资料不完整');paint();}
    catch(e){if(!controller.signal.aborted)main.querySelector('#rank-status').textContent=e.message;}
    finally{if(!controller.signal.aborted)button.disabled=false;}
  }
  main.querySelectorAll('[data-ranking]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.ranking;main.querySelectorAll('[data-ranking]').forEach(x=>x.classList.toggle('active',x===b));paint();}));
  main.querySelector('#rank-following').addEventListener('change',e=>{onlyFollowing=e.target.checked;paint();});
  main.querySelector('#rank-refresh').addEventListener('click',load);load();
  const timer=setInterval(()=>{if(!document.hidden)load();},60000);
  return()=>{controller.abort();clearInterval(timer);};
}
