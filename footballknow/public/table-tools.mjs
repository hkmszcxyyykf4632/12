// Column sorting and CSV export for every data table, applied after each render and each 60-second refresh.
const sortState=new Map();

const cellValue=cell=>{
  const text=(cell?.textContent||'').trim();
  const number=Number(text.replace(/[,%+\s]/g,'').replace(/^—$/,''));
  return text!==''&&text!=='—'&&Number.isFinite(number)&&/^[-+\d.,%\s]+$/.test(text)?number:text;
};

function applySort(table,{column,direction}) {
  const body=table.tBodies[0];if(!body)return;
  const rows=[...body.rows].map((row,index)=>({row,index,value:cellValue(row.cells[column])}));
  rows.sort((a,b)=>{
    const order=typeof a.value==='number'&&typeof b.value==='number'?a.value-b.value:String(a.value).localeCompare(String(b.value),'zh');
    return (direction==='ascending'?order:-order)||a.index-b.index;
  });
  rows.forEach(item=>body.append(item.row));
  [...(table.tHead?.rows[0]?.cells||[])].forEach((th,index)=>index===column?th.setAttribute('aria-sort',direction):th.removeAttribute('aria-sort'));
}

export function enhanceTables(root,routeKey) {
  root.querySelectorAll('.table-wrap').forEach((wrap,index)=>{
    const table=wrap.querySelector('table');
    if(!table?.tHead||!table.tBodies[0])return;
    const key=`${routeKey}|${index}`;
    if(!wrap.dataset.tableKey) {
      wrap.dataset.tableKey=key;
      const tools=document.createElement('div');
      tools.className='table-tools';
      tools.innerHTML='<button type="button" class="button quiet compact" data-export-csv>导出 CSV</button>';
      wrap.after(tools);
    }
    const state=sortState.get(wrap.dataset.tableKey);
    if(state)applySort(table,state);
  });
}

export function toCsv(table) {
  const quote=value=>`"${String(value).replace(/\s+/g,' ').trim().replaceAll('"','""')}"`;
  return [...table.rows].filter(row=>!row.classList.contains('hidden')).map(row=>[...row.cells].map(cell=>quote(cell.textContent)).join(',')).join('\r\n');
}

export function bindTableTools(routeName) {
  document.addEventListener('click',event=>{
    const exportButton=event.target.closest?.('[data-export-csv]');
    if(exportButton) {
      const table=exportButton.closest('.table-tools')?.previousElementSibling?.querySelector('table');
      if(!table)return;
      // The byte-order mark lets spreadsheet programs read the Chinese text correctly.
      const url=URL.createObjectURL(new Blob(['﻿'+toCsv(table)],{type:'text/csv;charset=utf-8'}));
      const link=document.createElement('a');
      link.href=url;link.download=`FootballKnow-${routeName()}-${new Date().toISOString().slice(0,10)}.csv`;link.click();
      setTimeout(()=>URL.revokeObjectURL(url),5000);
      return;
    }
    const heading=event.target.closest?.('thead th');
    const wrap=heading?.closest('.table-wrap');
    if(!heading||!wrap?.dataset.tableKey||event.target.closest('a,button,input,select'))return;
    const direction=heading.getAttribute('aria-sort')==='descending'?'ascending':'descending';
    const state={column:heading.cellIndex,direction};
    sortState.set(wrap.dataset.tableKey,state);
    applySort(wrap.querySelector('table'),state);
  });
}
