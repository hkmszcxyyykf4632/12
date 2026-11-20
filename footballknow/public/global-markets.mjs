import {main,esc,sourceLink} from './ui.mjs';
import {policyCells} from './market-reference.mjs';
import {mountCommodityChart,COMMODITY_IDS} from './commodity-chart.mjs';

const TITLES={'global-indices':'全球股票指数',commodities:'贵金属与原油',forex:'主要货币兑美元'};
const GROUPS={'global-indices':'indices',commodities:'commodities',forex:'forex'};
const amount=(value,digits=2)=>Number.isFinite(value)?value.toLocaleString('zh-CN',{minimumFractionDigits:digits,maximumFractionDigits:digits}):'—';
const stamp=value=>value?new Date(value).toLocaleString('zh-CN',{hour12:false}):'尚无报价';
const change=q=>Number.isFinite(q.changePercent)?`<span class="${q.changePercent>0?'market-rise':q.changePercent<0?'market-fall':''}">${q.changePercent>0?'+':''}${amount(q.changePercent)}%</span>`:'—';
const timing=q=>`${q.lastCheckOk===false?'本次未更新 · ':''}${q.delaySeconds?`来源延迟约 ${Math.round(q.delaySeconds/60)} 分钟`:q.updateMode==='streaming'?'来源流式报价':'来源未标注延迟'}<small>采集 ${esc(stamp(q.fetchedAt))}</small>`;

