import {filterVenue,matchSettlement,quotesForMatch,regulationScore,SETTLEMENT_NAMES} from './settlement.mjs';
import {PHASE_NAMES} from './markets-core.mjs';

const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function handicapSeries(matches,teamName,snapshot,{venue='all',season=null,competition=null,limit=20}={}){
  const seen=new Set();
  let rows=filterVenue(matches,teamName,venue).filter(m=>regulationScore(m)&&(!season||m.season===season)&&(!competition||m.competition===competition)).sort((a,b)=>(a.kickoff||a.date).localeCompare(b.kickoff||b.date)||a.id.localeCompare(b.id));
  rows=rows.filter(m=>{if(seen.has(m.id))return false;seen.add(m.id);return true;});
  if(limit)rows=rows.slice(-limit);
  return rows.map(match=>{const home=match.home===teamName,settled=matchSettlement(match,teamName,quotesForMatch(snapshot,match)).handicap;return {match,venue:home?'home':'away',opponent:home?match.away:match.home,result:settled?.result??null,line:settled?.line??null,quote:settled?.quote??null};});
}
export function bindHandicapTrend(target,getContext,cn=x=>x){
  let venue='all',range='recent';
  target.innerHTML='<div class="section-head"><h2>亚洲盘主客场走势</h2><div class="segmented"><button data-ah-venue="all" class="active">全部</button><button data-ah-venue="home">主场</button><button data-ah-venue="away">客场</button></div></div><div class="toolbar"><label>比赛范围 <select data-ah-range><option value="recent">最近 20 场已完赛</option><option value="season">本赛季</option></select></label><span class="small subtle">按比赛时间从左至右 · 以本队为准</span></div><div data-ah-chart></div>';
  function paint(){
    if(!target.isConnected)return;
    const {matches,teamName,snapshot,season,competition}=getContext();
    const rows=handicapSeries(matches,teamName,snapshot,{venue,season:range==='season'?season:null,competition,limit:range==='recent'?20:null}),known=rows.filter(r=>r.result!==null);
    const area=target.querySelector('[data-ah-chart]');
    if(!known.length){area.innerHTML=`<div class="empty">此范围有 ${rows.length} 场已完赛比赛，暂未收录可核对的亚洲让球盘口。</div>`;return;}
    const x=i=>60+(rows.length===1?420:i*840/(rows.length-1)),y=v=>132-v*84;
    let segments=[],part=[];for(let i=0;i<rows.length;i++){if(rows[i].result===null){if(part.length)segments.push(part);part=[];}else part.push(`${x(i)},${y(rows[i].result)}`);}if(part.length)segments.push(part);
    const counts=[1,.5,0,-.5,-1].map(v=>known.filter(r=>r.result===v).length);
    area.innerHTML=`<dl class="stat-grid"><div><dt>有盘口 / 已完赛</dt><dd>${known.length} / ${rows.length}</dd></div><div><dt>赢盘 / 赢半 / 走盘 / 输半 / 输盘</dt><dd>${counts.join(' / ')}</dd></div></dl><figure class="handicap-chart"><svg viewBox="0 0 960 270" role="img" aria-label="球队亚洲盘逐场走势，横轴按比赛日期，纵轴为赢盘至输盘">${[1,.5,0,-.5,-1].map(v=>`<line x1="60" y1="${y(v)}" x2="920" y2="${y(v)}" class="ah-grid"/><text x="48" y="${y(v)+4}" text-anchor="end">${SETTLEMENT_NAMES[v]}</text>`).join('')}${segments.map(points=>`<polyline points="${points.join(' ')}" class="ah-path"/>`).join('')}${rows.map((r,i)=>r.result===null?`<text x="${x(i)}" y="252" text-anchor="middle">缺</text>`:`<circle tabindex="0" role="button" data-ah-point="${i}" aria-label="${esc(r.match.date+' '+(r.venue==='home'?'主场':'客场')+' 对 '+cn(r.opponent)+' '+SETTLEMENT_NAMES[r.result])}" cx="${x(i)}" cy="${y(r.result)}" r="6" class="ah-point ${r.result>0?'ah-win':r.result<0?'ah-loss':'ah-push'}"><title>${esc(r.match.date+' '+cn(r.opponent)+' '+SETTLEMENT_NAMES[r.result])}</title></circle>`).join('')}<text x="60" y="266">${esc(rows[0].match.date)}</text><text x="920" y="266" text-anchor="end">${esc(rows.at(-1).match.date)}</text></svg><figcaption>赢盘、赢半、走盘、输半、输盘为逐场结算结果，折线不代表盈利。缺少盘口处断开；点击圆点查看本场资料。</figcaption></figure><div data-ah-detail class="research-summary"></div><details><summary>展开全部盘路记录</summary><div class="table-wrap"><table><thead><tr><th>日期</th><th>主客 / 对手</th><th>比分（主 : 客）</th><th>本队盘口</th><th>盘路</th><th>采用报价</th></tr></thead><tbody>${rows.map(r=>`<tr><td><a href="#/match/${encodeURIComponent(r.match.id)}">${esc(r.match.date)}</a></td><td>${r.venue==='home'?'主场':'客场'} · ${esc(cn(r.opponent))}</td><td>${r.match.homeGoals} : ${r.match.awayGoals}</td><td>${r.line===null?'—':(r.line>0?'+':'')+r.line}</td><td>${r.result===null?'缺少盘口':SETTLEMENT_NAMES[r.result]}</td><td>${r.quote?esc(r.quote.provider+' · '+PHASE_NAMES[r.quote.phase]):'—'}</td></tr>`).join('')}</tbody></table></div></details><p class="note">优先使用最后盘口，缺少时采用标明的早期或开始盘口；排除即场与手工盘口。主队让球转为客队视角时反转正负，四分之一盘按两半结算。仅用 90 分钟含补时比分。</p>`;
    function detail(i){const r=rows[i];if(!r?.quote)return;let source='';try{const u=new URL(r.quote.source||r.quote.sourceUrl);if(u.protocol==='https:')source=` · <a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">赔率来源 ↗</a>`;}catch{}area.querySelector('[data-ah-detail]').innerHTML=`<strong>${esc(r.match.date)} · ${r.venue==='home'?'主场':'客场'}对 ${esc(cn(r.opponent))} · ${SETTLEMENT_NAMES[r.result]}</strong><p>比分 ${r.match.homeGoals} : ${r.match.awayGoals}（主 : 客） · 本队盘口 ${r.line>0?'+':''}${r.line} · ${esc(r.quote.provider)} / ${esc(PHASE_NAMES[r.quote.phase])} · 本队十进制赔率 ${r.quote.prices[r.venue==='home'?'H':'A']}</p><a href="#/match/${encodeURIComponent(r.match.id)}">查看比赛详情 →</a>${source}`;}
    area.querySelectorAll('[data-ah-point]').forEach(el=>{el.addEventListener('click',()=>detail(Number(el.dataset.ahPoint)));el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();detail(Number(el.dataset.ahPoint));}});});
    detail(rows.findLastIndex(r=>r.quote));
  }
  target.querySelectorAll('[data-ah-venue]').forEach(b=>b.addEventListener('click',()=>{venue=b.dataset.ahVenue;target.querySelectorAll('[data-ah-venue]').forEach(x=>x.classList.toggle('active',x===b));paint();}));
  target.querySelector('[data-ah-range]').addEventListener('change',e=>{range=e.target.value;paint();});paint();return paint;
}
