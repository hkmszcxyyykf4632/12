import {api} from './api.mjs';
import {data} from './repository.mjs';
import {main,esc,cn,pageHeading,timeText} from './ui.mjs';
import {playerLabel,timestamp} from './football-components.mjs';
import {league,analysisPath} from './league.mjs';

function baselinePanel(report) {
  const model=report.baseline;
  if(!model)return `<p class="note">${league.name}样本待补充。</p>`;
  const probabilities=[['主胜',model.probabilities.home,'home'],['平局',model.probabilities.draw,'draw'],['客胜',model.probabilities.away,'away']];
  return `<div class="model-panel"><div class="section-head"><h2>胜平负与比分</h2><span class="tag">独立泊松</span></div><div class="probability-row">${probabilities.map(([label,value,kind])=>`<div class="probability ${kind}"><span>${label}</span><strong>${(value*100).toFixed(1)}<small>%</small></strong><div class="probability-track" role="img" aria-label="${label} ${(value*100).toFixed(1)}%"><i style="width:${value*100}%"></i></div></div>`).join('')}</div><dl class="model-facts"><div><dt>主队模型进球均值</dt><dd>${model.homeGoalMean.toFixed(2)}</dd></div><div><dt>客队模型进球均值</dt><dd>${model.awayGoalMean.toFixed(2)}</dd></div><div><dt>${report.match?.neutral?'中立场 · 双方同赛事样本':'主队主场 / 客队客场样本'}</dt><dd>${model.homeSample} / ${model.awaySample} 场</dd></div><div><dt>${league.name}背景样本</dt><dd>${model.leagueSample} 场</dd></div></dl><p class="note">概率较高的比分：${model.scorelines.map(([score,p])=>`${esc(score)}（${(p*100).toFixed(1)}%）`).join(' · ')}</p><details class="method-details"><summary>计算方法</summary><p>${report.match?.neutral?'中立场双方各取最近至多20场同赛事比赛，不加入主场优势。':'主队主场与客队客场各取最近至多20场。'}加入相当于5场同赛事平均值的收缩量，计算独立进球分布。样本截止到比赛日期之前。</p><ul>${model.limitations.map(item=>`<li>${esc(item)}</li>`).join('')}</ul></details></div>`;
}

function comparison(report) {
  const home=report.homeForm,away=report.awayForm;
  if(!home||!away)return '';
  const rows=[['样本场数',home.matches,away.matches],['胜 / 平 / 负',`${home.wins} / ${home.draws} / ${home.losses}`,`${away.wins} / ${away.draws} / ${away.losses}`],['进球',home.scored,away.scored],['失球',home.conceded,away.conceded]];
  return `<div class="section-head"><h2>近况对照</h2><span class="small subtle">最近至多二十场${league.historyLabel} · 可含${league.lower}</span></div><div class="table-wrap"><table class="comparison-table"><thead><tr><th>观察指标</th><th>${esc(cn(home.team))}</th><th>${esc(cn(away.team))}</th></tr></thead><tbody>${rows.map(([label,h,a])=>`<tr><td>${label}</td><td>${h}</td><td>${a}</td></tr>`).join('')}</tbody></table></div><p class="note">近况覆盖${league.name}与${league.lower}；概率计算采用${league.name}样本。</p>`;
}

function localSummary(report) {
  const model=report.baseline;
  if(!model)return [`本场已有赛程，现有${league.name}样本尚不足以形成胜平负倾向。`,'补齐双方近期比赛与人员资料后，可更新本场结论。'];
  const ranked=[['home',model.probabilities.home],['draw',model.probabilities.draw],['away',model.probabilities.away]].sort((a,b)=>b[1]-a[1]);
  const leader=ranked[0][0],close=ranked[0][1]-ranked[1][1]<0.08;
  const tendency=leader==='draw'?'双方战平':`${cn(leader==='home'?report.match.home:report.match.away)}取胜`;
  return [`按当前本地统计，本场暂偏向${tendency}。${close?'前两种结果接近，整体形势较为均衡。':'这一结果在当前三项比较中领先。'}`,
    report.unavailablePlayers.length?`双方名单中有 ${report.unavailablePlayers.length} 名球员存在出场状态或转会动态，关键位置的最终人选仍会影响比赛走势。首发公布后适合更新判断。`:'双方目前没有额外的出场状态标记。最终首发与临场安排是下一次更新需要核对的信息。'];
}

