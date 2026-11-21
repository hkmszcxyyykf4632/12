import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {JSDOM} from 'jsdom';

const root=new URL('../public/jingzang/',import.meta.url);
const [html,script,index,chapters,sources]=await Promise.all([
  readFile(new URL('index.html',root),'utf8'),readFile(new URL('jingzang.js',root),'utf8'),
  ...['index.json','books/lyj.json','lengyan-sources.json'].map(file=>readFile(new URL(file,root),'utf8').then(JSON.parse)),
]);
const tick=()=>new Promise(resolve=>setTimeout(resolve,10));
async function open(hash='#'){
  const dom=new JSDOM(html,{url:'https://culture.test/'+hash,runScripts:'outside-only'}),w=dom.window;
  w.scrollTo=()=>{};w.jingzangCountVisit=()=>{};
  w.localStorage.setItem('jz-last',JSON.stringify({book:'xj',ch:0}));
  w.fetch=async path=>({ok:true,json:async()=>path==='./videos.json'?{}:JSON.parse(await readFile(new URL(path,root),'utf8'))});
  w.eval(script);await tick();await tick();
  return {w,dom,$:selector=>w.document.querySelector(selector),async go(hash){w.location.hash=hash;await tick();await tick();}};
}

test('all ten volumes preserve source text, verses, mantra and final conclusion',()=>{
  const book=index.find(b=>b.id==='lyj');
  assert.equal(book.ch.length,10);assert.equal(chapters.length,10);assert.equal(sources.volumes.length,10);
  chapters.forEach((chapter,i)=>{
    const text=chapter.p.join('');assert.ok(text.length>4500);
    assert.equal(createHash('sha256').update(text).digest('hex'),sources.volumes[i].textSha256);
    assert.equal(chapter.p.length,sources.volumes[i].paragraphs);assert.match(book.ch[i].sourceUrl,/oldid=\d+/);
  });
  assert.match(chapters[0].p[0],/^如是我聞/);
  assert.match(chapters[2].p.join(''),/妙湛總持不動尊/);
  assert.match(chapters[6].p.join(''),/南無/);
  assert.match(chapters[9].p.at(-1),/作禮而去/);
});

test('home has left-side categories and omits removed shortcuts and copy',async t=>{
  const h=await open();t.after(()=>h.w.close());
  assert.ok(h.$('#culture-navigation #culture-menu'));
  assert.equal(h.w.document.querySelectorAll('.culture-traditions>a').length,3);
  const header=h.$('.culture-home');assert.ok(header);
  assert.doesNotMatch(header.textContent,/不收费|没有广告|接着上次读|108|繁體/);
  assert.doesNotMatch(h.$('#app').textContent,/从这里读起|接着上次读/);
  assert.equal(header.querySelectorAll('a,button').length,0);
  h.$('#culture-menu-toggle').click();assert.equal(h.$('#culture-menu-toggle').getAttribute('aria-expanded'),'true');
  h.$('a[href="#fo-hanchuan"]').click();await tick();await tick();
  assert.equal(h.$('#culture-menu-toggle').getAttribute('aria-expanded'),'false');
  assert.match(h.$('h1').textContent,/北传/);
  assert.ok(h.$('#app a[href="#b-lyj-1"]'));assert.ok(h.$('#app a[href="#b-ysz-1"]'));assert.ok(h.$('#app a[href="#b-dbz-1"]'));
  assert.doesNotMatch(h.$('#app').textContent,/108/);
  assert.equal(h.$('#culture-menu a[aria-current="page"]').hash,'#fo-hanchuan');
});

test('new categories and all ten chapters can be opened and searched',async t=>{
  const h=await open('#fo');t.after(()=>h.w.close());
  assert.equal(h.w.document.querySelectorAll('.tradition-card').length,3);
  await h.go('#fo-nanchuan');assert.equal(h.w.document.querySelectorAll('.tradition-resources>a').length,5);
  assert.equal(h.$('#app a[href="#b-lyj-1"]'),null);
  await h.go('#fo-zangchuan');assert.ok(h.$('#app a[href="#zang"]'));
  for(let i=1;i<=10;i++){
    await h.go('#b-lyj-'+i);assert.ok(h.$('#text'));
    assert.equal(h.$('#chapter').options.length,10);assert.equal(h.$('#chapter').value,String(i-1));
    assert.equal(h.w.document.querySelectorAll('#text>p').length,chapters[i-1].p.length);
    assert.equal(h.$('#next').disabled,i===10);assert.equal(h.$('#prev').disabled,i===1);
    assert.equal(h.$('#culture-menu a[aria-current="page"]').hash,'#fo-hanchuan');
  }
  const input=h.$('#find');input.value='作禮而去';input.dispatchEvent(new h.w.Event('input',{bubbles:true}));
  assert.match(h.$('#hits').textContent,/作禮而去/);
  await h.go('#cat-dao');assert.match(h.$('h1').textContent,/道家经典/);assert.ok(h.$('#app a[href="#b-ddj-1"]'));
});
