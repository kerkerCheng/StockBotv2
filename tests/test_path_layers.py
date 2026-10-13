"""路徑上各層（個股頁 S3c，2026-10-09；`alpha/path_layers.py`）。

守：①路徑只收通到它坐的層的鏈（經過本公司就截在它之前；不經過本公司的依賴邊不收、照計數）；②層的年增只算那一季與
去年同季都有值的代表公司（固定成分），其餘逐家寫缺什麼；③單一公司比去年同一季、14 週的季不比；④只有錨那一節有值不算
「有值」（否則恆亮，L14-4）；⑤每個缺席 code 都在封閉字彙、種類過 check_absence_kind；⑥頁面合約拿掉同層各家變化（使用者 ①A）。"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.absence import check_absence_kind
from alpha.path_layers import HOP_ABSENCES, PAGE_ABSENCES, company_paths, fiscal_yoy, layer_yoy, page_path
from briefing.analyst_view import page_schema as ps
from webapp.materialize import page_extra_for

ROWS = [
    {"company_id": "co:cohr", "relation": "supplies_to", "chain": ["tech:ai_switch", "tech:cpo"]},
    {"company_id": "co:cohr", "relation": "supplies_to", "chain": ["tech:ai_switch", "tech:cpo"]},          # 同序列去重
    {"company_id": "co:cohr", "relation": "supplies_to", "chain": ["tech:x", "co:cohr"]},                    # 退回公司才走到
    {"company_id": "co:cohr", "relation": "constrained_by", "chain": ["tech:ai_switch", "tech:cpo", "co:cohr", "tech:inp"]},
    {"company_id": "co:cohr", "relation": "depends_on", "chain": ["tech:optical", "co:lite", "mat:inp_substrate"]},  # 上游
    {"company_id": "co:cohr", "relation": "supplies_to", "chain": []},
    {"company_id": "co:other", "relation": "supplies_to", "chain": ["tech:ai_switch", "co:nvidia"]},
]


def test_paths_stop_before_the_page_company_and_drop_input_side_chains() -> None:
    paths, dropped = company_paths(ROWS, "co:cohr")
    assert paths == [("tech:ai_switch", "tech:cpo"), ("tech:x",)]
    assert dropped == {"no_chain": 1, "input_side": 1}
    assert all("co:cohr" not in p for p in paths) and not any("mat:inp_substrate" in p for p in paths)


def test_a_layer_year_over_year_only_counts_companies_present_in_both_quarters() -> None:
    usd = {"co:a": {"2025Q2": {"usd": 100.0, "known_on": "2025-08-01"}, "2026Q2": {"usd": 150.0, "known_on": "2026-08-01"}},
           "co:b": {"2026Q2": {"usd": 999.0, "known_on": "2026-08-01"}}}
    out = layer_yoy(usd, ["co:a", "co:b", "co:c"], {"co:c": "分部「X」還沒有季營收序列"}, as_of=date(2026, 10, 9))
    point = out["points"][-1]
    assert point["period"] == "2026Q2" and point["yoy"] == pytest.approx(0.5) and point["members"] == ["co:a"]
    assert point["coverage"] == "1/3" and point["known_on"] == "2026-08-01"
    why = {m["company"]: m["reason"] for m in point["missing"]}
    assert "缺 2025Q2" in why["co:b"] and "分部" in why["co:c"]
    early = layer_yoy(usd, ["co:a"], {}, as_of=date(2026, 7, 31))        # 還不可知的那一季不算
    assert all(p["period"] != "2026Q2" for p in early["points"]) and "還不可知" in early["gaps"][-1]["reason"]


def test_a_single_company_compares_the_same_quarter_a_year_ago_and_skips_a_fourteen_week_quarter() -> None:
    rows = [{"period_start": "2025-03-30", "period_end": "2025-06-28", "value": 100.0, "currency": "USD", "filed": "2025-08-01"},
            {"period_start": "2026-03-29", "period_end": "2026-06-27", "value": 130.0, "currency": "USD", "filed": "2026-08-01"},
            {"period_start": "2024-12-29", "period_end": "2025-03-29", "value": 90.0, "currency": "USD", "filed": "2025-05-01"},
            {"period_start": "2025-12-21", "period_end": "2026-03-28", "value": 120.0, "currency": "USD", "filed": "2026-05-01"}]
    out = fiscal_yoy(rows, {}, as_of=date(2026, 10, 9))
    assert [p["period"] for p in out["points"]] == ["2026-06-27"] and out["points"][0]["yoy"] == pytest.approx(0.3)
    assert any("98 天" in g["reason"] for g in out["gaps"])                # 2026-03-28 那一季 98 天、去年同季 91 天


def test_only_non_anchor_values_count_and_every_absence_code_is_declared() -> None:
    hops = {"tech:ai_switch": {"kind": "anchor", "series": [{"yoy": 0.87}]},
            "tech:cpo": {"kind": "layer", "latest": None, "absence": {"code": "no_representatives_declared"}},
            "co:nvidia": {"kind": "company", "latest": {"yoy": 1.06}}}
    page = page_path([("tech:ai_switch", "tech:cpo")], {"no_chain": 0, "input_side": 0}, hops, page_company="co:cohr")
    assert page["valued_nodes"] == [] and page_extra_for("X", None, path_layers=page)["path_layers"] == []
    page2 = page_path([("tech:ai_switch", "co:nvidia")], {"no_chain": 0, "input_side": 0}, hops, page_company="co:cohr")
    assert page2["valued_nodes"] == ["co:nvidia"]
    assert page_path([("tech:ai_switch",)], {}, hops, page_company="co:mu")["absence"]["code"] == "sits_on_anchor"
    assert page_path([], {}, hops, page_company="co:x", in_structure=False)["absence"]["code"] == "not_in_structure"
    for table in (HOP_ABSENCES, PAGE_ABSENCES):
        for kind, _text in table.values():
            check_absence_kind(kind)
    # 一輪讀不到的整頁缺席不給頁外輸入（填得滿表印「這一輪沒讀到」，不是「沒有」）
    unread = {"absence": {"kind": "upstream_unavailable"}}
    assert "path_layers" not in (page_extra_for("X", None, path_layers=unread) or {})


def test_the_page_contract_drops_same_layer_peers_and_reads_the_path_input_three_ways() -> None:
    """使用者 2026-10-09 ①A：拿掉「同層各家變化」（10-05 回饋 #18：只是一堆年增數字，沒有內涵）。"""
    keys = {e.key for e in ps.ELEMENTS}
    assert "B2.peer_changes" not in keys and "B2.path_layers" in keys
    assert ps.PAGE_SCHEMA_VERSION == "stock-page-schema/1.1" and ps.check_schema() == []
    cell = lambda extra: {r["element"]: r for r in ps.fill_table({}, extra=extra)}["B2.path_layers"]  # noqa: E731
    assert cell({})["absence_kind"] == "upstream_unavailable"
    assert cell({"path_layers": []})["absence_kind"] == "not_yet_recorded" and "代表公司" in cell({"path_layers": []})["looked"]
    assert cell({"path_layers": ["co:nvidia"]})["state"] == "value"
