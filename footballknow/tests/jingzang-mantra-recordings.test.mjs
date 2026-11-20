import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';

const base=new URL('../public/jingzang/',import.meta.url);
const [html,reader,recordings,index,text]=await Promise.all(['index.html','jingzang.js','recorded-reading.js','index.json','books/ysz.json'].map(f=>readFile(new URL(f,base),'utf8')));
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
async function open(completed=0){
  const dom=new JSDOM(html,{url:'https://culture.test/#b-ysz-1',runScripts:'outside-only'}),w=dom.window,instances=[];
  let clock=0,timer=null;
  w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};w.jingzangCountVisit=()=>{};
  w.localStorage.setItem('jz-recitation-ysz',JSON.stringify({version:1,completed}));
  w.fetch=async path=>({ok:true,json:async()=>path==='./index.json'?JSON.parse(index):path==='./videos.json'?{}:JSON.parse(text)});
  w.setInterval=fn=>{timer=fn;return 1;};w.clearInterval=()=>{timer=null;};Object.defineProperty(w.performance,'now',{value:()=>clock});
  class Player {
    constructor(mount,options){this.options=options;this.rate=1;this.time=0;this.state=2;this.loads=0;this.frame=w.document.createElement('iframe');mount.replaceWith(this.frame);instances.push(this);}
    getIframe(){return this.frame;}getDuration(){return 56.2;}getCurrentTime(){return this.time;}getPlayerState(){return this.state;}
    getAvailablePlaybackRates(){return [1,1.25,1.5,1.75,2];}getPlaybackRate(){return this.rate;}
    setPlaybackRate(rate){this.rate=rate;this.options.events.onPlaybackRateChange({target:this,data:rate});}
    loadVideoById(options){this.segment=options;this.loads++;this.time=options.startSeconds;this.state=1;this.options.events.onStateChange({target:this,data:1});}
    playVideo(){this.state=1;this.options.events.onStateChange({target:this,data:1});}
    pauseVideo(){this.state=2;this.options.events.onStateChange({target:this,data:2});}
    destroy(){this.destroyed=true;this.frame.remove();}ready(){this.options.events.onReady({target:this});}
    error(){this.options.events.onError({target:this,data:100});}
    step(){if(this.state!==1)return;clock+=250;this.time=Math.min(this.segment.endSeconds,this.time+this.rate*.25);timer?.();}
    finish(){const n=this.loads;for(let i=0;i<500&&this.loads===n&&this.state===1;i++)this.step();}
  }
  w.YT={Player};w.eval(recordings);w.eval(reader);await tick();await tick();
  const $=s=>w.document.querySelector(s);
  return {w,dom,$,instances,count:()=>Number($('#recitation-count').textContent),
    async play(){$('[data-recording-play]').click();await tick();instances.at(-1)?.ready();},
    change(selector,value){$(selector).value=value;$(selector).dispatchEvent(new w.Event('change',{bubbles:true}));},
    stepClock(){clock+=250;timer?.();},
  };
}

test('Mandarin and Cantonese recordings work without installed speech voices',async t=>{
  const h=await open();t.after(()=>h.dom.window.close());assert.equal(h.w.speechSynthesis,undefined);
  assert.equal(h.$('[data-recording-rate]').value,'2');await h.play();const yue=h.instances[0];
  assert.equal(yue.segment.videoId,'MthStAd4YKI');assert.deepEqual([yue.segment.startSeconds,yue.segment.endSeconds],[1180,1221]);
  yue.finish();assert.equal(h.count(),1);assert.equal(yue.rate,2);
  h.change('[data-recording-source]','1');assert.equal(yue.destroyed,true);assert.equal(h.$('[data-recording-rate]').value,'1');
  assert.match(h.$('[data-recording-credit]').textContent,/法鼓山安和分院/);await h.play();const mandarin=h.instances[1];
  assert.equal(mandarin.segment.videoId,'JWNB9wODEHg');assert.equal(mandarin.segment.startSeconds,0);assert.equal(mandarin.rate,1);
  mandarin.step();assert.equal(h.count(),1,'a partial 108-recitation programme cannot claim completion');
  assert.match(h.$('#recitation-status').textContent,/整段播完/);
  mandarin.finish();assert.equal(h.count(),108);assert.equal(mandarin.loads,1,'the complete programme must not be looped 108 times');assert.equal(JSON.parse(h.w.localStorage.getItem('jz-recitation-ysz')).completed,108);
});

