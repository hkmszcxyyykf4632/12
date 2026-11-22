export const competitions=[['epl','英超'],['laliga','西甲'],['seriea','意甲'],['bundesliga','德甲'],['ucl','欧冠']];
export const poolNames={WIN:'独赢',PLA:'位置',QIN:'连赢',QPL:'位置连赢'};
export const rate=(hits,n)=>n?`${(hits/n*100).toFixed(1)}%`:'—';
export const percent=(hits,n)=>n?100*hits/n:0;
export function footballSelection(records,stage='adopted'){
  const groups=new Map();
  for(const r of records){
    if(stage!=='adopted'&&r.stage!==stage)continue;
    const key=r.league+':'+r.eventId;
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(r);
  }
  return [...groups.values()].map(rows=>rows.sort((a,b)=>Number(b.status!=='excluded')-Number(a.status!=='excluded')||Number(b.stage==='final')-Number(a.stage==='final')||b.issuedAt.localeCompare(a.issuedAt))[0]);
}
export function footballTotals(rows){
  const settled=rows.filter(r=>r.status==='settled'),asian=settled.filter(r=>['赢盘','赢半','输半','输盘'].includes(r.asianResult));
  const count=value=>settled.filter(r=>r.asianResult===value).length;
  return {total:rows.length,settled:settled.length,pending:rows.filter(r=>r.status==='pending').length,
    excluded:rows.filter(r=>['excluded','void'].includes(r.status)).length,
    exact:settled.filter(r=>r.exactHit===true).length,result:settled.filter(r=>r.resultHit===true).length,
    asian:asian.length,asianHits:count('赢盘')+count('赢半'),win:count('赢盘'),halfWin:count('赢半'),push:count('走盘'),
    halfLoss:count('输半'),loss:count('输盘'),unselected:count('unselected'),unverified:count('unverified')};
}
export const paperUnit=type=>['WIN','PLA'].includes(type)?100:10;
export function poolTotals(rows,type){
  const unit=paperUnit(type);let planned=0,pendingStake=0;
  let races=0,hits=0,pending=0,refunds=0,tickets=0,winningTickets=0,returns=0;
  for(const r of rows){
    if(r.status==='excluded')continue;
    const all=r.pools.find(p=>p.type===type)?.tickets||[];
    planned+=all.length*unit;
    refunds+=all.filter(t=>t.status==='refund').length;
    if(r.status==='void')continue;
    if(!all.length||all.some(t=>t.status==='pending')){pending++;pendingStake+=all.filter(t=>t.status!=='refund').length*unit;continue;}
    const valid=all.filter(t=>t.status==='hit'||t.status==='miss');
    if(!valid.length)continue;
    races++;hits+=Number(valid.some(t=>t.status==='hit'));tickets+=valid.length;
    winningTickets+=valid.filter(t=>t.status==='hit').length;
    returns+=valid.reduce((n,t)=>n+(t.dividend??0)/10*unit,0);
  }
  const stake=tickets*unit;
  return {races,hits,pending,refunds,tickets,winningTickets,stake,returns,planned,pendingStake,refundAmount:refunds*unit,net:returns-stake,multiple:stake?returns/stake:null};
}
export function byDay(rows){
  const groups=new Map();
  for(const r of rows){if(!groups.has(r.day))groups.set(r.day,[]);groups.get(r.day).push(r);}
  return [...groups.entries()].sort(([a],[b])=>b.localeCompare(a));
}
export function celebrations(football,racing){
  const items=[];
  for(const [round,rows] of byRound(footballSelection(football))){
    const t=footballTotals(rows),day=rows.map(r=>r.day).sort().at(-1);
    if(t.pending||!rows.every(r=>r.round&&r.roundComplete))continue;
    for(const [label,hits,n] of [['比分',t.exact,t.settled],['亚洲盘',t.asianHits,t.asian]])
      if(n&&hits/n>.8)items.push({key:`football:${round}:${label}`,day,title:`足球${label}命中率 ${rate(hits,n)}`,text:`${round} · ${hits} / ${n} 场有效预测${n<10?' · 小样本':''}`,href:'#/football-statistics',kind:'rate'});
  }
  for(const [day,rows] of byDay(racing)){
    if(rows.some(r=>r.status==='pending'||!r.meetingComplete))continue;
    for(const type of Object.keys(poolNames)){
      const t=poolTotals(rows,type);
      if(!t.pending&&t.races&&t.hits/t.races>.8)items.push({key:`racing:${day}:${type}`,day,title:`赛马${poolNames[type]}命中率 ${rate(t.hits,t.races)}`,text:`${t.hits} / ${t.races} 场 · 原推荐名单${t.races<10?' · 小样本':''}`,href:'#/racing-statistics',kind:'rate'});
    }
  }
  for(const r of racing.filter(r=>r.status==='settled'))for(const p of r.pools){
    const threshold=({WIN:10,QIN:50})[p.type];if(!threshold)continue;
    for(const t of p.tickets.filter(t=>t.status==='hit'&&t.multiple>=threshold)){
      const names=t.combination.split(',').map(no=>{const h=r.runners.find(h=>Number(h.number)===Number(no));return `${no}号 ${h?.name||'马名未核实'}`;}).join(' ＋ ');
      items.push({key:r.raceId+':'+p.type+':'+t.combination,day:r.day,title:`${p.type==='WIN'?'冷门独赢':'高派彩连赢'}命中 · ${t.multiple.toFixed(2)}倍`,
        text:`${r.courseName} 第${r.raceNo}场 · ${names} · 每10元派${t.dividend.toFixed(2)}元（含本金）`,href:'#/race/'+encodeURIComponent(r.raceId),kind:'payout'});
    }
  }
  return items.sort((a,b)=>b.day.localeCompare(a.day)||Number(b.kind==='payout')-Number(a.kind==='payout'));
}

