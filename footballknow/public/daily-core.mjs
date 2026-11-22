import {sameDailyFixture,reconcileDailyMatches} from './score-reconciliation.mjs';
import {supportsFootballAnalysis} from './football-scope.mjs';
import {combinedFixtures} from './competition-feed.mjs';
import {quotesForMatch} from './settlement.mjs';
export const hkDay=value=>!Number.isFinite(new Date(value).getTime())?'':new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Hong_Kong',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));
export const hkTime=value=>!Number.isFinite(new Date(value).getTime())?'时间待定':new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Hong_Kong',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(value));
export const shiftDay=(day,offset)=>new Date(Date.parse(day+'T12:00:00Z')+offset*86400000).toISOString().slice(0,10);
export function matchStatus(row){
  if(row.finished)return '已完赛';
  const raw=String(row.status||'');
  if(/[\u3400-\u9fff]/.test(raw))return raw;
  if(/HALFTIME|HALF_TIME|HalfTime/i.test(raw))return '中场休息';
  if(/FIRST_HALF/i.test(raw))return '上半场';
  if(/SECOND_HALF/i.test(raw))return '下半场';
  return ({postponed:'延期',cancelled:'取消',abandoned:'中断',live:'进行中',scheduled:'未开赛'})[row.state]||(row.started?'进行中':'未开赛');
}
export function validDaily(value){
  return value?.version===1&&value.timezone==='Asia/Hong_Kong'&&Array.isArray(value.matches)&&value.matches.every(m=>
    /^\d{1,16}$/.test(m.id)&&Number.isFinite(Date.parse(m.kickoff))&&m.teams?.home?.id&&m.teams?.away?.id&&m.teams.home.id!==m.teams.away.id);
}
export function dailyRows(snapshot,feeds,{date=hkDay(Date.now()),competition='all',search='',season='',teamName='',now=Date.now()}={}){
  const locals=combinedFixtures(feeds,{state:'all',date:'',now,windowAt:date?Date.parse(date+'T12:00:00+08:00'):now,allDates:!date});
  const consumed=new Set(),rows=[];
  for(const global of snapshot?.matches||[]){
    const h=global.teams.home,a=global.teams.away;
    const feed=feeds.find(f=>f.league===global.league);
    const candidates=locals.filter(m=>sameDailyFixture(m,global,feed?.data||{},m.league));
    const match=candidates.length===1?candidates[0]:null;
    if(match)consumed.add(match.league+'|'+match.id);
    const reconciled=match?reconcileDailyMatches([match],feed.data,{matches:[global]},match.league,match.updatedAt)[0]:null;
    const chosen=reconciled||{...global,homeGoals:h.goals,awayGoals:a.goals};
    const state=chosen.state||(chosen.finished?'finished':chosen.started?'live':'scheduled');
    rows.push({...global,...chosen,id:match?.id||global.id,dailyId:global.id,local:match||null,
      key:'daily:'+global.id,home:match?.home||h.name,away:match?.away||a.name,homeLabel:match?.homeLabel||h.label||h.name,awayLabel:match?.awayLabel||a.label||a.name,
      season:match?.season||String(global.season||''),day:hkDay(chosen.kickoff),state,status:matchStatus({...chosen,state}),
      teams:{home:{...h,goals:chosen.homeGoals},away:{...a,goals:chosen.awayGoals}},quotes:[...(global.quotes||[]),...(match?quotesForMatch(feed?.markets,match):[])],
      delayed:!chosen.finished&&(!Number.isFinite(Date.parse(chosen.updatedAt))||now-Date.parse(chosen.updatedAt)>180000)});
  }
  for(const m of locals){
    if(consumed.has(m.league+'|'+m.id))continue;
    rows.push({...m,key:m.league+'|'+m.id,local:m,day:hkDay(m.kickoff||m.date),competitionId:({epl:'700',laliga:'740',seriea:'730',bundesliga:'720',ucl:'775'})[m.league],
      state:m.finished?'finished':m.started?'live':'scheduled',status:m.finished?'已完赛':m.started?'进行中':'未开赛',
      quotes:quotesForMatch(feeds.find(f=>f.league===m.league)?.markets,m)});
  }
  const q=search.trim().toLocaleLowerCase();
  return rows.filter(m=>(!date||m.day===date)&&(!season||m.season===season)&&(!teamName||[m.home,m.away].includes(teamName))&&(competition==='all'||competition==='major'&&supportsFootballAnalysis(m)||competition==='five'&&Boolean(m.league)||competition==='league:'+m.league||competition==='competition:'+m.competitionId)
    &&(!q||[m.home,m.away,m.homeLabel,m.awayLabel,m.competition].join(' ').toLocaleLowerCase().includes(q)))
    .sort((a,b)=>(Date.parse(a.kickoff||a.date)||Infinity)-(Date.parse(b.kickoff||b.date)||Infinity)||a.key.localeCompare(b.key));
}
