"""Verify strategy definitions against code."""

from __future__ import annotations

import inspect
import importlib

from strategy_loader import load_strategies


def main() -> None:
    specs = load_strategies()
    codes = importlib.import_module("bot.strategy")
    available = {name for name, _ in inspect.getmembers(codes, inspect.isfunction)}
    missing = []
    for sc, spec in specs.items():
        if spec.short_code not in available:
            missing.append(spec.short_code)
    if missing:
        print("[WARN] missing strategy implementations:", ", ".join(missing))
    else:
        print("All strategies implemented")


if __name__ == "__main__":
    main()

