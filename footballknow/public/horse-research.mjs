import {esc,sourceLink} from './ui.mjs';
import {table,val,stamp,horseLink} from './racing-ui.mjs';

const known=v=>typeof v==='string'&&v.trim()&&!/^(?:-|—|未知|unknown|n\/a)$/i.test(v.trim());
const normal=v=>String(v||'').trim().replace(/\s+/g,' ').toLowerCase();
export function sireFamily(h,directory){
  if(!known(h.pedigree?.sire))return [];
  const seen=new Set([h.id]);
  return (directory.horses||[]).filter(x=>{if(seen.has(x.id)||normal(x.pedigree?.sire)!==normal(h.pedigree.sire))return false;seen.add(x.id);return true;}).sort((a,b)=>(b.rating??-1)-(a.rating??-1));
}
export function pedigreeIntro(h,directory){
  const b=h.pedigree||{},family=sireFamily(h,directory);
  return `<div class="research-summary"><p>${esc(h.name)}的父系为 ${val(b.sire)}，母系为 ${val(b.dam)}，外祖父为 ${val(b.damsire)}。父系连接同父马匹，外祖父说明母系一侧的血缘背景；相同父系不代表相同途程或场地表现。</p><p>本站已收录 ${family.length} 匹同父系香港马匹，按现时评分排列。点击马名可比较各自的场地、途程与历次往绩。</p></div>${family.length?table(['同父系马匹','评分','练马师','母系','最近名次'],family.map(x=>[horseLink(x,true),val(x.rating),esc(x.trainer?.name||'—'),val(x.pedigree?.dam),esc((x.recent||[]).join(' · ')||'—')])):'<p class="note">目前目录没有可确认的其他同父系马匹。</p>'}`;
}
export function runningPositions(record){
  const value=String(record.running||'').trim();
  return /^\d+(?:\s+\d+)+$/.test(value)?value.split(/\s+/).map(Number).filter(n=>n>0):[];
}
export function hotWinner(record){
  return !record.withdrawn&&record.place===1&&Number.isFinite(record.winOdds)&&record.winOdds>0&&record.winOdds<=2;
}
export function reviewRecord(r){
  if(r.withdrawn)return '退出赛事，不计出赛或胜负。';
  const points=runningPositions(r),parts=[];
  if(Number.isInteger(r.place)&&r.place>0)parts.push(`以第 ${r.place} 名完成`);
  else return '来源未提供可核对的完成名次，暂不评价表现。';
  if(points.length>1&&points.at(-1)===r.place){
    parts.push(`首个记录点居第 ${points[0]} 位`);
    const from=points.at(-2),gain=from-r.place;
    parts.push(gain>0?`最后一个记录段追前 ${gain} 位`:gain<0?`最后一个记录段后退 ${-gain} 位`:'最后一个记录段守住原位');
  }
  if(r.place!==1&&known(r.margin))parts.push(`距头马 ${r.margin} 马位`);
  return parts.join('，')+'。';
}
export function paceSummary(records){
  const sample=[...records].filter(r=>!r.withdrawn).sort((a,b)=>b.date.localeCompare(a.date)).slice(0,10).map(r=>({r,p:runningPositions(r)})).filter(x=>x.p.length>1);
  const counts={'前领':0,'跟前':0,'居中':0,'留后':0};
  for(const {p} of sample)counts[p[0]===1?'前领':p[0]<=4?'跟前':p[0]<=8?'居中':'留后']++;
  const ranked=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  const label=!sample.length?'走位资料不足':ranked[0][1]===ranked[1][1]?'跑法多变':ranked[0][0]+'较多';
  return {sample:sample.length,counts,label};
}
export function paceBlock(records,research={}){
  const profile=paceSummary(records),rows=research.sectionals||[];
  return `<div class="racing-kpis"><div><span>近十场走位概况</span><strong>${profile.label}</strong></div>${Object.entries(profile.counts).map(([k,n])=>`<div><span>${k}</span><strong>${n}<small> 场</small></strong></div>`).join('')}</div><p class="note">${profile.sample} 场有走位记录。按首个记录点分组：第 1 位前领、第 2–4 位跟前、第 5–8 位居中、第 9 位及以后留后；这是位置描述，不是固定战术，也不是速度评级。</p><h3>最近三场官方分段时间</h3>${rows.length?rows.map(r=>`<div class="research-summary horse-sectional"><div class="section-head"><h4>${esc(r.date)} · ${esc(r.course)} · ${val(r.distance)} 米</h4>${sourceLink(r.source,'官方分段 ↗')}</div><p>完成 ${esc(r.finishTime)} · 第 ${esc(r.position)} 名 · ${r.fieldSize} 匹 · 采集 ${stamp(r.fetchedAt)}</p>${table(['分段','途程','本马用时','段末位置','每 200 米用时'],r.splits.map((s,i)=>[`第 ${i+1} 段`,s.metres?`${s.metres} 米`:'—',s.seconds.toFixed(2)+' 秒',s.position?`第 ${s.position} 位`:'—',s.sub200?.length?s.sub200.map(n=>n.toFixed(2)).join(' / ')+' 秒':'—']))}<p class="note">${r.splits.at(-1)?.metres===400?'末段 400 米 '+r.splits.at(-1).seconds.toFixed(2)+' 秒。':''}不同马场、途程和场地状况的时间不能直接当作能力排名。</p></div>`).join(''):`<div class="empty">${research.pending?'正在读取官方分段时间…':'暂无已核对的官方分段时间。'}</div>`}`;
}
export function bindWorkouts(target,research={}){
  const all=research.workouts?.records||[];let page=0,type='',days='90';
  target.innerHTML=`<div class="toolbar"><label>时间范围<select id="workout-days"><option value="90">最近 90 天</option><option value="30">最近 30 天</option><option value="all">全部已收录</option></select></label><label>操练类别<select id="workout-type"><option value="">全部类别</option>${[...new Set(all.map(r=>r.type))].map(t=>`<option>${esc(t)}</option>`).join('')}</select></label></div><p id="workout-count" class="note"></p><div id="workout-table"></div><div class="toolbar" id="workout-pagination"></div><p class="note">${research.workouts?'香港赛马会 · 采集 '+stamp(research.workouts.fetchedAt)+' · '+sourceLink(research.workouts.source,'资料来源 ↗'):''} 途程只显示来源明列的米数；圈数不折算为米数。用时保留来源格式，非比赛完成时间。晨操次数不等同于状态优劣。</p>`;
  function paint(){
    const cutoff=new Date(Date.now()-Number(days)*86400000).toISOString().slice(0,10);
    const rows=all.filter(r=>(!type||r.type===type)&&(days==='all'||r.date>=cutoff)),pages=Math.max(1,Math.ceil(rows.length/20));page=Math.min(page,pages-1);
    target.querySelector('#workout-count').textContent=`筛选后 ${rows.length} 条，已收录 ${all.length} 条晨操。`;
    target.querySelector('#workout-table').innerHTML=rows.length?table(['日期','类别','马场 / 跑道','途程','公布用时','骑乘人员','操练详情 / 配备'],rows.slice(page*20,page*20+20).map(r=>[esc(r.date),esc(r.type),esc(r.track),r.distance?`${r.distance} 米`:'—',val(r.publishedTime),val(r.rider),`${esc(r.details||'—')}<small>${esc(r.equipment||'')}</small>`])):`<div class="empty">${research.pending?'正在读取晨操记录…':research.workouts?'这个筛选范围没有已公布记录。':'暂无已收录晨操；来源恢复后会在打开档案时重试。'}</div>`;
    const pager=target.querySelector('#workout-pagination');pager.innerHTML=`<span>第 ${page+1} / ${pages} 页</span><button class="button secondary compact" data-prev ${page===0?'disabled':''}>上一页</button><button class="button secondary compact" data-next ${page===pages-1?'disabled':''}>下一页</button>`;
    pager.querySelector('[data-prev]').onclick=()=>{page--;paint();};pager.querySelector('[data-next]').onclick=()=>{page++;paint();};
  }
  target.querySelector('#workout-days').onchange=e=>{days=e.target.value;page=0;paint();};
  target.querySelector('#workout-type').onchange=e=>{type=e.target.value;page=0;paint();};paint();
}
