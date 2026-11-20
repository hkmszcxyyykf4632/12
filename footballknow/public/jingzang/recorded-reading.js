/* Verified original recordings: Buddhist Temple, and the user-selected Buddhistdoor edition. */
(()=>{
  const lessons='https://buddhisttemple.ca/zh-hant/buddhism/lessons/';
  const video=(id,label)=>({kind:'youtube',id,label,url:'https://www.youtube.com/watch?v='+id});
  const catalogue={
    ysz:[
      {...video('MthStAd4YKI','粤语 · 观成法师原声'),start:1180,end:1221,repeat:108,rate:2,credit:'观成法师诵读 · 佛门网发布；《药师经》19:40–20:21 的药师咒段'},
      {...video('JWNB9wODEHg','国语 · 法鼓山安和分院（完整108遍）'),start:0,repeat:108,units:108,rate:1,credit:'法鼓山安和分院「安和直播」发布 · 原片自带完整 108 遍；整段播完才记为完成，暂停可继续，停止后重新播放整段'},
    ],
    ysj:[video('MthStAd4YKI','药师经 · 全篇与回向文'),video('8Bs-gagtGA4','药师经 · 国际佛教观音寺原版')],
    jgj:[video('DgI1TFjxUBQ','金刚经 · 全篇')],
    xj:[{kind:'audio',label:'心经 · 粤语导诵',url:'https://buddhisttemple.ca/wp-content/uploads/2017/02/Heart_Sutra.mp3'}],
    dzj:[video('FxKANq2yPs8','地藏经 · 卷上'),video('aCZG69gvG-M','地藏经 · 卷中'),video('Sff9emcqW-Q','地藏经 · 卷下')],
    fhj:[...[[1,'O_2qC-pDn34'],[2,'Q6IT4yEYpKQ'],[3,'7FEP9GAid_Q'],[4,'sfGX7F05pzU'],[5,'H0rn62Dmn40'],[8,'NnBnOmrDqnw'],[12,'uOXCjbTxg6o'],[25,'4UmRJT6EXdY'],[26,'9wZ3Oey7gcg'],[28,'Yl8H-Eujcoc']].map(([n,id])=>video(id,'法华经 · 原片第 '+n+' 集')),video('oYYyutTBNRQ','观世音菩萨普门品第二十五')],
  };
  const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let player=null,audio=null,epoch=0,apiPromise=null,interval=null,round=null,active=null,desiredRate=2,pauseRequested=false;
  const root=()=>document.querySelector('#recorded-reading');
  const note=text=>{const n=root()?.querySelector('[data-recording-note]');if(n)n.textContent=text;};
  function stop(){epoch++;clearInterval(interval);interval=null;round=null;active=null;player?.destroy();player=null;if(audio){audio.pause();audio.removeAttribute('src');audio=null;}const box=root()?.querySelector('[data-recording-host]');if(box){box.replaceChildren();box.hidden=true;}const button=root()?.querySelector('[data-recording-play]');if(button)button.disabled=false;const pause=root()?.querySelector('[data-recording-pause]');if(pause){pause.disabled=true;pause.textContent='暂停';}window.JingzangRecitation?.recordingStatus('ready');}
  function panel(book,chapter){
    const list=catalogue[book];if(!list)return '';
    const selected=book==='dzj'?Math.max(0,['卷上','卷中','卷下'].indexOf(chapter?.g)):book==='fhj'&&chapter?.t?.includes('普门')?list.length-1:0;
    if(book==='ysz')return `<section class="wrap recorded-reading" id="recorded-reading" data-book="ysz"><h2>药师咒 · 国语 / 粤语原声</h2><p>粤语采用观成法师《药师经》中的药师咒段，逐遍循环；国语为法鼓山安和分院的完整 108 遍课诵，整段播放。选好语言即可开始。</p><div class="recorded-controls"><label>诵读语言<select class="ctl" data-recording-source>${list.map((s,i)=>`<option value="${i}">${esc(s.label)}</option>`).join('')}</select></label><label>播放速度<select class="ctl" data-recording-rate>${[1,1.25,1.5,1.75,2].map(v=>`<option value="${v}" ${v===2?'selected':''}>${v} 倍</option>`).join('')}</select></label><button class="ctl play" data-recording-play>开始 108 遍</button><button class="ctl" data-recording-pause disabled>暂停</button><button class="ctl" data-recording-close>停止</button><a data-recording-origin href="${list[0].url}&t=${list[0].start}s" target="_blank" rel="noopener noreferrer">打开原版片段</a></div><p data-recording-note role="status">粤语默认 2 倍速；国语默认原速，也可自行调整。</p><div class="recording-host" data-recording-host hidden></div><p class="recording-credit" data-recording-credit>${list[0].credit}</p></section>`;
    return `<section class="wrap recorded-reading" id="recorded-reading" data-book="${book}"><h2>观成法师 · 真人粤语诵读</h2><p>原版声音与节奏，默认 2 倍速。可一边听，一边读下方经文。</p><div class="recorded-controls"><label>诵读版本<select class="ctl" data-recording-source>${list.map((s,i)=>`<option value="${i}" ${i===selected?'selected':''}>${esc(s.label)}</option>`).join('')}</select></label><label>播放速度<select class="ctl" data-recording-rate>${[1,1.25,1.5,1.75,2].map(v=>`<option value="${v}" ${v===2?'selected':''}>${v} 倍</option>`).join('')}</select></label><button class="ctl play" data-recording-play>播放法师原版</button><button class="ctl" data-recording-close>关闭播放</button><a data-recording-origin href="${esc(list[selected].url)}" target="_blank" rel="noopener noreferrer">打开原版页面</a></div><p data-recording-note role="status">点击播放后载入原版音视频。</p><div class="recording-host" data-recording-host hidden></div><p class="recording-credit">观成法师 · 国际佛教观音寺${book==='ysj'?'；首选视频由佛门网发布':''} · <a href="${lessons}" target="_blank" rel="noopener noreferrer">诵读来源</a>${book==='fhj'?'。按原片编号提供已核实的集数；录音与下方目录分别选择。':''}</p></section>`;
  }
  function youtubeApi(){
    if(window.YT?.Player)return Promise.resolve(window.YT);
    if(apiPromise)return apiPromise;
    apiPromise=new Promise((resolve,reject)=>{
      const tag=document.createElement('script');let done=false;
      const fail=()=>{if(done)return;done=true;clearTimeout(timer);tag.remove();reject(Error('YouTube 播放器暂时无法载入，请使用「打开原版页面」。'));};
      const previous=window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady=()=>{previous?.();if(done)return;done=true;clearTimeout(timer);resolve(window.YT);};
      const timer=setTimeout(fail,15000);tag.src='https://www.youtube.com/iframe_api';tag.onerror=fail;document.head.appendChild(tag);
    }).catch(error=>{apiPromise=null;throw error;});
    return apiPromise;
  }
  async function play(){
    const r=root();if(!r)return;const entry=catalogue[r.dataset.book]?.[Number(r.querySelector('[data-recording-source]').value)];if(!entry)return;
    stop();window.dispatchEvent(new Event('jingzang:recorded-play'));if(entry.repeat&&window.JingzangRecitation?.getCompleted()>=entry.repeat){note('已完成 108 遍，点击「重新计数」开始下一轮。');return;}pauseRequested=false;active=entry;desiredRate=Number(r.querySelector('[data-recording-rate]').value);const ticket=epoch,box=r.querySelector('[data-recording-host]');
    box.hidden=false;r.querySelector('[data-recording-play]').disabled=true;note('正在准备法师原版…');
    const valid=()=>ticket===epoch&&r===root();
    if(entry.kind==='audio'){
      audio=document.createElement('audio');audio.controls=true;audio.preload='metadata';audio.src=entry.url;audio.playbackRate=Number(r.querySelector('[data-recording-rate]').value);box.appendChild(audio);
      audio.addEventListener('ratechange',()=>{if(valid())showRate(audio.playbackRate);});
      audio.addEventListener('playing',()=>{if(valid())showRate(audio.playbackRate);});
      audio.addEventListener('error',()=>{if(valid())note('原版音频暂时无法播放，请使用「打开原版页面」。');});
      try{await audio.play();}catch{if(valid())note('请点击音频播放器中的播放键。');}return;
    }
    try{
      const YT=await youtubeApi();if(!valid())return;
      const mount=document.createElement('div');box.appendChild(mount);
      player=new YT.Player(mount,{width:'100%',height:'100%',videoId:entry.id,playerVars:{playsinline:1,origin:location.origin,rel:0},events:{
        onReady:e=>{if(!valid()){e.target.destroy();return;}const frame=e.target.getIframe();frame.title=entry.repeat?entry.label+' · 药师咒':entry.label+' · 观成法师粤语诵读';frame.setAttribute('referrerpolicy','strict-origin-when-cross-origin');if(entry.repeat){beginRound();interval=setInterval(()=>sampleRound(),250);r.querySelector('[data-recording-pause]').disabled=false;}else{setRate(desiredRate);e.target.playVideo();}},
        onPlaybackRateChange:e=>{if(valid())showRate(e.data);},
        onStateChange:e=>{if(!valid())return;if(entry.repeat){sampleRound(e.data===0);if(e.data===1){if(pauseRequested){e.target.pauseVideo();return;}if(e.target.getPlaybackRate()!==desiredRate)setRate(desiredRate);else showRate(desiredRate);window.JingzangRecitation?.recordingStatus('running',entry.units);r.querySelector('[data-recording-pause]').textContent='暂停';}else if(e.data===2&&round&&!round.finished){window.JingzangRecitation?.recordingStatus('paused',entry.units);r.querySelector('[data-recording-pause]').textContent='继续';}}else if(e.data===1)showRate(e.target.getPlaybackRate());},
        onAutoplayBlocked:()=>{if(valid())note('请点击视频中的播放键，播放速度已按所选速度设置。');},
        onError:e=>{if(valid()){console.warn('Original recording playback error',entry.id,e?.data);clearInterval(interval);round=null;window.JingzangRecitation?.recordingStatus('ready');note(entry.repeat?'原版播放器暂时不可用，可重新播放或打开原版片段；本遍未计数。':'原版播放器暂时不可用，请使用「打开原版页面」。');r.querySelector('[data-recording-play]').disabled=false;const pause=r.querySelector('[data-recording-pause]');if(pause)pause.disabled=true;}},
      }});
    }catch(error){if(valid()){note(error.message);r.querySelector('[data-recording-play]').disabled=false;}}
  }
  function beginRound(){
    if(!player||!active?.repeat)return;
    const end=active.end||player.getDuration();if(!Number.isFinite(end)||end<=active.start){note('原片时长尚未载入，请重新播放。');root().querySelector('[data-recording-play]').disabled=false;return;}
    round={start:active.start,end,last:null,wall:performance.now(),covered:0,valid:true,finished:false,playing:false};
    player.loadVideoById({videoId:active.id,startSeconds:round.start,endSeconds:round.end});
    window.JingzangRecitation?.recordingStatus('running',active.units);
  }
  function sampleRound(ended=false){
    const current=round;if(!current||current.finished||!player)return;
    const time=player.getCurrentTime(),now=performance.now(),playing=player.getPlayerState()===1;
    if(!Number.isFinite(time))return;
    if(current.last===null){if(!playing)return;if(time<current.start-.5)return;current.valid=Math.abs(time-current.start)<=1;current.covered=Math.max(0,time-current.start);}
    else{
      const delta=time-current.last,elapsed=(now-current.wall)/1000,limit=Math.max(1,Math.min(elapsed,3)*player.getPlaybackRate()+.6);
      if(delta<-.6||delta>limit||(!current.playing&&!playing&&Math.abs(delta)>.6))current.valid=false;
      else if(current.valid&&delta>0)current.covered+=delta;
    }
    current.last=time;current.wall=now;current.playing=playing;
    if(time>=current.end||ended){
      current.finished=true;
      if(current.valid&&time>=current.end-.6&&current.covered>=current.end-current.start-.6){
        const completed=window.JingzangRecitation?.completeRecordingRound(active.units||1);
        if(completed>=active.repeat){clearInterval(interval);player.pauseVideo();root().querySelector('[data-recording-pause]').disabled=true;note('已完成 108 遍。');return;}
      }else note('本遍有跳转或播放中断，未计数，正在从本遍开头重播。');
      beginRound();
    }
  }
  function showRate(rate){const select=root()?.querySelector('[data-recording-rate]');if(select&&[...select.options].some(o=>Number(o.value)===rate))select.value=String(rate);note(`原版诵读 · 当前 ${rate} 倍速`);}
  function setRate(rate){
    if(![1,1.25,1.5,1.75,2].includes(rate))return;
    if(audio){audio.playbackRate=rate;showRate(audio.playbackRate);}
    else if(player?.getAvailablePlaybackRates){const available=player.getAvailablePlaybackRates();if(available.includes(rate)){player.setPlaybackRate(rate);note('正在切换播放速度…');}else{showRate(player.getPlaybackRate());note(`原版播放器目前不支持 ${rate} 倍速，当前 ${player.getPlaybackRate()} 倍速。`);}}
  }
  document.addEventListener('click',e=>{if(e.target.closest('[data-recording-play]'))play();else if(e.target.closest('[data-recording-pause]')&&player){const button=e.target.closest('[data-recording-pause]');pauseRequested=button.textContent!=='继续';sampleRound();if(pauseRequested){player.pauseVideo();button.textContent='继续';window.JingzangRecitation?.recordingStatus('paused');}else player.playVideo();}else if(e.target.closest('[data-recording-close]')){stop();note('播放已关闭，已完成遍数保留。');}});
  document.addEventListener('change',e=>{if(e.target.matches('[data-recording-rate]')){desiredRate=Number(e.target.value);setRate(desiredRate);}else if(e.target.matches('[data-recording-source]')){stop();const entry=catalogue[root().dataset.book][Number(e.target.value)];root().querySelector('[data-recording-origin]').href=entry.url+(entry.start?'&t='+entry.start+'s':'');if(entry.repeat){root().querySelector('[data-recording-rate]').value=String(entry.rate);root().querySelector('[data-recording-credit]').textContent=entry.credit;}note('版本已选择，点击播放开始。');}});
  window.addEventListener('pagehide',stop);
  window.RecordedReading={panel,stop,has:book=>!!catalogue[book]};
})();
