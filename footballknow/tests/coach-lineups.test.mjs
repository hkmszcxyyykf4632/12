import test from 'node:test';
import assert from 'node:assert/strict';
import {coachPeriodMatches,coachMatchesForTeam,coachLineupChange,previousCoachMatch} from '../public/coach-lineups.mjs';
const now=Date.parse('2026-11-23T12:00:00Z');
const match=(date,id,extra={})=>({date,id,home:'Team',away:'Other',competition:'英超',season:'2026/27',finished:true,started:true,...extra});
const a=match('2026-11-01','a'),b=match('2026-11-07','b'),c=match('2026-11-14','c');
const lineup=(m,ids,extra={})=>({league:'epl',matchId:m.id,date:m.date,home:m.home,away:m.away,formation:'4-3-3',starters:ids.map(id=>({id,name:'Player '+id})),...extra});
test('30-day filter includes exact boundary and excludes future and missing dates',()=>{
 for(const [date,expected] of [['2026-10-24T12:00:00Z',true],['2026-10-24T11:59:59Z',false],['2026-11-24',false],[null,false],['bad',false]])assert.equal(coachPeriodMatches(date,'30',now),expected);
 assert.equal(coachPeriodMatches('2026-10-01','recent',now),true);
 assert.equal(coachPeriodMatches('2020-01-01','all',now),true);
});
test('lineup changes use stable player identities and actual adjacent match',()=>{
 const rows=[lineup(a,['1','2']),lineup(b,['1','3']),lineup(c,['4','1'],{formation:'4-4-2'})];
 const previous=previousCoachMatch([c,a,b],c,'Team',now);assert.equal(previous.id,'b');
 const change=coachLineupChange(c,previous,rows,'epl');
 assert.equal(change.status,'compared');assert.equal(change.formationChanged,true);
 assert.deepEqual(change.added.map(p=>p.id),['4']);assert.deepEqual(change.removed.map(p=>p.id),['3']);
 const missing=coachLineupChange(c,previous,[rows[0],rows[2]],'epl');assert.equal(missing.status,'baseline-missing');
});
test('wrong fixture and other league lineups never supply a comparison',()=>{
 const rows=[lineup(b,['1']),lineup(c,['2'],{away:'Wrong'}),lineup(c,['3'],{league:'ucl'})];
 assert.equal(coachLineupChange(c,b,rows,'epl').status,'missing');
 assert.equal(coachLineupChange(c,b,[lineup(c,['1'],{formation:''}),lineup(b,['1'])],'epl').formationChanged,false);
});
test('postponements excluded; an overdue unknown result remains the immediate baseline',()=>{
 const pending=match('2026-11-10','pending',{started:false,finished:false});
 const postponed=match('2026-11-12','later',{started:false,finished:false,status:'Postponed'});
 assert.equal(previousCoachMatch([a,b,pending,postponed,c],c,'Team',now).id,'pending');
});
test('all known club competitions join without league team ID collisions',()=>{
 const data=(teams,matches,competition)=>({teams,matches,season:'2026/27',competition});
 const team={id:1,espnId:12,name:'Team',cn:'本队'};
 const feeds=[{league:'epl',data:data([team], [a], '英超')},{league:'ucl',data:data([{id:99,espnId:12,name:'Team English',cn:'本队'}],[match('2026-11-03','cup',{home:'Team English',competition:'欧冠'})],'欧冠')},{league:'laliga',data:data([{id:1,espnId:77,name:'Unrelated',cn:'另一队'}],[],'西甲')}];
 const result=coachMatchesForTeam(feeds,'epl',team);
 assert.deepEqual(result.targets,[{league:'epl',teamId:1},{league:'ucl',teamId:99}]);
 assert.equal(result.matches.length,2);const cup=result.matches.find(m=>m.id==='cup');assert.equal(cup.home,'Team');assert.equal(cup.sourceHome,'Team English');assert.equal(cup.league,'ucl');
});

test('same coach change appears once across domestic and Champions League views',async()=>{
 const {uniqueCoachChanges}=await import('../public/coach-lineups.mjs');
 const common={date:'2026-11-01',team:{name:'Arsenal',espnId:'359'},change:{incoming:'A',outgoing:'B'}};
 const ucl={...common,league:'ucl'},epl={...common,league:'epl'};
 const other={...epl,date:'2026-08-01'},different={...epl,team:{name:'Other',espnId:'360'}};
 assert.deepEqual(uniqueCoachChanges([ucl,epl,other,different]),[epl,other,different]);
 assert.deepEqual(uniqueCoachChanges([ucl]),[ucl]);
});
