import {api} from './api.mjs';
import {main,esc,pageHeading} from './ui.mjs';

const val=x=>x==null||x===''?'—':esc(String(x));
const stamp=x=>x?new Date(x).toLocaleString('zh-CN',{timeZone:'Asia/Hong_Kong',hour12:false}):'—';
const source=(url,label='马会原始资料')=>url&&/^https:\/\/racing\.hkjc\.com\//.test(url)?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:'';
const horseLink=h=>`<a class="racing-horse" href="#/horse/${esc(h.id)}"><strong>${esc(h.name||h.brand||h.id)}</strong><small>${esc(h.brand||h.id.split('_').at(-1))}</small></a>`;
const person=p=>p?.source?source(p.source,p.name):val(p?.name);
const table=(headers,rows)=>rows.length?`<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(c=>`<tr>${c.map(v=>`<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<div class="empty">暂未收录这项资料。</div>';
async function json(path,signal){const r=await fetch(path,{cache:'no-cache',signal});if(!r.ok)throw Error('资料正在同步，请稍后重新读取。');return r.json();}

export function renderRacing(){
  const controller=new AbortController();let schedule={},catalogue={},tab='upcoming',query='',page=0;
  main.innerHTML=pageHeading('香港赛马','赛期、排位表、赛果与马匹资料，按香港时间显示。',source('https://racing.hkjc.com/zh-hk/local/information/fixture','马会完整赛期'))+
    '<div class="tabs racing-tabs" role="tablist" aria-label="赛马资料"><button data-racing-tab="upcoming" role="tab" aria-selected="true" class="active">赛程与排位</button><button data-racing-tab="results" role="tab" aria-selected="false">赛果与赛后评价</button><button data-racing-tab="horses" role="tab" aria-selected="false">马匹档案</button></div><div id="racing-body" class="loading">正在读取马会资料…</div><p id="racing-source" class="note"></p>';
  function paint(){
    const target=main.querySelector('#racing-body');if(!target)return;
    target.className='';
    if(tab==='horses'){
      target.innerHTML='<div class="toolbar"><label class="search-field">搜索马匹<input id="horse-search" type="search" placeholder="马名或烙号，例如禾道威、J463" value="'+esc(query)+'"></label><p class="note">目录 '+(catalogue.horses?.length||0)+' 匹；打开档案获取血统及详细往绩</p></div><div id="horse-list"></div><div class="toolbar"><button class="button secondary compact" id="horse-prev">上一页</button><span id="horse-page"></span><button class="button secondary compact" id="horse-next">下一页</button></div>';
      const paintHorses=()=>{const list=(catalogue.horses||[]).filter(h=>(h.name+' '+h.brand).toLowerCase().includes(query.toLowerCase())),pages=Math.max(1,Math.ceil(list.length/40));page=Math.min(page,pages-1);target.querySelector('#horse-list').innerHTML=table(['马匹','烙号','档案'],list.slice(page*40,page*40+40).map(h=>[horseLink(h),esc(h.brand),`<a href="#/horse/${h.id}">血统 · 往绩 · 场地表现</a>`]));target.querySelector('#horse-page').textContent=`${list.length} 匹 · 第 ${page+1} / ${pages} 页`;target.querySelector('#horse-prev').disabled=page===0;target.querySelector('#horse-next').disabled=page>=pages-1;};
      target.querySelector('#horse-search').addEventListener('input',e=>{query=e.target.value;page=0;paintHorses();});target.querySelector('#horse-prev').onclick=()=>{page--;paintHorses();};target.querySelector('#horse-next').onclick=()=>{page++;paintHorses();};paintHorses();
    }else{
      const finished=tab==='results';const races=(schedule.races||[]).filter(r=>(r.status==='finished')===finished).sort((a,b)=>(finished?b.date.localeCompare(a.date):a.date.localeCompare(b.date))||a.raceNo-b.raceNo);
      target.innerHTML=table(['赛期 / 马场','场次与赛事','时间 / 状态','条件','出赛马匹','研究'],races.map(r=>[`${esc(r.date)}<small>${esc(r.courseName)}</small>`,`<a href="#/race/${esc(r.id)}"><b>第 ${r.raceNo} 场 · ${esc(r.name)}</b></a>`,finished?'已出赛果':r.offTime?stamp(r.offTime):'待公布',`${val(r.distance)} 米<small>${esc(r.class||'')} · ${esc(r.going||'')}</small>`,val(r.runners),`<a href="#/race/${r.id}">${finished?'赛果与评价':'排位与预测'} →</a>`]));
      if(!races.length)target.innerHTML='<div class="empty">当前没有已收录的'+(finished?'正式赛果':'排位表')+'，可查看马会完整赛期。</div>';
    }
    main.querySelector('#racing-source').innerHTML='香港赛马会公开资料 · 赛事最近检查 '+stamp(schedule.updatedAt)+'；马匹目录 '+stamp(catalogue.updatedAt)+'。赛事每 5 分钟检查，马匹档案按需缓存。'+(schedule.failed?.length?'部分场次等待来源更新。':'');
  }
  main.querySelectorAll('[data-racing-tab]').forEach(button=>button.addEventListener('click',()=>{tab=button.dataset.racingTab;main.querySelectorAll('[data-racing-tab]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-selected',String(b===button));});paint();}));
  async function load(){try{[schedule,catalogue]=await Promise.all([json('./racing/meetings.json',controller.signal),json('./racing/catalogue.json',controller.signal)]);if(!controller.signal.aborted)paint();}catch(error){if(!controller.signal.aborted)main.querySelector('#racing-body').innerHTML='<div class="empty">'+esc(error.message)+'</div>';}}
  load();const timer=setInterval(()=>{if(!document.hidden&&tab!=='horses')load();},60000);return()=>{controller.abort();clearInterval(timer);};
}

function evaluationHtml(state,race){
  const e=state.evaluation,phase=race.status==='finished'?'post':'pre';
  const report=state.reports?.[phase],prior=state.reports?.pre;
  const name=id=>race.entries.find(h=>h.id===id)?.name||id;
  let html=`<div class="forecast-rates"><div><span>首选胜出命中率</span><strong>${e.evaluated?(e.wins/e.evaluated*100).toFixed(1)+'%':'等待赛果验证'}</strong><small>${e.wins} / ${e.evaluated} 次有效预测 · ${e.pending} 次待赛果 · ${e.void} 次作废</small></div><div><span>首选前三名率</span><strong>${e.evaluated?(e.top3/e.evaluated*100).toFixed(1)+'%':'等待赛果验证'}</strong><small>前三名统计与胜出统计分开计算</small></div></div>`;
  if(report){html+='<div class="research-summary">'+(report.pick?'<p class="racing-pick">首选：'+esc(name(report.pick))+'</p><p>关注：'+report.shortlist.map(id=>esc(name(id))).join(' · ')+'</p>':'')+report.summary.map(p=>'<p>'+esc(p)+'</p>').join('')+'<p class="note">DeepSeek · '+esc(report.model)+' · '+stamp(report.issuedAt)+'</p><details><summary>更多详细资料</summary>'+report.details.map(d=>'<h3>'+esc(d.title)+'</h3><p>'+esc(d.text)+'</p>').join('')+'</details></div>';}
  else html+='<div class="empty">'+(phase==='pre'?'尚未发布本场预测，管理员可使用已配置的 DeepSeek 生成。':'管理员可生成赛后评价，结合实际赛果复盘。')+'</div>';
  if(phase==='post')html+='<details class="racing-original"><summary>原始赛前预测与验证</summary>'+(prior?'<p>发布：'+stamp(prior.issuedAt)+' · 首选 '+esc(name(prior.pick))+'</p>'+prior.summary.map(p=>'<p>'+esc(p)+'</p>').join('')+'<p>验证：'+(state.outcome?.status==='evaluated'?'实际名次 '+val(state.outcome.position)+'；'+(state.outcome.win?'首选胜出命中':'首选胜出未命中'):esc(state.outcome?.reason||'等待完整赛果'))+'</p>':'<p>本场没有赛前发布的预测，不计入命中率。</p>')+'</details>';
  return html+'<p class="note">赛前预测在开跑前固定保存。正式赛果发布后计算首选胜出和前三名结果；退出作废。所有有效预测均纳入，不包含赛后补写的判断。</p>';
}

export function renderRace(id){
  const controller=new AbortController();let race,analyzing=false;
  main.innerHTML=pageHeading('赛马详情','正在读取本场资料。','<a class="button secondary" href="#/racing">香港赛马</a>')+'<div id="race-content" class="loading">正在读取排位及赛果…</div>';
  async function analysis(generate=false){
    const button=main.querySelector('#race-generate'),msg=main.querySelector('#race-ai-message');if(!button)return;button.disabled=true;analyzing=true;
    try{const value=await api('/api/racing/races/'+id+'/analysis'+(generate?'?phase='+(race.status==='finished'?'post':'pre'):''),{signal:controller.signal,timeout:90000,...(generate?{method:'POST'}:{})});if(controller.signal.aborted)return;main.querySelector('#race-analysis').innerHTML=evaluationHtml(value,race);msg.textContent=generate?'分析已保存。':'';}
    catch(error){if(!controller.signal.aborted)msg.innerHTML=esc(error.message)+' <a href="#/admin">管理后台</a>';}
    finally{analyzing=false;if(!controller.signal.aborted)button.disabled=false;}
  }
  async function load(){
    try{
      race=await api('/api/racing/races/'+id,{signal:controller.signal});if(controller.signal.aborted)return;
      const finished=race.status==='finished',winner=race.entries.filter(e=>e.place===1);
      main.innerHTML=pageHeading(`${race.courseName} · 第 ${race.raceNo} 场`,race.date+' · '+race.name,'<a class="button secondary" href="#/racing">香港赛马</a>')+
        '<div class="research-summary racing-race-head"><div><span>'+(finished?'正式赛果':'排位表')+'</span><h2>'+esc(race.name)+'</h2><p>'+esc(race.track)+' · '+esc(race.class)+'</p><p>'+(race.offTime?'香港时间 '+stamp(race.offTime):'赛事日期 '+esc(race.date))+'</p></div><div><strong>'+val(race.distance)+'<small> 米</small></strong><p>'+race.entries.length+' 匹已收录</p></div></div>'+
        (finished?'<section><h2>赛后结果摘要</h2><div class="research-summary"><p>'+winner.map(h=>esc(h.name)+'（'+esc(h.number)+'号）以 '+val(h.finishTime)+' 完赛，名列第一').join('；')+'。</p><p>前列马匹：'+race.entries.filter(e=>e.place&&e.place<=3).map(h=>val(h.position)+'名 '+esc(h.name)).join(' · ')+'。完整名次、沿途走位及独赢赔率列于下表。</p></div></section>':'')+
        '<section><div class="section-head"><h2>'+(finished?'赛果详情':'出赛马匹')+'</h2>'+source(race.source,finished?'马会赛果与重播':'马会排位表')+'</div>'+table(finished?['名次','马号 / 马匹','骑师 / 练马师','档位','负磅 / 体重','头马距离','沿途走位','完成时间','赛后独赢赔率']:['马号 / 马匹','近六仗','档位','骑师 / 练马师','负磅 / 体重','评分','装备','父系 / 母系'],race.entries.map(h=>finished?[val(h.position),val(h.number)+' · '+horseLink(h),person(h.jockey)+'<small>'+person(h.trainer)+'</small>',val(h.draw),val(h.weight)+' / '+val(h.bodyWeight),val(h.margin),val(h.running),val(h.finishTime),val(h.winOdds)]:[val(h.number)+' · '+horseLink(h)+(h.withdrawn?'<span class="attention">退出</span>':''),val(h.recent),val(h.draw),person(h.jockey)+'<small>'+person(h.trainer)+'</small>',val(h.weight)+' / '+val(h.bodyWeight),val(h.rating),val(h.equipment),val(h.sire)+'<small>'+val(h.dam)+'</small>']))+'</section>'+
        '<section><div class="section-head"><h2>'+(finished?'赛后评价':'赛前预测')+'</h2><button class="button" id="race-generate">生成'+(finished?'赛后评价':'赛前预测')+'</button></div><p id="race-ai-message" role="status"></p><div id="race-analysis" class="loading">读取分析记录…</div></section><p class="note">来源：香港赛马会 · 最近采集 '+stamp(race.updatedAt)+'。负磅及排位体重单位为磅。'+(finished?'独赢赔率为赛果页公布的赛后资料。':'排位、骑师及场地状况可能更改。')+'</p>';
      main.querySelector('#race-generate').onclick=()=>analysis(true);analysis();
    }catch(error){if(!controller.signal.aborted)main.innerHTML=pageHeading('赛马详情','','<a href="#/racing">返回香港赛马</a>')+'<div class="empty">'+esc(error.message)+'</div>';}
  }
  load();const timer=setInterval(()=>{if(!document.hidden&&!analyzing&&race?.status==='scheduled')load();},60000);return()=>{controller.abort();clearInterval(timer);};
}

export function renderHorse(id){
  const controller=new AbortController();let retry;
  main.innerHTML=pageHeading('马匹档案','正在读取血统、往绩和场地表现。','<a class="button secondary" href="#/racing">香港赛马</a>')+'<div id="horse-detail" class="loading">正在读取马匹资料…</div>';
  async function load(){
    try{
      const h=await api('/api/racing/horses/'+encodeURIComponent(id),{signal:controller.signal,timeout:45000});if(controller.signal.aborted)return;
      if(h.pending){retry=setTimeout(load,3000);return;}
      if(!h.profile){main.querySelector('#horse-detail').innerHTML='<div class="empty">'+esc(h.message||'马匹资料尚未更新。')+'</div>';return;}
      const p=h.profile,b=h.pedigree||{};
      main.innerHTML=pageHeading(h.name+' · '+h.brand,'香港赛马 · 马匹档案','<a class="button secondary" href="#/racing">香港赛马</a>')+
        '<section><h2>基本资料</h2><dl class="identity-grid">'+Object.entries(p).filter(([k])=>!['父系','母系','外祖父'].includes(k)).map(([k,v])=>'<div><dt>'+esc(k)+'</dt><dd>'+val(v)+'</dd></div>').join('')+'</dl></section>'+
        '<section><h2>血统</h2><div class="racing-pedigree">'+[['父系',b.sire],['母系',b.dam],['外祖父',b.damsire]].map(([k,v])=>'<div><span>'+k+'</span><strong>'+val(v)+'</strong></div>').join('')+'</div></section>'+
        '<section><h2>场地与途程表现</h2><p class="note">按已收录实际出赛计算。前三名率＝进入前三次数／出赛次数；退出不计。少于 5 场标为样本较少。血统作为背景，适应表现以往绩为依据。</p><div class="racing-suitability">'+Object.entries(h.suitability||{}).map(([key,rows])=>'<div><h3>'+({course:'马场',surface:'跑道类型',distance:'途程（米）',going:'场地状况'}[key])+'</h3>'+table(['条件','出赛','冠军','前三','胜出率 / 前三率'],rows.map(r=>[esc(r.label)+(r.lowSample?'<small class="attention">样本较少</small>':''),r.starts,r.wins,r.top3,`${(r.wins/r.starts*100).toFixed(1)}% / ${(r.top3/r.starts*100).toFixed(1)}%`]))+'</div>').join('')+'</div></section>'+
        '<section><h2>历次赛绩</h2><p class="note">'+esc(h.coverage)+' · 当前 '+h.records.length+' 场</p>'+table(['日期 / 赛事','名次','马场 / 跑道','途程 / 场地','班次 / 评分','档位','骑师 / 练马师','负磅 / 体重','头马距离','沿途走位','完成时间','独赢赔率','装备'],h.records.map(r=>[source(r.source,r.date)||esc(r.date),val(r.position),esc(r.track),val(r.distance)+' 米<small>'+esc(r.going)+'</small>',esc(r.class)+' / '+val(r.rating),esc(r.draw),esc(r.jockey)+'<small>'+esc(r.trainer)+'</small>',val(r.weight)+' / '+val(r.bodyWeight),esc(r.margin),esc(r.running),esc(r.finishTime),val(r.winOdds),esc(r.equipment)]))+'</section><p class="note">'+source(h.source)+' · 最近采集 '+stamp(h.updatedAt)+(h.message?' · '+esc(h.message):'')+'。奖金单位为港元；负磅及排位体重单位为磅。</p>';
    }catch(error){if(!controller.signal.aborted)main.querySelector('#horse-detail').innerHTML='<div class="empty">'+esc(error.message)+'</div>';}
  }
  load();return()=>{controller.abort();clearTimeout(retry);};
}
