// static/js/pages/strategy.js
// 전략 설정 페이지에서만 사용하는 JS

// 전략 적용 버튼 이벤트 예시
document.addEventListener("DOMContentLoaded", function(){
  const applyBtn = document.getElementById('btn-apply-strategy');
  if(applyBtn){
    applyBtn.addEventListener('click', async function(){
      // 폼 데이터 수집 (예시, 실제 form 구조에 맞게 수정)
      const strat = document.getElementById('strategy').value;
      const tp = parseFloat(document.getElementById('tp').value);
      const sl = parseFloat(document.getElementById('sl').value);
      const trail = parseFloat(document.getElementById('trail').value);
      const data = {
        strategy: strat,
        params: {tp, sl, trail}
      };
      const result = await callApi('/api/apply-strategy', data);
      // 결과 메시지는 callApi에서 자동으로 showAlert됨
    });
  }
});
