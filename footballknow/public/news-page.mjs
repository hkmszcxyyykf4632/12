import {LEAGUES} from './league.mjs';
import {main,esc,pageHeading,timeText,sourceLink} from './ui.mjs';
import {readLeagueSnapshot} from './competition-feed.mjs';

let saved=[],updated=0,pending=null;
const snapshots=new Map();
export function mergeNews(feeds){
  const seen=new Map();
  for(const {league,articles=[]} of feeds)for(const a of articles){
    if(!/^https:\/\//.test(a.url)||!Number.isFinite(Date.parse(a.publishedAt)))continue;
    const previous=seen.get(a.url);seen.set(a.url,{...a,leagues:[...new Set([...(previous?.leagues||[]),league])],teams:[...new Set([...(previous?.teams||[]),...(a.teamIds||[]).map(id=>league+':'+id)])]});
  }
  return [...seen.values()].sort((a,b)=>Date.parse(b.publishedAt)-Date.parse(a.publishedAt)||a.url.localeCompare(b.url));
}
async function load(){
  if(pending)return pending;if(Date.now()-updated<55000)return saved;
  pending=(async()=>{const result=await Promise.allSettled(Object.values(LEAGUES).map(async l=>{const n=await readLeagueSnapshot(l.id,'news');if(n.league!==l.id||!Array.isArray(n.articles))throw Error();return n;}));
    const good=result.filter(r=>r.status==='fulfilled').map(r=>r.value);if(good.length){for(const n of good)snapshots.set(n.league,n);saved=mergeNews([...snapshots.values()]);updated=Date.now();}return saved;})();
  try{return await pending;}finally{pending=null;}
}
function articleHtml(a){return `<article class="news-item"><div class="news-meta"><span>${a.leagues.map(l=>LEAGUES[l].name).join(' · ')}</span><time>${esc(timeText(a.publishedAt))}</time><span>${esc(a.category||'球队新闻')}</span></div><h3>${sourceLink(a.url,a.titleZh||a.title)}</h3><p class="small subtle">${esc(a.source)}${a.titleZh?' · 中文翻译':' · 原文标题'}</p>${a.titleZh?`<details><summary>英文原标题</summary><p lang="en">${esc(a.title)}</p></details>`:''}</article>`;}
export async function paintNewsPreview(target){
  const rows=await load();if(!target?.isConnected)return;
  target.innerHTML=rows.length?`<div class="news-grid">${rows.slice(0,6).map(articleHtml).join('')}</div>`:'<div class="empty">球队新闻正在同步。</div>';
}
export function renderNews(teamKey=''){
  let disposed=false,rows=[],teams=[],selected=teamKey.split(':')[0]||'all',team=teamKey,query='';
  if(!LEAGUES[selected])selected='all';
  main.innerHTML=`${pageHeading('球队新闻','五项赛事的最新消息 · 按发布时间从新到旧','<button class="button secondary" id="news-refresh">检查更新</button>')}<div class="toolbar match-filters"><label>赛事<select id="news-league"><option value="all">全部赛事</option>${Object.values(LEAGUES).map(l=>`<option value="${l.id}" ${l.id===selected?'selected':''}>${l.name}</option>`).join('')}</select></label><label>球队<select id="news-team"><option value="">全部球队</option></select></label><label>搜索<input type="search" id="news-search" placeholder="中文或原文关键词"></label></div><p id="news-status" class="note" role="status">正在读取新闻…</p><div id="news-list"></div>`;
  function draw(){if(disposed)return;const filtered=rows.filter(a=>(selected==='all'||a.leagues.includes(selected))&&(!team||a.teams.includes(team))&&[a.titleZh,a.title].join(' ').toLowerCase().includes(query.toLowerCase()));main.querySelector('#news-status').textContent=`${filtered.length} 条 · 每 60 秒检查 · 时间为媒体发布时间；中文为标题译文，全文见原文链接`;main.querySelector('#news-list').innerHTML=filtered.length?filtered.map(articleHtml).join(''):'<div class="empty">当前筛选范围暂未收录新闻，可切换其他球队或清除关键词。</div>';}
  function choices(){const selector=main.querySelector('#news-team');selector.innerHTML='<option value="">全部球队</option>'+teams.filter(t=>selected==='all'||t.league===selected).map(t=>`<option value="${t.key}" ${team===t.key?'selected':''}>${esc(t.cn)} · ${LEAGUES[t.league].name}</option>`).join('');}
  async function refresh(force=false){if(force)updated=0;rows=await load();draw();}
  main.querySelector('#news-league').addEventListener('change',e=>{selected=e.target.value;team='';choices();draw();});main.querySelector('#news-team').addEventListener('change',e=>{team=e.target.value;draw();});main.querySelector('#news-search').addEventListener('input',e=>{query=e.target.value;draw();});main.querySelector('#news-refresh').addEventListener('click',()=>refresh(true));
  Promise.allSettled(Object.values(LEAGUES).map(async l=>{const d=await readLeagueSnapshot(l.id,'data');return d.teams.map(t=>({...t,league:l.id,key:l.id+':'+t.id}));})).then(result=>{if(disposed)return;teams=result.filter(r=>r.status==='fulfilled').flatMap(r=>r.value);choices();});
  refresh();const timer=setInterval(()=>{if(!document.hidden)refresh();},60000);return()=>{disposed=true;clearInterval(timer);};
}
