import test from 'node:test';
import assert from 'node:assert/strict';
import {videoDownloadUrl,videoSourceUrl} from '../public/video-media.mjs';

test('download uses the current site and requests an attachment for a published media file',()=>{
  assert.equal(videoDownloadUrl('https://inwesting.shop/media/videos/sample.mp4','https://inwesting.shop/#/videos/one'),'/media/videos/sample.mp4?download=1');
  assert.equal(videoDownloadUrl('https://inwesting.shop/media/videos/sample.mp4','https://footballknow.art/#/videos/one'),'/media/videos/sample.mp4?download=1');
  assert.equal(videoDownloadUrl('/media/videos/sample.webm','http://localhost:8771/'),'/media/videos/sample.webm?download=1');
});

test('external and non-media addresses do not get a misleading local download button',()=>{
  for(const value of ['https://example.com/media/videos/sample.mp4','https://inwesting.shop/api/private.mp4','https://inwesting.shop/media/videos/../../private.mp4','javascript:alert(1)']){
    assert.equal(videoDownloadUrl(value,'https://inwesting.shop/'),'');
  }
});

test('owned video and poster files stay on the current site without loosening media security',()=>{
  assert.equal(videoSourceUrl('https://inwesting.shop/media/videos/a.mp4','https://www.footballknow.art/#/videos'),'/media/videos/a.mp4');
  assert.equal(videoSourceUrl('https://inwesting.shop/media/videos/a.jpg','https://www.inwesting.shop/#/videos'),'/media/videos/a.jpg');
  assert.equal(videoSourceUrl('https://example.com/a.mp4','https://inwesting.shop'),'https://example.com/a.mp4');
});
