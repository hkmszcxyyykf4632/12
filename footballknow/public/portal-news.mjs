import {main,esc,pageHeading} from './ui.mjs';

const categories={finance:'财经',football:'足球',racing:'赛马'};
let cached=null,checked=0,pending;
const time=x=>new Date(x).toLocaleString('zh-CN',{timeZone:'Asia/Hong_Kong',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});
export function chineseArticles(data){
  return Object.entries(data.categories||{}).flatMap(([category,feed])=>(feed.articles||[]).map(a=>({...a,category})))
    .filter(a=>categories[a.category]&&/^https:\/\//.test(a.url)&&/[\u3400-\u9fff]/.test(a.titleZh||a.title)&&Number.isFinite(Date.parse(a.publishedAt)))
    .sort((a,b)=>Date.parse(b.publishedAt)-Date.parse(a.publishedAt)||a.url.localeCompare(b.url));
}
async function load(){
  if(cached&&Date.now()-checked<55000)return cached;
  if(!pending)pending=fetch('./portal-news.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('新闻正在同步。');return r.json();}).then(d=>{cached=d;checked=Date.now();return d;}).finally(()=>pending=null);
  return pending;
}
const meta=a=>`${esc(a.source)} · ${time(a.publishedAt)}${a.translated?' · 中文译文':''}`;
const image=a=>a.imageUrl?`<figure class="news-photo"><img src="${esc(a.imageUrl)}" alt="" loading="lazy" decoding="async"><figcaption>图片来源：${esc(a.source)}</figcaption></figure>`:'';
const bindImages=root=>root.querySelectorAll('.news-photo img').forEach(img=>img.addEventListener('error',()=>img.closest('figure').remove(),{once:true}));
const link=a=>`href="${esc(a.url)}" target="_blank" rel="noopener noreferrer"`;
export async function paintPortalNews(target,full=false){
  if(!target)return;
  try{const data=await load();if(!target.isConnected)return;
    const rows=chineseArticles(data),selected=target.dataset.category||'all';
    target.innerHTML=`${!full?`<div class="portal-feature-grid">${Object.keys(categories).map(category=>{const a=rows.find(r=>r.category===category&&r.imageUrl)||rows.find(r=>r.category===category);return a?`<article class="portal-feature feature-${category}"><div class="portal-feature-top"><span>${categories[category]}焦点</span><span>${time(a.publishedAt)}</span></div>${image(a)}<h3><a ${link(a)}>${esc(a.titleZh||a.title)}</a></h3><div class="portal-feature-source">${esc(a.source)}<span aria-hidden="true">↗</span></div></article>`:`<article class="portal-feature feature-${category}"><span>${categories[category]}</span><h3>正在整理最新资讯</h3></article>`;}).join('')}</div>`:''}<div class="portal-news-toolbar"><div class="portal-tabs" role="group" aria-label="新闻分类">${[['all','全部资讯'],...Object.entries(categories)].map(([id,name])=>`<button data-news-category="${id}" aria-pressed="${selected===id}" class="${selected===id?'active':''}">${name}</button>`).join('')}</div><span>每 5 分钟检查 · ${time(data.updatedAt)}</span></div><div class="portal-news-stream"></div><p class="note">标题与发布时间来自原发布媒体。英文来源使用已完成的中文译文，点击标题可阅读原文。</p>`;
    const draw=category=>{target.dataset.category=category;const filtered=rows.filter(a=>category==='all'||a.category===category).slice(0,full?90:12);
      target.querySelector('.portal-news-stream').innerHTML=filtered.length?filtered.map(a=>`<article class="portal-news-row"><span class="news-topic topic-${a.category}">${categories[a.category]}</span><div><h3><a ${link(a)}>${esc(a.titleZh||a.title)}</a></h3><p>${meta(a)}</p></div><span class="news-open" aria-hidden="true">↗</span></article>`).join(''):'<div class="empty">这个分类正在等待来源更新。</div>';
      target.querySelectorAll('[data-news-category]').forEach(b=>{b.classList.toggle('active',b.dataset.newsCategory===category);b.setAttribute('aria-pressed',String(b.dataset.newsCategory===category));});};
    target.querySelectorAll('[data-news-category]').forEach(b=>b.onclick=()=>draw(b.dataset.newsCategory));draw(selected);bindImages(target);
  }catch(error){if(target.isConnected)target.innerHTML=`<div class="empty">${esc(error.message)}</div>`;}
}
export function renderPortalNews(initial='all'){
  main.innerHTML=pageHeading('即时资讯','中文财经、足球与赛马新闻，按发布时间从新到旧。','<a class="button secondary" href="#/">回到首页</a>')+'<div id="all-portal-news" class="loading">正在读取资讯…</div>';
  const target=main.querySelector('#all-portal-news');target.dataset.category=categories[initial]?initial:'all';
  paintPortalNews(target,true);const timer=setInterval(()=>{if(!document.hidden)paintPortalNews(target,true);},60000);return()=>clearInterval(timer);
}
