export async function mountVisitCounter(target){
  if(!target)return;
  target.innerHTML='<span>访问次数</span> <strong>—</strong>';
  const event=crypto.randomUUID();
  try{
    const response=await fetch('/api/visits',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event}),keepalive:true});
    const data=await response.json();
    if(!response.ok||!Number.isSafeInteger(data.total)||data.total<0)throw Error('Counter unavailable');
    if(target.isConnected)target.querySelector('strong').textContent=data.total.toLocaleString('zh-CN');
  }catch{if(target.isConnected)target.querySelector('strong').textContent='暂未更新';}
}
