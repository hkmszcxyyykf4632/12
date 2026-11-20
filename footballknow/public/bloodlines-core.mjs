export const pedigreeKey=name=>String(name||'').normalize('NFKC').replace(/[’‘]/g,"'").replace(/\s*\((?:AUS|NZ|IRE|GB|USA|FR|JPN|CAN)\)\s*$/i,'').replace(/\./g,'').replace(/\s+/g,' ').trim().toLowerCase();
export function ancestorPath(start,ancestor,edges){
  const index=new Map();
  for(const edge of edges){const key=pedigreeKey(edge.name),old=index.get(key);if(old&&pedigreeKey(old.sire)!==pedigreeKey(edge.sire))index.set(key,null);else if(old!==null)index.set(key,edge);}
  const seen=new Set(),path=[];let current=start;
  while(current&&path.length<16){
    const key=pedigreeKey(current);if(seen.has(key))return null;seen.add(key);
    if(key===pedigreeKey(ancestor))return [...path,{name:current}];
    const edge=index.get(key);if(!edge||!/^https:\/\//.test(edge.source))return null;
    path.push({name:current,source:edge.source});current=edge.sire;
  }
  return null;
}
export function horseBranches(horse,family,edges){
  if(!horse?.pedigree)return [];
  return ['sire','damsire'].flatMap(branch=>{
    const path=ancestorPath(horse.pedigree[branch],family.ancestor,edges);
    return path?[{branch,path,horse}]:[];
  });
}
export function familyHorses(directory,family,edges,branch='sire',query=''){
  const seen=new Set(),q=pedigreeKey(query);
  return (directory.horses||[]).filter(h=>{if(!h.id||seen.has(h.id)||h.retired===true)return false;seen.add(h.id);return true;})
    .map(h=>({horse:h,branches:horseBranches(h,family,edges).filter(b=>branch==='all'||b.branch===branch)}))
    .filter(r=>r.branches.length&&(!q||pedigreeKey([r.horse.name,r.horse.brand,r.horse.owner,r.horse.trainer?.name,...r.branches.flatMap(b=>b.path.map(p=>p.name))].join(' ')).includes(q)))
    .sort((a,b)=>(b.horse.rating??-1)-(a.horse.rating??-1)||a.horse.id.localeCompare(b.horse.id));
}
