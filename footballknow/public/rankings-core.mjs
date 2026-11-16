export function validTable(value, data, league) {
 if(value?.version!==1||value.league!==league||value.season!==data.season||!Number.isFinite(Date.parse(value.updatedAt)))return false;
 if(!Array.isArray(value.entries)||value.entries.length!==data.teams.length)return false;
 const ids=new Set(data.teams.map(t=>t.id));
 return new Set(value.entries.map(r=>r.teamId)).size===ids.size&&value.entries.every(r=>ids.has(r.teamId)&&['rank','played','wins','draws','losses','goalsFor','goalsAgainst','goalDifference','points'].every(k=>Number.isInteger(r[k]))&&r.rank>0&&r.rank<=ids.size&&r.played===r.wins+r.draws+r.losses&&r.goalDifference===r.goalsFor-r.goalsAgainst);
}
export function validLeaders(value,data,league) {
 const ids=new Set(data.teams.map(t=>t.id));
 return value?.version===1&&value.league===league&&value.season===data.season&&Number.isFinite(Date.parse(value.updatedAt))&&['scorers','assists'].every(k=>Array.isArray(value.boards?.[k])&&value.boards[k].every(r=>ids.has(r.teamId)&&Number.isInteger(r.value)&&r.value>=0&&Number.isInteger(r.appearances)&&r.appearances>=0));
}
export function metricRows(table,leaders,metric) {
 const values=table?.entries?.map(r=>{const d=leaders?.discipline?.find(d=>d.teamId===r.teamId);return {...r,yellowCards:d?.yellowCards,redCards:d?.redCards,played:['yellowCards','redCards'].includes(metric)?d?.played:r.played};})||[];
 const sign=metric==='goalsAgainst'?1:-1;
 const metricValue=r=>metric==='goalsPerGame'?(r.played?r.goalsFor/r.played:null):r[metric];
 const rows=values.filter(r=>Number.isFinite(metricValue(r))).sort((a,b)=>sign*(metricValue(a)-metricValue(b))||a.cn.localeCompare(b.cn,'zh'));
 return rows.map((r,i)=>({...r,value:metricValue(r),rank:i&&metricValue(rows[i-1])===metricValue(r)?rows.findIndex(x=>metricValue(x)===metricValue(r))+1:i+1}));
}
export const followKey=league=>`footballknow-followed-v1-${league}`;
export function loadFollowing(storage,league,teams) {
 try {const ids=JSON.parse(storage.getItem(followKey(league))||'[]');return Array.isArray(ids)?ids.filter(id=>teams.some(t=>t.id===id)):[];}catch{return [];}
}
export function headToHead(matches,home,away,before) {
 return matches.filter(m=>m.finished&&m.date<before&&((m.home===home&&m.away===away)||(m.home===away&&m.away===home))).sort((a,b)=>b.date.localeCompare(a.date)).slice(0,10);
}
