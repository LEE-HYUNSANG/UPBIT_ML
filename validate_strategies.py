"""Verify strategy definitions against code."""

from __future__ import annotations

import inspect
import importlib

from strategy_loader import load_strategies


def main() -> None:
    specs = load_strategies()
    codes = importlib.import_module("bot.strategy")
    available = {name for name, _ in inspect.getmembers(codes, inspect.isfunction)}

    def _func_name(short_code: str) -> str:
        """Convert short code to function name."""
        return short_code.lower().replace("-", "_")

    missing = []
    for sc in specs:
        if _func_name(sc) not in available:
            missing.append(sc)
    if missing:
        print("[WARN] missing strategy implementations:", ", ".join(missing))
    else:
        print("All strategies implemented")


if __name__ == "__main__":
    main()

