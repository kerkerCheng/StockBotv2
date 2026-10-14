"""營收從哪來（個股頁 S3d，2026-10-14；`alpha/revenue_mix.py`＋`alpha/providers/revenue_mix.py`）。

守：①占比只畫頂層 0..1 的數值鍵——總額（total_*）與 `_` 開頭的鍵照列「沒畫」，不當成一個分部；②前一次的占比只在名稱逐字對得上時帶；
③只取生效那一筆（被更正的不印）、同一觀測期兩筆生效不挑一個；④as-of 只看那天以前記錄的；⑤客戶與 backlog 的文字照抄、先印第一句；
⑥沒有觀測具名缺席；⑦頁面合約 B3 兩格讀頁外輸入；⑧前端只照抄。"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import date
from pathlib import Path

from alpha.providers.revenue_mix import revenue_mix
from alpha.revenue_mix import backlog_text, customers_text, headline, share_parts
from briefing.analyst_view import page_schema as ps
from webapp.materialize import page_extra_for

APP = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")


def _body(name: str) -> str:
    start = APP.index(f"function {name}(")
    nxt = re.search(r"\n(?:async )?function |\nconst [A-Z_]+ =", APP[start + 10:])
    return APP[start: start + 10 + (nxt.start() if nxt else len(APP))]


def _db(rows):
    from engine_c.manual_observations import ensure_manual_observation_schema

    conn = sqlite3.connect(":memory:")
    ensure_manual_observation_schema(conn)
    for oid, field, value, as_of, recorded, sup in rows:
        conn.execute("INSERT INTO manual_observations (observation_id, ticker, field_name, value, source_ref, as_of, author, "
                     "supersedes_id, recorded_at, payload_digest) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (oid, "X", field, value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
                      f"src-{oid}", as_of, "t", sup, recorded, f"d-{oid}"))
    return conn


def test_only_top_level_shares_are_drawn_and_previous_shares_match_by_name() -> None:
    out = share_parts({"磊晶片": 0.9921, "其他": 0.0079, "total_ntd_thousand": 2202822, "營收合計": 2202822, "_amounts": {"a": 1},
                       "fiscal_period": "FY2025"}, previous={"磊晶片": 0.9878, "舊名稱": 0.0122})
    assert [p["name"] for p in out["parts"]] == ["磊晶片", "其他"]
    assert out["parts"][0]["prev_share"] == 0.9878 and out["parts"][1]["prev_share"] is None
    assert out["ignored"] == ["_amounts", "total_ntd_thousand", "營收合計"] and out["period"] == "FY2025"


def test_text_is_copied_and_the_headline_is_the_first_sentence() -> None:
    text = "114 年度主要銷貨客戶：C06 25.76%；C09 21.01%；其他 29.50%。前四大合計 70.50%。"
    assert customers_text(text) == text and headline(text) == "114 年度主要銷貨客戶：C06 25.76%；C09 21.01%；其他 29.50%。"
    js = {"period": "1H2026", "customers": [{"label": "客戶甲", "pct_total_revenue": 13.35}], "top_two_combined_pct": 26.38,
          "judgment_note": "前兩大合計不到三成"}
    assert customers_text(js) == "1H2026：客戶甲 13.35%；前兩大合計 26.38%；前兩大合計不到三成"
    assert backlog_text({"has_order_book": False, "judgment_note": "按月議定"}) == "沒有揭露在手訂單（backlog）；按月議定"


def test_live_rows_only_superseded_and_conflicting_rows_are_not_printed_and_as_of_hides_later_records() -> None:
    conn = _db([
        ("a1", "product_line_revenue_share", {"磊晶片": 0.98, "其他": 0.02}, "2024-12-31", "2025-06-01T00:00:00+00:00", None),
        ("a2", "product_line_revenue_share", {"磊晶片": 0.97, "其他": 0.03}, "2025-12-31", "2026-06-01T00:00:00+00:00", None),
        ("a3", "product_line_revenue_share", {"磊晶片": 0.99, "其他": 0.01}, "2025-12-31", "2026-07-01T00:00:00+00:00", "a2"),
        ("c1", "customer_concentration", "前四大合計 70.50%。其他略。", "2025-12-31", "2026-06-01T00:00:00+00:00", None),
        ("c2", "customer_concentration", "另一筆同期生效的。", "2025-12-31", "2026-06-02T00:00:00+00:00", None),
    ])
    out = revenue_mix(conn, "X")
    latest = out["shares"][0]["points"][-1]
    assert latest["parts"][0] == {"name": "磊晶片", "share": 0.99, "prev_share": 0.98}      # 更正後那一筆、前一次對得上
    assert out["customers"] is None and out["conflicts"][0]["ids"] == ["c1", "c2"]          # 同期兩筆生效：不挑一個
    assert out["backlog"] is None and "backlog" in out["absences"]["backlog"]["reason"]
    early = revenue_mix(conn, "X", as_of=date(2026, 6, 15))                                  # 更正還沒寫：看到原本那一筆
    assert early["shares"][0]["points"][-1]["parts"][0]["share"] == 0.97
    none = revenue_mix(conn, "X", as_of=date(2025, 1, 1))
    assert none["shares"] == [] and "占比" in none["absences"]["shares"]["reason"]


def test_the_page_contract_reads_revenue_mix_and_backlog_from_the_page_input() -> None:
    mix = {"shares": [{"field": "segment_revenue_share"}], "customers": {"as_of": "2025-12-31"}, "backlog": None}
    extra = page_extra_for("X", None, revenue_mix=mix)
    rows = {r["element"]: r for r in ps.fill_table({}, extra=extra)}
    assert rows["B3.revenue_mix"]["state"] == "value" and rows["B3.backlog"]["absence_kind"] == "not_yet_recorded"
    unread = page_extra_for("X", None, revenue_mix={"unread": {"kind": "upstream_unavailable"}}) or {}
    rows = {r["element"]: r for r in ps.fill_table({}, extra=unread)}
    assert rows["B3.revenue_mix"]["absence_kind"] == "upstream_unavailable"                  # 讀不到≠沒有紀錄


def test_the_b3_figures_only_copy_the_materialized_mix() -> None:
    assert "mixFigures(payload)" in _body("blockVisuals") and "mixDetail(payload)" in _body("blockDetail")
    fig = _body("mixFigures")
    for copied in ("payload.revenue_mix", "p.share", "p.prev_share", "item.headline", "mix.absences", "mix.conflicts"):
        assert copied in fig, copied
    for forbidden in (".sort(", "value / ", "reduce(("):
        assert forbidden not in fig and forbidden not in _body("mixDetail"), forbidden


def test_a_long_first_sentence_is_cut_at_the_last_separator_that_fits() -> None:
    long = "主要銷貨客戶：" + "；".join(f"C{i:02d} 567,378 千元 25.76%" for i in range(1, 12)) + "。"
    out = headline(long)
    assert out.endswith("；…") and len(out) <= 122 and out.count("；") >= 3
