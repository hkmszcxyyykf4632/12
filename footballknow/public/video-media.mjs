const siteHosts=new Set(['inwesting.shop','www.inwesting.shop','footballknow.art','www.footballknow.art']);

export function videoDownloadUrl(value, pageUrl){
  try{
    const page=new URL(pageUrl),media=new URL(value,page);
    if(media.origin!==page.origin&&!(siteHosts.has(media.hostname)&&siteHosts.has(page.hostname)&&media.protocol==='https:'))return '';
    if(!/^\/media\/videos\/[^/\\]+\.(mp4|webm)$/i.test(media.pathname))return '';
    return media.pathname+'?download=1';
  }catch{return '';}
}

export function videoSourceUrl(value,pageUrl){
  try{
    const page=new URL(pageUrl),media=new URL(value,page);
    if(siteHosts.has(media.hostname)&&siteHosts.has(page.hostname)&&media.protocol==='https:'&&/^\/media\/videos\/[^/\\]+\.(mp4|webm|jpg|jpeg|png|webp)$/i.test(media.pathname))return media.pathname+media.search;
  }catch{}
  return value;
}
