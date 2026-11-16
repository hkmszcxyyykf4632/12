import test from 'node:test';
import assert from 'node:assert/strict';
import { validDate, moneyInput, decimalOdds, payout, summary, validateStore } from '../public/core.mjs';

test('decimal stake and odds produce exact cent-level returns', () => {
  assert.equal(moneyInput('19.99'), 1999);
  assert.equal(decimalOdds('2.125'), 2125);
  assert.equal(payout(1999, 2125, 'H', 'H'), 4248);
  assert.equal(payout(1999, 2125, 'H', 'A'), 0);
  assert.equal(payout(1999, 2125, 'H', 'V'), 1999);
  assert.equal(payout(1999, 2125, 'H', null), null);
});
test('pending stakes are reserved and voids do not inflate ROI', () => {
  const bank = summary([
    {stake:10000,oddsMilli:2500,selection:'H',result:'H'},
    {stake:5000,oddsMilli:3000,selection:'H',result:'A'},
    {stake:20000,oddsMilli:2000,selection:'D',result:null},
    {stake:12000,oddsMilli:4000,selection:'A',result:'V'},
  ]);
  assert.equal(bank.balance, 990000);
  assert.equal(bank.profit, 10000);
  assert.equal(bank.pending, 20000);
  assert.equal(bank.settledStake, 15000);
  assert.equal(bank.settled, 2);
  assert.equal(bank.wins, 1);
  assert.ok(Math.abs(bank.roi - 66.6666667) < 0.000001);
});
test('invalid numerical inputs cannot poison the account', () => {
  for(const value of ['-1','0','NaN','Infinity','1e6','0.001','1000001']) assert.throws(()=>moneyInput(value));
  for(const value of ['0','1','NaN','Infinity','1001','2.1234']) assert.throws(()=>decimalOdds(value));
  assert.throws(()=>payout(10000,2000,'invalid','H'));
});
test('backup validation rejects duplicate records and impossible balances', () => {
  const bet = {id:'a',home:'Arsenal',away:'Chelsea',date:'2026-11-01',source:'test',stake:10000,oddsMilli:2100,selection:'H',result:null};
  assert.equal(validateStore({version:1,odds:[],bets:[bet]}).bets.length,1);
  assert.throws(()=>validateStore({version:1,odds:[],bets:[bet,bet]}));
  assert.throws(()=>validateStore({version:1,odds:[],bets:[{...bet,stake:2000000}]}));
  assert.throws(()=>validateStore({version:2,odds:[],bets:[]}));
});
test('calendar dates cannot roll into another month during backup import', () => {
  assert.equal(validDate('2024-02-29'), true);
  for (const date of ['2026-02-29', '2026-02-30', '2026-04-31', '2026-13-01', '2026-00-10', '2026-1-01', '', null]) assert.equal(validDate(date), false);
  const row = {id:'a', home:'Arsenal', away:'Chelsea', date:'2026-02-30', source:'test', H:2.1, D:3.2, A:4};
  assert.throws(()=>validateStore({version:1,odds:[row],bets:[]}));
  assert.throws(()=>validateStore({version:1,odds:[{...row,date:'2026-02-28',away:' arsenal '}],bets:[]}));
});
