"""
업비트 5분봉 자동매매 메인 트레이더 (최종본)
- 9전략 지원, 실시간 지표/전략 평가, 실전 주문(모의/실매수 모두 가능)
- Flask, 로그 연동, 스레드 안전, 초보자용 상세 주석
"""
import time           # 주기적 실행을 위한 시간 모듈
import threading      # 스레드 사용을 위해
import pandas as pd   # 데이터프레임 처리
import pyupbit        # 업비트 API 연동
from utils import calc_tis
from .strategy import select_strategy
from .indicators import calc_indicators


def calc_sell_signal(dc: bool, tis: float, pnl: float, sl_th: float, tp_th: float,
                     ema5: float, ema20: float) -> str:
    """Return sell signal label based on given indicators."""
    if dc or tis < 95:
        return "강제 매도"
    if pnl is not None and sl_th and pnl < -sl_th:
        return "손절 준비"
    if pnl is not None and tp_th and pnl > tp_th:
        return "익절 준비"
    if ema5 > ema20:
        return "수익 극대화"
    return "관망"

class UpbitTrader:
    def __init__(self, upbit_key, upbit_secret, config, logger=None):
        self.upbit = pyupbit.Upbit(upbit_key, upbit_secret)  # API 객체 생성
        self.config = config    # 설정(dict)
        self.running = False    # 봇 실행 여부
        self.logger = logger    # 로거
        self.thread = None      # 실행 스레드
        self.tickers = config.get("tickers", ["KRW-BTC", "KRW-ETH"])
        if self.logger:
            self.logger.debug("Trader initialized with config %s", config)

    def set_tickers(self, tickers: list[str]) -> None:
        """Update trading tickers list."""
        self.tickers = tickers
        if self.logger:
            self.logger.info("[TRADER] Tickers updated: %s", tickers)

    def start(self) -> bool:
        """자동매매 시작 (스레드)"""
        if self.thread and self.thread.is_alive():
            if self.logger:
                self.logger.warning("Trader already running")
            return False
        self.running = True  # 루프 실행 플래그 활성화
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()  # 별도 스레드에서 run_loop 실행
        if self.logger:
            self.logger.debug("Trader start called")
            self.logger.info("[TRADER] 자동매매 봇 시작됨")
        return True

    def stop(self) -> bool:
        """자동매매 종료"""
        if not self.thread or not self.thread.is_alive():
            if self.logger:
                self.logger.warning("Trader not running")
            self.running = False
            return False
        self.running = False  # 루프 종료 플래그
        if self.thread:
            self.thread.join(timeout=1)  # 스레드 종료 대기
        if self.logger:
            self.logger.debug("Trader stop called")
            self.logger.info("[TRADER] 자동매매 봇 중지됨")
        return True

    def run_loop(self):
        """메인 5분봉 매매 루프"""
        while self.running:
            try:
                if self.logger:
                    self.logger.debug("run_loop iteration")
                tickers = self.tickers
                if not tickers:
                    if self.logger:
                        self.logger.warning("[TRADER] No tickers to trade")
                    time.sleep(60)
                    continue
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
                    tis = calc_tis(ticker) or 0
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

    def account_summary(self, excluded=None):
        """Return cash/total/pnl summary calculated from balances.

        Parameters
        ----------
        excluded : set[str] | None
            Coins to ignore when calculating the summary.
        """
        balances = self.get_balances()
        if excluded:
            balances = [b for b in balances if b.get("currency") not in excluded]
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

    def build_positions(self, balances, excluded=None):
        """Convert balance list to dashboard position entries.

        Parameters
        ----------
        balances : list[dict]
            Raw balance entries from Upbit.
        excluded : set[str] | None
            Coins to ignore entirely.
        """
        positions = []
        params = self.config.get("params", {})
        sl_pct = params.get("sl", 0) * 100
        tp_pct = params.get("tp", 0) * 100
        for b in balances:
            currency = b.get("currency")
            bal = float(b.get("balance", 0))
            if currency == "KRW" or bal == 0:
                continue
            if excluded and currency in excluded:
                if self.logger:
                    self.logger.debug("Skip position for excluded coin %s", currency)
                continue
            try:
                price = pyupbit.get_current_price(f"KRW-{currency}") or 0
            except Exception:
                if self.logger:
                    self.logger.warning("Price lookup failed for %s", currency)
                price = 0
            avg_buy = float(b.get("avg_buy_price", 0))
            pnl = round((price - avg_buy) / avg_buy * 100, 1) if avg_buy else None

            if avg_buy and sl_pct and tp_pct:
                stop = avg_buy * (1 - sl_pct / 100)
                take = avg_buy * (1 + tp_pct / 100)
                entry_pct = round(100 * (avg_buy - stop) / (take - stop), 1)
                pin_pct = round(100 * (price - stop) / (take - stop), 1)
                entry_pct = max(0, min(100, entry_pct))
                pin_pct = max(0, min(100, pin_pct))
            else:
                entry_pct = None
                pin_pct = None

            label = calc_sell_signal(False, 100, pnl, sl_pct, tp_pct, 0, 0)
            signal_map = {
                "강제 매도": "sell-force",
                "손절 준비": "sell-sl",
                "익절 준비": "sell-tp",
                "수익 극대화": "sell-max",
                "관망": "sell-wait",
            }

            positions.append({
                "coin": currency,
                "pnl": pnl,
                "entry_pct": entry_pct,
                "pin_pct": pin_pct,
                "trend": 50,
                "trend_color": "gray",
                "signal": signal_map.get(label, "sell-wait"),
                "signal_label": label,
            })
            if self.logger:
                self.logger.debug("Position added %s %.6f", currency, bal)
        return positions
