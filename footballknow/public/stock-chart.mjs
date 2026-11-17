import {esc,sourceLink} from './ui.mjs';
import {figure,finite} from './finance-core.mjs';
import {technicalWindow,technicalScale,volumeUnit} from './stock-technicals.mjs';

const compact=value=>!finite(value)?'—':value>=1e8?figure(value/1e8,2)+'亿':value>=1e4?figure(value/1e4,2)+'万':figure(value,0);
const price=value=>figure(value,finite(value)&&Math.abs(value)<.1?4:finite(value)&&Math.abs(value)<1?3:2);

export function renderStockChart(target,history,range=90,options={ma5:true,ma10:true}){
  const rows=technicalWindow(history?.bars,range),scale=technicalScale(rows);
  if(!scale){target.innerHTML='<div class="empty">历史日线正在同步，取得开高低收资料后显示阴阳烛。</div>';return;}
  const left=68,right=914,top=22,bottom=282,volumeTop=330,volumeBottom=416,step=(right-left)/rows.length;
  const x=i=>left+(i+.5)*step,y=value=>bottom-(value-scale.low)/(scale.high-scale.low)*(bottom-top),bodyWidth=Math.max(1.2,Math.min(12,step*.64));
  const unit=volumeUnit(history),currency=history.currency||'',fixed=value=>value.toFixed(2);
  const ticks=Array.from({length:5},(_,i)=>{const value=scale.high-i*(scale.high-scale.low)/4,py=y(value);return `<line class="chart-grid" x1="${left}" x2="${right}" y1="${fixed(py)}" y2="${fixed(py)}"/><text x="${left-10}" y="${fixed(py+4)}" text-anchor="end">${price(value)}</text>`;}).join('');
  function maPath(key){let drawing=false,path='';for(let i=0;i<rows.length;i++){const value=rows[i][key];if(!finite(value)){drawing=false;continue;}path+=(drawing?'L':'M')+fixed(x(i))+','+fixed(y(value));drawing=true;}return path;}
  const candles=rows.map((row,i)=>{
    if(!finite(row.close))return '';
    if(!row.candle)return `<circle class="chart-close-only" cx="${fixed(x(i))}" cy="${fixed(y(row.close))}" r="2.5"/>`;
    const up=row.close>=row.open,bodyTop=y(Math.max(row.open,row.close)),bodyHeight=Math.max(1,Math.abs(y(row.open)-y(row.close)));
    return `<g class="${up?'candle-up':'candle-down'}"><line x1="${fixed(x(i))}" x2="${fixed(x(i))}" y1="${fixed(y(row.high))}" y2="${fixed(y(row.low))}"/><rect x="${fixed(x(i)-bodyWidth/2)}" y="${fixed(bodyTop)}" width="${fixed(bodyWidth)}" height="${fixed(bodyHeight)}"/></g>`;
  }).join('');
  const volumes=rows.map((row,i)=>{if(row.volume===null)return '';const height=scale.volumeMax?row.volume/scale.volumeMax*(volumeBottom-volumeTop):0;return `<rect class="volume-bar ${row.candle?(row.close>=row.open?'candle-up':'candle-down'):'volume-neutral'}" x="${fixed(x(i)-bodyWidth/2)}" y="${fixed(volumeBottom-height)}" width="${fixed(bodyWidth)}" height="${fixed(height)}"/>`;}).join('');
  const dates=[...new Set([0,Math.floor((rows.length-1)/2),rows.length-1])].map((i,n)=>`<text x="${n===0?left:n===2?right:x(i)}" y="443" text-anchor="${n===0?'start':n===2?'end':'middle'}">${rows[i].date}</text>`).join('');
  target.innerHTML=`<div class="stock-technical-chart"><div class="stock-chart-controls"><span>日线 · ${rows.length} 个交易日</span><label class="ma5-key"><input type="checkbox" data-ma="ma5" ${options.ma5?'checked':''}> MA5 · 5日均线</label><label class="ma10-key"><input type="checkbox" data-ma="ma10" ${options.ma10?'checked':''}> MA10 · 10日均线</label><span class="candle-legend"><i class="up-key"></i>阳烛 <i class="down-key"></i>阴烛</span></div><div class="stock-chart-readout" role="status" aria-live="off"></div><div class="stock-chart-scroll"><svg class="stock-candles" viewBox="0 0 940 460" role="img" tabindex="0" aria-label="日线阴阳烛、5日和10日移动平均线及成交量；左右方向键查看日期">${ticks}<g>${candles}</g><path class="stock-ma5" d="${maPath('ma5')}" style="display:${options.ma5?'':'none'}"/><path class="stock-ma10" d="${maPath('ma10')}" style="display:${options.ma10?'':'none'}"/><text x="${left}" y="313">成交量（${esc(unit)}）</text><text x="${right}" y="313" text-anchor="end">${compact(scale.volumeMax)}</text><line class="chart-grid" x1="${left}" x2="${right}" y1="${volumeBottom}" y2="${volumeBottom}"/>${volumes}<line data-chart-crosshair class="chart-crosshair" x1="${fixed(x(rows.length-1))}" x2="${fixed(x(rows.length-1))}" y1="${top}" y2="${volumeBottom}"/>${dates}</svg></div><label class="stock-date-slider">查看交易日<input type="range" min="0" max="${rows.length-1}" value="${rows.length-1}" aria-label="查看交易日"><span data-chart-date></span></label></div><p class="note">${sourceLink(history.source,history.provider)} · ${esc(currency)} · ${history.adjustment==='forward'?'前复权日线':'来源日线价格'}。MA5／MA10 按最近 5／10 个交易日的收盘价计算，与阴阳烛使用同一价格口径。${rows.some(row=>!row.candle)?'缺少开高低资料的日期仅显示收盘点。':''}${unit==='来源单位'?'成交量沿用来源数值，未换算成股数。':''}<br>资料截至 ${esc(rows.at(-1).date)}；采集 ${esc(history.updatedAt?new Date(history.updatedAt).toLocaleString('zh-CN'):'时间待提供')}。当日尚未收市时，日线仍会变化。</p>`;
  const svg=target.querySelector('.stock-candles'),slider=target.querySelector('input[type="range"]'),crosshair=target.querySelector('[data-chart-crosshair]');
  let selected=rows.length-1;
  function select(index){
    selected=Math.max(0,Math.min(rows.length-1,index));const row=rows[selected];
    target.querySelector('.stock-chart-readout').innerHTML=`<strong>${row.date}</strong>`+[['开',row.open],['高',row.high],['低',row.low],['收',row.close],['MA5',row.ma5],['MA10',row.ma10]].map(([label,value])=>`<span class="${label==='MA5'?'ma5-key':label==='MA10'?'ma10-key':''}">${label} <b>${price(value)}</b></span>`).join('')+`<span>量 <b>${compact(row.volume)}</b> ${esc(unit)}</span>`;
    crosshair.setAttribute('x1',fixed(x(selected)));crosshair.setAttribute('x2',fixed(x(selected)));
    slider.value=String(selected);slider.setAttribute('aria-valuetext',row.date+'，收盘 '+price(row.close));target.querySelector('[data-chart-date]').textContent=row.date;
  }
  function point(event){const rect=svg.getBoundingClientRect(),position=(event.clientX-rect.left)/rect.width*940;select(Math.floor((position-left)/step));}
  svg.addEventListener('pointermove',point);svg.addEventListener('click',point);
  svg.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();select(event.key==='Home'?0:event.key==='End'?rows.length-1:selected+(event.key==='ArrowLeft'?-1:1));}});
  slider.addEventListener('input',()=>select(Number(slider.value)));
  target.querySelectorAll('[data-ma]').forEach(input=>input.addEventListener('change',()=>{options[input.dataset.ma]=input.checked;target.querySelector('.stock-'+input.dataset.ma).style.display=input.checked?'':'none';}));
  select(selected);
}
