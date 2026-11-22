import {esc} from './ui.mjs';
import {portrait} from './portraits.mjs';

export const val=x=>x==null||x===''?'—':esc(String(x));
export const stamp=x=>x?new Date(x).toLocaleString('zh-CN',{timeZone:'Asia/Hong_Kong',hour12:false}):'—';
export const clock=x=>x?new Date(x).toLocaleTimeString('zh-CN',{timeZone:'Asia/Hong_Kong',hour:'2-digit',minute:'2-digit',hour12:false}):'待公布';
export const classes=['全部班次','第一班','第二班','第三班','第四班','第五班','未评分'];
export const classText=h=>h.classGroup?classes[h.classGroup]:'未评分';
export const table=(headers,rows,cls='')=>rows.length?`<div class="table-wrap ${cls}"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(c=>`<tr>${c.map(v=>`<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<div class="empty">没有符合条件的记录。</div>';
export const horseLink=(h,photo=false)=>`<a class="horse-identity" href="#/horse/${esc(h.id)}">${photo?portrait(h.photo?.thumbnail||h.photo,h.name,'horse'):''}<span><strong>${esc(h.name||h.brand)}</strong><small>${esc(h.brand||h.id?.split('_').at(-1)||'')}</small></span></a>`;
export const placeBadge=h=>h.withdrawn?'<span class="race-status">退出</span>':h.place?`<span class="placing place-${h.place<=3?h.place:'other'}">${esc(h.position||h.place)}</span>`:'<span class="muted">待赛</span>';
export const racingNav=active=>`<nav class="racing-subnav" aria-label="赛马导航">${[['racing','赛马日'],['racing-statistics','分析统计'],['racing-paper','模拟投注'],['horses','马匹资料'],['bloodlines','著名血统'],['racing-rankings','骑练排行榜']].map(([id,name])=>`<a href="#/${id}" ${active===id?'aria-current="page"':''}>${name}</a>`).join('')}</nav>`;
export async function racingJson(path,signal){const r=await fetch('./racing/'+path,{cache:'no-cache',signal});if(!r.ok)throw Error('资料正在整理，请稍后重新读取。');return r.json();}
export function personId(p,kind){if(p?.id)return p.id;try{return new URL(p?.source).searchParams.get(kind+'id')||p.name;}catch{return p?.name||'待公布';}}
export function groupRunners(races,kind){
  const groups=new Map();
  for(const race of [...races].sort((a,b)=>a.raceNo-b.raceNo))for(const horse of race.entries||[]){
    const p=horse[kind]||{},id=personId(p,kind);
    if(!groups.has(id))groups.set(id,{id,name:p.name||'待公布',runs:[],wins:0,top3:0});
    const group=groups.get(id);group.runs.push({race,horse});
    if(!horse.withdrawn&&race.resultOfficial){group.wins+=Number(horse.place===1);group.top3+=Number(horse.place>=1&&horse.place<=3);}
  }
  return [...groups.values()].sort((a,b)=>b.wins-a.wins||b.top3-a.top3||b.runs.length-a.runs.length||a.name.localeCompare(b.name,'zh-HK'));
}
