import {esc,timeText} from './ui.mjs';
import {evidenceReviewHtml} from './evidence-review.mjs';
import {settleLine,SETTLEMENT_NAMES} from './settlement.mjs';

const supported=m=>m.competitionId!=null?['700','740','730','720','775'].includes(String(m.competitionId)):['epl','laliga','seriea','bundesliga','ucl'].includes(m.league);
const line=v=>v===0?'平手':`${v<0?'让':'受让'} ${Math.abs(v)} 球`;
const source=url=>/^https:\/\//.test(url||'')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">来源 ↗</a>`:'';

export function forecastMatches(value,m){
  return value?.supported===true&&value.eventId===(m.dailyId||m.id)&&Date.parse(value.kickoff)===Date.parse(m.kickoff)
    &&['home','away'].every(s=>String(value.teams?.[s])===String(m.teams?.[s]?.id));
}

function scoreRelationship(m,r){
  if(!Array.isArray(r.score)||r.score.length!==2||!r.score.every(n=>Number.isInteger(n)&&n>=0))return '';
  const name=side=>m.teams?.[side]?.label||m[side+'Label']||m[side]||(side==='home'?'主队':'客队');
  const difference=r.score[0]-r.score[1],result=difference===0?'双方打平':`${name(difference>0?'home':'away')}赢球`;
  let handicap='';
  if(['H','A'].includes(r.asianSide)&&r.quote){
    const home=r.asianSide==='H',selectedLine=home?r.quote.line:-r.quote.line;
    const settlement=settleLine(home?difference:-difference,selectedLine);
    if(settlement!==null)handicap=`；${name(home?'home':'away')} ${line(selectedLine)}：${SETTLEMENT_NAMES[settlement]}`;
  }
  return `<p class="forecast-score-meaning">按预测比分 ${r.score.map(esc).join(' : ')} 演算：${esc(result+handicap)}。</p>${handicap?'<p class="note">这是该比分对应的结算情境；亚洲盘方向还取决于全部比分概率与赔率。</p>':''}`;
}

function forecastNarrative(r,stage){
  const amendments=Array.isArray(r.amendments)?r.amendments:[],latest=amendments.at(-1);
  const original=(r.summary||[]).map(p=>`<p>${esc(p)}</p>`).join('');
  const details=(r.details||[]).map(d=>`<h4>${esc(d.title)}</h4><p>${esc(d.text)}</p>`).join('');
  if(!latest)return {summary:`${r.baselineExplanation?.text?`<p class="note">${esc(r.baselineExplanation.text)}</p>`:''}${original}`,details};
  const facts=['home','away'].map(side=>{
    const fact=latest.facts?.[side];if(!fact)return '';
    const parts=[fact.formSummary,fact.formation?`阵型 ${fact.formation}`:'',Number.isInteger(fact.previousRetained)?`较上一场保留 ${fact.previousRetained} 名首发`:'',Number.isInteger(fact.headToHeadRetained)?`较上次交锋保留 ${fact.headToHeadRetained} 名首发`:''].filter(Boolean);
    return `<p><strong>${esc(fact.name||'')}</strong>：${esc(parts.join('；'))}。</p>`;
  }).join('');
  const corrections=amendments.map(a=>`<p class="note">${esc(timeText(a.issuedAt))} · ${esc(a.reason)}</p><p>${esc(a.text)}</p>`).join('');
  return {summary:`<div class="forecast-amendment"><p><strong>说明已更正</strong> · ${esc(timeText(latest.issuedAt))}</p><p>${esc(latest.text)}</p><p class="note">原预测比分和亚洲盘方向保留，以下补充核对依据。</p></div>`,details:`${facts}${corrections}<details class="er-disclosure" data-disclosure="forecast-${stage}-original"><summary>原始说明（已更正）</summary>${original}${details}</details>`};
}

