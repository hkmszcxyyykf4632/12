const labels={team:'球队',horse:'马匹',owner:'马主',trainer:'练马师',jockey:'骑师'};
const escapeRE=s=>[...s].map(c=>'.*+?^${}()|[]'.includes(c)||c.charCodeAt(0)===92?String.fromCharCode(92)+c:c).join('');
// Only spelling variants are folded; ambiguous aliases remain unlinked.
const traditional='馬龍騰飛寶運勝樂華國萬東風雲將軍輝陽勁駿歡樂財葉鄧頓張黃陳羅蘇賢偉鄭鵬鍾賀馮紹許劉盧韋爾強麗榮進達銀團體學關義興銘';
const simplified='马龙腾飞宝运胜乐华国万东风云将军辉阳劲骏欢乐财叶邓顿张黄陈罗苏贤伟郑鹏钟贺冯绍许刘卢韦尔强丽荣进达银团体学关义兴铭';
const chars=new Map([...traditional].map((c,i)=>[c,[...simplified][i]]));
export const normalizeEntityName=s=>String(s||'').normalize('NFKC').replace(/./gu,c=>chars.get(c)||c).toLocaleLowerCase().trim();
export function personHref(kind,p){
 if(!labels[kind]||!p)return '';
 let id=kind==='owner'?(typeof p==='string'?p:p.name):p.id;
 if(!id&&p.source){try{id=new URL(p.source).searchParams.get(kind+'id');}catch{}}
 if(!id||kind!=='owner'&&!/^[a-z0-9_-]{1,32}$/i.test(id))return '';
 return '#/racing-person/'+kind+'/'+encodeURIComponent(id);
}
export function createEntityIndex(rows=[]){
 const aliases=new Map();
 for(const entity of rows){if(!labels[entity.kind]||!entity.href||!entity.name)continue;
  for(const raw of new Set([entity.name,...(entity.aliases||[])])){
   const key=normalizeEntityName(raw);if(key.length<2)continue;
   if(!aliases.has(key))aliases.set(key,[]);
   if(!aliases.get(key).some(e=>e.kind===entity.kind&&e.id===entity.id))aliases.get(key).push(entity);
  }
 }
 const words=[...aliases.keys()].sort((a,b)=>b.length-a.length);
 return {aliases,pattern:words.length?new RegExp(words.map(escapeRE).join('|'),'gu'):null};
}
export function resolveEntity(index,name,kind){
 const rows=(index.aliases.get(normalizeEntityName(name))||[]).filter(e=>!kind||e.kind===kind);
 return rows.length===1?rows[0]:null;
}
export function entityHref(entity,search=globalThis.location?.search||''){
 if(entity.kind!=='team')return entity.href;
 const league=new URLSearchParams(search).get('league')||'epl';
 const local=entity.targets?.find(t=>t.league===league);
 return local?'#/team/'+local.id:entity.href;
}
const excluded='a,button,input,select,textarea,script,style,code,pre,svg,h1,[contenteditable],summary,[data-no-entities]';
export function enhanceEntityLinks(root,index){
 if(!root||!index.pattern)return 0;
 const doc=root.ownerDocument,walker=doc.createTreeWalker(root,4),nodes=[];let node,count=0;
 while((node=walker.nextNode()))if(node.parentElement&&!node.parentElement.closest(excluded)&&node.textContent.trim())nodes.push(node);
 for(const text of nodes){
  const raw=text.textContent;
  // Trimming or compatibility folds can change offsets; preserve the original text exactly.
  const comparable=String(raw).replace(/./gu,c=>chars.get(c)||c).toLocaleLowerCase();
  if(comparable.length!==raw.length)continue;
  index.pattern.lastIndex=0;const matches=[...comparable.matchAll(index.pattern)];if(!matches.length)continue;
  const fragment=doc.createDocumentFragment();let cursor=0;
  for(const match of matches){const start=match.index,end=start+match[0].length;
   if(/[a-z0-9]/i.test(match[0][0])&&/[a-z0-9]/i.test(comparable[start-1]||''))continue;
   if(/[a-z0-9]/i.test(match[0].at(-1))&&/[a-z0-9]/i.test(comparable[end]||''))continue;
   const entity=resolveEntity(index,match[0],text.parentElement.closest('[data-entity-kind]')?.dataset.entityKind);
   if(!entity)continue;
   fragment.append(doc.createTextNode(raw.slice(cursor,start)));const link=doc.createElement('a');
   link.href=entityHref(entity);link.className='entity-link';link.dataset.entityKind=entity.kind;
   link.title='查看'+labels[entity.kind]+'资料：'+entity.name;link.textContent=raw.slice(start,end);fragment.append(link);cursor=end;count++;
  }
  if(cursor){fragment.append(doc.createTextNode(raw.slice(cursor)));text.replaceWith(fragment);}
 }
 return count;
}
export function bindEntityLinks(root){
 let disposed=false,index=null,queued=0,controller=new AbortController();
 const Observer=root.ownerDocument.defaultView.MutationObserver;
 const observer=new Observer(schedule);
 function run(){queued=0;if(disposed||!index)return;observer.disconnect();enhanceEntityLinks(root,index);observer.observe(root,{subtree:true,childList:true});}
 function schedule(){if(!queued&&index&&!disposed)queued=setTimeout(run,100);}
 observer.observe(root,{subtree:true,childList:true});
 fetch('/api/entities',{signal:controller.signal,cache:'no-cache'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(disposed)return;index=createEntityIndex(d.entities);schedule();}).catch(()=>{});
 return()=>{disposed=true;controller.abort();observer.disconnect();clearTimeout(queued);};
}
