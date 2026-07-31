"""Pending leads 的封閉狀態機、URL-hash 去重、harvest 紀錄與 atomic 寫檔。

只依賴標準庫（Daily Approval Loop plan U1 的硬約束）。本機的
`library/leads/pending_leads.json` 是 authority；push 只是同步機制，cloud
routine 讀 pushed baseline、不回寫（plan KTD1／KTD4）。

不變式（plan R2）：任何 status 都不影響 evidence tier。狀態只是注意力
metadata，升格入圖仍走 lead-intake／source-trace／Research Action 核准。
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from access_failures import FAILURE_CLASSES

SCHEMA_VERSION = "2"
_SUPPORTED_SCHEMA_VERSIONS = frozenset({"1", SCHEMA_VERSION})

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEADS_PATH = _ROOT / "library" / "leads" / "pending_leads.json"

# 封閉狀態機（plan R2）。key = 現況，value = 允許轉移到的狀態集合。
#   pending → triaged_go | triaged_no_go
#   triaged_go → researching → action_prepared → applied
#   任何非終態 → parked；parked → pending（un-park 後重新 triage）
# applied 是終態（已入圖真相，不再轉出）。此處刻意不讓 applied → parked：
# 對「任何狀態可 parked」的字面唯一收窄，理由是 park 一筆已入圖的 lead 會
# 隱藏已完成事實；其餘所有狀態都可 park。
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"triaged_go", "triaged_no_go", "parked"}),
    "triaged_go": frozenset({"researching", "parked"}),
    "researching": frozenset({"action_prepared", "parked"}),
    "action_prepared": frozenset({"applied", "parked"}),
    "triaged_no_go": frozenset({"parked"}),
    "applied": frozenset(),
    "parked": frozenset({"pending"}),
}

ALL_STATUSES: frozenset[str] = frozenset(ALLOWED_TRANSITIONS)

HARVEST_RESULTS: frozenset[str] = frozenset({"ok", "fetch_failed", "parse_failed"})
HARVEST_FAILURE_CLASSES: frozenset[str] = FAILURE_CLASSES


class LeadStateError(ValueError):
    """非法狀態轉移或未知 lead。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_url(url: str) -> str:
    """正規化 URL 供去重：小寫 scheme/host、去 fragment、去尾斜線。

    保留 path 與 query（EDGAR／RSS 常靠 query 或 accession 區分文件）。
    """
    cleaned = (url or "").strip()
    if not cleaned:
        raise ValueError("lead URL 不可為空")
    parts = urlsplit(cleaned)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/")
    # fragment 丟棄；query 保留原樣
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def lead_id_for(url: str) -> str:
    """URL content hash（正規化後 sha256），格式 lead_<32hex>。"""
    digest = hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()
    return "lead_" + digest[:32]


def empty_store() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "leads": {},
        "harvest_log": [],
        "source_state": {},
    }


def load(path: Path | str = DEFAULT_LEADS_PATH) -> dict[str, Any]:
    """讀 leads store；不存在回空骨架。"""
    p = Path(path)
    if not p.exists():
        return empty_store()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "leads" not in data:
        raise ValueError(f"leads store 格式非法：{p}")
    version = str(data.get("schema_version") or "1")
    if version not in _SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(f"leads store schema_version 不支援：{version}")
    # v2 只有 additive fields（raw_text／media），舊資料可 lazy migration。
    data["schema_version"] = SCHEMA_VERSION
    data.setdefault("leads", {})
    data.setdefault("harvest_log", [])
    # 各來源的增量抓取狀態（如 X 的 since_id／user_id 快取）。X API 是
    # pay-per-use（按回傳貼文數計費），since_id 讓每次只抓新貼文＝成本下限。
    data.setdefault("source_state", {})
    return data


def get_source_state(store: dict[str, Any], key: str) -> dict[str, Any]:
    return dict(store.setdefault("source_state", {}).get(key) or {})


