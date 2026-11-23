import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import {managerFixtures} from '../public/coach-fixtures.mjs';
import {mergeMatches} from '../public/live-core.mjs';

const now=Date.parse('2026-11-21T12:00:00Z');
const match=(id,date,extra={})=>({id,date,season:'2026/27',competition:'西甲',home:'Espanol',away:'Opponent',started:true,finished:true,homeGoals:1,awayGoals:0,...extra});
const options={competition:'西甲',now};

test('appointment inclusive, successor exclusive, chronological live and expected fixture numbers',()=>{
  const rows=[match('next-term','2026-12-01',{started:false,finished:false}),match('future','2026-11-30',{started:false,finished:false}),match('live','2026-11-21',{finished:false}),match('before','2026-10-27'),match('first','2026-10-28')];
  const result=managerFixtures(rows,'Espanol','2026-10-28','2026-12-01',options);
  assert.deepEqual(result.rows.map(row=>[row.match.id,row.label]),[['first','换帅后第1场'],['live','换帅后第2场'],['future','预计第3场']]);
  assert.equal(result.next.match.id,'future');
  assert.equal(managerFixtures(rows,'Espanol','2026-10-28','2026-11-21',options).next,null);
});

test('departure alone gives no new coach sequence; earlier appointment uses collected ordinal',()=>{
  const rows=[match('one','2026-10-30'),match('two','2026-11-30',{started:false,finished:false})];
  assert.deepEqual(managerFixtures(rows,'Espanol',null,null,options).rows,[]);
  const result=managerFixtures(rows,'Espanol','2026-01-01',null,options);
  assert.equal(result.coverageLimited,true);
  assert.deepEqual(result.rows.map(row=>row.label),['已收录第1场','预计第2场（已收录序号）']);
});

test('deduplicates aliases transitively; excludes other competitions and unplayed cancelled/postponed games',()=>{
  const rows=[match('before','2026-10-01'),match('old','2026-10-29',{started:false,finished:false}),match('current','2026-10-30',{aliases:['middle']}),match('middle','2026-10-31',{aliases:['old'],started:false,finished:false}),match('cup','2026-11-01',{competition:'国王杯'}),match('cancel','2026-11-02',{started:false,finished:false,status:'STATUS_CANCELED'}),match('postpone','2026-11-03',{started:false,finished:false,status:'Postponed'}),match('played','2026-11-04',{status:'Postponed'}),match('future','2026-11-30',{started:false,finished:false})];
  const result=managerFixtures(rows,'Espanol','2026-10-28',null,options);
  assert.deepEqual(result.rows.map(row=>row.number),[1,2,3]);
  assert.ok(result.rows[0].match.finished);
  assert.equal(result.rows[1].match.id,'played');
  assert.equal(result.next.label,'预计第3场');
});

test('same day fixtures follow kickoff order and fixture ids do not merge different seasons',()=>{
  const rows=[match('before','2026-10-01'),match('late','2026-11-21',{away:'B',kickoff:'2026-11-21T20:00:00Z',fixtureId:7}),match('early','2026-11-21',{away:'C',kickoff:'2026-11-21T10:00:00Z',finished:false}),match('old-season','2026-11-20',{fixtureId:7,season:'2025/26'})];
  assert.deepEqual(managerFixtures(rows,'Espanol','2026-10-28',null,options).rows.map(row=>row.match.id),['old-season','early','late']);
});

test('overdue scheduled game stays provisional and does not shift the next expected number',()=>{
  const rows=[match('before','2026-10-01'),match('first','2026-10-30'),match('unknown','2026-11-20',{started:false,finished:false}),match('next','2026-11-30',{started:false,finished:false})];
  const result=managerFixtures(rows,'Espanol','2026-10-28',null,options);
  assert.equal(result.rows[1].pending,true);
  assert.equal(result.rows[1].label,'预计第2场');
  assert.equal(result.next.label,'预计第3场');
});