function evaluationPanel(value) {
  if(!value)return '';
  const percent=number=>number==null?'待积累':`${(number*100).toFixed(1)}%`;
  const range=metric=>metric.interval95?metric.interval95.map(percent).join(' – '):'待积累';
  const baseline=value.baseline,measured=value.ai;
  return `<section class="evaluation-panel"><div class="section-head"><h2>命中率记录</h2><span class="small subtle">90 分钟胜／平／负 · 目标 38%</span></div><div class="table-wrap"><table><thead><tr><th>记录类型</th><th>已结算</th><th>命中率</th><th>95% 参考区间</th></tr></thead><tbody><tr><td>本地模型历史回测</td><td>${baseline.samples}</td><td>${percent(baseline.hitRate)}</td><td>${range(baseline)}</td></tr><tr><td>DeepSeek 赛前实测</td><td>${measured.samples}</td><td>${percent(measured.hitRate)}</td><td>${range(measured)}</td></tr></tbody></table></div><p class="note">回测范围：${esc(baseline.dateFrom||'待积累')} 至 ${esc(baseline.dateTo||'待积累')}。同批比赛全部选主胜：${percent(baseline.alwaysHomeHitRate)}；按赛前历史多数类选择：${percent(baseline.priorMajorityHitRate)}。</p><p class="note">${esc(measured.method)} 已记录 ${measured.recorded} 场，待结算 ${measured.pending} 场。历史回测与 DeepSeek 实测分开统计。</p></section>`;
}

function lineupEvidence(value){
 if(!value)return '';
 return `<section><div class="section-head"><h2>历史阵容依据</h2></div><div class="detail-columns">${Object.entries(value).map(([club,v])=>`<div><h3>${esc(cn(club))}</h3><p>最近 ${v.requestedMatches} 场中已取得 ${v.coveredMatches} 份完整首发。${v.latestTwoStarterOverlap!=null?`最近两份名单重合 ${v.latestTwoStarterOverlap} 人。`:''}</p><p class="small subtle">已收录阵型：${esc(Object.entries(v.formations||{}).map(([f,n])=>`${f||'未提供'}（${n}场）`).join('、')||'待补充')}</p>${v.matches?.length?`<ul>${v.matches.slice(0,5).map(m=>`<li><a href="#/match/${encodeURIComponent(m.matchId)}">${esc(m.date)} · ${esc(m.competition)} · ${esc(m.formation)} →</a></li>`).join('')}</ul>`:''}</div>`).join('')}</div><p class="note">只统计已收录名单。重合人数比较最近两份可用名单，未覆盖比赛不视为休息；具体出场与分钟可进入比赛详情查看。</p></section>`;
}

