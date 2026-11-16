import {INITIAL_BALANCE,OUTCOMES,validDate,moneyInput,decimalOdds,payout,summary,validateStore} from './core.mjs';
import {data,findMatch} from './repository.mjs';
import {store,STORAGE_KEY,commit,latestStore} from './personal-store.mjs';
import {main,esc,amount,oddsText,dateText,cn,pageHeading,toast} from './ui.mjs';
let draft=null;
function draftFromMatch(m, selection = 'H') {
  const odds = m.odds?.[0];
  return { matchId: m.id, home: m.home, away: m.away, date: m.date, result: m.result, selection,
    H: odds?.H ?? '', D: odds?.D ?? '', A: odds?.A ?? '', source: odds ? `Football-Data / ${odds.label}` : '手动录入' };
}
export function renderSimulator() {
  const bank = summary(store.bets);
  const d = draft || { home:'', away:'', date: new Date().toLocaleDateString('en-CA'), source:'手动录入', selection:'H' };
  const upcoming = data.matches.filter(m => !m.finished && !m.started && validDate(m.date)).sort((a,b) => a.date.localeCompare(b.date)).slice(0, 30);
  const past = data.matches.filter(m => m.finished).slice(0, 180);
  if (d.matchId && ![...upcoming,...past].some(m => m.id === d.matchId)) {
    const selected = data.matches.find(m => m.id === d.matchId); if (selected) past.unshift(selected);
  }
  const matchOptions = rows => rows.map(m=>`<option value="match:${esc(m.id)}" ${!d.savedId && d.matchId===m.id?'selected':''}>${dateText(m.date)} · ${esc(cn(m.home))} vs ${esc(cn(m.away))}${m.finished?'（已完赛）':''}</option>`).join('');
  main.innerHTML = `${pageHeading('把判断，放进一次模拟。', '先选比赛并记录赔率，再用虚拟资金检验你的想法。', '<a class="button secondary" href="#/records">查看我的记录</a>')}
    <div class="sim-layout"><section class="panel"><h2>${d.savedId ? '编辑已保存的赔率' : '比赛与赔率'}</h2>
    <form id="bet-form"><div class="field"><label for="match-picker">选择比赛</label><select id="match-picker"><option value="custom" ${!d.matchId&&!d.savedId?'selected':''}>自行输入一场比赛</option>${store.odds.length?`<optgroup label="我保存的赔率">${store.odds.map(o=>`<option value="saved:${esc(o.id)}" ${d.savedId===o.id?'selected':''}>${dateText(o.date)} · ${esc(cn(o.home))} vs ${esc(cn(o.away))} · ${esc(o.source)}</option>`).join('')}</optgroup>`:''}<optgroup label="即将进行 · 赔率需手动输入">${matchOptions(upcoming)}</optgroup><optgroup label="已完成 · 历史回测">${matchOptions(past)}</optgroup></select></div>
    <div class="field-row"><div class="field"><label for="home">主队</label><input id="home" name="home" maxlength="80" required value="${esc(d.home)}" ${d.matchId?'readonly':''} placeholder="例如：阿森纳"></div><div class="field"><label for="away">客队</label><input id="away" name="away" maxlength="80" required value="${esc(d.away)}" ${d.matchId?'readonly':''} placeholder="例如：切尔西"></div></div>
    <div class="field-row"><div class="field"><label for="match-date">比赛日期</label><input id="match-date" name="date" type="date" required value="${esc(d.date)}" ${d.matchId?'readonly':''}></div><div class="field"><label for="odds-source">赔率来源 / 备注</label><input id="odds-source" name="source" maxlength="150" required value="${esc(d.source)}" placeholder="例如：我记录的赛前赔率"></div></div>
    <div class="odds-fields">${['H','D','A'].map(k=>`<div class="field"><label for="odds-${k}">${OUTCOMES[k]}赔率</label><input id="odds-${k}" name="${k}" inputmode="decimal" type="number" step="0.001" min="1.001" max="1000" required value="${esc(d[k] ?? '')}" placeholder="如 2.10"></div>`).join('')}</div>
    <div class="notice">${d.result ? `此场已有赛果：${OUTCOMES[d.result]}。加入模拟后按已知赛果立即结算，记录为历史回测。` : '未设置赛果的记录会保留为待结算，虚拟本金先从可用余额扣除。'} 十进制赔率包含本金。</div>
    ${!d.matchId?`<div class="field" style="margin-top:18px"><label for="manual-result">已知赛果（可选）</label><select id="manual-result"><option value="">尚未结算</option>${['H','D','A','V'].map(k=>`<option value="${k}" ${d.result===k?'selected':''}>${OUTCOMES[k]}</option>`).join('')}</select></div>`:''}
    <hr class="form-divider"><h3>模拟投注</h3><div class="field-row"><div class="field"><label for="selection">我的选择</label><select id="selection" name="selection">${['H','D','A'].map(k=>`<option value="${k}" ${(d.selection || 'H')===k?'selected':''}>${OUTCOMES[k]}</option>`).join('')}</select></div><div class="field"><label for="stake">投注金额（虚拟单位）</label><input id="stake" name="stake" type="number" inputmode="decimal" min="0.01" max="1000000" step="0.01" value="100"></div></div>
    <div class="quote-preview"><span>若命中，含本金返还<br><strong id="return-preview">—</strong></span><span>预计净盈利<br><strong id="profit-preview">—</strong></span></div>
    <p id="form-error" class="form-error" role="alert"></p><div class="form-actions"><button type="submit" class="button">加入模拟记录</button><button type="button" class="button secondary" id="save-odds">${d.savedId?'保存赔率修改':'只保存赔率'}</button></div><p class="note">记录保存在当前浏览器。可在“我的记录”导出备份，带到其他设备。</p></form></section>
    <aside class="sim-aside"><section class="bankroll"><h2>我的虚拟账户</h2><div class="balance">${amount(bank.balance)}</div><span class="unit">当前可用 · 虚拟单位</span><dl><div><dt>累计净盈亏</dt><dd>${bank.profit>=0?'+':''}${amount(bank.profit)}</dd></div><div><dt>待结算本金</dt><dd>${amount(bank.pending)}</dd></div><div><dt>已结算收益率</dt><dd>${bank.roi.toFixed(2)}%</dd></div></dl></section><details class="rules"><summary>模拟规则与计算方式</summary><p>初始虚拟资金为 ${amount(INITIAL_BALANCE)}。<br>命中返还 = 投注金额 × 十进制赔率。<br>未命中返还 0；作废退回本金。<br>每笔金额精确到两位小数。</p><p>赔率在加入模拟时锁定，之后修改个人赔率不会改动已有投注。</p><p>历史回测按已知赛果结算；赛前记录在完赛后结算。</p></details></aside></div>`;
  document.querySelector('#match-picker').addEventListener('change', event => {
    const value = event.target.value;
    if (value.startsWith('match:')) draft = draftFromMatch(findMatch(value.slice(6)));
    else if (value.startsWith('saved:')) { const o=store.odds.find(o=>o.id===value.slice(6)); draft={...o,savedId:o.id}; }
    else draft = null;
    renderSimulator();
  });
  document.querySelector('#bet-form').addEventListener('input', updateQuote);
  document.querySelector('#bet-form').addEventListener('submit', event => { event.preventDefault(); saveForm(true); });
  document.querySelector('#save-odds').addEventListener('click', () => { if(document.querySelector('#bet-form').reportValidity()) saveForm(false); });
  updateQuote();
}
function updateQuote() {
  try {
    const stake = moneyInput(document.querySelector('#stake').value);
    const selection = document.querySelector('#selection').value;
    const odds = decimalOdds(document.querySelector(`#odds-${selection}`).value);
    const returned = payout(stake, odds, selection, selection);
    document.querySelector('#return-preview').textContent = amount(returned);
    document.querySelector('#profit-preview').textContent = '+' + amount(returned - stake);
  } catch {
    document.querySelector('#return-preview').textContent = '—';
    document.querySelector('#profit-preview').textContent = '—';
  }
}
function saveForm(bet) {
  const errorElement = document.querySelector('#form-error');
  try {
    const fields = new FormData(document.querySelector('#bet-form'));
    const home = String(fields.get('home')).trim(), away = String(fields.get('away')).trim();
    if (!home || !away || home.toLowerCase() === away.toLowerCase()) throw new Error('请填写两支不同的球队。');
    const date = String(fields.get('date'));
    if (!validDate(date)) throw new Error('请填写有效的比赛日期。');
    const source = String(fields.get('source')).trim();
    if (!source) throw new Error('请注明赔率来源或备注。');
    const odds = Object.fromEntries(['H','D','A'].map(k=>[k,decimalOdds(fields.get(k))/1000]));
    const result = draft?.matchId ? findMatch(draft.matchId)?.result ?? draft.result ?? null : (document.querySelector('#manual-result')?.value || null);
    if (result && date > new Date().toLocaleDateString('en-CA')) throw new Error('未来日期的比赛不能填写已知赛果。');
    const row = { id:crypto.randomUUID(), date, home, away, ...odds, source, matchId:draft?.matchId || null, result, createdAt:new Date().toISOString() };
    const next = latestStore();
    if (bet) {
      const stake = moneyInput(fields.get('stake'));
      if (stake > summary(next.bets).balance) throw new Error('投注金额超过可用虚拟余额，请减少金额。');
      const selection = fields.get('selection');
      next.bets.push({...row, stake, selection, oddsMilli:decimalOdds(fields.get(selection)), resultSource:result ? '已知赛果回测' : '待结算'});
      commit(next); draft = null; location.hash = '#/records'; toast('已保存模拟投注。' + (result ? ' 已按历史赛果结算。' : ' 等待比赛结算。'));
    } else {
      if (draft?.savedId) {
        const index=next.odds.findIndex(o=>o.id===draft.savedId);
        if(index<0) throw new Error('这条记录已经变更，请重新打开。');
        next.odds[index] = {...row, id:draft.savedId};
      } else next.odds.push(row);
      commit(next); draft={...row,savedId:draft?.savedId || row.id}; renderSimulator(); toast('赔率已保存在本浏览器。');
    }
  } catch(error) { errorElement.textContent = error.message || '保存失败，请检查浏览器存储空间。'; }
}
export function renderRecords() {
  const bank=summary(store.bets);
  main.innerHTML = `${pageHeading('每一次判断，都有记录。', '个人赔率与虚拟投注保存在本浏览器，可导出备份后转移。', '<a class="button" href="#/simulator">录入一场比赛</a>')}
    <div class="record-stats"><div><span>可用虚拟余额</span><strong>${amount(bank.balance)}</strong></div><div><span>累计净盈亏</span><strong class="${bank.profit<0?'negative':'profit'}">${bank.profit>=0?'+':''}${amount(bank.profit)}</strong></div><div><span>待结算本金</span><strong>${amount(bank.pending)}</strong></div><div><span>已结算收益率</span><strong>${bank.roi.toFixed(2)}%</strong></div></div>
    <div class="toolbar"><p class="note">清除浏览器数据会移除本地记录，请定期备份。</p><div><button class="button secondary compact" id="export-data">导出备份</button> <label class="button secondary compact" for="import-data" tabindex="0">导入备份</label><input type="file" id="import-data" accept="application/json,.json" class="hidden"></div></div><div id="import-confirm" class="notice hidden" role="status"></div>
    <div class="section-head"><h2>模拟投注 <span class="small subtle">${store.bets.length} 笔</span></h2><p>返还包含本金 · 已知赛果标为回测</p></div>
    ${store.bets.length?`<div class="table-wrap"><table><thead><tr><th>比赛 / 日期</th><th>选择</th><th>锁定赔率</th><th>金额</th><th>返还</th><th>净盈亏</th><th>状态 / 操作</th></tr></thead><tbody>${[...store.bets].reverse().map(b=>{
      const returned=payout(b.stake,b.oddsMilli,b.selection,b.result); const net=returned==null?null:returned-b.stake;
      return `<tr><td class="team-cell">${esc(cn(b.home))} vs ${esc(cn(b.away))}<div class="small subtle">${dateText(b.date)} · ${esc(b.source)}</div></td><td>${OUTCOMES[b.selection]}</td><td>${(b.oddsMilli/1000).toFixed(3).replace(/0$/,'')}</td><td>${amount(b.stake)}</td><td>${returned==null?'—':amount(returned)}</td><td class="${net<0?'negative':'profit'}">${net==null?'待结算':`${net>=0?'+':''}${amount(net)}`}</td><td>${b.result?`<span class="tag">${b.result==='V'?'已作废':returned>0?'命中':'未命中'}</span><div class="small subtle">${esc(b.resultSource || '已结算')} · ${OUTCOMES[b.result]}</div>`:`<div class="inline-settle"><select aria-label="${esc(cn(b.home)+' 对 '+cn(b.away)+' 的赛果')}" data-settle-value="${esc(b.id)}"><option value="">选择赛果</option>${['H','D','A','V'].map(k=>`<option value="${k}">${OUTCOMES[k]}</option>`).join('')}</select><button class="button secondary compact" data-settle="${esc(b.id)}">结算</button></div>`}</td></tr>`;
    }).join('')}</tbody></table></div>`:'<div class="empty">还没有模拟投注。先选择一场比赛，记录你的第一笔判断。<br><a class="button quiet" href="#/simulator">开始一次模拟 →</a></div>'}
    <div class="section-head"><h2>我保存的赔率 <span class="small subtle">${store.odds.length} 组</span></h2><a class="button quiet" href="#/simulator">录入赔率 →</a></div>
    ${store.odds.length?`<div class="table-wrap"><table><thead><tr><th>比赛 / 日期</th><th>主胜</th><th>平局</th><th>客胜</th><th>来源</th><th></th></tr></thead><tbody>${[...store.odds].reverse().map(o=>`<tr><td class="team-cell">${esc(cn(o.home))} vs ${esc(cn(o.away))}<div class="small subtle">${dateText(o.date)}</div></td><td>${oddsText(o.H)}</td><td>${oddsText(o.D)}</td><td>${oddsText(o.A)}</td><td>${esc(o.source)}</td><td><button class="button quiet compact" data-use-odds="${esc(o.id)}">编辑 / 模拟</button></td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">还没有个人赔率。录入赔率后点击“只保存赔率”，即可建立自己的记录。</div>'}`;
  document.querySelector('#export-data').addEventListener('click',()=>{
    const url=URL.createObjectURL(new Blob([localStorage.getItem(STORAGE_KEY) || JSON.stringify(store,null,2)],{type:'application/json'}));
    const a=document.createElement('a'); a.href=url; a.download=`FootballKnow-备份-${new Date().toISOString().slice(0,10)}.json`; a.click(); setTimeout(()=>URL.revokeObjectURL(url),5000);
  });
  document.querySelector('label[for="import-data"]').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();document.querySelector('#import-data').click();}});
  document.querySelector('#import-data').addEventListener('change',async event=>{
    try {
      const file=event.target.files[0]; if(!file)return;
      if(file.size>5000000)throw new Error('备份文件不能超过 5 MB。');
      const imported=validateStore(JSON.parse(await file.text()));
      const confirmArea=document.querySelector('#import-confirm');
      confirmArea.classList.remove('hidden');
      confirmArea.innerHTML=`<p>备份包含 ${imported.bets.length} 笔模拟与 ${imported.odds.length} 组赔率。导入会替换当前记录，建议先导出当前备份。</p><button class="button compact" id="confirm-import">确认导入并替换记录</button> <button class="button secondary compact" id="cancel-import">取消导入</button>`;
      document.querySelector('#confirm-import').addEventListener('click',()=>{try{commit(imported);renderRecords();toast('已恢复备份。');}catch(error){toast(error.message);}});
      document.querySelector('#cancel-import').addEventListener('click',()=>{confirmArea.classList.add('hidden');event.target.value='';});
    }catch(error){toast(error.message||'导入失败，请选择有效备份。');}
  });
}

export function selectMatch(match,selection) {draft=draftFromMatch(match,selection);}
export function selectSavedOdds(id) {const row=store.odds.find(o=>o.id===id);if(row)draft={...row,savedId:row.id};}
export function settleRecord(button) {
    const select=main.querySelector(`[data-settle-value="${CSS.escape(button.dataset.settle)}"]`);const result=select.value;
    if(!['H','D','A','V'].includes(result)){toast('请先选择主胜、平局、客胜或作废。');return;}
    try{
      const next=latestStore();const bet=next.bets.find(b=>b.id===button.dataset.settle);
      if(!bet||bet.result)throw new Error('这笔模拟已经结算，请刷新记录。');
      if(result!=='V'&&bet.date>new Date().toLocaleDateString('en-CA'))throw new Error('比赛日期尚未到来，不能提前结算。');
      if(button.dataset.confirmResult!==result){button.dataset.confirmResult=result;button.textContent=`确认${OUTCOMES[result]}`;toast(`将按“${OUTCOMES[result]}”结算，请再次点击确认按钮。`);return;}
      bet.result=result;bet.resultSource='手动结算';commit(next);renderRecords();toast('虚拟账户已结算。');
    }catch(error){toast(error.message);}
}
