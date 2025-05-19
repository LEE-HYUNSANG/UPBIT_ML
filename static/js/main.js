// static/js/main.js
// 전체 페이지에서 공통으로 쓰는 JS (알림, 모달, API 연동, SocketIO 등)

// 1. Bootstrap 알림 모달 표시 함수
// 모달 인스턴스를 한 번만 생성해 중복 백드롭이 생기지 않도록 한다.
const alertModalEl = document.getElementById('alertModal');
const alertModal = new bootstrap.Modal(alertModalEl);

// Confirm modal
const confirmModalEl = document.getElementById('confirmModal');
const confirmModal = confirmModalEl ? new bootstrap.Modal(confirmModalEl) : null;

function showConfirm(message){
  return new Promise(resolve=>{
    if(!confirmModal) return resolve(window.confirm(message));
    confirmModalEl.querySelector('.modal-body').innerText = message;
    const okBtn = confirmModalEl.querySelector('[data-action="ok"]');
    const cancelBtn = confirmModalEl.querySelector('[data-action="cancel"]');
    function cleanup(){
      okBtn.removeEventListener('click', ok);
      cancelBtn.removeEventListener('click', cancel);
    }
    function ok(){ cleanup(); confirmModal.hide(); resolve(true); }
    function cancel(){ cleanup(); confirmModal.hide(); resolve(false); }
    okBtn.addEventListener('click', ok);
    cancelBtn.addEventListener('click', cancel);
    confirmModal.show();
  });
}

function showAlert(message, title = "알림") {
  document.querySelector('#alertModal .modal-title').innerText = title;
  document.querySelector('#alertModal .modal-body').innerText = message;
  alertModal.show();
}

// 2. 모든 버튼에 AJAX로 진행 시 로딩 커서 표시
document.querySelectorAll('button, .btn').forEach(btn => {
  btn.addEventListener('click', function() {
    document.body.style.cursor = 'wait';
    setTimeout(() => { document.body.style.cursor = ''; }, 800);
  });
  if(btn.dataset.api){
    btn.addEventListener('click', async function(){
      const form = btn.closest('form');
      const data = form ? Object.fromEntries(new FormData(form)) : null;
      await callApi(btn.dataset.api, data);
    });
  }
});

// 3. Flask API 호출 (예시: 봇 시작/정지/설정 저장 등)
async function callApi(url, data, method="POST") {
  try {
    const resp = await fetch(url, {
      method,
      headers: {'Content-Type':'application/json'},
      body: data ? JSON.stringify(data) : undefined
    });
    const result = await resp.json();
    if(result.message) showAlert(result.message);
    return result;
  } catch (err) {
    showAlert("서버 연결 오류. 네트워크 또는 서버를 확인해 주세요.", "에러");
    return null;
  }
}

// 4. SocketIO 실시간 알림 (옵션)
let socket;
if(window.io){
  socket = io();
  socket.on('notification', function(data){
    if(data.message) showAlert(data.message, "실시간 알림");
    const box = document.getElementById('liveAlerts');
    if(box){
      const div = document.createElement('div');
      div.textContent = data.message;
      box.prepend(div);
    }
    const list = document.getElementById('alertList');
    if(list){
      const div = document.createElement('div');
      div.textContent = data.message;
      list.prepend(div);
    }
  });

  socket.on('positions', data => updatePositions(data));
  socket.on('alerts', data => updateAlerts(data));
}

// 5. Tooltip 자동 활성화 (Bootstrap 5)
document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el=>{
  new bootstrap.Tooltip(el);
});

// 6. 기본 콘솔 안내
console.log("main.js loaded - UPBIT AutoTrading 공통 JS");

