"""Event Watch 模組——系統裡所有「以後要回來看」的等待條件的統一 registry。

設計依 docs/brainstorms/2026-08-31-event-watch-module-requirements.md：
- 三層檢查成本階梯：T0 被動（新 triage PASS lead 具名標的比對，零 token）、
  T1 日期（sync 比對 until，零 token）、T2 主動輪詢（sweep 給出本輪該查的 K 個，
  由 agent 做 WebSearch；K 可調，調 0 即退回純被動且系統照常運作）。
- 喚醒是簿記：把 pq2 項的 waiting_on 翻回「等你決定」並留 woken_by 稽核，
  **不自動 go、不碰四個 authority gate**。
- 封閉字彙 kind（contract，不是 taxonomy）：`date`／`entity_filing_signal`／
  `fact_verification`／`related_entity_signal`。新增 kind＝承認有一類等待無法被表達，
  不是放寬既有 kind。
- 喚醒目標三選一：`wake_pq2`（翻醒待辦）／`hypothesis_ref`（假設對照）／
  `wake_lead`（把追源線索排回 pq1）。

2026-08-31（[321]）：trace 引擎併入本模組。原設計（brainstorm §動工切法 4）把它排在
最後並註明「那端現況健康，搬遷風險最高、收益最低」——**「現況健康」當時沒有被驗證過**。
實測推翻：50 筆非 terminal backlog 有 14 筆已不可能再被喚醒（10 筆標的全被 consumed-marker
消化、4 筆根本沒有具名標的），而 `auto_trigger_reachable` 對這 14 筆全回 true——它只答
「有沒有標的可比對」，不答「這些標的是不是都用完了」（L12 一個表示兩種語意）。

併入的真正收益不是整齊，是**讓 trace 繼承它缺的那道硬邊界：`expires` 必填**。
14 筆的死因是 consumed-marker（2026-08-12 為防止重複喚醒吃光 pq1 slot 而加的補丁）
沒有到期兜底，用完即靜默沉底。有 expires 之後，喚醒幾次都無所謂——等不到就會到期現形，
追源型轉終局 `watch_expired` 並計數（Phase 1 A3）；需要人決定的等待才進 pq2。consumed-marker 保留（它防的浪費是真的），只是不再是
唯一的終止條件。

同時消掉一組重複實作：`entity_filing_signal` 與 trace 的 `primary_source_signal` 判準
完全相同（tier ≤ 1 ＋ entities 交集），連 `PRIMARY_SOURCE_TIER = 1` 都各寫一份。
遷移時 `primary_source_signal` 一律映射到 `entity_filing_signal`（L16：分類要有單一 SSOT）。
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

WATCHES_PATH = Path("library/leads/event_watches.json")
CONFIG_PATH = Path("config/event_watch.json")

WATCH_KINDS = frozenset({
    "date",
    "entity_filing_signal",
    "fact_verification",
    "related_entity_signal",
    "semantic_condition",
})

#: 語意條件 watch（Phase 1 Step 1.4；G7、C2）：thesis／讀圖寫下的反證或確認條件，**原文逐字**。
#: T0 只做「一手文件、實體有交集、時間在建立之後」的機械比對——醒來＝待檢，**判定在互動 session**
#: （`semantic-queue` → `judge`）；daily 的預篩只標旗、不改狀態。喚醒目標恆為 `disproof_ref`
#: （＝`source_ref`，指回 memo 條目或讀圖）。「一手」與「是誰的文件」讀 lead 的來源宣告
#: （`source_class`／`company_id`／`form_type`，harvest 登記當下寫的），**不看 triage 的 tier 或 go**。
SEMANTIC_KIND = "semantic_condition"
SEMANTIC_MIN_CONDITION_CHARS = 20

# 需要 tier-1 一手來源才觸發的 kind：「等某實體的正式文件」不該被任何一則提到該實體的
# 推文觸發。`related_entity_signal` 刻意不在此列——它等的就是「同一標的有任何新動靜」。
PRIMARY_ONLY_KINDS = frozenset({"entity_filing_signal", "fact_verification"})

# 會做具名標的比對的 kind（T0 被動層）。
ENTITY_MATCH_KINDS = frozenset({
    "entity_filing_signal", "fact_verification", "related_entity_signal",
})

# tier-1 判斷的 SSOT 在 lead_refs（leads 與 event_watch 共用，放低層才不循環 import）。
from engine_b.lead_refs import PRIMARY_SOURCE_TIER, is_primary_source  # noqa: F401


class EventWatchError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> date:
    return datetime.now(timezone.utc).date()


# 一個財報週期（90 天）＋緩衝。最常見的等待模式是「下一份季報會不會揭露」；
# 等滿一輪還沒出現就結案——追源型轉終局 `watch_expired` 並由心跳計數（A3，不佔 pq2、也不無聲續等）。
DEFAULT_TRACE_TTL_DAYS = 120


#: 持股申報（Form 3／4／5、144、SC 13D／13G 及其修正）：語意 watch 一律不比對——EDGAR lead 七成以上是它們，
#: 大公司的 watch 會被數十筆 Form 4 淹沒（2026-09-09 NVDA／TSM 同型事故）。config 缺席時用這份。
DEFAULT_OWNERSHIP_FORMS = ("3", "3/A", "4", "4/A", "5", "5/A", "144", "144/A",
                           "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A")


def load_config() -> dict[str, Any]:
    """T2 力度旋鈕。檔案缺席時 fail-soft 到保守預設（sweep 停用、預篩 0）。"""
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "enabled": False, "sweep_budget_per_run": 0, "min_recheck_days": 3,
            "trace_ttl_days": DEFAULT_TRACE_TTL_DAYS,
            "semantic_screen_daily_limit": 0, "prescreen_text_max_chars": 20000,
            "ownership_forms_excluded": list(DEFAULT_OWNERSHIP_FORMS),
        }
    return {
        "enabled": bool(cfg.get("enabled", True)),
        "sweep_budget_per_run": int(cfg.get("sweep_budget_per_run", 2)),
        "min_recheck_days": int(cfg.get("min_recheck_days", 3)),
        "trace_ttl_days": int(cfg.get("trace_ttl_days", DEFAULT_TRACE_TTL_DAYS)),
        "semantic_screen_daily_limit": int(cfg.get("semantic_screen_daily_limit", 0)),
        "prescreen_text_max_chars": int(cfg.get("prescreen_text_max_chars", 20000)),
        "ownership_forms_excluded": [str(f) for f in cfg.get("ownership_forms_excluded",
                                                             DEFAULT_OWNERSHIP_FORMS)],
    }


def parse_published(raw: Any) -> date | None:
    """lead 的 `published_at` → 日期。**兩種格式**（第 2 輪 N-c）：RSS feed 是 RFC 822
    （`Tue, 30 Jun 2026 23:15:00 +0000`），EDGAR／MOPS 是 ISO 日期。**不得用字串比較**——
    `"Tue, …" > "2026-…"` 恆真，那道檢查會靜默失效。解析不到回 None（呼叫端計數，不猜）。"""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime

        stamp = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    if stamp is None:
        return None
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(timezone.utc)
    return stamp.date()


_CONDITION_DATE = re.compile(
    r"(?P<y>20\d{2})\s*[-/年]\s*(?P<m>\d{1,2})\s*[-/月]\s*(?P<d>\d{1,2})")


def condition_dates(text: str) -> list[date]:
    """條件原文裡寫出的完整日期（`2027-06-30`、`2027/6/30`、`2027 年 6 月 30 日`）——到期不得早於它們。"""
    out: list[date] = []
    for match in _CONDITION_DATE.finditer(str(text or "")):
        try:
            out.append(date(int(match["y"]), int(match["m"]), int(match["d"])))
        except ValueError:
            continue
    return out


def ensure_trace_watch(
    lead_id: str,
    *,
    kind: str,
    entities: Iterable[str],
    query_hint: str = "",
    note: str = "",
    consumed_entities: Iterable[str] = (),
    created_at: str | None = None,
    today: date | None = None,
) -> dict[str, Any] | None:
    """替一筆剛 park 的追源線索建立等待條件（沒有就建，有就沿用）。

    這是 [321] 的**入口端**：遷移只處理了既有 backlog，新 park 的若不建 watch，
    就會立刻變回沒有到期日、沒人管的等待——L13「管子只接了一頭」。
    """
    entities = sorted({str(e).strip() for e in entities if str(e).strip()})
    if not entities:
        return None  # 沒有具名標的就沒有觸發條件，不假裝在等（由 wake_state=unwatched 現形）
    data = load_watches()
    for watch in data.get("watches", []):
        # 只沿用還在等的（active／fired）。到期的那一筆代表**上一輪**等待——lead 研究完再 park 是新的一輪，
        # 沿用它會變成沒有到期的等待且不被任何計數器數到（R2-b NB-1）。
        if watch.get("wake_lead") == lead_id and watch.get("status") in ("active", "fired"):
            return watch
    today = today or _today()
    ttl = load_config()["trace_ttl_days"]
    watch = add_watch(
        data,
        kind="entity_filing_signal" if kind == "primary_source_signal" else kind,
        wake_lead=lead_id,
        expires=(today + timedelta(days=ttl)).isoformat(),
        entities=entities,
        consumed_entities=consumed_entities,
        poll_query_hint=query_hint[:200],
        note=note,
        # 等待從「這條線索被 park」那一刻起算，不是從 registry 寫入那一刻。
        # T0 比對用 `created_at` 判斷「這則 lead 是不是等待開始後才出現的」，
        # 用寫入時間會讓 park 當下已在佇列中的新 lead 被誤判成舊事件。
        created_at=created_at,
    )
    save_watches(data)
    return watch


def load_watches(path: Path | None = None) -> dict[str, Any]:
    # 路徑在呼叫時解析而非用預設參數綁定——預設參數在 import 時就固定了，
    # 測試無法用 monkeypatch 導向暫存檔（見 tests/conftest.py 的自動隔離）。
    path = Path(path) if path else WATCHES_PATH
    if not path.exists():
        return {"schema_version": 1, "watches": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("watches", [])
    return data


def save_watches(data: Mapping[str, Any], path: Path | None = None) -> None:
    path = Path(path) if path else WATCHES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def add_watch(
    data: dict[str, Any],
    *,
    kind: str,
    wake_pq2: int | None = None,
    expires: str,
    until: str | None = None,
    entities: Iterable[str] = (),
    fact: str = "",
    fact_check_ref: str = "",
    poll_eligible: bool = False,
    poll_query_hint: str = "",
    hypothesis_ref: str = "",
    wake_lead: str = "",
    consumed_entities: Iterable[str] = (),
    note: str = "",
    created_at: str | None = None,
    disproof_ref: str = "",
    wake_reading: str = "",
    condition: str = "",
    source_ref: str = "",
    quote_locator: str = "",
    check_frequency: str = "",
    action_48h: str = "",
    node: str = "",
    today: date | None = None,
) -> dict[str, Any]:
    if kind not in WATCH_KINDS:
        raise EventWatchError(f"未知 watch kind：{kind}（封閉字彙 {sorted(WATCH_KINDS)}）")
    if kind == "date" and not until:
        raise EventWatchError("kind=date 必須帶 until")
    if kind in ENTITY_MATCH_KINDS and not list(entities):
        raise EventWatchError(f"kind={kind} 必須帶 entities")
    if kind == "fact_verification" and not fact:
        raise EventWatchError("kind=fact_verification 必須帶 fact")
    if not expires:
        raise EventWatchError("expires 必填——無限期等待會腐爛成事實（brainstorm 硬邊界）")
    # 喚醒目標恰好擇一（[321] 由二選一擴充；Phase 1 Step 1.4 加 disproof_ref）：pq2 編號（翻醒 waiting 項）、
    # 假設 id（fact-check 到點）、lead id（追源線索排回 pq1）、或反證來源（語意條件，指回 memo／讀圖）。
    # Phase 1 Step 1.5 再加 wake_reading（讀圖節點：需求側客戶出了新一手文件 → 該節點列進 needs_reread）。
    targets = [bool(wake_pq2), bool(hypothesis_ref), bool(wake_lead), bool(disproof_ref), bool(wake_reading)]
    if sum(targets) != 1:
        raise EventWatchError("wake_pq2／hypothesis_ref／wake_lead／disproof_ref／wake_reading 必須恰好擇一")
    if wake_reading and kind != "entity_filing_signal":
        raise EventWatchError("wake_reading 只用在 entity_filing_signal（等需求側客戶的一手文件）")
    if (kind == SEMANTIC_KIND) != bool(disproof_ref):
        raise EventWatchError("semantic_condition 的喚醒目標必須是 disproof_ref，其他 kind 不得用它")
    if kind == SEMANTIC_KIND:
        _validate_semantic(condition=condition, entities=list(entities), source_ref=source_ref,
                           disproof_ref=disproof_ref, check_frequency=check_frequency,
                           action_48h=action_48h, expires=expires, today=today or _today())
    watch = {
        "watch_id": f"ew_{len(data['watches']) + 1:04d}_{_today().isoformat()}",
        "created_at": created_at or _now(),
        "expires": expires,
        "kind": kind,
        "until": until,
        "entities": sorted({str(e).strip() for e in entities if str(e).strip()}),
        "fact": fact,
        "fact_check_ref": fact_check_ref,
        "wake_pq2": int(wake_pq2) if wake_pq2 else None,
        "hypothesis_ref": hypothesis_ref,
        "wake_lead": wake_lead,
        # 同一標的觸發過就不再重複（防 2026-08-12 的「5 個 pq1 slot 被同批重排吃光」）。
        # 它不再是終止條件——expires 才是；標的用完只代表暫時停滯，到期仍會現形。
        "consumed_entities": sorted(
            {str(e).strip().upper() for e in consumed_entities if str(e).strip()}
        ),
        "poll": {
            "eligible": bool(poll_eligible),
            "last_checked": None,
            "query_hint": poll_query_hint,
        },
        "note": note,
        "status": "active",
        "woken_by": None,
    }
    if wake_reading:
        watch["wake_reading"] = wake_reading
    if kind == SEMANTIC_KIND:
        watch.update({
            "disproof_ref": disproof_ref,
            "condition": condition,
            "source_ref": source_ref,
            "quote_locator": quote_locator,
            "check_frequency": check_frequency,
            "action_48h": action_48h,
            "node": node or None,
        })
    data["watches"].append(watch)
    return watch


def _validate_semantic(*, condition: str, entities: list[str], source_ref: str, disproof_ref: str,
                       check_frequency: str, action_48h: str, expires: str, today: date) -> None:
    """L7 三件套、實體（INV-1）、到期不早於條件自己寫的日期——缺一拒收。"""
    if len(str(condition or "").strip()) < SEMANTIC_MIN_CONDITION_CHARS:
        raise EventWatchError(f"condition 必須是原文逐字、至少 {SEMANTIC_MIN_CONDITION_CHARS} 字")
    if not str(check_frequency or "").strip() or not str(action_48h or "").strip():
        raise EventWatchError("L7 三件套缺件：check_frequency 與 action_48h 都必填")
    if not (source_ref.startswith("thesis:") or source_ref.startswith("reading:")) or "#" not in source_ref:
        raise EventWatchError("source_ref 必須是 thesis:<memo 路徑>#<n> 或 reading:<reading_id>#<n>")
    if disproof_ref != source_ref:
        raise EventWatchError("disproof_ref 必須等於 source_ref（喚醒時指回原文）")
    companies = [e for e in entities if str(e).startswith("co:")]
    if not companies:
        raise EventWatchError("entities 至少要有一個 co:*——feed 的 lead 只帶 co:*，只寫 ticker 永遠叫不醒（第 2 輪 N-b）")
    from identity.registry import get_registry

    registry = get_registry()
    unknown = [c for c in companies if not registry.has_company(c)]
    if unknown:
        raise EventWatchError(f"entities 有 registry 解析不到的 co:*（INV-1，不憑名字猜）：{unknown}")
    try:
        until = date.fromisoformat(str(expires))
    except ValueError as exc:
        raise EventWatchError(f"expires 不是 ISO 日期：{expires}") from exc
    if until <= today:
        raise EventWatchError("expires 必須晚於建立日")
    written = condition_dates(condition)
    if written and until < max(written):
        raise EventWatchError(f"expires {until} 早於條件自己寫的日期 {max(written)}——不得早於核查點或催化劑")


def _lead_stamp(lead: Mapping[str, Any]) -> str:
    triage = lead.get("triage") or {}
    return str(triage.get("decided_at") or lead.get("first_seen") or "")


def _is_primary(lead: Mapping[str, Any]) -> bool:
    try:
        return int((lead.get("triage") or {}).get("tier")) <= PRIMARY_SOURCE_TIER
    except (TypeError, ValueError):
        return False


def check_watches(
    data: dict[str, Any],
    *,
    leads: Mapping[str, Any] | None = None,
    today: date | None = None,
    stats: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """跑 T0＋T1 檢查，回傳觸發清單（呼叫端負責喚醒 pq2 與存檔）。

    T1：until <= 今天 → 觸發（kind=date）。
    T0：kind=entity_filing_signal／fact_verification 的 watch，若有 watch 建立後
        新 triage PASS 且 tier-1 的 lead 與 entities 有交集 → 觸發。
    到期（expires < 今天）的 watch 標 `expired`，不觸發——過期歸檔留稽核。
    """

    today = today or _today()
    fired: list[dict[str, Any]] = []
    mark_expired(data, today=today)
    for watch in data["watches"]:
        if watch.get("status") != "active":
            continue
        kind = watch["kind"]
        if kind == "date":
            try:
                due = date.fromisoformat(str(watch.get("until")))
            except (TypeError, ValueError):
                continue
            if due <= today:
                watch["status"] = "fired"
                watch["woken_by"] = {"kind": "date", "at": _now()}
                fired.append(dict(watch))
        elif kind == SEMANTIC_KIND and leads:
            hit = _semantic_matches(watch, leads, stats=stats)
            if not hit:
                continue
            lead_id, shared = hit[0]
            watch["status"] = "fired"
            watch["woken_by"] = {"kind": kind, "lead_id": lead_id, "shared_entities": shared,
                                 "at": _now(), "disproof_ref": watch.get("disproof_ref")}
            watch["consumed_leads"] = sorted(set(watch.get("consumed_leads") or ()) | {lid for lid, _ in hit})
            fired.append(dict(watch))
        elif kind in ENTITY_MATCH_KINDS and leads:
            targets = set(watch.get("entities") or ())
            created = str(watch.get("created_at") or "")
            consumed = set(watch.get("consumed_entities") or ())
            consumed_leads = set(watch.get("consumed_leads") or ())
            from engine_b.entities import lead_entities

            # 先把**這一刻**所有會命中的 lead 收齊，再決定叫醒一次。
            # 叫醒只用第一則（woken_by），但全部命中的 lead 都進 consumed_leads：
            # 它們對這個 watch 而言都是「已經發生」的事件，被 consumer 回 active 之後
            # 不該再被其中任何一則逐輪叫醒。2026-09-09 實測：NVDA／TSM 的 entity_filing
            # watch 各有數十則歷史 Form 4 命中，逐則消化要跑數十輪 sync 才會收斂。
            matches: list[tuple[str, list[str]]] = []
            for lead_id, lead in leads.items():
                if (lead.get("triage") or {}).get("decision") != "go":
                    continue
                # 同一則 lead 只能把同一個 watch 叫醒一次。fired watch 被 consumer 回 active
                # 之後（2026-09-09 起 lead 型會這樣做），沒有這條它會被同一則 lead 每輪再叫醒
                # 一次——對 PRIMARY_ONLY kind 尤其如此，因為那類刻意不用 entity 消化標記
                # （下一季的 10-Q 是新事件，但**同一份** 10-Q 不是）。
                if lead_id in consumed_leads:
                    continue
                # 追源重排不是事件：requeue_trace 會把 triage receipt 整包重寫成今天，
                # 於是這則舊 lead 看起來像剛 PASS 的新 lead。2026-09-09 實測：35 筆重排後
                # 下一次 sync 又叫醒 21 個 watch，其中 7 個的觸發者就是重排回來的同一批。
                if _is_trace_requeue(lead):
                    continue
                # `related_entity_signal` 等的是「同一標的有任何新動靜」，不限一手；
                # 其餘 kind 等的是正式文件，不該被任何一則提及觸發。
                if kind in PRIMARY_ONLY_KINDS and not is_primary_source(lead):
                    continue
                if _lead_stamp(lead) <= created:
                    continue
                shared = sorted(targets & lead_entities(lead))
                if not shared:
                    continue
                # consumed-marker 只套用在 related_entity_signal：同一檔的第二則轉述
                # 不會帶來新事證。一手來源相反——下一季的 10-Q 本身就是新事件，
                # 故不以標的消化（沿用 leads._requeue_related_trace_backlog 的原判準）。
                if kind == "related_entity_signal":
                    novel = [s for s in shared if s.strip().upper() not in consumed]
                    if not novel:
                        continue
                    shared = novel
                matches.append((lead_id, shared))
            if not matches:
                continue
            lead_id, shared = matches[0]
            watch["status"] = "fired"
            woken: dict[str, Any] = {
                "kind": kind,
                "lead_id": lead_id,
                "shared_entities": shared,
                "at": _now(),
            }
            # fact_verification 喚醒必帶對照欄位——醒來的人（agent）要直接
            # 拿 fact 去對觸發 lead 的一手數字，不必回頭翻 watch（L16：
            # 分類跟著資料走到消費端）。
            if kind == "fact_verification":
                woken["fact"] = watch.get("fact")
                woken["fact_check_ref"] = watch.get("fact_check_ref")
            if watch.get("hypothesis_ref"):
                woken["hypothesis_ref"] = watch["hypothesis_ref"]
            if watch.get("wake_lead"):
                woken["wake_lead"] = watch["wake_lead"]
                watch["consumed_entities"] = sorted(
                    consumed | {s.strip().upper() for _lid, sh in matches for s in sh}
                )
            watch["consumed_leads"] = sorted(consumed_leads | {lid for lid, _sh in matches})
            watch["woken_by"] = woken
            fired.append(dict(watch))
    return fired


#: 到期處置的封閉字彙（R2-b NB-6；L16：字彙有行為後果就必須被強制）——每一筆 expired 都落在其中一格。
#: 續等不在這裡：續等讓 watch 回 active、處置清空，歷史在 `renewals`。
EXPIRY_RESOLUTION_KINDS: dict[str, str] = {
    "requeued_to_pq2": "pq2 型：指向的未結案編號翻回球在你",
    "pq2_item_gone": "pq2 型：指向的編號已結案，無事可做",
    "trace_closed": "追源型：lead 轉終局 watch_expired",
    "lead_already_terminal": "追源型：lead 的 trace_status 早已是終局，不覆寫",
    "lead_in_flight": "追源型：lead 已在路上（之後再 park 會建新的等待）",
    "lead_closed": "追源型：lead 已 applied／no-go",
    "lead_missing": "追源型：lead 不存在",
    "superseded_by_newer_watch": "追源型：同一 lead 已有較新的等待",
    "reading_expiry": "讀圖型：由讀圖自己的到期重問",
    "source_superseded": "語意型：來源 memo／讀圖已不是現行",
    "dropped": "使用者 drop（watch_decision）",
    "touched": "使用者 go：研究結論＝條件已被觸及（watch_decision）",
}


def mark_expired(data: dict[str, Any], *, today: date | None = None, only: str | None = None) -> list[str]:
    """`expires < 今天` 的 active watch → `expired`，記 `expired_at`（Phase 1 Step 1.7）。回傳這一次轉到期的 id。

    到期不是丟（INV-2）：需要人決定的（語意型、假設型）由 `todo sync` 鑄 `watch_decision`；pq2 型把它指向的
    編號翻回「球在你」；追源型把 lead 轉終局 `watch_expired` 並計數；讀圖型由讀圖自己的到期重問。"""
    today = today or _today()
    out: list[str] = []
    for watch in data["watches"]:
        if only is not None and watch.get("watch_id") != only:
            continue
        if watch.get("status") == "active" and past_expiry(watch, today=today):
            watch["status"] = "expired"
            watch["expired_at"] = _now()
            out.append(str(watch["watch_id"]))
    return out


def past_expiry(watch: Mapping[str, Any], *, today: date | None = None) -> bool:
    """`expires < 今天`（日期壞掉的不算——那是資料錯，由 audit 現形，不在這裡猜）。"""
    try:
        return date.fromisoformat(str(watch["expires"])) < (today or _today())
    except (KeyError, ValueError):
        return False


def expiry_class(watch: Mapping[str, Any]) -> str:
    """到期要怎麼處置（Phase 1 Step 1.7；到期成批的設計 B，使用者 2026-09-24）：

    - `pq2`：它指向的編號翻回球在你｜`trace`：lead 轉終局並計數｜`reading`（`wake_reading`）：只記處置
    - `thesis_review`：thesis 來源的語意條件——**不鑄號**，列進那份 thesis 的複查項目，複查（go／drop）時續盯
    - `reread`：讀圖來源的語意條件——**不鑄號**，列進該節點的重讀理由，重讀時收掉換新
    - `decision`：其餘（假設型等**沒有自己複查週期**的等待）→ pq2 `watch_decision`
    """
    if watch.get("wake_pq2"):
        return "pq2"
    if watch.get("wake_lead"):
        return "trace"
    if watch.get("wake_reading"):
        return "reading"
    if watch.get("kind") == SEMANTIC_KIND:
        ref = str(watch.get("source_ref") or "")
        if ref.startswith("thesis:"):
            return "thesis_review"
        if ref.startswith("reading:"):
            return "reread"
    return "decision"


def condition_label(text: Any, limit: int = 40) -> str:
    """給人讀的條件短句（NB2-9）：去掉 markdown 粗體、開頭的【…】標記、「…」省略前的逐字前導、
    「圖外三條要人看：」這類接在編號前的導語——標題要讓人不展開就知道主詞。"""
    import re

    s = " ".join(str(text or "").replace("**", "").split())
    s = re.sub(r"^【[^】]*】", "", s)
    if "…" in s:
        s = s.rsplit("…", 1)[1]
    s = re.sub(r"^[^：]{0,40}：(?=[①-⑳])", "", s)
    s = s.strip("：:；; ")
    return s if len(s) <= limit else s[:limit] + "…"


def renew(data: dict[str, Any], watch_id: str, *, until: str, n: int | None = None) -> dict[str, Any]:
    """續等（`watch_decision` 的 `pending --until`）：以新到期日回 `active`，歷史附加、不覆寫（Phase 1 Step 1.7）。

    等待只住 registry——續等不在 pq2 掛 `waiting_on`。"""
    until_day = date.fromisoformat(str(until))
    if until_day <= _today():
        raise EventWatchError(f"續等的新到期日必須晚於今天：{until}")
    for watch in data["watches"]:
        if watch["watch_id"] != watch_id:
            continue
        if watch.get("status") != "expired":
            raise EventWatchError(f"只能續等已到期的 watch：{watch_id}（現況 {watch.get('status')}）")
        watch["renewals"] = [*(watch.get("renewals") or []),
                             {"at": _now(), "previous_expires": watch["expires"],
                              "expired_at": watch.get("expired_at"), "until": until_day.isoformat(), "n": n}]
        watch["expires"] = until_day.isoformat()
        watch["status"] = "active"
        watch.pop("expired_at", None)
        watch.pop("expiry_resolution", None)
        return watch
    raise EventWatchError(f"watch 不存在：{watch_id}")


def resolve_expiry(data: dict[str, Any], watch_id: str, resolution: Mapping[str, Any]) -> dict[str, Any]:
    """到期處置的收據（`expiry_resolution`）。只能寫在 expired 的 watch 上，寫過就不改；`kind` 必須在封閉字彙裡。"""
    kind = str(resolution.get("kind") or "")
    if kind not in EXPIRY_RESOLUTION_KINDS:
        raise EventWatchError(f"未知的到期處置 kind：{kind!r}（封閉字彙 {sorted(EXPIRY_RESOLUTION_KINDS)}）")
    for watch in data["watches"]:
        if watch["watch_id"] != watch_id:
            continue
        if watch.get("status") != "expired":
            raise EventWatchError(f"{watch_id} 不是 expired（現況 {watch.get('status')}）")
        if watch.get("expiry_resolution"):
            return watch
        watch["expiry_resolution"] = {**dict(resolution), "at": _now()}
        return watch
    raise EventWatchError(f"watch 不存在：{watch_id}")


def record_touched(data: dict[str, Any], watch_id: str, *, quote: str, note: str, n: int,
                   receipt: str) -> dict[str, Any]:
    """`watch_decision` 的 go＝研究結論「條件已被觸及」（R2-b B2）——與 `judge(touches=True)` 同形，接手路徑才接得到。

    - 語意型：寫 `judgment`（`touches=yes`、`quote`、`handled=None`、`via=watch_decision:<n>`）→ thesis 來源由
      `thesis_lifecycle` 那一筆接住（`touched_disproof_by_thesis`）、讀圖來源列進 needs_reread（`reread_reasons`）。
    - 假設型：記 `woken_by`（`kind=watch_decision`）並**停在 fired** → 假設對照（`hypotheses verify` → consume）與
      個股頁的 `disproof_signal` 照原本的路接手（NB2-2）。
    語意型轉 `consumed`（同 judge）。兩者都記 `expiry_resolution: touched`。不改任何 authority。"""
    if not str(quote or "").strip():
        raise EventWatchError("條件已被觸及必須附原文（quote；L18）")
    watch = next((w for w in data["watches"] if w.get("watch_id") == watch_id), None)
    if watch is None:
        raise EventWatchError(f"watch 不存在：{watch_id}")
    resolve_expiry(data, watch_id, {"kind": "touched", "n": n, "receipt": receipt, "reason": note or None})
    stamp = _now()
    via = f"watch_decision:{n}"
    judgment = {"at": stamp, "touches": "yes", "note": note or "watch_decision 研究結論：條件已被觸及",
                "quote": quote, "handled": None, "via": via, "evidence": receipt, "lead_id": None}
    if watch.get("kind") != SEMANTIC_KIND:
        # 假設型：停在 fired、記 woken_by——走回原本的路（`hypotheses verify` 對照後 `event_watch consume`；
        # oa_* 由個股頁 disproof_signal 標 review_required）。直接 consumed 會繞過假設層（R2-b 重審 NB2-2）。
        watch["woken_by"] = {"kind": "watch_decision", "at": stamp, "n": n, "evidence": receipt, "quote": quote,
                             "note": note or None}
        watch["status"] = "fired"
        return watch
    watch["judgment"] = judgment
    watch["status"] = "consumed"
    return watch


def _semantic_matches(watch: Mapping[str, Any], leads: Mapping[str, Any], *,
                      stats: dict[str, int] | None = None) -> list[tuple[str, list[str]]]:
    """語意 watch 的 T0：①來源宣告 primary（**不看 triage**）②不是持股申報 ③實體有交集
    ④`first_seen` 晚於 watch 建立、且 `published_at`（有值時）不早於建立日——EDGAR `lookback_count`
    回補與新 feed 首跑會把舊文件以今天的 `first_seen` 登記 ⑤不在 consumed_leads、不是追源重排。
    `published_at` 解析不到就只用 `first_seen` 並計數 `published_at_unparsed`（INV-3）。"""
    from engine_b.entities import lead_entities

    excluded = {str(f).strip().upper() for f in load_config()["ownership_forms_excluded"]}
    targets = set(watch.get("entities") or ())
    created = str(watch.get("created_at") or "")
    try:
        created_day = date.fromisoformat(created[:10])
    except ValueError:
        created_day = None
    consumed = set(watch.get("consumed_leads") or ())
    out: list[tuple[str, list[str]]] = []
    for lead_id, lead in leads.items():
        if lead_id in consumed or _is_trace_requeue(lead):
            continue
        if lead.get("source_class") != "primary":
            continue
        if str(lead.get("form_type") or "").strip().upper() in excluded:
            continue
        if str(lead.get("first_seen") or "") <= created:
            continue
        raw_published = lead.get("published_at")
        published = parse_published(raw_published)
        if raw_published and published is None and stats is not None:
            stats["published_at_unparsed"] = stats.get("published_at_unparsed", 0) + 1
        if published is not None and created_day is not None and published < created_day:
            continue
        shared = sorted(targets & lead_entities(lead))
        if shared:
            out.append((lead_id, shared))
    return out


def _is_trace_requeue(lead: Mapping[str, Any]) -> bool:
    """這則 lead 目前的 triage receipt 是不是由追源重排寫的（而非原始 PASS）。

    `requeue_trace` 把 `triage.decided_at` 與 `refs.trace_requeued_at` 寫成同一個 stamp；
    兩者相等＝這一輪是重排。原始 PASS 的 decided_at 早於任何 requeue，不會相等。
    """
    refs = lead.get("refs") or {}
    stamp = str(refs.get("trace_requeued_at") or "")
    return bool(stamp) and stamp == str((lead.get("triage") or {}).get("decided_at") or "")


def sweep_due(data: Mapping[str, Any], *, today: date | None = None) -> list[dict[str, Any]]:
    """T2：回傳本輪該主動查的 watch（最多 sweep_budget_per_run 個）。

    只回清單不做查詢——WebSearch 是 agent 的工作；budget=0 或 enabled=false 時
    回空清單，系統退回 T0＋T1 純被動（退化路徑）。
    """

    cfg = load_config()
    if not cfg["enabled"] or cfg["sweep_budget_per_run"] <= 0:
        return []
    today = today or _today()
    candidates = []
    for watch in data["watches"]:
        if watch.get("status") != "active" or not (watch.get("poll") or {}).get("eligible"):
            continue
        last = (watch.get("poll") or {}).get("last_checked")
        if last:
            try:
                days = (today - date.fromisoformat(str(last)[:10])).days
                if days < cfg["min_recheck_days"]:
                    continue
            except ValueError:
                pass
        waited = 0
        try:
            waited = (today - date.fromisoformat(str(watch["created_at"])[:10])).days
        except ValueError:
            pass
        candidates.append((waited, watch))
    candidates.sort(key=lambda pair: -pair[0])
    return [dict(w) for _, w in candidates[: cfg["sweep_budget_per_run"]]]


def mark_checked(data: dict[str, Any], watch_id: str, *, today: date | None = None) -> None:
    today = today or _today()
    for watch in data["watches"]:
        if watch["watch_id"] == watch_id:
            watch.setdefault("poll", {})["last_checked"] = today.isoformat()
            return
    raise EventWatchError(f"watch 不存在：{watch_id}")


def is_stalled(watch: Mapping[str, Any]) -> bool:
    """標的全被消化，短期內不會再被動觸發——但**沒有死**，到期仍會現形。

    [321] 之前這個狀態沒有名字：`auto_trigger_reachable` 只答「有沒有標的可比對」，
    對 10 筆標的已全數消化的 lead 一律回 true，於是它們安靜沉底、無人知道
    （L12：一個表示承載兩種語意，下游被迫二選一而兩邊都錯）。
    現在它有名字、有計數器，且有 `expires` 兜底——停滯不等於死亡。
    """
    if watch.get("kind") != "related_entity_signal":
        return False
    entities = {str(e).strip().upper() for e in (watch.get("entities") or ())}
    if not entities:
        return True
    consumed = {str(e).strip().upper() for e in (watch.get("consumed_entities") or ())}
    return not (entities - consumed)


def counters(data: Mapping[str, Any], *, coverage: frozenset[str] | None = None) -> dict[str, int | None]:
    """常駐計數器（L14：防呆要自己出現）。

    `coverage`（Phase 1 Step 1.4）：有一手來源會產出 lead 的實體集合（`primary_coverage()`）。
    沒給就不算 `semantic_unreachable`，回 None——「沒算」不是 0（INV-3）。"""

    active = [w for w in data["watches"] if w.get("status") == "active"]
    semantic = [w for w in data["watches"] if w.get("kind") == SEMANTIC_KIND]
    watching = [w for w in semantic if w.get("status") in ("active", "fired")]
    pending = [w for w in semantic if w.get("status") == "fired"]
    extra: dict[str, int | None] = {
        "semantic_active": sum(1 for w in semantic if w.get("status") == "active"),
        # 醒了、還沒判定＝待檢（有沒有預篩標旗都算；預篩只標旗、不減少未檢）
        "semantic_pending_check": len(pending),
        "semantic_flagged": sum(1 for w in pending if flag_for_current(w) is not None),
        "wake_disproof": sum(1 for w in active if w.get("disproof_ref")),
        "wake_reading": sum(1 for w in active if w.get("wake_reading")),
        "semantic_unreachable": (None if coverage is None else
                                 sum(1 for w in watching if not is_reachable(w, coverage))),
        **expiry_counters(data),
    }
    return {**_base_counters(data, active), **extra}


def expiry_counters(data: Mapping[str, Any], *, today: date | None = None) -> dict[str, int]:
    """到期處置的計數（Phase 1 Step 1.7）：到期不是丟——每一筆 expired 都要落在某個處置裡，沒落的現形。

    - `expiry_decision_pending`：假設型等沒有自己複查週期的到期、還沒處置（＝待決 `watch_decision`）
    - `expiry_thesis_review_pending`／`expiry_reread_pending`：thesis／讀圖來源的條件到期、等複查／重讀（設計 B）
    - `trace_expired_closed`／`_today`：追源型到期、lead 轉終局 `watch_expired`（重問＝計數現形，不佔 pq2）
    - `expiry_unresolved`：任何型別 expired 且沒有 `expiry_resolution`（含 A3 之前的歷史到期）"""
    today_iso = (today or _today()).isoformat()
    expired = [w for w in data["watches"] if w.get("status") == "expired"]
    closed = [w for w in expired if (w.get("expiry_resolution") or {}).get("kind") == "trace_closed"]
    unresolved = [w for w in expired if not w.get("expiry_resolution")]
    return {
        "expiry_decision_pending": sum(1 for w in unresolved if expiry_class(w) == "decision"),
        "expiry_thesis_review_pending": sum(1 for w in unresolved if expiry_class(w) == "thesis_review"),
        "expiry_reread_pending": sum(1 for w in unresolved if expiry_class(w) == "reread"),
        "trace_expired_closed": len(closed),
        "trace_expired_closed_today": sum(1 for w in closed
                                          if str(w["expiry_resolution"].get("at") or "")[:10] == today_iso),
        "expiry_unresolved": sum(1 for w in expired if not w.get("expiry_resolution")),
    }


def _base_counters(data: Mapping[str, Any], active: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "active": len(active),
        "t1_date": sum(1 for w in active if w["kind"] == "date"),
        "t0_passive": sum(1 for w in active if w["kind"] in ENTITY_MATCH_KINDS),
        "t2_pollable": sum(1 for w in active if (w.get("poll") or {}).get("eligible")),
        # 喚醒目標分佈：使用者的「在等什麼」有三種去處，混在一起看不出比例。
        "wake_pq2": sum(1 for w in active if w.get("wake_pq2")),
        "wake_lead": sum(1 for w in active if w.get("wake_lead")),
        "wake_hypothesis": sum(1 for w in active if w.get("hypothesis_ref")),
        # 停滯＝被動層短期不會再觸發，只剩 expires 與 T2 輪詢能救它。
        # 這個數字若持續攀升，代表被動喚醒的涵蓋率不足，不是「大家都在等」。
        "stalled": sum(1 for w in active if is_stalled(w)),
        "fired_unconsumed": sum(1 for w in data["watches"] if w.get("status") == "fired"),
        "expired": sum(1 for w in data["watches"] if w.get("status") == "expired"),
    }


def consume_fired(data: dict[str, Any], watch_id: str) -> None:
    """喚醒動作完成後把 fired 收掉（稽核保留）。"""

    for watch in data["watches"]:
        if watch["watch_id"] == watch_id and watch.get("status") == "fired":
            watch["status"] = "consumed"
            return
    raise EventWatchError(f"沒有待消化的 fired watch：{watch_id}")


def reactivate(data: dict[str, Any], watch_id: str, *, note: str | None = None) -> None:
    """fired watch 對照後判定「與等待條件無關」→ 回 active 繼續等，不是 consume。

    與 `consume_fired` 的差別：`consume` 說的是「這個等待結束了」；`reactivate` 說的是
    「觸發它的那則 lead 不是它在等的東西，等待條件依然成立」。兩者都把觸發 lead 留在
    `consumed_leads` 裡（fire 時就寫好了），所以同一則不會再叫醒第二次；到期仍由
    expires 收斂。

    ⚠ 兩個用途都真實存在：①lead 型 watch 排回 pq1 後回到等待——同一份文件可能要等
    好幾輪才出現；②假說型（`fact_verification`）被**無關的** tier-1 lead 以 entity
    交集誤觸——2026-09-09 實測 ew_0005／0007／0057 三個都是（COHR 8-K 是 RSU、
    AAOI 8-K 是租賃）。當時沒有這個命令，只能直接改 JSON。

    `note` 進 `reactivations`（append，不覆蓋 `note` 那格建 watch 時寫的原始理由）——
    「為什麼判定無關」是稽核要看的東西，不得只活在某個 session 的 transcript 裡。
    """
    for watch in data["watches"]:
        if watch["watch_id"] == watch_id and watch.get("status") == "fired":
            watch["status"] = "active"
            entry: dict[str, Any] = {"at": _now(), "woken_by": watch.get("woken_by")}
            if note:
                entry["note"] = note
            watch["reactivations"] = [*(watch.get("reactivations") or []), entry]
            watch["woken_by"] = None
            return
    raise EventWatchError(f"沒有待消化的 fired watch：{watch_id}")


def flag_for_current(watch: Mapping[str, Any]) -> dict[str, Any] | None:
    """預篩標旗——只算**這一次叫醒它的那則 lead** 的標旗（reactivate 後被別則叫醒要重新標）。"""
    flag = watch.get("semantic_flag")
    woken = watch.get("woken_by") or {}
    if isinstance(flag, dict) and flag.get("lead_id") and flag.get("lead_id") == woken.get("lead_id"):
        return flag
    return None


#: 預篩 verdict 的封閉字彙（`crons/prescreen_schema.json` 的 enum 由測試斷言等於它）。
PRESCREEN_VERDICTS = ("likely_touches", "likely_unrelated", "cannot_tell")


def flag(data: dict[str, Any], watch_id: str, *, lead_id: str, verdict: str,
         quote: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    """預篩標旗（C7；只由 ⑩c `prescreen-apply` 呼叫）：**只寫 `semantic_flag`，不改狀態**（G7：只標旗不判定）。"""
    if verdict not in PRESCREEN_VERDICTS:
        raise EventWatchError(f"verdict 必須是 {PRESCREEN_VERDICTS} 之一：{verdict!r}")
    for watch in data["watches"]:
        if watch["watch_id"] != watch_id:
            continue
        if watch.get("kind") != SEMANTIC_KIND or watch.get("status") != "fired":
            raise EventWatchError(f"只能對 fired 的語意 watch 標旗：{watch_id}")
        if (watch.get("woken_by") or {}).get("lead_id") != lead_id:
            raise EventWatchError(f"{watch_id} 不是被 {lead_id} 叫醒的")
        if verdict == "likely_touches" and not str(quote or "").strip():
            raise EventWatchError("likely_touches 必須附文件逐字引文（L18）")
        entry = {"lead_id": lead_id, "at": _now(), "verdict": verdict, "quote": quote,
                 "session_id": session_id}
        watch["semantic_flag"] = entry
        return entry
    raise EventWatchError(f"watch 不存在：{watch_id}")


def judge(data: dict[str, Any], watch_id: str, *, touches: bool, note: str,
          quote: str | None = None) -> dict[str, Any]:
    """互動 session 的判定（G7：判定只在互動）。

    - `touches=False` → `reactivate`（note 必填）：觸發 lead 已在 consumed_leads，不會再叫醒；到期仍由 expires 收斂。
    - `touches=True` → consume＋寫 `judgment`（`quote`＝文件逐字，**必填**；L18：標籤要指得回原文）。
      **等待不在這裡消失**：thesis 來源的由 `thesis_lifecycle` 那一筆接住、讀圖來源的列進 `needs_reread`（C3／A5；Step 1.5）。
    """
    if not str(note or "").strip():
        raise EventWatchError("judge 必須附 note（為什麼判定觸及／無關）")
    for watch in data["watches"]:
        if watch["watch_id"] != watch_id:
            continue
        if watch.get("kind") != SEMANTIC_KIND or watch.get("status") != "fired":
            raise EventWatchError(f"只能判定 fired 的語意 watch：{watch_id}")
        judgment = {"at": _now(), "touches": "yes" if touches else "no", "note": note,
                    "lead_id": (watch.get("woken_by") or {}).get("lead_id")}
        if touches:
            if not str(quote or "").strip():
                raise EventWatchError("判定觸及必須附 --quote（文件逐字）")
            judgment["quote"] = quote
            judgment["handled"] = None
            watch["judgment"] = judgment
            watch["status"] = "consumed"
        else:
            watch["judgments"] = [*(watch.get("judgments") or []), judgment]
            reactivate(data, watch_id, note=note)
        return judgment
    raise EventWatchError(f"watch 不存在：{watch_id}")


def primary_coverage() -> frozenset[str]:
    """有一手來源會產出 lead 的實體（ticker 與 co:*）：宣告 primary 的 feed 公司、EDGAR 監看清單、
    MOPS 監看清單。語意 watch 的實體若全不在這裡＝**登記了但叫不醒**（只剩到期或互動查詢能救）。"""
    from engine_b import routine_config
    from identity.registry import get_registry

    registry = get_registry()
    config = json.loads((Path(__file__).resolve().parent.parent / "crons" / "harvest_config.json")
                        .read_text(encoding="utf-8"))
    out: set[str] = set()
    for feed in config.get("feeds") or []:
        if feed.get("source_class") == "primary" and feed.get("company_id"):
            out.add(str(feed["company_id"]))
    tickers: set[str] = set()
    watch = config.get("edgar_watch") or {}
    if watch:
        try:
            tracked = routine_config.discover_tracked_tickers(routine_config.load_config())
        except Exception:  # noqa: BLE001 — derivation 失敗只縮小涵蓋面（手動清單仍是下限）
            tracked = frozenset()
        tickers |= set(routine_config.edgar_watch_tickers(watch, tracked=tracked))
    mops = config.get("mops_watch") or {}
    if mops:
        taiwan = frozenset(t for company in registry.companies
                           for t in [str(getattr(company, "research_ticker", "") or "")]
                           if t.upper().endswith((".TW", ".TWO")))
        tickers |= set(routine_config.mops_watch_tickers(mops, registry_tickers=taiwan))
    for ticker in tickers:
        out.add(ticker)
        company = registry.company_id_for_ticker(ticker)
        if company:
            out.add(company)
    return frozenset(out)


def is_reachable(watch: Mapping[str, Any], coverage: frozenset[str]) -> bool:
    return bool(set(watch.get("entities") or ()) & coverage)


def watch_detail(watch: Mapping[str, Any]) -> str:
    """一句話說出「這個 watch 在等什麼」。

    ⚠ 這裡是 WATCH_KINDS 的平行消費端（L16）：新增 kind 必須同步補一行，
    否則 2026-09-02 的事故重演——[321] 併入 `related_entity_signal` 後這裡沒跟上，
    daily 的 sweep 整批 KeyError、38 筆 watch 一輪 0 檢查。用 .get 兜底讓
    單一未知 kind 只影響自己那一行，不再炸掉整份輸出。
    """
    return {
        "date": f"until {watch.get('until')}",
        "entity_filing_signal": f"等 {','.join(watch.get('entities') or [])} 的一手文件",
        "fact_verification": f"對照 {watch.get('fact', '')[:50]}",
        "related_entity_signal": f"等 {','.join(watch.get('entities') or [])} 的新動靜",
        "semantic_condition": (f"條件「{str(watch.get('condition') or '')[:40]}…」"
                               f"（{watch.get('source_ref')}；比對 {','.join(watch.get('entities') or [])} 的一手文件）"),
    }.get(watch["kind"], "（未知 kind——render 端缺條目，請補 watch_detail）")


def wake_target(watch: Mapping[str, Any]) -> dict[str, Any]:
    """這個 watch 觸發時會喚醒誰。三種去處，混在一起就看不出比例。"""

    if watch.get("wake_pq2"):
        return {"kind": "pq2", "ref": watch["wake_pq2"], "label": f"pq2 [{watch['wake_pq2']}]"}
    if watch.get("wake_lead"):
        return {"kind": "lead", "ref": watch["wake_lead"], "label": f"lead {watch['wake_lead']}"}
    if watch.get("disproof_ref"):
        return {"kind": "disproof", "ref": watch["disproof_ref"],
                "label": f"反證 {watch['disproof_ref']}（互動判定）"}
    if watch.get("wake_reading"):
        return {"kind": "reading", "ref": watch["wake_reading"],
                "label": f"讀圖 {watch['wake_reading']}（醒來＝列進該重讀，不自動重讀）"}
    if watch.get("hypothesis_ref"):
        return {"kind": "hypothesis", "ref": watch.get("hypothesis_ref"),
                "label": f"假設 {watch.get('hypothesis_ref')}"}
    # ⚠ 沒有任何喚醒目標的 watch 以前會被預設成「假設」（§14 已知陷阱）——現在照實說。
    return {"kind": "unknown", "ref": None, "label": "（沒有喚醒目標——add_watch 應已拒收）"}


def _render_watch(watch: Mapping[str, Any]) -> str:
    kind = watch["kind"]
    detail = watch_detail(watch)
    poll = "｜可輪詢" if (watch.get("poll") or {}).get("eligible") else ""
    target = wake_target(watch)["label"]
    return (
        f"  {watch['watch_id']} [{watch['status']}] {kind}：{detail}"
        f" → 喚醒 {target}{poll}（expires {watch['expires']}）"
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Event Watch registry")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("counters", help="常駐計數器（含語意型叫不醒數；會讀 harvest 設定算一手涵蓋面）")
    reg = sub.add_parser(
        "register-disproof",
        help="登記一條 thesis／讀圖的反證或確認條件（semantic_condition；原文逐字、L7 三件套必填）",
    )
    reg.add_argument("--condition", required=True, help="原文逐字（≥20 字）")
    reg.add_argument("--entities", required=True, help="逗號分隔；至少一個 registry 解析得到的 co:*")
    reg.add_argument("--source-ref", required=True, help="thesis:<memo 路徑>#<n> 或 reading:<reading_id>#<n>")
    reg.add_argument("--quote-locator", default="", help="原文在哪一節")
    reg.add_argument("--check-frequency", required=True)
    reg.add_argument("--action-48h", required=True)
    reg.add_argument("--expires", required=True)
    reg.add_argument("--node", default="")
    reg.add_argument("--note", default="")
    sub.add_parser("semantic-queue",
                   help="列醒來待檢的語意 watch（照醒來時間；標旗只是給人讀的提示，不是排序權）")
    jud = sub.add_parser("judge", help="互動 session 判定：觸及（consume＋judgment）或無關（reactivate）")
    jud.add_argument("watch_id")
    jud.add_argument("--touches", required=True, choices=("yes", "no"))
    jud.add_argument("--note", required=True)
    jud.add_argument("--quote", default="", help="文件逐字（--touches yes 時必填）")
    flg = sub.add_parser("flag", help="預篩標旗（只寫 semantic_flag、不改狀態；由 prescreen-apply 呼叫）")
    flg.add_argument("watch_id")
    flg.add_argument("--lead", required=True)
    flg.add_argument("--verdict", required=True, choices=PRESCREEN_VERDICTS)
    flg.add_argument("--quote", default="")
    flg.add_argument("--session-id", default="")
    prep = sub.add_parser("prescreen-prepare",
                          help="daily ⑩a：選醒來的語意 watch、以程式抓全文、寫預篩批次（名額＝每日上限扣當日已標旗）")
    prep.add_argument("--run-id", required=True)
    prep.add_argument("--out", required=True)
    papp = sub.add_parser("prescreen-apply",
                          help="daily ⑩c：驗證 LLM 的標旗提議（引文必須是原文逐字）後只寫 semantic_flag")
    papp.add_argument("--file", required=True)
    papp.add_argument("--batch", required=True)
    papp.add_argument("--run-id", required=True)
    consume = sub.add_parser("consume", help="假設對照完成後收掉 fired watch")
    consume.add_argument("watch_id")
    react = sub.add_parser(
        "reactivate",
        help="對照後判定觸發 lead 與等待條件無關 → 回 active 繼續等（不是 consume）",
    )
    react.add_argument("watch_id")
    react.add_argument("--note", default="", help="為什麼判定無關——稽核留在 watch 上")
    sweep = sub.add_parser("sweep", help="列出本輪 T2 該查的 watch（agent 拿去 WebSearch）")
    sweep.add_argument("--mark-checked", action="store_true")
    add = sub.add_parser("add")
    add.add_argument("--kind", required=True, choices=sorted(WATCH_KINDS))
    add.add_argument("--wake-pq2", type=int)
    add.add_argument("--expires", required=True)
    add.add_argument("--until")
    add.add_argument("--entities", default="")
    add.add_argument("--fact", default="")
    add.add_argument("--fact-check-ref", default="")
    add.add_argument("--wake-hypothesis", default="", help="假設 id（三個 wake 目標擇一）")
    add.add_argument(
        "--wake-lead", default="",
        help="追源線索 id（三個 wake 目標擇一）；一般由 park 自動建立，手動用於補漏",
    )
    add.add_argument("--poll", action="store_true")
    add.add_argument("--query-hint", default="")
    add.add_argument("--note", default="")
    args = parser.parse_args(argv)

    data = load_watches()
    if args.cmd == "list":
        for watch in data["watches"]:
            print(_render_watch(watch))
        print(json.dumps(counters(data), ensure_ascii=False))
        return 0
    if args.cmd == "consume":
        consume_fired(data, args.watch_id)
        save_watches(data)
        print(f"✓ 已收 {args.watch_id}")
        return 0
    if args.cmd == "reactivate":
        reactivate(data, args.watch_id, note=args.note or None)
        save_watches(data)
        print(f"✓ {args.watch_id} 回 active 繼續等（觸發 lead 已在 consumed_leads，不會再叫醒）")
        return 0
    if args.cmd == "counters":
        try:
            coverage: frozenset[str] | None = primary_coverage()
        except Exception as exc:  # noqa: BLE001 — 涵蓋面算不出來就照實說，不當成 0
            print(f"（一手涵蓋面算不出來：{type(exc).__name__}: {exc}——semantic_unreachable 記 null）")
            coverage = None
        print(json.dumps(counters(data, coverage=coverage), ensure_ascii=False))
        return 0
    if args.cmd == "register-disproof":
        watch = add_watch(
            data, kind=SEMANTIC_KIND, disproof_ref=args.source_ref, expires=args.expires,
            entities=[e for e in args.entities.split(",") if e.strip()], condition=args.condition,
            source_ref=args.source_ref, quote_locator=args.quote_locator,
            check_frequency=args.check_frequency, action_48h=args.action_48h, node=args.node,
            note=args.note,
        )
        save_watches(data)
        print(f"✓ 已登記 {watch['watch_id']} ← {args.source_ref}")
        return 0
    if args.cmd == "semantic-queue":
        from engine_b.leads import load as load_leads

        try:
            leads_store = load_leads()["leads"]
        except Exception:  # noqa: BLE001
            leads_store = {}
        pending = [w for w in data["watches"] if w.get("kind") == SEMANTIC_KIND and w.get("status") == "fired"]
        pending.sort(key=lambda w: str((w.get("woken_by") or {}).get("at") or ""))
        if not pending:
            print("（沒有醒來待檢的語意 watch）")
        for watch in pending:
            woken = watch.get("woken_by") or {}
            lead = leads_store.get(str(woken.get("lead_id"))) or {}
            current = flag_for_current(watch)
            print(f"{watch['watch_id']}｜醒於 {woken.get('at')}｜{watch.get('source_ref')}")
            print(f"  條件：{watch.get('condition')}")
            print(f"  觸發：{lead.get('title') or woken.get('lead_id')}｜{lead.get('url')}"
                  f"｜form {lead.get('form_type') or '—'}｜共用 {','.join(woken.get('shared_entities') or [])}")
            if current:
                print(f"  預篩（提示，不是判定）：{current.get('verdict')}"
                      + (f"｜引文：{current.get('quote')}" if current.get("quote") else ""))
            text_path = Path("library/private/semantic_text") / f"{woken.get('lead_id')}.txt"
            if text_path.is_file():
                print(f"  全文：{text_path}")
            print(f"  判定：python -m engine_b.event_watch judge {watch['watch_id']} --touches yes|no "
                  f"--note \"…\" [--quote \"文件逐字\"]")
        return 0
    if args.cmd == "judge":
        judgment = judge(data, args.watch_id, touches=args.touches == "yes", note=args.note,
                         quote=args.quote or None)
        save_watches(data)
        if args.touches == "yes":
            watch = next(w for w in data["watches"] if w["watch_id"] == args.watch_id)
            print(f"✓ {args.watch_id} 判定觸及（{judgment['at']}）")
            print(f"下一步：L7 48 小時動作＝{watch.get('action_48h')}")
            print("（等待不會消失：thesis 來源由 todo sync 出一筆 thesis_lifecycle；讀圖來源列進 needs_reread）")
        else:
            print(f"✓ {args.watch_id} 判定無關，回 active 繼續等（觸發 lead 不會再叫醒）")
        return 0
    if args.cmd == "flag":
        flag(data, args.watch_id, lead_id=args.lead, verdict=args.verdict,
             quote=args.quote or None, session_id=args.session_id or None)
        save_watches(data)
        print(f"✓ {args.watch_id} 標旗 {args.verdict}（狀態不變）")
        return 0
    if args.cmd == "prescreen-prepare":
        from engine_b import semantic_prescreen

        return semantic_prescreen.cmd_prepare(run_id=args.run_id, out=Path(args.out))
    if args.cmd == "prescreen-apply":
        from engine_b import semantic_prescreen

        return semantic_prescreen.cmd_apply(result_path=Path(args.file), batch_path=Path(args.batch),
                                            run_id=args.run_id)
    if args.cmd == "sweep":
        due = sweep_due(data)
        for watch in due:
            print(_render_watch(watch))
            hint = (watch.get("poll") or {}).get("query_hint")
            if hint:
                print(f"      query hint：{hint}")
            if args.mark_checked:
                mark_checked(data, watch["watch_id"])
        if args.mark_checked and due:
            save_watches(data)
        if not due:
            cfg = load_config()
            print(f"（本輪無 T2 待查；enabled={cfg['enabled']} budget={cfg['sweep_budget_per_run']}）")
        return 0
    if args.cmd == "add":
        watch = add_watch(
            data,
            kind=args.kind,
            wake_pq2=args.wake_pq2,
            expires=args.expires,
            until=args.until,
            entities=[e for e in args.entities.split(",") if e.strip()],
            fact=args.fact,
            fact_check_ref=args.fact_check_ref,
            hypothesis_ref=args.wake_hypothesis,
            wake_lead=args.wake_lead,
            poll_eligible=args.poll,
            poll_query_hint=args.query_hint,
            note=args.note,
        )
        save_watches(data)
        if watch.get("wake_pq2"):
            target = f"pq2 [{watch['wake_pq2']}]"
        elif watch.get("hypothesis_ref"):
            target = f"假設 {watch['hypothesis_ref']}"
        else:
            target = f"追源線索 {watch.get('wake_lead')}"
        print(f"✓ 已建 watch {watch['watch_id']} → {target}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
