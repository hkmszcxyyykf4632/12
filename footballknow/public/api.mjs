export async function api(path,{method='GET',body,signal,timeout=15000}={}) {
  const controller=new AbortController();
  const abort=()=>controller.abort();
  if(signal?.aborted)controller.abort();
  signal?.addEventListener('abort',abort,{once:true});
  const timer=setTimeout(abort,timeout);
  try {
    const response=await fetch(path,{method,credentials:'same-origin',cache:'no-store',signal:controller.signal,
      headers:{Accept:'application/json',...(body===undefined?{}:{'Content-Type':'application/json'})},
      ...(body===undefined?{}:{body:JSON.stringify(body)})});
    let value;
    try {value=await response.json();}catch {throw new Error('网站服务暂时无法响应，请稍后重试。');}
    if(!response.ok) {const error=new Error(typeof value.detail==='string'?value.detail:'操作未完成，请稍后重试。');error.status=response.status;throw error;}
    return value;
  } catch(error) {
    if(error.name==='AbortError'&&!signal?.aborted)throw new Error('等待响应超时，请稍后重试。');
    throw error;
  } finally {clearTimeout(timer);signal?.removeEventListener('abort',abort);}
}
