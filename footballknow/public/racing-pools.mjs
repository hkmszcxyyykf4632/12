import {esc} from './ui.mjs';
import {table,val,stamp,horseLink} from './racing-ui.mjs';

const labels={WIN:'独赢',PLA:'位置',QIN:'连赢',QPL:'位置连赢'};
export function quoteFor(race,type,no){return race.pools?.find(p=>p.type===type)?.quotes?.find(q=>q.combination===String(Number(no)));}
export function quoteMarkup(q,missing='待公布'){
  if(!q)return `<span class="muted">${esc(missing)}</span>`;
  const value=Number(q.value),first=Number(q.first),changed=q.first&&Number.isFinite(value)&&Number.isFinite(first)&&value!==first;
  const trend=changed?value<first?'odds-shorter':'odds-longer':'';
  return `<strong class="race-price ${q.favourite?'race-favourite':''} ${trend}">${val(q.value)}</strong>${changed?`<small class="${trend}">${value<first?'↓':'↑'} 首录 ${val(q.first)}</small>`:''}`;
}
export function dividendsHtml(race){
  const rows=(race.dividends||[]).filter(d=>labels[d.type]);
  return rows.length?`<div class="race-dividends">${rows.map(d=>`<div><span>${labels[d.type]}</span><strong>${esc(d.combination.replaceAll(',','－'))}</strong><b>${d.amount==null?esc(d.display):'$'+Number(d.amount).toFixed(2)}</b></div>`).join('')}</div><p class="note">正式派彩 · 每注港币 10 元，金额为港元。</p>`:'<p class="note">正式派彩尚未发布。</p>';
}
export function poolsHtml(race){
  const pools=race.pools||[],win=pools.find(p=>p.type==='WIN'),place=pools.find(p=>p.type==='PLA'),qin=pools.find(p=>p.type==='QIN');
  const checking=[...pools].sort((a,b)=>(b.checkedAt||'').localeCompare(a.checkedAt||''))[0]?.checkedAt;
  const open=pools.some(p=>/START_SELL|SELLING_STARTED/i.test(p.sellStatus||p.status||''));
  const stale=checking&&Date.now()-Date.parse(checking)>180000;
  const state=race.status==='finished'?'赛后保留报价':stale?'最近保存报价':open?'最新赔率':'未开盘 / 已封盘';
  let html=`<section class="race-odds-section"><div class="section-head"><h2>独赢 · 位置 · 连赢</h2><span class="race-status ${open&&!stale?'status-live':''}">${state}</span></div><p class="note">来源：香港赛马会公开赔率 · 最近检查 ${stamp(checking)} · 独赢更新 ${stamp(win?.sourceUpdatedAt)} · 位置更新 ${stamp(place?.sourceUpdatedAt)}</p>`;
  html+=table(['马号 / 马匹','独赢','位置','独赢首次收录','位置首次收录'],race.entries.map(h=>[`${esc(h.number)} · ${horseLink(h)}`,h.withdrawn?'退出':quoteMarkup(quoteFor(race,'WIN',h.number),race.status==='finished'?'未收录':'待公布')+(race.status==='finished'&&!quoteFor(race,'WIN',h.number)&&h.winOdds!=null?`<small>赛果独赢 ${val(h.winOdds)}</small>`:''),h.withdrawn?'退出':quoteMarkup(quoteFor(race,'PLA',h.number),race.status==='finished'?'未收录':'待公布'),val(quoteFor(race,'WIN',h.number)?.first),val(quoteFor(race,'PLA',h.number)?.first)]));
  const pairs=qin?.quotes||[],name=no=>race.entries.find(h=>Number(h.number)===Number(no))?.name||'';
  html+=`<details class="quinella-detail"><summary>连赢组合赔率 · ${pairs.length} 个组合</summary><p class="note">两匹马分列前两名，不分先后 · 来源更新 ${stamp(qin?.sourceUpdatedAt)}</p>${table(['组合马号','马匹','最新赔率','首次收录'],pairs.map(q=>[esc(q.combination.replaceAll(',','－')),q.combination.split(',').map(n=>esc(name(n))).join(' / '),quoteMarkup(q),val(q.first)]))}</details>`;
  if(race.status==='finished'||race.dividends?.length)html+='<h3>正式派彩</h3>'+dividendsHtml(race);
  return html+'<p class="note">箭头与首次收录报价比较。首次收录不是官方开盘价；尚未收录的历史报价留空。独赢、位置和连赢赔率会随彩池变化，封盘后保留最后取得的报价。</p></section>';
}
