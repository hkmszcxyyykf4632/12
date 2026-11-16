import {validateStore} from './core.mjs';
export const STORAGE_KEY = 'footballknow.personal.v1';
const freshStore = () => ({version:1,odds:[],bets:[]});
export let store = freshStore(), storeProblem = '';
export function loadStore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? validateStore(JSON.parse(raw)) : freshStore();
  } catch {
    storeProblem = '无法读取本浏览器的个人记录。原内容未覆盖；请先导出备份或检查浏览器存储设置。';
    return freshStore();
  }
}
store = loadStore();
export function commit(next) {
  if (storeProblem) throw new Error(storeProblem);
  validateStore(next);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  store = next;
}
export function latestStore() {
  const latest = loadStore();
  if (storeProblem) throw new Error(storeProblem);
  return latest;
}

export function reloadStore() { storeProblem='';store=loadStore();return store; }
export function reconcile(matches) {
  if(storeProblem)return false;
  const next=latestStore();let changed=false;
  for(const bet of next.bets) {
    if(bet.result || !bet.matchId)continue;
    const candidates=matches.filter(m=>m.id===bet.matchId || m.aliases?.includes(bet.matchId));
    if(candidates.length===1 && candidates[0].finished && ['H','D','A'].includes(candidates[0].result)) {
      bet.result=candidates[0].result;bet.resultSource='公开赛果结算';changed=true;
    }
  }
  if(changed)commit(next);return changed;
}
