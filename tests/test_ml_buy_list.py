import f2_buy_signal as f2


def test_check_signals_basic(tmp_path, monkeypatch):
    csv = tmp_path / "KRW-AAA_pred.csv"
    csv.write_text("buy_signal,rsi14,ema5,ema20\n1,50,10,9\n")
    monkeypatch.setattr(f2, "PRED_DIR", tmp_path)
    result = f2.check_signals("KRW-AAA")
    assert result == {"signal1": True, "signal2": True, "signal3": True}


def test_check_signals_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(f2, "PRED_DIR", tmp_path)
    result = f2.check_signals("NONE")
    assert result == {"signal1": False, "signal2": False, "signal3": False}
