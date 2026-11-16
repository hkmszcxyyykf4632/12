// Pure calculations shared by the dashboard, match and comparison pages.

/** Bookmaker prices to probabilities with the margin removed proportionally; null unless all three prices are valid. */
export function impliedProbabilities(quote) {
  const prices=['H','D','A'].map(key=>Number(quote?.[key]));
  if(!prices.every(price=>Number.isFinite(price)&&price>1))return null;
  const raw=prices.map(price=>1/price),total=raw[0]+raw[1]+raw[2];
  return {H:raw[0]/total,D:raw[1]/total,A:raw[2]/total,margin:total-1};
}

export function seasonStats(matches,competition,season,now=Date.now()) {
  const rows=matches.filter(m=>m.competition===competition&&m.season===season);
  const done=rows.filter(m=>m.finished&&Number.isInteger(m.homeGoals)&&Number.isInteger(m.awayGoals));
  const goals=done.reduce((sum,m)=>sum+m.homeGoals+m.awayGoals,0);
  const count=key=>done.filter(m=>m.result===key).length;
  const day=new Date(now),local=m=>{const d=new Date(m.kickoff);return d.getFullYear()===day.getFullYear()&&d.getMonth()===day.getMonth()&&d.getDate()===day.getDate();};
  return {total:rows.length,played:done.length,goals,average:done.length?goals/done.length:null,
    home:count('H'),draw:count('D'),away:count('A'),
    live:rows.filter(m=>m.started&&!m.finished).length,today:rows.filter(m=>m.kickoff&&local(m)).length};
}

/** The match to lead with: one in play, otherwise the next kickoff. */
export function leadMatch(matches,competition,season,now=Date.now()) {
  const rows=matches.filter(m=>m.competition===competition&&m.season===season);
  return rows.find(m=>m.started&&!m.finished)
    ||rows.filter(m=>!m.started&&!m.finished&&m.kickoff&&Date.parse(m.kickoff)>now).sort((a,b)=>a.kickoff.localeCompare(b.kickoff))[0]||null;
}

export function countdownText(kickoff,now=Date.now()) {
  const minutes=Math.floor((Date.parse(kickoff)-now)/60000);
  if(!Number.isFinite(minutes)||minutes<0)return '';
  const days=Math.floor(minutes/1440),hours=Math.floor(minutes%1440/60);
  return days?`${days} 天 ${hours} 小时`:hours?`${hours} 小时 ${minutes%60} 分钟`:`${Math.max(1,minutes)} 分钟`;
}

/** Side-by-side figures for two standings rows; `better` says which direction wins the row. */
export function comparisonRows(a,b) {
  const perGame=row=>row.played?row.goalsFor/row.played:0;
  const spec=[['排名','rank','low',0],['积分','points','high',0],['已赛','played','none',0],['胜','wins','high',0],['平','draws','none',0],['负','losses','low',0],
    ['进球','goalsFor','high',0],['失球','goalsAgainst','low',0],['净胜球','goalDifference','high',0],['零封','cleanSheets','high',0]];
  const rows=spec.filter(([,key])=>Number.isFinite(a[key])&&Number.isFinite(b[key])).map(([label,key,better,digits])=>({label,left:a[key],right:b[key],better,digits}));
  rows.push({label:'场均进球',left:perGame(a),right:perGame(b),better:'high',digits:2});
  return rows.map(row=>{
    const lead=row.better==='none'||row.left===row.right?'':((row.left>row.right)===(row.better==='high'))?'left':'right';
    const scale=Math.max(Math.abs(row.left),Math.abs(row.right))||1;
    return {...row,lead,leftShare:Math.abs(row.left)/scale,rightShare:Math.abs(row.right)/scale};
  });
}

const GROUPS={scores:'比分与赛程',catalogue:'球队与球员',history:'转会与领队',names:'中文姓名',rankings:'积分与球员榜',lineups:'阵容与技术统计',odds:'赔率'};
const KINDS={live:['比分与赛程','scores'],catalogue:['球队与球员','catalogue'],history:['转会与领队','history'],names:['中文姓名','names'],
  standings:['积分榜','rankings'],leaders:['射手、助攻与纪律榜','rankings'],lineups:['阵容与技术统计','lineups'],odds:['赔率快照','odds']};

/** Readable name and category for a synchronizer job id such as "laliga-standings". */
export function describeJob(name,group='') {
  if(name==='odds-official-checks')return {league:'全部赛事',label:'书商官网可访问性检查',group:GROUPS.odds};
  const parts=name.split('-'),prefixed=['epl','laliga','ucl'].includes(parts[0])&&parts.length>1;
  const [label,kind]=KINDS[prefixed?parts.slice(1).join('-'):name]||[name,group];
  return {league:{epl:'英超',laliga:'西甲',ucl:'欧冠'}[prefixed?parts[0]:'epl'],label,group:GROUPS[group||kind]||'其他'};
}

export function statusSummary(status,now=Date.now()) {
  const jobs=Object.values(status?.jobs||{});
  const summary=status?.summary||{total:jobs.length,ok:jobs.filter(j=>j.ok===true).length,failed:jobs.filter(j=>j.ok===false).length,pending:jobs.filter(j=>j.ok==null).length};
  const age=now-Date.parse(status?.heartbeat);
  const alive=Boolean(status?.running)&&Number.isFinite(age)&&age<120000;
  return {...summary,alive,level:!alive?'down':summary.failed?'warn':'ok',
    text:!alive?'同步服务未运行，或心跳已超过两分钟':summary.failed?`${summary.ok} 项正常，${summary.failed} 项失败并自动重试`:summary.pending?`${summary.ok} 项正常，${summary.pending} 项等待首次同步`:`全部 ${summary.total} 项同步正常`};
}
