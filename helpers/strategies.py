# -*- coding: utf-8 -*-
"""Simple strategy signal helpers."""

from __future__ import annotations

import logging
import os
from typing import Dict

import pandas as pd
import pyupbit

from bot.indicators import calc_indicators
from utils import calc_tis, load_secrets, send_telegram
from helpers.utils.risk import load_risk_settings

logger = logging.getLogger(__name__)

try:
    _SEC = load_secrets()
    _TOKEN = _SEC.get("TELEGRAM_TOKEN")
    _CHAT = _SEC.get("TELEGRAM_CHAT_ID")
except Exception:  # pragma: no cover
    _TOKEN = os.getenv("TELEGRAM_TOKEN")
    _CHAT = os.getenv("TELEGRAM_CHAT_ID")


def _alert(msg: str) -> None:
    if _TOKEN and _CHAT:
        try:
            send_telegram(_TOKEN, _CHAT, msg)
        except Exception:
            logger.debug("telegram send failed")


BUY_PARAMS: Dict[str, Dict[str, Dict[str, float]]] = {
    "M-BREAK": {
        "공격적": {"atr": 0.03, "vol": 1.6, "break": 0.001},
        "중도적": {"atr": 0.035, "vol": 1.8, "break": 0.0015},
        "보수적": {"atr": 0.04, "vol": 2.0, "break": 0.002},
    },
    "P-PULL": {
        "공격적": {"rsi": 30, "vol": 1.1, "near": 0.004},
        "중도적": {"rsi": 28, "vol": 1.2, "near": 0.003},
        "보수적": {"rsi": 26, "vol": 1.3, "near": 0.002},
    },
    "T-FLOW": {
        "공격적": {"slope": 0.001, "rsi_low": 45, "rsi_high": 60},
        "중도적": {"slope": 0.0015, "rsi_low": 48, "rsi_high": 60},
        "보수적": {"slope": 0.002, "rsi_low": 50, "rsi_high": 58},
    },
    "B-LOW": {
        "공격적": {"box": 0.08, "touch": 0.02, "rsi": 30},
        "중도적": {"box": 0.06, "touch": 0.01, "rsi": 25},
        "보수적": {"box": 0.05, "touch": 0.0, "rsi": 22},
    },
    "V-REV": {
        "공격적": {"drop": 0.035, "vol": 2.0, "rebound": 0.04},
        "중도적": {"drop": 0.04, "vol": 2.5, "rebound": 0.04},
        "보수적": {"drop": 0.05, "vol": 3.0, "rebound": 0.05},
    },
    "G-REV": {
        "공격적": {"rsi": 45, "vol": 0.5},
        "중도적": {"rsi": 48, "vol": 0.6},
        "보수적": {"rsi": 50, "vol": 0.7},
    },
    "VOL-BRK": {
        "공격적": {"atr": 1.4, "vol": 1.8, "rsi": 55},
        "중도적": {"atr": 1.5, "vol": 2.0, "rsi": 60},
        "보수적": {"atr": 1.6, "vol": 2.2, "rsi": 65},
    },
    "EMA-STACK": {
        "공격적": {"adx": 25},
        "중도적": {"adx": 30},
        "보수적": {"adx": 35},
    },
    "VWAP-BNC": {
        "공격적": {"vwap": 0.015, "rsi_low": 40, "rsi_high": 65, "vol": 0.9},
        "중도적": {"vwap": 0.012, "rsi_low": 45, "rsi_high": 60, "vol": 1.0},
        "보수적": {"vwap": 0.01, "rsi_low": 48, "rsi_high": 58, "vol": 1.1},
    },
}

SELL_PARAMS: Dict[str, Dict[str, Dict[str, float]]] = {
    name: {
        "공격적": {"tp": 0.06, "sl": 0.03, "tis": 95},
        "중도적": {"tp": 0.04, "sl": 0.02, "tis": 95},
        "보수적": {"tp": 0.03, "sl": 0.015, "tis": 95},
    }
    for name in BUY_PARAMS.keys()
}


def _get_df(ticker: str) -> pd.DataFrame | None:
    try:
        df = pyupbit.get_ohlcv(ticker, interval="minute5", count=80)
    except Exception as e:
        logger.error("[API Exception] OHLCV fail %s", e)
        _alert(f"[API Exception] 캔들 조회 실패: {ticker} {e}")
        return None
    if df is None or df.empty:
        return None
    return calc_indicators(df)


