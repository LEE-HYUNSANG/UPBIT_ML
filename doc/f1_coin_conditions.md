# f1_universe/01.coin_conditions.py 사용법

업비트 KRW 마켓을 조회해 가격대와 거래대금 조건을 만족하는 코인을 선별하여
`config/f1_f5_data_collection_list.json` 파일에 저장합니다.

## 주요 조건
- 최근 가격이 `PRICE1_MIN` ~ `PRICE1_MAX` 또는 `PRICE2_MIN` ~ `PRICE2_MAX` 범위에 속해야 합니다.
- 24시간 거래대금(`acc_trade_price_24h`)이 `TRADE_VALUE_MIN` 이상이어야 합니다.
- `EXCEPTION_COINS`에 지정된 종목은 조건을 만족하더라도 제외됩니다.

스크립트 상단의 "Coin Conditions" 영역에서 값을 수정해 조건을 조정할 수 있습니다.
`PRICE2_MIN` 과 `PRICE2_MAX`를 모두 0으로 설정하면 두 번째 가격 범위는 사용하지 않습니다.
실행 방법은 다음과 같습니다.
```bash
python f1_universe/01.coin_conditions.py
```
