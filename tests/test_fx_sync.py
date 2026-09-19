"""FX 觀測同步（`scripts/sync_fx_observations.py`，2026-09-19）的 permission contract。

這支腳本是**無人值守會寫 append-only authority** 的東西，所以它能存在的唯一理由是
那道「只寫得了一個 mechanical 欄位」的閘門，而且那道閘門必須在腳本裡、不可由 CLI 繞過
（照 `scripts/backfill_fiscal_year_results.py` 2026-09-10 的先例；L15：放行與收緊必須同時發生）。

事發（2026-09-19）：四筆手抄的 `fx_rate` 觀測停在 09-11、過期 8 天，
6680.HK／HEXA-B.ST／XFAB.PA／XPEV 四檔的隱含報酬因此全部算不出來——
**而它不會壞、不會報錯、測試不會紅**（L17-1）。
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / ".codex" / "rules" / "stockbot-automations.rules"
SCRIPT = ROOT / "scripts" / "sync_fx_observations.py"


def _module():
    spec = importlib.util.spec_from_file_location("_fx_sync", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_it_can_only_ever_write_one_field_and_the_gate_is_in_the_script() -> None:
    """`FIELD` 是常數不夠——常數會被改，而改的人不會知道他同時改掉了一道人工 gate。"""
    module = _module()
    assert module.FIELD == "fx_rate"

    # registry 說它不是 mechanical 時，啟動就要死，不是寫完才發現
    from engine_c.observation_fields import get_observation_field_registry

    real = get_observation_field_registry().get("fx_rate")
    assert real is not None and real.verifiability == "mechanical", (
        "前提變了：fx_rate 不再是 mechanical，那這支腳本就不該存在於無人值守")

    class _Judgment:
        verifiability = "judgment"
        requires_user_approval = True

    import engine_c.observation_fields as fields_mod

    original = fields_mod.get_observation_field_registry
    try:
        fields_mod.get_observation_field_registry = lambda: {"fx_rate": _Judgment()}
        with pytest.raises(SystemExit) as caught:
            module._require_field_is_still_mechanical()
        assert "mechanical" in str(caught.value)
    finally:
        fields_mod.get_observation_field_registry = original


def test_no_cli_flag_can_swap_the_field_or_the_author() -> None:
    """surface 必須是「一個欄位」而不是「registry 裡所有 mechanical 欄位」。"""
    source = SCRIPT.read_text(encoding="utf-8")
    flags = set(re.findall(r'add_argument\("(--[a-z-]+)"', source))
    assert flags == {"--dry-run", "--format"}, f"多了可以換掉寫入目標的旗標：{flags}"
    assert "--field" not in source and "--author" not in source
    assert "--ticker" not in source, "標的也不得由 CLI 指定——幣別對必須從既有觀測導出"


def test_pairs_come_from_the_ledger_not_a_hand_written_list() -> None:
    """手寫清單會腐壞，而且新標的加進來時沒有人會記得改它（L16）。

    ⚠ **這條測行為，不掃原始碼字串。** 第一版寫成「原始碼裡不得出現 `6680.HK`」，
    當場被自己的 docstring 誤觸——那段字是事發記錄，不是一份清單。
    這正是 L15 記過的形狀：gate 攔到的是散文不是它想攔的東西，
    而修法是**改它問問題的方式**，不是把註解刪掉。
    """
    module = _module()

    class _FakeConn:
        def __init__(self, rows):
            self.rows = rows
            self.seen = []

        def execute(self, sql, params=()):
            self.seen.append((sql, params))
            return self

        def fetchall(self):
            return self.rows

    conn = _FakeConn([
        ("AAA.XX", '{"base": "JPY", "quote": "KRW", "rate": 9.1}'),
        ("BBB.YY", '{"base": "GBP", "quote": "CHF", "rate": 1.1}'),
        ("CCC.ZZ", "not json at all"),                      # 壞掉的一筆不讓整批停擺
        ("AAA.XX", '{"base": "JPY", "quote": "KRW", "rate": 9.2}'),   # 同一組去重
    ])
    pairs = module.known_pairs(conn)

    # 幣別對完全由 ledger 決定：餵什麼就得到什麼，腳本沒有自己的清單
    assert pairs == [("AAA.XX", "JPY", "KRW"), ("BBB.YY", "GBP", "CHF")]
    assert conn.seen and "manual_observations" in conn.seen[0][0]
    assert conn.seen[0][1] == ("fx_rate",)


def test_it_is_not_escalated_in_the_codex_sandbox() -> None:
    """它跑在獨立排程裡，**不需要** Codex 的 outside-sandbox rule。

    ⚠ 問的是「有沒有這樣一條 rule」，不是「檔案裡有沒有這串字」——
    掃 `pattern=[...]` 而不是全文（L15：gate 攔到的是散文不是權限）。
    """
    if not RULES.is_file():
        pytest.skip("本機沒有 .codex/rules")
    patterns = re.findall(r"pattern=\[(.*?)\]", RULES.read_text(encoding="utf-8"), re.S)
    assert patterns, "rules 檔解析不出任何 pattern——這條檢查會變成恆真"
    offenders = [p for p in patterns if "sync_fx_observations" in p]
    assert not offenders, f"FX 同步不走 Codex，卻出現在 rule pattern：{offenders}"


def test_report_counts_every_pair_and_never_drops_one_silently() -> None:
    """INV-3：每一組都要落在 written／skipped／failed 其中一格，加起來等於 input。"""
    module = _module()
    report = module.sync(dry_run=True)
    assert report["input"] == report["written"] + report["skipped"] + report["failed"] + sum(
        1 for r in report["rows"] if r["state"] == "would_write")
    assert set(report) >= {"input", "written", "skipped", "failed", "reasons", "rows"}
