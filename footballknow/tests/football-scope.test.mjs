import test from 'node:test';
import assert from 'node:assert/strict';
import {supportsFootballAnalysis} from '../public/football-scope.mjs';
test('only four leagues and Champions League carry analysis',()=>{
 for(const id of ['700','740','730','720','775'])assert.equal(supportsFootballAnalysis({competitionId:id}),true);
 assert.equal(supportsFootballAnalysis({competitionId:'710',league:'epl'}),false);
 assert.equal(supportsFootballAnalysis({competitionId:'770'}),false);
 assert.equal(supportsFootballAnalysis({league:'ucl'}),true);
 assert.equal(supportsFootballAnalysis({competitionId:'ucl',league:'ucl'}),true);
});
