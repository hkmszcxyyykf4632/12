// Parent relationships are deliberately curated; each chain has a stud or registry source.
export const checkedAt='2026-11-20';
export const families=[
 {id:'danehill',name:'丹山',ancestor:'Danehill',intro:'丹山是研究现代澳洲及欧洲纯血马血统的重要起点。其父系分支包括 Fastnet Rock、Exceed And Excel，以及经 Danehill Dancer、Choisir 延伸的 Starspangledbanner。香港马匹常通过这些后代与丹山相连，并非都是丹山的直接子嗣。',focus:'先看本马属于哪一条分支，再比较它本身的场地、途程、班次及近期走位；不能仅凭“丹山系”判断短途能力或湿地表现。',source:'https://coolmore.com/assets/docs/pedigree/Fastnet-Rock-Pedigree.pdf'},
 {id:'sadlers-wells',name:'鞍匠井',ancestor:"Sadler's Wells",intro:'鞍匠井经 High Chaparral 等后代延续父系影响。香港常见的 Toronado，以及 Dundeel、Super Seth，可以沿已核对的父系关系追溯到这一支。Toronado 自身曾在一哩一级赛取胜，其后代的胜出途程也并不局限于单一距离。',focus:'研究这一支时，可先比较同场同程往绩与末段走位，再看增加或缩短途程后的实际表现。父系背景只能提供研究方向。',source:'https://swettenham.com.au/stallions/toronado/'},
 {id:'mr-prospector',name:'淘金者',ancestor:'Mr Prospector',intro:'淘金者的父系分支很多。本页已核对 Machiavellian、Street Cry 一支，继而连接 Street Boss 和 Per Incanto。两匹马即使都能追溯至淘金者，也可能相隔多个世代，父亲和母系配搭仍然不同。',focus:'把具体父亲与本马的实绩结合看，特别是相同场地、途程与班次的样本，不把远祖名称直接当成速度评分。',source:'https://www.darley.com.au/stallions/our-stallions/street-boss?page=2'},
 {id:'storm-cat',name:'暴风猫',ancestor:'Storm Cat',intro:'暴风猫经 Giant’s Causeway、Shamardal 等后代形成多条支线。Lope de Vega 是 Shamardal 的儿子；本页会把这些代际关系展开，让读者区分直接同父与较远的同系。',focus:'结合本马近况、早段取位与末段追赶能力判断；祖先的竞赛风格不会自动成为每匹后代的固定跑法。',source:'https://www.darley.com.au/news/shamardal-succession-0'},
 {id:'zabeel',name:'沙彪',ancestor:'Zabeel',intro:'沙彪曾是澳洲和新西兰冠军种马，其后代包括 Savabeel 和 Octagonal。Octagonal 又是 Lonhro 的父亲。这些分支在澳纽赛马与育种中有持续影响，也能从香港在册马匹的父系或母父资料中查到联系。',focus:'长途背景需要用本马的实际途程纪录验证；同时查看休赛天数、负磅和沿途走位，不把血统当作耐力保证。',source:'https://waikatostud.com/stallions/savabeel/'},
 {id:'northern-dancer',name:'北地舞人',ancestor:'Northern Dancer',intro:'北地舞人是更上游的父系祖先。丹山可经 Danzig 追溯至北地舞人，鞍匠井也是其儿子；Deep Field 则经 Northern Meteor、Encosta de Lago、Fairy King 连接到这一祖先。因此，本页多个血系可以重叠。',focus:'越远的共同祖先，越不能直接说明两匹马表现相近。先从最近的父亲和母父研究，再参考较远的血缘关系。',source:'https://www.newgate.com.au/wp-content/uploads/2020/09/Deep-Field-Pedigree-1.pdf'}
];
const chains=[
 [['Fastnet Rock','Danehill','Danzig','Northern Dancer'],'https://coolmore.com/assets/docs/pedigree/Fastnet-Rock-Pedigree.pdf'],
 [['Bivouac','Exceed And Excel','Danehill'],'https://www.darley.com.au/ja/node/32064'],
 [['Starspangledbanner','Choisir','Danehill Dancer','Danehill'],'https://coolmore.com/assets/docs/pedigree/Starspangledbanner-Pedigree.pdf'],
 [['The Autumn Sun',"Redoute's Choice",'Danehill'],'https://www.magicmillions.com.au/wp-content/uploads/2025/05/26GPR_PDFCatalogue.pdf'],
 [['Snitzel',"Redoute's Choice"],'https://arrowfield.com.au/stallions/snitzel/'],
 [['Toronado','High Chaparral',"Sadler's Wells",'Northern Dancer'],'https://swettenham.com.au/stallions/toronado/'],
 [['Dundeel','High Chaparral'],'https://arrowfield.com.au/stallions/dundeel/'],
 [['Super Seth','Dundeel'],'https://coolmore.com/en/australia/stallions/'],
 [['Per Incanto','Street Cry'],'https://littleavondale.co.nz/stallions/per-incanto/about-per-incanto'],
 [['Street Boss','Street Cry','Machiavellian','Mr Prospector'],'https://www.darley.com.au/stallions/our-stallions/street-boss?page=2'],
 [['Lope de Vega','Shamardal'],'https://www.ballylinchstud.ie/stallions/LOPE-DE-VEGA/'],
 [['Shamardal',"Giant's Causeway",'Storm Cat'],'https://www.darley.com.au/news/shamardal-succession-0'],
 [['Storm Cat','Storm Bird','Northern Dancer'],'https://www.jbis.jp/horse/0000858233/pedigree/'],
 [['Savabeel','Zabeel'],'https://waikatostud.com/stallions/savabeel/'],
 [['Lonhro','Octagonal','Zabeel'],'https://www.darley.com.au/news/feature-blog/news-lonhro-true-champion-track-and-stud'],
 [['Pierro','Lonhro'],'https://coolmore.com/en/australia/stallions/'],
 [['Deep Field','Northern Meteor','Encosta de Lago','Fairy King','Northern Dancer'],'https://www.newgate.com.au/wp-content/uploads/2020/09/Deep-Field-Pedigree-1.pdf']
];
export const ancestry=chains.flatMap(([names,source])=>names.slice(0,-1).map((name,i)=>({name,sire:names[i+1],source})));
