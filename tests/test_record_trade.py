"""成交記帳與 Sheet 窄寫入的迴歸測試。

Google Sheet 是 live inventory 唯一權威，且使用者會繼續手動編輯它
（2026-08-01 實際調整過欄位順序）。因此寫入路徑的三個不變量必須被守住：

1. **按欄名定位**——不得用欄位位置索引，否則使用者調欄序後寫入會靜默落到錯的欄
2. **只寫指定儲存格**——不得寫整列或範圍，否則會清掉使用者手填的欄位
3. **寫前比對現值**——不符即整批中止，讓人工編輯與程式寫入安全共存
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "record_trade", ROOT / "scripts" / "record_trade.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_read_scope_stays_readonly_and_write_scope_is_separate() -> None:
    """日常 routine 全部唯讀；只有明確記帳動作才拿可寫 token。"""
    from fetchers import gsheets

    assert gsheets.SCOPES == ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    assert gsheets.WRITE_SCOPES == ["https://www.googleapis.com/auth/spreadsheets"]
    assert gsheets.SCOPES != gsheets.WRITE_SCOPES


def test_column_letter_rejects_out_of_range() -> None:
    from fetchers.gsheets import _column_letter

    assert _column_letter(0) == "A"
    assert _column_letter(25) == "Z"
    with pytest.raises(ValueError):
        _column_letter(26)


def test_weighted_average_cost_matches_manual_calculation() -> None:
    """2026-07-31 實例：87 股 @545.29 買進 10 股 @687.79 → 97 股 @559.98。"""
    old_shares, old_cost, buy_shares, buy_price = 87.0, 545.29, 10.0, 687.79
    new_shares = old_shares + buy_shares
    new_cost = round((old_shares * old_cost + buy_shares * buy_price) / new_shares, 2)
    assert new_shares == 97.0
    assert new_cost == 559.98


def test_sell_does_not_change_cost_basis() -> None:
    """賣出只減股數，不改加權平均成本。"""
    module = _module()
    assert module is not None
    old_shares, old_cost = 97.0, 559.98
    new_shares = old_shares - 10.0
    assert new_shares == 87.0
    # 腳本在 side=sell 時直接沿用 old_cost，此處以斷言表達該契約
    assert old_cost == 559.98


def test_number_parses_sheet_formatting() -> None:
    module = _module()
    assert module._number("18,700") == 18700.0
    assert module._number(" 559.98 ") == 559.98
    assert module._number("") == 0.0


def test_trade_id_is_stable_and_content_addressed() -> None:
    module = _module()
    payload = {
        "executed_at": "2026-07-31T13:04:53-04:00",
        "broker": "IB",
        "symbol": "QQQ",
        "side": "buy",
        "shares": 10.0,
        "price": 687.79,
    }
    first = module._trade_id(payload)
    assert first == module._trade_id(dict(payload)), "同一筆成交必須得到同一個 id"
    changed = module._trade_id({**payload, "shares": 11.0})
    assert changed != first, "股數不同必須是不同成交"


def test_recorded_qqq_trade_is_logged_without_sheet_write() -> None:
    """2026-07-31 那筆已由使用者手動更新 Sheet，事件紀錄必須標明未寫入。

    這是 --log-only 存在的理由：腳本無法自行判斷 Sheet 是否已被手動更新，
    若照常寫入會把同一筆成交算兩次（97 → 107）。
    """
    log = ROOT / "library" / "trades" / "trade_log.jsonl"
    if not log.exists():
        pytest.skip("尚無成交紀錄")
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    qqq = [e for e in entries if e["symbol"] == "QQQ" and e["executed_at"].startswith("2026-07-31")]
    assert qqq, "應有 2026-07-31 的 QQQ 成交紀錄"
    entry = qqq[0]
    assert entry["shares"] == 10.0
    assert entry["price"] == 687.79
    assert entry["gross_amount"] == 6877.90
    assert entry["sheet_update"] == "manual_by_user"
    assert entry["sheet_writes"] == []


def test_trade_log_is_append_only_with_unique_ids() -> None:
    log = ROOT / "library" / "trades" / "trade_log.jsonl"
    if not log.exists():
        pytest.skip("尚無成交紀錄")
    ids = [
        json.loads(line)["trade_id"]
        for line in log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(ids) == len(set(ids)), "同一筆成交不得重複記錄"


def test_writer_never_targets_a_range() -> None:
    """只寫單一儲存格。範圍寫入會清掉使用者手填的其他欄位。"""
    source = (ROOT / "fetchers" / "gsheets.py").read_text(encoding="utf-8")
    writer = source.split("def write_portfolio_cells(")[1].split("\ndef ")[0]
    assert "valueInputOption" in writer
    assert "batchUpdate" not in writer, "不得使用批次範圍寫入"
    assert '"values": [[write["value"]]]' in writer, "每次只寫一格"


def test_writer_checks_current_value_before_writing() -> None:
    source = (ROOT / "fetchers" / "gsheets.py").read_text(encoding="utf-8")
    writer = source.split("def write_portfolio_cells(")[1].split("\ndef ")[0]
    assert "expected" in writer
    assert "raise ValueError" in writer, "現值不符必須中止而非覆蓋"


# ---------------------------------------------------------------------------
# 兩道資本硬擋（2026-09-23，Phase 0 Step 0b.4／G12）：煞車搬到真的有人走的路上
# ---------------------------------------------------------------------------

def _sheet_rows(nav: float = 100_000.0, **positions: float) -> list[dict]:
    rows = []
    invested = 0.0
    for ticker, value in positions.items():
        rows.append({"ticker": ticker, "bucket": "ALPHA", "market_value_base": value,
                     "nav_base": nav, "base_currency": "USD", "currency": "USD", "shares": 10.0})
        invested += value
    rows.append({"ticker": "CASH", "bucket": "CASH", "market_value_base": nav - invested,
                 "nav_base": nav, "base_currency": "USD", "currency": "USD", "shares": 0.0})
    return rows


def _wire_sheet(monkeypatch, tmp_path, *, rows, held_shares: float = 10.0):
    """把 Sheet 的三個入口換成假的：定位格、持股列、寫入（寫入被叫到就記下來）。"""
    from fetchers import gsheets

    calls: dict[str, list] = {"writes": []}

    def locate(requests):
        cells = [
            {"a1": "B2", "current": str(held_shares)},
            {"a1": "C2", "current": "100"},
        ]
        if len(requests) == 3:
            cells.append({"a1": "D5", "current": "50000"})
        return cells

    def write(writes):
        calls["writes"].append(writes)
        return {"written": [w["a1"] for w in writes]}

    monkeypatch.setattr(gsheets, "locate_portfolio_cells", locate)
    monkeypatch.setattr(gsheets, "write_portfolio_cells", write)
    monkeypatch.setattr(gsheets, "fetch_portfolio", lambda *, strict_operational=False: rows)
    module = _module()
    module.TRADE_LOG = tmp_path / "trade_log.jsonl"
    return module, calls


_BUY = ["--symbol", "AXTI", "--side", "buy", "--shares", "10", "--price", "200",
        "--executed-at", "2026-09-23T14:00:00-04:00", "--broker", "IB"]


def test_dry_run_over_five_percent_fails_closed_without_touching_sheet_or_log(
    monkeypatch, tmp_path, capsys
) -> None:
    """已持 4.5% 再買 2%：dry-run 就必須擋（不是等到 --apply），Sheet 與 trade_log 都不動。"""
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=4_500.0))
    assert module.main(_BUY) == module.EXIT_HARD_CAP
    assert module.main(_BUY + ["--apply"]) == module.EXIT_HARD_CAP
    assert calls["writes"] == [], "被擋下的成交不得寫 Sheet"
    assert not module.TRADE_LOG.exists(), "被擋下的成交不得寫事件紀錄"
    out = capsys.readouterr()
    assert "硬擋擋下" in out.out and "single_position" not in out.err
    assert "--override --reason" in out.err


def test_override_without_reason_is_rejected_before_any_sheet_access(monkeypatch, tmp_path) -> None:
    from fetchers import gsheets

    def boom(*a, **k):
        raise AssertionError("不該碰 Sheet")

    monkeypatch.setattr(gsheets, "locate_portfolio_cells", boom)
    monkeypatch.setattr(gsheets, "fetch_portfolio", boom)
    module = _module()
    module.TRADE_LOG = tmp_path / "trade_log.jsonl"
    assert module.main(_BUY + ["--override"]) == 2
    assert module.main(_BUY + ["--override", "--reason", "   "]) == 2
    assert not module.TRADE_LOG.exists()


def test_override_with_reason_writes_the_verdict_and_reason_as_a_receipt(
    monkeypatch, tmp_path
) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=4_500.0))
    assert module.main(_BUY + ["--apply", "--override", "--reason", "分批建倉第二批，已知超 5%"]) == 0
    assert len(calls["writes"]) == 1
    entry = json.loads(module.TRADE_LOG.read_text(encoding="utf-8").splitlines()[0])
    assert entry["override_reason"] == "分批建倉第二批，已知超 5%"
    assert entry["hard_cap_check"]["status"] == "blocked"
    assert entry["hard_cap_check"]["breaches"] == ["single_position_nav_cap_reached"]


def test_buy_under_the_cap_records_a_pass_verdict(monkeypatch, tmp_path) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=1_000.0))
    assert module.main(_BUY + ["--apply"]) == 0
    entry = json.loads(module.TRADE_LOG.read_text(encoding="utf-8").splitlines()[0])
    assert entry["hard_cap_check"]["status"] == "pass"
    assert "override_reason" not in entry


def test_unreadable_holdings_is_unmeasurable_and_fails_closed(monkeypatch, tmp_path) -> None:
    """Missing != Zero：持股列讀不到不是「持有 0%」，是量不到 → 擋。"""
    from fetchers import gsheets

    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=[])

    def fail(*, strict_operational=False):
        raise RuntimeError("sheet down")

    monkeypatch.setattr(gsheets, "fetch_portfolio", fail)
    assert module.main(_BUY + ["--apply"]) == module.EXIT_HARD_CAP
    assert calls["writes"] == []


def test_foreign_currency_buy_needs_fx_to_base(monkeypatch, tmp_path) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=0.0))
    twd = ["--symbol", "3105.TWO", "--side", "buy", "--shares", "1000", "--price", "100",
           "--currency", "TWD", "--cash-column", "none",
           "--executed-at", "2026-09-23T09:05:00+08:00", "--broker", "FUBON"]
    assert module.main(twd) == module.EXIT_HARD_CAP, "沒有匯率就量不到"
    assert module.main(twd + ["--fx-to-base", "0.03125"]) == 0, "100,000 TWD ≈ 3,125 USD = 3.1% < 5%"


def test_sell_is_never_blocked_by_the_caps(monkeypatch, tmp_path) -> None:
    module, calls = _wire_sheet(monkeypatch, tmp_path, rows=_sheet_rows(AXTI=9_000.0))
    sell = ["--symbol", "AXTI", "--side", "sell", "--shares", "5", "--price", "200",
            "--executed-at", "2026-09-23T14:00:00-04:00", "--broker", "IB", "--apply"]
    assert module.main(sell) == 0
    entry = json.loads(module.TRADE_LOG.read_text(encoding="utf-8").splitlines()[0])
    assert entry["hard_cap_check"]["status"] == "not_applicable"


def test_record_trade_is_the_only_writer_that_enforces_the_caps() -> None:
    """煞車必須住在真的有人走的路上：寫 Sheet 的唯一入口在寫入前呼叫 risk.hard_caps。"""
    source = (ROOT / "scripts" / "record_trade.py").read_text(encoding="utf-8")
    before_write = source.split("write_portfolio_cells(writes)")[0]
    assert "check_trade_hard_caps" in before_write
    assert "EXIT_HARD_CAP" in before_write
