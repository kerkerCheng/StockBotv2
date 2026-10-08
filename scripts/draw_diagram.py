"""照說明檔的 `layout` 畫技術示意圖（個股頁 S5b 第二段；研究 session 用）。

`library/private/research_notes/diagrams/<id>.json` 的 `layout.steps` 是一條由上往下的鏈，每一步是一個方框或一個箭頭：

    {"box": "light", "title": "雷射晶片", "desc": "…", "suppliers": ["Coherent、聯亞（CW DFB）"],
     "nodes": ["tech:cw_dfb_laser", "tech:eml"],
     "dashed": false, "inner": [{"title": "…", "desc": "…", "suppliers": [...], "nodes": [...]}]}
    {"arrow": "從磊晶片切出"}

`box` 是配色（elec／light／mat／heat／power／note／gray）；`suppliers` 照圖上真的有的供貨邊寫（附「列舉不完整」），
空的就印「這一層還沒有供應商」。`nodes`＝這一格畫的是圖上哪幾個節點（一個節點只畫在一格；全部格的聯集＝`nodes_shown`），
個股頁據此標「這檔在這裡」（2026-10-08 使用者：「我想知道它出現在示意圖的哪一個地方」）。
畫好寫 `<id>.svg`、把每一格的位置表（`geometry`：格名、節點、上緣、高、左緣、寬，綁這張 SVG 的 sha256）寫回說明檔，
接著跑 `scripts/check_diagrams.py` 的量測並寫量測紀錄——不合格 exit 1（規則 9：字不重疊、不出框、不壓框線，0 才發佈）。
只寫這三個私有檔，不寫任何 authority。

直式、寬 360（手機）；字寬用估計值斷行（中文 1em、英文 0.56–0.68em），英文字與數字不拆開、收尾標點不放行首、
開頭括號不放行尾。估計不準的地方由量測抓——這裡只負責「大多數時候一次就過」。

用法：python scripts/draw_diagram.py <id> [<id> ...]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from webapp.diagrams import DIAGRAM_DIR, NODE_PREFIXES, svg_digest  # noqa: E402

W = 360
X0, X1 = 12, 348          # 方框左右
PAD = 12                  # 方框內留白
INNER_PAD = 8             # 框中框內留白
INNER_GAP = 8             # 框中框與上下文字之間
LINE_GAP = 2              # 上一行的字框底到下一行的字框頂
ASC, DSC = 1.08, 0.26     # 字框估計：baseline 往上 1.08em、往下 0.26em（Windows 上 SVG 文字框照第一個可用字型 Segoe UI）
INK, MUTED = "#1f2328", "#57606a"
FILL = {"elec": "#e8f0fe", "light": "#e6f4ea", "mat": "#fdf1df", "heat": "#fde7e7", "power": "#efe7fb",
        "note": "#ffffff", "gray": "#f2f4f7"}
STROKE = {"elec": "#9db8ef", "light": "#9fd0ad", "mat": "#efc98e", "heat": "#f0a7a7", "power": "#c7b2ee",
          "note": "#9aa4b2", "gray": "#c9d1db"}
FONT = "-apple-system, Segoe UI, Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif"

# 英文字／數字整段是一個 token（含重音字母，例如 Stäubli）；其他每個字自己一個
_TOKEN = re.compile(r"[A-Za-z0-9À-ɏ][A-Za-z0-9À-ɏ.\-'’&/+]*|\s+|.", re.S)
_NO_LINE_START = frozenset("）」』、。，；：！？)]}%")
_NO_LINE_END = frozenset("（「『([{→")
_SOFT_BREAK_AFTER = frozenset("、，；）：。")


def text_width(s: str, size: float) -> float:
    w = 0.0
    for ch in s:
        if ord(ch) >= 0x2000:          # 中文、全形標點、箭頭與破折號：當一個字寬
            w += size
        elif ch == " ":
            w += size * 0.3
        elif ch.isdigit():
            w += size * 0.58
        elif ch.isupper():
            w += size * 0.68
        else:
            w += size * 0.56
    return w


def wrap(text: str, size: float, width: float) -> list[str]:
    """估計字寬斷行：超寬就斷；6 個 token 內有「、，；）：。」就斷在它後面；避頭避尾；最後一行不只剩兩個字寬。"""
    lines = _wrap(text, size, width)
    if len(lines) >= 2 and text_width(lines[-1], size) < 2.5 * size:
        prev = _TOKEN.findall(lines[-2])
        take = 1          # 從上一行尾巴帶幾個 token 下來：帶下來的不能以收尾標點開頭，留下的不能以開頭括號結尾
        while take < len(prev) - 1 and (prev[-take] in _NO_LINE_START or prev[-take] == " "
                                         or prev[-take - 1] in _NO_LINE_END):
            take += 1
        if len(prev) - take >= 2 and text_width("".join(prev[-take:]) + lines[-1], size) <= width:
            lines[-2:] = ["".join(prev[:-take]).rstrip(), "".join(prev[-take:]).lstrip() + lines[-1]]
    return lines


def _wrap(text: str, size: float, width: float) -> list[str]:
    lines: list[str] = []
    cur: list[str] = []
    for tok in _TOKEN.findall(text):
        if tok.isspace():
            if cur and cur[-1] != " ":
                cur.append(" ")
            continue
        if not cur or text_width("".join(cur + [tok]), size) <= width:
            cur.append(tok)
            continue
        carry = [tok]
        cut = max((i for i, t in enumerate(cur) if t in _SOFT_BREAK_AFTER and len(cur) - 1 - i <= 6), default=None)
        if cut is not None and cut < len(cur) - 1:
            carry = cur[cut + 1:] + carry
            cur = cur[:cut + 1]
        # 收尾標點不放行首：前一個字一起帶下去（空白跟著搬，字與字之間的空白才不會掉）
        while next((t for t in carry if t != " "), "") in _NO_LINE_START and len(cur) > 1:
            carry.insert(0, cur.pop())
        while len(cur) > 1 and (cur[-1] == " " or cur[-1] in _NO_LINE_END):   # 開頭括號、箭頭不放行尾
            carry.insert(0, cur.pop())
        lines.append("".join(cur).rstrip())
        while carry and carry[0] == " ":
            carry.pop(0)
        cur = carry
    if cur:
        lines.append("".join(cur).rstrip())
    return lines


def supplier_line(suppliers: list[str]) -> str:
    return "圖上：" + "、".join(suppliers) + "（列舉不完整）" if suppliers else "圖上：這一層還沒有供應商"


def _place(lines: list[tuple[str, float, str, str]], x: float, cursor: float, first_gap: float):
    """把一串行由 cursor 往下排；回傳 [(x, baseline, 字, 字級, 粗細, 顏色)] 與排完的字框底。"""
    placed = []
    for i, (s, size, weight, fill) in enumerate(lines):
        base = cursor + (first_gap if i == 0 else LINE_GAP) + ASC * size
        placed.append((x, base, s, size, weight, fill))
        cursor = base + DSC * size
    return placed, cursor


class Canvas:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.y = 30.0
        #: 每一格（含框中框）的位置與節點——個股頁標「在這裡」用（座標是 viewBox 單位）
        self.boxes: list[dict[str, Any]] = []

    def _text(self, x: float, y: float, s: str, size: float, weight: str, fill: str, anchor: str = "start") -> None:
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
                          f'text-anchor="{anchor}">{escape(s)}</text>')

    def box(self, kind: str, title: str, desc: str, suppliers: list[str], *, dashed: bool = False,
            inner: list[dict[str, Any]] | None = None, nodes: list[str] | None = None) -> None:
        """一層：粗體名字、描述、（可選）框中框、最後灰字「圖上：…」。"""
        text_w = X1 - X0 - 2 * PAD
        top = self.y
        head = [(title, 14.5, "700", INK)] + [(ln, 12.5, "400", INK) for ln in wrap(desc, 12.5, text_w)]
        placed, cursor = _place(head, X0 + PAD, top, PAD - 2)
        inner_rects = []
        for spec in inner or ():
            itop = cursor + INNER_GAP
            iw = text_w - 2 * INNER_PAD
            ilines = [(str(spec["title"]), 13, "700", INK)] \
                + [(ln, 12, "400", INK) for ln in wrap(str(spec.get("desc") or ""), 12, iw)] \
                + [(ln, 11, "400", MUTED) for ln in wrap(supplier_line(list(spec.get("suppliers") or [])), 11, iw)]
            iplaced, icursor = _place(ilines, X0 + PAD + INNER_PAD, itop, INNER_PAD - 2)
            ibottom = icursor + INNER_PAD
            inner_rects.append((itop, ibottom - itop, str(spec["title"]), list(spec.get("nodes") or ())))
            placed += iplaced
            cursor = ibottom
        sup = [(ln, 11, "400", MUTED) for ln in wrap(supplier_line(suppliers), 11, text_w)]
        splaced, cursor = _place(sup, X0 + PAD, cursor, INNER_GAP if inner_rects else LINE_GAP + 2)
        placed += splaced
        h = cursor + PAD - 2 - top
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(f'<rect x="{X0}" y="{top:.1f}" width="{X1 - X0}" height="{h:.1f}" rx="10" '
                          f'fill="{FILL[kind]}" stroke="{STROKE[kind]}" stroke-width="1.4"{dash}/>')
        # 位置表的數字照抄上面 rect 的屬性（同一個格式化），標記才會疊在畫出來的框上
        self.boxes.append({"title": title, "nodes": list(nodes or ()), "top": float(f"{top:.1f}"),
                           "height": float(f"{h:.1f}"), "left": X0, "span": X1 - X0})
        for itop, ih, ititle, inodes in inner_rects:
            self.parts.append(f'<rect x="{X0 + PAD}" y="{itop:.1f}" width="{text_w}" height="{ih:.1f}" rx="8" '
                              f'fill="#ffffff" stroke="{STROKE[kind]}" stroke-width="1"/>')
            self.boxes.append({"title": ititle, "nodes": inodes, "top": float(f"{itop:.1f}"),
                               "height": float(f"{ih:.1f}"), "left": X0 + PAD, "span": text_w, "inside": title})
        for x, base, s, size, weight, fill in placed:
            self._text(x, base, s, size, weight, fill)
        self.y = top + h

    def arrow(self, label: str) -> None:
        top, bottom = self.y + 4, self.y + 34
        self.parts.append(f'<line x1="{W / 2}" y1="{top:.1f}" x2="{W / 2}" y2="{bottom - 6:.1f}" stroke="{MUTED}" '
                          f'stroke-width="2" marker-end="url(#arrow)"/>')
        if label:
            self._text(W / 2 + 12, top + 18, label, 11.5, "400", MUTED)
        self.y = bottom + 4

    def svg(self) -> str:
        h = self.y + 16
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h:.0f}" font-family="{FONT}">'
                '<defs><marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="{MUTED}"/></marker></defs>'
                f'<rect x="0" y="0" width="{W}" height="{h:.0f}" fill="#ffffff"/>'
                f'<text x="{W - 12}" y="18" font-size="11" fill="#8c959f" text-anchor="end">示意</text>')
        return head + "".join(self.parts) + "</svg>"


def layout_problems(layout: Any) -> list[str]:
    steps = (layout or {}).get("steps") if isinstance(layout, dict) else None
    if not isinstance(steps, list) or not steps:
        return ["說明檔沒有 layout.steps（要畫的鏈）"]
    problems = []
    seen: dict[str, str] = {}

    def check_nodes(where: str, nodes: Any) -> None:
        if nodes is None:
            return
        if not isinstance(nodes, list):
            problems.append(f"{where}的 nodes 要是清單")
            return
        for node in nodes:
            if not str(node).startswith(NODE_PREFIXES):
                problems.append(f"{where}的節點 {node!r} 不是 tech:／mat:／prod:")
            elif str(node) in seen:
                problems.append(f"節點 {node} 同時畫在「{seen[str(node)]}」和{where}（一個節點只畫在一格，標記才不會兩處都亮）")
            else:
                seen[str(node)] = where

    for i, step in enumerate(steps, 1):
        if not isinstance(step, dict) or ("box" in step) == ("arrow" in step):
            problems.append(f"第 {i} 步要嘛是 box、要嘛是 arrow")
        elif "box" in step:
            if step["box"] not in FILL:
                problems.append(f"第 {i} 步的配色 {step['box']!r} 不認得（{sorted(FILL)}）")
            if not str(step.get("title") or "").strip():
                problems.append(f"第 {i} 步的方框沒有名字")
            check_nodes(f"第 {i} 步", step.get("nodes"))
            for j, spec in enumerate(step.get("inner") or (), 1):
                if not str((spec or {}).get("title") or "").strip():
                    problems.append(f"第 {i} 步的第 {j} 個框中框沒有名字")
                check_nodes(f"第 {i} 步的第 {j} 個框中框", (spec or {}).get("nodes"))
    return problems


def layout_nodes(layout: dict[str, Any]) -> list[str]:
    """layout 每一格畫的節點（依出現順序）——說明檔的 `nodes_shown` 要和它一樣（同一份，L16）。"""
    out: list[str] = []
    for step in layout.get("steps") or ():
        if "box" in step:
            out += [str(n) for n in step.get("nodes") or ()]
            out += [str(n) for spec in step.get("inner") or () for n in (spec or {}).get("nodes") or ()]
    return out


def draw(layout: dict[str, Any]) -> Canvas:
    canvas = Canvas()
    for step in layout["steps"]:
        if "arrow" in step:
            canvas.arrow(str(step["arrow"] or ""))
        else:
            canvas.box(step["box"], str(step["title"]), str(step.get("desc") or ""), list(step.get("suppliers") or []),
                       dashed=bool(step.get("dashed")), inner=list(step.get("inner") or []),
                       nodes=[str(n) for n in step.get("nodes") or ()])
    return canvas


def render(layout: dict[str, Any]) -> str:
    return draw(layout).svg()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    from scripts.check_diagrams import EDGE, check, report

    ok = True
    for diagram_id in argv:
        meta_path = DIAGRAM_DIR / f"{diagram_id}.json"
        if not meta_path.is_file():
            print(f"✗ {diagram_id}：找不到 {meta_path.name}")
            ok = False
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        layout = meta.get("layout")
        problems = layout_problems(layout)
        if not problems and sorted(set(layout_nodes(layout))) != sorted(set(meta.get("nodes_shown") or ())):
            problems.append("nodes_shown 和每一格畫的節點對不上——"
                            f"格裡有、nodes_shown 沒有：{sorted(set(layout_nodes(layout)) - set(meta.get('nodes_shown') or ()))}；"
                            f"nodes_shown 有、沒有一格畫它：{sorted(set(meta.get('nodes_shown') or ()) - set(layout_nodes(layout)))}")
        if problems:
            print(f"✗ {diagram_id}：" + "；".join(problems))
            ok = False
            continue
        canvas = draw(layout)
        svg = canvas.svg()
        (DIAGRAM_DIR / f"{diagram_id}.svg").write_text(svg, encoding="utf-8")
        # 位置表綁這張 SVG：圖重畫或手改過，位置表就對不上、不嵌（webapp.diagrams.geometry_problems）
        meta["geometry"] = {"svg_sha256": svg_digest(svg), "boxes": canvas.boxes}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        if not Path(EDGE).is_file():
            print(f"△ {diagram_id}：已畫，但找不到 Edge 量不到——沒有量測紀錄，materialize 不會嵌")
            ok = False
            continue
        ok = report(diagram_id, check(diagram_id)) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
