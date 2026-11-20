/* Verified original recordings: Buddhist Temple, and the user-selected Buddhistdoor edition. */
(()=>{
  const lessons='https://buddhisttemple.ca/zh-hant/buddhism/lessons/';
  const video=(id,label)=>({kind:'youtube',id,label,url:'https://www.youtube.com/watch?v='+id});
  const catalogue={
    ysj:[video('MthStAd4YKI','药师经 · 全篇与回向文'),video('8Bs-gagtGA4','药师经 · 国际佛教观音寺原版')],
    jgj:[video('DgI1TFjxUBQ','金刚经 · 全篇')],
    xj:[{kind:'audio',label:'心经 · 粤语导诵',url:'https://buddhisttemple.ca/wp-content/uploads/2017/02/Heart_Sutra.mp3'}],
    dzj:[video('FxKANq2yPs8','地藏经 · 卷上'),video('aCZG69gvG-M','地藏经 · 卷中'),video('Sff9emcqW-Q','地藏经 · 卷下')],
    fhj:[...[[1,'O_2qC-pDn34'],[2,'Q6IT4yEYpKQ'],[3,'7FEP9GAid_Q'],[4,'sfGX7F05pzU'],[5,'H0rn62Dmn40'],[8,'NnBnOmrDqnw'],[12,'uOXCjbTxg6o'],[25,'4UmRJT6EXdY'],[26,'9wZ3Oey7gcg'],[28,'Yl8H-Eujcoc']].map(([n,id])=>video(id,'法华经 · 原片第 '+n+' 集')),video('oYYyutTBNRQ','观世音菩萨普门品第二十五')],
  };
  const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let player=null,audio=null,epoch=0,apiPromise=null;
  const root=()=>document.querySelector('#recorded-reading');
  const note=text=>{const n=root()?.querySelector('[data-recording-note]');if(n)n.textContent=text;};
  function stop(){epoch++;player?.destroy();player=null;if(audio){audio.pause();audio.removeAttribute('src');audio=null;}const box=root()?.querySelector('[data-recording-host]');if(box){box.replaceChildren();box.hidden=true;}const button=root()?.querySelector('[data-recording-play]');if(button)button.disabled=false;}
  function panel(book,chapter){
    const list=catalogue[book];if(!list)return '';
    const selected=book==='dzj'?Math.max(0,['卷上','卷中','卷下'].indexOf(chapter?.g)):book==='fhj'&&chapter?.t?.includes('普门')?list.length-1:0;
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
    stop();window.dispatchEvent(new Event('jingzang:recorded-play'));const ticket=epoch,box=r.querySelector('[data-recording-host]');
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
        onReady:e=>{if(!valid()){e.target.destroy();return;}const frame=e.target.getIframe();frame.title=entry.label+' · 观成法师粤语诵读';frame.setAttribute('referrerpolicy','strict-origin-when-cross-origin');setRate(Number(r.querySelector('[data-recording-rate]').value));e.target.playVideo();},
        onPlaybackRateChange:e=>{if(valid())showRate(e.data);},
        onStateChange:e=>{if(valid()&&e.data===1)showRate(e.target.getPlaybackRate());},
        onAutoplayBlocked:()=>{if(valid())note('请点击视频中的播放键，播放速度已按所选速度设置。');},
        onError:()=>{if(valid())note('原版播放器暂时不可用，请使用「打开原版页面」。');},
      }});
    }catch(error){if(valid()){note(error.message);r.querySelector('[data-recording-play]').disabled=false;}}
  }
  function showRate(rate){const select=root()?.querySelector('[data-recording-rate]');if(select&&[...select.options].some(o=>Number(o.value)===rate))select.value=String(rate);note(`原版诵读 · 当前 ${rate} 倍速`);}
  function setRate(rate){
    if(![1,1.25,1.5,1.75,2].includes(rate))return;
    if(audio){audio.playbackRate=rate;showRate(audio.playbackRate);}
    else if(player?.getAvailablePlaybackRates){const available=player.getAvailablePlaybackRates();if(available.includes(rate)){player.setPlaybackRate(rate);note('正在切换播放速度…');}else{showRate(player.getPlaybackRate());note(`原版播放器目前不支持 ${rate} 倍速，当前 ${player.getPlaybackRate()} 倍速。`);}}
  }
  document.addEventListener('click',e=>{if(e.target.closest('[data-recording-play]'))play();else if(e.target.closest('[data-recording-close]')){stop();note('播放已关闭。');}});
  document.addEventListener('change',e=>{if(e.target.matches('[data-recording-rate]'))setRate(Number(e.target.value));else if(e.target.matches('[data-recording-source]')){stop();root().querySelector('[data-recording-origin]').href=catalogue[root().dataset.book][Number(e.target.value)].url;note('版本已选择，点击播放开始。');}});
  window.addEventListener('pagehide',stop);
  window.RecordedReading={panel,stop,has:book=>!!catalogue[book]};
})();
