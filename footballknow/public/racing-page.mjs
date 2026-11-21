import {racingLiveBlock} from './racing-live.mjs';
import {api} from './api.mjs';
import {main,esc,pageHeading} from './ui.mjs';
import {poolsHtml,dividendsHtml} from './racing-pools.mjs';
import {racingNav} from './racing-ui.mjs';
import {replayBlock,bindReplay} from './racing-replay.mjs';
import {mountPaceSimulation} from './racing-pace.mjs';
import {mountPreparation} from './racing-preparation.mjs';
import {evidenceReviewHtml} from './evidence-review.mjs';

const val=x=>x==null||x===''?'—':esc(String(x));
const stamp=x=>x?new Date(x).toLocaleString('zh-CN',{timeZone:'Asia/Hong_Kong',hour12:false}):'—';
const source=(url,label='马会原始资料')=>url&&/^https:\/\/racing\.hkjc\.com\//.test(url)?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:'';
const horseLink=h=>`<a class="racing-horse" href="#/horse/${esc(h.id)}"><strong>${esc(h.name||h.brand||h.id)}</strong><small>${esc(h.brand||h.id.split('_').at(-1))}</small></a>`;
const person=p=>p?.source?source(p.source,p.name):val(p?.name);
const table=(headers,rows)=>rows.length?`<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(c=>`<tr>${c.map(v=>`<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'<div class="empty">暂未收录这项资料。</div>';
async function json(path,signal){const r=await fetch(path,{cache:'no-cache',signal});if(!r.ok)throw Error('资料正在同步，请稍后重新读取。');return r.json();}

function amendmentsHtml(report){
  const amendments=report.amendments||[],latest=amendments.at(-1);if(!latest)return '';
  const market=latest.marketSnapshot||{},pools=market.pools||[],win=pools.find(p=>p.type==='WIN'),place=pools.find(p=>p.type==='PLA');
  const selected=new Set([report.pick,...(report.shortlist||[])]);
  const prep=(latest.preparationSnapshot?.runners||[]).filter(h=>selected.has(h.id));
  const quotes=(win?.quotes||[]).filter(q=>(q.horses||[]).some(h=>selected.has(h.id)));
  const quoteRows=quotes.map(q=>[(q.horses||[]).map(h=>esc(h.number+' · '+h.name)).join('、'),val(q.value),val(place?.quotes?.find(p=>p.combination===q.combination)?.value)]);
  const prepRows=prep.map(h=>[esc(h.number+' · '+h.name),esc(h.activity||'资料不足'),h.known?val(h.counts7?.fast)+' / '+val(h.counts7?.trial):'—',esc(h.window?.to||'—')]);
  return '<div class="racing-amendment"><p><strong>资料说明已更正</strong> · '+stamp(latest.issuedAt)+'</p><p>'+esc(latest.reason)+'</p><p class="note">首选、关注名单与原发布时间保持不变。</p><details><summary>核对后的赔率与晨操资料</summary>'+
    '<p>'+esc(market.status==='available'?'已取得本场赛前报价；报价存在不代表已有完整变动走势。':'本次未取得可核对的赛前报价。')+'</p>'+
    (quotes.length?table(['关注马','独赢','位置'],quoteRows):'')+
    pools.map(p=>'<p class="note">'+esc(({WIN:'独赢',PLA:'位置',QIN:'连赢'})[p.type]||p.type)+' · 来源更新 '+stamp(p.sourceUpdatedAt)+' · 检查 '+stamp(p.checkedAt)+(p.retained||p.stale?' · 保留的历史报价':'')+'</p>').join('')+
    '<p class="note">补充记录 '+stamp(market.asOf)+'；不将此时点的赔率倒写为原预测时已知。</p>'+
    (prep.length?table(['原关注马','已保存的备战观察','近7天快操 / 试闸','观察截至'],prepRows):'')+
    '<p class="note">晨操分类取自本版预测保存的观察记录，仅描述公开操练，不代表胜率。</p></details></div>';
}
function reportBody(report){
  const paragraphs=(report.summary||[]).map(p=>'<p>'+esc(p)+'</p>').join('');
  const details=(report.details||[]).map(d=>'<h3>'+esc(d.title)+'</h3><p>'+esc(d.text)+'</p>').join('');
  return report.amendments?.length?amendmentsHtml(report)+'<details class="racing-original"><summary>原始说明（已更正）</summary>'+paragraphs+details+'</details>':paragraphs+'<details><summary>更多详细资料</summary>'+details+'</details>';
}

export function evaluationHtml(state,race){
  const e=state.evaluation,phase=race.status==='finished'?'post':'pre';
  const report=state.reports?.[phase],prior=state.reports?.pre;
  const name=id=>race.entries.find(h=>h.id===id)?.name||id;
  let html=`<div class="forecast-rates"><div><span>首选胜出命中率</span><strong>${e.evaluated?(e.wins/e.evaluated*100).toFixed(1)+'%':'等待赛果验证'}</strong><small>${e.wins} / ${e.evaluated} 次有效预测 · ${e.pending} 次待赛果 · ${e.void} 次作废</small></div><div><span>首选前三名率</span><strong>${e.evaluated?(e.top3/e.evaluated*100).toFixed(1)+'%':'等待赛果验证'}</strong><small>前三名统计与胜出统计分开计算</small></div></div>`;
  if(report?.format==='evidence-review-1'){html+=evidenceReviewHtml(report);}
  else if(report){html+='<div class="research-summary">'+(report.pick?'<p class="racing-pick">首选：'+esc(name(report.pick))+'</p><p>关注：'+(report.shortlist||[]).map(id=>esc(name(id))).join(' · ')+'</p>':'')+reportBody(report)+(report.model||report.issuedAt?'<p class="note">'+[report.model,report.issuedAt?stamp(report.issuedAt):null].filter(Boolean).map(esc).join(' · ')+'</p>':'')+'</div>';}
  else html+='<div class="empty">'+(phase==='pre'?'本场预测正在等待自动生成；排位与马匹资料齐备后会在开跑前直接发布。':'管理员可生成赛后评价，结合实际赛果复盘。')+'</div>';
  if(phase==='post')html+='<details class="racing-original"><summary>原始赛前预测与验证</summary>'+(prior?.pick?'<p>发布：'+stamp(prior.issuedAt)+' · 首选 '+esc(name(prior.pick))+'</p>'+reportBody(prior)+'<p>验证：'+(state.outcome?.status==='evaluated'?'实际名次 '+val(state.outcome.position)+'；'+(state.outcome.win===true?'首选胜出命中':state.outcome.win===false?'首选胜出未命中':'尚不能验证'):esc(state.outcome?.reason||'等待完整赛果'))+'</p>':'<p>本场没有赛前发布的预测，不计入命中率。</p>')+'</details>';
  if(phase==='post'&&prior?.pick){html+='<div class="table-wrap"><table><thead><tr><th>原关注马</th><th>原标记</th><th>实际名次</th><th>结果</th></tr></thead><tbody>'+[...new Set([prior.pick,...(prior.shortlist||[])])].filter(Boolean).map(id=>{const h=race.entries.find(e=>e.id===id);return '<tr><td>'+esc(name(id))+'</td><td>'+(id===prior.pick?'首选':'关注')+'</td><td>'+val(h?.place)+'</td><td>'+(h?.withdrawn?'退出作废':h?.place===1?'胜出':h?.place>0?'未胜出':'等待正式赛果')+'</td></tr>';}).join('')+'</tbody></table></div>';}
  return html+'<p class="note">赛前预测在开跑前固定保存。正式赛果发布后计算首选胜出和前三名结果；退出作废。所有有效预测均纳入，不包含赛后补写的判断。</p>';
}

export function renderRace(id){
  const controller=new AbortController();let race,analyzing=false,pace=null,preparation=null;
  main.innerHTML=pageHeading('赛马详情','正在读取本场资料。','<a class="button secondary" href="#/racing">香港赛马</a>')+'<div id="race-content" class="loading">正在读取排位及赛果…</div>';
  async function analysis(generate=false){
    const button=main.querySelector('#race-generate'),msg=main.querySelector('#race-ai-message');if(!button)return;button.disabled=true;analyzing=true;
    try{const value=await api('/api/racing/races/'+id+'/analysis'+(generate?'?phase='+(race.status==='finished'?'post':'pre'):''),{signal:controller.signal,timeout:150000,...(generate?{method:'POST'}:{})});if(controller.signal.aborted)return;const panel=main.querySelector('#race-analysis');panel.classList.remove('loading');panel.innerHTML=evaluationHtml(value,race);pace?.setPrediction(value);msg.textContent=generate?(value.reports?.post?.format==='evidence-review-1'&&value.reports.post.analysisStatus!=='ready'?'已整理事实，详细原因分析尚未完成。':'分析已保存。'):'';}
    catch(error){if(!controller.signal.aborted)msg.innerHTML=esc(error.message)+' <a href="#/admin">管理后台</a>';}
    finally{analyzing=false;if(!controller.signal.aborted)button.disabled=false;}
  }
  async function load(){
    try{
      race=await api('/api/racing/races/'+id,{signal:controller.signal});if(controller.signal.aborted)return;
      pace?.dispose();pace=null;
      preparation?.dispose();preparation=null;
      if(race.status==='cancelled'){main.innerHTML=pageHeading(`${race.date} · ${race.courseName} 第 ${race.raceNo} 场`,'马会已公布取消本场赛事。')+racingNav('racing')+'<div class="empty">赛事取消。独赢、位置及连赢退款，不纳入预测命中率及骑练赛果统计。</div>'+dividendsHtml(race)+`<a class="button secondary" href="#/racing-day/${race.id.replace(/-\d+$/,'')}">返回赛马日</a>`;return;}
      const provisional=race.status==='provisional',finished=race.status==='finished'||provisional,winner=race.entries.filter(e=>e.place===1);
      main.innerHTML=pageHeading(`${race.courseName} · 第 ${race.raceNo} 场`,race.date+' · '+race.name,'<a class="button secondary" href="#/racing">香港赛马</a>')+
        '<div class="research-summary racing-race-head"><div><span>'+(provisional?'初步赛果 · 等待正式确认':finished?'正式赛果':'排位表')+'</span><h2>'+esc(race.name)+'</h2><p>'+esc(race.track)+' · '+esc(race.class)+'</p><p>'+(race.offTime?'香港时间 '+stamp(race.offTime):'赛事日期 '+esc(race.date))+'</p></div><div><strong>'+val(race.distance)+'<small> 米</small></strong><p>'+race.entries.length+' 匹已收录</p></div></div>'+
        (finished?'<section><h2>赛后结果摘要</h2><div class="research-summary"><p>'+winner.map(h=>esc(h.name)+'（'+esc(h.number)+'号）以 '+val(h.finishTime)+' 完赛，名列第一').join('；')+'。</p><p>前列马匹：'+race.entries.filter(e=>e.place&&e.place<=3).map(h=>val(h.position)+'名 '+esc(h.name)).join(' · ')+'。完整名次、沿途走位及独赢赔率列于下表。</p></div></section>':'')+
        '<section><div class="section-head"><h2>'+(finished?'赛果详情':'出赛马匹')+'</h2>'+source(race.source,finished?'马会赛果与重播':'马会排位表')+'</div>'+table(finished?['名次','马号 / 马匹','骑师 / 练马师','档位','负磅 / 体重','头马距离','沿途走位','完成时间','赛后独赢赔率']:['马号 / 马匹','近六仗','档位','骑师 / 练马师','负磅 / 体重','评分','装备','父系 / 母系'],race.entries.map(h=>finished?[val(h.position),val(h.number)+' · '+horseLink(h),person(h.jockey)+'<small>'+person(h.trainer)+'</small>',val(h.draw),val(h.weight)+' / '+val(h.bodyWeight),val(h.margin),val(h.running),val(h.finishTime),val(h.winOdds)]:[val(h.number)+' · '+horseLink(h)+(h.withdrawn?'<span class="attention">退出</span>':''),val(h.recent),val(h.draw),person(h.jockey)+'<small>'+person(h.trainer)+'</small>',val(h.weight)+' / '+val(h.bodyWeight),val(h.rating),val(h.equipment),val(h.sire)+'<small>'+val(h.dam)+'</small>']))+'</section>'+
        '<section><div class="section-head"><h2>'+(finished?'赛后评价':'赛前预测')+'</h2><button class="button" id="race-generate">生成'+(finished?'赛后评价':'赛前预测')+'</button></div><p id="race-ai-message" role="status"></p><div id="race-analysis" class="loading">读取分析记录…</div></section><p class="note">来源：香港赛马会 · 最近采集 '+stamp(race.updatedAt)+'。负磅及排位体重单位为磅。'+(finished?'独赢赔率为赛果页公布的赛后资料。':'排位、骑师及场地状况可能更改。')+'</p>';
      main.insertAdjacentHTML('afterbegin',racingNav('racing'));
      main.querySelector('.racing-race-head').insertAdjacentHTML('afterend','<section id="race-pace"></section>');
      pace=mountPaceSimulation(main.querySelector('#race-pace'),race);
      main.querySelector('#race-generate').closest('section').insertAdjacentHTML('beforebegin','<section id="race-preparation"></section>');
      preparation=mountPreparation(main.querySelector('#race-preparation'),race);
      if(!finished)main.querySelector('.racing-race-head').insertAdjacentHTML('afterend',racingLiveBlock());
      if(finished){main.querySelector('.racing-race-head').insertAdjacentHTML('afterend',replayBlock(race));bindReplay(main,race);}
      main.querySelector('#race-generate').closest('section').insertAdjacentHTML('beforebegin',poolsHtml(race));
      main.querySelector('.page-heading').insertAdjacentHTML('afterend',`<a class="back-link" href="#/racing-day/${esc(race.id.replace(/-\d+$/,''))}">← 本赛马日 · 分组出赛与赛果</a>`);
      main.querySelector('#race-generate').onclick=()=>analysis(true);
      if(provisional){main.querySelector('#race-generate').hidden=true;main.querySelector('#race-generate').closest('section').querySelector('h2').textContent='赛前预测记录 · 等待正式赛果';}
      analysis();
    }catch(error){if(!controller.signal.aborted)main.innerHTML=pageHeading('赛马详情','','<a href="#/racing">返回香港赛马</a>')+'<div class="empty">'+esc(error.message)+'</div>';}
  }
  load();const timer=setInterval(()=>{if(!document.hidden&&!analyzing&&race&&!['finished','cancelled'].includes(race.status))load();},60000);return()=>{controller.abort();clearInterval(timer);pace?.dispose();preparation?.dispose();};
}
