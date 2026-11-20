import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {ancestorPath,familyHorses,horseBranches,pedigreeKey} from '../public/bloodlines-core.mjs';
import {families,ancestry} from '../public/bloodlines-data.mjs';
const dom=new JSDOM('<main id="main"></main>',{url:'http://localhost/'});
Object.assign(globalThis,{document:dom.window.document,window:dom.window,location:dom.window.location,localStorage:dom.window.localStorage});
const {scenarioPosition,paceEffect}=await import('../public/racing-pace.mjs');
const {researchMatches}=await import('../public/match-centre-research.mjs');

test('pedigrees distinguish paternal and maternal-grandsire branches and reject unverified links',()=>{
  const family=families.find(f=>f.ancestor==='Danehill');
  const h={id:'A',name:'甲',rating:80,pedigree:{sire:'Bivouac (AUS)',damsire:'Fastnet Rock'}};
  assert.equal(horseBranches(h,family,ancestry).length,2);
  assert.deepEqual(ancestorPath('Bivouac','Danehill',ancestry).map(p=>p.name),['Bivouac','Exceed And Excel','Danehill']);
  assert.equal(familyHorses({horses:[h,h,{...h,id:'B',retired:true}]},family,ancestry,'all').length,1);
  assert.equal(familyHorses({horses:[h]},family,ancestry,'sire','Fastnet').length,0);
  assert.equal(familyHorses({horses:[h]},family,ancestry,'damsire','Fastnet').length,1);
  assert.equal(ancestorPath('Unknown','Danehill',ancestry),null);
  assert.equal(pedigreeKey(' Mr. Prospector (USA) '),'mr prospector');
});
test('cyclic or conflicting ancestry never creates a family match',()=>{
  const edge=(name,sire)=>({name,sire,source:'https://example.test/pedigree'});
  assert.equal(ancestorPath('A','Z',[edge('A','B'),edge('B','A')]),null);
  assert.equal(ancestorPath('A','Z',[edge('A','B'),edge('A','C'),edge('B','Z')]),null);
  assert.equal(ancestorPath('A','Z',[{name:'A',sire:'Z',source:'javascript:alert(1)'}]),null);
});
test('scenario positions stay bounded, lack of history stays absent and fast pace alters conditions',()=>{
  const front={earlyPosition:2,lateGain:0,draw:3,style:'跟前'};
  assert.ok(scenarioPosition(front,'fast',1,12)>scenarioPosition(front,'slow',1,12));
  assert.equal(scenarioPosition({...front,earlyPosition:null},'fast',1,12),null);
  for(const stage of [0,.2,.4,.8,1])assert.ok(scenarioPosition(front,'normal',stage,12)>=1&&scenarioPosition(front,'normal',stage,12)<=12);
  assert.match(paceEffect(front,'fast'),/消耗/);
});
test('match research cannot cross leagues, legs or home-away identity',()=>{
  const m={id:'espn:123',home:'A',away:'B',date:'2026-11-20',kickoff:'2026-11-20T20:00:00Z'};
  const v={...m,matchId:m.id,league:'epl'};
  assert.ok(researchMatches(v,m,'epl'));
  assert.equal(researchMatches(v,m,'ucl'),false);
  assert.equal(researchMatches({...v,away:'C'},m,'epl'),false);
  assert.equal(researchMatches({...v,kickoff:'2026-11-21T20:00Z'},m,'epl'),false);
});
