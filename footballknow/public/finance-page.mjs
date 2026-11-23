import {bindFollowingSync} from './stock-sync.mjs';
import {main,esc,pageHeading,sourceLink,timeText,toast} from './ui.mjs';
import {finite,figure,signed,direction,forecastLabel,validQuotes,chartPoints,rateText,financialRows,financialAmount,financialUnit,stockSector,industryGroups,filterStocks} from './finance-core.mjs';

import {STOCK_FOLLOWING_KEY,readStockFollowing,toggleStockFollowing} from './stock-following.mjs';
import {renderStockChart} from './stock-chart.mjs';
import {range52} from './market-reference.mjs';
import {bindReview,syncStockWatchlist} from './review-panel.mjs';
import {chairmenHtml} from './company-leaders.mjs';
import {capitalCategory,capitalBadge,capitalDetail} from './capital-structure.mjs';

function followButton(code,name,following){return '<button type="button" class="stock-watch-toggle'+(following?' is-following':'')+'" data-stock-follow="'+code+'" aria-pressed="'+following+'" aria-label="'+esc((following?'取消关注':'关注')+name)+'"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.8 5.7 6.3.9-4.6 4.5 1.1 6.3-5.6-3-5.6 3 1.1-6.3-4.6-4.5 6.3-.9Z"/></svg><span>'+(following?'已关注':'关注')+'</span></button>';}

