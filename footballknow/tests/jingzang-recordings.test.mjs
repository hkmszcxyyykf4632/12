import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';

const base=new URL('../public/jingzang/',import.meta.url);
const script=await readFile(new URL('recorded-reading.js',base),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));

function open(book='ysj',chapter={},available=[1,2]){
  const dom=new JSDOM('<body></body>',{url:'https://culture.test/',runScripts:'outside-only'}),w=dom.window;
  const instances=[];let stopRequests=0;
  w.addEventListener('jingzang:recorded-play',()=>stopRequests++);
  w.eval(script);w.document.body.innerHTML=w.RecordedReading.panel(book,chapter);
  class Player {
    constructor(mount,options){this.options=options;this.rate=1;this.destroyed=false;this.frame=w.document.createElement('iframe');mount.replaceWith(this.frame);instances.push(this);}
    getIframe(){return this.frame;}
    getAvailablePlaybackRates(){return available;}
    getPlaybackRate(){return this.rate;}
    setPlaybackRate(rate){this.requestedRate=rate;}
    playVideo(){this.played=true;}
    destroy(){this.destroyed=true;this.frame.remove();}
    ready(){this.options.events.onReady({target:this});}
    applied(rate){this.rate=rate;this.options.events.onPlaybackRateChange({target:this,data:rate});}
  }
  w.YT={Player};const $=s=>w.document.querySelector(s);
  return {dom,w,$,instances,get stopRequests(){return stopRequests;},async play(){$('[data-recording-play]').click();await tick();},change(s,value){$(s).value=value;$(s).dispatchEvent(new w.Event('change',{bubbles:true}));}};
}

test('original playback requests 2x and reports only confirmed playback speed',async t=>{
  const h=open();t.after(()=>h.dom.window.close());
  assert.equal(h.instances.length,0,'no external player before a click');
  assert.equal(h.$('[data-recording-rate]').value,'2');await h.play();
  assert.equal(h.stopRequests,1);const player=h.instances[0];player.ready();
  assert.equal(player.options.videoId,'MthStAd4YKI');assert.equal(player.requestedRate,2);assert.equal(player.played,true);
  assert.match(h.$('[data-recording-note]').textContent,/正在切换/);
  player.applied(2);assert.match(h.$('[data-recording-note]').textContent,/当前 2 倍速/);
  h.change('[data-recording-rate]','1');player.applied(1);assert.match(h.$('[data-recording-note]').textContent,/当前 1 倍速/);
  h.$('[data-recording-close]').click();assert.equal(player.destroyed,true);assert.equal(h.$('[data-recording-host]').hidden,true);
  player.applied(2);assert.match(h.$('[data-recording-note]').textContent,/已关闭/,'stale events cannot overwrite state');
});

test('unavailable rates and playback errors expose accurate status and original link',async t=>{
  const h=open('jgj',{},[1]);t.after(()=>h.dom.window.close());await h.play();const player=h.instances[0];player.ready();
  assert.equal(player.options.videoId,'DgI1TFjxUBQ');assert.match(h.$('[data-recording-note]').textContent,/不支持 2 倍速，当前 1 倍速/);
  player.options.events.onError();assert.match(h.$('[data-recording-note]').textContent,/打开原版页面/);
  assert.equal(h.$('[data-recording-origin]').href,'https://www.youtube.com/watch?v=DgI1TFjxUBQ');
});

test('changing editions destroys the current player and updates the source',async t=>{
  const h=open();t.after(()=>h.dom.window.close());await h.play();const old=h.instances[0];old.ready();
  h.change('[data-recording-source]','1');assert.equal(old.destroyed,true);assert.equal(h.$('[data-recording-play]').disabled,false);
  assert.match(h.$('[data-recording-origin]').href,/8Bs-gagtGA4/);await h.play();assert.equal(h.instances[1].options.videoId,'8Bs-gagtGA4');
  h.w.dispatchEvent(new h.w.Event('pagehide'));assert.equal(h.instances[1].destroyed,true);
});

test('closing while the API loads prevents delayed playback',async t=>{
  const h=open();t.after(()=>h.dom.window.close());const YT=h.w.YT;delete h.w.YT;
  await h.play();assert.ok(h.w.document.querySelector('script[src="https://www.youtube.com/iframe_api"]'));
  h.$('[data-recording-close]').click();h.w.YT=YT;h.w.onYouTubeIframeAPIReady();await tick();assert.equal(h.instances.length,0);
});

test('verified catalogue selects the matching volume and leaves lectures unpromoted',t=>{
  const h=open('dzj',{g:'卷下'});t.after(()=>h.dom.window.close());
  assert.equal(h.$('[data-recording-source]').value,'2');assert.match(h.$('[data-recording-origin]').href,/Sff9emcqW-Q/);
  assert.equal(h.w.RecordedReading.has('amtj'),false);
  const panel=h.w.RecordedReading.panel('fhj',{t:'观世音菩萨普门品第二十五'});
  assert.match(panel,/oYYyutTBNRQ/);assert.match(panel,/已核实的集数/);
  assert.match(h.w.RecordedReading.panel('xj',{}),/Heart_Sutra\.mp3/);
});

test('Medicine Buddha ending retains the sutra ending followed by the verified dedication',async()=>{
  const parts=JSON.parse(await readFile(new URL('books/ysj.json',base),'utf8'));
  const paragraphs=parts.flatMap(part=>part.p);const text=paragraphs.join('\n');
  const ending=text.indexOf('皆大欢喜，信受奉行');const appendix=text.indexOf('回向文（诵读附录）');
  assert.ok(ending>=0&&appendix>ending);
  assert.deepEqual(paragraphs.slice(-4),['愿消三障诸烦恼，','愿得智慧真明了。','普愿罪障悉消除，','世世常行菩萨道。']);
});

test('Medicine Buddha recitation includes the verified middle passages in source order',async()=>{
  const parts=JSON.parse(await readFile(new URL('books/ysj.json',base),'utf8'));
  const text=parts.flatMap(part=>part.p).join('\n');
  const markers=['文殊师利菩萨、观世音菩萨、得大势菩萨、无尽意菩萨、宝檀华菩萨、药王菩萨、药上菩萨、弥勒菩萨',
    '彼药师琉璃光如来得菩提时','南谟薄伽伐帝','尔时，光中说此咒已','咒一百八遍','常持此咒，勿令废忘',
    '晨嚼齿木','尔时，曼殊室利童子白佛言'];
  let previous=-1;
  for(const marker of markers){const position=text.indexOf(marker);assert.ok(position>previous,marker);assert.equal(text.split(marker).length,2,marker);previous=position;}
  const catalogue=JSON.parse(await readFile(new URL('index.json',base),'utf8'));
  const book=catalogue.find(book=>book.id==='ysj');
  assert.match(book.src,/课诵版本/);assert.match(book.src,/T0450/);assert.match(book.sourceUrl,/J19nB044/);
});
