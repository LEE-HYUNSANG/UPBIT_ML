// static/js/main.js
// 전체 페이지에서 공통으로 쓰는 JS (알림, 모달, API 연동, SocketIO 등)

// 1. Bootstrap 알림 모달 표시 함수
// 모달 인스턴스를 한 번만 생성해 중복 백드롭이 생기지 않도록 한다.
const alertModalEl = document.getElementById('alertModal');
const alertModal = new bootstrap.Modal(alertModalEl);

// 서버 연결 상태 플래그
let disconnected = false;

function handleDisconnect(code) {
  if (disconnected) return;

  const msg = `서버 연결 오류(${code}). 네트워크 또는 서버를 확인해 주세요.`;
  if (code === 'A002' || code === 'A003') {
    console.debug(`[NET-${code}] ${msg}`);
  } else {
    console.error(`[NET-${code}] disconnect`);
    showAlert(msg, '에러');
  }
  disconnected = true;
}

// Confirm modal
const confirmModalEl = document.getElementById('confirmModal');
const confirmModal = confirmModalEl ? new bootstrap.Modal(confirmModalEl) : null;

function showConfirm(message, okText = '매도 진행', cancelText = '매도 취소'){
  return new Promise(resolve=>{
    if(!confirmModal) return resolve(window.confirm(message));
    confirmModalEl.querySelector('.modal-body').innerText = message;
    const okBtn = confirmModalEl.querySelector('[data-action="ok"]');
    const cancelBtn = confirmModalEl.querySelector('[data-action="cancel"]');
    const origOk = okBtn.innerText;
    const origCancel = cancelBtn.innerText;
    okBtn.innerText = okText;
    cancelBtn.innerText = cancelText;
    function cleanup(){
      okBtn.removeEventListener('click', ok);
      cancelBtn.removeEventListener('click', cancel);
      okBtn.innerText = origOk;
      cancelBtn.innerText = origCancel;
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

async function fetchJsonRetry(url, options = {}, retries = 3, delay = 200) {
  for (let i = 0; i < retries; i++) {
    try {
      const resp = await fetch(url, options);
      return await resp.json();
    } catch (err) {
      if (i < retries - 1) {
        await new Promise(r => setTimeout(r, delay));
      } else {
        throw err;
      }
    }
  }
}

// 2. 모든 버튼에 AJAX로 진행 시 로딩 커서 표시
document.querySelectorAll('button, .btn').forEach(btn => {
  btn.addEventListener('click', function() {
    console.log('[BTN]', this.innerText.trim());
    document.body.style.cursor = 'wait';
    setTimeout(() => { document.body.style.cursor = ''; }, 800);
  });
});

// 3. Flask API 호출 (예시: 봇 시작/정지/설정 저장 등)
async function callApi(url, data, method="POST", code="A000") {
  try {
    const result = await fetchJsonRetry(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: data ? JSON.stringify(data) : undefined
    });
    disconnected = false;
    console.log(`[API-${code}]`, method, url, result);
    if (result && result.message) showAlert(result.message);
    return result;
  } catch (err) {
    handleDisconnect(code);
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
  socket.on('refresh_data', () => {
    for(let i=0;i<3;i++){
      setTimeout(async () => {
        await reloadBalance();
        await reloadBuyMonitor();
        await loadStatus();
      }, i * 1000);
    }
  });
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
  console.log('[BTN-API]', btn.dataset.api);
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
  const code = `API${btn.dataset.api.replace(/[^a-z0-9]/gi,'').toUpperCase()}`;
  const result = await callApi(btn.dataset.api, data, 'POST', code);
  const apiList = ['/save','/api/save-settings','/api/start-bot','/api/stop-bot'];
  if(apiList.includes(btn.dataset.api) && result && result.result === 'success'){
    await loadStatus();
    if(btn.dataset.api !== '/api/start-bot' && btn.dataset.api !== '/api/stop-bot'){
      await reloadBuyMonitor();
    }
  } else if(btn.dataset.api === '/api/exclude-coin' && result && result.result === 'success'){
    await reloadBalance();
  } else if(btn.dataset.api === '/api/restore-coin' && result && result.result === 'success'){
    await reloadBalance();
    const row = btn.closest('tr');
    if(row) row.remove();
    const body = document.getElementById('excludeListBody');
    if(body && !body.querySelector('tr')){
      body.innerHTML = '<tr><td colspan="3" class="text-muted py-3">없음</td></tr>';
    }
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
  const leftBar = document.getElementById('drag-left');
  const rightBar = document.getElementById('drag-right');
  const left = document.getElementById('left');
  const right = document.getElementById('right');
  function attach(bar, target, dir){
    if(!bar || !target) return;
    let sx=0, sw=0;
    bar.addEventListener('mousedown', e=>{
      sx = e.clientX; sw = target.offsetWidth;
      document.addEventListener('mousemove', mv);
      document.addEventListener('mouseup', up);
    });
    function mv(e){
      const delta = dir==='left' ? e.clientX - sx : sx - e.clientX;
      const w = sw + delta;
      const min=220, max=window.innerWidth*0.4;
      if(w>min && w<max) target.style.width = w+'px';
    }
    function up(){
      document.removeEventListener('mousemove', mv);
      document.removeEventListener('mouseup', up);
    }
  }
  attach(leftBar, left, 'left');
  attach(rightBar, right, 'right');
}
document.addEventListener('DOMContentLoaded', initDragLayout);

// 10. 포지션/알림 실시간 갱신
function initDotPositions(){
  document.querySelectorAll('.dot[data-pos]').forEach(el=>{
    el.style.left = el.dataset.pos + '%';
  });
  document.querySelectorAll('.se-bar .pin[data-pos]').forEach(el=>{
    el.style.left = el.dataset.pos + '%';
  });
  document.querySelectorAll('.trend-pin[data-pos]').forEach(el=>{
    el.style.left = el.dataset.pos + '%';
  });  
}

function updatePositions(list){
  const body = document.getElementById('positionBody');
  if(!body) return;
  body.innerHTML = list.map(p => `
    <tr>
      <td>${p.coin}</td>
      <td>${p.strategy || ''}</td>
      <td>
        <button class="btn btn-sm btn-outline-primary text-dark"
                data-api="/api/exclude-coin" data-coin="${p.coin}">제외</button>
      </td>
      <td>
        ${p.pnl === null
          ? '<span class="text-muted">데이터 없음</span>'
          : `<span class="badge ${p.pnl >= 0 ? 'badge-profit' : 'badge-loss'}">`+
            `${p.pnl > 0 ? '+' : ''}${p.pnl.toFixed(1)}%</span>`}
      </td>
      <td>
        <div class="se-bar">
          <span class="dot stop"></span>
          <span class="dot entry" data-pos="${p.entry_pct}"></span>
          <span class="dot take"></span>
          ${p.pin_pct !== null
            ? `<span class="pin" data-pos="${p.pin_pct}"></span>`
            : ''}
        </div>
        <div class="trend-bar mt-1">
          <span class="tick tick1"></span>
          <span class="tick tick2"></span>
          <span class="dot trend ${p.trend_color}" data-pos="${p.trend}"></span>
        </div>
      </td>
      <td><span class="badge badge-${p.signal}">${p.signal_label}</span></td>
      <td>
        <button class="btn btn-sm btn-outline-danger" data-api="/api/manual-sell"
                data-confirm="시장가로 매도 요청을 하시겠습니까?" data-coin="${p.coin}">
          수동 매도
        </button>
      </td>
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
    const data = await fetchJsonRetry('/api/balances');
    console.log('[API-A002] GET /api/balances', data);
    if (data.result === 'success' && data.balances) {
      if (disconnected) {
        console.log('서버 연결이 복구되었습니다.');
      }
      disconnected = false;
      updateBalanceTable(data.balances);
    } else if (data.message) {
      showAlert(data.message, '에러');
    }
  } catch(err){
    handleDisconnect('A002');
  }
}

function updateBalanceTable(list){
  const body = document.getElementById('positionBody');
  if(!body) return;
  body.innerHTML = list.map(p => `
    <tr>
      <td>${p.coin}</td>
      <td>
        <button class="btn btn-sm btn-outline-primary text-dark"
                data-api="/api/exclude-coin" data-coin="${p.coin}">제외</button>
      </td>
      <td>
          ${p.pnl === null
            ? '<span class="text-muted">데이터 없음</span>'
            : `<span class="badge ${p.pnl >= 0 ? 'badge-profit' : 'badge-loss'}">`+
              `${p.pnl > 0 ? '+' : ''}${p.pnl.toFixed(1)}%</span>`}
      </td>
      <td>
        <div class="se-bar">
          <span class="dot stop"></span>
          <span class="dot entry" data-pos="${p.entry_pct}"></span>
          <span class="dot take"></span>
            ${p.pin_pct !== null
              ? `<span class="pin" data-pos="${p.pin_pct}"></span>`
              : ''}
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
        <td>
          <button class="btn btn-sm btn-outline-success" data-api="/api/manual-buy" data-coin="${s.coin}">수동 매수</button>
        </td>
    </tr>
  `).join('');
  initDotPositions();
}

// 매수 모니터링 테이블 갱신
async function reloadBuyMonitor(){
  try {
    const data = await fetchJsonRetry('/api/signals');
    console.log('[API-A003] GET /api/signals', data);
    if (data.result === 'success' && data.signals) {
      updateSignalTable(data.signals);
      disconnected = false;
    } else if (data.message) {
      showAlert(data.message, '에러');
    }
  } catch(err){
    handleDisconnect('A003');
  }
}

function updateSignalTable(list){
  const body = document.getElementById('signalBody');
  if(!body) return;
  body.innerHTML = list.map(s => `
    <tr>
      <td>${s.coin}</td>
      <td>${formatNumber(s.price)}</td>
      <td class="icon-cell">${s.trend}</td>
      <td class="icon-cell">${s.volatility}</td>
      <td class="icon-cell">${s.volume}</td>
      <td class="icon-cell">${s.strength}</td>
      <td class="icon-cell">${s.gc}</td>
      <td class="icon-cell">${s.rsi}</td>
      <td><span class="badge badge-${s.signal_class}">${s.signal}</span></td>
      <td>
        <button class="btn btn-sm btn-outline-success" data-api="/api/manual-buy"
                data-coin="${s.coin}">수동 매수</button>
      </td>
    </tr>
  `).join('');
}

// 서버 상태 조회 후 화면 갱신
async function loadStatus(){
  try {
    const data = await fetchJsonRetry('/api/status');
    console.log('[API-A004] GET /api/status', data);
    if (data.result === 'success' && data.status) {
      const stateEl = document.getElementById('bot-state');
      const timeEl = document.getElementById('webStart');
      const btn = document.getElementById('botActionBtn');
      if (stateEl) {
        if (disconnected) {
          stateEl.innerHTML = '🛑';
        } else if (data.status.running) {
          stateEl.innerHTML = '🟩';
        } else {
          stateEl.innerHTML = '🟨';
        }
      }
      if (timeEl) {
        timeEl.textContent = `${data.status.start_time} [${data.status.uptime}]`;
      }
      if (btn) {
        if (data.status.running) {
          btn.classList.remove('btn-primary');
          btn.classList.add('btn-danger');
          btn.dataset.api = '/api/stop-bot';
          btn.textContent = '봇 중지';
        } else {
          btn.classList.remove('btn-danger');
          btn.classList.add('btn-primary');
          btn.dataset.api = '/api/start-bot';
          btn.textContent = '봇 시작';
        }
      }
      if (data.status.next_refresh) {
        const next = new Date(data.status.next_refresh).getTime();
        const remain = Math.max(0, Math.ceil((next - Date.now()) / 1000));
        balRemain = remain;
        sigRemain = remain;
      }
      disconnected = false;
    } else if (data.message) {
      showAlert(data.message, '에러');
    }
  } catch(err){
    handleDisconnect('A004');
  }
}

function formatNumber(val){
  const num = parseFloat(val);
  if(isNaN(num)) return val;
  return num.toLocaleString();
}

async function reloadAccount(){
  try {
    const data = await fetchJsonRetry('/api/account');
    console.log('[API-A005] GET /api/account', data);
    if (data.result === 'success' && data.account) {
      const c = document.getElementById('accountCash');
      const t = document.getElementById('accountTotal');
      const p = document.getElementById('accountPnl');
      if (c) c.textContent = formatNumber(data.account.cash) + ' 원';
      if (t) t.textContent = formatNumber(data.account.total) + ' 원';
      if (p) p.textContent = data.account.pnl + ' %';
      disconnected = false;
    }
  } catch(err){
    handleDisconnect('A005');
  }
}

const STATUS_INT = 300000;  // 5분
const BAL_INT = 300000;  // 5분
const SIG_INT = 300000;
const REFRESH_SEC = BAL_INT / 1000;
let balRemain = REFRESH_SEC;
let sigRemain = REFRESH_SEC;

function updateRemain(id, sec){
  const el = document.getElementById(id);
  if(!el) return;
  const m = Math.floor(sec / 60);
  const s = String(sec % 60).padStart(2, '0');
  el.textContent = `데이터 갱신 잔여시간: ${m}:${s}`;
}

document.addEventListener('DOMContentLoaded', ()=>{
  setInterval(loadStatus, STATUS_INT);
  setInterval(reloadAccount, 10000);
  setInterval(async ()=>{ await reloadBalance(); await loadStatus(); }, BAL_INT);
  setInterval(async ()=>{ await reloadBuyMonitor(); await loadStatus(); }, SIG_INT);
  setInterval(()=>{
    balRemain = balRemain > 0 ? balRemain - 1 : REFRESH_SEC;
    updateRemain('balanceTimer', balRemain);
  },1000);
  setInterval(()=>{
    sigRemain = sigRemain > 0 ? sigRemain - 1 : REFRESH_SEC;
    updateRemain('signalTimer', sigRemain);
  },1000);
  setTimeout(loadStatus, 3000);
  reloadAccount();
  reloadBalance();
  reloadBuyMonitor();
  updateRemain('balanceTimer', balRemain);
  updateRemain('signalTimer', sigRemain);
  const btn = document.getElementById('btnExcludedList');
  if(btn){
    btn.addEventListener('click', async ()=>{
      try{
        const data = await fetchJsonRetry('/api/excluded-coins');
        console.log('[API-A006] GET /api/excluded-coins', data);
        if(data.result === 'success'){
          const body = document.getElementById('excludeListBody');
          if(body){
            body.innerHTML = data.coins.length ?
              data.coins.map(c => `
                <tr>
                  <td>${c.coin}</td>
                  <td>${c.deleted}</td>
                  <td>
                    <button class="btn btn-sm btn-outline-primary"
                            data-api="/api/restore-coin"
                            data-coin="${c.coin}">복구</button>
                  </td>
                </tr>`).join('') :
              '<tr><td colspan="3" class="text-muted py-3">없음</td></tr>';
            new bootstrap.Modal(document.getElementById('excludeListModal')).show();
          }
        } else if(data.message){
          showAlert(data.message, '에러');
        }
      }catch(err){
        handleDisconnect('A006');
      }
    });
  }
});
