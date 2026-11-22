const stamp=value=>Date.parse(value)||0;
const goals=m=>[m.homeGoals,m.awayGoals].every(n=>Number.isInteger(n)&&n>=0&&n<=99);
export const confirmedScore=m=>Boolean(m?.finished&&!m.provisional&&goals(m)&&/^90/.test(m.scoreScope||''));
export function preferIncomingScore(current,incoming){
  const oldFinal=confirmedScore(current),newFinal=confirmedScore(incoming);
  if(oldFinal!==newFinal)return newFinal;
  if(current?.finished&&!incoming.finished)return false;
  if(current?.started&&!incoming.started&&!['postponed','cancelled','abandoned'].includes(incoming.state))return false;
  return stamp(incoming.scoreUpdatedAt||incoming.updatedAt)>=stamp(current?.scoreUpdatedAt||current?.updatedAt);
}
export function sameDailyFixture(m,g,archive,league){
  if(g.league!==league||m.competition!==(archive.competition||'英超'))return false;
  if(m.season&&m.season!==archive.season||g.season&&Number.parseInt(m.season)!==Number.parseInt(g.season))return false;
  if(!stamp(m.kickoff)||stamp(m.kickoff)!==stamp(g.kickoff))return false;
  if(m.id?.startsWith('espn:')&&m.id!==`espn:${g.id}`)return false;
  return ['home','away'].every(side=>{
    const team=archive.teams?.find(t=>t.name===m[side]),other=g.teams?.[side];
    if(!other)return false;
    if(team?.espnId&&other.id)return String(team.espnId)===String(other.id);
    return [other.name,other.originalName].includes(m[side])||Boolean(team?.cn&&team.cn===other.label);
  });
}
export function dailyScore(g){
  const homeGoals=g.teams?.home?.goals,awayGoals=g.teams?.away?.goals;
  return {started:g.started,finished:g.finished,provisional:false,homeGoals,awayGoals,
    result:g.finished&&Number.isInteger(homeGoals)&&Number.isInteger(awayGoals)?homeGoals===awayGoals?'D':homeGoals>awayGoals?'H':'A':null,
    scoreScope:g.scoreScope,state:g.state,status:g.status,clock:g.clock||'',
    scoreUpdatedAt:g.updatedAt,updatedAt:g.updatedAt,scoreSource:g.source};
}
export function reconcileDailyMatches(matches,archive,daily,league,updatedAt){
  return matches.map(m=>{
    const candidates=(daily?.matches||[]).filter(g=>sameDailyFixture(m,g,archive,league));
    if(candidates.length!==1)return m;
    const g=candidates[0],score=dailyScore(g),linked={...m,dailyId:g.id};
    if(score.finished&&!confirmedScore(score))return linked;
    return preferIncomingScore({...m,updatedAt:m.updatedAt||updatedAt},score)?{...linked,...score}:linked;
  });
}
