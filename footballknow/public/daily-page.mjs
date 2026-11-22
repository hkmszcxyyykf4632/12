import {supportsFootballAnalysis} from './football-scope.mjs';
import {LEAGUES} from './league.mjs';
import {main,esc,pageHeading,timeText} from './ui.mjs';
import {competitionFeeds,readLeagueSnapshot} from './competition-feed.mjs';
import {broadcastLinks} from './broadcasts.mjs';
import {eventTimeline} from './match-extras.mjs';
import {selectQuote} from './settlement.mjs';
import {dailyRows,hkDay,hkTime,shiftDay,validDaily} from './daily-core.mjs';
import {handicapAlerts,lineText,quotePhase} from './odds-alerts.mjs';
import {motivationHtml,alertsHtml,globalEventsHtml} from './daily-research.mjs';
import {forecastsHtml,forecastSummaryHtml} from './football-forecasts.mjs';

export function renderLive({leagueId=null}={}){
  let disposed=false,busy=false,feeds=[],snapshot=null,failed=false,paused=false,rows=[],competition=leagueId?'league:'+leagueId:'major',state='all',date=hkDay(Date.now()),region='all',search='',limit=80;
  const opened=new Set(),events=new Map(),disclosures=new Map();const fullForecasts=new Map(),forecastLoading=new Set(),forecastErrors=new Set();let forecasts={},forecastFailed=false,followToday=true,mode=leagueId?'season':'day',season='',teamName='',period='nearby';
  main.innerHTML=`${pageHeading('比赛中心','赛程、即场比分与完场赛果集中查看，预测和复盘按需展开。','<button id="live-refresh" class="button secondary">检查更新</button>')}
    <div class="centre-mode" role="group" aria-label="赛程查看方式"><button type="button" data-centre-mode="day">按日查看</button><button type="button" data-centre-mode="season">联赛赛程</button></div><div class="daily-date-nav" id="daily-date-controls"><button class="button secondary compact" id="daily-prev" aria-label="前一天">← 前一天</button><label>澳门／香港日期<input type="date" id="live-date" value="${date}"></label><button class="button secondary compact" id="daily-next" aria-label="后一天">后一天 →</button><button class="button quiet compact" id="daily-today">今天</button></div>
    <div class="toolbar match-filters"><label>赛事<select id="live-league"><option value="all">全球全部赛事</option></select></label><label hidden>状态<select id="live-state"><option value="all">全部状态</option><option value="live">正在进行</option><option value="scheduled">未开赛</option><option value="finished">已完场</option><option value="alerts">赔率提醒</option></select></label><label>球队或赛事<input id="daily-search" type="search" placeholder="搜索球队、联赛"></label></div><div id="season-filters" class="toolbar match-filters" hidden><label>赛季<select id="centre-season"></select></label><label>范围<select id="centre-period"><option value="nearby">最近及未来七天</option><option value="all">全赛季</option></select></label><label>球队<select id="centre-team"><option value="">全部球队</option></select></label></div><details class="centre-source-options"><summary>资料说明与直播地区</summary><label>观看地区<select id="live-region"><option value="all">全部地区</option><option value="mo">澳门 · MPLUS</option><option value="hk">香港</option><option value="cn">中国内地</option></select></label><p class="note">澳门／香港时间 UTC+8。比分按来源确认状态更新；让球或大小球变动至少 0.5 球、让受方向反转，或同盘口赔率升降至少 15%，触发提醒。</p></details>
    <p id="live-feed-status" class="note" role="status">正在读取每日赛事…</p><div id="daily-summary" class="daily-summary"></div><div id="combined-fixtures"></div><button id="daily-more" class="button secondary" hidden>显示更多比赛</button>`;
  const list=main.querySelector('#combined-fixtures'),href=m=>`./?league=${m.league}#/match/${encodeURIComponent(m.id)}`;
  function options(){
    const select=main.querySelector('#live-league'),extras=new Map((snapshot?.matches||[]).filter(m=>!m.league).map(m=>[m.competitionId,m.competition]));
    select.innerHTML='<option value="all">全球全部赛事</option><option value="major">四大联赛与欧冠 · 分析</option>'+Object.values(LEAGUES).map(l=>`<option value="league:${l.id}">${l.name}</option>`).join('')+[...extras].sort((a,b)=>a[1].localeCompare(b[1],'zh')).map(([id,name])=>`<option value="competition:${esc(id)}">${esc(name)}</option>`).join('');
    if(mode==='season')select.querySelectorAll('option').forEach(o=>{o.disabled=!o.value.startsWith('league:');});
    if([...select.options].some(o=>o.value===competition))select.value=competition;else competition='major';
    seasonOptions();
  }
  function seasonOptions(){
    const feed=feeds.find(f=>'league:'+f.league===competition),seasons=[...new Set((feed?.data?.matches||[]).filter(m=>m.competition===LEAGUES[feed.league].name).map(m=>m.season))].sort().reverse();
    if(!seasons.includes(season))season=feed?.data?.season||seasons[0]||'';
    main.querySelector('#centre-season').innerHTML=seasons.map(v=>`<option ${v===season?'selected':''}>${esc(v)}</option>`).join('');
    const teams=feed?.data?.teams||[];if(!teams.some(t=>t.name===teamName))teamName='';
    main.querySelector('#centre-team').innerHTML='<option value="">全部球队</option>'+teams.map(t=>`<option value="${esc(t.name)}" ${t.name===teamName?'selected':''}>${esc(t.cn)}</option>`).join('');
  }
  function draw(){
    if(disposed)return;
    for(const card of list.querySelectorAll('[data-live-key]'))for(const detail of card.querySelectorAll('details[data-disclosure]'))
      disclosures.set(card.dataset.liveKey+'|'+detail.dataset.disclosure,detail.open);
    main.querySelector('#daily-date-controls').hidden=mode!=='day';
    main.querySelector('#season-filters').hidden=mode!=='season';
    main.querySelectorAll('[data-centre-mode]').forEach(b=>{b.classList.toggle('active',b.dataset.centreMode===mode);b.setAttribute('aria-pressed',String(b.dataset.centreMode===mode));});
    const candidates=dailyRows(snapshot,feeds,{date:mode==='day'?date:'',competition,search,season:mode==='season'?season:'',teamName:mode==='season'?teamName:''}).filter(m=>mode!=='season'||period==='all'||Math.abs(Date.parse(m.kickoff||m.date)-Date.now())<=7*86400000);
    const withAlerts=candidates.map(m=>({...m,alerts:supportsFootballAnalysis(m)?handicapAlerts(m,feeds.find(f=>f.league===m.league)):[]}));
    rows=withAlerts.filter(m=>state==='all'||state==='alerts'&&m.alerts.length||m.state===state);
    const failures=feeds.filter(f=>f.failed).map(f=>LEAGUES[f.league].name);
    main.querySelector('#daily-summary').innerHTML=[['all','全部',candidates.length],['live','进行中',candidates.filter(m=>m.state==='live').length],['scheduled','未开赛',candidates.filter(m=>m.state==='scheduled').length],['finished','已完赛',candidates.filter(m=>m.state==='finished').length],['alerts','赔率提醒',withAlerts.filter(m=>m.alerts.length).length]].map(([key,label,n])=>`<button type="button" data-centre-status="${key}" aria-pressed="${state===key}">${label} <b>${n}</b></button>`).join('');
    const outside=mode==='day'&&snapshot?.window&&(date<snapshot.window.from||date>snapshot.window.to);
    main.querySelector('#live-feed-status').textContent=`显示 ${rows.length} 场 · ${paused?'管理员已暂停同步，显示留存资料':'自动更新中'} · 最近采集 ${timeText(snapshot?.updatedAt)}${failed?' · 全球比分读取失败，保留上次资料':''}${snapshot?.errors?.length>=4?' · 全球赛事本次更新失败，已匹配比赛采用较新的联赛比分':snapshot?.errors?.length?' · 部分赛事来源更新失败':''}${failures.length?' · '+failures.join('、')+'详细资料待更新':''}${outside?' · 此日不在全球实时窗口内，仅显示已收录记录':''}`;
    list.innerHTML=rows.length?rows.slice(0,limit).map((m,i)=>{
      const q=selectQuote(m.quotes,'asian-handicap',m.finished?['closing','latest','preclosing','opening']:['latest','preclosing','opening']);
      const panel=kind=>opened.has(m.key+'|'+kind),toggle=(kind,text)=>`<button class="button secondary compact" data-panel="${kind}" data-index="${i}" aria-expanded="${panel(kind)}">${text}</button>`;
      return `<article class="live-match ${m.state==='live'?'is-live':''} ${m.finished?'is-finished':''}" data-live-key="${esc(m.key)}"><div class="live-match-top"><time>${esc(hkTime(m.kickoff))}</time><span class="tag">${esc(m.competition)}</span><strong class="${m.state==='live'?'profit':''}">${esc(m.status)} ${esc(m.clock||'')}</strong>${m.delayed&&!m.finished?'<span class="attention">比分待更新</span>':''}${m.alerts.length?`<span class="daily-alert-tag">赔率提醒 ${m.alerts.length}</span>`:''}</div>
      <${m.local?'a':'div'} class="live-match-pair" ${m.local?`href="${href(m)}"`:''}><strong>${esc(m.homeLabel)}</strong><b>${m.started||m.finished?`${m.homeGoals??'—'} : ${m.awayGoals??'—'}`:'VS'}</b><strong>${esc(m.awayLabel)}</strong></${m.local?'a':'div'}>
      ${supportsFootballAnalysis(m)?`<div class="forecast-brief">${forecastFailed&&!forecasts[m.dailyId]?'<span class="subtle">预测暂时未读到，可展开重试</span>':forecastSummaryHtml(m,forecasts[m.dailyId])}</div><details class="centre-analysis" data-disclosure="match-analysis"><summary>${m.finished?'预测与赛后复盘':'预测与分析依据'}<span>展开查看</span></summary><div class="live-handicap"><strong>亚洲让球盘</strong>${q?`<span>主队${lineText(q.line)} <b>${q.prices.H.toFixed(2)}</b></span><span>客队${lineText(-q.line)} <b>${q.prices.A.toFixed(2)}</b></span><small>${esc(q.provider)} · ${quotePhase(q)} · 采集 ${esc(timeText(q.fetchedAt))}${m.started&&!q.lastPregame?' · 来源未确认滚球':''}</small>`:'<span class="subtle">暂未取得可核对盘口</span>'}</div>
      ${fullForecasts.has(m.dailyId)?forecastsHtml(m,fullForecasts.get(m.dailyId).value):`<p class="note">${forecastErrors.has(m.dailyId)?'预测读取未成功，请收起后重新打开。':'展开后读取本场预测与详细复盘…'}</p>`}
      <div class="toolbar">${toggle('intent',m.finished?'赛前背景与赛后对照':'积分与比赛背景')}${toggle('odds','赔率提醒与原因')}${toggle('events','进球 · 换人 · 红黄牌')}${m.dailyId?toggle('research','阵容 · 天气 · 走势'):''}${m.local?`<a class="button quiet compact" href="${href(m)}">比赛详情 →</a>`:''}</div>
      <div class="daily-panel" ${panel('intent')?'':'hidden'}>${panel('intent')?motivationHtml(m):''}</div><div class="daily-panel" ${panel('odds')?'':'hidden'}>${panel('odds')?alertsHtml(m,m.alerts):''}</div><div class="daily-panel" ${panel('events')?'':'hidden'}>${panel('events')?events.get(m.key)||globalEventsHtml(m):''}</div><div class="daily-panel" data-research="${esc(m.key)}" ${panel('research')?'':'hidden'}>${panel('research')?events.get(m.key+'|research')||'<p class="note">正在读取阵容、天气与近期走势…</p>':''}</div>
      </details>`:''}
      ${m.league?`<details><summary>官方直播入口</summary>${broadcastLinks(m.league,region)}</details>`:''}<small class="subtle">比分采集 ${esc(timeText(m.updatedAt))} · ${m.scoreSource||m.source?`<a href="${esc(m.scoreSource||m.source)}" target="_blank" rel="noopener noreferrer">赛事来源 ↗</a>`:''}</small></article>`;
    }).join(''):'<div class="empty">这个日期没有符合筛选的已收录比赛。可切换前后一天或改选全部状态。</div>';
    for(const card of list.querySelectorAll('[data-live-key]'))for(const detail of card.querySelectorAll('details[data-disclosure]')){
      const key=card.dataset.liveKey+'|'+detail.dataset.disclosure;if(disclosures.has(key))detail.open=disclosures.get(key);
    }
    main.querySelector('#daily-more').hidden=rows.length<=limit;
  }
  async function loadForecast(m){
    if(!m.dailyId||forecastLoading.has(m.dailyId)||Date.now()-(fullForecasts.get(m.dailyId)?.at||0)<60000)return;
    forecastLoading.add(m.dailyId);forecastErrors.delete(m.dailyId);
    try{const r=await fetch(`/api/daily-football/${encodeURIComponent(m.dailyId)}/forecast`,{cache:'no-store',signal:AbortSignal.timeout(45000)});if(!r.ok)throw Error();fullForecasts.set(m.dailyId,{value:await r.json(),at:Date.now()});}
    catch{forecastErrors.add(m.dailyId);}finally{forecastLoading.delete(m.dailyId);draw();}
  }
  list.addEventListener('toggle',e=>{if(!e.target.matches('details.centre-analysis')||!e.target.isConnected)return;const key=e.target.closest('[data-live-key]').dataset.liveKey,previous=disclosures.get(key+'|match-analysis');disclosures.set(key+'|match-analysis',e.target.open);if(e.target.open&&!previous){const m=rows.find(r=>r.key===key);if(m)loadForecast(m);}},true);
  async function loadEvents(m){
    if(!m.local)return;
    try{
      const [response,names]=await Promise.all([fetch(`/api/match?league=${m.league}&match_id=${encodeURIComponent(m.id)}`,{cache:'no-store',signal:AbortSignal.timeout(30000)}),readLeagueSnapshot(m.league,'names').catch(()=>null)]);
      if(!response.ok)throw Error();const detail=await response.json();
      if(detail.league!==m.league||detail.matchId!==m.id||detail.home!==m.home||detail.away!==m.away)throw Error();
      const people=Object.values(detail.lineups||{}).flatMap(s=>s.players||[]);
      events.set(m.key,eventTimeline({...detail,home:m.homeLabel,away:m.awayLabel},p=>names?.names?.[String(people.find(x=>x.espnId===p.espnId)?.playerCode)]?.mandarin||p.name));
    }catch{events.set(m.key,globalEventsHtml(m));}draw();
  }
  async function loadResearch(m){
    try{const {matchResearchHtml}=await import('./match-research.mjs');const r=await fetch(`/api/daily-football/${m.dailyId}/research`,{cache:'no-store',signal:AbortSignal.timeout(90000)});if(!r.ok)throw Error();events.set(m.key+'|research',matchResearchHtml(await r.json()));}
    catch{events.set(m.key+'|research','<p class="note">本场补充资料暂时无法读取，请稍后收起再打开。已有比分与赛前记录继续保留。</p>');}draw();
  }
  list.addEventListener('click',e=>{const b=e.target.closest('[data-panel]');if(!b)return;const m=rows[Number(b.dataset.index)];if(!m)return;const key=m.key+'|'+b.dataset.panel;if(opened.has(key))opened.delete(key);else{opened.add(key);if(b.dataset.panel==='events')loadEvents(m);if(b.dataset.panel==='research')loadResearch(m);}draw();});
  for(const [id,set] of [['live-league',v=>{competition=v;season='';teamName='';seasonOptions();}],['live-state',v=>state=v],['live-date',v=>{date=v||hkDay(Date.now());followToday=!v;}],['live-region',v=>region=v]])main.querySelector('#'+id).addEventListener('change',e=>{set(e.target.value);limit=80;draw();});
  main.querySelectorAll('[data-centre-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.centreMode;if(mode==='season'&&!competition.startsWith('league:'))competition='league:'+(leagueId||'epl');limit=80;options();draw();});
  main.querySelector('#daily-summary').onclick=e=>{const b=e.target.closest('[data-centre-status]');if(b){state=b.dataset.centreStatus;main.querySelector('#live-state').value=state;limit=80;draw();}};
  main.querySelector('#centre-season').onchange=e=>{season=e.target.value;period='all';main.querySelector('#centre-period').value=period;limit=80;draw();};
  main.querySelector('#centre-period').onchange=e=>{period=e.target.value;limit=80;draw();};
  main.querySelector('#centre-team').onchange=e=>{teamName=e.target.value;limit=80;draw();};
  main.querySelector('#daily-search').addEventListener('input',e=>{search=e.target.value;limit=80;draw();});
  const changeDate=(value,today=false)=>{date=value;followToday=today;main.querySelector('#live-date').value=date;limit=80;draw();};
  main.querySelector('#daily-prev').onclick=()=>changeDate(shiftDay(date,-1));main.querySelector('#daily-next').onclick=()=>changeDate(shiftDay(date,1));main.querySelector('#daily-today').onclick=()=>changeDate(hkDay(Date.now()),true);
  main.querySelector('#daily-more').onclick=()=>{limit+=80;draw();};
  async function refresh(){
    if(disposed||busy)return;busy=true;const b=main.querySelector('#live-refresh');b.disabled=true;
    if(followToday&&date!==hkDay(Date.now())){date=hkDay(Date.now());main.querySelector('#live-date').value=date;limit=80;}
    try{const result=await Promise.allSettled([competitionFeeds(),fetch('./daily-football.json',{cache:'no-cache',signal:AbortSignal.timeout(15000)}).then(async r=>{if(!r.ok)throw Error();const data=await r.json();if(!validDaily(data))throw Error();return data;}),fetch('./sync-status.json',{cache:'no-cache',signal:AbortSignal.timeout(12000)}).then(r=>r.json()),fetch('/api/football-forecasts?compact=true',{cache:'no-store',signal:AbortSignal.timeout(15000)}).then(async r=>{if(!r.ok)throw Error();return r.json();})]);
      forecastFailed=result[3].status!=='fulfilled';if(!forecastFailed)forecasts=result[3].value.matches||{};
      if(disposed)return;if(result[0].status==='fulfilled')feeds=result[0].value;failed=result[1].status!=='fulfilled';if(!failed)snapshot=result[1].value;if(result[2].status==='fulfilled')paused=Boolean(result[2].value.paused);options();draw();
      for(const m of rows.filter(m=>disclosures.get(m.key+'|match-analysis')))loadForecast(m);
      for(const m of rows.filter(m=>m.state==='live'&&opened.has(m.key+'|events')))await loadEvents(m);
      for(const m of rows.filter(m=>m.dailyId&&opened.has(m.key+'|research')))await loadResearch(m);
    }finally{busy=false;if(!disposed)b.disabled=false;}
  }
  const onVisible=()=>{if(!document.hidden)refresh();};
  main.querySelector('#live-refresh').onclick=refresh;refresh();const timer=setInterval(onVisible,60000);
  document.addEventListener('visibilitychange',onVisible);
  return()=>{disposed=true;clearInterval(timer);document.removeEventListener('visibilitychange',onVisible);};
}
