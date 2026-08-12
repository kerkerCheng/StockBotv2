"""統一待辦池（廣義 pq2）——所有需要使用者決策的事，一個編號空間。

設計原則（2026-07-26 校正）：
- **單一核准收件匣：** prepared Research Action 入圖、決策複查、thesis 到期、
  Sheet-only 持股與手動 authority 問題收斂到這一個池。Raw／triaged leads 屬 pq1 工作佇列，
  routine 先自動 trace＋extract；只有 prepared 結果才進 pq2，避免同一題問使用者兩次。
- **編號持久：** `n` 在項目首次進池時指派，直到 resolve 才釋放。**不因排序或當日
  狀態重算**——否則你隔天回「3 go」會指到別的東西（正確性風險，不只是體驗問題）。
- **池是狀態，report 是敘事：** daily brief 不留檔；稽核價值由本池的 append-only
  `log`（何時提出、你怎麼決定、理由）承擔。
- 本模組只做池的機制（純標準庫）；各來源的蒐集在 CLI／composer 層注入，避免
  engine_b 反向依賴 Engine A/C/D。

pq1／pq2 定義見 CONCEPTS.md。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "1"

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POOL_PATH = _ROOT / "library" / "leads" / "todo_pool.json"

# 項目類型 → 該類型的 `go` 代表什麼動作（type-aware dispatch 的權威對照）。
ITEM_TYPES: dict[str, str] = {
    "lead_research": "（legacy）已移回自動 pq1，不再建立新項目",
    "ra_admission": "核准入圖（apply_research_action）",
    "decision_review": "核准補缺口研究；取得新 receipt 後 reassess",
    "source_trace_review": "核准人工 authority 後做 bounded 追源；go 只 dispatch 回 pq1",
    "thesis_lifecycle": "本機複查 thesis 並手動更新 lifecycle.json",
    "sheet_only_holding": "評估這筆 Sheet 持股（evaluate-signal 或 onboard）",
    "engine_c_observation": "核准把人工觀測寫入 Engine C append-only ledger",
    "thesis_mutation": "核准 thesis lifecycle 變更（revise／retire／watch）",
    "manual": "依 hint 執行",
}

VERBS = ("go", "drop", "pending")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class TodoError(ValueError):
    """未知編號、未知類型或非法操作。"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_pool() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "next_n": 1, "items": [], "log": []}


