import {main,esc,pageHeading} from './ui.mjs';
import {portrait} from './portraits.mjs';
import {table,val,stamp,clock,horseLink,placeBadge,racingNav,racingJson,groupRunners} from './racing-ui.mjs';
import {quoteFor,quoteMarkup,dividendsHtml} from './racing-pools.mjs';

const meetingKey=r=>r.id.replace(/-\d+$/,'');
const raceClock=r=>r.status==='cancelled'?'已取消':r.offTime?clock(r.offTime):r.status==='finished'?'已完赛':'待公布';
const statusText=r=>r.resultOfficial?'正式赛果':r.status==='provisional'?'初步赛果':r.status==='cancelled'?'赛事取消':'待开跑';
export function renderRacingHub(){
  const controller=new AbortController();let disposed=false;
  main.innerHTML=pageHeading('香港赛马','赛马日、即时赛果、独赢位置连赢赔率与骑练出赛分组。')+racingNav('racing')+'<div id="meeting-cards" class="loading">正在读取赛马日…</div>';
  async function refresh(){try{const data=await racingJson('meetings.json',controller.signal);if(disposed)return;
    const meetings=new Map();for(const race of data.races||[]){const key=meetingKey(race);if(!meetings.has(key))meetings.set(key,{id:key,date:race.date,course:race.courseName,races:[]});meetings.get(key).races.push(race);}
    const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    const rows=[...meetings.values()].sort((a,b)=>(a.date<today)-(b.date<today)||(a.date>=today?a.date.localeCompare(b.date):b.date.localeCompare(a.date)));
    main.querySelector('#meeting-cards').className='';main.querySelector('#meeting-cards').innerHTML=`<div class="racing-hub-hero"><div><span class="eyebrow">HONG KONG RACING</span><h2>每一个赛马日，一页看清。</h2><p>出赛马匹、骑练分组、即时赛果和赔率同步呈现。</p></div><a class="button" href="#/horses">浏览马匹资料 →</a></div><div class="meeting-grid">${rows.map(m=>{const done=m.races.filter(r=>r.resultOfficial).length;return `<article class="meeting-card"><div class="meeting-card-top"><span>${m.date>=today?'赛程与即时资料':'已举行赛马日'}</span><span>${m.course}</span></div><h2>${esc(m.date)} <small>${new Date(m.date+'T12:00:00+08:00').toLocaleDateString('zh-CN',{weekday:'long'})}</small></h2><p>${m.races.length} 场已收录 · ${done} 场正式赛果</p><div class="meeting-race-dots">${m.races.sort((a,b)=>a.raceNo-b.raceNo).map(r=>`<a href="#/race/${r.id}" class="${r.resultOfficial?'completed':''}" title="第 ${r.raceNo} 场 · ${esc(r.name)}">${r.raceNo}</a>`).join('')}</div><div class="meeting-actions"><a class="button" href="#/racing-day/${m.id}">${done?'赛果与分组':'赛马日详情'} →</a><a href="#/racing-day/${m.id}/trainer">练马师分场表</a><a href="#/racing-day/${m.id}/jockey">骑师分场表</a></div></article>`;}).join('')}</div><p class="note">即时赛果与赔率每 60 秒检查，详细赛果每 5 分钟更新。最近检查 ${stamp(data.liveCheckedAt||data.updatedAt)}。每个已收录赛马日均保留独立页面。</p>`;
  }catch(e){if(!disposed)main.querySelector('#meeting-cards').innerHTML=`<div class="empty">${esc(e.message)}</div>`;}}
  refresh();const timer=setInterval(()=>{if(!document.hidden)refresh();},60000);return()=>{disposed=true;controller.abort();clearInterval(timer);};
}

