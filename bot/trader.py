"""
업비트 5분봉 자동매매 메인 트레이더 (최종본)
- 9전략 지원, 실시간 지표/전략 평가, 실전 주문(모의/실매수 모두 가능)
- Flask, 로그 연동, 스레드 안전, 초보자용 상세 주석
"""
import time           # 주기적 실행을 위한 시간 모듈
import threading      # 스레드 사용을 위해
import pandas as pd   # 데이터프레임 처리
import pyupbit        # 업비트 API 연동
from .strategy import select_strategy
from .indicators import calc_indicators

class UpbitTrader:
    def __init__(self, upbit_key, upbit_secret, config, logger=None):
        self.upbit = pyupbit.Upbit(upbit_key, upbit_secret)  # API 객체 생성
        self.config = config    # 설정(dict)
        self.running = False    # 봇 실행 여부
        self.logger = logger    # 로거
        self.thread = None      # 실행 스레드
        if self.logger:
            self.logger.debug("Trader initialized with config %s", config)

    def start(self):
        """자동매매 시작 (스레드)"""
        if self.thread and self.thread.is_alive():
            if self.logger:
                self.logger.warning("Trader already running")
            return
        self.running = True  # 루프 실행 플래그 활성화
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()  # 별도 스레드에서 run_loop 실행
        if self.logger:
            self.logger.debug("Trader start called")
            self.logger.info("[TRADER] 자동매매 봇 시작됨")

    def stop(self):
        """자동매매 종료"""
        self.running = False  # 루프 종료 플래그
        if self.thread:
            self.thread.join(timeout=1)  # 스레드 종료 대기
        if self.logger:
            self.logger.debug("Trader stop called")
            self.logger.info("[TRADER] 자동매매 봇 중지됨")

    def run_loop(self):
        """메인 5분봉 매매 루프"""
        while self.running:
            try:
                if self.logger:
                    self.logger.debug("run_loop iteration")
                tickers = self.config.get("tickers", ["KRW-BTC", "KRW-ETH"])
                strat_name = self.config.get("strategy", "M-BREAK")
                params = self.config.get("params", {})
                if self.logger:
                    self.logger.debug(
                        "Tickers=%s strategy=%s params=%s",
                        tickers,
                        strat_name,
                        params,
                    )
                for ticker in tickers:
                    df = pyupbit.get_ohlcv(ticker, interval="minute5", count=120)
                    if df is None or len(df) < 60:
                        if self.logger:
                            self.logger.debug("Insufficient data for %s", ticker)
                        continue
                    if self.logger:
                        self.logger.debug(
                            "Fetched OHLCV for %s close=%s", ticker, df['close'].iloc[-1]
                        )
                    df = calc_indicators(df)
                    if self.logger:
                        last = df.iloc[-1].to_dict()
                        self.logger.debug("Indicators %s", last)
                    # 실시간 체결강도, 예시용 (0~200)
                    tis = 120  # 예시 체결강도 (0~200)
                    ok, strat_params = select_strategy(strat_name, df, tis, params)
                    if self.logger:
                        self.logger.debug(
                            "Strategy %s result=%s params=%s",
                            strat_name,
                            ok,
                            strat_params,
                        )
                    if ok:
                        # 실제 매수/매도 로직 (실매수시 주의)
                        last_price = df['close'].iloc[-1]  # 현재가
                        qty = self.config.get("amount", 10000) / last_price  # 매수 수량
                        # self.upbit.buy_market_order(ticker, qty)  # 실전 매수(주의)
                        if self.logger:
                            self.logger.info(
                                "[BUY] %s %.1f (%0.4f개) %s 진입",
                                ticker,
                                last_price,
                                qty,
                                strat_name,
                            )
                time.sleep(300)  # 5분 대기 후 다음 루프
            except Exception as e:
                if self.logger:
                    self.logger.exception("[TRADER ERROR] %s", e)
                time.sleep(10)  # 잠시 대기 후 재시도

    def get_balances(self):
        """Return raw balances from Upbit API."""
        try:
            if self.logger:
                self.logger.debug("Fetching balances from Upbit")
            return self.upbit.get_balances()
        except Exception as e:
            if self.logger:
                self.logger.exception("Failed to get balances: %s", e)
            return None

    def account_summary(self):
        """Return cash/total/pnl summary calculated from balances."""
        balances = self.get_balances()
        if not balances:
            return None
        try:
            cash = 0.0
            total = 0.0
            for b in balances:
                bal = float(b.get("balance", 0))
                if b.get("currency") == "KRW":
                    cash += bal
                    total += bal
                else:
                    try:
                        price = pyupbit.get_current_price(f"KRW-{b['currency']}") or 0
                    except Exception:
                        if self.logger:
                            self.logger.warning("Price lookup failed for %s", b['currency'])
                        price = 0
                    total += bal * price
                if self.logger:
                    self.logger.debug(
                        "Balance %s=%.6f price=%s",
                        b.get("currency"),
                        bal,
                        locals().get("price", "N/A"),
                    )
            pnl = ((total - cash) / cash * 100) if cash else 0.0
            summary = {
                "cash": int(cash),
                "total": int(total),
                "pnl": round(pnl, 2),
            }
            if self.logger:
                self.logger.debug("Account summary %s", summary)
            return summary
        except Exception as e:
            if self.logger:
                self.logger.exception("Failed to calculate summary: %s", e)
            return None

    def build_positions(self, balances):
        """Convert balance list to dashboard position entries."""
        positions = []
        for b in balances:
            currency = b.get("currency")
            bal = float(b.get("balance", 0))
            if currency == "KRW" or bal == 0:
                continue
            try:
                price = pyupbit.get_current_price(f"KRW-{currency}") or 0
            except Exception:
                if self.logger:
                    self.logger.warning("Price lookup failed for %s", currency)
                price = 0
            avg_buy = float(b.get("avg_buy_price", 0))
            pnl = round((price - avg_buy) / avg_buy * 100, 2) if avg_buy else 0.0
            positions.append({
                "coin": currency,
                "pnl": pnl,
                "entry": 50,
                "trend": 50,
                "trend_color": "green",
                "signal": "sell-wait",
                "signal_label": "관망",
            })
            if self.logger:
                self.logger.debug("Position added %s %.6f", currency, bal)
        return positions
