export const LEAGUES = Object.freeze({
  epl: {id:'epl',name:'英超',country:'英格兰',fullName:'超级联赛',lower:'英冠',folder:'',roster:'FPL',teamCount:20,countLabel:'二十',historyLabel:'联赛',historyFilter:'英超及英冠'},
  laliga: {id:'laliga',name:'西甲',country:'西班牙',fullName:'甲级联赛',lower:'西乙',folder:'laliga/',roster:'ESPN',teamCount:20,countLabel:'二十',historyLabel:'联赛',historyFilter:'西甲及西乙'},
  seriea: {id:'seriea',name:'意甲',country:'意大利',fullName:'甲级联赛',lower:'意乙',folder:'seriea/',roster:'ESPN',teamCount:20,countLabel:'二十',historyLabel:'联赛',historyFilter:'意甲及意乙'},
  bundesliga: {id:'bundesliga',name:'德甲',country:'德国',fullName:'甲级联赛',lower:'德乙',folder:'bundesliga/',roster:'ESPN',teamCount:18,countLabel:'十八',historyLabel:'联赛',historyFilter:'德甲及德乙'},
  ucl: {id:'ucl',name:'欧冠',country:'欧洲',fullName:'冠军联赛',lower:'其他正式赛事',folder:'ucl/',roster:'ESPN',teamCount:36,countLabel:'三十六',historyLabel:'正式比赛',historyFilter:'全部已收录正式赛事'}
});
export function leagueFromSearch(search='') {
  return LEAGUES[new URLSearchParams(search).get('league')] || LEAGUES.epl;
}
export const league=leagueFromSearch(globalThis.location?.search || '');
export const analysisPath=id=>`/api/analysis/${Number(id)}${league.id==='epl'?'':`?league=${league.id}`}`;
