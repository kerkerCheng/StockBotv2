"""技術示意圖的機械量測（個股頁 schema v1.0 規則 9：圖上的字不准互相重疊，0 才發佈）。

每張 `library/private/research_notes/diagrams/<id>.svg` 原樣內嵌進一個本機暫存頁，用 headless Edge 量每段 `<text>` 的實際外框：
①字與字重疊 ②字出框（左右各留 8px、上下各 2px） ③字壓到框線或箭頭（跟一個方框相交卻沒有整段落在框內，或碰到線）。
量完把結果寫成 `<id>.check.json`（綁 SVG 的 sha256；materialize 只嵌有通過紀錄的圖——webapp/diagrams.py）。
不改圖、不寫任何 authority；暫存頁寫在系統暫存目錄。

用法：python scripts/check_diagrams.py [<id> ...]   （不給就量全部；任一張不合格 exit 1）
需要本機的 Edge（STOCKBOT_EDGE 可指定路徑）；量不到（找不到 Edge、頁面沒跑完）就照實說量不到、不寫紀錄，不印 0（INV-3）。
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from webapp.diagrams import CHECK_PROBLEMS, CHECK_VERSION, DIAGRAM_DIR, receipt_path, svg_digest  # noqa: E402

EDGE = os.environ.get("STOCKBOT_EDGE", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
_MEASURE = """
<script>
window.addEventListener('load', () => {
  const svg = document.querySelector('svg');
  const vb = svg.viewBox.baseVal;
  const boxes = Array.from(svg.querySelectorAll('text')).map((t) => ({ t: t.textContent, r: t.getBBox() }));
  const meet = (a, b) => a.x < b.x + b.width - 0.5 && b.x < a.x + a.width - 0.5
    && a.y < b.y + b.height - 0.5 && b.y < a.y + a.height - 0.5;
  const within = (a, b) => a.x >= b.x - 0.5 && a.y >= b.y - 0.5
    && a.x + a.width <= b.x + b.width + 0.5 && a.y + a.height <= b.y + b.height + 0.5;
  const overlaps = [];
  for (let i = 0; i < boxes.length; i += 1) for (let j = i + 1; j < boxes.length; j += 1) {
    if (meet(boxes[i].r, boxes[j].r)) overlaps.push(boxes[i].t + ' ↔ ' + boxes[j].t);
  }
  const outside = boxes.filter((b) => b.r.x < 8 - 0.5 || b.r.x + b.r.width > vb.width - 8 + 0.5
    || b.r.y < 2 - 0.5 || b.r.y + b.r.height > vb.height - 2 + 0.5)
    .map((b) => `${b.t}（x ${Math.round(b.r.x)}–${Math.round(b.r.x + b.r.width)}、y ${Math.round(b.r.y)}–${Math.round(b.r.y + b.r.height)}／${vb.width}×${vb.height}）`);
  // 方框：整張底色那種（跟畫布一樣大）不算；線：箭頭本體（marker 裡的箭頭尖不算）
  const frames = Array.from(svg.querySelectorAll('rect')).map((el) => el.getBBox())
    .filter((r) => r.width < vb.width - 1 || r.height < vb.height - 1);
  const strokes = Array.from(svg.querySelectorAll('line, polyline, path'))
    .filter((el) => !el.closest('marker, defs')).map((el) => el.getBBox());
  const touch = (a, l) => a.x <= l.x + l.width + 1 && l.x <= a.x + a.width + 1 && a.y <= l.y + l.height + 1 && l.y <= a.y + a.height + 1;
  const crossing = [];
  boxes.forEach((b) => {
    frames.forEach((f) => {
      if (meet(b.r, f) && !within(b.r, f)) crossing.push(`${b.t} ↔ 框線（y ${Math.round(f.y)}–${Math.round(f.y + f.height)}）`);
    });
    strokes.forEach((l) => {
      if (touch(b.r, l)) crossing.push(`${b.t} ↔ 線（x ${Math.round(l.x)}、y ${Math.round(l.y)}–${Math.round(l.y + l.height)}）`);
    });
  });
  document.getElementById('r').textContent = JSON.stringify({ texts: boxes.length, overlaps, outside, crossing });
});
</script>
"""


def measure_svg(svg_text: str) -> dict:
    page = ("<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0'>"
            + svg_text + "<pre id='r'></pre>" + _MEASURE + "</body></html>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as handle:
        handle.write(page)
        tmp = Path(handle.name)
    try:
        dom = subprocess.run([EDGE, "--headless", "--disable-gpu", "--virtual-time-budget=5000", "--dump-dom",
                              tmp.as_uri()], capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=120).stdout
    finally:
        tmp.unlink(missing_ok=True)
    m = re.search(r"<pre id=\"r\">(.*?)</pre>", dom, re.S)
    if not m or not m.group(1).strip():
        return {"error": "量不到（頁面沒跑完或 Edge 沒有輸出）"}
    return json.loads(html.unescape(m.group(1)))


def measure(svg_path: Path) -> dict:
    return measure_svg(svg_path.read_text(encoding="utf-8"))


def check(diagram_id: str, directory: Path = DIAGRAM_DIR) -> dict:
    """量一張、寫量測紀錄（量不到就不寫——舊紀錄若還對得上同一張 SVG 就照舊有效）。"""
    svg_path = directory / f"{diagram_id}.svg"
    if not svg_path.is_file():
        return {"error": f"找不到 {svg_path.name}"}
    svg_text = svg_path.read_text(encoding="utf-8")
    result = measure_svg(svg_text)
    if "error" in result:
        return result
    receipt = {"check_version": CHECK_VERSION, "svg_sha256": svg_digest(svg_text),
               "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "texts": result.get("texts", 0), **{key: result.get(key) or [] for key in CHECK_PROBLEMS}}
    receipt_path(directory, diagram_id).write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8")
    return receipt


def report(diagram_id: str, result: dict) -> bool:
    if "error" in result:
        print(f"✗ {diagram_id}：{result['error']}")
        return False
    ok = bool(result.get("texts")) and not any(result.get(key) for key in CHECK_PROBLEMS)
    print(f"{'✓' if ok else '✗'} {diagram_id}：字 {result.get('texts')} 段｜字疊字 {len(result['overlaps'])}｜"
          f"出框 {len(result['outside'])}｜壓框線 {len(result['crossing'])}")
    for key, label in (("overlaps", "字疊字"), ("outside", "出框"), ("crossing", "壓框線")):
        for item in result[key][:8]:
            print(f"    {label}：", item)
    return ok


def main(argv: list[str]) -> int:
    if not Path(EDGE).is_file():
        print(f"✗ 找不到 Edge：{EDGE}（STOCKBOT_EDGE 可指定）——量不到，不是 0")
        return 2
    ids = argv or sorted(p.stem for p in DIAGRAM_DIR.glob("*.svg"))
    results = [report(diagram_id, check(diagram_id)) for diagram_id in ids]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
