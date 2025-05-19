// 메인 알림 모달 제어 함수
function showAlert(msg) {
  var modal = new bootstrap.Modal(document.getElementById('alertModal'));
  document.querySelector('#alertModal .modal-body').innerText = msg;
  modal.show();
}
// SocketIO 알림 (예시)
// var socket = io();
// socket.on('notification', function(data){ showAlert(data.message); });
