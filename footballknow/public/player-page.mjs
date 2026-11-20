import {data,history} from './repository.mjs';
import {playerResearch} from './player-research.mjs';
import {valuationHtml} from './player-values.mjs';
import {main,esc,dateText,monogram,sourceLink,cn} from './ui.mjs';
import {localized} from './football-components.mjs';
import {playerPortrait} from './portraits.mjs';
import {league} from './league.mjs';
import {radarPoints} from './insights.mjs';
import {playerStats,METRICS,POSITIONS,STATUS,clubOf,playerOriginal} from './player-stats.mjs';

const show=(value,digits=0)=>value==null?'—':digits?value.toFixed(digits):String(value);
const displayName=p=>localized(p)?.mandarin||p.web_name;
const RADAR=[['goals','进球'],['assists','助攻'],['expectedGoals','xG'],['expectedAssists','xA'],['minutes','分钟'],['starts','首发'],['goalsPer90','每90分钟进球']];

function radar(a,b) {
  const sa=playerStats(a),sb=playerStats(b);
  const axes=RADAR.filter(([key])=>sa[key]!=null&&sb[key]!=null&&(sa[key]>0||sb[key]>0));
  if(axes.length<3)return '<div class="empty">两名球员可比较的数据不足三项，同步更多比赛后会显示对比图。</div>';
  const size=130,center=160,share=(stats,key)=>stats[key]/Math.max(sa[key],sb[key]);
  const ring=scale=>radarPoints(axes.map(()=>scale),size,center,center);
  const labels=axes.map(([,label],index)=>{const angle=-Math.PI/2+index*2*Math.PI/axes.length;return `<text x="${(center+(size+20)*Math.cos(angle)).toFixed(1)}" y="${(center+(size+20)*Math.sin(angle)+4).toFixed(1)}" text-anchor="middle">${label}</text>`;}).join('');
  return `<div class="radar-wrap"><svg class="radar" viewBox="0 0 320 320" role="img" aria-label="${esc(displayName(a))} 与 ${esc(displayName(b))} 的数据对比图，各项以两人中的较高值为满格">
    ${[0.25,0.5,0.75,1].map(scale=>`<polygon class="radar-grid" points="${ring(scale)}"/>`).join('')}${labels}
    <polygon class="radar-a" points="${radarPoints(axes.map(([key])=>share(sa,key)),size,center,center)}"/><polygon class="radar-b" points="${radarPoints(axes.map(([key])=>share(sb,key)),size,center,center)}"/></svg>
    <div class="table-wrap"><table class="comparison-table"><thead><tr><th>指标</th><th><span class="swatch a"></span>${esc(displayName(a))}</th><th><span class="swatch b"></span>${esc(displayName(b))}</th></tr></thead><tbody>${METRICS.filter(([key])=>sa[key]!=null||sb[key]!=null).map(([key,label,digits])=>`<tr><th scope="row">${label}</th><td>${show(sa[key],digits)}</td><td>${show(sb[key],digits)}</td></tr>`).join('')}</tbody></table></div></div>
    <p class="note">图中每一项以两人中的较高值为满格，只表示两人之间的相对高低，不代表联赛排名。</p>`;
}

function transfers(p) {
  const keys=new Set([playerOriginal(p),p.web_name,[p.first_name,p.second_name].filter(Boolean).join(' ')].map(v=>String(v||'').toLowerCase()).filter(Boolean));
  const rows=(history?.transfers||[]).filter(t=>keys.has(String(t.player||'').toLowerCase()));
  return rows.length?`<div class="table-wrap"><table><thead><tr><th>日期</th><th>转出</th><th>转入</th><th>类型</th><th>费用</th><th>来源</th></tr></thead><tbody>${rows.map(t=>`<tr><td>${dateText(t.date)}${t.endDate?`<small>至 ${dateText(t.endDate)}</small>`:''}</td><td>${esc(cn(t.fromTeam)||'—')}</td><td>${esc(cn(t.toTeam)||'—')}</td><td>${esc(t.type||'—')}</td><td>${esc(t.fee||'未公布')}</td><td>${sourceLink(t.source,'公告或报道')}</td></tr>`).join('')}</tbody></table></div>`
    :`<div class="empty">本站收录的 ${esc(data.season)} 转会记录中没有这名球员。更早的转会尚未收录。</div>`;
}

