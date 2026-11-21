import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {readFile,writeFile} from 'node:fs/promises';
import {evidenceReviewHtml,bindEvidenceReview} from '../public/evidence-review.mjs';

function fixture(){return {
  format:'evidence-review-1',revision:'a1234567890b',analysisStatus:'ready',generatedAt:'2026-11-20T13:00:00Z',
  summary:['比赛结果与原判断的对照。','失准原因仍需后续样本核验。'],
  claimAudits:[{claimId:'claim-private-id',verdict:'contradicted',explanation:'进球时段与原判断不符。',evidenceIds:['fact-private-id']}],
  drivers:[{title:'局势转折',kind:'observed',explanation:'60分钟发生进球。',evidenceIds:['fact-private-id']},
    {title:'可能的解释',kind:'inference',explanation:'可能与阵型变化相关，但不能确认。',evidenceIds:['fact-private-id']}],
  marketReview:[{title:'同一市场的赔率变化',explanation:'两个采样点不等于正式开盘与封盘。',evidenceIds:['fact-private-id']}],
  lessons:[{title:'检查时间分布',category:'method',explanation:'原判断可能过度依赖总量。',claimIds:['claim-private-id'],evidenceIds:['fact-private-id'],nextCheck:'下一批十场先记录时段，再比较预测与实际。'},
    {title:'比赛后新变化',category:'unexpected',explanation:'开赛后出现新情况。',claimIds:[],evidenceIds:['fact-private-id'],nextCheck:'保留首次公开时间。'}],
  dossier:{domain:'football',original:{pick:'H'},claims:[{id:'claim-private-id',text:'固定原文：主队「下半场」保持优势。'}],
    timeline:[{time:'60′',text:'客队进球，比分0:1。',evidenceIds:['fact-private-id']}],
    facts:[{id:'fact-private-id',time:'60′',text:'官方逐分钟记录进球。',sourceIds:['source-private-id']}],
    sources:[{id:'source-private-id',title:'官方比赛中心',url:'https://example.org/match?a=1&b=2',updatedAt:'2026-11-20T12:00:00Z'}],
    gaps:['缺少首发公布前后的连续赔率快照。']}
};}
const dom=report=>new JSDOM(evidenceReviewHtml(report),{url:'https://local.test/#/match/test'});

test('detailed review exposes timeline, exact claims, causal limits, odds and prospective checks',()=>{
  const document=dom(fixture()).window.document;
  for(const title of ['实际发生了什么','原判断逐条核对','关键转折与可能原因','盘口与赔率研究','下次怎样检验改进','尚缺哪些资料','资料来源']){
    assert.ok([...document.querySelectorAll('h3')].some(heading=>heading.textContent===title),title);
  }
  assert.equal(document.querySelector('blockquote').textContent,'固定原文：主队「下半场」保持优势。');
  for(const text of ['证据反驳','已核实事实','可能解释','方法与遗漏','事后新情况','下一批十场','后续样本检验','不是公告首次公开时间','缺少首发公布前后的连续赔率快照。'])assert.ok(document.body.textContent.includes(text),text);
  assert.equal(document.querySelector('.er-evidence').open,false);
  assert.equal(document.querySelectorAll('table').length,0);
  assert.equal(document.querySelector('a[target="_blank"]').rel,'noopener noreferrer');
  for(const privateId of ['claim-private-id','fact-private-id','source-private-id'])assert.ok(!document.body.textContent.includes(privateId));
});

test('all user-provided text is escaped and malformed links cannot inject executable content',()=>{
  const report=fixture(),attack='<img src=x onerror="alert(1)"><script>alert(1)</script>';
  report.summary=[attack];report.revision='"><script>bad()</script>';
  report.dossier.claims[0].text=attack;report.dossier.timeline[0].text=attack;
  report.dossier.timeline[0].time=attack;report.dossier.facts[0].text=attack;
  report.dossier.facts[0].time=attack;report.dossier.sources[0].title=attack;
  report.dossier.sources[0].updatedAt=attack;report.dossier.gaps=[attack];
  report.claimAudits[0].explanation=attack;report.drivers[0].title=attack;
  report.drivers[0].explanation=attack;report.marketReview[0].explanation=attack;
  report.lessons[0].nextCheck=attack;report.lessons[0].explanation=attack;
  report.dossier.sources[0].url='javascript:alert(1)';
  const document=dom(report).window.document;
  assert.equal(document.querySelectorAll('script,img,[onerror],[onclick]').length,0);
  assert.ok(document.body.textContent.includes(attack));
  assert.equal(document.querySelectorAll('a[target="_blank"]').length,0);
  assert.ok([...document.querySelectorAll('[id]')].every(node=>/^[a-zA-Z0-9_-]+$/.test(node.id)));
});

