import {esc,sourceLink,timeText} from './ui.mjs';
import {renderStockChart} from './stock-chart.mjs';
const ITEMS={gold:'黄金',silver:'白银',platinum:'铂金',palladium:'钯金',wti:'WTI原油',brent:'布伦特原油'};
export const COMMODITY_IDS={'COMEX:GC1!':'gold','COMEX:SI1!':'silver','NYMEX:PL1!':'platinum','NYMEX:PA1!':'palladium','NYMEX:CL1!':'wti','ICEEUR:BRN1!':'brent'};
export function mountCommodityChart(target){
  let disposed=false,token=0,payload=null,selected='gold',range=90;
  target.innerHTML=`<div class="section-head"><h2>走势与分析</h2><select aria-label="图表品种">${Object.entries(ITEMS).map(([id,label])=>`<option value="${id}">${label}</option>`).join('')}</select></div><div class="toolbar"><select aria-label="图表时间范围"><option value="30">近1个月</option><option value="90" selected>近3个月</option><option value="365">近1年</option></select><span class="note">日线 · 5 / 10 日均线 · 成交量</span></div><div data-commodity-chart></div><div data-commodity-analysis></div>`;
  const plot=target.querySelector('[data-commodity-chart]'),text=target.querySelector('[data-commodity-analysis]'),select=target.querySelector('[aria-label="图表品种"]');
  function draw(){renderStockChart(plot,payload,range);const a=payload?.analysis;text.innerHTML=`${payload?.message?`<p class="note">${esc(payload.message)}</p>`:''}${a?`<h3>${esc(ITEMS[selected])} · ${esc(a.trend||'资料待齐')}</h3><p>${esc(a.summary)}</p><p>${esc(a.context||'')}</p>${Number.isFinite(a.volatility20Annualized)?`<p>20日年化波动率：<b>${a.volatility20Annualized.toFixed(1)}%</b></p>`:''}<details><summary>计算方法与资料时间</summary><p class="note">${esc(a.method||'')}</p><p class="note">日线截至 ${esc(a.asOf||'—')} · 采集 ${timeText(payload.updatedAt)}</p></details>`:''}<p class="note">${esc(payload?.basis||'历史日线与报价表分别标注来源。')}${payload?.paused?' · 管理员已暂停同步':''} ${sourceLink(payload?.source,'日线来源')}</p>`;}
  async function load(id){if(!ITEMS[id])return;selected=id;select.value=id;payload=null;plot.innerHTML='<div class="empty">正在读取历史日线…</div>';text.innerHTML='';const current=++token;try{const r=await fetch('/api/commodities/'+id+'/history',{cache:'no-store',signal:AbortSignal.timeout(60000)});if(!r.ok)throw Error();const next=await r.json();if(disposed||current!==token)return;payload=next;draw();}catch{if(!disposed&&current===token)plot.innerHTML='<div class="empty">日线暂时无法读取，请切换品种后重试。</div>';}}
  select.onchange=()=>load(select.value);target.querySelector('[aria-label="图表时间范围"]').onchange=e=>{range=Number(e.target.value);draw();};load('gold');
  return {select:load,dispose(){disposed=true;token++;}};
}
