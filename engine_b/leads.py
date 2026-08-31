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
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

from access_failures import FAILURE_CLASSES
from engine_b.lead_refs import (
    PRIMARY_SOURCE_TIER,
    get_trace_status_registry,
    is_primary_source,
    validate_ref_updates,
)

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
    cleaned_ref = validate_ref_updates(ref) if ref else {}
    lead = _require(store, lead_id)
    if (
        to_status == "parked"
        and cleaned_ref.get("trace_next_trigger")
        and str(cleaned_ref.get("trace_requires_user") or "").lower()
        not in {"1", "true", "yes"}
    ):
        # trace_next_trigger 保留給人讀；真正的 routine linkage 使用封閉 kind
        # 與確定性 entities。新 related signal 只把它排回 bounded pq1，不提高
        # evidence tier，也不放寬 graph admission。
        from engine_b.entities import lead_entities

        entities = sorted(lead_entities(lead))
        if entities:
            cleaned_ref.setdefault("trace_trigger_kind", "related_entity_signal")
            cleaned_ref.setdefault("trace_trigger_entities", entities)
    current = lead["status"]
    if to_status not in ALLOWED_TRANSITIONS[current]:
        raise LeadStateError(f"非法轉移：{current} → {to_status}")
    lead["status"] = to_status
    if to_status == "pending":
        # un-park：清掉舊 triage，回到待判斷
        lead["triage"] = None
    if cleaned_ref:
        lead["refs"].update(cleaned_ref)

    # [321] 入口端：park 成追源等待的當下就建 Event Watch，讓它有到期日。
    # 沒有這一步，遷移只修好存量，新 park 的立刻變回沒人管的等待（L13）。
    if to_status == "parked":
        refs = lead.get("refs") or {}
        trace_status = str(refs.get("trace_status") or "").strip()
        parked_reason = str(refs.get("parked_reason") or "").strip()
        has_trace = bool(trace_status) or "trace" in parked_reason.lower()
        requires_user = str(refs.get("trace_requires_user") or "").lower() in {
            "1", "true", "yes",
        }
        if (
            has_trace
            and not requires_user
            and not get_trace_status_registry().is_terminal(trace_status)
        ):
            from engine_b import event_watch as ew

            ew.ensure_trace_watch(
                lead_id,
                kind=str(refs.get("trace_trigger_kind") or "related_entity_signal"),
                entities=refs.get("trace_trigger_entities") or (),
                query_hint=str(refs.get("trace_next_trigger") or ""),
                note=f"park 時自動建立；trace_status={trace_status or 'unstructured'}",
                consumed_entities=refs.get("trace_requeue_consumed_entities") or (),
                created_at=(lead.get("triage") or {}).get("decided_at"),
            )
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
    cleaned = validate_ref_updates(refs)
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


#: 通過 triage 的狀態——代表「我們判斷過它值得研究」。`triaged_no_go` 與 `pending`
#: 刻意排除：前者已被判定不值得，後者還沒被判斷過，兩者都不該推動 onboarding。
_VETTED_STATUSES: frozenset[str] = frozenset(
    {"triaged_go", "researching", "action_prepared", "applied", "parked"}
)


