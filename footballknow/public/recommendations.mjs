import {api} from './api.mjs';
import {main,esc,pageHeading} from './ui.mjs';
import {competitions,rate} from './prediction-stats-core.mjs';
import {footballSummary,footballRows,racingRows,poolSummary,footballPaperCell,paperCell} from './prediction-stats.mjs';
import {loadBriefs} from './review-briefs.mjs';
import {recommendationVideo} from './recommendation-video.mjs';
const time=x=>new Date(x).toLocaleString('zh-CN',{timeZone:'Asia/Hong_Kong',hour12:false});
function card(c,clips=[]){
 const r=c.receipt,football=c.domain==='football',label=football?`${competitions.find(x=>x[0]===r.league)?.[1]||r.league} · ${r.season} ${r.round}`:`${r.day} · ${r.courseName} 第${r.raceNo}场`;
 const horse=football?null:r.runners.find(h=>h.id===r.pick),line=football&&r.line!=null?r.line*(r.asianSide==='H'?1:-1):null;
 const pick=football?`${r.asianSide==='H'?r.home:r.away} ${line>0?'+':''}${line??'—'} · 比分 ${(r.scoreCandidates?.length?r.scoreCandidates:[r.score]).map(s=>s.join(':')).join(' / ')}`:`首选 ${horse?.number||'—'}号 ${horse?.name||'马名核对中'}`;
 const href=football?(r.matchId?`./?league=${r.league}#/match/${encodeURIComponent(r.matchId)}`:'#/live'):'#/race/'+encodeURIComponent(r.raceId);
 return `<article class="recommendation-card"><div class="recommendation-label">${esc(label)} <span>${({pending:'待赛果',settled:'已结算',void:'作废',excluded:'核对中'})[r.status]}</span></div><h3>${football?esc(r.home+' vs '+r.away):esc(r.courseName+' · 第'+r.raceNo+'场精选')}</h3><p class="recommendation-pick">${esc(pick)}</p>${recommendationVideo(c,clips)}<p class="note">开赛 ${time(c.kickoff)}<br>入选发布 ${time(c.publishedAt)} · ${c.stage==='final'?'确认首发版':football?'初步版':'赛前版'}</p><p>${esc(c.summary?.[0]||'查看原赛前分析了解依据。')}</p><details><summary>入选依据与风险</summary><ul>${c.reasons.map(s=>`<li>${esc(s)}</li>`).join('')}</ul>${(c.summary||[]).slice(1).map(s=>`<p>${esc(s)}</p>`).join('')}<p class="note">入选后保持本次方向和版本，后续临场分析可在比赛详情查看。排名是相对筛选，不是胜率承诺。</p></details><a class="editorial-read" href="${href}">赛事与详细分析 ↗</a></article>`;
}
export async function paintRecommendationPreview(target){
 if(!target)return;
 try{const d=await api('/api/recommendations');if(!target.isConnected)return;const rows=(d.records||[]).filter(c=>c.receipt.status==='pending').sort((a,b)=>a.kickoff.localeCompare(b.kickoff)).slice(0,3);target.innerHTML=rows.length?`<div class="recommendation-grid">${rows.map(c=>card(c)).join('')}</div>`:'<p class="note">精选从尚未开赛的有效预测中产生；足球各赛事每轮最多三场，赛马每个赛马日一场。<a href="#/recommendations">查看发布记录与累计成绩 →</a></p>';}
 catch{if(target.isConnected)target.innerHTML='<p class="note"><a href="#/recommendations">进入峰弈推荐，查看最新发布与成绩 →</a></p>';}
}
export function renderRecommendations(){
 const controller=new AbortController();let records=[],clips=[],domain=null,league='all',briefs={football:[],racing:[]},loading=false;
 main.innerHTML=`<div class="prediction-statistics">${pageHeading('峰弈推荐','从已发布的赛前分析中精选，留下判断，持续验证。')}<div class="recommendation-promise"><span>各联赛及欧冠 · 每轮三场</span><span>赛马 · 每个赛马日一场</span><span>原推荐保留 · 成绩持续累加</span></div><div id="recommendation-content" role="status">正在读取推荐记录…</div></div>`;
 const target=main.querySelector('#recommendation-content');
 function draw(method){
  const selected=records.filter(c=>c.domain===domain&&(league==='all'||domain!=='football'||c.receipt.league===league));
  const receipts=selected.map(c=>c.receipt),football=domain==='football';
  const primary=receipts.filter(r=>r.status==='settled').map(r=>{const h=r.runners?.find(h=>h.id===r.pick);return r.pools?.find(p=>p.type==='WIN')?.tickets.find(t=>Number(t.combination)===Number(h?.number));}).filter(t=>t&&['hit','miss'].includes(t.status));
  target.innerHTML=`<div class="toolbar"><label>项目<select id="rec-domain"><option value="football" ${football?'selected':''}>足球精选</option><option value="racing" ${!football?'selected':''}>赛马精选</option></select></label>${football?`<label>赛事<select id="rec-league"><option value="all">全部赛事</option>${competitions.map(([id,n])=>`<option value="${id}" ${league===id?'selected':''}>${n}</option>`).join('')}</select></label>`:''}<button class="button secondary" id="rec-refresh">刷新</button></div>${selected.some(c=>c.receipt.status==='pending')?`<h2>本期推荐</h2><div class="recommendation-grid">${selected.filter(c=>c.receipt.status==='pending').map(c=>card(c,clips)).join('')}</div>`:''}<h2>精选累计成绩 · ${receipts.length} 场</h2>${football?footballSummary(receipts):`<p>首选独赢：${primary.filter(t=>t.status==='hit').length} / ${primary.length} 场 · ${rate(primary.filter(t=>t.status==='hit').length,primary.length)}；下方四项按当时完整关注名单结算。</p>${poolSummary(receipts)}`}<details class="ps-rules"><summary>精选模拟账本与逐场成绩</summary><p class="note">沿用足球亚洲盘100元、比分合计50元（两个比分各25元）；赛马名单每匹独赢及位置各100元，连赢及位置连赢各组合10元。与全部预测账本分开，不能重复相加。</p>${football?footballPaperCell(receipts):paperCell(receipts)}${football?footballRows(receipts,briefs.football,true):racingRows(receipts,briefs.racing,true)}</details><details class="ps-rules"><summary>怎样入选，以及统计口径</summary><p>${esc(method)}</p><p>只从启用本栏目后、尚未开赛的预测中发布；以前已完场赛事不会补写为精选。版本固定为入选时版本。赛马精选按香港时间在赛马日前一天，从已有完整赛前分析中发布；当天核对退赛、场地及赔率，原推荐保留。足球提前检查未来四天，已核对变盘的初步预测可直接入选；不足三场时先发布合格选择，后续只补空位。全部历史保留，不删输场。</p></details><h2>历史推荐记录</h2>${selected.some(c=>c.receipt.status!=='pending')?`<div class="recommendation-grid">${selected.filter(c=>c.receipt.status!=='pending').sort((a,b)=>Number(b.receipt.status==='pending')-Number(a.receipt.status==='pending')||b.kickoff.localeCompare(a.kickoff)).map(c=>card(c,clips)).join('')}</div>`:'<div class="empty">本范围暂无历史推荐记录；待开赛的精选会在本页上方显示。</div>'}`;
  target.querySelector('#rec-domain').onchange=e=>{domain=e.target.value;draw(method);};target.querySelector('#rec-league')?.addEventListener('change',e=>{league=e.target.value;draw(method);});target.querySelector('#rec-refresh').onclick=load;
 }
 async function load(){if(loading)return;loading=true;try{const [d,v]=await Promise.all([api('/api/recommendations',{signal:controller.signal}),api('/media/recommendation-videos.json',{signal:controller.signal}).catch(()=>({videos:[]}))]);if(!controller.signal.aborted){records=d.records||[];clips=Array.isArray(v.videos)?v.videos:[];if(domain===null)domain=records.find(c=>c.receipt.status==='pending')?.domain||'football';draw(d.method||'');}}catch(e){if(!controller.signal.aborted)target.innerHTML=`<p class="notice">${esc(e.message)} <a href="#/">返回首页</a></p>`;}finally{loading=false;}}
 for(const d of ['football','racing'])loadBriefs(d).then(x=>{briefs[d]=x;}).catch(()=>{});
 load();const timer=setInterval(()=>{if(!document.hidden)load();},60000);return()=>{controller.abort();clearInterval(timer);};
}
