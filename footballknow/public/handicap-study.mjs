const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = v => v == null ? '—' : `${Number(v).toFixed(2)}%`;
const count = v => Number(v || 0).toLocaleString('zh-CN');
const measure = m => `<strong>${pct(m.pct)}</strong><small>${count(m.count)} / ${count(m.n)} 场</small>`;
const seasonName = s => s.replace('-', '/');
const lineName = n => n === 0 ? '平手' : `${n < 0 ? '主让' : '主受让'}${Math.abs(n) === .25 ? '平／半' : '半球'}`;
const sideName = {home:'固定买主队',away:'固定买客队',upper:'固定买上盘',lower:'固定买下盘'};
const money = n => `${n > 0 ? '+' : ''}${Number(n).toLocaleString('zh-CN',{maximumFractionDigits:2,minimumFractionDigits:2})}`;
const safeSource = value => /^https:\/\/(www\.)?football-data\.co\.uk\//.test(value || '') ? esc(value) : '#';

export function selectStudy(report, season='all', league='all') {
  const period = season === 'all' ? report.all : report.seasons.find(s=>s.season===season);
  if (!period) throw new Error('找不到这个赛季的研究资料');
  const selected = league === 'all' ? period : period.leagues.find(l=>l.id===league);
  if (!selected) throw new Error('找不到这个联赛的研究资料');
  return selected;
}

