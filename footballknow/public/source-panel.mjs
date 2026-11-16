import {odds,standings,rankings} from './repository.mjs';
import {main,esc,sourceLink} from './ui.mjs';
import {timestamp} from './football-components.mjs';

export function addedSourceSections(){
 return `<h2>积分、球员与球队榜</h2><p>积分榜每 60 秒检查，并保留 ESPN 提供的名次；主客场与近五场榜由完整核对后的本赛季赛果计算。射手、助攻和纪律统计本站每 60 秒检查，来源自身注明夜间更新；球员榜收录前50名。欧冠积分榜只统计联赛阶段，其他赛事不混入积分。</p><p>积分最近检查：${timestamp(standings?.updatedAt)} · 球员榜：${timestamp(rankings?.updatedAt)}。${sourceLink(standings?.officialUrl,'联赛官网')} · ${sourceLink(standings?.source,'积分数据')} · ${sourceLink(rankings?.sources?.[0],'球员数据')}</p>
 <h2>赛后出场名单与比赛中心</h2><p>每场比赛详情提供来源已公布的首发、替补、阵型、换人、红黄牌、关键事件和技术统计。后台分批补齐本赛季完赛及各队最近20场，打开较早比赛时按需取得。名单尚未提供时直接标注，历史首发不会当作下一场确认首发。分钟数缺失时，依据已公布换人/红牌时间估算并标“约”，不计补时。</p><p>阵型图按来源位置分组示意；下一场分析会读取实际覆盖的历史名单、首发频次、阵型、轮换重合度和已知分钟负荷。我的关注保存在本浏览器，三个赛事分别记录。</p>
 <h2>赔率来源核查</h2><p>目前这项赛事收录的报价包括：${esc(odds?.providers?.join('、')||'正在同步')}。历史赔率通过 Football-Data 收录，赛前报价通过 ESPN 收录，页面保留公司、三项十进制赔率、原始来源与采集时间。市场平均与同一公司的赛前/收盘数据不算多家独立来源。交易所报价未扣佣金。</p><p>赛前快照与官网连接每 60 秒检查，覆盖随来源开放市场而变化。连接成功仅表示网页可读；以下各站没有被标为已接入的直接报价接口。最近报价检查：${timestamp(odds?.updatedAt)}。</p><div id="official-source-checks" class="note">正在载入官网检查记录…</div>`;
}
export async function loadOfficialChecks(){
 const target=main.querySelector('#official-source-checks');
 if(!target)return;
 try{const response=await fetch('./odds-sources.json',{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error();const result=await response.json();if(!target.isConnected)return;
 target.innerHTML=`<div class="table-wrap"><table><thead><tr><th>官方网站</th><th>直接读取状态</th><th>历史报价途径</th><th>检查时间</th></tr></thead><tbody>${result.sources.map(s=>`<tr><td>${sourceLink(s.url,s.name)}</td><td class="source-status-cell">${esc(s.message)}</td><td>${esc(s.historicalVia)}</td><td>${timestamp(s.checkedAt)}</td></tr>`).join('')}</tbody></table></div>`;
 }catch{if(target.isConnected)target.textContent='官网检查记录暂时无法读取。已有报价仍可在各场比赛中查看来源。';}
}
