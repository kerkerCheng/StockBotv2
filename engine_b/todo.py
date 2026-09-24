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
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "1"

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POOL_PATH = _ROOT / "library" / "leads" / "todo_pool.json"

# 項目類型 → 該類型的 `go` 代表什麼動作（type-aware dispatch 的權威對照）。
# ⚠ **2026-09-22（Phase 0 Step 0a.4）：`decision_review` 與 `sheet_only_holding` 改成 legacy 標記。**
# 兩個 kind **不刪 key**——池裡的歷史項目仍是這兩個 type，讀取端必須認得（否則舊項目會變成
# 「查不到了」，而那不是合法 lifecycle，INV-3）；`GO_AUTHORIZATION` 的鍵也由測試斷言與這裡一致。
# 停的是**鑄號**：`SOURCE_COLLECTORS` 不再登記 decisions collector，所以不會再有新項目進來。
ITEM_TYPES: dict[str, str] = {
    "lead_research": "（legacy）已移回自動 pq1，不再建立新項目",
    "ra_admission": "核准入圖（apply_research_action）",
    "decision_review": "（legacy）機制退役（Phase 0／G12），不再建立新項目",
    "source_trace_review": "核准人工 authority 後做 bounded 追源；go 只 dispatch 回 pq1",
    "thesis_lifecycle": "本機複查 thesis 並手動更新 lifecycle.json",
    "sheet_only_holding": "（legacy）機制退役（Phase 0），不再建立新項目；Sheet 有而敘事沒有的持股改列候選板「已持有、缺敘事」（Phase 3）",
    "engine_c_observation": "核准把人工觀測寫入 Engine C append-only ledger",
    "thesis_mutation": "核准 thesis lifecycle 變更（revise／retire／watch）",
    "watch_decision": ("假設型等沒有自己複查週期的 watch 到期、沒對照到：續等（resolve <n> --verb pending --until <日期>）、"
                       "放棄（drop）；研究後發現已發生 → go（receipt 帶 outcome:touched＋研究結果、--quote 原文）。"
                       "thesis／讀圖的反證到期不在這裡——併進 thesis 複查與節點重讀"),
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
    "decision_review": ("（legacy）不再建立新項目", "任何 authority mutation"),
    "source_trace_review": ("bounded 追源（dispatch 回 pq1）", "提高 evidence tier 與入圖"),
    "thesis_lifecycle": ("本機複查該 thesis", "自動改 lifecycle 或入圖"),
    "sheet_only_holding": ("（legacy）不再建立新項目", "任何部位動作"),
    "engine_c_observation": ("寫入 Engine C append-only ledger", "入圖與 thesis mutation"),
    "thesis_mutation": ("該筆 thesis lifecycle 變更", "入圖與 live"),
    # Phase 1 Step 1.7（定案 #4）：永不列入常規授權——它真正要你答的是續等或放棄，自動 go 會讓重問消失。
    "watch_decision": ("記下研究結論「條件已被觸及」（附研究結果與原文）→ 交給假設對照接手（watch 回 fired）",
                       "任何 authority mutation（入圖、Engine C 判讀、thesis mutation、live）；"
                       "研究本身不在 go 裡（要研究就在互動 session 說）；條件沒被觸及不得 go（續等或 drop）"),
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
    if item_type in {"decision_review", "sheet_only_holding"}:
        # ⚠ 2026-09-23（Phase 0 Step 0b.4）：兩個 legacy kind 的 go 語意（dispatch／reassess／
        # decision receipt）隨 decision_lab 研究側退役。池裡若還有歷史項目只能 drop。
        raise TodoError(f"{item_type} 是 legacy 型（Phase 0 機制退役）：不得 go；歷史項目請 drop")

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

    if item_type == "watch_decision":
        raise TodoError("watch_decision 的 go 由 resolve 依 watch 狀態驗證（_resolve_watch_decision），不走這裡")

    if not receipt.strip():
        raise TodoError(f"{item_type} go 必須附 underlying authority receipt")
    fields = _receipt_fields(receipt)

    if item_type == "ra_admission":
        # ⚠ 2026-09-23（Phase 0 Step 0b.4）：receipt 不再帶 `cohort`——Decision cohort handoff
        # 隨 decision_lab 研究側退役；入圖本身已 durable，pq2 授權的就是入圖。
        if set(fields) != {"action", "digest", "commit"}:
            raise TodoError("ra_admission receipt 必須含 action、digest、commit")
        if fields["action"] != item["ref_id"]:
            raise TodoError("ra_admission receipt 的 action 不符 exact pq2 item")
        if not _SHA256_RE.fullmatch(fields["digest"]):
            raise TodoError("ra_admission receipt digest 必須是 64 位 sha256")
        if fields["commit"] != "not_required" and not _GIT_COMMIT_RE.fullmatch(fields["commit"]):
            raise TodoError("ra_admission receipt commit 必須是 40 位 Git SHA 或 not_required")
        completion = item.get("completion_authority") or {}
        if (
            completion.get("action_digest") != fields["digest"]
            or completion.get("commit") != fields["commit"]
        ):
            raise TodoError("請用 todo complete-ra 驗證 apply／publish 後再結案")
        return

    if item_type == "thesis_lifecycle":
        if set(fields) != {"lifecycle", "commit"}:
            raise TodoError("thesis_lifecycle receipt 必須含 lifecycle 與 commit")
        if fields["lifecycle"] != item["ref_id"] or not _GIT_COMMIT_RE.fullmatch(fields["commit"]):
            raise TodoError("thesis_lifecycle receipt 必須對應 exact thesis 與 40 位 Git SHA")
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
    quote: str | None = None,
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
    if (until or trigger or event_type) and verb != "pending":
        raise TodoError("until／trigger／event-type 只適用於 pending")
    if item["type"] == "watch_decision":
        if _skip_receipt_validation:
            raise TodoError("watch_decision 沒有 complete-* 入口")
        return _resolve_watch_decision(pool, item, verb, reason=reason, receipt=receipt, quote=quote, at=at,
                                       until=until, trigger=trigger, event_type=event_type)
    if quote:
        raise TodoError("--quote 只用在 watch_decision 的 go（outcome:touched 的原文）")
    if verb == "go" and not _skip_receipt_validation:
        # 只有已完成 underlying 寫入的 complete-* 入口才略過——它自己就是收據來源。
        _validate_go_receipt(item, receipt)
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
        if item["type"] == "thesis_lifecycle" and verb in ("go", "drop"):
            _mark_disproof_handled(item, verb, stamp)
    pool["log"].append({
        "at": stamp, "n": item["n"], "type": item["type"],
        "ref_id": item["ref_id"], "verb": verb, "reason": reason or None,
        "receipt": receipt or None,
    })
    return item


_WATCH_DECISION_EVIDENCE_KEYS = frozenset({"lead", "report", "watch"})
_WATCH_DECISION_OUTCOMES = ("touched", "not_touched")
#: report 收據只收研究產出所在的目錄（R2-b NB-5：`report:AGENTS.md` 這種「存在但不是研究結果」的檔案不算）
_WATCH_DECISION_REPORT_ROOTS = ("docs/reports/", "thesis/", "library/private/")


def _validate_watch_decision_go(receipt: str, *, quote: str | None, watch: Mapping[str, Any]) -> dict[str, str]:
    """`watch_decision` 的 go＝「研究結論：條件已被觸及」（R2-b B2）。收據要**指得回這次到期之後的研究結果**：

    - `outcome:touched` 必填（`not_touched` 不是 go：續等或 drop）；`--quote` 必填（文件逐字；L18）。
    - 至少一項 `lead:<id>`（leads store 有、且最後動作不早於這次到期日）／`report:<路徑>`（在
      `_WATCH_DECISION_REPORT_ROOTS` 之下、檔案存在）／`watch:<id>`（不是自己、非 consumed、建立不早於到期日）。
    """
    if not receipt.strip():
        raise TodoError('watch_decision 的 go 必須附研究結論與結果：--receipt "outcome:touched;report:<路徑>" '
                        '--quote "<原文>"（批次語法的 bare go 一律拒絕；條件沒被觸及就續等或 drop）')
    fields = _receipt_fields(receipt)
    unknown = set(fields) - _WATCH_DECISION_EVIDENCE_KEYS - {"outcome"}
    if unknown:
        raise TodoError(f"watch_decision go receipt 不認得的欄位：{sorted(unknown)}（只收 outcome／lead／report／watch）")
    outcome = fields.get("outcome")
    if outcome not in _WATCH_DECISION_OUTCOMES:
        raise TodoError("watch_decision go receipt 必須帶 outcome:touched（研究結論：條件已被觸及）")
    if outcome == "not_touched":
        raise TodoError("條件沒被觸及不是 go：續等用 resolve <n> --verb pending --until <日期>，放棄用 --verb drop")
    if not set(fields) & _WATCH_DECISION_EVIDENCE_KEYS:
        raise TodoError("go 必須附研究結果：lead:<id>／report:<路徑>／watch:<id>")
    if not str(quote or "").strip():
        raise TodoError("outcome:touched 必須附 --quote（文件逐字；L18：標籤要指得回原文）")
    since = str(watch.get("expires") or "")
    if "lead" in fields:
        from engine_b import leads as leads_mod

        lead = (leads_mod.load().get("leads") or {}).get(fields["lead"])
        if lead is None:
            raise TodoError(f"watch_decision receipt 的 lead 不存在：{fields['lead']}")
        # 只認 first_seen：追源重排會改寫 decided_at，舊 lead 會被騙成「剛研究過」（R2-b 重審 NB2-3）
        first_seen = str(lead.get("first_seen") or "")
        if first_seen[:10] < since:
            raise TodoError(f"receipt 的 lead {fields['lead']} 首次出現 {first_seen[:10] or '（無）'} 早於這次到期 {since}"
                            "——要指研究這次到期時找到的產出（或改附 report:）")
    if "report" in fields:
        rel = fields["report"].replace("\\", "/")
        path = (_ROOT / rel).resolve()
        if (not rel.startswith(_WATCH_DECISION_REPORT_ROOTS) or not path.is_relative_to(_ROOT.resolve())
                or not path.is_file()):
            raise TodoError(f"watch_decision receipt 的 report 必須是 {'／'.join(_WATCH_DECISION_REPORT_ROOTS)} "
                            f"之下存在的檔案：{fields['report']}")
        # 報告要寫到這個 watch（NB2-3：lifecycle.json、兩個月前的報告都會通過「存在」這一關）
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            body = ""
        if str(watch.get("watch_id")) not in body:
            raise TodoError(f"receipt 的 report 內文沒有提到 {watch.get('watch_id')}——研究結果要寫明它回答的是哪一個等待")
    if "watch" in fields:
        from engine_b import event_watch

        if fields["watch"] == watch.get("watch_id"):
            raise TodoError("receipt 的 watch 不能是這個到期的 watch 自己")
        new = next((w for w in event_watch.load_watches().get("watches") or []
                    if w.get("watch_id") == fields["watch"]), None)
        if new is None or new.get("status") == "consumed" or str(new.get("created_at") or "")[:10] < since:
            raise TodoError(f"receipt 的 watch {fields['watch']} 必須存在、未 consumed、建立不早於這次到期 {since}")
    return fields


def watch_id_of(item: Mapping[str, Any]) -> str:
    """`watch_decision` 的 ref_id 是 `<watch_id>@<expires>`（每個到期事件恰好一個編號）。"""
    return str(item.get("ref_id") or "").split("@", 1)[0]


def _watch_decision_stale(watch: Mapping[str, Any] | None, event_expires: str) -> str | None:
    """這個編號對應的到期事件還在不在（R2-b NB-3）。回傳過時的理由，還在就回 None。"""
    from engine_b import event_watch

    if watch is None:
        return "watch 已不在 registry"
    if watch.get("expiry_resolution"):
        return f"這次到期已處置過（{watch['expiry_resolution'].get('kind')}）"
    if event_expires and str(watch.get("expires")) != event_expires:
        return f"watch 的到期日已變成 {watch.get('expires')}（續等過）"
    if watch.get("status") == "active" and event_watch.past_expiry(watch):
        return None
    if watch.get("status") != "expired":
        return f"watch 現況 {watch.get('status')}"
    return None


def _resolve_watch_decision(pool: dict[str, Any], item: dict[str, Any], verb: str, *, reason: str,
                            receipt: str, quote: str | None, at: str | None, until: str | None,
                            trigger: str | None, event_type: str | None) -> dict[str, Any]:
    """`watch_decision` 的三個動詞（Phase 1 Step 1.7；R2-b 修訂）——**等待只住 registry，不得同時掛在 pq2 的 `waiting_on`**。

    - `pending --until <日期>`＝續等：watch 以新到期日回 active（歷史附加），這個編號結案（`resolution=renewed`）、
      receipt 記新到期日。bare `pending`、`--trigger`、`--event-type` 拒收（L12）；來源已不是現行時拒收（NB-4）。
    - `drop`：watch 記 `expiry_resolution: dropped`。
    - `go`：研究結論「條件已被觸及」（`_validate_watch_decision_go`）→ `event_watch.record_touched`，接手路徑與 judge 同形（B2）。
    - 編號對應的到期事件已過時（watch 已處置／續等過／不在）→ 只准 `drop`，結案成 `stale_event`、不動 registry（NB-3）。
    ⚠ `_mark_source_cleared` 永不自動 resolve，所以結案在這同一個動作裡明確做。
    """
    from engine_b import event_watch

    stamp = at or _now()
    watch_id = watch_id_of(item)
    event_expires = str(item.get("ref_id") or "").partition("@")[2]
    data = event_watch.load_watches()
    watch = next((w for w in data["watches"] if w.get("watch_id") == watch_id), None)
    stale = _watch_decision_stale(watch, event_expires)
    if stale is not None:
        if verb != "drop":
            raise TodoError(f"編號 {item['n']} 對應的到期事件已過時：{stale}——只能 drop 結案（不動 registry）")
        return _close_watch_decision(pool, item, verb, resolution="stale_event", receipt=f"stale:{stale}",
                                     reason=reason, stamp=stamp)
    # 到期當天收集時 watch 還是 active——只標這一筆（NB-9：互動 resolve 不掃整份 registry）
    event_watch.mark_expired(data, only=watch_id)
    try:
        if verb == "pending":
            if trigger or event_type or not until:
                raise TodoError("watch_decision 的 pending 必須帶 --until <日期>：python -m engine_b.todo resolve "
                                f"{item['n']} --verb pending --until <日期>（續等住 registry，不在 pq2 掛等待；"
                                "批次語法帶不了日期；--trigger／--event-type 不適用）；要放棄就 drop")
            from engine_b.disproof import source_is_current

            if not source_is_current(watch):
                raise TodoError("來源已不是現行（memo 換版／thesis retired／讀圖已被取代）——這個條件沒有對象了，drop 即可")
            event_watch.renew(data, watch_id, until=until, n=item["n"])
            resolution, final_receipt = "renewed", f"renewed_until:{until}"
        elif verb == "drop":
            event_watch.resolve_expiry(data, watch_id, {"kind": "dropped", "n": item["n"],
                                                        "reason": reason or None})
            resolution, final_receipt = "drop", None
        else:
            _validate_watch_decision_go(receipt, quote=quote, watch=watch)
            from engine_b.disproof import source_is_current

            if not source_is_current(watch):
                # 續等已有這一道，go 是對稱面（R2-b 重審 NB2-1）：來源換版後判定觸及，沒有任何複查項目接得住
                raise TodoError("來源已不是現行（或 lifecycle 讀不到）——這個條件沒有對象了，drop 即可")
            event_watch.record_touched(data, watch_id, quote=str(quote), note=reason, n=item["n"], receipt=receipt)
            resolution, final_receipt = "go", receipt
    except (event_watch.EventWatchError, ValueError) as exc:
        raise TodoError(str(exc)) from exc
    event_watch.save_watches(data)
    return _close_watch_decision(pool, item, verb, resolution=resolution, receipt=final_receipt,
                                 reason=reason, stamp=stamp)


def _close_watch_decision(pool: dict[str, Any], item: dict[str, Any], verb: str, *, resolution: str,
                          receipt: str | None, reason: str, stamp: str) -> dict[str, Any]:
    item.pop("waiting_on", None)
    item.pop("deferred_at", None)
    item["resolved_at"] = stamp
    item["resolution"] = resolution
    item["reason"] = reason or None
    item["receipt"] = receipt
    pool["log"].append({"at": stamp, "n": item["n"], "type": item["type"], "ref_id": item["ref_id"],
                        "verb": verb, "reason": reason or None, "receipt": receipt})
    return item


#: `awaiting_approval` 的工單在等哪一個 pq2 編號。**結構化欄位，不是 receipt 字串。**
#: 過渡期仍會讀既有 receipt 裡的 `manual_todo:<n>`（那是人手寫的），但新寫入一律走這裡。
AWAITING_GATE_KEY = "awaiting_gate"

#: receipt 裡人手寫的舊式 pointer。只用於讀取既有資料，不是寫入格式。
_LEGACY_GATE_PATTERN = re.compile(r"manual_todo:(\d+)")


def gate_pointer(item: Mapping[str, Any]) -> dict[str, Any] | None:
    """這張工單在等哪個 pq2 編號？回傳 `{"n": int, "origin": ...}` 或 None。

    `origin` 誠實記錄這個 pointer 是**結構化欄位**還是**從舊 receipt 解析出來的**——
    後者是過渡相容，不該被當成同等可靠的紀錄（解析自由字串本來就會漏）。
    """

    structured = item.get(AWAITING_GATE_KEY)
    if isinstance(structured, Mapping) and structured.get("n") is not None:
        return {"n": int(structured["n"]), "origin": "structured"}
    if isinstance(structured, int):
        return {"n": int(structured), "origin": "structured"}
    match = _LEGACY_GATE_PATTERN.search(str(item.get("dispatch_receipt") or ""))
    if match:
        return {"n": int(match.group(1)), "origin": "legacy_receipt"}
    return None


def set_awaiting_gate(pool: dict[str, Any], n: int, gate_n: int | None) -> dict[str, Any]:
    """記錄／清掉這張工單在等的 pq2 編號。"""

    item = get(pool, n)
    if gate_n is None:
        item.pop(AWAITING_GATE_KEY, None)
        return item
    gate_n = int(gate_n)
    if gate_n == int(n):
        raise TodoError(f"[{n}] 不能等自己")
    get(pool, gate_n)  # 指不到的編號直接拋——pointer 必須解析得到（INV-4）
    item[AWAITING_GATE_KEY] = {"n": gate_n, "set_at": _now()}
    return item


def gated_items(pool: Mapping[str, Any]) -> list[dict[str, Any]]:
    """所有停在 `awaiting_approval` 的工單，附上它等的 gate 現況。

    三種結果，下一步完全不同——這正是原本被壓成同一個狀態的三件事：
    - `waiting`：pointer 指得到、那個編號還沒 resolve → 真的在等你，不必動。
    - `gate_resolved`：pointer 指得到、但那個編號**已經 resolve** → gate 沒了，
      工單卻還掛著。下一步是完成 pq1 checkpoint 拿 terminal receipt，不是直接收掉
      （2026-09-10 實測：兩張工單 reassess 後都浮出**不同的**新缺口）。
    - `no_pointer`：說不出在等誰 ＝ 沒有到期，也沒有人會叫醒它（INV-2／INV-4）。
    """

    by_n = {int(i["n"]): i for i in pool.get("items", []) if i.get("n") is not None}
    out: list[dict[str, Any]] = []
    for item in active_items(pool):
        if item.get("dispatch_status") != "awaiting_approval":
            continue
        pointer = gate_pointer(item)
        if pointer is None:
            state = "no_pointer"
            gate = None
        else:
            gate = by_n.get(pointer["n"])
            if gate is None:
                state = "no_pointer"
            elif gate.get("resolution"):
                state = "gate_resolved"
            else:
                state = "waiting"
        out.append({
            "n": int(item["n"]),
            "title": item.get("title"),
            "ref_id": item.get("ref_id"),
            "state": state,
            "gate_n": (pointer or {}).get("n"),
            "gate_origin": (pointer or {}).get("origin"),
            "gate_resolution": (gate or {}).get("resolution"),
            "gate_resolved_at": (gate or {}).get("resolved_at"),
            "dispatch_updated_at": item.get("dispatch_updated_at"),
        })
    return out


#: 常規授權不動的兩種項目：使用者明示 pending 的、與在等世界的（見 config/standing_authorization.json _doc）。
_STANDING_SKIP_DISPATCH = frozenset({"queued", "researching", "awaiting_approval", "completed", "parked"})


def standing_go_candidates(
    pool: Mapping[str, Any],
    *,
    authorization: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """常規授權（佇列段 2b）的成員與被跳過者。判準全部機械：

    - 類型在 `authorized`（config/standing_authorization.json 是唯一 SSOT）；
    - 不在 pq1 in-flight、沒有 terminal receipt；
    - **沒有** `deferred_at`（使用者明示 pending——常規授權不替使用者改決定）；
    - **沒有** `waiting_on`（在等世界——常規授權買的是注意力，不是讓事情發生）；
    - `source_trace_review` 的 hint 含付費字樣者跳過（付費取得永遠要 exact 金額核准）。

    ⚠ 2026-09-23（Phase 0 Step 0b.4）：原本還有 `decision_review` 的「go 會讓哪個數字變」判定
    （work order／user_decision blocker／brief 讀不到就跳過）；該 kind 隨 decision_lab 研究側退役，
    `config/standing_authorization.json` 早已把它列在 `never`（Step 0a.1）。
    """

    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for item in active_items(pool):
        item_type = str(item["type"])
        if not authorization.is_authorized(item_type):
            continue
        if item.get("dispatch_status") in _STANDING_SKIP_DISPATCH:
            continue
        # 先判「等世界」再判「使用者 pending」：`pending --trigger` 兩個欄位都會設，更具體的理由要先講。
        if item.get("waiting_on"):
            skipped.append({"n": item["n"], "reason": "在等世界（waiting_on）——常規授權買的是注意力，不是讓事情發生"})
            continue
        if item.get("deferred_at"):
            skipped.append({"n": item["n"], "reason": "使用者明示 pending（deferred_at）——常規授權不替使用者改決定"})
            continue
        tokens = authorization.skip_hint_tokens(item_type)
        text = f"{item.get('title') or ''}｜{item.get('hint') or ''}"
        if tokens and any(tok in text for tok in tokens):
            skipped.append({"n": item["n"], "reason": "hint 提及付費／訂閱——付費取得永遠要 exact 金額核准"})
            continue
        candidates.append(item)
    return candidates, skipped


def standing_go(
    pool: dict[str, Any],
    *,
    leads_path: Path | str | None = None,
    at: str | None = None,
    dry_run: bool = False,
    authorization: Any = None,
) -> dict[str, Any]:
    """段 2b 的 consumer：對常規授權類別執行「使用者本來會下的那個 go」，一個都不多。

    source_trace_review → `dispatch_source_trace_review`（requeue 回 pq1）。這是 pq2 既有的 go
    語意，本函式只是把「誰按的」從使用者換成 config——receipt 一樣、gate 一樣、不含入圖與 authority 寫入。
    ⚠ 2026-09-23（Phase 0 Step 0b.4）：`decision_review → advance_decision_review` 那條分支隨研究側退役。
    """

    from engine_b.leads import DEFAULT_LEADS_PATH

    if authorization is None:
        from engine_b import standing_authorization as sa

        authorization = sa.load()
    stamp = at or _now()
    candidates, skipped = standing_go_candidates(pool, authorization=authorization)
    result: dict[str, Any] = {
        "candidates": [int(it["n"]) for it in candidates], "skipped": skipped,
        "done": [], "failed": [], "dry_run": dry_run, "config": str(getattr(authorization, "path", "")),
    }
    if dry_run:
        return result
    for item in candidates:
        n = int(item["n"])
        item_type = str(item["type"])
        try:
            if item_type == "source_trace_review":
                outcome = dispatch_source_trace_review(pool, n, leads_path=leads_path or DEFAULT_LEADS_PATH, at=stamp)
                verb_outcome = "dispatched"
                receipt = str(item.get("dispatch_ref") or "")
            else:  # config 驗過封閉性，這裡理論上到不了
                raise TodoError(f"[{n}] 類型 {item_type} 在 authorized 卻沒有 consumer 分支")
        except Exception as exc:  # noqa: BLE001 — 單筆失敗不擋其餘，但要現形
            result["failed"].append({"n": n, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        pool["log"].append({
            "at": stamp, "n": n, "type": item_type, "ref_id": item["ref_id"],
            "verb": "standing_go",
            "reason": f"常規授權（{Path(str(getattr(authorization, 'path', ''))).name}）：{item_type} 的 go 只是注意力 gate；outcome={verb_outcome}",
            "receipt": receipt,
        })
        result["done"].append({"n": n, "type": item_type, "outcome": verb_outcome, "receipt": receipt})
    return result


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
            # ⚠ 問的是「有沒有抽取依據」，不是「有沒有這個檔名」。206 個 doc_id 中有
            # 11 個的 `extractions/<doc_id>.json` 不存在（檔名與 doc_id 不同），
            # 拼檔名會把它們全部誤報成無依據（L15：gate 攔下的不是它想攔的東西）。
            from loader.extraction_index import exists as _extraction_exists

            if not _extraction_exists(doc_id):
                raise TodoError(
                    f"找不到 doc_id={doc_id} 的抽取檔，graph receipt 無可稽核依據"
                )
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
    if to_status != "awaiting_approval":
        # 離開 awaiting_approval 就沒有 gate 可等了——留著會變成過期的 pointer。
        item.pop(AWAITING_GATE_KEY, None)
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
    from intake.actions import read_action

    return read_action(action_id)


def _declared_focus_for_action(action_id: str) -> str | None:
    """讀 RA 自報的 focus_company_id；讀不到就回 None（由呼叫端決定怎麼辦）。"""

    try:
        from intake.actions import read_action

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
    # 帶著 lead_id 一起走：id 是 dict 的 key，不在值裡（先前只取 values() 就拿不到）。
    pairs = [
        (str(lead_id), lead) for lead_id, lead in store["leads"].items()
        if (lead.get("refs") or {}).get("research_action_id") == action_id
    ]
    matches = [lead for _lead_id, lead in pairs]
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
    # ⚠ 這裡**自己記帳，不向呼叫端索取**（2026-09-11 改）。
    #
    # 先前這三段是檢查：lead 必須已經是 applied、必須已帶 action_digest、必須已帶唯一
    # focus_company_id——否則報錯。但呼叫端到這一步已經通過 digest 比對、state=pushed/applied、
    # 每份 document receipt 與 report receipt 都 complete 的驗證：**RA 確實落地了是既成事實**，
    # 把它記進 lead 是簿記，不是判斷。要求呼叫端先手動做，造成兩個實測後果：
    #   ① 2026-09-11 三筆 RA 各失敗兩次才補齊（先補 action_digest、再補 focus_company_id）；
    #   ② 更糟的是反向——[363] 由另一條走廊結案時沒人補，三條 lead 就卡在 action_prepared
    #      十天，而 `queue_segments` 把它歸成「等 pq2 入圖核准」所以稽核照過。
    # 兩者是同一個缺陷的兩端：結案走廊不負責 lead 簿記。加偵測只會讓孤兒**被看見**；
    # 讓結案自己記帳，孤兒才**不可能產生**（修法層級：根除）。
    declared_focus = (_declared_focus_for_action(action_id) or "").strip()
    recorded = {
        str((lead.get("refs") or {}).get("focus_company_id") or "").strip()
        for lead in matches
    } - {""}
    if len(recorded) > 1:
        raise TodoError(f"來源 lead 的 focus_company_id 不一致：{sorted(recorded)}")
    if recorded and declared_focus and recorded != {declared_focus}:
        # 兩個 authority 互相矛盾時不得靜默挑一個——那正是 L15 的 authority laundering。
        raise TodoError(
            f"lead 的 focus_company_id（{sorted(recorded)[0]}）與 RA 自報的"
            f"（{declared_focus}）不符——不猜，請先確認哪一個是對的")
    focus = (sorted(recorded)[0] if recorded else declared_focus)
    if not focus:
        raise TodoError(
            f"{action_id} 既沒有 lead 帶 focus_company_id，RA 也未自報——無法決定 focus company")

    # ⚠ **只補空白，不覆寫不符的值。** 已經帶著「別的 digest」的 lead 代表它綁在另一個
    # 已核准版本上——那是衝突，不是漏記；蓋過去就是讓引用去尋找能通過的權威（L15）。
    conflicting = [
        lead_id for lead_id, lead in pairs
        if str((lead.get("refs") or {}).get("action_digest") or "").strip()
        not in ("", action_digest)
    ]
    if conflicting:
        raise TodoError(
            "來源 lead 帶的 action_digest 與本次核准內容不符（不覆寫，請先確認綁錯了哪一個）："
            + "、".join(conflicting))

    stale = [(lead_id, lead) for lead_id, lead in pairs if lead.get("status") != "applied"]
    illegal = [(i, l) for i, l in stale if l.get("status") != "action_prepared"]
    if illegal:
        # `parked` 是「我們決定不要」的終局，`triaged_go`／`researching` 代表根本還沒備妥 RA。
        # 這兩種都不是簿記漏掉，是真的狀態不對——不得自動推進。
        raise TodoError(
            "來源 lead 的狀態不合法（只有 action_prepared 可由本函式推進到 applied）："
            + "、".join(f"{i}={l.get('status')}" for i, l in illegal))

    missing_refs = [
        lead_id for lead_id, lead in pairs
        if not str((lead.get("refs") or {}).get("action_digest") or "").strip()
        or not str((lead.get("refs") or {}).get("focus_company_id") or "").strip()
    ]
    if stale or missing_refs:
        from engine_b.leads import advance as advance_lead
        from engine_b.leads import annotate_refs, save as save_leads

        for lead_id, lead in pairs:
            refs = lead.get("refs") or {}
            patch = {}
            if not str(refs.get("action_digest") or "").strip():
                patch["action_digest"] = action_digest
            if not str(refs.get("focus_company_id") or "").strip():
                patch["focus_company_id"] = focus
            if patch:
                annotate_refs(store, lead_id, refs=patch)
            if lead.get("status") == "action_prepared":
                advance_lead(store, lead_id, "applied")
        save_leads(store, leads_path)
    companies = {focus}
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
    """驗證 RA 已完整 apply/publish 後才 resolve pq2。

    ⚠ 2026-09-23（Phase 0 Step 0b.4）：原本這裡還會建立（或沿用）Decision Shadow cohort 並把
    `cohort:<dc_…>` 寫進 receipt；Decision handoff 隨 decision_lab 研究側退役，receipt 只剩
    `action;digest;commit`。入圖本身已 durable，pq2 授權的就是入圖。

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
    del ticker  # 保留參數只為呼叫端相容；Decision handoff 退役後不再用它
    stamp = at or _now()
    receipt = f"action:{action_id};digest:{digest};commit:{commit}"
    item["completion_authority"] = {
        "action_digest": digest,
        "commit": commit,
        "company_id": target_company,
        "verified_at": stamp,
    }
    resolved = resolve(
        pool,
        n,
        "go",
        reason="Research Action durable apply／publish 完成",
        receipt=receipt,
        at=stamp,
    )
    return {"item": resolved, "action": action_id, "receipt": receipt}


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
    reconciled: dict[str, Any] | None = None,
) -> dict[str, int]:
    """把各來源蒐集到的項目 upsert 進池。

    `reconciled`：呼叫端已在**收集之前**跑過 thesis 反證對帳時傳入它的結果，這裡就不再跑（CLI 的順序；R2-b NB-3：
    memo 在到期當天換版時，先收集會先鑄一個之後結不了案的編號）。

    `incoming` 每筆需有 type／ref_id／title，可選 hint／source。已 resolve 的
    (type, ref_id) 會重新進池（代表它又出現了，例如同一條 lead 再次需要追源）——這是
    刻意的：resolve 表示「當時處理過」，不是永久黑名單。

    唯一例外是 `ra_admission`：Research Action 是 content-addressed 凍結物件，
    digest 固定、內容不會自行改變，所以 `drop` 一個 exact action_id 就是永久
    決定。若不排除，apply 永遠失敗的 RA（例如撞 DuplicateUrlError 而停在
    `partial`）會每次 sync 都取得新編號，把待辦池洗成噪音。要重新提出必須重跑
    prepare，那會產生新的 action_id 與 digest，自然重新進池。
    """
    added = 0
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
        # 圖影響一句話跟著項目走（L16）；collector 沒算出來就維持缺席。
        if row.get("graph_impact"):
            item["graph_impact"] = str(row["graph_impact"])
        # 同理：標的歸屬。既有 item 在下一次 sync 一併補上（upsert 是同一條路）。
        if row.get("company_id"):
            item["company_id"] = str(row["company_id"])
        if row.get("ticker"):
            item["ticker"] = str(row["ticker"])
        # 反證被判觸及（C3）：item 記下它涵蓋的 watch_id；有新的觸及時，若它躺在「等事件」區就叫回來
        # （比照 `watch_wake`）——否則觸及會安靜地躺在等事件那一區。
        if row.get("disproof_watch_ids"):
            known = set(item.get("disproof_watch_ids") or ())
            fresh = sorted(set(row["disproof_watch_ids"]) - known)
            item["disproof_watch_ids"] = sorted(known | set(row["disproof_watch_ids"]))
            if fresh and (item.get("waiting_on") or item.get("deferred_at")):
                prior = dict(item.get("waiting_on") or {})
                item.pop("waiting_on", None)
                item.pop("deferred_at", None)
                pool["log"].append({
                    "at": stamp, "n": item["n"], "type": item["type"], "ref_id": item["ref_id"],
                    "verb": "disproof_touch", "reason": f"反證被判觸及：{', '.join(fresh)}",
                    "receipt": None, "prior_waiting_on": prior,
                })

    reconcile = reconciled if reconciled is not None else _reconcile_disproof()

    cleared, uncleared = _mark_source_cleared(
        pool, seen_keys, healthy_sources, stamp=stamp
    )

    watch_woken, watch_counts = _check_event_watches(pool, stamp=stamp)

    # ⚠ 2026-09-23（Phase 0 Step 0b.4）：`reactivated`／`waiting_refreshed`／`system_internal_retired`／
    # `churn_suppressed` 四個計數器隨 decision_review collector 退役——它們唯一的輸入
    # （event_link／derived waiting_on／system_internal_only／residual_digest）都只由那個 collector 產生。
    return {
        "added": added,
        "source_cleared": cleared,
        "source_returned": uncleared,
        "watch_woken": watch_woken,
        "watch_counters": watch_counts,
        "disproof_reconcile": reconcile,
        "active": len(active_items(pool)),
    }


def _reconcile_disproof() -> dict[str, Any] | None:
    """thesis 反證對帳（Phase 1 Step 1.5）：在 watch 比對之前跑，這一輪新登記的條件同一輪就開始比對。

    fail-soft：失敗回 None（呼叫端照實印「對帳沒跑」），不阻斷 sync。"""
    try:
        from engine_b import disproof
        from engine_b import event_watch

        data = event_watch.load_watches()
        summary = disproof.reconcile_thesis_disproof(data)
        if summary["registered"] or summary["consumed"]:
            event_watch.save_watches(data)
        return summary
    except Exception:  # noqa: BLE001
        return None


def _mark_disproof_handled(item: Mapping[str, Any], verb: str, stamp: str) -> None:
    """`thesis_lifecycle` 結案（go／drop）時，把它涵蓋的反證 watch 標 `judgment.handled`（C3）。

    best-effort：寫不進去就大聲說——下一次 sync 會因同一條觸及再出一筆，等待不會消失（只是多問一次）。"""
    ids = set(item.get("disproof_watch_ids") or ())
    if not ids:
        return
    try:
        from engine_b import disproof, event_watch

        data = event_watch.load_watches()
        # 觸及 → handled＋（memo 仍現行）續盯；到期 → 續到下一個核查點（設計 B；NB2-5）
        outcome = disproof.after_thesis_review(data, sorted(ids), n=item.get("n"), verb=verb, stamp=stamp)
        event_watch.save_watches(data)
        for err in outcome["errors"]:
            print(f"⚠ 複查後續盯失敗：{err}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ 反證 watch 標 handled 失敗（下一次 sync 會再出一筆）：{type(exc).__name__}: {exc}",
              file=sys.stderr)


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
        # 也收「先前已 fired、但由別的呼叫端觸發而本函式沒看到」的 pq2 型 watch。
        # 2026-09-08 實測：triage 路徑先把 ew_0002（喚醒 [134]）標成 fired 存檔；本函式
        # 之後每天 check 時它已不是 active，永遠不會再回到 fired 清單——掛了一週。
        # check 的回傳只含「這一次新觸發的」，consumer 卻該掃 status 本身。
        fresh_ids = {w["watch_id"] for w in fired}
        backlog = [
            dict(w) for w in data["watches"]
            if w.get("status") == "fired" and w.get("wake_pq2")
            and w["watch_id"] not in fresh_ids
        ]
        woken = 0
        # 到期處置（Phase 1 Step 1.7，A3）：pq2 型 → 它指向的未結案編號翻回「球在你」（不另鑄號）；
        # 讀圖型 → 不另處置（讀圖自己的到期由 needs_reread 重問），只記處置；語意／假設型 → 收集器鑄 watch_decision；
        # 追源型 → consume-fired 轉終局。
        for watch in data["watches"]:
            if watch.get("status") != "expired":
                continue
            resolution = watch.get("expiry_resolution") or {}
            if event_watch.expiry_class(watch) == "reading":
                if not resolution:
                    event_watch.resolve_expiry(data, watch["watch_id"], {"kind": "reading_expiry",
                                                                         "node": watch.get("wake_reading")})
                continue
            if not watch.get("wake_pq2") or (resolution and resolution.get("kind") != "requeued_to_pq2"):
                continue
            # 依編號現況判斷（冪等，R2-b 重審 NB2-13）：registry 已記 requeued、pool 還沒存到就崩潰的話，
            # 下一輪照樣翻回；使用者在到期**之後**自己又 pending 的不動。
            n = int(watch["wake_pq2"])
            item = next((it for it in pool["items"] if it["n"] == n and not it.get("resolved_at")), None)
            expired_at = str(watch.get("expired_at") or watch.get("expires") or "")
            if item is not None and (item.get("waiting_on") or item.get("deferred_at")):
                set_at = str((item.get("waiting_on") or {}).get("set_at") or item.get("deferred_at") or "")
                if not set_at or set_at <= expired_at:
                    prior = dict(item.get("waiting_on") or {})
                    item.pop("waiting_on", None)
                    item.pop("deferred_at", None)
                    pool["log"].append({
                        "at": stamp, "n": n, "type": item["type"], "ref_id": item["ref_id"],
                        "verb": "watch_expired", "reason": f"event watch {watch['watch_id']} 到期：它等的事件沒發生",
                        "receipt": None, "prior_waiting_on": prior,
                    })
            if not resolution:
                event_watch.resolve_expiry(data, watch["watch_id"], {
                    "kind": "requeued_to_pq2" if item is not None else "pq2_item_gone", "n": n})
        for watch in fired + backlog:
            if not watch.get("wake_pq2"):
                # 假設型 fact-check 到點：沒有 pq2 可翻醒——停在 fired 現形於
                # 計數器（fired_unconsumed），agent 對照＋verify 後以
                # `event_watch consume` 收掉。刻意不自動 consume：對照是研究
                # 動作，收據要留在假設層。
                continue
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

    從凍結 payload 數 nodes／edges／claims 並列 origin＋tier。
    解析失敗回空字串（fail-soft：影響行缺席，密度契約其餘不變）。

    ⚠ 兩個 key 都要認：draft（`library/leads/action_drafts/*.json`）用字串
    `extraction_json`，但 prepare 凍結後正規化成 dict `extraction`。本函式原本只讀前者，
    於是對**所有真實 RA** 都回空字串——2026-08-31 上線當天實測 328 個池內項目
    `graph_impact` 出現 0 次。這是 L13「管子只接了一頭」：機制寫好了，但讀的欄位
    不是消費端手上那份資料。
    """

    try:
        n_nodes = n_edges = n_claims = 0
        origins: list[str] = []
        for doc in payload.get("documents") or []:
            raw = doc.get("extraction_json")
            if raw is None:
                raw = doc.get("extraction")
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
    from intake.actions import iter_actions

    rows: list[dict[str, Any]] = []
    for action in iter_actions():
        if action.get("state") in {
            "ready", "applying", "partial", "ready_for_approval", "partial_apply"
        }:
            action_id = str(action.get("action_id") or action.get("id") or "")
            # RA 自己聲明的 focus company 優先。從 lead 來的 RA 由綁定 lead 提供
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
                    f"核准 exact graph delta；focus company：{focuses[0]}。"
                    "RA 內其他公司只作 evidence／relationship context，不自動建 cohort。"
                )
            elif focuses:
                handoff_hint = (
                    "BLOCKER：Research Action 有多個 focus_company_id："
                    f"{', '.join(focuses)}；先回 pq1 拆成明確 focus company。"
                )
            else:
                handoff_hint = (
                    "BLOCKER：Research Action 尚未聲明唯一 focus_company_id；"
                    "先回 pq1 補 focus company，不得先 apply。"
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
    """到期／review_required／反證被判觸及的 thesis → 本機複查待辦（同一 thesis 只會有一筆，理由合併）。

    反證被判觸及（C3／A5，Phase 1 Step 1.5）：row 帶 `disproof_watch_ids`，`sync` 寫到 item 上；使用者對這一筆
    `go`／`drop` 時，同一個動作把那些 watch 標 `judgment.handled`——觸及的等待由這一筆接住，不會消失。"""
    from crons.thesis_freshness_check import lifecycle_due_detail

    return [
        {
            "type": "thesis_lifecycle",
            "ref_id": tid,
            "title": f"thesis {tid}：{why}",
            "source": "lifecycle",
            **({"disproof_watch_ids": ids} if ids else {}),
        }
        for tid, why, ids in lifecycle_due_detail(strict=True)
    ]


def _collect_watch_expiry_rows() -> list[dict[str, Any]]:
    """沒有自己複查週期的 watch（假設型等）到期、還沒處置 → `watch_decision`（Phase 1 Step 1.7；設計 B：thesis／讀圖
    來源的語意條件不在這裡——`expiry_class` 回 `thesis_review`／`reread`，重問併進 thesis 複查與節點重讀）。

    **每個到期事件恰好一個編號**：ref_id＝`<watch_id>@<expires>`——續等會改 `expires`，所以再到期是新的事件、
    新的編號；同一次到期重跑 sync 不重鑄。**用 `expires` 不用 `expired_at`**：CLI 的 sync 先收集、後由
    `check_watches` 標到期，到期當天收集時 watch 還是 active——這裡照日期認，當天就出編號，而且標記前後
    ref_id 相同（用 `expired_at` 會在標記後換 key、重鑄一號）。
    標題不得只寫 `co:*` 或 watch_id（使用者要不展開就知道主詞）。"""
    from engine_b import event_watch

    rows: list[dict[str, Any]] = []
    for watch in event_watch.load_watches().get("watches") or []:
        expired = watch.get("status") == "expired" or (
            watch.get("status") == "active" and event_watch.past_expiry(watch))
        if not expired or watch.get("expiry_resolution"):
            continue
        if event_watch.expiry_class(watch) != "decision":
            continue
        when = str(watch.get("expires"))
        rounds = len(watch.get("renewals") or []) + 1
        nth = f"（第 {rounds} 次到期）" if rounds > 1 else ""
        target = (f"假設 {watch.get('hypothesis_ref')}" if watch.get("hypothesis_ref")
                  else f"{','.join(str(e) for e in (watch.get('entities') or [])[:3])}")
        title = (f"等待到期、沒有對照到{nth}：{event_watch.condition_label(watch.get('fact') or watch.get('condition') or watch.get('note'))}"
                 f"（{target}）")
        rows.append({
            "type": "watch_decision",
            "ref_id": f"{watch['watch_id']}@{when}",
            "title": title,
            "hint": ("續等：python -m engine_b.todo resolve <編號> --verb pending --until <日期>｜放棄：drop｜"
                     "要研究就在互動 session 說；研究後已發生才 go（receipt 帶 outcome:touched＋內文提到這個 watch 的報告、"
                     "--quote 原文）"),
            "source": "watch_expiry",
        })
    return rows


def collect_all() -> list[dict[str, Any]]:
    return collect_all_with_health().rows


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
    # ⚠ 2026-09-22（Step 0a.4）：`"decisions": {"decision_review", "sheet_only_holding"}` 已移除。
    # 兩個 legacy kind 從此**沒有 collector**——與 `manual` 同形：缺席不代表完成（見上方 docstring）。
    "engine_c_observations": frozenset({"engine_c_observation"}),
    "thesis_mutations": frozenset({"thesis_mutation"}),
    "watch_expiry": frozenset({"watch_decision"}),
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
# ⚠ **2026-09-22（Phase 0 Step 0a.4）：`("decisions", "_collect_decision_rows")` 已從登記表移除。**
# 這一行就是「池子停止鑄 decision_review／sheet_only_holding 號」的唯一開關：collector 不在
# 登記表上就不會被呼叫，也永遠不會進 `healthy`——於是 `_mark_source_cleared` 一筆都不判定
# （它只看 healthy 列出的來源），**池裡既有的 17 筆歷史項目不會被自動標記或結案**。
# 它們在 Step 0c 由使用者授權的批次 `drop` 關閉，理由「機制退役」。
SOURCE_COLLECTORS: tuple[tuple[str, str], ...] = (
    ("research_actions", "_collect_research_action_rows"),
    ("source_trace", "_collect_source_trace_rows"),
    ("lifecycle", "_collect_lifecycle_rows"),
    ("engine_c_observations", "_collect_engine_c_observation_rows"),
    ("thesis_mutations", "_collect_thesis_mutation_rows"),
    # 2026-09-24 R2-b 兩輪 NO_GO 都曾回滾停登記；RB-1／RB-2／NB2 修好、到期成批改設計 B 後重新啟用（plan §0.7）。
    ("watch_expiry", "_collect_watch_expiry_rows"),
)


def collect_all_with_health() -> SourceCollection:
    """⚠ 2026-09-22（Step 0a.4）：`include_decisions` 參數已移除。

    原本它預設 `True`，呼叫端要主動關掉才不鑄 decision 型號。現在**只有一條路**——
    登記表上沒有 decisions collector，所以沒有開關可以把它打開（L15：權限要 deterministic，
    不留一個「傳個參數就回來了」的旁門）。
    """
    rows: list[dict[str, Any]] = []
    healthy: set[str] = set()
    sources: list[tuple[str, Any]] = [
        (name, globals()[attr]) for name, attr in SOURCE_COLLECTORS
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
    # hint 是密度契約的內容（TL;DR），先前在 CLI 完全不顯示＝資訊遺失；
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
        # ⚠ 這一段原本把兩件事寫成同一句「等人工 gate」：真的在等你核准，以及
        # gate 早就 resolve 了卻沒人回頭動這張工單（2026-09-10 實測 [311]／[411]）。
        # 分開講，因為下一步不同——後者要完成 checkpoint，不是等你。
        gate_state = {row["n"]: row for row in gated_items(pool)}
        lines.append(
            f"## pq1 已交回，等人工 gate（{len(gated)} 項；不吃 go／drop／pending）"
        )
        for item in gated:
            state = gate_state.get(int(item["n"]), {})
            suffix = ""
            if state.get("state") == "gate_resolved":
                suffix = (
                    f"　⚠ 它等的 [{state['gate_n']}] 已 {state['gate_resolution']}"
                    "——gate 已消失，下一步是完成 pq1 checkpoint 並以 terminal receipt 結案"
                )
            elif state.get("state") == "no_pointer":
                suffix = "　⚠ 說不出在等哪個編號——這個等待沒有到期（INV-2）"
            lines.append(f"  [{item['n']}] {item['title']}{suffix}")
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
    # ⚠ 2026-09-22（Step 0a.4）：`--no-decisions` 已移除——decisions collector 不在登記表上，
    # 沒有東西可以跳過，留著一個沒有作用的旗標會讓讀者以為預設是「有跑」。
    p_sync.add_argument("--json", action="store_true")

    p_standing = sub.add_parser(
        "standing-go",
        help="佇列段 2b：對常規授權類別（config/standing_authorization.json）執行使用者本來會下的 go；預設只列候選",
    )
    p_standing.add_argument("--run", action="store_true", help="實際 dispatch；預設只列出候選與跳過者")
    p_standing.add_argument("--leads", default="")
    p_standing.add_argument("--json", action="store_true")

    p_res = sub.add_parser("resolve", help="處理編號：go／drop／pending")
    p_res.add_argument("numbers", nargs="+")
    p_res.add_argument("--verb", required=True, choices=VERBS)
    p_res.add_argument("--reason", default="")
    p_res.add_argument("--receipt", default="")
    p_res.add_argument("--quote", default=None,
                       help="watch_decision 的 go 專用：outcome:touched 的文件原文逐字（L18）")
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

    p_work = sub.add_parser("work", help="更新已 dispatch 的 source_trace_review pq1 job")
    p_work.add_argument("number", type=int)
    p_work.add_argument(
        "--to", required=True,
        choices=("researching", "awaiting_approval", "completed", "parked"),
    )
    p_work.add_argument("--receipt", required=True)
    p_work.add_argument("--reason", default="")
    p_work.add_argument("--leads", default="")
    p_work.add_argument(
        "--awaiting-gate", type=int, default=None,
        help="進 awaiting_approval 時：它在等哪個 pq2 編號（結構化 pointer，不要寫進 receipt）",
    )

    sub.add_parser(
        "gated",
        help="列出停在 awaiting_approval 的工單，並分辨『真的在等你』與『gate 已消失』",
    ).add_argument("--json", action="store_true")

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
        help="驗證 RA durable apply／publish 後結案 exact pq2 item",
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
        reconciled = _reconcile_disproof()  # 先對帳再收集（R2-b NB-3）
        collected = collect_all_with_health()
        result = sync(
            pool, collected.rows, healthy_sources=collected.healthy, reconciled=reconciled,
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
            rc = result.get("disproof_reconcile")
            reconcile_line = ("；反證對帳沒跑（失敗）" if rc is None else
                              "；⚠ 反證對帳：lifecycle 讀不到，本輪不動任何等待" if rc.get("lifecycle_unreadable") else
                              f"；反證對帳：登記 {len(rc['registered'])}、收掉 {len(rc['consumed'])}"
                              f"、sidecar 不符 {len(rc['sidecar_mismatch'])}"
                              + (f"、沒有結構化反證 {len(rc['no_structured'])}（由 Step 1.6 補登記）"
                                 if rc["no_structured"] else "")
                              + (f"、⚠ 登記失敗 {len(rc.get('errors') or [])}"
                                 if rc.get("errors") else ""))
            print(
                f"（新增 {result['added']}，目前 {result['active']} 項待辦"
                f"{migration}{watch_line}{reconcile_line}）\n"
            )
            print(_render(pool))
        return 0

    if args.command == "standing-go":
        from engine_b.leads import DEFAULT_LEADS_PATH

        outcome = standing_go(pool, leads_path=args.leads or DEFAULT_LEADS_PATH, dry_run=not args.run)
        if args.run:
            save(pool, args.pool)
        if args.json:
            print(json.dumps(outcome, ensure_ascii=False, indent=2))
        else:
            if outcome["dry_run"]:
                print(f"段2b 常規授權候選 {len(outcome['candidates'])} 項：{outcome['candidates'] or '—'}"
                      f"｜跳過 {len(outcome['skipped'])}（加 --run 執行）")
            else:
                done = [f"[{row['n']}]→{row['outcome']}" for row in outcome["done"]]
                print(f"段2b 常規授權：候選 {len(outcome['candidates'])}｜執行 {len(outcome['done'])}"
                      f"（{'、'.join(done) or '—'}）｜跳過 {len(outcome['skipped'])}｜失敗 {len(outcome['failed'])}")
            for row in outcome["skipped"]:
                print(f"  · [{row['n']}] 跳過：{row['reason']}")
            for row in outcome["failed"]:
                print(f"  ✗ [{row['n']}] {row['reason']}", file=sys.stderr)
        return 1 if outcome["failed"] else 0


    if args.command == "resolve":
        failures = 0
        for raw in args.numbers:
            try:
                done = resolve(
                    pool, int(raw), args.verb,
                    reason=args.reason, receipt=args.receipt,
                    until=args.until, trigger=args.trigger,
                    event_type=args.event_type, quote=args.quote,
                )
                suffix = ""
                if done.get("resolution") == "stale_event":
                    suffix = f"（到期事件已過時，只結案編號：{done.get('receipt')}）"
                elif done.get("resolution") == "renewed":
                    suffix = f"（續等到 {args.until}：watch 回 active，這個編號結案——等待只住 registry）"
                elif args.verb == "pending" and (args.until or args.trigger):
                    suffix = f"（等：{args.until or args.trigger}）"
                print(f"✓ [{raw}] → {args.verb}{suffix}")
            except (TodoError, ValueError) as exc:
                failures += 1
                print(f"✗ [{raw}]：{exc}", file=sys.stderr)
        save(pool, args.pool)
        return 1 if failures else 0

    if args.command == "gated":
        rows = gated_items(pool)
        if getattr(args, "json", False):
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        if not rows:
            print("沒有工單停在 awaiting_approval。")
            return 0
        label = {
            "waiting": "真的在等你核准",
            "gate_resolved": "⚠ gate 已消失（下一步：完成 pq1 checkpoint 並結案）",
            "no_pointer": "⚠ 說不出在等哪個編號——沒有到期（INV-2）",
        }
        for state in ("gate_resolved", "no_pointer", "waiting"):
            group = [r for r in rows if r["state"] == state]
            if not group:
                continue
            print(f"\n## {label[state]}（{len(group)} 項）")
            for row in group:
                gate = f"等 [{row['gate_n']}]" if row["gate_n"] else "無 pointer"
                origin = row["gate_origin"] or "—"
                print(f"  [{row['n']}] {row['title']}")
                print(f"        ↳ {gate}（pointer 來源：{origin}）"
                      f"｜最後更新 {row['dispatch_updated_at']}")
        return 0

    if args.command in {"dispatch", "work"}:
        from engine_b.leads import DEFAULT_LEADS_PATH

        failures = 0
        if args.command == "dispatch":
            for raw in args.numbers:
                try:
                    item = get(pool, int(raw))
                    if item["type"] == "source_trace_review":
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
                if item["type"] == "source_trace_review":
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
        before_next_n = int(pool["next_n"])
        was = {it["n"]: (it["title"], it.get("hint") or "") for it in pool["items"]}
        item = upsert(
            pool, item_type="manual",
            ref_id=args.ref or f"manual:{pool['next_n']}",
            title=args.title, hint=args.hint, source="manual",
        )
        save(pool, args.pool)
        if int(pool["next_n"]) == before_next_n:
            # upsert 是冪等的（同 type+ref_id 未 resolve 就更新原項），但那代表**沒有鑄新號**，
            # 而且原本的 title／hint 已被覆蓋。不說出來的話，呼叫者會以為自己拿到了新編號。
            old_title, old_hint = was.get(item["n"], ("", ""))
            print(f"⚠ 未鑄新號：(manual, {item['ref_id']}) 已在池中且未 resolve，改成更新既有 [{item['n']}]。")
            if old_title and old_title != item["title"]:
                print(f"  ↳ 原 title 已被覆蓋：{old_title}")
            if args.hint and old_hint and old_hint != (item.get("hint") or ""):
                print(f"  ↳ 原 hint 已被覆蓋：{old_hint}")
            print("  ↳ 要另鑄一個編號，請換一個 --ref。")
        print(f"✓ 已加入 [{item['n']}] {item['title']}")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
