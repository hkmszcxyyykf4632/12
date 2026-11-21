import {data,refresh,findMatch,startPolling} from './repository.mjs';
import {storeProblem,STORAGE_KEY,reloadStore,reconcile} from './personal-store.mjs';
import {main,esc,toast} from './ui.mjs';
import {renderTeams,renderSources} from './pages.mjs';
import {renderHome} from './dashboard.mjs';
import {renderCoaches} from './coaches-page.mjs';
import {renderLive} from './daily-page.mjs';
import {renderNews} from './news-page.mjs';
import {renderPortalNews} from './portal-news.mjs';
import {renderSponsors} from './sponsors-page.mjs';
import {renderRace} from './racing-page.mjs';
import {renderBloodlines} from './bloodlines-page.mjs';
import {renderRacingHub,renderRacingDay} from './racing-day.mjs';
import {renderHorseDirectory} from './horse-directory.mjs';
import {renderHorseProfile} from './horse-profile.mjs';
import {renderHorseGoing} from './horse-going.mjs';
import {renderVideos,renderVideoAdmin} from './videos-page.mjs';
import {renderCNMarkets,renderVolume,renderUSReference} from './equity-page.mjs';
import {renderRacingRankings} from './racing-rankings.mjs';
import {bindPortraits,hydratePlayerPortraits} from './portraits.mjs';
import {renderMarkets,renderStock,renderAsset} from './finance-page.mjs';
import {renderGlobalMarkets} from './global-markets.mjs';
import {renderStockRankings} from './market-reference.mjs';
import {renderStatus} from './status-page.mjs';
import {renderCompare} from './compare-page.mjs';
import {bindTheme,bindDrawer,bindPalette,paintSync,startSyncIndicator} from './shell.mjs';
import {enhanceTables,bindTableTools} from './table-tools.mjs';
import {renderPlayer} from './player-page.mjs';
import {renderQuality} from './quality-page.mjs';
import {checkAlerts,mountAlertPanel} from './notifications.mjs';
import {renderTeam} from './team-page.mjs';
import {renderSimulator,renderRecords,selectMatch,selectSavedOdds,settleRecord} from './simulator.mjs';
import {renderAdmin} from './admin.mjs';
import {renderAnalysis} from './analysis-page.mjs';
import {league} from './league.mjs';
import {renderRankings} from './rankings-page.mjs';
import {renderMatches,renderMatch,toggleFollow} from './matches-page.mjs';
import {bindEvidenceReview} from './evidence-review.mjs';

