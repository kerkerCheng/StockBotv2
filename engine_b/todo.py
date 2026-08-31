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
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "1"

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POOL_PATH = _ROOT / "library" / "leads" / "todo_pool.json"

# 項目類型 → 該類型的 `go` 代表什麼動作（type-aware dispatch 的權威對照）。
ITEM_TYPES: dict[str, str] = {
    "lead_research": "（legacy）已移回自動 pq1，不再建立新項目",
    "ra_admission": "核准入圖（apply_research_action）",
    "decision_review": "REVIEW 有兩種成因，逐項 hint 才是準的：有 blocker → go 派回 pq1；無 blocker → 改跑 reassess",
    "source_trace_review": "核准人工 authority 後做 bounded 追源；go 只 dispatch 回 pq1",
    "thesis_lifecycle": "本機複查 thesis 並手動更新 lifecycle.json",
    "sheet_only_holding": "評估這筆 Sheet 持股（evaluate-signal 或 onboard）",
    "engine_c_observation": "核准把人工觀測寫入 Engine C append-only ledger",
    "thesis_mutation": "核准 thesis lifecycle 變更（revise／retire／watch）",
    "manual": "依 hint 執行",
}

# 每個 pq2 類型的 `go` 究竟授權什麼、以及**最相鄰的哪一步不在授權內**。
#
# ⚠ 「不含」欄不是修辭。`AGENTS.md` 反覆寫過同一件事（研究 `go` 不代表入圖、
# 入圖 `go` 不代表 thesis mutation、任何 `go` 都不代表 live），但那些句子散在政策檔裡，
# 每個消費端都得自己回想一次——而回想錯的方向永遠是「以為授權比較寬」。
# 分類有 SSOT 就要跟著資料走到需要它的地方（L16）：掛在 item 上，brief 就不必記得。
#
# 鍵必須與 `ITEM_TYPES` 完全一致，由 `tests/test_engine_b_todo.py` 斷言——
# 新增一個類型時會被強迫決定它的授權邊界，而不是預設繼承某個較寬的。
GO_AUTHORIZATION: dict[str, tuple[str, str]] = {
    "lead_research": ("（legacy）不再建立新項目", "任何 authority mutation"),
    "ra_admission": ("exact graph admission（apply_research_action）", "thesis mutation 與 live"),
    "decision_review": ("bounded research（派回 pq1）", "入圖、Engine C 寫入與 live"),
    "source_trace_review": ("bounded 追源（dispatch 回 pq1）", "提高 evidence tier 與入圖"),
    "thesis_lifecycle": ("本機複查該 thesis", "自動改 lifecycle 或入圖"),
    "sheet_only_holding": ("evaluate-signal／onboard 建 cohort", "任何部位動作"),
    "engine_c_observation": ("寫入 Engine C append-only ledger", "入圖與 thesis mutation"),
    "thesis_mutation": ("該筆 thesis lifecycle 變更", "入圖與 live"),
    "manual": ("依 hint 執行的 exact 動作", "hint 未載明的任何動作"),
}