export function byRound(rows){
 const groups=new Map();
 for(const r of rows){const name=competitions.find(x=>x[0]===r.league)?.[1]||r.league,key=name+' '+(r.season||'')+' '+(r.round||'轮次尚未核实');if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r);}
 return [...groups.entries()].sort((a,b)=>b[1].map(r=>r.day).sort().at(-1).localeCompare(a[1].map(r=>r.day).sort().at(-1)));
}

export function paperTotals(rows){
 const pools=Object.keys(poolNames).map(p=>poolTotals(rows,p));
 const sum=k=>pools.reduce((n,p)=>n+p[k],0);
 return {planned:sum('planned'),stake:sum('stake'),refunds:sum('refundAmount'),returns:sum('returns'),net:sum('net'),pending:sum('pendingStake')};
}
export function footballPaper(row){
 const units=[{type:'亚洲盘',stake:row.asianSide==='pass'?0:100,price:row.asianPrice,outcome:row.asianResult},
  {type:'比分',stake:50,price:row.scorePrice,outcome:row.exactHit?'赢盘':'输盘'}];
 return units.map(u=>{
  if(row.status==='excluded')return {...u,status:'excluded',returned:null};
  if(!u.stake)return {...u,status:'skip',returned:0};
  if(row.status==='void')return {...u,status:'refund',returned:u.stake};
  if(!Number.isFinite(u.price)||u.price<=1)return {...u,status:'unpriced',returned:null};
  if(row.status!=='settled'||!['赢盘','赢半','走盘','输半','输盘'].includes(u.outcome))return {...u,status:'pending',returned:null};
  const fraction=({'赢盘':u.price,'赢半':(u.price+1)/2,'走盘':1,'输半':.5,'输盘':0})[u.outcome];
  return {...u,status:'settled',returned:Math.round(u.stake*fraction*100)/100};
 });
}
export function footballPaperTotals(rows){
 const bets=rows.flatMap(footballPaper),settled=bets.filter(b=>b.status==='settled'),sum=(list,key)=>list.reduce((n,b)=>n+(b[key]??0),0);
 const stake=sum(settled,'stake'),returns=sum(settled,'returned');
 return {planned:sum(bets.filter(b=>b.status!=='excluded'),'stake'),stake,returns,net:returns-stake,
  refunds:sum(bets.filter(b=>b.status==='refund'),'stake'),pending:sum(bets.filter(b=>['pending','unpriced'].includes(b.status)),'stake'),
  unpriced:bets.filter(b=>b.status==='unpriced').length};
}
