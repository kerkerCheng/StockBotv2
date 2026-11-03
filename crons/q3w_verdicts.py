"""Q3W 裁決的常駐計數器——短版 ④ 每天一行「Q3W 裁決：到點 N｜已寫 M」，到點未寫的逐檔點名。

整體盲點審查 2026-11-01 §2 D（plan `docs/plans/2026-11-02-001-dev-blind-spot-remediation-proposal.md` §1 第 1 條）：
名單第 1–5 列的裁決點 10-21～10-29 都過了、研究端也都換了版，`cases.md` 的「### 裁決」仍是 0 行——等待有到期、叫醒也響了，
響完沒有人接量測那一步（L13）。拖到第一個 30 天量測日之後才補，結構裁決會被價格污染、預先登記白做。

只讀 `docs/reports/phase7/cases.md` 這一份評估檔，不是第二個狀態源：
- 每列的到點日＝名單規則 2 的裁決點——「候選 watch（until）」欄的第一個日期；沒有候選 watch 的列（COHR）取「裁決點」欄的第一個日期。
- 已寫＝「### 裁決」段裡第二格是這個代號的行（`- 日期｜代號｜…`）。
讀不到檔、找不到名單或裁決段，就說讀不到（INV-3）——不印 0。名單每列都到點而且都寫了，這一行就不再印（出口）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "docs" / "reports" / "phase7" / "cases.md"

_SECTION = "## Q3W"
_WINDOW = re.compile(r"窗：(\d{4})-(\d{2})-(\d{2})")
_MMDD = re.compile(r"(?<![\d-])(\d{2})-(\d{2})(?![\d-])")
_TICKER = re.compile(r"^\s*([0-9A-Z][0-9A-Z.\-]*)")


@dataclass(frozen=True)
class Q3WRow:
    ticker: str
    due: date | None          # None＝兩欄都讀不到日期


@dataclass(frozen=True)
class Q3WCounts:
    rows: tuple[Q3WRow, ...]
    written: frozenset[str]

    def due(self, today: date) -> list[Q3WRow]:
        return [r for r in self.rows if r.due is not None and r.due <= today]

    def unwritten_due(self, today: date) -> list[str]:
        return [r.ticker for r in self.due(today) if r.ticker not in self.written]

    def undated(self) -> list[str]:
        return [r.ticker for r in self.rows if r.due is None]


def _block(lines: list[str], heading: str) -> list[str]:
    """`heading` 開頭那一行之後、下一個同級以上標題之前的行。"""
    start = next((i for i, line in enumerate(lines) if line.startswith(heading)), None)
    if start is None:
        return []
    level = len(heading) - len(heading.lstrip("#"))
    out = []
    for line in lines[start + 1:]:
        if line.startswith("#") and len(line) - len(line.lstrip("#")) <= level:
            break
        out.append(line)
    return out


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _first_date(text: str, *, year: int, start_month: int) -> date | None:
    m = _MMDD.search(text)
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    try:
        return date(year + (1 if month < start_month else 0), month, day)
    except ValueError:
        return None


def parse(text: str) -> Q3WCounts:
    """解析 cases.md 的 Q3W 段。格式認不得就 raise ValueError（呼叫端照實印讀不到）。"""
    section = _block(text.splitlines(), _SECTION)
    if not section:
        raise ValueError("cases.md 沒有 Q3W 段")
    window = next((m for m in map(_WINDOW.search, section) if m), None)
    if window is None:
        raise ValueError("Q3W 段沒有「窗：YYYY-MM-DD」那一行")
    year, start_month = int(window.group(1)), int(window.group(2))
    table = _block(section, "### 名單")
    header = next((_cells(line) for line in table if line.startswith("| #")), None)
    if header is None:
        raise ValueError("Q3W 名單表沒有表頭")
    try:
        i_ticker = header.index("ticker")
        i_due = next(i for i, h in enumerate(header) if h.startswith("裁決點"))
        i_watch = next(i for i, h in enumerate(header) if h.startswith("候選 watch"))
    except (ValueError, StopIteration) as exc:
        raise ValueError(f"Q3W 名單表頭認不得：{header}") from exc
    rows = []
    for line in table:
        cells = _cells(line)
        if not line.startswith("|") or len(cells) != len(header) or not cells[0].isdigit():
            continue
        due = (_first_date(cells[i_watch], year=year, start_month=start_month)
               or _first_date(cells[i_due], year=year, start_month=start_month))
        rows.append(Q3WRow(ticker=cells[i_ticker], due=due))
    if not rows:
        raise ValueError("Q3W 名單表沒有任何一列")
    tickers = {r.ticker for r in rows}
    written = set()
    for line in _block(section, "### 裁決（"):    # 「### 裁決點來源」也是「### 裁決」開頭
        parts = line.lstrip("- ").split("｜")
        if len(parts) < 2 or not re.match(r"\d{4}-\d{2}-\d{2}", parts[0]):
            continue
        m = _TICKER.match(parts[1])
        if m and m.group(1) in tickers:
            written.add(m.group(1))
    return Q3WCounts(rows=tuple(rows), written=frozenset(written))


def status_lines(today: date, *, path: Path = CASES_PATH) -> list[str]:
    """短版 ④ 與完整心跳段 2 的那一行（0 或 1 行，不帶項目符號）。全部到點而且都寫了就不印；讀不到照實說。"""
    try:
        counts = parse(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"Q3W 裁決：讀不到（{exc}）"]
    due, unwritten, undated = counts.due(today), counts.unwritten_due(today), counts.undated()
    total = len(counts.rows)
    if len(due) == total and not unwritten:
        return []
    line = f"Q3W 裁決：到點 {len(due)}／{total}｜已寫 {len(counts.written)}"
    if unwritten:
        line += f"｜**到點未寫 {len(unwritten)}：{'、'.join(unwritten)}**（換版或複查的同一個動作 append cases.md）"
    if undated:
        line += f"｜裁決點讀不到 {len(undated)}：{'、'.join(undated)}"
    return [line]


__all__ = ["CASES_PATH", "Q3WCounts", "Q3WRow", "parse", "status_lines"]
