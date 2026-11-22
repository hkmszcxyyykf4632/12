import {api} from './api.mjs';
import {main,esc,pageHeading} from './ui.mjs';
const key='fengyi.qa.v1';
const examples=['让半球和让一球，分析时应该怎样区别？','怎样判断一匹马适合快步速还是慢步速？','实际利率和黄金价格有什么关系？'];
export function renderInteractiveQA(){
 const controller=new AbortController();let messages=[],busy=false;
 try{const saved=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(saved))messages=saved.filter(x=>['user','assistant'].includes(x.role)&&typeof x.content==='string').slice(-30);}catch{}
 main.innerHTML=`<section class="qa-page">${pageHeading('峰弈 · AI互动','一起提问、追问，找出判断背后的理由。')}<div class="qa-intro"><span class="qa-trial">试用</span><p>足球、赛马、金融都可以聊。解释原理、比较看法，也欢迎直接指出回答里的问题。</p><p class="note">由网站配置的独立AI服务回答；一般知识可直接讨论，最新事实需核实。这里的对话与ChatGPT中的聊天相互独立。</p></div><div class="qa-examples" aria-label="试试这些问题">${examples.map((s,i)=>`<button type="button" data-example="${i}">${esc(s)} ↗</button>`).join('')}</div><div class="qa-toolbar"><span>当前对话保存在本浏览器</span><button class="button quiet compact" id="qa-clear" type="button">清空对话</button></div><div id="qa-messages" class="qa-messages" aria-label="对话记录"></div><form class="qa-form" id="qa-form"><label for="qa-question">你想讨论什么？</label><textarea id="qa-question" maxlength="1500" rows="3" placeholder="输入你的问题，也可以继续追问上一条回答…" required></textarea><div><span class="note">Ctrl + Enter 发送 · 不要输入账户密码</span><button class="button" id="qa-send" type="submit">发送问题 ↗</button></div><p id="qa-status" class="note" role="status" aria-live="polite"></p></form></section>`;
 const box=main.querySelector('#qa-messages'),form=main.querySelector('#qa-form'),input=main.querySelector('#qa-question'),send=main.querySelector('#qa-send'),status=main.querySelector('#qa-status');
 function save(){try{localStorage.setItem(key,JSON.stringify(messages.slice(-30)));}catch{status.textContent='浏览器未允许保存记录；本次对话仍可继续。';}}
 function draw(){
  box.innerHTML=messages.length?messages.map((m,i)=>`<article class="qa-message qa-${m.role}"><header>${m.role==='user'?'你':'峰弈 AI'}${m.at?`<time>${new Date(m.at).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})}</time>`:''}</header><div>${m.content.split('\n\n').map(p=>`<p>${esc(p)}</p>`).join('')}</div>${m.sources?.length?`<details><summary>本次使用的资料</summary><ul>${m.sources.filter(s=>/^https:\/\//.test(s.url||'')).map(s=>`<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a><small>资料时间 ${esc(s.updatedAt||'未标注')}</small></li>`).join('')}</ul></details>`:''}${m.followups?.length?`<div class="qa-followups">${m.followups.map((q,j)=>`<button type="button" data-followup="${i}:${j}">${esc(q)}</button>`).join('')}</div>`:''}</article>`).join(''):'<div class="qa-welcome"><strong>从一个好问题开始。</strong><p>可以先说你的看法，我会解释依据，也会讨论哪些证据可能推翻它。</p></div>';
  box.querySelectorAll('[data-followup]').forEach(button=>button.onclick=()=>{const [i,j]=button.dataset.followup.split(':').map(Number);input.value=messages[i].followups[j];input.focus();});
 }
 form.onsubmit=async e=>{
  e.preventDefault();const question=input.value.trim();if(!question||busy)return;
  const history=messages.filter(m=>!m.error).slice(-6).map(({role,content})=>({role,content:content.slice(0,2500)}));
  messages.push({role:'user',content:question,at:new Date().toISOString()});draw();save();busy=true;send.disabled=true;input.disabled=true;main.querySelector('#qa-clear').disabled=true;status.textContent='正在整理回答，请稍候…';
  try{const answer=await api('/api/ask',{method:'POST',body:{question,history},signal:controller.signal,timeout:90000});if(controller.signal.aborted)return;messages.push({role:'assistant',content:answer.answer.join('\n\n'),at:answer.answeredAt,sources:answer.sources,followups:answer.followups});input.value='';status.textContent='回答已完成，可以继续追问。';draw();save();}
  catch(error){if(!controller.signal.aborted){messages.pop();status.textContent=error.message+' 你的问题仍保留在输入框中。';draw();save();}}
  finally{busy=false;if(!controller.signal.aborted){send.disabled=false;input.disabled=false;main.querySelector('#qa-clear').disabled=false;input.focus();}}
 };
 input.onkeydown=e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();form.requestSubmit();}};
 main.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>{input.value=examples[Number(b.dataset.example)];input.focus();});
 main.querySelector('#qa-clear').onclick=()=>{if(!busy){messages=[];save();draw();status.textContent='已开始新的对话。';}};
 draw();return()=>controller.abort();
}
