"""佇列段序（closed vocabulary）——**「有工作存在」的每一種狀態都必須指得出 consumer。**

## 為什麼需要它

2026-09-08 實測：39 個 fired watch、27 檔沒有 forward view 的 tracked 標的，
兩類工作都不在任何佇列定義裡，於是 `drain` 顯示「佇列已空」、research-drain 宣告閉包，
而工作其實還在——L13（管子只接一頭）與 L16（分類存在但沒送到消費端）的合體。
根因不是某個 bug，是**佇列的定義是散文**：段序寫在 skill 裡，新的工作類型長出來時
沒有任何東西會叫。

本模組把段序變成程式裡的封閉字彙，並提供一個**由資料反推**的觀測函式：
把 leads／watches／todo 的每一筆現況分類到某一段，分不到的就是 `unmapped`。
`audit invariants --only QueueSegments`（INV-4）對 `unmapped` 非空 fail——
新狀態出現的那一天，第一筆資料就會讓稽核變紅，不必有人記得來改這裡。

## 兩種成本，不共用同一個預算

- `mechanical`：確定性命令、零 token（fired 重排、pq2 翻醒、gated 指認）。**不吃** pq1 的
  `drain_limit_per_run`。⚠ 2026-09-22（Phase 0 Step 0a.1）：`reassess` 已不在這一類——
  decision_lab 研究側退役，段序不再登記它。
- `research`：要 web search／讀文件／寫判斷。⚠ **2026-09-17 更正：只有 `engine_b.cli drain` 那條路徑
  吃 `drain_limit_per_run`**（唯一執行點 `engine_b/cli.py::_cmd_drain`）。`pending_triage` 雖然也標
  `research`，但它的 consumer 是 `engine_b.cli triage`，**完全不讀 routine_config**——所以 D12 把
  `drain_limit_per_run` 歸零（daily 不做研究）**不會關掉分類層**，那正是三層拆分要的效果。
  原句寫「共用 `drain_limit_per_run`」在 limit 歸零後就變成假的，留著會讓下一個讀者以為 triage 也停了。
  順序由
  `engine_b/priority.py`（lead）與 Decision Store 的 work order 排序決定——本模組**不排序**，
  只回答「這一筆屬於哪一段、誰會來取」。

## 這一層刻意不做的事

- 不重排 lead（priority.py 是唯一權威）。
- 不寫任何檔案；`observe()` 是純函式。
- 不判定 forward view／走圖的**內容**——那兩段的計數由呼叫端注入（authority 分別是
  analyst view artifact、走圖 `query.graph_walk`），本模組只登記它們的 consumer。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Segment:
    key: str
    order: int
    label: str
    #: "mechanical"（零 token，不吃 pq1 預算）或 "research"（要 token）。
    #: ⚠ `research` **不等於**「吃 drain_limit_per_run」——見檔頭：只有 drain 那條路徑吃它。
    cost: str
    #: 誰會來取——命令字串或 skill 段落。**不得為空**：沒有 consumer 的段就是黑洞。
    consumer: str
    note: str = ""


#: 段序是封閉字彙。順序＝執行順序：先分流新 harvest，再把機械段清掉，最後才是研究段。
SEGMENTS: tuple[Segment, ...] = (
    Segment(
        "pending_triage", 0, "新 harvest 的 pending lead 分流（signal-triage）",
        "research", "daily ⑦（claude -p 零工具提議＋engine_b.cli triage-apply 程式寫入）；"
                    "超過每日上限或 LLM 失敗的由互動 session 以 python -m engine_b.cli triage 處理",
        "使用者定案（2026-09-09 B 項）：每日進來的新東西先處理，避免全部被卡住。",
    ),
    Segment(
        "fired_lead_requeue", 1, "fired watch → parked 追源 lead 重排回 pq1",
        "mechanical", "python -m engine_b.cli consume-fired",
        "2026-09-08 實測 34 筆卡在 fired：todo sync 與 triage 各自呼叫 check_watches、"
        "各只處理自己那一種喚醒對象，另一種被存成 fired 後再也不會出現在 fired 清單裡。",
    ),
    Segment(
        "fired_pq2_wake", 1, "fired watch → pq2 項目由「等事件」翻回「等你決定」",
        "mechanical", "python -m engine_b.todo sync",
    ),
    Segment(
        "semantic_pending_check", 1, "fired 語意 watch（反證／確認條件）→ 互動 session 判定觸及與否",
        "research", "互動 session：python -m engine_b.event_watch semantic-queue → judge",
        "Phase 1 Step 1.4（G7）：醒來＝待檢；daily 的預篩只標旗、不判定，所以這一段不會因預篩而變少。",
    ),
    Segment(
        "fired_reading_reread", 1, "fired 讀圖 watch（需求側客戶出了新一手文件）→ 該節點要重讀",
        "research", "互動 session：python -m query.structure <node> → alpha structure-reading <node> --add"
                    "（下一次 --add 自動 consume 這些 watch）",
        "Phase 1 Step 1.5：醒來只把節點列進 needs_reread（理由寫出是哪位客戶的哪份文件），不自動重讀——重讀是研究。",
    ),
    Segment(
        "narrative_rewrite", 1, "敘事來源的 watch 醒來、被判觸及或到期未判，或敘事連結的反證來源已不在盯（收掉／觸及／到期／不存在）→ 該重寫那一檔的敘事",
        "research", "research-drain「敘事該重寫」段：讀那一檔現行敘事與觸發的 watch → "
                    "python -m alpha brief <T> --add spec.json（v2；`acknowledged_touched` 逐條處置，不列就拒收；"
                    "連結斷了的那一條：來源換版就把 link_source_ref 換成新來源鍵，來源被觸及／到期就先看來源那一邊的處置再改寫）",
        "Phase 3 Step 3.4：`brief:` 語意 watch（敘事自己的反證）與 `wake_brief` watch（「缺 X」「已定價等回落」在等的事）"
        "醒來、觸及或到期都不鑄 pq2、不進假設對照——下一步是重寫敘事，而重寫是研究。換版與撤回不會吞掉它們。"
        "Step 3.6：敘事 `disproof[].link_source_ref` 連到的 watch 已不在盯（`narrative_watches.link_breaks`，附為什麼斷）"
        "也算這一段的工作——它不是任何一筆 watch 的狀態，由呼叫端注入 `observe(narrative_link_breaks=…)`。",
    ),
    Segment(
        "fired_hypothesis_check", 1, "fired watch → 截圖假設對照（agent 拿 fact 去對一手）",
        "research", "research-drain 段 0b：對照後 `python -m engine_b.event_watch consume <watch_id>`",
        "刻意不自動 consume：對照是研究動作，收據要留在假設層（engine_b/hypotheses.py）。",
    ),
    # ⚠ 段 2（`reassess_stale`）**已於 2026-09-22 Phase 0 Step 0a.1 退役**：decision_lab 研究側
    # 整批退役（ROADMAP Phase 0／G3、G12），所以「只因凍結 context 過期而 REVIEW」這種工作
    # 不會再產生。**它不是安靜消失**——同一個 change 一併拿掉 `.codex/rules` 的 fixed entry、
    # daily prompt 的那一步與 `audit/checks.py` 的注入，所以沒有任何 producer 還在製造它。
    Segment(
        "approved_work_orders", 3, "使用者已 go 的 decision work order（queued／researching）",
        "research", "python -m engine_b.cli drain（[USER-GO] 列）",
    ),
    Segment(
        "triaged_go_leads", 4, "triaged_go／researching lead（含 fired 重排回來的）",
        "research", "python -m engine_b.cli drain（依 engine_b/priority.py 排序）",
    ),
    Segment(
        "forward_view_backlog", 5, "tracked 標的的單檔判讀 blocked、且仍有未 settled 的 blocker",
        "research", "research-drain §每檔閉環（P3；深度優先，一檔到終局才開下一檔）",
        "終局三種：ready／剩餘 blocker 全部 settled／全部掛在 pq2 編號上。",
    ),
    # ⚠ 2026-09-26（Phase 2 Step 2.6）：`coverage_gaps`、`duplicate_node_candidates`、`stale_structure_readings`
    # 三段併成 `graph_holes`——它們成為走圖的第 7／8、9、4 型（`query/graph_walk.py`），另加五型
    # （薄層沒人讀、獨家且自報、供給側未填、lead 點名不在圖、供貨走不到錨）。三段不是安靜消失：
    # 同一個 change 改掉 `observe()` 的注入參數、`audit/checks.py` 與心跳的呼叫端、research-drain 第三段。
    # `fired_reading_reread`（watch 那一側叫醒的重讀）**留**——它是事件驅動，走圖第 4 型只看圖那一側。
    Segment(
        "graph_holes", 6, "走圖九型問句的命中（圖上該去研究的洞；每型各自一格，不排序）",
        "research", "research-drain 第三段：python -m query.graph_walk（每筆命中附下一個研究動作）",
        "計數＝**有命中的型別數**（0–9；`graph_holes_count()`），**只用來回答「這一段有沒有工作」**（INV-4）——"
        "九型的單位各不相同（節點、公司、lead、節點對），命中筆數相加沒有意義，所以不加總、也不進 `research_total`。"
        "它不是分數、不排序、不在任何人讀的畫面上當成一個數字印（心跳與 APP 一律九格各自印）。"
        "母體 ≥10 的型別命中率 ≥50% 就是恆亮（L14-4），走圖自己會標出來。",
    ),
    Segment(
        "pollable_watches", 7, "stalled 且可主動輪詢的 watch（被動層不會再醒）",
        "research", "python -m engine_b.event_watch sweep（budget 見 config/event_watch.json）",
    ),
    # 下面兩段是 2026-09-10 新增的偵測。它們**必須有一個會自己出現的地方**，否則
    # 就只是「要人讀的段落」（L14）——而 `engine_b.todo work` 是 daily 的 fixed entry，
    # 排程有能力製造這兩種狀態。
    Segment(
        "gated_gate_resolved", 8, "停在 awaiting_approval，但它等的 pq2 編號已經 resolve",
        "mechanical", "python -m engine_b.todo gated（下一步是完成 pq1 checkpoint 並結案）",
        "gate 消失不等於可以直接收單：實測三張工單 reassess 後都浮出不同的新缺口。",
    ),
    Segment(
        "gated_no_pointer", 9, "停在 awaiting_approval，卻說不出在等哪個編號",
        "mechanical", "python -m engine_b.todo gated（補 `todo work --awaiting-gate <n>`）",
        "說不出在等誰的等待就是沒有到期的等待（INV-2），也沒有 consumer（INV-4）。",
    ),
)

SEGMENT_BY_KEY: dict[str, Segment] = {s.key: s for s in SEGMENTS}

#: 每個來源的已知狀態字彙。**這裡列的是「我們認得的全部」**：資料裡出現不在此的值
#: 就是 `unmapped`——不是錯誤處理，是本模組存在的目的。
LEAD_STATUSES: frozenset[str] = frozenset({
    "pending", "triaged_go", "researching", "action_prepared",
    "parked", "applied", "triaged_no_go",
})
WATCH_STATUSES: frozenset[str] = frozenset({"active", "fired", "consumed", "expired"})
DISPATCH_STATUSES: frozenset[str | None] = frozenset({
    None, "", "queued", "researching", "awaiting_approval", "completed", "parked",
})

#: 不是工作、也不是缺口的狀態——它們有自己的去處（人工 gate／終局），列出來是為了
#: 讓「分不到段」與「刻意不算工作」分得開（L12：兩種語意不得同形）。
NOT_WORK: dict[str, str] = {
    "lead:action_prepared": "等 pq2 入圖核准（人工 gate，不是 pq1 工作）",
    "lead:parked": "等待條件住 Event Watch registry；醒來才回到 fired_lead_requeue",
    "lead:applied": "終局",
    "lead:triaged_no_go": "終局",
    "watch:active": "在等（未觸發）",
    "watch:consumed": "終局",
    "watch:expired": "到期：thesis／讀圖來源的列進 thesis 複查與節點重讀（A7）；假設型等轉 pq2 watch_decision；pq2 型已翻回球在你；追源型已結案（watch_expired）；敘事型（未處置的）在 narrative_rewrite",
    "todo:awaiting_approval": "等 pq2 人工 gate",
    "todo:completed": "終局（等 resolve）",
    "todo:parked": "終局（等 resolve）",
    "todo:user_decision": "球在使用者手上（pq2）",
}


class QueueSegmentError(ValueError):
    """段序字彙被違反（例如登記了沒有 consumer 的段）。"""


def validate_registry() -> None:
    """段序本身的不變量：key 唯一、consumer 非空、cost 只有兩種。import 時就跑。"""
    seen: set[str] = set()
    for seg in SEGMENTS:
        if seg.key in seen:
            raise QueueSegmentError(f"段 key 重複：{seg.key}")
        seen.add(seg.key)
        if not seg.consumer.strip():
            raise QueueSegmentError(f"段 {seg.key} 沒有 consumer——沒有 consumer 的段就是黑洞")
        if seg.cost not in {"mechanical", "research"}:
            raise QueueSegmentError(f"段 {seg.key} 的 cost 必須是 mechanical 或 research")


validate_registry()


# ---------------------------------------------------------------------------
# 逐筆分類（純函式）
# ---------------------------------------------------------------------------

def classifier_of(lead: Mapping[str, Any]) -> str:
    """這則 lead 的 PASS 分類是誰下的（`triage.classification.classified_by`）；沒有分類記 `unclassified`。"""
    classification = ((lead.get("triage") or {}).get("classification")) or {}
    return str(classification.get("classified_by") or "").strip() or "unclassified"


def classify_lead(lead: Mapping[str, Any]) -> str | None:
    """回傳段 key；不是工作回 `None`；狀態不認得回 `"unmapped:lead:<status>"`。"""
    status = str(lead.get("status") or "")
    if status not in LEAD_STATUSES:
        return f"unmapped:lead:{status or '<empty>'}"
    if status == "pending":
        return "pending_triage"
    if status in {"triaged_go", "researching"}:
        return "triaged_go_leads"
    return None


def is_narrative_watch(watch: Mapping[str, Any]) -> bool:
    """敘事來源的 watch（Phase 3 Step 3.4）：敘事自己的反證（`brief:` 語意）或敘事在等的事（`wake_brief`）。"""
    return bool(watch.get("wake_brief")) or str(watch.get("source_ref") or "").startswith("brief:")


def narrative_rewrite_state(watch: Mapping[str, Any]) -> str | None:
    """敘事來源的 watch 處在哪一種「該重寫」狀態：`fired`（醒來）｜`touched`（判定觸及、未處置）｜
    `expired`（到期未處置）；還在等（active）或已處置回 None。**換版與撤回的 hook 只收 None 的**（§5 第 6 點）。"""
    if not is_narrative_watch(watch):
        return None
    status = watch.get("status")
    if status == "fired":
        return "fired"
    judgment = watch.get("judgment") or {}
    if status == "consumed" and judgment.get("touches") == "yes" and not judgment.get("handled"):
        return "touched"
    if status == "expired" and not watch.get("expiry_resolution"):
        return "expired"
    return None


def classify_watch(watch: Mapping[str, Any]) -> str | None:
    status = str(watch.get("status") or "")
    if status not in WATCH_STATUSES:
        return f"unmapped:watch:{status or '<empty>'}"
    # ⚠ 敘事來源先判（Phase 3 Step 3.4）：`wake_brief` 的 date watch 到 until 轉 fired，若落到下面的預設分支就會被
    # 當成「假設對照」——錯的 consumer，QueueLiveness 還會照綠（plan §13）。
    if narrative_rewrite_state(watch) is not None:
        return "narrative_rewrite"
    if status == "fired":
        if watch.get("wake_pq2"):
            return "fired_pq2_wake"
        if watch.get("wake_lead"):
            return "fired_lead_requeue"
        if watch.get("disproof_ref"):
            return "semantic_pending_check"
        if watch.get("wake_reading"):
            return "fired_reading_reread"
        return "fired_hypothesis_check"
    if status == "active" and (watch.get("poll") or {}).get("eligible"):
        # 可輪詢的 active watch 才是「要人主動去查」的工作；其餘 active 只是等。
        # 是否 stalled 由 event_watch.is_stalled 決定，這裡只看「可不可以主動撈」。
        return "pollable_watches"
    return None


def classify_todo(item: Mapping[str, Any]) -> str | None:
    """pq2 項目只有一種算 pq1 工作：已 dispatch 的 work order。

    ⚠ 2026-09-22（Step 0a.1）：原本還有第二種（只需 reassess 的 decision_review）。
    reassess 隨 decision_lab 研究側退役，所以這裡少一個分支、`observe()` 少一個參數。
    """
    if item.get("resolved_at"):
        return None
    dispatch = item.get("dispatch_status")
    if dispatch not in DISPATCH_STATUSES:
        return f"unmapped:todo:{dispatch}"
    if dispatch in {"queued", "researching"}:
        return "approved_work_orders"
    return None


# ---------------------------------------------------------------------------
# 觀測
# ---------------------------------------------------------------------------

def graph_holes_count(questions: Iterable[Mapping[str, Any]]) -> int | None:
    """`graph_holes` 段的計數：走圖九型裡**有命中的型別數**（Phase 3 Step 3.1a）。

    `questions` 是 `query.graph_walk.collect()["questions"]`（稽核直接跑走圖）或 `graph_walk` artifact 的
    `questions`（心跳只讀 artifact）——兩者同形，所以兩個呼叫端共用這一份，不各算一次（L16）。
    ⚠ 原本是九型命中筆數之和（2026-09-26 實測 60）——節點、公司、lead、節點對混在一起加，那個數沒有單位。
    帶 `absence` 的型別不計；**全部型別都沒讀到時回 `None`**（「沒讀到」與「沒有洞」不得同形，INV-3）。
    """
    present = [q for q in questions if not q.get("absence")]
    if not present:
        return None
    return sum(1 for q in present if int(q.get("hit_n") or 0) > 0)


def observe(
    *,
    leads: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]] = (),
    watches: Iterable[Mapping[str, Any]] = (),
    todo_items: Iterable[Mapping[str, Any]] = (),
    forward_view_backlog: int | None = None,
    graph_holes: int | None = None,
    narrative_link_breaks: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """由資料反推每一段有幾筆工作。

    `narrative_link_breaks`（Phase 3 Step 3.6）：`engine_b.narrative_watches.link_breaks()` 的結果——現行敘事的
    連結來源已換版。它不是任何一筆 watch 的狀態（是「敘事指向的那筆 watch 不在了」），所以由呼叫端注入，
    每一條算一筆 `narrative_rewrite` 工作。

    `forward_view_backlog`／`graph_holes` 由呼叫端注入
    （它們的 authority 不在 leads 目錄）；給 `None` 表示「本次沒有讀到那個 authority」，
    輸出會照實寫 `None`，不寫 0（INV-3）。
    """
    counts: dict[str, int | None] = {seg.key: 0 for seg in SEGMENTS}
    examples: dict[str, list[str]] = {seg.key: [] for seg in SEGMENTS}
    unmapped: list[str] = []

    lead_rows = leads.values() if isinstance(leads, Mapping) else leads
    by_classifier: dict[str, int] = {}
    for lead in lead_rows:
        key = classify_lead(lead)
        if key is None:
            continue
        if key.startswith("unmapped:"):
            unmapped.append(f"{key}（{lead.get('lead_id', '?')}）")
            continue
        counts[key] = (counts[key] or 0) + 1
        if len(examples[key]) < 3:
            examples[key].append(str(lead.get("lead_id", "?")))
        if key == "triaged_go_leads":
            who = classifier_of(lead)
            by_classifier[who] = by_classifier.get(who, 0) + 1

    for watch in watches:
        key = classify_watch(watch)
        if key is None:
            continue
        if key.startswith("unmapped:"):
            unmapped.append(f"{key}（{watch.get('watch_id', '?')}）")
            continue
        counts[key] = (counts[key] or 0) + 1
        if len(examples[key]) < 3:
            examples[key].append(str(watch.get("watch_id", "?")))

    # ⚠ 固化：`todo_items` 是 Iterable，下面要走訪兩次（分段計數 ＋ gated 判定）。
    # 傳 generator 進來時第二次會是空的，而空集合不會報錯——只會安靜地少報（L13-2）。
    todo_rows = list(todo_items)
    for item in todo_rows:
        key = classify_todo(item)
        if key is None:
            continue
        if key.startswith("unmapped:"):
            unmapped.append(f"{key}（[{item.get('n', '?')}]）")
            continue
        counts[key] = (counts[key] or 0) + 1
        if len(examples[key]) < 3:
            examples[key].append(f"[{item.get('n', '?')}]")

    for brk in narrative_link_breaks:
        counts["narrative_rewrite"] = (counts["narrative_rewrite"] or 0) + 1
        if len(examples["narrative_rewrite"]) < 3:
            examples["narrative_rewrite"].append(
                f"{brk.get('ticker')}（連結 {brk.get('link_source_ref')}：{brk.get('label') or '已換版'}）")

    counts["forward_view_backlog"] = forward_view_backlog
    counts["graph_holes"] = graph_holes

    # gated 兩段由 todo_items 直接算得出來（不需要外部 authority），所以不走注入。
    from engine_b.todo import gate_pointer

    by_n = {int(i["n"]): i for i in todo_rows if i.get("n") is not None}
    for item in todo_rows:
        if item.get("resolution") or item.get("dispatch_status") != "awaiting_approval":
            continue
        pointer = gate_pointer(item)
        gate = by_n.get(pointer["n"]) if pointer else None
        if pointer is None or gate is None:
            key = "gated_no_pointer"
        elif gate.get("resolution"):
            key = "gated_gate_resolved"
        else:
            continue
        counts[key] = (counts[key] or 0) + 1
        if len(examples[key]) < 3:
            examples[key].append(f"[{item.get('n', '?')}]")

    return {
        "segments": [
            {
                "key": seg.key,
                "order": seg.order,
                "label": seg.label,
                "cost": seg.cost,
                "consumer": seg.consumer,
                "count": counts[seg.key],
                "examples": examples[seg.key],
            }
            for seg in SEGMENTS
        ],
        "unmapped": unmapped,
        # triaged_go_leads 按「PASS 分類是誰下的」分開計（Phase 4 Step 4.5b）：分類層的與互動 session 從走圖起的
        # 不是同一件事——混在一個數裡，讀的人分不出分類層有沒有在出貨（L12）。沒有分類的舊 lead 記 `unclassified`。
        "triaged_go_by_classifier": dict(sorted(by_classifier.items())),
        "mechanical_total": sum(
            (counts[s.key] or 0) for s in SEGMENTS if s.cost == "mechanical"
        ),
        # `graph_holes` 的計數是型別數、不是工作筆數（Phase 3 Step 3.1a）——加進來就是異單位相加。
        "research_total": sum(
            (counts[s.key] or 0) for s in SEGMENTS
            if s.cost == "research" and counts[s.key] is not None and s.key != "graph_holes"
        ),
        "not_work": dict(NOT_WORK),
    }


def render(observation: Mapping[str, Any]) -> str:
    """一段一行；`None` 印成「未讀到」不印 0。"""
    lines = []
    for seg in observation["segments"]:
        count = seg["count"]
        shown = "未讀到" if count is None else str(count)
        lines.append(
            f"  段{seg['order']}｜{seg['label']}：{shown}"
            f"（{seg['cost']}）→ {seg['consumer']}"
        )
    if observation["unmapped"]:
        lines.append("  ⚠ 分不到段的狀態（新工作類型？先在 queue_segments 登記 consumer）：")
        lines.extend(f"    - {row}" for row in observation["unmapped"])
    return "\n".join(lines)


__all__ = [
    "DISPATCH_STATUSES", "LEAD_STATUSES", "NOT_WORK", "SEGMENTS", "SEGMENT_BY_KEY",
    "Segment", "WATCH_STATUSES", "QueueSegmentError", "classifier_of", "classify_lead", "classify_todo",
    "classify_watch", "observe", "render", "validate_registry",
]
