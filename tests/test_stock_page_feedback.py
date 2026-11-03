"""回饋紀錄常駐（個股頁 plan S6b；2026-11-03 使用者「S6 1A 2A」）：`docs/feedback/stock-page.jsonl` 的合約。

守的事：①每一列指得出版本與元素（S1 的驗收「回饋紀錄每列指得出版本與元素」由機器驗）；②壞行不靜默丟、跳號會紅；
③元素是封閉字彙，跟著 page schema 的塊與 APP 導覽列走；④前 39 列就是 brainstorm §8 那張表（逐字搬，原件留著）；
⑤它不是待辦池（形狀裡沒有狀態、優先序、到期）。寫入只在互動 session：append 一列，格式由這支測試擋。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from briefing.analyst_view import feedback_log as fb
from briefing.analyst_view.page_schema import BLOCKS, PAGE_SCHEMA_HISTORY, PAGE_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _row(**over):
    row = {"id": 1, "date": "2026-11-03", "said": "首頁卡片的字太多", "said_kind": "原話", "elements": ["公司頁"],
           "schema_version": PAGE_SCHEMA_VERSION, "outcome": "照推薦收短", "ref": "docs/ROADMAP.md「個股頁 schema」"}
    row.update(over)
    return row


def test_the_log_in_the_repo_passes_the_contract() -> None:
    """真的那一本：每一列過合約、id 從 1 逐列 +1、日期不倒退。回填 68 列（§8 39＋凍結後 29），之後只會變多。"""
    rows, problems = fb.load_feedback()
    assert problems == [], problems
    assert len(rows) >= 68 and [r.id for r in rows] == list(range(1, len(rows) + 1))
    assert {k for r in rows for k in r.elements} <= fb.ELEMENT_KEYS


def test_the_first_39_rows_are_the_brainstorm_table_verbatim() -> None:
    """§8 那張表是原件（凍結前的回饋）：前 39 列的原話與處理逐字等於表上那一格——改了一邊沒改另一邊就紅。"""
    text = (ROOT / "docs" / "brainstorms" / "2026-10-05-stock-page-schema.md").read_text(encoding="utf-8")
    body = text[text.index("## 8. 收斂機制與回饋紀錄"):text.index("## 9. 實作路徑")]
    cells = [[c.strip() for c in line.strip().strip("|").split("|")]
             for line in body.splitlines() if re.match(r"^\| \d+ \|", line)]
    rows, _problems = fb.load_feedback()
    assert len(cells) == 39
    for (n, day, said, _affect, how, _ver), row in zip(cells, rows):
        assert (row.id, row.date.isoformat(), row.said, row.outcome) == (int(n), f"2026-{day}", said, how)
        assert row.said_kind == "濃縮" and row.schema_version.startswith("canvas/")


@pytest.mark.parametrize("over, message", [
    ({"elements": ["B13"]}, "未登記的鍵"),
    ({"elements": []}, "至少一個"),
    ({"elements": ["B2", "B2"]}, "重複"),
    ({"schema_version": "stock-page-schema/9.9"}, "不是出現過的版本"),
    ({"ref": "  "}, "ref 不得是空的"),
    ({"said": ""}, "said 不得是空的"),
    ({"said_kind": "轉述"}, "said_kind"),
    ({"date": "2026/11/03"}, "YYYY-MM-DD"),
    ({"id": 0}, "從 1 起"),
    ({"status": "open"}, "形狀封閉"),           # 不是待辦池：沒有狀態欄
])
def test_each_field_is_checked_and_the_message_names_it(over, message) -> None:
    with pytest.raises(ValueError, match=message):
        fb.parse_feedback(_row(**over))
    assert fb.parse_feedback(_row()).elements == ("公司頁",)


def test_bad_lines_and_gaps_are_reported_instead_of_dropped(tmp_path) -> None:
    """壞行不是「少一列」：每一行壞在哪裡都印出來；id 跳號、日期倒退也紅（append-only）。變異：拿掉跳號檢查 → 紅。"""
    path = tmp_path / "log.jsonl"
    lines = [json.dumps(_row(id=1, date="2026-11-02"), ensure_ascii=False), "{壞掉的一行",
             json.dumps(_row(id=3, date="2026-11-01"), ensure_ascii=False)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rows, problems = fb.load_feedback(path)
    assert [r.id for r in rows] == [1, 3]
    assert any(p.startswith("第 2 行") for p in problems)
    assert any("id 1 之後是 3" in p for p in problems)
    assert any("早於前一列" in p for p in problems)
    assert fb.load_feedback(tmp_path / "nope.jsonl")[1] == ["nope.jsonl 不存在"]


def test_the_vocabulary_follows_the_page_schema_and_the_app_nav() -> None:
    """元素字彙跟著它的 SSOT 走：塊鍵來自 `page_schema.BLOCKS`；APP 頁來自導覽列（`index.html` 的 data-view）——
    導覽列加一頁、這裡沒跟上就紅；版本史的最後一個＝現行版本（升版忘了登記就紅）。"""
    assert {b.key for b in BLOCKS} <= fb.ELEMENT_KEYS
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    nav = html[html.index('<nav class="nav"'):html.index("</nav>")]
    assert set(re.findall(r'data-view="([a-z]+)"', nav)) == set(fb.APP_PAGE_KEYS)
    assert PAGE_SCHEMA_HISTORY[-1] == PAGE_SCHEMA_VERSION and len(set(PAGE_SCHEMA_HISTORY)) == len(PAGE_SCHEMA_HISTORY)
    assert set(fb.VERSIONS) >= set(PAGE_SCHEMA_HISTORY)
    # 不是待辦池（AGENTS「不建立與待辦池競爭的第二個狀態源」）：形狀裡沒有狀態、優先序、到期
    assert not {"status", "priority", "due", "expires", "owner"} & set(fb.FIELDS)
