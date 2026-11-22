import {mountTeamSections,foldResearch} from './team-sections.mjs';
import {hydrateBriefs} from './review-briefs.mjs';
import {bindHandicapTrend} from './handicap-trend.mjs';
import {data,names,playerValues,markets} from './repository.mjs';
import {valuationHtml} from './player-values.mjs';
import {playerStar,positionalGaps} from './player-research.mjs';
import {main,esc,cn,dateText,monogram,recent,resultFor,formRun,matchTable,sourceLink} from './ui.mjs';
import {localized,fixtureStrip} from './football-components.mjs';
import {playerPortrait,hydratePlayerPortraits} from './portraits.mjs';
import {historySections,bindHistory} from './team-history.mjs';
import {league} from './league.mjs';
import {clubResearch} from './club-research.mjs';
import {followButton} from './matches-page.mjs';
import {seasonBlock,availabilityBlock,calendarBlock} from './team-extras.mjs';

const POSITIONS={1:'门将',2:'后卫',3:'中场',4:'前锋'};
const STATUS={unreported:'未标注伤停',a:'可出场',d:'出场待定',i:'伤缺',s:'停赛',u:'暂不可用',n:'暂不可用'};

function playerRows(team) {
  const players=data.players.filter(p=>p.team===team.id).sort((a,b)=>a.position-b.position||(b.minutes||0)-(a.minutes||0));
  return players.map(p=>{
    const name=localized(p);
    const search=[name?.cantonese,name?.mandarin,p.first_name,p.second_name,p.web_name].join(' ').toLowerCase();
    return `<tr data-player="${esc(search)}" data-position="${p.position}"><td class="player-name"><span class="person-identity">${playerPortrait(p,league.id)}<span><a href="#/player/${p.id}">${name?esc(name.cantonese):'<span class="subtle">译名待收录</span>'}</a> ${playerStar(p)}<small>${esc(p.known_name||p.web_name)}</small></span></span></td><td class="player-name">${name?esc(name.mandarin):'—'}<small>${name?.status==='draft'?'<span class="attention">暂用音译 · 两版均待核</span>':name?sourceLink(name.mandarinSource,'普通话')+' · '+sourceLink(name.cantoneseSource,'香港译名'):esc(p.first_name+' '+p.second_name)}</small></td><td>${POSITIONS[p.position]||'—'}</td><td>${dateText(p.birth_date)}</td><td class="player-value">${valuationHtml(p,true)}</td><td>${p.minutes??'—'}</td><td>${p.goals_scored??'—'} / ${p.assists??'—'}</td><td><span class="status ${p.status==='a'?'':'attention'}" title="${esc(p.news||'')}">${STATUS[p.status]||'未知'}</span>${p.news?`<details class="player-news"><summary>说明</summary><p>${esc(p.news)}</p></details>`:''}</td></tr>`;
  }).join('');
}

function summaryBlock(team) {
  const matches=recent(team);
  const wins=matches.filter(row=>resultFor(row,team)==='win').length;
  const draws=matches.filter(row=>row.result==='D').length;
  const goals=matches.reduce((sum,row)=>sum+(row.home===team.name?row.homeGoals:row.awayGoals),0);
  const conceded=matches.reduce((sum,row)=>sum+(row.home===team.name?row.awayGoals:row.homeGoals),0);
  return `<div><dt>近 ${matches.length} 场${league.historyLabel}</dt><dd>${wins}<small> 胜 </small>${draws}<small> 平 </small>${matches.length-wins-draws}<small> 负</small></dd></div><div><dt>进球 / 失球</dt><dd>${goals} <small>/</small> ${conceded}</dd></div><div><dt>最近五场 · 最新在左</dt><dd class="form-run">${formRun(team)}</dd></div>`;
}

