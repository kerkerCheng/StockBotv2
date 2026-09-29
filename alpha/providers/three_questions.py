"""財務三題的組裝（Phase 3 Step 3.3）：取數在 Engine C、判定在 `alpha.three_questions`，這裡只把兩端接起來，
並處理**跨檔**的那一段（主題等權組成員各自的①與日線）。

只在 materialize 與互動命令跑（會開 Engine C 正式庫，唯讀）；request path 讀 artifact。
成員的①在同一個行程內記憶（同一輪 materialize 73 檔，成員會被重複用到）。
"""
from __future__ import annotations

import sqlite3
from datetime import date
from functools import lru_cache
from typing import Any, Mapping

from .. import three_questions as tq


def _open_readonly() -> sqlite3.Connection:
    """Engine C 正式庫的**唯讀**連線（三題只讀；不經 `get_conn()` 以免在讀取路徑上跑建表）。"""
    from engine_c.db import sqlite_path

    return sqlite3.connect(f"file:{sqlite_path().as_posix()}?mode=ro", uri=True, check_same_thread=False)


@lru_cache(maxsize=4)
def _conn_for(_key: str) -> sqlite3.Connection:
    return _open_readonly()


def _inputs(ticker: str, today: date, conn: Any) -> dict[str, Any]:
    from engine_c.three_question_inputs import get_three_question_inputs

    return get_three_question_inputs(ticker, conn=conn, today=today)


@lru_cache(maxsize=512)
def _member_snapshot(ticker: str, today_iso: str) -> tuple[dict[str, Any], tuple[tuple[date, float | None], ...]]:
    today = date.fromisoformat(today_iso)
    inp = _inputs(ticker, today, _conn_for("ro"))
    return tq.own_history(inp, today=today), tuple(inp.get("adjusted_bars") or ())


def clear_cache() -> None:
    _member_snapshot.cache_clear()
    _conn_for.cache_clear()


def cohort_contexts(ticker: str, *, today: date, cohorts: list[Any] | None = None
                    ) -> tuple[list[dict[str, Any]], dict[str, str] | None, list[str]]:
    """本檔所屬每一組的 `{cohort, member_results, member_bars}`（本檔除外）；一組都沒有時回缺席說明。"""
    from .theme_cohorts import current_cohorts, memberships

    errors: list[str] = []
    if cohorts is None:
        cohorts, errors = current_cohorts(as_of=today)
    if not cohorts:
        return [], {"absence_kind": "not_yet_recorded", "reason": "主題等權組未定義（Step 3.5 提 pq2、使用者定）"}, errors
    mine = memberships(ticker, cohorts)
    if not mine:
        return [], {"absence_kind": "not_yet_recorded", "reason": "不在任何主題等權組"}, errors
    out = []
    for cohort in mine:
        results, bars = {}, {}
        for member in cohort.members:
            if member.ticker == ticker.upper():
                continue                                   # 本檔排除在自己的基準之外
            own, adj = _member_snapshot(member.ticker, today.isoformat())
            results[member.ticker] = own
            bars[member.ticker] = list(adj)
        out.append({"cohort": {"record_id": cohort.cohort_id, "theme": cohort.theme,
                               "decided_on": cohort.decided_on.isoformat(), "pq2_ref": cohort.pq2_ref},
                    "member_results": results, "member_bars": bars})
    return out, None, errors


def three_questions_for(ticker: str, *, today: date, wipeout: Mapping[str, Mapping[str, Any]] | None,
                        wipeout_reason: str | None = None,
                        history_not_comparable: Mapping[str, Any] | None = None,
                        conn: Any = None) -> dict[str, Any]:
    """一檔的三題稽核區（`alpha.three_questions.evaluate` 的輸出＋組別資訊）。"""
    connection = conn or _conn_for("ro")
    inp = _inputs(ticker, today, connection)
    contexts, absence, errors = cohort_contexts(ticker, today=today)
    result = tq.evaluate(inp, today=today, wipeout=wipeout, wipeout_reason=wipeout_reason, cohorts=contexts,
                         cohort_absence=absence, history_not_comparable=history_not_comparable)
    result["filer_class"] = inp.get("filer_class")
    result["cohort_parse_errors"] = errors
    return result


__all__ = ["clear_cache", "cohort_contexts", "three_questions_for"]
