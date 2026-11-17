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
