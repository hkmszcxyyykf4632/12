import test from 'node:test';
import assert from 'node:assert/strict';
import {createDeck,shuffle,dealHand,dealShoe,bankerDraw,DEFAULT_RATES,amountCents,settleBet,settleRound,ledgerTotals,newSession,restoreSession} from '../public/baccarat-core.mjs';
import {bigRoad,derivedRoad,roadProbe,placeRoad} from '../public/baccarat-roads.mjs';
const hands=s=>[...s].map((result,i)=>({result,number:i+1}));
test('8 decks contain each suit/rank eight times and deals never replace a card',()=>{
 const deck=createDeck();assert.equal(deck.length,416);assert.equal(new Set(deck).size,416);for(let c=0;c<52;c++)assert.equal(deck.filter(x=>x%52===c).length,8);
 for(let seed=1;seed<=30;seed++){let n=seed;const shuffled=shuffle(deck,max=>{n=(Math.imul(n,1664525)+1013904223)>>>0;return n%max;});const h=dealShoe(shuffled);assert.equal(h.length,70);const cards=h.flatMap(r=>[...r.playerCards,...r.bankerCards]);assert.equal(new Set(cards).size,cards.length);assert.equal(cards.length,h.at(-1).next);}
});
test('third card table agrees with all 88 banker/player-third combinations',()=>{
 const expected=['0123456789','0123456789','0123456789','012345679','234567','4567','67',''];
 for(let b=0;b<=7;b++){assert.equal(bankerDraw(b,null),b<=5);for(let p=0;p<=9;p++)assert.equal(bankerDraw(b,p),expected[b].includes(String(p)),`banker ${b}, player third ${p}`);}
});
test('naturals, rank pairs and Lucky 6/7 use dealt cards and final winner',()=>{
 const natural=dealHand([3,8,3,0,4,5]);assert.equal(natural.next,4);assert.equal(natural.result,'P');assert.ok(natural.playerPair);
 const seven=dealHand([1,4,1,9,2]);assert.equal(seven.result,'P');assert.equal(seven.player,7);assert.equal(seven.playerCards.length,3);assert.ok(seven.lucky7);
 const six=dealHand([1,2,2,2,9]);assert.ok(six.lucky6);assert.equal(six.bankerCards.length,2);
 const threeSix=dealHand([9,1,2,1,1,1]);assert.ok(threeSix.lucky6);assert.equal(threeSix.bankerCards.length,3);
 const unequalFaces=dealHand([10,3,11,4]);assert.equal(unequalFaces.playerPair,false);
 const tie={...seven,result:'T',lucky7:false};assert.equal(settleBet(tie,{type:'L7',stake:10000}).status,'loss');
 assert.throws(()=>dealHand([0,0,0,0]),/不足/);
});
test('settlement includes returned principal, commission, tie pushes and independent side bets',()=>{
 const h=dealHand([1,2,2,2,9]);const r=settleRound(h,[{type:'B',stake:10000},{type:'P',stake:10000},{type:'BP',stake:1000},{type:'L6',stake:1000}],DEFAULT_RATES);
 assert.deepEqual(r.tickets.map(x=>x.profit),[9500,-10000,11000,12000]);assert.equal(r.profit,22500);assert.equal(r.returned,44500);
 const push=settleBet({...h,result:'T'},{type:'B',stake:12345});assert.equal(push.returned,12345);assert.equal(push.profit,0);assert.equal(push.status,'push');
 assert.equal(settleBet(h,{type:'B',stake:1}).profit,1);assert.equal(ledgerTotals([r]).stake,22000);
 assert.equal(amountCents('12.34'),1234);for(const value of ['-1','0','NaN','1e6','1.999','1000001'])assert.throws(()=>amountCents(value));
});
test('big road ignores tie advancement, retains initial ties and turns at six rows without collisions',()=>{
 const road=bigRoad(hands('TTBBBBBBBTTPPPPPPP'));assert.equal(road.cells.length,14);assert.equal(road.cells[0].ties,2);assert.equal(road.cells[6].ties,2);assert.deepEqual([road.cells[6].col,road.cells[6].row],[1,5]);assert.deepEqual([road.cells[7].col,road.cells[7].row],[1,0]);assert.equal(new Set(road.cells.map(c=>c.col+':'+c.row)).size,14);
 assert.equal(bigRoad(hands('TTT')).initialTies,3);
});
test('derived roads compare logical streak depths, including dragon tails, rather than banker/player colors',()=>{
 const sample=hands('BBPPBPPPBBBP');
 assert.deepEqual(derivedRoad(sample,1).map(x=>x.color),['red','red','blue','blue','red','blue','red','red','red']);
 assert.deepEqual(derivedRoad(sample,2).map(x=>x.color),['blue','red','blue','blue','blue','red','blue']);
 for(const offset of [1,2,3])assert.deepEqual(derivedRoad(hands('BBTPPBTPPPBBBP'),offset).map(x=>x.color),derivedRoad(sample,offset).map(x=>x.color));
 assert.equal(derivedRoad(hands('BBBBBBBBPPPPPPPP'),1).at(-1).color,'red');
 assert.deepEqual(roadProbe(hands('BP'),'B'),['red',null,null]);assert.deepEqual(roadProbe(hands('BP'),'P'),['blue',null,null]);
 assert.equal(placeRoad(Array.from({length:70},()=>({color:'red'}))).length,70);
});
test('saved shoe preserves pending bets and historical rates and rejects corrupted cards',()=>{
 const session=newSession(),all=dealShoe(session.deck);session.pending=[{type:'B',stake:10000}];session.revealed=1;session.rounds=[{bets:[{type:'P',stake:5000}],rates:{...DEFAULT_RATES}}];session.rates.P=2;
 const restored=restoreSession(JSON.stringify(session));assert.equal(restored.rates.P,2);assert.equal(restored.rounds[0].rates.P,1);assert.deepEqual(dealShoe(restored.deck),all);assert.equal(restored.pending[0].stake,10000);
 session.deck[0]=session.deck[1];assert.throws(()=>restoreSession(JSON.stringify(session)));assert.throws(()=>restoreSession('{'));
});
