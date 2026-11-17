import {esc,sourceLink} from './ui.mjs';

export const capitalCategory=(data,code)=>data?.rows?.[code]?.category||'unknown';
export function capitalBadge(row){return `<span class="capital-badge capital-${esc(row?.category||'unknown')}">${esc(row?.label||'待补资料')}</span>${row?.reportDate?`<small>报告期 ${esc(row.reportDate)}</small>`:''}`;}
export function capitalDetail(row,method){
  if(!row)return '<p class="note">现金与负债资料正在同步。</p>';
  const amount=v=>Number.isFinite(v)?(v/1e8).toLocaleString('zh-CN',{maximumFractionDigits:2}):'—';
  return `<section class="capital-panel"><div class="section-head"><h2>现金与负债分类</h2>${capitalBadge(row)}</div><dl class="stat-grid"><div><dt>现金及存款</dt><dd>${amount(row.cash)} 亿</dd></div><div><dt>借款、债券与租赁</dt><dd>${amount(row.debt)} 亿</dd></div><div><dt>两者差额</dt><dd class="capital-${row.category}">${amount(row.net)} 亿</dd></div></dl><p class="note">${esc(row.currency||'币种待提供')} · ${esc(method||'按最新报告期的同币种字段比较。')}</p>${row.components?.length?`<details><summary>查看计算依据</summary><div class="table-wrap"><table><thead><tr><th>分组</th><th>报表项目</th><th>金额（亿元）</th></tr></thead><tbody>${row.components.map(r=>`<tr><td>${r.group==='cash'?'现金及存款':'借款债券租赁'}</td><th>${esc(r.name)}</th><td>${amount(r.amount)}</td></tr>`).join('')}</tbody></table></div>${sourceLink(row.source,row.sourceLabel||'报表来源')}</details>`:''}</section>`;
}
