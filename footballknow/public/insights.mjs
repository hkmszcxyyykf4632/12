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

const GROUPS={scores:'比分与赛程',catalogue:'球队与球员',history:'转会与领队',names:'中文姓名',rankings:'积分与球员榜',lineups:'阵容与技术统计',odds:'赔率',news:'球队新闻',profiles:'球队背景'};
const KINDS={live:['比分与赛程','scores'],catalogue:['球队与球员','catalogue'],history:['转会与领队','history'],names:['中文姓名','names'],
  standings:['积分榜','rankings'],leaders:['射手、助攻与纪律榜','rankings'],lineups:['阵容与技术统计','lineups'],odds:['赔率快照','odds'],news:['球队新闻','news'],profiles:['背景与持有人','profiles']};

/** Readable name and category for a synchronizer job id such as "laliga-standings". */
export function describeJob(name,group='') {
  if(name.startsWith('racing-'))return {league:'香港赛马',label:({meetings:'排位与赛果',catalogue:'现役马匹目录',horses:'血统与往绩'})[name.slice(7)]||name,group:'赛马资料'};
  if(name.startsWith('finance-'))return {league:'市场',label:({quotes:'港股报价',assets:'黄金、原油与比特币',companies:'公司与财务',history:'历史价格',evaluation:'预测验证',catalogue:'全港股目录'})[name.slice(8)]||name,group:'市场资料'};
  if(name==='odds-official-checks')return {league:'全部赛事',label:'书商官网可访问性检查',group:GROUPS.odds};
  const parts=name.split('-'),prefixed=['epl','laliga','ucl','seriea','bundesliga'].includes(parts[0])&&parts.length>1;
  const [label,kind]=KINDS[prefixed?parts.slice(1).join('-'):name]||[name,group];
  return {league:{epl:'英超',laliga:'西甲',ucl:'欧冠',seriea:'意甲',bundesliga:'德甲'}[prefixed?parts[0]:'epl'],label,group:GROUPS[group||kind]||'其他'};
}

export function statusSummary(status,now=Date.now()) {
  const jobs=Object.values(status?.jobs||{});
  const summary=status?.summary||{total:jobs.length,ok:jobs.filter(j=>j.ok===true).length,failed:jobs.filter(j=>j.ok===false).length,pending:jobs.filter(j=>j.ok==null).length};
  const age=now-Date.parse(status?.heartbeat);
  const alive=Boolean(status?.running)&&Number.isFinite(age)&&age<120000;
  return {...summary,alive,level:!alive?'down':status.paused?'warn':summary.failed?'warn':'ok',
    text:!alive?'同步服务未运行，或心跳已超过两分钟':status.paused?'管理员已暂停同步，显示最近成功资料':summary.failed?`${summary.ok} 项正常，${summary.failed} 项失败并自动重试`:summary.pending?`${summary.ok} 项正常，${summary.pending} 项等待首次同步`:`全部 ${summary.total} 项同步正常`};
}

// ---- Season, player and data-quality calculations ----

/** Home, away and overall record of one club in one competition season, from confirmed results only. */
export function teamSeason(matches,name,competition,season) {
  const blank=()=>({played:0,wins:0,draws:0,losses:0,goalsFor:0,goalsAgainst:0,cleanSheets:0,failedToScore:0});
  const record={all:blank(),home:blank(),away:blank()};
  for(const m of matches) {
    if(!m.finished||m.competition!==competition||m.season!==season||!Number.isInteger(m.homeGoals)||!Number.isInteger(m.awayGoals))continue;
    const side=m.home===name?'home':m.away===name?'away':null;
    if(!side)continue;
    const scored=side==='home'?m.homeGoals:m.awayGoals,conceded=side==='home'?m.awayGoals:m.homeGoals;
    for(const row of [record.all,record[side]]) {
      row.played++;row.goalsFor+=scored;row.goalsAgainst+=conceded;
      row[scored>conceded?'wins':scored<conceded?'losses':'draws']++;
      row.cleanSheets+=Number(conceded===0);row.failedToScore+=Number(scored===0);
    }
  }
  return record;
}

export function ageOn(birth,now=Date.now()) {
  const born=new Date(birth),today=new Date(now);
  if(!birth||Number.isNaN(born.getTime()))return null;
  const age=today.getFullYear()-born.getFullYear()-Number(today.getMonth()<born.getMonth()||today.getMonth()===born.getMonth()&&today.getDate()<born.getDate());
  return age>=14&&age<=60?age:null;
}

