import {esc,timeText} from './ui.mjs';
import {alertValue,alertSubject} from './odds-alerts.mjs';
export const sourceLink=(url,label='来源')=>/^https:\/\//.test(url||'')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:'';
const objectiveTitles=new Set(['比赛场地','来源所列近期战绩','赛前积分形势','本场取分影响','已收录后续赛程']);
const tacticalScenarios=['若比分落后且需要追分，可观察是否增加前场投入；这是假设情境，不是已确认部署。','若比分领先，可观察是否减少冒险、加强防守；不能据此反推赛前只想保平。'];
function currentFacts(m,side){
  const form=String(m.teams?.[side]?.form||'').toUpperCase().replace(/[^WDL]/g,'');
  const facts=[{title:'比赛场地',fact:m.neutral?'中立场':side==='home'?'主场':'客场',source:m.source,asOf:m.updatedAt}];
  if(form)facts.push({title:'来源所列近期战绩',fact:`${form.length}场：${[...form].filter(c=>c==='W').length}胜、${[...form].filter(c=>c==='D').length}平、${[...form].filter(c=>c==='L').length}负`,source:m.source,asOf:m.updatedAt});
  return facts;
}
export function motivationSummary(m,side){
  const saved=(m.motivation?.original?.teams?.[side]?.evidence||[]).filter(e=>objectiveTitles.has(e.title)&&e.title!=='本场取分影响');
  return (saved.length?saved:currentFacts(m,side)).map(e=>e.fact).join('；');
}
export function motivationHtml(m){
  const original=m.motivation?.original,review=m.motivation?.review,legacy=original&&original.version!=='match-context-2';
  const stamp=original?`赛前客观资料留存 ${esc(timeText(original.generatedAt))}`:`已收录比赛资料 ${esc(timeText(m.updatedAt))}`;
  return `<p class="note">${stamp} · 积分与近况是比赛背景；比赛目标须有明确表态，战术情境是条件假设，比分预测单独呈现。</p><div class="intent-grid">${['home','away'].map(side=>{
    const t=original?.teams?.[side],r=review?.teams?.[side];
    const saved=(t?.evidence||[]).filter(e=>objectiveTitles.has(e.title));
    const facts=saved.length?saved:currentFacts(m,side);
    const name=t?.team||m.teams?.[side]?.label||m[side+'Label']||m[side]||(side==='home'?'主队':'客队');
    const observations=r?.observations||[];
    return `<section class="intent-team"><h3>${esc(name)} <span class="tag">客观背景</span></h3><p>${facts.filter(e=>e.title!=='本场取分影响').map(e=>esc(e.fact)).join('；')}</p>${facts.filter(e=>e.title==='本场取分影响').map(e=>`<p>${esc(e.fact)}</p>`).join('')}<p class="note">现有资料未收录可核对的本场目标表态，不从排名或近况判断球队是否接受平局。</p>
      <details class="er-disclosure" data-disclosure="motivation-${side}-basis"><summary>查看客观资料来源与待确认项目</summary>${facts.map(e=>`<p><strong>${esc(e.title)}</strong>：${esc(e.fact)}<br><small>${sourceLink(e.source)} ${esc(timeText(e.asOf))}</small></p>`).join('')}<p class="note">待确认：${(t?.missing||['本场教练赛前言论','确认首发与轮换']).map(esc).join('、')}</p></details>
      <details class="er-disclosure" data-disclosure="motivation-${side}-scenarios"><summary>查看条件性战术情境（非球队表态）</summary>${tacticalScenarios.map(text=>`<p>${esc(text)}</p>`).join('')}</details>
      ${observations.length?`<h4>赛后客观记录</h4><p>${observations.map(item=>`${esc(item.label)}：${esc(item.observed)}`).join('；')}</p>`:''}
      ${legacy?`<details class="er-disclosure" data-disclosure="motivation-${side}-original"><summary>查看旧版原始赛前记录（仅供审计）</summary><p class="note">旧版由排名、主客场和近况生成推测标签，不作为当前有效结论；原记录保留，赛果不能证明主观心态。</p><p>版本 ${esc(original.version)} · 记录 ${esc(String(original.hash||'').slice(0,12))}</p><p>原标签：${esc(t?.tendency)}；原摘要：${esc(t?.summary)}</p><p>原接受平局判断：${esc(t?.drawAcceptance)}；原依据强度：${esc(t?.confidence)}；原主动求败判断：${esc(t?.loseIntent)}</p>${(t?.evidence||[]).map(e=>`<p>${esc(e.title)}：${esc(e.fact)}<br>原推论：${esc(e.inference)} ${sourceLink(e.source)} ${esc(timeText(e.asOf))}</p>`).join('')}${(t?.checks||[]).map(c=>`<p>原登记指标：${esc(c.label)}</p>`).join('')}${r&&!observations.length?`<p>旧版复核原文：${esc(r.summary)}</p>${(r.checks||[]).map(c=>`<p>${esc(c.label)} · ${esc(c.observed)} · 原判定：${c.passed===true?'支持':c.passed===false?'未支持':'待资料'}</p>`).join('')}`:''}<p>${esc(original.method)} ${esc(original.reviewMethod)}</p></details>`:''}</section>`;
  }).join('')}</div>`;
}
export function alertsHtml(m,alerts){
  if(!alerts.length)return '<p class="note">当前可比较资料中，未发现达到提醒门槛的变化（盘口 0.5 球或同盘口赔率 15%）。同一主客场的历史交锋至少需要两次同机构报价；盘口缺失时不作“没有变化”的判断。</p>';
  return alerts.slice(0,6).map(a=>`<section class="odds-alert"><h3>${esc(a.type)} · ${esc(a.provider)}</h3><p><strong> ${esc(alertSubject(a))}：${alertValue(a,a.from)} → ${alertValue(a,a.to)}</strong>，${a.measure==='price'?'赔率变化 '+Math.abs(a.change*100).toFixed(1)+'%':'相差 '+Math.abs(a.change)+' 球'}</p><p class="note">${esc(a.basis)} · 当前报价采集 ${esc(timeText(a.current.fetchedAt))} ${sourceLink(a.current.source)}</p><details class="er-disclosure" data-disclosure="alert-${esc(JSON.stringify([a.market,a.provider,a.current.via,a.type,a.selection]))}"><summary>查看历史报价与可能原因</summary>${a.samples.map(s=>`<p>${esc(s.date)} · ${alertValue(a,a.measure==='price'?s.quote.prices[a.selection]:s.quote.line)} · ${esc(s.quote.provider)} ${sourceLink(s.quote.source)}</p>`).join('')}<p><strong>可核实的相关资料</strong></p>${Object.values(m.motivation?.original?.teams||{}).flatMap(t=>t.evidence.filter(e=>e.title!=='比赛场地').map(e=>`<p>${esc(t.team)} · ${esc(e.fact)} ${sourceLink(e.source)}</p>`)).join('')||'<p class="note">暂无足够的积分或阵容资料解释此次调整。</p>'}${(m.relatedNews||[]).map(n=>`<p>${sourceLink(n.url,n.titleZh||n.title)} <small>${esc(timeText(n.publishedAt))}</small></p>`).join('')}<p class="note">上述资料提供核查线索，尚不能确认就是变盘原因。继续核对已公布首发、关键伤停与换帅；跨赛季、不同报价阶段及样本较少都会影响可比性。</p></details></section>`).join('');
}
export function globalEventsHtml(m){
  if(!m.events?.length)return '<p class="note">来源尚未提供本场事件，比分仍独立更新。</p>';
  return `<div class="daily-events">${m.events.map(e=>`<p><b>${esc(e.clock)}</b><span>${esc(e.kind)} · ${esc(e.teamId===m.teams?.home?.id?m.homeLabel:e.teamId===m.teams?.away?.id?m.awayLabel:'')} ${e.players.map(esc).join(' / ')}${e.ownGoal?'（乌龙）':''}${e.penalty?'（点球）':''}</span></p>`).join('')}</div><p class="note">仅展示来源已收录事件。</p>`;
}
