// Alerts for followed clubs while the site is open: kick-off, goals and full time, found by comparing refreshes.
import {data} from './repository.mjs';
import {league} from './league.mjs';
import {cn,toast} from './ui.mjs';
import {loadFollowing} from './rankings-core.mjs';
import {matchAlerts} from './insights.mjs';

const KEY='footballknow-alerts';
let previous=null;
const supported=()=>typeof Notification!=='undefined';
export function alertsOn() {try {return localStorage.getItem(KEY)==='on';}catch {return false;}}

export function checkAlerts() {
  const current=data.matches.filter(m=>m.season===data.season).map(m=>({id:m.id,home:m.home,away:m.away,started:m.started,finished:m.finished,homeGoals:m.homeGoals,awayGoals:m.awayGoals}));
  const before=previous;previous=current;
  if(!before||!alertsOn())return [];
  const followed=loadFollowing(localStorage,league.id,data.teams).map(id=>data.teams.find(t=>t.id===id)?.name).filter(Boolean);
  const alerts=matchAlerts(before,current,followed,cn);
  for(const alert of alerts) {
    toast(`${alert.title}：${alert.text}`);
    if(supported()&&Notification.permission==='granted') {
      try {new Notification(alert.title,{body:alert.text,tag:`${alert.matchId}-${alert.kind}-${alert.text}`,icon:'./icon.svg'});}catch {/* Some browsers only allow notifications from a service worker; the in-page message still shows. */}
    }
  }
  return alerts;
}

export function alertPanel() {
  const on=alertsOn(),permission=supported()?Notification.permission:'unsupported';
  return `<section class="notice alert-panel" id="alert-panel"><div><strong>关注球队提醒</strong><p>${on?`已开启：关注球队的比赛开球、进球和结束时提醒。${permission==='granted'?'系统通知已允许。':permission==='denied'?'浏览器已拒绝系统通知，目前只在页面内提示；可在浏览器的网站设置中改为允许。':'目前只在页面内提示。'}`:'开启后，关注球队的比赛开球、进球和结束时会提醒你。'}提醒依靠本页面每 60 秒的同步，需要保持本站在浏览器中打开；关闭页面后不会推送。</p></div><button class="button ${on?'secondary':''} compact" type="button" id="alert-toggle" aria-pressed="${on}">${on?'关闭提醒':'开启提醒'}</button></section>`;
}

export function mountAlertPanel(root) {
  const place=()=>{root.querySelector('#alert-panel')?.remove();root.querySelector('.page-heading')?.insertAdjacentHTML('afterend',alertPanel());root.querySelector('#alert-toggle')?.addEventListener('click',toggle);};
  async function toggle() {
    const next=!alertsOn();
    try {localStorage.setItem(KEY,next?'on':'off');}catch {toast('浏览器暂时无法保存这项设置。');return;}
    if(next&&supported()&&Notification.permission==='default') {try {await Notification.requestPermission();}catch {/* Page messages remain. */}}
    toast(next?'已开启关注球队提醒。':'已关闭提醒。');place();
  }
  place();
}