export function renderGlobalMarkets(page) {
  let rates=null,payload=null,filter='',query='',disposed=false,busy=false;
  const controller=new AbortController(),forex=page==='forex',commodity=page==='commodities';
  const description=forex?'统一列出本币兑美元与美元兑本币，方便直接比较。':commodity?'黄金、白银、铂金、钯金，以及布伦特与 WTI 原油的连续期货报价。':'按地区查看主要市场的指数点位与当日涨跌。';
  main.innerHTML=`<div class="page-heading"><div><p class="eyebrow">市场资讯</p><h1>${TITLES[page]}</h1><p class="lede">${description}</p></div><button class="button secondary" id="global-refresh">重新读取</button></div>
    <nav class="tabs market-tabs" aria-label="市场分类">${Object.entries(TITLES).map(([key,label])=>`<a href="#/${key}" class="${key===page?'active':''}">${label}</a>`).join('')}</nav>
    <div id="dollar-index"></div><div class="toolbar"><label class="search"><span class="sr-only">搜索市场</span><input type="search" id="global-search" placeholder="搜索名称、地区或代码"></label><select id="global-group" class="filter-select" aria-label="筛选市场地区"><option value="">全部${commodity?'品种':'地区'}</option></select></div>
    <p class="note" id="global-status" role="status">正在读取行情…</p><div class="${commodity?'commodity-layout':''}"><div id="global-quotes"></div>${commodity?'<section id="commodity-research"></section>':''}</div>
    <p class="note">涨跌幅按来源的上一收盘基准计算。页面每 60 秒检查一次，采集时间与交易所报价时间不同。${forex?'汇率为市场参考中间报价，不含银行买卖差价；涨跌幅统一表示本币相对美元的变化。':commodity?'连续期货会随主力合约换月，不等同于现货、金店售价或加油站零售价。':'各市场交易时段与延迟不同；休市时保留最近报价。'}每一行均可查看原始来源。</p>`;
  const chartPanel=commodity?mountCommodityChart(main.querySelector('#commodity-research')):null;
  main.querySelector('#global-quotes').addEventListener('click',e=>{const b=e.target.closest('[data-commodity]');if(b)chartPanel?.select(b.dataset.commodity);});
  const render=()=>{
    if(disposed||!payload)return;
    if(forex){const d=payload.quotes.find(q=>q.category==='dollarIndex'),us=rates?.rates?.USD;main.querySelector('#dollar-index').innerHTML='<section class="policy-summary"><div><span>美元指数 DXY</span><strong>'+amount(d?.price)+'</strong><span>'+change(d||{})+'</span></div><div><small>采集 '+esc(stamp(d?.fetchedAt))+'</small>'+sourceLink(d?.sourceUrl,'行情来源')+'</div><div><span>美国 · '+esc(us?.name||'政策利率')+'</span><strong>'+amount(us?.rate,3)+'%</strong><small>'+esc(us?.asOf||'资料待同步')+'</small></div></section><p class="note">'+esc(rates?.method||'政策利率资料正在同步')+'</p>';}
    const all=payload.quotes.filter(q=>q.category===GROUPS[page]);
    const groups=[...new Set(all.map(q=>forex?q.country:q.group))];
    const select=main.querySelector('#global-group');
    select.innerHTML=`<option value="">全部${commodity?'品种':'地区'}</option>`+groups.map(g=>`<option value="${esc(g)}">${esc(g)}</option>`).join('');select.value=filter;
    const rows=all.filter(q=>(!filter||(forex?q.country:q.group)===filter)&&(!query||[q.name,q.symbol,q.country,q.currencyCode].join(' ').toLowerCase().includes(query)));
    const misses=all.filter(q=>!q.lastCheckOk).length;
    main.querySelector('#global-status').textContent=`显示 ${rows.length} / ${all.length} 项 · 最近检查 ${stamp(payload.checkedAt)}${misses?` · ${misses} 项本次未更新，保留已有报价`:''}`;
    main.querySelector('#global-quotes').innerHTML=rows.length?`<div class="table-wrap"><table class="global-quotes"><thead><tr><th>${forex?'货币 / 地区':'名称 / 市场'}</th>${forex?'<th>1 单位本币 = 美元</th><th>1 美元 = 本币</th><th>本币兑美元涨跌</th>':'<th>最新报价</th><th>涨跌幅</th><th>今日范围</th>'}${forex?'<th>央行基准 / 参考利率</th><th>最近加减 / 资料日期</th>':''}<th>报价与采集</th><th>来源</th></tr></thead><tbody>${rows.map(q=>`<tr><th scope="row">${esc(q.name)}${commodity?` <button class="button quiet compact" data-commodity="${COMMODITY_IDS[q.symbol]}">走势分析</button>`:''}<small>${esc(q.currencyCode||q.symbol)} · ${esc(q.country||q.group)}${commodity?' · 连续期货':''}</small></th>${forex?`<td class="market-number">${amount(q.usdPerUnit,6)} <small>USD</small></td><td class="market-number">${amount(q.unitsPerUsd,4)} <small>${esc(q.currencyCode)}</small></td><td>${change(q)}</td>`:`<td class="market-number">${amount(q.price)}<small>${esc(q.unit)}</small></td><td>${change(q)}<small>${Number.isFinite(q.change)?`${q.change>0?'+':''}${amount(q.change)}`:'—'}</small></td><td>${amount(q.low)} — ${amount(q.high)}</td>`}${forex?policyCells(rates?.rates?.[q.currencyCode],rates?.failed):''}<td class="small">${timing(q)}</td><td>${sourceLink(q.sourceUrl,'TradingView')}</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">没有符合筛选条件的市场。</div>';
  };
  const load=async()=>{
    if(busy||disposed)return;busy=true;
    const button=main.querySelector('#global-refresh');button.disabled=true;
    try{if(forex){try{const r=await fetch('./finance/policy-rates.json',{cache:'no-cache',signal:controller.signal});if(r.ok)rates=await r.json();}catch{}}const response=await fetch('./finance/global-markets.json',{cache:'no-cache',signal:controller.signal});if(!response.ok)throw Error('行情尚未同步');const next=await response.json();if(!Array.isArray(next.quotes))throw Error('行情格式不完整');payload=next;render();}
    catch(error){if(!disposed&&error.name!=='AbortError')main.querySelector('#global-status').textContent=`${error.message}。${payload?'继续显示上次行情。':'稍后重试。'}`;}
    finally{busy=false;if(!disposed)button.disabled=false;}
  };
  main.querySelector('#global-search').addEventListener('input',e=>{query=e.target.value.trim().toLowerCase();render();});
  main.querySelector('#global-group').addEventListener('change',e=>{filter=e.target.value;render();});
  main.querySelector('#global-refresh').addEventListener('click',load);
  const timer=setInterval(()=>{if(!document.hidden)load();},60_000);load();
  return()=>{disposed=true;controller.abort();chartPanel?.dispose();clearInterval(timer);};
}
