import {api} from './api.mjs';
import {esc,sourceLink} from './ui.mjs';
import {table,stamp} from './racing-ui.mjs';

const number=v=>Number.isFinite(v)?String(v):'—';
const signed=v=>Number.isFinite(v)?(v>0?'+':'')+v:'—';
export function preparationDetails(r){
  if(!r)return '';
  const c=r.classWatch;
  return `<div class="research-summary"><p><strong>${esc(r.activity)}</strong> · ${esc(c.label)}</p><p>${esc(c.summary)}</p><details><summary>查看晨操、评分依据与其他解释</summary><p class="note">观察 ${esc(r.window.from)} 至 ${esc(r.window.to)} · 采集 ${stamp(r.fetchedAt)}。同日公布时间不明的晨操不纳入；出赛不计作训练。</p>${r.evidence.map(p=>`<p>${esc(p)}</p>`).join('')}${r.alternatives.map(p=>`<p class="note">${esc(p)}</p>`).join('')}<p>${esc(c.basis)}：${c.class?'第 '+c.class+' 班':'未核对'}；评分 ${number(c.rating)}，较最近已收录三仗中最早一仗 ${signed(c.change)} 分。${c.threshold!==null?`低一班标准上限 ${c.threshold} 分，${c.gap>0?'尚差 '+c.gap+' 分':'已到该范围'}。`:''}</p>${table(['出赛日期','班次','赛前评分','名次'],c.history.map(h=>[esc(h.date),esc(h.class||'—'),number(h.rating),number(h.place)]))}<p class="note">${esc(c.intent)} 具体参赛资格以该场条件为准。${sourceLink(c.policy,'马会评分政策 ↗')} ${sourceLink(c.source,'评分来源 ↗')}</p>${r.workouts.length?table(['晨操日期','类别','跑道','用时 / 途程','骑乘人员'],r.workouts.map(w=>[esc(w.date),esc(w.type),esc(w.track||'—'),`${esc(w.publishedTime||'—')} / ${w.distance?number(w.distance)+'米':'未列明'}`,esc(w.rider||'—')])):''}<p>${sourceLink(r.source,'晨操原始资料 ↗')}</p></details></div>`;
}

export function preparationHtml(data){
  const rows=(data.runners||[]).filter(r=>!(data.withdrawnIds||[]).includes(r.id));
  const reviews=data.review;
  let html=`<p class="note">${data.status==='retrospective'?'本场没有保存赛前备战判断；以下为已收录历史资料回看，不作事前验证。':`观察记录 ${stamp(data.generatedAt)} · ${data.hasPregame?'已保存赛前版本':'尚未保存赛前版本'}`} ${data.paused?'同步已暂停，使用已保存资料。':''}</p>`;
  html+=table(['马匹','备战观察','近7天快操 / 试闸','评分与降班观察','详细依据'],rows.map(r=>[`${esc(r.number||'')} · <a href="#/horse/${esc(r.id)}">${esc(r.name)}</a>`,esc(r.activity),r.source?`${r.counts7.fast} / ${r.counts7.trial}<small>${r.days7} 个已记录操练日</small>`:'待同步',`${number(r.classWatch.rating)} 分<small>${esc(r.classWatch.label)}${r.classWatch.gap>0?' · 尚差 '+r.classWatch.gap+' 分':''}</small>`,`<details><summary>展开依据</summary>${preparationDetails(r)}</details>`]));
  if(reviews?.available&&reviews.hasPregame){
    html+='<h3>赛后对照与降班跟进</h3>'+table(['马匹','原备战观察','本场名次','之后评分变化','之后编班'],reviews.runners.map(r=>[esc(r.name),esc(r.activity),r.void?'退出 / 未核对':number(r.place),r.void?'不作验证':r.followingDate?`${signed(r.ratingChange)} 分<small>${esc(r.followingDate)} ${sourceLink(r.source,'下次出赛 ↗')}</small>`:'等待下一次出赛',r.void?'不作验证':r.class?`第 ${r.class} 班${r.downClass===true?' · 已降班':r.downClass===false?' · 未降班':''}`:'待公布']));
    html+='<p class="note">结果核对名次、评分及班次变化；不能用一场输赢验证幕后目的。</p>';
  }
  return html+'<details><summary>备战分类方法</summary><p>完整21天记录且48小时内已更新时，比较最近7天与此前14天折算的每周记录。最近7天至少4个操练日、快操及试闸至少1次且比此前周均多至少1次，标为加紧备战；至少5个操练日及2次快操/试闸，标为较积极。此前14天至少6个操练日，最近7天降至其四分之一或以下且无快操/试闸，标为操练减少；若刚赛后7天内则标为调整期。其余为常规或资料不足。阈值用于整理观察，未作为胜率模型验证。</p><p>降班观察要求评分下降并距离低一班标准上限1至3分；更高强度不等于状态更好，缺失记录不等于没有训练。第五班不再推定更低班次。</p></details>';
}

export function mountPreparation(target,race){
  const controller=new AbortController();let timer,attempts=0;
  target.innerHTML='<div class="section-head"><h2>晨操备战与降班观察</h2><button class="button secondary compact" data-preparation-refresh>重新读取</button></div><p data-preparation-status role="status">正在整理本场备战资料…</p><div data-preparation-content></div>';
  const button=target.querySelector('[data-preparation-refresh]'),status=target.querySelector('[data-preparation-status]');
  async function load(){
    clearTimeout(timer);button.disabled=true;
    try{
      const data=await api('/api/racing/races/'+encodeURIComponent(race.id)+'/preparation',{signal:controller.signal,timeout:20000});
      if(controller.signal.aborted)return;
      if(data.raceId!==race.id||!Array.isArray(data.runners))throw Error('本场备战资料尚未齐备。');
      target.querySelector('[data-preparation-content]').innerHTML=preparationHtml(data);
      status.textContent=data.pending?'正在分批读取晨操，完成后自动显示；每次最多处理两匹马。':data.message||'';
      if(data.pending&&attempts++<15)timer=setTimeout(load,12000);
      else if(data.pending)status.textContent='已显示可用资料，其余晨操仍在同步，可稍后重新读取。';
    }catch(error){if(!controller.signal.aborted)status.textContent=error.message;}
    finally{if(!controller.signal.aborted)button.disabled=false;}
  }
  button.onclick=()=>{attempts=0;load();};load();
  return {dispose(){controller.abort();clearTimeout(timer);}};
}
