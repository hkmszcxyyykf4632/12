import {playerValues} from './repository.mjs';
import {esc,dateText,sourceLink} from './ui.mjs';

export function valuationHtml(player,compact=false){
  const value=playerValues?.values?.[String(player.code)];
  if(!value||value.birthDate!==player.birth_date||value.currency!=='EUR'||!Number.isFinite(value.amount)||value.amount<=0)return '<span class="subtle">暂未收录</span>';
  const amount=value.amount>=1e8?(value.amount/1e8).toFixed(2)+' 亿欧元':(value.amount/1e4).toLocaleString('zh-CN',{maximumFractionDigits:0})+' 万欧元';
  return `<strong>${esc(amount)}</strong><small>${sourceLink(value.sourceUrl,'FotMob 估值')}${compact?'':' · '+esc(value.team||'')}</small><small>采集 ${dateText(value.fetchedAt)}</small>`;
}
