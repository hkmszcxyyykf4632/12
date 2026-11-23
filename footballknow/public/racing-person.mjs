import {main,esc,pageHeading} from './ui.mjs';
import {api} from './api.mjs';
import {portrait} from './portraits.mjs';
import {table,horseLink,val,stamp,classText,racingNav} from './racing-ui.mjs';
import {personHref} from './entity-links.mjs';
export function racingPersonLink(p,kind){const name=typeof p==='string'?p:p?.name,href=personHref(kind,p);return href?`<a class="entity-link" href="${esc(href)}">${esc(name||p.id)}</a>`:esc(name||'—');}
export function renderRacingPerson(kind,rawId){
 const controller=new AbortController();let id;try{id=decodeURIComponent(rawId||'');}catch{id='';}
 const label=({owner:'马主',trainer:'练马师',jockey:'骑师'})[kind];
 main.innerHTML=pageHeading(label?label+'档案':'人物档案','关联马匹、出赛记录与赛季成绩。')+'<div class="loading">正在读取人物资料…</div>';
 if(!label||!id){main.innerHTML='<div class="empty">档案编号不正确。<a href="#/horses">浏览马匹资料</a></div>';return()=>{};}
 api('/api/racing/person?kind='+kind+'&id='+encodeURIComponent(id),{signal:controller.signal}).then(d=>{
  if(controller.signal.aborted)return;
  const p=d.person,stats=Number.isFinite(p.numStarts),horses=d.horses||[],entries=d.entries||[];
  main.innerHTML=racingNav(kind==='owner'?'horses':'racing-rankings')+`<div class="entity-profile-head">${kind==='owner'?'<span class="owner-seal">马主</span>':portrait(p.photo,p.name,'person',true)}<div><span class="eyebrow">${label}档案</span><h1>${esc(p.name)}</h1><p>${esc(p.nameEn||'')}</p></div><a class="button secondary" href="${kind==='jockey'?'#/racing-rankings/jockeys':'#/horses/'+kind+'/'+encodeURIComponent(id)}">${kind==='jockey'?'骑师榜':'查看分类名单'} →</a></div>`+
  (stats?`<div class="racing-kpis">${[['本季排名',p.rank??'—'],['出赛',p.numStarts],['头马',p.numFirst],['前三',p.numFirst+p.numSecond+p.numThird],['胜出率',p.numStarts?(100*p.numFirst/p.numStarts).toFixed(1)+'%':'—']].map(([k,v])=>`<div><span>${k}</span><strong>${v}</strong></div>`).join('')}</div><p class="note">${esc(d.season)} 马季 · 香港本地成绩截至 ${esc(d.asOf||'—')} · 来源：香港赛马会骑练榜 · 更新 ${stamp(d.updatedAt)}</p>`:'')+
  `<section><div class="section-head"><h2>${kind==='jockey'?'已收录的策骑马匹':'现役关联马匹'}</h2><span>${horses.length} 匹</span></div><div class="toolbar"><label>搜索马匹<input id="person-horse-search" type="search" placeholder="马名或烙号"></label><label>评分班次<select id="person-class"><option value="">全部班次</option>${[1,2,3,4,5].map(c=>`<option value="${c}">第${'一二三四五'[c-1]}班</option>`).join('')}</select></label></div><div id="person-horses"></div><div id="person-pager" class="toolbar"></div></section>`+
  '<section><div class="section-head"><h2>出赛与赛果</h2><label>赛马日<select id="person-day"><option value="">全部已收录赛马日</option>'+[...new Set(entries.map(e=>e.race.date))].map(date=>`<option>${esc(date)}</option>`).join('')+'</select></label></div><div id="person-runs"></div></section><p class="note">'+esc(d.scope)+' 目录更新 '+stamp(d.directoryUpdatedAt)+'</p>';
  let page=0;
  function paintHorses(){const q=main.querySelector('#person-horse-search').value.toLowerCase(),group=main.querySelector('#person-class').value;
   const list=horses.filter(h=>(h.name+' '+h.brand).toLowerCase().includes(q)&&(!group||String(h.classGroup)===group)).sort((a,b)=>(b.rating??-1)-(a.rating??-1));
   page=Math.min(page,Math.max(0,Math.ceil(list.length/30)-1));
   main.querySelector('#person-horses').innerHTML=table(['马匹','评分 / 班次','练马师','马主'],list.slice(page*30,page*30+30).map(h=>[horseLink(h,true),val(h.rating)+'<small>'+classText(h)+'</small>',racingPersonLink(h.trainer,'trainer'),racingPersonLink(h.owner,'owner')]));
   main.querySelector('#person-pager').innerHTML=`<button class="button secondary compact" data-prev ${page===0?'disabled':''}>上一页</button><span>${page+1} / ${Math.max(1,Math.ceil(list.length/30))}</span><button class="button secondary compact" data-next ${(page+1)*30>=list.length?'disabled':''}>下一页</button>`;
   main.querySelector('[data-prev]').onclick=()=>{page--;paintHorses();};main.querySelector('[data-next]').onclick=()=>{page++;paintHorses();};
  }
  function paintRuns(){const day=main.querySelector('#person-day').value,rows=entries.filter(e=>!day||e.race.date===day);
   main.querySelector('#person-runs').innerHTML=table(['日期 / 场次','马匹','骑师','练马师','赛果','独赢赔率'],rows.map(({race:r,horse:h})=>[`<a href="#/race/${esc(r.id)}">${esc(r.date)}<small>${esc(r.courseName)} 第 ${val(r.raceNo)} 场</small></a>`,horseLink(h),racingPersonLink(h.jockey,'jockey'),racingPersonLink(h.trainer,'trainer'),h.withdrawn?'退出':r.resultOfficial?val(h.position||h.place):r.status==='cancelled'?'取消':r.status==='provisional'?'初步 '+val(h.position||h.place):r.date<new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Hong_Kong'})?'待公布赛果':'待赛',val(h.winOdds)]));
  }
  main.querySelector('#person-horse-search').oninput=()=>{page=0;paintHorses();};main.querySelector('#person-class').onchange=()=>{page=0;paintHorses();};main.querySelector('#person-day').onchange=paintRuns;paintHorses();paintRuns();
 }).catch(e=>{if(!controller.signal.aborted)main.innerHTML=pageHeading(label+'档案','')+`<div class="empty">${esc(e.message)} <a href="#/horses">浏览马匹资料</a></div>`;});
 return()=>controller.abort();
}
