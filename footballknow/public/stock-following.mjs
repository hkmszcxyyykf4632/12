export const STOCK_FOLLOWING_KEY='footballknow.stock-following.v1';
const validCode=code=>typeof code==='string'&&/^\d{5,6}$/.test(code);

export function readStockFollowing(storage){
  try{
    const raw=(storage??globalThis.localStorage).getItem(STOCK_FOLLOWING_KEY);
    if(!raw)return {codes:[],problem:''};
    const value=JSON.parse(raw);
    if(value?.version!==1||!Array.isArray(value.codes)||value.codes.length>10000||!value.codes.every(validCode)||new Set(value.codes).size!==value.codes.length)throw new Error('Invalid saved list');
    return {codes:value.codes,problem:''};
  }catch{return {codes:[],problem:'暂时无法读取股票关注，请检查浏览器存储设置；原有关注记录仍保留。'};}
}

export function toggleStockFollowing(code,storage){
  if(!validCode(code))throw new Error('股票代码不正确。');
  const current=readStockFollowing(storage);
  if(current.problem)throw new Error(current.problem);
  const codes=new Set(current.codes),following=!codes.has(code);
  if(following)codes.add(code);else codes.delete(code);
  if(codes.size>10000)throw new Error('关注列表已满。');
  try{(storage??globalThis.localStorage).setItem(STOCK_FOLLOWING_KEY,JSON.stringify({version:1,codes:[...codes]}));}
  catch{throw new Error('关注未保存，请允许本网站使用浏览器存储后重试。');}
  return {codes:[...codes],following,problem:''};
}
