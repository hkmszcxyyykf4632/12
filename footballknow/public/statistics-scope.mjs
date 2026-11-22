export const startDay='2026-11-22';
export const startSeason=2026;
export const startRounds={epl:11,laliga:13,seriea:12,bundesliga:10,ucl:5};
export const startText={football:'从2026/27赛季英超第11轮、西甲第13轮、意甲第12轮、德甲第10轮及欧冠联赛阶段第5轮起累计。本轮已完场赛事先计入，新完场赛事持续更新。',racing:'从2026年11月22日赛马日起累计，每场正式赛果及派彩公布后持续更新。'};
export function scopedRecords(records,domain){
 if(!Array.isArray(records))return [];
 if(domain==='racing')return records.filter(r=>r.day>=startDay);
 return records.filter(r=>{
  if(!(r.league in startRounds)||!r.round||!r.season)return false;
  const year=Number(r.season.slice(0,4)),number=Number(r.round.match(/第(\d+)轮/)?.[1]);
  return year>startSeason||(year===startSeason&&number>=startRounds[r.league]);
 });
}
