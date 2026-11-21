import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
const dom=new JSDOM('<main id="main"></main>',{url:'http://localhost/'});
Object.assign(globalThis,{document:dom.window.document,window:dom.window,location:dom.window.location,localStorage:dom.window.localStorage});
const {groupRunners}=await import('../public/racing-ui.mjs');
const {chineseArticles}=await import('../public/portal-news.mjs');
const {poolsHtml}=await import('../public/racing-pools.mjs');

test('daily trainer grouping retains race order and counts only official non-withdrawn places',()=>{
  const horse=(id,place,withdrawn=false)=>({id,name:id,place,withdrawn,trainer:{id:'HDA',name:'賀賢'}});
  const groups=groupRunners([
    {raceNo:3,resultOfficial:true,entries:[horse('c',1,true)]},
    {raceNo:1,resultOfficial:false,entries:[horse('a',1)]},
    {raceNo:2,resultOfficial:true,entries:[horse('b',2)]},
  ],'trainer');
  assert.deepEqual(groups[0].runs.map(r=>r.race.raceNo),[1,2,3]);
  assert.equal(groups[0].wins,0);assert.equal(groups[0].top3,1);
});
test('portal includes Chinese only and sorts across categories by publication time',()=>{
  const a=(title,date,url)=>({titleZh:title,publishedAt:date,url});
  const rows=chineseArticles({categories:{finance:{articles:[a('金融新聞','2026-11-17T09:00Z','https://example.test/a')]},
    racing:{articles:[a('馬匹新聞','2026-11-17T10:00Z','https://example.test/b'),a('English','2026-11-17T11:00Z','https://example.test/c')]},
    football:{articles:[a('球隊新聞','2026-11-17T08:00Z','javascript:alert(1)')]}}});
  assert.deepEqual(rows.map(r=>r.category),['racing','finance']);
});
test('pool view separates recorded prices from official dividends and escapes horse names',()=>{
  const html=poolsHtml({entries:[{number:'1',name:'<img src=x>',id:'a'},{number:'2',name:'乙',id:'b'}],pools:[
    {type:'WIN',quotes:[{combination:'1',value:'3.3',first:'4.0'}],sourceUpdatedAt:new Date().toISOString()},
    {type:'PLA',quotes:[{combination:'1',value:'1.4'}]},
    {type:'QIN',quotes:[{combination:'1,2',value:'8.2'}]}],dividends:[{type:'WIN',combination:'1',display:'33.00',unit:10}]});
  assert.ok(html.includes('3.3')&&html.includes('1.4')&&html.includes('8.2')&&html.includes('33.00'));
  assert.ok(!html.includes('<img src=x>'));
});

test('race fact amendments retain the pick and original narrative with dated quote and training evidence',async()=>{
  const {evaluationHtml}=await import('../public/racing-page.mjs');
  const report={pick:'a',shortlist:['a','b'],issuedAt:'2026-11-21T12:00:00Z',summary:['旧文称没有赔率'],details:[{title:'旧依据',text:'原文保留'}],amendments:[{issuedAt:'2026-11-21T13:00:00Z',reason:'有报价，不代表已有完整走势。',marketSnapshot:{status:'available',asOf:'2026-11-21T13:00:00Z',pools:[{type:'WIN',sourceUpdatedAt:'2026-11-21T12:55:00Z',checkedAt:'2026-11-21T12:56:00Z',quotes:[{combination:'1',value:'1.2',horses:[{id:'a',number:'1',name:'<img src=x>'}]}]}]},preparationSnapshot:{runners:[{id:'b',number:'5',name:'乙',activity:'维持常规操练',known:true,counts7:{fast:1,trial:0},window:{to:'2026-11-20'}}]}}]};
  const race={status:'scheduled',entries:[{id:'a',name:'甲'},{id:'b',name:'乙'}]};
  const state={reports:{pre:report},evaluation:{evaluated:0,wins:0,top3:0,pending:1,void:0}};
  const view=new JSDOM(evaluationHtml(state,race)).window.document;
  assert.equal(view.querySelector('.racing-pick').textContent,'首选：甲');
  assert.match(view.querySelector('.racing-amendment').textContent,/维持常规操练/);
  assert.match(view.querySelector('.racing-amendment').textContent,/1 \/ 0/);
  assert.equal(view.querySelector('.racing-original').open,false);
  assert.match(view.querySelector('.racing-original').textContent,/旧文称没有赔率/);
  assert.equal(view.querySelector('img'),null);
  assert.equal(report.pick,'a');
});
