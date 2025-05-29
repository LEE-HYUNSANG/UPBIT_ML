"""09단계 백테스트 결과에서 성과가 우수한 전략을 자동 선정한다."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils import ensure_dir

# 기본 경로 설정
ROOT_DIR = Path(__file__).resolve().parents[1]
SUMMARY_DIR = ROOT_DIR / "ml_data/09_backtest"
PARAM_DIR = ROOT_DIR / "ml_data/04_label"
OUT_DIR = ROOT_DIR / "ml_data/10_selected"
OUT_FILE = OUT_DIR / "selected_strategies.json"
LOG_PATH = ROOT_DIR / "logs/select_best_strategies.log"
MONITORING_LIST_FILE = ROOT_DIR / "config/coin_list_monitoring.json"

# ----- 확장 포인트: 성과 기준과 정렬 기준 -----
MIN_WIN_RATE = 0.55      # 승률 55% 이상
MIN_AVG_ROI = 0.001      # 진입 1회당 0.1% 이상
MIN_SHARPE = 1.0         # 샤프비 1.0 이상
MAX_MDD = 0.10           # 최대 낙폭 10% 이하
MIN_ENTRIES = 50         # 최소 50회 진입
TOP_N = 10               # 상위 10개 전략만 채택
# -------------------------------------------------


def setup_logger() -> None:
    """로그 설정."""
    ensure_dir(LOG_PATH.parent)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            RotatingFileHandler(
                LOG_PATH,
                encoding="utf-8",
                maxBytes=50_000 * 1024,
                backupCount=5,
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )


def load_json(path: Path) -> dict:
    """JSON 파일을 로드한다."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def passes_criteria(summary: dict) -> bool:
    """주어진 성과가 필터 조건을 통과하는지 확인."""
    mdd = abs(summary.get("mdd", summary.get("max_drawdown", 0)))
    return (
        summary.get("win_rate", 0) >= MIN_WIN_RATE
        and summary.get("avg_roi", 0) >= MIN_AVG_ROI
        and summary.get("sharpe", 0) >= MIN_SHARPE
        and mdd <= MAX_MDD
        and summary.get("total_entries", 0) >= MIN_ENTRIES
    )


def select_strategies() -> list[dict]:
    """요건을 만족하는 전략을 정렬 후 반환."""
    strategies = []
    for file in SUMMARY_DIR.glob("*_summary.json"):
        symbol = file.stem.split("_")[0]
        try:
            summary = load_json(file)
        except Exception as exc:  # pragma: no cover - best effort
            logging.warning("%s 로드 실패: %s", file, exc)
            continue
        if not passes_criteria(summary):
            continue
        try:
            params = load_json(PARAM_DIR / f"{symbol}_best_params.json")
        except Exception:  # pragma: no cover - optional file
            params = {}
        strategies.append({
            "symbol": symbol,
            "win_rate": summary.get("win_rate", 0.0),
            "avg_roi": summary.get("avg_roi", 0.0),
            "sharpe": summary.get("sharpe", 0.0),
            "max_drawdown": abs(summary.get("mdd", summary.get("max_drawdown", 0))),
            "total_entries": summary.get("total_entries", 0),
            "params": params,
        })
    strategies.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
    return strategies[:TOP_N]


def save_monitoring_list(symbols: list[str]) -> None:
    """Save selected symbols for monitoring."""
    ensure_dir(MONITORING_LIST_FILE.parent)
    try:
        with open(MONITORING_LIST_FILE, "w", encoding="utf-8") as f:
            json.dump(symbols, f, ensure_ascii=False, indent=2)
        logging.info("[SELECT] monitoring list updated: %s", MONITORING_LIST_FILE)
    except Exception as exc:  # pragma: no cover - best effort
        logging.error("monitoring list 저장 실패: %s", exc)


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(SUMMARY_DIR)
    ensure_dir(PARAM_DIR)
    ensure_dir(OUT_DIR)
    setup_logger()

    selected = select_strategies()
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2)

    symbols = [s.get("symbol") for s in selected if s.get("symbol")]
    save_monitoring_list(symbols)

    logging.info("[SELECT] %d strategies saved", len(selected))


if __name__ == "__main__":
    main()
