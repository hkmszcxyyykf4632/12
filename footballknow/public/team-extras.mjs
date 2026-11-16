import {data,facts} from './repository.mjs';
import {esc,cn,timeText} from './ui.mjs';
import {localized} from './football-components.mjs';
import {league} from './league.mjs';
import {teamSeason} from './insights.mjs';
import {STATUS} from './player-stats.mjs';

const per=(value,games)=>games?(value/games).toFixed(2):'—';

export function seasonBlock(team) {
  const record=teamSeason(data.matches,team.name,league.name,data.season),extra=facts?.teams?.[team.name];
  if(!record.all.played)return `<div class="empty">本赛季${league.name}还没有已完赛的比赛。</div>`;
  const row=(label,r)=>`<tr><th scope="row">${label}</th><td>${r.played}</td><td>${r.wins}</td><td>${r.draws}</td><td>${r.losses}</td><td>${r.goalsFor}</td><td>${r.goalsAgainst}</td><td>${per(r.goalsFor,r.played)}</td><td>${per(r.goalsAgainst,r.played)}</td><td>${r.cleanSheets}</td><td>${r.failedToScore}</td></tr>`;
  const split=(label,r)=>{const n=r.w+r.d+r.l;return `<div><dt>${label}</dt><dd>${n?`${r.w} 胜 ${r.d} 平 ${r.l} 负`:'—'}</dd>${n?`<small>共 ${n} 场，${label==='先进球时'?'胜率':'不败率'} ${Math.round((label==='先进球时'?r.w:r.w+r.d)/n*100)}%</small>`:''}</div>`;};
  const a=extra?.averages||{};
  const rate=(part,whole)=>a[whole]?`${Math.round(a[part]/a[whole]*100)}%`:'—';
  return `<div class="table-wrap"><table><thead><tr><th>范围</th><th>赛</th><th>胜</th><th>平</th><th>负</th><th>进球</th><th>失球</th><th>场均进球</th><th>场均失球</th><th>零封</th><th>未进球</th></tr></thead><tbody>${row('全部',record.all)}${row('主场',record.home)}${row('客场',record.away)}</tbody></table></div>
    ${extra?`<dl class="stat-grid">${split('先进球时',extra.scoredFirst)}${split('先失球时',extra.concededFirst)}
      ${[['场均控球',a.possessionPct!=null?`${a.possessionPct.toFixed(1)}%`:'—'],['场均射门 / 射正',a.totalShots!=null?`${a.totalShots.toFixed(1)} / ${a.shotsOnTarget.toFixed(1)}`:'—'],['场均角球',a.wonCorners?.toFixed(1)??'—'],['传球成功率',rate('accuratePasses','totalPasses')],['场均抢断 / 拦截',a.totalTackles!=null?`${a.totalTackles.toFixed(1)} / ${a.interceptions.toFixed(1)}`:'—'],['场均犯规',a.foulsCommitted?.toFixed(1)??'—'],['黄牌 / 红牌',extra.totals?.yellowCards!=null?`${extra.totals.yellowCards} / ${extra.totals.redCards}`:'—']].map(([term,value])=>`<div><dt>${term}</dt><dd>${value}</dd></div>`).join('')}</dl>
      <p class="note">技术统计为已收录 ${extra.statMatches} 场比赛的平均值。先进球与先失球只统计事件记录能与终场比分对上的比赛，场数可能少于已赛场次。</p>`
      :'<p class="note">技术统计平均值在比赛名单汇总生成后显示。</p>'}`;
}

export function availabilityBlock(team) {
  const out=data.players.filter(p=>p.team===team.id&&['d','i','s','u','n'].includes(p.status));
  if(league.id!=='epl')return '<p class="note">这项赛事的公开名单不提供伤停标注，本站不作推测。</p>';
  if(!out.length)return '<div class="empty">来源目前没有标注这支球队的伤停或停赛球员。</div>';
  return `<div class="table-wrap"><table><thead><tr><th>球员</th><th>状态</th><th>下轮出场概率</th><th>来源说明</th></tr></thead><tbody>${out.map(p=>`<tr><td><a class="player-name" href="#/player/${p.id}">${esc(localized(p)?.mandarin||p.web_name)}<small>${esc(p.web_name)}</small></a></td><td><span class="status attention">${STATUS[p.status]}</span></td><td>${p.chance_of_playing_next_round!=null?`${p.chance_of_playing_next_round}%`:'—'}</td><td class="job-message">${esc(p.news||'—')}</td></tr>`).join('')}</tbody></table></div><p class="note">状态与说明取自英超公开数据的球员可用性标注，俱乐部正式公告可能更新。</p>`;
}

export function calendarBlock(team) {
  const rows=data.matches.filter(m=>m.season===data.season&&m.competition===league.name&&[m.home,m.away].includes(team.name)).sort((a,b)=>(a.kickoff||a.date).localeCompare(b.kickoff||b.date));
  if(!rows.length)return '<div class="empty">本赛季赛程尚未公布。</div>';
  return `<div class="table-wrap"><table><thead><tr><th>场次</th><th>时间</th><th>主客</th><th>对手</th><th>比分</th><th>结果</th></tr></thead><tbody>${rows.map((m,index)=>{
    const home=m.home===team.name,scored=home?m.homeGoals:m.awayGoals,conceded=home?m.awayGoals:m.homeGoals;
    const result=!m.finished||scored==null?'':scored>conceded?'win':scored<conceded?'loss':'draw';
    return `<tr><td>${index+1}</td><td>${esc(m.kickoff?timeText(m.kickoff):m.date)}</td><td>${home?'主':'客'}</td><td>${esc(cn(home?m.away:m.home))}</td><td class="score"><a href="#/match/${encodeURIComponent(m.id)}">${m.started||m.finished?`${m.homeGoals??'—'} : ${m.awayGoals??'—'}`:'未开赛'}</a></td><td>${result?`<span class="result ${result}">${{win:'胜',draw:'平',loss:'负'}[result]}</span>`:m.started?'进行中':''}</td></tr>`;}).join('')}</tbody></table></div><p class="note">场次按本队本赛季${league.name}比赛的时间顺序编号，不是联赛官方轮次。</p>`;
}
