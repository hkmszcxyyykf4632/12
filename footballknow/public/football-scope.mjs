const competitions=new Set(['700','740','730','720','775']);
const leagues=new Set(['epl','laliga','seriea','bundesliga','ucl']);
export function supportsFootballAnalysis(row){
  const id=String(row.competitionId||'');
  return id&&/^\d+$/.test(id)?competitions.has(id):leagues.has(row.league);
}
