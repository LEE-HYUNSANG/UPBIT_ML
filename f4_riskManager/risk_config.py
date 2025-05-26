"""
F4 RiskConfig - 리스크 파라미터 관리 및 핫리로드
"""
import json
import os


class RiskConfig:
    def __init__(self, path):
        self.path = path
        self._cache = {}
        self._mtime = 0
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
        """Reload ``config/risk.json`` if it has changed. Return True if updated."""
        if not os.path.exists(self.path):
            return False
        mtime = os.path.getmtime(self.path)
        if mtime != self._mtime:
            self._cache = self._load_json()
            self._mtime = mtime
            return True
        return False

    def get(self, key, default=None):
        return self._cache.get(key, default)
