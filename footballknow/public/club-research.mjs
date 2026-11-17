import {data,history,profiles} from './repository.mjs';
import {esc,cn,sourceLink} from './ui.mjs';
import {league} from './league.mjs';
import {opponentRecords,transferPattern} from './research-core.mjs';

export function clubResearch(team){
  const profile=profiles?.teams?.[team.id],rivals=opponentRecords(data.matches,team.name),pattern=transferPattern(history?.transfers||[],team.name);
  const opponentTable=(rows,title)=>'<section><h3>'+title+'</h3>'+(rows.length?'<div class="table-wrap"><table><thead><tr><th>对手</th><th>场次</th><th>胜 / 平 / 负</th><th>进 / 失球</th><th>最近交锋</th></tr></thead><tbody>'+rows.map(r=>'<tr><td>'+esc(cn(r.name))+'</td><td>'+r.played+'</td><td>'+r.wins+' / '+r.draws+' / '+r.losses+'</td><td>'+r.goals+' / '+r.conceded+'</td><td>'+esc(r.latest)+'</td></tr>').join('')+'</tbody></table></div>':'<p class="empty">当前历史窗口内没有达到条件的对手。</p>')+'</section>';
  const fields=[['全名','fullName'],['成立','founded'],['主场','stadium'],['容量','capacity'],['所有者 / 控股方','ownership'],['主席','chairman'],['会长','president']];
  const identity=profile?'<dl class="identity-grid">'+fields.filter(([,k])=>profile[k]).map(([l,k])=>'<div><dt>'+l+'</dt><dd>'+esc(profile[k])+'</dd></div>').join('')+'</dl><p class="note">'+sourceLink(profile.source,'球队背景来源')+' · 核对时间 '+esc(new Date(profile.updatedAt).toLocaleString('zh-CN'))+(profile.website?' · '+sourceLink(profile.website,'俱乐部官网'):'')+'</p>':'<p class="empty">球队背景资料正在同步。</p>';
  const finances=profile?.financials||[];
  return '<section id="club-section"><div class="section-head"><h2>球队背景与财务</h2><a class="button quiet" href="#/news/'+league.id+':'+team.id+'">本队新闻 →</a></div>'+identity+
    '<h3>已收录财务披露</h3>'+(finances.length?'<div class="table-wrap"><table><thead><tr><th>报告期</th><th>指标</th><th>金额</th><th>来源与口径</th></tr></thead><tbody>'+finances.map(f=>'<tr><td>'+esc(f.period)+'</td><td>'+esc(f.metric)+'</td><td>'+esc(f.value)+' '+esc(f.unit)+'</td><td>'+sourceLink(f.source,'报告')+' · '+esc(f.basis)+'</td></tr>').join('')+'</tbody></table></div>':'<p class="empty">尚未收录可核对的财报数值。'+(profile?.website?sourceLink(profile.website,'俱乐部官方资料'):'')+'</p>')+
    '<p class="note">财报按对应报告期展示。营业收入、利润、负债与转会支出是不同指标；未公开数值保留为空。</p></section>'+
    '<section id="rivals-section"><div class="section-head"><h2>对手相性</h2><span class="small subtle">已收录交锋 · 至少 '+rivals.minimum+' 场</span></div><div class="detail-columns">'+opponentTable(rivals.difficult,'较难应付的对手 · 历史负多于胜')+opponentTable(rivals.favourable,'占优对手 · 历史胜多于负')+'</div><p class="note">使用已收录跨赛季90分钟赛果，按失利率或胜率排序；表示这一历史窗口内的相性，不是下一场的确定结果。</p></section>'+
    '<section id="transfer-style-section"><h2>买卖球员习惯</h2><dl class="kpi-strip"><div class="kpi"><dt>引入 / 转出</dt><dd>'+pattern.incoming+' / '+pattern.outgoing+'</dd></div><div class="kpi"><dt>租借引入 / 外租</dt><dd>'+pattern.loanIn+' / '+pattern.loanOut+'</dd></div><div class="kpi"><dt>自由转会引入</dt><dd>'+pattern.freeIn+'</dd></div><div class="kpi"><dt>费用未公开记录</dt><dd>'+pattern.undisclosed+'</dd></div></dl><p>已收录引援较常来自：'+(pattern.partners.length?pattern.partners.map(([name,count])=>esc(cn(name))+'（'+count+' 次）').join('、'):'待积累转会记录')+'。</p><p class="note">统计当前收录的转会记录'+(pattern.first?'，最早为 '+esc(pattern.first):'')+'；租借与买断分别计数，费用没有跨币种相加。逐项来源见下方转会表。</p></section>';
}
