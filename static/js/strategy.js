const apiURL = "/api/strategies";         // TODO: 다음 단계에서 구현
const tbody  = document.querySelector("#tbl-strategy tbody");
const tpl    = document.querySelector("#row-tpl");
const lastSaved = document.getElementById("last-saved");

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

// ────────────────────────────────
// 3. 전략 추가 (빈 행)
// ────────────────────────────────
document.getElementById("btn-add").onclick = ()=>{
  const obj = {active:true,name:"신규전략",
               buy_condition:"중도적",sell_condition:"중도적",
               priority: tbody.children.length+1};
  tbody.appendChild(makeRow(obj));
};

// ────────────────────────────────
// 4. 저장 (TODO: 백엔드 POST는 다음 단계에서)
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
  console.log("★ 저장 payload", rows);
  // TODO: fetch(apiURL,{method:"POST",headers:{...},body:JSON.stringify(rows)})
  alert("로컬 미리보기용 — POST 로직은 다음 단계에서 연결합니다.");
};

// ────────────────────────────────
// 5. 외부 동기화용 커스텀 이벤트 
//    (다른 모듈이 필요할 때 listen 가능)
// ────────────────────────────────
function dispatchUpdated(rows){
  document.dispatchEvent(new CustomEvent("strategiesUpdated",{detail:rows}));
}
