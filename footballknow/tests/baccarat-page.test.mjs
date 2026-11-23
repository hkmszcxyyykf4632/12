import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {createDeck,DEFAULT_RATES,STORAGE_KEY,dealShoe} from '../public/baccarat-core.mjs';
import {restoreStudySession,priorContext,recordStudyBet} from '../public/baccarat-study.mjs';
import {derivedRoad} from '../public/baccarat-roads.mjs';
const dom=new JSDOM('<main id="main"></main>',{url:'https://example.test/#/baccarat'});
Object.assign(globalThis,{document:dom.window.document,window:dom.window,location:dom.window.location,localStorage:dom.window.localStorage,FormData:dom.window.FormData});
const {renderBaccarat}=await import('../public/baccarat-page.mjs');
const q=s=>document.querySelector(s),click=s=>q(s).click();
function set(selector,value,event='input'){q(selector).value=value;q(selector).dispatchEvent(new dom.window.Event(event,{bubbles:true}));}
function submit(){q('#bac-bet-form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));}
function seed(extra={}){localStorage.clear();localStorage.setItem(STORAGE_KEY,JSON.stringify({version:1,id:'test',deck:createDeck(),createdAt:'2026-11-23',revealed:0,rounds:[],pending:[],rates:{...DEFAULT_RATES},...extra}));}
function saved(){return restoreStudySession(localStorage.getItem(STORAGE_KEY));}
test('complete 70-hand order is visible immediately; arbitrary entries settle and retain reasoning on reload',()=>{
 seed();let stop=renderBaccarat();
 assert.equal(document.querySelectorAll('.bac-order-hand').length,70);assert.equal(q('[data-bac="finish"]'),null);assert.ok(q('.playing-card'));
 click('[data-hand="42"]');set('#bac-method','下三路','change');set('#bac-reason','此前路形对照');set('#bac-type','P','change');set('#bac-amount','123.45');submit();set('#bac-review-note','检查延续与转向，不把结果当原因。');
 assert.equal(saved().study.selected,42);assert.equal(saved().study.entries[0].bets[0].stake,12345);assert.match(q('#bac-last').textContent,/本口净盈亏/);
 click('[data-hand="7"]');assert.match(q('.bac-current-roads').textContent,/第 1 至 6 口/);assert.equal(q('#bac-reason').value,'');
 const prior=dealShoe(createDeck()).slice(0,6);assert.deepEqual([...document.querySelectorAll('.bac-current-roads .bac-lower')].map(el=>el.querySelectorAll('.bac-road-cell').length),[1,2,3].map(i=>derivedRoad(prior,i).length));
 stop();stop=renderBaccarat();click('[data-hand="42"]');assert.equal(q('#bac-reason').value,'此前路形对照');assert.equal(q('#bac-review-note').value,'检查延续与转向，不把结果当原因。');assert.match(q('.bac-statistics').textContent,/1 口有投注/);assert.equal(saved().revealed,0);stop();
});
test('shuffle opens a new complete shoe immediately and archives previous arbitrary-hand results without adding wagers',()=>{
 seed();const stop=renderBaccarat();click('[data-hand="20"]');set('#bac-reason','研究第20口');submit();const deck=saved().deck;
 click('[data-bac="new"]');assert.equal(document.querySelectorAll('.bac-order-hand').length,70);assert.notDeepEqual(saved().deck,deck);assert.equal(saved().study.entries.length,0);assert.match(q('.bac-statistics').textContent,/0 口有投注/);
 click('[data-shoe="test"]');assert.deepEqual(saved().deck,deck);assert.equal(saved().study.selected,20);assert.equal(q('#bac-reason').value,'研究第20口');assert.match(q('.bac-statistics').textContent,/1 口有投注/);stop();
});
test('previous sequential wagers and pending drafts survive migration separately from retrospective statistics',()=>{
 seed({revealed:1,rounds:[{bets:[{type:'P',stake:10000}],rates:{...DEFAULT_RATES}}],pending:[{type:'B',stake:5000}]});const stop=renderBaccarat();
 assert.match(q('.bac-legacy').textContent,/1 口有投注/);assert.match(q('.bac-statistics').textContent,/0 口有投注/);click('[data-hand="70"]');submit();assert.equal(saved().rounds[0].bets[0].stake,10000);assert.equal(saved().pending[0].stake,5000);assert.equal(saved().study.entries[0].hand,70);stop();
});
test('past context excludes the selected and future hands; notes are escaped and rate snapshots stay immutable',()=>{
 seed();const session=saved(),hands=dealShoe(session.deck),before=priorContext(hands,8);const changed=hands.map((h,i)=>i>=7?{...h,result:'T'}:h);
 assert.deepEqual(priorContext(changed,8).counts,before.counts);assert.equal(priorContext(changed,8).streak,before.streak);
 recordStudyBet(session,8,{type:'B',stake:10000});session.rates.B=10;recordStudyBet(session,8,{type:'B',stake:10000});assert.equal(session.study.entries[0].rates.B,.95);
 session.study.entries[0].reason='<img src=x onerror=bad()>';localStorage.setItem(STORAGE_KEY,JSON.stringify(session));const stop=renderBaccarat();click('[data-hand="8"]');assert.equal(q('.bac-ticket img'),null);assert.equal(q('#bac-reason').value,'<img src=x onerror=bad()>');
 session.study.entries.push({...session.study.entries[0]});assert.throws(()=>restoreStudySession(JSON.stringify(session)));stop();
});

test('the first complete shoe is saved before any wager or selection',()=>{
 localStorage.clear();let stop=renderBaccarat();const original=saved().deck;assert.equal(dealShoe(original).length,70);stop();stop=renderBaccarat();assert.deepEqual(saved().deck,original);stop();
});