test('Espanyol real snapshots and rendered links expose first win and every tenure match by default',async()=>{
  const read=name=>readFile(new URL(`../public/laliga/${name}.json`,import.meta.url),'utf8').then(JSON.parse);
  const [data,live,history]=await Promise.all(['data','live','history'].map(read));
  const change=history.managers.find(row=>row.team==='Espanol');
  assert.equal(change.joinedAt,'2026-10-28');
  const matches=mergeMatches({...data,league:'laliga'},live);
  const record={league:'laliga',team:data.teams.find(row=>row.name==='Espanol'),change,matches,names:Object.fromEntries(data.teams.map(row=>[row.name,row.cn]))};
  const sequence=managerFixtures(matches,'Espanol',change.joinedAt,null,options);
  assert.equal(sequence.rows[0].match.id,'2026-10-30|Villarreal|Espanol');
  assert.equal(sequence.rows[0].label,'换帅后第1场');
  assert.equal(sequence.rows[0].match.homeGoals,0);
  assert.equal(sequence.rows[0].match.awayGoals,1);
  const dom=new JSDOM('<main id="main"></main>',{url:'http://localhost/'});
  globalThis.document=dom.window.document;
  const {coachFixturesHtml}=await import('../public/coaches-page.mjs');
  const html=coachFixturesHtml(record,now);
  dom.window.document.querySelector('main').innerHTML=html;
  const section=dom.window.document.querySelector('.coach-fixtures');
  assert.equal(section.querySelectorAll(':scope > ul > li').length,sequence.rows.length);
  assert.equal(section.querySelector(':scope > details'),null);
  const firstLink=[...section.querySelectorAll('a')].find(link=>link.textContent.includes('换帅后第1场'));
  assert.equal(firstLink.getAttribute('href'),'./?league=laliga#/match/2026-10-30%7CVillarreal%7CEspanol');
  assert.match(firstLink.textContent,/0:1/);
  assert.match(section.textContent,/按已收录的西甲比赛顺序编号/);
  assert.match(coachFixturesHtml({...record,change:{leftAt:'2026-10-27'}},now),/继任日期未确认/);
  assert.doesNotMatch(coachFixturesHtml({...record,change:{leftAt:'2026-10-27'}},now),/#\/match/);
  if(process.env.COACH_EVIDENCE_DIR){
    await mkdir(process.env.COACH_EVIDENCE_DIR,{recursive:true});
    await writeFile(`${process.env.COACH_EVIDENCE_DIR}/espanyol-rendered.html`,html);
    await writeFile(`${process.env.COACH_EVIDENCE_DIR}/espanyol-snapshot-check.json`,JSON.stringify({change,now:new Date(now).toISOString(),coverageLimited:sequence.coverageLimited,rows:sequence.rows},null,2));
  }
  dom.window.close();
});

test('all tenure results and concise lineup changes are rendered with sources',async()=>{
  const {managerComparison,coachFixturesHtml}=await import('../public/coaches-page.mjs');
  const before=match('before','2026-09-30');
  const matches=[before,...Array.from({length:12},(_,i)=>match('m'+i,'2026-10-'+String(i+1).padStart(2,'0')))];
  assert.equal(managerComparison(matches,'Espanol','2026-10-01').after.played,12);
  const starters=(replace=false)=>Array.from({length:11},(_,i)=>({id:String(replace&&i===10?99:i),name:replace&&i===10?'新首发':'球员'+i}));
  const lineups=[before,matches[1]].map((m,i)=>({league:'laliga',matchId:m.id,date:m.date,home:m.home,away:m.away,formation:i?'4-4-2':'4-3-3',starters:starters(Boolean(i)),source:'https://example.com/lineups'}));
  const record={league:'laliga',team:{name:'Espanol'},change:{joinedAt:'2026-10-01'},matches,lineups};
  const html=coachFixturesHtml(record,now);
  assert.match(html,/首发调整 1 人/);assert.match(html,/4-3-3 → 4-4-2/);assert.match(html,/进入首发.*新首发/);assert.match(html,/退出首发.*球员10/);assert.match(html,/（换帅前）/);assert.match(html,/本场首发来源/);assert.match(html,/换帅后第12场/);
});
