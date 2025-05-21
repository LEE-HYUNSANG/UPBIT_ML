const apiURL = "/api/strategies";
const restoreURL = "/api/restore-defaults/strategy";
const tbody  = document.querySelector("#tbl-strategy tbody");
const tpl    = document.querySelector("#row-tpl");
const lastSaved = document.getElementById("last-saved");
const toggleAll = document.getElementById("toggle-all");

// ────────────────────────────────
// 1. 초기 로딩
// ────────────────────────────────
(async function init() {
  let data;
  try {                     // 실제 API가 없으면 임시 스텁 사용
    const res = await fetch(apiURL);
    data = res.ok ? await res.json() : null;
  } catch { /* dev */ }
  if (!data) {
    // ─── 임시 기본값 (25개 전략) ───
    data = [
      // 예: 이름, 기본 휴리스틱 설정
      "M-BREAK","VOL-BRK","RSI-PULL","ADX-TREND","MA-CROSS",
      "Boll-BB","KDJ-OSC","MACD-BOOST","CCI-REV","OBV-PEAK",
      "TEMA-PUMP","Ichimoku","SAR-SWING","FIBO-PIVOT","HTF-ALIGN",
      "VWAP-EDGE","ROC-MOM","ATR-STOP","STOCH-RDY","KD-RANGE",
      "PSAR-TRAIL","BB-BREAK","VOL-EXP","ADX-DM","RSI-BIAS"
    ].map((n,i)=>({active:false,name:n,
                   buy_condition:"중도적",sell_condition:"중도적",
                   priority:i+1}));
  }
  renderTable(data);
})();

// ────────────────────────────────
// 2. 테이블 렌더링
// ────────────────────────────────
function renderTable(arr){
  tbody.innerHTML = "";
  arr.sort((a,b)=>a.priority-b.priority)
     .forEach(obj=>tbody.appendChild(makeRow(obj)));
  lastSaved.textContent = new Date().toLocaleString();
  applyToggleAll();
}

function makeRow(o){
  const tr = tpl.content.firstElementChild.cloneNode(true);
  tr.querySelector(".active-toggle").checked = o.active;
  tr.querySelector(".strat-name").textContent = o.name;
  tr.querySelector(".buy-cond").value  = o.buy_condition;
  tr.querySelector(".sell-cond").value = o.sell_condition;
  tr.querySelector(".priority").value  = o.priority;
  return tr;
}

function applyToggleAll(){
  const on = toggleAll.checked;
  tbody.querySelectorAll(".active-toggle").forEach(el=>{
    el.checked = on;
  });
}

toggleAll.addEventListener("change", applyToggleAll);

// ────────────────────────────────
// 3. 저장
// ────────────────────────────────
document.getElementById("btn-save").onclick = async ()=>{
  const rows = [...tbody.querySelectorAll("tr")].map(tr=>({
    active: tr.querySelector(".active-toggle").checked,
    name  : tr.querySelector(".strat-name").textContent,
    buy_condition : tr.querySelector(".buy-cond").value,
    sell_condition: tr.querySelector(".sell-cond").value,
    priority      : +tr.querySelector(".priority").value || 99,
    updated       : new Date().toISOString()
  }));
  const res = await fetch(apiURL,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(rows)});
  if(res.ok){
    showAlert("저장되었습니다.");
    dispatchUpdated(rows);
    lastSaved.textContent = new Date().toLocaleString();
  }else{
    showAlert("저장 실패","에러");
  }
};

document.getElementById("btn-restore").onclick = async ()=>{
  const ok = await showConfirm("정말 복원하시겠습니까?", "복원 진행", "복원 취소");
  if(!ok) return;
  const res = await fetch(restoreURL,{method:"POST"});
  if(res.ok){
    const list = await fetch(apiURL).then(r=>r.json());
    renderTable(list);
    showAlert("복원 완료");
  }else{
    showAlert("복원 실패","에러");
  }
};

// ────────────────────────────────
// 5. 외부 동기화용 커스텀 이벤트 
//    (다른 모듈이 필요할 때 listen 가능)
// ────────────────────────────────
function dispatchUpdated(rows){
  document.dispatchEvent(new CustomEvent("strategiesUpdated",{detail:rows}));
}
