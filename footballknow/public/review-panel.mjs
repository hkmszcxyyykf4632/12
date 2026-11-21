import {esc} from './ui.mjs';
import {readStockFollowing} from './stock-following.mjs';
import {evidenceReviewHtml} from './evidence-review.mjs';

const stamp=v=>v?new Date(v).toLocaleString('zh-CN',{hour12:false}):'—';
const pick={H:'主胜',D:'平局',A:'客胜',up:'上涨',flat:'横盘',down:'下跌'};
const percent=v=>Number.isFinite(v)?`${v>0?'+':''}${(v*100).toFixed(2)}%`:'—';
export function conciseReport(report){
  if(report?.format==='evidence-review-1')return evidenceReviewHtml(report);
  return report?`<div class="research-summary">${(report.summary||[]).map(p=>`<p>${esc(p)}</p>`).join('')}${report.generatedAt?`<small class="subtle">整理 ${esc(stamp(report.generatedAt))}</small>`:''}<details><summary>更多详细资料</summary>${(report.details||[]).map(d=>`<h3>${esc(d.title)}</h3><p>${esc(d.text)}</p>`).join('')}</details></div>`:'';
}
export async function syncStockWatchlist(signal){
  const state=readStockFollowing();
  if(state.problem)throw Error('当前浏览器关注名单不可读取，未更改服务器名单。');
  const r=await fetch('/api/stocks/watchlist',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({codes:state.codes}),signal});
  const data=await r.json();if(!r.ok)throw Error(data.detail||'关注名单尚未同步');return data;
}
export function bindReview(target,{kind,id,league,signal}){
  let busy=false;
  const isStock=kind==='stock',isAsset=kind==='asset';
  const url=isStock?`/api/stocks/${id}/review`:isAsset?`/api/assets/${id}/analysis`:`/api/reviews/football?league=${league}&match_id=${encodeURIComponent(id)}`;
  target.innerHTML=`<div class="section-head"><h2>${isStock?'收盘复盘':isAsset?'市场分析':'赛前预测 · 赛后复盘'}</h2><button class="button secondary" data-review-generate>生成${isAsset?'分析':'复盘'}</button></div><p data-review-message class="note" role="status">正在读取…</p><div data-review-body></div>`;
  const button=target.querySelector('[data-review-generate]'),message=target.querySelector('[data-review-message]'),body=target.querySelector('[data-review-body]');
  function allowed(){return !isStock||readStockFollowing().codes.includes(id);}
  const updateAllowed=()=>{button.disabled=busy||!allowed()||button.dataset.unavailable==='1';if(!allowed())message.textContent='加入我的关注后，才会进行新的分析和收盘复盘。';};
  async function load(generate=false){
    if(busy||signal?.aborted)return;
    if(generate&&!allowed())return;
    busy=true;button.disabled=true;message.textContent=generate?'正在根据原记录整理…':'正在读取…';
    const controller=new AbortController(),abort=()=>controller.abort();signal?.addEventListener('abort',abort,{once:true});
    const timer=setTimeout(abort,generate?150000:15000);
    try{
      if(generate&&isStock)await syncStockWatchlist(controller.signal);
      const r=await fetch(url,{cache:'no-cache',signal:controller.signal,...(generate?{method:'POST'}:{})}),data=await r.json();
      if(!r.ok)throw Error(data.detail||'暂时无法读取');if(signal?.aborted)return;
      if(isAsset){body.innerHTML=conciseReport(data.report);message.textContent=data.report?'每个品种每天保留一份分析。':'管理员可以生成当天的市场分析。';return;}
      const original=data.original;
      const hasOriginal=isStock?['week','quarter'].every(h=>['up','flat','down'].includes(original?.[h])):['H','D','A'].includes(original?.pick);
      if(!hasOriginal){body.innerHTML=conciseReport(data.review);message.textContent=data.message||(isStock?'此收盘之前没有保存的有效预测，暂不能对照复盘。':data.finished?'没有保存的赛前预测；下方为赛后事实研究，不补写原判断。':'比赛未完场，赛后再核对事实。');button.dataset.unavailable=(isStock||!data.finished)?'1':'';return;}
      let content='';
      if(isStock){content=`<p>收盘日期：<strong>${esc(data.close?.date||'待确认')}</strong> · 当日复权涨跌 ${percent(data.dailyReturn)}</p><div class="forecast-rates">${['week','quarter'].map(h=>{const o=data.outcomes?.[h]||{};return `<div><span>${h==='week'?'一周':'一季度'}原预测：${pick[original[h]]}</span><strong>${o.status==='已到期'?(o.correct===true?'命中':o.correct===false?'未命中':'尚不能验证'):'观察中'}</strong><small>${esc(o.completedSessions??0)} / ${esc(o.requiredSessions??(h==='week'?5:63))} 个交易日${o.status==='已到期'?' · 区间 '+percent(o.return):''}</small></div>`;}).join('')}</div>`;}
      else{content=`<p>原首选：<strong>${pick[original.pick]}</strong> · ${data.finished?`实际 ${pick[data.actual]||'待确认'}${Array.isArray(data.score)?`（${data.score.map(esc).join(' : ')}）`:''} · <strong>${data.correct===true?'命中':data.correct===false?'未命中':'尚不能验证'}</strong>`:'尚未完场'}</p>`;}
      const paragraphs=isStock?original.summary:original.analysis?.summary;
      content+=`<details class="racing-original"><summary>查看固定保存的原分析</summary><p>发布 ${esc(stamp(original.issuedAt||original.generatedAt))}</p>${paragraphs?.length?paragraphs.map(p=>`<p>${esc(p)}</p>`).join(''):'<p>旧版本只保存了首选，没有保存原分析全文。</p>'}${((isStock?original.details:original.analysis?.details)||[]).map(d=>`<h3>${esc(d.title)}</h3><p>${esc(d.text)}</p>`).join('')}</details>`;
      body.innerHTML=content+conciseReport(data.review);
      message.textContent=data.review?'原分析与复盘分别保存。':isStock?'已收盘；未到期预测继续观察，管理员可生成详细复盘。':data.finished?'已完场，可对照原预测生成复盘。':'比赛尚未完场。';
      button.dataset.unavailable=(!isStock&&!data.finished)?'1':'';
    }catch(e){if(!signal?.aborted)message.textContent=e.name==='AbortError'?'整理用时较长，请稍后重试。':e.message;}
    finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);busy=false;if(!signal?.aborted){updateAllowed();if(button.dataset.unavailable==='1')button.disabled=true;}}
  }
  button.addEventListener('click',()=>load(true));target.addEventListener('stock-following-changed',updateAllowed);load();
  return {reload:load,updateAllowed};
}
