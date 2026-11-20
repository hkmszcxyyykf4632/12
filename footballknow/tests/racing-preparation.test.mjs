import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';

const dom=new JSDOM('<main id="main"></main>',{url:'https://example.test/'});
globalThis.document=dom.window.document;
const {preparationHtml,preparationDetails}=await import('../public/racing-preparation.mjs');
const runner={id:'HK_2022_H459',name:'<img src=x onerror=alert(1)>',number:'1',activity:'近期加紧备战',source:'https://racing.hkjc.com/workouts',fetchedAt:'2026-11-21T00:00:00Z',
  window:{from:'2026-10-31',to:'2026-11-20'},days7:5,counts7:{fast:3,trial:1},evidence:['公开晨操'],alternatives:['休赛恢复'],workouts:[],
  classWatch:{label:'接近低一班上限',summary:'评分下降，留意下一次编班',basis:'本场班次',class:3,rating:63,change:-4,threshold:60,gap:3,history:[],intent:'目的未确认'}};

test('horse details expose dated evidence without executing source text',()=>{
  document.querySelector('main').innerHTML=preparationDetails(runner);
  assert.match(document.querySelector('main').textContent,/2026-10-31/);
  assert.equal(document.querySelectorAll('details').length,1);
  assert.match(document.querySelector('main').textContent,/休赛恢复/);
});

test('race summary escapes names and links the correct horse',()=>{
  document.querySelector('main').innerHTML=preparationHtml({status:'pregame',hasPregame:true,generatedAt:runner.fetchedAt,runners:[runner]});
  assert.equal(document.querySelectorAll('img').length,0);
  assert.equal(document.querySelector('a[href^="#/horse/"]').getAttribute('href'),'#/horse/HK_2022_H459');
  assert.match(document.querySelector('main').textContent,/3 \/ 1/);
});

test('withdrawn horses are removed and retrospective observations have no validation table',()=>{
  const html=preparationHtml({status:'retrospective',runners:[runner],withdrawnIds:[runner.id],review:{available:true,hasPregame:false,runners:[]}});
  document.querySelector('main').innerHTML=html;
  assert.equal(document.querySelectorAll('a[href^="#/horse/"]').length,0);
  assert.doesNotMatch(document.querySelector('main').textContent,/赛后对照与降班跟进/);
});

test('post-race comparison distinguishes pending ratings and withdrawals',()=>{
  document.querySelector('main').innerHTML=preparationHtml({status:'saved',runners:[],review:{available:true,hasPregame:true,runners:[
    {name:'甲',activity:'备战较积极',place:8,void:false},
    {name:'乙',activity:'常规操练',void:true,followingDate:'2026-11-25',ratingChange:-2,class:4}
  ]}});
  const body=document.querySelector('main').textContent;
  assert.match(body,/等待下一次出赛/);
  assert.match(body,/不作验证/);
  assert.doesNotMatch(body,/成功率|命中率/);
});