def check_buy_signal(strategy_name: str, ticker: str, level: str = "중도적") -> bool:
    """Return True if buy conditions are met for given strategy and level."""
    params = BUY_PARAMS.get(strategy_name, {}).get(level)
    if not params:
        return False
    df = _get_df(ticker)
    if df is None:
        return False
    last = df.iloc[-1]

    if strategy_name == "M-BREAK":
        prev_high = df["high"][-21:-1].max()
        vol_ma20 = df["volume"][-20:].mean()
        return (
            last["ema5"] > last["ema20"] > last["ema60"]
            and last["atr"] >= params["atr"]
            and last["volume"] >= vol_ma20 * params["vol"]
            and last["close"] > prev_high * (1 + params["break"])
        )
    if strategy_name == "P-PULL":
        prev_vol = df["volume"].iloc[-2]
        ema50 = last["ema50"]
        return (
            last["ema5"] > last["ema20"] > last["ema60"]
            and abs(last["close"] - ema50) / (ema50 + 1e-9) < params["near"]
            and last["rsi"] <= params["rsi"]
            and last["volume"] >= prev_vol * params["vol"]
        )
    if strategy_name == "T-FLOW":
        slope = (df["ema20"].iloc[-1] - df["ema20"].iloc[-5]) / (abs(df["ema20"].iloc[-5]) + 1e-9)
        obv_inc = all(df["obv"].iloc[-i] > df["obv"].iloc[-i - 1] for i in range(1, 4))
        return (
            slope > params["slope"]
            and obv_inc
            and params["rsi_low"] <= last["rsi"] <= params["rsi_high"]
        )
    if strategy_name == "B-LOW":
        low80 = df["low"][-80:].min()
        high80 = df["high"][-80:].max()
        box_ratio = (high80 - low80) / (low80 + 1e-9)
        return (
            box_ratio < params["box"]
            and last["low"] <= low80 * (1 + params["touch"])
            and last["rsi"] < params["rsi"]
        )
    if strategy_name == "V-REV":
        prev = df.iloc[-2]
        price_drop = abs(prev["close"] - last["close"]) / (prev["close"] + 1e-9)
        volume_burst = last["volume"] > prev["volume"] * params["vol"]
        rsi_rise = last["rsi"] > 20 and prev["rsi"] <= 18
        rebound = (last["close"] - prev["close"]) / (prev["close"] + 1e-9) > params["rebound"]
        return price_drop >= params["drop"] and volume_burst and rsi_rise and rebound
    if strategy_name == "G-REV":
        prev_vol = df["volume"].iloc[-2]
        golden = last["ema50"] > last["ema200"]
        return golden and last["rsi"] >= params["rsi"] and last["volume"] >= prev_vol * params["vol"]
    if strategy_name == "VOL-BRK":
        atr10 = df["atr"][-10:].mean()
        vol20 = df["volume"][-20:].mean()
        high20 = df["high"][-20:].max()
        return (
            last["atr"] > atr10 * params["atr"]
            and last["volume"] > vol20 * params["vol"]
            and last["high"] > high20 * 0.999
            and last["rsi"] >= params["rsi"]
        )
    if strategy_name == "EMA-STACK":
        return (
            last["ema25"] > last["ema100"] > last["ema200"]
            and last["adx"] >= params["adx"]
        )
    if strategy_name == "VWAP-BNC":
        prev_vol = df["volume"].iloc[-2]
        vwap_ratio = abs(last["close"] - last["vwap"]) / (last["vwap"] + 1e-9)
        return (
            last["ema5"] > last["ema20"] > last["ema60"]
            and vwap_ratio < params["vwap"]
            and params["rsi_low"] <= last["rsi"] <= params["rsi_high"]
            and last["volume"] >= prev_vol * params["vol"]
        )
    return False


def check_sell_signal(
    strategy_name: str,
    ticker: str,
    buy_price: float,
    level: str = "중도적",
    risk_conf: Dict[str, float] | None = None,
) -> bool:
    """Return True if sell conditions are met for given strategy and level.

    ``risk_conf`` 가 제공되면 전역 손절 한도를 함께 적용한다.
    """
    params = SELL_PARAMS.get(strategy_name, {}).get(level)
    if not params:
        return False
    if risk_conf is None:
        risk_conf = load_risk_settings()
    df = _get_df(ticker)
    if df is None:
        return False
    try:
        price = pyupbit.get_current_price(ticker) or float(df["close"].iloc[-1])
    except Exception as e:
        logger.error("[API Exception] price fail %s", e)
        _alert(f"[API Exception] 시세 조회 실패: {ticker} {e}")
        return False
    last = df.iloc[-1]
    tis = calc_tis(ticker) or 100
    pnl = (price - buy_price) / (buy_price + 1e-9)
    dc = df["ema5"].iloc[-2] > df["ema20"].iloc[-2] and df["ema5"].iloc[-1] < df["ema20"].iloc[-1]

    if risk_conf and pnl <= -float(risk_conf.get("max_dd_per_coin", 0.0)):
        return True

    if dc or tis < params["tis"]:
        return True
    if pnl <= -params["sl"] or pnl >= params["tp"]:
        return True
    return False
