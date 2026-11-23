import test from 'node:test';
import assert from 'node:assert/strict';
import {filterStocks,industryGroups,stockSector} from '../public/finance-core.mjs';

const rows=[
  {code:'00700',name:'腾讯控股',englishName:'TENCENT',sector:'科技',industryUpdatedAt:'2026-11-17',board:'主板',isHsi:true},
  {code:'01928',name:'金沙中国',sector:'博彩',industryUpdatedAt:'2026-11-17',board:'主板',isHsi:true},
  {code:'08400',name:'亚洲先锋娱乐',sector:'博彩',industryUpdatedAt:'2026-11-17',board:'GEM'},
  {code:'09999',name:'新上市公司',sector:'消费',board:'主板'},
  {code:'00823',name:'领展',sector:'地产',industryUpdatedAt:'2026-11-17',category:'Real Estate Investment Trusts'}
];

test('industry, exchange scope and bilingual search combine independently',()=>{
  assert.deepEqual(filterStocks(rows,{sector:'博彩'}).map(r=>r.code),['01928','08400']);
  assert.deepEqual(filterStocks(rows,{sector:'博彩',scope:'hsi'}).map(r=>r.code),['01928']);
  assert.deepEqual(filterStocks(rows,{sector:'博彩',scope:'gem'}).map(r=>r.code),['08400']);
  assert.equal(filterStocks(rows,{sector:'科技',query:'tencent'}).length,1);
  assert.equal(filterStocks(rows,{sector:'科技',query:'01928'}).length,0);
  assert.equal(filterStocks(rows,{sector:'地产',scope:'reit'}).length,1);
  assert.equal(filterStocks(rows,{query:'金沙',quotes:{'01928':{name:'金沙中国有限公司'}}}).length,1);
});

test('category totals include unclassified stocks without inventing an industry',()=>{
  assert.equal(stockSector(rows[3]),'待分类');
  assert.deepEqual(industryGroups(rows),[['地产',1],['博彩',2],['科技',1],['待分类',1]]);
  assert.equal(filterStocks(rows,{sector:'待分类'})[0].code,'09999');
  assert.equal(industryGroups(rows).reduce((sum,[,count])=>sum+count,0),rows.length);
});


test('other industry includes classified sectors outside the four shortcuts and combines with scope and search',()=>{
  const extra=[...rows,
    {code:'00992',name:'消费样本',sector:'消费',industryUpdatedAt:'2026-11-17',board:'主板',isHsi:true},
    {code:'08001',name:'能源样本',sector:'能源资源',industryUpdatedAt:'2026-11-17',board:'GEM'},
    {code:'09998',name:'无行业资料',sector:'未分类',industryUpdatedAt:'2026-11-17',board:'主板'}
  ];
  assert.deepEqual(filterStocks(extra,{sector:'其它'}).map(r=>r.code),['00992','08001']);
  assert.deepEqual(filterStocks(extra,{sector:'其它',scope:'hsi'}).map(r=>r.code),['00992']);
  assert.deepEqual(filterStocks(extra,{sector:'其它',query:'能源'}).map(r=>r.code),['08001']);
  assert.deepEqual(filterStocks(extra,{sector:'待分类'}).map(r=>r.code),['09999','09998']);
});
