import {main,esc} from './ui.mjs';
let pending;
const safeUrl=url=>/^https:\/\//.test(url||'')?esc(url):'#';
export function loadEditorial(){
 if(!pending)pending=fetch('./editorial-articles.json').then(r=>{if(!r.ok)throw Error('专题暂时无法载入');return r.json();}).catch(e=>{pending=null;throw e;});
 return pending;
}
function picture(a,lazy=true){return `<img src="./editorial/${esc(a.image)}" alt="${esc(a.imageAlt)}" width="960" height="640" ${lazy?'loading="lazy"':'fetchpriority="high"'} decoding="async">`;}
export function editorialCards(data){return `<div class="editorial-grid">${data.articles.map((a,i)=>`<article class="editorial-card ${i===0?'editorial-featured':''}"><a class="editorial-image" href="#/insights/${esc(a.id)}" tabindex="-1" aria-hidden="true">${picture(a,i>0)}<span>资料图片</span></a><div class="editorial-card-body"><p class="editorial-category">${esc(a.category)} <span>研究 · ${esc(data.updatedAt)}</span></p><h3><a href="#/insights/${esc(a.id)}">${esc(a.title)}</a></h3><p>${esc(a.dek)}</p><a class="editorial-read" href="#/insights/${esc(a.id)}">阅读分析 <span aria-hidden="true">↗</span></a></div></article>`).join('')}</div>`;}
export async function paintEditorial(target){
 if(!target)return;
 try{const data=await loadEditorial();if(target.isConnected)target.innerHTML=editorialCards(data);}
 catch(e){if(target.isConnected){target.innerHTML=`<p class="notice">${esc(e.message)} <button class="button secondary" data-retry>重试</button></p>`;target.querySelector('[data-retry]').onclick=()=>paintEditorial(target);}}
}
export function renderEditorial(id){
 let disposed=false;main.innerHTML='<div class="loading" role="status">正在读取专题分析…</div>';
 loadEditorial().then(data=>{
  if(disposed)return;
  if(!id){main.innerHTML=`<header class="editorial-heading"><span class="eyebrow">峰弈研究</span><h1>看清变化，理解原因</h1><p>从可核对的事实出发，讨论影响、情景与会改变判断的证据。</p></header>${editorialCards(data)}`;return;}
  const a=data.articles.find(x=>x.id===id);if(!a){main.innerHTML='<div class="empty">没有找到这篇分析。<a href="#/insights">返回专题</a></div>';return;}
  main.innerHTML=`<article class="editorial-article"><a class="editorial-back" href="#/insights">← 全部专题分析</a><header><p class="editorial-category">${esc(a.category)}</p><h1>${esc(a.title)}</h1><p class="editorial-dek">${esc(a.dek)}</p><p class="note">${esc(data.author)} · 发布及资料核对：${esc(data.updatedAt)}</p></header><figure>${picture(a,false)}<figcaption>${esc(a.caption)} <a href="${safeUrl(a.imageSource)}" target="_blank" rel="noopener noreferrer">${esc(a.credit)} ↗</a></figcaption></figure><section class="editorial-view"><h2>峰弈观点</h2><p>${esc(a.view)}</p></section><section><h2>已核对的事实</h2>${a.facts.map(f=>`<p>${esc(f.text)} <a class="source-link" href="${safeUrl(a.sources[f.source]?.url)}" target="_blank" rel="noopener noreferrer">[${f.source+1}]</a></p>`).join('')}</section><section><h2>我们的分析</h2>${a.sections.map(s=>`<h3>${esc(s.title)}</h3><p>${esc(s.text)}</p>`).join('')}</section><section><h2>接下来可能怎样演变</h2><p class="note">以下是条件情景，不是已经发生的事实，也不是确定的价格预测。</p><div class="editorial-scenarios">${a.scenarios.map((s,i)=>`<div><span>0${i+1}</span><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p></div>`).join('')}</div></section><section><h2>持续跟踪与反证</h2><ul>${a.watch.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></section><details class="editorial-sources"><summary>资料来源与阅读说明</summary><ol>${a.sources.map(s=>`<li><a href="${safeUrl(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.label)} ↗</a></li>`).join('')}</ol><p>本文为截至发布日的研究观点，不随行情自动改写。来源提供事实背景，因果解释与情景判断由本站整理；不构成针对个人的买卖建议。后续事实可能改变判断。</p></details><a class="button secondary" href="#/insights">返回全部分析</a></article>`;
 }).catch(e=>{if(!disposed)main.innerHTML=`<div class="empty">${esc(e.message)} <a href="#/">返回首页</a></div>`;});
 return()=>{disposed=true;};
}
