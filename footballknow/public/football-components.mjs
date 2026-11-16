import {data,names} from './repository.mjs';
import {esc,cn,dateText,timeText,sourceLink} from './ui.mjs';
import {nameDrafts} from './name-drafts.mjs';
import {laligaNameDrafts} from './laliga-name-drafts.mjs';
import {uclNameDrafts} from './ucl-name-drafts.mjs';
import {league} from './league.mjs';

export function localized(player) {return names?.names?.[String(player.code)]||(league.id==='epl'?nameDrafts:league.id==='ucl'?{...laligaNameDrafts,...uclNameDrafts}:laligaNameDrafts)[String(player.code)];}

export function playerLabel(player) {
  const name=localized(player);
  return (name?.cantonese||name?.mandarin||player.web_name)+(name?.status==='draft'?'（暂译）':'');
}

export function transferPlayer(name) {
  const normalize=value=>String(value||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  const key=normalize(name);
  const matches=data.players.filter(p=>[p.known_name,p.web_name,`${p.first_name} ${p.second_name}`].some(value=>normalize(value)===key));
  const translated=matches.length===1?localized(matches[0]):null;
  return translated?`<strong>${esc(translated.cantonese)}</strong><small>${translated.status==='draft'?'暂用音译 · ':''}${esc(translated.mandarin)} · ${esc(name)}</small>`:esc(name);
}

export function nextMatch(team) {
  const now=Date.now();
  return data.matches.filter(row=>row.competition===league.name&&!row.finished&&!row.started&&[row.home,row.away].includes(team.name)&&row.kickoff&&Date.parse(row.kickoff)>now)
    .sort((a,b)=>a.kickoff.localeCompare(b.kickoff))[0];
}

export function fixtureStrip(team) {
  const match=nextMatch(team);
  if(!match)return '<div class="notice">暂未收录下一场已确定时间的比赛；同步后会自动显示。</div>';
  return `<div class="fixture-strip"><div><span class="fixture-label">下一场${league.name}比赛</span><h2>${esc(cn(match.home))}<span class="versus">vs</span>${esc(cn(match.away))}</h2><p>${esc(timeText(match.kickoff))} · ${league.name}${match.phase?' · '+esc(match.phase):''}${match.neutral?' · 中立场':''} · 本地时间</p></div><a class="button" href="#/analysis/${team.id}">查看赛前分析 <span aria-hidden="true">↗</span></a></div>`;
}

export function fixtureBoard() {
  const active=data.matches.filter(row=>row.competition===league.name&&row.season===data.season&&row.started&&!row.finished);
  const upcoming=data.matches.filter(row=>row.competition===league.name&&row.season===data.season&&!row.started&&!row.finished&&row.kickoff&&Date.parse(row.kickoff)>Date.now())
    .sort((a,b)=>a.kickoff.localeCompare(b.kickoff)).slice(0,4);
  const fixtures=[...active,...upcoming];
  if(!fixtures.length)return `<div class="empty">暂无正在进行或已排期的${league.name}比赛。</div>`;
  return `<div class="fixture-list">${fixtures.map(row=>{
    const team=data.teams.find(t=>t.name===row.home);
    return `<div class="fixture-row"><div class="fixture-meta"><span class="${row.started?'tag attention':'subtle'}">${row.provisional?'等待赛果确认':row.started?'进行中':timeText(row.kickoff)}</span><small>${league.name} ${esc(row.season)}</small></div><span class="fixture-club">${esc(cn(row.home))}</span><strong class="fixture-score">${row.started?`${row.homeGoals??'—'} : ${row.awayGoals??'—'}`:'vs'}</strong><span class="fixture-club">${esc(cn(row.away))}</span>${row.started?sourceLink(row.source,'比分来源'):`<a class="button quiet compact" href="#/analysis/${team.id}">赛前分析 ↗</a>`}</div>`;
  }).join('')}</div>`;
}

export function timestamp(value) {return value?esc(new Date(value).toLocaleString('zh-CN')):'尚未成功获取';}
