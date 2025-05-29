"""공용 유틸리티 함수 모음."""
from datetime import datetime
from pathlib import Path
from typing import Any


def _convert_value(val: str) -> Any:
    """Convert YAML scalar to int, float, bool or str."""
    lowered = val.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return val


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse a very small subset of YAML used for configs."""
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip())
            key, _, value = raw.lstrip().partition(":")
            key = key.strip()
            value = value.strip()
            while indent <= stack[-1][0] and len(stack) > 1:
                stack.pop()
            parent = stack[-1][1]
            if value == "":
                new_dict: dict[str, Any] = {}
                parent[key] = new_dict
                stack.append((indent, new_dict))
            else:
                parent[key] = _convert_value(value)
    return result


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file without requiring PyYAML."""
    path = Path(path)
    try:  # pragma: no cover - missing dependency in CI
        import yaml  # type: ignore
    except Exception:
        return _parse_simple_yaml(path)
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return _parse_simple_yaml(path)


def timestamp() -> str:
    """현재 시간을 YYYYMMDDHHMMSS 형식으로 반환."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def ensure_dir(path: str | Path) -> Path:
    """폴더가 없으면 생성 후 Path 객체 반환."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
