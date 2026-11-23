import {main,esc,pageHeading,dateText,sourceLink} from './ui.mjs';
import {api} from './api.mjs';
import {LEAGUES} from './league.mjs';
import {readLeagueSnapshot,competitionFeeds} from './competition-feed.mjs';
import {managerFixtures,uniqueCoachFixtures} from './coach-fixtures.mjs';
import {uniqueCoachChanges,coachPeriodMatches,coachMatchesForTeam,coachLineupChange,previousCoachMatch} from './coach-lineups.mjs';
const STORE='footballknow-coach-following';
function followings(){try{return new Set(JSON.parse(localStorage.getItem(STORE)||'[]'));}catch{return new Set();}}
export function managerComparison(matches,team,date,nextDate=null){
  const rows=uniqueCoachFixtures(matches).filter(m=>m.finished&&[m.home,m.away].includes(team)&&Number.isInteger(m.homeGoals)&&Number.isInteger(m.awayGoals));
  const before=rows.filter(m=>m.date<date).sort((a,b)=>b.date.localeCompare(a.date)).slice(0,10);
  const after=rows.filter(m=>m.date>=date&&(!nextDate||m.date<nextDate)).sort((a,b)=>a.date.localeCompare(b.date));
  const stats=items=>({played:items.length,wins:items.filter(m=>(m.home===team?m.homeGoals:m.awayGoals)>(m.home===team?m.awayGoals:m.homeGoals)).length,draws:items.filter(m=>m.homeGoals===m.awayGoals).length,scored:items.reduce((n,m)=>n+(m.home===team?m.homeGoals:m.awayGoals),0),conceded:items.reduce((n,m)=>n+(m.home===team?m.awayGoals:m.homeGoals),0)});
  return {before:stats(before),after:stats(after)};
}
export function coachLineupHtml(record,match,now=Date.now()){
  if(!record.lineups)return '<p class="note coach-lineup">正在读取首发对照…</p>';
  const previous=previousCoachMatch(record.matches,match,record.team.name,now);
  const change=coachLineupChange(match,previous,record.lineups,record.league);
  if(change.status==='missing')return `<p class="note coach-lineup">${record.lineupFailed?'部分首发资料暂时无法读取，可打开本场详情查看。':!match.started&&!match.finished?'正式首发公布并收录后，展示阵容变化。':'本场完整首发尚未收录，暂不判断阵容变化。'}</p>`;
  const {current,prior}=change;
  const names=players=>players.map(p=>esc(p.name||p.english||p.id)).join('、');
  const baseline=previous?`${dateText(previous.date)} ${esc(previous.competition||'')} ${esc(previous.homeLabel||record.names?.[previous.home]||previous.home)} 对 ${esc(previous.awayLabel||record.names?.[previous.away]||previous.away)}`:'';
  const formation=prior?.formation&&current.formation?(change.formationChanged?`阵型：${esc(prior.formation)} → ${esc(current.formation)}`:`阵型维持 ${esc(current.formation)}`):`本场阵型：${esc(current.formation||'未提供')}；暂不能核对阵型变化`;
  const summary=change.status==='compared'?change.added.length?`首发调整 ${change.added.length} 人`:'首发人员不变':'暂不能完整对照上一场';
  const detail=change.status==='compared'?`<p><strong>${summary}</strong> · ${formation}</p>${change.added.length?`<p><span class="coach-lineup-in">进入首发</span> ${names(change.added)}<br><span class="coach-lineup-out">退出首发</span> ${names(change.removed)}</p>`:''}`:`<p><strong>${summary}</strong> · 本场阵型 ${esc(current.formation||'未提供')}</p><p class="note">${previous?'上一场完整首发尚未收录，不以更早比赛代替。':'现有赛程中没有更早的比赛记录。'}</p>`;
  return `<div class="coach-lineup">${detail}<details><summary>首发名单与对照依据</summary>${previous?`<p class="note">对照上一场：${baseline}${previous.date<record.change.joinedAt?'（换帅前）':''}</p>`:''}<p><strong>本场首发</strong> ${names(current.starters)}</p>${prior?`<p><strong>上场首发</strong> ${names(prior.starters)}</p>`:''}<p class="note">${sourceLink(current.source,'本场首发来源')} · 更新 ${esc(current.updatedAt?.slice(0,16).replace('T',' ')||'—')}${prior?` · ${sourceLink(prior.source,'上场首发来源')}`:''}</p><p class="note">首发变化不等同于伤停或战术弃用，具体原因需结合球队消息核实。</p></details></div>`;
}
export function coachFixturesHtml(record,now=Date.now()){
  if(!record.change.joinedAt)return '<p class="note">继任日期未确认，暂不编排新帅场次。</p>';
  const sequence=managerFixtures(record.matches,record.team.name,record.change.joinedAt,record.nextChange,{now});
  const competitions=[...new Set(sequence.rows.map(r=>r.match.competition))].filter(Boolean).join('、')||LEAGUES[record.league].name;
  const rowHtml=row=>{const m=row.match,names=record.names||{},score=m.finished||m.started?`${m.homeGoals??'—'}:${m.awayGoals??'—'}`:'对',status=m.finished?'已完赛':m.started?'进行中':row.pending?'赛况待更新':'未开赛';return `<li><div class="coach-fixture-head"><a href="./?league=${encodeURIComponent(m.league||record.league)}#/match/${encodeURIComponent(m.id)}"><strong>${esc(row.label)}</strong> · ${score} · 本场详情</a><span class="small subtle">${dateText(m.date)} · ${esc(m.competition)} · ${status}</span></div><p class="coach-fixture-teams"><span data-entity-kind="team">${esc(m.homeLabel||names[m.home]||m.home)}</span> <span class="subtle">对</span> <span data-entity-kind="team">${esc(m.awayLabel||names[m.away]||m.away)}</span></p>${coachLineupHtml(record,m,now)}</li>`;};
  const pending=sequence.rows.filter(row=>row.pending).length;
  return `<section class="coach-fixtures" aria-label="换帅后比赛编号"><h3>换帅后的全部比赛 <span class="small subtle">${sequence.rows.length} 场已收录</span></h3><p class="note">按已收录的${esc(competitions)}比赛顺序编号，未收录的杯赛不在此列。${sequence.coverageLimited?'上任早于现有比赛覆盖范围；数字为已收录序号，不能视为执教首场。':''}未开赛场次为预计，赛程变化后重新排序。${pending?`有${pending}场赛况待更新，预计编号以已收录赛程为准。`:''}</p>${sequence.rows.length?`<ul class="coach-fixture-list">${sequence.rows.map(rowHtml).join('')}</ul>`:'<p class="note">暂无已比赛或未来赛程。</p>'}</section>`;
}
export function renderCoaches(){
  let disposed=false,records=[],league='all',period='recent',query='',followed=followings(),drawVersion=0,active=0;
  const controller=new AbortController(),requests=new Map(),queue=[];
  main.innerHTML=`${pageHeading('教练与换帅观察','跟踪领队更换、任期内全部已收录比赛，以及逐场首发与阵型变化。')}<div class="toolbar"><label>赛事<select id="coach-league"><option value="all">全部赛事</option>${Object.values(LEAGUES).map(l=>`<option value="${l.id}">${l.name}</option>`).join('')}</select></label><label>范围<select id="coach-period"><option value="30">近30天换帅</option><option value="recent" selected>近180天换帅</option><option value="all">全部已收录记录</option><option value="following">我的教练关注</option></select></label><label>球队或教练<input id="coach-search" type="search" placeholder="搜索球队或教练"></label></div><div id="coach-results"><p class="note">正在读取领队资料…</p></div>`;
  const box=main.querySelector('#coach-results');
  function pump(){while(!disposed&&active<2&&queue.length){active++;const {target,resolve}=queue.shift();api(`/api/coaches/lineups?league=${target.league}&team_id=${encodeURIComponent(target.teamId)}`,{signal:controller.signal}).then(resolve,()=>resolve({matches:[],failed:true})).finally(()=>{active--;pump();});}}
  function lineupRequest(target){const key=target.league+':'+target.teamId;if(!requests.has(key))requests.set(key,new Promise(resolve=>{queue.push({target,resolve});pump();}));return requests.get(key);}
  function draw(){
    if(disposed)return;const version=++drawVersion;
    const selected=uniqueCoachChanges(records.filter(r=>(league==='all'||r.league===league)&&(period!=='following'||followed.has(r.key))&&coachPeriodMatches(r.change.joinedAt,period)&&(!query||[r.team.cn,r.team.name,r.change.incoming,r.change.outgoing].join(' ').toLowerCase().includes(query))));
    box.innerHTML=selected.length?selected.map((r,index)=>{
      const comparison=managerComparison(r.matches,r.team.name,r.date,r.nextChange),s=stat=>stat.played?`${stat.played}场 · ${stat.wins}胜 ${stat.draws}平 ${stat.played-stat.wins-stat.draws}负 · 进${stat.scored}失${stat.conceded}`:'暂无可用赛果';
      return `<article class="coach-card" data-coach-record="${index}"><div class="section-head"><h2><a href="./?league=${r.league}#/team/${r.team.id}">${esc(r.team.cn)}</a> · ${LEAGUES[r.league].name}</h2><button class="button secondary compact" data-coach-follow="${esc(r.key)}" aria-pressed="${followed.has(r.key)}">${followed.has(r.key)?'已关注':'关注球队换帅'}</button></div><h3>${esc(r.change.outgoing||'原领队未列')} → ${esc(r.change.incoming||'继任待公布')}</h3><p>${r.change.joinedAt?'上任':'原帅离任'} ${dateText(r.date)} · ${esc(r.change.reason||'离任原因未列')} ${sourceLink(r.change.source,'变更来源')}</p><dl class="team-summary"><div><dt>换帅前最近10场内</dt><dd class="coach-stat">${s(comparison.before)}</dd></div><div><dt>${r.change.joinedAt?'上任后全部已完赛':'离任后已完赛'}</dt><dd class="coach-stat">${s(comparison.after)}</dd></div></dl><p>${!r.change.joinedAt?'继任日期尚未确认，离任后的赛果暂不归属于新任教练。':comparison.after.played<5?'新任期样本少于5场，暂不评价换帅是否有效。':'先比较胜平负与得失球，再结合对手强弱、主客场、伤停和赛程判断。成绩变化不能全部归因于教练。'}</p><p class="note">按已收录比赛计算；上任日期当天归入新任期，下一次换帅后不计入该教练。</p>${coachFixturesHtml(r)}<a href="./?league=${r.league}#/team/${r.team.id}">球队、阵容与赛程 →</a></article>`;
    }).join(''):'<div class="empty">此范围暂无已收录的换帅记录。可选择全部记录；资料缺少不代表没有换帅。</div>';
    for(const [index,r] of selected.entries()){
      if(r.lineups||!r.change.joinedAt)continue;
      Promise.all(r.targets.map(lineupRequest)).then(values=>{
        r.lineups=values.flatMap(v=>v.matches||[]);r.lineupFailed=values.some(v=>v.failed);
        if(disposed||version!==drawVersion)return;
        const section=box.querySelector(`[data-coach-record="${index}"] .coach-fixtures`);
        if(section)section.outerHTML=coachFixturesHtml(r);
      });
    }
  }
  box.onclick=e=>{const b=e.target.closest('[data-coach-follow]');if(!b)return;const key=b.dataset.coachFollow;followed.has(key)?followed.delete(key):followed.add(key);localStorage.setItem(STORE,JSON.stringify([...followed]));draw();};
  main.querySelector('#coach-league').onchange=e=>{league=e.target.value;draw();};main.querySelector('#coach-period').onchange=e=>{period=e.target.value;draw();};main.querySelector('#coach-search').oninput=e=>{query=e.target.value.toLowerCase();draw();};
  async function load(){
    const feeds=await competitionFeeds();
    await Promise.allSettled(feeds.map(async f=>{
      if(!f.data||disposed)return;const h=await readLeagueSnapshot(f.league,'history');
      const names=Object.fromEntries(f.data.teams.map(t=>[t.name,t.cn]));
      for(const c of h.managers||[]){
        const team=f.data.teams.find(t=>t.name===c.team);if(!team)continue;
        const date=c.joinedAt||c.leftAt;if(!date)continue;
        const nextChange=(h.managers||[]).filter(x=>x.team===c.team&&x.joinedAt>date).map(x=>x.joinedAt).sort()[0];
        const {matches,targets}=coachMatchesForTeam(feeds,f.league,team);
        records.push({key:f.league+':'+team.id,league:f.league,team,change:c,date,nextChange,matches,targets,names});
      }
    }));
    records.sort((a,b)=>b.date.localeCompare(a.date));draw();
  }
  load().catch(()=>{if(!disposed)box.innerHTML='<div class="empty">教练资料暂时无法读取。</div>';});
  return()=>{disposed=true;controller.abort();while(queue.length)queue.shift().resolve({matches:[],failed:true});};
}
