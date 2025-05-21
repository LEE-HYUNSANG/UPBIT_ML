// static/js/dashboard.js
// 대시보드 실시간 로그 테이블 관리

let logList = [];

function updateLogTable(list){
  const body = document.getElementById('logBody');
  if(!body) return;
  if(!list.length){
    body.innerHTML = '<tr><td colspan="6" class="text-muted py-3">없음</td></tr>';
    return;
  }
  body.innerHTML = list.map(l => `
    <tr>
      <td>${l.time}</td>
      <td>${l.type}</td>
      <td>${l.action || ''}</td>
      <td>${l.coin || ''}</td>
      <td>${l.price !== undefined ? formatNumber(l.price) : ''}</td>
      <td>${l.amount !== undefined ? formatNumber(l.amount) : ''}</td>
    </tr>
  `).join('');
}

async function loadLogs(){
  try{
    const data = await fetchJsonRetry('/api/logs');
    if(data && data.result === 'success'){
      logList = data.logs;
      updateLogTable(logList);
    }
  }catch(err){
    console.error('loadLogs failed', err);
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  loadLogs();
  if(window.io){
    const sock = io();
    sock.on('log', log => {
      logList.unshift(log);
      logList = logList.slice(0,20);
      updateLogTable(logList);
    });
  }
});

