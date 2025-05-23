"""
업비트 5분봉 자동매매 메인 트레이더 (최종본)
- 22전략 지원, 실시간 지표/전략 평가, 실전 주문(모의/실매수 모두 가능)
- Flask, 로그 연동, 스레드 안전, 초보자용 상세 주석
"""
import time           # 주기적 실행을 위한 시간 모듈
import threading      # 스레드 사용을 위해
import pandas as pd   # 데이터프레임 처리
import pyupbit        # 업비트 API 연동
import json
import os
MIN_POSITION_VALUE = 5000.0  # 5천원 이하는 매매 불가이므로 보유 개수 계산에서 제외
from utils import calc_tis, load_secrets, send_telegram, call_upbit_api
import notifications

from helpers.strategies import (
    check_buy_signal,
    check_sell_signal,
    df_to_market,
)
from .indicators import calc_indicators
from helpers.utils.positions import load_open_positions, save_open_positions


def calc_sell_signal(dc: bool, tis: float, pnl: float, sl_th: float, tp_th: float,
                     ema5: float, ema20: float) -> str:
    """지표 값에 따라 매도 신호 라벨을 반환한다."""
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
    """업비트 자동매매를 실행하는 메인 클래스.

    백그라운드 루프에서 지정된 전략을 평가하고
    조건 충족 시 주문을 실행한다.
    """
    def __init__(self, upbit_key, upbit_secret, config, logger=None, on_price_fail=None):
        self.upbit = pyupbit.Upbit(upbit_key, upbit_secret)  # API 객체 생성
        self.config = config    # 설정(dict)
        self.running = False    # 봇 실행 여부
        self.logger = logger    # 로거
        self.thread = None      # 실행 스레드
        self.tickers = config.get("tickers", ["KRW-BTC", "KRW-ETH"])
        self.positions: dict[str, dict] = {}  # 보유 포지션 관리
        self.on_price_fail = on_price_fail
        self._fail_counts: dict[str, int] = {}
        try:
            sec = load_secrets()
            self.token = sec.get("TELEGRAM_TOKEN")
            self.chat = sec.get("TELEGRAM_CHAT_ID")
        except Exception:
            self.token = os.getenv("TELEGRAM_TOKEN")
            self.chat = os.getenv("TELEGRAM_CHAT_ID")
        if self.logger:
            self.logger.debug("Trader initialized with config %s", config)

    def _alert(self, msg: str) -> None:
        if self.token and self.chat:
            try:
                send_telegram(self.token, self.chat, msg)
            except Exception:
                if self.logger:
                    self.logger.debug("telegram send failed")

    def _notify(self, msg: str) -> None:
        """SocketIO 및 텔레그램으로 일반 메시지를 전송한다."""
        try:
            notifications.notify(msg)
        except Exception:
            if self.logger:
                self.logger.debug("telegram send failed")

    def _record_price_failure(self, currency: str) -> None:
        """시세 조회 실패 횟수를 누적하고 경고만 전송한다."""
        count = self._fail_counts.get(currency, 0) + 1
        self._fail_counts[currency] = count
        limit = self.config.get("failure_limit", 3)
        if count >= limit:
            self._alert(f"[WARN] {currency} 시세 조회 {count}회 연속 실패")
            self._fail_counts[currency] = 0
        if self.on_price_fail:
            try:
                self.on_price_fail(currency)
            except Exception:
                if self.logger:
                    self.logger.debug("on_price_fail callback error")

    def _position_count(self) -> int:
        """5천원 이상 가치가 있는 포지션 수를 반환한다."""
        return sum(1 for p in self.positions.values() if p.get("qty", 0) * p.get("entry", 0) > MIN_POSITION_VALUE)

    def set_tickers(self, tickers: list[str]) -> None:
        """거래 대상 티커 목록을 갱신한다."""
        self.tickers = tickers
        if self.logger:
            self.logger.info("[TRADER] Tickers updated: %s", tickers)

    def _load_active_strategies(self) -> list[dict]:
        """활성화된 전략 정보를 우선순위 순으로 반환한다."""
        try:
            from helpers.utils.strategy_cfg import load_strategy_list
            table = load_strategy_list()
            active = [s for s in table if s.get("active")]
            active.sort(key=lambda x: x.get("priority", 0))
            return active
        except Exception as exc:  # pragma: no cover - file missing
            if self.logger:
                self.logger.warning("Strategy list load failed: %s", exc)
            return [
                {
                    "name": self.config.get("strategy", "M-BREAK"),
                    "buy_condition": self.config.get("level", "중도적"),
                    "sell_condition": self.config.get("level", "중도적"),
                }
            ]

    def start(self) -> bool:
        """자동매매 시작 (스레드)"""
        if os.path.exists(PID_FILE) or (self.thread and self.thread.is_alive()):
            if self.logger:
                self.logger.warning("Trader already running")
            return False
        self.sync_positions()
        self.running = True  # 루프 실행 플래그 활성화
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()  # 별도 스레드에서 run_loop 실행
        try:
            with open(PID_FILE, "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except Exception:
            if self.logger:
                self.logger.debug("PID file write failed")
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
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                if self.logger:
                    self.logger.debug("PID file remove failed")
        if self.logger:
            self.logger.debug("Trader stop called")
            self.logger.info("[TRADER] 자동매매 봇 중지됨")
        return True

    def run_loop(self):
        """메인 5분봉 매매 루프"""
        error_count = 0
        while self.running:
            try:
                if self.logger:
                    self.logger.debug("run_loop iteration")
                now = time.time()
                tickers = self.tickers
                if not tickers:
                    if self.logger:
                        self.logger.warning("[TRADER] No tickers to trade")
                    time.sleep(60)
                    continue
                params = self.config.get("params", {})
                strategies = self._load_active_strategies()
                if self.logger:
                    self.logger.debug(
                        "Tickers=%s strategies=%s params=%s",
                        tickers,
                        strategies,
                        params,
                    )
                # 매도 신호 확인을 우선한다
                for ticker, pos in list(self.positions.items()):
                    df = call_upbit_api(pyupbit.get_ohlcv, ticker, interval="minute5", count=120)
                    if df is None or len(df) < 20:
                        continue
                    df = df.rename(
                        columns={
                            "open": "Open",
                            "high": "High",
                            "low": "Low",
                            "close": "Close",
                            "volume": "Volume",
                        }
                    )
                    df_ind = calc_indicators(df)
                    market = df_to_market(df_ind, 0)
                    market["Entry"] = pos["entry"]
                    market["Peak"] = df_ind["High"].cummax().iloc[-1]
                    if check_sell_signal(pos["strategy"], pos["level"], market):
                        call_upbit_api(self.upbit.sell_market_order, ticker, pos["qty"])
                        if self.logger:
                            self.logger.info(
                                "[SELL] %s %.1f (%0.4f개) %s 청산",
                                ticker,
                                df_ind['Close'].iloc[-1],
                                pos["qty"],
                                pos["strategy"],
                            )
                        self.positions.pop(ticker, None)
                        save_open_positions(self.positions)

                for ticker in tickers:
                    if self._position_count() >= self.config.get("max_positions", 1):
                        if self.logger:
                            self.logger.debug("[TRADER] max positions reached")
                        break
                    df = call_upbit_api(pyupbit.get_ohlcv, ticker, interval="minute5", count=120)
                    if df is None or len(df) < 60:
                        if self.logger:
                            self.logger.debug("Insufficient data for %s", ticker)
                        continue
                    if self.logger:
                        self.logger.debug(
                            "Fetched OHLCV for %s close=%s", ticker, df['close'].iloc[-1]
                        )
                    df = df.rename(
                        columns={
                            "open": "Open",
                            "high": "High",
                            "low": "Low",
                            "close": "Close",
                            "volume": "Volume",
                        }
                    )
                    df_ind = calc_indicators(df)
                    tis = calc_tis(ticker) or 0
                    market = df_to_market(df_ind, tis)

                    chosen = None
                    level = "중도적"
                    for s in strategies:
                        if check_buy_signal(s["name"], s.get("buy_condition", "중도적"), market):
                            chosen = s["name"]
                            level = s.get("sell_condition", "중도적")
                            break

                    if chosen:
                        if self._position_count() >= self.config.get("max_positions", 1):
                            if self.logger:
                                self.logger.debug("[TRADER] max positions reached")
                            break
                        last_price = df_ind["Close"].iloc[-1]
                        krw = self.config.get("amount", 10000)
                        qty = krw / last_price
                        call_upbit_api(self.upbit.buy_market_order, ticker, krw)
                        self.positions[ticker] = {
                            "qty": qty,
                            "entry": last_price,
                            "strategy": chosen,
                            "level": level,
                        }
                        save_open_positions(self.positions)
                        if self.logger:
                            self.logger.info(
                                "[BUY] %s %.1f (%0.4f개) %s 진입",
                                ticker,
                                last_price,
                                qty,
                                chosen,
                            )
                        self._notify(
                            f"[BUY] {ticker} {qty:.4f}개 @ {last_price:,.1f}원"
                        )

                # 매도 신호 확인
                for ticker, pos in list(self.positions.items()):
                    df = call_upbit_api(
                        pyupbit.get_ohlcv, ticker, interval="minute5", count=120
                    )
                    if df is None or len(df) < 20:
                        continue
                    df = df.rename(
                        columns={
                            "open": "Open",
                            "high": "High",
                            "low": "Low",
                            "close": "Close",
                            "volume": "Volume",
                        }
                    )
                    df_ind = calc_indicators(df)
                    market = df_to_market(df_ind, 0)
                    market["Entry"] = pos["entry"]
                    market["Peak"] = df_ind["High"].cummax().iloc[-1]
                    if check_sell_signal(pos["strategy"], pos["level"], market):
                        call_upbit_api(self.upbit.sell_market_order, ticker, pos["qty"])
                        if self.logger:
                            self.logger.info(
                                "[SELL] %s %.1f (%0.4f개) %s 청산",
                                ticker,
                                df_ind['Close'].iloc[-1],
                                pos["qty"],
                                pos["strategy"],
                            )
                        self._notify(
                            f"[SELL] {ticker} {pos['qty']:.4f}개 @ {df_ind['Close'].iloc[-1]:,.1f}원"
                        )
                        self.positions.pop(ticker, None)
                time.sleep(300)  # 5분 대기 후 다음 루프
                error_count = 0
            except Exception as e:
                if self.logger:
                    self.logger.exception("[TRADER ERROR] %s", e)
                self._alert(f"[ERROR] 트레이더 루프 오류: {e}")
                error_count += 1
                if error_count >= 3:
                    self._alert(f"[ERROR] 트레이더 연속 {error_count}회 오류")
                    error_count = 0
                time.sleep(10)  # 잠시 대기 후 재시도

    def get_balances(self):
        """업비트 API로부터 원시 잔고 데이터를 가져온다."""
        try:
            if self.logger:
                self.logger.debug("Fetching balances from Upbit")
            return call_upbit_api(self.upbit.get_balances)
        except Exception as e:
            if self.logger:
                self.logger.exception("Failed to get balances: %s", e)
            self._alert(f"[API Exception] 잔고 조회 실패: {e}")
            return None

    def sync_positions(self) -> None:
        """현재 보유 코인을 self.positions에 반영한다."""
        balances = self.get_balances()
        if not balances:
            return
        saved = load_open_positions()
        self.positions.clear()
        level = self.config.get("level", "중도적")
        for b in balances:
            if b.get("currency") == "KRW":
                continue
            qty = float(b.get("balance", 0))
            value = qty * float(b.get("avg_buy_price", 0))
            if value <= MIN_POSITION_VALUE:
                continue
            if qty <= 0:
                continue
            ticker = f"KRW-{b['currency']}"
            src = saved.get(ticker, {})
            self.positions[ticker] = {
                "qty": qty,
                "entry": float(b.get("avg_buy_price", 0)),
                "strategy": src.get("strategy", "INIT"),
                "level": src.get("level", level),
            }
        save_open_positions(self.positions)

    def account_summary(self, excluded=None):
        """잔고 목록을 이용해 보유 KRW, 총 매수금액, 총 평가금액과 손익률을 계산한다.

        Parameters
        ----------
        excluded : set[str] | None
            계산에서 제외할 코인 심볼 집합.
        """
        balances = self.get_balances()
        if not balances:
            return None
        if excluded:
            balances = [b for b in balances if b.get("currency") not in excluded]
        if not balances:
            return None
        try:
            krw = 0.0
            buy_total = 0.0
            eval_total = 0.0
            for b in balances:
                bal = float(b.get("balance", 0))
                currency = b.get("currency")
                if currency == "KRW":
                    krw += bal
                    continue
                avg_buy = float(b.get("avg_buy_price", 0))
                buy_total += bal * avg_buy
                try:
                    price = call_upbit_api(
                        pyupbit.get_current_price, f"KRW-{currency}"
                    ) or 0
                except Exception:
                    if self.logger:
                        self.logger.warning("Price lookup failed for %s", currency)
                    self._alert(f"[API Exception] 시세 조회 실패: {currency}")
                    self._record_price_failure(currency)
                    price = 0
                eval_total += bal * price
                if self.logger:
                    self.logger.debug(
                        "Balance %s=%.6f buy=%s price=%s",
                        currency,
                        bal,
                        avg_buy,
                        price,
                    )
            pnl = (eval_total / buy_total * 100) if buy_total else 0.0
            summary = {
                "krw": int(krw),
                "buy_total": int(buy_total),
                "eval_total": int(eval_total),
                "pnl": round(pnl, 2),
            }
            if self.logger:
                self.logger.cal("Account summary %s", summary)
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
        # 기본 전략값이 없으면 원인 불명 포지션으로 간주한다
        default_strategy = "INIT"
        default_level = self.config.get("level", "중도적")
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
                price = call_upbit_api(pyupbit.get_current_price, f"KRW-{currency}") or 0
            except Exception:
                if self.logger:
                    self.logger.warning("Price lookup failed for %s", currency)
                self._alert(f"[API Exception] 시세 조회 실패: {currency}")
                self._record_price_failure(currency)
                price = 0
            ticker = f"KRW-{currency}"
            strategy_code = default_strategy
            risk_level = default_level
            if ticker in self.positions:
                info = self.positions[ticker]
                strategy_code = info.get("strategy", strategy_code)
                risk_level = info.get("level", risk_level)
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
                "strategy": strategy_code,
                "level": risk_level,
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
