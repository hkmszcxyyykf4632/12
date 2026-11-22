import {api} from './api.mjs';
import {main,esc,pageHeading} from './ui.mjs';
import {competitions,poolNames,rate,footballSelection,footballTotals,poolTotals,byDay,byRound} from './prediction-stats-core.mjs';
import {footballSummary,footballGroups,footballRows,poolSummary,racingRows,kpi,table,bar,footballRules,racingRules,paperCell,footballPaperCell} from './prediction-stats.mjs';
import {loadBriefs} from './review-briefs.mjs';
import {scopedRecords,startText} from './statistics-scope.mjs';
export function renderPredictionStats(domain,{paper=false}={}){
 const controller=new AbortController();let records=[],briefs=[],stage='adopted',filter='all',round='all',page=0,unreadable=0,loaded=false,loading=false;
 const football=domain==='football',title=(football?'足球':'赛马')+(paper?'模拟投注':'分析统计');
 const ledger=football?footballPaperCell:paperCell;
 main.innerHTML=`<div class="prediction-statistics">${pageHeading(title,paper?'固定金额模拟，逐场核对投入、派回与盈亏。':'每一场预测都有记录，每一次结果都可核对。')}<p class="notice">${startText[domain]}</p><nav class="ps-page-links"><a href="#/${domain}-statistics" ${!paper?'aria-current="page"':''}>分析统计</a><a href="#/${domain}-paper" ${paper?'aria-current="page"':''}>模拟投注</a></nav><div id="ps-content" role="status">正在读取赛前封存记录…</div></div>`;
 const box=main.querySelector('#ps-content');
 function summary(rows){
  if(paper)return ledger(rows);
  if(football)return footballSummary(rows);
  return `<div class="ps-kpis">${kpi('累计分析',rows.length+' 场',`${byDay(rows).length} 个赛马日`)}${kpi('已确认赛果',rows.filter(r=>r.status==='settled').length+' 场',`待赛果 ${rows.filter(r=>r.status==='pending').length} 场`)}${kpi('作废 / 未计入',rows.filter(r=>['void','excluded'].includes(r.status)).length+' 场','保留原记录，不补写历史推荐')}</div>${poolSummary(rows)}`;
 }
 function groupedTable(groups){
  const headings=football?['赛事 / 轮次','分析 / 结算',...(paper?['本轮投入与盈亏']:['比分命中','亚洲盘命中'])]:['赛马日','已分析',...(paper?['全天投入与盈亏']:Object.values(poolNames))];
  return table(headings,groups.map(([key,rows])=>{
   if(football){const t=footballTotals(rows);return [esc(key)+`<small>${rows.every(r=>r.roundComplete)?'本轮赛程已结束':'本轮进行中 · 已完场先统计'}</small>`,`${t.total} / ${t.settled}`,...(paper?[ledger(rows)]:[bar(t.exact,t.settled),bar(t.asianHits,t.asian)])];}
   return [key,rows.length,...(paper?[ledger(rows)]:Object.keys(poolNames).map(p=>{const t=poolTotals(rows,p);return `${t.hits}/${t.races} 场 · ${rate(t.hits,t.races)}<small>整组 ${t.multiple==null?'—':t.multiple.toFixed(2)+'倍'}</small>`;}))];
  }));
 }
 function draw(){
  if(controller.signal.aborted)return;
  const scoped=scopedRecords(records,domain),all=football?footballSelection(scoped):scoped;
  let selected=(football?footballSelection(scoped,stage):scoped).filter(r=>filter==='all'||(football?r.league===filter:r.day===filter));
  const rounds=football?byRound(selected):[];
  if(round!=='all'&&!rounds.some(([key])=>key===round))round='all';
  if(football&&round!=='all')selected=rounds.find(([key])=>key===round)?.[1]||[];
  selected.sort((a,b)=>b.day.localeCompare(a.day)||((b.raceNo||0)-(a.raceNo||0))||String(b.kickoff).localeCompare(String(a.kickoff)));
  const pages=Math.max(1,Math.ceil(selected.length/25));page=Math.min(page,pages-1);
  const filterOptions=(football?competitions:byDay(all).map(([d])=>[d,d])).map(([id,name])=>`<option value="${id}" ${filter===id?'selected':''}>${name}</option>`).join('');
  const stages=!paper&&football?`<label>预测版本<select id="ps-stage">${[['adopted','采用版 · 每场一次'],['initial','初步版'],['final','确认首发版']].map(([v,n])=>`<option value="${v}" ${stage===v?'selected':''}>${n}</option>`).join('')}</select></label>`:'';
  const roundOptions=football?`<label>比赛轮次<select id="ps-round"><option value="all">全部轮次</option>${rounds.map(([r])=>`<option value="${esc(r)}" ${round===r?'selected':''}>${esc(r)}</option>`).join('')}</select></label>`:'';
  const filters=`<div class="toolbar ps-filters"><label>${football?'赛事':'赛马日'}<select id="ps-filter"><option value="all">${football?'四大联赛与欧冠':'全部赛马日'}</option>${filterOptions}</select></label>${stages}${roundOptions}<button class="button secondary" id="ps-refresh">刷新结果</button><span class="note" id="ps-error" role="status"></span></div>`;
  const groups=football?byRound(selected):byDay(selected);
  const breakdown=football?(paper?table(['赛事','模拟投入与盈亏'],competitions.map(([id,name])=>[name,ledger(selected.filter(r=>r.league===id))])):footballGroups(selected)):poolSummary(selected,paper);
  const waiting=football?footballSelection(records.filter(r=>!r.round&&r.day>='2026-11-20')).length:0;
  const ruleNotice=paper?`<p class="notice">${football?'亚洲盘每场100港元、比分每场50港元；同一场只采用一次赛前预测。':'每匹推荐马独赢100港元、位置100港元；两两组合的连赢及位置连赢各10港元。三匹齐选每场660港元。'}仅模拟记录，不涉及真实投注。</p>`:'';
  box.innerHTML=`<section aria-label="累计总账"><div class="section-head"><h2>${paper?'累计模拟账本':'累计总账'}</h2><span class="note">不随筛选归零</span></div>${summary(all)}${unreadable?`<p class="notice">另有 ${unreadable} 条封存记录无法完整核对，未纳入命中率。</p>`:''}${waiting?`<p class="note">${waiting} 场尚待确认轮次，核实后自动归入对应轮次。</p>`:''}</section>${ruleNotice}<details class="ps-rules"><summary>统计口径与倍数说明</summary><p>${football?footballRules:racingRules}</p>${football?'':'<a href="https://special.hkjc.com/e-win/zh-HK/betting-info/racing/beginners-guide/local-pools/" target="_blank" rel="noopener noreferrer">香港赛马会玩法说明 ↗</a>'}</details>${filters}<section><h2>${football?'按赛事分别统计':'按玩法统计'}</h2>${breakdown}</section><section><h2>${football?'每轮'+(paper?'账本':'成绩'):'每个赛马日'} · ${groups.length} ${football?'轮':'天'}</h2>${groupedTable(groups)}</section><section><div class="section-head"><h2>逐场${paper?'模拟明细':'核对'}</h2><span>${selected.length} 场 · 最新在前</span></div>${selected.length?(football?footballRows(selected.slice(page*25,page*25+25),briefs,paper):racingRows(selected.slice(page*25,page*25+25),briefs,paper)):'<div class="empty">本范围尚无保存的赛前预测；开始发布后会持续累加。</div>'}<div class="toolbar"><button class="button secondary" id="ps-prev" ${page===0?'disabled':''}>上一页</button><span>第 ${page+1} / ${pages} 页</span><button class="button secondary" id="ps-next" ${page+1>=pages?'disabled':''}>下一页</button></div></section><p class="note">${paper?'未结算金额单列，已结算净额不是整轮最终盈亏。':'命中率只描述以上有效样本，不代表未来表现。'}预测原文与详细复盘可进入对应赛事查看。</p>`;
  box.querySelector('#ps-filter').onchange=e=>{filter=e.target.value;round='all';page=0;draw();};
  box.querySelector('#ps-stage')?.addEventListener('change',e=>{stage=e.target.value;page=0;draw();});
  box.querySelector('#ps-round')?.addEventListener('change',e=>{round=e.target.value;page=0;draw();});
  box.querySelector('#ps-refresh').onclick=load;box.querySelector('#ps-prev').onclick=()=>{page--;draw();};box.querySelector('#ps-next').onclick=()=>{page++;draw();};
 }
 async function load(){
  if(loading||controller.signal.aborted)return;loading=true;
  try{const data=await api('/api/statistics/'+domain,{signal:controller.signal,timeout:30000});if(controller.signal.aborted)return;records=data.records;unreadable=data.unreadable;loaded=true;draw();}
  catch(e){if(controller.signal.aborted)return;const error=box.querySelector('#ps-error');if(error)error.textContent=e.message;else{box.innerHTML=`<div class="empty">${esc(e.message)} <button class="button" id="ps-retry">重试</button></div>`;box.querySelector('#ps-retry').onclick=load;}}
  finally{loading=false;}
 }
 load();loadBriefs(domain).then(data=>{if(!controller.signal.aborted){briefs=data;if(loaded)draw();}}).catch(()=>{});
 const timer=setInterval(()=>{if(!document.hidden)load();},60000);
 return()=>{controller.abort();clearInterval(timer);};
}
