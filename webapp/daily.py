"""「每日」頁的 state artifact（2026-10-07 使用者指示：心跳太雜）：Discord 那一則（短版）照抄。

照抄 daily ⑱ 寫下的 `brief_<日期>.md` 與當天每日摘要、雷達收據的計數，**一個字都不改、不重算**。
完整心跳五段**不進這一頁**（同日使用者：「不需要給我看的…不是收起來 是拿掉」）：它照樣每天寫進 heartbeat 目錄給互動
session 查細節；你要看的基本狀態（候選各格、watch 今日、反證、無到期的等待、健康度）在短版的 ④（`crons/daily_brief.py`）。
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from typing import Any, Mapping

from .contracts import STATE_SCHEMA_VERSIONS, canonical_digest, state_freshness_identity

DAILY_MATERIALIZER_VERSION = "webapp-materialize-daily/1"

DAILY_THIS_IS_NOT: tuple[str, ...] = (
    "不是新的判讀：短版是 daily ⑱ 當下寫的檔，本頁照抄；TL;DR 那兩段是 LLM 寫的提議（每句指得回當天的 lead），"
    "不是判定——判定只在互動 session。",
    "不重算、不重跑：要更新就等明天的 daily，或在本機重跑心跳與 `python -m webapp materialize --daily`。",
)


def build_daily_artifact(*, day: date, brief_md: str | None,
                         digest: Mapping[str, Any] | None = None, radar_summary: Mapping[str, Any] | None = None,
                         generated_at: datetime | None = None) -> dict[str, Any]:
    """**純函式**。短版讀不到就寫明缺席（L16：由產生缺席的這一端宣告），不是空字串。"""
    stamp = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    brief = ({"markdown": brief_md, "absence": None} if brief_md else
             {"markdown": None, "absence": {"kind": "upstream_unavailable",
                                            "reason": f"brief_{day.isoformat()}.md 不在——短版今天沒寫出來"
                                                      "（心跳沒帶 --brief-out，或 ⑱ 沒跑）"}})
    payload: dict[str, Any] = {
        "schema_version": STATE_SCHEMA_VERSIONS["daily"],
        "kind": "daily",
        "title": f"每日：{day.isoformat()}",
        "generated_at": stamp.isoformat(),
        "as_of": day.isoformat(),
        "point_in_time": {"mode": "current", "as_of": day.isoformat()},
        "authority": {"function": "crons.heartbeat ⑱ 寫的短版（crons/daily_brief.py）＋ engine_b.digest（每日摘要）"
                                  "＋ engine_b.radar（收據）",
                      "command": "python -m webapp materialize --daily",
                      "note": "照抄 daily 當天寫下的檔；本層不重算、不判讀。"},
        "brief": brief,
        "digest": {"summary": dict((digest or {}).get("summary") or {}), "present": digest is not None},
        "radar": dict(radar_summary or {}),
        "this_is_not": list(DAILY_THIS_IS_NOT),
        "materializer": {"version": DAILY_MATERIALIZER_VERSION,
                         "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                         "note": "artifact 是 derived cache，不是 authority——刪掉重跑就會回來（L10）"},
    }
    payload["freshness_identity"] = state_freshness_identity(
        kind="daily", as_of=day.isoformat(),
        identity={"day": day.isoformat(), "brief": bool(brief_md), "digest": digest is not None})
    payload["content_digest"] = canonical_digest(payload)
    return payload


__all__ = ["DAILY_MATERIALIZER_VERSION", "DAILY_THIS_IS_NOT", "build_daily_artifact"]
