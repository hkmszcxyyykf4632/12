import {api} from './api.mjs';
import {esc} from './ui.mjs';
import {scopedRecords} from './statistics-scope.mjs';
import {celebrations} from './prediction-stats-core.mjs';
export async function paintCelebrations(target){
 if(!target||target.dataset.loading==='true')return;
 target.dataset.loading='true';
 try{
  const [football,racing]=await Promise.allSettled(['football','racing'].map(x=>api('/api/statistics/'+x,{timeout:30000})));
  if(!target.isConnected)return;
  const items=celebrations(scopedRecords(football.status==='fulfilled'?football.value.records:[],'football'),scopedRecords(racing.status==='fulfilled'?racing.value.records:[],'racing'));
  const card=item=>`<a class="celebration-card" href="${esc(item.href)}"><span class="celebration-date">${esc(item.day)} · 成绩速报</span><strong>恭喜峰弈科技分析命中${esc(item.kind==='rate'?'率超八成 · '+item.title:item.title.replace('命中 ·','·'))}</strong><span>${esc(item.text)}</span><small>查看原预测及结算 →</small></a>`;
  target.innerHTML=items.length?`<section class="prediction-celebrations" aria-label="分析成绩庆祝"><div class="section-head"><h2>分析佳绩</h2><a href="#/football-statistics">足球统计</a><a href="#/racing-statistics">赛马统计</a></div><div class="celebration-grid">${items.slice(0,3).map(card).join('')}</div>${items.length>3?`<details><summary>更多已核实佳绩 · ${items.length-3} 条</summary><div class="celebration-grid">${items.slice(3).map(card).join('')}</div></details>`:''}<p class="note">仅展示已核实记录：整轮足球／赛马日命中率超过80%，或独赢派彩至少10倍、连赢至少50倍。倍数含本金；完整命中与未中记录均保留在统计页。</p></section>`:'';
 }finally{target.dataset.loading='false';}
}
