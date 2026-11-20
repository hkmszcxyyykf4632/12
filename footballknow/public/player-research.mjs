import {data,history} from './repository.mjs';
import {playerStats,playerOriginal,clubOf,POSITIONS,STATUS} from './player-stats.mjs';
import {esc,cn,dateText,sourceLink} from './ui.mjs';
import {localized} from './football-components.mjs';
const label=p=>localized(p)?.mandarin||p.web_name;
const normalized=v=>String(v||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]/g,'');
export function importantPlayer(p){
  const own=playerStats(p),mates=data.players.filter(x=>x.team===p.team).map(x=>({id:x.id,minutes:playerStats(x).minutes||0})).sort((a,b)=>b.minutes-a.minutes||a.id-b.id);
  return own.minutes>=450&&own.minutes>=(mates[0]?.minutes||Infinity)*.65&&mates.slice(0,5).some(x=>x.id===p.id);
}
export function playerStar(p){return importantPlayer(p)?'<span class="important-player" title="本队本赛季分钟前5，至少450分钟且达到队内最多分钟的65%" aria-label="重要球员">★</span>':'';}
export function playerResearch(p){
  const team=clubOf(p),s=playerStats(p),keys=new Set([playerOriginal(p),p.web_name].map(normalized)),today=new Date().toISOString().slice(0,10);
  const incoming=(history?.transfers||[]).filter(t=>t.toTeam===team?.name&&keys.has(normalized(t.player))&&t.date<=today).sort((a,b)=>b.date.localeCompare(a.date))[0];
  const joined=incoming?.date||p.team_join_date,isNew=joined&&Date.parse(joined)<=Date.now()&&Date.now()-Date.parse(joined)<365*86400000;
  const mates=data.players.filter(x=>x.team===p.team),maximum=Math.max(...mates.map(x=>playerStats(x).minutes||0)),share=maximum&&s.minutes!=null?s.minutes/maximum:null;
  const usage=s.minutes==null?'出场资料不足':s.minutes<270?'出场样本仍少':share>=.65?'已获得较多比赛时间':share>=.25?'处于轮换使用阶段':'目前出场占比较低';
  return `<section class="player-research"><div class="section-head"><h2>状态与球队融入 ${playerStar(p)}</h2>${isNew?'<span class="tag">近一年加盟</span>':''}</div><p><b>${usage}</b>。${s.minutes!=null?`本赛季已收录 ${s.minutes} 分钟，${s.starts??'—'} 次首发、${s.goals??'—'} 球、${s.assists??'—'} 次助攻。`:''}${importantPlayer(p)?'按已收录出场时间，列为本队重点关注球员。':''}</p><p>${isNew?`加盟日期 ${dateText(joined)}，需要继续观察其首发稳定性、同位置竞争和连续出场后的贡献。`:'结合本赛季使用情况和近期出场状态跟踪。'}${p.status&&!['a','unreported'].includes(p.status)?` 当前状态：${STATUS[p.status]||'待核实'}。`:''}</p>${p.news?`<p class="note">来源状态说明：${esc(p.news)}</p>`:''}<details><summary>分析依据与重要球员标记</summary><p class="note">重点标记：本队本赛季分钟前5、至少450分钟，且不少于队内最多分钟的65%。融入判断只描述出场使用情况；传球配合和更衣室关系没有数据时不推断。上方数值为本赛季，不冒充全部发生在加盟后。</p>${incoming?`<p>${sourceLink(incoming.source,'加盟记录来源')}</p>`:''}</details></section>`;
}
export function positionalGaps(team){
  const players=data.players.filter(p=>p.team===team.id),missing=players.filter(p=>importantPlayer(p)&&['i','s','d','u','n'].includes(p.status));
  const departures=(history?.transfers||[]).filter(t=>t.fromTeam===team.name&&t.date&&Date.parse(t.date)<=Date.now()&&Date.now()-Date.parse(t.date)<180*86400000);
  return `<section class="position-gaps"><div class="section-head"><h2>重要位置与人员变化</h2><a href="#/coaches">教练关注 →</a></div>${missing.length?missing.map(p=>`<p class="attention">${playerStar(p)} ${esc(POSITIONS[p.position])} · <a href="#/player/${p.id}">${esc(label(p))}</a>：${esc(STATUS[p.status])}。${esc(p.news||'原因待补充')}</p>`).join(''):'<p class="note">当前已收录名单中，没有符合重点标记规则的伤停球员；名单未披露的伤停仍待补充。</p>'}<details><summary>近半年离队与位置核对（${departures.length}条）</summary>${departures.map(t=>{const p=players.find(p=>[playerOriginal(p),p.web_name].map(normalized).includes(normalized(t.player)));return `<p>${p?playerStar(p):''}${esc(p?label(p):t.player)} · ${esc(p?POSITIONS[p.position]||'位置待核实':'位置待核实')} · ${dateText(t.date)} → ${esc(cn(t.toTeam))} ${sourceLink(t.source,'来源')}</p>`;}).join('')||'<p class="note">暂无已收录离队记录。</p>'}<p class="note">已离开当前名单、缺少此前分钟的球员，不凭转会费用自动判定重要程度。</p></details></section>`;
}
