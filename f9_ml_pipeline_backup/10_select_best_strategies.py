"""09단계 백테스트 결과에서 성과가 우수한 전략을 자동 선정한다."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils import ensure_dir

# 기본 경로 설정
PIPELINE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_ROOT.parent
SUMMARY_DIR = PIPELINE_ROOT / "ml_data" / "09_backtest"
PARAM_DIR = PIPELINE_ROOT / "ml_data" / "04_label"
OUT_DIR = PIPELINE_ROOT / "ml_data" / "10_selected"
OUT_FILE = OUT_DIR / "selected_strategies.json"
LOG_PATH = PIPELINE_ROOT / "logs" / "select_best_strategies.log"
MONITORING_LIST_FILE = PROJECT_ROOT / "config" / "f5_f1_monitoring_list.json"


# ----- 확장 포인트: 성과 기준과 정렬 기준 -----
# 테스트 용
# MIN_WIN_RATE = 0.35      # 승률 35% 이상
# MIN_AVG_ROI = -0.001     # 진입 1회당 -0.1% 이상
# MIN_SHARPE = 0.1         # 샤프비 0.1 이상
# MAX_MDD = 0.50           # 최대 낙폭 50% 이하
# MIN_ENTRIES = 1          # 최소 1회 진입
# TOP_N = 1               # 상위 10개 전략만 채택
# 상용 기본값
MIN_WIN_RATE = 0.50      # 승률 50% 이상
MIN_AVG_ROI = 0.001      # 진입 1회당 0.1% 이상
MIN_SHARPE = 1.0         # 샤프비 1.0 이상
MAX_MDD = 0.10           # 최대 낙폭 10% 이하
MIN_ENTRIES = 20         # 최소 50회 진입
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


def _to_float(value: object, default: float = 0.0) -> float:
    """Convert a value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - best effort
        return default


def passes_criteria(summary: dict) -> bool:
    """주어진 성과가 필터 조건을 통과하는지 확인."""
    win_rate = _to_float(summary.get("win_rate"))
    avg_roi = _to_float(summary.get("avg_roi"))
    sharpe = _to_float(summary.get("sharpe"))
    mdd = abs(_to_float(summary.get("mdd", summary.get("max_drawdown", 0))))
    entries = int(_to_float(summary.get("total_entries")))
    return (
        win_rate >= MIN_WIN_RATE
        and avg_roi >= MIN_AVG_ROI
        and sharpe >= MIN_SHARPE
        and mdd <= MAX_MDD
        and entries >= MIN_ENTRIES
    )


def select_strategies() -> list[dict]:
    """요건을 만족하는 전략을 정렬 후 반환."""
    logging.info("[SELECT] scanning summaries in %s", SUMMARY_DIR)
    strategies = []
    files = list(SUMMARY_DIR.glob("*_summary.json"))
    if not files:
        logging.info("[SELECT] no summary files found")
    for file in files:
        symbol = file.stem.split("_")[0]
        logging.info("[SELECT] processing %s", symbol)
        try:
            summary = load_json(file)
        except Exception as exc:  # pragma: no cover - best effort
            logging.warning("%s 로드 실패: %s", file, exc)
            continue
        if not passes_criteria(summary):
            logging.info("[SELECT] %s skipped", symbol)
            continue
        try:
            params = load_json(PARAM_DIR / f"{symbol}_best_params.json")
        except Exception:  # pragma: no cover - optional file
            params = {}
        record = {
            "symbol": symbol,
            "win_rate": summary.get("win_rate", 0.0),
            "avg_roi": summary.get("avg_roi", 0.0),
            "sharpe": summary.get("sharpe", 0.0),
            "max_drawdown": abs(summary.get("mdd", summary.get("max_drawdown", 0))),
            "total_entries": summary.get("total_entries", 0),
            "params": params,
        }
        strategies.append(record)
        logging.info(
            "[SELECT] added %s wr=%.2f roi=%.4f sharpe=%.2f entries=%s",
            symbol,
            record["win_rate"],
            record["avg_roi"],
            record["sharpe"],
            record["total_entries"],
        )
    strategies.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
    logging.info("[SELECT] %d candidates", len(strategies))
    return strategies[:TOP_N]


def save_monitoring_list(records: list[dict]) -> None:
    """Save selected strategies in monitoring list format."""
    ensure_dir(MONITORING_LIST_FILE.parent)
    data = []
    for rec in records:
        symbol = rec.get("symbol")
        params = rec.get("params", {})
        if symbol:
            data.append({
                "symbol": symbol,
                "thresh_pct": float(params.get("thresh_pct", 0)),
                "loss_pct": float(params.get("loss_pct", 0)),
            })
    try:
        with open(MONITORING_LIST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info("[SELECT] monitoring list updated: %s", MONITORING_LIST_FILE)
    except Exception as exc:  # pragma: no cover - best effort
        logging.error("monitoring list 저장 실패: %s", exc)


def write_json(path: Path, data: list[dict]) -> None:
    """Write data to JSON file, clearing existing contents."""
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    if data:
        symbols = [s.get("symbol") for s in data if s.get("symbol")]
        logging.info("[SELECT] wrote %s with %d entries: %s", path, len(data), symbols)
    else:
        logging.info("[SELECT] wrote %s (empty)", path)


def main() -> None:
    """실행 엔트리 포인트."""
    ensure_dir(SUMMARY_DIR)
    ensure_dir(PARAM_DIR)
    ensure_dir(OUT_DIR)
    setup_logger()

    logging.info("[SELECT] start")

    selected = select_strategies()
    write_json(OUT_FILE, selected)

    save_monitoring_list(selected)
    symbols = [s.get("symbol") for s in selected if s.get("symbol")]

    logging.info("[SELECT] %d strategies saved", len(selected))
    if selected:
        logging.info("[SELECT] symbols: %s", symbols)
    if not selected:
        logging.info("[SELECT] no strategies met criteria; files cleared")

    logging.info("[SELECT] done")


if __name__ == "__main__":
    main()
