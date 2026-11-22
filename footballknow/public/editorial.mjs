import {main,esc} from './ui.mjs';
let pending;
const safeUrl=url=>/^https:\/\//.test(url||'')?esc(url):'#';
export function loadEditorial(){
 if(!pending)pending=fetch('./editorial-articles.json').then(r=>{if(!r.ok)throw Error('专题暂时无法载入');return r.json();}).catch(e=>{pending=null;throw e;});
 return pending;
}
function picture(a,lazy=true){return `<img src="./editorial/${esc(a.image)}" alt="${esc(a.imageAlt)}" width="960" height="640" ${lazy?'loading="lazy"':'fetchpriority="high"'} decoding="async">`;}
function sources(a){return `<details class="editorial-sources"><summary>查看来源</summary><ul>${a.sources.map(s=>`<li><a href="${safeUrl(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.label)} ↗</a></li>`).join('')}</ul><p>${esc(a.caption)} <a href="${safeUrl(a.imageSource)}" target="_blank" rel="noopener noreferrer">${esc(a.credit)} ↗</a></p></details>`;}
export function editorialCards(data){return `<div class="editorial-list">${data.articles.map((a,i)=>`<article class="editorial-card"><a class="editorial-image" href="#/insights/${esc(a.id)}" tabindex="-1" aria-hidden="true">${picture(a,i>0)}<span>资料图片</span></a><div class="editorial-card-body"><h3><a href="#/insights/${esc(a.id)}">${esc(a.title)}</a></h3><p class="editorial-analysis">${esc(a.analysis)}</p>${sources(a)}</div></article>`).join('')}</div>`;}
export async function paintEditorial(target){
 if(!target)return;
 try{const data=await loadEditorial();if(target.isConnected)target.innerHTML=editorialCards(data);}
 catch(e){if(target.isConnected){target.innerHTML=`<p class="notice">${esc(e.message)} <button class="button secondary" data-retry>重试</button></p>`;target.querySelector('[data-retry]').onclick=()=>paintEditorial(target);}}
}
export function renderEditorial(id){
 let disposed=false;main.innerHTML='<div class="loading" role="status">正在读取专题分析…</div>';
 loadEditorial().then(data=>{
  if(disposed)return;
  if(!id){main.innerHTML=`<header class="editorial-heading"><h1>峰弈专题分析</h1><p class="note">${esc(data.author)} · ${esc(data.updatedAt)}</p></header>${editorialCards(data)}`;return;}
  const a=data.articles.find(x=>x.id===id);if(!a){main.innerHTML='<div class="empty">没有找到这篇分析。<a href="#/insights">返回专题</a></div>';return;}
  main.innerHTML=`<article class="editorial-article"><a class="editorial-back" href="#/insights">← 全部专题分析</a><header><h1>${esc(a.title)}</h1><p class="note">${esc(data.author)} · ${esc(data.updatedAt)}</p></header><figure>${picture(a,false)}<figcaption>${esc(a.caption)} <a href="${safeUrl(a.imageSource)}" target="_blank" rel="noopener noreferrer">${esc(a.credit)} ↗</a></figcaption></figure><p class="editorial-analysis">${esc(a.analysis)}</p>${sources(a)}</article>`;
 }).catch(e=>{if(!disposed)main.innerHTML=`<div class="empty">${esc(e.message)} <a href="#/">返回首页</a></div>`;});
 return()=>{disposed=true;};
}
