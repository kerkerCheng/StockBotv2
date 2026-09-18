"""`graph_context` 的截斷必須說話——而且說話不得動到任何一列資料。

事發（2026-09-17／18 兩次）：`query/graph_context.py` 的每個區段都把 `LIMIT` 寫在
Cypher 裡，回來的結果**無法分辨「只有這麼多」與「被切掉了」**（L13-2：成功與失敗
在同一個訊號上同形）。實測代價是一個架構級的假結論——`co:axt` 的 context 在預設
`claim_limit=20` 下字串 `jx` 出現 1 次、放到 200 出現 21 次，於是 JX Advanced Metals
宣布 InP 產能拉到 7–10 倍的那批證據看起來「不在圖裡」，病因被誤診成「圖中缺一條
`competes_with` 邊」，補了那條邊（pq2 [602]）也沒有解決問題。

2026-09-18 實測的截斷幅度：公司模式 claims 20／154（AXT）、20／243（COHR）；
全圖 supply 50／515、claims 20／325、demand 10／23、瓶頸 30／52。**六段裡五段沉默。**
"""
from __future__ import annotations

import pytest

from query.graph_context import (
    _LIMIT_RE,
    _Q_BOTTLENECK,
    _Q_CLAIMS,
    _Q_COMPANY_CLAIMS,
    _Q_COMPANY_SUPPLY,
    _Q_DEMAND,
    _Q_SUPPLY,
    _build_claims_section,
    _build_supply_section,
    _fetch,
    _truncation_note,
)


class _FakeSession:
    """記錄每一次 run 的 Cypher，並依有沒有 LIMIT 回不同列數。"""

    def __init__(self, total: int) -> None:
        self.total = total
        self.queries: list[str] = []

    def run(self, query: str, **params):
        self.queries.append(query)
        rows = [{"i": i} for i in range(self.total)]
        # 模擬 Neo4j：帶 LIMIT 時只回前 N 列
        m = _LIMIT_RE.search(query)
        if m:
            n = int(query[m.start():m.end()].split()[-1])
            return rows[:n]
        return rows


def test_truncation_speaks_and_absence_of_truncation_also_speaks() -> None:
    """0 與缺席不得同形：沒截斷時也要印一行，否則「全部列出」與「這段壞了」一樣。"""
    assert "只列出 20／154" in _truncation_note(20, 154)
    assert "134" in _truncation_note(20, 154)
    assert "全部列出" in _truncation_note(10, 10)
    # 資料比 limit 少時不得反過來說被截斷
    assert "只列出" not in _truncation_note(10, 10)


def test_rows_come_from_the_untouched_query_and_only_the_count_strips_limit() -> None:
    """**要用的那幾列一律走原封不動的查詢。**

    首版把 `LIMIT` 拿掉改在 Python 端截——看起來等價，實測不是：帶 `LIMIT` 時
    Neo4j 走 Top-N 運算子，平手（本圖大量 confidence=0.90）的 tie-break 與全排序不同，
    於是 `co:axt` 的 20 條 claim 換了一批。舊版連跑兩次完全相同，所以那是改出來的。
    本測試鎖住：第一趟的 Cypher **必須仍帶 LIMIT**，只有第二趟（數總數）才拿掉。
    """
    session = _FakeSession(total=154)
    rows, total = _fetch(session, _Q_CLAIMS, 20)

    assert len(rows) == 20
    assert total == 154
    assert len(session.queries) == 2, "一趟取列、一趟數總數"
    assert _LIMIT_RE.search(session.queries[0]), "取列那一趟不得拿掉 LIMIT"
    assert not _LIMIT_RE.search(session.queries[1]), "數總數那一趟必須拿掉 LIMIT"


def test_every_limit_bearing_query_is_covered_by_the_regex() -> None:
    """六個區段都要被 `_fetch` 認得——漏一個就是又一段沉默的截斷。

    ⚠ `_Q_DEMAND`（硬編 LIMIT 10）與 `_Q_BOTTLENECK`（硬編 LIMIT 30）沒有 `{limit}`
    佔位符，很容易在加這個機制時被漏掉；實測它們也都在截（23→10、52→30）。
    """
    for name, query in [
        ("_Q_DEMAND", _Q_DEMAND), ("_Q_SUPPLY", _Q_SUPPLY),
        ("_Q_BOTTLENECK", _Q_BOTTLENECK), ("_Q_CLAIMS", _Q_CLAIMS),
        ("_Q_COMPANY_SUPPLY", _Q_COMPANY_SUPPLY), ("_Q_COMPANY_CLAIMS", _Q_COMPANY_CLAIMS),
    ]:
        assert _LIMIT_RE.search(query), f"{name} 沒有被 _LIMIT_RE 認出來"


def test_bottleneck_query_survives_format_because_it_has_bare_braces() -> None:
    """`_Q_BOTTLENECK` 含裸的 `coalesce(r.attributes, '{}')`，不得對它呼叫 `.format()`。

    判斷條件必須是「模板裡有沒有 `{limit}`」，不是「要不要套 limit」——
    這是實作時當場炸出來的（CypherSyntaxError: Invalid input '{'）。
    """
    assert "{}" in _Q_BOTTLENECK and "{limit}" not in _Q_BOTTLENECK
    session = _FakeSession(total=52)
    rows, total = _fetch(session, _Q_BOTTLENECK, 30)
    assert (len(rows), total) == (30, 52)
    assert "{}" in session.queries[0], "裸大括號必須原樣送到 Neo4j"


@pytest.mark.parametrize("builder", [_build_supply_section, _build_claims_section])
def test_sections_report_the_total_not_just_what_they_show(builder) -> None:
    text = builder([], 0)
    assert "無資料" in text            # 空集合仍是空集合，不偽裝成截斷
    rows = [
        {"src": "a", "rel": "SUPPLIES_TO", "dst": "b", "attrs": None,
         "confidence": 0.9, "source_ids": ["s1"],
         "statement": "x", "proof_level": "confirmed", "disproof": None, "subject": "s"}
    ]
    assert "只列出 1／9" in builder(rows, 9)
