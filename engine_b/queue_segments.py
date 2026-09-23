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
- 不判定 forward view／coverage 缺口／結構讀圖／重複節點候選的**內容**——那四段的計數
  由呼叫端注入（authority 分別是 analyst view artifact、Neo4j、state artifact、Neo4j），
  本模組只登記它們的 consumer。
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
        "research", "python -m engine_b.cli list --status pending --by-priority（daily Step 2）",
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
    Segment(
        "coverage_gaps", 6, "圖的 🔴 研究缺口與 🟡 建模待補",
        "research", "research-drain 第三段（python -m query.coverage_gaps）",
    ),
    Segment(
        "duplicate_node_candidates", 6, "名字重疊的重複節點候選（沒人提過的那些）",
        "research", "research-drain 第三段：python -m query.duplicate_nodes（判定同一個 → pq2 ra_admission）",
        "2026-09-18 V3：它與 coverage_gaps 是同一頁的兩題，但方向相反——後者問「誰供應這個節點」，"
        "前者問「這個節點是不是旁邊那個」。重複節點正是 coverage 🔴 的誤報來源。"
        "⚠ 只收 `unmentioned`（registry 從沒提過的）：registry 已經寫過 note 的那些不算待辦，"
        "否則清單會恆亮而恆亮＝零鑑別力（L14-4）。合併仍逐筆 ra_admission，本段只提名。",
    ),
    Segment(
        "stale_structure_readings", 6, "結構讀圖與圖不再一致（分級後仍會改變 A/B 讀法的）",
        "research", "research-drain：重跑 `python -m query.structure <node>` 後改寫讀圖紀錄",
        "2026-09-17 Q5：偵測到 stale 只是 producer——沒有東西真的去重讀，計數器只會愈長愈大"
        "（L13「已排入不等於已推進」、INV-4「producer 指得出 consumer」）。"
        "⚠ 只收 `stale`／`expired`：`stale_low`（只有 evidence 變）不進佇列，"
        "否則 binary 的 stale 會恆亮而恆亮＝零鑑別力（L14-4）。",
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
    "watch:expired": "到期歸檔（Expiry check 另管）",
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


def classify_watch(watch: Mapping[str, Any]) -> str | None:
    status = str(watch.get("status") or "")
    if status not in WATCH_STATUSES:
        return f"unmapped:watch:{status or '<empty>'}"
    if status == "fired":
        if watch.get("wake_pq2"):
            return "fired_pq2_wake"
        if watch.get("wake_lead"):
            return "fired_lead_requeue"
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

def observe(
    *,
    leads: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]] = (),
    watches: Iterable[Mapping[str, Any]] = (),
    todo_items: Iterable[Mapping[str, Any]] = (),
    forward_view_backlog: int | None = None,
    coverage_gaps: int | None = None,
    stale_structure_readings: int | None = None,
    duplicate_node_candidates: int | None = None,
) -> dict[str, Any]:
    """由資料反推每一段有幾筆工作。

    `forward_view_backlog`／`coverage_gaps`／`stale_structure_readings`／
    `duplicate_node_candidates` 由呼叫端注入
    （它們的 authority 不在 leads 目錄）；給 `None` 表示「本次沒有讀到那個 authority」，
    輸出會照實寫 `None`，不寫 0（INV-3）。
    """
    counts: dict[str, int | None] = {seg.key: 0 for seg in SEGMENTS}
    examples: dict[str, list[str]] = {seg.key: [] for seg in SEGMENTS}
    unmapped: list[str] = []

    lead_rows = leads.values() if isinstance(leads, Mapping) else leads
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

    counts["forward_view_backlog"] = forward_view_backlog
    counts["coverage_gaps"] = coverage_gaps
    counts["stale_structure_readings"] = stale_structure_readings
    counts["duplicate_node_candidates"] = duplicate_node_candidates

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
        "mechanical_total": sum(
            (counts[s.key] or 0) for s in SEGMENTS if s.cost == "mechanical"
        ),
        "research_total": sum(
            (counts[s.key] or 0) for s in SEGMENTS
            if s.cost == "research" and counts[s.key] is not None
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
    "Segment", "WATCH_STATUSES", "QueueSegmentError", "classify_lead", "classify_todo",
    "classify_watch", "observe", "render", "validate_registry",
]
