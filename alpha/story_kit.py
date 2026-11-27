"""故事頁的三張圖（Phase 8 plan `docs/plans/2026-11-26-001-feat-phase8-story-page-app-plan.md` Step 8.4b）。

- `ladder_map`：誰賣給誰——由下往上幾排，主角標色。
- `time_bars`：量或錢的時間長條（可以有負的、可以缺）。
- `price_log`：對數股價折線＋編號事件，圖上寫明畫到哪一天。

純函式：呼叫的人把數列傳進來，回傳一段 `<figure><svg>…</svg><figcaption>…</figcaption></figure>`——只用片段白名單裡的標籤與屬性
（`alpha.narrative.story_page`；寫入與物化兩道照樣檢查），顏色只用 class（`webapp/static/story.css`：tier、focus、muted、line、
series-1、bar、bar-alt、grid、axis），寬度照手機（`viewBox` 寬 360）。不抓資料、不讀帳、不看今天的日期；同樣的輸入兩次輸出一字不差。
空數列回一張寫明「沒有資料」的圖，不丟例外。字寬是估的（全形一字＝字級、其餘約 0.6 字級）：放不下就換兩行、再縮字、最後才截斷；
會撞在一起的數字標籤照優先順序放、撞到的略過（值照樣在 aria-label 與圖說裡）。畫完照 skill 用 headless 的 390 寬自檢看一次疊字。
"""
from __future__ import annotations

import html
import math
import unicodedata
from datetime import date
from typing import Iterable, Sequence

WIDTH = 360
_PAD = 10
_FONT = 12
_SMALL = 11
_MIN_FONT = 9


# ---------------------------------------------------------------- 共用

def _f(value: float) -> str:
    """座標寫法固定（一位小數、去尾零）：同樣的輸入兩次輸出一字不差，檔案也不會被長小數撐大。"""
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def text_width(text: str, size: float = _FONT) -> float:
    """估字寬（px）：全形字一個字寬＝字級，其餘約 0.6 字級。只拿來判斷要不要換行、縮字或略過標籤。"""
    return sum(size if unicodedata.east_asian_width(ch) in ("W", "F") else size * 0.6 for ch in text)


