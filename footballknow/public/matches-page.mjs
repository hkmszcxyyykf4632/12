import {data,findMatch} from './repository.mjs';
import {main,esc,cn,team,monogram,pageHeading,timeText,sourceLink,matchTable,toast} from './ui.mjs';
import {league} from './league.mjs';
import {localized,timestamp} from './football-components.mjs';
import {followKey,loadFollowing,headToHead} from './rankings-core.mjs';
import {impliedProbabilities,matchDetailMatches} from './insights.mjs';
import {statsAndEvents,matchFacts,oddsExtras} from './match-extras.mjs';

export const matchHref=id=>`#/match/${encodeURIComponent(id)}`;
const following=()=>loadFollowing(localStorage,league.id,data.teams);
export const followButton=t=>`<button class="button secondary compact" data-follow="${t.id}" aria-pressed="${following().includes(t.id)}">${following().includes(t.id)?'已关注':'关注球队'}</button>`;
export function toggleFollow(id){
 const selected=following();const next=selected.includes(id)?selected.filter(v=>v!==id):[...selected,id];
 try{localStorage.setItem(followKey(league.id),JSON.stringify(next));document.querySelectorAll(`[data-follow="${id}"]`).forEach(b=>{b.textContent=next.includes(id)?'已关注':'关注球队';b.setAttribute('aria-pressed',String(next.includes(id)));});toast(next.includes(id)?'已关注，可在“我的关注”查看赛程。':'已取消关注。');return true;}catch{toast('浏览器暂时无法保存关注。');return false;}
}
function clubLink(name){const t=team(name);return t?`<a class="club-inline" href="#/team/${t.id}">${monogram(t,'tiny')}<span>${esc(t.cn)}</span></a>`:esc(name);}
function matchRow(m){return `<div class="match-list-row"><div class="match-meta">${esc(timeText(m.kickoff||m.date))}<span>${esc(m.competition)}${m.phase?' · '+esc(m.phase):''}</span></div><div class="match-pair">${clubLink(m.home)}<a class="match-result ${m.started&&!m.finished?'in-play':''}" href="${matchHref(m.id)}">${m.started||m.finished?`${m.homeGoals??'—'} : ${m.awayGoals??'—'}`:'VS'}<small>${m.finished?'已完赛':m.started?'比赛中':'未开赛'}</small></a>${clubLink(m.away)}</div><a class="button quiet compact" href="${matchHref(m.id)}">${m.finished?'阵容与数据':'比赛详情'} →</a></div>`;}
export function renderMatches(followOnly=false){
 let status=followOnly?'all':'upcoming',season=data.season,teamId='',date='',count=30;
 const seasons=[...new Set(data.matches.filter(m=>m.competition===league.name).map(m=>m.season))].sort().reverse();
 main.innerHTML=`${pageHeading(followOnly?'我的关注':`${league.name} · 比赛中心`,followOnly?'本浏览器保存的关注球队与比赛。':'按赛程、球队和日期查找比赛，进入详情查看阵容与技术统计。')}${followOnly?`<section class="follow-clubs" aria-label="选择关注球队">${data.teams.map(t=>`<div>${clubLink(t.name)}${followButton(t)}</div>`).join('')}</section>`:''}<div class="toolbar match-filters"><label>状态<select id="match-status">${Object.entries({upcoming:'即将开赛',live:'正在进行',finished:'已完赛',all:'全部'}).map(([v,l])=>`<option value="${v}" ${v===status?'selected':''}>${l}</option>`).join('')}</select></label><label>赛季<select id="match-season">${seasons.map(s=>`<option ${s===season?'selected':''}>${esc(s)}</option>`).join('')}</select></label><label>球队<select id="match-team"><option value="">全部球队</option>${data.teams.map(t=>`<option value="${t.id}">${esc(t.cn)}</option>`).join('')}</select></label><label>比赛日期<input id="match-date" type="date"></label><button class="button quiet compact" id="match-clear">清除筛选</button></div><div id="match-count" class="note" role="status"></div><div id="match-list"></div><button class="button secondary" id="match-more">显示更多比赛</button>`;
 function update(){
  if(!main.querySelector('#match-list'))return;
  const ids=following(),selectedTeam=data.teams.find(t=>String(t.id)===teamId)?.name;
  let rows=data.matches.filter(m=>m.competition===league.name&&m.season===season&&(!selectedTeam||[m.home,m.away].includes(selectedTeam))&&(!date||m.date===date)&&(!followOnly||data.teams.some(t=>ids.includes(t.id)&&[m.home,m.away].includes(t.name))));
  rows=rows.filter(m=>status==='all'||status==='finished'&&m.finished||status==='live'&&m.started&&!m.finished||status==='upcoming'&&!m.finished&&!m.started);
  rows.sort((a,b)=>status==='upcoming'?(a.kickoff||a.date).localeCompare(b.kickoff||b.date):(b.kickoff||b.date).localeCompare(a.kickoff||a.date));
  main.querySelector('#match-count').textContent=`${rows.length} 场 · 时间按本地时区显示 · 比赛日期筛选采用来源日期`;
  main.querySelector('#match-list').innerHTML=rows.length?rows.slice(0,count).map(matchRow).join(''):`<div class="empty">${followOnly&&!ids.length?'先关注上方球队，就能集中查看它们的比赛。':status==='live'?'目前没有正在进行的比赛。':'这个范围内没有比赛，请调整筛选。'}</div>`;
  main.querySelector('#match-more').hidden=count>=rows.length;
 }
 for(const [id,set] of [['match-status',v=>status=v],['match-season',v=>season=v],['match-team',v=>teamId=v],['match-date',v=>date=v]])main.querySelector('#'+id).addEventListener('change',e=>{set(e.target.value);count=30;update();});
 main.querySelector('#match-more').addEventListener('click',()=>{count+=30;update();});
 main.querySelector('#match-clear').addEventListener('click',()=>{teamId='';date='';main.querySelector('#match-team').value='';main.querySelector('#match-date').value='';update();});
 main.querySelectorAll('[data-follow]').forEach(b=>b.addEventListener('click',()=>queueMicrotask(update)));
 update();return update;
}

