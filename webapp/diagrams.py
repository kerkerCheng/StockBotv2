"""技術示意圖（個股頁 S5b 第二段，2026-10-08；schema v1.0 規則 5、6：示意圖讀起來像事實 → 標「示意」、附出處）。

每張圖三個檔，住 `library/private/research_notes/diagrams/`（研究 session 寫；私有、不進 repo）：

- `<id>.json`——`{"title", "caption", "nodes_shown": [tech:/mat:/prod: 節點], "sources": [{"ref", "what"}], "drawn_at", "author"}`；
  可另帶 `layout`（`scripts/draw_diagram.py` 照它畫 SVG；這裡不讀）與 `geometry`（畫圖器寫的位置表：每一格的名字、節點、
  上緣、高、左緣、寬，綁 SVG 的 sha256）——個股頁據此標「這檔在這裡」（2026-10-08 使用者）。手畫的圖沒有位置表＝標不出
  在哪一格（照實說，不是錯）；有位置表就要對得上現在這張 SVG、節點的聯集要等於 `nodes_shown`，否則不嵌。
- `<id>.svg`——圖本身（`scripts/draw_diagram.py` 畫或手寫，手機寬度可讀）。
- `<id>.check.json`——`scripts/check_diagrams.py` 的量測紀錄（規則 9：字不重疊、不出框、不壓框線；**量過、0 才發佈**）。
  紀錄綁 SVG 的 sha256：圖改過就要重量，沒量、量測沒過、量測版本舊了都不嵌。

materialize 時由這裡載入、檢查、編成 data URI；APP 用 `<img>` 顯示（SVG 在 img 裡不執行任何東西；CSP 原本就是
`img-src 'self' data:`，不用放寬）。
**檢查不過就不嵌**，理由照實列出（INV-3：不靜默丟）：沒有出處、沒有節點、SVG 解析不了、有 script／foreignObject／外部連結
或事件屬性、沒有通過的量測紀錄。這裡不判圖畫得對不對——那是研究，出處讓人回頭核。
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_DIR = ROOT / "library" / "private" / "research_notes" / "diagrams"
RAW_DIR = ROOT / "library" / "raw"

NODE_PREFIXES = ("tech:", "mat:", "prod:")
#: 量測紀錄的副檔名與版本：量測規則變了（多量一種問題）就升版，舊紀錄一律當沒量過。
RECEIPT_SUFFIX = ".check.json"
CHECK_VERSION = 1
#: 量測紀錄裡「必須是 0」的三種問題。
CHECK_PROBLEMS = ("overlaps", "outside", "crossing")
#: 圖裡不准出現的元素（會執行、會載入外部內容、或把 HTML 塞進 SVG）。
FORBIDDEN_TAGS = frozenset({"script", "foreignobject", "iframe", "object", "embed", "image", "audio", "video",
                            "animate", "set", "animatemotion", "animatetransform", "handler", "listener"})
_ID = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,80}$")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def svg_problems(svg_text: str) -> list[str]:
    """SVG 本身的檢查：解析得了、根是 svg 且有 viewBox、沒有會執行或載入外部的東西。"""
    try:
        root = ElementTree.fromstring(svg_text)
    except ElementTree.ParseError as exc:
        return [f"SVG 解析不了（{exc}）"]
    problems: list[str] = []
    if _local(root.tag) != "svg":
        problems.append(f"根元素是 {_local(root.tag)}，不是 svg")
    if not root.get("viewBox"):
        problems.append("缺 viewBox（手機寬度縮放要靠它）")
    for node in root.iter():
        tag = _local(str(node.tag))
        if tag in FORBIDDEN_TAGS:
            problems.append(f"不允許的元素 <{tag}>")
        for name, value in node.attrib.items():
            attr = _local(name)
            if attr.startswith("on"):
                problems.append(f"不允許的事件屬性 {attr}（<{tag}>）")
            if attr == "href" and not str(value).startswith("#"):
                problems.append(f"不允許的外部連結 {value!r}（<{tag}>）")
            if "url(" in str(value) and not re.fullmatch(r"\s*url\(#[^)]+\)\s*", str(value)):
                problems.append(f"不允許的外部 url()（<{tag}> {attr}）")
        if tag == "style" and node.text and ("@import" in node.text or re.search(r"url\((?!#)", node.text)):
            problems.append("<style> 裡不允許 @import 或外部 url()")
    return problems


def meta_problems(meta: Mapping[str, Any], *, raw_dir: Path = RAW_DIR) -> list[str]:
    """說明檔的檢查：要有標題、說明、至少一個節點、至少一個出處；`raw:` 出處要指得回 library/raw 的檔。"""
    problems: list[str] = []
    for key in ("title", "caption"):
        if not str(meta.get(key) or "").strip():
            problems.append(f"缺 {key}")
    nodes = meta.get("nodes_shown")
    if not isinstance(nodes, list) or not nodes:
        problems.append("缺 nodes_shown（這張圖畫的是哪幾個節點）")
    else:
        bad = [n for n in nodes if not str(n).startswith(NODE_PREFIXES)]
        if bad:
            problems.append(f"nodes_shown 只收 tech:／mat:／prod: 節點：{bad}")
    sources = meta.get("sources")
    if not isinstance(sources, list) or not sources:
        problems.append("缺 sources（示意圖必附出處——規則 6）")
    else:
        for i, src in enumerate(sources, 1):
            ref = str((src or {}).get("ref") or "")
            if not ref:
                problems.append(f"第 {i} 個出處沒有 ref")
            elif ref.startswith("raw:") and not (raw_dir / ref[4:]).is_file() \
                    and not (raw_dir / f"{ref[4:]}.txt").is_file():
                problems.append(f"第 {i} 個出處 {ref} 在 library/raw 找不到")
    return problems


def svg_digest(svg_text: str) -> str:
    return hashlib.sha256(svg_text.encode("utf-8")).hexdigest()


def receipt_path(directory: Path, diagram_id: str) -> Path:
    return directory / f"{diagram_id}{RECEIPT_SUFFIX}"


def receipt_problems(svg_text: str, path: Path) -> list[str]:
    """量測紀錄的檢查：有、對得上現在這張 SVG、是現行版本的量測、三種問題都是 0。"""
    if not path.is_file():
        return ["沒有量測紀錄（跑 python scripts/check_diagrams.py——規則 9：量過、0 才發佈）"]
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return ["量測紀錄不是合法 JSON（重跑 scripts/check_diagrams.py）"]
    if receipt.get("check_version") != CHECK_VERSION:
        return [f"量測紀錄是舊版量測（v{receipt.get('check_version')}，現行 v{CHECK_VERSION}），重跑 scripts/check_diagrams.py"]
    if receipt.get("svg_sha256") != svg_digest(svg_text):
        return ["圖改過、還沒重新量測（量測紀錄對不上現在的 SVG）"]
    if not receipt.get("texts"):
        return ["量測量到 0 段字（頁面可能沒跑完），重跑 scripts/check_diagrams.py"]
    counts = {key: len(receipt.get(key) or ()) for key in CHECK_PROBLEMS}
    if any(counts.values()):
        return [f"量測沒過：字疊字 {counts['overlaps']}、出框 {counts['outside']}、壓框線 {counts['crossing']}"]
    return []


def viewbox_size(svg_text: str) -> tuple[float, float] | None:
    """SVG viewBox 的寬高（個股頁把位置表換成百分比疊在圖上）；讀不到回 None。"""
    try:
        parts = str(ElementTree.fromstring(svg_text).get("viewBox") or "").replace(",", " ").split()
        width, height = float(parts[2]), float(parts[3])
    except (ElementTree.ParseError, IndexError, ValueError):
        return None
    return (width, height) if width > 0 and height > 0 else None


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def geometry_problems(meta: Mapping[str, Any], svg_text: str) -> list[str]:
    """位置表（`geometry`）的檢查：綁得上現在這張 SVG、每一格有名字且落在圖裡、一個節點只在一格、
    節點的聯集＝`nodes_shown`（選圖與標記同一份，L16）。沒有位置表回空（手畫的圖；個股頁照實說標不出）。"""
    geometry = meta.get("geometry")
    if geometry is None:
        return []
    if not isinstance(geometry, Mapping) or not isinstance(geometry.get("boxes"), list):
        return ["位置表（geometry）格式不對（重跑 scripts/draw_diagram.py）"]
    if geometry.get("svg_sha256") != svg_digest(svg_text):
        return ["圖改過、位置表沒跟著重畫（位置表對不上現在的 SVG；重跑 scripts/draw_diagram.py）"]
    size = viewbox_size(svg_text)
    if size is None:
        return ["位置表需要 SVG 的 viewBox 寬高"]
    width, height = size
    problems: list[str] = []
    placed: dict[str, str] = {}
    for i, box in enumerate(geometry["boxes"], 1):
        if not isinstance(box, Mapping) or not str(box.get("title") or "").strip():
            problems.append(f"位置表第 {i} 格沒有名字")
            continue
        title = str(box["title"])
        if not all(_number(box.get(k)) for k in ("top", "height", "left", "span")):
            problems.append(f"位置表「{title}」的上緣／高／左緣／寬要是非負數")
        elif box["top"] + box["height"] > height + 0.5 or box["left"] + box["span"] > width + 0.5:
            problems.append(f"位置表「{title}」落在圖外")
        nodes = box.get("nodes")
        if not isinstance(nodes, list):
            problems.append(f"位置表「{title}」的 nodes 要是清單")
            continue
        for node in nodes:
            if str(node) in placed:
                problems.append(f"節點 {node} 同時在「{placed[str(node)]}」和「{title}」兩格")
            placed[str(node)] = title
    shown = {str(n) for n in meta.get("nodes_shown") or ()}
    if not problems and set(placed) != shown:
        problems.append(f"位置表的節點和 nodes_shown 對不上（格裡有、nodes_shown 沒有：{sorted(set(placed) - shown)}；"
                        f"nodes_shown 有、沒有一格畫它：{sorted(shown - set(placed))}）")
    return problems


def load_diagrams(directory: Path | None = None, *, raw_dir: Path = RAW_DIR) -> dict[str, Any]:
    """全部示意圖：`{"diagrams": [可嵌的], "rejected": [{id, problems}]}`。目錄不存在＝0 張（不是錯）。"""
    root = directory or DIAGRAM_DIR
    out: dict[str, Any] = {"diagrams": [], "rejected": []}
    if not root.is_dir():
        return out
    for meta_path in sorted(p for p in root.glob("*.json") if not p.name.endswith(RECEIPT_SUFFIX)):
        diagram_id = meta_path.stem
        problems: list[str] = []
        if not _ID.match(diagram_id):
            problems.append("檔名只收小寫英數、底線、連字號")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            out["rejected"].append({"id": diagram_id, "problems": [f"說明檔不是合法 JSON（{exc}）"]})
            continue
        svg_path = meta_path.with_suffix(".svg")
        svg_text = svg_path.read_text(encoding="utf-8") if svg_path.is_file() else ""
        if not svg_text:
            problems.append(f"找不到 {svg_path.name}")
        else:
            problems += (svg_problems(svg_text) or receipt_problems(svg_text, receipt_path(root, diagram_id))
                         or geometry_problems(meta, svg_text))
        problems += meta_problems(meta, raw_dir=raw_dir)
        if problems:
            out["rejected"].append({"id": diagram_id, "problems": problems})
            continue
        width, height = viewbox_size(svg_text) or (None, None)
        geometry = meta.get("geometry")
        out["diagrams"].append({
            "id": diagram_id,
            "title": str(meta["title"]),
            "caption": str(meta["caption"]),
            "nodes_shown": [str(n) for n in meta["nodes_shown"]],
            "sources": [{"ref": str(s.get("ref")), "what": str(s.get("what") or "")} for s in meta["sources"]],
            "drawn_at": meta.get("drawn_at"),
            "author": meta.get("author") or "session",
            "src": "data:image/svg+xml;base64," + base64.b64encode(svg_text.encode("utf-8")).decode("ascii"),
            # 每一格的位置（viewBox 單位）與它畫的節點；None＝這張圖沒有位置表（手畫的），個股頁標不出在哪一格
            "width": width, "height": height,
            "boxes": None if geometry is None else [
                {"title": str(b["title"]), "nodes": [str(n) for n in b["nodes"]], "top": b["top"], "height": b["height"],
                 "left": b["left"], "span": b["span"], "inside": b.get("inside")} for b in geometry["boxes"]],
        })
    return out


def diagrams_for_nodes(loaded: Mapping[str, Any] | None, nodes: Any) -> list[dict[str, Any]]:
    """涵蓋這幾個節點的圖（一張圖畫一條路徑，路徑上的每一層、每一頁共用同一張）。"""
    if not loaded:
        return []
    want = {str(n) for n in nodes or ()}
    return [d for d in loaded.get("diagrams") or () if want & set(d.get("nodes_shown") or ())]


__all__ = ["CHECK_PROBLEMS", "CHECK_VERSION", "DIAGRAM_DIR", "FORBIDDEN_TAGS", "NODE_PREFIXES", "RECEIPT_SUFFIX",
           "diagrams_for_nodes", "geometry_problems", "load_diagrams", "meta_problems", "receipt_path", "receipt_problems",
           "svg_digest", "svg_problems", "viewbox_size"]
