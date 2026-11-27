"""故事頁的三張圖（Phase 8 plan 2026-11-26-001 Step 8.4b；`alpha.story_kit`）。

守三件事：
1. **三張圖的輸出各自過得了片段檢查**（寫入與物化兩道用的同一套規則）——圖是研究 session 貼進頁面的，過不了整頁就收不進帳；
   用到的 class 都在 story.css 裡有樣式（否則畫出來是黑塊或看不見）。
2. 同樣的輸入兩次輸出一字不差；空數列回一張寫明「沒有資料」的圖，不丟例外。
3. **讀圖不被騙**：股價是對數刻度（同樣的倍數同樣的高度）、畫到哪一天寫在圖上、那天之後的收盤與事件不畫；
   放不下的字換行、縮字或略過，不疊在一起。
"""
from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

import pytest

from alpha import story_kit as kit
from alpha.narrative import story_page as sp

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "story_page" / "ZZZZ"
HTML = (FIXTURE / "page.html").read_text(encoding="utf-8")
DECL = json.loads((FIXTURE / "page.json").read_text(encoding="utf-8"))
CORPUS = sp.normalize_for_match((FIXTURE / "source_excerpt.txt").read_text(encoding="utf-8"))
NAMES = {"co:zzzz_example": ["範例精密"], "co:pkg_a": ["封裝廠甲"], "co:pkg_b": ["封裝廠乙"]}

LADDER = kit.ladder_map([["範例精密（檢測機台）"], ["封裝廠甲", "封裝廠乙"], ["晶片設計公司（最終買家）"]],
                        focus="範例精密（檢測機台）")
BARS = kit.time_bars([("2023", 12.5), ("2024", 30.0), ("2025", None), ("2026E", 41.2)], "百萬美元",
                     highlight="2026E", highlight_label="公司財測")
PRICE = kit.price_log([("2025-01-02", 10.0), ("2025-06-02", 20.0), ("2025-12-01", 40.0), ("2026-03-02", 35.0)],
                      [("2025-06-02", "法說上調財測"), ("2026-03-02", "大客戶下單")], "2026-03-31", currency="美元")
EMPTY = {
    "ladder": kit.ladder_map([]),
    "bars": kit.time_bars([], "億元"),
    "bars_all_missing": kit.time_bars([("2024", None)], "億元"),
    "price": kit.price_log([], [], "2026-01-01"),
    "price_all_after_cutoff": kit.price_log([("2026-02-01", 10.0)], [], "2026-01-01"),
}


def _embed(chart: str) -> str:
    """把圖放進範例頁 q6 那一節的標題後面。"""
    start = HTML.index('<section id="q6">')
    end = HTML.index("</h2>", start) + len("</h2>")
    return HTML[:end] + "\n" + chart + HTML[end:]


def _classes(chart: str) -> set[str]:
    return {c for value in re.findall(r'class="([^"]+)"', chart) for c in value.split()}


def _texts(chart: str) -> list[tuple[float, float, str, str, int]]:
    """單行的 <text>：(x, y, anchor, 字, 字級)。"""
    out = []
    for attrs, body in re.findall(r"<text ([^>]*)>([^<]*)</text>", chart):
        get = dict(re.findall(r'([a-z-]+)="([^"]*)"', attrs))
        out.append((float(get["x"]), float(get["y"]), get.get("text-anchor", "start"), body,
                    int(get.get("font-size", 12))))
    return out


def _box(x: float, y: float, anchor: str, body: str, size: int) -> tuple[float, float, float, float]:
    w = kit.text_width(body, size)
    left = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
    return left, y - size, left + w, y


