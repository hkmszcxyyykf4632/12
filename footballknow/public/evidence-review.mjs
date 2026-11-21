const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const list=value=>Array.isArray(value)?value:[];
const verdicts={supported:'证据支持',contradicted:'证据反驳',unresolved:'尚不能判断'};
const categories={method:'方法与遗漏',unexpected:'事后新情况',unresolved:'仍待查明'};
const stamp=value=>typeof value==='string'&&value.includes('T')&&Number.isFinite(Date.parse(value))
  ?new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Hong_Kong',hour12:false})+'（香港时间）':String(value??'');

function safeHref(value){
  const text=String(value??'');
  if(/[\\\u0000-\u0020\u007f]/.test(text))return '';
  let decoded;try{decoded=decodeURIComponent(text);}catch{return '';}
  if(/[\\\u0000-\u001f\u007f]/.test(decoded))return '';
  if(text.startsWith('/'))return !decoded.startsWith('//')&&text[1]!=='/'?text:'';
  try{const url=new URL(text);return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password?url.href:'';}catch{return '';}
}

function prefix(report){
  const revision=String(report.revision??'').replace(/[^a-zA-Z0-9_-]/g,'').slice(0,20);
  if(revision)return `er-${revision}`;
  let hash=2166136261;for(const char of JSON.stringify(report))hash=Math.imul(hash^char.charCodeAt(0),16777619);
  return `er-${(hash>>>0).toString(16)}`;
}

