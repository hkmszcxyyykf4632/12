export const STOCK_FOLLOWING_KEY='footballknow.stock-following.v1';
const validCode=code=>typeof code==='string'&&/^\d{5,6}$/.test(code);
const problem='暂时无法读取股票关注，请检查浏览器存储设置；原有关注记录仍保留。';
export function readFollowingRecord(storage=globalThis.localStorage){
  const raw=storage.getItem(STOCK_FOLLOWING_KEY);
  if(!raw)return {version:1,codes:[],cloud:{pending:[]}};
  const value=JSON.parse(raw);
  if(value?.version!==1||!Array.isArray(value.codes)||value.codes.length>10000||!value.codes.every(validCode)||new Set(value.codes).size!==value.codes.length)throw Error(problem);
  if(value.cloud&&(!Array.isArray(value.cloud.pending)||!value.cloud.pending.every(c=>validCode(c.code)&&typeof c.following==='boolean'&&typeof c.id==='string')))throw Error(problem);
  return {...value,cloud:value.cloud||{pending:[]}};
}
export function saveFollowingRecord(value,storage=globalThis.localStorage){
  try{const raw=JSON.stringify(value);if(storage.getItem(STOCK_FOLLOWING_KEY)!==raw)storage.setItem(STOCK_FOLLOWING_KEY,raw);}
  catch{throw Error('关注未保存，请允许本网站使用浏览器存储后重试。');}
}
export function readStockFollowing(storage){
  try{return {codes:readFollowingRecord(storage).codes,problem:''};}
  catch{return {codes:[],problem};}
}
export function toggleStockFollowing(code,storage){
  if(!validCode(code))throw new Error('股票代码不正确。');
  const current=readFollowingRecord(storage),codes=new Set(current.codes),following=!codes.has(code);
  if(following)codes.add(code);else codes.delete(code);
  if(codes.size>10000)throw new Error('关注列表已满。');
  const change={id:globalThis.crypto.randomUUID(),code,following};
  saveFollowingRecord({...current,codes:[...codes],cloud:{...current.cloud,pending:[...current.cloud.pending,change]}},storage);
  return {codes:[...codes],following,problem:''};
}
export function receiveFollowing(remote,acknowledged=[],storage){
  if(!remote?.id||!remote.device||!Array.isArray(remote.codes)||!remote.codes.every(validCode)||remote.codes.length>10000)throw Error('服务器关注资料格式不正确，保留本机记录。');
  const current=readFollowingRecord(storage),acked=new Set(acknowledged),pending=current.cloud.pending.filter(c=>!acked.has(c.id)),codes=new Set(remote.codes);
  for(const c of pending){if(c.following)codes.add(c.code);else codes.delete(c.code);}
  const next={...current,codes:[...codes],cloud:{...current.cloud,id:remote.id,device:remote.device,devices:remote.devices,revision:remote.revision,pending}};
  saveFollowingRecord(next,storage);return next;
}
