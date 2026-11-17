import {data,facts} from './repository.mjs';
import {esc,monogram} from './ui.mjs';
import {localized,timestamp} from './football-components.mjs';
import {league} from './league.mjs';
import {boardRows} from './insights.mjs';
import {playerStats,METRICS,POSITIONS,clubOf,playerOriginal} from './player-stats.mjs';

export const advancedState={metric:'goals',position:'',age:'',search:''};

const table=()=>data.players.map(p=>({p,stats:playerStats(p)}));
const available=rows=>METRICS.filter(([key])=>rows.some(row=>row.stats[key]>0));

export function advancedControls() {
  const options=available(table());
  if(!options.some(([key])=>key===advancedState.metric))advancedState.metric=options[0]?.[0]||'goals';
  return `<label>指标 <select id="adv-metric">${options.map(([key,label])=>`<option value="${key}" ${key===advancedState.metric?'selected':''}>${label}</option>`).join('')}</select></label>
    <label>位置 <select id="adv-position"><option value="">全部位置</option>${Object.entries(POSITIONS).map(([key,label])=>`<option value="${key}" ${key===advancedState.position?'selected':''}>${label}</option>`).join('')}</select></label>
    <label>年龄 <select id="adv-age">${[['','全部年龄'],['21','21 岁及以下'],['23','23 岁及以下']].map(([value,label])=>`<option value="${value}" ${value===advancedState.age?'selected':''}>${label}</option>`).join('')}</select></label>
    <label class="rank-search">搜索球员 / 球队 <input type="search" id="adv-search" value="${esc(advancedState.search)}" placeholder="中文、粤语或原名"></label>`;
}

export function bindAdvanced(root,update) {
  for(const [id,key,event] of [['adv-metric','metric','change'],['adv-position','position','change'],['adv-age','age','change'],['adv-search','search','input']])
    root.querySelector('#'+id)?.addEventListener(event,e=>{advancedState[key]=e.target.value;update();});
}

export function advancedStatus() {
  return facts?`由比赛名单汇总 ${facts.coveredMatches} / ${facts.targetMatches} 场，最近生成 ${timestamp(facts.updatedAt)}。${league.id==='epl'?'英超的分钟、进球、助攻、纪律与预期数据取自联赛公开数据。':''}`
    :`比赛名单汇总尚未生成${league.id==='epl'?'，目前显示联赛公开数据已有的指标':''}。`;
}

export function advancedHtml() {
  const {metric,position,age,search}=advancedState;
  const [,label,digits]=METRICS.find(([key])=>key===metric)||METRICS[0];
  const query=search.trim().toLowerCase();
  const rows=boardRows(table().filter(({p,stats})=>(!position||String(p.position)===position)&&(!age||stats.age!=null&&stats.age<=Number(age))),row=>row.stats[metric],{limit:400})
    .map(item=>({...item,name:localized(item.row.p),club:clubOf(item.row.p)}))
    .filter(({row,name,club})=>!query||[name?.mandarin,name?.cantonese,playerOriginal(row.p),row.p.web_name,club?.cn,club?.name].join(' ').toLowerCase().includes(query)).slice(0,50);
  if(!rows.length)return `<div class="empty">${query||position||age?'没有符合筛选条件的球员。':'这项统计还没有可用数据，同步完成后会显示。'}</div>`;
  return `<div class="table-wrap"><table><thead><tr><th>排名</th><th>球员</th><th>球队</th><th>位置</th><th>年龄</th><th>分钟</th><th>${label}</th></tr></thead><tbody>${rows.map(({row,rank,value,name,club})=>`<tr><td>${rank}</td><td><a class="player-name" href="#/player/${row.p.id}">${esc(name?.mandarin||row.p.web_name)}<small>${esc(playerOriginal(row.p))}</small></a></td><td>${club?`<a class="club-inline" href="#/team/${club.id}">${monogram(club,'tiny')}<span>${esc(club.cn)}</span></a>`:'—'}</td><td>${POSITIONS[row.p.position]||'—'}</td><td>${row.stats.age??'—'}</td><td>${row.stats.minutes??'—'}</td><td class="points-cell">${digits?value.toFixed(digits):value}</td></tr>`).join('')}</tbody></table></div>
    <p class="note">显示前 50 名，数值相同并列。每 90 分钟进球只统计出场满 300 分钟的球员。年龄按今天计算。未收录到本站球员名单的球员不在此榜。</p>`;
}

const RULES={
  epl:'20 队主客场双循环共 38 轮。积分相同时依次比较净胜球、进球数。最后三名降入英冠。前四名获得下赛季欧冠联赛阶段资格，第五名通常进入欧联；欧战名额会因杯赛冠军归属和欧足联系数排名增减，以英超与欧足联公告为准。',
  laliga:'20 队主客场双循环共 38 轮。积分相同时先比较相互交锋成绩，再比较净胜球。最后三名降入西乙。前四名获得下赛季欧冠联赛阶段资格，其后名次对应欧联与欧协联；名额会因国王杯冠军归属和欧足联系数排名增减，以西甲与欧足联公告为准。',
  seriea:'20 队主客场双循环，共 38 轮、380 场。总榜保留官方来源的排序，同分裁定和欧战、升降级名额以赛事当季公告为准。',
  bundesliga:'18 队主客场双循环，共 34 轮、306 场。总榜保留官方来源的排序，同分裁定和欧战、升降级名额以赛事当季公告为准。',
  ucl:'36 队组成一张联赛阶段积分榜，每队对阵 8 个不同对手，主客场各 4 场。前 8 名直接进入十六强，第 9 至 24 名进行两回合附加赛，第 25 名及以后被淘汰，不再转入欧联。淘汰赛阶段除决赛外均为两回合。',
};
export const leagueRules=()=>`<details class="rules"><summary>${league.name}赛制与名次规则</summary><p>${RULES[league.id]||''}</p></details>`;