def set_source_state(store: dict[str, Any], key: str, **fields: Any) -> dict[str, Any]:
    state = store.setdefault("source_state", {}).setdefault(key, {})
    state.update({k: v for k, v in fields.items() if v is not None})
    state["updated_at"] = _now()
    return state


def save(store: dict[str, Any], path: Path | str = DEFAULT_LEADS_PATH) -> None:
    """Atomic 寫檔（tempfile + fsync + os.replace），沿用 repo 慣例。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=p.parent,
        prefix=f".{p.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(store, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, p)
    finally:
        temp_path.unlink(missing_ok=True)


def register(
    store: dict[str, Any],
    *,
    source: str,
    url: str,
    title: str = "",
    raw_text: str | None = None,
    media: list[dict[str, Any]] | None = None,
    published_at: str | None = None,
    seen_at: str | None = None,
) -> tuple[str, bool]:
    """以 URL-hash upsert 一筆 lead；重抓只補內容，不覆寫狀態／triage。

    回傳 (lead_id, is_new)。這是 harvest 去重的唯一入口——同一 URL 重複
    harvest 只註冊一次，狀態不倒退。X 等可取得全文的來源以 raw_text 保存
    原始換行，title 只做空白正規化；media 保存來源 metadata 與 private cache ref。
    """
    source = (source or "").strip()
    if not source:
        raise ValueError("lead 必須註明 source")
    lead_id = lead_id_for(url)
    leads = store["leads"]
    clean_title = (title or "").strip()
    clean_media = _clean_media(media)
    if lead_id in leads:
        lead = leads[lead_id]
        enriched = False
        old_title = str(lead.get("title") or "")
        if (
            clean_title
            and len(clean_title) > len(old_title)
            and clean_title.startswith(old_title)
        ):
            lead["title"] = clean_title
            enriched = True
        if raw_text is not None:
            incoming_raw = str(raw_text)
            old_raw = lead.get("raw_text")
            if old_raw is None or (
                len(incoming_raw) > len(str(old_raw))
                and incoming_raw.startswith(str(old_raw))
            ):
                lead["raw_text"] = incoming_raw
                enriched = True
        if media is not None:
            merged = _merge_media(lead.get("media") or [], clean_media)
            if "media" not in lead or merged != lead.get("media"):
                lead["media"] = merged
                enriched = True
        if not lead.get("published_at") and published_at:
            lead["published_at"] = published_at
            enriched = True
        if enriched:
            lead["content_updated_at"] = _now()
            lead["entities"] = _entities_for(lead)
            lead["themes"] = _themes_for(lead)
        return lead_id, False
    lead = {
        "lead_id": lead_id,
        "source": source,
        "url": url.strip(),
        "title": clean_title,
        "published_at": published_at,
        "first_seen": seen_at or _now(),
        "status": "pending",
        "triage": None,
        "refs": {},
    }
    if raw_text is not None:
        lead["raw_text"] = str(raw_text)
    if media is not None:
        lead["media"] = clean_media
    # 具名標的是 lead 之間唯一的確定性關聯鍵（URL hash 只認同一篇文章）。
    lead["entities"] = _entities_for(lead)
    lead["themes"] = _themes_for(lead)
    leads[lead_id] = lead
    return lead_id, True


def _entities_for(lead: dict[str, Any]) -> dict[str, list[str]]:
    from engine_b.entities import extract_entities

    return extract_entities(
        title=lead.get("title"),
        raw_text=lead.get("raw_text"),
        source=lead.get("source"),
    )


def _themes_for(lead: dict[str, Any]) -> dict[str, Any]:
    """第二層關聯鍵：已註冊主題的關鍵字比對（含反證詞）。"""
    from engine_b.themes import match_themes

    return match_themes(lead.get("title"), lead.get("raw_text"))


def _clean_media(media: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if media is None:
        return []
    if not isinstance(media, list):
        raise ValueError("lead media 必須是 list")
    allowed = {
        "media_key", "type", "url", "preview_image_url", "alt_text",
        "width", "height", "duration_ms",
    }
    cache_allowed = {"local_path", "sha256", "bytes", "content_type"}
    cleaned: list[dict[str, Any]] = []
    for raw in media:
        if not isinstance(raw, dict) or not raw.get("media_key"):
            raise ValueError("每筆 media 必須有 media_key")
        item = {key: raw[key] for key in allowed if raw.get(key) is not None}
        item["media_key"] = str(raw["media_key"])
        cache = raw.get("cache")
        if cache is not None:
            if not isinstance(cache, dict):
                raise ValueError("media cache 必須是 object")
            item["cache"] = {
                key: cache[key] for key in cache_allowed if cache.get(key) is not None
            }
        cleaned.append(item)
    return cleaned


def _merge_media(
    existing: list[dict[str, Any]], incoming: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """依 media_key enrich，保留既有 cache，順序以最新 API attachments 為準。"""
    old_by_key = {str(item.get("media_key")): item for item in existing}
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in incoming:
        key = str(item["media_key"])
        combined = dict(old_by_key.get(key) or {})
        combined.update(item)
        merged.append(combined)
        seen.add(key)
    merged.extend(item for key, item in old_by_key.items() if key not in seen)
    return merged


def _require(store: dict[str, Any], lead_id: str) -> dict[str, Any]:
    lead = store["leads"].get(lead_id)
    if lead is None:
        raise LeadStateError(f"未知 lead：{lead_id}")
    return lead


def advance(
    store: dict[str, Any],
    lead_id: str,
    to_status: str,
    *,
    ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """一般性 guarded 轉移；非法轉移 raise LeadStateError。"""
    if to_status not in ALL_STATUSES:
        raise LeadStateError(f"未知狀態：{to_status}")
    lead = _require(store, lead_id)
    current = lead["status"]
    if to_status not in ALLOWED_TRANSITIONS[current]:
        raise LeadStateError(f"非法轉移：{current} → {to_status}")
    lead["status"] = to_status
    if to_status == "pending":
        # un-park：清掉舊 triage，回到待判斷
        lead["triage"] = None
    if ref:
        lead["refs"].update(ref)
    return lead


def annotate_refs(
    store: dict[str, Any],
    lead_id: str,
    *,
    refs: dict[str, Any],
) -> dict[str, Any]:
    """補充 lead provenance metadata，但不改變狀態或 evidence tier。"""
    if not refs:
        raise ValueError("refs 不可為空")
    cleaned: dict[str, Any] = {}
    for raw_key, value in refs.items():
        key = str(raw_key).strip()
        if not key:
            raise ValueError("ref key 不可為空")
        if value is None:
            raise ValueError(f"ref {key} 不可為 null")
        cleaned[key] = value
    lead = _require(store, lead_id)
    lead.setdefault("refs", {}).update(cleaned)
    return lead


def tag_campaign(
    store: dict[str, Any],
    lead_id: str,
    *,
    campaign_id: str,
) -> dict[str, Any]:
    """將 lead 納入具名研究 campaign；保留所有歷次 campaign。"""
    cleaned = str(campaign_id or "").strip()
    if not cleaned:
        raise ValueError("campaign_id 不可為空")
    lead = _require(store, lead_id)
    refs = lead.setdefault("refs", {})
    history = refs.get("campaign_ids") or []
    if not isinstance(history, list):
        raise ValueError("campaign_ids 必須是 list")
    refs["campaign_ids"] = list(dict.fromkeys([*history, cleaned]))
    return lead


def requeue_for_triage(
    store: dict[str, Any],
    lead_id: str,
    *,
    reason: str,
    campaign_id: str,
    requeued_at: str | None = None,
) -> dict[str, Any]:
    """明確 campaign 可重審舊 no-go，且不得抹掉先前 triage receipt。"""
    cleaned_reason = str(reason or "").strip()
    cleaned_campaign = str(campaign_id or "").strip()
    if not cleaned_reason or not cleaned_campaign:
        raise ValueError("requeue 必須附 reason 與 campaign_id")
    lead = _require(store, lead_id)
    if lead["status"] != "triaged_no_go":
        raise LeadStateError(
            f"campaign requeue 只允許 triaged_no_go；現況 {lead['status']}"
        )
    previous = lead.get("triage")
    if previous:
        history = lead.setdefault("triage_history", [])
        if not isinstance(history, list):
            raise ValueError("triage_history 必須是 list")
        history.append(
            {
                "status": lead["status"],
                "triage": dict(previous),
                "superseded_at": requeued_at or _now(),
                "superseded_reason": cleaned_reason,
                "campaign_id": cleaned_campaign,
            }
        )
    lead["status"] = "pending"
    lead["triage"] = None
    tag_campaign(store, lead_id, campaign_id=cleaned_campaign)
    return lead


def trace_backlog(store: dict[str, Any]) -> list[dict[str, Any]]:
    """列出 parked 的追源未果項目，避免規則書中的 backlog 變成黑洞。

    舊資料若只有 ``parked_reason`` 含 trace，也會列為 ``unstructured``；這讓
    routine 能顯示資料品質缺口，而不是因缺少新欄位就把歷史項目靜默漏掉。
    ``trace_requires_user`` 只表示需要 access／付費／優先權等人工 authority，
    不表示 claim 可信或可入圖。
    """

    rows: list[dict[str, Any]] = []
    for lead in store["leads"].values():
        if lead.get("status") != "parked":
            continue
        refs = lead.get("refs") or {}
        trace_status = str(refs.get("trace_status") or "").strip()
        parked_reason = str(refs.get("parked_reason") or "").strip()
        if not trace_status and "trace" not in parked_reason.lower():
            continue
        if trace_status in {"original_obtained", "tier_1_2_honest_passthrough"}:
            continue
        requires_user = str(refs.get("trace_requires_user") or "").lower() in {
            "1", "true", "yes",
        }
        full_title = " ".join(str(lead.get("title") or "").split())
        short_title = full_title[:197] + "..." if len(full_title) > 200 else full_title
        rows.append({
            "lead_id": lead["lead_id"],
            "title": short_title,
            "url": lead.get("url") or "",
            "trace_status": trace_status or "unstructured",
            "next_trigger": refs.get("trace_next_trigger") or "unspecified",
            "attempts_ref": refs.get("trace_attempts_ref"),
            "requires_user": requires_user,
            "lane": "pq2_manual_authority" if requires_user else "event_or_scheduled_pq1",
            "review_title": refs.get("trace_review_title"),
            "review_hint": refs.get("trace_review_hint"),
        })
    return sorted(rows, key=lambda row: (not row["requires_user"], row["lead_id"]))


def requeue_trace(
    store: dict[str, Any],
    lead_id: str,
    *,
    trigger: str,
    reason: str,
    requeued_at: str | None = None,
) -> dict[str, Any]:
    """把 exact trace review 從 parked 重新排入 pq1，並保留舊 triage receipt。"""

    cleaned_trigger = str(trigger or "").strip()
    cleaned_reason = str(reason or "").strip()
    if not cleaned_trigger or not cleaned_reason:
        raise ValueError("trace requeue 必須附 trigger 與 reason")
    lead = _require(store, lead_id)
    if lead["status"] != "parked":
        raise LeadStateError(f"trace requeue 只允許 parked；現況 {lead['status']}")
    refs = lead.get("refs") or {}
    if not refs.get("trace_status") and "trace" not in str(
        refs.get("parked_reason") or ""
    ).lower():
        raise LeadStateError("lead 沒有 trace backlog receipt")

    stamp = requeued_at or _now()
    previous = lead.get("triage")
    if previous:
        history = lead.setdefault("triage_history", [])
        if not isinstance(history, list):
            raise ValueError("triage_history 必須是 list")
        history.append({
            "status": "parked",
            "triage": dict(previous),
            "superseded_at": stamp,
            "superseded_reason": cleaned_reason,
            "trace_trigger": cleaned_trigger,
        })
    previous_flags = dict((previous or {}).get("priority_flags") or {})
    if cleaned_trigger in {"user_go", "user_requested", "access_granted"}:
        previous_flags["user_requested"] = True
    lead["status"] = "triaged_go"
    lead["triage"] = {
        "decision": "go",
        "tier": int((previous or {}).get("tier") or 4),
        "reason": cleaned_reason,
        "decided_at": stamp,
        "priority_flags": previous_flags,
    }
    lead.setdefault("refs", {}).update({
        "trace_requeued_at": stamp,
        "trace_requeue_trigger": cleaned_trigger,
    })
    return lead


_PRIORITY_FLAG_KEYS = (
    "contradiction",
    "novelty",
    "independent_source",
    "user_requested",
)


def triage(
    store: dict[str, Any],
    lead_id: str,
    *,
    go: bool,
    tier: int,
    reason: str,
    priority_flags: Mapping[str, Any] | None = None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    """對 pending lead 下 triage 判斷，轉入 triaged_go／triaged_no_go。

    tier 只是 triage 的初步來源分級記錄，**不是** evidence tier，不影響入圖
    強度（plan R2 不變式）；真正 evidence tier 由 source-trace／lead-intake 決定。

    priority_flags（可選）記 signal-triage 五要素中的 boolean 訊號
    （contradiction／novelty／independent_source／user_requested），供 priority 計分用；不影響
    狀態機、不影響 evidence tier。
    """
    if not (1 <= int(tier) <= 4):
        raise ValueError("triage tier 必須是 1–4")
    if not (reason or "").strip():
        raise ValueError("triage 必須附 reason（含 no-go 也要記原因）")
    lead = _require(store, lead_id)
    target = "triaged_go" if go else "triaged_no_go"
    if target not in ALLOWED_TRANSITIONS[lead["status"]]:
        raise LeadStateError(f"只能對 pending lead triage；現況 {lead['status']}")
    flags = {
        key: bool((priority_flags or {}).get(key))
        for key in _PRIORITY_FLAG_KEYS
        if (priority_flags or {}).get(key)
    }
    lead["status"] = target
    lead["triage"] = {
        "decision": "go" if go else "no_go",
        "tier": int(tier),
        "reason": reason.strip(),
        "decided_at": decided_at or _now(),
        "priority_flags": flags,
    }
    return lead


def record_run(
    store: dict[str, Any],
    *,
    source: str,
    result: str,
    new: int,
    run_at: str | None = None,
    failure_class: str | None = None,
) -> None:
    """記一次 harvest run 結果。parse_failed／fetch_failed 都必須誠實入帳
    （plan R4：解析失敗 ≠ 無新文）。"""
    if result not in HARVEST_RESULTS:
        raise ValueError(f"未知 harvest result：{result}")
    if failure_class is not None and failure_class not in HARVEST_FAILURE_CLASSES:
        raise ValueError(f"未知 harvest failure_class：{failure_class}")
    if result == "ok" and failure_class is not None:
        raise ValueError("successful harvest run cannot have failure_class")
    entry = {
        "run_at": run_at or _now(),
        "source": source,
        "result": result,
        "new": int(new),
    }
    if failure_class is not None:
        entry["failure_class"] = failure_class
    store["harvest_log"].append(entry)


def unresolved_harvest_failures(store: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only sources whose latest recorded attempt still failed。"""

    latest: dict[str, dict[str, Any]] = {}
    for raw in store.get("harvest_log") or []:
        if not isinstance(raw, dict) or not str(raw.get("source") or "").strip():
            continue
        latest[str(raw["source"])] = dict(raw)
    return [
        latest[source]
        for source in sorted(latest)
        if latest[source].get("result") != "ok"
    ]


def status_counts(store: dict[str, Any]) -> dict[str, int]:
    """各狀態計數，給 session digest／brief 用。"""
    counts: dict[str, int] = {}
    for lead in store["leads"].values():
        counts[lead["status"]] = counts.get(lead["status"], 0) + 1
    return counts