// 7. data-api 버튼 클릭 시 폼 데이터 전송
document.addEventListener('click', async e => {
  const btn = e.target.closest('[data-api]');
  if(!btn) return;
  e.preventDefault();
  if(btn.dataset.confirm){
    const ok = await showConfirm(btn.dataset.confirm);
    if(!ok) return;
  }
  const form = btn.closest('form');
  let data = {};
  if(form){
    data = Object.fromEntries(new FormData(form).entries());
  }
  // merge dataset values except 'api'
  Object.entries(btn.dataset).forEach(([k,v])=>{ if(k!=='api') data[k]=v; });
  const result = await callApi(btn.dataset.api, data);
  if(['/save','/api/save-settings'].includes(btn.dataset.api) && result && result.result === 'success'){
    await loadStatus();
  }
});

// 8. data-alert 속성 클릭 시 알림 표시
document.addEventListener('click', e => {
  const el = e.target.closest('[data-alert]');
  if(el){
    showAlert(el.dataset.alert);
  }
});

// 9. 레이아웃 드래그 분할 초기화
function initDragLayout(){
  const drag = document.getElementById('drag');
  const left = document.getElementById('left');
  if(!drag || !left) return;
  let sx=0, sw=0;
  drag.addEventListener('mousedown', e=>{
    sx = e.clientX; sw = left.offsetWidth;
    document.addEventListener('mousemove', mv);
    document.addEventListener('mouseup', up);
  });
  function mv(e){
    const w = sw + (e.clientX - sx);
    const min=260, max=window.innerWidth*0.45;
    if(w>min && w<max) left.style.width = w+'px';
  }
  function up(){
    document.removeEventListener('mousemove', mv);
    document.removeEventListener('mouseup', up);
  }
}
document.addEventListener('DOMContentLoaded', initDragLayout);

// 10. 포지션/알림 실시간 갱신
function initDotPositions(){
  document.querySelectorAll('.dot[data-pos]').forEach(el=>{
    el.style.left = el.dataset.pos + '%';
  });
}

function updatePositions(list){
  const body = document.getElementById('positionBody');
  if(!body) return;
  body.innerHTML = list.map((p, i) => `
    <tr>
      <td>${i+1}</td><td>${p.coin}</td>
      <td>
        <div class="bar-graph">
          <span class="dot stop"></span>
          <span class="dot entry" data-pos="${p.entry}"></span>
          <span class="dot take"></span>
        </div>
      </td>
      <td>
        <div class="trend-bar">
          <span class="tick tick1"></span>
          <span class="tick tick2"></span>
          <span class="dot trend ${p.trend_color}" data-pos="${p.trend}"></span>
        </div>
      </td>
      <td><span class="badge badge-${p.signal}">${p.signal_label}</span></td>
      <td><button class="btn btn-sm btn-outline-danger" data-api="/api/manual-sell" data-confirm="시장가로 매도 요청을 하시겠습니까?" data-coin="${p.coin}">수동 매도</button></td>
    </tr>
  `).join('');
  initDotPositions();
}

function updateAlerts(list){
  const box = document.getElementById('liveAlerts');
  const listBox = document.getElementById('alertList');
  if(box){
    if(list.length){
      box.innerHTML = list.map(a => `<div>[${a.time}] ${a.message}</div>`).join('');
    } else {
      box.innerHTML = '<div class="text-muted">실시간 알림 대기중......</div>';
    }
  }
  if(listBox){
    listBox.innerHTML = box.innerHTML;
  }
}

document.addEventListener('DOMContentLoaded', initDotPositions);

// refresh buttons
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-refresh]');
  if(!btn) return;
  const type = btn.dataset.refresh;
  if(type === 'balances'){
    reloadBalance();
  } else if(type === 'signals'){
    reloadBuyMonitor();
  } else if(socket){
    socket.emit('refresh', {type});
  }
});

// 잔고 테이블 실시간 갱신
async function reloadBalance(){
  try {
    const resp = await fetch('/api/balances');
    const data = await resp.json();
    if(data.result === 'success' && data.balances){
      updateBalanceTable(data.balances);
    } else if(data.message){
      showAlert(data.message, '에러');
    }
  } catch(err){
    showAlert('서버 연결 오류. 네트워크 또는 서버를 확인해 주세요.', '에러');
  }
}

