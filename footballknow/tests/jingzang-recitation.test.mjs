import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';

const root=new URL('../public/jingzang/',import.meta.url);
const [html,script,index]=await Promise.all([
  readFile(new URL('index.html',root),'utf8'),
  readFile(new URL('jingzang.js',root),'utf8'),
  readFile(new URL('index.json',root),'utf8').then(JSON.parse),
]);
const books=index.filter(b=>['ysz','dbz','xj'].includes(b.id));
const texts=Object.fromEntries(await Promise.all(books.map(async b=>[b.id,JSON.parse(await readFile(new URL(`books/${b.id}.json`,root),'utf8'))])));
const turn=()=>new Promise(resolve=>setTimeout(resolve,0));

async function open(id='ysz',options={}){
  const dom=new JSDOM(html,{url:`https://culture.test/#b-${id}-1`,runScripts:'outside-only'}),w=dom.window;
  let current=null,voices=options.voices??[{name:'Mandarin',lang:'zh-CN'},{name:'Cantonese',lang:'zh-HK'}];
  const spoken=[];
  w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};w.jingzangCountVisit=()=>{};
  w.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
  w.speechSynthesis={getVoices:()=>voices,addEventListener(){},speak(u){current=u;spoken.push(u);},cancel(){const old=current;current=null;old?.onerror?.({error:'interrupted'});}};
  for(const [key,value] of Object.entries(options.saved??{}))w.localStorage.setItem(key,JSON.stringify(value));
  w.fetch=async path=>({ok:true,json:async()=>JSON.parse(JSON.stringify(path==='./index.json'?books:path==='./videos.json'?{}:texts[String(path).match(/books\/(.+)\.json/)?.[1]]))});
  w.eval(script);await turn();await turn();
  assert.ok(w.document.querySelector('#play'),'reader loaded');
  const $=s=>w.document.querySelector(s);
  return {dom,w,$,spoken,get current(){return current;},setVoices(v){voices=v;w.speechSynthesis.onvoiceschanged?.();},count:()=>Number($('#recitation-count')?.textContent),
    click(s){$(s).click();},change(s,value){$(s).value=value;$(s).dispatchEvent(new w.Event('change',{bubbles:true}));},
    end(n=1){for(let i=0;i<n;i++){assert.ok(current,'an utterance is active');const done=current;current=null;done.onend();}},
    async navigate(id){w.location.hash=`#b-${id}-1`;await turn();await turn();},
  };
}

for(const [id,phrases] of [['ysz',14],['dbz',84]])test(`${id}: exactly 108 complete readings, then stop and reset`,async t=>{
  const h=await open(id);t.after(()=>h.dom.window.close());
  assert.equal(texts[id][0].p.length,phrases);assert.equal(books.find(b=>b.id===id).repeat,108);
  h.click('#play');
  for(let round=0;round<108;round++){
    assert.equal(h.current.text,texts[id][0].p[0]);
    h.end(phrases-1);assert.equal(h.count(),round,'partial round never counts');
    assert.equal(h.current.text,texts[id][0].p.at(-1));
    h.end();assert.equal(h.count(),round+1);
  }
  assert.equal(h.current,null);assert.equal(h.spoken.length,108*phrases);assert.equal(h.$('#play').disabled,true);
  assert.deepEqual(JSON.parse(h.w.localStorage.getItem('jz-recitation-'+id)),{version:1,completed:108});
  const last=h.spoken.at(-1);last.onend();assert.equal(h.count(),108,'duplicate callback cannot exceed target');
  h.click('#recitation-reset');assert.equal(h.count(),0);assert.equal(h.$('#play').disabled,false);assert.equal(h.current,null);
});

test('pause and language changes keep completed rounds and reject canceled callbacks',async t=>{
  const h=await open();t.after(()=>h.dom.window.close());h.click('#play');h.end(14);h.end(3);
  const canceled=h.current,phrase=canceled.text;h.click('#play');canceled.onend();assert.equal(h.count(),1);assert.equal(h.current,null);
  h.change('#lang','zh-HK');h.click('#play');assert.equal(h.current.text,phrase);assert.equal(h.current.voice.lang,'zh-HK');
  h.end(11);assert.equal(h.count(),2);
  const before=h.current;h.change('#lang','zh-CN');before.onend();assert.equal(h.current.voice.lang,'zh-CN');assert.equal(h.current.text,texts.ysz[0].p[0]);
  h.end(14);assert.equal(h.count(),3);
});

