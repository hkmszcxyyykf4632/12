import {data,refresh,findMatch,startPolling} from './repository.mjs';
import {storeProblem,STORAGE_KEY,reloadStore,reconcile} from './personal-store.mjs';
import {main,esc,toast} from './ui.mjs';
import {renderTeams,renderSources} from './pages.mjs';
import {renderHome} from './dashboard.mjs';
import {renderStatus} from './status-page.mjs';
import {renderCompare} from './compare-page.mjs';
import {bindTheme,bindDrawer,bindPalette,paintSync,startSyncIndicator} from './shell.mjs';
import {enhanceTables,bindTableTools} from './table-tools.mjs';
import {renderTeam} from './team-page.mjs';
import {renderSimulator,renderRecords,selectMatch,selectSavedOdds,settleRecord} from './simulator.mjs';
import {renderAdmin} from './admin.mjs';
import {renderAnalysis} from './analysis-page.mjs';
import {league} from './league.mjs';
import {renderRankings} from './rankings-page.mjs';
import {renderMatches,renderMatch,toggleFollow} from './matches-page.mjs';

document.querySelector('[data-league-team-label]').textContent=league.name+'球队';
document.querySelectorAll('[data-league]').forEach(link=>{const active=link.dataset.league===league.id;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','true');});

let disposePage=()=>{},updatePage=()=>{},stopPolling=()=>{},stopIndicator=()=>{};
const route=()=>location.hash.replace(/^#\/?/,'').split('/');
const routeKey=()=>`${league.id}:${route().join('/')}`;
bindTheme();bindPalette();bindTableTools(()=>`${league.name}-${route()[0]||'总览'}`);
const closeDrawer=bindDrawer();

function updateStatus() {
 if(!data)return;
 paintSync();
 document.querySelector('#update-label').textContent=`球队资料 ${new Date(data.updatedAt).toLocaleString('zh-CN')}`;
}

function recordsChanged() {
 if(route()[0]==='records'&&!main.querySelector('#records-update'))main.insertAdjacentHTML('afterbegin','<div class="notice" id="records-update">模拟记录已有更新。<button class="button quiet compact" data-refresh-records>刷新记录</button></div>');
}

export function updateView() {
 if(!data)return;
 try {if(reconcile(data.matches)){recordsChanged();toast('已按确认完赛结果更新模拟记录。');}}catch(error){toast(error.message);}
 updateStatus();updatePage();enhanceTables(main,routeKey());
}

function render() {
 disposePage();disposePage=()=>{};updatePage=()=>{};
 const [current,id,second]=route(),page=current||'home';closeDrawer();
 const active=['team','analysis'].includes(page)?'teams':page==='match'?'matches':page;
 document.querySelectorAll('[data-nav]').forEach(nav=>{nav.classList.toggle('active',nav.dataset.nav===active);if(nav.dataset.nav===active)nav.setAttribute('aria-current','page');else nav.removeAttribute('aria-current');});
 document.querySelector('#breadcrumb').textContent=({home:`${league.name} / 总览`,status:'系统 / 同步监控',compare:`${league.name} / 球队对比`,teams:`${league.country} / ${league.fullName}`,team:`${league.country} / 球队档案`,rankings:`${league.name} / 数据中心`,matches:`${league.name} / 比赛中心`,match:`${league.name} / 比赛详情`,following:'个人研究室 / 我的关注',analysis:'个人研究室 / 赛前分析',simulator:'个人研究室 / 模拟投注',records:'个人研究室 / 我的记录',sources:'足球资料库 / 数据说明',admin:'Football Know / 管理后台'})[page]||'足球资料库';
 if(page==='admin'){disposePage=renderAdmin();updateStatus();return;}
 if(page==='status'){disposePage=renderStatus();updateStatus();return;}
 if(!data)return;
 if(page==='home')updatePage=renderHome();
 else if(page==='rankings')updatePage=renderRankings();
 else if(page==='compare')updatePage=renderCompare(id,second);
 else if(page==='matches')updatePage=renderMatches();
 else if(page==='following')updatePage=renderMatches(true);
 else if(page==='match')disposePage=renderMatch(id);
 else if(page==='teams')renderTeams();
 else if(page==='team')updatePage=renderTeam(id);
 else if(page==='analysis')disposePage=renderAnalysis(id);
 else if(page==='simulator')renderSimulator();
 else if(page==='records')renderRecords();
 else if(page==='sources')renderSources();
 else main.innerHTML='<div class="empty">页面不存在。<a href="#/">回到联赛总览</a></div>';
 if(storeProblem)main.insertAdjacentHTML('afterbegin',`<div class="error-box">${esc(storeProblem)}</div>`);
 if(data.warnings?.length)main.insertAdjacentHTML('afterbegin','<p class="notice">部分历史资料来源暂未更新，正在显示最近成功记录。<a href="#/sources">查看来源</a></p>');
 updateStatus();enhanceTables(main,routeKey());
}

document.addEventListener('click',event=>{
 if(event.target.closest('.skip-link')){event.preventDefault();main.focus();return;}
 const button=event.target.closest('button');if(!button)return;
 if(button.hasAttribute('data-refresh-records')){render();return;}
 if(!data)return;
 if(button.hasAttribute('data-follow')){toggleFollow(Number(button.dataset.follow));return;}
 if(button.dataset.bet){const match=findMatch(button.dataset.bet);if(match){selectMatch(match,button.dataset.selection);location.hash='#/simulator';}}
 if(button.dataset.jump){main.querySelector(`#${button.dataset.jump}-section`)?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});main.querySelectorAll('.tabs button').forEach(tab=>tab.classList.toggle('active',tab===button));}
 if(button.dataset.useOdds){selectSavedOdds(button.dataset.useOdds);location.hash='#/simulator';}
 if(button.dataset.settle)settleRecord(button);
});
window.addEventListener('hashchange',()=>{render();window.scrollTo({top:0});});
window.addEventListener('storage',event=>{if(event.key===STORAGE_KEY){reloadStore();recordsChanged();toast('另一页面修改了个人记录；当前输入已保留。');}});
// Tables that arrive after a page is drawn (lineups, source checks, sync jobs) get the same sorting and export.
const Observer=globalThis.MutationObserver||globalThis.window?.MutationObserver;
let tableObserver=null,tablePass=0;
if(Observer) {
 tableObserver=new Observer(()=>{
  if(tablePass)return;
  tablePass=setTimeout(()=>{tableObserver.disconnect();enhanceTables(main,routeKey());tableObserver.takeRecords();tableObserver.observe(main,{childList:true,subtree:true});tablePass=0;},60);
 });
 tableObserver.observe(main,{childList:true,subtree:true});
}
window.addEventListener('pagehide',()=>{stopPolling();stopIndicator();disposePage();tableObserver?.disconnect();clearTimeout(tablePass);});

async function start() {
 try {await refresh(true);reconcile(data.matches);render();stopPolling=startPolling(updateView);stopIndicator=startSyncIndicator(()=>stopPolling.now?.());}
 catch(error) {
   if(['admin','status'].includes(route()[0])){render();return;}
   main.innerHTML=`<div class="error-box"><h2>暂时无法载入球队资料</h2><p>${esc(error.message)}。已有个人记录仍保存在本浏览器。</p><button class="button" id="reload">重新载入</button> <a class="button secondary" href="#/admin">管理后台</a></div>`;
   main.querySelector('#reload').addEventListener('click',()=>location.reload());
 }
}
start();
