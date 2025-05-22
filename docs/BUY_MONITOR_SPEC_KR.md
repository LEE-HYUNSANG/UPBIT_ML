# 매수 모니터링 대시보드 상세 명세

본 문서는 `Home.html` 의 "매수 모니터링" 섹션에서 사용되는 표 컬럼과 계산 방법을 정리합니다. 모든 값은 완료된 봉(Closed Candle)을 기준으로 산출됩니다.

## 1. 표 컬럼

```
코인 | 현재가 | 추세 | 변동성(ATR%) | 거래량(%) | 체결강도 | GC | RIS | Buy 시그널 | 액션
```

## 2. 컬럼별 명세

### 2.1 코인
- **툴팁**: 실시간 감시 중인 코인의 심볼(BTC, ETH 등)을 표시합니다.
- **동작**: `매수 모니터링 코인 조건` 에 맞는 코인만 표시합니다.
- **UI 예시**: `<td>LSK</td>`

### 2.2 현재가 (`now_price`)
- **툴팁**: 해당 코인의 실시간 거래 가격을 표시합니다.
- **동작**: 5초 단위로 갱신되며, 값이 없을 경우 "⛔" 를 표시합니다.
- **UI 예시**: `<td>745.6</td>`

### 2.3 추세 (`trend`)
- **툴팁**
  - EMA5/20/60 배열과 기울기를 이용해 추세를 계산합니다.
  - 결과는 상승(U)/하락(D)/횡보(S)/불확실(F) 네 가지로 표시됩니다.
- **수식**:
  ```python
  ema5 = df['close'].ewm(span=5).mean()
  ema20 = df['close'].ewm(span=20).mean()
  ema60 = df['close'].ewm(span=60).mean()
  slope20 = ema20.pct_change(1)
  cond_up = (ema5 > ema20) & (ema20 > ema60) & (slope20 > 0)
  cond_down = (ema5 < ema20) & (ema20 < ema60) & (slope20 < 0)
  cond_side = slope20.abs() < 0.0005
  trend = np.select([cond_up, cond_down, cond_side], ['U', 'D', 'S'], 'F')
  ```
- **케이스 1:** 🔼 상승(U)
- **케이스 2:** 🔻 하락(D)
- **케이스 3:** 🔸 횡보/불확실(S/F)
- **UI 예시**: `<span class="trend-up">🔼</span>`

### 2.4 변동성(ATR%) (`atr_pct`)
- **툴팁**
  - 14봉 ATR을 현재가와 비교해 백분율로 표시합니다.
  - 값이 높을수록 변동성이 큰 상태를 의미합니다.
- **수식**:
  ```python
  atr = ta.ATR(df['high'], df['low'], df['close'], 14)
  atr_pct = atr / df['close'] * 100
  ```
- **케이스 1:** 🔵 5% 이상
- **케이스 2:** 🟡 1~5%
- **케이스 3:** 🔻 1% 미만
- **UI 예시**: `<span class="atr-high">🔵 6.4%</span>`

### 2.5 거래량(%) (`vol_ratio`)
- **툴팁**
  - 완료 봉 거래량이 최근 20봉 평균 대비 몇 배인지 표시합니다.
  - 1.0 이상이면 평균보다 많은 거래가 발생한 것입니다.
- **수식**:
  ```python
  vol_ratio = df['volume'] / df['volume'].rolling(20).mean()
  ```
- **케이스 1:** ⏫ 2.00 이상
- **케이스 2:** 🔼 1.10~1.99
- **케이스 3:** 🔸 0.70~1.09
- **케이스 4:** 🔻 0.70 미만
- **UI 예시**: `<span class="vol-veryhigh">⏫ 2.3</span>`

### 2.6 체결강도 (`tis`)
- **툴팁**
  - 최근 N분간 매수 체결량과 매도 체결량을 집계해 비율을 계산합니다.
  - 값이 100보다 크면 매수세 우위를 뜻합니다.
- **수식**:
  ```python
  tis = df['buy_qty'] / df['sell_qty'] * 100
  ```
  - `buy_qty`, `sell_qty` 값은 `/v1/trades/ticks` 체결 데이터를 최근 5분 동안 집계해 계산합니다.
- **케이스 1:** ⏫ 120 이상
- **케이스 2:** 🔼 105~119
- **케이스 3:** 🔸 95~104
- **케이스 4:** 🔻 95 미만
- **UI 예시**: `<span class="tis-high">⏫ 135</span>`

