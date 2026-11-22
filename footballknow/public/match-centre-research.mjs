import {api} from './api.mjs';
import {esc} from './ui.mjs';
import {data,markets,findMatch} from './repository.mjs';
import {league} from './league.mjs';
import {quotesForMatch} from './settlement.mjs';
import {handicapAlerts} from './odds-alerts.mjs';
import {motivationHtml,alertsHtml} from './daily-research.mjs';
import {matchResearchHtml} from './match-research.mjs';
import {forecastsHtml,forecastSummaryHtml} from './football-forecasts.mjs';

export function researchMatches(value,match,leagueId){
  return value?.league===leagueId&&value.matchId===match.id&&value.home===match.home&&value.away===match.away
    &&value.date===match.date&&(!match.kickoff||Date.parse(value.kickoff)===Date.parse(match.kickoff));
}

export function mountMatchResearch(target,match){
  const controller=new AbortController();let value=null,tab='intent',busy=false,detailBusy=false,forecast=null;
  target.innerHTML=`<div class="section-head"><h2>${match.finished?'本场分析与赛后验证':'本场赛前分析'}</h2><button class="button secondary compact" data-research-refresh>更新分析资料</button></div><p class="note">先看保存的预测，再展开本场依据；各入口使用同一份记录。</p><details class="analysis-disclosure" data-research-evidence><summary>阵容、赔率与比赛背景</summary><div class="tabs" role="group" aria-label="本场分析分类">${[['intent','战意与赛后验证'],['odds','赔率变化提醒'],['detail','阵容 · 天气 · 近况']].map(([k,t])=>`<button data-research-tab="${k}" aria-pressed="${k===tab}">${t}</button>`).join('')}</div><p data-research-status role="status">正在读取本场分析…</p><div data-research-content></div></details>`;
  const status=target.querySelector('[data-research-status]'),content=target.querySelector('[data-research-content]');
  const forecastPanel=document.createElement('div');target.insertBefore(forecastPanel,target.firstChild);
  function paint(){
    if(controller.signal.aborted)return;
    const current=findMatch(match.id)||match;
    const row={...value?.match,...current,quotes:[...(value?.match?.quotes||[]),...quotesForMatch(markets,current)]};
    const opened=forecastPanel.querySelector('details[data-forecast-full]')?.open||false;
    forecastPanel.innerHTML=value?.match?`<div class="forecast-brief">${forecastSummaryHtml({...value.match,league:league.id},forecast)}</div><details class="analysis-disclosure" data-forecast-full ${opened?'open':''}><summary>${current.finished?'两版预测与详细复盘':'初步与临场预测详情'}</summary>${forecastsHtml({...value.match,league:league.id},forecast)}</details>`:'';
    target.querySelectorAll('[data-research-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.researchTab===tab);b.setAttribute('aria-pressed',String(b.dataset.researchTab===tab));});
    content.innerHTML=tab==='intent'?motivationHtml(row):tab==='odds'?alertsHtml(row,handicapAlerts(row,{data,markets})):value?.supplement?matchResearchHtml(value.supplement):'<div class="empty">'+(detailBusy?'正在核对本场首发、近况与天气…':'打开后读取本场阵容、天气和近期战绩。')+'</div>';
  }
  async function load(detail=false){
    if(detail?detailBusy:busy)return;
    if(detail)detailBusy=true;else busy=true;
    status.textContent=detail?'正在核对首发与历史比赛，首次读取可能稍久…':'正在更新本场分析…';paint();
    try{
      const next=await api(`/api/match/research?league=${league.id}&match_id=${encodeURIComponent(match.id)}${detail?'&include_detail=true':''}`,{signal:controller.signal,timeout:150000});
      if(controller.signal.aborted)return;
      if(!researchMatches(next,match,league.id))throw Error('分析与本场身份不一致，未载入这份资料。');
      value={...next,supplement:next.supplement||value?.supplement};
      if(next.match?.id){try{forecast=await api(`/api/daily-football/${encodeURIComponent(next.match.id)}/forecast`,{signal:controller.signal,timeout:10000});}catch{forecast=null;}}
      status.textContent=[next.paused?'同步已暂停，显示已保存资料。':'',next.message||'',next.match?.updatedAt?'资料时间 '+new Date(next.match.updatedAt).toLocaleString('zh-CN',{hour12:false}):''].filter(Boolean).join(' ');
    }catch(error){if(!controller.signal.aborted)status.textContent=error.message;}
    finally{if(detail)detailBusy=false;else busy=false;paint();}
  }
  target.querySelectorAll('[data-research-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.researchTab;paint();if(tab==='detail'&&!value?.supplement)load(true);});
  target.querySelector('[data-research-refresh]').onclick=()=>load(tab==='detail');
  load();const timer=setInterval(()=>{if(!document.hidden)load(tab==='detail');},60000);
  return()=>{controller.abort();clearInterval(timer);};
}
