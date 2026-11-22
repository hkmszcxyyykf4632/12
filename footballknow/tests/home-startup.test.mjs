import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

const scenarios=['home-success','home-failure','teams-deeplink','navigate-sponsors','navigate-teams','navigate-sponsors-failure'];
for(const scenario of scenarios)test(`startup: ${scenario}`,()=>{
  const result=execFileSync(process.execPath,['--input-type=module','-e',`(${runScenario.toString()})(${JSON.stringify(scenario)})`],{cwd:new URL('..',import.meta.url),encoding:'utf8',timeout:15000});
  assert.match(result,/PASS/);
});

async function runScenario(scenario){
  const {default:assert}=await import('node:assert/strict');
  const {readFile,writeFile}=await import('node:fs/promises');
  const {JSDOM}=await import('jsdom');
  const root=new URL('./public/',`file:///${process.cwd().replaceAll('\\','/')}/`);
  const fixture=JSON.parse(await readFile(new URL('data.json',root),'utf8'));
  const initialHash=scenario==='teams-deeplink'?'#/teams':'';
  const dom=new JSDOM(await readFile(new URL('index.html',root),'utf8'),{url:'http://localhost:8765/'+initialHash});
  const w=dom.window;
  w.scrollTo=()=>{};
  Object.assign(globalThis,{window:w,document:w.document,location:w.location,localStorage:w.localStorage,FormData:w.FormData,matchMedia:()=>({matches:true}),CSS:{escape:value=>value}});
  const tick=()=>new Promise(resolve=>setTimeout(resolve,30));
  let releaseData,releaseOdds,releaseFeeds;
  const dataGate=new Promise(resolve=>releaseData=resolve),oddsGate=new Promise(resolve=>releaseOdds=resolve),feedsGate=new Promise(resolve=>releaseFeeds=resolve);
  const requests=[];
  globalThis.fetch=async path=>{
    path=String(path);requests.push(path);
    if(path==='./finance/assets.json'||path==='./editorial-articles.json')await feedsGate;
    let body={};
    if(path==='./data.json'){
      await dataGate;
      if(scenario.endsWith('failure'))throw Error('test football unavailable');
      body=fixture;
    }else if(path==='./odds-history.json')await oddsGate;
    else if(path==='/api/visits')body={total:42};
    else if(path==='./editorial-articles.json')body={updatedAt:'2026-11-22',articles:[{id:'test',title:'测试专题分析',image:'gold.jpg',category:'测试',dek:'观点',imageAlt:'金条'}]};
    else if(path==='/api/status')body={jobs:{}};
    return {ok:true,status:200,json:async()=>body};
  };
  const capture=async name=>{if(process.env.HOME_STARTUP_EVIDENCE)await writeFile(process.env.HOME_STARTUP_EVIDENCE+'/'+scenario+'-'+name+'.html',w.document.documentElement.outerHTML);};
  try{
    await import('./public/app.js');await tick();
    const main=w.document.querySelector('#main');
    if(!initialHash){
      assert.ok(main.querySelector('.portal-masthead'));
      assert.match(main.querySelector('#home-markets').textContent,/正在读取市场行情/);
      assert.match(main.querySelector('#home-insights').textContent,/正在读取专题分析/);
      await capture('feeds-pending');
    }
    releaseFeeds();await tick();
    if(initialHash){
      assert.equal(w.location.hash,initialHash);assert.match(main.textContent,/正在读取球队资料/);assert.equal(main.querySelector('.portal-masthead'),null);
    }else{
      assert.ok(main.querySelector('.portal-masthead'));assert.ok(main.querySelector('#home-insights'));assert.ok(main.querySelector('#home-markets'));
      assert.match(main.querySelector('#home-lead').textContent,/正在读取足球/);
      assert.match(main.querySelector('#home-insights').textContent,/测试专题分析/);
      assert.match(main.querySelector('#home-markets').textContent,/市场行情/);
      assert.match(main.querySelector('#home-visits').textContent,/42/);
      assert.ok(requests.includes('./finance/assets.json'));assert.ok(requests.includes('./editorial-articles.json'));assert.ok(requests.includes('/api/visits'));
      assert.equal(w.location.hash,'');
    }
    await capture('pending');
    if(scenario.startsWith('navigate-')){
      w.location.hash=scenario==='navigate-teams'?'#/teams':'#/sponsors';await tick();
      assert.equal(main.querySelector('.portal-masthead'),null);
    }
    const identity=main.firstElementChild;
    releaseData();await tick();
    if(!scenario.endsWith('failure')){
      assert.ok(requests.includes('./odds-history.json'));
      assert.equal(main.firstElementChild,identity,'slow optional snapshots must not redraw the current page');
      releaseOdds();await tick();
    }
    if(scenario==='home-success'){
      assert.equal(main.firstElementChild,identity,'completion updates football slots in place');
      assert.ok(main.querySelector('#home-kpi .kpi-strip'));assert.doesNotMatch(main.querySelector('#home-lead').textContent,/正在读取足球/);assert.equal(w.location.hash,'');
    }else if(scenario==='home-failure'){
      assert.equal(main.firstElementChild,identity);assert.match(main.querySelector('#home-lead').textContent,/test football unavailable/);
      assert.match(main.querySelector('#home-insights').textContent,/测试专题分析/);assert.match(main.querySelector('#home-markets').textContent,/市场行情/);
      w.location.hash='#/teams';await tick();assert.match(main.textContent,/test football unavailable/);
      w.location.hash='#/';await tick();assert.ok(main.querySelector('.portal-masthead'));assert.match(main.querySelector('#home-lead').textContent,/test football unavailable/);
    }else if(scenario.includes('sponsors')){
      assert.equal(w.location.hash,'#/sponsors');assert.equal(main.firstElementChild,identity);assert.ok(main.querySelector('.sponsor-grid'));
    }else{
      assert.equal(w.location.hash,'#/teams');assert.equal(main.querySelectorAll('[data-team-search]').length,fixture.teams.length);
    }
    await capture('complete');console.log('PASS '+scenario);
  }finally{releaseData();releaseOdds();releaseFeeds();w.dispatchEvent(new w.Event('pagehide'));w.close();}
}
