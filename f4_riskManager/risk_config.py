"""
F4 RiskConfig - 리스크 파라미터 관리 및 핫리로드
"""
import json
import os


class RiskConfig:
    def __init__(self, path):
        self.path = path
        self._cache = {}
        self._mtime_ns = 0
        self.reload()

    def _load_json(self) -> dict:
        """Return JSON data from ``self.path`` allowing ``//`` comments."""
        with open(self.path, "r", encoding="utf-8") as f:
            lines = []
            for line in f:
                if "//" in line:
                    line = line.split("//", 1)[0]
                lines.append(line)
        text = "\n".join(lines)
        return json.loads(text or "{}")

    def reload(self):
        """Reload ``self.path`` if it has changed. Return True if updated."""
        if not os.path.exists(self.path):
            return False
        mtime_ns = os.stat(self.path).st_mtime_ns
        if mtime_ns != self._mtime_ns:
            self._cache = self._load_json()
            self._mtime_ns = mtime_ns
            return True
        try:
            new_data = self._load_json()
        except Exception:
            return False
        if new_data != self._cache:
            self._cache = new_data
            return True
        return False

    def get(self, key, default=None):
        return self._cache.get(key, default)
