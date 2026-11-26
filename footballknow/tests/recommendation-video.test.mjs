import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
const dom=new JSDOM('<main id="main"></main>',{url:'https://inwesting.shop/#/recommendations'});
globalThis.document=dom.window.document;globalThis.location=dom.window.location;
const {recommendationVideo}=await import('../public/recommendation-video.mjs');
const c={event:'2026-11-25-HV-7',stage:'pre',receipt:{pick:'HK_2024_K239'}};
const clip={event:c.event,stage:'pre',pick:c.receipt.pick,url:'/media/videos/race-example.mp4',poster:'/media/videos/race-example.jpg',title:'第7场 · 顺善宝'};
test('a recommendation video is tied to the original event and horse, with silent on-demand playback',()=>{
 const html=recommendationVideo(c,[clip]); const doc=new JSDOM(html).window.document;
 const video=doc.querySelector('video'); assert.ok(video.controls);assert.equal(video.preload,'none');assert.ok(video.hasAttribute('playsinline'));assert.ok(!video.autoplay);
 assert.equal(doc.querySelector('a').getAttribute('href'),'/media/videos/race-example.mp4?download=1');
 assert.equal(recommendationVideo({...c,event:'other'},[clip]),'');
 assert.equal(recommendationVideo({...c,receipt:{pick:'other'}},[clip]),'');
 assert.equal(recommendationVideo(c,[{...clip,url:'javascript:alert(1)'}]),'');
 assert.equal(recommendationVideo(c,[{...clip,poster:'https://elsewhere.test/track.jpg'}]),'');
});

test('football clip must match frozen stage, issue time, handicap and both scores',()=>{
 const candidate={event:'123',domain:'football',stage:'initial',issuedAt:'2026-11-27T00:00:00Z',receipt:{asianSide:'H',line:-.5,score:[2,1],scoreCandidates:[[2,1],[1,0]]}};
 const video={...clip,event:'123',stage:'initial',issuedAt:candidate.issuedAt,asianSide:'H',line:-.5,scoreCandidates:[[2,1],[1,0]]};
 assert.match(recommendationVideo(candidate,[video]),/<video/);
 for(const change of [{issuedAt:'wrong'},{line:.5},{asianSide:'A'},{scoreCandidates:[[1,0],[2,1]]}])assert.equal(recommendationVideo(candidate,[{...video,...change}]),'');
});