export function renderAnalysis(id) {
  const controller=new AbortController();
  const request=(path,options={})=>api(path,{...options,signal:controller.signal});
  main.innerHTML=`${pageHeading('下一场比赛','正在整理本场结论…')}<div class="loading">读取分析资料…</div>`;
  const load=async()=>{
    const [payload,session]=await Promise.all([request(analysisPath(id)),request('/api/auth/me').catch(()=>({authenticated:false}))]);
    if(controller.signal.aborted)return;
    const report=payload.report,match=report.match;
    if(!match){main.innerHTML=`${pageHeading('下一场比赛','尚未找到这支球队下一场已排期的比赛。')}<a class="button secondary" href="#/team/${Number(id)}">返回球队资料</a>`;return;}
    main.innerHTML=`<a class="back-link" href="#/team/${Number(id)}">← 返回 ${esc(report.team.cn)} 资料</a>${pageHeading(`${esc(cn(match.home))} <span class="versus">vs</span> ${esc(cn(match.away))}`,`${league.name}${match.phase?' · '+match.phase:''}${match.neutral?' · 中立场':''}。先看本场结论，再按需要展开依据。`,`<span class="tag">${esc(timeText(match.kickoff))}</span>`)}
      <section id="ai-section" class="analysis-result"><div class="section-head"><h2>本地模型辅助分析</h2>${session.authenticated?'<button class="button" id="generate-analysis">生成 / 更新结论</button>':'<a class="button secondary" href="#/admin">管理员登录后生成</a>'}</div><div id="ai-answer" aria-live="polite"></div><p id="analysis-error" class="form-error" role="alert"></p></section>
      <details id="analysis-details" class="analysis-disclosure"><summary><span>更多详细资料</span><small>数据、计算与来源</small></summary><div class="analysis-evidence"><div id="ai-detail-answer"></div><p class="note">球队资料：${timestamp(report.dataUpdatedAt)} · 赛程资料：${timestamp(report.liveUpdatedAt)} · 开赛时间按本地时区显示。</p>${baselinePanel(report)}${comparison(report)}
      ${lineupEvidence(payload.lineupEvidence)}<section><div class="section-head"><h2>人员情况</h2><a class="button quiet" href="#/team/${Number(id)}">转会与领队记录 ↗</a></div>${report.unavailablePlayers.length?`<div class="availability-list">${report.unavailablePlayers.map(p=>{const player=data.players.find(row=>row.code===p.code);return `<div><strong>${esc(player?playerLabel(player):p.web_name)}</strong><p>${esc(p.news||'人员动态待补充。')}</p></div>`;}).join('')}</div>`:'<p class="note">当前名单暂无额外出场状态标记。</p>'}</section>${evaluationPanel(payload.evaluation)}<p class="note"><a href="#/sources">查看资料来源与统计口径 ↗</a></p></div></details>`;
    const answer=main.querySelector('#ai-answer');
    function showAI(result,matches=true) {
      const current=matches&&Array.isArray(result?.summary)&&result.summary.length>=2&&result.summary.length<=3&&result.summary.every(item=>typeof item==='string'&&item.trim()&&item.length<=240);
      const paragraphs=current?result.summary:localSummary(report);
      answer.innerHTML=`<div class="analysis-summary">${paragraphs.map(text=>`<p>${esc(text)}</p>`).join('')}</div><p class="note analysis-stamp">${current?`结论更新：${timestamp(result.generatedAt)}`:'本地数据简报 · 大模型结论待生成'}</p>`;
      const detail=main.querySelector('#ai-detail-answer');
      if(!result){detail.innerHTML='';return;}
      detail.innerHTML=`${matches?'':'<p class="notice">以下已存报告对应之前比赛，本场结论待更新。</p>'}<div class="ai-meta">生成于 ${timestamp(result.generatedAt)} · ${esc(result.model)} · 规则版本 ${esc(result.rulesVersion)}</div>${result.details?.length?result.details.map(section=>`<section class="ai-detail"><h3>${esc(section.title)}</h3><p>${esc(section.text)}</p></section>`).join(''):`<div class="ai-answer">${esc(result.text)}</div>`}`;
    }
    showAI(payload.ai,payload.aiMatchesNext);
    main.querySelector('#generate-analysis')?.addEventListener('click',async event=>{
      const button=event.target;button.disabled=true;button.textContent='正在整理资料…';main.querySelector('#analysis-error').textContent='';
      try {const result=await request(analysisPath(id),{method:'POST',timeout:75000});if(!controller.signal.aborted)showAI(result,true);}
      catch(error){if(!controller.signal.aborted)main.querySelector('#analysis-error').textContent=error.message;}
      finally {button.disabled=false;button.textContent='生成 / 更新结论';}
    });
  };
  load().catch(error=>{if(!controller.signal.aborted)main.innerHTML=`${pageHeading('分析资料暂时无法载入','请稍后重试；球队与模拟记录仍可使用。')}<div class="error-box">${esc(error.message)}</div><a class="button secondary" href="#/team/${Number(id)}">返回球队资料</a>`;});
  return ()=>controller.abort();
}
