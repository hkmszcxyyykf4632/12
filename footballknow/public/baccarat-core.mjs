export const BET_NAMES=Object.freeze({B:'庄',P:'闲',T:'和',BP:'庄对',PP:'闲对',L6:'幸运6',L7:'幸运7'});
export const DEFAULT_RATES=Object.freeze({B:.95,P:1,T:8,BP:11,PP:11,L6two:12,L6three:20,L7:40});
export const STORAGE_KEY='fengyi.baccarat.simulation.v1';
export const cardValue=card=>card%13<9?card%13+1:0;
export const handTotal=cards=>cards.reduce((sum,c)=>sum+cardValue(c),0)%10;
export function cardLabel(card){return ['♠','♥','♣','♦'][Math.floor(card/13)%4]+['A','2','3','4','5','6','7','8','9','10','J','Q','K'][card%13];}
export function createDeck(){return Array.from({length:416},(_,i)=>i);}
export function randomBelow(n){
 const limit=Math.floor(4294967296/n)*n,buffer=new Uint32Array(1);let value;
 do{globalThis.crypto.getRandomValues(buffer);value=buffer[0];}while(value>=limit);return value%n;
}
export function shuffle(cards,choose=randomBelow){const out=[...cards];for(let i=out.length-1;i>0;i--){const j=choose(i+1);if(!Number.isInteger(j)||j<0||j>i)throw Error('洗牌随机值无效');[out[i],out[j]]=[out[j],out[i]];}return out;}
export function bankerDraw(total,third){
 if(third===null)return total<=5;
 return total<=2||total===3&&third!==8||total===4&&third>=2&&third<=7||total===5&&third>=4&&third<=7||total===6&&(third===6||third===7);
}
export function dealHand(deck,start=0){
 let cursor=start;const draw=()=>{if(cursor>=deck.length)throw Error('本靴剩余纸牌不足');return deck[cursor++];};
 const p=[draw()],b=[draw()];p.push(draw());b.push(draw());
 const pt=handTotal(p),bt=handTotal(b),natural=pt>=8||bt>=8;
 if(!natural){if(pt<=5)p.push(draw());if(bankerDraw(bt,p.length===3?cardValue(p[2]):null))b.push(draw());}
 const player=handTotal(p),banker=handTotal(b),result=banker>player?'B':banker<player?'P':'T';
 return {playerCards:p,bankerCards:b,player,banker,result,natural,bankerPair:b[0]%13===b[1]%13,playerPair:p[0]%13===p[1]%13,lucky6:result==='B'&&banker===6,lucky7:result==='P'&&player===7&&p.length===3,next:cursor};
}
export function dealShoe(deck,limit=70){const hands=[];let cursor=0;while(hands.length<limit&&cursor+4<=deck.length){try{const hand=dealHand(deck,cursor);hands.push({...hand,number:hands.length+1});cursor=hand.next;}catch{break;}}return hands;}
export function amountCents(value){const s=String(value).trim();if(!/^\d+(\.\d{1,2})?$/.test(s))throw Error('金额请输入正数，最多两位小数。');const n=Math.round(Number(s)*100);if(!Number.isSafeInteger(n)||n<=0||n>100000000)throw Error('单项金额须在 0.01 至 1,000,000 之间。');return n;}
export function validRates(rates){return Object.keys(DEFAULT_RATES).every(k=>Number.isFinite(rates?.[k])&&rates[k]>=0&&rates[k]<=1000);}
export function settleBet(hand,bet,rates=DEFAULT_RATES){
 if(!BET_NAMES[bet.type]||!Number.isInteger(bet.stake)||bet.stake<=0||bet.stake>100000000||!validRates(rates))throw Error('模拟投注资料无效');
 const push=hand.result==='T'&&['B','P'].includes(bet.type);
 const win=({B:hand.result==='B',P:hand.result==='P',T:hand.result==='T',BP:hand.bankerPair,PP:hand.playerPair,L6:hand.lucky6,L7:hand.lucky7})[bet.type];
 const rate=bet.type==='L6'?rates[hand.bankerCards.length===2?'L6two':'L6three']:rates[bet.type];
 const profit=push?0:win?Math.round(bet.stake*rate):-bet.stake;
 return {...bet,rate,status:push?'push':win?'win':'loss',profit,returned:bet.stake+profit};
}
export function settleRound(hand,bets,rates){const tickets=bets.map(b=>settleBet(hand,b,rates));return {number:hand.number,tickets,stake:tickets.reduce((s,b)=>s+b.stake,0),returned:tickets.reduce((s,b)=>s+b.returned,0),profit:tickets.reduce((s,b)=>s+b.profit,0)};}
export function ledgerTotals(rounds){const tickets=rounds.flatMap(r=>r.tickets);return {rounds:rounds.filter(r=>r.tickets.length).length,tickets:tickets.length,stake:tickets.reduce((s,b)=>s+b.stake,0),returned:tickets.reduce((s,b)=>s+b.returned,0),profit:tickets.reduce((s,b)=>s+b.profit,0),wins:tickets.filter(b=>b.status==='win').length,losses:tickets.filter(b=>b.status==='loss').length,pushes:tickets.filter(b=>b.status==='push').length};}
export function newSession(){return {version:1,id:globalThis.crypto.randomUUID(),createdAt:new Date().toISOString(),deck:shuffle(createDeck()),revealed:0,rounds:[],pending:[],rates:{...DEFAULT_RATES}};}
export function restoreSession(raw){
 const s=JSON.parse(raw);if(s?.version!==1||!Array.isArray(s.deck)||s.deck.length!==416||new Set(s.deck).size!==416||s.deck.some(c=>!Number.isInteger(c)||c<0||c>=416)||!validRates(s.rates))throw Error('本机模拟记录无法读取');
 const hands=dealShoe(s.deck);if(!Number.isInteger(s.revealed)||s.revealed<0||s.revealed>hands.length||s.rounds?.length!==s.revealed||!Array.isArray(s.pending)||s.pending.length>7)throw Error('本机模拟进度无效');
 for(const round of s.rounds)if(!Array.isArray(round.bets)||round.bets.length>7||!validRates(round.rates))throw Error('本机结算记录无效');
 s.rounds.forEach((r,i)=>settleRound(hands[i],r.bets,r.rates));s.pending.forEach(b=>settleBet(hands[0],b,s.rates));return s;
}
