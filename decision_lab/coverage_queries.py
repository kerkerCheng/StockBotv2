"""Decision Store 的唯讀查詢，供**不開整個 store** 的唯讀消費端使用。

`scripts/catalyst_watch.py` 是 daily 的 unattended entry point，它刻意用
`mode=ro` 的裸 sqlite 連線而不是 `open_default_store()`——唯讀連線碰不到
append-only authority，permission surface 因此比開整個 store 窄。SQL 住這裡而不住
腳本裡：它認識的是 Decision Store 的 schema，那是 Engine D 的東西。

⚠ 這裡只放**純讀**查詢。任何寫入都必須走 `DecisionStore` 的既有方法，
才會經過 transaction、事件記錄與 invariant 檢查。
"""
from __future__ import annotations

import json
from typing import Any

__all__ = ["company_decision_facts", "latest_coverage_assessments"]


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


#: `company_decision_facts` 從 `sizing` payload 只取這幾個**研究**欄位。
#: ⚠ 白名單是刻意的：同一個 dict 裡還有 `live_current_position`／`single_position_nav_cap`／
#: `live_blockers`，那些是資本與部位，唯讀 read model 一個都不得帶走。
_SIZING_RESEARCH_KEYS = ("research_status", "weakest_axis", "rubric_version")


def _cutoff(as_of: str | None) -> str | None:
    """as-of 的日粒度截止（YYYY-MM-DD）。

    Decision Store 的時間欄位有兩種寫法（`2026-07-22 06:22:25` 與
    `2026-08-31T11:30:20.678605+00:00`），但**前十個字元都是 ISO 日期**，所以用
    `substr(col, 1, 10) <= ?` 比對日期即可，不必正規化整個 timestamp。
    截止日當天的紀錄算「T 時刻已知」，與 `ResearchContext.as_of` 的日粒度一致。
    """
    if not as_of:
        return None
    text = str(as_of).strip()
    if len(text) < 10:
        raise ValueError(f"as_of 必須是 YYYY-MM-DD 開頭的日期：{as_of!r}")
    return text[:10]


