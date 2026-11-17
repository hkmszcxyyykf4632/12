import {markets} from './repository.mjs';
import {league} from './league.mjs';
import {esc,sourceLink,timeText} from './ui.mjs';
import {MARKET_NAMES,PHASE_NAMES,SELECTIONS,validMarket,marketComparisons,movementSummary,manualMarket} from './markets-core.mjs';

function storageKey(match){return 'footballknow-market-notes-v1-'+league.id+'-'+match.id;}
function manualRows(match){try{const value=JSON.parse(localStorage.getItem(storageKey(match))||'[]');return Array.isArray(value)?value.filter(q=>q.manual&&validMarket(q)):[];}catch{return [];}}
function rowsFor(match){return [...(markets?.matches?.[match.id]||[]),...manualRows(match)].filter(validMarket);}
function prices(row){return Object.entries(row.prices).map(([k,v])=>(SELECTIONS[k]||k)+' '+v.toFixed(2)).join(' · ');}
function quoteTable(rows){
  return rows.length?'<div class="table-wrap"><table><thead><tr><th>机构 / 盘口</th><th>时点</th><th>盘口条件</th><th>十进制赔率</th><th>来源 / 时间</th></tr></thead><tbody>'+rows.map(q=>'<tr><td>'+esc(q.provider)+'<small>'+MARKET_NAMES[q.market]+'</small></td><td>'+PHASE_NAMES[q.phase]+(q.manual?'<small>个人录入</small>':'')+'</td><td>'+esc(q.line??'—')+'</td><td>'+esc(prices(q))+'</td><td>'+ (q.manual?'个人记录，仅保存在本浏览器':sourceLink(q.source,q.via||'来源'))+'<small>'+(q.quotedAt?'报价 '+esc(timeText(q.quotedAt)):'采集 '+esc(timeText(q.fetchedAt)))+'</small></td></tr>').join('')+'</tbody></table></div>':'<div class="empty">这个市场还没有可核对的报价。可在下方补充个人记录。</div>';
}
export function mountMarkets(target,match){
  let selected='90-minute-1x2';
  target.innerHTML='<div class="section-head"><h2>盘口、开始与最后赔率</h2></div><div class="tabs market-tabs">'+Object.entries(MARKET_NAMES).map(([k,v])=>'<button type="button" data-market="'+k+'">'+v+'</button>').join('')+'</div><div id="market-quotes"></div><p class="note">让球数按主队视角，大／小球按全场90分钟总进球。开始赔率只用于来源明确标为开盘的报价；历史表的早期报价另列。比分市场尚无稳定公开数据时，保留为空或使用个人录入。</p><section><h3>赔率变化分析</h3><div id="market-analysis" class="research-summary"></div><div id="market-moves"></div></section><details class="manual-market"><summary>补充个人盘口记录</summary><form id="market-form"><div class="field-row"><label>机构<input name="provider" required maxlength="80" placeholder="报价机构名称"></label><label>报价时点<select name="phase"><option value="opening">开始赔率</option><option value="latest">最新赔率</option><option value="closing">最后赔率</option></select></label><label>报价时间<input name="quotedAt" type="datetime-local" required></label></div><div id="market-inputs"></div><p class="form-error" role="alert"></p><button class="button secondary">保存到本机</button></form></details>';
  function paint(){
    if(!target.isConnected)return;
    const rows=rowsFor(match),filtered=rows.filter(q=>q.market===selected);
    target.querySelectorAll('[data-market]').forEach(b=>b.classList.toggle('active',b.dataset.market===selected));
    target.querySelector('#market-quotes').innerHTML=quoteTable(filtered);
    target.querySelector('#market-analysis').innerHTML=movementSummary(filtered).map(p=>'<p>'+esc(p)+'</p>').join('');
    const history=(markets?.history?.[match.id]||[]).filter(q=>q.market===selected&&validMarket(q));
    target.querySelector('#market-moves').innerHTML=history.length?'<details><summary>逐次变化记录（'+history.length+'次）</summary>'+quoteTable(history)+'</details>':'<p class="note">尚无逐次变化记录；系统从首次采集后持续记录，不能补造采集前的过程。</p>';
  }
  function inputs(){
    const keys=selected==='90-minute-1x2'?['H','D','A']:selected==='asian-handicap'?['H','A']:selected==='total-goals'?['O','U']:['score'];
    target.querySelector('#market-inputs').innerHTML='<div class="field-row">'+(['asian-handicap','total-goals'].includes(selected)?'<label>盘口线（让球按主队）<input name="line" type="number" step=".25" min="'+(selected==='total-goals'?0:-20)+'" max="20" required></label>':'')+(selected==='correct-score'?'<label>比分（主:客）<input name="score" required pattern="[0-9]{1,2}:[0-9]{1,2}" placeholder="2:1"></label>':'')+keys.map(k=>'<label>'+(SELECTIONS[k]||'该比分')+'赔率<input name="price-'+k+'" type="number" min="1.001" max="10000" step=".001" required></label>').join('')+'</div>';
  }
  target.querySelectorAll('[data-market]').forEach(b=>b.addEventListener('click',()=>{selected=b.dataset.market;inputs();paint();}));
  target.querySelector('#market-form').addEventListener('submit',event=>{
    event.preventDefault();const form=event.currentTarget,value=new FormData(form),prices={};
    for(const [key,v] of value)if(key.startsWith('price-'))prices[key==='price-score'?value.get('score'):key.slice(6)]=Number(v);
    try{const row=manualMarket({market:selected,provider:value.get('provider'),phase:value.get('phase'),quotedAt:new Date(value.get('quotedAt')).toISOString(),line:value.has('line')?Number(value.get('line')):null,prices});const prior=manualRows(match);if(prior.length>=300)throw Error('这场比赛已有300条个人记录。');localStorage.setItem(storageKey(match),JSON.stringify([...prior,row]));form.querySelector('.form-error').textContent='已保存到本浏览器。';paint();}
    catch(error){form.querySelector('.form-error').textContent=error.message;}
  });
  inputs();paint();return paint;
}
