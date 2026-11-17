import {esc} from './ui.mjs';

export const BROADCASTS=Object.freeze([
  {name:'MPLUS · M直播',region:'mo',regionName:'澳门',leagues:['epl','laliga','seriea','bundesliga'],url:'https://www.mplus-live.com/',access:'按平台套餐及本场节目表',source:'https://apps.apple.com/cn/app/m%E7%9B%B4%E6%92%AD/id1156766016'},
  {name:'Now TV · Now Player',region:'hk',regionName:'香港',leagues:['epl','laliga'],url:'https://nowplayer.now.com/',access:'需相应体育套餐',source:'https://nowplayer.now.com/tvguide/channeldetail/632/1?isfromchannel=false&lang=zh'},
  ...[['ucl','uefa-champions-league'],['seriea','serie-a'],['bundesliga','bundesliga']].map(([league,slug])=>({name:'beIN SPORTS CONNECT',region:'hk',regionName:'香港',leagues:[league],url:`https://connect-hk.beinsports.com/en/competition/${slug}`,access:'需相应订阅',source:`https://connect-hk.beinsports.com/en/competition/${slug}`})),
  {name:'咪咕视频 · 体育',region:'cn',regionName:'中国内地',leagues:['epl','laliga'],url:'https://www.miguvideo.com/',access:'按本场节目及会员安排',source:'https://www.premierleague.com/en/news/3703577/premier-league-broadcast-deals-for-2025-2028/'},
]);
export const BROADCAST_CHECKED='2026-11-17';
export function broadcasters(league,region='all'){return BROADCASTS.filter(p=>p.leagues.includes(league)&&(region==='all'||p.region===region));}
export function broadcastLinks(league,region='all') {
  const links=broadcasters(league,region);
  return `<div class="broadcast-links">${links.length?links.map(p=>`<a class="broadcast-link" href="${esc(p.url)}" target="_blank" rel="noopener noreferrer"><strong>${esc(p.name)} ↗</strong><small>${esc(p.regionName)} · ${esc(p.access)}</small></a>`).join(''):'<p class="note">这个地区暂未收录可核实的转播入口。</p>'}</div><p class="small subtle">前往官方平台查看本场节目与观看条件。入口按赛事授权范围关联，不代表本场已确认直播；站内不直接播放。核对 ${BROADCAST_CHECKED}。</p>`;
}
