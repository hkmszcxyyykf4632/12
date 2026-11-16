import {data,names,facts,changes} from './repository.mjs';
import {main,esc,cn,pageHeading,timeText} from './ui.mjs';
import {league} from './league.mjs';
import {qualityReport} from './insights.mjs';

const KINDS={kickoff:'开球时间变更',start:'比赛开始',score:'比分变化',final:'比赛结束',correction:'赛后比分更正'};

export function renderQuality() {
  main.innerHTML=`${pageHeading('数据质量',`${league.name}各项资料的覆盖率、需要核对的记录和最近的变更。空缺会如实标出，不用估算值填补。`)}
    <div class="section-head"><h2>字段覆盖率</h2></div><div id="quality-fields"></div>
    <div class="section-head"><h2>需要核对的记录</h2></div><div id="quality-anomalies"></div>
    <div class="section-head"><h2>变更记录</h2><p>比分与赛程每次同步后的差异，最新在上</p></div><div id="quality-changes"></div>`;
  const update=()=>{
    if(!main.querySelector('#quality-fields'))return;
    const report=qualityReport({data,names,facts,competition:league.name});
    main.querySelector('#quality-fields').innerHTML=`<div class="table-wrap"><table><thead><tr><th>资料</th><th>已有</th><th>应有</th><th>覆盖率</th><th>说明</th></tr></thead><tbody>${report.fields.map(f=>{const share=f.total?f.filled/f.total:0;return `<tr><th scope="row">${esc(f.label)}</th><td>${f.filled}</td><td>${f.total}</td><td><div class="coverage"><div class="meter" role="img" aria-label="${Math.round(share*100)}%"><i class="${share<0.5?'low':share<0.9?'mid':''}" style="width:${share*100}%"></i></div><span>${f.total?`${(share*100).toFixed(share===1?0:1)}%`:'—'}</span></div></td><td class="job-message">${esc(f.note||(f.total-f.filled?`缺 ${f.total-f.filled} 项`:'完整'))}</td></tr>`;}).join('')}</tbody></table></div>`;
    main.querySelector('#quality-anomalies').innerHTML=report.anomalies.length?`<div class="table-wrap"><table><thead><tr><th>记录</th><th>操作</th></tr></thead><tbody>${report.anomalies.map(a=>`<tr><td class="job-message attention">${esc(a.text)}</td><td><a class="button quiet compact" href="#/match/${encodeURIComponent(a.matchId)}">查看比赛</a></td></tr>`).join('')}</tbody></table></div>`
      :'<div class="empty">没有发现缺比分、比分异常、胜负标记不符、长时间未结束或重复的比赛。</div>';
    const rows=(changes?.entries||[]).slice(0,120);
    main.querySelector('#quality-changes').innerHTML=rows.length?`<div class="table-wrap"><table><thead><tr><th>发现时间</th><th>比赛</th><th>类型</th><th>原值</th><th>新值</th></tr></thead><tbody>${rows.map(e=>{const stamp=value=>e.kind==='kickoff'&&value?timeText(value):value??'—';return `<tr><td>${esc(timeText(e.at))}</td><td><a href="#/match/${encodeURIComponent(e.matchId)}">${esc(cn(e.home))} vs ${esc(cn(e.away))}</a></td><td><span class="pill ${e.kind==='correction'?'failed':e.kind==='kickoff'?'running':'waiting'}">${KINDS[e.kind]||esc(e.kind)}</span></td><td>${esc(stamp(e.from))}</td><td>${esc(stamp(e.to))}</td></tr>`;}).join('')}</tbody></table></div>`
      :'<div class="empty">还没有变更记录。同步服务发现比分、开球时间或比赛状态变化时会记在这里。</div>';
  };
  update();return update;
}
