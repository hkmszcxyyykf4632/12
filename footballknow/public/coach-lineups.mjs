import {uniqueCoachFixtures} from './coach-fixtures.mjs';
import {mergeMatches} from './live-core.mjs';
export const coachTime=m=>Date.parse(m.kickoff||m.date+'T12:00:00Z');
export function coachPeriodMatches(date,period,now=Date.now()){
 const days=period==='30'?30:period==='recent'?180:null;
 if(days===null)return true;
 const age=now-Date.parse(date);return Number.isFinite(age)&&age>=0&&age<=days*86400000;
}
export function coachMatchesForTeam(feeds,league,team){
 const matches=[],targets=[];
 for(const feed of feeds){
  if(!feed.data)continue;
  const candidates=feed.data.teams.filter(t=>feed.league===league?String(t.id)===String(team.id):t.espnId&&team.espnId?String(t.espnId)===String(team.espnId):t.name===team.name||Boolean(t.cn&&t.cn===team.cn));
  if(candidates.length!==1)continue;
  const local=candidates[0],names=Object.fromEntries(feed.data.teams.map(t=>[t.name,t.cn]));targets.push({league:feed.league,teamId:local.id});
  for(const m of mergeMatches({...feed.data,league:feed.league},feed.live).filter(m=>[m.home,m.away].includes(local.name))){
   matches.push({...m,league:feed.league,sourceHome:m.home,sourceAway:m.away,homeLabel:names[m.home]||m.home,awayLabel:names[m.away]||m.away,home:m.home===local.name?team.name:m.home,away:m.away===local.name?team.name:m.away});
  }
 }
 return {matches:uniqueCoachFixtures(matches),targets};
}
export function findCoachLineup(match,lineups,league){
 const ids=new Set([match.id,...(match.aliases||[]),match.dailyId?'espn:'+match.dailyId:null].filter(Boolean));
 const candidates=(lineups||[]).filter(d=>d.league===(match.league||league)&&d.date===match.date&&d.home===(match.sourceHome||match.home)&&d.away===(match.sourceAway||match.away));
 const exact=candidates.filter(d=>ids.has(d.matchId)||d.eventId&&ids.has('espn:'+d.eventId));
 const rows=exact.length?exact:candidates;
 return [...rows].sort((a,b)=>(Date.parse(b.updatedAt)||0)-(Date.parse(a.updatedAt)||0))[0]||null;
}
export function coachLineupChange(match,previous,lineups,league){
 const current=findCoachLineup(match,lineups,league),prior=previous?findCoachLineup(previous,lineups,league):null;
 if(!current)return {status:'missing',current:null,previous};
 if(!prior)return {status:'baseline-missing',current,previous};
 const old=new Set(prior.starters.map(p=>p.id)),next=new Set(current.starters.map(p=>p.id));
 return {status:'compared',current,prior,previous,added:current.starters.filter(p=>!old.has(p.id)),removed:prior.starters.filter(p=>!next.has(p.id)),formationChanged:Boolean(current.formation&&prior.formation&&current.formation!==prior.formation)};
}
export function previousCoachMatch(matches,current,team,now=Date.now()){
 return uniqueCoachFixtures(matches).filter(m=>[m.home,m.away].includes(team)&&coachTime(m)<coachTime(current)&&(m.started||m.finished||coachTime(m)<now)&&!(!m.started&&!m.finished&&/postpon|cancel|abandon|延期|取消|推迟/i.test(`${m.status||''} ${m.statusText||''}`))).sort((a,b)=>coachTime(b)-coachTime(a))[0]||null;
}

export function uniqueCoachChanges(records){
 const rows=new Map();
 for(const record of records){
  const identity=record.team.espnId?'espn:'+record.team.espnId:'name:'+record.team.name;
  const key=JSON.stringify([identity,record.date,record.change.incoming||'',record.change.outgoing||'']);
  const prior=rows.get(key);
  if(!prior||prior.league==='ucl'&&record.league!=='ucl')rows.set(key,record);
 }
 return [...rows.values()];
}
