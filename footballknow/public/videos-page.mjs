import {main,esc,pageHeading,sourceLink} from './ui.mjs';
import {api} from './api.mjs';

const categories={football:'足球分析',racing:'赛马分析',stocks:'股票分析',markets:'市场分析',other:'其他分析'};
const stamp=s=>s?new Date(s).toLocaleDateString('zh-CN'):'';
export function renderVideos(id=''){
  const controller=new AbortController();let rows=[],category='',query='';
  main.innerHTML=pageHeading('分析视频','足球、赛马与市场的研究和复盘。','<a class="button secondary" href="#/video-admin">管理视频</a>')+'<div id="video-content" class="loading">正在读取视频…</div>';
  function paint(){
    if(controller.signal.aborted)return;
    const target=main.querySelector('#video-content');target.className='';
    if(id){const v=rows.find(r=>r.id===id);if(!v){target.innerHTML='<div class="empty">视频尚未发布或已下架。<a href="#/videos">返回视频区</a></div>';return;}
      const p=v.playback||{kind:'link',url:v.url};
      target.innerHTML=`<a href="#/videos">← 全部分析视频</a><h2>${esc(v.title)}</h2><p class="note">${categories[v.category]} · ${stamp(v.publishedAt)}</p><div class="video-player">${p.kind==='file'?`<video controls playsinline preload="metadata" ${v.poster?`poster="${esc(v.poster)}"`:''} src="${esc(p.url)}" aria-label="${esc(v.title)}"></video>`:p.kind==='youtube'?`<iframe src="${esc(p.url)}" title="${esc(v.title)}" allow="fullscreen; picture-in-picture" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>`:`<div class="video-link-player"><h3>在视频平台观看</h3>${sourceLink(v.url,'打开视频 →')}</div>`}</div><p class="video-description">${esc(v.description)}</p><p>${sourceLink(v.url,'视频原始地址 ↗')}</p>`;return;
    }
    target.innerHTML=`<div class="toolbar"><label>视频分类<select id="video-category"><option value="">全部视频</option>${Object.entries(categories).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label class="search-field">搜索视频<input type="search" id="video-search" placeholder="标题或内容"></label></div><div id="video-grid" class="video-grid"></div>`;
    function filter(){const list=rows.filter(r=>(!category||r.category===category)&&(r.title+' '+r.description).toLowerCase().includes(query));target.querySelector('#video-grid').innerHTML=list.length?list.map(v=>`<a class="video-card" href="#/videos/${v.id}"><div class="video-cover">${v.poster?`<img src="${esc(v.poster)}" alt="" loading="lazy">`:'<span>分析视频</span>'}<span class="video-play" aria-hidden="true">▷</span></div><div><small>${categories[v.category]} · ${stamp(v.publishedAt)}</small><h3>${esc(v.title)}</h3><p>${esc(v.description.slice(0,100))}</p></div></a>`).join(''):'<div class="empty">'+(rows.length?'没有符合条件的视频。':'分析视频即将上线，发布后会出现在这里。')+'</div>';}
    target.querySelector('#video-category').onchange=e=>{category=e.target.value;filter();};target.querySelector('#video-search').oninput=e=>{query=e.target.value.trim().toLowerCase();filter();};filter();
  }
  api('/api/videos',{signal:controller.signal}).then(v=>{rows=v.videos||[];paint();}).catch(e=>{if(!controller.signal.aborted)main.querySelector('#video-content').textContent=e.message;});return()=>controller.abort();
}

export function renderVideoAdmin(){
  const controller=new AbortController();let rows=[],editing='',busy=false;
  main.innerHTML=pageHeading('视频管理','填写视频地址，预览后发布到分析视频区。','<a class="button secondary" href="#/videos">视频区</a>')+'<div id="video-admin-content" class="loading">正在检查管理员登录…</div>';
  function paint(){
    const target=main.querySelector('#video-admin-content');if(!target||controller.signal.aborted)return;target.className='';
    const row=rows.find(r=>r.id===editing)||{};
    target.innerHTML=`<form id="video-form" class="video-edit panel"><h2>${editing?'编辑视频':'添加视频'}</h2><label>标题<input name="title" required maxlength="120" value="${esc(row.title||'')}"></label><label>分类<select name="category">${Object.entries(categories).map(([k,v])=>`<option value="${k}" ${row.category===k?'selected':''}>${v}</option>`).join('')}</select></label><label>视频地址<input name="url" type="url" required placeholder="https://…/video.mp4 或视频平台链接" value="${esc(row.url||'')}"></label><p class="note">支持 MP4、WebM 文件地址和 YouTube 链接在站内播放；其他平台保留观看入口。</p><label>封面地址（可选）<input name="poster" type="url" value="${esc(row.poster||'')}"></label><label>简介<textarea name="description" rows="5" maxlength="3000">${esc(row.description||'')}</textarea></label><label><input name="published" type="checkbox" ${row.published?'checked':''}> 发布，所有访客可见</label><div class="toolbar"><button class="button" type="submit">保存视频</button><button type="button" class="button secondary" id="video-new">新建</button></div><p id="video-save-status" role="status"></p></form><section><h2>已有视频（${rows.length}）</h2>${rows.length?rows.map(r=>`<div class="section-head"><div><strong>${esc(r.title)}</strong><small>${categories[r.category]} · ${r.published?'已发布':'草稿 / 已下架'}</small></div><button class="button secondary" data-edit-video="${r.id}">编辑</button></div>`).join(''):'<div class="empty">尚未添加视频。</div>'}</section>`;
    target.querySelector('#video-new').onclick=()=>{editing='';paint();};target.querySelectorAll('[data-edit-video]').forEach(b=>b.onclick=()=>{editing=b.dataset.editVideo;paint();});
    target.querySelector('#video-form').onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;const form=e.currentTarget,values=new FormData(form),status=target.querySelector('#video-save-status');form.querySelector('[type=submit]').disabled=true;
      try{const body=Object.fromEntries(['title','description','category','url','poster'].map(k=>[k,values.get(k)||'']));body.published=values.get('published')==='on';await api('/api/admin/videos'+(editing?'/'+editing:''),{method:editing?'PUT':'POST',body,signal:controller.signal});if(controller.signal.aborted)return;await load();main.querySelector('#video-save-status').textContent=body.published?'视频已发布。':'草稿已保存，访客不可见。';}
      catch(error){if(!controller.signal.aborted)status.textContent=error.message;}finally{busy=false;if(form.isConnected)form.querySelector('[type=submit]').disabled=false;}};
  }
  async function load(){try{const data=await api('/api/admin/videos',{signal:controller.signal});rows=data.videos||[];paint();}catch(e){if(!controller.signal.aborted)main.querySelector('#video-admin-content').innerHTML=`<div class="empty">${esc(e.message)} <a href="#/admin">登录管理后台</a></div>`;}}
  load();return()=>controller.abort();
}