test('source href allows HTTP(S) and safe single-slash paths only',()=>{
  for(const [url,allowed] of [
    ['https://example.org/a',true],['http://example.org/a',true],['/source/item?a=1',true],
    ['javascript:alert(1)',false],['data:text/html,hello',false],['//evil.test/a',false],
    ['/\\evil.test/a',false],['/%5cevil.test/a',false],['/%2fevil.test/a',false],
    ['https:\\evil.test',false],['https://ok.test/\nfoo',false],['https://a:b@evil.test/',false],
  ]){
    const report=fixture();report.dossier.sources[0].url=url;
    assert.equal(Boolean(dom(report).window.document.querySelector('a[target="_blank"]')),allowed,url);
  }
});

test('awaiting and limited reports show facts without implying finished reasoning',()=>{
  for(const status of ['awaiting','limited']){
    const report=fixture();report.analysisStatus=status;report.generatedAt=null;report.drivers=[];report.lessons=[];report.marketReview=[];
    const document=dom(report).window.document;
    assert.ok(document.body.textContent.includes('详细原因分析尚未完成'));
    assert.ok(document.body.textContent.includes('官方逐分钟记录进球。'));
    assert.ok(!document.body.textContent.includes('已整理详细复盘'));
    assert.ok(!document.body.textContent.includes('复盘整理时间：'));
  }
});

test('missing original never renders invented claim audits or method omissions',()=>{
  const report=fixture();report.dossier.original=null;
  report.claimAudits[0].explanation='凭空声称忽略了首发';report.lessons[0].explanation='凭空声称漏看';
  const document=dom(report).window.document;
  assert.ok(document.body.textContent.includes('没有保存的原预测'));
  assert.ok(!document.body.textContent.includes('固定原文：'));
  assert.ok(!document.body.textContent.includes('凭空声称'));
  assert.ok(document.body.textContent.includes('官方逐分钟记录进球。'));
});

test('citation clicks open evidence and focus the matching fact without changing the SPA route',()=>{
  const window=dom(fixture()).window,document=window.document;
  bindEvidenceReview(document);bindEvidenceReview(document);
  const link=document.querySelector('.er-timeline a[data-evidence-anchor]');
  const destination=document.getElementById(link.getAttribute('href').slice(1));
  let scrolls=0;destination.scrollIntoView=()=>{scrolls++;};
  const event=new window.MouseEvent('click',{bubbles:true,cancelable:true});
  link.dispatchEvent(event);
  assert.equal(event.defaultPrevented,true);
  assert.equal(document.querySelector('.er-evidence').open,true);
  assert.equal(document.activeElement,destination);
  assert.equal(window.location.hash,'#/match/test');
  assert.equal(scrolls,1);
  const sourceLink=destination.querySelector('a[data-evidence-anchor]');
  sourceLink.dispatchEvent(new window.MouseEvent('click',{bubbles:true,cancelable:true}));
  assert.ok(document.activeElement.className!==undefined);
  assert.equal(document.activeElement.id,sourceLink.getAttribute('href').slice(1));
});

test('revision-prefixed anchors remain distinct across reports and invalid references are omitted',()=>{
  const first=fixture(),second=fixture();second.revision='b1234567890c';
  second.claimAudits[0].evidenceIds=['missing'];
  const document=new JSDOM(evidenceReviewHtml(first)+evidenceReviewHtml(second)).window.document;
  const ids=[...document.querySelectorAll('[id]')].map(node=>node.id);
  assert.equal(new Set(ids).size,ids.length);
  for(const link of document.querySelectorAll('a[data-evidence-anchor]'))assert.ok(document.getElementById(link.getAttribute('href').slice(1)));
  assert.ok(!document.body.textContent.includes('missing'));
});

test('empty input returns no fake review and stocks use the market comparison label',()=>{
  assert.equal(evidenceReviewHtml(null),'');assert.equal(evidenceReviewHtml({}),'');
  const report=fixture();report.dossier.domain='stocks';
  assert.ok(dom(report).window.document.body.textContent.includes('价格与市场对照'));
});

test('football and stock panels render factual reviews for empty originals and never score null as failure',async()=>{
  const window=new JSDOM('<main id="main"></main>',{url:'https://local.test/#/match/test'}).window;
  Object.assign(globalThis,{document:window.document,window,location:window.location,localStorage:window.localStorage});
  const {bindReview,conciseReport}=await import('../public/review-panel.mjs');
  const originalFetch=globalThis.fetch;
  localStorage.setItem('footballknow.stock-following.v1',JSON.stringify({version:1,codes:['00700']}));
  try{
    const cases=[
      {kind:'football',original:{},correct:null,finished:true,enabled:true},
      {kind:'football',original:{pick:'H',analysis:{summary:['原分析']}},correct:null,finished:true,enabled:true},
      {kind:'stock',original:{},correct:null,finished:false,enabled:false},
      {kind:'stock',original:{week:'up',quarter:'flat',summary:['原分析']},correct:null,finished:false,enabled:true},
    ];
    for(const item of cases){
      const report=fixture();report.dossier.original=item.original.pick||item.original.week?item.original:null;
      if(item.kind==='stock')report.dossier.domain='stocks';
      const data={original:item.original,finished:item.finished,correct:item.correct,actual:null,score:null,review:report,
        close:{date:'2026-11-20'},outcomes:{week:{status:'已到期',correct:null},quarter:{status:'观察中',correct:null}}};
      const calls=[];globalThis.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>data};};
      const target=document.createElement('section');document.querySelector('main').append(target);
      bindReview(target,{kind:item.kind,id:item.kind==='stock'?'00700':'test',league:'epl'});
      await new Promise(resolve=>setImmediate(resolve));
      assert.ok(target.querySelector('.evidence-review'));
      assert.ok(!target.textContent.includes('undefined'));
      assert.ok(!target.textContent.includes('未命中'));
      assert.equal(target.querySelector('[data-review-generate]').disabled,!item.enabled);
      target.dispatchEvent(new window.Event('stock-following-changed'));
      assert.equal(target.querySelector('[data-review-generate]').disabled,!item.enabled);
      assert.equal(calls.length,1);
      assert.match(calls[0][0],item.kind==='stock'?/^\/api\/stocks\/00700\/review$/:/^\/api\/reviews\/football\?/);
      target.remove();
    }
    assert.ok(conciseReport(fixture()).includes('evidence-review'));
  }finally{globalThis.fetch=originalFetch;}
});