export function forecastsHtml(m,value,at=Date.now()){
  if(!supported(m))return '';
  const valid=forecastMatches(value,m),ended=Date.parse(m.kickoff)<=at||m.started||m.finished;
  const due=Date.parse(m.kickoff)-6*3600000;
  return `<section class="football-forecasts" aria-label="两阶段自动预测"><div class="forecast-grid">${[['initial','初步预测'],['final','首发确认后预测']].map(([stage,label])=>{
    const data=valid?value.stages?.[stage]:null,r=data?.report,q=r?.quote,narrative=r?forecastNarrative(r,stage):null;
    const side=r?.asianSide==='H'?'home':'away',name=m.teams?.[side]?.label||m[side+'Label']||m[side];
    const direction=r?.asianSide==='pass'?(q?'暂不选边':'盘口待更新'):`${name} ${line(side==='home'?q?.line:-q?.line)}`;
    const message=data?.message||(ended?'本阶段没有可核对的赛前记录':stage==='initial'?`预计 ${timeText(new Date(due).toISOString())} 自动生成`:'等待双方正式首发，开赛前两小时开始检查');
    const reference=r?.reference?`<p class="note forecast-reference"><strong>赛前参考版</strong> · 报价文件更新 ${esc(timeText(r.reference.sourceUpdatedAt))}，非即时盘口。${source(r.reference.source)}</p>`:'';
    return `<div class="forecast-card ${r?'has-forecast':''}"><h3>${label}<span>${r?'已保存':ended?'未留存赛前记录':'等待生成'}</span></h3>${r?`${reference}<p class="forecast-result"><strong>${esc(direction)}</strong><b>${r.score.map(esc).join(' : ')}</b></p><p class="note">比分主队在前 · ${esc(timeText(r.issuedAt))}</p>${scoreRelationship(m,r)}${narrative.summary}<details class="er-disclosure" data-disclosure="forecast-${stage}-basis"><summary>更多预测依据</summary>${narrative.details}<p class="note">${esc(r.baseline?.method||'')} · ${esc(r.model)} · 资料核对 ${esc(timeText(r.researchAt))}</p>${q?`<p class="note">主队${line(q.line)} · 主 ${Number(q.prices.H).toFixed(2)} / 客 ${Number(q.prices.A).toFixed(2)} · ${esc(q.provider)} · 采集 ${esc(timeText(q.fetchedAt))} ${source(q.source)}</p>`:'<p class="note">本版没有可核对的即时亚洲盘，保留比分预测。</p>'}</details>${r.review?.status==='evaluated'?`<p class="forecast-review">${esc(r.review.text)} ${source(r.review.source)}</p>`:r.review?.text?`<p class="note">${esc(r.review.text)}</p>`:''}`:`<p class="note">${esc(message)}</p>`}</div>`;
  }).join('')}</div><p class="note forecast-policy">初版默认开赛前6小时生成；开赛前两小时优先检查，正式首发齐全后生成临场版。两版独立留存，赛后分别对照。</p>${valid?[['initial','初步预测'],['final','首发确认后预测']].map(([stage,label])=>{const review=value.stages?.[stage]?.report?.review?.analysis;return review?`<section class="forecast-evidence-review"><h2>${label} · 赛后复盘</h2>${evidenceReviewHtml(review,{compact:true,disclosurePrefix:`forecast-${stage}-review`})}</section>`:'';}).join(''):''}</section>`;
}

export function forecastSummaryHtml(m,value){
  if(!forecastMatches(value,m))return '<span class="subtle">本场尚无已保存预测</span>';
  const stage=value.stages?.final?.report?'final':'initial',report=value.stages?.[stage]?.report;
  if(!report)return '<span class="subtle">本场尚无已保存预测</span>';
  const side=report.asianSide==='H'?'home':'away',name=m.teams?.[side]?.label||m[side+'Label']||m[side];
  const pick=report.asianSide==='pass'?'亚洲盘暂不选边':report.quote&&['H','A'].includes(report.asianSide)?`${name} ${line(side==='home'?report.quote.line:-report.quote.line)}`:'亚洲盘未记录';
  return `<span class="forecast-brief-stage">${stage==='final'?'临场版':'初步版'}</span><strong>${esc(pick)}</strong><span>预测比分 <b>${report.score.map(esc).join(' : ')}</b></span>${m.finished&&report.review?.status==='evaluated'?'<span class="tag">已复盘</span>':''}`;
}
