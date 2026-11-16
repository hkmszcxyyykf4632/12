import {data,rankings} from './repository.mjs';
import {main,esc,cn,team,monogram,pageHeading,matchTable,timeText,oddsText} from './ui.mjs';
import {fixtureBoard,localized} from './football-components.mjs';
import {league} from './league.mjs';
import {standingsPreview} from './rankings-page.mjs';
import {impliedProbabilities,seasonStats,leadMatch,countdownText,statusSummary} from './insights.mjs';
import {readStatus} from './status-page.mjs';

const percent=value=>`${Math.round(value*100)}%`;

function leadFixture() {
  const m=leadMatch(data.matches,league.name,data.season);
  if(!m)return `<div class="empty">本赛季暂时没有进行中或已排期的${league.name}比赛。<a class="button quiet" href="#/matches">查看全部赛果</a></div>`;
  const side=name=>{const t=team(name);return t?`<a class="lead-team" href="#/team/${t.id}">${monogram(t)}<span>${esc(t.cn)}</span></a>`:`<span class="lead-team"><span>${esc(name)}</span></span>`;};
  const home=team(m.home),quote=m.odds?.[0],probabilities=impliedProbabilities(quote);
  const wait=countdownText(m.kickoff);
  return `<section class="lead-fixture" aria-label="${m.started?'进行中的比赛':'下一场比赛'}"><div class="lead-main">
    <span class="lead-state ${m.started?'in-play':''}">${m.started?'比赛进行中':`下一场${league.name}比赛`}${m.phase?` · ${esc(m.phase)}`:''}</span>
    <div class="lead-teams">${side(m.home)}<strong class="lead-score ${m.started?'':'pending'}">${m.started?`${m.homeGoals??'—'} : ${m.awayGoals??'—'}`:'VS'}</strong>${side(m.away)}</div>
    <p class="lead-meta">${esc(timeText(m.kickoff))} 开球（本地时间）${wait?`，距开赛 <strong>${esc(wait)}</strong>`:''}</p>
    <div class="lead-actions"><a class="button" href="#/match/${encodeURIComponent(m.id)}">比赛详情</a>${home&&!m.started?`<a class="button secondary" href="#/analysis/${home.id}">赛前分析</a>`:''}<a class="button secondary" href="#/matches">全部赛程</a></div></div>
    <div class="lead-side"><h2>${probabilities?'市场隐含概率':'赛前报价'}</h2>${probabilities?`<dl class="prob-list">${[['主胜','H'],['平局','D'],['客胜','A']].map(([label,key])=>`<div><dt>${label}</dt><div class="prob-bar" role="img" aria-label="${label} ${percent(probabilities[key])}"><i style="width:${probabilities[key]*100}%"></i></div><dd>${percent(probabilities[key])}</dd><dd class="price">${oddsText(quote[key])}</dd></div>`).join('')}</dl><p>${esc(quote.label||'报价来源')}，已按比例扣除 ${(probabilities.margin*100).toFixed(1)}% 的报价水位。</p>`
      :`<p>这场比赛还没有可核对的三项报价。系统每 60 秒检查来源，取得报价后会显示在这里，也可以先<a class="source-link" href="#/match/${encodeURIComponent(m.id)}">录入已有赔率</a>。</p>`}</div></section>`;
}