def _split2(text: str) -> list[str]:
    """拆成兩行：離一半最近的自然斷點（括號前、空白頓號斜線與右括號後）；沒有就從字寬的一半斷。"""
    half = text_width(text) / 2
    best, best_gap = max(1, len(text) // 2), None
    for i in range(1, len(text)):
        natural = text[i - 1] in " 、／/）)" or text[i] in "（("
        gap = abs(text_width(text[:i]) - half) - (half if natural else 0)
        if best_gap is None or gap < best_gap:
            best, best_gap = i, gap
    return [text[:best].strip() or text[:best], text[best:].strip() or text[best:]]


def _fit(text: str, width: float, *, size: int = _FONT) -> tuple[list[str], int]:
    """放進 `width` 寬：一行 → 兩行 → 縮字 → 截斷（最後一招，加「…」）。回 (各行, 字級)。"""
    if text_width(text, size) <= width:
        return [text], size
    parts = _split2(text) if len(text) > 1 else [text]
    for candidate in range(min(size, _SMALL), _MIN_FONT - 1, -1):
        if max(text_width(p, candidate) for p in parts) <= width:
            return parts, candidate
    clipped = []
    for part in parts:
        while part and text_width(part + "…", _MIN_FONT) > width:
            part = part[:-1]
        clipped.append(part + "…")
    return clipped, _MIN_FONT


def _text(lines: Sequence[str], *, x: float, y: float, size: int, anchor: str = "middle",
          cls: str | None = None) -> str:
    """一段字（`y`＝第一行的基線）；兩行用 tspan。"""
    attrs = f'x="{_f(x)}" y="{_f(y)}" text-anchor="{anchor}"'
    if size != _FONT:
        attrs += f' font-size="{size}"'
    if cls:
        attrs += f' class="{cls}"'
    if len(lines) == 1:
        return f"<text {attrs}>{_esc(lines[0])}</text>"
    spans = [f'<tspan x="{_f(x)}" dy="{_f(0 if i == 0 else size * 1.2)}">{_esc(line)}</tspan>'
             for i, line in enumerate(lines)]
    return f"<text {attrs}>{''.join(spans)}</text>"


def _figure(height: float, label: str, body: Sequence[str], caption: str) -> str:
    # svg 的 title 只放字、字裡像標記的也擋（`story_page.SVG_TEXT_ONLY`）：名字裡的角括號在 title 裡換成全形
    words = label.replace("<", "＜").replace(">", "＞")
    return "\n".join([
        "<figure>",
        f'<svg viewBox="0 0 {WIDTH} {_f(height)}" role="img" aria-label="{_esc(label)}">',
        f"<title>{_esc(words)}</title>",
        *body,
        "</svg>",
        f"<figcaption>{_esc(caption)}</figcaption>",
        "</figure>",
    ])


def _empty(label: str, caption: str | None, note: str | None = None) -> str:
    body = [_text(["沒有資料"], x=WIDTH / 2, y=30, size=_FONT, cls="muted")]
    if note:
        body.append(_text([note], x=WIDTH / 2, y=48, size=10, cls="muted"))
    return _figure(60, f"{label}：沒有資料", body, caption or f"{label}：沒有資料。")


def _num(value: float) -> str:
    """值的寫法：整數加千分位；不是整數的留一位小數。"""
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    return f"{value:,.1f}"


def _short(value: float) -> str:
    """刻度字：一萬以上寫成「20萬」（韓股、日股的價位放得進左邊那一欄）。"""
    if abs(value) >= 10_000:
        return f"{value / 10_000:g}萬"
    return _num(value)


def _clear(box: tuple[float, float, float, float], placed: list[tuple[float, float, float, float]]) -> bool:
    """(左, 上, 右, 下) 跟已經放的都不重疊（留 2px）。"""
    left, top, right, bottom = box
    return all(right + 2 <= a or left - 2 >= c or bottom + 2 <= b or top - 2 >= d for a, b, c, d in placed)

# ---------------------------------------------------------------- 誰賣給誰

_ROW_H = 36
_GAP_Y = 26
_GAP_X = 8
_MAX_PER_ROW = 4


def ladder_map(tiers: Sequence[Sequence[str]], focus: str | Iterable[str] = (), *,
               links: Sequence[tuple[str, str]] | None = None, label: str = "誰賣給誰",
               caption: str | None = None) -> str:
    """誰賣給誰。`tiers` 由下往上給（第 0 排＝貨的起點，最後一排＝最終買家），每排一串名字；`focus` 的格標色。
    `links`＝(賣方, 買方) 成對（只畫買方在上面的）；沒給就把每一排連到上一排的每一格。一排超過四格時收成「另 N 家」
    （全名照樣在 aria-label）。"""
    rows = [[str(n).strip() for n in row if str(n).strip()] for row in tiers]
    rows = [row for row in rows if row]
    if not rows:
        return _empty(label, caption)
    focus_set = {focus} if isinstance(focus, str) else {str(f) for f in focus}
    shown = [row if len(row) <= _MAX_PER_ROW else row[:_MAX_PER_ROW - 1] + [f"另 {len(row) - _MAX_PER_ROW + 1} 家"]
             for row in rows]
    height = _PAD * 2 + len(shown) * _ROW_H + (len(shown) - 1) * _GAP_Y
    boxes: dict[str, list[tuple[float, float, int]]] = {}
    cells: list[str] = []
    for i, row in enumerate(shown):
        top = height - _PAD - (i + 1) * _ROW_H - i * _GAP_Y
        width = (WIDTH - 2 * _PAD - (len(row) - 1) * _GAP_X) / len(row)
        for j, name in enumerate(row):
            left = _PAD + j * (width + _GAP_X)
            cls = "tier focus" if name in focus_set else "tier"
            cells.append(f'<rect class="{cls}" x="{_f(left)}" y="{_f(top)}" width="{_f(width)}" '
                         f'height="{_ROW_H}" rx="4"></rect>')
            lines, size = _fit(name, width - 8)
            first = top + _ROW_H / 2 + size * 0.35 - (size * 0.6 if len(lines) == 2 else 0)
            cells.append(_text(lines, x=left + width / 2, y=first, size=size))
            boxes.setdefault(name, []).append((left + width / 2, top, i))
    pairs: list[tuple[str, str]] = list(links) if links is not None else [
        (low, high) for i in range(len(shown) - 1) for low in shown[i] for high in shown[i + 1]]
    edges: list[str] = []
    for seller, buyer in pairs:
        for sx, stop, si in boxes.get(seller, ()):
            for bx, btop, bi in boxes.get(buyer, ()):
                if bi > si:
                    edges.append(f'<line class="line" x1="{_f(sx)}" y1="{_f(stop)}" x2="{_f(bx)}" '
                                 f'y2="{_f(btop + _ROW_H)}"></line>')
    named = "；".join("、".join(row) for row in reversed(rows))
    return _figure(height, f"{label}（由上往下：{named}）", [*edges, *cells], caption or f"{label}：貨由下往上賣。")

# ---------------------------------------------------------------- 時間長條

_BARS_H = 170
_BARS_BOTTOM = 26


def time_bars(rows: Sequence[tuple[str, float | None]], unit: str, highlight: str | Iterable[str] = (), *,
              highlight_label: str = "標色的那幾根", label: str | None = None, caption: str | None = None) -> str:
    """量或錢的時間長條。`rows`＝(期間, 值) 由舊到新；值可以是負的（從零往下畫）、可以是 None（缺，印「—」）。
    `highlight` 的那幾根換色，圖上一行圖例寫 `highlight_label`（顏色不單獨帶意思）。值的字：六根以內全標，多了只標
    標色的、最新、最大、最小、最舊——撞在一起的照這個順序略過。"""
    data = [(str(k), None if v is None else float(v)) for k, v in rows]
    title = label or f"時間長條（{unit}）"
    present = [i for i, (_k, v) in enumerate(data) if v is not None]
    if not present:
        return _empty(title, caption)
    marked = {highlight} if isinstance(highlight, str) else {str(h) for h in highlight}
    values = [data[i][1] for i in present]
    low, high = min(0.0, min(values)), max(0.0, max(values))
    unit_text = f"單位：{unit}"
    legend_row2 = bool(marked) and text_width(unit_text, _SMALL) + text_width(highlight_label, _SMALL) + 40 > WIDTH - 2 * _PAD
    plot_top = 34 + (14 if legend_row2 else 0)
    plot_bottom = _BARS_H - _BARS_BOTTOM - (_SMALL + 4 if low < 0 else 0)

    def y_of(v: float) -> float:
        return plot_bottom - (v - low) / ((high - low) or 1.0) * (plot_bottom - plot_top)

    zero = y_of(0.0)
    n = len(data)
    slot = (WIDTH - 2 * _PAD) / n
    bar_w = min(36.0, slot * 0.62)
    body = [_text([unit_text], x=_PAD, y=14, size=_SMALL, anchor="start", cls="muted")]
    if marked:
        legend_y = 28 if legend_row2 else 14
        body.append(f'<rect class="bar-alt" x="{_f(WIDTH - _PAD - 10)}" y="{_f(legend_y - 9)}" width="10" height="10" '
                    'rx="2"></rect>')
        body.append(_text([highlight_label], x=WIDTH - _PAD - 14, y=legend_y, size=_SMALL, anchor="end", cls="muted"))
    body.append(f'<line class="axis" x1="{_PAD}" y1="{_f(zero)}" x2="{WIDTH - _PAD}" y2="{_f(zero)}"></line>')
    tops: dict[int, tuple[float, float]] = {}
    for i, (key, value) in enumerate(data):
        cx = _PAD + slot * (i + 0.5)
        if value is None:
            body.append(_text(["—"], x=cx, y=zero - 4, size=_SMALL, cls="muted"))
            continue
        top, bottom = sorted((y_of(value), zero))
        tops[i] = (top, bottom)
        body.append(f'<rect class="{"bar-alt" if key in marked else "bar"}" x="{_f(cx - bar_w / 2)}" y="{_f(top)}" '
                    f'width="{_f(bar_w)}" height="{_f(max(bottom - top, 1.0))}" rx="2"></rect>')
    # 值的字：照優先順序放，撞到的略過
    order = present if n <= 6 else list(dict.fromkeys(
        [i for i in reversed(present) if data[i][0] in marked]
        + [present[-1], max(present, key=lambda i: data[i][1]), min(present, key=lambda i: data[i][1]), present[0]]))
    placed: list[tuple[float, float, float, float]] = []
    for i in order:
        value = data[i][1]
        top, bottom = tops[i]
        cx = _PAD + slot * (i + 0.5)
        y = top - 4 if value >= 0 else bottom + _SMALL
        w = text_width(_num(value), _SMALL)
        box = (cx - w / 2, y - _SMALL, cx + w / 2, y)
        if box[0] >= 0 and box[2] <= WIDTH and _clear(box, placed):
            placed.append(box)
            body.append(_text([_num(value)], x=cx, y=y, size=_SMALL))
    # 期間的字：每 step 根一個（最新那根一定有），貼邊的往裡收
    label_w = max(text_width(k, _SMALL) for k, _v in data)
    step = max(1, math.ceil((label_w + 4) / slot))
    for i, (key, _value) in enumerate(data):
        if (n - 1 - i) % step:
            continue
        w = text_width(key, _SMALL)
        cx = min(max(_PAD + slot * (i + 0.5), w / 2 + 1), WIDTH - w / 2 - 1)
        body.append(_text([key], x=cx, y=_BARS_H - 8, size=_SMALL, cls="muted"))
    aria = f"{title}：" + "、".join(f"{k} {'—' if v is None else _num(v)}" for k, v in data)
    return _figure(_BARS_H, aria, body, caption or f"{title}，由舊到新。")

# ---------------------------------------------------------------- 對數股價

_PRICE_H = 218
_PRICE_LEFT = 40
_PRICE_TOP = 34          # 最高點上的事件圓圈不壓到「畫到哪一天」那一行
_PRICE_BOTTOM = 26
_MARK_R = 7
_MAX_POINTS = 360
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def _day(value: object) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _log_ticks(lo: float, hi: float, fallback: tuple[float, float]) -> list[float]:
    """1–2–5 刻度，落在 [lo, hi] 裡的；超過五條就隔一條取；不到兩條就印最低與最高（區間很窄時一條都沒有，讀者讀不到價位）。"""
    ticks = [m * 10 ** e for e in range(math.floor(math.log10(lo)) - 1, math.ceil(math.log10(hi)) + 1)
             for m in (1, 2, 5) if lo <= m * 10 ** e <= hi]
    while len(ticks) > 5:
        ticks = ticks[::2]
    return ticks if len(ticks) >= 2 else sorted(set(fallback))


def price_log(closes: Sequence[tuple[object, float | None]], events: Sequence[tuple[object, str]], as_of: object, *,
              currency: str | None = None, label: str = "股價（對數刻度）", caption: str | None = None) -> str:
    """對數股價折線（同樣的高度＝同樣的倍數）。`closes`＝(日期, 收盤)；`as_of` 之後的收盤與事件一律不畫（畫到哪一天寫在圖上）。
    `events`＝(日期, 一句) 在線上標 1、2…，那幾句照 ①②… 寫進圖說；離得太近的往上疊、不疊字。"""
    cutoff = _day(as_of)
    note = f"畫到 {cutoff.isoformat()}"
    points = sorted((_day(d), float(c)) for d, c in closes
                    if c is not None and float(c) > 0 and _day(d) <= cutoff)
    marks = sorted(((_day(d), str(text)) for d, text in events if _day(d) <= cutoff), key=lambda e: e[0])
    title = f"{label}（{currency}）" if currency else label
    if not points:
        return _empty(title, caption, note=note)
    first, last = points[0][0], points[-1][0]
    days = max((last - first).days, 1)
    lo, hi = min(c for _d, c in points), max(c for _d, c in points)
    log_lo, log_hi = math.log10(lo / 1.06), math.log10(hi * 1.06)
    plot_left, plot_right = _PRICE_LEFT, WIDTH - _PAD
    plot_top, plot_bottom = _PRICE_TOP, _PRICE_H - _PRICE_BOTTOM

    def x_of(day: date) -> float:
        return plot_left + (day - first).days / days * (plot_right - plot_left)

    def y_of(close: float) -> float:
        return plot_bottom - (math.log10(close) - log_lo) / ((log_hi - log_lo) or 1.0) * (plot_bottom - plot_top)

    def nearest(day: date) -> int:
        return min(range(len(points)), key=lambda i: (abs((points[i][0] - day).days), i))

    body = [_text([note], x=WIDTH - _PAD, y=14, size=_SMALL, anchor="end", cls="muted")]
    if currency:
        body.append(_text([f"單位：{currency}"], x=_PAD, y=14, size=_SMALL, anchor="start", cls="muted"))
    for tick in _log_ticks(lo / 1.06, hi * 1.06, (lo, hi)):
        y = y_of(tick)
        body.append(f'<line class="grid" x1="{_f(plot_left)}" y1="{_f(y)}" x2="{_f(plot_right)}" y2="{_f(y)}"></line>')
        body.append(_text([_short(tick)], x=plot_left - 4, y=y + 4, size=10, anchor="end", cls="muted"))
    step = max(1, math.ceil(len(points) / _MAX_POINTS))
    keep = {0, len(points) - 1} | set(range(0, len(points), step)) | {nearest(day) for day, _t in marks}
    line = " ".join(f"{_f(x_of(d))},{_f(y_of(c))}" for i, (d, c) in enumerate(points) if i in keep)
    body.append(f'<polyline class="series-1" stroke-width="2" points="{line}"></polyline>')
    body.append(_text([first.strftime("%Y-%m")], x=plot_left, y=_PRICE_H - 8, size=10, anchor="start", cls="muted"))
    body.append(_text([last.strftime("%Y-%m")], x=plot_right, y=_PRICE_H - 8, size=10, anchor="end", cls="muted"))
    placed: list[tuple[float, float]] = []
    legend = []
    def taken(x: float, y: float) -> bool:
        return any(abs(x - px) < _MARK_R * 2 + 2 and abs(y - py) < _MARK_R * 2 + 2 for px, py in placed)

    for n, (day, words) in enumerate(marks, 1):
        index = nearest(day)
        x, line_y = x_of(points[index][0]), y_of(points[index][1])
        y = line_y - _MARK_R - 4
        while taken(x, y):
            y -= _MARK_R * 2 + 2
        if y < _PRICE_TOP - _MARK_R - 4:        # 往上疊會壓到「畫到哪一天」那一行（2026-11-27 COHR）：改放線下、往下疊
            y = line_y + _MARK_R + 4
            while taken(x, y):
                y += _MARK_R * 2 + 2
        placed.append((x, y))
        body.append(f'<circle class="focus" cx="{_f(x)}" cy="{_f(y)}" r="{_MARK_R}"></circle>')
        body.append(_text([str(n)], x=x, y=y + 3.5, size=10))
        legend.append(f"{_CIRCLED[n - 1] if n <= len(_CIRCLED) else n} {day.isoformat()} {words}")
    text = caption or f"{title}：同樣的高度代表同樣的倍數，{note}。"
    if legend:
        text += "　" + "；".join(legend)
    aria = f"{title}，{first.isoformat()} 到 {last.isoformat()}，{_num(points[0][1])} 到 {_num(points[-1][1])}；{note}"
    return _figure(_PRICE_H, aria, body, text)


__all__ = ["WIDTH", "ladder_map", "price_log", "text_width", "time_bars"]
