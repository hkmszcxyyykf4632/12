export const INITIAL_BALANCE = 1000000;
export const OUTCOMES = { H: '主胜', D: '平局', A: '客胜', V: '作废' };
export function validDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(value + 'T00:00:00.000Z');
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}
export function moneyInput(value) {
  const text = String(value).trim();
  if (!/^\d+(\.\d{1,2})?$/.test(text)) throw new Error('金额须为正数，最多两位小数。');
  const cents = Math.round(Number(text) * 100);
  if (!Number.isSafeInteger(cents) || cents <= 0 || cents > 100000000) throw new Error('金额须大于 0 且不超过 1,000,000。');
  return cents;
}
export function decimalOdds(value) {
  const text = String(value).trim();
  const number = Number(text);
  if (!/^\d+(\.\d{1,3})?$/.test(text) || !Number.isFinite(number) || number <= 1 || number > 1000) {
    throw new Error('十进制赔率须大于 1、至多 1000，最多三位小数。');
  }
  return Math.round(number * 1000);
}
export function payout(stake, oddsMilli, selection, result) {
  if (!Number.isSafeInteger(stake) || stake <= 0 || !Number.isSafeInteger(oddsMilli) || oddsMilli <= 1000 || oddsMilli > 1000000 || !['H', 'D', 'A'].includes(selection)) throw new Error('投注数据无效。');
  if (result == null) return null;
  if (!['H', 'D', 'A', 'V'].includes(result)) throw new Error('赛果无效。');
  return result === 'V' ? stake : selection === result ? Math.round(stake * oddsMilli / 1000) : 0;
}
export function summary(bets) {
  let balance = INITIAL_BALANCE, profit = 0, settledStake = 0, wins = 0, settled = 0, pending = 0;
  for (const bet of bets) {
    const returned = payout(bet.stake, bet.oddsMilli, bet.selection, bet.result);
    balance -= bet.stake;
    if (returned == null) pending += bet.stake;
    else {
      balance += returned;
      profit += returned - bet.stake;
      if (bet.result !== 'V') { settled++; settledStake += bet.stake; if (returned > 0) wins++; }
    }
  }
  return { balance, profit, settledStake, wins, settled, pending, roi: settledStake ? profit / settledStake * 100 : 0 };
}
export function validateStore(value) {
  if (!value || value.version !== 1 || !Array.isArray(value.odds) || !Array.isArray(value.bets) || value.odds.length > 10000 || value.bets.length > 10000) throw new Error('备份格式不正确。');
  const text = (v, max = 150) => typeof v === 'string' && v.length > 0 && v.length <= max;
  const ids = new Set();
  for (const row of [...value.odds, ...value.bets]) {
    if (!text(row.id) || ids.has(row.id) || !text(row.home) || !text(row.away) || row.home.trim().toLowerCase() === row.away.trim().toLowerCase() || !validDate(row.date) || !text(row.source, 200) || (row.matchId != null && !text(row.matchId, 350))) throw new Error('备份包含无效记录。');
    ids.add(row.id);
    if (row.result != null && !['H', 'D', 'A', 'V'].includes(row.result)) throw new Error('备份赛果无效。');
  }
  for (const row of value.odds) {
    for (const key of ['H', 'D', 'A']) decimalOdds(row[key]);
  }
  for (const bet of value.bets) {
    if (bet.stake > 100000000) throw new Error('备份金额超出范围。');
    payout(bet.stake, bet.oddsMilli, bet.selection, bet.result);
  }
  if (summary(value.bets).balance < 0) throw new Error('备份余额无效。');
  return value;
}
