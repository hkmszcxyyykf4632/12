import {main,esc,pageHeading,sourceLink} from './ui.mjs';
import {racingJson,racingNav,table,stamp,horseLink} from './racing-ui.mjs';
import {portrait} from './portraits.mjs';
import {families,ancestry,checkedAt} from './bloodlines-data.mjs';
import {familyHorses,horseBranches} from './bloodlines-core.mjs';

export function bloodlineLinks(horse){
  const matches=families.filter(f=>horseBranches(horse,f,ancestry).length);
  return `<p class="note">著名血统关联：${matches.length?matches.map(f=>`<a href="#/bloodlines/${f.id}">${esc(f.name)} · ${esc(f.ancestor)}</a>`).join(' ／ '):'此马的远祖关系尚未全部核对。'} <a href="#/bloodlines">浏览血统介绍与香港同系马 →</a></p>`;
}

export function renderBloodlines(initial){
  const controller=new AbortController();let family=families.find(f=>f.id===initial)||families[0],directory=null,branch='sire',query='',count=30;
  main.innerHTML=pageHeading('著名血统与香港马匹','从父亲、母父追溯代表血系，查看香港已收录的关联马匹。')+racingNav('bloodlines')+'<div id="bloodline-page" class="loading">正在核对香港马匹目录…</div>';
  function paint(){
    if(controller.signal.aborted)return;
    const target=main.querySelector('#bloodline-page');target.className='';
    target.innerHTML=`<div class="bloodline-tabs" role="group" aria-label="选择血统">${families.map(f=>`<button class="button secondary" data-family="${f.id}" aria-pressed="${f.id===family.id}">${esc(f.name)}</button>`).join('')}</div><article class="bloodline-intro"><h2>${esc(family.name)} <small>${esc(family.ancestor)}</small></h2><p>${esc(family.intro)}</p><p>${esc(family.focus)}</p>${sourceLink(family.source,'血统介绍来源')}</article><div class="bloodline-stats"><span><strong>${familyHorses(directory,family,ancestry,'sire').length}</strong>匹已核对父系关联</span><span><strong>${familyHorses(directory,family,ancestry,'damsire').length}</strong>匹已核对母父关联</span></div><div class="toolbar"><label>血缘路径<select id="bloodline-branch"><option value="sire">父系传承</option><option value="damsire">母父支系</option><option value="all">父系及母父</option></select></label><label class="search-field">搜索马名、父亲、练马师<input id="bloodline-search" type="search" value="${esc(query)}" placeholder="输入名称或烙号"></label></div><p id="bloodline-count" role="status"></p><div id="bloodline-results"></div><button class="button secondary" id="bloodline-more">显示更多马匹</button><details><summary>收录范围与血缘核对方法</summary><p>香港名单来自马会在册目录快照，最近同步 ${stamp(directory.updatedAt)}。父系及母父取自各马档案，远祖关系逐条链接牧场、拍卖机构或登记资料。祖先库核对日期 ${checkedAt}。</p><p>目前收录六个代表血系及部分已核对支线，并非完整族谱。未列入只表示现有关系链尚未连通，不代表该马一定没有这一祖先。同一匹马可以同时出现在父系、母父及更上游血系；人数不能直接相加。</p><p>沿“本马 ← 父亲 ← 祖先”阅读。母父路径会另外注明母亲；这些马属于同系，未必同父。</p>${sourceLink(directory.source,'香港马匹目录来源')}</details>`;
    target.querySelector('#bloodline-branch').value=branch;
    target.querySelectorAll('[data-family]').forEach(b=>b.onclick=()=>{family=families.find(f=>f.id===b.dataset.family);count=30;paint();});
    target.querySelector('#bloodline-branch').onchange=e=>{branch=e.target.value;count=30;draw();};
    target.querySelector('#bloodline-search').oninput=e=>{query=e.target.value;count=30;draw();};
    target.querySelector('#bloodline-more').onclick=()=>{count+=30;draw();};draw();
  }
  function draw(){
    const rows=familyHorses(directory,family,ancestry,branch,query);
    main.querySelector('#bloodline-count').textContent=`找到 ${rows.length} 匹，按现时评分排列。点击马名查看往绩、跑法和场地表现。`;
    main.querySelector('#bloodline-results').innerHTML=rows.length?table(['香港马匹','评分 / 班次','练马师 / 马主','已核对血缘路径'],rows.slice(0,count).map(({horse:h,branches})=>[
      `<div class="bloodline-identity">${portrait(h.photo,h.name,'horse')}${horseLink(h)}</div>`,`${h.rating??'—'} / ${h.classGroup?`第${h.classGroup}班`:'班次待定'}`,`${esc(h.trainer?.name||'—')}<small>${esc(h.owner||'—')}</small>`,
      branches.map(b=>`<div><strong>${b.branch==='sire'?'父系':'母父支系'}</strong><div class="bloodline-chain">${esc(h.name)} ← ${b.branch==='damsire'?`母亲 ${esc(h.pedigree.dam||'未收录')} ← `:''}${b.path.map((p,i)=>`${i?' ← ':''}${p.source?sourceLink(p.source,p.name):esc(p.name)}`).join('')}</div>${sourceLink(h.source,'本马父母资料')}</div>`).join('')])):'<div class="empty">此筛选范围暂未找到已核对的关联马匹。</div>';
    main.querySelector('#bloodline-more').hidden=count>=rows.length;
  }
  racingJson('directory.json',controller.signal).then(d=>{directory=d;paint();}).catch(e=>{if(!controller.signal.aborted)main.querySelector('#bloodline-page').textContent=e.message;});
  return()=>controller.abort();
}