test('automatic football and racing settlement surfaces use detailed review while forecasts remain brief',async()=>{
  const {forecastsHtml}=await import('../public/football-forecasts.mjs');
  const {evaluationHtml}=await import('../public/racing-page.mjs');
  const row={id:'123',dailyId:'123',competitionId:'710',kickoff:'2026-11-21T16:00:00Z',finished:true,
    teams:{home:{id:'1',label:'甲'},away:{id:'2',label:'乙'}}};
  const report=fixture();report.revision='football-integration';
  const prediction={score:[2,1],asianSide:'pass',issuedAt:'2026-11-21T09:00:00Z',summary:['简短赛前预测。'],details:[],
    review:{status:'evaluated',text:'赛果已确认。',analysis:report}};
  const value={supported:true,eventId:'123',kickoff:row.kickoff,teams:{home:'1',away:'2'},stages:{initial:{report:prediction}}};
  const footballHtml=forecastsHtml(row,value),football=new JSDOM(footballHtml).window.document;
  assert.ok(football.querySelector('.forecast-evidence-review .evidence-review'));
  assert.equal(football.querySelector('.forecast-card .evidence-review'),null);
  assert.ok(football.querySelector('.forecast-card').textContent.includes('简短赛前预测。'));
  assert.equal(new JSDOM(forecastsHtml({...row,id:'other',dailyId:'other'},value)).window.document.querySelector('.evidence-review'),null);
  const race={status:'finished',entries:[]},racingReport=fixture();
  racingReport.revision='racing-integration';racingReport.dossier.domain='racing';racingReport.dossier.original=null;
  const state={evaluation:{evaluated:0,wins:0,top3:0,pending:0,void:0},reports:{post:racingReport,pre:{}},outcome:{status:'evaluated',win:null}};
  const racingHtml=evaluationHtml(state,race),racing=new JSDOM(racingHtml).window.document;
  assert.ok(racing.querySelector('.evidence-review'));
  for(const invalid of ['undefined','Invalid Date','未命中'])assert.ok(!racing.body.textContent.includes(invalid));
  assert.ok(racing.body.textContent.includes('没有赛前发布的预测'));
  const html=await readFile(new URL('../public/index.html',import.meta.url),'utf8');
  const app=await readFile(new URL('../public/app.js',import.meta.url),'utf8');
  assert.match(html,/href="\.\/evidence-review\.css"/);
  assert.match(app,/bindEvidenceReview\(document\)/);
  if(process.env.EVIDENCE_RENDER_DIR){
    const awaiting=fixture();awaiting.revision='awaiting-preview';awaiting.analysisStatus='awaiting';awaiting.generatedAt=null;awaiting.drivers=[];awaiting.marketReview=[];awaiting.lessons=[];
    const content=`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>详细复盘组件验证</title><link rel="stylesheet" href="../../../public/styles.css"><link rel="stylesheet" href="../../../public/expansion.css"><link rel="stylesheet" href="../../../public/sections.css"><link rel="stylesheet" href="../../../public/daily.css"><link rel="stylesheet" href="../../../public/research-features.css"><link rel="stylesheet" href="../../../public/evidence-review.css"><style>main{max-width:1000px;margin:auto;padding:24px}.validation-surface{margin-bottom:48px}</style></head><body><main><h1>详细复盘组件验证</h1><p>以下为界面测试夹具，不是真实预测成绩。</p><section class="validation-surface"><h2>足球两阶段预测</h2>${footballHtml}</section><section class="validation-surface"><h2>赛马事实研究</h2>${racingHtml}</section><section class="validation-surface"><h2>详细分析尚待生成</h2>${evidenceReviewHtml(awaiting)}</section></main><script type="module">import {bindEvidenceReview} from '../../../public/evidence-review.mjs';bindEvidenceReview(document);</script></body></html>`;
    await writeFile(`${process.env.EVIDENCE_RENDER_DIR}/renderer-fixture.html`,content,'utf8');
  }
});