export function renderPlayer(id,otherId) {
  const p=data.players.find(row=>String(row.id)===String(id));
  if(!p){main.innerHTML='<div class="empty">没有找到这名球员。<a href="#/rankings">返回数据榜单</a></div>';return ()=>{};}
  const club=clubOf(p),name=localized(p);
  let other=data.players.find(row=>String(row.id)===String(otherId)&&row.id!==p.id)||null;
  const label=row=>`${displayName(row)}（${clubOf(row)?.cn||''}）`;
  const candidates=data.players.filter(row=>row.id!==p.id).sort((a,b)=>(b.minutes||0)-(a.minutes||0));
  main.innerHTML=`<a class="back-link" href="${club?`#/team/${club.id}`:'#/teams'}">← ${club?esc(club.cn):'球队列表'}</a>
    <div class="page-heading"><div class="team-title">${playerPortrait(p,league.id,true)}<div><h1>${esc(name?.mandarin||p.web_name)}</h1><p class="lede">${name?.cantonese&&name.cantonese!==name.mandarin?`粤 ${esc(name.cantonese)} · `:''}${esc(playerOriginal(p))}${name?.status==='draft'?' · 中文为暂用音译':''}</p>${club?`<a href="#/team/${club.id}">${esc(club.cn)}</a>`:''}</div></div><button class="button secondary compact" type="button" data-share>分享链接</button></div>
    <dl class="team-summary" id="player-profile"></dl>
    <div class="section-head"><h2>${esc(data.season)} ${league.name}数据</h2></div><dl class="stat-grid" id="player-stats"></dl><p class="note" id="player-basis"></p>
    <div id="player-research">${playerResearch(p)}</div><div class="section-head"><h2>与另一名球员对比</h2></div>
    <div class="toolbar"><label class="search"><span class="sr-only">选择对比球员</span><input id="compare-player" type="search" list="compare-options" placeholder="输入球员名称后从列表选择" value="${other?esc(label(other)):''}"></label><datalist id="compare-options">${candidates.slice(0,900).map(row=>`<option value="${esc(label(row))}"></option>`).join('')}</datalist></div>
    <div id="player-compare"></div>
    <div class="section-head"><h2>转会记录</h2></div><div id="player-transfers"></div>`;
  const update=()=>{
    if(!main.querySelector('#player-stats'))return;
    const s=playerStats(p);
    main.querySelector('#player-profile').innerHTML=[['位置',POSITIONS[p.position]||'—'],['球衣号码',p.squad_number??'—'],['出生日期',`${dateText(p.birth_date)}${s.age!=null?`<small> ${s.age} 岁</small>`:''}`],['国籍',esc(p.country||'—')],
      ['估算身价',valuationHtml(p)],['加入球队',dateText(p.team_join_date)],['出场状态',`<span class="${p.status==='a'||p.status==='unreported'?'':'attention'}">${STATUS[p.status]||'未知'}</span>${p.chance_of_playing_next_round!=null&&p.status!=='a'?`<small> 下轮出场概率 ${p.chance_of_playing_next_round}%</small>`:''}`]]
      .map(([term,value])=>`<div><dt>${term}</dt><dd>${value}</dd></div>`).join('');
    main.querySelector('#player-stats').innerHTML=METRICS.map(([key,term,digits])=>`<div><dt>${term}</dt><dd>${show(s[key],digits)}</dd></div>`).join('');
    main.querySelector('#player-basis').innerHTML=`${p.news?`${esc(p.news)}。`:''}“—”表示来源没有提供这项数据，不等于 0。${league.id==='epl'?'分钟、进球、助攻、纪律与预期数据取自英超公开数据，出场次数与替补进球由比赛名单汇总。':'全部由已收录的比赛名单汇总，未收录的比赛不计入。'}身价为 FotMob 公开估值，币种为欧元，资料日期为采集时间；与实际转会成交价分开。`;
    main.querySelector('#player-compare').innerHTML=other?radar(p,other):'<div class="empty">选择一名球员，逐项比较本赛季数据。</div>';
    main.querySelector('#player-transfers').innerHTML=transfers(p);
    main.querySelector('#player-research').innerHTML=playerResearch(p);
  };
  const choosePlayer=event=>{
    const found=candidates.find(row=>label(row)===event.target.value);
    if(!found&&event.target.value)return;
    other=found||null;
    window.history.replaceState(null,'',`${location.pathname}${location.search}#/player/${p.id}${other?`/${other.id}`:''}`);update();
  };
  for(const event of ['input','change'])main.querySelector('#compare-player').addEventListener(event,choosePlayer);
  update();return update;
}