def onboard_candidates(store: dict[str, Any]) -> list[dict[str, Any]]:
    """已通過 triage 的 lead 裡逐字點名、但 registry 沒有的標的。

    **這裡補的是一個結構性黑洞。** pq2 的六個 collector 沒有一個負責
    「這家公司該不該註冊」：已有 cohort 但缺可交易 ticker 的走
    `decision_lab.brief.identity_registration_pending`；而**完全不在 registry、
    也沒有 cohort 的公司，先前沒有任何機制會讓它浮出來**。2026-08-25 實測：
    一條 pq1 研究點名 Largan(3008)、FOCI(3363)、TFC 三家 FAU 供應商，
    registry 76 家裡一家都沒有，而「也許該 onboard Largan」這個判斷只活在
    private 研究筆記裡——沒有任何路徑會讓它再次出現（L13：管子只接一頭）。

    判準刻意是**確定性**的，不靠任何人記得標註：
    `entities.extract_entities` 已經把 cashtag 與結構化 source ticker 抽成
    `tickers`，並把能反查 registry 的放進 `company_ids`。**兩者的差集就是候選。**
    這也表示它不會因為研究者換人或那天忘了寫就消失。

    回傳按「被幾筆不同 lead 點名」排序——重複出現是確定性的注意力訊號，
    不是誰的主觀判斷。⚠ 它只回答「誰一直出現卻不在圖裡」，
    **不回答該不該 onboard**：那是使用者的決定，onboarding 會改 registry
    （authority），仍走 `skills/company-onboard`。
    """

    from engine_b.entities import extract_entities

    try:
        from identity.registry import get_registry

        registry = get_registry()
        registered = {
            str(getattr(c, "research_ticker", "") or "").upper()
            for c in registry.companies
        }
        registered |= {
            ticker.split(".", 1)[0]
            for ticker in registered
            if "." in ticker
        }
        registered.discard("")
    except Exception:
        # 讀不到 registry 就不猜：回空集合，而不是把每個 ticker 都報成未登記。
        return []

    seen: dict[str, dict[str, Any]] = {}
    for lead in store["leads"].values():
        if lead.get("status") not in _VETTED_STATUSES:
            continue
        # 研究中以純文字點名的公司。cashtag 抽取刻意是零幻覺的 regex（L6），
        # 代價是抓不到「Largan Precision (3008)」這種寫法——而那正是 2026-08-25
        # 促成本函式的實際案例。辨識公司名是語意任務，依 L15 由研究者解析、
        # 這裡只做 deterministic 的 registry 比對，不做模糊比對也不呼叫 LLM。
        for raw_name in (lead.get("refs") or {}).get("onboard_candidate_names") or ():
            name = str(raw_name).strip()
            if not name:
                continue
            row = seen.setdefault(
                name,
                {
                    "ticker": name,
                    "detected_by": "manual",
                    "lead_count": 0,
                    "lead_ids": [],
                    "sample_title": "",
                },
            )
            row["lead_count"] += 1
            if len(row["lead_ids"]) < 5:
                row["lead_ids"].append(lead["lead_id"])
            if not row["sample_title"]:
                title = " ".join(str(lead.get("title") or "").split())
                row["sample_title"] = title[:120]
        entities = extract_entities(
            title=lead.get("title"),
            raw_text=lead.get("raw_text"),
            source=lead.get("source"),
        )
        # company_ids 是已反查成功的；tickers 裡剩下的就是 registry 不認得的。
        if entities["company_ids"] and len(entities["company_ids"]) >= len(
            entities["tickers"]
        ):
            continue
        for ticker in entities["tickers"]:
            upper = str(ticker).upper()
            if upper in registered:
                continue
            if registry.company_id_for_ticker(upper):
                continue
            row = seen.setdefault(
                upper,
                {
                    "ticker": upper,
                    "detected_by": "cashtag",
                    "lead_count": 0,
                    "lead_ids": [],
                    "sample_title": "",
                },
            )
            row["lead_count"] += 1
            if len(row["lead_ids"]) < 5:
                row["lead_ids"].append(lead["lead_id"])
            if not row["sample_title"]:
                title = " ".join(str(lead.get("title") or "").split())
                row["sample_title"] = title[:120]
    return sorted(
        seen.values(), key=lambda row: (-row["lead_count"], row["ticker"])
    )


