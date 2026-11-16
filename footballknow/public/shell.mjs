// Application frame: theme, the 60-second sync indicator, navigation drawer and the search palette.
import {data,syncState,SYNC_MS,liveStatus} from './repository.mjs';
import {league} from './league.mjs';
import {esc,cn,timeText} from './ui.mjs';
import {localized} from './football-components.mjs';

const RING=94.25;
const $=selector=>document.querySelector(selector);

export function bindTheme() {
  $('#theme-toggle')?.addEventListener('click',()=>{
    const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
    document.documentElement.dataset.theme=next;
    try {localStorage.setItem('footballknow-theme',next);}catch {/* The choice still applies to this visit. */}
  });
}

export function bindDrawer() {
  const sidebar=$('#sidebar'),scrim=$('#scrim'),toggle=$('#nav-toggle');
  if(!sidebar||!scrim||!toggle)return ()=>{};
  const set=open=>{sidebar.classList.toggle('open',open);scrim.hidden=!open;toggle.setAttribute('aria-expanded',String(open));};
  toggle.addEventListener('click',()=>set(!sidebar.classList.contains('open')));
  scrim.addEventListener('click',()=>set(false));
  sidebar.addEventListener('click',event=>{if(event.target.closest('a'))set(false);});
  return ()=>set(false);
}

export function paintSync() {
  const pill=$('#sync-pill');if(!pill)return;
  const status=data?liveStatus():null;
  const remaining=Math.max(0,Math.ceil((syncState.nextAt-Date.now())/1000));
  $('#sync-ring').style.strokeDashoffset=String(RING*(1-Math.min(1,remaining*1000/SYNC_MS)));
  $('#sync-countdown').textContent=syncState.busy?'正在同步…':syncState.nextAt?`${remaining} 秒后同步`:'每 60 秒同步';
  pill.classList.toggle('busy',syncState.busy);
  pill.classList.toggle('delayed',Boolean(status&&(status.stale||status.failed)));
  const area=$('#live-status');
  area.className=`sync-banner ${status&&(status.stale||status.failed)?'delayed':''}`;
  area.textContent=status?`${status.text} · 最近成功 ${status.stamp}`:'正在检查更新时间…';
}

/** Ticks the countdown once a second; returns a function that stops it. */
export function startSyncIndicator(syncNow) {
  const timer=setInterval(paintSync,1000);
  const click=()=>syncNow();
  $('#sync-pill')?.addEventListener('click',click);
  paintSync();
  return ()=>{clearInterval(timer);$('#sync-pill')?.removeEventListener('click',click);};
}

const PAGES=[['总览','#/'],['比赛中心','#/matches'],['数据榜单','#/rankings'],['球队列表','#/teams'],['球队对比','#/compare'],['我的关注','#/following'],
  ['模拟投注','#/simulator'],['我的记录','#/records'],['同步监控','#/status'],['数据质量','#/quality'],['数据说明','#/sources'],['管理后台','#/admin']];

/** Everything the palette can open, rebuilt when it is shown so it reflects the latest snapshot. */
export function searchIndex() {
  const rows=PAGES.map(([label,href])=>({kind:'页面',label,detail:'',href,keys:label}));
  if(!data)return rows;
  for(const t of data.teams)rows.push({kind:'球队',label:t.cn,detail:t.name,href:`#/team/${t.id}`,keys:[t.cn,t.name,t.short].join(' ')});
  for(const p of data.players) {
    const name=localized(p),club=data.teams.find(t=>t.id===p.team);
    const original=p.known_name||[p.first_name,p.second_name].filter(Boolean).join(' ')||p.web_name;
    rows.push({kind:'球员',label:name?.mandarin||p.web_name,detail:[name?.cantonese&&name.cantonese!==name.mandarin?`粤 ${name.cantonese}`:'',original,club?.cn].filter(Boolean).join(' · '),
      href:`#/player/${p.id}`,keys:[name?.mandarin,name?.cantonese,p.web_name,original].join(' ')});
  }
  const now=Date.now();
  data.matches.filter(m=>m.competition===league.name&&m.season===data.season&&(m.started&&!m.finished||m.kickoff&&Date.parse(m.kickoff)>now))
    .sort((a,b)=>(a.kickoff||'').localeCompare(b.kickoff||'')).slice(0,60)
    .forEach(m=>rows.push({kind:'比赛',label:`${cn(m.home)} vs ${cn(m.away)}`,detail:timeText(m.kickoff),href:`#/match/${encodeURIComponent(m.id)}`,keys:[cn(m.home),cn(m.away),m.home,m.away].join(' ')}));
  return rows;
}

export function searchRows(index,query,limit=12) {
  const words=query.toLowerCase().split(/\s+/).filter(Boolean);
  if(!words.length)return index.slice(0,limit);
  return index.filter(row=>{const keys=row.keys.toLowerCase();return words.every(word=>keys.includes(word));})
    .sort((a,b)=>Number(b.keys.toLowerCase().startsWith(words[0]))-Number(a.keys.toLowerCase().startsWith(words[0]))).slice(0,limit);
}

export function bindPalette() {
  const palette=$('#palette'),input=$('#palette-input'),list=$('#palette-results'),trigger=$('#open-search');
  if(!palette||!input||!list)return;
  let index=[],rows=[],selected=0,returnFocus=null;
  const paint=()=>{
    rows=searchRows(index,input.value);selected=Math.min(selected,Math.max(0,rows.length-1));
    list.innerHTML=rows.length?rows.map((row,i)=>`<li role="option" data-index="${i}" aria-selected="${i===selected}"><em>${esc(row.kind)}</em><span>${esc(row.label)}</span><small>${esc(row.detail)}</small></li>`).join('')
      :'<li class="palette-empty">没有找到。试试球队英文名、球员原名或页面名称。</li>';
    list.querySelector('[aria-selected="true"]')?.scrollIntoView?.({block:'nearest'});
  };
  const close=()=>{if(palette.hidden)return;palette.hidden=true;returnFocus?.focus?.();};
  const open=()=>{returnFocus=document.activeElement;index=searchIndex();input.value='';selected=0;palette.hidden=false;paint();input.focus();};
  const go=row=>{if(!row)return;close();location.hash=row.href;};
  trigger?.addEventListener('click',open);
  input.addEventListener('input',()=>{selected=0;paint();});
  palette.addEventListener('click',event=>{
    const item=event.target.closest('li[data-index]');
    if(item)go(rows[Number(item.dataset.index)]);else if(event.target===palette)close();
  });
  document.addEventListener('keydown',event=>{
    const typing=/^(INPUT|TEXTAREA|SELECT)$/.test(event.target?.tagName||'');
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();palette.hidden?open():close();return;}
    if(palette.hidden){if(event.key==='/'&&!typing){event.preventDefault();open();}return;}
    if(event.key==='Escape'){event.preventDefault();close();}
    else if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();if(rows.length){selected=(selected+(event.key==='ArrowDown'?1:rows.length-1))%rows.length;paint();}}
    else if(event.key==='Enter'){event.preventDefault();go(rows[selected]);}
  });
}
