import {api} from './api.mjs';
const escape=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cache=new Map();
export async function loadBriefs(domain){
 const old=cache.get(domain);if(old&&Date.now()-old.at<60000)return old.promise;
 const promise=api('/api/review-briefs/'+domain,{timeout:30000}).then(x=>x.records);
 cache.set(domain,{at:Date.now(),promise});try{return await promise;}catch(e){cache.delete(domain);throw e;}
}
export function briefHtml(brief,url){
 if(!brief)return '<span class="note">尚无已完成复盘</span>';
 const text=brief.finding||brief.summary,short=text.length>115?text.slice(0,115)+'…':text;
 const kind=({method:'方法检查',unexpected:'赛中意外',unresolved:'原因待验证'})[brief.category]||'过程观察';
 const sources=(brief.sources||[]).filter(s=>/^https?:\/\//.test(s.url));
 return `<div class="review-brief"><span class="ps-tag">${kind}</span><p>${escape(short)}</p>${brief.nextCheck?`<small>下次检查：${escape(brief.nextCheck.length>70?brief.nextCheck.slice(0,70)+'…':brief.nextCheck)}</small>`:''}<details><summary>完整短评与依据</summary><p>${escape(brief.summary)}</p><p>${escape(brief.finding)}</p>${brief.nextCheck?`<p>下次检查：${escape(brief.nextCheck)}</p>`:''}<small>复盘 ${escape(new Date(brief.generatedAt).toLocaleString('zh-CN',{timeZone:'Asia/Hong_Kong'}))}</small>${sources.map(s=>`<a href="${escape(s.url)}" target="_blank" rel="noopener noreferrer">${escape(s.title||'依据')} ↗</a>`).join(' · ')}<p><a href="${escape(url)}">打开赛事详细复盘 →</a></p></details></div>`;
}
export async function hydrateBriefs(root,domain){
 const nodes=[...root.querySelectorAll('[data-review-identity]')].filter(n=>domain==='football'?n.dataset.reviewIdentity.includes(':'):!n.dataset.reviewIdentity.includes(':'));if(!nodes.length)return;
 try{const briefs=await loadBriefs(domain);for(const node of nodes){if(!node.isConnected)continue;const brief=briefs.find(b=>b.identity===node.dataset.reviewIdentity);node.innerHTML=briefHtml(brief,node.dataset.reviewUrl);}}
 catch{for(const node of nodes)if(node.isConnected)node.textContent='复盘读取暂未完成';}
}