def company_decision_facts(
    conn, company_id: str, *, as_of: str | None = None
) -> dict[str, Any] | None:
    """某公司的**公開** cohort 事實（唯讀、單一公司）。供 `briefing/alpha_view` 消費。

    - `as_of` 非 None 時做**真正的歷史過濾**：Decision Store 是 append-only 且每張表都帶
      時間戳，所以「T 時刻 Engine D 知道什麼」答得出來——cohort 的 `created_at`、decision
      的 `effective_at`、coverage 的 `created_at`、lifecycle 事件的 `effective_at`、
      variant perception 的 `created_at`（含 supersede 的時點）全部以 `as_of` 截止。
      回傳值帶 `point_in_time`，讓消費端能驗證它拿到的確實是過濾過的。
    - 選 cohort 的規則寫在回傳值裡（`selection_rule`），不藏在呼叫端：有 decision 的 cohort
      取 `effective_at` 最新者；都沒有 decision 時取最新建立的 cohort。同公司有幾個 cohort
      也一併回報（`cohort_count`），讓消費端知道自己只看到其中一個。
    - 只回研究欄位；部位／NAV／cap 一個都不會出現（`_SIZING_RESEARCH_KEYS` 白名單）。

    回 `None`＝（截至 `as_of`）Engine D 沒有這家公司的 cohort。
    """
    cutoff = _cutoff(as_of)

    def dated(column: str) -> tuple[str, tuple[str, ...]]:
        if cutoff is None:
            return "", ()
        return f" AND substr({column}, 1, 10) <= ?", (cutoff,)

    clause, params = dated("created_at")
    cohorts = conn.execute(
        f"""
        SELECT cohort_id, research_ticker, created_at
          FROM decision_cohorts
         WHERE company_id = ?{clause}
         ORDER BY created_at, cohort_id
        """,
        (company_id, *params),
    ).fetchall()
    if not cohorts:
        return None

    best: tuple[tuple[int, str], Any, Any] | None = None
    clause, params = dated("effective_at")
    for cohort in cohorts:
        decision = conn.execute(
            f"""
            SELECT decision_id, payload_json, effective_at, coverage_assessment_id
              FROM system_decisions
             WHERE cohort_id = ?{clause}
             ORDER BY effective_at DESC, decision_id DESC
             LIMIT 1
            """,
            (cohort["cohort_id"], *params),
        ).fetchone()
        key = (1, str(decision["effective_at"])) if decision else (0, str(cohort["created_at"]))
        if best is None or key > best[0]:
            best = (key, cohort, decision)
    assert best is not None
    _key, cohort, decision = best
    cohort_id = str(cohort["cohort_id"])

    facts: dict[str, Any] = {
        "cohort_id": cohort_id,
        "cohort_count": len(cohorts),
        "selection_rule": "latest_decision_effective_at_else_latest_created",
        "point_in_time": {"mode": "as_of" if cutoff else "current", "as_of": cutoff},
    }
    coverage_row = None
    if decision is not None:
        payload = json.loads(decision["payload_json"])
        sizing = payload.get("sizing") if isinstance(payload, dict) else None
        sizing = sizing if isinstance(sizing, dict) else {}
        facts["decision_effective_at"] = decision["effective_at"]
        for key in _SIZING_RESEARCH_KEYS:
            facts[key] = sizing.get(key)
        facts["legacy_axis_levels"] = {
            str(axis): str(item.get("effective_level") or item.get("level") or "unknown")
            for axis, item in (sizing.get("axis_results") or {}).items()
            if isinstance(item, dict)
        }
        if decision["coverage_assessment_id"]:
            # decision 引用的 assessment 一定早於 decision 本身，天然滿足 as_of
            coverage_row = conn.execute(
                """
                SELECT catalyst, disproof, expiry, created_at
                  FROM coverage_assessments WHERE assessment_id = ?
                """,
                (decision["coverage_assessment_id"],),
            ).fetchone()
    if coverage_row is None:
        clause, params = dated("created_at")
        coverage_row = conn.execute(
            f"""
            SELECT catalyst, disproof, expiry, created_at
              FROM coverage_assessments
             WHERE cohort_id = ?{clause}
             ORDER BY created_at DESC, assessment_id DESC
             LIMIT 1
            """,
            (cohort_id, *params),
        ).fetchone()
    if coverage_row is not None:
        facts["catalyst"] = coverage_row["catalyst"]
        facts["disproof"] = coverage_row["disproof"]
        facts["expiry"] = coverage_row["expiry"]
        facts["coverage_created_at"] = coverage_row["created_at"]

    clause, params = dated("started_at")
    epoch = conn.execute(
        f"""
        SELECT epoch, status, review_due_at FROM probe_lifecycle_epochs
         WHERE cohort_id = ?{clause} ORDER BY epoch DESC LIMIT 1
        """,
        (cohort_id, *params),
    ).fetchone()
    if epoch is None:
        # 沒有 epoch 列時 store.current_lifecycle 的既定語意是 active；這裡沿用，不另創。
        facts["lifecycle_status"] = "active"
        facts["review_due_at"] = None
    elif cutoff is None:
        facts["lifecycle_status"] = str(epoch["status"])
        facts["review_due_at"] = epoch["review_due_at"]
    else:
        # epoch 列的 status 是**當前**值；T 時刻的狀態要從 lifecycle 事件回放：
        # 該 epoch 在 as_of 前最後一次轉換的 to_status，沒有事件就是 epoch 起始的 active。
        event = conn.execute(
            """
            SELECT to_status FROM probe_lifecycle_events
             WHERE cohort_id = ? AND epoch = ? AND substr(effective_at, 1, 10) <= ?
             ORDER BY effective_at DESC, lifecycle_event_id DESC LIMIT 1
            """,
            (cohort_id, int(epoch["epoch"]), cutoff),
        ).fetchone()
        facts["lifecycle_status"] = str(event["to_status"]) if event else "active"
        facts["review_due_at"] = None          # review_due_at 沒有歷史，as-of 下不回答

    if cutoff is None:
        perception = conn.execute(
            """
            SELECT t.variant_perception, t.created_at
              FROM cohort_thesis t
              JOIN decision_cohorts c ON c.cohort_id = t.cohort_id
             WHERE c.company_id = ?
               AND NOT EXISTS (SELECT 1 FROM cohort_thesis n WHERE n.supersedes_id = t.thesis_id)
             ORDER BY t.created_at DESC, t.thesis_id DESC
             LIMIT 1
            """,
            (company_id,),
        ).fetchone()
    else:
        # T 時刻「尚未被 supersede」＝supersede 它的那筆在 T 之後才寫
        perception = conn.execute(
            """
            SELECT t.variant_perception, t.created_at
              FROM cohort_thesis t
              JOIN decision_cohorts c ON c.cohort_id = t.cohort_id
             WHERE c.company_id = ?
               AND substr(t.created_at, 1, 10) <= ?
               AND NOT EXISTS (
                   SELECT 1 FROM cohort_thesis n
                    WHERE n.supersedes_id = t.thesis_id
                      AND substr(n.created_at, 1, 10) <= ?
               )
             ORDER BY t.created_at DESC, t.thesis_id DESC
             LIMIT 1
            """,
            (company_id, cutoff, cutoff),
        ).fetchone()
    if perception is not None:
        facts["variant_perception"] = perception["variant_perception"]
        facts["variant_perception_created_at"] = perception["created_at"]
    return facts