export function renderRacingDay(id,initial='results'){
  const controller=new AbortController();let mode=['trainer','jockey','runners'].includes(initial)?initial:'results',races=[],schedule={},people={},missing=0,query='',busy=false;
  if(!/^\d{4}-\d{2}-\d{2}-(ST|HV)$/.test(id)){main.innerHTML='<div class="empty">赛马日编号不正确。</div>';return()=>{};}
  const day=id.slice(0,10),course=id.endsWith('ST')?'沙田':'跑马地';
  main.innerHTML=pageHeading(`${day} · ${course}`,'赛马日资料按香港时间显示。')+racingNav('racing')+'<div id="racing-day" class="loading">读取出赛马匹和赛果…</div>';
  function paint(){const target=main.querySelector('#racing-day');if(!target)return;target.className='';
    const official=races.filter(r=>r.resultOfficial).length,entries=races.flatMap(r=>r.entries||[]).filter(h=>!h.withdrawn);
    target.innerHTML=`<div class="racing-day-heading"><div><span class="eyebrow">RACE DAY · ${course}</span><h2>${day}</h2></div><label>选择赛马日<select id="day-select">${[...new Map((schedule.races||[]).map(r=>[meetingKey(r),r])).values()].sort((a,b)=>b.date.localeCompare(a.date)).map(r=>`<option value="${meetingKey(r)}" ${meetingKey(r)===id?'selected':''}>${r.date} ${r.courseName}</option>`).join('')}</select></label><button class="button secondary" id="day-refresh">检查更新</button></div><div class="racing-kpis"><div><span>已收录场次</span><strong>${races.length}</strong></div><div><span>正式赛果</span><strong>${official} / ${races.length}</strong></div><div><span>出赛马匹</span><strong>${entries.length}</strong></div><div><span>资料检查（香港时间）</span><strong class="kpi-time">${stamp(schedule.liveCheckedAt||schedule.updatedAt)}</strong></div></div><div class="race-number-nav">${races.map(r=>`<a href="#/race/${r.id}" class="${r.resultOfficial?'completed':''}"><b>${r.raceNo}</b><small>${raceClock(r)}</small></a>`).join('')}</div><div class="tabs">${[['results','即时赛果'],['runners','按场次出赛'],['trainer','练马师分组'],['jockey','骑师分组']].map(([k,n])=>`<button data-day-mode="${k}" class="${mode===k?'active':''}">${n}</button>`).join('')}</div><div id="day-content"></div><p class="note">${missing?`${missing} 场资料暂未读到；` : ''}初步赛果与正式赛果分开标示。骑练头马与前三统计只计算正式赛果，退出马匹不计。</p>`;
    target.querySelector('#day-select').onchange=e=>location.hash='#/racing-day/'+e.target.value;
    target.querySelector('#day-refresh').onclick=refresh;
    target.querySelectorAll('[data-day-mode]').forEach(b=>b.onclick=()=>{mode=b.dataset.dayMode;query='';paint();});
    const body=target.querySelector('#day-content');
    if(mode==='trainer'||mode==='jockey'){
      const peopleMap=new Map((people[mode==='trainer'?'trainers':'jockeys']||[]).map(p=>[p.id,p]));
      body.innerHTML=`<div class="toolbar"><label class="search-field">搜索${mode==='trainer'?'练马师':'骑师'}或马匹<input id="day-group-search" type="search" value="${esc(query)}" placeholder="输入名字"></label><span class="note">每格列出场次内的马号、马名和赛果</span></div><div id="day-group-table"></div>`;
      const drawGroups=()=>{const groups=groupRunners(races,mode).filter(g=>(g.name+' '+g.runs.map(x=>x.horse.name).join(' ')).includes(query));
        body.querySelector('#day-group-table').innerHTML=table([mode==='trainer'?'练马师':'骑师','出赛 / 头马 / 前三',...races.map(r=>`<a href="#/race/${r.id}">第 ${r.raceNo} 场<small>${raceClock(r)}</small></a>`)],groups.map(g=>{const person=peopleMap.get(g.id);return [`<div class="person-identity">${portrait(person?.photo,g.name)}<span>${mode==='trainer'?`<a href="#/horses/trainer/${encodeURIComponent(g.id)}"><b>${esc(g.name)}</b></a>`:`<b>${esc(g.name)}</b>`}</span></div>`,`${g.runs.filter(x=>!x.horse.withdrawn).length} / <strong>${g.wins}</strong> / ${g.top3}`,...races.map(r=>g.runs.filter(x=>x.race.id===r.id).map(({horse})=>`<div class="group-run ${horse.place===1&&r.resultOfficial?'group-winner':''}"><span class="runner-number">${esc(horse.number)}</span>${horseLink(horse)}${placeBadge(horse)}</div>`).join('')||'—')];}),'racing-matrix');};
      body.querySelector('#day-group-search').oninput=e=>{query=e.target.value;drawGroups();};drawGroups();
    }else{
      body.innerHTML=races.map(r=>{if(r.status==='cancelled')return `<section class="race-day-block"><div class="race-day-title"><span class="race-round">${r.raceNo}</span><h3>赛事取消</h3><span class="race-status">马会已公布</span></div><p>本场取消，独赢、位置及连赢退款；不计入骑练赛果统计。</p>${dividendsHtml(r)}</section>`;const finished=r.resultOfficial||r.status==='provisional';const rows=[...r.entries].sort((a,b)=>mode==='results'&&finished?(a.place??99)-(b.place??99):Number(a.number)-Number(b.number));
        return `<section class="race-day-block"><div class="race-day-title"><span class="race-round">${r.raceNo}</span><div><h3><a href="#/race/${r.id}">${esc(r.name)}</a></h3><span>${raceClock(r)} · ${val(r.distance)} 米 · ${esc(r.class)} · ${esc(r.going)}</span></div><span class="race-status">${statusText(r)}</span><a href="#/race/${r.id}">完整资料与赔率 →</a></div>${table([mode==='results'?'名次':'状态','马号 / 马匹','档位','骑师','练马师','独赢','位置'],rows.map(h=>[placeBadge(h),`${esc(h.number)} · ${horseLink(h)}`,val(h.draw),esc(h.jockey?.name||''),esc(h.trainer?.name||''),quoteFor(r,'WIN',h.number)?quoteMarkup(quoteFor(r,'WIN',h.number)):val(h.winOdds),quoteFor(r,'PLA',h.number)?quoteMarkup(quoteFor(r,'PLA',h.number)):finished?'未收录':'待公布']))}${mode==='results'&&finished?dividendsHtml(r):''}</section>`;}).join('');
    }
  }
  async function refresh(){if(busy)return;busy=true;try{
    schedule=await racingJson('meetings.json',controller.signal);const list=(schedule.races||[]).filter(r=>meetingKey(r)===id).sort((a,b)=>a.raceNo-b.raceNo);
    const results=await Promise.allSettled(list.map(r=>racingJson('races/'+r.id+'.json',controller.signal)));
    if(controller.signal.aborted)return;missing=results.filter(r=>r.status==='rejected').length;
    const saved=new Map(races.map(r=>[r.id,r]));results.forEach(r=>{if(r.status==='fulfilled')saved.set(r.value.id,r.value);});races=[...saved.values()].sort((a,b)=>a.raceNo-b.raceNo);
    if(!races.length)throw Error('本赛马日尚未收录。');paint();
  }catch(e){if(!controller.signal.aborted&&!races.length)main.querySelector('#racing-day').innerHTML=`<div class="empty">${esc(e.message)} <a href="#/racing">查看已收录赛马日</a></div>`;}finally{busy=false;}}
  racingJson('people.json',controller.signal).then(d=>{people=d;if(races.length)paint();}).catch(()=>{});
  refresh();const timer=setInterval(()=>{if(!document.hidden&&!main.querySelector('#day-group-search:focus'))refresh();},60000);return()=>{controller.abort();clearInterval(timer);};
}