test('exactly 108 complete original segments stop and reset safely',async t=>{
  const h=await open();t.after(()=>h.dom.window.close());await h.play();const p=h.instances[0];
  for(let i=1;i<=108;i++){p.finish();assert.equal(h.count(),i);}
  assert.equal(p.state,2);assert.equal(p.loads,108);assert.equal(h.$('[data-recording-pause]').disabled,true);
  p.options.events.onStateChange({target:p,data:0});assert.equal(h.count(),108);
  h.$('#recitation-reset').click();assert.equal(h.count(),0);assert.equal(p.destroyed,true);assert.equal(h.$('[data-recording-play]').disabled,false);
});

test('pause resumes the same original segment without adding a count',async t=>{
  const h=await open(6);t.after(()=>h.dom.window.close());await h.play();const p=h.instances[0];
  for(let i=0;i<15;i++)p.step();const position=p.time;
  h.$('[data-recording-pause]').click();assert.equal(p.state,2);for(let i=0;i<20;i++)h.stepClock();assert.equal(h.count(),6);
  h.$('[data-recording-pause]').click();assert.equal(p.time,position);p.finish();assert.equal(h.count(),7);
});

test('seeking past the chant never counts an incomplete round',async t=>{
  const h=await open();t.after(()=>h.dom.window.close());await h.play();const p=h.instances[0];p.step();
  p.time=p.segment.endSeconds;p.options.events.onStateChange({target:p,data:0});assert.equal(h.count(),0);assert.equal(p.loads,2);
  p.finish();assert.equal(h.count(),1);
  h.$('[data-recording-pause]').click();p.time+=20;h.$('[data-recording-pause]').click();p.finish();assert.equal(h.count(),1);
});

test('pause during buffering stays paused when the player becomes ready',async t=>{
  const h=await open();t.after(()=>h.dom.window.close());await h.play();const p=h.instances[0];p.step();p.state=3;
  h.$('[data-recording-pause]').click();assert.equal(p.state,2);assert.equal(h.$('[data-recording-pause]').textContent,'继续');
  p.playVideo();assert.equal(p.state,2,'late playing event cannot undo requested pause');assert.equal(h.count(),0);
  h.$('[data-recording-pause]').click();p.finish();assert.equal(h.count(),1);
});

test('errors, source changes, close and leaving discard unfinished audio',async t=>{
  const h=await open(2);t.after(()=>h.dom.window.close());await h.play();let p=h.instances[0];p.step();p.error();
  assert.equal(h.count(),2);assert.equal(h.$('[data-recording-play]').disabled,false);
  await h.play();p=h.instances[1];p.step();h.$('[data-recording-close]').click();assert.equal(h.count(),2);assert.equal(p.destroyed,true);
  p.options.events.onStateChange({target:p,data:0});assert.equal(h.count(),2);
  await h.play();p=h.instances[2];h.w.dispatchEvent(new h.w.Event('pagehide'));assert.equal(p.destroyed,true);assert.equal(h.count(),2);
});

test('saved completion does not autoplay, and a blocked player can be started directly',async t=>{
  const h=await open(108);t.after(()=>h.dom.window.close());assert.equal(h.instances.length,0);await h.play();assert.equal(h.instances.length,0);
  h.$('#recitation-reset').click();await h.play();const p=h.instances[0];p.options.events.onAutoplayBlocked();
  assert.match(h.$('[data-recording-note]').textContent,/视频中的播放键/);assert.equal(h.count(),0);
});
