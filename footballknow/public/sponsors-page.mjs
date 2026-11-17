import {main,esc,pageHeading} from './ui.mjs';

export const SPONSORS=Object.freeze([
  {name:'茗是观茶叶',category:'古树茶 · 茶文化',description:'茗是观于2021年在台湾成立，专注古树茶与茶文化推广，产品涵盖古树白茶、普洱生茶、红茶与乌龙茶。品牌将品茶与文化艺术相结合，让茶香融入日常生活。',mark:'茗',tone:'tea',url:'https://www.msgbev.com.tw/'},
  {name:'自在堂唐卡',category:'唐卡 · 小扎卡艺术',description:'自在堂是茗是观旗下的艺术品牌，专注唐卡与小扎卡的收藏、展示及文化推广。通过作品、画师、画派与展览介绍，让更多人认识唐卡艺术的细腻笔触、丰富色彩与文化传承。',mark:'自',tone:'art',url:'https://msgart.com/ldcms'}
]);

export function sponsorCard(sponsor){
  const content='<span class="sponsor-mark" aria-hidden="true">'+esc(sponsor.mark)+'</span><span class="sponsor-category">'+esc(sponsor.category)+'</span><h2>'+esc(sponsor.name)+'</h2><p>'+esc(sponsor.description||'')+'</p>';
  const url=typeof sponsor.url==='string'&&/^https:\/\/[^/\s]+/i.test(sponsor.url)?sponsor.url:null;
  return '<article class="sponsor-card '+esc(sponsor.tone)+'">'+(url?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+content+'<span class="sponsor-visit">访问官方网站 ↗</span></a>':content)+'</article>';
}

export function renderSponsors(){
  main.innerHTML=pageHeading('赞助商','感谢合作伙伴对 Football Know 的支持。')+
    '<div class="sponsor-grid">'+SPONSORS.map(sponsorCard).join('')+'</div>';
}
