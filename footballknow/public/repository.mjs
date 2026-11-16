import {league} from './league.mjs';
import {mergeMatches,validLive,freshness} from './live-core.mjs';
import {validTable,validLeaders} from './rankings-core.mjs';

export let data=null, live=null, names=null, history=null;
export let liveFailed=false;
export let standings=null,rankings=null,rankingsFailed=false;
export let odds=null;
let archive=null, busy=false;
// One cadence for everything: the server checks every source each minute and the page re-reads every snapshot each minute.
export const SYNC_MS=60000;
export const syncState={lastAttempt:0,lastSuccess:0,nextAt:0,busy:false};

async function readSnapshot(name) {
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),10000);
  try {
    const response=await fetch(`./${league.folder}${name}.json`,{cache:'no-cache',signal:controller.signal});
    if(!response.ok)throw new Error('资料暂时无法读取');
    return await response.json();
  } finally {clearTimeout(timeout);}
}

export async function refresh(force=false) {
  if(busy)return false;
  busy=true;syncState.busy=true;syncState.lastAttempt=Date.now();
  try {
    const full=true;
    if(full) {
      try {
        const next=await readSnapshot('data');
        if((next?.competition||'英超')!==league.name||next?.version!==1||next.teams?.length!==league.teamCount||!Array.isArray(next.players)||!Array.isArray(next.matches))throw new Error('球队资料格式不完整');
        archive=next;
      } catch(error) {if(!archive)throw error;}
    }
    const snapshotKeys=full?['live','names','history','standings','rankings','odds']:['live','standings','rankings','odds'];
    const snapshots=await Promise.allSettled(snapshotKeys.map(readSnapshot));
    const result=snapshots[0];
    if(result.status==='fulfilled'&&validLive(result.value,archive)) {live=result.value;liveFailed=false;}
    else liveFailed=true;
    if(full) {
      const n=snapshots[1], h=snapshots[2];
      if(n.status==='fulfilled'&&n.value.version===1&&n.value.season===archive.season&&n.value.names&&Array.isArray(n.value.unresolved))names=n.value;
      if(h.status==='fulfilled'&&h.value.version===1&&h.value.season===archive.season&&Array.isArray(h.value.transfers)&&Array.isArray(h.value.managers))history=h.value;
    }
    data={...archive,matches:mergeMatches(archive,live,data?.matches||[])};
    const table=snapshots[snapshotKeys.indexOf('standings')],leaders=snapshots[snapshotKeys.indexOf('rankings')];
    const tableOK=table.status==='fulfilled'&&validTable(table.value,archive,league.id),leadersOK=leaders.status==='fulfilled'&&validLeaders(leaders.value,archive,league.id);
    if(tableOK)standings=table.value;
    if(leadersOK)rankings=leaders.value;
    if(standings?.season!==archive.season)standings=null;
    if(rankings?.season!==archive.season)rankings=null;
    rankingsFailed=!tableOK||!leadersOK;
    const quoteResult=snapshots[snapshotKeys.indexOf('odds')];
    if(quoteResult.status==='fulfilled'&&quoteResult.value.version===1&&quoteResult.value.league===league.id&&quoteResult.value.season===archive.season&&quoteResult.value.matches)odds=quoteResult.value;
    if(odds?.season!==archive.season)odds=null;
    if(odds)data.matches=data.matches.map(m=>{const rows=odds.matches[m.id]?.filter(q=>q.market==='90-minute-1x2'&&['H','D','A'].every(k=>Number.isFinite(q[k])&&q[k]>1&&q[k]<=10000));return rows?.length?{...m,odds:rows}:m;});
    syncState.lastSuccess=Date.now();
    return true;
  } finally {busy=false;syncState.busy=false;}
}

export function findMatch(id) {return data?.matches.find(row=>row.id===id||row.aliases?.includes(id));}

export function liveStatus() {
  const state=freshness(live,liveFailed);
  const stamp=live?.updatedAt ? new Date(live.updatedAt).toLocaleString('zh-CN') : '尚无成功记录';
  return {...state,text:state.stale?'比分资料待更新':state.failed?'连接暂时中断':'全部资料每 60 秒同步',stamp};
}

export function startPolling(onUpdate) {
  let disposed=false,timer;
  const schedule=()=>{clearTimeout(timer);syncState.nextAt=Date.now()+SYNC_MS;timer=setTimeout(poll,SYNC_MS);};
  async function poll() {
    if(disposed)return;
    schedule();
    if(document.hidden)return;
    try {if(await refresh())onUpdate();}catch {liveFailed=true;onUpdate();}
  }
  // A tab that was in the background catches up at once when it is shown again.
  const visibility=()=>{if(!document.hidden&&Date.now()-syncState.lastAttempt>=SYNC_MS)poll();};
  document.addEventListener('visibilitychange',visibility);
  schedule();
  const stop=()=>{disposed=true;clearTimeout(timer);document.removeEventListener('visibilitychange',visibility);};
  stop.now=poll;
  return stop;
}