async function read(url,signal,options={}){
  const controller=new AbortController(),abort=()=>controller.abort();
  signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)abort();
  const timer=setTimeout(abort,options.timeoutMs||(options.method?90000:15000));
  try{
    const response=await fetch(url,{cache:'no-cache',...options,signal:controller.signal});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||'资料暂时无法读取。');
    return data;
  }finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
}
const stamp=value=>value?esc(new Date(value).toLocaleString('zh-CN')):'—';
const quoteNote=q=>'<small class="subtle">'+(q?.quotedAt?'报价 '+stamp(q.quotedAt):'采集 '+stamp(q?.fetchedAt||q?.updatedAt))+' · '+esc(q?.provider||'来源待同步')+(q?.delaySeconds?' · 延迟约 '+Math.round(q.delaySeconds/60)+' 分钟':'')+'</small>';
const assetChange=q=>!finite(q?.changePercent)?'涨跌幅待提供':signed(q.changePercent)+'%'+(q.changeBasis?' · '+esc(q.changeBasis):'');
function spark(bars,limit=90){
  const graph=chartPoints(bars,limit);
  if(!graph)return '<div class="empty">价格历史正在同步。</div>';
  return '<figure class="price-chart"><svg viewBox="0 0 770 220" role="img" aria-label="收盘价格走势"><line x1="30" y1="190" x2="740" y2="190" stroke="var(--line)"/><polyline points="'+graph.points+'" fill="none" stroke="var(--brand)" stroke-width="2.5" vector-effect="non-scaling-stroke"/><text x="30" y="215">'+esc(graph.rows[0].date)+'</text><text x="740" y="215" text-anchor="end">'+esc(graph.rows.at(-1).date)+'</text></svg><figcaption>区间最低 '+figure(graph.low)+' · 最高 '+figure(graph.high)+' · 每日收盘</figcaption></figure>';
}
function assetCards(snapshot){
  return '<div class="asset-strip">'+['gold','brent','wti','bitcoin'].map(key=>{
    const q=snapshot?.assets?.[key];
    return '<a class="asset-tile" href="#/asset/'+key+'"><span>'+esc(q?.name||({gold:'黄金期货',brent:'布伦特原油',wti:'WTI 原油',bitcoin:'比特币'})[key])+'</span><strong>'+figure(q?.price)+'</strong><span class="'+direction(q?.changePercent)+'">'+assetChange(q)+'</span><small>'+esc(q?.unit||'美元')+'</small>'+quoteNote(q)+(snapshot?.failedAssets?.includes(key)?'<small class="attention">更新暂未成功</small>':'')+'</a>';
  }).join('')+'</div>';
}
export async function paintMarketPreview(target){
  if(!target)return;
  try{const data=await read('./finance/assets.json');if(target.isConnected)target.innerHTML='<div class="section-head"><h2>市场行情</h2><a class="button quiet" href="#/markets">港股与市场 →</a></div>'+assetCards(data);}
  catch{if(target.isConnected)target.innerHTML='<p class="note"><a href="#/markets">查看港股与市场行情 →</a></p>';}
}
export function renderMarkets(followingOnly=false){
  const controller=new AbortController();let catalogue=null,quotes={quotes:{}},assets=null,query='',scope='all',sector='all',page=0,loadingQuotes=false,searchTimer,watchlist=readStockFollowing(),capital=null,capitalFilter='all';
  main.innerHTML=pageHeading(followingOnly?'我的关注':'港股与市场',followingOnly?'集中查看关注股票的报价与资料；连接手机与电脑后，关注列表自动同步。':'港交所全部上市股票与全球市场参考行情。',followingOnly?'<a class="button secondary" href="#/markets">添加关注股票</a>':'<a class="button secondary" id="stock-following-link" href="#/stock-following">我的关注</a>')+(followingOnly?'<div id="stock-device-sync"></div>':'')+'<p><a href="#/stock-rankings">每日涨跌榜与 52 周高低位 →</a> · <a href="#/stock-volume">长期低成交与放量提醒 →</a> · <a href="#/cn-markets">沪深 A 股 →</a></p><div id="market-assets"'+(followingOnly?' hidden':'')+'></div><section id="hsi-quote"'+(followingOnly?' hidden':'')+'></section><p id="stock-following-message" class="note" role="status"></p><div class="toolbar"><label class="search-field">搜索全部港股<input type="search" id="stock-search" placeholder="股票代码、中文或英文名称"></label><label>股票范围<select id="stock-sector"><option value="all">全部港股</option><option value="hsi">恒指成份股</option><option value="main">主板</option><option value="gem">GEM 创业板</option><option value="reit">房地产信托 REIT</option></select></label><label>行业分类<select id="stock-industry"><option value="all">全部行业</option></select></label></div><div class="capital-filters" aria-label="现金负债分类"><button data-capital="all" aria-pressed="true">全部财务类型</button><button data-capital="cash" class="capital-cash" aria-pressed="false">现金多</button><button data-capital="debt" class="capital-debt" aria-pressed="false">负债多</button><button data-capital="unknown" aria-pressed="false">待补资料</button><button data-capital="special" aria-pressed="false">金融业独立口径</button></div><p id="capital-coverage" class="note"></p><div id="stock-industry-quick" class="stock-industry-quick" role="group" aria-label="常用行业"></div><p id="stock-count" role="status"></p><div id="stock-list" class="loading">正在读取全部港股名单…</div><div class="toolbar"><button class="button secondary" id="stock-prev">上一页</button><span id="stock-page"></span><button class="button secondary" id="stock-next">下一页</button></div><p id="stock-source" class="note"></p>';
  function available(){const codes=new Set(watchlist.codes);return (catalogue?.stocks||[]).filter(row=>!followingOnly||codes.has(row.code));}
  function selected(){return filterStocks(available(),{scope,sector,query,quotes:quotes.quotes}).filter(row=>capitalFilter==='all'||capitalCategory(capital,row.code)===capitalFilter);}
  function visible(){const rows=selected();page=Math.min(page,Math.max(0,Math.ceil(rows.length/40)-1));return rows.slice(page*40,page*40+40);}
  function paint(){
    if(controller.signal.aborted||!catalogue)return;
    const hsi=quotes.quotes?.HSI,all=selected(),rows=visible();
    const groupStocks=available(),groups=industryGroups(groupStocks),counts=new Map(groups),followed=new Set(watchlist.codes);
    counts.set('其它',filterStocks(groupStocks,{sector:'其它'}).length);
    main.querySelector('#stock-following-message').textContent=watchlist.problem;
    const followingLink=main.querySelector('#stock-following-link');if(followingLink)followingLink.textContent='我的关注（'+watchlist.codes.length+'）';
    main.querySelector('#stock-industry').innerHTML='<option value="all">全部行业（'+groupStocks.length+'）</option>'+'<option value="其它">其它（'+counts.get('其它')+'）</option>'+groups.filter(([name])=>name!=='其它').map(([name,count])=>'<option value="'+esc(name)+'">'+esc(name)+'（'+count+'）</option>').join('');
    main.querySelector('#stock-industry').value=sector;
    main.querySelector('#stock-industry-quick').innerHTML=['all','地产','金融','博彩','科技','其它'].map(name=>'<button type="button" data-stock-industry="'+name+'" aria-pressed="'+(sector===name)+'" class="'+(sector===name?'active':'')+'">'+(name==='all'?'全部行业':name)+'<span>'+(name==='all'?groupStocks.length:counts.get(name)||0)+'</span></button>').join('');
    main.querySelector('#market-assets').innerHTML=assetCards(assets);
    main.querySelector('#hsi-quote').innerHTML='<div class="market-index"><div><span>恒生指数 HSI</span><strong>'+figure(hsi?.price)+'<small> 点</small></strong></div><div class="'+direction(hsi?.changePercent)+'">'+signed(hsi?.change)+' · '+signed(hsi?.changePercent)+'%</div><div>'+quoteNote(hsi)+'</div></div>';
    main.querySelector('#capital-coverage').textContent='公司财务档案已收录 '+Object.keys(capital?.rows||{}).length+' / '+catalogue.stocks.length+' 个交易柜台；后台按全名单持续分批补录。财务分类未确定不等于没有公司资料，可进入详情查看已披露报表。'+(capital?.method||'按已披露现金、存款与借款债券租赁比较。');
    main.querySelector('#stock-count').textContent=(followingOnly?'已关注 '+groupStocks.length+' 个股票及 REIT 交易柜台':'共 '+catalogue.stocks.length+' 个股票及 REIT 交易柜台')+' · 当前筛选 '+all.length+' 个';
    main.querySelector('#stock-list').className='';
    main.querySelector('#stock-list').innerHTML=rows.length?'<div class="table-wrap"><table><thead><tr><th>关注</th><th>股票</th><th>现金 / 负债分类</th><th>行业</th><th>市场 / 类别</th><th>报价 / 币种</th><th>涨跌幅</th><th>开盘</th><th>最高 / 最低</th><th>报价时间</th></tr></thead><tbody>'+rows.map(r=>{const q=quotes.quotes?.[r.code];return '<tr><td>'+followButton(r.code,q?.name||r.name,followed.has(r.code))+'</td><td><a class="stock-name capital-'+capitalCategory(capital,r.code)+'" href="#/stock/'+r.code+'"><strong>'+esc(q?.name||r.name)+'</strong><small>'+r.code+' · '+esc(r.englishName||'')+'</small></a></td><td>'+capitalBadge(capital?.rows?.[r.code])+'</td><td><span class="stock-sector-label">'+esc(stockSector(r))+'</span>'+(r.industry&&r.industry!==stockSector(r)?'<small>'+esc(r.industry)+'</small>':'')+'</td><td>'+esc(r.board)+(r.isHsi?'<small>恒指成份股</small>':'')+'</td><td><b>'+figure(q?.price)+'</b><small>'+esc(q?.currency||r.currency)+'</small></td><td class="'+direction(q?.changePercent)+'">'+signed(q?.changePercent)+'%</td><td>'+figure(q?.open)+'</td><td>'+figure(q?.high)+' / '+figure(q?.low)+'</td><td class="small">'+stamp(q?.quotedAt)+(quotes.failedCodes?.includes(r.code)?'<small class="attention">等待报价更新</small>':'')+'</td></tr>';}).join('')+'</tbody></table></div>':'<div class="empty">'+(watchlist.problem&&followingOnly?'关注列表暂时无法读取。':followingOnly&&!groupStocks.length?'还没有关注股票。<a href="#/markets">去港股列表添加关注 →</a>':'没有符合条件的股票。')+'</div>';
    main.querySelector('#stock-page').textContent='第 '+(page+1)+' / '+Math.max(1,Math.ceil(all.length/40))+' 页';
    main.querySelector('#stock-prev').disabled=page===0;main.querySelector('#stock-next').disabled=(page+1)*40>=all.length;
    main.querySelector('#stock-source').innerHTML=sourceLink(catalogue.source,catalogue.sourceLabel||'港交所完整证券名单')+' · 名单日期 '+esc(catalogue.effectiveDate)+'。'+esc(catalogue.scope||'')+' 当前页报价按分钟检查，公司资料按需读取并缓存。'+(catalogue.industryUpdatedAt?'<br>行业资料：'+sourceLink(catalogue.industrySource,catalogue.industrySourceLabel)+' · 更新 '+stamp(catalogue.industryUpdatedAt)+' · 已分类 '+catalogue.industryCoverage+' / '+catalogue.stocks.length+'。按主营行业归组；博彩含博彩、彩票及相关业务。'+(catalogue.industryRefreshFailed?' 行业更新暂未成功，保留上次资料。':''):'<br>行业资料正在同步，缺少资料的股票列为待分类。');
  }
  async function refreshVisible(){
    if(loadingQuotes||controller.signal.aborted||!catalogue)return;
    loadingQuotes=true;const codes=['HSI',...visible().map(r=>r.code)];
    try{const results=await Promise.allSettled([read('/api/stocks/quotes?codes='+codes.join(','),controller.signal),read('./finance/capital-structure.json',controller.signal)]);if(!controller.signal.aborted){if(results[0].status==='fulfilled'){const fresh=results[0].value;quotes={...fresh,quotes:{...quotes.quotes,...fresh.quotes}};}if(results[1].status==='fulfilled')capital=results[1].value;paint();}}
    catch{}finally{loadingQuotes=false;if(!controller.signal.aborted&&codes.join(',')!==['HSI',...visible().map(r=>r.code)].join(','))refreshVisible();}
  }
  async function load(){
    const results=await Promise.allSettled((followingOnly?['stocks','quotes']:['stocks','quotes','assets']).map(name=>read('./finance/'+name+'.json',controller.signal)));
    if(controller.signal.aborted)return;
    if(results[0].status==='fulfilled'&&Array.isArray(results[0].value.stocks))catalogue=results[0].value;
    if(results[1].status==='fulfilled'&&validQuotes(results[1].value))quotes={...results[1].value,quotes:{...results[1].value.quotes,...quotes.quotes}};
    if(results[2]?.status==='fulfilled')assets=results[2].value;
    if(followingOnly&&catalogue){const cn=await Promise.allSettled(['cn-stocks','cn-quotes'].map(name=>read('./finance/'+name+'.json',controller.signal)));if(controller.signal.aborted)return;if(cn[0].status==='fulfilled')catalogue={...catalogue,stocks:[...catalogue.stocks,...(cn[0].value.stocks||[])]};if(cn[1].status==='fulfilled')quotes={...quotes,quotes:{...quotes.quotes,...(cn[1].value.quotes||{})}};}
    if(!catalogue){main.querySelector('#stock-list').innerHTML='<div class="notice">港股名单暂时无法读取，请稍后刷新。</div>';return;}
    paint();refreshVisible();
  }
  read('./finance/capital-structure.json',controller.signal).then(data=>{capital=data;paint();}).catch(()=>{});
  main.querySelectorAll('[data-capital]').forEach(button=>button.addEventListener('click',()=>{capitalFilter=button.dataset.capital;main.querySelectorAll('[data-capital]').forEach(x=>x.setAttribute('aria-pressed',String(x===button)));changed();}));
  const changed=()=>{page=0;paint();clearTimeout(searchTimer);searchTimer=setTimeout(refreshVisible,300);};
  main.querySelector('#stock-search').addEventListener('input',e=>{query=e.target.value.trim().toLowerCase();changed();});
  main.querySelector('#stock-sector').addEventListener('change',e=>{scope=e.target.value;changed();});
  main.querySelector('#stock-industry').addEventListener('change',e=>{sector=e.target.value;changed();});
  main.querySelector('#stock-industry-quick').addEventListener('click',e=>{const button=e.target.closest('[data-stock-industry]');if(button){sector=button.dataset.stockIndustry;changed();}});
  main.querySelector('#stock-prev').addEventListener('click',()=>{page--;paint();refreshVisible();});
  main.querySelector('#stock-next').addEventListener('click',()=>{page++;paint();refreshVisible();});
  main.querySelector('#stock-list').addEventListener('click',event=>{const button=event.target.closest('[data-stock-follow]');if(!button)return;try{watchlist=toggleStockFollowing(button.dataset.stockFollow);syncStockWatchlist(controller.signal).catch(()=>{if(!controller.signal.aborted)toast('本机关注已保存；设备同步暂未完成，恢复连接后会重试。');});paint();if(followingOnly)refreshVisible();toast(watchlist.following?'已加入股票关注。':'已取消股票关注。');}catch(error){toast(error.message);}});
  const syncFollowing=event=>{if(event.type==='stock-following-changed'||event.key===STOCK_FOLLOWING_KEY||event.key===null){watchlist=readStockFollowing();paint();if(followingOnly)refreshVisible();}};
  window.addEventListener('storage',syncFollowing);window.addEventListener('stock-following-changed',syncFollowing);const stopFollowingSync=bindFollowingSync(main.querySelector('#stock-device-sync'));
  load();const timer=setInterval(()=>{if(!document.hidden)refreshVisible();},60000);
  return()=>{controller.abort();clearInterval(timer);clearTimeout(searchTimer);window.removeEventListener('storage',syncFollowing);window.removeEventListener('stock-following-changed',syncFollowing);stopFollowingSync();};
}
function holderTable(value){
  if(!value?.rows?.length)return '<div class="empty">这个来源暂未提供主要股东资料。</div>';
  return '<div class="table-wrap"><table><thead><tr><th>持有人 / 身份</th><th>权益比例</th><th>归属股数</th><th>直接股数</th><th>股份类别</th><th>报告日期 / 披露日期</th></tr></thead><tbody>'+value.rows.map(r=>'<tr><td><strong>'+esc(r.name)+'</strong><small>'+esc(r.identity||'')+' '+esc(r.basis||'')+'</small></td><td>'+figure(r.percentage)+'%</td><td>'+figure(r.shares,0)+'</td><td>'+figure(r.directShares,0)+'</td><td>'+esc(r.shareClass||'—')+'</td><td>'+esc(r.asOf?.slice(0,10)||'—')+'<small>'+esc(r.announcedAt?.slice(0,10)||'—')+'</small></td></tr>').join('')+'</tbody></table></div><p class="note">归属权益可能包含受控公司持股，同一权益可出现在多个持有人名下，不能相加。报告期与公告日分开显示。最近采集 '+stamp(value.updatedAt)+'。</p>';
}
function predictionHtml(data){
  const current=data.latest;
  const stats=data.evaluation||{};
  const kpis='<div class="forecast-rates">'+['week','quarter'].map(k=>'<div><span>'+({week:'一周',quarter:'一季度'})[k]+'预测命中率</span><strong>'+rateText(stats[k])+'</strong><small>'+ (stats[k]?.correct||0)+' / '+(stats[k]?.evaluated||0)+' 次已验证 · '+(stats[k]?.pending||0)+' 次待到期</small></div>').join('')+'</div>';
  const result=current?'<div class="research-summary"><div class="forecast-picks"><span>短期：<b>'+forecastLabel[current.week]+'</b></span><span>中期：<b>'+forecastLabel[current.quarter]+'</b></span></div>'+current.summary.map(p=>'<p>'+esc(p)+'</p>').join('')+'<small class="subtle">DeepSeek · '+esc(current.model)+' · 发布 '+stamp(current.issuedAt)+'</small><details><summary>更多详细资料</summary>'+(current.priceData?'<p>价格资料截至 '+esc(current.priceData.lastCompletedDate)+'，采集 '+stamp(current.priceData.fetchedAt)+(current.priceData.refreshFailed?'；本次刷新未成功，使用最近保存资料。':'。')+'</p>':'')+current.details.map(d=>'<h3>'+esc(d.title)+'</h3><p>'+esc(d.text)+'</p>').join('')+'</details></div>':'<div class="empty">尚未发布这只股票的预测。管理员可使用已配置的 DeepSeek 生成。</div>';
  const ledger=(data.forecasts||[]).slice(0,30);
  return kpis+result+'<p class="note">计分基准：'+esc(data.rules?.baseline)+'。短期 '+esc(data.rules?.short)+'；中期 '+esc(data.rules?.medium)+'。全部到期预测都会计入，未到期不计成功或失败。</p><details><summary>历史预测与验证记录（最近 '+ledger.length+' 份）</summary><div class="table-wrap"><table><thead><tr><th>发布时间</th><th>一周预测 / 结果</th><th>一季度预测 / 结果</th></tr></thead><tbody>'+ledger.map(row=>'<tr><td>'+stamp(row.issuedAt)+'</td>'+['week','quarter'].map(h=>{const o=row.outcomes?.[h];return '<td>'+forecastLabel[row[h]]+' · '+(o?(o.correct?'命中':'未命中')+'<small>'+esc(o.base_date)+' → '+esc(o.target_date)+'，复权收益 '+signed(o.return_value*100)+'%</small>':'待到期')+'</td>';}).join('')+'</tr>').join('')+'</tbody></table></div></details>';
}
export function renderStock(code){
  const controller=new AbortController();let company=null,history=null,chartLimit=90,stockName=code;const chartOptions={ma5:true,ma10:true,volume:true};let stockReview=null;
  if(!/^\d{5,6}$/.test(code||'')){main.innerHTML='<div class="empty">股票代码不正确。</div>';return()=>{};}
  main.innerHTML=pageHeading('股票资料 · '+esc(code),'报价、业务、股东、财务与预测。','<div class="stock-heading-actions"><span id="stock-follow-action"></span><a class="button secondary" href="#/stock-following">我的关注</a><a class="button secondary" href="#/markets">港股列表</a><a class="button secondary" href="#/cn-markets">沪深 A 股</a></div>')+'<div id="stock-top" class="loading">正在读取报价…</div><div id="stock-range"></div><section><div class="section-head"><h2>阴阳烛与技术指标</h2><div class="segmented"><button data-chart-range="30">近30天</button><button data-chart-range="90" class="active">近90天</button><button data-chart-range="260">近一年</button></div></div><div id="stock-chart"></div></section><section><div class="section-head"><h2>AI 分析与预测</h2><button class="button" id="stock-analyze">生成今日分析</button></div><p id="stock-ai-message" role="status"></p><div id="stock-prediction" class="loading">读取历史预测…</div></section><section id="stock-close-review"></section><section><div class="section-head"><h2>公司业务与背景</h2></div><div id="stock-company" class="loading">正在读取资料…</div></section><section><div class="section-head"><h2>主要股东与披露权益</h2></div><div id="stock-holders"></div></section><section><div class="section-head"><h2>财务报表</h2></div><div class="toolbar"><label>报表<select id="statement-kind"><option value="balance">资产负债表</option><option value="income">利润表</option><option value="cashflow">现金流量表</option></select></label><label>报告期<select id="statement-period"></select></label></div><div id="stock-financials"></div><p class="note">报表金额以亿元列示，每股指标以元/股列示；币种随行标注（来源统一折算）。空白不视为零。中期与年度报告不能直接混比。</p></section><p id="company-source" class="note"></p>';
  async function loadRange(){try{const snapshot=await read('./finance/'+(code.length===6?'cn-quotes':'stock-rankings')+'.json',controller.signal);const q=code.length===6?snapshot.quotes?.[code]:snapshot.rows?.find(q=>q.code===code);if(!controller.signal.aborted)main.querySelector('#stock-range').innerHTML=range52(q?{...q,tradeDate:q.tradeDate||q.barAt?.slice(0,10)}:null);}catch{if(!controller.signal.aborted)main.querySelector('#stock-range').innerHTML=range52(null);}}
  function paintFollow(){const state=readStockFollowing(),following=state.codes.includes(code);main.querySelector('#stock-follow-action').innerHTML=followButton(code,stockName,following);main.querySelector('#stock-analyze').disabled=!following;stockReview?.updateAllowed();if(!following)main.querySelector('#stock-ai-message').textContent='加入我的关注后才进行新的分析与预测。';}
  const syncFollowing=event=>{if(event.type==='stock-following-changed'||event.key===STOCK_FOLLOWING_KEY||event.key===null)paintFollow();};
  main.querySelector('#stock-follow-action').addEventListener('click',()=>{try{const state=toggleStockFollowing(code);syncStockWatchlist(controller.signal).catch(()=>{if(!controller.signal.aborted)toast('本机关注已保存；设备同步暂未完成，恢复连接后会重试。');});paintFollow();toast(state.following?'已加入股票关注。':'已取消股票关注。');}catch(error){toast(error.message);}});
  window.addEventListener('storage',syncFollowing);window.addEventListener('stock-following-changed',syncFollowing);const stopFollowingSync=bindFollowingSync(main.querySelector('#stock-device-sync'));paintFollow();
  function paintChart(){renderStockChart(main.querySelector('#stock-chart'),history,chartLimit,chartOptions);}
  async function quote(){
    try{const snapshot=await read('/api/stocks/quotes?codes='+code,controller.signal),q=snapshot.quotes?.[code];if(controller.signal.aborted)return;stockName=q?.name||company?.name||code;paintFollow();main.querySelector('#stock-top').className='';main.querySelector('#stock-top').innerHTML='<div class="market-index"><div><span class="stock-title">'+esc(q?.name||company?.name||code)+'</span><strong>'+figure(q?.price)+'<small> '+esc(q?.currency==='CNY'?'人民币':q?.currency==='USD'?'美元':'港元')+'</small></strong></div><div class="'+direction(q?.changePercent)+'">'+signed(q?.change)+' · '+signed(q?.changePercent)+'%</div><div>'+quoteNote(q)+'</div></div>';}catch{if(!controller.signal.aborted)main.querySelector('#stock-top').textContent='报价暂时无法更新。';}
  }
  function paintFinancials(){
    const kind=main.querySelector('#statement-kind').value,date=main.querySelector('#statement-period').value,rows=financialRows(company?.financials,kind,date);
    main.querySelector('#stock-financials').innerHTML=rows.length?'<div class="table-wrap"><table><thead><tr><th>项目</th><th>数值</th><th>单位 / 币种</th><th>报告类型</th></tr></thead><tbody>'+rows.map(r=>'<tr><th>'+esc(r.name)+'</th><td>'+financialAmount(r)+'</td><td>'+esc(financialUnit(r)+' · '+(r.currency||'来源未注明'))+'</td><td>'+esc(r.reportType||'—')+'</td></tr>').join('')+'</tbody></table></div>':'<div class="empty">这个来源暂未提供此期报表。</div>';
  }
  async function loadCompany(){
    try{
      company=await read('/api/stocks/'+code+'/company',controller.signal,{timeoutMs:90000});if(controller.signal.aborted)return;
      if(company.code!==code)throw new Error('公司身份不一致');
      if(company.pending){main.querySelector('#stock-company').textContent='资料正在排队读取…';setTimeout(()=>{if(!controller.signal.aborted)loadCompany();},3000);return;}
      const p=company.profile||{};
      main.querySelector('#stock-company').className='research-summary';
      main.querySelector('#stock-company').innerHTML='<h3>'+esc(p.legalName||company.name)+'</h3><p>'+esc(p.business||company.message||'来源暂未提供主要业务说明。')+'</p><dl class="identity-grid">'+[['所属行业',p.industry],['成立日期',p.foundedAt?.slice(0,10)],['上市日期',p.listedAt?.slice(0,10)],['主席',p.chairman],['注册地',p.registeredAt],['员工人数',p.employees]].map(([label,value])=>'<div><dt>'+label+'</dt><dd>'+esc(value??'—')+'</dd></div>').join('')+'</dl>';
      main.querySelector('#stock-chairmen')?.remove();
      main.querySelector('#stock-capital')?.remove();
      main.querySelector('#stock-company').insertAdjacentHTML('afterend','<section id="stock-chairmen"><h2>集团主席</h2>'+chairmenHtml(company)+'</section><div id="stock-capital"></div>');
      read('./finance/capital-structure.json',controller.signal).then(value=>{if(!controller.signal.aborted)main.querySelector('#stock-capital').innerHTML=capitalDetail(value.rows?.[code],value.method);}).catch(()=>{});
      main.querySelector('#stock-chairmen').querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{img.hidden=true;}));
      main.querySelector('#stock-holders').innerHTML=holderTable(company.holders);
      main.querySelector('#statement-period').innerHTML=(company.financials?.periods||[]).map(p=>'<option value="'+esc(p.REPORT_DATE.slice(0,10))+'">'+esc(p.REPORT_DATE.slice(0,10)+' '+(p.REPORT_TYPE||''))+'</option>').join('');
      main.querySelector('#company-source').innerHTML=sourceLink(company.source,company.sourceLabel)+' · '+sourceLink(company.officialFilings,company.filingsLabel||'港交所披露易')+'。采集时间 '+stamp(company.checkedAt)+(company.failedSections?.length?'；部分栏目更新暂未成功，保留最近资料。':'。');
      paintFinancials();
    }catch{if(!controller.signal.aborted){main.querySelector('#stock-company').className='empty';main.querySelector('#stock-company').textContent='公司资料正在同步，稍后可重新进入本页。';}}
  }
  async function loadHistory(){
    try{history=await read('/api/stocks/'+code+'/history',controller.signal,{timeoutMs:90000});if(controller.signal.aborted)return;if(history.pending){setTimeout(()=>{if(!controller.signal.aborted)loadHistory();},3000);return;}paintChart();}catch{if(!controller.signal.aborted)main.querySelector('#stock-chart').innerHTML='<div class="empty">历史价格正在同步。</div>';}
  }
  async function prediction(generate=false){
    const button=main.querySelector('#stock-analyze');button.disabled=true;
    try{if(generate){if(!readStockFollowing().codes.includes(code))throw Error('请先加入我的关注。');await syncStockWatchlist(controller.signal);}const data=await read('/api/stocks/'+code+'/analysis',controller.signal,generate?{method:'POST'}:{});if(!controller.signal.aborted){main.querySelector('#stock-prediction').className='';main.querySelector('#stock-prediction').innerHTML=predictionHtml(data);main.querySelector('#stock-ai-message').textContent=generate?'今日预测已保存；同一天重复点击会显示同一份结果。':readStockFollowing().codes.includes(code)?'':'加入我的关注后才进行新的分析与预测。';}}
    catch(error){if(!controller.signal.aborted){main.querySelector('#stock-ai-message').innerHTML=esc(error.name==='AbortError'?'分析用时较长，请稍后重试。':error.message)+' <a href="#/admin">管理后台</a>';if(!generate){main.querySelector('#stock-prediction').className='';main.querySelector('#stock-prediction').textContent='暂无可读取的预测记录。';}}}
    finally{if(!controller.signal.aborted)button.disabled=!readStockFollowing().codes.includes(code);}
  }
  main.querySelector('#stock-analyze').addEventListener('click',()=>prediction(true));
  main.querySelector('#statement-kind').addEventListener('change',paintFinancials);main.querySelector('#statement-period').addEventListener('change',paintFinancials);
  main.querySelectorAll('[data-chart-range]').forEach(button=>button.addEventListener('click',()=>{chartLimit=Number(button.dataset.chartRange);main.querySelectorAll('[data-chart-range]').forEach(b=>b.classList.toggle('active',b===button));paintChart();}));
  stockReview=bindReview(main.querySelector('#stock-close-review'),{kind:'stock',id:code,signal:controller.signal});
  quote();loadRange();loadCompany();loadHistory();prediction();const timer=setInterval(()=>{if(!document.hidden)quote();},60000);
  return()=>{controller.abort();clearInterval(timer);window.removeEventListener('storage',syncFollowing);window.removeEventListener('stock-following-changed',syncFollowing);stopFollowingSync();};
}
export function renderAsset(id){
  const controller=new AbortController();
  main.innerHTML=pageHeading('市场品种','报价与近期走势。','<a class="button secondary" href="#/markets">返回市场</a>')+'<div id="asset-detail" class="loading">正在读取市场资料…</div><section id="asset-analysis"></section>';
  async function load(){
    try{const all=await read('./finance/assets.json',controller.signal);if(controller.signal.aborted)return;const q=all.assets?.[id];if(!q)throw new Error('这个品种暂时没有报价。');main.querySelector('#asset-detail').className='';main.querySelector('#asset-detail').innerHTML='<div class="market-index"><div><span>'+esc(q.name)+'</span><strong>'+figure(q.price)+'</strong><small>'+esc(q.unit)+'</small></div><div class="'+direction(q.changePercent)+'">'+assetChange(q)+'</div><div>'+quoteNote(q)+'</div></div>'+(q.history?'<h2>历史收盘参考</h2>'+spark(q.history.bars)+'<p class="note">'+sourceLink(q.history.source,q.history.provider)+' · 历史资料采集 '+stamp(q.history.updatedAt)+'，与上方报价来源分开展示。</p>':q.bars?spark(q.bars):'')+'<p class="note">'+esc(q.contract||q.symbol)+' · '+sourceLink(q.source,q.provider)+'。'+(q.instrumentType==='FUTURE'?'这是期货合约报价，连续图表可能受换月影响。':'美元交易参考价。')+'</p>';}catch(error){if(!controller.signal.aborted)main.querySelector('#asset-detail').innerHTML='<div class="notice">'+esc(error.message)+'</div>';}
  }
  bindReview(main.querySelector('#asset-analysis'),{kind:'asset',id,signal:controller.signal});
  load();const timer=setInterval(()=>{if(!document.hidden)load();},60000);return()=>{controller.abort();clearInterval(timer);};
}
