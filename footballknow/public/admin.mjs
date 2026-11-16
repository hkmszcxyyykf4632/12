import {api} from './api.mjs';
import {main,esc,pageHeading,toast,timeText} from './ui.mjs';

const JOBS={live:'比赛与比分',catalogue:'球队与球员',history:'转会与领队',names:'中文姓名'};

export function renderAdmin() {
  const controller=new AbortController();
  const request=(path,options={})=>api(path,{...options,signal:controller.signal});
  main.innerHTML=`${pageHeading('管理后台','管理 AI 服务与分析规则，查看资料同步情况。')}<div class="loading">正在检查登录状态…</div>`;
  const fail=error=>{if(!controller.signal.aborted)main.innerHTML=`${pageHeading('管理后台','管理员服务暂时无法读取。')}<div class="error-box">${esc(error.message)}</div><a class="button secondary" href="#/">返回网站</a>`;};

  function login(message='') {
    if(controller.signal.aborted)return;
    main.innerHTML=`${pageHeading('管理员登录','使用你的独立管理员账号进入。')}<div class="admin-login-layout"><section class="panel login-panel"><h2>欢迎回来</h2><form id="login-form"><div class="field"><label for="admin-username">管理员账号</label><input id="admin-username" name="username" autocomplete="username" maxlength="30" required placeholder="admin01 / admin02"></div><div class="field"><label for="admin-password">密码</label><input id="admin-password" name="password" type="password" autocomplete="current-password" maxlength="256" required></div><p class="form-error" id="login-error" role="alert">${esc(message)}</p><button class="button" type="submit">登录管理后台</button></form></section><div class="login-note"><h2>把资料交给系统，<br>把判断留给自己。</h2><p>在这里连接 AI 服务、维护分析方法，以及查看每个资料来源的同步情况。</p><p class="note">当前提供两个管理员账号。账号密码由网站负责人单独保管。</p></div></div>`;
    main.querySelector('#login-form').addEventListener('submit',async event=>{
      event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;button.textContent='正在登录…';
      const password=main.querySelector('#admin-password');
      try {const session=await request('/api/auth/login',{method:'POST',body:{username:main.querySelector('#admin-username').value.trim(),password:password.value}});password.value='';if(!controller.signal.aborted)await dashboard(session);}
      catch(error) {password.value='';if(!controller.signal.aborted){main.querySelector('#login-error').textContent=error.message;button.disabled=false;button.textContent='登录管理后台';}}
    });
  }

  async function dashboard(session) {
    const [settings,rules]=await Promise.all([request('/api/ai/settings'),request('/api/analysis/rules')]);
    if(controller.signal.aborted)return;
    main.innerHTML=`${pageHeading('管理后台',`已登录：${esc(session.username)} · 管理员`, '<button class="button secondary" id="sign-out">退出登录</button>')}
      <nav class="section-nav" aria-label="后台内容"><a href="#ai-config">AI 接口</a><a href="#analysis-rules">分析方法</a><a href="#sync-panel">资料同步</a><a href="#password-panel">修改密码</a></nav>
      <div class="admin-grid"><section class="panel" id="ai-config"><h2>连接 DeepSeek</h2><p class="note" id="key-status">${settings.configured?'已保存密钥；留空即可继续使用。':'已预设 DeepSeek，只需粘贴 API 密钥即可生成分析。'}</p>
      <form id="ai-settings-form"><div class="field"><label for="ai-key">DeepSeek API 密钥</label><input id="ai-key" type="password" autocomplete="new-password" maxlength="4000" ${settings.configured?'':'required'} placeholder="${settings.configured?'已保存；不修改时留空':'粘贴你的 DeepSeek API 密钥'}"><small>填写 DeepSeek 开放平台的 API 密钥。保存后不会回显。<a href="https://platform.deepseek.com/" target="_blank" rel="noopener noreferrer">获取密钥</a></small></div><p class="form-error" role="alert"></p><button class="button" type="submit">保存 DeepSeek 密钥</button></form></section>
      <section class="panel" id="sync-panel"><h2>同步情况</h2><div id="sync-jobs">正在读取…</div><button class="button secondary compact" id="refresh-status">刷新同步状态</button><p class="note">比赛目标每 60 秒更新；球队、转会与领队每小时检查。来源不可用时保留最近成功资料。</p></section></div>
      <section class="panel spaced-panel" id="analysis-rules"><h2>本地分析规范</h2><p class="note">详细方法随每次请求交给 DeepSeek，前台呈现两三段结论，其余依据可展开查看。</p><form id="rules-form"><div class="field"><label for="rules-text">要求 AI 遵守的方法与输出规范</label><textarea id="rules-text" rows="16" minlength="80" maxlength="16000" required>${esc(rules.text)}</textarea></div><p class="form-error" role="alert"></p><button class="button" type="submit">保存分析规范</button></form></section>
      <section class="panel spaced-panel" id="password-panel"><h2>修改我的密码</h2><form id="password-form"><div class="field-row"><div class="field"><label for="current-password">当前密码</label><input id="current-password" type="password" autocomplete="current-password" required maxlength="256"></div><div class="field"><label for="new-password">新密码</label><input id="new-password" type="password" autocomplete="new-password" required minlength="12" maxlength="256"><small>至少 12 个字符。</small></div></div><div class="field"><label for="confirm-password">再次输入新密码</label><input id="confirm-password" type="password" autocomplete="new-password" required minlength="12" maxlength="256"></div><p class="form-error" role="alert"></p><button class="button secondary" type="submit">修改密码并重新登录</button></form></section>`;
    main.querySelectorAll('.section-nav a').forEach(link=>link.addEventListener('click',event=>{event.preventDefault();main.querySelector(link.getAttribute('href'))?.scrollIntoView({behavior:'smooth'});}));
    main.querySelector('#sign-out').addEventListener('click',async()=>{try{await request('/api/auth/logout',{method:'POST'});if(!controller.signal.aborted)login();}catch(error){toast(error.message);}});
    bind('#ai-settings-form',async()=>{
      const input=main.querySelector('#ai-key');
      try {await request('/api/ai/settings',{method:'PUT',body:{apiKey:input.value}});input.required=false;input.placeholder='已保存；不修改时留空';main.querySelector('#key-status').textContent='DeepSeek 密钥已保存，可以到下一场比赛页面生成分析。';}
      finally {input.value='';}
    },'DeepSeek 密钥已保存。');
    bind('#rules-form',()=>request('/api/analysis/rules',{method:'PUT',body:{text:main.querySelector('#rules-text').value}}),'分析规范已保存，下次生成时生效。');
    bind('#password-form',async()=>{
      const replacement=main.querySelector('#new-password').value;
      if(replacement!==main.querySelector('#confirm-password').value)throw new Error('两次输入的新密码不一致。');
      await request('/api/auth/password',{method:'POST',body:{current:main.querySelector('#current-password').value,replacement}});
      login('密码已修改，请使用新密码登录。');
    });
    main.querySelector('#refresh-status').addEventListener('click',refreshStatus);
    refreshStatus();
  }

  function bind(selector,action,message) {
    main.querySelector(selector).addEventListener('submit',async event=>{
      event.preventDefault();const form=event.target,button=form.querySelector('button');button.disabled=true;form.querySelector('.form-error').textContent='';
      try {await action();if(!controller.signal.aborted&&message)toast(message);}
      catch(error) {if(!controller.signal.aborted){if(error.status===401)login('登录已过期，请重新登录。');else form.querySelector('.form-error').textContent=error.message;}}
      finally {button.disabled=false;}
    });
  }

  async function refreshStatus() {
    try {
      const status=await request('/api/status');if(controller.signal.aborted)return;
      const area=main.querySelector('#sync-jobs');if(!area)return;
      const fresh=status.running&&Date.now()-Date.parse(status.heartbeat)<120000;
      area.innerHTML=`<p class="notice">${fresh?'后台同步任务运行中':'后台同步尚未运行，或心跳已超过两分钟。'}</p><dl class="sync-list">${Object.entries(JOBS).map(([key,label])=>{const job=status.jobs?.[key];return `<div><dt>${label}</dt><dd>${job?.running?'正在获取':job?.ok?'最近检查成功':job?.ok===false?'检查失败，稍后重试':'尚未完成'}<small>最近成功：${job?.lastSuccess?esc(timeText(job.lastSuccess)):'暂无'}</small></dd></div>`;}).join('')}</dl>`;
    } catch(error) {const area=main.querySelector('#sync-jobs');if(area&&!controller.signal.aborted)area.textContent=error.message;}
  }
  request('/api/auth/me').then(session=>session.authenticated?dashboard(session):login()).catch(error=>error.status===401?login():fail(error));
  return ()=>controller.abort();
}
