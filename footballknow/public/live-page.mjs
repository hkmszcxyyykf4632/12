import {LEAGUES} from './league.mjs';
import {main,esc,pageHeading,timeText} from './ui.mjs';
import {competitionFeeds,combinedFixtures,readLeagueSnapshot} from './competition-feed.mjs';
import {broadcastLinks} from './broadcasts.mjs';
import {eventTimeline} from './match-extras.mjs';
import {quotesForMatch,selectQuote} from './settlement.mjs';
import {PHASE_NAMES} from './markets-core.mjs';

export function renderLive(){
  let disposed=false,busy=false,feeds=[],rows=[],selected='all',state='upcoming',date='',region='all';
  const opened=new Map();
  main.innerHTML=`${pageHeading('即场比赛','英超、西甲、意甲、德甲、欧冠合并排列 · 开球时间从早到晚', '<button id="live-refresh" class="button secondary">检查更新</button>')}
    <div class="toolbar match-filters"><label>赛事<select id="live-league"><option value="all">全部五项赛事</option>${Object.values(LEAGUES).map(l=>`<option value="${l.id}">${l.name}</option>`).join('')}</select></label><label>状态<select id="live-state"><option value="upcoming">进行中与未来七天</option><option value="live">正在进行</option><option value="finished">最近完赛</option><option value="all">全部</option></select></label><label>本地日期<input type="date" id="live-date"></label><label>观看地区<select id="live-region"><option value="all">全部地区</option><option value="mo">澳门 · MPLUS</option><option value="hk">香港</option><option value="cn">中国内地</option></select></label></div>
    <p id="live-feed-status" class="note" role="status">正在读取五项赛事…</p><div id="combined-fixtures"></div>`;
  const href=m=>`./?league=${m.league}#/match/${encodeURIComponent(m.id)}`;
  function handicapHtml(m){
    const quotes=quotesForMatch(feeds.find(f=>f.league===m.league)?.markets,m);
    const q=selectQuote(quotes,'asian-handicap',m.finished?['closing','preclosing','opening']:['latest','preclosing','opening']);
    if(!q)return '<div class="live-handicap"><strong>亚洲让球盘</strong><span class="subtle">盘口暂缺</span></div>';
    const line=n=>(n>0?'+':'')+n;
    return '<div class="live-handicap"><strong>亚洲让球盘</strong><span>主队 '+line(q.line)+' <b>'+q.prices.H.toFixed(2)+'</b></span><span>客队 '+line(-q.line)+' <b>'+q.prices.A.toFixed(2)+'</b></span><small>'+esc(q.provider)+' · '+PHASE_NAMES[q.phase]+' · 采集 '+esc(timeText(q.fetchedAt))+(m.started&&!m.finished?' · 来源未标注滚球，按报价快照展示':'')+'</small></div>';
  }
  function draw(){
    if(disposed)return;
    rows=combinedFixtures(feeds,{league:selected,state,date});
    const failed=feeds.filter(f=>f.failed).map(f=>LEAGUES[f.league].name);
    main.querySelector('#live-feed-status').textContent=`${rows.length} 场 · 本地时区 ${Intl.DateTimeFormat().resolvedOptions().timeZone} · 每 60 秒检查${failed.length?' · '+failed.join('、')+'读取失败，保留上次资料':''}`;
    let day='';
    main.querySelector('#combined-fixtures').innerHTML=rows.length?rows.map((m,i)=>{
      const heading=m.day!==day?`<h2 class="fixture-day">${esc(m.day||'时间待定')}</h2>`:'';day=m.day;
      const running=m.started&&!m.finished,key=m.league+'|'+m.id;
      return `${heading}<article class="live-match ${running?'is-live':''}" data-live-key="${esc(key)}"><div class="live-match-top"><time>${esc(timeText(m.kickoff||m.date))}</time><span class="tag">${LEAGUES[m.league].name}</span><span class="${running?'profit':''}">${m.finished?'已完赛':running?`进行中 ${esc(m.clock||'')}`:'未开赛'}</span>${m.delayed?'<span class="attention">比分待更新</span>':''}</div><a class="live-match-pair" href="${href(m)}"><strong>${esc(m.homeLabel)}</strong><b>${m.started||m.finished?`${m.homeGoals??'—'} : ${m.awayGoals??'—'}`:'VS'}</b><strong>${esc(m.awayLabel)}</strong></a>${handicapHtml(m)}<div class="toolbar"><a class="button quiet compact" href="${href(m)}">${m.finished?'赛后总结 / 赔率分析':'比赛详情 / 赔率分析'} →</a><button class="button secondary compact" data-live-events="${i}" aria-expanded="${opened.has(key)}">进球 · 换人 · 红黄牌</button></div><div class="live-events" ${opened.has(key)?'':'hidden'}>${opened.get(key)||''}</div><details><summary>官方直播入口</summary>${broadcastLinks(m.league,region)}</details><small class="subtle">比分最近更新 ${esc(timeText(m.updatedAt))}</small></article>`;
    }).join(''):'<div class="empty">这个时段没有符合筛选的比赛。可选择其他日期或“全部”状态。</div>';
  }
  async function loadEvents(index){
    const m=rows[index];if(!m)return;const key=m.league+'|'+m.id;
    if(opened.has(key)){opened.delete(key);draw();return;}
    opened.set(key,'<p class="note">正在读取本场事件…</p>');draw();
    try{
      const [response,names]=await Promise.all([fetch(`/api/match?league=${m.league}&match_id=${encodeURIComponent(m.id)}`,{cache:'no-store',signal:AbortSignal.timeout(30000)}),readLeagueSnapshot(m.league,'names').catch(()=>null)]);
      if(!response.ok)throw Error();const detail=await response.json();
      if(detail.league!==m.league||detail.matchId!==m.id||detail.home!==m.home||detail.away!==m.away)throw Error();
      const people=Object.values(detail.lineups||{}).flatMap(s=>s.players||[]);
      const name=p=>names?.names?.[String(people.find(x=>x.espnId===p.espnId)?.playerCode)]?.mandarin||p.name;
      if(opened.has(key))opened.set(key,eventTimeline({...detail,home:m.homeLabel,away:m.awayLabel},name));
    }catch{if(opened.has(key))opened.set(key,`<p class="note">本场事件暂未取得。<a href="${href(m)}">进入比赛详情重新检查</a></p>`);}
    draw();
  }
  main.querySelector('#combined-fixtures').addEventListener('click',e=>{const b=e.target.closest('[data-live-events]');if(b)loadEvents(Number(b.dataset.liveEvents));});
  for(const [id,set] of [['live-league',v=>selected=v],['live-state',v=>state=v],['live-date',v=>date=v],['live-region',v=>region=v]])main.querySelector('#'+id).addEventListener('change',e=>{set(e.target.value);draw();});
  async function refresh(){if(disposed||busy)return;busy=true;const b=main.querySelector('#live-refresh');b.disabled=true;try{feeds=await competitionFeeds();if(!disposed){draw();const expanded=[...opened.keys()];for(const key of expanded){const i=rows.findIndex(m=>m.league+'|'+m.id===key);if(i>=0&&rows[i].started&&!rows[i].finished){opened.delete(key);await loadEvents(i);}}}}finally{busy=false;if(!disposed)b.disabled=false;}}
  main.querySelector('#live-refresh').addEventListener('click',refresh);refresh();
  const timer=setInterval(()=>{if(!document.hidden)refresh();},60000);
  return()=>{disposed=true;clearInterval(timer);};
}
