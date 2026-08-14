"""Thesis 複查排程——「什麼時候該重看」的唯一權威。

L7 要求每條 disproof 條件附核查頻率，但**頻率不是唯一的排程來源**。真正決定
「什麼時候會知道答案」的往往是催化劑：AXT v4 的裁決點是 2026 Q3 財報的毛利率與
10-Q 的合約 exhibit，Coherent 是 12 月的六吋 InP 產能倍增檢核點。

2026-08-13 實測：這些催化劑**寫在 memo 與 lifecycle 的散文 note 裡，卻沒有任何欄位
承載它們**，於是 `next_check` 退化成 `last_checked + check_interval_days` 的機械日曆
——AXT 的複查被排到 2026-11-15，而它的裁決點在那之前。thesis 正確識別了催化劑，
排程卻讀不到。這是 L7 的變體：欄位有填不等於流程存在，這裡是流程存在但讀錯欄位。

本模組把兩個來源合成一個生效到期日，並回報**是哪一個觸發的**，因為使用者要據此
決定「現在該做什麼」——固定週期到期是「例行複查」，催化劑到期是「去讀那份文件」。

⚠ 本模組刻意不依賴 store／Neo4j／Engine C，因為它有兩個分屬不同層的消費者：
SessionStart hook（`crons/thesis_freshness_check.py`）與健康審查
（`query/health_audit.py`）。先前兩邊各有一份到期判準，是同一個判準跑兩次。
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

CADENCE = "cadence"
CATALYST = "catalyst"
REVIEW_REQUIRED = "review_required"
UNSCHEDULED = "unscheduled"


def _parse(value: Any) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def catalyst_checkpoints(entry: Mapping[str, Any]) -> list[dict[str, Any]]:
    """正規化 `catalyst_checkpoints`；缺欄位或日期無法解析的直接略過。

    ``date_confidence`` 只有兩個值：``confirmed``（公司已公告日期）與
    ``estimated``（由歷史申報節奏推估）。**推估的日期照樣排程**——提早看一次的成本
    遠低於錯過裁決點，但呈現時必須標明，不得讓推估值看起來像已公告。
    """
    raw = entry.get("catalyst_checkpoints")
    if not isinstance(raw, (list, tuple)):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        when = _parse(item.get("date"))
        if when is None:
            continue
        confidence = str(item.get("date_confidence") or "estimated")
        out.append(
            {
                "date": when,
                "what": str(item.get("what") or "未命名催化劑"),
                "decides": str(item.get("decides") or ""),
                "date_confidence": confidence if confidence in {"confirmed", "estimated"} else "estimated",
            }
        )
    return sorted(out, key=lambda item: item["date"])


def effective_next_check(
    entry: Mapping[str, Any], *, today: date | None = None
) -> tuple[date | None, str, dict[str, Any] | None]:
    """回傳 (生效到期日, 來源, 觸發的 checkpoint)。

    來源取 ``next_check``（固定週期）與**尚未被複查涵蓋的**催化劑中較早的那個。
    「尚未被複查涵蓋」＝ checkpoint 日期晚於 ``last_checked``；已經在上次複查之前
    發生的催化劑不再排程，否則每次都會重新喚醒（那是 2026-08-12 已記錄過的
    reactivation 迴圈形狀）。

    催化劑日期**已過但仍晚於 last_checked** 時照樣算到期——那正是「催化劑到了卻沒人
    去看」的情況，不該因為日期在過去就安靜跳過。
    """
    today = today or date.today()
    last_checked = _parse(entry.get("last_checked"))

    candidates: list[tuple[date, str, dict[str, Any] | None]] = []
    cadence = _parse(entry.get("next_check"))
    if cadence is not None:
        candidates.append((cadence, CADENCE, None))
    for checkpoint in catalyst_checkpoints(entry):
        if last_checked is not None and checkpoint["date"] <= last_checked:
            continue
        candidates.append((checkpoint["date"], CATALYST, checkpoint))

    if not candidates:
        return None, UNSCHEDULED, None
    # 同日時催化劑優先呈現：它帶著「去讀哪份文件」的資訊，例行複查沒有。
    candidates.sort(key=lambda item: (item[0], item[1] != CATALYST))
    return candidates[0]


def is_due(entry: Mapping[str, Any], *, today: date | None = None) -> tuple[bool, str]:
    """回傳 (是否到期, 人可讀的原因)。``review_required`` 恆視為到期。"""
    today = today or date.today()
    if entry.get("status") == REVIEW_REQUIRED:
        return True, REVIEW_REQUIRED
    when, source, checkpoint = effective_next_check(entry, today=today)
    if when is None:
        # 沒有任何排程來源＝沒有出口。維持既有行為（視為到期）並讓原因說清楚。
        return True, "未設定 next_check 或 catalyst_checkpoints"
    if when > today:
        return False, ""
    if source == CATALYST and checkpoint is not None:
        mark = "" if checkpoint["date_confidence"] == "confirmed" else "（日期為推估）"
        detail = f"催化劑 {when}{mark}：{checkpoint['what']}"
        if checkpoint["decides"]:
            detail += f" — 裁決 {checkpoint['decides']}"
        return True, detail
    return True, f"到期 {when}"


__all__ = [
    "CADENCE",
    "CATALYST",
    "REVIEW_REQUIRED",
    "UNSCHEDULED",
    "catalyst_checkpoints",
    "effective_next_check",
    "is_due",
]
