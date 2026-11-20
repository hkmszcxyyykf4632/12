import {main,esc,pageHeading} from './ui.mjs';
import {portrait} from './portraits.mjs';
import {table,horseLink,classes,classText,racingNav,racingJson,stamp,val} from './racing-ui.mjs';

export function renderHorseDirectory(mode='trainer',selected=''){
  const controller=new AbortController();mode=mode==='owner'?'owner':'trainer';
  try{selected=decodeURIComponent(selected);}catch{selected='';}
  let data={},query='',group='0',page=0;
  main.innerHTML=pageHeading('马匹资料','按练马师或马主浏览，查看评分、血统、照片与历季往绩。')+racingNav('horses')+'<div id="horse-directory" class="loading">正在读取马匹目录…</div>';
  main.querySelector('#horse-directory').insertAdjacentHTML('beforebegin','<p><a class="button secondary" href="#/horse-going">按场地表现分类：黏地、软烂地、湿泥地 →</a></p>');
  function paint(){
    const container=main.querySelector('#horse-directory');if(!container)return;
    const all=data.horses||[],key=h=>mode==='owner'?h.owner||'待更新':h.trainer?.id||'pending';
    const inGroup=selected?all.filter(h=>key(h)===selected):all;
    const title=selected?(mode==='owner'?selected:inGroup[0]?.trainer?.name||'待更新'):'';
    container.className='';container.innerHTML=`<div class="tabs"><a class="${mode==='trainer'?'active':''}" href="#/horses/trainer">按练马师</a><a class="${mode==='owner'?'active':''}" href="#/horses/owner">按马主</a></div>${selected?`<div class="stable-heading">${mode==='trainer'?portrait(inGroup[0]?.trainer?.photo,title,'person',true):'<span class="owner-seal">马主</span>'}<div><a href="#/horses/${mode}">← 全部${mode==='owner'?'马主':'练马师'}</a><h2>${esc(title)}</h2><p>${inGroup.length} 匹现役马匹</p></div></div>`:''}<div class="toolbar"><label class="search-field">${selected?'搜索本组马匹':'搜索马匹、练马师或马主'}<input id="directory-search" type="search" value="${esc(query)}" placeholder="输入中文名字或马匹烙号"></label><label>评分班次<select id="horse-class">${classes.map((name,i)=>`<option value="${i}" ${String(i)===group?'selected':''}>${name}</option>`).join('')}</select></label><span class="note">共 ${all.length} 匹 · 已有马主资料 ${data.ownersKnown||0} 匹</span></div><div id="directory-content"></div><div id="directory-pager" class="toolbar"></div><p class="note">${esc(data.classMethod||'')}<br>马房目录更新 ${stamp(data.stableUpdatedAt)} · 资料整理 ${stamp(data.updatedAt)}</p>`;
    container.querySelector('#directory-search').oninput=e=>{query=e.target.value;page=0;paintContent();};
    container.querySelector('#horse-class').onchange=e=>{group=e.target.value;page=0;paintContent();};
    function paintContent(){
      let list=inGroup.filter(h=>(group==='0'||String(h.classGroup??6)===group)&&[h.name,h.brand,h.owner,h.trainer?.name].join(' ').toLowerCase().includes(query.trim().toLowerCase()));
      const target=container.querySelector('#directory-content'),pager=container.querySelector('#directory-pager');
      if(!selected&&!query){
        const groups=new Map();for(const h of list){const k=key(h);if(!groups.has(k))groups.set(k,{id:k,name:mode==='owner'?k:h.trainer?.name||'待更新',photo:h.trainer?.photo,horses:[]});groups.get(k).horses.push(h);}
        const rows=[...groups.values()].sort((a,b)=>b.horses.length-a.horses.length||a.name.localeCompare(b.name,'zh-HK'));
        const pages=Math.max(1,Math.ceil(rows.length/36));page=Math.min(page,pages-1);
        target.innerHTML=`<div class="stable-grid">${rows.slice(page*36,page*36+36).map(g=>`<a class="stable-card" href="#/horses/${mode}/${encodeURIComponent(g.id)}">${mode==='trainer'?portrait(g.photo,g.name):'<span class="owner-seal">主</span>'}<span><strong>${esc(g.name)}</strong><small>${g.horses.length} 匹 · ${[1,2,3,4,5].filter(c=>g.horses.some(h=>h.classGroup===c)).map(c=>classes[c]).join(' / ')||'待评分'}</small></span><span aria-hidden="true">→</span></a>`).join('')}</div>`;
        paginate(rows.length,pages,'组');
      }else{
        list.sort((a,b)=>(b.rating??-1)-(a.rating??-1)||a.brand.localeCompare(b.brand));
        const pages=Math.max(1,Math.ceil(list.length/30));page=Math.min(page,pages-1);
        target.innerHTML=table(['马匹','评分 / 班次','练马师','马主','近六仗（最近在左）','往绩'],list.slice(page*30,page*30+30).map(h=>[horseLink(h,true),`<strong class="rating-number">${val(h.rating)}</strong><small>${classText(h)}</small>`,`<a href="#/horses/trainer/${encodeURIComponent(h.trainer?.id||'pending')}">${esc(h.trainer?.name||'待更新')}</a>`,`<a href="#/horses/owner/${encodeURIComponent(h.owner||'待更新')}">${esc(h.owner||'待更新')}</a>`,(h.recent||[]).map(x=>`<span class="form-chip ${parseInt(x)===1?'won':''}">${esc(x)}</span>`).join('')||'—',`<a href="#/horse/${h.id}">${h.recordCount||0} 场 · 查看档案 →</a>`]));
        paginate(list.length,pages,'匹');
      }
      function paginate(total,pages,unit){pager.innerHTML=`<span>${total} ${unit} · 第 ${page+1} / ${pages} 页</span><button class="button secondary compact" data-prev ${page===0?'disabled':''}>上一页</button><button class="button secondary compact" data-next ${page>=pages-1?'disabled':''}>下一页</button>`;pager.querySelector('[data-prev]').onclick=()=>{page--;paintContent();};pager.querySelector('[data-next]').onclick=()=>{page++;paintContent();};}
    }
    paintContent();
  }
  racingJson('directory.json',controller.signal).then(value=>{if(!controller.signal.aborted){data=value;paint();}}).catch(error=>{if(!controller.signal.aborted)main.querySelector('#horse-directory').innerHTML=`<div class="empty">${esc(error.message)}</div>`;});
  return()=>controller.abort();
}
