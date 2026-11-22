import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';

test('dialogue posts a JSON object, carries followup history and clears local conversation',async()=>{
 const dom=new JSDOM(await readFile(new URL('../public/index.html',import.meta.url),'utf8'),{url:'http://localhost/#/ask'}),w=dom.window;
 Object.assign(globalThis,{window:w,document:w.document,location:w.location,localStorage:w.localStorage});
 const calls=[];globalThis.fetch=async(url,options)=>{const body=JSON.parse(options.body);calls.push(body);return {ok:true,json:async()=>({answer:['这是一般原理。'],followups:['那么走盘呢？'],sources:[],answeredAt:'2026-11-22T08:00:00Z'})};};
 const {renderInteractiveQA}=await import('../public/interactive-qa.mjs');const dispose=renderInteractiveQA();
 const input=w.document.querySelector('#qa-question'),form=w.document.querySelector('#qa-form');
 input.value='让半球是什么意思？';await form.onsubmit({preventDefault(){}});
 assert.equal(calls[0].question,'让半球是什么意思？');assert.deepEqual(calls[0].history,[]);
 assert.match(w.document.querySelector('#qa-messages').textContent,/这是一般原理/);
 w.document.querySelector('[data-followup]').click();assert.equal(input.value,'那么走盘呢？');
 await form.onsubmit({preventDefault(){}});assert.equal(calls[1].history.length,2);assert.equal(calls[1].history[1].role,'assistant');
 w.document.querySelector('#qa-clear').click();assert.deepEqual(JSON.parse(w.localStorage.getItem('fengyi.qa.v1')),[]);
 dispose();w.close();
});

test('all published editorials have sources and actual local photographs',async()=>{
 const data=JSON.parse(await readFile(new URL('../public/editorial-articles.json',import.meta.url),'utf8'));
 assert.equal(data.articles.length,5);
 for(const a of data.articles){assert.ok(a.analysis.length>150);assert.ok(a.sources.length&&a.sources.every(s=>s.url.startsWith('https://')));const image=await readFile(new URL('../public/editorial/'+a.image,import.meta.url));assert.ok(image.length>10000);}
});