/** Ranked rows for one numeric field; equal values share a rank and rows without the figure are left out. */
export function boardRows(rows,value,{limit=50,ascending=false}={}) {
  const scored=rows.map(row=>({row,value:Number(value(row))})).filter(item=>Number.isFinite(item.value)&&item.value>0)
    .sort((a,b)=>ascending?a.value-b.value:b.value-a.value).slice(0,limit);
  let rank=0;
  return scored.map((item,index)=>{if(index===0||item.value!==scored[index-1].value)rank=index+1;return {...item,rank};});
}

/** Kelly index per bookmaker: its price times the average margin-free probability of all listed bookmakers. */
export function kellyRows(quotes) {
  const groups=new Map();
  for(const quote of quotes||[]) {
    const p=impliedProbabilities(quote);
    if(!p||quote.kind==='aggregate'||quote.market&&quote.market!=='90-minute-1x2')continue;
    const phase=quote.phase||'',group=groups.get(phase)||new Map(),prior=group.get(quote.provider);
    if(!prior||String(quote.fetchedAt||'')>=String(prior.quote.fetchedAt||''))group.set(quote.provider,{quote,p});
    groups.set(phase,group);
  }
  return [...groups].flatMap(([phase,group])=>{
    const priced=[...group.values()];if(priced.length<2)return [];
    const mean=key=>priced.reduce((sum,item)=>sum+item.p[key],0)/priced.length;
    const average={H:mean('H'),D:mean('D'),A:mean('A')};
    return priced.map(({quote})=>({provider:quote.provider+(phase?` · ${phase}`:''),H:quote.H*average.H,D:quote.D*average.D,A:quote.A*average.A}));
  });
}

/** Opening and latest price per provider from the recorded movement. */
export function priceMovement(rows) {
  const providers=new Map();
  for(const row of rows||[]) {
    const key=JSON.stringify([row.provider,row.phase||'采集快照',row.via||'']);
    const label=[row.provider,row.phase,row.via].filter(Boolean).join(' · ');
    const entry=providers.get(key)||{provider:label,opening:row,latest:row,points:[]};
    entry.latest=row;entry.points.push(row);providers.set(key,entry);
  }
  return [...providers.values()];
}

export function matchDetailMatches(detail,match,league) {
  if(!detail||detail.matchId!==match.id||detail.league!==league)return false;
  if(detail.status!=='available'&&!detail.home&&!detail.away)return true;
  return ['home','away'].every(side=>detail[side]===match[side]&&(!detail.lineups?.[side]||detail.lineups[side].name===match[side]));
}

/** Announcements for followed clubs between two refreshes: kick-off, goal, full time. */
export function matchAlerts(before,after,clubs,label=name=>name) {
  const old=new Map((before||[]).map(m=>[m.id,m])),alerts=[];
  for(const m of after||[]) {
    const prior=old.get(m.id);
    if(!prior||!clubs.includes(m.home)&&!clubs.includes(m.away))continue;
    const pair=`${label(m.home)} ${m.homeGoals??0} : ${m.awayGoals??0} ${label(m.away)}`;
    if(!prior.started&&m.started&&!m.finished)alerts.push({kind:'start',matchId:m.id,title:'比赛开始',text:`${label(m.home)} vs ${label(m.away)}`});
    else if(prior.started&&!prior.finished&&!m.finished&&(prior.homeGoals!==m.homeGoals||prior.awayGoals!==m.awayGoals)) {
      const scorer=(m.homeGoals??0)>(prior.homeGoals??0)?m.home:(m.awayGoals??0)>(prior.awayGoals??0)?m.away:null;
      alerts.push({kind:'goal',matchId:m.id,title:scorer?`${label(scorer)}进球`:'比分更正',text:pair});
    }
    if(!prior.finished&&m.finished&&prior.started)alerts.push({kind:'final',matchId:m.id,title:'比赛结束',text:pair});
  }
  return alerts;
}

