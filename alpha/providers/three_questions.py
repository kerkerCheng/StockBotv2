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


def own_history_at(ticker: str, day: date, *, history_not_comparable: Mapping[str, Any] | None = None,
                   conn: Any = None) -> dict[str, Any]:
    """點時（as-of `day`）的已定價①——取數全部帶 as-of 欄位（價格 bar ≤ day、申報 filed ≤ day、台股月營收法定截止
    ≤ day、股數 available_on ≤ day），所以這就是「day 那天已公開的資料算出來的百分位」（INV-6）。
    ⚠ 舊版本的判斷日一律用**判斷日（台北）前一天**當 `day`：daily 05:30 才抓前一天收盤，寫敘事的人那天看到的最新
    一根 bar 是前一天的（2026-10-21 抽查 16 份手打百分位，前一天截點 15 份差 ≤0.5、含當天截點 6 份差 >1）。
    回算不等於寫入當時看到的（事後資料或程式變動）——呼叫端要標「回算」。"""
    if history_not_comparable is None and conn is None:
        return dict(_member_snapshot(ticker, day.isoformat())[0])
    inp = _inputs(ticker, day, conn or _conn_for("ro"))
    return tq.own_history(inp, today=day, history_not_comparable=history_not_comparable)


def adjusted_bars(ticker: str, today: date, *, conn: Any = None) -> list[tuple[date, float | None]]:
    """調整後收盤（與已定價③同一個口徑），bar_date ≤ today。"""
    if conn is None:
        return list(_member_snapshot(ticker, today.isoformat())[1])
    return list(_inputs(ticker, today, conn).get("adjusted_bars") or ())


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


__all__ = ["adjusted_bars", "clear_cache", "cohort_contexts", "own_history_at", "three_questions_for"]