export function renderTeam(id) {
  const team=data.teams.find(row=>row.id===Number(id));
  if(!team){main.innerHTML='<div class="empty">球队不存在。<a href="#/teams">返回球队列表</a></div>';return ()=>{};}
  const players=data.players.filter(p=>p.team===team.id);
  main.innerHTML=`<a class="back-link" href="#/teams">← 全部${league.name}球队</a><div class="page-heading"><div class="team-title">${monogram(team)}<div><h1>${esc(team.cn)}</h1><p class="lede">${esc(team.name)} · ${esc(data.season)} ${league.name}</p></div></div><span class="tag">${players.length} 位收录球员</span></div>
    <div class="toolbar">${followButton(team)}<button class="button secondary compact" type="button" data-share>分享链接</button><a class="button quiet compact" href="#/rankings">查看${league.name}排名 →</a><a class="button quiet compact" href="#/matches">比赛中心 →</a></div><dl class="team-summary" id="team-summary">${summaryBlock(team)}</dl><div id="team-fixture">${fixtureStrip(team)}</div>
    <div id="team-research">${clubResearch(team)}</div><div id="team-position-gaps">${positionalGaps(team)}</div><nav class="tabs" aria-label="球队资料跳转"><button class="active" data-jump="players">球员资料</button><button data-jump="season">赛季数据</button><button data-jump="availability">伤停</button><button data-jump="calendar">赛程日历</button><button data-jump="matches">近二十场</button><button data-jump="transfers">转会记录</button><button data-jump="managers">领队更换</button></nav>
    <section id="players-section"><div class="section-head"><div><h2>球员资料</h2></div><span class="small subtle">粤语 · 普通话 · 原名</span></div><div class="toolbar"><div class="search"><input id="player-search" type="search" placeholder="搜索中文、粤语译名或英文名" aria-label="搜索球员"></div><select class="filter-select" id="position-filter" aria-label="筛选球员位置"><option value="">全部位置</option>${Object.entries(POSITIONS).map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select></div>
    <div class="table-wrap"><table class="squad-table"><thead><tr><th>粤语 / 香港译名</th><th>普通话 / 大陆译名</th><th>位置（${league.roster}）</th><th>出生日期</th><th>估算身价</th><th>分钟</th><th>进球 / 助攻</th><th>状态</th></tr></thead><tbody id="player-rows">${playerRows(team)}</tbody></table></div><div id="player-empty" class="empty hidden">没有符合筛选条件的球员。</div><p class="note" id="names-coverage"></p><p class="note">分钟、进球与助攻为本赛季${league.name}数据；位置按 ${league.roster} 分类，未提供的数值留空，名单可能不包含全部注册球员。</p></section>
    <section id="season-section"><div class="section-head"><h2>赛季攻防数据</h2><p>${esc(data.season)} ${league.name}</p></div><div id="team-season">${seasonBlock(team)}</div></section>
    <section id="availability-section"><div class="section-head"><h2>伤停与停赛</h2></div><div id="team-availability">${availabilityBlock(team)}</div></section>
    <section id="team-handicap-trend"></section><section id="calendar-section"><div class="section-head"><h2>赛程日历</h2><p>本赛季全部${league.name}比赛</p></div><div class="toolbar"><label class="small">主客场 <select class="filter-select" id="team-venue" aria-label="筛选球队主客场"><option value="all">全部</option><option value="home">主场</option><option value="away">客场</option></select></label><span class="small subtle">同时筛选赛程与最近二十场</span></div><div id="team-calendar">${calendarBlock(team)}</div></section>
    <section id="matches-section"><div class="section-head"><div><h2>最近二十场${league.historyLabel}</h2></div><p>最新在上 · 跨赛季</p></div><div class="toolbar"><p class="note">点击赔率，记录一次模拟判断</p><select class="filter-select" id="competition-filter" aria-label="筛选比赛赛事"><option value="all">${league.historyFilter}</option><option value="pl">仅${league.name}</option></select></div><div id="matches-table">${matchTable(recent(team),team)}</div><p class="note">比分和赔率按主队、客队排列。不足二十场时显示实际数量。${league.id==='ucl'?'已收录正式赛事按90分钟含补时统计；加时、点球与总比分分开，缺少可核对比分的场次不参与统计。':'当前范围不包含杯赛。'}缺少赔率可手动录入。</p></section>${historySections(team)}`;
  const overview=()=>`<div class="section-head"><h2>最近五场赛果</h2><span class="small subtle">已确认完赛 · 最新在前</span></div>${recent(team).slice(0,5).map(m=>`<div class="team-recent-row"><time>${esc(m.date)}</time><span>${esc(cn(m.home))}</span><a href="#/match/${encodeURIComponent(m.id)}"><b>${m.homeGoals} : ${m.awayGoals}</b></a><span>${esc(cn(m.away))}</span><span class="tag">已完赛</span></div>`).join('')||'<p class="note">暂未收录已确认赛果。</p>'}<p class="note">查看完整赛程、亚洲盘与大小球结果，请切换「赛程与赛果」。</p>`;
  mountTeamSections(main,`<div id="team-overview-results">${overview()}</div>`);
  const updateHandicap=bindHandicapTrend(main.querySelector('#team-handicap-trend'),()=>({matches:data.matches,teamName:team.name,snapshot:markets,season:data.season,competition:league.name}),cn);
  function filterPlayers() {
    const query=main.querySelector('#player-search').value.trim().toLowerCase();
    const position=main.querySelector('#position-filter').value;
    let count=0;
    main.querySelectorAll('[data-player]').forEach(row=>{const show=row.dataset.player.includes(query)&&(!position||row.dataset.position===position);row.classList.toggle('hidden',!show);if(show)count++;});
    main.querySelector('#player-empty').classList.toggle('hidden',count>0);
    const roster=data.players.filter(p=>p.team===team.id);
    main.querySelector('#names-coverage').textContent=`本队 ${roster.length} 名球员，${roster.filter(p=>names?.names?.[String(p.code)]).length} 名已有普通话与香港译名来源；暂用音译已逐项标注。`;
  }
  const venue=()=>main.querySelector('#team-venue').value;
  const updateMatches=()=>{main.querySelector('#matches-table').innerHTML=matchTable(recent(team,main.querySelector('#competition-filter').value==='pl',venue()),team);hydrateBriefs(main,'football');};
  main.querySelector('#team-venue').addEventListener('change',()=>{main.querySelector('#team-calendar').innerHTML=calendarBlock(team,venue());updateMatches();});
  main.querySelector('#player-search').addEventListener('input',filterPlayers);
  main.querySelector('#position-filter').addEventListener('change',filterPlayers);
  main.querySelector('#competition-filter').addEventListener('change',updateMatches);
  bindHistory(team);filterPlayers();
  let rosterVersion=data.updatedAt, namesVersion=names?.updatedAt, valueVersion=playerValues?.updatedAt;
  return ()=>{
    main.querySelector('#team-fixture').innerHTML=fixtureStrip(team);
    main.querySelector('#team-summary').innerHTML=summaryBlock(team);
    main.querySelector('#team-season').innerHTML=seasonBlock(team);main.querySelector('#team-availability').innerHTML=availabilityBlock(team);main.querySelector('#team-calendar').innerHTML=calendarBlock(team,venue());
    updateHandicap();updateMatches();
    main.querySelector('#team-overview-results').innerHTML=overview();
    const research=main.querySelector('#team-research'),openIds=[...research.querySelectorAll('details[open]')].map(d=>d.dataset.clubSection);
    research.innerHTML=clubResearch(team);foldResearch(research);research.querySelectorAll('details[data-club-section]').forEach(d=>d.open=openIds.includes(d.dataset.clubSection));
    if(rosterVersion!==data.updatedAt||namesVersion!==names?.updatedAt||valueVersion!==playerValues?.updatedAt){main.querySelector('#player-rows').innerHTML=playerRows(team);filterPlayers();hydratePlayerPortraits(main,league.id);rosterVersion=data.updatedAt;namesVersion=names?.updatedAt;valueVersion=playerValues?.updatedAt;}
  };
}
