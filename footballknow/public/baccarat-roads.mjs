export function placeRoad(items){
 const cells=[],occupied=new Set();let col=0,row=0,base=0,turned=false,previous=null;
 for(const item of items){
  if(previous!==null&&item.color!==previous){base++;col=base;row=0;turned=false;while(occupied.has(col+':0')){base++;col=base;}}
  else if(previous!==null){if(!turned&&row<5&&!occupied.has(col+':'+(row+1)))row++;else{turned=true;col++;while(occupied.has(col+':'+row))col++;}}
  occupied.add(col+':'+row);cells.push({...item,col,row});previous=item.color;
 }
 return cells;
}
export function bigRoad(hands){
 const runs=[],items=[];let initialTies=0;
 for(const h of hands){
  if(h.result==='T'){if(items.length)items.at(-1).ties++;else initialTies++;continue;}
  const item={color:h.result==='B'?'red':'blue',result:h.result,hand:h.number,ties:items.length?0:initialTies,bankerPair:h.bankerPair,playerPair:h.playerPair,lucky6:h.lucky6,lucky7:h.lucky7};
  items.push(item);if(!runs.length||runs.at(-1)[0].result!==h.result)runs.push([]);runs.at(-1).push(item);
 }
 return {cells:placeRoad(items),runs,initialTies:items.length?0:initialTies};
}
export function derivedRoad(hands,offset){
 if(![1,2,3].includes(offset))throw Error('下三路间距无效');
 const {runs}=bigRoad(hands),items=[];
 for(let col=0;col<runs.length;col++)for(let row=0;row<runs[col].length;row++){
  let color=null;
  if(row===0&&col>offset)color=runs[col-1].length===runs[col-1-offset].length?'red':'blue';
  else if(row>0&&col>=offset)color=row===runs[col-offset].length?'blue':'red';
  if(color)items.push({color,hand:runs[col][row].hand});
 }
 return placeRoad(items);
}
export function roadProbe(hands,result){
 return [1,2,3].map(offset=>{const before=derivedRoad(hands,offset),after=derivedRoad([...hands,{number:hands.length+1,result}],offset);return after.length>before.length?after.at(-1).color:null;});
}
