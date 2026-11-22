export function foldResearch(target){
  if(!target)return;
  const states=new Map([...target.querySelectorAll('details[data-club-section]')].map(d=>[d.dataset.clubSection,d.open]));
  for(const section of [...target.children]){
    if(section.tagName!=='SECTION')continue;
    const detail=document.createElement('details'),summary=document.createElement('summary');
    detail.className='analysis-disclosure';detail.dataset.clubSection=section.id;detail.open=states.get(section.id)||false;
    summary.textContent=section.querySelector('h2')?.textContent||'详细资料';detail.append(summary);section.before(detail);detail.append(section);
  }
}
export function mountTeamSections(root,overview){
  const oldNav=root.querySelector('[aria-label="球队资料跳转"]');
  const nav=document.createElement('div');nav.className='team-section-tabs';nav.setAttribute('role','tablist');nav.setAttribute('aria-label','球队资料分类');
  oldNav.replaceWith(nav);
  const groups=[['overview','球队概况',[]],['fixtures','赛程与赛果',['calendar-section','matches-section']],['players','球员与伤停',['players-section','availability-section','team-position-gaps']],['performance','数据与盘路',['season-section','team-handicap-trend']],['background','背景与转会',['team-research','transfers-section','managers-section']]];
  const panels=new Map();let previous=nav;
  for(const [key,title,ids] of groups){
    const panel=document.createElement('section');panel.className='team-panel';panel.id='team-panel-'+key;panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby','team-tab-'+key);
    if(key==='overview')panel.innerHTML=overview;
    for(const id of ids){const section=root.querySelector('#'+id);if(section)panel.append(section);}
    previous.after(panel);previous=panel;panels.set(key,panel);
    const button=document.createElement('button');button.type='button';button.id='team-tab-'+key;button.textContent=title;button.dataset.teamTab=key;button.setAttribute('role','tab');button.setAttribute('aria-controls',panel.id);nav.append(button);
  }
  function select(key){
    for(const [id,panel] of panels)panel.hidden=id!==key;
    for(const b of nav.children){const active=b.dataset.teamTab===key;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;}
  }
  nav.addEventListener('click',e=>{const b=e.target.closest('[data-team-tab]');if(b)select(b.dataset.teamTab);});
  nav.addEventListener('keydown',e=>{
    const keys=groups.map(g=>g[0]),index=keys.indexOf(e.target.dataset.teamTab);if(index<0)return;
    const next=e.key==='ArrowRight'?(index+1)%keys.length:e.key==='ArrowLeft'?(index+keys.length-1)%keys.length:e.key==='Home'?0:e.key==='End'?keys.length-1:null;
    if(next!==null){e.preventDefault();select(keys[next]);nav.children[next].focus();}
  });
  select('overview');foldResearch(root.querySelector('#team-research'));
}
