import {esc,timeText} from './ui.mjs';
import {evidenceReviewHtml} from './evidence-review.mjs';

const supported=m=>['700','710','720','730','740'].includes(String(m.competitionId))||['epl','laliga','seriea','bundesliga'].includes(m.league);
const line=v=>v===0?'平手':`${v<0?'让':'受让'} ${Math.abs(v)} 球`;
const source=url=>/^https:\/\//.test(url||'')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">来源 ↗</a>`:'';

export function forecastMatches(value,m){
  return value?.supported===true&&value.eventId===(m.dailyId||m.id)&&Date.parse(value.kickoff)===Date.parse(m.kickoff)
    &&['home','away'].every(s=>String(value.teams?.[s])===String(m.teams?.[s]?.id));
}

export function forecastsHtml(m,value,at=Date.now()){
  if(!supported(m))return '';
  const valid=forecastMatches(value,m),ended=Date.parse(m.kickoff)<=at||m.started||m.finished;
  const due=Date.parse(m.kickoff)-6*3600000;
  return `<section class="football-forecasts" aria-label="两阶段自动预测"><div class="forecast-grid">${[['initial','初步预测'],['final','首发确认后预测']].map(([stage,label])=>{
    const data=valid?value.stages?.[stage]:null,r=data?.report,q=r?.quote;
    const side=r?.asianSide==='H'?'home':'away',name=m.teams?.[side]?.label||m[side+'Label']||m[side];
    const direction=r?.asianSide==='pass'?(q?'暂不选边':'盘口待更新'):`${name} ${line(side==='home'?q?.line:-q?.line)}`;
    const message=data?.message||(ended?'本阶段没有可核对的赛前记录':stage==='initial'?`预计 ${timeText(new Date(due).toISOString())} 自动生成`:'等待双方正式首发，开赛前90分钟内自动检查');
    const reference=r?.reference?`<p class="note forecast-reference"><strong>赛前参考版</strong> · 报价文件更新 ${esc(timeText(r.reference.sourceUpdatedAt))}，非即时盘口。${source(r.reference.source)}</p>`:'';
    return `<div class="forecast-card ${r?'has-forecast':''}"><h3>${label}<span>${r?'已保存':ended?'未留存赛前记录':'等待生成'}</span></h3>${r?`${reference}<p class="forecast-result"><strong>${esc(direction)}</strong><b>${r.score.map(esc).join(' : ')}</b></p><p class="note">比分主队在前 · ${esc(timeText(r.issuedAt))}</p>${r.summary.map(p=>`<p>${esc(p)}</p>`).join('')}<details><summary>更多预测依据</summary>${r.details.map(d=>`<h4>${esc(d.title)}</h4><p>${esc(d.text)}</p>`).join('')}<p class="note">${esc(r.baseline?.method||'')} · ${esc(r.model)} · 资料核对 ${esc(timeText(r.researchAt))}</p>${q?`<p class="note">主队${line(q.line)} · 主 ${Number(q.prices.H).toFixed(2)} / 客 ${Number(q.prices.A).toFixed(2)} · ${esc(q.provider)} · 采集 ${esc(timeText(q.fetchedAt))} ${source(q.source)}</p>`:'<p class="note">本版没有可核对的即时亚洲盘，保留比分预测。</p>'}</details>${r.review?.status==='evaluated'?`<p class="forecast-review">${esc(r.review.text)} ${source(r.review.source)}</p>`:r.review?.text?`<p class="note">${esc(r.review.text)}</p>`:''}`:`<p class="note">${esc(message)}</p>`}</div>`;
  }).join('')}</div><p class="note forecast-policy">初版默认开赛前6小时生成；正式首发齐全后自动生成临场版。两版独立留存，赛后分别对照。</p>${valid?[['initial','初步预测'],['final','首发确认后预测']].map(([stage,label])=>{const review=value.stages?.[stage]?.report?.review?.analysis;return review?`<section class="forecast-evidence-review"><h2>${label} · 赛后复盘</h2>${evidenceReviewHtml(review)}</section>`:'';}).join(''):''}</section>`;
}
