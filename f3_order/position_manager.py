"""
[F3] 포지션 상태 관리(HOLD FSM, 불타기/물타기/익절/손절/트레일 등)
로그: logs/f3/F3_position_manager.log
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import sqlite3
import json
from .utils import log_with_tag, now
from f6_setting.alarm_control import get_template
from .upbit_api import UpbitClient

logger = logging.getLogger("F3_position_manager")
os.makedirs("logs/f3", exist_ok=True)
fh = RotatingFileHandler(
    "logs/f3/F3_position_manager.log",
    encoding="utf-8",
    maxBytes=100_000 * 1024,
    backupCount=1000,
)
formatter = logging.Formatter('%(asctime)s [F3] %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)


def _now_kst():
    import datetime
    tz = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(tz).isoformat(timespec="seconds")


def _log_jsonl(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")


def _save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _load_json(path: str):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # pragma: no cover - best effort
        return []

def _load_json_dict(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

class PositionManager:
    def __init__(self, config, kpi_guard, exception_handler, parent_logger=None):
        self.config = config
        self.kpi_guard = kpi_guard
        self.exception_handler = exception_handler
        self.db_path = self.config.get("DB_PATH", "logs/f3/orders.db")
        self.positions_file = self.config.get("POSITIONS_FILE", "config/f1_f3_coin_positions.json")
        self.sell_config_path = self.config.get(
            "SELL_LIST_PATH", "config/f3_f3_realtime_sell_list.json"
        )
        self.positions = _load_json(self.positions_file)
        self.client = UpbitClient()
        self.tp_orders: dict[str, str] = {}
        # 계좌의 기존 잔고를 가져와 본 앱에서 연 포지션과 함께 관리
        self.import_existing_positions()

    def has_position(self, symbol: str) -> bool:
        """Return True if *symbol* has an open or pending position."""
        for p in self.positions:
            if p.get("symbol") == symbol and p.get("status") in ("open", "pending"):
                return True
        try:
            data = _load_json(self.positions_file)
            return any(
                p.get("symbol") == symbol and p.get("status") in ("open", "pending")
                for p in data
            )
        except Exception:  # pragma: no cover - best effort
            return False

    def _persist_positions(self) -> None:
        try:
            _save_json(self.positions_file, self.positions)
        except Exception as exc:  # pragma: no cover - best effort
            log_with_tag(logger, f"Failed to persist positions: {exc}")

    def open_position(self, order_result, status: str = "open"):
        """신규 포지션 오픈 (주문 결과 또는 잔고 가져오기)

        Parameters
        ----------
        order_result : dict
            주문 결과 또는 잔고 정보.
        status : str, optional
            초기 포지션 상태. 기본값은 ``"open"`` 이며 미체결 주문을
            추적할 때는 ``"pending"`` 을 사용할 수 있다.
        """
        price = order_result.get("price")
        qty = order_result.get("qty")
        if price is None or qty is None:
            log_with_tag(logger, f"Invalid order result, skipping position: {order_result}")
            return
        pos = {
            "symbol": order_result["symbol"],
            "entry_time": now(),
            "entry_price": price,
            "qty": qty,
            "pyramid_count": 0,
            "avgdown_count": 0,
            "status": status,
            "origin": order_result.get("origin", "trade"),
        }
        if "strategy" in order_result:
            pos["strategy"] = order_result["strategy"]
        self.positions.append(pos)
        self._persist_positions()
        log_with_tag(logger, f"Open position: {pos}")
        if status == "open" and pos.get("origin") != "imported":
            self.place_tp_order(pos)

    def place_tp_order(self, position):
        """Immediately place a limit sell order for take profit."""
        cfg = _load_json_dict(self.sell_config_path)
        tp = cfg.get(position["symbol"], {}).get("TP_PCT", self.config.get("TP_PCT", 1.0))
        price = position["entry_price"] * (1 + float(tp) / 100)
        res = self.place_order(position["symbol"], "ask", position["qty"], "limit", price)
        uuid = res.get("uuid")
        if uuid:
            self.tp_orders[position["symbol"]] = uuid

    def cancel_tp_order(self, symbol: str):
        uuid = self.tp_orders.pop(symbol, None)
        if uuid:
            try:
                self.client.cancel_order(uuid)
            except Exception as exc:  # pragma: no cover - best effort
                log_with_tag(logger, f"Failed to cancel TP order {uuid}: {exc}")

    def import_existing_positions(self, threshold: float = 5000.0) -> None:
        """Scan account balances and register them as open positions."""
        try:
            accounts = self.client.get_accounts()
        except Exception as exc:  # pragma: no cover - best effort
            log_with_tag(logger, f"Failed to fetch accounts: {exc}")
            return

        imported = []
        ignored = []
        for coin in accounts:
            if coin.get("currency") == "KRW":
                continue
            bal = float(coin.get("balance", 0))
            price = float(coin.get("avg_buy_price", 0))
            eval_amt = bal * price
            symbol = f"{coin.get('unit_currency', 'KRW')}-{coin.get('currency')}"
            log_data = {
                "time": _now_kst(),
                "symbol": symbol,
                "qty": bal,
                "entry_price": price,
                "eval_amt": eval_amt,
            }
            if eval_amt >= threshold:
                exists = any(
                    p.get("symbol") == symbol and p.get("status") == "open"
                    for p in self.positions
                )
                if not exists:
                    self.open_position({
                        "symbol": symbol,
                        "price": price,
                        "qty": bal,
                        "origin": "imported",
                        "strategy": "imported",
                    })
                log_data.update({"event": "ImportPosition", "origin": "imported", "action": "매도 시그널 감시 시작"})
                imported.append(f"{symbol}({int(eval_amt):,}원)")
            else:
                log_data.update({"event": "IgnoreSmallBalance", "action": "매수대상 유지"})
                ignored.append(f"{symbol}({int(eval_amt):,}원)")
            _log_jsonl("logs/etc/position_init.log", log_data)

        if self.exception_handler and (imported or ignored):
            lines = ["[시스템] 시작 시 보유코인 점검 완료."]
            if imported:
                lines.append("- 5천원 이상 보유: " + ", ".join(imported) + " → 매도 감시")
            if ignored:
                lines.append("- 5천원 미만: " + ", ".join(ignored) + " → 신규 매수 가능")
            self.exception_handler.send_alert(
                "\n".join(lines), "info", "system_start_stop"
            )

    def refresh_positions(self) -> None:
        """Update price and PnL information for all open positions."""
        open_syms = [p.get("symbol") for p in self.positions if p.get("status") in ("open", "pending")]
        if not open_syms:
            # Remove any closed positions and persist an empty list
            self.positions = [p for p in self.positions if p.get("status") == "open"]
            self._persist_positions()
            return

        try:
            accounts = self.client.get_accounts()
            accounts_ok = True
        except Exception as exc:  # pragma: no cover - best effort
            log_with_tag(logger, f"Failed to fetch accounts: {exc}")
            accounts = []
            accounts_ok = False

        acc_map = {
            f"{a.get('unit_currency', 'KRW')}-{a.get('currency')}": a
            for a in accounts
        }

        try:
            ticker_data = self.client.ticker(open_syms)
        except Exception as exc:  # pragma: no cover - best effort
            log_with_tag(logger, f"Failed to fetch ticker: {exc}")
            ticker_data = []

        price_map = {t.get("market"): float(t.get("trade_price", 0)) for t in ticker_data}

        for pos in self.positions:
            if pos.get("status") not in ("open", "pending"):
                continue
            sym = pos.get("symbol")
            info = acc_map.get(sym, {})
            pos["avg_price"] = float(info.get("avg_buy_price", pos.get("entry_price") or 0))
            if pos.get("status") == "pending":
                qty = float(info.get("balance", 0))
            else:
                qty = float(info.get("balance", pos.get("qty") or 0))
            pos["qty"] = qty
            if pos.get("status") == "pending" and accounts_ok and qty > 0:
                pos["status"] = "open"
            elif accounts_ok and qty <= 0 and pos.get("status") == "open":
                pos["status"] = "closed"
            if sym in price_map:
                pos["current_price"] = price_map[sym]
            if pos.get("current_price") is not None:
                pos["eval_amount"] = qty * pos["current_price"]
            if pos.get("avg_price"):
                cur = pos.get("current_price", pos["avg_price"])
                pos["pnl_percent"] = (cur - pos["avg_price"]) / pos["avg_price"] * 100

        # 종료된 포지션은 목록에서 제거하되, 미체결 주문은 남겨 둔다
        self.positions = [
            p for p in self.positions if p.get("status") in ("open", "pending")
        ]

        self._persist_positions()

    def hold_loop(self):
        """
        1Hz 루프: 각 포지션별 FSM 관리 (불타기/물타기/익절/손절/트레일/타임스탑 등)
        ※ 조건/산식은 config 기준. (실제 시세 연동 필요)
        """
        remaining = []
        sell_cfg = _load_json_dict(self.sell_config_path)
        for pos in self.positions:
            if pos.get("status") != "open":
                continue
            cur_price = pos.get("current_price")
            if cur_price is None:
                log_with_tag(logger, f"No price info for {pos['symbol']}")
                remaining.append(pos)
                continue

            entry = pos.get("entry_price", cur_price)
            pos["max_price"] = max(pos.get("max_price", cur_price), cur_price)
            pos["min_price"] = min(pos.get("min_price", cur_price), cur_price)
            from .utils import tick_size

            tick = tick_size(entry)
            change_tick = int((cur_price - entry) / tick)
            change_pct = (cur_price - entry) / entry * 100

            hold_secs = self.config.get("HOLD_SECS", 0)
            held_too_long = hold_secs and now() - pos.get("entry_time", 0) >= hold_secs

            tp = sell_cfg.get(pos.get("symbol"), {}).get("TP_PCT", self.config.get("TP_PCT", 1.2))
            sl = sell_cfg.get(pos.get("symbol"), {}).get("SL_PCT", self.config.get("SL_PCT", 1.0))

            tp_tick = int(entry * tp / 100 / tick)
            sl_tick = int(entry * abs(sl) / 100 / tick)

            if change_tick >= tp_tick:
                # take-profit order will execute automatically
                pass
            elif change_tick <= -sl_tick:
                self.cancel_tp_order(pos.get("symbol"))
                self.execute_sell(pos, "stop_loss")
            else:
                if pos.get("avg_price") and pos["avg_price"] > cur_price:
                    self.cancel_tp_order(pos.get("symbol"))
                elif pos.get("avg_price") and pos["avg_price"] <= cur_price:
                    if pos.get("symbol") not in self.tp_orders:
                        self.place_tp_order(pos)

                if held_too_long:
                    self.manage_trailing_stop(pos)
                else:
                    self.process_pyramiding(pos)
                    self.process_averaging_down(pos)
                    self.manage_trailing_stop(pos)

            if pos.get("status") == "open":
                remaining.append(pos)

        self.positions = remaining

    def place_order(self, symbol, side, qty, order_type="market", price=None):
        """Submit an order through the Upbit API and return the response."""
        # Translate legacy side values
        side = {"buy": "bid", "sell": "ask"}.get(side, side)
        try:
            resp = self.client.place_order(
                market=symbol,
                side=side,
                volume=qty,
                price=price,
                ord_type=order_type,
            )

            # 체결 상태와 체결 수량 계산
            executed_qty = float(resp.get("executed_volume", 0))
            if executed_qty == 0 and resp.get("remaining_volume") is not None:
                try:
                    executed_qty = float(qty) - float(resp.get("remaining_volume", 0))
                except Exception:
                    executed_qty = 0

            is_partial = resp.get("state") != "done" and executed_qty > 0

            resp["filled"] = resp.get("state") == "done"
            resp["timestamp"] = now()
            resp["symbol"] = symbol
            resp["qty"] = qty
            resp["price"] = price
            resp["order_type"] = order_type

            log_with_tag(logger, f"Order API response: {resp}")

            if is_partial:
                fill = {
                    "market": symbol,
                    "side": side,
                    "volume": str(executed_qty),
                    "price": price or resp.get("price"),
                }
                self.update_position_from_fill(resp.get("uuid"), fill)

            self.log_order_to_db(resp)
            return resp
        except Exception as e:
            self.exception_handler.handle(e, context="place_order")
            return {"symbol": symbol, "side": side, "qty": qty, "price": price, "order_type": order_type, "filled": False}

    def update_position_from_fill(self, order_id, fill_info):
        """Update a position based on filled order information."""
        symbol = fill_info.get("market")
        for pos in self.positions:
            if pos.get("symbol") == symbol and pos.get("status") == "open":
                if fill_info.get("side") == "bid":
                    pos["qty"] += float(fill_info.get("volume", 0))
                    if not pos.get("entry_price"):
                        pos["entry_price"] = float(fill_info.get("price", 0))
                else:
                    pos["qty"] -= float(fill_info.get("volume", 0))
                    if pos["qty"] <= 0:
                        pos["status"] = "closed"
                log_with_tag(logger, f"Position updated from fill {order_id}: {pos}")
                break

    def execute_sell(self, position, exit_type, qty=None):
        """Execute a sell order for a position."""
        if qty is None:
            qty = position.get("qty", 0)
        if self.exception_handler:
            msg = f"[매도 시도] {position['symbol']} @{position.get('current_price')}"
            self.exception_handler.send_alert(msg, "info", "order_execution")
        order = self.place_order(position["symbol"], "ask", qty, "market", position.get("current_price"))
        slip = 0.0
        if position.get("current_price") and position.get("entry_price"):
            slip = abs(position["current_price"] - position["entry_price"]) / position["entry_price"] * 100
        order["exit_type"] = exit_type
        order["slippage_pct"] = slip
        self.exception_handler.handle_slippage(position["symbol"], order)
        position["qty"] -= qty
        if position["qty"] <= 0:
            position["status"] = "closed"
        self._persist_positions()
        log_with_tag(logger, f"Position exit: {position['symbol']} via {exit_type}")
        if self.exception_handler:
            template = get_template("sell")
            reason = "손절 매도" if exit_type == "stop_loss" else "익절 매도"
            try:
                msg = template.format(
                    symbol=position["symbol"],
                    price=order.get("price"),
                    reason=reason,
                )
            except KeyError:
                msg = template.format(
                    symbol=position["symbol"],
                    price=order.get("price"),
                )
            self.exception_handler.send_alert(msg, "info", "order_execution")
        return order

    def manage_trailing_stop(self, position):
        if not self.config.get("TRAILING_STOP_ENABLED", True):
            return
        cur = position.get("current_price")
        if cur is None:
            return
        entry = position.get("entry_price")
        if entry is None:
            return
        max_price = position.get("max_price", cur)
        start_pct = self.config.get("TRAIL_START_PCT", 0.7)
        step_pct = self.config.get("TRAIL_STEP_PCT", 1.0)
        gain_pct = (max_price - entry) / entry * 100
        if gain_pct >= start_pct:
            drop = (max_price - cur) / max_price * 100
            if drop >= step_pct:
                self.execute_sell(position, "trailing_stop")

    def process_pyramiding(self, position):
        if not self.config.get("PYR_ENABLED", False):
            return
        if position["pyramid_count"] >= self.config.get("PYR_MAX_COUNT", 0):
            return
        cur = position.get("current_price")
        if cur is None:
            return
        trigger = self.config.get("PYR_TRIGGER", 1.0)
        if (cur - position["entry_price"]) / position["entry_price"] * 100 >= trigger:
            qty = self.config.get("PYR_SIZE", 0) / cur
            res = self.place_order(position["symbol"], "bid", qty, "market", cur)
            if res.get("filled"):
                position["qty"] += qty
                position["pyramid_count"] += 1

    def process_averaging_down(self, position):
        if not self.config.get("AVG_ENABLED", False):
            return
        if position["avgdown_count"] >= self.config.get("AVG_MAX_COUNT", 0):
            return
        cur = position.get("current_price")
        if cur is None:
            return
        trigger = self.config.get("AVG_TRIGGER", 1.0)
        if (position["entry_price"] - cur) / position["entry_price"] * 100 >= trigger:
            qty = self.config.get("AVG_SIZE", 0) / cur
            res = self.place_order(position["symbol"], "bid", qty, "market", cur)
            if res.get("filled"):
                position["qty"] += qty
                position["avgdown_count"] += 1

    def log_order_to_db(self, order_data):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS orders (timestamp TEXT, uuid TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, order_type TEXT, state TEXT, exit_type TEXT, slippage REAL)"
        )
        cur.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                order_data.get("timestamp", now()),
                order_data.get("uuid"),
                order_data.get("symbol"),
                order_data.get("side"),
                order_data.get("qty"),
                order_data.get("price"),
                order_data.get("order_type"),
                order_data.get("state"),
                order_data.get("exit_type"),
                order_data.get("slippage_pct", 0.0),
            ),
        )
        conn.commit()
        conn.close()

    def close_all_positions(self, order_type="market"):
        """Close all open positions immediately."""
        remaining = []
        for pos in list(self.positions):
            if pos.get("status") == "open":
                self.cancel_tp_order(pos.get("symbol"))
                self.execute_sell(pos, "risk_close", pos.get("qty"))
            if pos.get("status") == "open":
                remaining.append(pos)
        self.positions = remaining
        self._persist_positions()

    def close_position(self, symbol: str, reason: str = "") -> None:
        for pos in list(self.positions):
            if pos.get("symbol") == symbol and pos.get("status") == "open":
                self.cancel_tp_order(symbol)
                self.execute_sell(pos, reason or "universe_exit", pos.get("qty"))
        self._persist_positions()

    def sync_with_universe(self, universe) -> None:
        for pos in list(self.positions):
            if pos.get("status") != "open":
                continue
            if pos.get("symbol") not in universe and pos.get("origin") != "imported":
                self.close_position(pos.get("symbol"), "Universe Excluded")
                _log_jsonl(
                    "logs/etc/position_universe_sync.log",
                    {
                        "time": _now_kst(),
                        "event": "Universe Excluded",
                        "symbol": pos.get("symbol"),
                        "action": "AutoClose",
                        "reason": "Universe에서 제외됨",
                    },
                )


