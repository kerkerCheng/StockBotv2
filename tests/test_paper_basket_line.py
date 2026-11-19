"""短版 ④ 每週一行「紙上籃子」（使用者 2026-11-19「a OK」）。

1. 數字由 outcome 腳本算好（`_by_state` 的每組多兩格：對主題等權組超額、量測起始），心跳照抄、不另算（L16）。
2. 只在週一印；其他天不印。
3. 缺席各自說，不印 0（INV-3）：artifact 讀不到、沒有 paper lane、早於分組、可開 0 檔、量得到 0 檔、舊 artifact 沒有新格。
4. 只認寫下那天說「可開」的組（當時寫的字，INV-6）；11-03 前寫「等回落」的另說，不併進來。
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _outcome():
    spec = importlib.util.spec_from_file_location("oist_paper_basket", ROOT / "scripts" / "outcome_if_settled_today.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(ticker: str, state: str, ret: float | None, *, cohort: float | None = None,
         anchor: date = date(2026, 11, 3)) -> dict:
    return {"ticker": ticker, "anchor_state": state, "absolute_return": ret, "excess_QQQ": None if ret is None else ret - 0.01,
            "excess_theme_cohort": cohort, "anchor_date": anchor}


# ---- 1. producer：每組多兩格 ---------------------------------------------------------------------
def test_each_anchor_group_carries_cohort_excess_and_start() -> None:
    oist = _outcome()
    rows = [_row("A", "open", 0.10, cohort=0.04, anchor=date(2026, 11, 5)),
            _row("B", "open", -0.20, cohort=None, anchor=date(2026, 11, 3)),
            _row("C", "open", None),                                         # 量不到：不進起始、不進超額分母
            _row("D", "pass", 0.50, cohort=0.30)]
    groups = oist._by_state(rows, key="anchor_state", missing="unknown", lane="paper")
    open_ = groups["open"]
    assert open_["n"] == 3 and open_["aggregate"]["measured"] == 2
    assert open_["theme_cohort_excess"] == {"n": 1, "of": 2, "mean": 0.04}
    assert open_["measurement_start"] == "2026-11-03"
    assert abs(open_["aggregate"]["absolute"] - (-0.05)) < 1e-12
    assert groups["pass"]["theme_cohort_excess"]["mean"] == 0.30          # 各組分母分開


# ---- 3＋4. 心跳那一行 ----------------------------------------------------------------------------
def _line(monkeypatch, payload, absence=None) -> str:
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "_load_state", lambda state_dir, kind: (payload, absence))
    return hb.paper_basket_line(None)


def _payload(groups: dict | None) -> dict:
    return {"lanes": {"paper": {"n": 9, "by_anchor_state": groups}}}


def test_the_line_copies_the_open_group(monkeypatch) -> None:
    group = {"n": 4, "aggregate": {"absolute": 0.123, "excess": -0.045, "benchmark": "QQQ", "measured": 4},
             "reached_2x_ever": 0, "small_sample": True,
             "theme_cohort_excess": {"n": 3, "of": 4, "mean": 0.02}, "measurement_start": "2026-11-03"}
    text = _line(monkeypatch, _payload({"open": group, "priced_wait": {"n": 2}}))
    for must in ("寫下時說可開的 4 檔", "+12.3%", "對 QQQ -4.5%", "對主題組 +2.0%（3/4 檔）", "曾達 2 倍 0",
                 "量得到 4/4", "起始 2026-11-03", "小樣本", "「等回落」的 2 檔不在內", "只印不判"):
        assert must in text, must


def test_absences_are_said_not_zero(monkeypatch) -> None:
    from crons.heartbeat import Absence

    assert "讀不到" in _line(monkeypatch, {}, Absence("upstream_unavailable", "positions artifact 讀不到：x"))
    assert "沒有 paper lane" in _line(monkeypatch, {"lanes": {}})
    assert "早於" in _line(monkeypatch, _payload(None))
    assert "說可開 0 檔" in _line(monkeypatch, _payload({"pass": {"n": 3}}))
    none_measured = {"n": 2, "aggregate": {"measured": 0}}
    assert "量得到報酬的 0 檔——不是 0%" in _line(monkeypatch, _payload({"open": none_measured}))
    old = {"n": 2, "aggregate": {"absolute": 0.1, "excess": 0.0, "benchmark": "QQQ", "measured": 2}}
    text = _line(monkeypatch, _payload({"open": old}))
    assert "對主題組：artifact 還沒有這一格" in text and "起始 artifact 還沒有這一格" in text


# ---- 2. 只在週一印 -------------------------------------------------------------------------------
def _compose(tmp_path, monkeypatch, now: datetime) -> str:
    from crons import daily_brief
    from crons import heartbeat as hb

    monkeypatch.setattr(hb, "watch_today_counts", lambda **_kw: {"woken": 0, "expired": 0, "semantic_flagged": 0})
    monkeypatch.setattr(hb, "quota_entries", lambda rows, now: [])
    monkeypatch.setattr(hb, "paper_basket_line", lambda state_dir: "紙上籃子（測試）")
    leads_path = tmp_path / "pending_leads.json"
    leads_path.write_text(json.dumps({"leads": {}, "harvest_log": []}), encoding="utf-8")
    text = daily_brief.compose_brief(now=now, summary="Daily｜球在你 0", snapshot={},
                                     run_record_path=tmp_path / "missing.json", leads_path=leads_path,
                                     heartbeat_dir=tmp_path)
    return text.split("### ④ 狀態與健康度", 1)[1].split("### ⑤", 1)[0]


def test_only_monday_prints_the_line(tmp_path, monkeypatch) -> None:
    monday = datetime(2026, 11, 23, 1, 0, tzinfo=timezone.utc)             # 台北 2026-11-23 週一 09:00
    thursday = datetime(2026, 11, 19, 1, 0, tzinfo=timezone.utc)
    assert "- 紙上籃子（測試）" in _compose(tmp_path, monkeypatch, monday)
    assert "紙上籃子" not in _compose(tmp_path, monkeypatch, thursday)
