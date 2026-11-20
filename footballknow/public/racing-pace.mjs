import {api} from './api.mjs';
import {esc} from './ui.mjs';
import {table,stamp} from './racing-ui.mjs';

export const paceNames={slow:'偏慢',normal:'正常',fast:'偏快',unknown:'资料不足'};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export function scenarioPosition(runner,scenario,progress,total){
  if(!Number.isFinite(runner.earlyPosition))return null;
  const early=clamp(runner.earlyPosition,1,total),gain=clamp(runner.lateGain||0,-3,3);
  const forward=['放头','跟前'].includes(runner.style),back=runner.style==='后追';
  const adjustment=scenario==='fast'?(forward?1.5:back?-1.5:-.5):scenario==='slow'?(forward?-1:back?1.5:.5):0;
  const final=clamp(early-gain+adjustment,1,total),start=clamp(runner.draw||early,1,total);
  return progress<.3?start+(early-start)*progress/.3:early+(final-early)*(progress-.3)/.7;
}
export function paceEffect(r,pace){
  if(r.earlyPosition===null)return '往绩不足，暂不判断步速利弊';
  if(pace==='fast')return ['放头','跟前'].includes(r.style)?'前段争位消耗可能增加，留意能否放松领跑':r.style==='后追'?'前列消耗增大时可能受惠，仍需顺畅冲刺路线':'可观察能否避开前段争抢并及时跟进';
  if(pace==='slow')return ['放头','跟前'].includes(r.style)?'较易保存体力，留意直路能否及时加速':r.style==='后追'?'前列可能保留体力，需要更早启动追赶':'留意位置是否太后及末段加速时机';
  return '主要对照本马近况、途程、档位和末段走位';
}

