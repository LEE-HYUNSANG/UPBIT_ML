# Documentation Index

초보 기획자를 위해 `doc/` 폴더의 문서를 정리했습니다. 주요 문서를 번호순으로 나열하고 관련 파일, 동작 흐름, 로그 위치 등을 간단히 소개합니다.

| 번호 | 파일명 | 개요 |
| --- | --- | --- |
| 1 | [01_select_universe.md](01_select_universe.md) | 유니버스 선정 절차와 사용 파일 설명 |
| 2 | [02_coin_buy_logic.md](02_coin_buy_logic.md) | 매수 신호 계산과 주문 흐름 |
| 3 | [03_coin_sell_logic.md](03_coin_sell_logic.md) | 보유 코인 매도 로직과 포지션 관리 |
| 4 | [04_risk_logic.md](04_risk_logic.md) | 리스크 매니저 구조와 주요 설정 |
| 5 | [api_endpoints.md](api_endpoints.md) | 웹 대시보드용 REST API 목록 |
| 6 | [config.md](config.md) | 프로젝트 전반의 JSON 설정 파일 안내 |
| 7 | [f2_ml_buy_signal.md](f2_ml_buy_signal.md) | 경량 머신러닝 매수 신호 모듈 |
| 8 | [f5ml_00_before_coin.md](f5ml_00_before_coin.md) | 코인 필터링 및 원시 데이터 수집 |
| 9 | [f5ml_00_yesterday_1min_data.md](f5ml_00_yesterday_1min_data.md) | 최근 72시간 1분봉 다운로드 |
| 10 | [f5ml_01_data_collect.md](f5ml_01_data_collect.md) | OHLCV 정기 수집 스크립트 |
| 11 | [f5ml_data_cleaning.md](f5ml_data_cleaning.md) | 원본 데이터 정제 방법 |
| 12 | [f5ml_feature_engineering.md](f5ml_feature_engineering.md) | 지표 계산을 통한 피처 생성 |
| 13 | [f5ml_labeling.md](f5ml_labeling.md) | 매수/매도 라벨 생성 기준 |
| 14 | [f5ml_05_split.md](f5ml_05_split.md) | 학습/검증/테스트 데이터 분할 |
| 15 | [f5ml_06_train.md](f5ml_06_train.md) | LightGBM 모델 학습 절차 |
| 16 | [f5ml_08_predict.md](f5ml_08_predict.md) | 학습 모델로 매수 확률 예측 |
| 17 | [f5ml_09_backtest.md](f5ml_09_backtest.md) | 예측 결과 백테스트 수행 |
| 18 | [f5ml_10_select_best_strategies.md](f5ml_10_select_best_strategies.md) | 우수 전략 선별 |
| 19 | [f5ml_pipeline.md](f5ml_pipeline.md) | 전체 F5 파이프라인 요약 |
| 20 | [f9ml_pipeline_backup.md](f9ml_pipeline_backup.md) | 예전 파이프라인 백업 자료 |
| 21 | [formula_offsets.md](formula_offsets.md) | 공식에 과거값 오프셋 사용하는 방법 |
| 22 | [order_limits.md](order_limits.md) | 업비트 주문 최소 금액 규정 |
| 23 | [overview.md](overview.md) | 시스템 전반 개요 |
| 24 | [roi_sharpe.md](roi_sharpe.md) | ROI와 Sharpe 지수 설명 |
| 25 | [sellqty_handling.md](sellqty_handling.md) | SellQty 지표 0 처리 방식 |
| 26 | [telegram_notifications.md](telegram_notifications.md) | 주문 알림 텔레그램 설정 |
| 27 | [telegram_remote_control.md](telegram_remote_control.md) | 텔레그램 원격 제어 봇 사용법 |
| 28 | [web_template_overview.md](web_template_overview.md) | 웹 대시보드 구성 설명 |
| 29 | [01_selecting_coins_to_buy.md](01_selecting_coins_to_buy.md) | 매수 대상 코인 선별 과정 |
| 30 | [02_coin_buy_signal.md](02_coin_buy_signal.md) | ML 기반 매수 시그널 생성 |
| 31 | [03_coin_buy_logic.md](03_coin_buy_logic.md) | 매수 주문 처리 절차 |
| 32 | [04_coin_sell_signal.md](04_coin_sell_signal.md) | 매도 시그널 계산 방식 |
| 33 | [05_coin_buy_signal.md](05_coin_buy_signal.md) | 매도 주문 처리 로직 |
| 34 | [06_f5_machine_learning.md](06_f5_machine_learning.md) | F5 전체 로직 한눈에 보기 |
| 35 | [07_alarm_setting.md](07_alarm_setting.md) | 알림 및 원격 설정 가이드 |
각 문서에서는 사용되는 설정 파일 경로, 실행 스크립트 위치, 데이터 저장 구조와 로그 파일 위치까지 가능한 한 구체적으로 서술했습니다. 문서를 읽는 순서는 위 표의 번호를 따라가면 이해가 빠릅니다.
