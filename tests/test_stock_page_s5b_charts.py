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


def test_the_ruler_lives_in_b6_and_the_revenue_bars_in_b3() -> None:
    """2026-10-08 使用者：「對我來說都是營收，一起看最好」——營收柱與「出現在數字裡了嗎」搬到 B3 營收從哪來。"""
    visuals = _body("blockVisuals")
    assert "key === 'B6'" in visuals and "rulerChart(view)" in visuals
    assert "key === 'B3'" in visuals and "revenueBars(view)" in visuals and "key === 'B7'" not in visuals
    assert "blockVisuals(payload, view, block.key)" in _body("schemaBlock")


def test_the_charts_only_copy_audit_values() -> None:
    """參考尺的四個數與營收序列都照抄三題（materialize 端算好）；前端不算百分位、不算年增。"""
    ruler = _body("rulerChart")
    assert ":own_history_pctile" in ruler and ":cohort_median" in ruler
    assert "det.min" in ruler and "det.median" in ruler and "det.max" in ruler and "det.multiple_today" in ruler
    bars = _body("revenueBars")
    assert ":in_numbers_series" in bars and "p.yoy" in bars
    assert "det.currency" in bars       # 幣別由序列自己帶（alpha.three_questions._series_currency），這裡只翻成中文


def test_the_ruler_puts_every_mark_on_one_line_with_end_ticks() -> None:
    """2026-10-08 使用者（電腦上看）：「同組中位根本沒在線上」「最高跟最低是不是應該也要有線」——整把尺一條線，
    自家範圍的兩端、中位都有刻度線，同組中位的菱形畫在同一條線上（不另起一列）。"""
    ruler = _body("rulerChart")
    assert "'ruler-axis'" in ruler and "'ruler-end'" in ruler and "'ruler-median'" in ruler
    assert "[det.min, det.max].forEach" in ruler                       # 兩端各一條刻度線
    assert "ruler-cohort-line" not in ruler and "Y2" not in ruler       # 同組中位不再另起一列
    assert "chartWidth()" in ruler                                      # 照內容欄的寬 1:1 出圖（電腦上不縮在左邊）


def test_bar_charts_have_a_y_axis_named_for_the_series_and_no_legend_underneath() -> None:
    """2026-10-08 使用者：「柱狀圖直接用 Y 軸（雲端四大現金資本支出…）然後標量就好了，下面那一坨小字不用」。
    四張柱狀圖（錨、NVIDIA、吃到多少、營收）都走 `barChart`：左上是軸名與單位、左邊是刻度，圖下不放說明字。"""
    chart = _body("barChart")
    assert "'chart-axis-title'" in chart and "'chart-tick'" in chart and "niceTicks(" in chart
    assert "chart-legend" not in chart
    for fn in ("anchorBars", "captureFigure", "revenueBars"):
        body = _body(fn)
        assert "barChart(" in body and "chart-legend" not in body, fn


def test_the_demand_anchor_lives_in_b2_and_only_copies_the_materialized_series() -> None:
    """個股頁 S3a（2026-10-08）：B2「錨的變化」照抄 materialize 的 `demand_anchor`——前端不加總、不換算、不算年增；
    可知日、推算的是哪幾家、代理說明、走到哪個錨放進這一塊的細節（`chainDetail`），圖下不放字；沒有就照印缺席的原因。"""
    assert "key === 'B2'" in _body("blockVisuals") and "anchorFigures(payload)" in _body("blockVisuals")
    figures = _body("anchorFigures")
    assert "payload.demand_anchor" in figures and "demand.absence.reason" in figures
    bars = _body("anchorBars")
    for copied in ("p.value", "p.period", ".yoy", "s.components"):
        assert copied in bars, f"錨圖少照抄了 {copied}"
    detail = _body("chainDetail")
    for copied in ("payload.demand_anchor", "last.known_on", "last.derived", "s.proxy", "demand.anchors"):
        assert copied in detail, f"錨的細節少照抄了 {copied}"
    for body in (bars, detail):
        for arithmetic in ("value / ", "value - ", " / prior", "reduce((", "Math.pow"):
            assert arithmetic not in body, f"錨圖不得自己算：{arithmetic}"


def test_the_capture_chart_lives_in_b2_and_only_copies_the_materialized_ratio() -> None:
    """個股頁 S3b（2026-10-08）：B2「吃到多少」照抄 materialize 的 `capture`（比值、季均價、可知日都在 `alpha.capture` 算好）；
    前端不換匯、不相除——只有柱高的座標換算；換匯與可知日放在這一塊的細節；沒有就照印原因。"""
    assert "captureFigure(payload)" in _body("blockVisuals")
    figure = _body("captureFigure")
    for copied in ("payload.capture", "p.per_billion", "cap.absence.reason"):
        assert copied in figure, f"吃到多少少照抄了 {copied}"
    detail = _body("chainDetail")
    for copied in ("payload.capture", "last.per_usd", "last.known_on", "cap.revenue_source"):
        assert copied in detail, f"吃到多少的細節少照抄了 {copied}"
    for body in (figure, detail):
        for arithmetic in ("revenue_usd /", "/ p.anchor", "* 1e9", "/ last.per_usd", "Math.pow"):
            assert arithmetic not in body, f"吃到多少不得自己算：{arithmetic}"


def test_diagrams_show_as_images_in_b4_and_on_the_layer_page_labelled_as_illustration() -> None:
    """示意圖由 materialize 檢查過、編成 data URI；前端只用 <img> 顯示，不把 SVG 原碼塞進頁面（SVG 在 img 裡不執行任何東西）。
    2026-10-08 使用者：「我想知道它出現在示意圖的哪一個地方」——坐的那幾格疊一個「在這裡」框（位置換算，不改圖），上方一句列出是哪幾格。"""
    assert "key === 'B4'" in _body("blockVisuals") and "payload.diagrams" in _body("blockVisuals")
    figure = _body("diagramFigure")
    assert "document.createElement('img')" in figure and "img.src = d.src" in figure
    assert "innerHTML" not in figure and "示意｜" in figure and "出處" in figure
    assert "d.boxes" in figure and "'diagram-mark'" in figure and "在這裡" in figure and "在這張圖的" in figure
    layer = _body("renderLayerNote")
    assert "row.diagrams" in layer and "diagramFigure(d, [row.node]" in layer


def test_selfcheck_runs_only_on_request_and_never_touches_the_network() -> None:
    assert re.search(r"if \(/\[\?&\]selfcheck=1\\b/\.test\(window\.location\.search\)\) setTimeout\(selfCheck, 0\);", SOURCE)
    check = _body("selfCheck")
    for forbidden in ("fetch(", "getJSON(", "XMLHttpRequest", "localStorage", "sendBeacon"):
        assert forbidden not in check, forbidden
    assert "text_overlaps" in check and "page_overflow_px" in check
