import html
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
film = ROOT / 'film'
data = json.loads((ROOT / 'timing.json').read_text(encoding='utf-8'))
duration = data['duration']
segments = data['segments']
boards = {
    'question': ('預測贏球<br>結果打和', '一句「爆冷」就算復盤？', 'question'),
    'evidence': ('場上究竟<br>發生咗咩事？', '先找證據，再講原因', 'evidence'),
    'before': ('賽前<br>睇漏咗啲乜？', '正選 · 傷停 · 盤口變化', 'before'),
    'match': ('場面點樣<br>被改變？', '入球 · 紅牌 · 換人 · 陣式', 'match'),
    'odds': ('賠率變動<br><em>係線索</em>', '唔等於賽果嘅原因', 'odds'),
    'method': ('偶發事件<br><em>定方法漏洞？</em>', '唔好全部歸咎運氣', 'method'),
    'next': ('證據夠<br><em>先下結論</em>', '記低下次賽前要加查啲乜', 'next'),
    'ending': ('預測可以錯<br><em>復盤要有用</em>', '峰弈科技 · 一起問清楚', 'ending')
}
beat_order = list(boards)
starts = {key: next(row['start'] for row in segments if row['beat']==key) for key in boards}
starts['question'] = 0
board_html = []
for index,key in enumerate(beat_order):
    start=starts[key]
    end=starts[beat_order[index+1]] if index+1<len(beat_order) else duration
    title,subtitle,_=boards[key]
    board_html.append(f'<section id="beat-{key}" class="clip board-clip" data-start="{start}" data-duration="{end-start:.3f}" data-track-index="2" data-beat="{key}"><div class="board-copy"><div class="board-kicker">{ "大首領提問" if key=="question" else "大天使解答" if key!="ending" else "峰弈 · AI 問答" }</div><h2>{title}</h2><div class="rule"></div><p>{subtitle}</p></div></section>')
caption_html=[]
audio_html=[]
for i,row in enumerate(segments):
    name='大首領' if row['speaker']=='chief' else '大天使'
    caption_html.append(f'<div id="caption-{i}" class="clip subtitle" data-start="{row["start"]}" data-duration="{row["duration"]+0.12:.3f}" data-track-index="3" data-track-kind="captions"><div class="subtitle-inner"><span class="speaker {row["speaker"]}">{name}</span><span class="caption-text">{html.escape(row["caption"]).replace(chr(10),"<br>")}</span></div></div>')
    audio_html.append(f'<audio id="voice-{i}" class="clip" src="{row["src"]}" data-start="{row["start"]}" data-duration="{row["duration"]}" data-track-index="4" data-volume="1"></audio>')
