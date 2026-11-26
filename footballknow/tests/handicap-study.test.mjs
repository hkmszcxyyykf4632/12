import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import {studyBody,selectStudy,renderHandicapStudy} from '../public/handicap-study.mjs';
const report=JSON.parse(await readFile(new URL('../public/research/shallow-handicap.json',import.meta.url),'utf8'));
const ready=()=>new Promise(resolve=>setTimeout(resolve,0));

test('real three-season sample reconciles to league and signed handicap totals',()=>{
 assert.equal(report.all.summary.n,2450);
 assert.deepEqual(report.seasons.map(x=>x.summary.n),[882,794,774]);
 for(const g of [report.all,...report.seasons]){
  assert.equal(g.leagues.reduce((n,x)=>n+x.summary.n,0),g.summary.n);
  assert.equal(g.byLine.reduce((n,x)=>n+x.n,0),g.summary.n);
  assert.equal(g.byDepth.reduce((n,x)=>n+x.n,0),g.summary.n);
  assert.equal(g.byMovement.reduce((n,x)=>n+x.n,0),g.summary.n);
 }
});
test('half-ball example distinguishes preselected two-score coverage from conditional share',()=>{
 const h=report.all.summary.halfBall;
 assert.equal(h.n,791);assert.equal(h.lowerWin.count,400);
 assert.equal(h.fixed00or11.count,177);assert.equal(h.fixed00or11.pct,22.38);
 assert.equal(h.draw00or11GivenLowerWin.pct,44.25);
 const dom=new JSDOM(studyBody(report));
 assert.match(dom.window.document.querySelector('.study-hypothesis').textContent,/22.38%/);
 assert.match(dom.window.document.querySelector('.study-hypothesis').textContent,/44.25%/);
 assert.equal(dom.window.document.querySelectorAll('details[open]').length,0);
});
test('league and season filters actually change denominators and survive rerender',async()=>{
 const dom=new JSDOM('<main></main>'),root=dom.window.document.querySelector('main');
 const dispose=renderHandicapStudy(root,async()=>({ok:true,json:async()=>report}));await ready();
 const season=root.querySelector('[name=study-season]'),league=root.querySelector('[name=study-league]');
 season.value='2024-25';season.dispatchEvent(new dom.window.Event('change',{bubbles:true}));
 league.value='epl';league.dispatchEvent(new dom.window.Event('change',{bubbles:true}));
 assert.equal(root.querySelector('.study-kpis b').textContent,'187');
 assert.equal(season.value,'2024-25');assert.equal(league.value,'epl');
 assert.equal(root.querySelectorAll('details').length,3);
 dispose();
});
test('unmounted loading cannot replace another page',async()=>{
 const dom=new JSDOM('<main></main>'),root=dom.window.document.querySelector('main');let finish;
 const dispose=renderHandicapStudy(root,()=>new Promise(r=>{finish=r;}));
 dispose();root.innerHTML='<p>下一页</p>';
 finish({ok:true,json:async()=>report});await ready();assert.equal(root.textContent,'下一页');
});
test('failed fetch offers functional retry and sources cannot become script links',async()=>{
 const dom=new JSDOM('<main></main>'),root=dom.window.document.querySelector('main');let attempts=0;
 const dispose=renderHandicapStudy(root,async()=> ++attempts===1?{ok:false}:{ok:true,json:async()=>report});
 await ready();assert.ok(root.querySelector('[role=alert]'));
 root.querySelector('[data-study-retry]').click();await ready();assert.equal(root.querySelector('.study-kpis b').textContent,'2,450');
 const poisoned=structuredClone(report);poisoned.sourceUrl='javascript:alert(1)';poisoned.version='<script>bad</script>';
 const view=new JSDOM(studyBody(poisoned));assert.equal(view.window.document.querySelectorAll('script,a[href^="javascript:"]').length,0);
 dispose();
});
test('unknown filters cannot silently show combined data',()=>{
 assert.throws(()=>selectStudy(report,'2022-23'));
 assert.throws(()=>selectStudy(report,'all','ucl'));
});
