import {BET_NAMES,newSession,restoreSession,dealShoe,settleRound,settleBet,validRates,cardLabel} from './baccarat-core.mjs';

export const STUDY_METHODS=['未分类','跟随连续','转向判断','单双跳','下三路','和局或附加项','其他判断'];
export function newStudySession(){
 let session;
 do{session=newSession();}while(dealShoe(session.deck).length!==70);
 session.study={version:1,selected:1,entries:[]};
 return session;
}
export function restoreStudySession(raw){
 const session=restoreSession(raw),hands=dealShoe(session.deck);
 if(!session.study){session.study={version:1,selected:1,entries:[]};return session;}
 const study=session.study;
 if(study.version!==1||!Number.isInteger(study.selected)||study.selected<1||study.selected>hands.length||!Array.isArray(study.entries)||study.entries.length>hands.length)throw Error('本机研究记录无效');
 const seen=new Set();
 for(const e of study.entries){
  if(!Number.isInteger(e.hand)||e.hand<1||e.hand>hands.length||seen.has(e.hand)||!Array.isArray(e.bets)||e.bets.length>7||new Set(e.bets.map(b=>b.type)).size!==e.bets.length||!validRates(e.rates)||!STUDY_METHODS.includes(e.method)||['reason','review'].some(k=>typeof e[k]!=='string'||e[k].length>2000))throw Error('本机研究记录无效');
  seen.add(e.hand);settleRound(hands[e.hand-1],e.bets,e.rates);
 }
 return session;
}
export function studyEntry(session,number){
 if(!Number.isInteger(number)||number<1||number>dealShoe(session.deck).length)throw Error('请选择本靴内的口数');
 let entry=session.study.entries.find(e=>e.hand===number);
 if(!entry){entry={hand:number,bets:[],rates:{...session.rates},method:'未分类',reason:'',review:''};session.study.entries.push(entry);session.study.entries.sort((a,b)=>a.hand-b.hand);}
 return entry;
}
export function recordStudyBet(session,number,bet){
 const hand=dealShoe(session.deck)[number-1];
 if(!hand)throw Error('请选择本靴内的口数');
 settleBet(hand,bet,session.rates);
 const entry=studyEntry(session,number),old=entry.bets.find(b=>b.type===bet.type);
 if(old&&old.stake+bet.stake>100000000)throw Error('同一项目累计金额超过上限。');
 if(!entry.bets.length)entry.rates={...session.rates};
 if(old)old.stake+=bet.stake;else entry.bets.push({...bet});
 return settleRound(hand,entry.bets,entry.rates);
}
export function priorContext(hands,number){
 const prior=hands.slice(0,number-1),recent=prior.slice(-10),counts={B:0,P:0,T:0};
 for(const h of recent)counts[h.result]++;
 const decisive=prior.filter(h=>h.result!=='T'),last=decisive.at(-1);let run=0;
 for(let i=decisive.length-1;i>=0&&decisive[i].result===last?.result;i--)run++;
 const streak=last?`此前庄闲主路最后一段为${BET_NAMES[last.result]} ${run} 连（和局不另起一段）`:'此前尚无庄闲胜负结果';
 const current=hands[number-1];
 const change=current.result==='T'?'本口为和局，庄闲主路不换方向':!last?'本口形成第一段庄闲结果':current.result===last.result?`本口继续开${BET_NAMES[current.result]}，延续上一段`:`本口转为${BET_NAMES[current.result]}，上一段结束`;
 return {prior,recent,counts,run,lastResult:last?.result||null,streak,change};
}
export function outcomeExplanation(hand,ticket){
 const winner=hand.result==='T'?'和局':BET_NAMES[hand.result]+'赢';
 if(['B','P','T'].includes(ticket.type))return `庄 ${hand.banker} 点、闲 ${hand.player} 点，实际${winner}；选择${BET_NAMES[ticket.type]}，${ticket.status==='push'?'遇和退回本金':ticket.status==='win'?'本项命中':'本项未中'}。`;
 if(ticket.type==='BP'||ticket.type==='PP'){
  const cards=ticket.type==='BP'?hand.bankerCards:hand.playerCards;
  return `${BET_NAMES[ticket.type]}比较首两张的牌面：${cards.slice(0,2).map(cardLabel).join('、')}，${cards[0]%13===cards[1]%13?'相同，命中对子':'不同，未中对子'}。`;
 }
 if(ticket.type==='L6')return `实际${winner}，庄 ${hand.banker} 点、${hand.bankerCards.length} 张牌；${hand.lucky6?'符合庄家 6 点获胜条件':'未同时符合庄家获胜及 6 点的条件'}。`;
 return `实际${winner}，闲 ${hand.player} 点、${hand.playerCards.length} 张牌；${hand.lucky7?'符合闲家三张牌 7 点获胜条件':'未同时符合闲家获胜、三张牌及 7 点的条件'}。`;
}
export function studyRounds(session,hands){return session.study.entries.filter(e=>e.bets.length).map(e=>({...settleRound(hands[e.hand-1],e.bets,e.rates),entry:e}));}
