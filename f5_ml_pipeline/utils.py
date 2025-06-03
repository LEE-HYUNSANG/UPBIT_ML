"""공용 유틸리티 함수 모음."""
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
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


def save_parquet_atomic(df: "pd.DataFrame", path: str | Path) -> None:
    """Write DataFrame to ``path`` using a temporary file to avoid corruption."""
    from pandas import DataFrame  # local import to avoid heavy dependency at module load
    target = Path(path)
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        assert isinstance(df, DataFrame)  # type: ignore
        df.to_parquet(tmp, index=False)
        tmp.replace(target)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


try:  # pragma: no cover - platform dependent
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - Windows
    fcntl = None  # type: ignore
    import msvcrt


@contextmanager
def file_lock(path: str | Path):
    """Context manager providing an exclusive lock on ``path``."""
    lock_path = Path(path)
    fh = lock_path.open("w")
    try:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_EX)
        else:  # pragma: no cover - Windows
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        yield fh
    finally:
        try:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_UN)
            else:  # pragma: no cover - Windows
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            fh.close()