export function mountPaceSimulation(target,race){
  const controller=new AbortController();let snapshot=null,prediction=null,scenario='normal',progress=0,timer=null;
  const stop=()=>{clearInterval(timer);timer=null;const b=target.querySelector('[data-pace-play]');if(b)b.textContent='播放模拟';};
  function projection(){
    if(!snapshot)return;
    const runners=snapshot.runners.filter(r=>!snapshot.withdrawnIds.includes(r.id)),known=runners.filter(r=>Number.isFinite(r.earlyPosition));
    target.querySelectorAll('[data-pace-runner]').forEach(node=>{
      const r=known.find(x=>x.id===node.dataset.paceRunner),p=scenarioPosition(r,scenario,progress,runners.length);
      const left=progress*75-(p-1)/Math.max(1,runners.length-1)*18;
      node.style.left=clamp(8+left,3,88)+'%';
      node.querySelector('small').textContent=progress<.01?'出闸':progress<.34?'早段':progress<.7?'中段':'终段';
    });
    target.querySelector('[data-pace-progress]').value=String(Math.round(progress*100));
    target.querySelector('[data-pace-phase]').textContent=progress<.01?'出闸示意':progress<.34?'早段争位':progress<.7?'中段位置':'终段跑法';
  }
  function predictionHtml(){
    const report=prediction?.reports?.pre;
    if(!report)return '<p class="note">尚无本场已发布的赛前首选。'+(snapshot?.status==='pregame'?'下方生成赛前预测时，DeepSeek 会同时收到这份步速与跑法资料。':'本场开赛后不补写赛前首选。')+'</p>';
    const shortlist=[...new Set([report.pick,...(report.shortlist||[])])].filter(Boolean);
    return `<p class="note">对照已发布赛前预测 · ${stamp(report.issuedAt)}。切换步速不会更改原首选。</p>${shortlist.map(id=>{const r=snapshot.runners.find(x=>x.id===id);return r?`<p><strong>${id===report.pick?'首选':'关注'} ${esc(r.number)}号 ${esc(r.name)}</strong> · ${esc(r.style)}<br>${esc(paceEffect(r,scenario))}</p>`:'';}).join('')}`;
  }
  function paint(){
    if(controller.signal.aborted||!snapshot)return;stop();
    const runners=snapshot.runners.filter(r=>!snapshot.withdrawnIds.includes(r.id));
    const known=runners.filter(r=>Number.isFinite(r.earlyPosition)),unknown=runners.filter(r=>!Number.isFinite(r.earlyPosition));
    target.innerHTML=`<div class="section-head"><h2>步速与跑位模拟</h2><span class="tag">${snapshot.status==='retrospective'?'赛前往绩回看推演':snapshot.hasPregame?'已保存赛前模拟':'往绩情景推演'}</span></div><div class="pace-summary"><div><span>预计步速</span><strong>${paceNames[snapshot.expectedPace]}</strong></div><p>${esc(snapshot.summary)}</p></div><p class="note">${snapshot.status==='retrospective'?'本场未留存赛前模拟，现按开赛前往绩重建，不能作为事前预测。':`推演记录 ${stamp(snapshot.generatedAt)}。`} ${snapshot.paused?'同步已暂停，使用本机已保存资料。':''}</p><div class="pace-controls"><label>步速情景<select data-pace-scenario><option value="slow">偏慢步速</option><option value="normal">正常步速</option><option value="fast">偏快步速</option></select></label><button class="button" data-pace-play ${known.length?'':'disabled'}>播放模拟</button><button class="button secondary" data-pace-reset>重置</button><label>播放速度<select data-pace-speed><option value="1">1 倍</option><option value="2">2 倍</option></select></label><strong data-pace-phase>出闸示意</strong></div><div class="pace-track" aria-label="马匹跑法模拟图，箭头向右，示意位置不是实际距离">${known.map(r=>`<div class="pace-lane"><a class="pace-name" href="#/horse/${esc(r.id)}"><b>${esc(r.number)}</b> ${esc(r.name)}<small>${esc(r.style)} · ${r.draw??'—'}档</small></a><div class="pace-lane-path"><span class="pace-runner" data-pace-runner="${esc(r.id)}"><b>${esc(r.number)}</b><small>出闸</small></span></div></div>`).join('')||'<div class="empty">至少需要两次有效沿途走位，已有资料的马匹才会进入跑位图。</div>'}<div class="pace-direction">行进方向 → · 终段示意，不代表预测名次</div></div><label class="pace-scrubber">拖动查看阶段<input data-pace-progress type="range" min="0" max="100" value="${Math.round(progress*100)}" aria-label="模拟进度"></label>${unknown.length?`<p class="note">暂不安排跑位：${unknown.map(r=>esc(r.number)+'号 '+esc(r.name)+'（'+r.samples+'次走位）').join('、')}。</p>`:''}<div class="pace-connection"><h3>对应本站赛前预测</h3><div data-pace-prediction>${predictionHtml()}</div></div><details><summary>各马跑法、依据与本情景影响</summary>${table(['马号 / 马匹','预计跑法','末段平均追前','依据','步速影响'],runners.map(r=>[`${esc(r.number)} · <a href="#/horse/${esc(r.id)}">${esc(r.name)}</a>`,esc(r.style)+'<small>'+r.confidence+'</small>',r.lateGain===null?'—':r.lateGain.toFixed(1)+' 位',`<details><summary>${r.samples} 次往绩</summary>${r.evidence.map(e=>`<p>${esc(e.date)} ${esc(e.course)} ${e.distance??'—'}米<br>沿途 ${esc(e.running)}${e.similar?' · 同场近途程':''}<br><a href="${esc(e.source||r.source)}" target="_blank" rel="noopener noreferrer">往绩来源 ↗</a></p>`).join('')}</details>`,esc(paceEffect(r,scenario))]))}</details><details><summary>计算方法与图示说明</summary><p>${esc(snapshot.method)}</p><p>情景测试：偏快步速把前置马终段示意后移1.5位、后追马前移1.5位；偏慢步速相反调整。此为条件对照参数，未经胜率校准，不用来排列夺冠名次。档位仅用于出闸示意。</p><p>${esc(snapshot.limits)}</p><p><a href="https://www.hkjc.com/chinese/formguide/formstudy_help.asp" target="_blank" rel="noopener noreferrer">马会速势走位图概念说明 ↗</a> · 本页为本站往绩推演。</p></details>${reviewHtml(snapshot,race)}`;
    target.querySelector('[data-pace-scenario]').value=scenario;
    target.querySelector('[data-pace-scenario]').onchange=e=>{scenario=e.target.value;paint();};
    target.querySelector('[data-pace-progress]').oninput=e=>{stop();progress=Number(e.target.value)/100;projection();};
    target.querySelector('[data-pace-reset]').onclick=()=>{stop();progress=0;projection();};
    target.querySelector('[data-pace-play]').onclick=()=>{
      if(timer){stop();return;}if(progress>=1)progress=0;
      target.querySelector('[data-pace-play]').textContent='暂停模拟';
      timer=setInterval(()=>{if(document.hidden||controller.signal.aborted){stop();return;}progress=Math.min(1,progress+.008*Number(target.querySelector('[data-pace-speed]').value));projection();if(progress>=1)stop();},100);
    };projection();
  }
  target.innerHTML='<h2>步速与跑位模拟</h2><p role="status">正在整理本场马匹的既往跑法…</p>';
  api('/api/racing/races/'+encodeURIComponent(race.id)+'/pace',{signal:controller.signal}).then(value=>{
    if(controller.signal.aborted)return;
    if(value.raceId!==race.id||!Array.isArray(value.runners))throw Error(value.message||'本场模拟资料尚未齐备。');
    snapshot={...value,withdrawnIds:value.withdrawnIds||[]};scenario=['slow','normal','fast'].includes(value.expectedPace)?value.expectedPace:'normal';paint();
  }).catch(error=>{if(!controller.signal.aborted)target.innerHTML='<h2>步速与跑位模拟</h2><p class="note">'+esc(error.message)+'</p>';});
  return {setPrediction(value){prediction=value;if(snapshot){const el=target.querySelector('[data-pace-prediction]');if(el)el.innerHTML=predictionHtml();}},dispose(){stop();controller.abort();}};
}

function reviewHtml(snapshot,race){
  const review=snapshot.review;if(!review?.available)return '<p class="note">正式赛果发布后，会在这里对照赛前跑法与实际沿途走位。</p>';
  return `<h3>赛后跑法对照</h3><p>${review.hasPregame?`可核对 ${review.checked} 匹，其中 ${review.matched} 匹早段分类一致。此为跑法一致性，不是胜出命中率。`:'未保存赛前模拟，只展示实际走位。'}</p>${table(['马匹','赛前跑法','实际早段','沿途走位','名次'],review.runners.map(r=>[esc(race.entries.find(e=>e.id===r.id)?.name||r.id),review.hasPregame?esc(r.predicted):'无赛前记录',r.withdrawn?'退出':esc(r.actual||'待资料'),esc(r.running||'—'),r.place??'—']))}`;
}
