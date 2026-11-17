export function orderedEvents(events=[]){
  const clock=e=>{const parts=String(e.clock||'').match(/\d+/g)||[];return [Number(parts[0]||0),Number(parts[1]||0)];};
  return events.map((event,index)=>({event,index})).sort((a,b)=>{
    const x=clock(a.event),y=clock(b.event);
    return (a.event.period||1)-(b.event.period||1)||x[0]-y[0]||x[1]-y[1]||a.index-b.index;
  }).map(item=>item.event);
}

export function opponentRecords(matches,name,{minimum=3,now=Date.now()}={}){
  const seen=new Set(),groups=new Map();
  for(const m of matches){
    if(!m.finished||![m.home,m.away].includes(name)||!Number.isInteger(m.homeGoals)||!Number.isInteger(m.awayGoals)||m.homeGoals<0||m.awayGoals<0||Date.parse(m.kickoff||m.date)>now)continue;
    const key=[m.season,m.competition,m.date,m.home,m.away].join('|');if(seen.has(key))continue;seen.add(key);
    const home=m.home===name,opponent=home?m.away:m.home;
    const r=groups.get(opponent)||{name:opponent,played:0,wins:0,draws:0,losses:0,goals:0,conceded:0,latest:''};
    const gf=home?m.homeGoals:m.awayGoals,ga=home?m.awayGoals:m.homeGoals;
    r.played++;r.goals+=gf;r.conceded+=ga;r.wins+=Number(gf>ga);r.draws+=Number(gf===ga);r.losses+=Number(gf<ga);
    if(m.date>r.latest)r.latest=m.date;groups.set(opponent,r);
  }
  const rows=[...groups.values()].filter(r=>r.played>=minimum).map(r=>({...r,winRate:r.wins/r.played,lossRate:r.losses/r.played}));
  return {difficult:rows.filter(r=>r.losses>r.wins).sort((a,b)=>b.lossRate-a.lossRate||b.played-a.played).slice(0,5),
    favourable:rows.filter(r=>r.wins>r.losses).sort((a,b)=>b.winRate-a.winRate||b.played-a.played).slice(0,5),
    minimum,opponents:groups.size};
}

export function transferPattern(rows,name){
  const seen=new Set(),unique=rows.filter(r=>{const key=[r.date,r.player,r.fromTeam,r.toTeam,r.type].join('|');if(seen.has(key))return false;seen.add(key);return true;});
  const incoming=unique.filter(r=>r.toTeam===name),outgoing=unique.filter(r=>r.fromTeam===name);
  const count=(items,test)=>items.filter(test).length;
  const partners=new Map();for(const r of incoming){if(r.fromTeam&&!['Unattached','无所属','自由球员'].includes(r.fromTeam))partners.set(r.fromTeam,(partners.get(r.fromTeam)||0)+1);}
  return {incoming:incoming.length,outgoing:outgoing.length,loanIn:count(incoming,r=>/租借/.test(r.type)),
    freeIn:count(incoming,r=>/自由/.test(r.type)),loanOut:count(outgoing,r=>/租借/.test(r.type)),
    undisclosed:count([...incoming,...outgoing],r=>!r.fee||/未公开|未知|undisclosed/i.test(r.fee)),
    partners:[...partners].sort((a,b)=>b[1]-a[1]).slice(0,3),first:[...incoming,...outgoing].map(r=>r.date).filter(Boolean).sort()[0]||null};
}

export function matchRecap(match,detail,home,away){
  if(!match.finished||!Number.isInteger(match.homeGoals)||!Number.isInteger(match.awayGoals))return [];
  const outcome=match.homeGoals===match.awayGoals?'双方战平':(match.homeGoals>match.awayGoals?home:away)+'获胜';
  const first=home+' '+match.homeGoals+' : '+match.awayGoals+' '+away+'，'+outcome+'。比分按90分钟含补时统计。';
  const events=detail?.events||[],red=events.filter(e=>['red-card','yellow-red-card'].includes(e.type)).length,subs=events.filter(e=>e.type==='substitution').length;
  const stats=Object.fromEntries((detail?.statistics||[]).map(s=>[s.side,s.values]));
  const shots=[stats.home?.shotsOnTarget,stats.away?.shotsOnTarget];
  const context=shots.every(v=>v!==null&&v!==undefined&&Number.isFinite(Number(v)))?'射正 '+shots[0]+' : '+shots[1]+'。':'';
  return [first,context+(events.length?'已收录事件中有 '+subs+' 次换人、'+red+' 次红牌或两黄变红；详细时间与球员见事件时间线。':'比赛事件待来源补充。')];
}
