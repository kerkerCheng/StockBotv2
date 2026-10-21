"""程式、skill、測試裡的 ROADMAP「X」要指得到（2026-10-21 批次二 E13 ①；Phase 7 failure log #60）。

ROADMAP 改寫時列會被拿掉；引用它的註解不會跟著改，於是讀的人照著名字去找、找不到，待決題就這樣安靜地消失
（「人工觀測的取代鏈」懸空 22 天）。規則：X 要在現行 `docs/ROADMAP.md` 裡，或在 `docs/archive/roadmap-backlog-log.md`
帶完成或退役標記的那一列裡。指向更早封存版的寫法是 `docs/archive/<檔>「X」`（不歸這支測試管）；格式範例用 `<…>` 佔位。
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.roadmap_pending_check import DONE_MARKERS, pending_rows, vanished

ROOT = Path(__file__).resolve().parents[1]
DIRS = ("alpha", "briefing", "engine_b", "engine_c", "query", "loader", "scripts", "crons", "webapp", "skills",
        "tests", "identity", "shared", "fetchers", "intake")
PATTERN = re.compile(r"ROADMAP「([^」]{1,80})」")


def _references() -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for d in DIRS:
        for path in (ROOT / d).rglob("*"):
            if path.suffix not in (".py", ".md") or "__pycache__" in path.parts or path.name == Path(__file__).name:
                continue
            for match in PATTERN.finditer(path.read_text(encoding="utf-8", errors="replace")):
                # 註解折行：「人工觀測的\n    # 取代鏈收多值」——去掉換行、縮排與續行的 #
                name = re.sub(r"\s*\n\s*#?\s*", "", match.group(1)).strip()
                if name.startswith("<"):
                    continue
                refs.setdefault(name, set()).add(str(path.relative_to(ROOT)))
    return refs


def test_every_roadmap_reference_points_somewhere() -> None:
    roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
    closed = [line for line in (ROOT / "docs" / "archive" / "roadmap-backlog-log.md").read_text(encoding="utf-8")
              .splitlines() if any(m in line for m in DONE_MARKERS)]
    dangling = {name: sorted(where) for name, where in _references().items()
                if name not in roadmap and not any(name in line for line in closed)}
    assert not dangling, ("這些 ROADMAP「…」在現行 ROADMAP 找不到、封存 backlog 也沒有完成或退役標記——"
                          f"列被拿掉了還是改名了？{dangling}")


def test_the_scan_sees_references_at_all() -> None:
    """掃描本身要有東西可比——0 個引用時上一條會恆綠（L14 ②：gate 本身也要驗）。"""
    assert len(_references()) >= 5


def test_pending_check_lists_a_pending_row_that_vanished() -> None:
    old = ("| **人工觀測的取代鏈收多值** | 待使用者選 A／B |\n"
           "| **已做完的那列** ✅ | 待決→已交付 |\n"
           "| **搬進 plan 的那列** | 待決 |\n")
    new = "| **別的列** | 開發中 |\n"
    assert [t for t, _ in pending_rows(old)] == ["人工觀測的取代鏈收多值", "搬進 plan 的那列"]
    assert vanished(old, new, ["plan 待決清單：搬進 plan 的那列"]) == ["人工觀測的取代鏈收多值"]
    assert vanished(old, old, []) == []
