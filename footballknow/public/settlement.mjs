import {validMarket} from './markets-core.mjs';

export const SETTLEMENT_NAMES={1:'赢盘','0.5':'半赢',0:'走盘','-0.5':'半输','-1':'输盘'};
export function splitLine(line){
  if(typeof line!=='number'||!Number.isFinite(line)||Math.abs(line)>30||line*4!==Math.round(line*4))return null;
  return Number.isInteger(line*2)?[line]:[Math.floor(line*2)/2,Math.ceil(line*2)/2];
}
export function settleLine(difference,line){
  const parts=splitLine(line);
  return parts&&Number.isInteger(difference)?parts.reduce((total,part)=>total+Math.sign(difference+part),0)/parts.length:null;
}
export function regulationScore(match){
  if(!match.finished||match.provisional||match.scoreScope&&/加时|点球|aggregate/i.test(match.scoreScope))return null;
  return [match.homeGoals,match.awayGoals].every(n=>Number.isInteger(n)&&n>=0&&n<=99)?[match.homeGoals,match.awayGoals]:null;
}
export function quotesForMatch(snapshot,match){
  const keys=[match.id,...(match.aliases||[]),`${match.date}|${match.home}|${match.away}`];
  return [...new Set(keys)].flatMap(key=>snapshot?.matches?.[key]||[]).filter(validMarket);
}
export function selectQuote(quotes,market,phases=['closing','preclosing','opening']){
  for(const phase of phases){
    const rows=quotes.filter(q=>q.market===market&&q.phase===phase&&!q.manual&&!q.inPlay);
    if(rows.length)return rows.find(q=>q.kind==='aggregate')||rows.slice().sort((a,b)=>a.provider.localeCompare(b.provider)||String(b.fetchedAt).localeCompare(String(a.fetchedAt)))[0];
  }
  return null;
}
export function matchSettlement(match,teamName,quotes){
  const score=regulationScore(match),home=match.home===teamName;
  if(!score||![match.home,match.away].includes(teamName))return {handicap:null,total:null};
  const ah=selectQuote(quotes,'asian-handicap'),ou=selectQuote(quotes,'total-goals');
  const line=ah?(home?ah.line:-ah.line):null;
  return {handicap:ah?{quote:ah,line,result:settleLine(home?score[0]-score[1]:score[1]-score[0],line)}:null,
    total:ou?{quote:ou,line:ou.line,goals:score[0]+score[1],over:settleLine(score[0]+score[1],-ou.line),under:-settleLine(score[0]+score[1],-ou.line)}:null};
}
export function filterVenue(matches,teamName,venue='all'){
  return matches.filter(m=>venue==='home'?m.home===teamName:venue==='away'?m.away===teamName:[m.home,m.away].includes(teamName));
}
export function settlementSummary(matches,teamName,snapshot){
  const result={finished:0,handicap:0,wins:0,halfWins:0,pushes:0,halfLosses:0,losses:0,totals:0,over:0,under:0,totalPushes:0};
  for(const m of matches){
    if(!regulationScore(m))continue;result.finished++;
    const s=matchSettlement(m,teamName,quotesForMatch(snapshot,m));
    if(s.handicap){result.handicap++;result[{'1':'wins','0.5':'halfWins','0':'pushes','-0.5':'halfLosses','-1':'losses'}[s.handicap.result]]++;}
    if(s.total){result.totals++;result[s.total.over>0?'over':s.total.over<0?'under':'totalPushes']++;}
  }
  return result;
}
