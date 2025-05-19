// static/js/main.js
// 전체 페이지에서 공통으로 쓰는 JS (알림, 모달, API 연동, SocketIO 등)

// 1. Bootstrap 알림 모달 표시 함수
function showAlert(message, title="알림") {
  const modal = new bootstrap.Modal(document.getElementById('alertModal'));
  document.querySelector('#alertModal .modal-title').innerText = title;
  document.querySelector('#alertModal .modal-body').innerText = message;
  modal.show();
}

// 2. 모든 버튼에 AJAX로 진행 시 로딩 커서 표시
document.querySelectorAll('button, .btn').forEach(btn => {
  btn.addEventListener('click', function() {
    document.body.style.cursor = 'wait';
    setTimeout(() => { document.body.style.cursor = ''; }, 800);
  });
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
if(window.io){
  const socket = io();
  socket.on('notification', function(data){
    if(data.message) showAlert(data.message, "실시간 알림");
    const box = document.getElementById('liveAlerts');
    if(box){
      const div = document.createElement('div');
      div.textContent = data.message;
      box.prepend(div);
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
  const form = btn.closest('form');
  let data = {};
  if(form){
    data = Object.fromEntries(new FormData(form).entries());
  }
  await callApi(btn.dataset.api, data);
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