def _overlap(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

# ---------------------------------------------------------------- 1. 過得了片段檢查

@pytest.mark.parametrize("name, chart", [("ladder", LADDER), ("bars", BARS), ("price", PRICE),
                                         *[(f"empty_{k}", v) for k, v in EMPTY.items()]])
def test_each_chart_passes_the_fragment_check(name: str, chart: str) -> None:
    page = _embed(chart)
    assert sp.fragment_problems(page) == [], (name, [f.line() for f in sp.fragment_problems(page)])
    result = sp.check_page(page, DECL, company_names=NAMES, quote_corpus=CORPUS)
    assert result.errors == [], (name, [f.line() for f in result.errors])


def test_every_class_the_charts_use_has_a_style() -> None:
    css = (ROOT / "webapp" / "static" / "story.css").read_text(encoding="utf-8")
    used = set().union(*(_classes(c) for c in (LADDER, BARS, PRICE, *EMPTY.values())))
    assert used, "抓不到 class，這條守衛等於沒作用"
    missing = sorted(c for c in used if f".story-page svg .{c} " not in css)
    assert not missing, f"story.css 沒有這幾個 class 的樣式：{missing}"


def test_svg_title_holds_only_words() -> None:
    """svg 的 title 只放字（2026-11-26 R2 那一條）：公司名裡有角括號也不會變成標記。"""
    chart = kit.ladder_map([["A<script>"], ["B"]], focus="A<script>")
    assert "<script>" not in chart and "&lt;script&gt;" in chart
    assert sp.fragment_problems(_embed(chart)) == []

# ---------------------------------------------------------------- 2. 穩定、空的不丟例外

def test_the_same_input_draws_the_same_bytes() -> None:
    assert kit.ladder_map([["範例精密（檢測機台）"], ["封裝廠甲", "封裝廠乙"], ["晶片設計公司（最終買家）"]],
                          focus="範例精密（檢測機台）") == LADDER
    assert kit.time_bars([("2023", 12.5), ("2024", 30.0), ("2025", None), ("2026E", 41.2)], "百萬美元",
                         highlight="2026E", highlight_label="公司財測") == BARS
    assert kit.price_log([("2025-01-02", 10.0), ("2025-06-02", 20.0), ("2025-12-01", 40.0), ("2026-03-02", 35.0)],
                         [("2025-06-02", "法說上調財測"), ("2026-03-02", "大客戶下單")], "2026-03-31",
                         currency="美元") == PRICE


@pytest.mark.parametrize("name", sorted(EMPTY))
def test_empty_series_say_no_data(name: str) -> None:
    assert "沒有資料" in EMPTY[name]
    assert "畫到 2026-01-01" in EMPTY["price"]

# ---------------------------------------------------------------- 3. 讀圖不被騙

def _polyline(chart: str) -> list[tuple[float, float]]:
    points = re.search(r'<polyline [^>]*points="([^"]+)"', chart).group(1)
    return [tuple(float(v) for v in p.split(",")) for p in points.split()]


def test_price_is_on_a_log_scale() -> None:
    chart = kit.price_log([("2025-01-01", 10.0), ("2025-02-01", 100.0), ("2025-03-01", 1000.0)], [], "2025-03-01")
    (_x1, y1), (_x2, y2), (_x3, y3) = _polyline(chart)
    assert y1 > y2 > y3
    assert abs((y1 - y2) - (y2 - y3)) <= 0.2               # 十倍就是十倍：同樣的高度


def test_nothing_after_as_of_is_drawn_and_the_day_is_written() -> None:
    chart = kit.price_log([("2026-01-02", 10.0), ("2026-02-02", 20.0), ("2026-03-02", 40.0)],
                          [("2026-01-02", "看得到的事"), ("2026-03-02", "之後的事")], "2026-02-15")
    assert len(_polyline(chart)) == 2
    assert "畫到 2026-02-15" in chart and "看得到的事" in chart and "之後的事" not in chart


def test_events_on_the_same_day_are_stacked_not_overlapped() -> None:
    chart = kit.price_log([("2025-01-01", 10.0), ("2025-06-01", 12.0)],
                          [("2025-06-01", "甲"), ("2025-06-01", "乙"), ("2025-06-01", "丙")], "2025-06-30")
    centres = [(float(x), float(y)) for x, y in re.findall(r'<circle [^>]*cx="([^"]+)" cy="([^"]+)"', chart)]
    assert len(centres) == 3
    for (xa, ya), (xb, yb) in itertools.combinations(centres, 2):
        assert abs(xa - xb) >= 16 - 1e-6 or abs(ya - yb) >= 16 - 1e-6       # 直徑 14＋留 2
    assert "① 2025-06-01 甲" in chart and "③ 2025-06-01 丙" in chart


def test_events_stacked_near_the_top_do_not_climb_into_the_as_of_line() -> None:
    """2026-11-27 COHR：高點附近幾件事往上疊，圈疊進「畫到哪一天」那一行（手機寬自檢抓到）——疊不下就改放線下。"""
    chart = kit.price_log([("2026-01-01", 10.0), ("2026-06-01", 40.0), ("2026-06-10", 39.0), ("2026-12-01", 20.0)],
                          [("2026-06-01", "甲"), ("2026-06-02", "乙"), ("2026-06-10", "丙")], "2026-12-01")
    texts = _texts(chart)
    note = next(t for t in texts if t[3].startswith("畫到"))
    marks = [t for t in texts if t[3] in {"1", "2", "3"}]
    assert len(marks) == 3
    assert not any(_overlap(_box(*note), _box(*m)) for m in marks)
    centres = [(float(x), float(y)) for x, y in re.findall(r'<circle [^>]*cx="([^"]+)" cy="([^"]+)"', chart)]
    assert len(centres) == 3 and all(y - 7 >= note[1] for _x, y in centres)       # 圈的上緣不高過那一行的基線
    for (xa, ya), (xb, yb) in itertools.combinations(centres, 2):
        assert abs(xa - xb) >= 16 - 1e-6 or abs(ya - yb) >= 16 - 1e-6


def test_large_prices_fit_the_axis_and_narrow_ranges_still_have_ticks() -> None:
    def ticks(chart: str) -> list:
        return [t for t in _texts(chart) if t[2] == "end" and t[0] == 36.0]     # 左邊那一欄（plot_left − 4）

    won = kit.price_log([("2025-01-01", 150_000.0), ("2025-12-01", 260_000.0)], [], "2025-12-31", currency="韓元")
    assert ticks(won) and all("萬" in t[3] for t in ticks(won))
    assert all(_box(*t)[0] >= 0 for t in ticks(won))      # 沒有超出左邊
    narrow = kit.price_log([("2025-01-01", 102.0), ("2025-02-01", 108.0)], [], "2025-02-01")
    assert len(ticks(narrow)) >= 2                         # 區間窄到 1–2–5 一條都沒有：印最低與最高


def test_negative_bars_hang_below_zero_and_missing_ones_say_so() -> None:
    chart = kit.time_bars([("Q1", 5.0), ("Q2", -3.0), ("Q3", None), ("Q4", 8.0)], "百萬美元")
    zero = float(re.search(r'<line class="axis" [^>]*y1="([^"]+)"', chart).group(1))
    rects = [(float(y), float(h)) for y, h in re.findall(r'<rect class="bar" [^>]*y="([^"]+)" [^>]*height="([^"]+)"', chart)]
    assert any(abs(y - zero) < 0.2 for y, _h in rects)       # 負的那根從零往下
    assert "—" in chart and "Q3 —" in chart


def test_many_bars_do_not_print_numbers_or_periods_on_top_of_each_other() -> None:
    # 要標的幾根擠在一起：最小、最大、標色的、最新是最後四根（相鄰、高度幾乎一樣、都在邊界內）——不避讓就一定疊
    rows = [(f"{2019 + i // 4}Q{i % 4 + 1}", 5_000.0 + i * 10) for i in range(20)]
    rows += [("2024Q1", 100.0), ("2024Q2", 9_990.0), ("2024Q3", 9_950.0), ("2024Q4", 9_960.0)]
    chart = kit.time_bars(rows, "百萬美元", highlight="2024Q3")
    texts = [t for t in _texts(chart) if not t[3].startswith("單位")]
    assert len([t for t in texts if "," in t[3]]) >= 1                     # 數字有標（不是全略過了）
    boxes = [_box(*t) for t in texts]
    for a, b in itertools.combinations(boxes, 2):
        assert not _overlap(a, b), (a, b)
    assert all(0 <= b[0] and b[2] <= kit.WIDTH for b in boxes)


def test_long_names_wrap_or_shrink_inside_their_box() -> None:
    names = ["一家名字非常非常長的封裝與測試服務公司", "乙", "丙封裝（高階覆晶與晶圓級封裝）", "丁"]
    chart = kit.ladder_map([["主角"], names], focus="主角")
    rects = [tuple(float(v) for v in m) for m in
             re.findall(r'<rect class="tier[^"]*" x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)"', chart)]
    checked = 0
    for attrs, inner in re.findall(r"<text ([^>]*)>(.*?)</text>", chart):
        get = dict(re.findall(r'([a-z-]+)="([^"]*)"', attrs))
        size = int(get.get("font-size", 12))
        lines = re.findall(r"<tspan [^>]*>([^<]*)</tspan>", inner) or [inner]
        cx, ty = float(get["x"]), float(get["y"])
        # 同一格：橫向包住字的中心、縱向包住第一行的基線（只看橫向會配到最下面那排一整條的主角格）
        width = next(w for x, y, w, h in rects if x <= cx <= x + w and y <= ty <= y + h)
        assert all(kit.text_width(line, size) <= width - 8 + 0.01 for line in lines), (lines, size, width)
        checked += 1
    assert checked == 5
