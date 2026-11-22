import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {readFile} from 'node:fs/promises';
const dom=new JSDOM('<main id="main"></main>',{url:'http://localhost/'});
Object.assign(globalThis,{document:dom.window.document,window:dom.window,location:dom.window.location,localStorage:dom.window.localStorage});
const {dailyRows}=await import('../public/daily-core.mjs');
const {renderLive}=await import('../public/daily-page.mjs');
const {mountTeamSections}=await import('../public/team-sections.mjs');

test('one centre supports both daily and full-season schedules and keeps analysis collapsed',async()=>{
 const oldFetch=globalThis.fetch;
 globalThis.fetch=async url=>({ok:true,json:async()=>String(url).startsWith('/api/')?{matches:{}}:JSON.parse(await readFile(new URL('../public/'+String(url).replace(/^\.\//,''),import.meta.url),'utf8'))});
 const dispose=renderLive({leagueId:'epl'});
 try{
  for(let i=0;i<100&&document.querySelector('#live-feed-status').textContent.includes('正在读取');i++)await new Promise(r=>setTimeout(r,20));
  assert.equal(document.querySelector('h1').textContent,'比赛中心');
  assert.equal(document.querySelector('#season-filters').hidden,false);
  assert.equal(document.querySelector('#daily-date-controls').hidden,true);
  document.querySelector('#centre-period').value='all';
  document.querySelector('#centre-period').dispatchEvent(new dom.window.Event('change'));
  assert.ok(document.querySelectorAll('.live-match').length>0);
  assert.ok([...document.querySelectorAll('.centre-analysis')].every(d=>!d.open));
  const disclosure=document.querySelector('.centre-analysis');disclosure.open=true;
  document.querySelector('#daily-search').dispatchEvent(new dom.window.Event('input'));
  assert.equal(document.querySelector('.centre-analysis').open,true);
  document.querySelector('[data-centre-status="finished"]').click();
  assert.ok([...document.querySelectorAll('.live-match')].every(d=>d.classList.contains('is-finished')));
  document.querySelector('[data-centre-mode="day"]').click();
  assert.equal(document.querySelector('#season-filters').hidden,true);
  assert.equal(document.querySelector('#daily-date-controls').hidden,false);
 }finally{dispose();globalThis.fetch=oldFetch;}
});

test('season and team filters include archive results even when live feed is unavailable',()=>{
 const match={id:'old',competition:'英超',season:'2025/26',date:'2026-04-01',kickoff:'2026-04-01T12:00:00Z',home:'A',away:'B',finished:true,started:true,homeGoals:1,awayGoals:0};
 const feed={league:'epl',data:{season:'2026/27',teams:[{name:'A',cn:'甲'},{name:'B',cn:'乙'}],matches:[match]}};
 assert.equal(dailyRows(null,[feed],{date:'',competition:'league:epl',season:'2025/26',teamName:'A'}).length,1);
 assert.equal(dailyRows(null,[feed],{date:'',season:'2026/27'}).length,0);
});

test('team categories retain controls and support keyboard navigation',()=>{
 const root=document.querySelector('main');
 root.innerHTML='<nav aria-label="球队资料跳转"></nav>'+['calendar-section','matches-section','players-section','availability-section','team-position-gaps','season-section','team-handicap-trend','team-research','transfers-section','managers-section'].map(id=>`<section id="${id}"><input value="preserved"></section>`).join('');
 mountTeamSections(root,'<h2>概况</h2>');
 assert.equal(root.querySelectorAll('.team-panel:not([hidden])').length,1);
 assert.equal(root.querySelector('#team-panel-overview').hidden,false);
 root.querySelector('[data-team-tab="fixtures"]').click();
 assert.equal(root.querySelector('#team-panel-fixtures').hidden,false);
 assert.equal(root.querySelector('#calendar-section input').value,'preserved');
 root.querySelector('[data-team-tab="fixtures"]').dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
 assert.equal(root.querySelector('#team-panel-players').hidden,false);
 assert.equal(root.querySelector('[data-team-tab="players"]').getAttribute('aria-selected'),'true');
});
