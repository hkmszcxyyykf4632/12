import {preferIncomingScore,confirmedScore} from './score-reconciliation.mjs';
export function mergeMatches(archive, live, previous=[]) {
  const key = row => archive.league==='ucl'?`${row.competition}|${row.id}`:`${row.season}|${row.competition}|${row.home}|${row.away}`;
  const prior = new Map(previous.map(row=>[key(row),row]));
  const current = new Map(archive.matches.map(row=>[key(row),{...row,updatedAt:row.updatedAt||archive.updatedAt}]));
  if(live?.season===archive.season) {
    for(const row of live.matches) {
      const archived=current.get(key(row));
      const old=prior.get(key(row));
      const aliases=[...new Set([row.id,archived?.id,old?.id,...(old?.aliases||[])].filter(Boolean))];
      let merged={...archived,...row,updatedAt:row.updatedAt||live.updatedAt,odds:row.odds?.length?row.odds:archived?.odds||old?.odds||[],
        oddsSource:archived?.oddsSource||archived?.source||old?.oddsSource,aliases};
      for(const previous of [archived,old])if(confirmedScore(previous)&&previous.kickoff===merged.kickoff&&!preferIncomingScore(previous,merged)){
        for(const field of ['started','finished','provisional','homeGoals','awayGoals','result','scoreScope','state','status','clock','updatedAt','scoreUpdatedAt','scoreSource'])if(previous[field]!==undefined)merged[field]=previous[field];
      }
      current.set(key(row),merged);
    }
  }
  return [...current.values()].sort((a,b)=>(b.date||'').localeCompare(a.date||'')||b.id.localeCompare(a.id));
}

export function validLive(value,archive) {
  const ucl=archive.competition==='欧冠';
  const expected=archive.teams.length*(archive.teams.length-1);
  if(value?.version!==1 || value.season!==archive.season || !Number.isFinite(Date.parse(value.updatedAt)) || !Array.isArray(value.matches) || (ucl?value.matches.length<144:value.matches.length!==expected))return false;
  const teams=new Set(archive.teams.map(row=>row.name));
  const pairs=new Set();
  const ids=new Set(), phaseCounts=new Map();let phaseMatches=0;
  for(const row of value.matches) {
    if(!teams.has(row.home)||!teams.has(row.away)||row.home===row.away||row.season!==value.season||row.competition!==(archive.competition||'英超'))return false;
    if(typeof row.finished!=='boolean'||typeof row.started!=='boolean'||typeof row.id!=='string')return false;
    if(row.finished && (![row.homeGoals,row.awayGoals].every(n=>Number.isInteger(n)&&n>=0&&n<=99)||!['H','D','A'].includes(row.result)))return false;
    if(!row.finished && row.result!=null)return false;
    pairs.add(`${row.home}|${row.away}`);
    if(ucl) {
      if(!Number.isInteger(row.fixtureId)||ids.has(row.fixtureId))return false;
      ids.add(row.fixtureId);
      if(row.phase==='联赛阶段'){phaseMatches++;for(const name of [row.home,row.away])phaseCounts.set(name,(phaseCounts.get(name)||0)+1);}
    }
  }
  return ucl?teams.size===36&&phaseMatches===144&&phaseCounts.size===36&&[...phaseCounts.values()].every(n=>n===8):teams.size>=2&&pairs.size===expected;
}

export function freshness(value,failed=false,now=Date.now()) {
  const age=now-Date.parse(value?.updatedAt);
  return {stale:!Number.isFinite(age)||age>180000||age< -60000,failed,age};
}