function updateBalanceTable(list){
  const body = document.getElementById('positionBody');
  if(!body) return;
  body.innerHTML = list.map(p => `
    <tr>
      <td>${p.coin}</td>
      <td>${p.pnl} %</td>
      <td>
        <div class="bar-graph">
          <span class="dot stop"></span>
          <span class="dot entry" data-pos="${p.entry}"></span>
          <span class="dot take"></span>
        </div>
      </td>
      <td>
        <div class="trend-bar">
          <span class="tick tick1"></span>
          <span class="tick tick2"></span>
          <span class="dot trend ${p.trend_color}" data-pos="${p.trend}"></span>
        </div>
      </td>
      <td><span class="badge badge-${p.signal}">${p.signal_label}</span></td>
      <td><button class="btn btn-sm btn-outline-danger" data-api="/api/manual-sell" data-confirm="시장가로 매도 요청을 하시겠습니까?" data-coin="${p.coin}">수동 매도</button></td>
    </tr>
  `).join('');
  initDotPositions();
}

// 매수 모니터링 테이블 갱신
async function reloadBuyMonitor(){
  try {
    const resp = await fetch('/api/signals');
    const data = await resp.json();
    if(data.result === 'success' && data.signals){
      updateSignalTable(data.signals);
    } else if(data.message){
      showAlert(data.message, '에러');
    }
  } catch(err){
    showAlert('서버 연결 오류. 네트워크 또는 서버를 확인해 주세요.', '에러');
  }
}

function updateSignalTable(list){
  const body = document.getElementById('signalBody');
  if(!body) return;
  body.innerHTML = list.map((s, i) => `
    <tr>
      <td>${i+1}</td><td>${s.coin}</td>
      <td class="icon-cell">${s.trend}</td>
      <td class="icon-cell">${s.volatility}</td>
      <td class="icon-cell">${s.volume}</td>
      <td class="icon-cell">${s.strength}</td>
      <td class="icon-cell">${s.gc}</td>
      <td class="icon-cell">${s.rsi}</td>
      <td><span class="badge badge-${s.signal_class}">${s.signal}</span></td>
      <td><button class="btn btn-sm btn-outline-success" data-api="/api/manual-buy" data-coin="${s.coin}">수동 매수</button></td>
    </tr>
  `).join('');
}

// 서버 상태 조회 후 화면 갱신
async function loadStatus(){
  try {
    const resp = await fetch('/api/status');
    const data = await resp.json();
    if(data.result === 'success' && data.status){
      const el = document.getElementById('bot-status');
      const timeEl = document.getElementById('updateTime');
      if(el){
        el.textContent = data.status.running ? '실행중' : '정지';
      }
      if(timeEl){
        timeEl.textContent = '업데이트: ' + data.status.updated;
      }
    } else if(data.message){
      showAlert(data.message, '에러');
    }
  } catch(err){
    showAlert('서버 연결 오류. 네트워크 또는 서버를 확인해 주세요.', '에러');
  }
}

function formatNumber(val){
  const num = parseFloat(val);
  if(isNaN(num)) return val;
  return num.toLocaleString();
}

async function reloadAccount(){
  try {
    const resp = await fetch('/api/account');
    const data = await resp.json();
    if(data.result === 'success' && data.account){
      const c = document.getElementById('accountCash');
      const t = document.getElementById('accountTotal');
      const p = document.getElementById('accountPnl');
      if(c) c.textContent = formatNumber(data.account.cash) + ' 원';
      if(t) t.textContent = formatNumber(data.account.total) + ' 원';
      if(p) p.textContent = data.account.pnl + ' %';
    }
  } catch(err){
    console.error(err);
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  setInterval(reloadAccount, 10000);
  setInterval(reloadBalance, 5000);
  reloadAccount();
  reloadBalance();
});