document.querySelector('[data-league-team-label]').textContent=league.name+'球队';
document.querySelectorAll('[data-league]').forEach(link=>{const active=link.dataset.league===league.id;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','true');});

let disposePage=()=>{},updatePage=()=>{},stopPolling=()=>{},stopIndicator=()=>{};
const route=()=>location.hash.replace(/^#\/?/,'').split('/');
const routeKey=()=>`${league.id}:${route().join('/')}`;
bindTheme();bindPalette();bindTableTools(()=>`${league.name}-${route()[0]||'首页'}`);bindPortraits(main);
bindEvidenceReview(document);
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
 try {checkAlerts();}catch {/* Alerts are optional and must never block a refresh. */}
}

function render() {
 disposePage();disposePage=()=>{};updatePage=()=>{};
 const [current,id,second]=route(),page=current||'home';closeDrawer();
 const racingPages=['racing','race','horse','horses','horse-going','bloodlines','racing-day','racing-rankings'];
 document.documentElement.dataset.section=racingPages.includes(page)?'racing':['markets','cn-markets','us-stocks','stock-volume','stock-rankings','stock-following','global-indices','commodities','forex','stock','asset'].includes(page)?'finance':['home','portal-news','sponsors','admin','status','videos','video-admin'].includes(page)?'portal':'football';
 const active=['race','racing-day'].includes(page)?'racing':page==='horse'?'horses':['stock','asset'].includes(page)?'markets':['team','analysis','player'].includes(page)?'teams':page==='match'?'matches':page;
 document.querySelectorAll('[data-nav]').forEach(nav=>{nav.classList.toggle('active',nav.dataset.nav===active);if(nav.dataset.nav===active)nav.setAttribute('aria-current','page');else nav.removeAttribute('aria-current');});
 document.querySelector('#breadcrumb').textContent=({home:'峰弈科技 / 首页',racing:'香港赛马 / 赛事与马匹',race:'香港赛马 / 赛事研究',horse:'香港赛马 / 马匹档案',sponsors:'峰弈科技 / 赞助商',markets:'市场 / 港股与报价',stock:'市场 / 股票详情',asset:'市场 / 品种走势',live:'全球足球 / 每日赛事与即场赛果',news:'五项赛事 / 球队新闻',status:'系统 / 同步监控',quality:'系统 / 数据质量',player:`${league.name} / 球员档案`,compare:`${league.name} / 球队对比`,teams:`${league.country} / ${league.fullName}`,team:`${league.country} / 球队档案`,rankings:`${league.name} / 数据中心`,matches:`${league.name} / 比赛中心`,match:`${league.name} / 比赛详情`,following:'个人研究室 / 我的关注',analysis:'个人研究室 / 赛前分析',simulator:'个人研究室 / 模拟投注',records:'个人研究室 / 我的记录',sources:'足球资料库 / 数据说明',admin:'峰弈科技 / 管理后台'})[page]||'足球资料库';
 if(page==='racing'){disposePage=renderRacingHub();return;}
 if(page==='horses'){document.querySelector('#breadcrumb').textContent='香港赛马 / 马匹资料';disposePage=renderHorseDirectory(id,second);return;}
 if(page==='racing-day'){document.querySelector('#breadcrumb').textContent='香港赛马 / 赛马日';disposePage=renderRacingDay(id,second);return;}
 if(page==='racing-rankings'){document.querySelector('#breadcrumb').textContent='香港赛马 / 骑练排行榜';disposePage=renderRacingRankings(id);return;}
 if(page==='race'){disposePage=renderRace(id);return;}
 if(page==='bloodlines'){document.querySelector('#breadcrumb').textContent='香港赛马 / 著名血统';disposePage=renderBloodlines(id);return;}
 if(page==='horse'){disposePage=renderHorseProfile(id);return;}
 if(page==='coaches'){document.querySelector('#breadcrumb').textContent='足球 / 教练与换帅观察';disposePage=renderCoaches();return;}
 if(page==='horse-going'){document.documentElement.dataset.section='racing';document.querySelector('#breadcrumb').textContent='香港赛马 / 场地表现';disposePage=renderHorseGoing();return;}
 if(page==='markets'){disposePage=renderMarkets();return;}
 if(['cn-markets','us-stocks','stock-volume'].includes(page)){document.querySelector('#breadcrumb').textContent='市场 / '+({'cn-markets':'沪深 A 股','us-stocks':'精选美股','stock-volume':'成交量观察'})[page];disposePage=({'cn-markets':renderCNMarkets,'us-stocks':renderUSReference,'stock-volume':renderVolume})[page]();return;}
 if(page==='videos'||page==='video-admin'){document.querySelector('#breadcrumb').textContent='峰弈科技 / 分析视频';disposePage=page==='videos'?renderVideos(id):renderVideoAdmin();return;}
 if(['global-indices','commodities','forex'].includes(page)){document.querySelector('#breadcrumb').textContent='市场 / '+({'global-indices':'全球股票指数',commodities:'贵金属与原油',forex:'主要货币兑美元'})[page];disposePage=renderGlobalMarkets(page);return;}
 if(page==='stock-rankings'){document.querySelector('#breadcrumb').textContent='市场 / 每日涨跌榜';disposePage=renderStockRankings(main);return;}
 if(page==='stock-following'){document.querySelector('#breadcrumb').textContent='市场 / 我的关注';disposePage=renderMarkets(true);return;}
 if(page==='stock'){disposePage=renderStock(id);return;}
 if(page==='asset'){disposePage=renderAsset(id);return;}
 if(page==='sponsors'){renderSponsors();return;}
 if(page==='admin'){disposePage=renderAdmin();updateStatus();return;}
 if(page==='status'){disposePage=renderStatus();updateStatus();return;}
 if(page==='live'){document.querySelector('#breadcrumb').textContent='全球足球 / 每日赛事与即场赛果';disposePage=renderLive();return;}
 if(page==='news'){disposePage=renderNews(id||'');return;}
 if(page==='portal-news'){document.querySelector('#breadcrumb').textContent='峰弈科技 / 即时资讯';disposePage=renderPortalNews(id);return;}
 if(!data)return;
 if(page==='home')updatePage=renderHome();
 else if(page==='rankings')updatePage=renderRankings();
 else if(page==='compare')updatePage=renderCompare(id,second);
 else if(page==='player')updatePage=renderPlayer(id,second);
 else if(page==='quality')updatePage=renderQuality();
 else if(page==='matches')updatePage=renderMatches();
 else if(page==='following'){updatePage=renderMatches(true);mountAlertPanel(main);}
 else if(page==='match')disposePage=renderMatch(id,second);
 else if(page==='teams')renderTeams();
 else if(page==='team')updatePage=renderTeam(id);
 else if(page==='analysis')disposePage=renderAnalysis(id);
 else if(page==='simulator')renderSimulator();
 else if(page==='records')renderRecords();
 else if(page==='sources')renderSources();
 else main.innerHTML='<div class="empty">页面不存在。<a href="#/">回到联赛总览</a></div>';
 if(storeProblem)main.insertAdjacentHTML('afterbegin',`<div class="error-box">${esc(storeProblem)}</div>`);
 if(data.warnings?.length)main.insertAdjacentHTML('afterbegin','<p class="notice">部分历史资料来源暂未更新，正在显示最近成功记录。<a href="#/sources">查看来源</a></p>');
 updateStatus();enhanceTables(main,routeKey());hydratePlayerPortraits(main,league.id);
}

async function sharePage() {
 const url=location.href,title=document.querySelector('#main h1')?.textContent||'峰弈科技';
 try {
  if(navigator.share){await navigator.share({title,url});return;}
  await navigator.clipboard.writeText(url);toast('链接已复制，可以直接粘贴分享。');
 } catch(error) {if(error?.name!=='AbortError')toast(`无法自动复制，请手动复制地址栏链接：${url}`);}
}

document.addEventListener('click',event=>{
 if(event.target.closest('.skip-link')){event.preventDefault();main.focus();return;}
 const button=event.target.closest('button');if(!button)return;
 if(button.hasAttribute('data-share')){sharePage();return;}
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
   if(['coaches','bloodlines','horse-going','videos','video-admin','cn-markets','us-stocks','stock-volume','admin','status','live','news','portal-news','sponsors','markets','stock-rankings','stock-following','global-indices','commodities','forex','stock','asset','racing','race','horse','horses','racing-day','racing-rankings'].includes(route()[0])){render();return;}
   main.innerHTML=`<div class="error-box"><h2>暂时无法载入球队资料</h2><p>${esc(error.message)}。已有个人记录仍保存在本浏览器。</p><button class="button" id="reload">重新载入</button> <a class="button secondary" href="#/admin">管理后台</a></div>`;
   main.querySelector('#reload').addEventListener('click',()=>location.reload());
 }
}
start();
