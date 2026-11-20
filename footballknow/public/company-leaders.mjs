import {esc,sourceLink} from './ui.mjs';

export function chairmenHtml(company){
  const data=company?.leadership,people=data?.people||[];
  if(!people.length)return '<div class="empty">'+esc(company?.profile?.chairman?'主席：'+company.profile.chairman+'。来源暂未提供可核实的公开履历。':'来源暂未提供现任主席资料。')+'</div>';
  return people.map(p=>`<article class="chair-profile">${p.photo?`<figure><img class="chair-photo" src="${esc(p.photo.url)}" alt="${esc(p.name)}" loading="lazy" referrerpolicy="no-referrer"><figcaption>${sourceLink(p.photo.source,p.photo.credit)} · 核对 ${esc(p.photo.checkedAt)}</figcaption></figure>`:''}<div><h3>${esc(p.name)}</h3><p class="lede">${esc(p.position)}</p><dl class="identity-grid"><div><dt>任职起始日</dt><dd>${esc(p.startedAt||'—')}</dd></div><div><dt>学历</dt><dd>${esc(p.degree||'—')}</dd></div></dl><h4>任职经历与职责</h4>${p.career.length?p.career.map(x=>`<p>${esc(x)}。</p>`).join(''):'<p>来源暂未提供。</p>'}${p.education.length?`<h4>教育经历</h4>${p.education.map(x=>`<p>${esc(x)}。</p>`).join('')}`:''}</div></article>`).join('')+`<p class="note">${sourceLink(data.source,data.sourceLabel)} · 采集 ${esc(new Date(data.updatedAt).toLocaleString('zh-CN'))}。${esc(data.scope)}${company.failedSections?.includes('leadership')?' 本次更新未成功，保留上次资料。':''}</p>`;
}
