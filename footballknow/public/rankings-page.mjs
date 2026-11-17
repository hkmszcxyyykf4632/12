import {data,standings,rankings,rankingsFailed,refresh} from './repository.mjs';
import {main,esc,pageHeading,monogram,sourceLink,toast} from './ui.mjs';
import {localized,timestamp} from './football-components.mjs';
import {league} from './league.mjs';
import {metricRows} from './rankings-core.mjs';
import {advancedControls,bindAdvanced,advancedHtml,advancedStatus,leagueRules} from './advanced-board.mjs';

const clubCell=r=>`<a class="club-inline" href="#/team/${r.teamId}">${monogram(r,'tiny')}<span>${esc(r.cn)}</span></a>`;
const formCell=r=>`<span class="form-run" aria-label="最近五场，最新在左">${(r.form||[]).map(v=>`<span class="result ${{W:'win',D:'draw',L:'loss'}[v]}">${{W:'胜',D:'平',L:'负'}[v]}</span>`).join('')}</span>`;
export function standingsPreview() {
 if(!standings)return '<div class="empty">积分榜正在同步。<a href="#/rankings">查看数据中心</a></div>';
 return `<div class="table-wrap"><table><thead><tr><th>排名</th><th>球队</th><th>场次</th><th>净胜球</th><th>积分</th><th>近五场</th></tr></thead><tbody>${standings.entries.slice(0,5).map(r=>`<tr><td>${r.rank}</td><td>${clubCell(r)}</td><td>${r.played}</td><td>${r.goalDifference>0?'+':''}${r.goalDifference}</td><td><strong>${r.points}</strong></td><td>${formCell(r)}</td></tr>`).join('')}</tbody></table></div>`;
}
export function renderRankings() {
 let board='table',scope='all',metric='scorers',teamMetric='goalsFor',search='';
 main.innerHTML=`${pageHeading(`${league.name} · 数据中心`,'积分走势、球员贡献与球队表现，一处查清。',`<span class="tag">${esc(data.season)}</span>`)}
 <div class="tabs board-tabs" role="group" aria-label="数据榜分类"><button data-board="table" class="active" aria-pressed="true">积分榜</button><button data-board="players" aria-pressed="false">球员榜</button><button data-board="advanced" aria-pressed="false">高阶球员榜</button><button data-board="clubs" aria-pressed="false">球队榜</button></div>
 <div class="toolbar rank-toolbar"><div id="rank-controls"></div><button class="button secondary compact" id="rank-refresh">检查更新</button></div><div id="rank-status" class="note" role="status"></div><div id="rank-content"></div>`;
 const controls=()=>{
  if(board==='advanced'){main.querySelector('#rank-controls').innerHTML=advancedControls();bindAdvanced(main,update);return;}
  main.querySelector('#rank-controls').innerHTML=board==='table'?`<label>统计范围 <select id="rank-scope">${Object.entries({all:'总榜',home:'主场',away:'客场',form:'近五场'}).map(([v,label])=>`<option value="${v}" ${v===scope?'selected':''}>${label}</option>`).join('')}</select></label>`:board==='players'?`<label>球员榜单 <select id="player-metric"><option value="scorers" ${metric==='scorers'?'selected':''}>射手榜</option><option value="assists" ${metric==='assists'?'selected':''}>助攻榜</option></select></label><label class="rank-search">搜索球员 / 球队 <input type="search" id="rank-search" value="${esc(search)}" placeholder="中文、粤语或原名"></label>`:`<label>球队指标 <select id="team-metric">${Object.entries({goalsFor:'进球数',goalsAgainst:'失球数（从少到多）',goalDifference:'净胜球',goalsPerGame:'场均进球',cleanSheets:'零封场次',yellowCards:'黄牌数',redCards:'红牌数'}).map(([v,label])=>`<option value="${v}" ${v===teamMetric?'selected':''}>${label}</option>`).join('')}</select></label>`;
  main.querySelector('#rank-scope')?.addEventListener('change',e=>{scope=e.target.value;update();});
  main.querySelector('#player-metric')?.addEventListener('change',e=>{metric=e.target.value;update();});
  main.querySelector('#team-metric')?.addEventListener('change',e=>{teamMetric=e.target.value;update();});
  main.querySelector('#rank-search')?.addEventListener('input',e=>{search=e.target.value;update();});
 };
 function update() {
  if(!main.querySelector('#rank-content'))return;
  if(board==='advanced'){main.querySelector('#rank-status').textContent=advancedStatus();main.querySelector('#rank-content').innerHTML=advancedHtml();return;}
  const snapshot=board==='players'||['yellowCards','redCards'].includes(teamMetric)&&board==='clubs'?rankings:standings;
  const age=Date.now()-Date.parse(snapshot?.updatedAt);
  main.querySelector('#rank-status').textContent=`${snapshot?`最近成功检查 ${timestamp(snapshot.updatedAt)}`:'尚未取得本赛季榜单'}${rankingsFailed?' · 最近检查未成功，保留已有资料':age>(snapshot?.intervalSeconds||60)*3000?' · 等待更新':''}。${board==='players'||board==='clubs'&&['yellowCards','redCards'].includes(teamMetric)?(snapshot?.providerCadence||'本站每 60 秒检查；来源更新后同步。'):'积分榜每 60 秒检查。'}`;
  let html='';
  if(board==='table'){
   const rows=scope==='all'?standings?.entries:standings?.breakdowns?.tables?.[scope];
   if(!rows)html=`<div class="empty">${standings?'主客场与近况正在核对全部赛果，请先查看总榜。':'积分榜暂未载入，请稍后检查更新。'}</div>`;
   else html=`<div class="table-wrap"><table class="standings-table"><caption class="sr-only">${league.name} ${data.season} 积分榜</caption><thead><tr><th>排名</th><th>球队</th><th>赛</th><th>胜</th><th>平</th><th>负</th><th>进球</th><th>失球</th><th>净胜</th><th>积分</th><th>近五场</th></tr></thead><tbody>${rows.map(r=>`<tr class="${league.id==='ucl'?'':'zone-'+esc(scope==='all'?r.zone:'')}"><td><span class="rank-number ${league.id==='ucl'&&scope==='all'?'rank-zone-'+esc(r.zone):''}" title="${esc(scope==='all'?r.zoneLabel||'':'')}">${r.rank}</span></td><td>${clubCell(r)}${r.pointsAdjustment?`<span class="small subtle">积分调整 ${r.pointsAdjustment>0?'+':''}${r.pointsAdjustment}</span>`:''}</td><td>${r.played}</td><td>${r.wins}</td><td>${r.draws}</td><td>${r.losses}</td><td>${r.goalsFor}</td><td>${r.goalsAgainst}</td><td>${r.goalDifference>0?'+':''}${r.goalDifference}</td><td class="points-cell">${r.points}</td><td>${formCell(r)}</td></tr>`).join('')}</tbody></table></div><p class="note">${scope==='all'?'总榜保留来源提供的排名顺序。标色表示当前排名区域，非提前确认最终名额。':'按已确认赛果计算，积分、净胜球、进球数依次排序；相同数据并列，不作为官方同分裁定。'}近五场从左到右由新到旧。</p>${scope==='all'?`<div class="rank-legend">${[...new Map(rows.filter(r=>r.zone).map(r=>[r.zone,r.zoneLabel])).entries()].map(([zone,label])=>`<span class="zone-key ${esc(zone)}">${esc(label)}</span>`).join('')}</div>`:''}<p class="note">${sourceLink(standings.source,'ESPN 数据')} · ${sourceLink(standings.officialUrl,`${league.name}官网积分榜`)}</p>`;
  }else if(board==='players'){
   const rows=(rankings?.boards?.[metric]||[]).map(r=>{const n=r.playerCode?localized({code:r.playerCode}):null;return {...r,translation:n?{...n,provisional:n.status==='draft'}:null};}).filter(r=>[r.name,r.teamName,r.translation?.mandarin,r.translation?.cantonese].join(' ').toLowerCase().includes(search.trim().toLowerCase()));
   html=rows.length?`<div class="table-wrap"><table><thead><tr><th>排名</th><th>球员 · 普通话 / 粤语</th><th>球队</th><th>出场</th><th>${metric==='scorers'?'进球':'助攻'}</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.rank}</td><td><strong>${esc(r.translation?.mandarin||r.name)}</strong>${r.translation?`<div class="small">粤 ${esc(r.translation.cantonese)}${r.translation.provisional?' · 暂译':''}</div>`:''}<div class="small subtle">${sourceLink(r.source,r.name)}</div></td><td><a href="#/team/${r.teamId}">${esc(r.teamName)}</a></td><td>${r.appearances}</td><td class="points-cell">${r.value}</td></tr>`).join('')}</tbody></table></div>`:`<div class="empty">${rankings?'没有符合搜索条件的球员。':'球员榜正在同步。'}</div>`;
   html+=`<p class="note">${rankings?.coverage?esc(rankings.providerCadence)+'。本站收录前 ':'来源收录前 '}${rankings?.limit||50} 名；数值相同按并列名次显示。统计为 ${esc(data.season)} ${league.name}，中文译名未核对时保留原名。${sourceLink(rankings?.sources?.[0],'查看榜单来源')}</p>`;
  }else{
   const rows=metricRows(standings,rankings,teamMetric);
   const label={goalsFor:'进球',goalsAgainst:'失球',goalDifference:'净胜球',goalsPerGame:'场均进球',cleanSheets:'零封',yellowCards:'黄牌',redCards:'红牌'}[teamMetric];
   html=rows.length?`<div class="table-wrap"><table><thead><tr><th>排名</th><th>球队</th><th>场次</th><th>${label}</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.rank}</td><td>${clubCell(r)}</td><td>${r.played}</td><td class="points-cell">${teamMetric==='goalsPerGame'?r.value.toFixed(2):r.value}</td></tr>`).join('')}</tbody></table></div><p class="note">按所选指标排序，相同数值并列；场均进球按各队已赛场次计算。零封仅显示赛果已完整核对的球队。${sourceLink(['yellowCards','redCards'].includes(teamMetric)?rankings?.sources?.[1]:standings?.source,'统计来源')}</p>`:'<div class="empty">这项统计尚未完整核对，请切换其他指标。</div>';
  }
  main.querySelector('#rank-content').innerHTML=html+(board==='table'?leagueRules():'');
 }
 main.querySelectorAll('[data-board]').forEach(b=>b.addEventListener('click',()=>{board=b.dataset.board;main.querySelectorAll('[data-board]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});controls();update();}));
 main.querySelector('#rank-refresh').addEventListener('click',async e=>{const b=e.currentTarget;b.disabled=true;b.textContent='正在检查…';try{await refresh(true);update();}catch{toast('暂时无法更新，请稍后重试。');}finally{b.disabled=false;b.textContent='检查更新';}});
 controls();update();return update;
}