function kpiStrip() {
  const s=seasonStats(data.matches,league.name,data.season);
  const share=key=>s.played?s[key]/s.played:0;
  return `<dl class="kpi-strip">
    <div class="kpi"><dt>赛季进度</dt><dd>${s.played}<small>/ ${s.total} 场</small></dd><div class="meter" role="img" aria-label="已完成 ${s.total?Math.round(s.played/s.total*100):0}%"><i style="width:${s.total?s.played/s.total*100:0}%"></i></div></div>
    <div class="kpi"><dt>场均进球</dt><dd>${s.average==null?'—':s.average.toFixed(2)}</dd><p>共 ${s.goals} 球</p></div>
    <div class="kpi"><dt>主胜 / 平 / 客胜</dt><dd>${s.played?`${percent(share('home'))}<small>${percent(share('draw'))} / ${percent(share('away'))}</small>`:'—'}</dd><div class="split" role="img" aria-label="主胜 ${s.home} 场，平局 ${s.draw} 场，客胜 ${s.away} 场"><i style="flex:${s.home||0.01}"></i><i style="flex:${s.draw||0.01}"></i><i style="flex:${s.away||0.01}"></i></div></div>
    <div class="kpi"><dt>今日比赛</dt><dd>${s.today}<small>场</small></dd><p>${s.live?`${s.live} 场进行中`:'目前没有进行中的比赛'}</p></div>
    <div class="kpi" id="kpi-sync"><dt>数据同步</dt><dd>—</dd><p><a href="#/status">查看同步监控</a></p></div></dl>`;
}

function scorers() {
  const rows=(rankings?.boards?.scorers||[]).slice(0,5);
  if(!rows.length)return '<div class="empty">射手榜正在同步。</div>';
  return `<ol class="mini-list">${rows.map(r=>{const n=r.playerCode?localized({code:r.playerCode}):null;return `<li><span class="rank">${r.rank}</span><div><strong>${esc(n?.mandarin||r.name)}</strong><small>${esc(r.teamName)} · ${r.appearances} 场</small></div><b>${r.value}</b></li>`;}).join('')}</ol>`;
}

async function paintSync() {
  try {
    const summary=statusSummary(await readStatus());
    const target=main.querySelector('#kpi-sync');if(!target)return;
    target.innerHTML=`<dt>数据同步</dt><dd class="${summary.level==='ok'?'':summary.level==='warn'?'attention':'negative'}">${summary.ok}<small>/ ${summary.total} 项正常</small></dd><p><a href="#/status">${esc(summary.level==='ok'?'每 60 秒检查全部来源':summary.text)}</a></p>`;
  } catch {/* The tile keeps its link to the monitor when the status service cannot be read. */}
}

export function renderHome() {
  main.innerHTML=`${pageHeading(`${league.name}总览`,`${esc(data.season)} 赛季的赛程、比分、积分与球员数据，全部每 60 秒同步一次。`,`<a class="button secondary" href="#/compare">对比两支球队</a>`)}
  <div id="home-lead"></div><div id="home-kpi"></div>
  <div class="dash-grid"><div>
    <div class="section-head"><h2>比赛动态与赛程</h2><a class="button quiet" href="#/matches">比赛中心</a></div><div id="home-fixtures"></div>
    <div class="section-head"><h2>最近完赛</h2><a class="button quiet" href="#/matches">全部赛果</a></div><div id="home-recent"></div>
  </div><div>
    <div class="section-head"><h2>积分榜前五</h2><a class="button quiet" href="#/rankings">完整榜单</a></div><div id="home-standings"></div>
    <div class="section-head"><h2>射手榜</h2><a class="button quiet" href="#/rankings">球员榜</a></div><div id="home-scorers"></div>
  </div></div>
  <p class="note">开球时间按本地时区显示。比分、胜平负按 90 分钟含补时统计。<a href="#/sources">查看数据来源与统计口径</a></p>`;
  const update=()=>{
    if(!main.querySelector('#home-lead'))return;
    main.querySelector('#home-lead').innerHTML=leadFixture();
    main.querySelector('#home-kpi').innerHTML=kpiStrip();
    main.querySelector('#home-fixtures').innerHTML=fixtureBoard();
    main.querySelector('#home-standings').innerHTML=standingsPreview();
    main.querySelector('#home-scorers').innerHTML=scorers();
    main.querySelector('#home-recent').innerHTML=matchTable(data.matches.filter(m=>m.finished&&m.season===data.season&&m.competition===league.name).slice(0,6));
    paintSync();
  };
  update();return update;
}