def go_authorization(item_type: str) -> dict[str, str]:
    """回傳這個類型的 `go` 授權邊界，供決策行的「go = …，不含 …」使用。"""

    authorizes, excludes = GO_AUTHORIZATION.get(
        item_type, ("依 hint 執行的 exact 動作", "hint 未載明的任何動作")
    )
    return {"go_authorizes": authorizes, "go_excludes": excludes}


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
        if not item.get("waiting_on")
        and item.get("dispatch_status") not in {
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
        if item.get("dispatch_status") == "completed" and not (
            receipt.startswith("action:ra_") or receipt.startswith("graph:")
        ):
            # 兩條入圖路徑都可結案；graph: 的實體存在性已在
            # checkpoint_source_trace_review 驗過（extractions/<doc_id>.json 必須存在，
            # 且 lead 必須 applied），此處只認前綴，不重複那道檢查。
            raise TodoError(
                "completed source_trace_review 必須附 action:<ra_id> 或 graph:<source_doc> receipt"
            )
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
            # 無條件 pending 的語意是「尚待人工決定」，不是沿用上一輪的外部事件。
            # 舊行為會保留既有 waiting_on，讓一個已知可由人現在判斷的項目永久躺在
            # 「等事件」區；人工判讀因而被錯當成外部觸發。明確不帶 until／trigger
            # 時清除舊條件，保留 stable 編號並回到決策佇列。
            item.pop("waiting_on", None)
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
        raise TodoError(
            f"cohort {cohort_id} 的最新 decision 沒有 research work order"
            "——代表 coverage 已無 blocker，沒有 bounded gap 可補。若是因為出現新證據而"
            "要重看，該走 reassess 產生新 decision，不是 dispatch 舊 work order。"
        )
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
    dispatch_ref = str(item["dispatch_ref"])
    if dispatch_ref.startswith(ASSESSMENT_GAP_PREFIX):
        # assessment 層缺口沒有 Decision Store work order 可 transition
        # （work order 只在 coverage_pending 時建立）。checkpoint 仍然要 receipt，
        # 只是狀態存在 pool 這一側——與 source_trace_review 的 `lead:` ref 同慣例。
        work_order = None
    else:
        work_order = store.transition_research_work_order(
            work_order_id=dispatch_ref,
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


#: 由 assessment 層缺口（非 coverage blocker）驅動的 pq1 dispatch。
#: 沿用 `dispatch_source_trace_review` 已建立的慣例——`dispatch_ref` 不一定指向
#: Decision Store work order（那邊指向 lead）。前綴讓 `work` 能分辨要不要去
#: transition work order。
ASSESSMENT_GAP_PREFIX = "assessment_gap:"


def _prior_execution_intent(store: Any, cohort_id: str) -> str:
    """該 cohort 上一筆 decision 用的 intent。

    沿用先前 intent，讓同一個 cohort 的評估條件不因呼叫端習慣而跳動。

    ⚠ 這裡原本記著一個更強的理由：2026-08-26 實測，對先前是 `paper` 的 cohort 跑
    `research`，研究完整度會由 READY 退成 DATA_NEEDED，純由參數造成。**那個陷阱已於
    2026-08-29 從源頭修掉**——`sizing.py` 改用嚴重度分類，diagnostic 級的
    `execution_intent_research_only` 不再有改判權。本函式保留是為了評估條件的一致性，
    不再是為了閃避那個 bug。
    """

    try:
        decision = store.latest_decision_for_cohort(cohort_id)
        intent = str((decision["payload"]["request"] or {}).get("execution_intent") or "")
    except Exception:  # noqa: BLE001
        intent = ""
    return intent or "research"


def _substantive_blockers(cohort_id: str) -> list[str]:
    """該 cohort 目前**真的需要人動手**的 blocker。

    唯一權威是 `config/decision_blockers.json` 的 `resolution_mode`；
    這裡不另外猜一份（2026-08-26 手寫過一份 stale 清單，立刻就誤判了 co:axt）。
    """

    from mcp_server.decision_tools import get_decision_brief_core

    try:
        items = get_decision_brief_core().get("items") or []
    except Exception:  # noqa: BLE001
        return []
    for item in items:
        if str(item.get("cohort_id") or "") != cohort_id:
            continue
        # brief 已經附上分組（`_blockers_by_mode`），直接用——這裡刻意**不**再分一次組。
        grouped = item.get("blockers_by_mode")
        if isinstance(grouped, Mapping):
            return sorted(str(b) for b in (grouped.get("user_decision") or []))
        # 舊 payload（例如遠端受限 surface）沒有這個欄位時才自行分組。
        from decision_lab.blockers import describe_blocker

        return sorted(
            code
            for code in {str(b) for b in (item.get("blockers") or []) if b}
            if getattr(describe_blocker(code), "resolution_mode", "user_decision")
            == "user_decision"
        )
    return []


def advance_decision_review(
    pool: dict[str, Any],
    n: int,
    *,
    store: Any,
    at: str | None = None,
) -> dict[str, Any]:
    """`go` 對 decision_review 的**全函數**實作：永遠等於「是，往下走一步」。

    先前 `go` 只覆蓋一種情況（已有 research work order → dispatch），其餘一律
    拒絕，於是使用者必須自己分辨這一筆屬於哪一類、再翻譯成另一個動詞。
    2026-08-26 實測 9 個 REVIEW 項目分三類，其中 **4 個會被 `go` 拒絕**——
    而三類長得一模一樣（都叫 `REVIEW — co:xxx`），系統分得出來卻沒有代勞。

    三個分支，對應實測分類：

    - **有 work order** → dispatch 回 pq1（原行為，不變）。
    - **無 work order、無實質 blocker** → REVIEW 只是凍結 context 自然老化，
      reassess 重新凍結即可；下次 sync 自己結案。
    - **無 work order、有實質 blocker** → 先 reassess（可能清掉一部分並產生
      work order），再依結果 dispatch 或以 assessment-gap ref 排入 pq1。

    ⚠ **四個 authority gate 完全不受影響**：graph admission、Engine C ledger
    寫入、thesis mutation、live 資本仍各自走 `complete-*` 與 exact 人工核准。
    本函式只把「研究要不要開始」這件可逆的事自動化——它本來就是 `go` 的語意。
    """

    item = get(pool, n)
    if item["type"] != "decision_review":
        raise TodoError(f"[{n}] 不是 decision_review")
    if item.get("dispatch_status") in {"queued", "researching", "awaiting_approval"}:
        return {"item": item, "outcome": "already_in_flight"}

    cohort_id = str(item["ref_id"])
    if not cohort_id.startswith("dc_"):
        raise TodoError("全域 authority blocker 沒有 bounded cohort work order，需依 hint 修復")

    if store.latest_research_work_order(cohort_id) is not None:
        result = dispatch_decision_review(pool, n, store=store, at=at)
        result["outcome"] = "dispatched"
        return result

    # 沒有 work order：先刷新凍結 context。這一步對兩種剩餘情況都必要，
    # 且不改變任何 authority——decision 是 append-only，舊筆原封不動。
    from decision_lab.workflow import reassess
    from engine_d_runtime.bootstrap import build_default_runtime_provider

    stamp = at or _now()
    intent = _prior_execution_intent(store, cohort_id)
    reassessed = reassess(
        store,
        build_default_runtime_provider(),
        cohort_id,
        execution_intent=intent,
    )
    decision_id = str(reassessed.get("decision_id") or "")

    if store.latest_research_work_order(cohort_id) is not None:
        result = dispatch_decision_review(pool, n, store=store, at=stamp)
        result["outcome"] = "reassessed_then_dispatched"
        result["decision_id"] = decision_id
        return result

    remaining = _substantive_blockers(cohort_id)
    if not remaining:
        # context 老化而已；sync 會依新 decision 自行結案，這裡不強制 resolve。
        pool["log"].append({
            "at": stamp,
            "n": int(n),
            "type": item["type"],
            "ref_id": cohort_id,
            "verb": "pq1_reassessed",
            "reason": f"go：僅 context 老化，已以 intent={intent} 重新凍結",
            "receipt": f"decision:{decision_id}",
        })
        return {"item": item, "outcome": "reassessed", "decision_id": decision_id}

    # 仍有實質 blocker：assessment 層缺口沒有對應的 Decision Store work order
    # （work order 只在 coverage_pending 時建立，而 assessment_blockers 是
    # sizing 階段才算出來的）。用 assessment-gap ref 排入 pq1，完成時同樣要 receipt。
    item["dispatch_status"] = "queued"
    item["dispatch_ref"] = f"{ASSESSMENT_GAP_PREFIX}{cohort_id}"
    item["dispatch_baseline_decision_id"] = decision_id
    item["dispatched_at"] = stamp
    item["dispatch_scope"] = remaining
    item.pop("deferred_at", None)
    item.pop("waiting_on", None)
    pool["log"].append({
        "at": stamp,
        "n": int(n),
        "type": item["type"],
        "ref_id": cohort_id,
        "verb": "pq1_queued",
        "reason": "go：assessment 層缺口，排入 bounded pq1；" + "、".join(remaining),
        "receipt": f"decision:{decision_id}",
    })
    return {
        "item": item,
        "outcome": "queued_assessment_gap",
        "decision_id": decision_id,
        "scope": remaining,
    }


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
        if lead.get("status") not in {"action_prepared", "applied"}:
            raise TodoError("completed trace lead 尚未 action_prepared／applied")
        refs = lead.get("refs") or {}
        action_id = str(refs.get("research_action_id") or "")
        source_doc = str(refs.get("source_doc") or "")
        # 兩條入圖路徑，各自要求自己的完整 receipt——不是二選一放寬，是分開後兩邊都更嚴。
        #
        # (a) Research Action：MCP prepare→apply 流程，receipt 是 ra_ id。
        # (b) loader.load_to_neo4j：repo 內既有的正規入圖路徑，但**不產生 RA id**，
        #     於是 2026-08-15 的 COHR／MTSI 兩筆逐字稿入圖後結不了案——圖裡資料是
        #     真的、lead 已 applied、commit 也在，卻被擋在 receipt 格式上。那是
        #     gate 攔格式而不是攔風險（L15 第 1 條），正確的入圖路徑就該結得了案。
        #
        # (b) 的門檻刻意比 (a) 高一項：除了 receipt 與 refs 一致，還要求
        # extractions/<doc_id>.json 實際存在。receipt 因此指向一個可稽核的實體，
        # 而不只是一個字串——否則放寬解析就會變成放寬判準（L15 第 5 條）。
        # 另要求 lead 必須是 applied：loader 路徑沒有 prepared 中間態，
        # 停在 action_prepared 就代表根本還沒載入。
        if receipt.startswith("graph:"):
            doc_id = receipt[len("graph:"):]
            if not doc_id or doc_id != source_doc:
                raise TodoError("graph receipt 必須是 graph:<lead refs 的 source_doc>")
            if lead.get("status") != "applied":
                raise TodoError("graph receipt 要求 lead 已 applied（loader 無 prepared 中間態）")
            if not (_ROOT / "extractions" / f"{doc_id}.json").exists():
                raise TodoError(f"找不到 extractions/{doc_id}.json，graph receipt 無可稽核依據")
        elif receipt != f"action:{action_id}" or not action_id.startswith("ra_"):
            raise TodoError(
                "completed trace receipt 必須是 action:<ra_id>（RA 路徑）"
                "或 graph:<source_doc>（loader 入圖路徑）"
            )
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
    system_internal_retired = 0
    churn_suppressed = 0
    stamp = at or _now()
    incoming = list(incoming)
    seen_keys = {_key(str(row["type"]), str(row["ref_id"])) for row in incoming}
    for row in incoming:
        if row.get("system_internal_only"):
            key = _key(str(row["type"]), str(row["ref_id"]))
            existing = next(
                (
                    candidate for candidate in active_items(pool)
                    if _key(candidate["type"], candidate["ref_id"]) == key
                ),
                None,
            )
            if existing is not None and existing.get("dispatch_status") not in {
                "queued", "researching", "awaiting_approval"
            }:
                prior_waiting = dict(existing.get("waiting_on") or {})
                existing.pop("waiting_on", None)
                existing.pop("deferred_at", None)
                existing["resolved_at"] = stamp
                existing["resolution"] = "system_internal"
                existing["reason"] = (
                    "blocker registry 判定只剩 system_internal；不需要使用者決定，"
                    "亦不冒充外部事件"
                )
                pool["log"].append({
                    "at": stamp,
                    "n": existing["n"],
                    "type": existing["type"],
                    "ref_id": existing["ref_id"],
                    "verb": "system_internal_retired",
                    "reason": existing["reason"],
                    "receipt": "blocker-registry:system_internal",
                    **({"prior_waiting_on": prior_waiting} if prior_waiting else {}),
                })
                system_internal_retired += 1
            # 新出現的純系統狀態不建立 pq2；既有 in-flight work order 也不由
            # classifier 越權結案，仍交給它自己的 terminal receipt。
            continue
        if str(row["type"]) == "ra_admission" and _dropped_before(pool, row):
            continue
        # churn 修法第二半（2026-08-31）：corroboration 殘餘類項目以**內容**當復活判準。
        # resolve 過且 residual_digest 相同＝研究已交付、殘餘未變——不重生新號；
        # digest 變了＝真的有新缺口，照常鑄號（標題會講新缺口）。
        if row.get("residual_digest"):
            key = _key(str(row["type"]), str(row["ref_id"]))
            active_same = any(
                _key(it["type"], it["ref_id"]) == key and not it.get("resolved_at")
                for it in pool["items"]
            )
            if not active_same:
                last_resolved = next(
                    (
                        it for it in reversed(pool["items"])
                        if _key(it["type"], it["ref_id"]) == key and it.get("resolved_at")
                    ),
                    None,
                )
                if last_resolved is not None and (
                    last_resolved.get("residual_digest") == row["residual_digest"]
                ):
                    churn_suppressed += 1
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
        # 圖影響一句話跟著項目走（L16）；collector 沒算出來就維持缺席。
        if row.get("graph_impact"):
            item["graph_impact"] = str(row["graph_impact"])
        if row.get("residual_digest"):
            item["residual_digest"] = str(row["residual_digest"])

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

    watch_woken, watch_counts = _check_event_watches(pool, stamp=stamp)

    return {
        "added": added,
        "reactivated": reactivated,
        "waiting_refreshed": refreshed,
        "source_cleared": cleared,
        "source_returned": uncleared,
        "system_internal_retired": system_internal_retired,
        "watch_woken": watch_woken,
        "watch_counters": watch_counts,
        "churn_suppressed": churn_suppressed,
        "active": len(active_items(pool)),
    }


def _check_event_watches(pool: dict[str, Any], *, stamp: str) -> tuple[int, dict]:
    """Event Watch T0＋T1 檢查（fail-soft）：fired watch 把對應 pq2 項的
    waiting_on 翻回「等你決定」。喚醒是簿記，不自動 go（見 engine_b/event_watch.py）。"""

    try:
        from engine_b import event_watch
        from engine_b.leads import load as load_leads

        data = event_watch.load_watches()
        if not data["watches"]:
            return 0, {}
        try:
            leads = load_leads()["leads"]
        except Exception:
            leads = {}
        fired = event_watch.check_watches(data, leads=leads)
        woken = 0
        for watch in fired:
            n = int(watch["wake_pq2"])
            item = next(
                (it for it in pool["items"]
                 if it["n"] == n and not it.get("resolved_at")),
                None,
            )
            if item is not None and (item.get("waiting_on") or item.get("deferred_at")):
                prior = dict(item.get("waiting_on") or {})
                item.pop("waiting_on", None)
                item.pop("deferred_at", None)
                item["watch_wake"] = watch.get("woken_by")
                pool["log"].append({
                    "at": stamp,
                    "n": n,
                    "type": item["type"],
                    "ref_id": item["ref_id"],
                    "verb": "watch_wake",
                    "reason": f"event watch {watch['watch_id']} 觸發（{watch['kind']}）",
                    "receipt": json.dumps(watch.get("woken_by") or {}, ensure_ascii=False),
                    "prior_waiting_on": prior,
                })
                woken += 1
            event_watch.consume_fired(data, watch["watch_id"])
        event_watch.save_watches(data)
        return woken, event_watch.counters(data)
    except Exception:
        # watch 檢查失敗不阻斷 sync；缺席時計數器不出現即是訊號。
        return 0, {}


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
        dispatch_in_flight = item.get("dispatch_status") in {
            "queued", "researching", "awaiting_approval",
        }
        if dispatch_in_flight:
            # Collector 不再產出 row，不能覆蓋 work order 自己更強的 current-state
            # authority。特別是 awaiting_approval 代表已知還有 exact gate；若此時標成
            # 「很可能完成，可 drop」，會直接把尚未寫入的 graph／ledger 修正藏掉。
            if item.get("source_cleared"):
                prior = dict(item.pop("source_cleared"))
                pool["log"].append({
                    "at": stamp,
                    "n": item["n"],
                    "type": item["type"],
                    "ref_id": item["ref_id"],
                    "verb": "source_returned",
                    "reason": "pq1 work order 尚在進行或等待 exact gate，撤銷完成候選標記",
                    "receipt": item.get("dispatch_receipt"),
                    "prior_source_cleared": prior,
                })
                returned += 1
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


def _ra_graph_impact(payload: Mapping[str, Any]) -> str:
    """一句話回答「核准這個 RA 對圖的影響是什麼」（2026-08-31 使用者要求）。

    從凍結 payload 的 extraction_json 數 nodes／edges／claims 並列 origin＋tier。
    解析失敗回空字串（fail-soft：影響行缺席，密度契約其餘不變）。
    """

    try:
        n_nodes = n_edges = n_claims = 0
        origins: list[str] = []
        for doc in payload.get("documents") or []:
            raw = doc.get("extraction_json")
            ex = json.loads(raw) if isinstance(raw, str) else (raw or {})
            n_nodes += len(ex.get("nodes") or [])
            n_edges += len(ex.get("edges") or [])
            n_claims += len(ex.get("claims") or [])
            src = ex.get("source_doc") or {}
            origin = str(src.get("origin_entity") or "").strip()
            tier = src.get("evidence_tier")
            if origin:
                origins.append(f"{origin}（tier {tier}）" if tier else origin)
        if not (n_nodes or n_edges or n_claims):
            return ""
        parts = [f"+{n_nodes} 節點、{n_edges} 邊、{n_claims} claims"]
        if origins:
            parts.append("來源：" + "、".join(dict.fromkeys(origins)))
        return "｜".join(parts)
    except Exception:
        return ""


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
            row: dict[str, Any] = {
                "type": "ra_admission",
                "ref_id": action_id,
                "title": str(title),
                "hint": handoff_hint,
                "source": "research_action",
            }
            impact = _ra_graph_impact(action.get("payload") or {})
            if impact:
                row["graph_impact"] = impact
            rows.append(row)
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


def _only_system_internal_blockers(blockers: Any) -> bool:
    """是否只有不該進 pq2 的系統內部狀態。

    ``system_internal`` 與 ``awaiting_external`` 對使用者都不需要立即決定，
    但前者依 registry 契約「不該呈現為待辦」。先前兩者共用
    ``_derive_waiting_on``，導致 stale context 等系統狀態永久躺在「等事件」。
    """

    codes = [str(b) for b in blockers if isinstance(b, str)]
    if not codes:
        return False
    try:
        from decision_lab.blockers import get_blocker_registry

        grouped = get_blocker_registry().classify(codes)
    except Exception:
        return False
    return bool(grouped["system_internal"]) and not (
        grouped["user_decision"] or grouped["awaiting_external"]
    )


def collect_from_decisions() -> list[dict[str, Any]]:
    """Fail-soft 外皮，維持既有呼叫面；健康狀態請改用 collect_all_with_health。"""

    return _fail_soft(_collect_decision_rows)


def _dispatchable_cohorts(items: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    """哪些 cohort 的最新 decision **真的**帶得動 `dispatch`。

    `REVIEW` 有兩種成因，但先前的 hint 只寫得出一種：
    coverage 還有 blocker（有 bounded gap work order，該 `dispatch`），
    與 coverage 已清空、REVIEW 純粹來自凍結 context 過期（沒有 work order，
    該 `reassess`）。舊 hint 一律寫「核准 bounded gap research」，把後者誤呈現成
    「存在可 dispatch 的研究缺口」——使用者照著下 `go`，`dispatch` 拒絕（沒有
    work order），`resolve --verb go` 也拒絕（decision_review 不得 bare go），
    看起來像死結。2026-08-26 由本機 Codex 與 Claude Code 各自獨立撞到同一處。

    這是 L12 的形狀：一個表示（`REVIEW` ＋ 單一 hint）承載兩種語意，下游被迫二選一。
    修法是先分開再各自給正確指示，不是放寬任一邊的判定。

    讀不到 store 時回空集合——此時 hint 退回「兩種都寫」的保守版本，
    仍然可執行，不會謊報某條路可走。
    """

    cohort_ids = [
        str(item.get("cohort_id") or "")
        for item in items
        if str(item.get("cohort_id") or "").startswith("dc_")
    ]
    if not cohort_ids:
        return frozenset()
    try:
        from decision_lab.bootstrap import open_default_store

        store = open_default_store()
    except Exception:  # noqa: BLE001 — 取不到 store 只降級 hint，不阻斷 sync
        return frozenset()
    try:
        return frozenset(
            cohort_id
            for cohort_id in cohort_ids
            if store.latest_research_work_order(cohort_id) is not None
        )
    except Exception:  # noqa: BLE001
        return frozenset()
    finally:
        store.close()


def _decision_review_hint(
    ref: str,
    dispatchable: frozenset[str],
    blockers: Sequence[str] = (),
) -> str:
    """逐項說出「這一筆現在該做什麼」。

    ⚠ 只分 dispatch／reassess 兩類仍然不夠。2026-08-26 實測：[223] co:lumentum
    沒有 work order（所以不是 dispatch），但 reassess **跑過之後仍是 REVIEW**——
    因為它的 blocker 是 `financial_resilience_corroboration_incomplete`，
    那要靠補證據，不是重跑一次評估。只寫「請跑 reassess」會讓人跑第二次然後
    再問一次「那我到底要下什麼」。

    所以非 dispatchable 的分支必須把 **blocker 本身**寫出來：reassess 只在
    REVIEW 純粹來自 context 過期時有用；有實質 blocker 時，要動的是那些 blocker。
    """

    if ref in dispatchable:
        return "coverage 仍有 blocker：go 會 dispatch 回 pq1 做 bounded research，完成後才 reassess"
    # 哪些 blocker 真的需要人動手，唯一權威是 config/decision_blockers.json 的
    # `resolution_mode`（`decision_lab.blockers` 是唯一 loader）。
    #
    # ⚠ 這裡原本手寫了一組 stale_only 清單——那是把一個已有 SSOT 的分類複製第二份，
    # 而複製品立刻就錯了：2026-08-26 實測 [220] co:axt 的
    # execution_fx_missing／holdings_unavailable／portfolio_leverage_unavailable
    # 被誤報成「要補證據／研究」，但 registry 早已把它們標為 system_internal／
    # awaiting_external，而該項實際上只要 reassess 就從 REVIEW 變成 NO ACTION。
    # 判準與 L15 一致：分類是語意問題，但它已經被登記成 deterministic 資料，
    # 就該去讀它，不要另外猜一份。
    from decision_lab.blockers import describe_blocker

    substantive = sorted(
        code
        for code in {str(b) for b in blockers if b}
        if getattr(describe_blocker(code), "resolution_mode", "user_decision")
        == "user_decision"
    )
    if substantive:
        # ⚠ 這裡曾寫「沒有 work order，go 不成立」——與 dispatch 實作直接矛盾：
        # `todo dispatch` 對無 work order 的項目會 reassess 刷新 context，仍有實質
        # blocker 就以 assessment_gap ref 排入 pq1 並附研究範圍（outcome=
        # queued_assessment_gap）。使用者的介面就是一個 go（2026-08-30 定案）；
        # 「大項」只是研究範圍較大，不是另一個動詞。
        return (
            "go（大項）＝reassess 後以 assessment_gap 排入 pq1，研究範圍："
            + "、".join(substantive)
            + "。產出為 assessment／研究包，完成後 reassess 以新 decision receipt 結案"
        )
    return (
        "coverage 已無 blocker，REVIEW 來自凍結 context 過期——"
        "不是 dispatch，請跑 `decision_lab reassess <cohort_id> --intent <原 intent>`，"
        "下次 sync 會自動結案"
    )


def _decision_review_title(
    label: str,
    *,
    weakest_axis: str | None,
    sheet_only: bool = False,
) -> str:
    """研究缺口項目的標題：指名補哪一檔的哪一軸。

    先前是 `f"{action} — {label}"`，也就是「REVIEW — co:coherent」——它說了狀態卻
    沒說成因，使用者看到只能再點進去查一次。最弱軸就是排序的瓶頸，也是提高排序的
    唯一路徑，所以它才是這一列該講的事。

    `sheet_only` 與軸缺失時退回「複查」措辭：那些項目本來就不是研究缺口，硬套研究
    措辭會讓它們看起來需要補證據。
    """
    if sheet_only or not weakest_axis:
        return f"複查 — {label}"
    from decision_lab.sizing import AXIS_RESEARCH_PROMPT

    prompt = AXIS_RESEARCH_PROMPT.get(weakest_axis)
    if not prompt:
        # 未登記的軸不猜措辭，但仍要指名它——沉默會讓新增的軸悄悄退回舊格式。
        return f"{label}：補 {weakest_axis}"
    return f"{label}：{prompt}"


def _residual_digest(user_codes: Iterable[str], missing_data: Iterable[str]) -> str:
    """corroboration 殘餘缺口的 content key。

    churn 的機械成因（2026-08-31 定案）：誠實 assessment 永遠列 missing_data →
    `corroborated + missing_data` 依規則掛 `{axis}_corroboration_incomplete` →
    收集端用固定軸文案鑄同標題新號（[294]→[308]）。使用者看到的是「go 了又重生」，
    實際上缺口每輪都在變小，只是標題不說。修法＝以**殘餘內容**當 key：內容沒變的
    不因 resolve 而復活；內容變了才鑄新號，且標題直接講新缺口。
    """

    import hashlib

    payload = json.dumps(
        [sorted(str(c) for c in user_codes), sorted(str(m) for m in missing_data)],
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _corroboration_only_user_codes(blockers: Any) -> list[str] | None:
    """若使用者要決定的 blocker **全部**是 `_corroboration_incomplete` 類（誠實殘餘），
    回傳那些 code；否則 None（有真缺口，照舊 cohort-keyed 行為）。"""

    codes = [str(b) for b in blockers if isinstance(b, str)]
    if not codes:
        return None
    try:
        from decision_lab.blockers import get_blocker_registry

        grouped = get_blocker_registry().classify(codes)
    except Exception:
        return None
    user_codes = list(grouped.get("user_decision") or ())
    if user_codes and all(c.endswith("_corroboration_incomplete") for c in user_codes):
        return user_codes
    return None


def _collect_decision_rows() -> list[dict[str, Any]]:
    """需要使用者注意的 Engine D 決策項（`attention == "REVIEW"`）→ 複查待辦。

    需要本機 private Decision Store 與外部 authority；失敗會往上拋，由呼叫端
    決定是 fail-soft 還是記錄成「來源不健康」。
    """
    from mcp_server.decision_tools import get_decision_brief_core

    brief = get_decision_brief_core()
    rows: list[dict[str, Any]] = []
    items = brief.get("items") or []
    dispatchable = _dispatchable_cohorts(items)
    for item in items:
        # U7 之前是 `recommended_action not in {"NO ACTION", ""}`；四動作已移除，
        # 現在唯一的判準是這一檔今天要不要人看（見 decision_lab.models.ATTENTION_STATES）。
        if str(item.get("attention") or "") != "REVIEW":
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
        blockers = item.get("blockers") or []
        material_event = str(item.get("evidence_delta") or "none") in {
            "material", "positive", "negative"
        }
        label = company if company not in {"", "unknown", "unresolved"} else (
            company_hint or ticker or "unknown"
        )
        missing = [
            str(m) for m in (item.get("weakest_missing_data") or []) if str(m).strip()
        ]
        title = _decision_review_title(
            label,
            weakest_axis=item.get("weakest_axis"),
            sheet_only=bool(item.get("sheet_only")),
        )
        hint = (
            _decision_review_hint(ref, dispatchable, blockers)
            if not item.get("sheet_only") else ""
        )
        corroboration_codes = (
            None if item.get("sheet_only")
            else _corroboration_only_user_codes(blockers)
        )
        if corroboration_codes:
            # 誠實殘餘類：標題直接講**當前**缺口，不用固定軸文案——使用者才看得出
            # [308] 問的其實是新問題，不是 [294] 重生（churn 修法第一半）。
            first = missing[0] if missing else "（missing_data 未列明）"
            title = f"{label}：殘餘缺口——{first[:70]}"
        if missing and hint:
            hint = "當前 missing_data：" + "；".join(m[:60] for m in missing[:3]) + \
                f"（共 {len(missing)} 項）｜" + hint
        row = {
            "type": "sheet_only_holding" if item.get("sheet_only") else "decision_review",
            "ref_id": ref,
            "title": title,
            **({"hint": hint} if hint else {}),
            "source": "decision_lab",
        }
        if corroboration_codes:
            row["residual_digest"] = _residual_digest(corroboration_codes, missing)
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
        # 純 system_internal 狀態不是 pq2，也不是外部事件。仍回傳給 sync，讓
        # 既有 stable item 留下 deterministic retirement audit；新狀態則不建 item。
        # material evidence 優先，不能因同時有 stale 診斷而被吞掉。
        if not item.get("sheet_only") and not material_event and \
                _only_system_internal_blockers(blockers):
            row["system_internal_only"] = True
            rows.append(row)
            continue
        # 若這個決策的所有 blocker 都不需要使用者決定（純粹在等世界產生新資料），
        # 就直接帶著推導出的等待理由入池，不佔決策注意力。保守規則：只要有一個
        # blocker 需要人決定就照舊進決策佇列。
        waiting = (
            None if material_event else _derive_waiting_on(blockers)
        )
        if waiting:
            row["waiting_on"] = waiting
        rows.append(row)
    # Engine D 也可能因 portfolio authority 全域失效而要求 REVIEW，這時沒有
    # cohort item（例如 Google Sheet holdings 完全讀不到）。這仍是需要使用者
    # 處理的 pq2，不能因 items=[] 就從統一待辦池消失。
    if brief.get("action_needed") and not items:
        blockers = sorted(str(b) for b in (brief.get("blockers") or []) if b)
        reason = str(brief.get("reason") or "Engine D 全域狀態需要複查")
        ref = "global:" + ("|".join(blockers) or "review")
        rows.append({
            "type": "decision_review",
            "ref_id": ref,
            "title": f"複查 — {reason}",
            "hint": "修復全域 authority blocker 後重跑 decision_lab today",
            "source": "decision_lab",
        })
    return rows


def collect_all(*, include_decisions: bool = True) -> list[dict[str, Any]]:
    return collect_all_with_health(include_decisions=include_decisions).rows


def _attach_go_authorization(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把授權邊界掛到每一列，讓 collector 不必各自記得（L16）。

    掛在這裡而不是各個 collector：新增 collector 時不會有人記得補這兩個欄位，
    而漏掉時的預設會是「沒有邊界」——最危險的那個方向。
    """

    for row in rows:
        row.update(go_authorization(str(row.get("type") or "")))
    return rows


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


# 待辦來源的唯一登記表。`collect_all_with_health` 與測試都由它導出，
# 因為手維護兩份清單的後果已經發生過：測試逐一 monkeypatch collector 名稱，
# 新增第 5、6 個 collector 時沒人記得更新，於是那兩個未被 patch 的 collector
# **讀到真實 private runtime 狀態**，測試從此隨 daily 產出漂移而恆紅
# （2026-08-13 發現）。恆紅的測試會讓整套 suite 失去鑑別力——下次真的壞掉時
# 是「2 failed」，沒人分得出差別（L13：成功與失敗在同一個訊號上同形）。
#
# 以「屬性名」而非函式物件登記，是為了讓 monkeypatch 能生效：collector 在
# 呼叫當下才由模組 globals 解析。
SOURCE_COLLECTORS: tuple[tuple[str, str], ...] = (
    ("research_actions", "_collect_research_action_rows"),
    ("source_trace", "_collect_source_trace_rows"),
    ("lifecycle", "_collect_lifecycle_rows"),
    ("engine_c_observations", "_collect_engine_c_observation_rows"),
    ("thesis_mutations", "_collect_thesis_mutation_rows"),
    ("decisions", "_collect_decision_rows"),
)


def collect_all_with_health(*, include_decisions: bool = True) -> SourceCollection:
    rows: list[dict[str, Any]] = []
    healthy: set[str] = set()
    sources: list[tuple[str, Any]] = [
        (name, globals()[attr])
        for name, attr in SOURCE_COLLECTORS
        if include_decisions or name != "decisions"
    ]
    for name, collector in sources:
        try:
            collected = collector()
        except Exception:
            # 失敗就是失敗：不進 healthy，該來源的項目本輪一律不判定完成。
            continue
        rows += collected
        healthy.add(name)
    return SourceCollection(
        rows=_attach_go_authorization(rows), healthy=frozenset(healthy)
    )


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
    # 決策行（AGENTS.md 2026-08-29 定案）：第一行就要能決定要不要展開——
    # 做什麼（title）＋ go 授權什麼／不含什麼（GO_AUTHORIZATION，L16：分類跟著資料走）。
    # 已 dispatch 的項目不吃 go，不重複授權邊界。
    line = f"  [{item['n']}] {item['title']}{flag}"
    if not item.get("dispatch_status"):
        scope = go_authorization(str(item.get("type") or ""))
        line += f"\n        ↳ go＝{scope['go_authorizes']}；不含{scope['go_excludes']}"
        # 圖影響一句話（2026-08-31 使用者要求）：核准了什麼、對圖加了什麼，
        # 不展開密度欄位也能決定。sync 時由凍結 payload 計算（L16：跟著資料走）。
        impact = str(item.get("graph_impact") or "").strip()
        if impact:
            line += f"\n        ↳ 圖影響：{impact}"
    # decision_review 的區段標題只寫得出一種成因（見 _dispatchable_cohorts）。
    # 逐項 hint 才知道這一筆該 dispatch 還是該 reassess——不顯示等於沒有，
    # 使用者只會看到區段標題然後下錯 verb（2026-08-26 實測）。
    # 其他類型的 hint 是密度契約的內容（TL;DR），先前在 CLI 完全不顯示＝資訊遺失；
    # 決策行契約是改閱讀順序不減密度，故一併收在決策行下面。
    hint = str(item.get("hint") or "").strip()
    if hint and not item.get("dispatch_status"):
        line += f"\n        ↳ {hint}"
    return line


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
    # explicit waiting_on 是使用者／已完成研究對「下一個可執行觸發」的較新判斷，
    # 必須優先於舊 dispatch_status。否則一個已確認只能等 filing 的 work order，
    # 仍會因先前的 awaiting_approval 被錯列成「等人工 gate」。
    waiting = [i for i in rest if i.get("waiting_on")]
    rest = [i for i in rest if i not in waiting]
    gated = [i for i in rest if i.get("dispatch_status") == "awaiting_approval"]
    in_flight = [
        i for i in rest if i.get("dispatch_status") in {"queued", "researching"}
    ]
    rest = [i for i in rest if i not in gated and i not in in_flight]
    deciding = rest

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
            wc = result.get("watch_counters") or {}
            watch_line = ""
            if wc:
                watch_line = (
                    f"；watch {wc.get('active', 0)} 筆"
                    f"（T1 {wc.get('t1_date', 0)}／T0 {wc.get('t0_passive', 0)}"
                    f"／可輪詢 {wc.get('t2_pollable', 0)}"
                    f"，本輪喚醒 {result.get('watch_woken', 0)}）"
                )
            print(
                f"（新增 {result['added']}，目前 {result['active']} 項待辦"
                f"{migration}{watch_line}）\n"
            )
            print(_render(pool))
        return 0

    if args.command == "resolve":
        failures = 0
        decision_store = None
        try:
            for raw in args.numbers:
                try:
                    # `go` 對 decision_review 是全函數：由系統決定下一步是
                    # dispatch、reassess 還是排入 assessment-gap pq1，
                    # 使用者不必自己分辨（見 advance_decision_review）。
                    item = get(pool, int(raw))
                    if (
                        args.verb == "go"
                        and item["type"] == "decision_review"
                        and item.get("dispatch_status") not in {"completed", "parked"}
                    ):
                        if decision_store is None:
                            from decision_lab.bootstrap import open_default_store

                            decision_store = open_default_store()
                        outcome = advance_decision_review(
                            pool, int(raw), store=decision_store
                        )
                        print(f"✓ [{raw}] → go（{outcome['outcome']}）")
                        scope = outcome.get("scope")
                        if scope:
                            print(f"    研究範圍：{'、'.join(scope)}")
                        continue
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
        finally:
            if decision_store is not None:
                decision_store.close()
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