function personName(p){const n=p.playerCode?localized({code:p.playerCode}):null;return n?`<strong>${esc(n.mandarin)}</strong><span class="small subtle">粤 ${esc(n.cantonese)}${n.status==='draft'?' · 暂译':''}</span><span class="small subtle">${esc(p.name)}</span>`:`<strong>${esc(p.name)}</strong>`;}
function lineupHtml(side,detail){
 if(!side)return '<div class="empty">来源暂未公布这一方的名单。</div>';
 const group=p=>p.position==='G'?'门将':/M/.test(p.position)?'中场':/D|^(LB|RB|SW)$/.test(p.position)?'后卫':/F/.test(p.position)?'前锋':'位置未提供';
 const groups=['门将','后卫','中场','前锋','位置未提供'].map(label=>[label,p=>group(p)===label]).filter(([label,test])=>label!=='位置未提供'||side.players.some(p=>p.starter&&test(p)));
 return `<section class="lineup-team"><div class="section-head"><h3>${esc(cn(side.name))}</h3><span class="tag">${esc(side.formation||'阵型未提供')}</span></div><div class="lineup-pitch" aria-label="首发按位置分组示意">${groups.map(([label,test])=>`<div class="pitch-line"><span class="position-label">${label}</span><div>${side.players.filter(p=>p.starter&&test(p)).map(p=>`<div class="pitch-player"><b>${esc(p.shirt||'—')}</b>${personName(p)}</div>`).join('')}</div></div>`).join('')}</div><p class="small subtle">位置分组示意，非球员实际跑位图。</p><div class="table-wrap"><table class="lineup-table"><thead><tr><th>球员</th><th>出场</th><th>分钟</th><th>进球 / 助攻</th></tr></thead><tbody>${side.players.map(p=>`<tr><td><div class="lineup-name"><span class="shirt-number">${esc(p.shirt)}</span><div>${personName(p)}</div></div></td><td>${p.starter?'首发':p.played?'替补上场':'替补未出场'}${p.entered?`<div class="small subtle">${esc(p.entered)} 上</div>`:''}${p.left?`<div class="small subtle">${esc(p.left)} 下 / 离场</div>`:''}${p.yellowCards?`<span class="card-yellow">黄 ${p.yellowCards}</span>`:''}${p.redCards?`<span class="card-red">红 ${p.redCards}</span>`:''}</td><td>${p.minutes==null?'—':`${p.minutesEstimated?'约 ':''}${p.minutes}`}</td><td>${p.goals??'—'} / ${p.assists??'—'}</td></tr>`).join('')}</tbody></table></div></section>`;
}
function detailHtml(detail){
 const labels={possessionPct:'控球率 %',totalShots:'射门',shotsOnTarget:'射正',wonCorners:'角球',foulsCommitted:'犯规',offsides:'越位',yellowCards:'黄牌',redCards:'红牌',saves:'扑救',accuratePasses:'成功传球',totalPasses:'传球',interceptions:'拦截',totalTackles:'抢断'};
 const stats=Object.fromEntries((detail.statistics||[]).map(s=>[s.side,s.values]));
 const people=Object.values(detail.lineups||{}).flatMap(s=>s.players||[]);
 const playerText=p=>{const known=people.find(x=>x.espnId===p.espnId);const n=known?.playerCode?localized({code:known.playerCode}):null;return esc(n?.mandarin||p.name);};
 return `${detail.status!=='available'?`<div class="notice">${esc(detail.message||'来源尚未提供完整首发，已提供的资料显示如下。')}</div>`:''}<div class="section-head"><h2>出场阵容</h2><span class="small subtle">${esc(detail.duration||90)} 分钟比赛${detail.duration===120?' · 含加时':''}</span></div><div class="lineups-grid">${['home','away'].map(s=>lineupHtml(detail.lineups?.[s],detail)).join('')}</div><p class="note">${esc(detail.minutesBasis||'')} ${sourceLink(detail.source,'阵容来源')} · 最近取得 ${timestamp(detail.updatedAt)}${detail.refreshFailed?' · 本次更新未成功':''}</p>
 ${statsAndEvents({...detail,home:cn(detail.home),away:cn(detail.away)})}`;
}
export function renderMatch(encodedId){
 let disposed=false,controller=null;let id;try{id=decodeURIComponent(encodedId);}catch{id='';}const m=findMatch(id);
 if(!m){main.innerHTML='<div class="empty">没有找到这场比赛。<a href="#/matches">返回比赛中心</a></div>';return()=>{};}
 const h2h=headToHead(data.matches,m.home,m.away,m.date);
 main.innerHTML=`${pageHeading(`${esc(cn(m.home))} · ${esc(cn(m.away))}`,`${esc(m.competition)} ${esc(m.season)} · ${esc(timeText(m.kickoff||m.date))}`,`<a class="button secondary" href="#/matches">比赛中心</a>`)}<section class="match-scoreboard"><div>${clubLink(m.home)}${team(m.home)?followButton(team(m.home)):''}</div><div class="match-score-large">${m.started||m.finished?`${m.homeGoals??'—'} : ${m.awayGoals??'—'}`:'VS'}<span>${m.finished?'已完赛 · 90分钟含补时':m.started?'比赛进行中':'尚未开赛'}</span></div><div>${clubLink(m.away)}${team(m.away)?followButton(team(m.away)):''}</div></section><div class="toolbar">${[m.home,m.away].filter(n=>team(n)).map(n=>`<a class="button secondary compact" href="#/analysis/${team(n).id}">${esc(cn(n))}下一场分析</a>`).join('')}<button class="button quiet compact" data-bet="${esc(m.id)}">录入赔率 / 模拟</button></div><div class="tabs"><a href="#match-lineups">阵容与数据</a><a href="#match-h2h">交锋记录</a><a href="#match-odds">赔率来源</a></div><section id="match-lineups"><div id="match-detail-body" class="loading">正在取得本场阵容与技术统计…</div><button class="button secondary compact" id="detail-refresh">重新检查本场资料</button></section><section id="match-h2h"><div class="section-head"><h2>此前交锋</h2><span class="small subtle">已收录最近 ${h2h.length} 场</span></div>${matchTable(h2h)}</section><section id="match-odds"><div class="section-head"><h2>本场赔率</h2><a class="button quiet" href="#/sources">来源检查 →</a></div>${m.odds?.length?`<div class="table-wrap"><table><thead><tr><th>来源 / 时点</th><th>主胜</th><th>平局</th><th>客胜</th><th>隐含概率 主 / 平 / 客</th><th>报价水位</th></tr></thead><tbody>${m.odds.map(o=>{const p=impliedProbabilities(o);return `<tr><td>${esc(o.label)}${o.source?`<div>${sourceLink(o.source)}</div>`:''}${o.fetchedAt?`<div class="small subtle">${timestamp(o.fetchedAt)}</div>`:''}</td><td>${o.H}</td><td>${o.D}</td><td>${o.A}</td><td>${p?['H','D','A'].map(k=>`${(p[k]*100).toFixed(1)}%`).join(' / '):'—'}</td><td>${p?`${(p.margin*100).toFixed(1)}%`:'—'}</td></tr>`;}).join('')}</tbody></table></div><p class="note">隐含概率由三项赔率换算并按比例扣除报价水位；交易所报价未扣佣金。</p>`:'<p class="empty">本场尚无可核对的三项赔率，可录入已有赔率。</p>'}</section>`;
 main.querySelector('.match-scoreboard').insertAdjacentHTML('afterend',`<div id="match-facts">${matchFacts(m)}</div>`);
 main.querySelector('#match-odds').insertAdjacentHTML('beforeend',`<div id="match-odds-extra">${oddsExtras(m)}</div>`);
 main.querySelector('#match-facts+.toolbar')?.insertAdjacentHTML('beforeend','<button class="button secondary compact" type="button" data-share>分享链接</button>');
 main.querySelectorAll('.tabs a').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();main.querySelector(a.getAttribute('href'))?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}));
 async function load(){controller?.abort();controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),70000),b=main.querySelector('#detail-refresh');b.disabled=true;try{const r=await fetch(`/api/match?league=${league.id}&match_id=${encodeURIComponent(m.id)}`,{signal:controller.signal,cache:'no-store'});if(!r.ok)throw new Error('本场资料暂时无法取得，请稍后重新检查。');const detail=await r.json();if(!matchDetailMatches(detail,m,league.id))throw new Error('本场阵容与比赛身份不一致，请重新检查资料。');if(!disposed){const target=main.querySelector('#match-detail-body');target.classList.remove('loading');target.innerHTML=detailHtml(detail);}}catch(e){if(!disposed)main.querySelector('#match-detail-body').innerHTML=`<div class="notice">${esc(e.name==='AbortError'?'读取本场资料用时较长，请稍后重试。':e.message)}</div>`;}finally{clearTimeout(timeout);if(!disposed)b.disabled=false;}}
 main.querySelector('#detail-refresh').addEventListener('click',load);load();
 const timer=setInterval(()=>{if(disposed||document.hidden)return;const current=findMatch(id);if(current){main.querySelector('.match-score-large').innerHTML=`${current.started||current.finished?`${current.homeGoals??'—'} : ${current.awayGoals??'—'}`:'VS'}<span>${current.finished?'已完赛 · 90分钟含补时':current.started?'比赛进行中':'尚未开赛'}</span>`;}const fresh=findMatch(id)||m;main.querySelector('#match-facts').innerHTML=matchFacts(fresh);main.querySelector('#match-odds-extra').innerHTML=oddsExtras(fresh);if(!main.querySelector('#detail-refresh').disabled)load();},60000);
 return()=>{disposed=true;clearInterval(timer);controller?.abort();};
}
