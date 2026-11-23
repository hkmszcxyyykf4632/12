import {racingPersonLink} from './racing-person.mjs';
import {main,esc,pageHeading} from './ui.mjs';
import {portrait} from './portraits.mjs';
import {table,val,stamp,racingNav,racingJson} from './racing-ui.mjs';

export function renderRacingRankings(initial='jockeys'){
  const controller=new AbortController();let kind=initial==='trainers'?'trainers':'jockeys',data={};
  main.innerHTML=pageHeading('骑师与练马师榜','香港本地赛季成绩，按头马及马会同分次序排列。')+racingNav('racing-rankings')+'<div id="racing-rankings" class="loading">正在读取排行榜…</div>';
  function paint(){const target=main.querySelector('#racing-rankings');if(!target)return;target.className='';
    const all=data[kind]||[],rows=all.filter(p=>p.section==='current'),others=all.filter(p=>p.section==='other');
    const row=p=>[p.rank??'—',`<div class="person-identity">${portrait(p.photo,p.name)}<span>${racingPersonLink(p,kind==='trainers'?'trainer':'jockey')}<small>${esc(p.nameEn)}</small></span></div>`,`<strong class="ranking-wins">${p.numFirst}</strong>`,p.numSecond,p.numThird,p.numFourth,p.numFifth,p.numStarts,p.numStarts?(100*p.numFirst/p.numStarts).toFixed(1)+'%':'—',p.prize==null?'—':'$'+Number(p.prize).toLocaleString('zh-HK')];
    const headers=['排名',kind==='trainers'?'练马师':'骑师','头马','第二','第三','第四','第五','出赛','胜出率','奖金（港元）'];
    target.innerHTML=`<div class="tabs"><button data-kind="jockeys" class="${kind==='jockeys'?'active':''}">骑师榜</button><button data-kind="trainers" class="${kind==='trainers'?'active':''}">练马师榜</button></div><div class="section-head"><h2>${esc(data.season)} 马季</h2><span class="note">截至 ${esc(data.asOf||'来源未标注赛期')} · 更新 ${stamp(data.updatedAt)}</span></div><div class="ranking-podium">${rows.slice(0,3).map(p=>`<div><span class="podium-rank">${p.rank}</span>${portrait(p.photo,p.name,'person',true)}<strong>${racingPersonLink(p,kind==='trainers'?'trainer':'jockey')}</strong><b>${p.numFirst}<small> 场头马</small></b><span>${p.numStarts} 次出赛 · ${p.numStarts?(100*p.numFirst/p.numStarts).toFixed(1):0}% 胜出</span></div>`).join('')}</div>${table(headers,rows.map(row))}${others.length?`<details><summary>其他及客串${kind==='trainers'?'练马师':'骑师'}（${others.length}）</summary>${table(headers,others.map(row))}</details>`:''}<p class="note">来源：香港赛马会骑练榜，不包括海外成绩及奖金。排名采用头马、平头头马及后续名次的官方排序；胜出率＝头马次数 ÷ 出赛次数。</p>`;
    target.querySelectorAll('[data-kind]').forEach(b=>b.onclick=()=>{kind=b.dataset.kind;paint();});
  }
  racingJson('people.json',controller.signal).then(value=>{if(!controller.signal.aborted){data=value;paint();}}).catch(e=>{if(!controller.signal.aborted)main.querySelector('#racing-rankings').innerHTML=`<div class="empty">${esc(e.message)}</div>`;});
  return()=>controller.abort();
}
