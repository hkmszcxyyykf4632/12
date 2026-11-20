import {main,esc,pageHeading,sourceLink} from './ui.mjs';
import {table,horseLink,racingNav,racingJson,stamp} from './racing-ui.mjs';

const percent=n=>Number.isFinite(n)?(n*100).toFixed(1)+'%':'—';
export function goingRows(horses,group,strongOnly=true){
  return horses.map(h=>({horse:h,stats:h.goingPerformance?.find(g=>g.group===group)})).filter(x=>x.stats?.starts>0&&(!strongOnly||x.stats.strong===true)).sort((a,b)=>b.stats.top3Rate-a.stats.top3Rate||b.stats.starts-a.stats.starts||a.horse.id.localeCompare(b.horse.id));
}
export function goingBlock(horse){
  const rows=(horse?.goingPerformance||[]).filter(r=>r.starts);
  return rows.length?table(['场地类别','出赛','头马 / 前三','胜率','前三率','统计结论'],rows.map(r=>[esc(r.label),r.starts,`${r.wins} / ${r.top3}`,percent(r.winRate),percent(r.top3Rate),r.strong?'表现较好':r.lowSample?'样本不足 5 场':'已有往绩'])):'<p class="note">该马暂无可核对的场地分类统计。</p>';
}
export function renderHorseGoing(){
  const controller=new AbortController();let data={},group='yielding',strong=true,query='',page=0;
  main.innerHTML=pageHeading('马匹场地表现','按草地黏地、软烂地和全天候湿泥地往绩寻找有经验的马匹。')+racingNav('horses')+`<div class="toolbar"><label>场地类别<select id="going-group"><option value="yielding">草地黏地</option><option value="soft">草地软 / 烂地</option><option value="wet">全天候湿泥地</option><option value="firm">草地好 / 快地</option><option value="dry">全天候干地</option></select></label><label>表现范围<select id="going-strength"><option value="strong">表现较好（至少 5 次）</option><option value="all">全部有往绩的马匹</option></select></label><label>马名 / 练马师<input type="search" id="going-search"></label></div><p id="going-count" class="note"></p><div id="going-table" class="loading">正在整理场地往绩…</div><div id="going-pager" class="toolbar"></div><p id="going-method" class="note"></p>`;
  function paint(){
    if(controller.signal.aborted)return;
    const rows=goingRows(data.horses||[],group,strong).filter(x=>[x.horse.name,x.horse.brand,x.horse.trainer?.name].join(' ').toLowerCase().includes(query)),pages=Math.max(1,Math.ceil(rows.length/30));page=Math.min(page,pages-1);
    main.querySelector('#going-count').textContent=`${rows.length} 匹符合条件 · 已整理 ${data.horses?.length||0} 匹。草地与全天候分开统计。`;
    const target=main.querySelector('#going-table');target.className='';
    target.innerHTML=rows.length?table(['马匹 / 练马师','出赛','头马','前三','胜率','前三率','最近该场地出赛','依据'],rows.slice(page*30,page*30+30).map(({horse:h,stats:s})=>[horseLink(h,true)+`<small>${esc(h.trainer?.name||'')}</small>`,s.starts,s.wins,s.top3,percent(s.winRate),percent(s.top3Rate),esc(s.lastDate),`<details><summary>${s.lowSample?'样本不足 5 场':'最近 '+s.records.length+' 场记录'}</summary>${s.records.map(r=>`<p>${esc(r.date)} · ${esc(r.course)} · ${esc(r.going)} · ${r.place?'第 '+r.place+' 名':'未列名次'} ${sourceLink(r.source,'赛果')}</p>`).join('')}</details>`])):'<div class="empty">目前没有符合该条件的马匹。可切换“全部有往绩”查看少量样本。</div>';
    main.querySelector('#going-method').innerHTML=esc(data.goingMethod||'')+'<br>前三率按前三名计算，不是位置派彩回报；资料截止各马已收录往绩。更新 '+stamp(data.updatedAt)+' · '+sourceLink(data.goingSource,'场地分组来源');
    const pager=main.querySelector('#going-pager');pager.innerHTML=`<button class="button secondary" data-prev ${page===0?'disabled':''}>上一页</button><span>${page+1} / ${pages}</span><button class="button secondary" data-next ${page===pages-1?'disabled':''}>下一页</button>`;pager.querySelector('[data-prev]').onclick=()=>{page--;paint();};pager.querySelector('[data-next]').onclick=()=>{page++;paint();};
  }
  main.querySelector('#going-group').onchange=e=>{group=e.target.value;page=0;paint();};main.querySelector('#going-strength').onchange=e=>{strong=e.target.value==='strong';page=0;paint();};main.querySelector('#going-search').oninput=e=>{query=e.target.value.trim().toLowerCase();page=0;paint();};
  racingJson('directory.json',controller.signal).then(v=>{data=v;paint();}).catch(e=>{if(!controller.signal.aborted)main.querySelector('#going-table').textContent=e.message;});return()=>controller.abort();
}
