import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {createDeck,DEFAULT_RATES,STORAGE_KEY,restoreSession} from '../public/baccarat-core.mjs';
const dom=new JSDOM('<main id="main"></main>',{url:'https://example.test/#/baccarat'});
Object.assign(globalThis,{document:dom.window.document,window:dom.window,location:dom.window.location,localStorage:dom.window.localStorage,FormData:dom.window.FormData});
const {renderBaccarat}=await import('../public/baccarat-page.mjs');
const q=s=>document.querySelector(s),click=s=>q(s).click();
function set(selector,value){q(selector).value=value;q(selector).dispatchEvent(new dom.window.Event(selector.includes('type')?'change':'input',{bubbles:true}));}
function submit(){q('#bac-bet-form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));}
test('betting panel keeps current lower roads beside wagers, hides future and settles before advancing',()=>{
 localStorage.setItem(STORAGE_KEY,JSON.stringify({version:1,id:'test',deck:createDeck(),createdAt:'2026-11-23',revealed:0,rounds:[],pending:[],rates:{...DEFAULT_RATES}}));
 let stop=renderBaccarat();assert.equal(q('.playing-card'),null);assert.equal(document.querySelectorAll('.bac-lower').length,3);assert.match(q('.bac-probe').textContent,/若开庄.*若开闲/);
 set('#bac-type','P');set('#bac-amount','100');submit();set('#bac-type','B');set('#bac-amount','50');submit();assert.equal(document.querySelectorAll('.bac-pending>div').length,2);
 click('[data-bac="deal"]');assert.match(q('#bac-last').textContent,/50.00/);assert.ok(q('#bac-last .bac-profit'));assert.equal(q('.bac-pending>div'),null);assert.ok(document.querySelectorAll('.playing-card').length>=4);
 const saved=restoreSession(localStorage.getItem(STORAGE_KEY));assert.equal(saved.revealed,1);assert.equal(saved.rounds[0].bets.length,2);
 stop();stop=renderBaccarat();assert.equal(document.querySelector('.bac-result').textContent,'第 1 口 · 闲赢');click('[data-bac="finish"]');assert.equal(q('[data-bac="deal"]').disabled,true);assert.match(q('.bac-statistics').textContent,/1 口有投注/);assert.equal(restoreSession(localStorage.getItem(STORAGE_KEY)).revealed,70);assert.equal(restoreSession(localStorage.getItem(STORAGE_KEY)).rounds.flatMap(r=>r.bets).length,2);stop();
});
