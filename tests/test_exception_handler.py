import os
import sys
import json
from urllib.parse import urlencode

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import f3_order.exception_handler as eh
from f3_order.exception_handler import ExceptionHandler


def _make_handler(monkeypatch):
    env = {"TELEGRAM_TOKEN": "TOKEN", "TELEGRAM_CHAT_ID": "CHAT"}
    monkeypatch.setattr(eh, "load_env", lambda: env)
    return ExceptionHandler({"SLIP_MAX": 0.05, "SLIP_FAIL_MAX": 2})


def _patch_sender(monkeypatch, calls):
    if eh.requests:
        def fake_post(url, data=None, timeout=None):
            calls.append({"url": url, "data": data, "timeout": timeout})
        monkeypatch.setattr(eh.requests, "post", fake_post)
    else:
        def fake_request(url, data=None):
            calls.append({"url": url, "data": data})
            class Dummy: pass
            return Dummy()
        def fake_urlopen(req, timeout=None):
            calls[-1]["timeout"] = timeout
        monkeypatch.setattr(eh._urlreq, "Request", fake_request)
        monkeypatch.setattr(eh._urlreq, "urlopen", fake_urlopen)


def test_send_alert_uses_telegram_api(monkeypatch):
    calls = []
    _patch_sender(monkeypatch, calls)
    handler = _make_handler(monkeypatch)
    handler.send_alert("hello", "warning")

    expected_url = "https://api.telegram.org/botTOKEN/sendMessage"
    if eh.requests:
        assert calls[0]["url"] == expected_url
        assert calls[0]["data"] == {"chat_id": "CHAT", "text": "[WARNING] hello"}
        assert calls[0]["timeout"] == 5
    else:
        assert calls[0]["url"] == expected_url
        assert calls[0]["data"] == urlencode({"chat_id": "CHAT", "text": "[WARNING] hello"}).encode()
        assert calls[0]["timeout"] == 5


def test_slippage_triggers_alert(monkeypatch):
    calls = []
    _patch_sender(monkeypatch, calls)
    handler = _make_handler(monkeypatch)

    order = {"slippage_pct": 0.1}
    handler.handle_slippage("KRW-BTC", order)
    assert calls == []
    handler.handle_slippage("KRW-BTC", order)

    expected_msg = "Slippage 0.10% for KRW-BTC (count 2)"
    expected_url = "https://api.telegram.org/botTOKEN/sendMessage"
    if eh.requests:
        assert calls[0] == {"url": expected_url, "data": {"chat_id": "CHAT", "text": f"[WARNING] {expected_msg}"}, "timeout": 5}
    else:
        assert calls[0]["url"] == expected_url
        assert calls[0]["data"] == urlencode({"chat_id": "CHAT", "text": f"[WARNING] {expected_msg}"}).encode()
        assert calls[0]["timeout"] == 5
    assert handler.slippage_count["KRW-BTC"] == 2


def test_log_event_writes_to_default_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(eh, "load_env", lambda: {})
    handler = ExceptionHandler({})
    handler._log_event({"event": "Test"})

    log_path = tmp_path / "logs" / "events.jsonl"
    assert log_path.exists()
    with log_path.open("r", encoding="utf-8") as f:
        data = json.loads(f.readline())
    assert data["event"] == "Test"
