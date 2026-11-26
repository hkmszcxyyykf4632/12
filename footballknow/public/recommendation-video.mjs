import {esc} from './ui.mjs';
import {videoDownloadUrl} from './video-media.mjs';

export function recommendationVideo(candidate, clips=[]){
 const clip=clips.find(v=>v.event===candidate.event&&v.stage===candidate.stage&&(candidate.domain==='football'?v.issuedAt===candidate.issuedAt&&v.asianSide===candidate.receipt.asianSide&&v.line===candidate.receipt.line&&JSON.stringify(v.scoreCandidates)===JSON.stringify(candidate.receipt.scoreCandidates?.length?candidate.receipt.scoreCandidates:[candidate.receipt.score]):v.pick===candidate.receipt.pick));
 if(!clip||!/^\/media\/videos\/[a-z0-9-]+\.mp4$/.test(clip.url)||!/^\/media\/videos\/[a-z0-9-]+\.(jpg|png|webp)$/.test(clip.poster))return '';
 const download=videoDownloadUrl(clip.url,location.href);
 return `<div class="recommendation-video"><video controls playsinline preload="none" poster="${esc(clip.poster)}" aria-label="${esc(clip.title)}"><source src="${esc(clip.url)}" type="video/mp4"></video><p class="note">${esc(clip.title)} · 视频与此处原推荐对应</p>${download?`<a class="button secondary" href="${esc(download)}" download>下载视频</a>`:''}</div>`;
}