/** Field coverage and records that look wrong, so gaps are stated instead of hidden. */
export function qualityReport({data,names,facts,competition,now=Date.now()}) {
  const players=data.players,season=data.matches.filter(m=>m.competition===competition&&m.season===data.season);
  const done=season.filter(m=>m.finished);
  const share=(label,filled,total,note='')=>({label,filled,total,note});
  const fields=[
    share('球员中文译名（已核对来源）',players.filter(p=>names?.names?.[String(p.code)]).length,players.length),
    share('球员出生日期',players.filter(p=>p.birth_date).length,players.length),
    share('球员国籍',players.filter(p=>p.country).length,players.length),
    share('球员球衣号码',players.filter(p=>p.squad_number!=null&&p.squad_number!=='').length,players.length),
    share('球员本赛季出场分钟',players.filter(p=>p.minutes!=null).length,players.length),
    share('已完赛比赛的比分',done.filter(m=>Number.isInteger(m.homeGoals)&&Number.isInteger(m.awayGoals)).length,done.length),
    share('未开赛比赛的开球时间',season.filter(m=>!m.finished&&m.kickoff).length,season.filter(m=>!m.finished).length),
    share('已完赛比赛的赔率',done.filter(m=>m.odds?.length).length,done.length),
    share('已完赛比赛的阵容与技术统计',facts?Math.min(facts.coveredMatches,done.length):0,done.length,facts?'':'汇总尚未生成'),
    share('可核对的半场比分',facts?done.filter(m=>facts.matches?.[m.id]?.halfTime).length:0,done.length,'仅在事件进球数与终场比分一致时给出'),
  ];
  const anomalies=[],seen=new Map();
  for(const m of season) {
    const pair=`${m.date} ${m.home} vs ${m.away}`;
    if(m.finished&&(!Number.isInteger(m.homeGoals)||!Number.isInteger(m.awayGoals)))anomalies.push({matchId:m.id,text:`${pair}：已完赛但缺少比分`});
    else if(m.finished&&(m.homeGoals>12||m.awayGoals>12))anomalies.push({matchId:m.id,text:`${pair}：比分 ${m.homeGoals}:${m.awayGoals} 超出常见范围，需要核对`});
    if(m.finished&&Number.isInteger(m.homeGoals)&&m.result&&m.result!==(m.homeGoals>m.awayGoals?'H':m.homeGoals<m.awayGoals?'A':'D'))anomalies.push({matchId:m.id,text:`${pair}：胜平负标记与比分不一致`});
    if(m.started&&!m.finished&&m.kickoff&&now-Date.parse(m.kickoff)>4*3600000)anomalies.push({matchId:m.id,text:`${pair}：开球超过 4 小时仍显示进行中`});
    if(!m.started&&!m.finished&&m.kickoff&&now-Date.parse(m.kickoff)>3*3600000)anomalies.push({matchId:m.id,text:`${pair}：已过开球时间 3 小时仍未开始，可能延期`});
    if(m.home===m.away)anomalies.push({matchId:m.id,text:`${pair}：主客队相同`});
    const key=`${m.date}|${m.home}|${m.away}`;
    if(seen.has(key))anomalies.push({matchId:m.id,text:`${pair}：同一天同对阵出现两次`});
    seen.set(key,true);
  }
  return {fields,anomalies};
}

/** Corner points of a radar polygon; shares are 0..1 and the first axis points up. */
export function radarPoints(shares,radius,cx=radius,cy=radius) {
  return shares.map((share,index)=>{
    const angle=-Math.PI/2+index*2*Math.PI/shares.length,r=radius*Math.max(0,Math.min(1,share));
    return `${(cx+r*Math.cos(angle)).toFixed(1)},${(cy+r*Math.sin(angle)).toFixed(1)}`;
  }).join(' ');
}

const EVENT_TEXT={goal:(a,b)=>`${a}破门${b?`，${b}助攻`:''}`,'penalty---scored':a=>`${a}主罚点球命中`,'own-goal':a=>`${a}打入乌龙球`,
  'yellow-card':a=>`${a}被出示黄牌`,'red-card':a=>`${a}被红牌罚下`,'yellow-red-card':a=>`${a}第二张黄牌，被罚下`,
  substitution:(a,b)=>b?`${a}上场，换下${b}`:`${a}换人上场`,'penalty---missed':a=>`${a}点球未进`};

/** One line describing a match event in the site's own words, from the structured event only. */
export function eventSentence(event,name=p=>p.name) {
  const people=(event.players||[]).map(name);
  return (EVENT_TEXT[event.type]||(()=>event.label||''))(people[0]||'球员',people[1]||'');
}
