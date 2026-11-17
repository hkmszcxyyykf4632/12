import {esc} from './ui.mjs';

export function portrait(photo,name,kind='person',large=false){
  const raw=typeof photo==='string'?photo:photo?.url;
  let url='';
  try{const parsed=new URL(raw);if(parsed.protocol==='https:'||parsed.origin===location.origin)url=parsed.href;}catch{}
  return `<span class="portrait portrait-${kind}${large?' portrait-large':''}${url?'':' is-missing'}"><span class="portrait-fallback" aria-label="暂无${esc(name)}照片">${kind==='horse'?'马匹':String(name||'').slice(0,1)||'—'}</span>${url?`<img src="${esc(url)}" alt="${esc(name)}${kind==='horse'?'的照片':'头像'}" loading="lazy" decoding="async" data-portrait>`:''}</span>`;
}

export function bindPortraits(root){
  const failed=event=>{const img=event.target;if(img?.matches?.('img[data-portrait]')){img.parentElement.classList.add('is-missing');img.remove();}};
  root.addEventListener('error',failed,true);
  return()=>root.removeEventListener('error',failed,true);
}

export function playerPhoto(player,leagueId){
  if(player?.photoUrl)return player.photoUrl;
  if(leagueId==='epl'&&/^\d+$/.test(String(player?.code)))return `https://resources.premierleague.com/premierleague/photos/players/250x250/p${player.code}.png`;
  return player?.headshot?.href||null;
}

export function playerPortrait(player,leagueId,large=false){
  const name=player.known_name||player.web_name;
  return `<span class="player-portrait" data-player-portrait="${esc(player.code)}" data-player-name="${esc(name)}" data-large="${large}" data-has-photo="${Boolean(playerPhoto(player,leagueId))}">${portrait(playerPhoto(player,leagueId),name,'player',large)}</span>`;
}

const playerPhotos=new Map();
export async function hydratePlayerPortraits(root,leagueId){
  const nodes=[...root.querySelectorAll('[data-player-portrait][data-has-photo="false"]:not([data-photo-checked])')];
  if(!nodes.length)return;
  nodes.forEach(n=>n.setAttribute('data-photo-checked','true'));
  const folder=leagueId==='epl'?'':leagueId+'/';
  if(!playerPhotos.has(leagueId))playerPhotos.set(leagueId,fetch('./'+folder+'photos.json',{cache:'no-cache'}).then(r=>r.ok?r.json():{}).catch(()=>({})));
  const data=await playerPhotos.get(leagueId);
  for(const node of nodes){if(!node.isConnected)continue;const p=data.photos?.[node.dataset.playerPortrait];if(!p)continue;
    const large=node.dataset.large==='true';node.innerHTML=portrait(p,node.dataset.playerName,'player',large)+(large?`<small class="photo-credit"><a href="${esc(p.source)}" target="_blank" rel="noopener noreferrer">照片：${esc(p.author||'Wikimedia Commons')} · ${esc(p.license)}</a></small>`:'');}
}
