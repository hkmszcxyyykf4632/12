import {api} from './api.mjs';
import {readFollowingRecord,saveFollowingRecord,receiveFollowing,STOCK_FOLLOWING_KEY} from './stock-following.mjs';
export function createFollowingSync({storage,request=api,changed=()=>{},uuid=()=>crypto.randomUUID()}={}){
 let running=null,status={state:'idle',message:'正在连接关注同步…',devices:1};
 const notify=(state,message,extra={})=>{status={...status,state,message,...extra};changed(status);};
 function sync(){
  if(running)return running;
  running=(async()=>{
   notify('syncing','正在同步关注…');
   try{
    let remote=await request('/api/stocks/following'),record=readFollowingRecord(storage);
    if(record.cloud.device!==remote.device){
     const additions=record.codes.map(code=>({id:uuid(),code,following:true}));
     record={...record,cloud:{...record.cloud,device:remote.device,pending:[...additions,...record.cloud.pending]}};
     saveFollowingRecord(record,storage);
    }
    record=receiveFollowing(remote,[],storage);
    while(record.cloud.pending.length){
     const batch=record.cloud.pending.slice(0,200);
     remote=await request('/api/stocks/following',{method:'POST',body:{changes:batch}});
     record=receiveFollowing(remote,batch.map(c=>c.id),storage);
    }
    notify('ready',remote.devices>1?`已连接 ${remote.devices} 台设备 · 关注自动同步`:'关注已保存 · 连接手机或电脑后自动同步',{devices:remote.devices});
    return remote;
   }catch(error){notify('error','同步暂未完成，已保留本机关注；连接恢复后重试。');throw error;}
  })().finally(()=>{running=null;});return running;
 }
 return {sync,getStatus:()=>status,async pair(){await sync();return request('/api/stocks/following/pair',{method:'POST'});},async join(code){
   await sync();const remote=await request('/api/stocks/following/join',{method:'POST',body:{code}});
   receiveFollowing(remote,[],storage);notify('ready',`已合并两端关注 · 已连接 ${remote.devices} 台设备`,{devices:remote.devices});return remote;
 }};
}
let shared;
const listeners=new Set();
function client(){return shared??=createFollowingSync({changed:status=>{
 if(typeof window!=='undefined'&&status.state==='ready')window.dispatchEvent(new Event('stock-following-changed'));
 for(const listener of listeners)listener(status);
}});}
export const syncFollowing=()=>client().sync();
export function bindFollowingSync(target){
 const show=status=>{const node=target?.querySelector('[data-sync-state]');if(node)node.textContent=status.message;};
 if(target){
  target.innerHTML='<section class="stock-device-sync"><div class="section-head"><h2>手机与电脑同步</h2><button class="button secondary compact" data-sync-refresh>立即同步</button></div><p class="note" data-sync-state role="status"></p><details><summary>连接另一台设备</summary><p>在一台设备生成同步码，在另一台设备输入。首次连接会合并两边的关注，以后增删自动同步。</p><button class="button secondary" data-sync-create>生成同步码</button><p data-sync-code role="status"></p><form data-sync-join><label>另一台设备的同步码<input name="code" autocomplete="off" autocapitalize="characters" placeholder="XXXX-XXXX-XXXX" minlength="12" maxlength="30" required></label><button class="button" type="submit">连接并合并关注</button></form><p class="note">同步码10分钟内有效，只使用一次。请只在自己的设备输入；清除网站数据后需要重新连接。</p><p class="note" data-sync-error role="alert"></p></details></section>';
  const error=target.querySelector('[data-sync-error]');
  target.querySelector('[data-sync-refresh]').onclick=()=>client().sync().catch(e=>{error.textContent=e.message;});
  target.querySelector('[data-sync-create]').onclick=async e=>{e.target.disabled=true;error.textContent='';try{const p=await client().pair();if(target.isConnected)target.querySelector('[data-sync-code]').textContent=p.code+' · 10分钟内有效';}catch(err){error.textContent=err.message;}finally{e.target.disabled=false;}};
  target.querySelector('[data-sync-join]').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;error.textContent='';try{await client().join(new FormData(e.target).get('code'));e.target.reset();target.querySelector('[data-sync-code]').textContent='连接成功，两端关注已合并。';}catch(err){error.textContent=err.message;}finally{button.disabled=false;}};
 }
 listeners.add(show);show(client().getStatus());
 const refresh=()=>{if(!document.hidden)client().sync().catch(()=>{});};
 const storage=e=>{if(e.key===STOCK_FOLLOWING_KEY)refresh();};
 const timer=setInterval(refresh,15000);
 window.addEventListener('focus',refresh);window.addEventListener('online',refresh);window.addEventListener('storage',storage);document.addEventListener('visibilitychange',refresh);refresh();
 return()=>{listeners.delete(show);clearInterval(timer);window.removeEventListener('focus',refresh);window.removeEventListener('online',refresh);window.removeEventListener('storage',storage);document.removeEventListener('visibilitychange',refresh);};
}