test('partial preview, errors, stop and navigation do not falsely finish a reading',async t=>{
  const h=await open();t.after(()=>h.dom.window.close());
  h.w.document.querySelectorAll('#text .s')[7].click();h.end(7);assert.equal(h.count(),0);assert.equal(h.current,null);
  h.click('#play');h.end(13);const interrupted=h.current;interrupted.onerror({error:'network'});interrupted.onend();assert.equal(h.count(),0);assert.equal(h.current,null);
  h.click('#play');assert.equal(h.current.text,texts.ysz[0].p.at(-1));h.end();assert.equal(h.count(),1);
  h.end(4);const stopped=h.current;h.click('#stop');stopped.onend();assert.equal(h.count(),1);h.click('#play');assert.equal(h.current.text,texts.ysz[0].p[0]);
  const previous=h.current;await h.navigate('dbz');previous.onend();assert.equal(h.count(),0);assert.equal(h.current,null);
  await h.navigate('ysz');assert.equal(h.count(),1);assert.equal(h.current,null);
});

test('refresh restores only full rounds and finished sessions never autoplay',async t=>{
  const h=await open('dbz',{saved:{'jz-recitation-dbz':{version:1,completed:107},'jz-recitation-ysz':{version:1,completed:6},'jz-prefs':{lang:'zh-HK'}}});t.after(()=>h.dom.window.close());
  assert.equal(h.count(),107);assert.equal(h.current,null);h.click('#play');assert.equal(h.current.voice.lang,'zh-HK');h.end(84);assert.equal(h.count(),108);
  await h.navigate('ysz');assert.equal(h.count(),6);await h.navigate('dbz');assert.equal(h.count(),108);assert.equal(h.$('#play').disabled,true);assert.equal(h.current,null);
});

test('unavailable Cantonese never silently falls back to Mandarin',async t=>{
  const h=await open('ysz',{voices:[{name:'Mandarin',lang:'zh-CN'}]});t.after(()=>h.dom.window.close());
  h.click('#play');h.end(3);const old=h.current;h.change('#lang','zh-HK');old.onend();assert.equal(h.current,null);assert.match(h.$('#voice-note').textContent,/没有安装粤语/);
  h.click('#play');assert.equal(h.current,null);assert.equal(h.count(),0);
  h.setVoices([{name:'Cantonese',lang:'yue-HK'}]);assert.equal(h.current,null);h.click('#play');assert.equal(h.current.voice.lang,'yue-HK');assert.equal(h.current.text,texts.ysz[0].p[3]);h.end(11);assert.equal(h.count(),1);
});

test('empty voices do not schedule delayed speech after leaving the reader',async t=>{
  const h=await open('ysz',{voices:[]});t.after(()=>h.dom.window.close());h.click('#play');assert.equal(h.spoken.length,0);
  await h.navigate('dbz');h.setVoices([{name:'Mandarin',lang:'zh-TW'}]);assert.equal(h.current,null);h.click('#play');assert.equal(h.current.voice.lang,'zh-TW');
  h.w.dispatchEvent(new h.w.Event('pagehide'));const old=h.spoken.at(-1);old.onend();assert.equal(h.count(),0);assert.equal(h.current,null);
});

test('invalid saved counts are rejected and failed saving is visible',async t=>{
  const h=await open('ysz',{saved:{'jz-recitation-ysz':{version:1,completed:999}}});t.after(()=>h.dom.window.close());assert.equal(h.count(),0);
  h.w.Storage.prototype.setItem=()=>{throw Error('storage full');};h.click('#play');h.end(14);assert.equal(h.count(),1);assert.match(h.$('#recitation-storage').textContent,/未能保存/);
});

test('ordinary books retain single-reading controls without repetition',async t=>{
  const h=await open('xj',{saved:{'jz-prefs':{chain:false}}});t.after(()=>h.dom.window.close());assert.equal(h.$('#recitation-count'),null);assert.ok(h.$('#chain'));
  const phrases=h.w.document.querySelectorAll('#text .s[data-k="o"]').length;h.click('#play');h.end(phrases);assert.equal(h.current,null);assert.equal(h.spoken.length,phrases);
});
