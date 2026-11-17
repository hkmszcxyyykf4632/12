import {orderedEvents} from './research-core.mjs';
import {facts,oddsHistory} from './repository.mjs';
import {esc,oddsText,timeText} from './ui.mjs';
import {localized} from './football-components.mjs';
import {eventSentence,kellyRows,priceMovement} from './insights.mjs';

const STAT_GROUPS=[['进攻',[['possessionPct','控球率','%'],['totalShots','射门'],['shotsOnTarget','射正'],['blockedShots','被封堵射门'],['wonCorners','角球'],['offsides','越位'],['penaltyKickShots','点球'],['penaltyKickGoals','点球进球']]],
  ['传球',[['totalPasses','传球'],['accuratePasses','成功传球'],['passPct','传球成功率','ratio'],['totalCrosses','传中'],['accurateCrosses','成功传中'],['totalLongBalls','长传'],['accurateLongBalls','成功长传']]],
  ['防守与纪律',[['totalTackles','抢断'],['effectiveTackles','成功抢断'],['interceptions','拦截'],['totalClearance','解围'],['saves','扑救'],['foulsCommitted','犯规'],['yellowCards','黄牌'],['redCards','红牌']]]];

function statRow(home,away,[key,label,kind]) {
  if(home?.[key]==null&&away?.[key]==null)return '';
  const value=raw=>{if(raw==null||raw==='')return null;const n=Number(raw);return Number.isFinite(n)?(kind==='ratio'?n*100:n):null;};
  const h=value(home?.[key]),a=value(away?.[key]),total=(h||0)+(a||0);
  const text=n=>n==null?'—':kind==='ratio'?`${Math.round(n)}%`:kind==='%'?`${n}%`:String(n);
  const share=n=>total?(n||0)/total*100:50;
  return `<div class="stat-row"><b class="${h>a?'lead':''}">${text(h)}</b><div class="stat-bars"><span>${label}</span><div class="stat-bar"><i class="${h>a?'lead':''}" style="width:${share(h)}%"></i><i class="${a>h?'lead':''}" style="width:${share(a)}%"></i></div></div><b class="${a>h?'lead':''}">${text(a)}</b></div>`;
}

export function eventTimeline(detail,customName){
  const people=Object.values(detail.lineups||{}).flatMap(s=>s.players||[]);
  const name=customName||((p)=>{const known=people.find(x=>x.espnId===p.espnId);const n=known?.playerCode?localized({code:known.playerCode}):null;return n?.mandarin||p.name;});
  let period=0;
  const events=orderedEvents(detail.events||[]).map(e=>{
    const marker=e.period&&e.period!==period&&period?`<li class="period-mark">${{2:'下半场',3:'加时赛上半场',4:'加时赛下半场'}[e.period]||`第 ${e.period} 节`}</li>`:'';
    period=e.period||period;
    return `${marker}<li class="event-${esc(e.type)} ${e.side==='away'?'away':''}"><time>${esc(e.clock)}</time><div><strong>${esc(e.label)}</strong> · ${e.side==='home'?esc(detail.home||'主队'):esc(detail.away||'客队')}<p>${esc(eventSentence(e,name))}</p></div></li>`;
  }).join('');
  return events?'<ol class="event-timeline">'+events+'</ol><p class="small subtle">按来源公布的时间排序；记录包含进球、点球、乌龙、换人及红黄牌。</p>':'<p class="empty">来源暂未提供比赛事件。</p>';
}

export function statsAndEvents(detail){
  const stats=Object.fromEntries((detail.statistics||[]).map(s=>[s.side,s.values]));
  const groups=STAT_GROUPS.map(([title,rows])=>[title,rows.map(row=>statRow(stats.home,stats.away,row)).join('')]).filter(([,html])=>html);
  return '<section><h2>技术统计</h2>'+(groups.length?'<div class="stat-panel"><div class="stat-head"><span>主队</span><span>客队</span></div>'+groups.map(([title,html])=>'<h3>'+title+'</h3>'+html).join('')+'</div>':'<p class="empty">本场技术统计暂未提供。</p>')+'<p class="note">主客队数据分列；加时赛场次包含加时数据。</p></section>';
}

export function matchFacts(match) {
  const row=facts?.matches?.[match.id];
  if(!row)return '';
  const parts=[row.halfTime?`半场 ${row.halfTime[0]} : ${row.halfTime[1]}`:'',row.venue?`球场 ${esc(row.venue)}`:'',Number.isFinite(row.attendance)&&row.attendance>0?`观众 ${row.attendance.toLocaleString('zh-CN')} 人`:''].filter(Boolean);
  return parts.length?`<p class="match-facts">${parts.join('<span aria-hidden="true">　</span>')}</p>`:'';
}

function sparkline(points,key) {
  const values=points.map(p=>p[key]);
  if(values.length<2)return '';
  const low=Math.min(...values),high=Math.max(...values),span=high-low||1;
  const path=values.map((v,i)=>`${(i/(values.length-1)*96+2).toFixed(1)},${(22-(v-low)/span*20).toFixed(1)}`).join(' ');
  return `<svg class="spark" viewBox="0 0 100 24" role="img" aria-label="从 ${values[0]} 到 ${values.at(-1)}"><polyline points="${path}"/></svg>`;
}

/** Opening against latest prices with the recorded movement, and the Kelly index when two or more bookmakers are listed. */
export function oddsExtras(match) {
  const moves=priceMovement(oddsHistory?.matches?.[match.id]),kelly=kellyRows(match.odds);
  const change=(from,to)=>to===from?'':`<small class="${to<from?'negative':'profit'}">${to<from?'↓':'↑'} ${Math.abs(to-from).toFixed(2)}</small>`;
  const cell=(m,key)=>`<td>${oddsText(m.opening[key])} → <strong>${oddsText(m.latest[key])}</strong>${change(m.opening[key],m.latest[key])}${sparkline(m.points,key)}</td>`;
  return `<div class="section-head"><h3>赔率变化</h3><p>初赔为本站首次记录到的报价</p></div>${moves.length?`<div class="table-wrap"><table><thead><tr><th>机构</th><th>主胜 初赔 → 即时</th><th>平局 初赔 → 即时</th><th>客胜 初赔 → 即时</th><th>记录</th></tr></thead><tbody>${moves.map(m=>`<tr><td>${esc(m.provider)}<small>${esc(timeText(m.opening.at))} 起</small></td>${cell(m,'H')}${cell(m,'D')}${cell(m,'A')}<td>${m.points.length} 次变动</td></tr>`).join('')}</tbody></table></div>`
      :'<div class="empty">这场比赛还没有记录到报价变化。本站每 60 秒检查一次，报价变动时新增一条记录。</div>'}
    ${kelly.length?`<div class="section-head"><h3>凯利指数</h3><p>机构赔率 × 各机构平均隐含概率</p></div><div class="table-wrap"><table><thead><tr><th>机构</th><th>主胜</th><th>平局</th><th>客胜</th></tr></thead><tbody>${kelly.map(k=>`<tr><td>${esc(k.provider)}</td><td>${k.H.toFixed(3)}</td><td>${k.D.toFixed(3)}</td><td>${k.A.toFixed(3)}</td></tr>`).join('')}</tbody></table></div><p class="note">指数高于 1 表示该机构这一项的赔率高于市场平均水平。只有同时列出两家以上机构时才计算。</p>`:''}`;
}
