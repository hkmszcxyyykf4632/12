import {api} from './api.mjs';
import {main,esc,pageHeading} from './ui.mjs';
import {portrait} from './portraits.mjs';
import {table,val,stamp,placeBadge,racingNav,racingJson} from './racing-ui.mjs';

export function renderHorseProfile(id){
  const controller=new AbortController();let retry,attempts=0;
  main.innerHTML=pageHeading('马匹档案','读取照片、血统与历季往绩。')+racingNav('horses')+'<div id="horse-detail" class="loading">正在读取马匹资料…</div>';
  async function load(){
    try{
      const [h,directory]=await Promise.all([api('/api/racing/horses/'+encodeURIComponent(id),{signal:controller.signal,timeout:45000}),racingJson('directory.json',controller.signal).catch(()=>({horses:[]}))]);
      if(controller.signal.aborted)return;
      if(h.pending&&attempts++<5){retry=setTimeout(load,3000);return;}
      if(!h.profile)throw Error(h.message||'马匹档案正在整理，请稍后重试。');
      const p=h.profile,b=h.pedigree||{},entry=directory.horses?.find(x=>x.id===id),trainer=entry?.trainer||h.trainer,owner=p['馬主'];
      const records=h.records||[],starts=records.filter(r=>!r.withdrawn),wins=starts.filter(r=>r.place===1).length,top3=starts.filter(r=>r.place>=1&&r.place<=3).length;
      main.innerHTML=racingNav('horses')+`<a class="back" href="#/horses">← 马匹资料</a><div class="horse-profile-hero">${portrait(h.photo,h.name,'horse',true)}<div><span class="eyebrow">HONG KONG RACING · ${esc(h.brand)}</span><h1>${esc(h.name)}</h1><p>${esc(p['出生地 / 馬齡']||'')} · ${esc(p['毛色 / 性別']||'')}</p><div class="horse-connections">练马师 ${trainer?.id?`<a href="#/horses/trainer/${encodeURIComponent(trainer.id)}">${esc(trainer.name)}</a>`:val(p['練馬師'])}<br>马主 ${owner?`<a href="#/horses/owner/${encodeURIComponent(owner)}">${esc(owner)}</a>`:'待更新'}</div></div><div class="horse-rating"><span>现时评分</span><strong>${val(entry?.rating??p['現時評分'])}</strong><small>季初 ${val(p['季初評分'])}</small></div></div><div class="racing-kpis"><div><span>已收录出赛</span><strong>${starts.length}</strong></div><div><span>头马 / 前三</span><strong>${wins} / ${top3}</strong></div><div><span>胜出率</span><strong>${starts.length?(100*wins/starts.length).toFixed(1)+'%':'—'}</strong></div><div><span>生涯冠－亚－季－出赛</span><strong>${val(p['冠-亞-季-總出賽次數'])}</strong></div><div><span>生涯奖金（港元）</span><strong>${val(p['總獎金'])}</strong></div></div><nav class="racing-jumps"><a href="#horse-records">历次往绩</a><a href="#horse-suitability">场地表现</a><a href="#horse-pedigree">血统资料</a></nav><section id="horse-records"><div class="section-head"><h2>历次往绩</h2><span class="note">最近比赛在前 · ${records.length} 条记录</span></div><div class="toolbar"><label>马季<select id="history-season"><option value="">全部马季</option>${[...new Set(records.map(r=>r.season).filter(Boolean))].map(s=>`<option>${esc(s)}</option>`).join('')}</select></label><label>马场<select id="history-course"><option value="">全部马场</option><option>沙田</option><option>跑马地</option></select></label><label>跑道<select id="history-surface"><option value="">全部跑道</option><option>草地</option><option>全天候跑道</option></select></label><label>途程<select id="history-distance"><option value="">全部途程</option>${[...new Set(records.map(r=>r.distance).filter(Boolean))].sort((a,b)=>a-b).map(d=>`<option value="${d}">${d} 米</option>`).join('')}</select></label><button class="button secondary compact" id="history-reset">重置</button></div><p class="note" id="history-summary"></p><div id="history-table"></div><div class="toolbar" id="history-pagination"></div></section><section id="horse-suitability"><h2>场地与途程表现</h2><div class="racing-suitability">${Object.entries(h.suitability||{}).map(([key,rows])=>`<div><h3>${{course:'马场',surface:'跑道',distance:'途程（米）',going:'场地状况'}[key]}</h3>${table(['条件','出赛','头马','前三','胜出率'],rows.map(r=>[esc(r.label)+(r.lowSample?'<small>少于 5 场</small>':''),r.starts,r.wins,r.top3,(100*r.wins/r.starts).toFixed(1)+'%']))}</div>`).join('')}</div></section><section id="horse-pedigree"><h2>血统与背景</h2><div class="racing-pedigree">${[['父系',b.sire],['母系',b.dam],['外祖父',b.damsire]].map(([k,v])=>`<div><span>${k}</span><strong>${val(v)}</strong></div>`).join('')}</div><dl class="identity-grid">${Object.entries(p).filter(([k])=>!['父系','母系','外祖父','練馬師','馬主'].includes(k)).map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${val(v)}</dd></div>`).join('')}</dl></section><p class="note">香港赛马会公开资料 · ${esc(h.coverage)} · 更新 ${stamp(h.updatedAt)}。赔率为该仗赛后公布的独赢赔率；负磅、马匹体重以磅列示。${h.message?esc(h.message):''}</p><dialog class="race-record-dialog" id="record-dialog"><div id="record-content"></div><button class="button" id="record-close">关闭详情</button></dialog>`;
      let page=0;
      const filters=['season','course','surface','distance'];
      function paintHistory(){
        const filtered=records.map((r,i)=>({...r,index:i})).filter(r=>filters.every(key=>{const value=main.querySelector('#history-'+key).value;return !value||String(r[key])===value;}));
        const sample=filtered.filter(r=>!r.withdrawn),victories=sample.filter(r=>r.place===1).length;
        const pages=Math.max(1,Math.ceil(filtered.length/25));page=Math.min(page,pages-1);
        main.querySelector('#history-summary').textContent=`筛选后 ${sample.length} 次出赛，${victories} 次头马，${sample.filter(r=>r.place>=1&&r.place<=3).length} 次前三。点击「本仗详情」直接查看完整记录。`;
        main.querySelector('#history-table').innerHTML=table(['日期 / 场次','名次','马场 / 跑道','途程 / 场地','班次 / 评分','档位','骑师','负磅','独赢','距头马 / 时间','详情'],filtered.slice(page*25,page*25+25).map(r=>[`${esc(r.date)}<small>${r.raceNo?'第 '+esc(r.raceNo)+' 场':''}</small>`,placeBadge(r),`${esc(r.course)}<small>${esc(r.surface)}</small>`,`${val(r.distance)} 米<small>${esc(r.going)}</small>`,`${val(r.class)} / ${val(r.rating)}`,val(r.draw),esc(r.jockey),val(r.weight),`<strong class="race-price">${val(r.winOdds)}</strong>`,`${val(r.margin)}<small>${val(r.finishTime)}</small>`,`<button class="button quiet compact" data-history-record="${r.index}">本仗详情</button>`]));
        const pager=main.querySelector('#history-pagination');pager.innerHTML=`<span>第 ${page+1} / ${pages} 页</span><button class="button secondary compact" data-prev ${page===0?'disabled':''}>上一页</button><button class="button secondary compact" data-next ${page>=pages-1?'disabled':''}>下一页</button>`;
        pager.querySelector('[data-prev]').onclick=()=>{page--;paintHistory();};pager.querySelector('[data-next]').onclick=()=>{page++;paintHistory();};
        main.querySelectorAll('[data-history-record]').forEach(button=>button.onclick=()=>{
          const r=records[Number(button.dataset.historyRecord)],dialog=main.querySelector('#record-dialog');
          main.querySelector('#record-content').innerHTML=`<span class="eyebrow">${esc(h.name)} · 本仗往绩</span><h2>${esc(r.date)} ${r.raceNo?'第 '+esc(r.raceNo)+' 场':''}</h2><div class="record-result">${placeBadge(r)}<span>${esc(r.track)} · ${val(r.distance)} 米 · ${esc(r.going)}</span></div><dl class="identity-grid">${[['骑师',r.jockey],['练马师',r.trainer],['班次 / 评分',`${r.class} / ${r.rating??'—'}`],['档位',r.draw],['负磅',r.weight],['马匹体重',r.bodyWeight],['距头马',r.margin],['完成时间',r.finishTime],['沿途走位',r.running],['装备',r.equipment],['赛后独赢赔率',r.winOdds]].map(([k,v])=>`<div><dt>${k}</dt><dd>${val(v)}</dd></div>`).join('')}</dl>`;dialog.showModal();
        });
      }
      filters.forEach(key=>main.querySelector('#history-'+key).onchange=()=>{page=0;paintHistory();});
      main.querySelector('#history-reset').onclick=()=>{filters.forEach(key=>main.querySelector('#history-'+key).value='');page=0;paintHistory();};
      main.querySelector('#record-close').onclick=()=>main.querySelector('#record-dialog').close();
      main.querySelectorAll('.racing-jumps a').forEach(a=>a.onclick=e=>{e.preventDefault();main.querySelector(a.getAttribute('href')).scrollIntoView({behavior:'smooth'});});
      paintHistory();
    }catch(error){if(!controller.signal.aborted)main.innerHTML=pageHeading('马匹档案','','<a href="#/horses">返回马匹资料</a>')+`<div class="empty">${esc(error.message)}</div>`;}
  }
  load();return()=>{controller.abort();clearTimeout(retry);};
}
