"""Decision Store 的唯讀查詢，供**不開整個 store** 的唯讀消費端使用。

`scripts/catalyst_watch.py` 是 daily 的 unattended entry point，它刻意用
`mode=ro` 的裸 sqlite 連線而不是 `open_default_store()`——唯讀連線碰不到
append-only authority，permission surface 因此比開整個 store 窄。SQL 住這裡而不住
腳本裡：它認識的是 Decision Store 的 schema，那是 Engine D 的東西。

⚠ 這裡只放**純讀**查詢。任何寫入都必須走 `DecisionStore` 的既有方法，
才會經過 transaction、事件記錄與 invariant 檢查。
"""
from __future__ import annotations

from typing import Any

__all__ = ["latest_coverage_assessments"]


def latest_coverage_assessments(conn) -> list[dict[str, Any]]:
    """每個 cohort 取最新一份 coverage assessment。

    ⚠ 資料源刻意是 Engine D 的 `coverage_assessments`，不是 `thesis/lifecycle.json`。
    後者只有 3 條 thesis，前者涵蓋全部 cohort；兩套 lifecycle 互不知道是既有的
    整合縫隙（已登記 ROADMAP），這裡不再蓋第三套。
    """
    rows = conn.execute(
        """
        SELECT co.company_id AS company_id, co.research_ticker AS ticker,
               ca.catalyst AS catalyst, ca.disproof AS disproof,
               ca.expiry AS expiry, ca.created_at AS created_at
          FROM coverage_assessments ca
          JOIN decision_cohorts co ON co.cohort_id = ca.cohort_id
         WHERE co.company_id IS NOT NULL
         ORDER BY ca.created_at DESC
        """
    ).fetchall()
    seen: set[str] = set()
    latest: list[dict[str, Any]] = []
    for row in rows:
        company = str(row["company_id"])
        if company in seen:
            continue
        seen.add(company)
        latest.append(dict(row))
    return latest
