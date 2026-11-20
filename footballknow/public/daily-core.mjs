import {combinedFixtures} from './competition-feed.mjs';
import {quotesForMatch} from './settlement.mjs';
export const hkDay=value=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));
export const hkTime=value=>new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Hong_Kong',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(value));
export const shiftDay=(day,offset)=>new Date(Date.parse(day+'T12:00:00Z')+offset*86400000).toISOString().slice(0,10);
export function validDaily(value){
  return value?.version===1&&value.timezone==='Asia/Hong_Kong'&&Array.isArray(value.matches)&&value.matches.every(m=>
    /^\d{1,16}$/.test(m.id)&&Number.isFinite(Date.parse(m.kickoff))&&m.teams?.home?.id&&m.teams?.away?.id&&m.teams.home.id!==m.teams.away.id);
}
export function dailyRows(snapshot,feeds,{date=hkDay(Date.now()),competition='all',search='',now=Date.now()}={}){
  const locals=combinedFixtures(feeds,{state:'all',date:'',now:Date.parse(date+'T12:00:00+08:00')});
  const consumed=new Set(),rows=[];
  for(const global of snapshot?.matches||[]){
    const h=global.teams.home,a=global.teams.away;
    const match=locals.find(m=>m.league===global.league&&m.home===h.name&&m.away===a.name&&Math.abs(Date.parse(m.kickoff)-Date.parse(global.kickoff))<86400000);
    if(match)consumed.add(match.league+'|'+match.id);
    const feed=feeds.find(f=>f.league===global.league);
    rows.push({...match,...global,id:match?.id||global.id,dailyId:global.id,local:match||null,
      key:'daily:'+global.id,home:h.name,away:a.name,homeLabel:h.label,awayLabel:a.label,
      homeGoals:h.goals,awayGoals:a.goals,quotes:[...(global.quotes||[]),...(match?quotesForMatch(feed?.markets,match):[])],
      delayed:!Number.isFinite(Date.parse(global.updatedAt))||now-Date.parse(global.updatedAt)>180000});
  }
  for(const m of locals){
    if(consumed.has(m.league+'|'+m.id))continue;
    rows.push({...m,key:m.league+'|'+m.id,local:m,day:hkDay(m.kickoff||m.date),competitionId:m.league,
      state:m.finished?'finished':m.started?'live':'scheduled',status:m.finished?'已完场':m.started?'进行中':'未开赛',
      quotes:quotesForMatch(feeds.find(f=>f.league===m.league)?.markets,m)});
  }
  const q=search.trim().toLocaleLowerCase();
  return rows.filter(m=>m.day===date&&(competition==='all'||competition==='five'&&Boolean(m.league)||competition==='league:'+m.league||competition==='competition:'+m.competitionId)
    &&(!q||[m.home,m.away,m.homeLabel,m.awayLabel,m.competition].join(' ').toLocaleLowerCase().includes(q)))
    .sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff)||a.key.localeCompare(b.key));
}