function table(headers, rows, caption='') {
  return `<div class="study-table"><table>${caption ? `<caption>${esc(caption)}</caption>` : ''}<thead><tr>${headers.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}

function scoreList(items, label) {
  return `<section class="study-scores"><h3>${label}</h3>${items.length ? items.slice(0,6).map(s=>`<div><b>${esc(s.score)}</b><span><i style="width:${Math.min(100,Number(s.pct)*3)}%"></i></span><strong>${pct(s.pct)}</strong><small>${count(s.count)} 场</small></div>`).join('') : '<p>此范围没有样本。</p>'}</section>`;
}

export function studyBody(report, season='all', league='all') {
  const g = selectStudy(report,season,league), s = g.summary, half = s.halfBall;
  const seasonRows = report.seasons.map(p=>({label:seasonName(p.season),...selectStudy(report,p.season,league).summary}));
  const period = season === 'all' ? report.all : report.seasons.find(p=>p.season===season);
  const leagueRows = period.leagues.filter(l=>league==='all'||l.id===league).map(l=>({label:l.label,...l.summary}));
  const compare = rows => table(['范围','样本数','平局','距盘口 ≤1球','0:0 或 1:1'],rows.map(r=>`<tr><th scope="row">${esc(r.label)}</th><td>${count(r.n)}</td><td>${measure(r.draw)}</td><td>${measure(r.bands['1'])}</td><td>${measure(r.draw00or11)}</td></tr>`));
  const receipts = report.sources.filter(r=>(season==='all'||r.season===season)&&(league==='all'||r.league===league));
  const total = receipts.reduce((n,r)=>n+r.audit.validResults,0);
  const missing = receipts.reduce((n,r)=>n+(r.audit.missingClosingLine||0)+(r.audit.invalidClosingLine||0),0);
  const deepN=receipts.reduce((n,r)=>n+(r.audit.outsideScope||0),0);
  const deepRate=k=>({count:receipts.reduce((n,r)=>n+(r.audit[k]||0),0),n:deepN,pct:deepN?receipts.reduce((n,r)=>n+(r.audit[k]||0),0)/deepN*100:null});
  const claim = half.n ? `半球盘下盘赢的 ${count(half.lowerWin.count)} 场中，0:0／1:1 有 ${count(half.draw00or11GivenLowerWin.count)} 场，占 ${pct(half.draw00or11GivenLowerWin.pct)}；另有 ${count(half.underdogOutrightWins)} 场是下盘直接赢球。` : '此范围没有半球盘样本。';
  const noGames = s.n === 0 ? '<p class="study-empty">此范围没有有效收盘样本，比例和收益不作估计。</p>' : '';
  return `${noGames}<p class="study-scope">${season==='all'?'三个完整赛季':esc(seasonName(season))} · ${league==='all'?'四大联赛':esc(g.label)} · 收盘平手／平半／半球</p>
  <div class="study-kpis">
    <div><span>纳入浅盘比赛</span><b>${count(s.n)}</b><small>从 ${count(total)} 场完整赛果筛选</small></div>
    <div><span>平局比例</span><b>${pct(s.draw.pct)}</b><small>${count(s.draw.count)} / ${count(s.n)} 场</small></div>
    <div><span>净胜球距盘口中心 ≤1球</span><b>${pct(s.bands['1'].pct)}</b><small>${count(s.bands['1'].count)} / ${count(s.n)} 场</small></div>
    <div><span>0:0 或 1:1 的占比</span><b>${pct(s.draw00or11.pct)}</b><small>${count(s.draw00or11.count)} / ${count(s.n)} 场</small></div>
  </div>
  <section class="study-finding"><span>这一组数据说明什么</span><p>${esc(claim)}</p><p>浅盘能提供净胜球参考，但不能单独确定比分。这个范围小于 2.5 球的比赛占 ${pct(s.under25.pct)}，还需结合大小球报价区分进球环境。</p></section>
  <div class="study-pair"><section class="study-panel"><h2>一个球季一个球季看</h2>${compare(seasonRows)}<p class="study-note">按当前联赛筛选显示三季，便于检查规律是否稳定。</p></section><section class="study-panel"><h2>四大联赛分开看</h2>${compare(leagueRows)}<p class="study-note">按当前赛季显示，避免把不同联赛混为一种规律。</p></section></div>
  <section class="study-panel"><h2>平手、平半、半球，分别有何不同</h2>
  ${table(['赛前收盘（主队视角）','场数','主胜','平局','客胜','距盘口 ≤1球','0:0／1:1'],g.byLine.map(r=>`<tr><th scope="row">${lineName(r.line)}<small>${r.line>0?'+':''}${r.line}</small></th><td>${count(r.n)}</td><td>${measure(r.homeWin)}</td><td>${measure(r.draw)}</td><td>${measure(r.awayWin)}</td><td>${measure(r.bands['1'])}</td><td>${measure(r.draw00or11)}</td></tr>`))}
  <p class="study-note">负数表示主队让球，正数表示主队受让。每场只算一次。比例分母为该行场数。</p></section>
  <section class="study-panel study-hypothesis"><h2>重点检验：半球下盘，是否主要落在 0:0／1:1</h2>
    <div class="study-hypothesis-grid"><div><span>全部半球盘</span><b>${count(half.n)} 场</b><p>其中下盘赢 ${count(half.lowerWin.count)} 场，${pct(half.lowerWin.pct)}。</p></div><div><span>假设每场都只选 0:0＋1:1</span><b>${pct(half.fixed00or11.pct)}</b><p>${count(half.fixed00or11.count)} / ${count(half.n)} 场。这才是两个固定比分对全部半球盘的覆盖率。</p></div><div><span>仅在下盘已赢的场次中观察</span><b>${pct(half.draw00or11GivenLowerWin.pct)}</b><p>0:0／1:1 共 ${count(half.draw00or11GivenLowerWin.count)} 场；其他平局 ${count(half.otherDraws)} 场；下盘直接赢球 ${count(half.underdogOutrightWins)} 场。</p></div></div>
    <p class="study-note">“下盘已赢”是赛后条件，不能把这组比例当作赛前比分命中率。数据没有成对比分投注价格，本研究不计算比分盈利。</p>
  </section>
  <div class="study-pair"><section class="study-panel"><h2>比分出现的频率</h2>${scoreList(s.homeScores,'主队 : 客队')}${scoreList(s.favoriteScores,'让球方 : 受让方（不含平手盘）')}<p class="study-note">这是同一批已完赛比赛中最常见的比分，含事后排序，不是提前发出的推荐。</p></section>
  <section class="study-panel"><h2>实际净胜球离盘口有多远</h2><p class="study-note">距离 = |主队进球 − 客队进球 + 主队收盘让球|。</p><div class="study-bands">${['0.5','1','2'].map(b=>`<div><span>距离 ≤${b} 球</span><strong>${pct(s.bands[b].pct)}</strong><div class="study-band"><i style="width:${s.bands[b].pct||0}%"></i></div><small>${count(s.bands[b].count)} / ${count(s.n)} 场</small></div>`).join('')}</div><p class="study-note">以上为累计范围，不能相加。例如主让半球，1:0 与 0:0 均距盘口中心半球，0:1 则相距一球半。范围覆盖率不等于精确比分命中率。</p></section></div>
  <details class="study-detail"><summary>上下盘结算与固定买入回报 <span>展开查看</span></summary><div class="study-detail-body"><p>每场固定 100 单位，以 Bet365 成对收盘十进制赔率结算。上盘为让球方，下盘为受让方；平手盘单独按主／客计算。赢半、输半和走盘分开列。</p>
  ${table(['盘口 / 固定选择','样本','全赢','赢半','走盘','输半','全输','有报价场数','净收益','回报率'],g.byDepth.flatMap(d=>(d.depth===0?['home','away']:['upper','lower']).map(side=>{const v=d.sides[side];return `<tr><th scope="row">${d.depth===0?'平手':d.depth===.25?'平／半':'半球'} · ${sideName[side]}</th><td>${count(v.n)}</td>${['全赢','赢半','走盘','输半','全输'].map(k=>`<td>${count(v.outcomes[k])}</td>`).join('')}<td>${count(v.pricedN)}</td><td>${v.pricedN?money(v.profitPer100):'—'}</td><td>${pct(v.roiPct)}</td></tr>`;})))}<p class="study-note">收益只使用有完整成对报价的场次，投入为有报价场数 ×100；并非网站真实推荐或实盘收益。没有比分赔率时不能推算比分回报。</p></div></details>
  <details class="study-detail"><summary>盘口变化与大小球环境 <span>展开查看</span></summary><div class="study-detail-body"><h3>较早采样盘 → 赛前收盘</h3><p>所有组最终均为半球以内。以最终让球方看升降；平手单列。这里只比较让球数，不把“盘口不变”误称为“赔率完全不变”。</p>
  ${table(['变化类型','场数','平局','距盘口 ≤1球','小于2.5球','上盘有盈利场次'],g.byMovement.filter(r=>r.n).map(r=>`<tr><th scope="row">${esc(r.movement)}</th><td>${count(r.n)}</td><td>${measure(r.draw)}</td><td>${measure(r.bands['1'])}</td><td>${measure(r.under25)}</td><td>${measure(r.sides.upper.positive)}</td></tr>`))}
  <p class="study-note">上盘有盈利包含全赢与赢半，分母不含平手盘。变化与赛果的关联不等于因果，本表不能判断是否由伤停、资金或阵容消息导致。</p><h3>收盘大小球报价分组</h3>
  ${table(['大小球环境','场数','实际小于2.5球','平局','0:0／1:1'],g.byTotalMarket.filter(r=>r.n).map(r=>`<tr><th scope="row">${esc(r.market)}</th><td>${count(r.n)}</td><td>${measure(r.under25)}</td><td>${measure(r.draw)}</td><td>${measure(r.draw00or11)}</td></tr>`))}
  <p class="study-note">用 Bet365 大／小2.5球成对收盘价格去除报价水位后分组：大球隐含概率 &lt;45% 为偏小球，45%–55% 为均衡，&gt;55% 为偏大球。它是统一的2.5球报价，并非每场的主流大小球盘口。</p>
  <h3>对照：浅盘是否更接近势均力敌</h3>
  ${table(['范围','场数','净胜球差 ≤1球','平局','0:0／1:1'],[
    `<tr><th scope="row">半球以内</th><td>${count(s.n)}</td><td>${measure(s.oneGoalOrDraw)}</td><td>${measure(s.draw)}</td><td>${measure(s.draw00or11)}</td></tr>`,
    `<tr><th scope="row">半球以外</th><td>${count(deepN)}</td><td>${measure(deepRate('deepCloseGame'))}</td><td>${measure(deepRate('deepDraws'))}</td><td>${measure(deepRate('deep00or11'))}</td></tr>`
  ])}<p class="study-note">此处“净胜球差 ≤1球”指实际主客进球差的绝对值，不加盘口。不同盘口组的球队实力构成不同，差异只作为描述性对照。</p></div></details>
  <details class="study-detail"><summary>计算口径、样本区间与资料来源 <span>展开查看</span></summary><div class="study-detail-body"><p>当前范围共 ${count(total)} 场完整赛果；纳入 ${count(s.n)} 场，盘口超范围 ${count(total-s.n-missing)} 场，收盘盘口缺失／无效 ${count(missing)} 场。每季全场数核对：英超、西甲、意甲各380场，德甲306场。</p>
  <ul>${Object.values(report.basis).map(t=>`<li>${esc(t)}</li>`).join('')}</ul>
  <p>距盘口一球以内比例的 Wilson 95% 区间：${s.bands['1'].interval95?.map(pct).join(' – ')||'无样本'}。本研究只做描述性统计，不把分组差异直接认定为稳定优势。</p>
  <p>来源：<a href="${safeSource(report.sourceUrl)}" target="_blank" rel="noopener">Football-Data 数据说明 ↗</a> · <a href="${safeSource(report.notesUrl)}" target="_blank" rel="noopener">字段定义 ↗</a>。计算版本 ${esc(report.version)}；更新 ${esc(report.generatedAt.slice(0,10))}。</p>
  ${table(['赛季','联赛','完整赛果','收盘可用','浅盘入选','来源'],receipts.map(r=>`<tr><td>${esc(seasonName(r.season))}</td><td>${esc(report.all.leagues.find(l=>l.id===r.league)?.label)}</td><td>${count(r.audit.validResults)}</td><td>${count(r.audit.validClosingLines)}</td><td>${count(r.audit.selected)}</td><td><a href="${safeSource(r.url)}" target="_blank" rel="noopener">原始来源 ↗</a></td></tr>`))}
  <p class="study-note">公开页面展示自行计算的统计结论；逐场研究表单独保存。资料源未提供精确采样时分，本页使用其标注的收盘数据，不混入滚球盘或拿早盘补收盘。</p></div></details>`;
}

export function renderHandicapStudy(root=document.querySelector('#main'), fetcher=globalThis.fetch) {
  let stopped=false, report;
  const controller=new AbortController();
  root.innerHTML='<section class="handicap-study"><div class="study-hero"><span>峰弈研究 · 历史样本检验</span><h1>半球以内的盘，比分落在哪里</h1><p>三个完整赛季 · 英超 / 西甲 / 意甲 / 德甲 · 统一以赛前收盘为准</p></div><div class="study-loading" role="status">正在读取已核对的三季统计…</div></section>';
  const container=root.querySelector('.handicap-study');
  const repaint=()=>{container.querySelector('[data-study-body]').innerHTML=studyBody(report,container.querySelector('[name=study-season]').value,container.querySelector('[name=study-league]').value);};
  const change=e=>{if(e.target.matches('[data-study-filter]'))repaint();};
  const load=async()=>{
    try {
      const response=await fetcher('./research/shallow-handicap.json',{signal:controller.signal});
      if(!response.ok)throw new Error('研究资料暂时无法读取');
      report=await response.json();
      if(stopped)return;
      if(report.version!=='closing-shallow-handicap-v1'||!report.all?.summary||report.seasons?.length!==3)throw new Error('研究资料版本不完整');
      container.querySelector('.study-loading')?.remove();
      container.insertAdjacentHTML('beforeend',`<div class="study-filters"><label>赛季<select name="study-season" data-study-filter><option value="all">三季合计</option>${report.seasons.map(s=>`<option value="${esc(s.season)}">${esc(seasonName(s.season))}</option>`).join('')}</select></label><label>联赛<select name="study-league" data-study-filter><option value="all">四大联赛合计</option>${report.all.leagues.map(l=>`<option value="${esc(l.id)}">${esc(l.label)}</option>`).join('')}</select></label><span>平手 · 平／半 · 半球<br>历史研究，不计入预测命中率</span></div><div data-study-body aria-live="polite"></div>`);
      container.addEventListener('change',change);repaint();
    }catch(error){if(stopped||error.name==='AbortError')return;container.querySelector('.study-loading')?.remove();container.insertAdjacentHTML('beforeend',`<div class="study-empty" role="alert">${esc(error.message)}。<button type="button" data-study-retry>重新读取</button></div>`);container.querySelector('[data-study-retry]').addEventListener('click',()=>{container.querySelector('.study-empty').remove();load();},{once:true});}
  };
  load();
  return ()=>{stopped=true;controller.abort();container.removeEventListener('change',change);};
}
