import {main,esc,pageHeading,dateText,sourceLink} from './ui.mjs';
import {LEAGUES} from './league.mjs';
import {mergeMatches} from './live-core.mjs';
import {readLeagueSnapshot,competitionFeeds} from './competition-feed.mjs';
import {managerFixtures,uniqueCoachFixtures} from './coach-fixtures.mjs';
const STORE='footballknow-coach-following';
function followings(){try{return new Set(JSON.parse(localStorage.getItem(STORE)||'[]'));}catch{return new Set();}}
export function managerComparison(matches,team,date,nextDate=null){
  const rows=uniqueCoachFixtures(matches).filter(m=>m.finished&&[m.home,m.away].includes(team)&&Number.isInteger(m.homeGoals)&&Number.isInteger(m.awayGoals));
  const before=rows.filter(m=>m.date<date).sort((a,b)=>b.date.localeCompare(a.date)).slice(0,10);
  const after=rows.filter(m=>m.date>=date&&(!nextDate||m.date<nextDate)).sort((a,b)=>a.date.localeCompare(b.date)).slice(0,10);
  const stats=items=>({played:items.length,wins:items.filter(m=>(m.home===team?m.homeGoals:m.awayGoals)>(m.home===team?m.awayGoals:m.homeGoals)).length,draws:items.filter(m=>m.homeGoals===m.awayGoals).length,scored:items.reduce((n,m)=>n+(m.home===team?m.homeGoals:m.awayGoals),0),conceded:items.reduce((n,m)=>n+(m.home===team?m.awayGoals:m.homeGoals),0)});
  return {before:stats(before),after:stats(after)};
}
export function coachFixturesHtml(record,now=Date.now()){
  const competition=LEAGUES[record.league].name;
  if(!record.change.joinedAt)return '<p class="note">继任日期未确认，暂不编排新帅场次。</p>';
  const sequence=managerFixtures(record.matches,record.team.name,record.change.joinedAt,record.nextChange,{competition,now});
  const rowHtml=row=>{const m=row.match,names=record.names||{},score=m.finished||m.started?`${m.homeGoals??'—'}:${m.awayGoals??'—'}`:'对',status=m.finished?'已完赛':m.started?'进行中':row.pending?'赛况待更新':'未开赛';return `<li><a href="./?league=${encodeURIComponent(record.league)}#/match/${encodeURIComponent(m.id)}"><strong>${esc(row.label)}</strong> · ${dateText(m.date)} · ${esc(names[m.home]||m.home)} ${score} ${esc(names[m.away]||m.away)}</a> <span class="small subtle">${status}</span></li>`;};
  const preview=[...sequence.recent,...(sequence.next?[sequence.next]:[])];
  const pending=sequence.rows.filter(row=>row.pending).length;
  return `<section class="coach-fixtures" aria-label="换帅后比赛编号"><h3>换帅后的比赛</h3><p class="note">仅按本页已收录的${esc(competition)}比赛编号，不含其他赛事。${sequence.coverageLimited?'上任早于现有比赛覆盖范围；数字为已收录序号，不能视为执教首场。':''}未开赛场次为预计，赛程变化后重新排序。${pending?`有${pending}场赛况待更新，预计编号以已收录赛程为准。`:''}</p>${preview.length?`<ul>${preview.map(rowHtml).join('')}</ul>`:'<p class="note">暂无已比赛或未来赛程。</p>'}${sequence.rows.length>preview.length?`<details><summary>查看任期内全部${sequence.rows.length}场已收录比赛</summary><ul>${sequence.rows.map(rowHtml).join('')}</ul></details>`:''}</section>`;
}
export function renderCoaches(){
  let disposed=false,records=[],league='all',period='recent',query='',followed=followings();
  main.innerHTML=`${pageHeading('教练与换帅观察','集中跟踪五项赛事的领队更换、上任后的成绩和下一场比赛。')}<div class="toolbar"><label>赛事<select id="coach-league"><option value="all">全部赛事</option>${Object.values(LEAGUES).map(l=>`<option value="${l.id}">${l.name}</option>`).join('')}</select></label><label>范围<select id="coach-period"><option value="recent">近180天换帅</option><option value="all">全部已收录记录</option><option value="following">我的教练关注</option></select></label><label>球队或教练<input id="coach-search" type="search" placeholder="搜索球队或教练"></label></div><div id="coach-results"><p class="note">正在读取领队资料…</p></div>`;
  const box=main.querySelector('#coach-results');
  function draw(){if(disposed)return;const selected=records.filter(r=>(league==='all'||r.league===league)&&(period!=='following'||followed.has(r.key))&&(period!=='recent'||r.date&&Date.now()-Date.parse(r.date)<=180*86400000)&&(!query||[r.team.cn,r.team.name,r.change.incoming,r.change.outgoing].join(' ').toLowerCase().includes(query)));
    box.innerHTML=selected.length?selected.map(r=>{const comparison=managerComparison(r.matches.filter(m=>m.competition===LEAGUES[r.league].name),r.team.name,r.date,r.nextChange),s=stat=>stat.played?`${stat.played}场 · ${stat.wins}胜 ${stat.draws}平 ${stat.played-stat.wins-stat.draws}负 · 进${stat.scored}失${stat.conceded}`:'暂无可用赛果';return `<article class="coach-card"><div class="section-head"><h2>${esc(r.team.cn)} · ${LEAGUES[r.league].name}</h2><button class="button secondary compact" data-coach-follow="${esc(r.key)}" aria-pressed="${followed.has(r.key)}">${followed.has(r.key)?'已关注':'关注球队换帅'}</button></div><h3>${esc(r.change.outgoing||'原领队未列')} → ${esc(r.change.incoming||'继任待公布')}</h3><p>${r.change.joinedAt?'上任':'原帅离任'} ${dateText(r.date)} · ${esc(r.change.reason||'离任原因未列')} ${sourceLink(r.change.source,'变更来源')}</p><dl class="team-summary"><div><dt>换帅前最近10场内</dt><dd class="coach-stat">${s(comparison.before)}</dd></div><div><dt>${r.change.joinedAt?'上任后':'离任后'}前10场内</dt><dd class="coach-stat">${s(comparison.after)}</dd></div></dl><p>${!r.change.joinedAt?'继任日期尚未确认，离任后的赛果暂不归属于新任教练。':comparison.after.played<5?'新任期样本少于5场，暂不评价换帅是否有效。':'先比较胜平负与得失球，再结合对手强弱、主客场、伤停和赛程判断。成绩变化不能全部归因于教练。'}</p><p class="note">按已收录比赛计算；上任日期当天归入新任期，下一次换帅后不计入该教练。</p>${coachFixturesHtml(r)}<a href="./?league=${r.league}#/team/${r.team.id}">球队、阵容与赛程 →</a></article>`;}).join(''):'<div class="empty">此范围暂无已收录的换帅记录。可选择全部记录；资料缺少不代表没有换帅。</div>';
  }
  box.onclick=e=>{const b=e.target.closest('[data-coach-follow]');if(!b)return;const key=b.dataset.coachFollow;followed.has(key)?followed.delete(key):followed.add(key);localStorage.setItem(STORE,JSON.stringify([...followed]));draw();};
  main.querySelector('#coach-league').onchange=e=>{league=e.target.value;draw();};main.querySelector('#coach-period').onchange=e=>{period=e.target.value;draw();};main.querySelector('#coach-search').oninput=e=>{query=e.target.value.toLowerCase();draw();};
  async function load(){const feeds=await competitionFeeds();await Promise.allSettled(feeds.map(async f=>{if(!f.data)return;const h=await readLeagueSnapshot(f.league,'history');const matches=mergeMatches({...f.data,league:f.league},f.live),names=Object.fromEntries(f.data.teams.map(t=>[t.name,t.cn]));for(const c of h.managers||[]){const team=f.data.teams.find(t=>t.name===c.team);if(!team)continue;const date=c.joinedAt||c.leftAt;if(!date)continue;const nextChange=(h.managers||[]).filter(x=>x.team===c.team&&x.joinedAt>date).map(x=>x.joinedAt).sort()[0];records.push({key:f.league+':'+team.id,league:f.league,team,change:c,date,nextChange,matches,names});}}));records.sort((a,b)=>b.date.localeCompare(a.date));draw();}load().catch(()=>{if(!disposed)box.innerHTML='<div class="empty">教练资料暂时无法读取。</div>';});return()=>{disposed=true;};
}
