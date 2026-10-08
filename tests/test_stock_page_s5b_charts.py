"""個股頁 S5b／S5c（2026-10-08）：圖住哪一塊、量測模式只讀不寫。

前端沒有 JS 測試環境（本機無 node）；這裡只鎖住「哪一塊畫哪張圖」「量測只在 `?selfcheck=1` 才跑、不連網」這兩個不該悄悄變的事，
畫得對不對由 headless Edge 的 `?selfcheck=1&w=390` 機械量測（溢出 0、字重疊 0）與截圖檢查。
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")


def _body(name: str) -> str:
    start = SOURCE.index(f"function {name}(")
    nxt = re.search(r"\n(?:async )?function |\nconst [A-Z_]+ =", SOURCE[start + 10:])
    return SOURCE[start: start + 10 + (nxt.start() if nxt else len(SOURCE))]


def test_the_ruler_lives_in_b6_and_the_revenue_bars_in_b7() -> None:
    visuals = _body("blockVisuals")
    assert "key === 'B6'" in visuals and "rulerChart(view)" in visuals
    assert "key === 'B7'" in visuals and "revenueBars(view)" in visuals
    assert "blockVisuals(view, block.key)" in _body("schemaBlock")


def test_the_charts_only_copy_audit_values() -> None:
    """參考尺的四個數與營收序列都照抄三題稽核區（materialize 端算好）；前端不算百分位、不算年增。"""
    ruler = _body("rulerChart")
    assert ":own_history_pctile" in ruler and ":cohort_median" in ruler
    assert "det.min" in ruler and "det.median" in ruler and "det.max" in ruler and "det.multiple_today" in ruler
    bars = _body("revenueBars")
    assert ":in_numbers_series" in bars and "p.yoy" in bars
    assert "det.currency" in bars       # 幣別由序列自己帶（alpha.three_questions._series_currency），這裡只翻成中文


def test_selfcheck_runs_only_on_request_and_never_touches_the_network() -> None:
    assert re.search(r"if \(/\[\?&\]selfcheck=1\\b/\.test\(window\.location\.search\)\) setTimeout\(selfCheck, 0\);", SOURCE)
    check = _body("selfCheck")
    for forbidden in ("fetch(", "getJSON(", "XMLHttpRequest", "localStorage", "sendBeacon"):
        assert forbidden not in check, forbidden
    assert "text_overlaps" in check and "page_overflow_px" in check
