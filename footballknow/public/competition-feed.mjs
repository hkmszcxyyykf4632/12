import {LEAGUES} from './league.mjs';
import {validLive,mergeMatches} from './live-core.mjs';

const cache=new Map();
export async function readLeagueSnapshot(league,name){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
  try{const r=await fetch(`./${LEAGUES[league].folder}${name}.json`,{cache:'no-cache',signal:controller.signal});if(!r.ok)throw Error('读取失败');return await r.json();}
  finally{clearTimeout(timer);}
}
export async function competitionFeeds(){
  await Promise.allSettled(Object.values(LEAGUES).map(async league=>{
    try{
      const [data,live,quoteData]=await Promise.all([readLeagueSnapshot(league.id,'data'),readLeagueSnapshot(league.id,'live').catch(()=>null),readLeagueSnapshot(league.id,'market-odds').catch(()=>null)]);
      const competition=data.competition||(league.id==='epl'?'英超':null);
      if(competition!==league.name||data.teams?.length!==league.teamCount||!Array.isArray(data.matches))throw Error('赛事资料不完整');
      const validQuotes=quoteData?.version===1&&quoteData.league===league.id&&quoteData.season===data.season;
      const liveOK=validLive(live,data);
      cache.set(league.id,{league:league.id,data,live:liveOK?live:cache.get(league.id)?.live,markets:validQuotes?quoteData:cache.get(league.id)?.markets,failed:!liveOK});
    }catch{cache.set(league.id,{...cache.get(league.id),league:league.id,failed:true});}
  }));
  return [...cache.values()];
}
export function localDate(value){const d=new Date(value);return Number.isFinite(d.getTime())?`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`:'';}
export const fixtureTime=m=>Date.parse(m.kickoff||(m.date?`${m.date}T12:00:00`:''));
export function combinedFixtures(feeds,{league='all',state='upcoming',date='',now=Date.now(),windowAt=now,allDates=false}={}){
  const rows=[];
  for(const feed of feeds){
    if(!feed.data||league!=='all'&&league!==feed.league)continue;
    const names=Object.fromEntries(feed.data.teams.map(t=>[t.name,t.cn]));
    for(const m of mergeMatches(feed.data,feed.live)){
      if(m.competition!==(feed.data.competition||'英超'))continue;
      const kickoff=fixtureTime(m),day=localDate(m.kickoff||`${m.date}T12:00:00`);
      if(date&&date!==day)continue;
      if(!allDates&&!date&&Number.isFinite(kickoff)&&(kickoff<windowAt-7*86400000||kickoff>windowAt+7*86400000))continue;
      if(state==='live'&&(!m.started||m.finished)||state==='upcoming'&&(m.finished||!m.started&&(!Number.isFinite(kickoff)||kickoff<now))||state==='finished'&&!m.finished)continue;
      const archived=feed.data.matches?.find(a=>a.season===m.season&&a.competition===m.competition&&a.home===m.home&&a.away===m.away&&(a.id===m.id||Date.parse(a.kickoff)===Date.parse(m.kickoff)));
      rows.push({...m,aliases:[...(m.aliases||[]),archived?.id].filter(Boolean),league:feed.league,homeLabel:names[m.home]||m.home,awayLabel:names[m.away]||m.away,day,
        updatedAt:m.updatedAt||feed.live?.updatedAt||feed.data.updatedAt,delayed:!m.finished&&(Boolean(feed.failed)||!Number.isFinite(Date.parse(m.updatedAt))||now-Date.parse(m.updatedAt)>180000)});
    }
  }
  return rows.sort((a,b)=>(fixtureTime(a)||Infinity)-(fixtureTime(b)||Infinity)||a.league.localeCompare(b.league)||a.id.localeCompare(b.id));
}
