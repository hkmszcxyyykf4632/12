import {main,esc,pageHeading} from './ui.mjs';
import {BET_NAMES,STORAGE_KEY,dealShoe,amountCents,settleRound,ledgerTotals,cardLabel,validRates} from './baccarat-core.mjs';
import {bigRoad,derivedRoad,roadProbe} from './baccarat-roads.mjs';
import {STUDY_METHODS,newStudySession,restoreStudySession,studyEntry,recordStudyBet,priorContext,outcomeExplanation,studyRounds} from './baccarat-study.mjs';
const money=n=>(n/100).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2});
const profitText=n=>(n>0?'+':'')+money(n);
const profitClass=n=>n>0?'bac-profit':n<0?'bac-loss':'bac-neutral';
const ROAD_NAMES=['大眼仔','小路','曱甴路'];
const ARCHIVE_KEY=STORAGE_KEY+'.archive';
const RULE_SOURCE='https://www.alc.ca/content/dam/alc/images/casino/live-baccarat/How%20to%20Play%20-%20Live%20Baccarat%20-%20EN.pdf';
const statusLabel={win:'赢',loss:'输',push:'退回本金'};
function roadGrid(cells,type,small=false,selected=0){
 const columns=Math.max(small?16:24,...cells.map(c=>c.col+1));
 return `<div class="bac-road-scroll"><div class="bac-road-grid ${small?'bac-road-small':''} road-${type}" style="--columns:${columns}" role="img" aria-label="${esc(type)}，${cells.length} 个标记">${cells.map(c=>`<span class="bac-road-cell ${c.hand===selected?'is-selected':''}" style="grid-column:${c.col+1};grid-row:${c.row+1}" title="第 ${c.hand} 口${c.ties?'，和 '+c.ties+' 次':''}"><i class="bac-mark ${c.color}">${type==='珠盘'?BET_NAMES[c.result]:''}</i>${c.ties?`<b class="bac-tie-count">${c.ties}</b>`:''}${c.bankerPair?'<i class="bac-pair banker"></i>':''}${c.playerPair?'<i class="bac-pair player"></i>':''}${c.lucky6||c.lucky7?`<em class="bac-lucky">${c.lucky6?'6':'7'}</em>`:''}</span>`).join('')}</div></div>`;
}
function lowerRoads(hands){return ROAD_NAMES.map((name,i)=>`<div class="bac-lower"><h3>${name}</h3>${roadGrid(derivedRoad(hands,i+1),name,true)}</div>`).join('');}
function probeHtml(hands){return `<div class="bac-probe"><div><span>这一口问路</span>${ROAD_NAMES.map(n=>'<small>'+n+'</small>').join('')}</div>${['B','P'].map(side=>`<div><strong>若开${BET_NAMES[side]}</strong>${roadProbe(hands,side).map((color,i)=>`<span class="road-${ROAD_NAMES[i]}"><i class="bac-mark ${color||'unstarted'}" aria-label="${color==='red'?'红':color==='blue'?'蓝':'尚未起路'}"></i></span>`).join('')}</div>`).join('')}</div>`;}
function cardsHtml(h){return `<div class="bac-cards">${[['P','playerCards','player'],['B','bankerCards','banker']].map(([side,cards,total])=>`<div><strong>${BET_NAMES[side]} ${h[total]} 点</strong><span>${h[cards].map(c=>`<i class="playing-card ${[1,3].includes(Math.floor(c/13)%4)?'card-red':''}">${cardLabel(c)}</i>`).join('')}</span></div>`).join('')}<b class="bac-result result-${h.result}">第 ${h.number} 口 · ${BET_NAMES[h.result]}${h.result==='T'?'局':'赢'}</b></div>`;}
function fullShoeHtml(hands,selected,rounds){
 const outcomes=new Map(rounds.map(r=>[r.number,r])),road=bigRoad(hands);
 return `<section class="bac-board bac-overview"><div class="section-head"><h2>整靴 ${hands.length} 口 · 已全部开出</h2><span>点选任意一口研究</span></div><p class="note">按口数从左到右、从上到下排列。绿色盈、红色亏；下注标记显示该口的模拟结果。</p><div class="bac-order" aria-label="整靴结果顺序">${hands.map(h=>{const r=outcomes.get(h.number);return `<button class="bac-order-hand result-${h.result} ${selected===h.number?'is-selected':''}" data-hand="${h.number}" aria-label="第 ${h.number} 口，${BET_NAMES[h.result]}${h.result==='T'?'局':'赢'}${r?'，已模拟投注':''}" aria-pressed="${selected===h.number}"><small>${h.number}</small><strong>${BET_NAMES[h.result]}</strong><span class="bac-order-flags">${[h.bankerPair?'庄对':'',h.playerPair?'闲对':'',h.lucky6?'6':'',h.lucky7?'7':''].filter(Boolean).join(' ')||'·'}</span>${r?`<em class="${profitClass(r.profit)}">${profitText(r.profit)}</em>`:''}</button>`;}).join('')}</div><details class="bac-full-roads"><summary>整靴大路、珠盘路和下三路</summary><h3>大路</h3>${roadGrid(road.cells,'大路',false,selected)}<h3>珠盘路 · 每列从上到下</h3>${roadGrid(hands.map((h,i)=>({...h,hand:h.number,row:i%6,col:Math.floor(i/6),color:h.result==='B'?'red':h.result==='P'?'blue':'green'})),'珠盘',false,selected)}<div class="bac-lower-grid">${lowerRoads(hands)}</div></details><p class="bac-legend"><span class="result-B">庄红</span><span class="result-P">闲蓝</span><span class="result-T">和绿</span><span>6：幸运6</span><span>7：幸运7</span></p></section>`;
}
function ticketHtml(session,hands,entry){
 const n=session.study.selected,round=entry?.bets.length?settleRound(hands[n-1],entry.bets,entry.rates):null;
 return `<div class="bac-ticket"><span class="eyebrow">整靴已可见 · 回看模拟</span><h2>第 ${n} 口 · 选择买入</h2><div class="bac-hand-nav"><button class="button secondary" data-step="-1" ${n===1?'disabled':''}>上一口</button><label>研究口数<select id="bac-hand-select">${hands.map(h=>`<option value="${h.number}" ${n===h.number?'selected':''}>第 ${h.number} 口 · ${BET_NAMES[h.result]}</option>`).join('')}</select></label><button class="button secondary" data-step="1" ${n===hands.length?'disabled':''}>下一口</button></div><div class="bac-notes"><label>判断方法<select id="bac-method">${STUDY_METHODS.map(m=>`<option ${entry?.method===m?'selected':''}>${m}</option>`).join('')}</select></label><label>为什么在这一口买入？<textarea id="bac-reason" maxlength="2000" rows="2" placeholder="记录当时看重的路形或条件">${esc(entry?.reason||'')}</textarea></label></div><form id="bac-bet-form"><label>选择项目<select id="bac-type">${Object.entries(BET_NAMES).map(([k,n])=>`<option value="${k}">${n}</option>`).join('')}</select></label><label>金额<input id="bac-amount" type="text" inputmode="decimal" required></label><div class="bac-chips">${[10,50,100,500,1000].map(n=>`<button type="button" data-chip="${n}">${n}</button>`).join('')}</div><button class="button bac-deal">记录模拟投注并结算</button></form><div class="bac-pending">${round?round.tickets.map(b=>`<div><strong>${BET_NAMES[b.type]}</strong><span class="${profitClass(b.profit)}">${money(b.stake)} · ${statusLabel[b.status]} ${profitText(b.profit)}</span><button class="button quiet compact" data-remove="${b.type}" aria-label="移除${BET_NAMES[b.type]}模拟投注">移除</button></div>`).join(''):'<p class="note">可同时模拟多个项目，同项再次记录会累加金额。</p>'}</div><p id="bac-last" role="status" class="${profitClass(round?.profit||0)}">${round?'本口净盈亏 '+profitText(round.profit):'本口尚未模拟投注'}</p><p class="note">这是看完排列后的研究记录；统计与此前逐口练习分开保存。</p></div>`;
}
function reviewHtml(hand,context,entry){
 const round=entry?.bets.length?settleRound(hand,entry.bets,entry.rates):null;
 return `<section class="bac-review"><h2>第 ${hand.number} 口 · 对照复盘</h2><div class="bac-review-grid"><div><h3>买入前能看到什么</h3><p>${esc(context.streak)}。</p><p>${context.recent.length?`此前最近 ${context.recent.length} 口：庄 ${context.counts.B}、闲 ${context.counts.P}、和 ${context.counts.T}。`:'这是开靴第一口，没有前序路形。'}</p><h3>实际发生什么</h3><p>${esc(context.change)}。${hand.natural?'首两张出现 8 或 9 点例牌，双方不再补牌。':`闲家 ${hand.playerCards.length===3?'补一张牌':'不补牌'}，庄家 ${hand.bankerCards.length===3?'补一张牌':'不补牌'}，按补牌规则形成最终点数。`}</p>${round?`<ul class="bac-explanations">${round.tickets.map(t=>`<li><strong class="${profitClass(t.profit)}">${BET_NAMES[t.type]} · ${statusLabel[t.status]} · ${profitText(t.profit)}</strong><p>${esc(outcomeExplanation(hand,t))}净赔率 ${t.rate}:1，返还 ${money(t.returned)}（含本金）。</p></li>`).join('')}</ul>`:'<p class="note">记录模拟投注后，这里逐项说明赢、输或退回本金的结算原因。</p>'}</div><div><label>复盘备注<textarea id="bac-review-note" rows="7" maxlength="2000" placeholder="对照买入理由：什么判断成立了？漏看了什么？下次用什么条件验证？">${esc(entry?.review||'')}</textarea></label><p class="note">路形延续或转向描述的是结果，不能单凭一口输赢认定判断方法有效。下方按相同方法汇总，方便比较。</p></div></div></section>`;
}
function statisticsHtml(rounds,hands,totals){
 return `<section class="bac-statistics"><div class="section-head"><h2>本靴回看模拟统计</h2><span>${totals.rounds} 口有投注 · ${totals.tickets} 项</span></div><div class="bac-scoreboard"><div><small>总投入</small><strong>${money(totals.stake)}</strong></div><div><small>总返还（含本金）</small><strong>${money(totals.returned)}</strong></div><div class="${profitClass(totals.profit)}"><small>净盈亏</small><strong>${profitText(totals.profit)}</strong></div><div><small>赢 / 输 / 退回 · 按投注项</small><strong>${totals.wins} / ${totals.losses} / ${totals.pushes}</strong></div></div><details open><summary>按买入理由比较</summary><div class="table-wrap"><table><thead><tr><th>方法</th><th>模拟口数</th><th>盈利 / 亏损 / 持平</th><th>总投入</th><th>净盈亏</th></tr></thead><tbody>${STUDY_METHODS.map(m=>{const group=rounds.filter(r=>r.entry.method===m);if(!group.length)return '';const t=ledgerTotals(group);return `<tr><th>${m}</th><td>${group.length}</td><td>${group.filter(r=>r.profit>0).length} / ${group.filter(r=>r.profit<0).length} / ${group.filter(r=>r.profit===0).length}</td><td>${money(t.stake)}</td><td class="${profitClass(t.profit)}">${profitText(t.profit)}</td></tr>`;}).join('')||'<tr><td colspan="5">选择口数并记录模拟投注后汇总。</td></tr>'}</tbody></table></div></details><details><summary>每笔投注、买入理由与复盘</summary><div class="table-wrap"><table><thead><tr><th>口数 / 结果</th><th>项目 / 金额 / 净赔率</th><th>买入理由</th><th>复盘备注</th><th>返还 / 净盈亏</th></tr></thead><tbody>${rounds.map(r=>`<tr><th><button class="button quiet compact" data-hand="${r.number}">第 ${r.number} 口 · ${BET_NAMES[hands[r.number-1].result]}</button></th><td>${r.tickets.map(t=>`<span class="bac-bet-result ${profitClass(t.profit)}">${BET_NAMES[t.type]} ${money(t.stake)} · ${t.rate}:1 · ${statusLabel[t.status]}</span>`).join('')}</td><td>${esc(r.entry.method)}<small>${esc(r.entry.reason||'未记录')}</small></td><td class="bac-saved-note">${esc(r.entry.review||'未记录')}</td><td>${money(r.returned)}<br><strong class="${profitClass(r.profit)}">${profitText(r.profit)}</strong></td></tr>`).join('')||'<tr><td colspan="5">暂无模拟投注。</td></tr>'}</tbody></table></div></details></section>`;
}
function legacyHtml(session,hands){
 if(!session.rounds.some(r=>r.bets.length)&&!session.pending.length)return '';
 const rounds=session.rounds.map((r,i)=>settleRound(hands[i],r.bets,r.rates)),totals=ledgerTotals(rounds);
 return `<details class="bac-legacy"><summary>此前逐口练习记录（保留原数据）</summary><p>${totals.rounds} 口有投注，投入 ${money(totals.stake)}，净盈亏 <span class="${profitClass(totals.profit)}">${profitText(totals.profit)}</span>。与本次看完整靴后的模拟分开统计。</p>${rounds.filter(r=>r.tickets.length).map(r=>`<p>第 ${r.number} 口：${r.tickets.map(t=>`${BET_NAMES[t.type]} ${money(t.stake)} / ${statusLabel[t.status]} / ${profitText(t.profit)}`).join('；')}</p>`).join('')}${session.pending.length?`<p>旧版尚未开牌的待投注：${session.pending.map(b=>BET_NAMES[b.type]+' '+money(b.stake)).join('；')}，未纳入已结算金额。</p>`:''}</details>`;
}
function rulesHtml(rates,open){return `<details id="bac-rules" ${open?'open':''}><summary>模拟规则与净赔率设置</summary><p>每靴 8 副共 416 张牌，随机洗牌后连续发牌，不放回；不烧牌、不设截牌。一次展示 70 口，若整靴纸牌不足 70 口则重新洗整靴。</p><p>8、9 点例牌停止补牌，其余按<a href="${RULE_SOURCE}" target="_blank" rel="noopener noreferrer">庄闲补牌表</a>发牌。对子按首两张牌的牌面相同判定。幸运 6＝庄家以 6 点胜；幸运 7＝闲家三张牌合计 7 点胜。</p><p>以下为可调整的模拟净赔率。赢时返还本金加盈利；默认庄赢扣 5% 佣金，庄闲遇和退回本金，附加项独立结算，金额四舍五入至分。同一口保留首次记录投注时的赔率。</p><form id="bac-rates" class="bac-rates">${Object.entries(rates).map(([k,v])=>`<label>${({L6two:'幸运6（两张）',L6three:'幸运6（三张）'})[k]||BET_NAMES[k]}<input name="${k}" type="number" min="0" max="1000" step="0.01" value="${v}" required></label>`).join('')}<button class="button secondary">保存后续新记录赔率</button><span id="bac-rate-message" role="status"></span></form><p class="note">虚拟金额研究，资料保存在本浏览器，保留最近 20 靴。已看完整结果后的模拟不能作为事前预测命中率；下三路不代表下一口的胜率。</p></details>`;}
export function renderBaccarat(){
 let session,notice='',amount='100',type='B',ended=false,rateOpen=false,fullRoadsOpen=true,archives=[],fresh=false;
 try{const raw=localStorage.getItem(STORAGE_KEY);fresh=!raw;session=raw?restoreStudySession(raw):newStudySession();}catch{session=newStudySession();notice='之前的本机记录未能读取；当前新靴暂未保存。';}
 try{const raw=JSON.parse(localStorage.getItem(ARCHIVE_KEY)||'[]');if(!Array.isArray(raw))throw Error();archives=raw.slice(-20).map(s=>restoreStudySession(JSON.stringify(s)));}catch{notice='历史靴记录未能读取，当前靴仍可研究。';}
 let hands=dealShoe(session.deck);
 function save(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(session));return true;}catch{notice='本机空间或权限不足，本次仅在当前页面保留。';return false;}}
 function archive(){
  const next=[...archives.filter(s=>s.id!==session.id),JSON.parse(JSON.stringify(session))].slice(-20);
  try{localStorage.setItem(ARCHIVE_KEY,JSON.stringify(next));archives=next;return true;}catch{notice='上一靴暂时无法保存，已保留当前靴；清理浏览器空间后再试。';return false;}
 }
 function choose(number,scroll=false){session.study.selected=Math.max(1,Math.min(hands.length,number));save();paint();if(scroll)main.querySelector('.bac-console').scrollIntoView?.({block:'start',behavior:'smooth'});}
 function paint(){
  if(ended)return;
  const n=session.study.selected,hand=hands[n-1],entry=session.study.entries.find(e=>e.hand===n),rounds=studyRounds(session,hands),totals=ledgerTotals(rounds),context=priorContext(hands,n),counts={B:0,P:0,T:0};
  hands.forEach(h=>counts[h.result]++);
  main.innerHTML=pageHeading('百家乐 · 70 口路单研究','洗牌即开整靴 · 自选买入位置 · 对照盈亏与判断理由','<button class="button secondary" data-bac="new">重新洗牌 · 开出70口</button>')+
  `<p id="bac-notice" class="note" role="status">${esc(notice)}</p><div class="bac-scoreboard"><div><small>本靴已开</small><strong>${hands.length} <small>/ ${hands.length}</small></strong></div>${['B','P','T'].map(k=>`<div class="result-${k}"><small>${BET_NAMES[k]}</small><strong>${counts[k]}</strong></div>`).join('')}<div><small>模拟投入</small><strong>${money(totals.stake)}</strong></div><div class="${profitClass(totals.profit)}"><small>模拟净盈亏</small><strong>${profitText(totals.profit)}</strong></div></div>`+
  fullShoeHtml(hands,n,rounds)+`<section class="bac-console" aria-label="所选口投注与下三路">${ticketHtml(session,hands,entry)}<div class="bac-current-roads"><h2>第 ${n} 口买入前 · 下三路</h2><p class="note">${n===1?'开靴第一口，尚无前序路形。':`只用第 1 至 ${n-1} 口生成，不含所选口及其后结果。`}</p>${probeHtml(context.prior)}<div class="bac-lower-grid">${lowerRoads(context.prior)}</div><details><summary>查看买入前大路</summary>${roadGrid(bigRoad(context.prior).cells,'大路')}</details></div></section>`+
  cardsHtml(hand)+reviewHtml(hand,context,entry)+statisticsHtml(rounds,hands,totals)+legacyHtml(session,hands)+
  `<details class="bac-archives"><summary>历史靴研究（${archives.filter(s=>s.id!==session.id).length} 靴）</summary><div class="bac-archive-list">${archives.filter(s=>s.id!==session.id).reverse().map(s=>{const t=ledgerTotals(studyRounds(s,dealShoe(s.deck)));return `<button class="button secondary" data-shoe="${esc(s.id)}">${esc(new Date(s.createdAt).toLocaleString('zh-CN'))} · ${t.rounds} 口模拟 · ${profitText(t.profit)}</button>`;}).join('')||'<p class="note">重新洗牌时自动保存上一靴，可回来看排列和研究记录。</p>'}</div></details>`+rulesHtml(session.rates,rateOpen);
  main.querySelector('.bac-full-roads').open=fullRoadsOpen;
  main.querySelector('#bac-amount').value=amount;main.querySelector('#bac-type').value=type;
  main.querySelectorAll('.bac-current-roads .bac-road-scroll').forEach(scroll=>{
   if(!scroll.clientWidth)return;
   const lastColumn=Math.max(0,...[...scroll.querySelectorAll('.bac-road-cell')].map(c=>Number(c.style.gridColumn)));
   const width=parseFloat(getComputedStyle(scroll.firstElementChild).getPropertyValue('--cell'))||15;
   scroll.scrollLeft=Math.max(0,lastColumn*width-scroll.clientWidth);
  });
  bind();
 }
 function bind(){
  main.querySelectorAll('[data-hand]').forEach(b=>b.onclick=()=>choose(Number(b.dataset.hand),true));
  main.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>choose(session.study.selected+Number(b.dataset.step)));
  main.querySelector('#bac-hand-select').onchange=e=>choose(Number(e.target.value));
  main.querySelector('#bac-amount').oninput=e=>amount=e.target.value;
  main.querySelector('#bac-type').onchange=e=>type=e.target.value;
  main.querySelectorAll('[data-chip]').forEach(b=>b.onclick=()=>{amount=b.dataset.chip;main.querySelector('#bac-amount').value=amount;});
  for(const [selector,key] of [['#bac-method','method'],['#bac-reason','reason'],['#bac-review-note','review']]){
   const input=main.querySelector(selector);
   const update=()=>{studyEntry(session,session.study.selected)[key]=input.value.slice(0,2000);if(!save())main.querySelector('#bac-notice').textContent=notice;};
   input.oninput=update;input.onchange=()=>{update();if(key==='method')paint();};
  }
  main.querySelector('#bac-bet-form').onsubmit=e=>{e.preventDefault();try{recordStudyBet(session,session.study.selected,{type,stake:amountCents(amount)});notice='第 '+session.study.selected+' 口模拟投注已记录，盈亏和复盘已更新。';save();paint();}catch(err){main.querySelector('#bac-notice').textContent=err.message;}};
  main.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>{const e=studyEntry(session,session.study.selected);e.bets=e.bets.filter(t=>t.type!==b.dataset.remove);notice='已移除此项模拟投注，统计已重新计算。';save();paint();});
  main.querySelector('[data-bac="new"]').onclick=()=>{if(!archive()){main.querySelector('#bac-notice').textContent=notice;return;}session=newStudySession();hands=dealShoe(session.deck);notice='已重新洗牌并开出全部 70 口，上一靴已保存到历史靴研究。';save();paint();};
  main.querySelectorAll('[data-shoe]').forEach(b=>b.onclick=()=>{const previous=archives.find(s=>s.id===b.dataset.shoe);if(!previous||!archive()){main.querySelector('#bac-notice').textContent=notice;return;}session=restoreStudySession(JSON.stringify(previous));hands=dealShoe(session.deck);notice='已打开历史靴，排列及研究记录保持原样。';save();paint();});
  main.querySelector('#bac-rules').ontoggle=e=>rateOpen=e.target.open;
  main.querySelector('.bac-full-roads').ontoggle=e=>fullRoadsOpen=e.target.open;
  main.querySelector('#bac-rates').onsubmit=e=>{e.preventDefault();const next=Object.fromEntries([...new FormData(e.target)].map(([k,v])=>[k,v.trim()===''?NaN:Number(v)]));if(!validRates(next)){main.querySelector('#bac-rate-message').textContent='请输入 0 至 1,000 的净赔率。';return;}session.rates=next;notice='新赔率用于尚未记录投注的口数，已有记录保持原赔率。';save();paint();};
 }
 const storage=e=>{if(e.key!==STORAGE_KEY||!e.newValue)return;try{session=restoreStudySession(e.newValue);hands=dealShoe(session.deck);notice='已读取另一页面保存的研究记录。';paint();}catch{}};
 window.addEventListener('storage',storage);if(fresh)save();paint();return()=>{ended=true;window.removeEventListener('storage',storage);};
}
