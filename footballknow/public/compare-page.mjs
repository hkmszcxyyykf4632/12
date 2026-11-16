import {data,standings} from './repository.mjs';
import {main,esc,monogram,pageHeading,matchTable,formRun} from './ui.mjs';
import {league} from './league.mjs';
import {comparisonRows} from './insights.mjs';
import {headToHead} from './rankings-core.mjs';

const format=(value,digits)=>digits?value.toFixed(digits):String(value);

function body(a,b) {
  if(a.id===b.id)return '<div class="empty">请选择两支不同的球队。</div>';
  const rowA=standings?.entries.find(r=>r.teamId===a.id),rowB=standings?.entries.find(r=>r.teamId===b.id);
  const meetings=headToHead(data.matches,a.name,b.name,'9999-12-31');
  const tally=meetings.reduce((sum,m)=>{const winner=m.result==='D'?'draw':(m.result==='H')===(m.home===a.name)?'a':'b';sum[winner]++;return sum;},{a:0,b:0,draw:0});
  const head=(t,row)=>`<a href="#/team/${t.id}">${monogram(t)}<div><strong>${esc(t.cn)}</strong><small>${row?`第 ${row.rank} 名 · ${row.points} 分`:esc(t.name)}</small><div class="form-run" aria-label="最近五场，最新在左">${formRun(t)}</div></div></a>`;
  return `<div class="compare-head">${head(a,rowA)}${head(b,rowB)}</div>
    ${rowA&&rowB?`<div class="compare-rows">${comparisonRows(rowA,rowB).map(r=>`<div class="compare-row"><b class="${r.lead==='left'?'lead':''}">${format(r.left,r.digits)}</b><div class="compare-bar left ${r.lead==='left'?'lead':''}"><i style="width:${r.leftShare*100}%"></i></div><span>${r.label}</span><div class="compare-bar ${r.lead==='right'?'lead':''}"><i style="width:${r.rightShare*100}%"></i></div><b class="${r.lead==='right'?'lead':''}">${format(r.right,r.digits)}</b></div>`).join('')}</div><p class="note">数据为 ${esc(data.season)} ${league.name}${league.id==='ucl'?'联赛阶段':''}积分榜。绿色表示该项占优；排名、负场与失球以数值小为优。</p>`
      :'<div class="empty">积分榜正在同步，稍后会显示逐项对比。</div>'}
    <div class="section-head"><h2>交锋记录</h2><p>${meetings.length?`已收录最近 ${meetings.length} 场：${esc(a.cn)} ${tally.a} 胜，${tally.draw} 平，${esc(b.cn)} ${tally.b} 胜`:''}</p></div>
    ${meetings.length?matchTable(meetings):'<div class="empty">已收录的比赛中没有这两队的交锋。</div>'}`;
}

export function renderCompare(first,second) {
  const pick=(value,fallback)=>data.teams.find(t=>t.id===Number(value))||fallback;
  const ranked=standings?.entries.map(r=>data.teams.find(t=>t.id===r.teamId)).filter(Boolean)||[];
  let a=pick(first,ranked[0]||data.teams[0]),b=pick(second,ranked[1]||data.teams[1]);
  const options=chosen=>data.teams.map(t=>`<option value="${t.id}" ${t.id===chosen.id?'selected':''}>${esc(t.cn)}</option>`).join('');
  main.innerHTML=`${pageHeading('球队对比',`选择两支${league.name}球队，逐项比较本赛季数据和交锋记录。`)}
    <div class="compare-pick"><label>球队一<select id="compare-a">${options(a)}</select></label><span class="versus">vs</span><label>球队二<select id="compare-b">${options(b)}</select></label></div>
    <div id="compare-body"></div>`;
  const update=()=>{const target=main.querySelector('#compare-body');if(target)target.innerHTML=body(a,b);};
  const choose=()=>{
    a=pick(main.querySelector('#compare-a').value,a);b=pick(main.querySelector('#compare-b').value,b);
    window.history.replaceState(null,'',`${location.pathname}${location.search}#/compare/${a.id}/${b.id}`);update();
  };
  main.querySelector('#compare-a').addEventListener('change',choose);
  main.querySelector('#compare-b').addEventListener('change',choose);
  update();return update;
}
