import {history} from './repository.mjs';
import {esc,cn,dateText,sourceLink,today} from './ui.mjs';
import {transferPlayer,timestamp} from './football-components.mjs';

const reasonLabel=reason=>({'Sacked':'解职','Resigned':'辞任','Mutual consent':'双方同意离任','End of interim spell':'临时任期结束','End of contract':'合约届满','Retired':'退休'}[reason]||reason||'未注明');
const managerLabel=name=>String(name).replace(/\(interim\)/gi,'（临时领队）').replace(/\(caretaker\)/gi,'（看守领队）');

export function historySections(team) {
  const transfers=history?.transfers.filter(row=>[row.fromTeam,row.toTeam].includes(team.name))||[];
  const managers=history?.managers.filter(row=>row.team===team.name)||[];
  return `<section id="transfers-section"><div class="section-head"><div><h2>转会记录</h2></div><span class="small subtle">最近两个赛季</span></div><div class="toolbar"><p class="note">转入、转出及租借 · ${transfers.length} 条已收录记录</p><select class="filter-select" id="transfer-filter" aria-label="筛选转会方向"><option value="all">全部转会</option><option value="in">转入本队</option><option value="out">转出本队</option><option value="loan">只看租借</option></select></div><div id="transfer-rows">${transferTable(transfers)}</div><p class="note">${history?'最近检查：'+timestamp(history.updatedAt):'转会来源暂未就绪。'} · 未公开的费用保持为空；每条记录可追溯原来源。</p></section>
    <section id="managers-section"><div class="section-head"><div><h2>领队更换</h2></div></div>${managers.length?`<div class="manager-timeline">${managers.map(row=>`<article class="manager-entry"><div class="manager-date">${dateText(row.joinedAt||row.leftAt)}<span class="tag">${row.joinedAt&&row.joinedAt>today()?'已公布 · 尚未上任':'已记录变更'}</span></div><div><h3>${esc(managerLabel(row.outgoing))}<span class="manager-arrow" aria-hidden="true">→</span>${esc(managerLabel(row.incoming))}</h3><p>离任：${dateText(row.leftAt)} · 上任：${dateText(row.joinedAt)} · ${esc(reasonLabel(row.reason))}</p>${sourceLink(row.source,'查看公告 / 来源')}</div></article>`).join('')}</div>`:`<div class="empty">${history?'近两个赛季暂未收录领队更换记录；这不表示球队没有领队。':'领队更换资料暂未获取。'}</div>`}</section>`;
}

function transferTable(rows) {
  if(!rows.length)return '<div class="empty">当前筛选下没有已收录的转会记录。</div>';
  return `<div class="table-wrap"><table><thead><tr><th>日期</th><th>球员</th><th>来自</th><th>前往</th><th>类型 / 费用</th><th>来源</th></tr></thead><tbody>${rows.map(row=>`<tr><td>${row.date?dateText(row.date):esc(row.window||'日期未列')}${row.date>today()?'<small>已公布 · 尚未生效</small>':''}</td><td class="player-name history-player">${transferPlayer(row.player)}</td><td>${esc(cn(row.fromTeam))}</td><td>${esc(cn(row.toTeam))}</td><td>${esc(row.type)}<small>${esc(row.fee)}${row.endDate?' · 租借至 '+dateText(row.endDate):''}</small></td><td>${sourceLink(row.source)}</td></tr>`).join('')}</tbody></table></div>`;
}

export function bindHistory(team) {
  document.querySelector('#transfer-filter')?.addEventListener('change',event=>{
    const choice=event.target.value;
    const rows=(history?.transfers||[]).filter(row=>[row.fromTeam,row.toTeam].includes(team.name)&&
      (choice==='all'||choice==='in'&&row.toTeam===team.name||choice==='out'&&row.fromTeam===team.name||choice==='loan'&&row.type.startsWith('租借')));
    document.querySelector('#transfer-rows').innerHTML=transferTable(rows);
  });
}
