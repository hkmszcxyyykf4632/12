// One merged view of a player's season: the league's own feed where it has the figure, match summaries otherwise.
import {data,facts} from './repository.mjs';
import {league} from './league.mjs';
import {ageOn} from './insights.mjs';

export const POSITIONS={1:'门将',2:'后卫',3:'中场',4:'前锋'};
export const STATUS={unreported:'未标注伤停',a:'可出场',d:'出场待定',i:'伤缺',s:'停赛',u:'暂不可用',n:'暂不可用'};
const num=value=>{const n=Number(value);return value==null||value===''||!Number.isFinite(n)?null:n;};

let indexed=new Map(),indexedFor=null;
function factIndex() {
  if(indexedFor!==facts){indexedFor=facts;indexed=new Map();for(const row of facts?.players||[]){if(row.playerCode!=null)indexed.set(`c${row.playerCode}`,row);indexed.set(`e${row.espnId}`,row);}}
  return indexed;
}
export const factRow=p=>factIndex().get(`c${p.code}`)||factIndex().get(`e${p.id}`)||null;

export function playerStats(p) {
  const f=factRow(p),own=league.id==='epl';
  // Outside the Premier League the roster feed reports zeros for unplayed and unknown alike, so match summaries lead.
  const pick=(feed,derived)=>own?num(feed)??num(derived):num(derived)??num(feed);
  const minutes=pick(p.minutes,f?.minutes),goals=pick(p.goals_scored,f?.goals);
  return {appearances:num(f?.appearances),starts:pick(p.starts,f?.starts),minutes,goals,assists:pick(p.assists,f?.assists),
    yellowCards:pick(p.yellow_cards,f?.yellowCards),redCards:pick(p.red_cards,f?.redCards),substituteGoals:num(f?.substituteGoals),
    expectedGoals:num(p.expected_goals),expectedAssists:num(p.expected_assists),saves:num(p.saves),cleanSheets:num(p.clean_sheets),
    goalsPer90:minutes>=300&&goals!=null?goals/minutes*90:null,age:ageOn(p.birth_date)};
}

export const METRICS=[['goals','进球',0],['assists','助攻',0],['expectedGoals','预期进球 xG',2],['expectedAssists','预期助攻 xA',2],['goalsPer90','每 90 分钟进球',2],
  ['minutes','出场分钟',0],['appearances','出场次数',0],['starts','首发次数',0],['substituteGoals','替补进球',0],['yellowCards','黄牌',0],['redCards','红牌',0],['saves','扑救',0],['cleanSheets','零封',0]];

export function playerOriginal(p) {return p.known_name||[p.first_name,p.second_name].filter(Boolean).join(' ')||p.web_name;}
export const clubOf=p=>data.teams.find(t=>t.id===p.team);
