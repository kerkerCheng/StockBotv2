"""ROADMAP 改寫時，待使用者決定的列不得消失（2026-10-21 批次二 E13 ②；Phase 7 failure log #60）。

**手動跑、不進 hook**——ROADMAP「不做 ROADMAP 驗收 linter」那一句照守（L16-4：會誤報的防呆本身是過度工程）。
它只是把「改寫前的版本裡、等使用者決定又沒有完成標記的列」與改寫後的版本做差集，列出新版 ROADMAP 與任何
Phase plan（`docs/plans/*.md`）都找不到標題的那幾列——讓改寫的人逐列答「去了哪裡」。標題比對是子字串（取粗體標題
前 20 字），改寫時把標題改掉的列會被列出來：那正是要人看一眼的情形，不是誤報。

事發（#60 三例）：「人工觀測的取代鏈」懸空 22 天；`duplicate_nodes` 檔頭指向已被拿掉的列；[613]／[614] 後兩條
is_variant_of 待判只留在封存檔。

    python -m scripts.roadmap_pending_check            # 對 HEAD 那一版比（改了還沒 commit 時用）
    python -m scripts.roadmap_pending_check --base HEAD~1
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
ROADMAP = "docs/ROADMAP.md"
#: 「等使用者決定」的字樣（ROADMAP 現行寫法；字彙留鬆，撞到新寫法再加）。
PENDING_MARKERS = ("待使用者", "待決", "要使用者選", "AWAITING_HUMAN")
#: 完成或退役的標記——有這些的列不算「還在等」。
DONE_MARKERS = ("✅", "交付", "已落地", "退役", "不做")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
NEEDLE_CHARS = 20


def pending_rows(text: str) -> list[tuple[str, str]]:
    """表格列裡等使用者決定、沒有完成標記的 → `(標題, 整列)`。標題＝第一格的第一段粗體（沒有就第一格）。"""
    out: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        if not any(m in line for m in PENDING_MARKERS) or any(m in line for m in DONE_MARKERS):
            continue
        first = line.strip("|").split("|", 1)[0]
        bold = _BOLD.search(first)
        title = (bold.group(1) if bold else first).strip().strip("~ ")
        if title:
            out.append((title, line))
    return out


def vanished(old_text: str, new_text: str, plan_texts: Iterable[str]) -> list[str]:
    """舊版待決列裡，新版 ROADMAP 與 Phase plan 都找不到標題（前 20 字）的那幾列標題。"""
    haystacks = [new_text, *plan_texts]
    return [title for title, _line in pending_rows(old_text)
            if not any(title[:NEEDLE_CHARS] in h for h in haystacks)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ROADMAP 改寫的待決題差集（手動跑，不進 hook）")
    parser.add_argument("--base", default="HEAD", help="比對的舊版（git rev；預設 HEAD）")
    args = parser.parse_args(argv)
    old = subprocess.run(["git", "show", f"{args.base}:{ROADMAP}"], cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    new = (ROOT / ROADMAP).read_text(encoding="utf-8")
    plans = [p.read_text(encoding="utf-8") for p in sorted((ROOT / "docs" / "plans").glob("*.md"))]
    gone = vanished(old, new, plans)
    print(f"{args.base} 那一版等使用者決定、沒有完成標記的列 {len(pending_rows(old))} 條；"
          f"新版 ROADMAP 與 Phase plan 都找不到的 {len(gone)} 條")
    for title in gone:
        print(f"  - {title}")
    return 1 if gone else 0


if __name__ == "__main__":
    sys.exit(main())
