export function prepareStockTables(root){
 for(const table of root.querySelectorAll('.table-wrap table')){
  if(table.dataset.quoteLayout)continue;
  const headers=[...(table.tHead?.rows[0]?.cells||[])],names=headers.map(c=>c.textContent.trim());
  const name=names.findIndex(s=>/^(股票|公司)$/.test(s)),price=names.findIndex(s=>/^(价格|美元价格|报价 \/ 币种|现价 \/ 币种)$/.test(s)),change=names.indexOf('涨跌幅');
  if(name<0||price<0||change<0)continue;
  const order=[name,price,change,...headers.map((_,i)=>i).filter(i=>![name,price,change].includes(i))];
  if([...table.rows].some(r=>r.cells.length!==headers.length))continue;
  for(const row of table.rows){const cells=[...row.cells];for(const i of order)row.append(cells[i]);}
  table.dataset.quoteLayout='true';const wrap=table.closest('.table-wrap');wrap.classList.add('stock-quote-table');
  const label=table.ownerDocument.createElement('label');label.className='stock-details-toggle';
  const input=table.ownerDocument.createElement('input');input.type='checkbox';input.addEventListener('change',()=>wrap.classList.toggle('show-stock-details',input.checked));
  label.append(input,' 显示行业、关注与更多资料');wrap.before(label);
 }
}
