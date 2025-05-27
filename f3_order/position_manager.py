"""
[F3] 포지션 상태 관리(HOLD FSM, 불타기/물타기/익절/손절/트레일 등)
로그: logs/F3_position_manager.log
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import sqlite3
import json
from .utils import log_with_tag, now
from .upbit_api import UpbitClient

logger = logging.getLogger("F3_position_manager")
fh = RotatingFileHandler(
    "logs/F3_position_manager.log",
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

class PositionManager:
    def __init__(self, config, dynamic_params, kpi_guard, exception_handler, parent_logger=None):
        self.config = config
        self.dynamic_params = dynamic_params
        self.kpi_guard = kpi_guard
        self.exception_handler = exception_handler
        self.db_path = self.config.get("DB_PATH", "logs/orders.db")
        self.positions = []
        self.client = UpbitClient()

    def open_position(self, order_result):
        """ 신규 포지션 오픈 (filled 주문 결과 기반) """
        pos = {
            "symbol": order_result["symbol"],
            "entry_time": now(),
            "entry_price": order_result.get("price", None),
            "qty": order_result.get("qty", None),
            "pyramid_count": 0,
            "avgdown_count": 0,
            "status": "open",
        }
        self.positions.append(pos)
        log_with_tag(logger, f"Open position: {pos}")

    def hold_loop(self):
        """
        1Hz 루프: 각 포지션별 FSM 관리 (불타기/물타기/익절/손절/트레일/타임스탑 등)
        ※ 조건/산식은 config와 dynamic_params 기준. (실제 시세 연동 필요)
        """
        remaining = []
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
            change_pct = (cur_price - entry) / entry * 100

            if change_pct >= self.config.get("TP_PCT", 1.2):
                self.execute_sell(pos, "take_profit")
            elif change_pct <= -abs(self.config.get("SL_PCT", 1.0)):
                self.execute_sell(pos, "stop_loss")
            else:
                self.process_pyramiding(pos)
                self.process_averaging_down(pos)
                self.manage_trailing_stop(pos)

            if pos.get("status") == "open":
                remaining.append(pos)

        self.positions = remaining

    def place_order(self, symbol, side, qty, order_type="market", price=None):
        """Submit an order through the Upbit API and return the response."""
        try:
            resp = self.client.place_order(
                market=symbol,
                side=side,
                volume=qty,
                price=price,
                ord_type=order_type,
            )

            # Determine fill status and executed quantity
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
        order = self.place_order(position["symbol"], "sell", qty, "market", position.get("current_price"))
        slip = 0.0
        if position.get("current_price") and position.get("entry_price"):
            slip = abs(position["current_price"] - position["entry_price"]) / position["entry_price"] * 100
        order["exit_type"] = exit_type
        order["slippage_pct"] = slip
        self.exception_handler.handle_slippage(position["symbol"], order)
        position["qty"] -= qty
        if position["qty"] <= 0:
            position["status"] = "closed"
        log_with_tag(logger, f"Position exit: {position['symbol']} via {exit_type}")
        return order

    def manage_trailing_stop(self, position):
        if not self.config.get("TRAILING_STOP_ENABLED", True):
            return
        cur = position.get("current_price")
        if cur is None:
            return
        max_price = position.get("max_price", cur)
        start_pct = self.config.get("TRAIL_START_PCT", 0.7)
        step_pct = self.config.get("TRAIL_STEP_PCT", 1.0)
        gain_pct = (max_price - position["entry_price"]) / position["entry_price"] * 100
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
        trigger = self.dynamic_params.get("PYR_TRIGGER", 1.0)
        if (cur - position["entry_price"]) / position["entry_price"] * 100 >= trigger:
            qty = self.config.get("PYR_SIZE", 0) / cur
            res = self.place_order(position["symbol"], "buy", qty)
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
        trigger = self.dynamic_params.get("AVG_TRIGGER", 1.0)
        if (position["entry_price"] - cur) / position["entry_price"] * 100 >= trigger:
            qty = self.config.get("AVG_SIZE", 0) / cur
            res = self.place_order(position["symbol"], "buy", qty)
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
                self.execute_sell(pos, "risk_close", pos.get("qty"))
            if pos.get("status") == "open":
                remaining.append(pos)
        self.positions = remaining

    def close_position(self, symbol: str, reason: str = "") -> None:
        for pos in list(self.positions):
            if pos.get("symbol") == symbol and pos.get("status") == "open":
                self.execute_sell(pos, reason or "universe_exit", pos.get("qty"))

    def sync_with_universe(self, universe) -> None:
        for pos in list(self.positions):
            if pos.get("status") != "open":
                continue
            if pos.get("symbol") not in universe:
                self.close_position(pos.get("symbol"), "Universe Excluded")
                _log_jsonl(
                    "logs/position_universe_sync.log",
                    {
                        "time": _now_kst(),
                        "event": "Universe Excluded",
                        "symbol": pos.get("symbol"),
                        "action": "AutoClose",
                        "reason": "Universe에서 제외됨",
                    },
                )


