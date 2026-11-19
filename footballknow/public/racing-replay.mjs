export function replayUrl(race){
  const date=String(race.date||''),number=Number(race.raceNo),time=Date.parse(date+'T00:00:00Z');
  if(!['ST','HV'].includes(race.course)||!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Number.isFinite(time)||new Date(time).toISOString().slice(0,10)!==date||!Number.isInteger(number)||number<1||number>12||!['finished','provisional'].includes(race.status))return '';
  return 'https://racing.hkjc.com/contentAsset/videoplayer_v4/video-player-iframe_v4.html?type=replay-full&date='+date.replaceAll('-','')+'&no='+String(number).padStart(2,'0')+'&lang=chi';
}

export function replayBlock(race){
  const url=replayUrl(race);if(!url)return '';
  return `<section class="racing-replay" id="race-replay"><div class="section-head"><div><p class="eyebrow">香港赛马会 · 中文原声</p><h2>赛事回放</h2></div><a href="${url.replaceAll('&','&amp;')}" target="_blank" rel="noopener noreferrer">在官方播放器观看 ↗</a></div><div class="replay-screen" id="replay-screen"><div class="replay-placeholder"><span class="replay-icon" aria-hidden="true">▶</span><h3>${race.date} · 第 ${race.raceNo} 场</h3><p>完整赛事重温</p><button class="button" id="play-race-replay">播放本场回放</button></div></div><p class="note">视频由香港赛马会官方播放器提供，点击播放后加载。刚完场的影片可能需要等待发布；如内嵌播放器无法播放，可使用右上方官方入口。</p></section>`;
}

export function bindReplay(target,race){
  const button=target.querySelector('#play-race-replay'),screen=target.querySelector('#replay-screen'),url=replayUrl(race);
  if(!button||!screen||!url)return;
  button.addEventListener('click',()=>{
    const frame=document.createElement('iframe');
    frame.src=url;frame.title=`${race.date} 第 ${race.raceNo} 场 · 香港赛马会赛事回放`;
    frame.allow='fullscreen; autoplay';frame.allowFullscreen=true;frame.referrerPolicy='strict-origin-when-cross-origin';
    frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-presentation');
    screen.replaceChildren(frame);
  },{once:true});
}

/** Race identity of one line in a horse's past record, or null when it has no Hong Kong replay (withdrawn, overseas, not yet run). */
export function recordRace(record,today=new Date().toISOString().slice(0,10)){
  const match=/^(\d{4}-\d{2}-\d{2})-(ST|HV)-(\d{1,2})$/.exec(String(record?.raceId||''));
  if(!match||record.withdrawn||match[1]!==record.date||match[1]>today)return null;
  return {date:match[1],course:match[2],raceNo:Number(match[3]),status:'finished'};
}

export function recordReplayUrl(record,today){
  const race=recordRace(record,today);
  return race?replayUrl(race):'';
}