def load(path: Path | str = DEFAULT_POOL_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return empty_pool()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "items" not in data:
        raise ValueError(f"todo pool 格式非法：{p}")
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("next_n", 1)
    data.setdefault("items", [])
    data.setdefault("log", [])
    return data


def save(pool: Mapping[str, Any], path: Path | str = DEFAULT_POOL_PATH) -> None:
    """Atomic 寫檔，沿用 repo 慣例（tempfile + fsync + os.replace）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=p.parent,
        prefix=f".{p.name}.", suffix=".tmp", delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(pool, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, p)
    finally:
        temp_path.unlink(missing_ok=True)


def active_items(pool: Mapping[str, Any]) -> list[dict[str, Any]]:
    """未 resolve 的項目，依編號排序。"""
    return sorted(
        (i for i in pool["items"] if not i.get("resolved_at")),
        key=lambda i: i["n"],
    )


def actionable_items(pool: Mapping[str, Any]) -> list[dict[str, Any]]:
    """尚需使用者決定的項目；已 dispatch 的 pq1 job 仍 active 但不重複詢問。"""

    return [
        item for item in active_items(pool)
        if item.get("dispatch_status") not in {
            "queued", "researching", "awaiting_approval"
        }
    ]


def _key(item_type: str, ref_id: str) -> tuple[str, str]:
    return (item_type, ref_id)


def upsert(
    pool: dict[str, Any],
    *,
    item_type: str,
    ref_id: str,
    title: str,
    hint: str = "",
    source: str = "",
    at: str | None = None,
) -> dict[str, Any]:
    """加入或更新一個項目。冪等：同 (type, ref_id) 已在池中且未 resolve 就只更新
    顯示欄位、**保留原編號**（編號持久是本池的核心不變式）。"""
    if item_type not in ITEM_TYPES:
        raise TodoError(f"未知項目類型：{item_type}")
    if not str(ref_id).strip():
        raise TodoError("ref_id 不可為空")
    for item in pool["items"]:
        if _key(item["type"], item["ref_id"]) == _key(item_type, ref_id) and not item.get("resolved_at"):
            item["title"] = title or item["title"]
            if hint:
                item["hint"] = hint
            return item
    item = {
        "n": int(pool["next_n"]),
        "type": item_type,
        "ref_id": str(ref_id),
        "title": title,
        "hint": hint or ITEM_TYPES[item_type],
        "source": source,
        "added_at": at or _now(),
        "resolved_at": None,
        "resolution": None,
        "reason": None,
    }
    pool["next_n"] = int(pool["next_n"]) + 1
    pool["items"].append(item)
    return item


def get(pool: Mapping[str, Any], n: int) -> dict[str, Any]:
    for item in pool["items"]:
        if item["n"] == int(n) and not item.get("resolved_at"):
            return item
    raise TodoError(f"編號 {n} 不存在或已處理")


def _receipt_fields(receipt: str) -> dict[str, str]:
    """解析 `key:value;key:value` receipt；拒絕空值與重複欄位。"""

    fields: dict[str, str] = {}
    for part in receipt.split(";"):
        key, separator, value = part.partition(":")
        key = key.strip()
        value = value.strip()
        if not separator or not key or not value:
            raise TodoError("receipt 必須是非空的 key:value（多欄以分號分隔）")
        if key in fields:
            raise TodoError(f"receipt 欄位重複：{key}")
        fields[key] = value
    return fields


def _validate_go_receipt(item: Mapping[str, Any], receipt: str) -> None:
    """依 pq2 類型驗證完成 receipt；推薦或 transcript 都不是 authority。"""

    item_type = str(item["type"])
    if item_type == "lead_research":
        raise TodoError("legacy lead 不得在 pq2 go；請先執行 todo sync 移回 pq1")
    if item_type == "decision_review":
        if item.get("dispatch_status") not in {"completed", "parked"}:
            raise TodoError("decision_review 不得 bare go；請先 dispatch 並完成 pq1 checkpoint")
        if not receipt.strip() or receipt != item.get("dispatch_receipt"):
            raise TodoError("decision_review receipt 必須等於 terminal pq1 checkpoint receipt")
        if item.get("dispatch_status") == "completed" and not receipt.startswith("decision:pd_"):
            raise TodoError("completed decision_review 必須附新 decision receipt")
        return

    if item_type == "thesis_mutation":
        raise TodoError(
            "thesis_mutation 不得 bare go；請用 "
            "`todo complete-thesis-mutation <編號>` 執行寫入"
        )

    if item_type == "engine_c_observation":
        raise TodoError(
            "engine_c_observation 不得 bare go；請用 "
            "`todo complete-observation <編號>` 執行寫入並取得 observation receipt"
        )

    if item_type == "source_trace_review":
        if item.get("dispatch_status") not in {"completed", "parked"}:
            raise TodoError("source_trace_review 不得 bare go；請先 dispatch 並完成 pq1 checkpoint")
        if not receipt.strip() or receipt != item.get("dispatch_receipt"):
            raise TodoError("source_trace_review receipt 必須等於 terminal pq1 checkpoint receipt")
        if item.get("dispatch_status") == "completed" and not receipt.startswith("action:ra_"):
            raise TodoError("completed source_trace_review 必須附 prepared action receipt")
        if item.get("dispatch_status") == "parked" and not receipt.startswith("trace:"):
            raise TodoError("parked source_trace_review 必須附 trace outcome receipt")
        return

    if not receipt.strip():
        raise TodoError(f"{item_type} go 必須附 underlying authority receipt")
    fields = _receipt_fields(receipt)

    if item_type == "ra_admission":
        if set(fields) != {"action", "digest", "commit", "cohort"}:
            raise TodoError("ra_admission receipt 必須含 action、digest、commit、cohort")
        if fields["action"] != item["ref_id"]:
            raise TodoError("ra_admission receipt 的 action 不符 exact pq2 item")
        if not _SHA256_RE.fullmatch(fields["digest"]):
            raise TodoError("ra_admission receipt digest 必須是 64 位 sha256")
        if fields["commit"] != "not_required" and not _GIT_COMMIT_RE.fullmatch(fields["commit"]):
            raise TodoError("ra_admission receipt commit 必須是 40 位 Git SHA 或 not_required")
        if not fields["cohort"].startswith("dc_"):
            raise TodoError("ra_admission receipt 必須含 Decision cohort")
        completion = item.get("completion_authority") or {}
        if (
            completion.get("action_digest") != fields["digest"]
            or completion.get("commit") != fields["commit"]
            or completion.get("cohort_id") != fields["cohort"]
        ):
            raise TodoError("請用 todo complete-ra 驗證 apply／publish／Decision handoff 後再結案")
        return

    if item_type == "thesis_lifecycle":
        if set(fields) != {"lifecycle", "commit"}:
            raise TodoError("thesis_lifecycle receipt 必須含 lifecycle 與 commit")
        if fields["lifecycle"] != item["ref_id"] or not _GIT_COMMIT_RE.fullmatch(fields["commit"]):
            raise TodoError("thesis_lifecycle receipt 必須對應 exact thesis 與 40 位 Git SHA")
        return

    if item_type == "sheet_only_holding":
        if set(fields) != {"decision"} or not fields["decision"].startswith("pd_"):
            raise TodoError("sheet_only_holding receipt 必須是 decision:<decision_id>")
        return

    if item_type == "manual":
        if set(fields) != {"authority", "ref"}:
            raise TodoError("manual receipt 必須含 authority:<kind>;ref:<underlying_id>")
        return

    raise TodoError(f"尚未定義 {item_type} 的 go receipt contract")


def resolve(
    pool: dict[str, Any],
    n: int,
    verb: str,
    *,
    reason: str = "",
    receipt: str = "",
    at: str | None = None,
    until: str | None = None,
    trigger: str | None = None,
    event_type: str | None = None,
    _skip_receipt_validation: bool = False,
) -> dict[str, Any]:
    """以動詞處理一個編號。`pending` 不 resolve（明確 defer，留在池中）。

    `pending` 可帶 `until`（日期）或 `trigger`（事件描述）。帶了觸發條件的項目會被
    歸入「等事件」而非「等你決定」——它仍在池中可稽核，但在觸發之前不佔用決策注意力。
    這是使用者明確表達的等待，優先於由 blocker 自動推導的分類。
    """
    if verb not in VERBS:
        raise TodoError(f"未知動詞：{verb}（可用：{', '.join(VERBS)}）")
    item = get(pool, n)
    if verb == "go" and not _skip_receipt_validation:
        # 只有已完成 underlying 寫入的 complete-* 入口才略過——它自己就是收據來源。
        _validate_go_receipt(item, receipt)
    if (until or trigger or event_type) and verb != "pending":
        raise TodoError("until／trigger／event-type 只適用於 pending")
    if event_type and not trigger:
        raise TodoError("event-type 必須搭配人類可讀的 trigger")
    stamp = at or _now()
    if verb == "pending":
        item["deferred_at"] = stamp
        if until or trigger:
            item["waiting_on"] = {
                "until": until or None,
                "trigger": trigger or None,
                "reason": reason or None,
                "set_at": stamp,
                **({"event_type": event_type} if event_type else {}),
            }
    else:
        item.pop("waiting_on", None)
        item["resolved_at"] = stamp
        item["resolution"] = verb
        item["reason"] = reason or None
        item["receipt"] = receipt or None
    pool["log"].append({
        "at": stamp, "n": item["n"], "type": item["type"],
        "ref_id": item["ref_id"], "verb": verb, "reason": reason or None,
        "receipt": receipt or None,
    })
    return item


def dispatch_decision_review(
    pool: dict[str, Any],
    n: int,
    *,
    store: Any,
    at: str | None = None,
) -> dict[str, Any]:
    """把使用者核准的 decision review 轉為持久 pq1 job，不先 resolve pq2。"""

    item = get(pool, n)
    if item["type"] != "decision_review":
        raise TodoError(f"[{n}] 不是 decision_review，不能 dispatch 到 gap pq1")
    cohort_id = str(item["ref_id"])
    if not cohort_id.startswith("dc_"):
        raise TodoError("全域 authority blocker 沒有 bounded cohort work order，需依 hint 修復")
    work_order = store.latest_research_work_order(cohort_id)
    if work_order is None:
        raise TodoError(f"cohort {cohort_id} 的最新 decision 沒有 research work order")
    if (
        str(work_order.get("status")) in {"queued", "researching", "awaiting_approval"}
        and item.get("dispatch_ref") == str(work_order["work_order_id"])
    ):
        # 同一 bounded job 已在 pq1 中；重送不建立新的 go event，也不重複提醒。
        item["dispatch_status"] = str(work_order["status"])
        return {"item": item, "work_order": work_order}
    stamp = at or _now()
    dispatch_attempt = 1 + sum(
        1
        for entry in pool["log"]
        if entry.get("n") == int(n) and entry.get("verb") == "pq1_queued"
    )
    operation_key = f"todo:{n}:go:{dispatch_attempt}"
    transitioned = store.transition_research_work_order(
        work_order_id=str(work_order["work_order_id"]),
        to_status="queued",
        operation_key=operation_key,
        receipt={
            "todo_n": int(n),
            "todo_ref_id": cohort_id,
            "baseline_decision_id": str(work_order["decision_id"]),
            # completed／parked work order 只可由 exact pq2 go 明確重啟；
            # store 會核對這個 prior status，不把 terminal receipt 靜默抹掉。
            "prior_work_order_status": str(work_order["status"]),
        },
        observed_at=stamp,
    )
    item["dispatch_status"] = "queued"
    item["dispatch_ref"] = str(work_order["work_order_id"])
    item["dispatch_baseline_decision_id"] = str(work_order["decision_id"])
    item["dispatch_attempt"] = dispatch_attempt
    item["dispatched_at"] = stamp
    item.pop("deferred_at", None)
    item.pop("waiting_on", None)
    if not any(
        entry.get("n") == int(n)
        and entry.get("verb") == "pq1_queued"
        and entry.get("receipt") == item["dispatch_ref"]
        and int(entry.get("attempt") or 1) == dispatch_attempt
        for entry in pool["log"]
    ):
        pool["log"].append({
            "at": stamp,
            "n": int(n),
            "type": item["type"],
            "ref_id": cohort_id,
            "verb": "pq1_queued",
            "reason": "使用者 go 授權 bounded gap research；尚未 reassess",
            "receipt": item["dispatch_ref"],
            "attempt": dispatch_attempt,
        })
    return {"item": item, "work_order": transitioned}


def checkpoint_decision_review(
    pool: dict[str, Any],
    n: int,
    *,
    store: Any,
    to_status: str,
    receipt: str,
    reason: str = "",
    at: str | None = None,
) -> dict[str, Any]:
    """Checkpoint dispatched research；terminal 狀態必須留下 underlying receipt。"""

    if to_status not in {"researching", "awaiting_approval", "completed", "parked"}:
        raise TodoError(f"不支援的 pq1 checkpoint：{to_status}")
    if not receipt.strip():
        raise TodoError("pq1 checkpoint 必須附 receipt")
    item = get(pool, n)
    if item["type"] != "decision_review" or not item.get("dispatch_ref"):
        raise TodoError(f"[{n}] 尚未 dispatch decision-review pq1")
    if to_status == "completed":
        decision_id = receipt.removeprefix("decision:")
        try:
            decision = store.get_decision(decision_id)
        except KeyError as exc:
            raise TodoError(f"completed receipt 不是有效 decision：{decision_id}") from exc
        if decision["cohort_id"] != item["ref_id"]:
            raise TodoError("completed decision 不屬於原 cohort")
        if decision_id == item.get("dispatch_baseline_decision_id"):
            raise TodoError("completed receipt 不可沿用 dispatch 前的 baseline decision")
    stamp = at or _now()
    operation_key = f"todo:{n}:{to_status}:{receipt}"
    work_order = store.transition_research_work_order(
        work_order_id=str(item["dispatch_ref"]),
        to_status=to_status,
        operation_key=operation_key,
        receipt={"todo_n": int(n), "reference": receipt, "reason": reason},
        observed_at=stamp,
    )
    item["dispatch_status"] = to_status
    item["dispatch_receipt"] = receipt
    item["dispatch_updated_at"] = stamp
    pool["log"].append({
        "at": stamp,
        "n": int(n),
        "type": item["type"],
        "ref_id": item["ref_id"],
        "verb": f"pq1_{to_status}",
        "reason": reason or None,
        "receipt": receipt,
    })
    if to_status in {"completed", "parked"}:
        resolve(
            pool,
            n,
            "go",
            reason=reason or f"pq1 {to_status}",
            receipt=receipt,
            at=stamp,
        )
    return {"item": item, "work_order": work_order}


def dispatch_source_trace_review(
    pool: dict[str, Any],
    n: int,
    *,
    leads_path: Path | str,
    at: str | None = None,
) -> dict[str, Any]:
    """將需要人工 authority 的 exact trace item 重新排入 pq1，不先 resolve。"""

    from engine_b import leads

    item = get(pool, n)
    if item["type"] != "source_trace_review":
        raise TodoError(f"[{n}] 不是 source_trace_review")
    store = leads.load(leads_path)
    stamp = at or _now()
    lead = leads.requeue_trace(
        store,
        str(item["ref_id"]),
        trigger="user_go",
        reason="使用者核准 exact source_trace_review；排入 bounded pq1，尚未接受 claim 或核准入圖",
        requeued_at=stamp,
    )
    leads.save(store, leads_path)
    item["dispatch_status"] = "queued"
    item["dispatch_ref"] = f"lead:{lead['lead_id']}"
    item["dispatched_at"] = stamp
    item.pop("deferred_at", None)
    item.pop("waiting_on", None)
    pool["log"].append({
        "at": stamp,
        "n": int(n),
        "type": item["type"],
        "ref_id": item["ref_id"],
        "verb": "pq1_queued",
        "reason": "使用者 go 只授權 bounded source trace",
        "receipt": item["dispatch_ref"],
    })
    return {"item": item, "lead": lead}


def checkpoint_source_trace_review(
    pool: dict[str, Any],
    n: int,
    *,
    leads_path: Path | str,
    to_status: str,
    receipt: str,
    reason: str = "",
    at: str | None = None,
) -> dict[str, Any]:
    """Checkpoint trace pq1；prepared action 或誠實 parked receipt 才可結案。"""

    from engine_b import leads

    if to_status not in {"researching", "completed", "parked"}:
        raise TodoError(f"source_trace_review 不支援 checkpoint：{to_status}")
    if not receipt.strip():
        raise TodoError("pq1 checkpoint 必須附 receipt")
    item = get(pool, n)
    if item["type"] != "source_trace_review" or not item.get("dispatch_ref"):
        raise TodoError(f"[{n}] 尚未 dispatch source-trace pq1")
    store = leads.load(leads_path)
    lead = store["leads"].get(str(item["ref_id"]))
    if lead is None:
        raise TodoError("source_trace_review 對應 lead 不存在")
    if to_status == "completed":
        action_id = str((lead.get("refs") or {}).get("research_action_id") or "")
        if lead.get("status") not in {"action_prepared", "applied"}:
            raise TodoError("completed trace lead 尚未 action_prepared／applied")
        if receipt != f"action:{action_id}" or not action_id.startswith("ra_"):
            raise TodoError("completed trace receipt 必須對應 lead 的 prepared action")
    elif to_status == "parked":
        trace_status = str((lead.get("refs") or {}).get("trace_status") or "")
        if lead.get("status") != "parked" or receipt != f"trace:{trace_status}":
            raise TodoError("parked trace receipt 必須對應 lead 的 trace_status")
    elif lead.get("status") != "researching":
        raise TodoError("researching checkpoint 需要 lead 已進 researching")

    stamp = at or _now()
    item["dispatch_status"] = to_status
    item["dispatch_receipt"] = receipt
    item["dispatch_updated_at"] = stamp
    pool["log"].append({
        "at": stamp,
        "n": int(n),
        "type": item["type"],
        "ref_id": item["ref_id"],
        "verb": f"pq1_{to_status}",
        "reason": reason or None,
        "receipt": receipt,
    })
    if to_status in {"completed", "parked"}:
        resolve(
            pool,
            n,
            "go",
            reason=reason or f"source trace pq1 {to_status}",
            receipt=receipt,
            at=stamp,
        )
    return {"item": item, "lead": lead}


def apply_batch(
    pool: dict[str, Any],
    parsed: Mapping[str, Iterable[int]],
    *,
    reason: str = "",
    at: str | None = None,
) -> dict[str, list[int]]:
    """套用 `engine_b.batch.parse_batch_reply` 的結果。

    回 {"applied": [...], "failed": [...]}；單一編號失敗不中斷其餘（部分成功是
    可接受的——未處理的仍留在池裡，下次 brief 會再出現）。
    """
    applied: list[int] = []
    failed: list[int] = []
    for verb, numbers in parsed.items():
        for n in numbers:
            try:
                resolve(pool, n, verb, reason=reason, at=at)
                applied.append(int(n))
            except TodoError:
                failed.append(int(n))
    return {"applied": sorted(applied), "failed": sorted(failed)}


def _read_action_for_completion(action_id: str) -> dict[str, Any]:
    from mcp_server.research_actions import read_action

    return read_action(action_id)


def _declared_focus_for_action(action_id: str) -> str | None:
    """讀 RA 自報的 focus_company_id；讀不到就回 None（由呼叫端決定怎麼辦）。"""

    try:
        from mcp_server.research_actions import read_action

        action = read_action(action_id) or {}
    except Exception:
        return None
    # compaction 後 payload 為 None，focus 會被提升到 record 頂層。
    declared = str(
        (action.get("payload") or {}).get("focus_company_id")
        or action.get("focus_company_id")
        or ""
    ).strip()
    return declared or None


def _lead_context_for_action(
    action_id: str, *, action_digest: str, leads_path: Path | str
) -> dict[str, str]:
    from engine_b.leads import load as load_leads

    store = load_leads(leads_path)
    matches = [
        lead for lead in store["leads"].values()
        if (lead.get("refs") or {}).get("research_action_id") == action_id
    ]
    if not matches:
        # 從 decision gap work order 產出的 RA 沒有來源 lead——它的 focus 由 RA
        # 自己聲明（見 mcp_server/research_actions 的 focus_company_id）。lead
        # receipt 對這類 RA 不存在，不能當成缺漏；action digest 已在呼叫端驗過。
        declared = _declared_focus_for_action(action_id)
        if declared:
            return {"company_id": declared, "title": ""}
        raise TodoError(
            f"找不到綁定 {action_id} 的 lead receipt，且該 RA 未自報 focus_company_id"
        )
    if any(lead.get("status") != "applied" for lead in matches):
        raise TodoError("Research Action 的來源 lead 尚未全部標記 applied")
    if any(
        (lead.get("refs") or {}).get("action_digest") != action_digest
        for lead in matches
    ):
        raise TodoError("applied lead 的 action_digest 缺失或與核准內容不符")
    companies = {
        str((lead.get("refs") or {}).get("focus_company_id") or "").strip()
        for lead in matches
    } - {""}
    if len(companies) != 1:
        raise TodoError("applied lead 必須留下唯一 focus_company_id")
    # lead title 是入圖當下對「這是什麼」最接近的一句話；帶下去當 atomic_claim，
    # 讓 cohort 自己記得住當初的判斷，而不必事後翻 intake 報告反推。
    titles = [str(lead.get("title") or "").strip() for lead in matches]
    return {
        "company_id": companies.pop(),
        "title": next((title for title in titles if title), ""),
    }


def complete_engine_c_observation(
    pool: dict[str, Any],
    n: int,
    *,
    at: str | None = None,
) -> dict[str, Any]:
    """核准後才把提案內容寫入 append-only ledger，並以 observation_id 結案。

    寫入動作刻意收在這裡而不是留在 CLI：讓「取得使用者對 exact 編號的核准」與
    「實際落 authority」是同一個動作，中間沒有可以繞過的路徑。
    """

    from engine_c import pending_observations
    from engine_c.db import get_conn
    from engine_c.manual_observations import append_manual_observation

    item = get(pool, n)
    if item["type"] != "engine_c_observation":
        raise TodoError(f"[{n}] 不是 engine_c_observation")
    proposal_id = str(item["ref_id"])
    record = pending_observations.read(proposal_id)
    if record is None:
        raise TodoError(f"找不到提案 {proposal_id}")
    if record.get("state") != "pending":
        raise TodoError(f"提案 {proposal_id} 已是 {record.get('state')}，不可重複寫入")

    payload = dict(record["payload"])
    conn = get_conn()
    try:
        observation_id = append_manual_observation(
            conn,
            ticker=payload["ticker"],
            field_name=payload["field_name"],
            value=payload["value"],
            source_ref=payload["source_ref"],
            as_of=payload["as_of"],
            author=payload["author"],
            supersedes_id=payload.get("supersedes_id"),
        )
    finally:
        conn.close()
    pending_observations.mark_applied(proposal_id, observation_id=observation_id)

    receipt = f"observation:{observation_id};proposal:{proposal_id}"
    resolve(pool, n, "go", reason="使用者核准後寫入 Engine C ledger",
            receipt=receipt, at=at, _skip_receipt_validation=True)
    return {"observation_id": observation_id, "receipt": receipt}


def complete_thesis_mutation(
    pool: dict[str, Any],
    n: int,
    *,
    at: str | None = None,
) -> dict[str, Any]:
    """核准後才把提案寫入 lifecycle.json，並以 thesis 狀態結案。"""

    from thesis.pending_lifecycle import apply_proposal

    item = get(pool, n)
    if item["type"] != "thesis_mutation":
        raise TodoError(f"[{n}] 不是 thesis_mutation")
    proposal_id = str(item["ref_id"])
    try:
        result = apply_proposal(proposal_id)
    except Exception as exc:
        raise TodoError(str(exc)) from exc

    receipt = f"thesis:{result['thesis_id']}:{result['status']};proposal:{proposal_id}"
    resolve(pool, n, "go", reason="使用者核准後寫入 thesis lifecycle",
            receipt=receipt, at=at, _skip_receipt_validation=True)
    return result | {"receipt": receipt}


def _ensure_shadow_for_completion(
    *, company_id: str, ticker: str | None, as_of: str, thesis: str | None = None
) -> dict[str, Any]:
    from decision_lab.bootstrap import open_default_store
    from decision_lab.workflow import ensure_shadow_for_company
    from engine_d_runtime.bootstrap import build_default_runtime_provider

    store = open_default_store()
    provider = None
    try:
        provider = build_default_runtime_provider()
        return ensure_shadow_for_company(
            store,
            provider,
            company_id=company_id,
            ticker=ticker,
            as_of=as_of,
            thesis=thesis,
        )
    finally:
        try:
            if provider is not None:
                provider.close()
        finally:
            store.close()


def complete_ra_admission(
    pool: dict[str, Any],
    n: int,
    *,
    action_digest: str,
    company_id: str | None = None,
    ticker: str | None = None,
    leads_path: Path | str | None = None,
    at: str | None = None,
) -> dict[str, Any]:
    """驗證 RA 已完整 apply/publish，建立（或沿用）Shadow 後才 resolve pq2。

    此 completion point 不綁 Codex 或 Claude Code；任何本機 agent 在收到使用者
    對 exact item 的明確核准後，都走同一組 authority 與 receipt 檢查。
    """

    item = get(pool, n)
    if item["type"] != "ra_admission":
        raise TodoError(f"[{n}] 不是 ra_admission")
    action_id = str(item["ref_id"])
    digest = action_digest.strip().lower()
    if not _SHA256_RE.fullmatch(digest):
        raise TodoError("--digest 必須是完整 64 位 sha256")
    action = _read_action_for_completion(action_id)
    if action.get("action_digest") != digest:
        raise TodoError("Research Action digest 不符 exact 核准內容")

    git = action.get("git") or {}
    if action.get("state") == "pushed" and git.get("status") == "pushed":
        commit = str(git.get("commit") or "").lower()
        if not _GIT_COMMIT_RE.fullmatch(commit):
            raise TodoError("pushed Research Action 缺少有效 commit receipt")
    elif action.get("state") == "applied" and git.get("status") == "not_required":
        commit = "not_required"
    else:
        raise TodoError("Research Action 尚未完成 apply 與 publish（或 local-only durable apply）")
    execution = action.get("execution") or {}
    if any(row.get("status") != "complete" for row in execution.get("documents") or []):
        raise TodoError("Research Action document receipts 尚未 complete")
    if (execution.get("report") or {}).get("status") != "complete":
        raise TodoError("Research Action report receipt 尚未 complete")

    from engine_b.leads import DEFAULT_LEADS_PATH
    lead_context = _lead_context_for_action(
        action_id,
        action_digest=digest,
        leads_path=leads_path or DEFAULT_LEADS_PATH,
    )
    recorded_company = lead_context["company_id"]
    if company_id and company_id.strip() != recorded_company:
        raise TodoError("--company-id 與 applied lead 的 focus_company_id 不符")
    target_company = recorded_company
    if not ticker:
        from identity.registry import get_registry

        ticker = get_registry().research_ticker(target_company)
    stamp = at or _now()
    handoff = _ensure_shadow_for_completion(
        company_id=target_company,
        ticker=ticker,
        as_of=stamp,
        thesis=lead_context.get("title"),
    )
    cohort_id = str(handoff.get("cohort_id") or "")
    if not cohort_id.startswith("dc_"):
        raise TodoError("Decision handoff 未回傳有效 cohort receipt")
    receipt = (
        f"action:{action_id};digest:{digest};commit:{commit};cohort:{cohort_id}"
    )
    item["completion_authority"] = {
        "action_digest": digest,
        "commit": commit,
        "company_id": target_company,
        "cohort_id": cohort_id,
        "verified_at": stamp,
    }
    resolved = resolve(
        pool,
        n,
        "go",
        reason="Research Action durable apply＋Decision Shadow handoff 完成",
        receipt=receipt,
        at=stamp,
    )
    return {"item": resolved, "action": action_id, "handoff": handoff, "receipt": receipt}


def retire_legacy_pq1_items(
    pool: dict[str, Any], *, at: str | None = None
) -> int:
    """把舊版 raw lead／Weekly research topic 移回 pq1；保留稽核。"""
    stamp = at or _now()
    retired = 0
    for item in active_items(pool):
        legacy_lead = item["type"] == "lead_research"
        legacy_weekly = (
            item["type"] == "manual"
            and str(item.get("title") or "").startswith("Weekly topic：")
        )
        if not (legacy_lead or legacy_weekly):
            continue
        item["resolved_at"] = stamp
        item["resolution"] = "migrated_to_pq1"
        item["reason"] = "triage PASS 後由 routine 自動 trace/extract；prepared RA 才進 pq2"
        pool["log"].append({
            "at": stamp,
            "n": item["n"],
            "type": item["type"],
            "ref_id": item["ref_id"],
            "verb": "migrated_to_pq1",
            "reason": item["reason"],
        })
        retired += 1
    return retired


# 舊 import 相容；新程式使用語意較完整的名稱。
retire_legacy_lead_research = retire_legacy_pq1_items


def _dropped_before(pool: Mapping[str, Any], row: Mapping[str, Any]) -> bool:
    """該 (type, ref_id) 是否已被使用者明確 drop 過。"""
    key = _key(str(row["type"]), str(row["ref_id"]))
    return any(
        _key(item["type"], item["ref_id"]) == key
        and item.get("resolved_at")
        and item.get("resolution") == "drop"
        for item in pool["items"]
    )


def sync(
    pool: dict[str, Any],
    incoming: Iterable[Mapping[str, Any]],
    *,
    at: str | None = None,
    healthy_sources: Iterable[str] | None = None,
) -> dict[str, int]:
    """把各來源蒐集到的項目 upsert 進池。

    `incoming` 每筆需有 type／ref_id／title，可選 hint／source。已 resolve 的
    (type, ref_id) 會重新進池（代表它又出現了，例如新的 evidence-delta）——這是
    刻意的：resolve 表示「當時處理過」，不是永久黑名單。

    唯一例外是 `ra_admission`：Research Action 是 content-addressed 凍結物件，
    digest 固定、內容不會自行改變，所以 `drop` 一個 exact action_id 就是永久
    決定。若不排除，apply 永遠失敗的 RA（例如撞 DuplicateUrlError 而停在
    `partial`）會每次 sync 都取得新編號，把待辦池洗成噪音。要重新提出必須重跑
    prepare，那會產生新的 action_id 與 digest，自然重新進池。
    """
    added = 0
    reactivated = 0
    refreshed = 0
    stamp = at or _now()
    incoming = list(incoming)
    seen_keys = {_key(str(row["type"]), str(row["ref_id"])) for row in incoming}
    for row in incoming:
        if str(row["type"]) == "ra_admission" and _dropped_before(pool, row):
            continue
        before = len(pool["items"])
        item = upsert(
            pool,
            item_type=str(row["type"]),
            ref_id=str(row["ref_id"]),
            title=str(row.get("title") or ""),
            hint=str(row.get("hint") or ""),
            source=str(row.get("source") or ""),
            at=stamp,
        )
        if len(pool["items"]) > before:
            added += 1

        incoming_waiting = row.get("waiting_on")
        event_link = row.get("event_link")
        event_type = str((event_link or {}).get("type") or "")
        event_value = str((event_link or {}).get("value") or "")
        waiting_event_type = str(
            (item.get("waiting_on") or {}).get("event_type") or ""
        )
        dispatch_in_flight = item.get("dispatch_status") in {
            "queued",
            "researching",
            "awaiting_approval",
        }
        if dispatch_in_flight and (item.get("waiting_on") or {}).get(
            "derived_from_blockers"
        ):
            item.pop("waiting_on", None)
        # Consumed-marker：同一筆 decision receipt 只喚醒一次。`reactivation_event`
        # 先前只寫不讀，於是只要 collector 還回報同一個 material delta，每次 sync 都會
        # 重新喚醒——使用者剛設回等待，下一輪就被打回決策佇列，等待條件永遠黏不住
        # （2026-08-11 實測 [74]）。綁 event_type 因此把「永遠不會醒」換成「永遠不睡」。
        # 比對 receipt 而非布林旗標：換一筆新 decision（新 receipt）仍會正常喚醒。
        consumed_receipt = str(
            (item.get("reactivation_event") or {}).get("receipt") or ""
        ).strip()
        incoming_receipt = str((event_link or {}).get("receipt") or "").strip()
        material_decision_event = (
            item["type"] == "decision_review"
            and event_type == "decision_evidence_delta"
            and event_value in {"material", "positive", "negative"}
            and waiting_event_type == event_type
            and not dispatch_in_flight
            and not (incoming_receipt and incoming_receipt == consumed_receipt)
        )

        # 使用者或 blocker 衍生的 waiting item 不能只靠自然語言等人記得回來。
        # Engine D 對同一 cohort 產生 material evidence delta 時，以 decision receipt
        # 喚醒原 stable pq2 item；這只恢復人工判斷，不 dispatch 研究、不建 decision。
        if material_decision_event and item.get("waiting_on"):
            prior_waiting = dict(item.get("waiting_on") or {})
            item.pop("waiting_on", None)
            item.pop("deferred_at", None)
            item["reactivated_at"] = stamp
            item["reactivation_event"] = dict(event_link)
            pool["log"].append({
                "at": stamp,
                "n": item["n"],
                "type": item["type"],
                "ref_id": item["ref_id"],
                "verb": "event_reactivated",
                "reason": "同一 cohort 出現 material evidence delta，恢復人工複查",
                "receipt": str((event_link or {}).get("receipt") or "") or None,
                "prior_waiting_on": prior_waiting,
            })
            reactivated += 1
        elif (
            item.get("waiting_on", {}).get("derived_from_blockers")
            and not incoming_waiting
        ):
            # blocker 已不再全屬 awaiting_external／system_internal，保守地回到
            # 決策佇列。人工設定的 waiting_on 不由此分支清除。
            prior_waiting = dict(item.get("waiting_on") or {})
            item.pop("waiting_on", None)
            item.pop("deferred_at", None)
            item["reactivated_at"] = stamp
            item["reactivation_event"] = {
                "type": "decision_blocker_mode_changed",
            }
            pool["log"].append({
                "at": stamp,
                "n": item["n"],
                "type": item["type"],
                "ref_id": item["ref_id"],
                "verb": "event_reactivated",
                "reason": "blocker 已不再全屬等待事件，恢復人工複查",
                "receipt": None,
                "prior_waiting_on": prior_waiting,
            })
            reactivated += 1
        elif (
            incoming_waiting
            and not item.get("waiting_on")
            and not material_decision_event
            and not dispatch_in_flight
        ):
            item["waiting_on"] = dict(incoming_waiting)
        elif (
            incoming_waiting
            and not material_decision_event
            and not dispatch_in_flight
            and (item.get("waiting_on") or {}).get("derived_from_blockers")
            and _waiting_reason_changed(item["waiting_on"], incoming_waiting)
        ):
            # blocker 仍全屬等待事件（mode 沒變，所以上面的 reactivate 分支不會觸發），
            # 但等的是不同的東西了。舊寫法只在沒有 waiting_on 時才填，於是顯示文字會
            # 一直停在第一次推導的當下——會告訴使用者去修一個已經修好的東西。
            # 只重算機器推導的；使用者以 --until/--trigger 明確設定的不動。
            prior_waiting = dict(item["waiting_on"])
            item["waiting_on"] = dict(incoming_waiting)
            pool["log"].append({
                "at": stamp,
                "n": item["n"],
                "type": item["type"],
                "ref_id": item["ref_id"],
                "verb": "waiting_reason_refreshed",
                "reason": "blocker 內容改變，重新推導等待理由",
                "receipt": None,
                "prior_waiting_on": prior_waiting,
            })
            refreshed += 1

    cleared, uncleared = _mark_source_cleared(
        pool, seen_keys, healthy_sources, stamp=stamp
    )

    return {
        "added": added,
        "reactivated": reactivated,
        "waiting_refreshed": refreshed,
        "source_cleared": cleared,
        "source_returned": uncleared,
        "active": len(active_items(pool)),
    }


def _mark_source_cleared(
    pool: dict[str, Any],
    seen_keys: set[tuple[str, str]],
    healthy_sources: Iterable[str] | None,
    *,
    stamp: str,
) -> tuple[int, int]:
    """標記「來源已成功執行但不再產出此項」的完成候選；**永不自動 resolve**。

    來源消失是推論，不是收據——`AGENTS.md` 的 provider-neutral 契約要求 pq2 的
    結案綁定使用者明確核准。這裡只把項目移出決策注意力並附上證據，關閉仍走
    `todo resolve <n> --verb drop`。

    只有 `healthy_sources` 明確列出的來源才判定；collector 失敗那一輪不列入，
    因此斷線不會被誤讀成「全部做完了」。
    """

    healthy = frozenset(healthy_sources or ())
    if not healthy:
        return 0, 0
    covered_types = {
        item_type
        for source, types in SOURCE_ITEM_TYPES.items()
        if source in healthy
        for item_type in types
    }
    cleared = 0
    returned = 0
    for item in active_items(pool):
        if item["type"] not in covered_types:
            continue
        present = _key(str(item["type"]), str(item["ref_id"])) in seen_keys
        if present and item.get("source_cleared"):
            # 來源又產出它了（例如新證據把 decision 推回 REVIEW）：撤銷標記。
            prior = dict(item.pop("source_cleared"))
            pool["log"].append({
                "at": stamp,
                "n": item["n"],
                "type": item["type"],
                "ref_id": item["ref_id"],
                "verb": "source_returned",
                "reason": "來源再次產出此項，撤銷完成候選標記",
                "receipt": None,
                "prior_source_cleared": prior,
            })
            returned += 1
            continue
        if present or item.get("source_cleared"):
            continue
        item["source_cleared"] = {
            "at": stamp,
            "source_healthy": True,
            "reason": "來源本輪成功執行，但不再產出此項；很可能已完成",
        }
        pool["log"].append({
            "at": stamp,
            "n": item["n"],
            "type": item["type"],
            "ref_id": item["ref_id"],
            "verb": "source_cleared",
            "reason": "來源本輪成功執行，但不再產出此項",
            "receipt": None,
        })
        cleared += 1
    return cleared, returned


# ── 來源蒐集（lazy import，避免 engine_b 反向依賴 Engine A/C/D）─────────────

def _fail_soft(collector: Any) -> list[dict[str, Any]]:
    """任何例外都回空清單——不讓池因為 Neo4j／Sheet／網路不通就整個壞掉。"""

    try:
        return list(collector())
    except Exception:
        return []


def collect_from_leads() -> list[dict[str, Any]]:
    """Raw／triaged leads 不屬 pq2；保留函式作相容面，永遠回空。"""
    return []


def collect_from_source_trace_reviews() -> list[dict[str, Any]]:
    """Fail-soft 外皮，維持既有呼叫面；健康狀態請改用 collect_all_with_health。"""

    return _fail_soft(_collect_source_trace_rows)


def _collect_source_trace_rows() -> list[dict[str, Any]]:
    """只有需要人類 authority 的 parked trace 才進 pq2；其餘仍屬 pq1/backlog。"""

    from engine_b.leads import load, trace_backlog

    rows = trace_backlog(load())
    return [
        {
            "type": "source_trace_review",
            "ref_id": row["lead_id"],
            "title": str(
                row.get("review_title")
                or f"追原報告／來源 access — {row['title'] or row['lead_id']}"
            ),
            "hint": str(
                row.get("review_hint")
                or "go 只排入 bounded pq1；不接受 claim、不入圖。若需付費，另核准 exact 金額／方案。"
            ),
            "source": "source_trace",
        }
        for row in rows
        if row["requires_user"]
    ]


def collect_from_research_actions() -> list[dict[str, Any]]:
    """Fail-soft 外皮，維持既有呼叫面；健康狀態請改用 collect_all_with_health。"""

    return _fail_soft(_collect_research_action_rows)


def _collect_research_action_rows() -> list[dict[str, Any]]:
    """等核准入圖的 Research Action → 經典 pq2。"""
    from mcp_server.research_actions import iter_actions

    rows: list[dict[str, Any]] = []
    for action in iter_actions():
        if action.get("state") in {
            "ready", "applying", "partial", "ready_for_approval", "partial_apply"
        }:
            action_id = str(action.get("action_id") or action.get("id") or "")
            # RA 自己聲明的 Decision handoff 優先。從 lead 來的 RA 由綁定 lead 提供
            # focus，但 decision gap work order 產出的 RA 根本沒有 lead 可綁——先前
            # 那類 RA 一律判成「未聲明 focus」而卡住，即使 cohort 早就指名了公司。
            declared = str(
                (action.get("payload") or {}).get("focus_company_id") or ""
            ).strip()
            try:
                from engine_b.leads import load as load_leads

                lead_store = load_leads()
                focuses = sorted({
                    str((lead.get("refs") or {}).get("focus_company_id") or "").strip()
                    for lead in lead_store["leads"].values()
                    if (lead.get("refs") or {}).get("research_action_id") == action_id
                } - {""})
            except Exception:
                focuses = []
            conflict = bool(declared) and bool(focuses) and set(focuses) != {declared}
            if declared and not conflict:
                focuses = [declared]
            if conflict:
                # 兩個來源都說話但說得不一樣：不猜，交還人工。
                handoff_hint = (
                    f"BLOCKER：RA 自報 focus_company_id={declared}，綁定 lead 卻是 "
                    f"{'、'.join(focuses)}；先回 pq1 對齊，不得先 apply。"
                )
            elif len(focuses) == 1:
                handoff_hint = (
                    f"核准 exact graph delta；Decision handoff：{focuses[0]}。"
                    "RA 內其他公司只作 evidence／relationship context，不自動建 cohort。"
                )
            elif focuses:
                handoff_hint = (
                    "BLOCKER：Research Action 有多個 focus_company_id："
                    f"{', '.join(focuses)}；先回 pq1 拆成明確 Decision handoff。"
                )
            else:
                handoff_hint = (
                    "BLOCKER：Research Action 尚未聲明唯一 focus_company_id；"
                    "先回 pq1 補 Decision handoff，不得先 apply。"
                )
            title = (
                action.get("slug")
                or action.get("title")
                or ((action.get("payload") or {}).get("report") or {}).get("title")
                or (action.get("review") or {}).get("title")
                or "Research Action"
            )
            rows.append({
                "type": "ra_admission",
                "ref_id": action_id,
                "title": str(title),
                "hint": handoff_hint,
                "source": "research_action",
            })
    return [r for r in rows if r["ref_id"]]


def _collect_engine_c_observation_rows() -> list[dict[str, Any]]:
    """待核准的 Engine C 人工觀測提案 → pq2。"""
    from engine_c.pending_observations import iter_pending

    rows: list[dict[str, Any]] = []
    for record in iter_pending():
        payload = record.get("payload") or {}
        rows.append({
            "type": "engine_c_observation",
            "ref_id": str(record["proposal_id"]),
            "title": (
                f"Engine C 觀測：{payload.get('ticker')} / {payload.get('field_name')}"
            ),
            "hint": (
                "核准後以 `todo complete-observation <編號>` 寫入 append-only ledger；"
                f"as_of={payload.get('as_of')}；來源={str(payload.get('source_ref'))[:80]}"
            ),
            "source": "engine_c",
        })
    return rows


def _collect_thesis_mutation_rows() -> list[dict[str, Any]]:
    """待核准的 thesis lifecycle 變更提案 → pq2。

    與 `thesis_lifecycle` 的差別：那是「這條 thesis 到期了，去複查」；這是「複查
    完了，主張它該轉成某個狀態」。前者由到期檢查產生，後者由研究結論產生。
    """
    from thesis.pending_lifecycle import iter_pending

    rows: list[dict[str, Any]] = []
    for record in iter_pending():
        payload = record.get("payload") or {}
        rows.append({
            "type": "thesis_mutation",
            "ref_id": str(record["proposal_id"]),
            "title": (
                f"thesis {payload.get('thesis_id')}："
                f"{payload.get('from_status')} → {payload.get('to_status')}"
            ),
            "hint": (
                "核准後以 `todo complete-thesis-mutation <編號>` 寫入 lifecycle.json；"
                f"理由：{str(payload.get('rationale'))[:120]}"
            ),
            "source": "thesis",
        })
    return rows


def collect_from_lifecycle() -> list[dict[str, Any]]:
    """Fail-soft 外皮，維持既有呼叫面；健康狀態請改用 collect_all_with_health。"""

    return _fail_soft(_collect_lifecycle_rows)


def _collect_lifecycle_rows() -> list[dict[str, Any]]:
    """到期／review_required 的 thesis → 本機複查待辦。"""
    from crons.thesis_freshness_check import lifecycle_due

    return [
        {
            "type": "thesis_lifecycle",
            "ref_id": tid,
            "title": f"thesis {tid}：{why}",
            "source": "lifecycle",
        }
        for tid, why in lifecycle_due()
    ]


def _waiting_reason_changed(
    current: Mapping[str, Any], incoming: Mapping[str, Any]
) -> bool:
    """只比對語意欄位；set_at 每次推導都會變，不算改變。"""

    fields = ("trigger", "reason", "until", "event_type")
    return any(current.get(field) != incoming.get(field) for field in fields)


def _derive_waiting_on(blockers: Any) -> dict[str, Any] | None:
    """依 blocker registry 判斷此項是否純粹在等外部資料。

    回傳 None 代表仍需使用者決定（保守預設：registry 未登記的 code 一律當成需要人看）。
    """
    codes = [str(b) for b in blockers if isinstance(b, str)]
    if not codes:
        return None
    try:
        from decision_lab.blockers import get_blocker_registry

        registry = get_blocker_registry()
    except Exception:
        return None
    if registry.needs_user_decision(codes):
        return None
    reasons = registry.waiting_reasons(codes)
    return {
        "until": None,
        "trigger": (
            "／".join(reasons[:3])
            if reasons
            else "僅剩系統內部狀態，重新 reassess 即可（無使用者決定）"
        ),
        "reason": "所有 blocker 都不需要使用者決定",
        "set_at": _now(),
        "derived_from_blockers": True,
    }


def collect_from_decisions() -> list[dict[str, Any]]:
    """Fail-soft 外皮，維持既有呼叫面；健康狀態請改用 collect_all_with_health。"""

    return _fail_soft(_collect_decision_rows)


def _collect_decision_rows() -> list[dict[str, Any]]:
    """需要動作的 Engine D 決策項（REVIEW／TRADE／HEDGE）→ 複查待辦。

    需要本機 private Decision Store 與外部 authority；失敗會往上拋，由呼叫端
    決定是 fail-soft 還是記錄成「來源不健康」。
    """
    from mcp_server.decision_tools import get_decision_brief_core

    brief = get_decision_brief_core()
    rows: list[dict[str, Any]] = []
    items = brief.get("items") or []
    for item in items:
        action = str(item.get("recommended_action") or "")
        if action in {"NO ACTION", ""}:
            continue
        ref = str(item.get("cohort_id") or item.get("decision_id") or "")
        company = str(item.get("company_id") or "unknown")
        company_hint = str(item.get("company_id_hint") or "").strip()
        ticker = str(item.get("ticker") or "").strip().upper()
        if not ref and item.get("sheet_only"):
            identity = company if company not in {"", "unknown", "unresolved"} else (
                f"ticker:{ticker}" if ticker else ""
            )
            ref = f"sheet:{identity}" if identity else ""
        if not ref:
            continue
        label = company if company not in {"", "unknown", "unresolved"} else (
            company_hint or ticker or "unknown"
        )
        row = {
            "type": "sheet_only_holding" if item.get("sheet_only") else "decision_review",
            "ref_id": ref,
            "title": f"{action} — {label}",
            **({"hint": "核准 bounded gap research；完成後才 reassess"}
               if not item.get("sheet_only") else {}),
            "source": "decision_lab",
        }
        if not item.get("sheet_only") and item.get("evidence_delta"):
            row["event_link"] = {
                "type": "decision_evidence_delta",
                "value": str(item.get("evidence_delta") or "none"),
                "receipt": (
                    f"decision:{item['decision_id']}"
                    if item.get("decision_id")
                    else ""
                ),
            }
        # 若這個決策的所有 blocker 都不需要使用者決定（純粹在等世界產生新資料），
        # 就直接帶著推導出的等待理由入池，不佔決策注意力。保守規則：只要有一個
        # blocker 需要人決定就照舊進決策佇列。
        waiting = (
            None
            if str(item.get("evidence_delta") or "none")
            in {"material", "positive", "negative"}
            else _derive_waiting_on(item.get("blockers") or [])
        )
        if waiting:
            row["waiting_on"] = waiting
        rows.append(row)
    # Engine D 也可能因 portfolio authority 全域失效而要求 REVIEW，這時沒有
    # cohort item（例如 Google Sheet holdings 完全讀不到）。這仍是需要使用者
    # 處理的 pq2，不能因 items=[] 就從統一待辦池消失。
    if brief.get("action_needed") and not items:
        action = str(brief.get("recommended_action") or "REVIEW")
        blockers = sorted(str(b) for b in (brief.get("blockers") or []) if b)
        reason = str(brief.get("reason") or "Engine D 全域狀態需要複查")
        ref = "global:" + ("|".join(blockers) or action.lower())
        rows.append({
            "type": "decision_review",
            "ref_id": ref,
            "title": f"{action} — {reason}",
            "hint": "修復全域 authority blocker 後重跑 decision_lab today",
            "source": "decision_lab",
        })
    return rows


def collect_all(*, include_decisions: bool = True) -> list[dict[str, Any]]:
    return collect_all_with_health(include_decisions=include_decisions).rows


# 哪個 collector 負責哪些 pq2 類型。只有來源健康時，「該類型的 item 沒出現在
# incoming」才可解讀成「它完成了」；`manual` 沒有 collector，永遠不自動標記。
SOURCE_ITEM_TYPES: dict[str, frozenset[str]] = {
    "research_actions": frozenset({"ra_admission"}),
    "source_trace": frozenset({"source_trace_review"}),
    "lifecycle": frozenset({"thesis_lifecycle"}),
    "decisions": frozenset({"decision_review", "sheet_only_holding"}),
    "engine_c_observations": frozenset({"engine_c_observation"}),
    "thesis_mutations": frozenset({"thesis_mutation"}),
}


@dataclass(frozen=True)
class SourceCollection:
    """蒐集結果 ＋ 哪些來源真的成功執行過。

    四個 collector 都是 fail-soft（任何例外回空清單），這在斷線時是對的，但也
    製造了一個致命歧義：「來源成功執行、這個項目確實完成了」與「Neo4j 掛了、
    什麼都讀不到」在 sync 眼中長得一模一樣。少了 `healthy` 這個訊號，任何
    「來源消失就結案」的邏輯都會在斷線那次把整個池安靜清空。
    """

    rows: list[dict[str, Any]]
    healthy: frozenset[str]


def collect_all_with_health(*, include_decisions: bool = True) -> SourceCollection:
    rows: list[dict[str, Any]] = []
    healthy: set[str] = set()
    sources: list[tuple[str, Any]] = [
        ("research_actions", _collect_research_action_rows),
        ("source_trace", _collect_source_trace_rows),
        ("lifecycle", _collect_lifecycle_rows),
        ("engine_c_observations", _collect_engine_c_observation_rows),
        ("thesis_mutations", _collect_thesis_mutation_rows),
    ]
    if include_decisions:
        sources.append(("decisions", _collect_decision_rows))
    for name, collector in sources:
        try:
            collected = collector()
        except Exception:
            # 失敗就是失敗：不進 healthy，該來源的項目本輪一律不判定完成。
            continue
        rows += collected
        healthy.add(name)
    return SourceCollection(rows=rows, healthy=frozenset(healthy))


# ── CLI ────────────────────────────────────────────────────────────────────

def _waiting_label(item: Mapping[str, Any]) -> str:
    waiting = item.get("waiting_on") or {}
    parts = [p for p in (waiting.get("until"), waiting.get("trigger")) if p]
    return "；".join(str(p) for p in parts) or "未指定觸發條件"


def _item_line(item: Mapping[str, Any]) -> str:
    if item.get("dispatch_status"):
        flag = (
            f"（pq1 {item['dispatch_status']}：{item.get('dispatch_ref')}；"
            "無需再次 go）"
        )
    else:
        flag = "（已 defer）" if item.get("deferred_at") else ""
    return f"  [{item['n']}] {item['title']}{flag}"


def _last_checkpoint(
    pool: Mapping[str, Any], n: int, verb: str
) -> dict[str, Any] | None:
    """取該編號最後一筆指定 verb 的 log。checkpoint 自己寫的理由比任何泛用
    提示準確——它知道 pq1 到底停在什麼 gate 上。"""

    for entry in reversed(pool.get("log") or []):
        if entry.get("n") == int(n) and entry.get("verb") == verb:
            return dict(entry)
    return None


def _render(pool: Mapping[str, Any]) -> str:
    items = active_items(pool)
    if not items:
        return "（待辦池已清空）"
    # 「等你決定」與「等世界發生某件事」分開呈現。後者仍在池中可稽核，
    # 但不佔用決策注意力——這是待辦池訊噪比的主要來源。
    # 第三區：來源已不再產出、很可能已完成的項目。它們既不需要你決定，也不是在
    # 等世界發生什麼——只是等你確認關閉。混進前兩區會讓池子看起來比實際更忙。
    cleared = [i for i in items if i.get("source_cleared")]
    rest = [i for i in items if not i.get("source_cleared")]
    # 已 dispatch 的項目先前混在決策佇列裡，區標寫「回覆用編號 go｜drop｜pending」
    # 而項目自己寫「無需再次 go」，自相矛盾；而且 awaiting_approval（pq1 做完、
    # 等人工 gate）與 queued（還沒開始）長得一模一樣，兩者對使用者的意義完全不同。
    gated = [i for i in rest if i.get("dispatch_status") == "awaiting_approval"]
    in_flight = [
        i for i in rest if i.get("dispatch_status") in {"queued", "researching"}
    ]
    rest = [i for i in rest if i not in gated and i not in in_flight]
    deciding = [i for i in rest if not i.get("waiting_on")]
    waiting = [i for i in rest if i.get("waiting_on")]

    lines: list[str] = []
    if deciding:
        lines += ["待辦事項統整（回覆用編號；`<編號…> go｜drop｜pending`）", ""]
        by_type: dict[str, list[dict[str, Any]]] = {}
        for item in deciding:
            by_type.setdefault(item["type"], []).append(item)
        for item_type, group in by_type.items():
            lines.append(f"## {item_type} — {ITEM_TYPES[item_type]}")
            lines += [_item_line(item) for item in group]
            lines.append("")
    else:
        lines += ["待辦事項統整：目前沒有需要你決定的項目。", ""]

    if gated:
        lines.append(
            f"## pq1 已交回，等人工 gate（{len(gated)} 項；不吃 go／drop／pending）"
        )
        for item in gated:
            lines.append(f"  [{item['n']}] {item['title']}")
            checkpoint = _last_checkpoint(pool, item["n"], "pq1_awaiting_approval")
            reason = str((checkpoint or {}).get("reason") or "").strip()
            receipt = str((checkpoint or {}).get("receipt") or "").strip()
            if reason:
                lines.append(f"        ↳ {reason}")
            if receipt:
                lines.append(f"        ↳ packet：{receipt}")
            lines.append(f"        ↳ work order：{item.get('dispatch_ref')}")
        lines.append("")

    if in_flight:
        lines.append(f"## pq1 進行中（{len(in_flight)} 項，不需動作）")
        for item in in_flight:
            lines.append(
                f"  [{item['n']}] {item['title']}"
                f"（{item.get('dispatch_status')}：{item.get('dispatch_ref')}）"
            )
        lines.append("")

    if waiting:
        lines.append(f"## 等事件（{len(waiting)} 項，觸發前不需動作）")
        for item in waiting:
            lines.append(f"  [{item['n']}] {item['title']}")
            lines.append(f"        ↳ 等：{_waiting_label(item)}")
        lines.append("")

    if cleared:
        numbers = " ".join(str(item["n"]) for item in cleared)
        lines.append(
            f"## 已完成，待確認關閉（{len(cleared)} 項；確認無誤可回 `{numbers} drop`）"
        )
        for item in cleared:
            lines.append(f"  [{item['n']}] {item['title']}")
            lines.append(
                f"        ↳ {(item.get('source_cleared') or {}).get('reason', '')}"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="統一待辦池（廣義 pq2）")
    ap.add_argument("--pool", default=str(DEFAULT_POOL_PATH))
    sub = ap.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="列出待辦（不同步）")
    p_list.add_argument("--json", action="store_true")

    p_sync = sub.add_parser("sync", help="從各來源同步後列出")
    p_sync.add_argument("--no-decisions", action="store_true",
                        help="跳過 Engine D 決策佇列（免外部連線）")
    p_sync.add_argument("--json", action="store_true")

    p_res = sub.add_parser("resolve", help="處理編號：go／drop／pending")
    p_res.add_argument("numbers", nargs="+")
    p_res.add_argument("--verb", required=True, choices=VERBS)
    p_res.add_argument("--reason", default="")
    p_res.add_argument("--receipt", default="")
    p_res.add_argument(
        "--until", default=None,
        help="pending 專用：等到哪個日期（如 2026-08-27）。設了就歸入「等事件」，不再佔決策注意力。",
    )
    p_res.add_argument(
        "--trigger", default=None,
        help="pending 專用：等哪個事件（如「S-4 公開」）。",
    )
    p_res.add_argument(
        "--event-type",
        default=None,
        choices=("decision_evidence_delta",),
        help="把人類 trigger 綁到可執行事件；目前支援 decision_evidence_delta。",
    )

    p_dispatch = sub.add_parser(
        "dispatch", help="把 decision／source-trace review 的 go checkpoint 成 pq1 job"
    )
    p_dispatch.add_argument("numbers", nargs="+")
    p_dispatch.add_argument("--leads", default="")

    p_work = sub.add_parser("work", help="更新已 dispatch 的 decision-review pq1 job")
    p_work.add_argument("number", type=int)
    p_work.add_argument(
        "--to", required=True,
        choices=("researching", "awaiting_approval", "completed", "parked"),
    )
    p_work.add_argument("--receipt", required=True)
    p_work.add_argument("--reason", default="")
    p_work.add_argument("--leads", default="")

    p_complete_obs = sub.add_parser(
        "complete-observation",
        help="核准後把 Engine C 觀測提案寫入 append-only ledger 並結案",
    )
    p_complete_obs.add_argument("number", type=int)

    p_complete_tm = sub.add_parser(
        "complete-thesis-mutation",
        help="核准後把 thesis lifecycle 變更寫入 lifecycle.json 並結案",
    )
    p_complete_tm.add_argument("number", type=int)

    p_complete_ra = sub.add_parser(
        "complete-ra",
        help="驗證 RA durable apply＋Decision handoff 後結案 exact pq2 item",
    )
    p_complete_ra.add_argument("number", type=int)
    p_complete_ra.add_argument("--digest", required=True)
    p_complete_ra.add_argument("--company-id", default="")
    p_complete_ra.add_argument("--ticker", default="")
    p_complete_ra.add_argument("--leads", default="")

    p_batch = sub.add_parser("batch", help="套用批次語法，如 '1 3 go 4 drop'")
    p_batch.add_argument("reply")

    p_add = sub.add_parser("add", help="手動加入待辦")
    p_add.add_argument("title")
    p_add.add_argument("--hint", default="")
    p_add.add_argument("--ref", default="")

    args = ap.parse_args(argv)
    pool = load(args.pool)

    if args.command == "list":
        print(json.dumps(active_items(pool), ensure_ascii=False, indent=2)
              if args.json else _render(pool))
        return 0

    if args.command == "sync":
        retired = retire_legacy_pq1_items(pool)
        collected = collect_all_with_health(include_decisions=not args.no_decisions)
        result = sync(
            pool, collected.rows, healthy_sources=collected.healthy
        )
        save(pool, args.pool)
        if args.json:
            print(json.dumps({**result, "items": active_items(pool)},
                             ensure_ascii=False, indent=2))
        else:
            migration = f"；移回 pq1 {retired}" if retired else ""
            print(f"（新增 {result['added']}，目前 {result['active']} 項待辦{migration}）\n")
            print(_render(pool))
        return 0

    if args.command == "resolve":
        failures = 0
        for raw in args.numbers:
            try:
                resolve(
                    pool, int(raw), args.verb,
                    reason=args.reason, receipt=args.receipt,
                    until=args.until, trigger=args.trigger,
                    event_type=args.event_type,
                )
                suffix = ""
                if args.verb == "pending" and (args.until or args.trigger):
                    suffix = f"（等：{args.until or args.trigger}）"
                print(f"✓ [{raw}] → {args.verb}{suffix}")
            except (TodoError, ValueError) as exc:
                failures += 1
                print(f"✗ [{raw}]：{exc}", file=sys.stderr)
        save(pool, args.pool)
        return 1 if failures else 0

    if args.command in {"dispatch", "work"}:
        from engine_b.leads import DEFAULT_LEADS_PATH

        decision_store = None
        failures = 0
        try:
            if args.command == "dispatch":
                for raw in args.numbers:
                    try:
                        item = get(pool, int(raw))
                        if item["type"] == "decision_review":
                            if decision_store is None:
                                from decision_lab.bootstrap import open_default_store
                                decision_store = open_default_store()
                            result = dispatch_decision_review(
                                pool, int(raw), store=decision_store
                            )
                        elif item["type"] == "source_trace_review":
                            result = dispatch_source_trace_review(
                                pool,
                                int(raw),
                                leads_path=args.leads or DEFAULT_LEADS_PATH,
                            )
                        else:
                            raise TodoError(
                                f"[{raw}] 類型 {item['type']} 不支援 pq1 dispatch"
                            )
                        save(pool, args.pool)
                        print(f"✓ [{raw}] → pq1 queued {result['item']['dispatch_ref']}")
                    except (TodoError, KeyError, ValueError) as exc:
                        failures += 1
                        print(f"✗ [{raw}]：{exc}", file=sys.stderr)
            else:
                try:
                    item = get(pool, args.number)
                    if item["type"] == "decision_review":
                        if decision_store is None:
                            from decision_lab.bootstrap import open_default_store
                            decision_store = open_default_store()
                        result = checkpoint_decision_review(
                            pool, args.number, store=decision_store,
                            to_status=args.to, receipt=args.receipt,
                            reason=args.reason,
                        )
                    elif item["type"] == "source_trace_review":
                        result = checkpoint_source_trace_review(
                            pool,
                            args.number,
                            leads_path=args.leads or DEFAULT_LEADS_PATH,
                            to_status=args.to,
                            receipt=args.receipt,
                            reason=args.reason,
                        )
                    else:
                        raise TodoError(
                            f"[{args.number}] 類型 {item['type']} 不支援 pq1 checkpoint"
                        )
                    save(pool, args.pool)
                    print(f"✓ [{args.number}] pq1 → {args.to} ({args.receipt})")
                except (TodoError, KeyError, ValueError) as exc:
                    failures += 1
                    print(f"✗ [{args.number}]：{exc}", file=sys.stderr)
        finally:
            if decision_store is not None:
                decision_store.close()
        return 1 if failures else 0

    if args.command == "complete-observation":
        try:
            result = complete_engine_c_observation(pool, args.number)
            save(pool, args.pool)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except TodoError as exc:
            print(f"✗ [{args.number}]：{exc}", file=sys.stderr)
            return 2

    if args.command == "complete-thesis-mutation":
        try:
            result = complete_thesis_mutation(pool, args.number)
            save(pool, args.pool)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except TodoError as exc:
            print(f"✗ [{args.number}]：{exc}", file=sys.stderr)
            return 2

    if args.command == "complete-ra":
        try:
            result = complete_ra_admission(
                pool,
                args.number,
                action_digest=args.digest,
                company_id=args.company_id or None,
                ticker=args.ticker or None,
                leads_path=args.leads or None,
            )
            save(pool, args.pool)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except (TodoError, KeyError, OSError, ValueError) as exc:
            print(f"✗ [{args.number}]：{exc}", file=sys.stderr)
            return 1

    if args.command == "batch":
        from engine_b.batch import parse_batch_reply

        parsed = parse_batch_reply(args.reply)
        if not parsed:
            print("無法解析批次語法（需要「數字…動詞」配對）", file=sys.stderr)
            return 1
        outcome = apply_batch(pool, parsed)
        save(pool, args.pool)
        print(json.dumps(outcome, ensure_ascii=False))
        return 0 if not outcome["failed"] else 1

    if args.command == "add":
        item = upsert(
            pool, item_type="manual",
            ref_id=args.ref or f"manual:{pool['next_n']}",
            title=args.title, hint=args.hint, source="manual",
        )
        save(pool, args.pool)
        print(f"✓ 已加入 [{item['n']}] {item['title']}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
