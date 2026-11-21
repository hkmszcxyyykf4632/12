/* 诵经影音：站长在这里登记自己的录音或确认过的视频链接，所有读者都能看到。
   lang 用 "国语" 或 "粤语"；type 用 "audio"（mp3 等音频地址，在页面内播放）或 "video"（打开原网页）。
   例：ddj:[{type:'audio',lang:'粤语',label:'道德经全文诵读',url:'https://你的网站/audio/ddj-yue.mp3'}] */
const MEDIA={
  ysz:[{type:'video',lang:'粤语',label:'观成法师 ·《药师经》中的药师咒原声片段',url:'https://www.youtube.com/watch?v=MthStAd4YKI&t=1180s'},
       {type:'video',lang:'国语',label:'法鼓山安和分院 · 药师咒（完整108遍）',url:'https://www.youtube.com/watch?v=JWNB9wODEHg'}],
  jgj:[{type:'video',lang:'粤语',label:'观成法师 · 跟观成法师一起诵经《金刚经》（国际佛教观音寺）',url:'https://www.youtube.com/watch?v=DgI1TFjxUBQ'},
       {type:'video',lang:'粤语',label:'观成法师 · 《金刚般若波罗蜜经》粤语恭诵',url:'https://www.youtube.com/watch?v=f_6ahQgYL5Q'},
       {type:'video',lang:'粤语',label:'观成法师讲解 · 《金刚经》全十一讲（播放清单）',url:'https://www.youtube.com/playlist?list=PLqhBSEbituts8vk90Me_bixX7sZ5YT80a'}],
  ysj:[{type:'video',lang:'粤语',label:'观成法师 · 恭诵《药师经》，跟观成法师一起诵经',url:'https://www.youtube.com/watch?v=MthStAd4YKI'},
       {type:'video',lang:'粤语',label:'观成法师 · 《药师琉璃光如来本愿功德经》，跟观成法师一起诵经（较早版本）',url:'https://www.youtube.com/watch?v=8Bs-gagtGA4'}],
  xj:[{type:'video',lang:'粤语',label:'观成法师讲解 · 《心经》第一讲',url:'https://www.youtube.com/watch?v=mDE4CKuyFlc'}],
  dzj:[{type:'video',lang:'粤语',label:'观成法师 · 《地藏菩萨本愿经》卷上，跟观成法师一起诵经',url:'https://www.youtube.com/watch?v=FxKANq2yPs8'},
       {type:'video',lang:'粤语',label:'观成法师 · 《地藏菩萨本愿经》卷中，跟观成法师一起诵经',url:'https://www.youtube.com/watch?v=aCZG69gvG-M'},
       {type:'video',lang:'粤语',label:'观成法师粤语读诵 · 《地藏菩萨本愿经》附字幕，139 分钟（他人上传）',url:'https://www.youtube.com/watch?v=zcFmNRl4bh4'},
       {type:'video',lang:'粤语',label:'观成法师粤语读诵 · 《地藏菩萨本愿经》附字幕，93 分钟（他人上传）',url:'https://www.youtube.com/watch?v=Jt3zMbvQB0Q'},
       {type:'video',lang:'粤语',label:'观成法师粤语读诵 · 《地藏菩萨本愿经》附字幕，79 分钟（他人上传）',url:'https://www.youtube.com/watch?v=7qhF0a1wxtU'},
       {type:'video',lang:'粤语',label:'观成法师粤语读诵 · 《地藏菩萨本愿经》附字幕，62 分钟（他人上传）',url:'https://www.youtube.com/watch?v=TdmO6owbUn4'},
       {type:'video',lang:'粤语',label:'观成法师讲解 · 《地藏菩萨本愿经》重要经句（午斋过堂开示）',url:'https://www.youtube.com/watch?v=C9IepLnpW1Y'}],
  fhj:[{type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 01',url:'https://www.youtube.com/watch?v=O_2qC-pDn34'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 02',url:'https://www.youtube.com/watch?v=Q6IT4yEYpKQ'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 03',url:'https://www.youtube.com/watch?v=7FEP9GAid_Q'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 04',url:'https://www.youtube.com/watch?v=sfGX7F05pzU'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 05',url:'https://www.youtube.com/watch?v=H0rn62Dmn40'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 08',url:'https://www.youtube.com/watch?v=NnBnOmrDqnw'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 12',url:'https://www.youtube.com/watch?v=uOXCjbTxg6o'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 25',url:'https://www.youtube.com/watch?v=4UmRJT6EXdY'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 26',url:'https://www.youtube.com/watch?v=9wZ3Oey7gcg'},
       {type:'video',lang:'粤语',label:'观成法师 · 《妙法莲华经》跟观成法师一起诵经 28',url:'https://www.youtube.com/watch?v=Yl8H-Eujcoc'},
       {type:'video',lang:'粤语',label:'观成法师 · 《观世音菩萨普门品第二十五》，跟观成法师一起诵经',url:'https://www.youtube.com/watch?v=oYYyutTBNRQ'},
       {type:'video',lang:'粤语',label:'观成法师粤语读诵 · 《观世音菩萨普门品》（香港戒定慧讲堂，他人上传）',url:'https://www.youtube.com/watch?v=TOfEgZzhpak'}],
  amtj:[{type:'video',lang:'粤语',label:'观成法师讲解 · 《佛说阿弥陀经》全七讲（播放清单）',url:'https://www.youtube.com/playlist?list=PLF2BA034D153CEDE2'}]
};

const MEDIA_GY={
  'ddj':[{type:'video',lang:'国语',label:'《道德经》朗读，全八十一章',url:'https://www.youtube.com/watch?v=xr2TYpCiCbY'}],
  'qjj':[{type:'video',lang:'国语',label:'《清静经》注音全文读诵（大字幕跟读）',url:'https://www.youtube.com/watch?v=19lGjEuJudg'},{type:'video',lang:'国语',label:'鲍崇茹道长诵读 ·《太上老君说常清静经》',url:'https://www.youtube.com/watch?v=d-wmMEDEifI'},{type:'video',lang:'国语',label:'《常清静经》原音唱诵版',url:'https://www.youtube.com/watch?v=4rNhalY3yXY'}],
  'xj':[{type:'video',lang:'国语',label:'《心经》读诵，拼音字幕，适合初学跟读',url:'https://www.youtube.com/watch?v=C-bYtzw8GV4'},{type:'video',lang:'国语',label:'《般若波罗蜜多心经》念诵',url:'https://www.youtube.com/watch?v=5YQBjX8O1Qo'}],
  'jgj':[{type:'video',lang:'国语',label:'见辉法师恭诵 ·《金刚般若波罗蜜经》字幕',url:'https://www.youtube.com/watch?v=ruifiWivdFw'},{type:'video',lang:'国语',label:'会常法师领众恭诵 ·《金刚般若波罗蜜经》',url:'https://www.youtube.com/watch?v=gPgA_7RktNI'},{type:'video',lang:'国语',label:'《金刚经》读诵，无配乐，大号字幕',url:'https://www.youtube.com/watch?v=TzJJGcN5_wY'}],
  'ysj':[{type:'video',lang:'国语',label:'南海寺僧团恭诵 ·《药师琉璃光如来本愿功德经》',url:'https://www.youtube.com/watch?v=0tszTzjhnRQ'},{type:'video',lang:'国语',label:'佛光山梵呗 ·《药师本愿功德经》',url:'https://www.youtube.com/watch?v=Lzc_rK0aHDg'},{type:'video',lang:'国语',label:'会常法师 ·《药师琉璃光如来本愿功德经》',url:'https://www.youtube.com/watch?v=A8fd1cOyft4'},{type:'video',lang:'国语',label:'《药师经》注音字幕，木鱼共修版',url:'https://www.youtube.com/watch?v=g8E10vlgdHg'}],
  'dzj':[{type:'video',lang:'国语',label:'悟梵法师 国语读诵 ·《地藏菩萨本愿经》',url:'https://www.youtube.com/watch?v=nBSFIczxETo'},{type:'video',lang:'国语',label:'佛光山梵呗赞颂团 ·《地藏菩萨本愿经》（播放清单）',url:'https://www.youtube.com/playlist?list=PLWysaQWs6cQy-RMeOrtPHQgAVi-huxRey'}],
  'fhj':[{type:'video',lang:'国语',label:'南海寺僧团恭诵 ·《观世音菩萨普门品》',url:'https://www.youtube.com/watch?v=SqsxGxQR2xY'},{type:'video',lang:'国语',label:'静思精舍恭诵 ·《观世音菩萨普门品》',url:'https://www.youtube.com/watch?v=lzltagg6GU4'},{type:'video',lang:'国语',label:'国语有声善书 ·《观世音菩萨普门品》',url:'https://www.youtube.com/watch?v=hJw37bvYnU0'},{type:'video',lang:'国语',label:'妙莲华 国语课诵 ·《观世音菩萨普门品》',url:'https://www.youtube.com/watch?v=JiDzz1lHDFc'}],
  'amtj':[{type:'video',lang:'国语',label:'台湾萨迦寺 ·《佛说阿弥陀经》大字注音跟诵',url:'https://www.youtube.com/watch?v=-I5w-IQnESA'},{type:'video',lang:'国语',label:'《阿弥陀经》念诵',url:'https://www.youtube.com/watch?v=3dUZBzOhuqg'}]
};
for(const k in MEDIA_GY)MEDIA[k]=MEDIA_GY[k].concat(MEDIA[k]||[]);

const VIDEOS={
  'ddj':[{type:'video',lang:'节目',label:'典籍里的中国 · 郭店楚简《道德经》的发现',url:'https://www.youtube.com/watch?v=8HQq5DCgUXg'}],
  'xj':[{type:'video',lang:'评论',label:'星云大师 ·《心经》讲解 第一集',url:'https://www.youtube.com/watch?v=kGCJ8xELuEI'}],
  'jgj':[{type:'video',lang:'评论',label:'费勇 ·《金刚经》是如何帮人消除烦恼的',url:'https://www.youtube.com/watch?v=t_uVU7fRCqk'}],
  'ly':[{type:'video',lang:'节目',label:'典籍里的中国 · 孔子“杏坛讲学”',url:'https://www.youtube.com/watch?v=qpY65WfKMHI'},{type:'video',lang:'评论',label:'傅佩荣 ·《论语》新解',url:'https://www.youtube.com/watch?v=AbdIwIiSedg'}],
  'zy':[{type:'video',lang:'评论',label:'傅佩荣 ·《中庸》新解：如何实践天命',url:'https://www.youtube.com/watch?v=l3sur-uNBew'}],
  'mz':[{type:'video',lang:'评论',label:'傅佩荣（台大开放式课程）·《孟子》解读：浩然之气',url:'https://www.youtube.com/watch?v=M-wAhHdw5Ys'},{type:'video',lang:'评论',label:'傅佩荣（台大开放式课程）·《孟子》解读：人性理论',url:'https://www.youtube.com/watch?v=9mxt-Vsm7yk'}],
  'sj':[{type:'video',lang:'节目',label:'典籍里的中国 · 中国人的浪漫都藏在《诗经》里',url:'https://www.youtube.com/watch?v=L3zDvgoVxtk'},{type:'video',lang:'节目',label:'典籍里的中国 ·《诗经》是这样形成的',url:'https://www.youtube.com/watch?v=gd2nHHQkPOI'}],
  'ss':[{type:'video',lang:'节目',label:'典籍里的中国 ·《尚书》原来也是一本“教科书”',url:'https://www.youtube.com/watch?v=Rl0Pz-9A_1A'}],
  'lj':[{type:'video',lang:'节目',label:'典籍里的中国 · 彭林、蒙曼等讲解《礼记》',url:'https://www.youtube.com/watch?v=Zd3tK1H9m7U'},{type:'video',lang:'节目',label:'典籍里的中国 ·《礼记》是怎样成书的',url:'https://www.youtube.com/watch?v=GEHcZVMlQLc'},{type:'video',lang:'节目',label:'典籍里的中国 · 出自《礼记》的大学校训',url:'https://www.youtube.com/watch?v=QGTJ7o52DEQ'}],
  'zztj':[{type:'video',lang:'评论',label:'百家讲坛 · 评说《资治通鉴》第一部（1）探寻历史的密码',url:'https://www.youtube.com/watch?v=xZUriyB-z6g'}],
  's02':[{type:'video',lang:'节目',label:'典籍里的中国 · 班家两代人接续修撰《汉书》',url:'https://www.youtube.com/watch?v=SQ0079Z48dU'}],
  's04':[{type:'video',lang:'纪录',label:'央视纪录片《官渡之战》第一集',url:'https://www.youtube.com/watch?v=O_mwia9pzCA'}],
  's13':[{type:'video',lang:'评论',label:'百家讲坛 ·《国史通鉴》隋唐五代篇（1）历史宿命',url:'https://www.youtube.com/watch?v=JEO8V-2xPZg'}],
  's16':[{type:'video',lang:'评论',label:'百家讲坛 ·《国史通鉴》隋唐五代篇（1）历史宿命',url:'https://www.youtube.com/watch?v=JEO8V-2xPZg'}],
  's17':[{type:'video',lang:'评论',label:'百家讲坛 ·《国史通鉴》隋唐五代篇（1）历史宿命',url:'https://www.youtube.com/watch?v=JEO8V-2xPZg'}],
  's18':[{type:'video',lang:'评论',label:'百家讲坛 ·《国史通鉴》隋唐五代篇（1）历史宿命',url:'https://www.youtube.com/watch?v=JEO8V-2xPZg'}],
  's19':[{type:'video',lang:'评论',label:'百家讲坛 ·《国史通鉴》隋唐五代篇（1）历史宿命',url:'https://www.youtube.com/watch?v=JEO8V-2xPZg'}],
  's24':[{type:'video',lang:'纪录',label:'纪录片《中国通史》第七十七集 永乐迁都',url:'https://www.youtube.com/watch?v=NH2L8kVh6QQ'}],
  'hlm':[{type:'video',lang:'评论',label:'欧丽娟（台大开放式课程）·《红楼梦》',url:'https://www.youtube.com/playlist?list=PLLlbohxoot2JZ3ruI91EHU-tTMx303ANf'}],
  'nj-sw':[{type:'video',lang:'评论',label:'百家讲坛 · 了不起的《黄帝内经》（1）生命百科全书',url:'https://www.youtube.com/watch?v=XYYWjiO3gU4'},{type:'video',lang:'评论',label:'百家讲坛 · 翟双庆解读《黄帝内经》（1）神秘的经典',url:'https://www.youtube.com/watch?v=-wsyhr870W4'}],
  'bcgm':[{type:'video',lang:'节目',label:'典籍里的中国 ·《本草纲目》蕴含着哪些学问',url:'https://www.youtube.com/watch?v=pFRB-g0KNsM'},{type:'video',lang:'纪录',label:'香港浸会大学 · 李时珍与《本草纲目》',url:'https://www.youtube.com/watch?v=qco6aNZe62c'}],
  'nj-ls':[{type:'video',lang:'评论',label:'百家讲坛 · 了不起的《黄帝内经》（1）生命百科全书',url:'https://www.youtube.com/watch?v=XYYWjiO3gU4'},{type:'video',lang:'评论',label:'百家讲坛 · 翟双庆解读《黄帝内经》（1）神秘的经典',url:'https://www.youtube.com/watch?v=-wsyhr870W4'}],
};
for(const k in VIDEOS)MEDIA[k]=(MEDIA[k]||[]).concat(VIDEOS[k]);
for(const k in MEDIA){const b=k.replace(/-(hsg|ldc|zl)$/,'');if(!['ddj','qjj','xj','jgj','ysj','ysz','dzj','fhj','amtj','dx','zy','ly','mz','sj','ss','lj','zyi','cq'].includes(b))delete MEDIA[k];}
const isTalk=m=>['评论','节目','纪录'].includes(m.lang)||/讲解|浅谈/.test(m.label);

const $=(s,r=document)=>r.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const store={get(k,d){try{const v=localStorage.getItem('jz-'+k);return v==null?d:JSON.parse(v);}catch{return d;}},set(k,v){try{localStorage.setItem('jz-'+k,JSON.stringify(v));return true;}catch{return false;}}};
const GROUPS=[['道','道家经典'],['佛','佛家经典'],['四书','四书'],['五经','五经'],['史','史传'],['正史','二十四史'],['小说','四大名著'],['注','古注']];
const FOUR=['dx','zy','ly','mz'];
let BOOKS=[],byId={},state={book:null,ch:0},prefs=Object.assign({mode:'orig',size:20,theme:'',lang:'zh-CN',rate:0.9,chain:true},store.get('prefs',{}));
const synth=window.speechSynthesis||null;let speaking=false,queue=[],at=0,token=0;
let recitation=null;
function loadRecitation(b){
  const saved=store.get('recitation-'+b.id,null);
  recitation=b.repeat===108?{id:b.id,target:108,completed:saved?.version===1&&Number.isInteger(saved.completed)&&saved.completed>=0&&saved.completed<=108?saved.completed:0,fullRound:false,status:'ready',saved:true}:null;
}
function recitationPanel(){
  if(!recitation)return '';
  return `<section class="wrap recitation" aria-label="一百零八遍诵读"><div class="recitation-head"><div><h2>一百零八遍诵读</h2><div class="recitation-count"><strong id="recitation-count">${recitation.completed}</strong><small> / 108 遍已完成</small></div></div><button class="ctl" id="recitation-reset">重新计数</button></div><progress id="recitation-progress" max="108" value="${recitation.completed}" aria-label="已完成诵读遍数"></progress><p id="recitation-status" role="status"></p><p>${recitation.id==='ysz'?'粤语原声逐遍计数，累计 108 遍自动停止；国语原片自带 108 遍，整段播完才确认完成。暂停可继续，停止或重新打开后从未完成片段的开头播放。':'读完整篇才计一遍，满 108 遍自动停止。进度保存在这台设备；重新打开时从下一遍的开头继续。点击中间句子可试听，不计为完整一遍。'}</p><p id="recitation-storage"></p><p>${recitation.id==='ysz'?'切换语言保留已完成次数。国语整段播放不估算中途遍数；跳过内容的片段不计数，结束后会重新播放。':'使用设备的国语或粤语合成语音。咒文音译字的读音依所选声音，唱诵版本可在「诵经影音」查找。'}</p></section>`;
}
function updateRecitation(){
  if(!recitation||!$('#recitation-count'))return;
  const r=recitation,complete=r.completed===r.target;
  $('#recitation-count').textContent=r.completed;$('#recitation-progress').value=r.completed;
  $('#recitation-status').textContent=complete?'已完成 108 遍。可重新计数开始下一轮。':r.status==='running'?(r.program===108?'正在播放国语 108 遍原版，整段播完后确认完成。':r.fullRound?`正在诵读第 ${r.completed+1} 遍`:'正在试听片段，本次不计数'):r.status==='paused'?(r.recorded?'原声已暂停，点击原声播放器的「继续」。':'已暂停，继续后从当前句开始。'):`准备诵读第 ${r.completed+1} 遍`;
  $('#recitation-storage').textContent=r.saved?'':'浏览器未能保存进度，请保留此页；关闭页面后本次计数可能丢失。';
  const p=$('#play');p.disabled=complete||!synth;if(complete)p.textContent='已完成 108 遍';else if(!speaking)p.textContent=r.status==='paused'?'▶ 继续':'▶ 开始诵读';
}
window.JingzangRecitation={
  getCompleted:()=>recitation?.completed||0,
  recordingStatus(status,units=1){if(recitation?.id!=='ysz')return;recitation.recorded=true;recitation.program=units;recitation.fullRound=status==='running';recitation.status=status;updateRecitation();},
  completeRecordingRound(units=1){if(recitation?.id!=='ysz')return 108;recitation.completed=Math.min(108,recitation.completed+(units===108?108:1));recitation.saved=store.set('recitation-ysz',{version:1,completed:recitation.completed});updateRecitation();return recitation.completed;},
};

let FAN=null,fanLoading=false;
function toFan(s){if(!FAN)return s;let out='';for(let i=0;i<s.length;){let hit=0;for(let n=Math.min(4,s.length-i);n>=2;n--){const v=FAN.p[s.substr(i,n)];if(v){out+=v;hit=n;break;}}if(hit){i+=hit;continue;}const c=s[i],v=FAN.m.get(c);out+=v||c;i++;}return out.replace(/雲(?=[：:])/g,'云');}
function fanNode(root){if(!prefs.fan||!FAN)return;const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);const list=[];while(w.nextNode())list.push(w.currentNode);for(const n of list){const p=n.parentNode;if(p&&(p.nodeName==='SCRIPT'||p.nodeName==='STYLE'||p.hasAttribute&&p.hasAttribute('data-fan')))continue;const v=toFan(n.nodeValue);if(v!==n.nodeValue)n.nodeValue=v;}}
function loadFan(then){if(FAN){then&&then();return;}if(fanLoading)return;fanLoading=true;fetch('./fanti.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(d=>{const m=new Map();for(let i=0;i<d.s.length;i++)m.set(d.s[i],d.t[i]);FAN={m,p:d.p};fanLoading=false;then&&then();}).catch(()=>{fanLoading=false;prefs.fan=false;store.set('prefs',prefs);});}
new MutationObserver(ms=>{if(!prefs.fan||!FAN)return;for(const m of ms)for(const n of m.addedNodes){if(n.nodeType===3){if(n.parentNode&&n.parentNode.hasAttribute&&n.parentNode.hasAttribute('data-fan'))continue;const v=toFan(n.nodeValue);if(v!==n.nodeValue)n.nodeValue=v;}else if(n.nodeType===1)fanNode(n);}}).observe(document.getElementById('app'),{childList:true,subtree:true});
document.addEventListener('submit',e=>{if(e.target.id!=='vadd')return;e.preventDefault();const f=new FormData(e.target),url=String(f.get('url')).trim();if(!/^https:\/\//.test(url))return;const id=f.get('book'),list=store.get('media-'+id,[]);list.push({label:String(f.get('label')).slice(0,60),url,lang:'评论',type:'video'});store.set('media-'+id,list);videoPage();});
document.addEventListener('click',e=>{const t=e.target;if(t.dataset&&t.dataset.vdel){const [id,i]=t.dataset.vdel.split(':'),list=store.get('media-'+id,[]);list.splice(Number(i),1);store.set('media-'+id,list);videoPage();}
  else if(t.id==='vexport'){const out={};BOOKS.forEach(b=>{const l=store.get('media-'+b.id,[]);if(l.length)out[b.id]=l.map(m=>({label:m.label,url:m.url,lang:m.lang||'评论'}));});const text=JSON.stringify(out,null,1),msg=$('#vmsg');if(!Object.keys(out).length){msg.textContent='还没有自己加的视频。';return;}(navigator.clipboard?navigator.clipboard.writeText(text):Promise.reject()).then(()=>{msg.textContent='已复制，共 '+Object.values(out).reduce((n,l)=>n+l.length,0)+' 支。';}).catch(()=>{msg.textContent=text;});}});
document.addEventListener('click',e=>{const b=e.target.closest&&e.target.closest('[data-fan]');if(!b)return;prefs.fan=!prefs.fan;store.set('prefs',prefs);stop();if(prefs.fan)loadFan(route);else route();});
function applyPrefs(){document.documentElement.dataset.theme=prefs.theme;document.documentElement.style.setProperty('--size',prefs.size+'px');store.set('prefs',prefs);}
function route(){window.RecordedReading?.stop();const m=/^#b-(.+)-(\d+)$/.exec(location.hash);stop();if(location.hash==='#yi')yiPage();else if(location.hash==='#video')videoPage();else if(location.hash==='#zang')zangPage();else if(location.hash==='#cha')chaPage();else if(m&&byId[m[1]])reader(byId[m[1]],Math.min(byId[m[1]].ch.length,Math.max(1,+m[2]))-1);else shelf();window.scrollTo(0,0);}
const href=(b,i)=>`#b-${b.id}-${i+1}`;
const shelfOf=b=>b.cat==='儒'?(FOUR.includes(b.id)?'四书':'五经'):b.cat;

function videoPage(){
  state.book=null;document.title='视频区 · 经藏';
  const groups=GROUPS.concat([['医','医书']]);
  $('#app').innerHTML=`<div class="wrap"><header class="site"><a class="back" href="#">← 经藏</a><h1>视频区</h1><p>只放对经书的解释和评论。诵经的影音在各部经的阅读页右侧。只选近年制作、画质较好、篇幅不长的片段，每部书最多三支，宁缺毋滥；点开会到 YouTube 观看。</p></header>
    ${groups.map(([key,label])=>{const mine=b=>store.get('media-'+b.id,[]).map((m,i)=>({...m,mine:i}));const list=BOOKS.filter(b=>(b.cat==='医'?'医':shelfOf(b))===key&&((MEDIA[b.id]||[]).some(isTalk)||mine(b).length));return list.length?`<div class="shelf-title"><h2>${label}</h2><span>${list.length} 部书有视频</span></div><div class="vids">${list.map(b=>`<section><h3><a href="${href(b,0)}">${esc(b.full)}</a></h3><ul>${(MEDIA[b.id]||[]).filter(isTalk).concat(mine(b)).map(m=>`<li><span>${m.mine!=null?'自加':esc(m.lang)}</span><div><a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.label)}</a>${m.mine!=null?` <button class="vdel" data-vdel="${b.id}:${m.mine}">删除</button>`:''}</div></li>`).join('')}</ul></section>`).join('')}</div>`:'';}).join('')}
    <div class="shelf-title"><h2>添加视频</h2><span>站长自己放视频的地方</span></div>
    <form class="vadd" id="vadd"><label>哪一部书<select class="ctl" name="book">${BOOKS.map(b=>`<option value="${b.id}">${esc(b.full)}</option>`).join('')}</select></label><label>标题<input class="ctl" name="label" maxlength="60" required placeholder="如：某某老师讲《心经》"></label><label>视频网址<input class="ctl" name="url" type="url" required placeholder="https://"></label><button class="ctl play">加进视频区</button></form>
    <p class="vnote">加进去的视频先存在这台设备的浏览器里，只有你自己看得到。要让所有访客都看到，按下面的按钮把清单复制出来：现在可以直接发给帮你维护网站的人；等网站搬到自己的网域后，把它存成网站目录下的 videos.json 档案就会生效，不必改程式。</p>
    <p><button class="ctl" id="vexport">复制我加的视频清单</button> <span id="vmsg" class="vnote"></span></p>
    <footer>视频都是外站连结，版权属于各自的制作单位；如果连结失效或内容不合适，请告诉站长更换。还没有视频的书会陆续补上。</footer></div>`;
}
/* 唐卡图片：把照片放进 images/tangka/ 目录，在这里登记档名与说明，页面就会显示。 */
const TANGKA=[]; /* {key:'shuiyue',file:'xxx.jpg',caption:'水月观音 · 噶玛噶赤画派'} */
const ZUN=[{"k":"shuiyue","n":"水月观音","d":"观音菩萨的一种形象：菩萨闲坐水边岩石上，静观水中月影，比喻世间万象如水中之月，看得见而没有实体。这个样式相传由唐代画家周昉创出，宋元时期在汉地的壁画、雕塑中极为流行，后来也进入藏地绘画。噶玛噶赤画派本来就吸收了汉地山水的画法，画水月观音尤其相宜。","w":[["水月观音（噶玛噶赤画派，德吉卓嘎绘）","808"]]},{"k":"molizhi","n":"摩利支天","d":"梵名的意思是“光”或“阳焰”，藏语称“具光佛母”。经中说她常行于日前，日不见她，她能见日，无人能捉、能害，所以古来被奉为护身、隐身、免于刀兵之难的本尊。唐代不空等人译出《摩利支天经》后传遍汉地，日本武士也多供奉；道教的斗姆元君与她的形象相通。她常坐在猪拉的车上或骑猪，手持针线与无忧树枝，针线用来缝住恶人的口眼。","w":[["摩利支天·坐姿（勉唐画派，晋美绘）","1052"],["摩利支天·站姿多尊（勉萨画派孜东风格，多吉旺久绘）","1051"]]},{"k":"daweide","n":"大威德金刚","d":"又称怖畏金刚，是文殊菩萨为降伏死主阎魔而现的忿怒相：水牛头，九面、三十四臂、十六足，脚下踩着诸天与鸟兽，表示智慧能摧破死亡与一切障碍。这一法门十一世纪由热译师等人从印度、尼泊尔传入西藏，各派都修。宗喀巴极为重视，格鲁派把他同密集金刚、胜乐金刚并列为三大本尊。","w":[["大威德金刚·多尊（齐岗画派）","1047"]]},{"k":"mahagala","n":"六臂玛哈嘎拉","d":"玛哈嘎拉意为“大黑天”，原是印度的神祇，被佛教吸收为护法。六臂的这一尊被认为是观音菩萨为护持佛法而化现的智慧护法，身黑蓝色，六手持钺刀、颅器、念珠、三叉戟等。十一世纪由香巴噶举的祖师琼波南觉传入西藏，后来成为格鲁派最重要的护法之一，在蒙古地区也广受供奉。","w":[["黑六臂玛哈嘎拉（勉唐画派，索朗次仁绘）","1045"]]},{"k":"baozhang","n":"宝帐怙主","d":"玛哈嘎拉的另一种身相，出自《金刚帐续》，是萨迦派的主要护法。他身形矮壮，两手在胸前持钺刀与颅器，双臂上横托一根木杖，传说寺院里的护法都藏身在这根杖中。元代萨迦派的八思巴受封为帝师，宝帐怙主也随之被供奉于元朝宫廷。","w":[["宝帐怙主（勉萨画派，欧珠绘）","1024"]]},{"k":"sansheng","n":"西方三圣","d":"阿弥陀佛居中，左右是观世音菩萨与大势至菩萨，合称西方三圣，出自《观无量寿经》等净土经典。阿弥陀佛在成佛前发愿建成没有苦难的极乐世界，凡是愿意往生的人都接引。藏地称阿弥陀佛为“无量光佛”，身红色，双手捧钵；祈愿往生极乐世界的发愿文是各派共同的日常功课。","w":[["西方三圣·极乐世界（勉萨画派孜东风格，多吉旺久绘）","1044"]]},{"k":"sanzun","n":"文殊三尊（三怙主）","d":"文殊菩萨、观音菩萨、金刚手菩萨合称“三怙主”，分别代表佛的智慧、慈悲与力量，是西藏最常见的组合，山口的石刻、寺院的壁画上处处可见。藏人把吐蕃的三位法王也同他们对应起来：松赞干布是观音，赤松德赞是文殊，赤热巴巾是金刚手。","w":[["文殊三尊（勉萨画派孜东系，次仁罗杰绘）","1040"]]},{"k":"baiwenshu","n":"白文殊","d":"文殊菩萨是智慧的象征，常见的是橘黄色、右手举剑的样子；白文殊是他的另一种身相，身色洁白，手持青莲，莲上托着经书与剑。学经的僧人和读书的孩子多修持白文殊，祈求增长记忆与理解。","w":[["白文殊（勉萨画派孜东风格，多吉旺久绘）","1037"]]},{"k":"caishen","n":"五姓财神","d":"藏语称“藏巴拉”，源自印度的财富之神，佛教中视为布施资粮、使修行人免于匮乏的护法，而不只是求财。按身色分黄、白、红、黑、绿五位，以黄财神为首。他们左手多握一只口吐珍宝的鼬鼠。相传白财神是阿底峡尊者见到穷人受苦而落泪时，由观音菩萨的悲心化现，骑在龙上；红财神主要由萨迦派传承。","w":[["黄财神（勉萨画派，欧珠绘）","1033"],["白财神（勉萨画派，欧珠绘）","1028"],["红财神·骑龙（勉萨画派，欧珠绘）","1032"],["黑财神（勉萨画派，欧珠绘）","1029"],["黑财神（齐岗画派，次仁罗杰绘）","1036"],["绿财神（勉萨画派，欧珠绘）","1025"]]}];

function zangPage(){
  state.book=null;document.title='藏传佛教与唐卡 · 经藏';
  const _unused=TANGKA.length?`<div class="tangka">${TANGKA.map(t=>`<figure><img src="./images/tangka/${esc(t.file)}" alt="${esc(t.caption)}" loading="lazy"><figcaption>${esc(t.caption)}${t.credit?`<small>${esc(t.credit)}</small>`:''}</figcaption></figure>`).join('')}</div>`:`<p class="caution">唐卡照片还没有放上来。站长提供照片后，会按题材配在下面各段旁边。</p>`;
  $('#app').innerHTML=`<div class="wrap"><header class="site"><a class="back" href="#">← 经藏</a><h1>藏传佛教与唐卡</h1><p>佛教传入青藏高原之后，同当地文化结合，形成了汉传、南传之外的第三大传统。唐卡是它最有代表性的艺术。</p></header>
  <div class="essay">
  <h2>藏传佛教</h2>
  <p>公元七世纪，吐蕃赞普松赞干布在位时，佛教从印度、尼泊尔和唐朝两个方向传入西藏。相传文成公主与尼泊尔的尺尊公主各自带来佛像，拉萨的大昭寺、小昭寺就是为供奉这些佛像而建。</p>
  <p>八世纪后半，赞普赤松德赞从印度请来学者寂护和密教大师莲花生，建成西藏第一座有僧团的寺院桑耶寺，开始大规模翻译佛经。这一段称为“前弘期”。九世纪中叶朗达玛禁佛，佛教在卫藏中断了一百多年。</p>
  <p>十世纪末佛教从阿里和青海两地重新传回，称为“后弘期”。1042 年印度高僧阿底峡入藏，整顿教法，影响深远。此后各教派陆续形成：</p>
  <dl><dt>宁玛派</dt><dd>最古老的一派，奉莲花生为祖师，传承前弘期译出的密法，以“大圆满”为最高教法。</dd>
  <dt>萨迦派</dt><dd>十一世纪创于后藏萨迦寺，由昆氏家族世代相传，以“道果”教法著称。十三世纪萨迦班智达与八思巴同元朝建立了密切关系。</dd>
  <dt>噶举派</dt><dd>由玛尔巴、米拉日巴师徒传下，重视师徒口传与实修，教法以“大手印”为核心。活佛转世的制度最早出现在这一派的噶玛噶举。</dd>
  <dt>格鲁派</dt><dd>十五世纪初由宗喀巴创立，1409 年建甘丹寺。强调戒律和先显后密的次第，后来成为藏区最大的教派，达赖、班禅两个转世系统都属于这一派。</dd></dl>
  <p>藏传佛教的经典总集称《甘珠尔》（佛所说的经与律）和《丹珠尔》（历代论师的注疏），合计四千余部，大多译自梵文。它的特点是显教与密教并重，讲究师承，学经制度严格，有辩经的传统。今天流传于西藏、青海、四川、甘肃、云南、内蒙古，以及蒙古国、不丹、尼泊尔和印度北部的喜马拉雅地区。</p>
  <h2>唐卡</h2>
  <p>“唐卡”是藏语的音译，指可以卷起来的卷轴画。游牧和朝圣的生活需要随身携带圣像，画在布上、能卷能挂的唐卡就成了移动的佛堂。它用来供奉礼拜，也是修行人观想的依据和法师讲法时的图示。</p>
  <h3>种类</h3>
  <p>按做法分两大类。一类是画出来的，藏语叫“止唐”，在棉布上用矿物和植物颜料绘制，最为常见；一类是用丝绸做的，叫“国唐”，包括刺绣、缂丝、堆绣和贴花。大型的堆绣唐卡可以有几十米高，在“晒佛节”时铺展在山坡上。</p>
  <p>绘画唐卡又按底色分：五彩底的叫彩唐，金底的叫金唐，朱红底的叫朱红唐，黑底上用金线勾画的叫黑唐，多用来画护法神。</p>
  <h3>画些什么</h3>
  <dl><dt>尊像</dt><dd>佛、菩萨、度母、本尊与护法，如释迦牟尼、四臂观音、绿度母、文殊。</dd>
  <dt>祖师</dt><dd>莲花生、米拉日巴、宗喀巴等各派祖师，常在四周画出他们的生平事迹。</dd>
  <dt>坛城</dt><dd>又称曼荼罗，以圆和方层层相套，表现本尊所居的宫殿与清净世界。</dd>
  <dt>教义图</dt><dd>如六道轮回图，由无常之神抱持一个大轮，分格画出众生流转的六种去处。</dd>
  <dt>故事</dt><dd>佛陀的生平与前世故事，以及历史人物和事件。</dd>
  <dt>医学与历算</dt><dd>十七世纪第司·桑结嘉措主持绘制了一套解说《四部医典》的医学挂图，藏语称“曼唐”，画出人体、药物、诊法与治疗。</dd></dl>
  <h3>怎样画成</h3>
  <ol><li>把棉布绷在木框上，刷胶和石粉，两面反复打磨到平滑。</li>
  <li>起稿。佛像的身量比例有严格规定，画师依《造像量度经》先打出格线，再勾出形体。</li>
  <li>上色。颜料多取自矿物：石青、石绿、朱砂、雄黄，加上金和银，所以几百年不褪色。</li>
  <li>勾线、描金，画出衣纹和装饰。</li>
  <li>最后画眼睛，称为“开眼”，是整幅画最郑重的一步。</li>
  <li>用锦缎镶边，上下装木轴，前面加一层遮护的丝帘；请僧人诵经开光之后，才算完成。</li></ol>
  <h3>画派与传承</h3>
  <p>十五、十六世纪形成了几个主要画派：勉唐派流行于卫藏，法度严谨；钦泽派色彩浓重，长于画护法与坛城；噶玛嘎孜派流行于康区，吸收了汉地山水画的青绿设色，画面疏朗。青海同仁一带的“热贡艺术”以唐卡、堆绣和雕塑闻名，2009 年列入联合国教科文组织的人类非物质文化遗产代表作名录。</p>
  <h3>怎样看一幅唐卡</h3>
  <p>先看正中最大的一位，那是主尊。他的肤色、手势和手里拿的东西说明他是谁：比如文殊右手举剑、左手持经，绿度母身绿、右腿前伸。主尊上方通常是这一法门的传承祖师，下方是护持它的护法神，四周是眷属或故事。背后往往写着咒语或题记。</p>
  <h2>唐卡里的诸尊</h2>
  <p>下面这几位都是唐卡上常见的主尊，画像由本站的赞助者自在堂提供。自在堂是台湾茗是观旗下的品牌，从事西藏唐卡与小扎卡的收藏和推广。</p>
  ${ZUN.map(z=>{const pics=TANGKA.filter(t=>t.key===z.k);return `<section class="zun"><h3>${z.n}</h3>${pics.length?`<div class="tangka">${pics.map(t=>`<figure><img src="./images/tangka/${esc(t.file)}" alt="${esc(t.caption)}" loading="lazy"><figcaption>${esc(t.caption)}<small>自在堂 藏</small></figcaption></figure>`).join('')}</div>`:`<div class="tangka"><div class="slot">${z.n}<small>画像待补</small></div></div>`}<p>${z.d}</p><p class="zun-links">自在堂的画像：${z.w.map(([t,n])=>`<a href="https://msgart.com/ldcms/fuwuanli/${n}.html" target="_blank" rel="noopener">${t}</a>`).join('、')}</p></section>`;}).join('')}
  <p><a href="https://msgart.com/" target="_blank" rel="noopener">自在堂网站 msgart.com</a></p>
  </div>
  <footer>以上是通行说法的简要整理，各教派自身的传承记载或有不同。</footer></div>`;
}
const CHAPICS=[
  {key:'msg-tray',file:'msg-tea-tray.png',name:'古树茶小饼',kind:'product'},
  {key:'msg-cakes',file:'msg-tea-cakes.png',name:'茶饼与茶席',kind:'product'},
  {key:'msg-balls',file:'msg-tea-balls.png',name:'茶丸与茶汤',kind:'product'},
  {key:'msg-box',file:'msg-tea-gift-box.png',name:'茶饼礼盒',kind:'product contain'},
  {key:'msg-taste',file:'msg-taste-award-2022.png',name:'2022 风味绝佳奖 · 三星',kind:'badge'},
  {key:'msg-gold',file:'msg-monde-gold-2022.png',name:'2022 Monde Selection · 金奖',kind:'badge'},
  {key:'msg-certificate',file:'msg-monde-grand-gold-2025.png',name:'2025 野生古树白茶 · 特金奖证书',kind:'document'},
  {key:'msg-timeline',file:'msg-awards-2022-2025.png',name:'茗是观获奖年表 · 2022—2025',kind:'document'}
];
const chaGallery=(keys,style='')=>`<div class="tangka cha-pics ${style}">${keys.map(key=>CHAPICS.find(pic=>pic.key===key)).filter(Boolean).map(pic=>`<figure class="tea-${pic.kind}"><a href="./images/cha/${pic.file}" target="_blank" rel="noopener" aria-label="查看原图：${esc(pic.name)}（新窗口）"><img src="./images/cha/${pic.file}" alt="${esc(pic.name)}" loading="lazy" decoding="async"></a><figcaption>${esc(pic.name)}<a class="tea-original" href="./images/cha/${pic.file}" target="_blank" rel="noopener" aria-label="查看原图：${esc(pic.name)}（新窗口）">查看原图 ↗</a></figcaption></figure>`).join('')}</div>`;
function chaPage(){
  state.book=null;document.title='茶 · 经藏';
  $('#app').innerHTML=`<div class="wrap"><header class="site"><a class="back" href="#">← 经藏</a><h1>茶</h1><p>中国是茶的故乡。一片树叶，从药用、食用到品饮，走了几千年，也把儒、释、道三家的心思都泡了进去。</p></header>
  <div class="essay">
  <h2>茗是观的茶</h2>
  <p>本站的赞助者茗是观（MSG Ltd.）2021 年在台湾成立，以古树茶为主：野生古树白茶、古树普洱生茶、古树红茶，另有乌龙茶。旗下的自在堂从事唐卡的收藏与推广。</p>
  ${chaGallery(['msg-tray','msg-cakes','msg-balls','msg-box'],'tea-products')}
  <h3>国际评鉴与获奖记录</h3>
  <p>从茶席到国际评鉴，留下每一年的记录。下方展示茗是观提供的奖章、证书及 2022—2025 年获奖年表；点选图片可查看完整原图。</p>
  ${chaGallery(['msg-taste','msg-gold'],'tea-badges')}
  <p>2025 年 Monde Selection 证书列明，MSG Ltd. 的 Wild Old Tree White Tea（野生古树白茶）获 Grand Gold Quality Award（特金奖）。其他茶款与年份见获奖年表。</p>
  ${chaGallery(['msg-certificate','msg-timeline'],'tea-documents')}
  <p class="tea-credit">茶品照片及获奖资料由茗是观提供。<a href="https://www.msgbev.com.tw/" target="_blank" rel="noopener">走进茗是观官网 ↗</a></p>
  <h2>茶的来历</h2>
  <dl><dt>上古至汉</dt><dd>传说神农尝百草，遇毒，得茶而解。可靠的记载里，茶最早出在巴蜀一带。西汉王褒的《僮约》写到“烹茶”“武阳买茶”，说明那时四川已有茶的买卖和饮用。</dd>
  <dt>魏晋南北朝</dt><dd>饮茶从西南沿长江传到江南，士人以茶待客，僧人用茶提神坐禅。</dd>
  <dt>唐</dt><dd>茶成为举国之饮。陆羽写成《茶经》三卷，从茶的起源、采制、器具讲到煮饮，是世界上第一部茶书，后人尊他为“茶圣”。当时的茶是蒸压成饼的，喝的时候碾碎了煮。</dd>
  <dt>宋</dt><dd>制茶更精，饮法改为“点茶”：把茶末放在盏中，注入沸水，用茶筅击打出细沫。文人之间流行“斗茶”，宋徽宗亲自写了《大观茶论》。这套方法传到日本，演变成后来的抹茶道。</dd>
  <dt>明</dt><dd>洪武二十四年（1391），朱元璋下令停造费工的团茶，改贡散叶茶。从此用沸水直接冲泡叶茶成为主流，一直沿用到今天。紫砂壶也在这时兴起。</dd>
  <dt>清</dt><dd>红茶、乌龙茶等制法先后成熟，六大茶类齐备。茶经由海路大量销往欧洲，又沿茶马古道运往西藏和西南边地。</dd>
  <dt>今天</dt><dd>2022 年，“中国传统制茶技艺及其相关习俗”列入联合国教科文组织人类非物质文化遗产代表作名录。</dd></dl>
  <h2>六大茶类</h2>
  <p>同一种茶树的叶子，因为制法不同，可以做成六类茶。区别主要在于叶子里的成分氧化到什么程度（俗称“发酵”）。</p>
  <table class="cha"><thead><tr><th>茶类</th><th>制法要点</th><th>茶汤与滋味</th><th>代表</th></tr></thead><tbody>
  <tr><td>绿茶</td><td>采后尽快高温杀青，不让它氧化</td><td>汤色清绿，鲜爽</td><td>西湖龙井、碧螺春、黄山毛峰</td></tr>
  <tr><td>白茶</td><td>不炒不揉，只摊晾、干燥</td><td>汤色浅黄，清甜</td><td>白毫银针、白牡丹、寿眉</td></tr>
  <tr><td>黄茶</td><td>杀青后多一道“闷黄”</td><td>黄叶黄汤，醇和</td><td>君山银针、蒙顶黄芽、霍山黄芽</td></tr>
  <tr><td>青茶（乌龙茶）</td><td>摇青使叶缘部分氧化，再炒制</td><td>汤色金黄至橙红，香气高</td><td>武夷岩茶、铁观音、凤凰单丛、冻顶乌龙</td></tr>
  <tr><td>红茶</td><td>揉捻后充分氧化</td><td>红汤红叶，甜醇</td><td>正山小种、祁门红茶、滇红</td></tr>
  <tr><td>黑茶</td><td>渥堆，在湿热和微生物作用下后发酵</td><td>汤色深红褐，陈醇</td><td>普洱熟茶、安化黑茶、六堡茶</td></tr>
  </tbody></table>
  <p>普洱茶分生茶和熟茶。熟茶用渥堆工艺制成，属于黑茶；生茶不经渥堆，靠存放慢慢转化，它该归入哪一类，茶界有不同的看法。</p>
  <h2>古树茶</h2>
  <p>茶树原产于中国西南。云南澜沧江两岸的山里，至今保存着成片的古茶园。这里的茶树是乔木型的大叶种，不修剪的话能长到几米甚至十几米高，采茶要爬到树上。树龄一百年以上的，习惯上称为古树；这个说法是茶界的约定，并没有全国统一的标准。</p>
  <h3>同茶园茶有什么不同</h3>
  <p>上世纪八十年代起，云南大量开辟密植的新式茶园，茶树修剪成齐腰高，成行成垄，产量高，当地叫“台地茶”。古茶园正好相反：茶树稀稀落落长在森林里，同樟树、杂木混生，靠落叶做肥，不打药、不施化肥，一棵树一年只采得出很少的茶。</p>
  <p>茶人普遍认为，古树根扎得深，叶子里的内含物多，所以滋味厚，苦涩化得快，回甘长，十几泡之后还有味道。</p>
  <h3>历史</h3>
  <p>在这一带最早种茶的是布朗族、傣族、哈尼族、拉祜族等民族的先民。景迈山的布朗族世代相传，祖先帕哎冷带领族人在林中种下茶树，留下遗训：留金银会用完，留牛马会死去，只有留下茶树，子孙才取之不尽。</p>
  <p>唐代樊绰的《蛮书》已经记载“茶出银生城界诸山”，指的就是今天的普洱、西双版纳一带。清雍正七年（1729）设普洱府，这里的茶以集散地为名，称普洱茶，并成为贡茶；茶叶压成饼和砖，由马帮沿茶马古道运往西藏、内地和东南亚。</p>
  <h3>有名的茶山</h3>
  <dl><dt>西双版纳</dt><dd>澜沧江以东是清代就出名的“古六大茶山”，以易武为代表，茶汤柔和甜润；江西边的勐海有布朗山、南糯山、贺开等，其中老班章的茶以气势强劲著称。</dd>
  <dt>普洱</dt><dd>景迈山有连片上万亩的古茶林，茶带兰花香；宁洱的困鹿山是清代的皇家贡茶园。</dd>
  <dt>临沧</dt><dd>双江的冰岛茶以甜著称，昔归的茶香高水细；凤庆有一棵被称为“锦绣茶祖”的大茶树，当地说已有三千多年。</dd></dl>
  <p>2023 年，“普洱景迈山古茶林文化景观”列入世界文化遗产，是全世界第一处以茶为主题的世界遗产。</p>
  <h3>怎样做成</h3>
  <ol><li>春天和秋天各采一季，以清明前后的头春茶最好，一般采一个芽带两三片叶。</li>
  <li>鲜叶摊晾后下锅杀青，趁热揉捻成条。</li>
  <li>摊在竹席上用太阳晒干，这就是“晒青毛茶”。晒干而不是烘干，是普洱茶日后能继续转化的关键。</li>
  <li>毛茶用蒸汽蒸软，装进布袋压成饼。传统的一饼重三百五十七克，七饼一筒，叫“七子饼”。</li></ol>
  <p>这样做出来的是生茶，新茶清香、有苦涩，存放几年到几十年，汤色由黄转红，滋味变得醇厚，所以有“越陈越香”的说法。存放要干燥、通风、避光，远离有气味的东西。</p>
  <h3>买茶时留意</h3>
  <p>古树茶产量少、价格高，市面上树龄和山头被夸大的情况很常见，也没有统一的鉴定办法。树龄几百年、上千年的说法多半出自估计。可靠的做法是找信得过的茶商，多试喝，以自己喝到的滋味为准。</p>
  <h2>怎样泡</h2>
  <table class="cha"><thead><tr><th>茶类</th><th>水温</th><th>要点</th></tr></thead><tbody>
  <tr><td>绿茶、黄茶</td><td>80 至 85 度</td><td>水太烫会把嫩芽烫熟，发苦</td></tr>
  <tr><td>白茶</td><td>85 至 95 度</td><td>新茶水温低些，老白茶可以煮</td></tr>
  <tr><td>红茶</td><td>90 至 95 度</td><td>出汤要快，久泡发酸涩</td></tr>
  <tr><td>乌龙茶</td><td>沸水</td><td>先温壶，高冲，才逼得出香气</td></tr>
  <tr><td>黑茶、普洱</td><td>沸水</td><td>第一道快冲倒掉，用来醒茶</td></tr>
  </tbody></table>
  <p>器具不必讲究，一只盖碗就能泡所有的茶。茶叶和水的比例、浸泡的时间，按自己的口味增减。</p>
  <h2>茶与三家</h2>
  <p>茶同本站收的这些书是连着的。</p>
  <dl><dt>茶与禅</dt><dd>僧人坐禅要不睡，寺院自古种茶、饮茶。唐代赵州和尚对来参学的人不论新到旧到，都说一句“吃茶去”；宋代有“禅茶一味”的说法。把饮茶带到日本的，正是到中国求法的僧人。</dd>
  <dt>茶与道</dt><dd>道家讲清静、养生，把茶看作轻身、涤烦的草木之精。陆羽说茶最宜“精行俭德之人”，这四个字是儒家的修身，也是道家的简朴。</dd>
  <dt>茶与儒</dt><dd>客来敬茶是礼。文人以茶会友，诗文里写茶的不计其数；《红楼梦》里妙玉用梅花上的雪水烹茶，就是把茶当作品格来写。</dd></dl>
  </div>
  <footer>以上是通行说法的简要整理。茶是饮品，不是药；身体不适请找医师。</footer></div>`;
}
function yiPage(){
  state.book=null;document.title='医书 · 经藏';const list=BOOKS.filter(b=>b.cat==='医');
  $('#app').innerHTML=`<div class="wrap yi"><header class="site"><a class="back" href="#">← 经藏</a><h1>医书</h1><p>《黄帝内经》与《本草纲目》。前者讲医理，是中医理论的源头；后者讲药物，是明代以前本草学的总汇。同样可以逐句朗读。</p></header>
    <p class="caution">这些是古代医书，供阅读和了解传统医学之用。书中的方剂、剂量和一部分药物（含汞、砷、铅的矿物药与有毒草药等），按今天的认识并不安全。身体不适请找合格的医师，不要照书自行用药。</p>
    <div class="shelf-title"><h2>黄帝内经</h2><span>素问、灵枢各八十一篇</span></div><div class="shelf">${(l=>CARDS(l))(list.filter(b=>b.id.startsWith('nj-')))}</div>
    <div class="shelf-title"><h2>本草</h2><span>五十二卷</span></div><div class="shelf">${CARDS(list.filter(b=>b.id==='bcgm'))}</div>
    <footer>文字据公版古籍电子本整理，尚未逐卷校对；《本草纲目》原书的药图没有收录。</footer></div>`;
}
const CARDS=list=>`${list.map(b=>`<a class="book" href="${href(b,0)}"><div class="cover"><div class="slip ${b.name.length>4?'long':''}">${esc(b.name)}</div>${b.plain?'<span class="badge">白话</span>':''}</div><div class="book-meta"><b>${esc(b.full)}</b>${esc(b.by)}<br>${b.ch.length} 章 · ${b.chars.toLocaleString()} 字</div></a>`).join('')}`;
function shelf(){
  queueMicrotask(()=>window.jingzangCountVisit(document.querySelector('#culture-visits')));
  state.book=null;document.title='经藏 · 经、史、医书与四大名著';
  const last=store.get('last',null),lb=last&&byId[last.book];
  $('#app').innerHTML=`<div class="wrap"><header class="site"><h1>经藏</h1><p>中华文化的根，在这些书里。这里把道、佛、儒三家的经典，连同正史、医书与四大名著放在一处，不收费，没有广告，可以读，也可以听，愿更多人翻开它们。</p><p>原文逐句朗读，国语粤语可选；已译的经文附白话对照。</p>
    <p class="site-visits">访问次数 <strong id="culture-visits" aria-live="polite">—</strong></p>
    <a class="side-door" href="#b-ysz-1">药师咒 · 108 遍</a><a class="side-door" href="#b-dbz-1">大悲咒 · 108 遍</a><a class="side-door" href="#yi">医书：黄帝内经、本草纲目</a><a class="side-door" href="#zang">藏传佛教与唐卡</a><a class="side-door" href="#cha">茶</a><a class="side-door" href="#video">视频区</a><button class="side-door" data-fan>${prefs.fan?'简体':'繁體'}</button>
    ${lb?`<a class="resume" href="${href(lb,Math.min(last.ch,lb.ch.length-1))}">接着上次读：${esc(lb.name)} · ${esc(lb.ch[Math.min(last.ch,lb.ch.length-1)].t)}</a>`:''}</header>
    <div class="shelf-title"><h2>从这里读起</h2><span>第一次来，不妨先翻这几篇</span></div><ul class="starts">${[['xj',1,'心经','二百六十字，三分钟读完，汉传佛教最常念诵的一部经。附白话。'],['ddj',1,'道德经 · 第一章','“道可道，非常道。”八十一章都很短，每章附白话。'],['ly',1,'论语 · 学而第一','孔子怎样谈学习、交友和做人。附白话。'],['dx',1,'大学','一千七百多字，讲从修身到平天下的次第。附白话。'],['sgyy',1,'三国演义 · 第一回','桃园三结义。章回小说适合用听的。'],['s01',7,'史记 · 项羽本纪','鸿门宴、垓下之围，司马迁最有名的一篇。']].filter(x=>byId[x[0]]).map(([id,n,t,d])=>`<li><a href="#b-${id}-${n}">${t}</a><span>${d}</span></li>`).join('')}</ul>
    <div class="shelf-title"><h2>三家源流</h2><span>道教、佛教与儒家经典的来历</span></div><div class="origins"><section><h3>道教</h3><p>道教是中国本土生长出来的宗教。思想源头是先秦的老子、庄子，东汉时结合神仙方术与民间信仰成为有组织的教团，尊老子为太上老君，奉《道德经》为根本经典，讲清静无为、修身养性。</p><details><summary>道教简史</summary><dl><dt>先秦</dt><dd>老子作《道德经》五千言，庄子继之，是为道家。此时只有思想学派，还没有宗教组织；民间另有神仙方术与长生之说流传。</dd><dt>东汉</dt><dd>顺帝时张陵在蜀地创立五斗米道（后称天师道），奉老子为太上老君，以《道德经》教人；同时张角的太平道奉《太平经》。道教作为有组织的宗教由此开始。</dd><dt>魏晋南北朝</dt><dd>葛洪著《抱朴子》，总结炼养之说；上清、灵宝两系经典相继出现。北魏寇谦之、南朝陆修静整顿教规与斋仪，陶弘景居茅山传上清之学。</dd><dt>唐</dt><dd>李唐皇室认老子为先祖，道教极盛，科举一度设“道举”，以《道德经》等取士。《清静经》也在这一时期通行。</dd><dt>宋、金、元</dt><dd>宋真宗、徽宗崇道。金代王重阳在北方创立全真道，主张出家清修、三教合一；弟子丘处机西行见成吉思汗。南方以龙虎山张天师为首的各符箓派合为正一道。此后道教分全真、正一两大派。</dd><dt>明、清</dt><dd>明正统十年（1445）编成《正统道藏》，万历年间又有续藏，本站所收道经即出于此。清代以后官方扶持减少，道教更多融入民间信仰与日常习俗。</dd><dt>今日</dt><dd>全真、正一两派并存，宫观遍及华人社会。</dd></dl></details></section><section><h3>佛教</h3><p>佛教起于古印度，创始人释迦牟尼生活在约二千五百年前，教人认识苦的由来、以智慧与慈悲求解脱。两汉之际传入中国，经数百年译经与讲习，同儒、道相互影响，成为中国文化的一部分。</p><details><summary>佛教简史</summary><dl><dt>公元前六至五世纪</dt><dd>释迦牟尼生于蓝毗尼（今尼泊尔南部），出家修行，在菩提伽耶觉悟，于鹿野苑初次说法，此后在恒河流域传道四十余年。</dd><dt>佛灭度后</dt><dd>弟子多次集会，诵出并整理佛所说的教法与戒律。公元前三世纪阿育王护持佛教，派人向四方传布。约公元前后大乘佛教兴起，般若、法华、净土等经典陆续出现。</dd><dt>两汉之际</dt><dd>佛教经西域传入中国，传统说法是东汉明帝永平年间。东汉末安世高、支娄迦谶在洛阳译经。</dd><dt>魏晋南北朝</dt><dd>鸠摩罗什于公元 401 年到长安，译出《金刚经》《法华经》《阿弥陀经》等，文字流畅，通行至今。道安、慧远等人奠定了僧团制度与净土信仰；菩提达摩来华，后世尊为禅宗初祖。</dd><dt>隋、唐</dt><dd>中国佛教的高峰，天台、华严、法相、律、净土、禅、密等宗派先后成立。玄奘西行求法十七年，回国后译经一千三百余卷，《心经》《药师经》通行本即出其手；《地藏经》题为实叉难陀译。六祖惠能之后，禅宗大盛。</dd><dt>唐末至宋</dt><dd>唐武宗会昌年间（845）大规模毁佛，义理诸宗受创，禅宗与净土宗成为主流，此后逐渐禅净合流。北宋开宝年间开始雕印大藏经。</dd><dt>向外传播</dt><dd>汉传佛教传到朝鲜、日本、越南；南传佛教经斯里兰卡传入东南亚；七世纪起佛教传入西藏，形成藏传佛教。</dd><dt>明、清至今</dt><dd>明清多次官刻大藏经，清雍正、乾隆年间刻成《乾隆大藏经》（龙藏）。今天汉传、南传、藏传三系并存。</dd></dl></details></section><section><h3>儒家与四书五经</h3><p>儒家由孔子开创，讲仁义礼智、修身齐家治国，是学问与教化，不是宗教。五经是孔子用来教学的古代典籍，四书是南宋朱熹选定的四部入门书，两者合起来是古代读书人的基本功课。</p><details><summary>四书五经简史</summary><dl><dt>春秋</dt><dd>孔子（公元前 551—479）在鲁国讲学，整理《诗》《书》《礼》《易》《春秋》等古代典籍，用来教弟子。弟子与再传弟子把他的言行辑成《论语》。</dd><dt>战国</dt><dd>孟子、荀子发扬孔子之学；《孟子》七篇成书。相传《大学》出于曾子一系，《中庸》为孔子之孙子思所作，两篇后来都收在《礼记》里。</dd><dt>秦、汉</dt><dd>秦始皇焚书，典籍散失，汉初靠老儒口授与民间藏本重新写定。汉武帝建元五年（前 136）立五经博士，《诗》《书》《礼》《易》《春秋》成为官学。原有《乐经》，已失传，所以称五经而不称六经。</dd><dt>唐</dt><dd>孔颖达等奉诏撰《五经正义》，统一解释，作为科举标准。经书的范围此后逐步扩大，到宋代定为十三经。</dd><dt>南宋</dt><dd>朱熹把《大学》《中庸》从《礼记》中抽出，与《论语》《孟子》合为“四书”，作《四书章句集注》，主张先读四书、再读五经。</dd><dt>元、明、清</dt><dd>元仁宗延祐年间恢复科举，规定从四书出题、以朱熹注为准，明清沿用，直到 1905 年废除科举。六百年间，四书五经是读书人的必读书。</dd><dt>五经各是什么</dt><dd>《诗经》是三百零五篇诗歌；《尚书》是上古的政事文献；《礼记》讲礼制与修身；《周易》讲阴阳变化，原是占筮之书；《春秋》是鲁国的编年史，本站所收为附《左传》的本子。</dd></dl></details></section></div><p class="origins-note">以上是通行史述的简要整理，年代从常见说法；各家自身的传承记载或有不同。</p>
    ${GROUPS.map(([key,label])=>{const list=BOOKS.filter(b=>shelfOf(b)===key);return list.length?`<div class="shelf-title"><h2>${label}</h2><span>${key==='注'?'古人的注解，整部收录':list.length+' 部'}</span></div><div class="shelf">${list.map(b=>`<a class="book" href="${href(b,0)}"><div class="cover"><div class="slip ${b.name.length>4?'long':''}">${esc(b.name)}</div>${b.plain?'<span class="badge">白话</span>':''}</div><div class="book-meta"><b>${esc(b.full)}</b>${esc(b.by)}<br>${b.ch.length} 章 · ${b.chars.toLocaleString()} 字</div></a>`).join('')}</div>`:'';}).join('')}
    <footer>经文为公版古籍，各部所据版本写在阅读页右侧。白话由本站自译，仅供理解，繁体由程序自动转换（转换字表来自开源项目 OpenCC），个别字可能不准，不能代替原文与师承讲解。朗读使用设备自带的中文语音，是合成声音，不是法师或道长的唱诵。</footer></div>`;
}

function sentences(p){return p.match(/[^。！？；]+[。！？；”’）]*|[。！？；”’）]+/g)||[p];}
function para(p,ci,pi,kind){
  if(p.startsWith('## '))return `<h3>${esc(p.slice(3))}</h3>`;
  let n=0;return `<p>${sentences(p).map(s=>`<span class="s" data-k="${kind}" data-p="${pi}" data-n="${n++}">${esc(s).replace(/【(经|传)】/g,'<span class="tag">【$1】</span>')}</span>`).join('')}</p>`;
}
function body(c,ci){
  const has=!!c.v,mode=has?prefs.mode:'orig';
  if(mode==='both')return c.p.map((p,i)=>`<div class="pair"><div>${para(p,ci,i,'o')}</div><div class="plain">${para(c.v[i]||'',ci,i,'v')}</div></div>`).join('');
  if(mode==='plain')return `<div class="plain-only">${c.v.map((p,i)=>para(p,ci,i,'v')).join('')}</div>`;
  return c.p.map((p,i)=>para(p,ci,i,'o')).join('');
}
function chapterOptions(b,cur){
  let html='',group=null;
  b.ch.forEach((c,i)=>{if(c.g!==group){if(group!=null)html+='</optgroup>';group=c.g;if(group)html+=`<optgroup label="${esc(group)}">`;}html+=`<option value="${i}" ${i===cur?'selected':''}>${esc(c.t)}</option>`;});
  return html+(group?'</optgroup>':'');
}
function mediaList(b){return [...(MEDIA[b.id]||[]).map(m=>({...m,fixed:true})),...store.get('media-'+b.id,[])];}
function mediaPanel(b){
  const base=b.of?byId[b.of]:b,name=base.full,q=t=>encodeURIComponent(`${name} ${t}`);
  const list=mediaList(base);
  return `<section><h2>诵经影音</h2><p>在视频网站查找《${esc(base.name)}》的诵读与唱诵：</p>
    <div class="links">${[['国语','国语 诵读'],['粤语','粤语 诵读']].map(([lang,words])=>`<a href="https://www.youtube.com/results?search_query=${q(words)}" target="_blank" rel="noopener">YouTube ${lang}</a><a href="https://search.bilibili.com/all?keyword=${q(words)}" target="_blank" rel="noopener">哔哩哔哩 ${lang}</a>`).join('')}</div>
    ${list.length?`<ul>${list.map((m,i)=>`<li>〔${esc(m.lang)}〕${m.type==='audio'?`${esc(m.label)}<audio controls preload="none" src="${esc(m.url)}"></audio>`:`<a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.label)}</a>`}${m.fixed?'':`<button class="del" data-del="${i-(MEDIA[base.id]||[]).length}" aria-label="删除这条链接">删除</button>`}</li>`).join('')}</ul>`:'<p>还没有登记录音或视频。找到喜欢的版本后，可以把链接存在下面。</p>'}
    <form class="add" id="add-media"><input name="label" placeholder="名称，如：某某法师诵读" required maxlength="40"><input name="url" type="url" placeholder="https:// 视频或音频地址" required>
      <select name="lang" aria-label="语言"><option>国语</option><option>粤语</option></select><select name="type" aria-label="类型"><option value="video">视频链接</option><option value="audio">音频文件（mp3）</option></select><button>保存到本机</button></form>
    <p style="margin-top:8px">保存的链接只存在这台设备的浏览器里。</p></section>`;
}
function reader(b,ci){
  if(b.parts)return readerPart(b,ci);
  if(b.loaded){draw(b,ci);return;}
  state={book:null,ch:0};const wanted=location.hash;
  $('#app').innerHTML=`<p class="loading">正在打开《${esc(b.name)}》…</p>`;
  fetch(`./books/${b.id}.json`).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(rows=>{
    rows.forEach((row,i)=>{if(b.ch[i]){b.ch[i].p=row.p;if(row.v)b.ch[i].v=row.v;else delete b.ch[i].v;}});b.loaded=true;
    if(location.hash===wanted)draw(b,ci);
  }).catch(()=>{if(location.hash===wanted)$('#app').innerHTML=`<p class="loading">《${esc(b.name)}》没有载入成功。<a href="${href(b,ci)}" id="retry">再试一次</a>，或<a href="#">回到经藏</a>。</p>`;});
}
function readerPart(b,ci){
  let k=0;while(k+1<b.parts.length&&b.parts[k+1]<=ci)k++;
  b.got=b.got||{};if(b.got[k]){draw(b,ci);return;}
  state={book:null,ch:0};const wanted=location.hash;
  $('#app').innerHTML=`<p class="loading">正在打开《${esc(b.name)}》…</p>`;
  fetch(`./books/${b.id}/${k}.json`).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(rows=>{
    rows.forEach((row,i)=>{const c=b.ch[b.parts[k]+i];if(c)c.p=row.p;});b.got[k]=true;
    if(location.hash===wanted)draw(b,ci);
  }).catch(()=>{if(location.hash===wanted)$('#app').innerHTML=`<p class="loading">《${esc(b.name)}》没有载入成功。<a href="${href(b,ci)}" id="retry">再试一次</a>，或<a href="#">回到经藏</a>。</p>`;});
}
function draw(b,ci){
  stop();loadRecitation(b);
  state={book:b,ch:ci};store.set('last',{book:b.id,ch:ci});
  const c=b.ch[ci],notes=BOOKS.filter(x=>x.of===b.id),base=b.of&&byId[b.of];
  document.title=`${b.name} · ${c.t} · 经藏`;
  $('#app').innerHTML=`<div class="bar"><div class="wrap"><a class="home" href="${b.cat==='医'?'#yi':'#'}">← ${b.cat==='医'?'医书':'经藏'}</a>
      <select class="ctl" id="chapter" aria-label="选择章节">${chapterOptions(b,ci)}</select>
      <button class="ctl" id="prev" ${ci?'':'disabled'}>上一章</button><button class="ctl" id="next" ${ci<b.ch.length-1?'':'disabled'}>下一章</button><span class="grow"></span>
      ${c.v?`<span class="seg" role="group" aria-label="显示内容">${[['orig','原文'],['both','对照'],['plain','白话']].map(([k,l])=>`<button class="ctl" data-mode="${k}" aria-pressed="${prefs.mode===k}">${l}</button>`).join('')}</span>`:''}
      <span class="seg" role="group" aria-label="字号"><button class="ctl" data-size="-2" aria-label="缩小字号">小</button><button class="ctl" data-size="2" aria-label="放大字号">大</button></span>
      <button class="ctl" data-fan>${prefs.fan?'简体':'繁體'}</button>
      <button class="ctl" id="theme" aria-pressed="${prefs.theme==='dark'}">夜间</button></div></div>
    ${window.RecordedReading?.panel(b.id,c)||''}${window.RecordedReading?.has(b.id)?'<details class="wrap device-reader"><summary>设备朗读 · 国语 / 粤语合成声音</summary>':''}<div class="player"><div class="wrap"><button class="ctl play" id="play">▶ 朗读</button><button class="ctl" id="stop" disabled>停止</button>
      <label>语言<select class="ctl" id="lang"><option value="zh-CN">国语</option><option value="zh-HK">粤语</option></select></label>
      <label>声音<select class="ctl" id="voice" style="max-width:11em"></select></label>
      <label>语速<select class="ctl" id="rate">${[[0.6,'很慢'],[0.75,'慢'],[0.9,'稍慢'],[1,'正常'],[1.2,'快']].map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></label>
      ${recitation?'':'<label><input type="checkbox" id="chain"> 读完自动接下一章</label>'}<span id="voice-note" role="status"></span></div></div>${window.RecordedReading?.has(b.id)?'</details>':''}
    ${recitationPanel()}<div class="wrap layout"><article><h1>${esc(c.t)}</h1><p class="by">${esc(b.full)} · ${esc(b.by)}</p><div class="text${recitation?' chant-text':''}" id="text">${body(c,ci)}</div>
      ${c.v||recitation?'':`<p class="none">${b.cat==='注'?'这是古人的注解原文。':'这一章的白话还没有译出。'}${notes.length?`可以先参看古注：${notes.map(n=>`<a href="${href(n,0)}">${esc(n.name)}</a>`).join('、')}。`:''}</p>`}
      <div class="pager"><button class="ctl" id="prev2" ${ci?'':'disabled'}>← 上一章</button><button class="ctl" id="next2" ${ci<b.ch.length-1?'':'disabled'}>下一章 →</button></div></article>
    <aside><section><h2>关于这部经</h2><p>${esc(b.intro)}</p><p>版本：${esc(b.src)}</p>${b.sourceUrl?`<p><a href="${esc(b.sourceUrl)}" target="_blank" rel="noopener noreferrer">查看咒文来源</a></p>`:''}${b.plain?`<p>白话：本站自译，已完成 ${b.plain} / ${b.ch.length} 章。</p>`:''}
        ${notes.length?`<p>古注：${notes.map(n=>`<a href="${href(n,0)}" style="color:var(--azure)">${esc(n.name)}</a>（${esc(n.by)}）`).join('；')}</p>`:''}${base?`<p>所注经文：<a href="${href(base,0)}" style="color:var(--azure)">${esc(base.name)}</a></p>`:''}</section>
      <section><h2>在本书中查找</h2><input id="find" type="search" placeholder="输入字词，如：上善若水" aria-label="在本书中查找"><div id="hits"></div></section>${mediaPanel(b)}</aside></div>`;
  $('#lang').value=prefs.lang;$('#rate').value=String(prefs.rate);fillVoices();if($('#chain'))$('#chain').checked=prefs.chain;updateRecitation();
  if(!synth){$('#play').disabled=true;$('#voice-note').textContent='这个浏览器不支持语音朗读，可以改用 Chrome、Edge 或 Safari。';}else voiceNote();
}
const go=i=>{location.hash=href(state.book,i);};

/* ---- 朗读 ---- */
function voicesFor(lang){const all=synth?synth.getVoices():[];const want=lang==='zh-HK'?/^(zh[-_]HK|yue)/i:/^zh[-_](CN|TW|SG|Hans|Hant)|^zh$|^cmn/i;const rank=v=>/natural|neural|online|premium|enhanced/i.test(v.name)?0:/google|siri/i.test(v.name)?1:2;return all.filter(v=>want.test(v.lang)).sort((a,b)=>rank(a)-rank(b));}
function voiceFor(lang){const list=voicesFor(lang);const saved=(prefs.voice||{})[lang];return list.find(v=>v.name===saved)||list[0]||null;}
function fillVoices(){const sel=$('#voice');if(!sel)return;const list=voicesFor(prefs.lang);const cur=voiceFor(prefs.lang);sel.innerHTML=list.length?list.map(v=>`<option value="${esc(v.name)}"${cur&&v.name===cur.name?' selected':''}>${esc(v.name.replace(/Microsoft |Google | - Chinese.*$/g,''))}</option>`).join(''):'<option value="">无可用声音</option>';sel.disabled=list.length<2;}
if(synth)synth.addEventListener&&synth.addEventListener('voiceschanged',()=>{fillVoices();});
function voiceNote(){const note=$('#voice-note');if(!note||!synth)return;const any=synth.getVoices().length;
  note.textContent=!any?'语音尚未准备好，请稍后再按播放，或在设备设置中添加中文语音。':voiceFor(prefs.lang)?'':prefs.lang==='zh-HK'?'这台设备没有安装粤语语音，暂时无法用粤语朗读。可在系统设置的“语音／朗读”里添加粤语（香港）语音，或在右侧查找粤语诵读影音。':'这台设备没有安装国语语音，请在系统设置里添加中文（普通话）语音。';}
function build(){const kind=(state.book.ch[state.ch].v&&prefs.mode==='plain')?'v':'o';queue=[...document.querySelectorAll(`#text .s[data-k="${kind}"]`)];}
function speak(){
  if(!synth||!speaking||!queue.length){stop();return;}
  if(at>=queue.length){
    if(recitation){
      if(!recitation.fullRound){stop();return;}
      recitation.completed=Math.min(recitation.target,recitation.completed+1);
      recitation.saved=store.set('recitation-'+recitation.id,{version:1,completed:recitation.completed});
      if(recitation.completed===recitation.target){stop();return;}
      at=0;updateRecitation();
    }else{
    if(speaking&&prefs.chain&&state.ch<state.book.ch.length-1){const again=++token;go(state.ch+1);setTimeout(()=>{if(again===token)start(0);},350);return;}
    stop();return;}}
  const el=queue[at],my=token;document.querySelectorAll('.s.now').forEach(e=>e.classList.remove('now'));el.classList.add('now');el.scrollIntoView({block:'center',behavior:'smooth'});
  const u=new SpeechSynthesisUtterance(el.textContent.replace(/[【】□]/g,''));const v=voiceFor(prefs.lang);if(!v){stop();voiceNote();return;}u.voice=v;u.lang=v.lang;u.rate=prefs.rate;let ended=false;
  u.onend=()=>{if(!ended&&my===token&&speaking){ended=true;at++;speak();}};u.onerror=()=>{if(!ended&&my===token&&speaking){ended=true;pause();const note=$('#voice-note');if(note)note.textContent='本句朗读中断，未计入完成遍数。请检查声音和网络，再按继续。';}};
  synth.speak(u);
}
function start(from,continuing=false){
  if(!synth||!state.book||(recitation&&recitation.completed===recitation.target))return;
  window.RecordedReading?.stop();
  token++;speaking=false;synth.cancel();build();at=Number.isInteger(from)&&from>=0&&from<queue.length?from:0;
  if(recitation){recitation.recorded=false;recitation.program=1;if(!continuing)recitation.fullRound=at===0;}
  if(!voiceFor(prefs.lang)){if(recitation)recitation.status=continuing?'paused':'ready';const p=$('#play');if(p)p.textContent=continuing?'▶ 继续':'▶ 朗读';updateRecitation();voiceNote();return;}
  voiceNote();speaking=true;if(recitation){recitation.status='running';updateRecitation();}
  const p=$('#play'),s=$('#stop');if(p)p.textContent='❚❚ 暂停';if(s)s.disabled=false;speak();
}
function stop(){token++;speaking=false;if(synth)synth.cancel();at=0;if(recitation){recitation.fullRound=false;recitation.status='ready';}document.querySelectorAll('.s.now').forEach(e=>e.classList.remove('now'));const p=$('#play'),s=$('#stop');if(p)p.textContent='▶ 朗读';if(s)s.disabled=true;updateRecitation();}
function pause(){speaking=false;token++;synth.cancel();if(recitation)recitation.status='paused';const p=$('#play');if(p)p.textContent='▶ 继续';updateRecitation();}

function find(q){
  const box=$('#hits');q=q.trim();if(!q){box.innerHTML='';return;}
  const hits=[];
  for(let i=0;i<state.book.ch.length&&hits.length<40;i++)for(const p of state.book.ch[i].p||[]){const k=p.indexOf(q);if(k>=0){hits.push([i,p.slice(Math.max(0,k-12),k),q,p.slice(k+q.length,k+q.length+18)]);if(hits.length>=40)break;}}
  box.innerHTML=hits.length?hits.map(([i,a,m,z])=>`<button data-go="${i}"><small>${esc(state.book.ch[i].t)}</small>${esc(a)}<b>${esc(m)}</b>${esc(z)}</button>`).join('')+(hits.length>=40?'<p>只显示前 40 处。</p>':''):(state.book.parts?'<p>这部书篇幅很大，只在已打开过的各卷里查找，没有找到这个词。</p>':'<p>本书原文中没有找到这个词。</p>');
}

document.addEventListener('click',e=>{
  const t=e.target.closest('button,.s');if(!t||!state.book)return;
  if(t.classList.contains('s')){build();const i=queue.indexOf(t);if(i>=0)start(i);return;}
  if(t.id==='prev'||t.id==='prev2')go(state.ch-1);
  else if(t.id==='next'||t.id==='next2')go(state.ch+1);
  else if(t.id==='play'){if(speaking)pause();else{const continuing=at<queue.length&&$('#play').textContent.includes('继续');start(continuing?at:0,continuing);}}
  else if(t.id==='stop'){stop();at=0;}
  else if(t.id==='recitation-reset'&&recitation){window.RecordedReading?.stop();stop();recitation.completed=0;recitation.saved=store.set('recitation-'+recitation.id,{version:1,completed:0});updateRecitation();}
  else if(t.id==='theme'){prefs.theme=prefs.theme==='dark'?'':'dark';applyPrefs();t.setAttribute('aria-pressed',prefs.theme==='dark');}
  else if(t.dataset.size){prefs.size=Math.min(34,Math.max(15,prefs.size+Number(t.dataset.size)));applyPrefs();}
  else if(t.dataset.mode){stop();at=0;prefs.mode=t.dataset.mode;applyPrefs();document.querySelectorAll('[data-mode]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.mode===prefs.mode));$('#text').innerHTML=body(state.book.ch[state.ch],state.ch);}
  else if(t.dataset.go)go(Number(t.dataset.go));
  else if(t.dataset.del){const base=state.book.of?byId[state.book.of]:state.book,list=store.get('media-'+base.id,[]);list.splice(Number(t.dataset.del),1);store.set('media-'+base.id,list);reader(state.book,state.ch);}
});
document.addEventListener('change',e=>{
  if(e.target.id==='chapter')go(Number(e.target.value));
  else if(e.target.id==='lang'){prefs.lang=e.target.value;applyPrefs();fillVoices();voiceNote();if(speaking)start(at,true);}
  else if(e.target.id==='voice'){prefs.voice=Object.assign({},prefs.voice,{[prefs.lang]:e.target.value});applyPrefs();if(speaking)start(at,true);}
  else if(e.target.id==='rate'){prefs.rate=Number(e.target.value);applyPrefs();if(speaking)start(at,true);}
  else if(e.target.id==='chain'){prefs.chain=e.target.checked;applyPrefs();}
});
document.addEventListener('input',e=>{if(e.target.id==='find')find(e.target.value);});
document.addEventListener('submit',e=>{
  if(e.target.id!=='add-media')return;e.preventDefault();
  const f=new FormData(e.target),url=String(f.get('url'));if(!/^https?:\/\//i.test(url))return;
  const base=state.book.of?byId[state.book.of]:state.book,list=store.get('media-'+base.id,[]);
  list.push({label:String(f.get('label')).slice(0,40),url,lang:f.get('lang'),type:f.get('type')});store.set('media-'+base.id,list);reader(state.book,state.ch);
});
window.addEventListener('hashchange',route);
document.addEventListener('click',e=>{if(e.target.id==='retry'){e.preventDefault();route();}});
window.addEventListener('pagehide',stop);
window.addEventListener('jingzang:recorded-play',stop);
if(synth)synth.onvoiceschanged=voiceNote;

applyPrefs();
fetch('./index.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(data=>{BOOKS=data;BOOKS.forEach(b=>byId[b.id]=b);return fetch('./videos.json').then(r=>r.ok?r.json():{}).catch(()=>({})).then(extra=>{for(const k in extra)if(byId[k])MEDIA[k]=(MEDIA[k]||[]).concat(extra[k].filter(m=>/^https:\/\//.test(m.url||'')).map(m=>({type:'video',lang:m.lang||'评论',label:String(m.label||'视频').slice(0,60),url:m.url})));if(prefs.fan)loadFan(route);else route();});})
  .catch(()=>{$('#app').innerHTML='<p class="loading">经文资料没有载入成功。请重新整理页面；如果是自己架设，请确认 index.json 与 books 文件夹和本页放在同一个目录，并通过网站服务器打开。</p>';});
