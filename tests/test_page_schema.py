"""個股頁 schema v1.0 的程式合約（2026-10-08，個股頁 plan 2026-10-05-003 S2；batch plan 2026-10-08-001 D8）。

驗收（S2 列）：七檔 × 元素有值或具名缺席 100%（稽核區）；字彙封閉性測試；變異（拿掉一個缺席宣告 → 紅）。
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from briefing.analyst_view import page_schema as ps

ROOT = Path(__file__).resolve().parent.parent


def test_the_contract_is_closed_and_complete() -> None:
    assert ps.check_schema() == []
    assert [b.key for b in ps.BLOCKS] == [f"B{i}" for i in range(13)]          # 十三塊（§5.3）
    assert {e.block for e in ps.ELEMENTS} == {b.key for b in ps.BLOCKS}


def test_removing_an_absence_declaration_turns_the_contract_red(monkeypatch) -> None:
    """驗收寫的那個變異：任何一個元素沒有缺席宣告（或寫成不能宣告的 kind）、沒寫在哪裡找過，合約自檢就紅。"""
    broken = dataclasses.replace(ps.ELEMENTS[0], absence="")
    monkeypatch.setattr(ps, "ELEMENTS", (broken, *ps.ELEMENTS[1:]))
    assert any("缺席宣告" in p for p in ps.check_schema())
    settled = dataclasses.replace(ps.ELEMENTS[1], absence="deliberate_abstention")   # 刻意不主張要有 Abstention 紀錄，合約不能宣告
    monkeypatch.setattr(ps, "ELEMENTS", (ps.ELEMENTS[0], settled, *ps.ELEMENTS[2:]))
    assert any("缺席宣告" in p for p in ps.check_schema())
    unlooked = dataclasses.replace(ps.ELEMENTS[0], looked=" ")
    monkeypatch.setattr(ps, "ELEMENTS", (unlooked, *ps.ELEMENTS[1:]))
    assert any("在哪裡找過" in p for p in ps.check_schema())


def test_the_evidence_level_map_covers_both_vocabularies(monkeypatch) -> None:
    from alpha.layer_note.contracts import EVIDENCE_LEVELS
    from query.bottleneck import EVIDENCE_RANK

    assert set(ps.EVIDENCE_LEVEL_MAP) == set(EVIDENCE_LEVELS)
    assert {c for row in ps.EVIDENCE_LEVEL_MAP.values() for c in row["graph"]} == set(EVIDENCE_RANK)
    trimmed = {k: v for k, v in ps.EVIDENCE_LEVEL_MAP.items() if k != "media"}
    monkeypatch.setattr(ps, "EVIDENCE_LEVEL_MAP", trimmed)
    assert any("證據等級對照表" in p for p in ps.check_schema())


def _view(**panels) -> dict:
    return {key: {"lines": lines} for key, lines in panels.items()}


def _line(key: str, status: str = "available", absence_kind: str | None = None) -> dict:
    return {"key": key, "datum": {"status": status, "absence_kind": absence_kind}}


def test_fill_rows_are_value_or_a_named_absence_and_copy_the_producers_kind() -> None:
    view = _view(
        candidate=[_line("candidate:state")],
        brief=[_line("brief:position", "missing", "not_yet_recorded")],
        wipeout=[_line("wipeout_debt", "not_modeled")],                     # 沒宣告 kind → status 查表
    )
    rows = {r["element"]: r for r in ps.fill_table(view, extra={"layer_notes": ["mat:inp_epiwafer"]})}
    assert rows["B0.candidate_state"]["state"] == "value"
    assert rows["B1.position"] == {**rows["B1.position"], "state": "absent", "absence_kind": "not_yet_recorded"}
    assert rows["B9.debt"]["absence_kind"] == "capability_absent"          # default_absence_kind("not_modeled")
    assert rows["B2.path_layers"]["absence_kind"] == "capability_absent" and "S3" in rows["B2.path_layers"]["looked"]
    assert rows["B4.layer_note"]["state"] == "value"
    assert all(r["state"] == "value" or (r["state"] == "absent" and r["absence_kind"]) for r in rows.values())


def test_an_unread_page_input_is_not_reported_as_nothing() -> None:
    rows = {r["element"]: r for r in ps.fill_table(_view())}
    assert rows["B4.layer_note"]["absence_kind"] == "upstream_unavailable" and "沒讀到" in rows["B4.layer_note"]["looked"]
    rows = {r["element"]: r for r in ps.fill_table(_view(), extra={"layer_notes": []})}
    assert rows["B4.layer_note"]["absence_kind"] == "not_yet_recorded"


def test_the_demand_anchor_cell_reads_the_page_input_three_ways() -> None:
    """個股頁 S3a（2026-10-08）：B2「錨的變化」讀頁外輸入 `@demand_anchor`——這一輪沒讀到（結構表或 Engine C 讀不到、
    回看的那天不推）＝`upstream_unavailable`；讀到但這家公司走不到錨或題材沒宣告序列＝`not_yet_recorded`；有序列＝有值。"""
    unread = {r["element"]: r for r in ps.fill_table(_view())}["B2.anchor_change"]
    empty = {r["element"]: r for r in ps.fill_table(_view(), extra={"demand_anchor": []})}["B2.anchor_change"]
    valued = {r["element"]: r for r in ps.fill_table(_view(), extra={"demand_anchor": ["hyperscaler_cash_capex"]})}
    assert unread["absence_kind"] == "upstream_unavailable"
    assert empty["absence_kind"] == "not_yet_recorded" and "demand_anchor_series" in empty["looked"]
    assert valued["B2.anchor_change"]["state"] == "value"


def test_the_capture_cell_reads_the_page_input_three_ways() -> None:
    """個股頁 S3b（2026-10-08）：B2「吃到多少」讀 `@capture_ratio`——沒讀到＝`upstream_unavailable`；讀到但沒有加總型的錨、
    沒有季營收或三者湊不齊＝`not_yet_recorded`；有值＝有值。"""
    unread = {r["element"]: r for r in ps.fill_table(_view())}["B2.capture_ratio"]
    empty = {r["element"]: r for r in ps.fill_table(_view(), extra={"capture_ratio": []})}["B2.capture_ratio"]
    valued = {r["element"]: r for r in ps.fill_table(_view(), extra={"capture_ratio": ["hyperscaler_cash_capex"]})}
    assert unread["absence_kind"] == "upstream_unavailable"
    assert empty["absence_kind"] == "not_yet_recorded" and "季均價" in empty["looked"]
    assert valued["B2.capture_ratio"]["state"] == "value"


def test_materialize_writes_the_fill_and_the_meta_carries_the_contract(tmp_path) -> None:
    from webapp.materialize import page_extra_for, write_vocabularies
    from webapp.store import ArtifactStore

    path = write_vocabularies(ArtifactStore(tmp_path))
    meta = json.loads(path.read_text(encoding="utf-8"))["page_schema"]
    assert meta["version"] == ps.PAGE_SCHEMA_VERSION and len(meta["elements"]) == len(ps.ELEMENTS)
    notes = {"rows": [{"node": "mat:x", "cited_by": {"pages": [{"ticker": "AXTI"}]}},
                      {"node": "mat:y", "cited_by": {"pages": [{"ticker": "IQE.L"}]}}]}
    assert page_extra_for("axti", notes) == {"layer_notes": ["mat:x"]}
    assert page_extra_for("AXTI", None) is None


@pytest.mark.parametrize("ticker", ["3081.TWO", "AXTI", "4979.TWO", "SIVE.ST", "AEHR", "3017.TW", "5802.T"])
def test_the_seven_test_set_pages_are_value_or_named_absence_everywhere(ticker: str) -> None:
    """S2 驗收：七檔測試集（schema §6）× 元素有值或具名缺席 100%。讀本機 materialize 過的 artifact；沒有就跳過（CI 無私有資料）。"""
    path = ROOT / "library" / "private" / "app" / "analyst_view" / f"{ticker}.json"
    if not path.exists():
        pytest.skip("本機沒有這一檔的 artifact（私有資料）")
    view = json.loads(path.read_text(encoding="utf-8"))["view"]
    summary = ps.fill_summary(ps.fill_table(view, extra={"layer_notes": []}))
    assert summary["unnamed"] == 0 and summary["value"] + summary["absent"] == len(ps.ELEMENTS)