timeline=json.dumps(data,ensure_ascii=False,separators=(',',':'))
template='''<!doctype html>
<html lang="zh-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>峰弈 AI 問答 · 粵語動態樣板</title>
<script src="assets/gsap.min.js"></script>
<style>
@font-face{font-family:Chinese;src:url('assets/fonts/chinese.ttc')}*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#e7eee6;font-family:Chinese,sans-serif;color:#173e35}
#root{position:relative;width:1920px;height:1080px;overflow:hidden}.stage{position:absolute;inset:0}.back-wall{position:absolute;inset:0;background:#e7eee6}.panel-left,.panel-right{position:absolute;top:0;bottom:180px;width:190px;background:#c7d7cb;border-right:18px solid #fff8e9}.panel-left{left:0}.panel-right{right:0;border-left:18px solid #fff8e9;border-right:0}.wood-floor{position:absolute;top:844px;bottom:0;width:100%;background:#cfb18e;border-top:10px solid #b98d62}.floor-line{position:absolute;left:0;top:884px;height:4px;width:1920px;background:#ba9870}
header{position:absolute;top:52px;left:230px;width:1460px;text-align:center;z-index:2}header p{margin:0 0 12px;font-size:36px;letter-spacing:5px;font-weight:700;color:#4b685c}h1{margin:0;font-size:74px;line-height:1.3;letter-spacing:1px;font-weight:900}
.board{position:absolute;left:649px;top:260px;width:622px;height:490px;background:#fff8e9;border:7px solid #36594c;border-radius:28px;box-shadow:0 16px 0 #b4c7b8}.board:before,.board:after{content:"";position:absolute;top:490px;height:100px;width:22px;background:#36594c}.board:before{left:65px}.board:after{right:65px}
.board-clip{position:absolute;inset:0;pointer-events:none}.board-copy{position:absolute;left:674px;top:290px;width:572px;height:420px;text-align:center}.board-kicker{font-size:30px;color:#6f6a54;margin-bottom:20px}h2{font-size:64px;line-height:1.32;font-weight:900;letter-spacing:0;margin:0}em{font-style:normal;color:#b44726}.rule{height:6px;width:78px;background:#c35e36;margin:24px auto}.board-copy p{font-size:32px;line-height:1.5;margin:0;color:#4d6358}.name{position:absolute;top:854px;font-size:38px;letter-spacing:6px;font-weight:700;width:500px;text-align:center}.chief-name{left:105px}.angel-name{right:105px}
#actors{position:absolute;inset:0;width:1920px;height:1080px;z-index:3}.subtitle{position:absolute;inset:0;z-index:5;pointer-events:none}.subtitle-inner{position:absolute;left:192px;top:915px;width:1536px;min-height:124px;background:#173e35;border-radius:20px;display:flex;align-items:center;justify-content:center;gap:28px;padding:12px 32px;box-shadow:0 8px 0 #ac8b66}.caption-text{font-size:55px;line-height:1.32;color:#fffdf4;font-weight:700;text-align:center;white-space:nowrap}.speaker{font-size:30px;line-height:1.2;min-width:106px;padding-right:25px;border-right:2px solid #92ad9b;color:#ffd79d}.speaker.angel{color:#c9e7ef}.intro-label{position:absolute;right:220px;top:815px;font-size:26px;color:#5c6b5c}
</style></head><body><main id="root" data-composition-id="main" data-width="1920" data-height="1080" data-start="0" data-duration="__DURATION__">
<div id="studio" class="clip stage" data-start="0" data-duration="__DURATION__" data-track-index="0" data-track-kind="graphics">
<div class="back-wall"></div><div class="panel-left"></div><div class="panel-right"></div><div class="wood-floor"></div><div class="floor-line"></div>
<header><p>峰弈科技 · AI 問答</p><h1>預測錯了，復盤看甚麼？</h1></header><div class="board"></div><div class="name chief-name">大首領</div><div class="name angel-name">大天使</div></div>
<canvas id="actors" width="1920" height="1080" aria-label="大首領與大天使的動態對話"></canvas>
__BOARDS__
__CAPTIONS__
__AUDIO__
</main><script>
const timing=__TIMING__;
const canvas=document.getElementById('actors'),ctx=canvas.getContext('2d');
const atlas=new Image();atlas.src='assets/expressions.png';
const calm=new Image();calm.src='assets/characters.png';
const clock={t:0};
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const activeAt=t=>timing.segments.find(s=>t>=s.start&&t<s.start+s.duration);
function speech(row,t){if(!row)return 0;return row.envelope[Math.floor((t-row.start)*30)]||0;}
function poseImage(img,cols,row,col,x,y,w,h,headAngle,bodyScale){
  const sw=img.width/cols,sh=img.height/2,split=.61,neck=h*split;
  ctx.save();ctx.translate(x+w/2,y+h);ctx.scale(1,bodyScale);ctx.translate(-w/2,-h);
  ctx.drawImage(img,col*sw,row*sh+sh*split,sw,sh*(1-split),0,neck,w,h-neck);
  ctx.save();ctx.translate(w/2,neck);ctx.rotate(headAngle);ctx.translate(-w/2,-neck);
  ctx.drawImage(img,col*sw,row*sh,sw,sh*(split+.014),0,0,w,neck+h*.014);
  ctx.restore();ctx.restore();
}
function actor(which,t,row){
  const isChief=which==='chief',talk=row&&row.speaker===which,energy=talk?speech(row,t):0;
  const origin=isChief?10:1205,phase=isChief?0:1.7,baseY=200,w=700,h=650;
  const q=t<7.8&&isChief, ending=t>54.9;
  const breath=Math.sin(t*2.4+phase)*.008;
  let jump=0,lean=0,angle=Math.sin(t*1.8+phase)*.017,scaleY=1+breath;
  if(q){const local=t-1.1;jump=local>0&&local<.75?-28*Math.sin(local/.75*Math.PI):0;lean=Math.sin(t*4.8)*5;angle=-.085+Math.sin(t*3.1)*.05;}
  if(talk){lean+=(isChief?1:-1)*(7+Math.sin(t*3.4)*4);angle+=Math.sin(t*5.3+phase)*.025;scaleY+=clamp(energy*1.7,0,.025);}
  else {const nod=Math.sin(t*2.1+phase);angle+=nod*.025;if((t+phase)%8<1.4)jump=-Math.max(0,Math.sin(((t+phase)%8)/1.4*Math.PI))*5;}
  if(ending){angle=Math.sin(t*5.5+phase)*.035;scaleY+=Math.sin(t*5.5)*.012;}
  ctx.save();ctx.fillStyle='rgba(55,63,45,.18)';ctx.beginPath();ctx.ellipse(origin+w/2,846,153*(1+jump/200),18,0,0,Math.PI*2);ctx.fill();ctx.restore();
  const blink=((t+phase)%4.7)<.17;
  let col=0, img=atlas,cols=4;
  if(blink){col=2;img=calm;cols=3;}
  else if(q && (t<3.4||energy>.032))col=2;
  else if(ending&&!talk)col=3;
  else if(talk&&energy>.016&&Math.sin(t*37)>-.45)col=1;
  if(t>7.9&&t<8.5&&isChief)col=2;
  if(t>34.0&&t<35.0&&isChief)col=2;
  if(t>48.7&&t<49.4&&isChief)col=3;
  // Keep the calm sheet only for a brief blink; its drawing is registered to the same cell box.
  poseImage(img,cols,isChief?0:1,col,origin+lean,baseY+jump,w,h,angle,scaleY);
  // A short attention burst belongs to the surprised reaction, never to generic decoration.
  if(q&&t>1.2&&t<2.3){ctx.save();ctx.strokeStyle='#c85b31';ctx.lineWidth=9;ctx.lineCap='round';for(let j=0;j<3;j++){ctx.beginPath();ctx.moveTo(615+j*21,356-j*34);ctx.lineTo(640+j*30,344-j*43);ctx.stroke();}ctx.restore();}
}
function draw(t=clock.t){canvas.dataset.renderTime=t.toFixed(3);ctx.clearRect(0,0,1920,1080);const row=activeAt(t);canvas.dataset.speaker=row?.speaker||'';canvas.dataset.energy=speech(row,t).toFixed(4);actor('chief',t,row);actor('angel',t,row);}
const assetsReady=Promise.all([atlas.decode(),calm.decode()]);
window.addEventListener('hf-seek',e=>{const pending=assetsReady.then(()=>draw(e.detail.time));e.detail.waitUntil?.(pending);});
assetsReady.then(()=>{
const tl=gsap.timeline({paused:true,onUpdate:()=>draw(clock.t)});
tl.to(clock,{t:timing.duration,duration:timing.duration,ease:'none'},0);
__BOARD_TWEENS__
window.__timelines=window.__timelines||{};window.__timelines.main=tl;draw();
});
</script></body></html>'''
tweens='\n'.join(f"tl.fromTo('#beat-{key} .board-copy',{{opacity:0,scale:.96}},{{opacity:1,scale:1,duration:.28,ease:'power3.out'}},{starts[key]});" for key in beat_order if key!='question')
out=template.replace('__DURATION__',str(duration)).replace('__BOARDS__','\n'.join(board_html)).replace('__CAPTIONS__','\n'.join(caption_html)).replace('__AUDIO__','\n'.join(audio_html)).replace('__TIMING__',timeline).replace('__BOARD_TWEENS__',tweens)
(film/'index.html').write_text(out,encoding='utf-8')
(film/'STORYBOARD.md').write_text('\n'.join(f'## Frame {i+1}\nstatus: implemented\nsrc: index.html\nbeat: {key}\nstart: {starts[key]}\nvisual: {boards[key][0]}\nmotion: references/types/character.md acting; references/motion.md board arrival\n' for i,key in enumerate(beat_order)),encoding='utf-8')
print(f'Wrote {duration}s animation, {len(segments)} speech clips')
