"""
F4 RiskConfig - 리스크 파라미터 관리 및 핫리로드
"""
import json
import os
import time

class RiskConfig:
    def __init__(self, path):
        self.path = path
        self._cache = {}
        self._mtime = 0
        self.reload()

    def reload(self):
        """config/risk.json이 변경되면 즉시 재로드"""
        if not os.path.exists(self.path): return
        mtime = os.path.getmtime(self.path)
        if mtime != self._mtime:
            with open(self.path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            self._mtime = mtime

    def get(self, key, default=None):
        return self._cache.get(key, default)
