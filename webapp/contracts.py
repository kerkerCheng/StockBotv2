"""Materialized Analyst View 的**契約**：一份 artifact 長什麼樣、什麼時候算 stale、什麼時候 fail closed。

## 產品 invariant（本層是它的可執行形式）

> **LLM changes cognition; APP reads cognition.**

`AlphaInvestmentView`（canonical read model）與 `AnalystView`（消費者投影）都是**組裝**出來的：
它們會讀 Neo4j、Engine C SQLite、三本 private ledger，跑 fundamental／valuation／implied-return／
refresh 四個模型。實測一次約 4.2 秒。**那不是一條 HTTP request 該做的事**——不只是慢，而是
「點一下就重跑一次研究」讓 request path 有能力改變（或看起來改變）系統對一家公司的認知。

所以：**materialize 與 serve 是兩條不同的責任鏈**。

```
authority（圖／Engine C／ledger）
      ↓  python -m webapp materialize   ← 唯一會跑模型的地方
AlphaInvestmentView → AnalystView → MaterializedArtifact（JSON 檔）
      ↓  python -m webapp serve         ← 只做 read + parse + validate
HTTP GET
```

## 四條硬要求

1. **artifact 不是 authority。** 它是 derived cache：刪掉它不會失去任何真相，重跑
   materialize 就會回來。它**不得**被任何人當成資料來源回寫。
2. **atomic write。** 先寫 `<name>.tmp-<pid>` 再 `os.replace`——半份 JSON 永遠不會被讀到。
3. **malformed／partial 一律 fail closed。** 解析失敗、schema_version 不符、digest 對不上、
   必要欄位缺席 → `ArtifactUnavailable`，**不回半份、不即時重建**。
   「讀不到」與「這檔沒有研究結論」是兩件事，不得同形（L12）。
4. **stale 是狀態不是錯誤。** 過期的 artifact 照樣回，但明確標成 stale ＋ 年齡；
   **request path 絕不因為 stale 就重建**——那正是「點一下就重跑研究」的後門。
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

#: artifact 的 schema 版本。**讀取端硬性比對**：版本不符 ＝ fail closed，不嘗試相容。
#: 相容性靠重跑 materialize 取得，而那是廉價且可重建的（L10：拿得回來的東西不背相容包袱）。
ARTIFACT_SCHEMA_VERSION = "stockbot-app/analyst-view/1"

#: 一份 artifact 的必要欄位。缺任何一個都是 partial write 或版本漂移 → fail closed。
REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "analyst_view_schema_version", "source_schema_version",
    "ticker", "company_id", "company_label", "generated_at", "as_of", "point_in_time_mode",
    "research_context_digest", "freshness_identity", "content_digest",
    "readiness", "refresh", "overview", "view", "materializer",
)

#: **state artifact**（跨標的的單一 JSON，不是 per-ticker）的 kind → schema 版本。
#: 這是**封閉字彙**：新 kind 必須先在這裡登記，store 才認得（`STATE_KINDS` 由此導出，
#: 不另抄一份）。目前只有 `ranking`；coverage／positions／beta／watches 依 ROADMAP 逐一加。
STATE_SCHEMA_VERSIONS: dict[str, str] = {
    "ranking": "stockbot-app/ranking/1",
    "beta": "stockbot-app/beta/1",
    "coverage": "stockbot-app/coverage/1",
    "watches": "stockbot-app/watches/1",
    "positions": "stockbot-app/positions/1",
}
STATE_KINDS: tuple[str, ...] = tuple(STATE_SCHEMA_VERSIONS)

#: state artifact 的必要欄位。內容欄位（rows／sectors…）由各 kind 自己定義；這裡只鎖
#: 「每一份都答得出：是哪一種、何時生成、什麼視角、誰是 authority、有沒有被改過」。
STATE_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "kind", "generated_at", "as_of", "point_in_time",
    "authority", "freshness_identity", "content_digest", "materializer",
)

#: 預設新鮮度上限（小時）。可用 `STOCKBOT_APP_MAX_AGE_HOURS` 覆寫。
#: ⚠ 這是**呈現用的年齡門檻**，不是資料正確性的判準——真正的「什麼變了」由 refresh 引擎
#: 在 materialize 當下算好並寫進 artifact（`refresh.overall`）。年齡只回答「這份快照多舊」。
DEFAULT_MAX_AGE_HOURS = 24.0

FRESH = "fresh"
STALE = "stale"


class ArtifactUnavailable(RuntimeError):
    """artifact 讀不到／不完整／版本不符。**這不是「這檔沒有研究結論」**，兩者不得同形。"""

    def __init__(self, ticker: str, reason: str) -> None:
        super().__init__(f"{ticker}: {reason}")
        self.ticker = ticker
        # state artifact 的主詞是 kind 不是 ticker；兩個名字指同一個值。
        self.subject = ticker
        self.reason = reason


def canonical_digest(payload: Mapping[str, Any]) -> str:
    """對 artifact 內容算 SHA-256（排除 `content_digest` 自己）。partial write 與人手改檔都會被抓到。"""
    body = {k: v for k, v in payload.items() if k != "content_digest"}
    text = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def freshness_identity(*, ticker: str, as_of: str | None, point_in_time_mode: str,
                       research_context_digest: str | None, source_schema_version: str,
                       readiness_state: str, refresh_overall: str) -> str:
    """**這份 artifact 是在什麼認知狀態下產生的**——一個可比對的身分。

    兩次 materialize 若 identity 相同，代表 point-in-time 視角、研究 context digest、read model
    版本、readiness 與 refresh 整體狀態都沒變。它**不是** content digest：內容可能因現價變動而
    改變，但認知狀態沒變。分開兩個 digest 是刻意的——「價格動了」與「我們的判斷該重看了」
    是兩件事，共用一個訊號就會讓其中一件永遠讀不出來（L12）。
    """
    text = json.dumps({
        "ticker": ticker, "as_of": as_of, "point_in_time_mode": point_in_time_mode,
        "research_context_digest": research_context_digest,
        "source_schema_version": source_schema_version,
        "readiness_state": readiness_state, "refresh_overall": refresh_overall,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def state_freshness_identity(*, kind: str, as_of: str | None, identity: Any) -> str:
    """state artifact 的**認知狀態身分**。與 per-ticker 的 `freshness_identity` 同一個用途：
    兩次 materialize 若 identity 相同，代表「我們的判斷該重看了」這件事沒發生——即使
    content digest 因為文件計數或時戳而不同（L12：兩個訊號分開）。
    每種 kind 自己決定 identity 裡放什麼；本函式只負責把它變成可比對的雜湊。
    """
    text = json.dumps({"kind": kind, "as_of": as_of, "identity": identity},
                      ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def max_age_hours() -> float:
    raw = os.environ.get("STOCKBOT_APP_MAX_AGE_HOURS")
    if not raw:
        return DEFAULT_MAX_AGE_HOURS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_MAX_AGE_HOURS
    return value if value > 0 else DEFAULT_MAX_AGE_HOURS


@dataclass(frozen=True, slots=True)
class Freshness:
    """artifact 的年齡狀態。**純算術**：`now − generated_at` 與一個宣告好的門檻，沒有判斷。"""

    state: str
    age_seconds: float
    generated_at: datetime
    max_age_hours: float

    @property
    def age_hours(self) -> float:
        return self.age_seconds / 3600.0

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state, "age_seconds": round(self.age_seconds, 3),
                "age_hours": round(self.age_hours, 3),
                "generated_at": self.generated_at.isoformat(),
                "max_age_hours": self.max_age_hours,
                "rule": f"age > {self.max_age_hours}h ＝ stale。**stale 不會觸發重建**——"
                        "重建是 materialize 的責任，不是 HTTP request 的。"}


def freshness_of(generated_at: datetime, *, now: datetime | None = None,
                 limit_hours: float | None = None) -> Freshness:
    limit = max_age_hours() if limit_hours is None else limit_hours
    moment = now or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    age = (moment - generated_at).total_seconds()
    return Freshness(state=STALE if age > limit * 3600.0 else FRESH, age_seconds=age,
                     generated_at=generated_at, max_age_hours=limit)


def validate_artifact(ticker: str, payload: Any) -> Mapping[str, Any]:
    """讀取端的 fail-closed 檢查。通過才回 payload；否則 `ArtifactUnavailable`＋逐字理由。"""
    if not isinstance(payload, Mapping):
        raise ArtifactUnavailable(ticker, "artifact 不是物件（可能是半份寫入或被改壞）")
    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        raise ArtifactUnavailable(ticker, f"artifact 缺必要欄位 {missing}——partial write 一律拒收")
    version = payload.get("schema_version")
    if version != ARTIFACT_SCHEMA_VERSION:
        raise ArtifactUnavailable(
            ticker, f"artifact schema {version!r} 與本版 {ARTIFACT_SCHEMA_VERSION!r} 不符——"
                    "請重跑 `python -m webapp materialize`（artifact 是可重建的 cache，不是 authority）")
    stored = payload.get("content_digest")
    actual = canonical_digest(payload)
    if stored != actual:
        raise ArtifactUnavailable(ticker, "artifact content_digest 對不上——內容在寫入後被改過或寫到一半")
    if str(payload.get("ticker") or "").upper() != ticker.upper():
        raise ArtifactUnavailable(ticker, f"artifact 內的 ticker 是 {payload.get('ticker')!r}——檔名與內容不一致")
    return payload


def validate_state_artifact(kind: str, payload: Any) -> Mapping[str, Any]:
    """state artifact 讀取端的 fail-closed 檢查——與 `validate_artifact` 同一套紀律，主詞是 kind。"""
    if kind not in STATE_SCHEMA_VERSIONS:
        raise ArtifactUnavailable(
            kind, f"未登記的 state kind {kind!r}——封閉字彙只有 {sorted(STATE_SCHEMA_VERSIONS)}")
    if not isinstance(payload, Mapping):
        raise ArtifactUnavailable(kind, "artifact 不是物件（可能是半份寫入或被改壞）")
    missing = [f for f in STATE_REQUIRED_FIELDS if f not in payload]
    if missing:
        raise ArtifactUnavailable(kind, f"artifact 缺必要欄位 {missing}——partial write 一律拒收")
    if payload.get("kind") != kind:
        raise ArtifactUnavailable(kind, f"artifact 內的 kind 是 {payload.get('kind')!r}——檔名與內容不一致")
    version = payload.get("schema_version")
    expected = STATE_SCHEMA_VERSIONS[kind]
    if version != expected:
        raise ArtifactUnavailable(
            kind, f"artifact schema {version!r} 與本版 {expected!r} 不符——"
                  f"請重跑 `python -m webapp materialize --{kind}`（artifact 是可重建的 cache，不是 authority）")
    if payload.get("content_digest") != canonical_digest(payload):
        raise ArtifactUnavailable(kind, "artifact content_digest 對不上——內容在寫入後被改過或寫到一半")
    return payload


__all__ = [
    "ARTIFACT_SCHEMA_VERSION", "ArtifactUnavailable", "DEFAULT_MAX_AGE_HOURS", "FRESH",
    "Freshness", "REQUIRED_FIELDS", "STALE", "STATE_KINDS", "STATE_REQUIRED_FIELDS",
    "STATE_SCHEMA_VERSIONS", "canonical_digest", "freshness_identity", "freshness_of",
    "max_age_hours", "state_freshness_identity", "validate_artifact", "validate_state_artifact",
]
