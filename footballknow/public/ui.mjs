import {OUTCOMES} from './core.mjs';
import {data} from './repository.mjs';
import {league} from './league.mjs';
export const main = document.querySelector('#main');
export const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[ch]));
export const amount = cents => (cents / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const oddsText = number => number == null ? '—' : Number(number).toFixed(2);
export const dateText = date => date ? date.slice(0, 10).replaceAll('-', '.') : '—';

let toastTimer;
export function toast(message) {
  const element = document.querySelector('#toast');
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove('show'), 4200);
}
export const team = name => data.teams.find(t => t.name === name);
export const cn = name => team(name)?.cn || name;
export const monogram = (t, extra = '') => `<span class="team-monogram ${extra}" style="--club:${t.color}" aria-hidden="true">${esc(t.short)}</span>`;
export const recent = (t, onlyPremier = false) => data.matches.filter(m => m.finished && [m.home, m.away].includes(t.name) && (!onlyPremier || m.competition === league.name)).slice(0, 20);
export function resultFor(match, t) {
  return match.result === 'D' ? 'draw' : ((match.result === 'H') === (match.home === t.name)) ? 'win' : 'loss';
}
export function formRun(t) {
  return recent(t).slice(0, 5).map(m => {
    const result = resultFor(m, t);
    return `<span class="result ${result}" title="${esc(dateText(m.date) + ' ' + cn(m.home) + ' ' + m.homeGoals + ':' + m.awayGoals + ' ' + cn(m.away))}">${({win:'胜', draw:'平', loss:'负'})[result]}</span>`;
  }).join('');
}
export function pageHeading(title, subtitle, extra = '') {
  return `<div class="page-heading"><div><h1>${title}</h1><p class="lede">${subtitle}</p></div>${extra}</div>`;
}
export function matchTable(matches, chosenTeam) {
  if (!matches.length) return '<div class="empty">这个范围内暂时没有已完成的比赛。可切换到全部联赛查看。</div>';
  return `<div class="table-wrap"><table><thead><tr><th>日期 / 赛事</th><th>主队</th><th>比分</th><th>客队</th>${chosenTeam ? '<th>结果</th>' : ''}<th>主胜</th><th>平局</th><th>客胜</th><th>赔率来源</th><th></th></tr></thead><tbody>${matches.map(m => {
    const o = m.odds?.[0];
    const result = chosenTeam ? resultFor(m, chosenTeam) : '';
    return `<tr><td>${dateText(m.date)}<div class="small subtle">${esc(m.competition)}</div></td><td class="team-cell">${esc(cn(m.home))}</td><td class="score"><a href="#/match/${encodeURIComponent(m.id)}" aria-label="查看${esc(cn(m.home)+'对'+cn(m.away))}的阵容和数据">${m.homeGoals} : ${m.awayGoals}<small class="small subtle">阵容 ↗</small></a></td><td class="team-cell">${esc(cn(m.away))}</td>${chosenTeam ? `<td><span class="result ${result}">${({win:'胜',draw:'平',loss:'负'})[result]}</span></td>` : ''}${['H','D','A'].map(k => `<td>${o ? `<button class="odds-button" data-bet="${esc(m.id)}" data-selection="${k}" aria-label="${esc(cn(m.home) + ' 对 ' + cn(m.away) + '，' + OUTCOMES[k] + '赔率' + o[k])}">${oddsText(o[k])}</button>` : '<span class="subtle">—</span>'}</td>`).join('')}<td class="small subtle">${o ? esc(o.label) : '暂无历史赔率'}</td><td><button class="button quiet compact" data-bet="${esc(m.id)}">${o ? '模拟' : '录入赔率'}</button></td></tr>`;
  }).join('')}</tbody></table></div>`;
}

export const timeText = value => value ? new Date(value).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}) : '时间待定';
export function safeUrl(value) {try {const url=new URL(value);return ['https:','http:'].includes(url.protocol)?url.href:'';}catch{return '';}}
export function sourceLink(url,label='来源') {const safe=safeUrl(url);return safe?`<a class="source-link" href="${esc(safe)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:esc(label);}
export function today() {const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