def trace_backlog(store: dict[str, Any]) -> list[dict[str, Any]]:
    """列出 parked 的追源未果項目，避免規則書中的 backlog 變成黑洞。

    舊資料若只有 ``parked_reason`` 含 trace，也會列為 ``unstructured``；這讓
    routine 能顯示資料品質缺口，而不是因缺少新欄位就把歷史項目靜默漏掉。
    ``trace_requires_user`` 只表示需要 access／付費／優先權等人工 authority，
    不表示 claim 可信或可入圖。
    """

    from engine_b.entities import lead_entities
    from engine_b import event_watch as ew_mod

    # 等待狀態的單一 authority（[321]）：每筆 backlog 的「還會不會醒」只由這裡回答。
    watch_data = ew_mod.load_watches()
    watch_by_lead: dict[str, dict[str, Any]] = {}
    for watch in watch_data.get("watches", []):
        lead_ref = str(watch.get("wake_lead") or "")
        if not lead_ref or watch.get("status") == "consumed":
            continue
        # 同一 lead 若有多筆（重建過），以最新的為準。
        current = watch_by_lead.get(lead_ref)
        if current is None or str(watch.get("created_at")) >= str(current.get("created_at")):
            watch_by_lead[lead_ref] = watch

    rows: list[dict[str, Any]] = []
    for lead in store["leads"].values():
        if lead.get("status") != "parked":
            continue
        refs = lead.get("refs") or {}
        trace_status = str(refs.get("trace_status") or "").strip()
        parked_reason = str(refs.get("parked_reason") or "").strip()
        if not trace_status and "trace" not in parked_reason.lower():
            continue
        # terminal 值由 config/lead_trace_status.json 決定，不寫死在這裡。
        # 2026-08-25 之前這是硬編碼字串，而 trace_status 本身沒有字彙約束——
        # 寫成未登記的同義詞（`primary_source_obtained`）不會報錯，只會讓已完成的
        # lead 永遠掛在 backlog 且 auto_trigger_reachable=false。字彙一旦有行為
        # 後果就必須被強制（L15：解析可以寬鬆，判定必須 deterministic）。
        if get_trace_status_registry().is_terminal(trace_status):
            continue
        requires_user = str(refs.get("trace_requires_user") or "").lower() in {
            "1", "true", "yes",
        }
        full_title = " ".join(str(lead.get("title") or "").split())
        short_title = full_title[:197] + "..." if len(full_title) > 200 else full_title
        trigger_entities = set(refs.get("trace_trigger_entities") or ())
        if not trigger_entities and refs.get("trace_next_trigger"):
            trigger_entities = lead_entities(lead)

        # [321]：等待狀態的 authority 是 Event Watch registry，不再由本函式推導。
        # 舊 `auto_trigger_reachable` 只答「有沒有標的可比對」，卻被讀成「還會不會醒」——
        # 實測 10 筆標的已全數消化的 lead 一律回 true，安靜沉底（L12）。
        watch = watch_by_lead.get(lead["lead_id"])
        if requires_user:
            wake_state, reason = "pq2_manual", None
        elif watch is None:
            wake_state, reason = "unwatched", (
                "沒有對應的 Event Watch：不會被任何事件喚醒，也沒有到期日會讓它現形。"
                "需建立 watch 或改設 trace_requires_user"
            )
        elif watch.get("status") == "expired":
            wake_state, reason = "expired", (
                f"等待已到期（{watch.get('expires')}）——請決定續等、改主動輪詢或放棄"
            )
        elif ew_mod.is_stalled(watch):
            wake_state, reason = "stalled", (
                f"具名標的已全部觸發過一輪，被動層短期不會再醒；"
                f"由到期日 {watch.get('expires')} 兜底現形"
                + ("，或由主動輪詢提前撈回" if (watch.get("poll") or {}).get("eligible") else "")
            )
        else:
            wake_state, reason = "watching", None

        rows.append({
            "lead_id": lead["lead_id"],
            "title": short_title,
            "url": lead.get("url") or "",
            "trace_status": trace_status or "unstructured",
            "next_trigger": refs.get("trace_next_trigger") or "unspecified",
            "attempts_ref": refs.get("trace_attempts_ref"),
            "requires_user": requires_user,
            "lane": "pq2_manual_authority" if requires_user else "event_or_scheduled_pq1",
            "wake_state": wake_state,
            "wake_state_reason": reason,
            "watch_id": watch.get("watch_id") if watch else None,
            "expires": watch.get("expires") if watch else None,
            "poll_eligible": bool((watch.get("poll") or {}).get("eligible")) if watch else False,
            # 相容欄位：語意收斂為「這筆現在還會不會被喚醒」，不再是「有沒有標的」。
            "auto_trigger_reachable": wake_state in {"pq2_manual", "watching"},
            "unreachable_reason": reason,
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
    preserved_classification = dict(
        (previous or {}).get("classification") or {}
    )
    if not preserved_classification:
        # 2026-08-27 實測：trace requeue 會把 active triage 整包重建，XFAB
        # 原本的 candidate_set／structural_fact 因此只剩在 history，drain 顯示
        # 未分類。分類描述的是 lead 本身，不是這次喚醒事件；重排時應沿用最近
        # 一筆 receipt，不另做語意推論。
        for entry in reversed(lead.get("triage_history") or []):
            candidate = ((entry.get("triage") or {}).get("classification") or {})
            if candidate:
                preserved_classification = dict(candidate)
                break
    lead["status"] = "triaged_go"
    lead["triage"] = {
        "decision": "go",
        "tier": int((previous or {}).get("tier") or 4),
        "reason": cleaned_reason,
        "decided_at": stamp,
        "priority_flags": previous_flags,
    }
    if preserved_classification:
        from engine_b import priority

        lead["triage"]["classification"] = priority.validate_classification(
            preserved_classification,
            require_receipt=True,
        )
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
    classification: Mapping[str, Any] | None = None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    """對 pending lead 下 triage 判斷，轉入 triaged_go／triaged_no_go。

    tier 只是 triage 的初步來源分級記錄，**不是** evidence tier，不影響入圖
    強度（plan R2 不變式）；真正 evidence tier 由 source-trace／lead-intake 決定。

    priority_flags（可選）記 signal-triage 五要素中的 boolean 訊號
    （contradiction／novelty／independent_source／user_requested），供 priority 計分用；不影響
    狀態機、不影響 evidence tier。

    classification 是 PASS 當下的結構化注意力語意。production CLI 對 PASS 強制
    必填；函式層保留 ``None`` 只為讀寫舊資料與低階測試相容，production drain 會
    將缺分類的 active lead 明列 withheld，不再以 unknown 參與排序。
    """
    if not (1 <= int(tier) <= 4):
        raise ValueError("triage tier 必須是 1–4")
    if not (reason or "").strip():
        raise ValueError("triage 必須附 reason（含 no-go 也要記原因）")
    if not go and classification is not None:
        raise ValueError("FILTER／no-go 不應寫 classification")
    lead = _require(store, lead_id)
    target = "triaged_go" if go else "triaged_no_go"
    if target not in ALLOWED_TRANSITIONS[lead["status"]]:
        raise LeadStateError(f"只能對 pending lead triage；現況 {lead['status']}")
    flags = {
        key: bool((priority_flags or {}).get(key))
        for key in _PRIORITY_FLAG_KEYS
        if (priority_flags or {}).get(key)
    }
    stamp = decided_at or _now()
    classification_record: dict[str, Any] | None = None
    if go and classification is not None:
        from engine_b import priority

        classification_record = priority.validate_classification(classification)
        classification_record["classified_by"] = "triage_semantic_v1"
        classification_record["classified_at"] = stamp
        classification_record["reason"] = str(
            classification_record.get("reason") or reason
        ).strip()
        classification_record = priority.validate_classification(
            classification_record,
            require_receipt=True,
        )

    lead["status"] = target
    triage_record: dict[str, Any] = {
        "decision": "go" if go else "no_go",
        "tier": int(tier),
        "reason": reason.strip(),
        "decided_at": stamp,
        "priority_flags": flags,
    }
    if classification_record is not None:
        triage_record["classification"] = classification_record
    lead["triage"] = triage_record
    if go:
        requeued = _requeue_related_trace_backlog(
            store,
            event_lead_id=lead_id,
            event_at=stamp,
        )
        if requeued:
            # receipt 掛在觸發 lead 的 triage 上，讓 routine 能說明本次額外
            # pq1 jobs 從哪個 event 來；它不是 claim／graph authority。
            lead["triage"]["related_trace_requeues"] = requeued
    return lead


# 寫入端仍接受的 trace 觸發類型（`trace_trigger_kind` ref 的合法值）。
# ⚠ 判斷不在這裡：[321] 起等待條件由 Event Watch 判定，`primary_source_signal`
# 在建 watch 時映射到 `entity_filing_signal`（判準本就相同）。這個集合只用來擋
# 寫入端的拼字錯誤，不再有喚醒行為——kind 的行為 SSOT 是 `event_watch.WATCH_KINDS`。
TRACE_TRIGGER_KINDS = frozenset({"related_entity_signal", "primary_source_signal"})

# tier 判準的 SSOT 在 lead_refs（event_watch 也用同一份）。[321] 之前這裡與
# event_watch.py 各有一份字面值，L16 的教科書案例。
_is_primary_source = is_primary_source


def _requeue_related_trace_backlog(
    store: dict[str, Any],
    *,
    event_lead_id: str,
    event_at: str,
) -> list[str]:
    """新 triage PASS lead 以具名標的喚醒相關 trace backlog。

    [321] 起這只是 Event Watch 的**相容轉接層**：真正的等待條件住在
    `library/leads/event_watches.json`，由 `event_watch.check_watches` 判定。
    保留本函式是為了讓 triage 流程的自動化程度不變（PASS 當下就把相關 parked
    lead 排回 pq1），呼叫端不必改。

    舊路徑（掃 parked leads 的 refs 自行比對）只在 registry 尚未涵蓋該 lead 時
    作為 fallback——遷移完成後應為空集合，若持續非空代表有 lead 沒建 watch。
    """

    from engine_b.entities import lead_entities
    from engine_b import event_watch as ew

    event_lead = _require(store, event_lead_id)
    event_entities = lead_entities(event_lead)
    if not event_entities:
        return []

    requeued: list[str] = []
    # --- 主路徑：Event Watch registry ---
    watch_data = ew.load_watches()
    covered: set[str] = {
        str(w.get("wake_lead"))
        for w in watch_data.get("watches", [])
        if w.get("wake_lead")
    }
    if covered:
        fired = ew.check_watches(
            watch_data,
            leads={event_lead_id: event_lead},
        )
        touched = False
        for watch in fired:
            lead_id = watch.get("wake_lead")
            if not lead_id or lead_id not in store["leads"]:
                continue
            candidate = store["leads"][lead_id]
            if candidate.get("status") != "parked":
                ew.reactivate(watch_data, watch["watch_id"])
                touched = True
                continue
            shared = watch.get("woken_by", {}).get("shared_entities") or []
            requeue_trace(
                store,
                lead_id,
                trigger=f"related_triaged_lead:{event_lead_id}",
                reason=(
                    f"Event Watch {watch['watch_id']} 觸發：新 triage PASS lead "
                    f"{event_lead_id} 與等待中的追源共用具名標的 {', '.join(shared)}"
                    "；事件觸發 bounded pq1 重查"
                ),
                requeued_at=event_at,
            )
            # 稽核欄位：哪個事件把它叫醒的、由哪個 watch 判定。消化標記已移進 watch，
            # 但「誰觸發的」仍留在 lead 上——它是這筆 lead 的歷史，不是等待條件。
            candidate.setdefault("refs", {}).update({
                "trace_trigger_event_ref": f"lead:{event_lead_id}",
                "trace_trigger_watch_ref": watch["watch_id"],
            })
            # lead 型 watch 重查未果時等待條件依然成立，回 active 續等；
            # 標的已進 consumed，到期由 expires 收斂。
            ew.reactivate(watch_data, watch["watch_id"])
            touched = True
            requeued.append(lead_id)
        if touched or fired:
            ew.save_watches(watch_data)

    # 沒有 fallback 路徑。[321] 遷移後實測「未被 registry 涵蓋的 backlog」為 0 筆，
    # 留一份平行實作只會讓兩邊再度偏離（L16：重造品會開始偏離，而偏離不報錯）。
    # 未涵蓋的 lead 由 trace_backlog 以 wake_state=unwatched 現形，交人處置。
    return sorted(requeued)


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


CLASSIFICATION_REQUIRED_STATUSES: frozenset[str] = frozenset(
    {"triaged_go", "researching", "action_prepared"}
)


def classification_gaps(store: dict[str, Any]) -> list[dict[str, Any]]:
    """列出 active pq1 lead 的缺漏／非法 classification receipt。

    ``unknown`` 仍是歷史相容 sentinel，但 active queue 不得靠它排序。這個 health
    surface 只讀 tracked leads authority，不讀 Neo4j、Sheet 或 private runtime。
    """

    from engine_b import priority

    rows: list[dict[str, Any]] = []
    for lead_id, lead in store["leads"].items():
        if lead.get("status") not in CLASSIFICATION_REQUIRED_STATUSES:
            continue
        record = priority.classification(lead)
        issue = "missing"
        if record:
            try:
                priority.validate_classification(record, require_receipt=True)
            except priority.ClassificationValidationError as exc:
                issue = str(exc)
            else:
                continue
        title = " ".join(str(lead.get("title") or "").split())
        rows.append({
            "lead_id": lead_id,
            "status": lead.get("status"),
            "source": lead.get("source"),
            "title": title[:200],
            "issue": issue,
        })
    return sorted(rows, key=lambda row: row["lead_id"])