해당 체결강도 값은 전략 수식에서 **Strength** 컬럼으로 사용됩니다. `utils.calc_tis()`
함수를 통해 계산한 값을 `compute_indicators()` 호출 전에 DataFrame에
`Strength` 열로 추가하면 전략 조건식을 그대로 평가할 수 있습니다.

### 2.7 GC (골든/데드크로스)
- **툴팁**
  - EMA5가 EMA20을 상향 돌파하면 골든크로스(GC)로 판단합니다.
  - 반대로 하향 돌파하면 데드크로스(DC)로 표시합니다.
- **수식**:
  ```python
  ema5 = df['close'].ewm(span=5).mean()
  ema20 = df['close'].ewm(span=20).mean()
  gc = (ema5.shift(1) < ema20.shift(1)) & (ema5 > ema20)
  dc = (ema5.shift(1) > ema20.shift(1)) & (ema5 < ema20)
  ```
- **케이스 1:** 🔼 GC
- **케이스 2:** 🔻 DC
- **케이스 3:** 🔸 없음

### 2.8 RIS (RSI 코드)
- **툴팁**
  - RSI14 값을 여러 구간으로 나누어 문자 코드(E~X)로 표시합니다.
  - 과매도(E)부터 극과매수(X)까지 다섯 단계로 구분합니다.
- **수식**:
  ```python
  rsi = ta.RSI(df['close'], 14)
  if rsi < 30:
      ris_code = 'E'
  elif 30 <= rsi < 40:
      ris_code = 'S'
  elif 40 <= rsi < 70:
      ris_code = 'N'
  elif 70 <= rsi < 80:
      ris_code = 'B'
  else:
      ris_code = 'X'
  ```
- **케이스 1:** ⏫ E
- **케이스 2:** 🔼 S
- **케이스 3:** 🔸 N
- **케이스 4:** 🔻 B/X

### 2.9 Buy 시그널 (`buy_signal`)
- **툴팁**
  - 추세, 변동성, 거래량, 체결강도 등을 종합해 신호를 산출합니다.
  - 결과는 "매수 적극 추천"부터 "매수 금지"까지 여섯 단계입니다.
- **점수 계산 예시**:
  ```python
  score = (
      (trend == 'U') * 25 +
      (atr_pct >= 5) * 15 + ((atr_pct >= 1) & (atr_pct < 5)) * 10 +
      (vol_ratio >= 2) * 15 + (vol_ratio >= 1.1) * 10 +
      (tis >= 120) * 15 + (tis >= 105) * 10 +
      (gc) * 5 +
      (ris_code == 'E') * 5 + (ris_code == 'S') * 3
  )
  ```
- **시그널 맵핑**:
  | 조건 | 배지/클래스 |
  | --- | --- |
- **케이스 1:** trend U & tis≥120 & ris_code in [E,S] & vol_ratio≥2 → `badge-buy-strong` (매수 적극 추천)
- **케이스 2:** trend U & tis≥105 & vol_ratio≥1.1 & ris_code not in [B,X] → `badge-buy` (매수 추천)
- **케이스 3:** trend != 'D' & ris_code not in [B,X] → `badge-wait` (관망)
- **케이스 4:** trend == 'D' or ris_code in [B,X] → `badge-avoid` (매수 회피)
- **케이스 5:** vol_ratio<0.7 or tis<95 → `badge-ban` (매수 금지)
- **케이스 6:** 데이터 없음 → `badge-nodata` (데이터 대기)

### 2.10 액션
- **툴팁**
  - 버튼 클릭 시 해당 코인에 대한 시장가 매수 주문을 요청합니다.
  - 봇 설정에 따라 매수 불가 상태라면 비활성화됩니다.
- **동작**: POST `/api/manual-buy` 호출, 매수 불가 시 비활성화됩니다.
- **UI 예시**: `<button class="btn btn-outline-success">수동 매수</button>`

## 3. 공통 예외 처리
- 모든 계산은 완료된 봉 기준으로 수행합니다.
- 데이터 미수신 시 "⛔" 혹은 "데이터 없음"으로 표시하고 이전 값을 유지합니다.
- 컬럼 헤더의 `ⓘ` 혹은 `?` 아이콘에 마우스 오버 시 툴팁을 제공합니다.
- 아이콘과 배지 색상은 대시보드 전반에서 일관되게 사용합니다.
