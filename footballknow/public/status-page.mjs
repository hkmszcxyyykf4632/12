import {api} from './api.mjs';
import {main,esc,pageHeading,timeText} from './ui.mjs';
import {describeJob,statusSummary} from './insights.mjs';

/** Synchronizer status from the API, or from the published snapshot when only static files are served. */
export async function readStatus(signal) {
  try {return await api('/api/status',{signal,timeout:8000});}
  catch(error) {
    if(signal?.aborted)throw error;
    const response=await fetch('./sync-status.json',{cache:'no-cache',signal});
    if(!response.ok)throw error;
    return response.json();
  }
}

const seconds=value=>value>=86400?`${value/86400} 天`:value>=3600?`${value/3600} 小时`:`${value} 秒`;
const duration=ms=>ms==null?'—':ms<1000?`${ms} 毫秒`:`${(ms/1000).toFixed(1)} 秒`;

function jobRows(status,onlyProblems) {
  return Object.entries(status.jobs||{}).filter(([,job])=>!onlyProblems||job.ok!==true).map(([name,job])=>{
    const info=describeJob(name,job.group);
    const state=job.running?['running','正在同步']:job.ok===true?['','正常']:job.ok===false?['failed',job.consecutiveFailures>1?`连续失败 ${job.consecutiveFailures} 次`:'失败，自动重试']:['waiting','等待首次同步'];
    return `<tr><td><strong>${esc(info.league)}</strong> ${esc(info.label)}<small>${esc(name)}</small></td><td>${esc(info.group)}</td><td><span class="pill ${state[0]}">${esc(state[1])}</span></td><td>${job.lastSuccess?esc(timeText(job.lastSuccess)):'暂无'}</td><td>${duration(job.lastDurationMs)}</td><td>${job.intervalSeconds?seconds(job.intervalSeconds):'—'}</td><td>${job.nextAttempt?esc(timeText(job.nextAttempt)):'—'}</td><td class="job-message">${esc(job.message||'')}</td></tr>`;
  }).join('');
}

export function renderStatus() {
  const controller=new AbortController();
  let onlyProblems=false,latest=null;
  main.innerHTML=`${pageHeading('同步监控','每一项数据来源的检查结果、用时和下一次检查时间。来源暂时不可用时，网站保留最近一次成功的资料。','<button class="button secondary" id="status-refresh" type="button">重新读取</button>')}
    <div id="status-banner" class="loading">正在读取同步状态…</div>
    <div class="toolbar"><p class="note" id="status-stamp"></p><button class="button secondary compact" id="status-filter" type="button" aria-pressed="false">只看异常</button></div>
    <div id="status-table"></div>
    <p class="note">任务按各自间隔从上一次开始时间起算；一次检查超过间隔时，结束后立即开始下一次，不会重叠。连续失败的来源会逐步拉长重试间隔，恢复后回到正常间隔。监控系统可读取 <a href="/api/health">/api/health</a>。</p>`;
  const paint=()=>{
    if(!latest||!main.querySelector('#status-table'))return;
    const summary=statusSummary(latest);
    main.querySelector('#status-banner').className=`status-banner ${summary.level==='ok'?'':summary.level}`;
    main.querySelector('#status-banner').innerHTML=`<span class="status-light"></span><div><strong>${esc(summary.text)}</strong><span>共 ${summary.total} 项任务${latest.syncSeconds?`，统一间隔 ${seconds(latest.syncSeconds)}`:''}</span></div>`;
    main.querySelector('#status-stamp').textContent=`同步服务心跳：${latest.heartbeat?timeText(latest.heartbeat):'暂无'}。本页每 10 秒读取一次。`;
    const rows=jobRows(latest,onlyProblems);
    main.querySelector('#status-table').innerHTML=rows?`<div class="table-wrap"><table><thead><tr><th>任务</th><th>分类</th><th>状态</th><th>最近成功</th><th>用时</th><th>间隔</th><th>下次检查</th><th>最近结果</th></tr></thead><tbody>${rows}</tbody></table></div>`
      :`<div class="empty">${onlyProblems?'没有异常任务。':'同步服务还没有发布任务状态。'}</div>`;
  };
  const load=async()=>{
    try {latest=await readStatus(controller.signal);paint();}
    catch(error) {if(!controller.signal.aborted&&main.querySelector('#status-banner')){main.querySelector('#status-banner').className='status-banner down';main.querySelector('#status-banner').innerHTML=`<span class="status-light"></span><div><strong>暂时读不到同步状态</strong><span>${esc(error.message)}</span></div>`;}}
  };
  main.querySelector('#status-refresh').addEventListener('click',load);
  main.querySelector('#status-filter').addEventListener('click',event=>{onlyProblems=!onlyProblems;event.currentTarget.setAttribute('aria-pressed',String(onlyProblems));paint();});
  const timer=setInterval(()=>{if(!document.hidden)load();},10000);
  load();
  return ()=>{clearInterval(timer);controller.abort();};
}
