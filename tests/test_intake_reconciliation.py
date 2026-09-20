"""入圖 gate 的 reconciliation 檢查：哪些關係算「未投影的 canonical edge」。

## 為什麼要鎖住排除清單

`CITES`／`ABOUT`／`QUOTES`／`FROM_DOC` 都是**走訪關係**，不是 canonical knowledge edge，
本來就沒有 `edge_key` 的概念。把它們算進 `legacy` 會讓 gate 對**所有** RA 一律拒絕。

## 事發（2026-09-20）

V1（逐字入圖，2026-09-18）把 1,105 段逐字載進圖，產生 `QUOTES` 2,968 ＋ `FROM_DOC` 1,058
＝ **4,026 筆被誤判成 legacy**，於是 `apply_research_action` 對所有 RA 回
`partial: graph reconciliation is incomplete`——**入圖閘門從那天起全面卡死**。

兩天沒有任何東西會叫，因為中間沒有人 apply 過 RA（pq2 [570] 是 09-12 prepare 的）。
與 2026-09-04 的 `legacy=1` 是同一個閘門、不同成因（那次是重複節點）。

⚠ 這條測試刻意測**源碼字串**而不是跑 Neo4j：它要防的是「有人把類型從清單裡拿掉」，
而那是一個編輯動作，不需要資料庫就驗得出來。
"""
from __future__ import annotations

import pathlib
import re


def _reconciliation_source() -> str:
    return pathlib.Path("intake/application.py").read_text(encoding="utf-8")


def test_traversal_relationships_are_excluded_from_the_legacy_check() -> None:
    """四種走訪關係都必須在排除清單裡——少一種就會把入圖閘門鎖死。"""
    src = _reconciliation_source()
    m = re.search(r"WHERE NOT type\(r\) IN \[([^\]]*)\]", src)
    assert m, "找不到 legacy 檢查的排除清單"
    listed = {x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()}
    for kind in ("CITES", "ABOUT", "QUOTES", "FROM_DOC"):
        assert kind in listed, (
            f"{kind} 不在排除清單裡——它是走訪關係、沒有 edge_key，"
            "算進 legacy 會讓 apply_research_action 對所有 RA 一律拒絕")


def test_the_other_two_reconciliation_checks_are_untouched() -> None:
    """⚠ 修的是**分類錯誤**不是放寬 gate：另外兩項檢查一字未動。"""
    src = _reconciliation_source()
    assert "r.edge_key IS NOT NULL AND r.projected_at IS NULL" in src,         "unprojected（有 edge_key 卻沒投影）必須照舊"
    assert "NOT (e)-[:CITES]->(:SourceDoc)" in src,         "orphaned_evidence 必須照舊"
    assert "if unprojected or legacy or orphaned:" in src,         "三項任一非零仍然要擋下——gate 本身沒有被放寬"
