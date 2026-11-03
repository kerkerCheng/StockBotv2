"""使用者對個股頁與 APP 的回饋紀錄（個股頁 plan S6b；2026-11-03 使用者「S6 1A 2A」）。

一本 append-only 的 JSONL（`docs/feedback/stock-page.jsonl`，tracked）：一列＝使用者對個股頁或 APP 說過的一句（或同一件事的
幾句）話，指得出**登記時的版本**與**哪幾個元素**，以及後來怎麼處理、處理記在哪裡。「每列指得出版本與元素」由合約機械驗——
這正是 S1 的回饋表做不到的事（凍結後的意見散在 plan 的 amendment 與 brainstorm，沒有一處常駐）。

- **它不是待辦池**：要開發的事唯一載體仍是 ROADMAP（AGENTS「不建立與待辦池競爭的第二個狀態源」）；`ref` 只寫指向
  （commit、plan 節、ROADMAP 列或 brainstorm 的發現編號）。
- **範圍只收個股頁與 APP**（使用者選 2A）：daily 短版、心跳、回覆長短這類回饋不收。
- **誰寫**：互動 session 收到對個股頁或 APP 的意見時 append 一列（`docs/AGENT_WORKFLOW.md`）；沒有命令，格式由
  `tests/test_stock_page_feedback.py` 擋——不合的列讓全套測試紅，不會被靜默丟掉（INV-3）。
- **回填（2026-11-03）**：brainstorm `2026-10-05-stock-page-schema` §8 的 39 列逐字搬（#1–#39，那張表留作原件）；凍結後的
  plan 003 Amendment E、F、G 與 brainstorm `2026-10-28-app-attention-ia` §1、§5 照原文補列。**其他對話裡的回饋沒有逐一回溯**
  ——這本裡沒有不等於使用者沒說過（L11-5）。

欄位（**形狀封閉**，未登記的鍵拒收）：
`id`（從 1 起、逐列 +1，跳號＝有列被拿掉）｜`date`（使用者說的那天）｜`said`＋`said_kind`（`原話` 或 `濃縮`）｜
`elements`（`ELEMENT_KEYS` 裡的鍵，至少一個）｜`schema_version`（這一列處理完時的版本：改了 schema 的是改完那一版，
沒改的是當時的現行版；凍結前寫 `canvas/v0.x`——同一天的幾列可能先 1.5 後 1.4，因為處理完的先後不同，所以不驗版本順序）｜
`outcome`（改了什麼，或不改＋理由）｜`ref`（記在哪裡，非空）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .page_schema import BLOCKS, CANVAS_VERSIONS, PAGE_SCHEMA_HISTORY

_ROOT = Path(__file__).resolve().parents[2]
FEEDBACK_PATH = _ROOT / "docs" / "feedback" / "stock-page.jsonl"

#: schema 的十一條規則（brainstorm `2026-10-05-stock-page-schema` §5.6）——規則加到第十二條時改這裡。
SCHEMA_RULE_COUNT = 11
#: 跨塊的鍵（個股頁本身用 `BLOCKS` 的塊鍵）：首屏的形式、整頁、規則，與凍結前磨合輪討論過的幾件事。
CROSS_KEYS: Mapping[str, str] = {
    "首屏": "個股頁首屏的形式（論點、故事、每塊一句讀法）",
    "全部": "整個個股頁或整個 APP 都受影響",
    **{f"規則{n}": f"schema 規則 {n}（brainstorm §5.6）" for n in range(1, SCHEMA_RULE_COUNT + 1)},
    "測試集": "七檔測試集與錨點（brainstorm §6、§10.1）",
    "時光機": "時光機頁（brainstorm §10.3、§11.4）",
    "報告": "分析師報告怎麼取用（brainstorm §10.2）",
    "架構": "schema、研究寫的讀法與 rubric 的分層（brainstorm §13）",
    "量測": "假說與量測（Phase 7 假說帳）",
}
#: APP 的頁（導覽列 `webapp/static/index.html` 的 `data-view` → 鍵；測試核對兩邊一致——導覽列加一頁，這裡沒跟上就紅）。
#: 2026-10-28 前的舊頁名照併進去的那一頁記（讀圖、走圖、層說明、結構表 → 圖頁；追蹤表、帳號計分表 → 成績單頁；
#: 候選板、在等什麼 → 公司頁）；`said` 留原話。
APP_PAGE_KEYS: Mapping[str, str] = {
    "stocks": "公司頁", "daily": "每日頁", "graph": "圖頁", "positions": "成績單頁", "beta": "資產配置頁",
}
ELEMENT_KEYS: frozenset[str] = (frozenset(b.key for b in BLOCKS) | frozenset(CROSS_KEYS)
                                | frozenset(APP_PAGE_KEYS.values()))
VERSIONS: tuple[str, ...] = CANVAS_VERSIONS + PAGE_SCHEMA_HISTORY
SAID_KINDS: tuple[str, ...] = ("原話", "濃縮")
FIELDS: tuple[str, ...] = ("id", "date", "said", "said_kind", "elements", "schema_version", "outcome", "ref")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True, slots=True)
class Feedback:
    id: int
    date: date
    said: str
    said_kind: str
    elements: tuple[str, ...]
    schema_version: str
    outcome: str
    ref: str


def parse_feedback(raw: Any) -> Feedback:
    """一列 → `Feedback`；任何一欄不合就 `ValueError`，訊息說哪一欄、為什麼。"""
    if not isinstance(raw, Mapping):
        raise ValueError("這一列不是 object")
    extra, missing = sorted(set(raw) - set(FIELDS)), [k for k in FIELDS if k not in raw]
    if extra or missing:
        raise ValueError(f"欄位不合：多了 {extra}、少了 {missing}（形狀封閉）")
    ident = raw["id"]
    if not isinstance(ident, int) or isinstance(ident, bool) or ident < 1:
        raise ValueError(f"id 要是從 1 起的整數：{ident!r}")
    day = str(raw["date"])
    if not _DATE.match(day):
        raise ValueError(f"date 要是 YYYY-MM-DD：{day!r}")
    try:
        parsed_day = date.fromisoformat(day)
    except ValueError as exc:
        raise ValueError(f"date 讀不懂：{day!r}") from exc
    texts = {k: raw[k] for k in ("said", "outcome", "ref")}
    for key, value in texts.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} 不得是空的")
    if raw["said_kind"] not in SAID_KINDS:
        raise ValueError(f"said_kind 只收 {list(SAID_KINDS)}：{raw['said_kind']!r}")
    elements = raw["elements"]
    if not isinstance(elements, list) or not elements or not all(isinstance(e, str) for e in elements):
        raise ValueError("elements 要是至少一個字串的 list")
    unknown = sorted(set(elements) - ELEMENT_KEYS)
    if unknown:
        raise ValueError(f"elements 有未登記的鍵 {unknown}（封閉字彙：塊鍵、跨塊鍵、APP 頁）")
    if len(set(elements)) != len(elements):
        raise ValueError(f"elements 有重複：{elements}")
    if raw["schema_version"] not in VERSIONS:
        raise ValueError(f"schema_version 不是出現過的版本：{raw['schema_version']!r}（升版時先在 page_schema 登記）")
    return Feedback(id=ident, date=parsed_day, said=texts["said"], said_kind=raw["said_kind"],
                    elements=tuple(elements), schema_version=raw["schema_version"], outcome=texts["outcome"],
                    ref=texts["ref"])


def load_feedback(path: Path | None = None) -> tuple[list[Feedback], list[str]]:
    """讀整本：(解析得到的列, 問題清單)。**壞行不靜默丟**——每一行壞在哪裡都回在問題清單；另驗 id 從 1 起逐列 +1、
    日期不倒退（append-only：後來的列不會比前一列更早說）。"""
    target = path or FEEDBACK_PATH
    rows: list[Feedback] = []
    problems: list[str] = []
    if not target.is_file():
        return rows, [f"{target.name} 不存在"]
    for number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            problems.append(f"第 {number} 行是空行（append-only 的一本不該有空行）")
            continue
        try:
            rows.append(parse_feedback(json.loads(line)))
        except ValueError as exc:
            problems.append(f"第 {number} 行：{exc}")
    for prev, row in zip(rows, rows[1:]):
        if row.id != prev.id + 1:
            problems.append(f"id {prev.id} 之後是 {row.id}（要逐列 +1；跳號＝有列被拿掉或插隊）")
        if row.date < prev.date:
            problems.append(f"id {row.id} 的日期 {row.date} 早於前一列 {prev.date}（append-only 不倒退）")
    if rows and rows[0].id != 1:
        problems.append(f"第一列的 id 是 {rows[0].id}，要從 1 起")
    return rows, problems


__all__ = ["APP_PAGE_KEYS", "CROSS_KEYS", "ELEMENT_KEYS", "FEEDBACK_PATH", "FIELDS", "Feedback", "SAID_KINDS",
           "SCHEMA_RULE_COUNT", "VERSIONS", "load_feedback", "parse_feedback"]