export function evidenceReviewHtml(report,{compact=false,disclosurePrefix='review'}={}){
  if(!report||typeof report!=='object'||!report.dossier)return '';
  const dossier=report.dossier,base=prefix(report);
  const facts=list(dossier.facts),sources=list(dossier.sources);
  const factIndex=new Map(facts.map((fact,index)=>[fact.id,index]));
  const sourceIndex=new Map(sources.map((source,index)=>[source.id,index]));
  const prose=value=>{let text=String(value??'');for(const [id,index] of factIndex)text=text.split(id).join(`证据 ${index+1}`);return esc(text);};
  const citations=ids=>{
    const indexes=[...new Set(list(ids).map(id=>factIndex.get(id)).filter(index=>index!==undefined))];
    return indexes.length?`<span class="er-citations">${indexes.map(index=>`<a data-evidence-anchor href="#${base}-fact-${index+1}" aria-label="查看证据 ${index+1}">证据 ${index+1}</a>`).join('')}</span>`:'';
  };
  const sourceRefs=ids=>list(ids).filter(id=>sourceIndex.has(id)).map(id=>{
    const index=sourceIndex.get(id);
    return `<a data-evidence-anchor href="#${base}-source-${index+1}">${esc(sources[index].title||'资料来源')}</a>`;
  }).join(' · ');
  const section=(title,body,cls='')=>`<section class="er-section ${cls}"><h3>${title}</h3>${body}</section>`;
  const disclosure=(key,title,body)=>compact
    ?`<details class="er-section er-disclosure" data-disclosure="${esc(disclosurePrefix)}-${key}"><summary>${title}</summary><div class="er-disclosure-body">${body}</div></details>`
    :section(title,body);
  const card=(title,body,badge='')=>`<article class="er-card"><div class="er-card-heading"><h4>${esc(title)}</h4>${badge}</div>${body}</article>`;
  const badge=(text,tone='neutral')=>`<span class="er-badge er-${tone}">${esc(text)}</span>`;
  const status=report.analysisStatus==='ready'?'已整理详细复盘':report.analysisStatus==='limited'?'证据不足，详细原因分析尚未完成':'详细原因分析尚未完成';
  let html=`<div class="evidence-review" aria-label="详细复盘"><header class="er-header"><h2>事实、判断与改进</h2>${badge(status,report.analysisStatus==='ready'?'neutral':'pending')}</header>`;
  html+=`<div class="er-summary">${list(report.summary).map(text=>`<p>${prose(text)}</p>`).join('')}</div>`;
  if(report.generatedAt)html+=`<p class="er-meta">复盘整理时间：${esc(stamp(report.generatedAt))}</p>`;
  const timeline=list(dossier.timeline);
  html+=disclosure('timeline','实际发生了什么',timeline.length?`<ol class="er-timeline">${timeline.map(event=>`<li><span class="er-time">${esc(stamp(event.time)||'时间未提供')}</span><div><p>${esc(event.text)}</p>${citations(event.evidenceIds)}</div></li>`).join('')}</ol>`:'<p class="er-muted">目前没有可核对的事件时间线。</p>');
  const claims=dossier.original?list(dossier.claims):[];
  const audits=new Map(list(report.claimAudits).map(audit=>[audit.claimId,audit]));
  html+=disclosure('claims','原判断逐条核对',claims.length?`<div class="er-stack">${claims.map((claim,index)=>{
    const audit=audits.get(claim.id),verdict=verdicts[audit?.verdict]?audit.verdict:'unresolved';
    return card(`原判断 ${index+1}`,`<blockquote>${esc(claim.text)}</blockquote><p>${prose(audit?.explanation||'原判断已保留，详细核对尚未完成。')}</p>${citations(audit?.evidenceIds)}`,badge(verdicts[verdict],verdict));
  }).join('')}</div>`:`<p class="er-muted">${dossier.original?'原记录没有保存可逐条核对的分析原文。':'没有保存的原预测；这里只整理事实，不补写当时的判断或声称漏看了什么。'}</p>`);
  html+=section('关键转折与可能原因',list(report.drivers).length?`<div class="er-stack">${report.drivers.map(driver=>card(driver.title,`<p>${prose(driver.explanation)}</p>${citations(driver.evidenceIds)}`,badge(driver.kind==='observed'?'已核实事实':'可能解释',driver.kind==='observed'?'neutral':'pending'))).join('')}</div>`:'<p class="er-muted">目前尚无足够证据形成详细原因分析。</p>');
  html+=disclosure('market',dossier.domain==='stocks'?'价格与市场对照':'盘口与赔率研究',list(report.marketReview).length?`<div class="er-stack">${report.marketReview.map(item=>card(item.title,`<p>${prose(item.explanation)}</p>${citations(item.evidenceIds)}`)).join('')}</div>`:'<p class="er-muted">目前没有足够的可比记录形成市场变化研究，具体缺项见下方。</p>');
  const lessons=list(report.lessons).filter(lesson=>lesson.category!=='method'||claims.length);
  html+=disclosure('lessons','下次怎样检验改进',`<p class="er-policy">改进建议均为待验证的候选检查项，需要用后续样本检验；不能因一次结果就认定有效，也不改写原预测。</p>${lessons.length?`<div class="er-stack">${lessons.map(lesson=>{
    const related=claims.filter(claim=>list(lesson.claimIds).includes(claim.id));
    return card(lesson.title,`<p>${prose(lesson.explanation)}</p>${related.map(claim=>`<blockquote><span class="er-muted">对应原判断：</span>${esc(claim.text)}</blockquote>`).join('')}<div class="er-next"><h5>下一次检查与验证</h5><p>${prose(lesson.nextCheck)}</p></div>${citations(lesson.evidenceIds)}`,badge(categories[lesson.category]||categories.unresolved,'pending'));
  }).join('')}</div>`:'<p class="er-muted">暂未形成有证据支持的具体改进建议。</p>'}`);
  html+=disclosure('gaps','尚缺哪些资料',list(dossier.gaps).length?`<ul class="er-gaps">${dossier.gaps.map(gap=>`<li>${esc(gap)}</li>`).join('')}</ul>`:'<p class="er-muted">当前记录没有列出具体缺项；这不代表资料完整。</p>');
  html+=`<details class="er-evidence"${compact?` data-disclosure="${esc(disclosurePrefix)}-facts"`:''}><summary>查看逐项证据（${facts.length}）</summary><ol class="er-facts">${facts.map((fact,index)=>`<li id="${base}-fact-${index+1}" tabindex="-1"><h4>证据 ${index+1}</h4>${fact.time?`<p class="er-meta">记录时点：${esc(stamp(fact.time))}</p>`:''}<p>${esc(fact.text)}</p><div class="er-source-refs">${sourceRefs(fact.sourceIds)||'来源未提供'}</div></li>`).join('')}</ol></details>`;
  html+=disclosure('sources','资料来源',sources.length?`<ul class="er-sources">${sources.map((source,index)=>{
    const href=safeHref(source.url),title=esc(source.title||'资料来源');
    return `<li id="${base}-source-${index+1}" tabindex="-1">${href?`<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${title} ↗</a>`:title}<small>来源采集／更新时间：${esc(stamp(source.updatedAt)||'未提供')}；不是公告首次公开时间。</small></li>`;
  }).join('')}</ul>`:'<p class="er-muted">来源暂未提供。</p>');
  return html+'</div>';
}

const boundTargets=new WeakSet();
export function bindEvidenceReview(target=globalThis.document){
  if(!target?.addEventListener||boundTargets.has(target))return;
  boundTargets.add(target);
  target.addEventListener('click',event=>{
    const link=event.target.closest?.('a[data-evidence-anchor]');
    if(!link||!target.contains(link)||event.button>0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    const region=link.closest('.evidence-review');
    if(!region)return;
    const anchor=link.getAttribute('href')?.slice(1);
    const destination=[...region.querySelectorAll('[id]')].find(element=>element.id===anchor);
    if(!destination)return;
    event.preventDefault();
    for(let parent=destination.parentElement;parent&&parent!==region;parent=parent.parentElement){
      if(parent.tagName==='DETAILS')parent.open=true;
    }
    destination.focus({preventScroll:true});
    destination.scrollIntoView?.({block:'start',behavior:'instant'});
  });
}
