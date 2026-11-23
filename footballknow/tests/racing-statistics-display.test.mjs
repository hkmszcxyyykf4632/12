import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
const dom=new JSDOM('<main id="main"></main>',{url:'https://example.test/'});
Object.assign(globalThis,{document:dom.window.document,window:dom.window,location:dom.window.location,localStorage:dom.window.localStorage});
const {poolSummary}=await import('../public/prediction-stats.mjs');
const {paintCelebrations}=await import('../public/prediction-celebrations.mjs');
test('place summary prominently shows one of three horses, the losing whole stake and no false full hit rate',()=>{
 const pools=['WIN','PLA','QIN','QPL'].map(type=>({type,tickets:[{status:'hit',dividend:11},{status:'miss',dividend:0},{status:'miss',dividend:0}]}));
 const fragment=JSDOM.fragment(poolSummary([{status:'settled',pools}]));const cards=fragment.querySelectorAll('article');
 assert.match(cards[0].textContent,/独赢场次命中率100.0%1 \/ 1 场/);
 assert.match(cards[1].textContent,/位置逐匹命中率33.3%1 \/ 3 匹/);assert.doesNotMatch(cards[1].textContent,/100.0%/);
 assert.match(cards[1].textContent,/投入 \$300.00/);assert.match(cards[1].textContent,/净盈亏 -190.00元/);assert.ok(cards[1].querySelector('.ps-miss'));
 assert.match(cards[3].textContent,/位置连赢逐注命中率33.3%1 \/ 3 注/);
});
test('legacy homepage caller clears a previous celebration without making a statistics request',async()=>{
 const target=document.querySelector('main');target.textContent='恭喜峰弈科技分析命中';let requested=false;
 globalThis.fetch=()=>{requested=true;throw Error('No request expected');};await paintCelebrations(target);assert.equal(target.textContent,'');assert.equal(requested,false);
});
