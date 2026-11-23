import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {createEntityIndex,enhanceEntityLinks,resolveEntity,personHref,entityHref,normalizeEntityName} from '../public/entity-links.mjs';
import {prepareStockTables} from '../public/stock-layout.mjs';
const arsenal={kind:'team',id:'epl:1',name:'阿森纳',aliases:['Arsenal'],href:'?league=epl#/team/1',targets:[{league:'epl',id:'1'},{league:'ucl',id:'359'}]};
test('entity links retain prose, avoid nested links and handle both spellings',()=>{
 const doc=new JSDOM('<main><p>阿森纳对曼城。Arsenal won. Arsenalized 不链接。</p><a href="#existing">阿森纳</a><button>阿森纳</button><p>潘顿与潘頓</p><input value="阿森纳"><h1>阿森纳</h1></main>').window.document;
 const index=createEntityIndex([arsenal,{kind:'jockey',id:'PZ',name:'潘頓',href:'#/racing-person/jockey/PZ'}]);const root=doc.querySelector('main'),original=root.textContent;
 assert.equal(enhanceEntityLinks(root,index),4);assert.equal(root.textContent,original);assert.equal(root.querySelectorAll('a a').length,0);assert.equal(root.querySelector('button a'),null);assert.equal(enhanceEntityLinks(root,index),0);
 assert.equal(root.querySelectorAll('a.entity-link').length,4);
});
test('canonical identity prevents cross-league id collisions and ambiguous aliases',()=>{
 assert.equal(entityHref(arsenal,'?league=ucl'),'#/team/359');assert.equal(entityHref(arsenal,'?league=laliga'),'?league=epl#/team/1');
 const index=createEntityIndex([arsenal,{...arsenal,id:'other',href:'#wrong'}]);assert.equal(resolveEntity(index,'阿森纳'),null);
 const mixed=createEntityIndex([arsenal,{kind:'horse',id:'a',name:'阿森纳',href:'#/horse/a'}]);assert.equal(resolveEntity(mixed,'阿森纳'),null);assert.equal(resolveEntity(mixed,'阿森纳','team'),arsenal);
 assert.equal(personHref('owner','甲/乙 團體'),'#/racing-person/owner/%E7%94%B2%2F%E4%B9%99%20%E5%9C%98%E9%AB%94');
 assert.equal(personHref('trainer',{id:'../x',name:'甲'}),'');assert.equal(normalizeEntityName('葉楚航'),'叶楚航');
});
test('HTML-looking and regex-special entity names remain safe text',()=>{
 const doc=new JSDOM('<main></main>').window.document,root=doc.querySelector('main');root.textContent='A.C. <img src=x> 阿森纳';
 enhanceEntityLinks(root,createEntityIndex([arsenal,{kind:'team',id:'ac',name:'A.C.',href:'#/team/2'}]));assert.equal(root.querySelector('img'),null);assert.equal(root.querySelectorAll('a').length,2);
});
test('quote layout puts stock price and change first without losing following controls',()=>{
 const doc=new JSDOM('<main><div class="table-wrap"><table><thead><tr><th>关注</th><th>股票</th><th>行业</th><th>报价 / 币种</th><th>涨跌幅</th></tr></thead><tbody><tr><td><button id="follow">关注</button></td><td>腾讯</td><td>科技</td><td>500</td><td>+2%</td></tr></tbody></table></div></main>').window.document;
 const root=doc.querySelector('main'),button=doc.querySelector('#follow');let clicks=0;button.onclick=()=>clicks++;
 prepareStockTables(root);prepareStockTables(root);
 assert.deepEqual([...doc.querySelectorAll('thead th')].map(x=>x.textContent),['股票','报价 / 币种','涨跌幅','关注','行业']);
 assert.deepEqual([...doc.querySelectorAll('tbody td')].map(x=>x.textContent),['腾讯','500','+2%','关注','科技']);button.click();assert.equal(clicks,1);
 assert.equal(root.querySelectorAll('.stock-details-toggle').length,1);const box=root.querySelector('input');box.click();assert.ok(root.querySelector('.table-wrap').classList.contains('show-stock-details'));
});
