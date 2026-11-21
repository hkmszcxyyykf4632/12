const day = value => String(value || '').slice(0,10);
const time = match => Date.parse(match.kickoff || `${match.date}T12:00:00Z`);
const excluded = match => !match.finished && !match.started && /postpon|cancel|abandon|延期|取消|推迟/i.test(`${match.status || ''} ${match.statusText || ''}`);

export function uniqueCoachFixtures(matches) {
  const groups = [];
  for (const match of matches) {
    const scope = `${match.competition}|${match.season}|`;
    const keys = new Set([match.id,...(match.aliases || [])].filter(Boolean).map(id=>scope+id));
    if (match.fixtureId != null) keys.add(`${scope}fixture:${match.fixtureId}`);
    keys.add(`${scope}pair:${match.home}|${match.away}|${match.date}`);
    const overlaps = groups.filter(group=>[...keys].some(key=>group.keys.has(key)));
    const rows = [match,...overlaps.flatMap(group=>group.rows)];
    for (const group of overlaps) {
      for (const key of group.keys) keys.add(key);
      groups.splice(groups.indexOf(group),1);
    }
    groups.push({keys,rows});
  }
  const rank = match => match.finished ? 3 : match.started ? 2 : excluded(match) ? 1 : 0;
  return groups.map(group=>group.rows.sort((a,b)=>rank(b)-rank(a))[0]);
}

export function managerFixtures(matches,team,joinedAt,nextJoinedAt=null,{competition,now=Date.now()}={}) {
  if (!joinedAt) return {rows:[],recent:[],next:null,coverageLimited:false};
  const teamRows = uniqueCoachFixtures(matches.filter(m=>[m.home,m.away].includes(team) && (!competition || m.competition===competition)))
    .filter(m=>Number.isFinite(time(m)) && !excluded(m))
    .sort((a,b)=>time(a)-time(b) || String(a.id).localeCompare(String(b.id)));
  const coverageLimited = !teamRows.length || day(joinedAt)<day(teamRows[0].date);
  const rows = teamRows.filter(m=>day(m.date)>=day(joinedAt) && (!nextJoinedAt || day(m.date)<day(nextJoinedAt)))
    .map((match,index)=>{
      const projected = !match.started && !match.finished;
      const number = index+1;
      const label = projected ? `预计第${number}场${coverageLimited?'（已收录序号）':''}` : coverageLimited ? `已收录第${number}场` : `换帅后第${number}场`;
      return {match,number,projected,label,pending:projected && time(match)<now};
    });
  return {rows,coverageLimited,recent:rows.filter(row=>!row.projected).slice(-2),next:rows.find(row=>row.projected && !row.pending) || null};
}
