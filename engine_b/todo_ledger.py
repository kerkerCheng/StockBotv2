"""待做清單（短版 ⑤「下一次研究要做的」）與**涵蓋登記表**——「把這些計數歸零就不漏球」的唯一 owner。

2026-10-22 使用者：「要確保以後的東西都不會被計數漏掉」「我只要把那些待做計數歸零，就不會漏球？這是我的宗旨」。
當天盤點（六個 registry 逐一窮舉）：舊 ⑤ 九格歸零時仍會漏的有——敘事該重寫（只在完整心跳）、缺分類（只以「daily
失敗 1 步」現形）、停放未處置對照、到期沒人處置、沒有等待指回的 active 假說（9 筆，到期會被安靜歸檔）、等使用者卻
沒鑄號也沒 watch 的停放 lead、敘事撤回後還在等的喚醒 watch、敘事騎已換版的讀圖。舊 ⑤ 還把「等你提供的文件」
（使用者的動作）算成研究待做、把敘事來源的 11 條同時算進「未檢」與「敘事該重寫」。

兩件事住這裡：

1. `LEDGER`＋`collect()`：⑤ 的每一格（順序固定）。**計數一律呼叫既有的唯一判定**（`queue_segments.observe` 的段、
   `leads.classification_gaps`、`impact.undisposed`、`event_watch.expiry_counters`…），不在這裡重數（L16）。
   每格附「工作量」（判定幾次、幾檔）與「最老幾天」——醒了幾條不等於要做幾次（10-22：未檢 45＝14 次判定）。
   讀不到的格是 None（「未讀到」不是 0，INV-3）。
2. `COVERAGE`：系統裡**每一種狀態**落在哪裡——⑤ 的哪一格、③ 待你決定、有到期的等事件、daily 機械段、終局、
   或研究題庫（走圖問句：機會不是承諾）。`tests/test_todo_ledger.py` 從各狀態字彙的 SSOT 列舉、逐一要求有登記；
   **以後新增一種狀態沒登記，測試就紅**——這是「以後也不會被計數漏掉」的機械保證（L14：會自己出現的計數器）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class LedgerRow:
    key: str              # 快照鍵（todo.*）
    label: str            # 短版印的字
    unit: str             # count 的單位
    command: str          # 歸零怎麼做


#: ⑤ 的每一格，順序＝短版印的順序。**全部是研究 session 做得掉的**（使用者的動作住 ③／③b，不放這裡）。
LEDGER: tuple[LedgerRow, ...] = (
    LedgerRow("todo.pending_triage", "未 triage", "則",
              "daily ⑦ 自動清；超過上限、LLM 失敗、或無內文（daily 不送分類，failure log #105）由互動 session "
              "讀全文後 `python -m engine_b.cli triage`（無內文的列在 `engine_b.cli drain` 段 0）"),
    LedgerRow("todo.unclassified", "缺分類", "則",
              "依 skills/signal-triage 產分類 → `python scripts/backfill_lead_classification.py --from-json … --apply`"),
    LedgerRow("todo.leads", "待深挖 lead", "則", "`/research-drain`（`python -m engine_b.cli drain`）做到入圖包、停放或已入圖"),
    LedgerRow("todo.semantic", "未檢", "條", "`python -m engine_b.event_watch semantic-queue` → `judge`（一組判一次）"),
    LedgerRow("todo.wake_hold", "叫醒擋下待確認", "條",
              "`python -m engine_b.event_watch wake-queue` → `wake-judge`（一份文件判一次；daily 預篩標觸及的自己放行）"),
    LedgerRow("todo.narrative", "敘事該重寫", "檔", "research-drain「敘事該重寫」段 → `python -m alpha brief <T> --add spec.json`"),
    LedgerRow("todo.reading", "讀圖該重讀", "份", "`python -m alpha structure-reading <node> --check` → 重讀，或判無關 `event_watch reactivate`"),
    LedgerRow("todo.layer_note", "層說明該重讀", "份", "`python -m alpha layer-note <node> --add`（換版）"),
    LedgerRow("todo.t2", "T2 命中待檢", "則", "`python -m engine_b.watch_poll queue` → judge"),
    LedgerRow("todo.hypothesis", "假設對照", "筆", "research-drain 段 0b：對照一手 → `engine_b.hypotheses verify` → `event_watch consume`"),
    LedgerRow("todo.disproof_touched", "反證觸及待處置", "條", "48 小時內：照該條的 action_48h 處置（重讀／重寫／thesis 複查）"),
    LedgerRow("todo.confirm_touched", "加碼條件觸及待處置", "條", "重寫該檔敘事（acknowledged_touched 逐條處置）"),
    LedgerRow("todo.expired", "到期沒人處置", "條", "依到期類型：重讀、重寫、thesis 複查，或 `todo sync` 鑄 watch_decision"),
    LedgerRow("todo.undisposed", "停放未處置對照", "組", "`python -m engine_b.impact --lead <id>` → 補停放理由逐條處置"),
    LedgerRow("todo.broken_waits", "接不上的等待", "筆", "補 watch（有到期）或鑄 pq2；敘事已撤回的喚醒 watch 收掉"),
    LedgerRow("todo.registry_rescan", "名冊變動未重算", "則", "`python -m engine_b.cli registry-rescan`"),
    LedgerRow("todo.thesis_due", "thesis 該核查未進 pq2", "條", "`python -m engine_b.todo sync`（鑄 thesis_lifecycle）"),
    LedgerRow("todo.gated", "工單收尾", "筆", "`python -m engine_b.todo gated`"),
    # 盲點修法第 20 條③（2026-11-03；使用者 11-02「隨機抽查 開subagent這件事 其實你就當成我是開綠燈吧」）
    LedgerRow("todo.admission_audit", "入圖包抽中待核", "包",
              "`python -m engine_b.admission_audit status` → 抽中的包交乾淨 context 唯讀 reviewer 從頭核"
              "（research-drain「入圖包抽查」）→ `python -m engine_b.admission_audit record <n> --found-by 抽查 …`"),
    LedgerRow("todo.edge_no_narrative", "邊緣卻沒敘事", "檔", "研究那一檔、寫第一份敘事（非邊緣的不寫）"),
    # 盲點修法第 18＋16 條（2026-11-03；使用者同日問「那系統會叫我去深挖嗎？還是得靠我自主？」——研究 session 去深挖）：
    # 加碼條件的 watch 只會被**新**文件叫醒，答案若在已經存在的年報、法說裡不會自己醒——要有一格叫人去查
    LedgerRow("todo.addon_unchecked", "加碼條件還沒查", "檔",
              "research-drain 段 5「加碼條件還沒查」：深挖清單十項逐項查（引用｜不適用：理由｜加碼條件：c<n>）→ "
              "`python -m alpha brief <T> --add spec.json`（depth_check）"),
    # 2026-11-04 盲點審查複查：起始門改了，但舊門寫的缺 X 只在各自的 watch 醒來或到期才重寫（Q3 財報季剛重寫的那幾份等的是
    # 2027 的年報）——一次性的母體，清完恆為 0（新的缺 X 都在新門下寫）
    LedgerRow("todo.old_gate_missing", "缺 X 還是舊門寫的", "檔",
              "research-drain 段 5「舊門缺 X 重判」：X 是起始門缺的（押的層沒讀、判讀是 neither、反證沒寫、會死嗎紅）→ 換版、"
              "理由寫明缺起始門哪一項；X 是加碼門缺的（讀到邊、客戶具名、營收拆分、深挖清單）→ 換版宣告可開、X 寫進 confirm[] "
              "→ `python -m alpha brief <T> --add spec.json`"),
    # 2026-10-29 使用者（個股頁）：「怎麼確保呈現的精神不變…之後才不會又慢慢爛掉」——敘事換版、故事就過期，
    # 首屏退回印依據；過期與沒寫是會自己出現的計數，不是要人記得的事（L14）
    LedgerRow("todo.story", "故事還沒寫", "檔",
              "`python -m alpha stories --gaps` → 照 research-drain「故事」段寫 → `python -m alpha stories --check "
              "spec.json` → `--add spec.json`"),
)
LEDGER_KEYS: tuple[str, ...] = tuple(r.key for r in LEDGER)
LEDGER_BY_KEY: Mapping[str, LedgerRow] = {r.key: r for r in LEDGER}

# ---------------------------------------------------------------------------
# 涵蓋登記表：每一種狀態落在哪裡
# ---------------------------------------------------------------------------

#: 目的地（封閉）：⑤ 的格（`todo.*`）或下面幾種「不是研究待做」。
DESTINATIONS: Mapping[str, str] = {
    "decision": "③ 待你決定（pq2 編號、可開待你選）／③b 等你提供的文件（球在使用者）",
    "wait": "有到期的等事件（醒來或到期才回到某一格；『無到期的等待』與『接不上的等待』兩格守著）",
    "mechanical": "daily 機械段自己清（清不掉時由對應的格或 daily 健康度現形）",
    "terminal": "終局（不是待做）",
    "question_bank": "研究題庫（走圖問句：機會不是承諾；research-drain 段 4 每次掃，不歸零）",
    "phase_plan": "Phase plan／ROADMAP（開發與 Phase 步驟；/phase-run 與 7.5 檢查點消費，『下一步貼』在研究計數全 0 時推它）",
}

COVERAGE: Mapping[str, str] = {
    # --- lead 狀態（engine_b.leads.ALL_STATUSES）
    "lead:pending": "todo.pending_triage",
    "lead:triaged_go": "todo.leads",
    "lead:researching": "todo.leads",
    "lead:action_prepared": "decision",          # 等 ra_admission 的 go
    "lead:parked": "wait",                       # 追源 watch 有到期；接不上的進 todo.broken_waits
    "lead:triaged_no_go": "terminal",
    "lead:applied": "terminal",
    # --- 佇列段（engine_b.queue_segments.SEGMENTS）
    "segment:pending_triage": "todo.pending_triage",
    "segment:fired_lead_requeue": "mechanical",  # daily ⑨ consume-fired
    "segment:fired_pq2_wake": "mechanical",      # daily ⑩ todo sync 翻回 ③
    "segment:semantic_pending_check": "todo.semantic",
    "segment:wake_screen_hold": "todo.wake_hold",      # #96：追源／讀圖叫醒擋下待確認
    "segment:fired_reading_reread": "todo.reading",
    "segment:narrative_rewrite": "todo.narrative",
    "segment:fired_hypothesis_check": "todo.hypothesis",
    "segment:approved_work_orders": "todo.leads",
    "segment:triaged_go_leads": "todo.leads",
    "segment:forward_view_backlog": "todo.edge_no_narrative",
    "segment:graph_holes": "question_bank",
    "segment:poll_hits_pending": "todo.t2",
    "segment:gated_gate_resolved": "todo.gated",
    "segment:gated_no_pointer": "todo.gated",
    # --- watch 狀態（engine_b.queue_segments.WATCH_STATUSES）
    "watch:active": "wait",
    "watch:fired": "todo.semantic",              # 依段分到 semantic／narrative／reading／hypothesis（上面那幾段）
    "watch:consumed": "terminal",
    "watch:expired": "todo.expired",             # 有 expiry_resolution 的是終局；沒有的進這一格
    # --- 到期類型（engine_b.event_watch.expiry_class）
    "expiry:decision": "decision",               # todo sync 鑄 watch_decision
    "expiry:thesis_review": "decision",          # thesis_lifecycle pq2
    "expiry:reread": "todo.reading",
    "expiry:rewrite": "todo.narrative",
    "expiry:trace": "terminal",                  # 追源到期轉 watch_expired 終局（計數現形）
    "expiry:pq2": "decision",                    # 指向的編號翻回 ③
    "expiry:reading": "todo.reading",            # 讀圖重讀等待到期：那份讀圖該重讀
    # --- pq2 派工狀態（engine_b.queue_segments.DISPATCH_STATUSES；None／"" ＝沒派工的一般項目）
    "dispatch:none": "decision",
    "dispatch:queued": "todo.leads",
    "dispatch:researching": "todo.leads",
    "dispatch:awaiting_approval": "decision",
    "dispatch:completed": "terminal",
    "dispatch:parked": "terminal",
    # --- 假說（engine_b.hypotheses.HYPOTHESIS_STATUSES）
    "hypothesis:active": "wait",                 # 必須有 watch 指回；沒有的進 todo.broken_waits
    "hypothesis:verified": "terminal",
    "hypothesis:refuted": "terminal",
    "hypothesis:expired": "terminal",            # 到期前一週 watch 先醒（2026-10-22 起逐筆登記）
    "hypothesis:archived": "terminal",
    # --- thesis（crons.heartbeat.THESIS_STATUSES）
    "thesis:active": "wait",                     # next_check／催化劑到 → todo sync 鑄 thesis_lifecycle（③）
    "thesis:watch": "wait",
    "thesis:review_required": "decision",
    "thesis:realized": "decision",
    "thesis:revised": "decision",                # 改寫 memo 掛 pq2（例：COHR [836]）；is_due 沒鑄的進 todo.thesis_due
    "thesis:retired": "terminal",
    # --- 候選板（alpha.candidates 的組）
    # 可開：每天重驗起始門（失效進 todo.narrative）；要不要進是使用者的 → 短版 ③「可開待你選」（這一版敘事還沒選過的）；
    # 加碼條件還沒查進 todo.addon_unchecked（2026-11-03 第 18＋16 條：等回落與只差已定價併回可開，那兩個登記一起拿掉）
    "candidate:open": "decision",
    "candidate:missing": "wait",                 # wake_brief watch 有到期
    "candidate:pass": "terminal",
    "candidate:held": "terminal",
    "candidate:not_multiple": "todo.narrative",  # 非邊緣卻有敘事：撤回（research-drain 規定不替非倍率寫敘事）
    "candidate:edge_unmeasurable": "wait",       # 宣告可開、邊緣判定少一個輸入：不放行、等量得到（2026-10-30 起缺 X／不要照敘事分組）
    "candidate:legacy": "todo.narrative",
    "candidate:precondition_failed": "todo.narrative",
    "candidate:no_narrative": "todo.edge_no_narrative",   # 只算邊緣或量不到的；非邊緣的是終局（不寫敘事）
    # --- 讀圖狀態（alpha.structure_reading.staleness.READING_STATUSES）
    "reading:current": "terminal",
    "reading:stale_low": "terminal",             # 只有證據等級變：記錄、不優先
    "reading:stale": "todo.reading",
    "reading:expired": "todo.reading",
    # --- 個股頁故事（alpha.providers.stories.STORY_GAP_KINDS）
    "story:never": "todo.story",
    "story:stale": "todo.story",                 # 敘事換版：舊故事不算數，首屏退回印依據
    # --- 其他來源
    "impact:undisposed": "todo.undisposed",
    "lead:classification_gap": "todo.unclassified",
    "lead:parked_without_expiry": "todo.broken_waits",
    "lead:requires_user_without_pq2": "todo.broken_waits",
    "watch:orphan_wake_brief": "todo.broken_waits",
    "hypothesis:active_without_watch": "todo.broken_waits",
    "brief:rides_superseded_reading": "todo.narrative",   # 候選板清單 kind=rides（候選板是唯一 owner，2026-10-29）
    "brief:new_edges_unread": "todo.narrative",           # 候選板清單 kind=new_edges：正文寫完後圖上有新邊、敘事沒讀過
    "brief:reading_kind_changed": "todo.narrative",       # 候選板清單 kind=reading_kind：正文寫時騎的讀圖判讀與現行不同（2026-11-03）
    "brief:supply_count_changed": "todo.narrative",       # 候選板清單 kind=supply_count：供給側家數與正文寫時不同（2026-11-03）
    "brief:link_break": "todo.narrative",
    # 可開／已持有的深挖清單還有沒查的項目（`alpha.candidates.addon_unchecked_rows`；2026-11-03 第 18＋16 條）
    "depth_check:unchecked": "todo.addon_unchecked",
    # 起始門改版前寫的缺 X（`alpha.candidates.START_GATE_SINCE`；2026-11-04）：重判一次
    "candidate:missing_before_start_gate": "todo.old_gate_missing",
    "registry:stale_lead_entities": "todo.registry_rescan",
    "thesis:due_not_minted": "todo.thesis_due",
    "disproof:touched": "todo.disproof_touched",
    "confirm:touched": "todo.confirm_touched",
    "layer_note:reread": "todo.layer_note",
    "pq2:source_trace_review": "decision",
    "pq2:awaiting_external": "wait",
    "daily:step_failed": "mechanical",           # 短版 ④ 健康度；持續性的（例：缺分類）另有自己的格
    "plan:open_step": "phase_plan",
    "roadmap:pending_user": "phase_plan",
    "failure_log:open": "phase_plan",
    # --- 入圖包抽查（engine_b.admission_audit.AUDIT_STATES；盲點修法第 20 條）
    "admission_audit:not_sampled": "terminal",
    "admission_audit:sampled_unreviewed": "todo.admission_audit",
    "admission_audit:reviewed": "terminal",
    "admission_audit:dropped": "terminal",       # 抽中但使用者已 drop：gate 已經說不，不必再核
}


def destination_label(dest: str) -> str:
    if dest in LEDGER_BY_KEY:
        return f"⑤ {LEDGER_BY_KEY[dest].label}"
    return DESTINATIONS[dest]


# ---------------------------------------------------------------------------
# 收集
# ---------------------------------------------------------------------------

@dataclass
class LedgerCount:
    key: str
    label: str
    count: int | None                 # None＝未讀到
    work: str | None = None           # 例：「14 次判定」「6 檔」
    oldest_days: int | None = None
    note: str | None = None
    reason: str | None = None         # 未讀到的理由
    progress: int | None = 0          # 這一格裡「歸零時有一檔離決定更近」的件數（`PROGRESS_LABELS`）；None＝算不出

    def as_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label, "count": self.count, "work": self.work,
                "oldest_days": self.oldest_days, "note": self.note, "reason": self.reason, "progress": self.progress}


def _days_since(stamp: Any, today: date) -> int | None:
    try:
        moment = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return max(0, (today - moment.astimezone().date()).days)


def _oldest(stamps: Iterable[Any], today: date) -> int | None:
    days = [d for d in (_days_since(s, today) for s in stamps) if d is not None]
    return max(days) if days else None


def _woken_at(watch: Mapping[str, Any]) -> Any:
    return (watch.get("woken_by") or {}).get("at") or watch.get("fired_at")


def active_hypotheses_without_watch(hypotheses: Iterable[Mapping[str, Any]],
                                    watches: Iterable[Mapping[str, Any]]) -> list[str]:
    """active 假說裡，沒有任何 active／fired watch 用 hypothesis_ref 指回的（到期會被安靜歸檔——INV-2 黑洞）。"""
    watched = {str(w.get("hypothesis_ref")) for w in watches
               if w.get("hypothesis_ref") and w.get("status") in ("active", "fired")}
    return sorted(str(h.get("hypothesis_id")) for h in hypotheses
                  if h.get("status") == "active" and str(h.get("hypothesis_id")) not in watched)


def requires_user_without_pq2(leads: Mapping[str, Mapping[str, Any]],
                              watches: Iterable[Mapping[str, Any]],
                              todo_items: Iterable[Mapping[str, Any]] = ()) -> list[str]:
    """停放、寫著等使用者（trace_requires_user），卻沒有 pq2_ref、也沒有 active 追源 watch 的 lead——完全隱形
    （`parked_without_expiry` 豁免了它：以為 pq2 那端有生命週期，其實那端沒有項目；2026-10-22 盤點 2 則）。
    對稱面同 `leads.parked_without_expiry`：待辦池有**未結案**項目以 `ref_id` 指回這筆 lead 也算有 pq2——「向你要文件」型的
    `source_trace_review` 是收集器從 lead 推出來的，lead 這端永遠不會回寫 `pq2_ref`；只看 lead 這端，每一筆開了口的都被算成
    接不上（2026-10-31 實測 3 則全是這一型：[897]–[899] 都開著）。"""
    watched = {str(w.get("wake_lead")) for w in watches if w.get("wake_lead") and w.get("status") in ("active", "fired")}
    asked = {str(i.get("ref_id")) for i in todo_items if i.get("ref_id") and not i.get("resolved_at")}
    out = []
    for lead_id, lead in leads.items():
        refs = lead.get("refs") or {}
        if (lead.get("status") != "parked" or lead_id in watched or lead_id in asked
                or str(refs.get("pq2_ref") or "").strip()):
            continue
        if str(refs.get("trace_requires_user") or "").lower() in {"1", "true", "yes"}:
            out.append(str(lead_id))
    return sorted(out)


def orphan_wake_briefs(watches: Iterable[Mapping[str, Any]], briefs: Iterable[Any]) -> list[str]:
    """還在等的 wake_brief watch，但那家公司的現行敘事**不在等**（撤回、改判不要／可開／已持有）——醒了會替一份
    不在等的敘事產生重寫工作（failure log #34；10-22 KLIC／MXL／HPS-A.TO／FORM 四筆）。
    ⚠ 只看狀態、不看 watch_id：一份缺 X／等回落的敘事可以有好幾筆喚醒（AXTI 的 ew_0148 與財報後的 ew_1433）。
    「在等」照 `engine_b.narrative_watches.WAITING_STATES`（寫入時收喚醒 watch 的同一份，L16）——舊的等回落讀成可開，
    但當時建的喚醒照舊等到期、醒了叫重寫，不算接不上。"""
    from engine_b.narrative_watches import WAITING_STATES

    waiting = {str(getattr(b, "company_id", "")) for b in briefs
               if getattr(getattr(b, "candidate_state", None), "state", None) in WAITING_STATES}
    return sorted(str(w.get("watch_id")) for w in watches
                  if w.get("wake_brief") and w.get("status") == "active" and str(w.get("wake_brief")) not in waiting)


#: 候選板清單裡「敘事落後」的幾種（`alpha.providers.candidates.board_rewrite`）→ ⑤ 工作描述的字。
#: 候選板是唯一 owner（ROADMAP「敘事 stale 計數器」同源，2026-10-29）：⑤ 只讀它的清單，不自己再算一份。
#: `reading_kind`／`supply_count`（2026-11-03，ROADMAP「敘事 stale 計數器」②④）：正文寫的時候騎的讀圖與這一格現行的
#: 讀圖相比，判讀變了／供給側家數變了——換騎不夠，正文要改。
#: 已回落（#116）、重開達成／沒寫重開（#124）2026-11-03 隨等回落併回可開退役：價格動了不再叫研究重寫。
BEHIND_KINDS: Mapping[str, str] = {"rides": "騎舊讀圖", "reading_kind": "判讀變了", "supply_count": "家數變了",
                                   "new_edges": "新邊沒讀"}


def _narrative_companies(watches: Sequence[Mapping[str, Any]], briefs: Sequence[Any]) -> dict[str, list[str]]:
    """narrative_rewrite 段的 watch → 公司（brief: 來源查現行敘事的 brief_id；wake_brief 直接是 co:*）。"""
    from engine_b.queue_segments import classify_watch

    by_brief = {str(getattr(b, "brief_id", "")): str(getattr(b, "company_id", "") or getattr(b, "ticker", ""))
                for b in briefs}
    out: dict[str, list[str]] = {}
    for w in watches:
        if classify_watch(w) != "narrative_rewrite":
            continue
        if w.get("wake_brief"):
            who = str(w["wake_brief"])
        else:
            ref = str(w.get("source_ref") or "")
            who = by_brief.get(ref.removeprefix("brief:").split("#")[0], ref.split("#")[0])
        out.setdefault(who, []).append(str(w.get("watch_id")))
    return out


#: 「持股或可開名下」的列（2026-11-04 盲點審查複查）：持股的反證醒了是出場紀律的工作（48 小時）；宣告可開的列（含前提失效）
#: 被反證卡住，判完就回到短版 ③ 或改判——這兩種歸零時都有一檔離決定更近（`PROGRESS_LABELS` 的判準）。其餘列（缺 X、不要、附組）的
#: 反證工作照舊只看年紀。
DECISION_ROWS: tuple[tuple[str, str], ...] = (("groups", "held"), ("groups", "open"), ("side_groups", "precondition_failed"))


def decision_rows(candidates: Mapping[str, Any] | None) -> tuple[list[Mapping[str, Any]] | None, str | None]:
    """持股、可開、前提失效三組的列（候選板唯一 owner；列上的 `blocking_watch_ids` 由 `engine_b.narrative_watches.
    blocking_watches` 算，起始門同一份判定——L16）。回 (列, None)，或 (None, 為什麼算不出)：候選板沒讀到、持股沒讀到
    （持股名下的反證數不到）、舊板（列上沒有那一格）——算不出不是 0（INV-3）。"""
    if candidates is None:
        return None, "候選板未讀到"
    if ((candidates.get("holdings") or {}).get("status") or "ok") != "ok":
        return None, "持股沒讀到——持股名下的反證數不到"
    rows = [r for bucket, group in DECISION_ROWS for r in ((candidates.get(bucket) or {}).get(group) or ())]
    if any(not isinstance(r.get("blocking_watch_ids"), list) for r in rows):
        return None, "候選板是舊版（列上沒有卡住的 watch 那一格）"
    return rows, None


def collect(*, today: date, leads_store: Mapping[str, Any], watches: Sequence[Mapping[str, Any]],
            todo_items: Sequence[Mapping[str, Any]], hypotheses: Sequence[Mapping[str, Any]],
            briefs: Sequence[Any] | None,
            reading_needs_reread: int | None, layer_note_reread: int | None,
            candidates: Mapping[str, Any] | None, thesis_due: Sequence[str] | None,
            loaders: Mapping[str, Callable[[], Any]] | None = None) -> list[LedgerCount]:
    """⑤ 每一格的計數。注入的值是呼叫端讀過的 authority（心跳讀 artifact 與 ledger）；None＝那個 authority 沒讀到。
    `loaders`：要另外讀檔才算得出的格（停放未處置對照、名冊重算、缺分類、故事還沒寫、入圖包抽查帳）——測試可換掉。"""
    from engine_b import event_watch as ew
    from engine_b import queue_segments as qs

    leads = leads_store.get("leads") or {}
    loaders = dict(loaders or {})
    rows: dict[str, LedgerCount] = {r.key: LedgerCount(r.key, r.label, None) for r in LEDGER}

    def put(key: str, count: int | None, **extra: Any) -> None:
        row = rows[key]
        row.count = count
        for name, value in extra.items():
            setattr(row, name, value)

    def guarded(key: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 — 一格讀不到不帶走其他格（INV-3：未讀到 ≠ 0）
            rows[key].count, rows[key].reason = None, f"{type(exc).__name__}: {str(exc)[:60]}"
            rows[key].progress = None

    breaks = []
    if briefs is not None:
        try:
            from engine_b.narrative_watches import link_breaks

            breaks = link_breaks(briefs, watches=watches)
        except Exception:  # noqa: BLE001
            breaks = []
    observation = qs.observe(leads=leads, watches=watches, todo_items=todo_items,
                             forward_view_backlog=None, graph_holes=None, narrative_link_breaks=breaks)
    seg = {s["key"]: s["count"] for s in observation["segments"]}
    held_or_open, _ = decision_rows(candidates)
    decision_ids = (None if held_or_open is None
                    else {str(i) for r in held_or_open for i in r["blocking_watch_ids"]})

    def decision_progress(items: Iterable[Mapping[str, Any]]) -> int | None:
        """這一格的 watch 裡，卡著持股或可開那幾列的條數（`decision_rows`）；算不出是 None。"""
        return None if decision_ids is None else sum(1 for w in items if str(w.get("watch_id")) in decision_ids)

    gaps_holder: dict[str, set[str]] = {"ids": set()}

    def unclassified() -> None:
        from engine_b.leads import classification_gaps

        gaps = (loaders.get("classification_gaps") or (lambda: classification_gaps(dict(leads_store))))()
        gaps_holder["ids"] = {str(g.get("lead_id")) for g in gaps}
        put("todo.unclassified", len(gaps_holder["ids"]))

    guarded("todo.unclassified", unclassified)

    def pending() -> None:
        from engine_b.lead_text import held_pending

        stamps = [lead.get("first_seen") for lead in leads.values() if lead.get("status") == "pending"]
        # 分類器看不到任何內文的 daily 不送分類（failure log #105）——這幾則不會被 ⑦ 清掉，要點名
        held = held_pending(leads)
        put("todo.pending_triage", seg.get("pending_triage"), oldest_days=_oldest(stamps, today),
            note=f"其中無內文 {len(held)} 則要互動 session 讀全文後 triage" if held else None)

    guarded("todo.pending_triage", pending)

    def lead_work() -> None:
        from engine_b.leads import last_entered_pq1_at

        active = {lid: lead for lid, lead in leads.items() if lead.get("status") in ("triaged_go", "researching")}
        withheld = gaps_holder["ids"] & set(active)
        orders = seg.get("approved_work_orders") or 0
        count = len(active) - len(withheld) + orders
        stamps = [last_entered_pq1_at({**lead, "lead_id": lid}) for lid, lead in active.items() if lid not in withheld]
        bits = []
        if orders:
            bits.append(f"含已 go 的工單 {orders}")
        if withheld:
            bits.append(f"另 {len(withheld)} 則缺分類先補（drain 會扣著）")
        put("todo.leads", count, oldest_days=_oldest(stamps, today), note="；".join(bits) or None, progress=orders)

    guarded("todo.leads", lead_work)

    def semantic() -> None:
        pending_watches = [w for w in watches if qs.classify_watch(w) == "semantic_pending_check"]
        groups = ew.semantic_queue_groups(pending_watches, leads_store)
        put("todo.semantic", len(pending_watches), work=f"{len(groups)} 次判定" if pending_watches else None,
            oldest_days=_oldest((_woken_at(w) for w in pending_watches), today),
            progress=decision_progress(pending_watches))

    guarded("todo.semantic", semantic)

    def wake_hold() -> None:
        held = [w for w in watches if qs.classify_watch(w) == "wake_screen_hold"]
        documents = {str((w.get("woken_by") or {}).get("lead_id")) for w in held}
        unrelated = sum(1 for w in held if ew.wake_screen(w) == "held_unrelated")
        bits = [f"{len(documents)} 份文件"] if held else []
        if held:
            bits.append(f"預篩標無關 {unrelated}、還沒預篩 {len(held) - unrelated}")
        put("todo.wake_hold", len(held), work="；".join(bits) or None,
            oldest_days=_oldest((_woken_at(w) for w in held), today), progress=decision_progress(held))

    guarded("todo.wake_hold", wake_hold)

    def narrative() -> None:
        companies = _narrative_companies(watches, briefs or ())
        for row in breaks:
            who = str(row.get("company_id") or row.get("ticker") or row.get("brief_id") or "?")
            companies.setdefault(who, []).append("連結斷")
        # 騎舊讀圖、新邊沒讀：讀候選板的清單（唯一 owner），點名是哪幾檔——drain 照名字去改（INV-4：指得出 consumer）
        behind: dict[str, set[str]] = {kind: set() for kind in BEHIND_KINDS}
        for item in (candidates or {}).get("narrative_rewrite") or ():
            kind = str(item.get("kind"))
            if kind in BEHIND_KINDS:
                companies.setdefault(str(item.get("company_id") or item.get("ticker")), []).append(BEHIND_KINDS[kind])
                behind[kind].add(str(item.get("ticker")))
        counts = (candidates or {}).get("counts") or {}
        board = [f"{k} {counts.get(k)}" for k in ("precondition_failed", "legacy", "not_multiple") if counts.get(k)]
        extra = sum(int(counts.get(k) or 0) for k in ("precondition_failed", "legacy", "not_multiple"))
        watch_n = sum(1 for ids in companies.values() for i in ids if i.startswith("ew_"))
        stamps = [_woken_at(w) for w in watches if qs.classify_watch(w) == "narrative_rewrite"]
        bits = [f"watch 醒 {watch_n} 條"] if watch_n else []
        bits += [f"{BEHIND_KINDS[k]} {len(names)}（{'、'.join(sorted(names))}）" for k, names in behind.items() if names]
        if breaks:
            bits.append(f"連結斷 {len(breaks)}")
        bits += [{"precondition_failed": "前提失效", "legacy": "舊版", "not_multiple": "非邊緣仍有敘事"}[b.split()[0]]
                 + " " + b.split()[1] for b in board]
        # 沒讀到不是 0（INV-3）：候選板讀不到，後幾種都沒算進來；圖讀不到，新邊沒讀沒算；讀圖紀錄讀不到（或舊板沒有這一格），
        # 判讀／家數變了沒算
        if candidates is None:
            note = "候選板未讀到——騎舊讀圖、判讀／家數變了、新邊沒讀、前提失效沒算進來"
        else:
            notes = []
            if (candidates.get("new_edges_check") or {}).get("status") != "ok":
                notes.append("新邊沒讀這次沒算（候選板沒讀到圖）")
            check = candidates.get("reading_change_check") or {}
            if check.get("status") != "ok":
                notes.append("判讀／家數變了這次沒算（候選板沒讀到讀圖紀錄，或是舊板）")
            elif check.get("unchecked"):
                notes.append(f"判讀／家數變了有 {check['unchecked']} 格沒比成（正文寫時騎的讀圖紀錄找不到）")
            note = "；".join(notes) or None
        # 進展（2026-11-04）：持股或可開的列，被**敘事來源**的反證卡著（醒來／觸及／到期未判、本版沒處置）的檔數——
        # 重寫完它就回到 ③ 或改判；騎舊讀圖、新邊沒讀這類落後照舊只看年紀
        progress = (None if held_or_open is None else
                    sum(1 for r in held_or_open
                        if set(r["blocking_watch_ids"]) & {str(i) for i in r.get("rewrite_watch_ids") or ()}))
        put("todo.narrative", len(companies) + extra, work="；".join(bits) or None,
            oldest_days=_oldest(stamps, today), note=note, progress=progress)

    guarded("todo.narrative", narrative)
    put("todo.reading", reading_needs_reread)
    put("todo.layer_note", layer_note_reread)

    def t2() -> None:
        status = ew.t2_status({"watches": list(watches)}, today=today)
        put("todo.t2", status["hits_pending"], work=f"{seg.get('poll_hits_pending')} 條等待" if status["hits_pending"] else None)

    guarded("todo.t2", t2)

    def hypothesis() -> None:
        fired = [w for w in watches if qs.classify_watch(w) == "fired_hypothesis_check"]
        put("todo.hypothesis", len(fired), oldest_days=_oldest((_woken_at(w) for w in fired), today))

    guarded("todo.hypothesis", hypothesis)

    def touched() -> None:
        from engine_b import disproof

        c = disproof.disproof_counts(list(watches), readings=disproof.current_readings(),
                                     coverage=None, layer_notes=disproof.current_layer_notes())
        value = None if c.get("lifecycle_unreadable") else c["touched_pending"]
        put("todo.disproof_touched", value, progress=value)
        k = disproof.confirm_counts(list(watches))
        put("todo.confirm_touched", k["touched_pending"], progress=k["touched_pending"])

    guarded("todo.disproof_touched", touched)
    if rows["todo.confirm_touched"].count is None and rows["todo.disproof_touched"].reason:
        rows["todo.confirm_touched"].reason = rows["todo.disproof_touched"].reason
        rows["todo.confirm_touched"].progress = None

    def expired() -> None:
        c = ew.expiry_counters({"watches": list(watches)}, today=today)
        # 進展只數卡著持股或可開的那幾條（`expiry_unresolved` 的同一個定義：expired 而且沒有 expiry_resolution）
        unresolved = [w for w in watches if w.get("status") == "expired" and not w.get("expiry_resolution")]
        put("todo.expired", c["expiry_unresolved"], progress=decision_progress(unresolved))

    guarded("todo.expired", expired)

    def undisposed() -> None:
        from engine_b import impact

        rows_ = (loaders.get("undisposed") or (lambda: impact.undisposed(leads)))()
        put("todo.undisposed", len(rows_), work=f"{len({r['lead_id'] for r in rows_})} 則 lead" if rows_ else None)

    guarded("todo.undisposed", undisposed)

    def broken() -> None:
        from engine_b.leads import parked_without_expiry

        holes = (loaders.get("parked_without_expiry") or (lambda: parked_without_expiry(dict(leads_store))))()
        users = requires_user_without_pq2(leads, watches, todo_items)
        orphans = orphan_wake_briefs(watches, briefs or ()) if briefs is not None else []
        hyps = active_hypotheses_without_watch(hypotheses, watches)
        parts = [(len(holes), "停放沒到期"), (len(users), "等使用者卻沒 pq2"), (len(orphans), "敘事不等的喚醒 watch"),
                 (len(hyps), "假說沒 watch")]
        put("todo.broken_waits", sum(n for n, _ in parts),
            work="；".join(f"{label} {n}" for n, label in parts if n) or None)

    guarded("todo.broken_waits", broken)

    def rescan() -> None:
        from engine_b.registry_batch import stale_lead_entities

        put("todo.registry_rescan", (loaders.get("stale_lead_entities") or (lambda: stale_lead_entities(leads_store)))())

    guarded("todo.registry_rescan", rescan)

    def thesis() -> None:
        if thesis_due is None:
            return
        open_refs = " ".join(str(i.get("title") or "") + str(i.get("ref_id") or "") for i in todo_items
                             if not i.get("resolved_at") and str(i.get("type") or "") == "thesis_lifecycle")
        missing = [t for t in thesis_due if t not in open_refs]
        put("todo.thesis_due", len(missing), work="、".join(missing) or None)

    guarded("todo.thesis_due", thesis)
    put("todo.gated", (seg.get("gated_gate_resolved") or 0) + (seg.get("gated_no_pointer") or 0))

    def admission_audit() -> None:
        from engine_b import admission_audit as aa

        audit_rows, problems = (loaders.get("admission_audit_ledger") or aa.load_ledger)()
        if problems:                        # 帳讀不懂就不知道哪幾包核過：未讀到，不是 0（INV-3）
            rows["todo.admission_audit"].reason = f"抽查帳：{problems[0][:60]}"
            return
        pending = aa.status(todo_items, audit_rows, today=today)["unreviewed"]
        added = {int(i["n"]): i.get("added_at") for i in todo_items if i.get("n") is not None}
        put("todo.admission_audit", len(pending), work="、".join(f"[{n}]" for n in pending) or None,
            oldest_days=_oldest((added.get(n) for n in pending), today))

    guarded("todo.admission_audit", admission_audit)

    def edge_no_narrative() -> None:
        if candidates is None:
            return
        rows_ = [r for r in candidates.get("no_narrative") or () if (r.get("edge") or {}).get("state") != "not_edge"]
        put("todo.edge_no_narrative", len(rows_), work="、".join(str(r.get("ticker")) for r in rows_[:5]) or None)

    guarded("todo.edge_no_narrative", edge_no_narrative)

    def addon_unchecked() -> None:
        # 可開／已持有、深挖清單還有沒查的檔（`alpha.candidates.addon_unchecked_rows`——候選板計數同一份，L16）。
        # 候選板沒讀到、持股沒讀到（已持有那一半數不到）、舊板（列上沒有這一格）都是未讀到，不是 0（INV-3）
        from alpha.candidates import ADDON_GROUPS, addon_unchecked_rows
        from alpha.narrative.contracts import RECORD_VERSION_V2

        cell = rows["todo.addon_unchecked"]
        groups = (candidates or {}).get("groups") or {}
        if candidates is None:
            cell.reason, cell.progress = "候選板未讀到", None
            return
        if ((candidates.get("holdings") or {}).get("status") or "ok") != "ok":
            cell.reason, cell.progress = "持股沒讀到——已持有那一半數不到", None
            return
        if any("addon_unchecked" not in r for g in ADDON_GROUPS for r in groups.get(g) or ()):
            cell.reason, cell.progress = "候選板是舊版（列上沒有加碼條件那一格）", None
            return
        found = addon_unchecked_rows(groups)
        work = "、".join(f"{r.get('ticker')}（{len(r['addon_unchecked'])} 項）" if r.get("record_version") == RECORD_VERSION_V2
                         else f"{r.get('ticker')}（沒有 v2 敘事）" for r in found)
        put("todo.addon_unchecked", len(found), work=work or None, progress=len(found))

    guarded("todo.addon_unchecked", addon_unchecked)

    def old_gate_missing() -> None:
        # 缺 X 列上的 `declared_before_start_gate`（候選板唯一 owner，L16）。候選板沒讀到、舊板（列上沒有那一格）都是未讀到，
        # 不是 0（INV-3）。每一檔重判完都可能直接可開——是進展格
        cell = rows["todo.old_gate_missing"]
        if candidates is None:
            cell.reason, cell.progress = "候選板未讀到", None
            return
        waiting = list((candidates.get("groups") or {}).get("missing") or ())
        if any("declared_before_start_gate" not in r for r in waiting):
            cell.reason, cell.progress = "候選板是舊版（缺 X 列上沒有起始門改版前那一格）", None
            return
        found = [r for r in waiting if r.get("declared_before_start_gate")]
        put("todo.old_gate_missing", len(found), work="、".join(str(r.get("ticker")) for r in found[:8]) or None,
            oldest_days=max((r["stall_days"] for r in found if isinstance(r.get("stall_days"), int)), default=None),
            progress=len(found))

    guarded("todo.old_gate_missing", old_gate_missing)

    def story() -> None:
        from alpha.providers.stories import gaps_now

        gaps = (loaders.get("story_gaps") or (lambda: gaps_now(today=today)[0]))()
        kinds = {"never": "從沒寫", "stale": "敘事換版"}
        bits = [f"{label} {n}" for kind, label in kinds.items() if (n := sum(1 for g in gaps if g["kind"] == kind))]
        put("todo.story", len(gaps), work="；".join(bits) or None)

    guarded("todo.story", story)
    return [rows[r.key] for r in LEDGER]


# ---------------------------------------------------------------------------
# 呈現與「下一步貼」
# ---------------------------------------------------------------------------

def render_cells(counts: Sequence[LedgerCount]) -> list[str]:
    """⑤ 兩行：非 0 的逐格（附工作量與最老天數）；0 的列名字（每格都要出現——L14 常駐）、有註記的照帶
    （「新邊沒讀這次沒算」在 0 的時候吞掉，就和真的 0 同形——INV-3）；未讀到的另列。"""
    live, zero, unread = [], [], []
    for row in counts:
        if row.count is None:
            unread.append(row.label)
        elif row.count == 0:
            zero.append(row.label + (f"（{row.note}）" if row.note else ""))
        else:
            unit = LEDGER_BY_KEY[row.key].unit
            bits = [b for b in (row.work, f"最老 {row.oldest_days} 天" if row.oldest_days else None, row.note) if b]
            live.append(f"{row.label} {row.count} {unit}" + (f"（{'；'.join(bits)}）" if bits else ""))
    lines = ["- 要做：" + ("｜".join(live) if live else "沒有——每一格都是 0")]
    lines.append("- 0 的格：" + ("、".join(zero) if zero else "沒有"))
    if unread:
        lines.append("- ⚠ 未讀到（不是 0）：" + "、".join(unread))
    return lines


#: 「進展格」（盲點修法 §1 第 2 條，2026-11-03；整體盲點審查 2026-11-01 §1.3：十天 15 段 drain、週額度 99%、候選狀態轉換 0，
#: 推薦條件是「任何研究格 > 0」，而停放是合法終局、歸零永遠做得到）。判準：**會叫人動手的數字，要問它歸零時有沒有任何一檔
#: 離決定更近；沒有的只當健康度、只在太老時叫人。** 推 `/research-drain` 只看下列幾件、或任一格最老 ≥ `MAINTENANCE_NUDGE_DAYS` 天。
#: 可開待你選不在這裡：要不要進是使用者的（短版 ③），drain 歸零不了它，放進來就是恆亮的燈（L14-4）。
#: 2026-11-03（第 18＋16 條）：「重開達成／已回落」隨等回落退役；「加碼條件還沒查」進來——查完一檔，那一檔的加碼決定就有根據。
#: 2026-11-04（盲點審查複查）：未檢、叫醒擋下、到期沒人處置、敘事該重寫四格裡**卡著持股或可開**的反證進來（`decision_rows`）——
#: 醒來待判的反證原本只算年紀：3081.TWO、4979.TWO、AXTI 離可開只差一次判定，提示卻寫「只剩維護」；持股的反證醒了最慢 7 天才叫人，
#: 「出場認反證、48 小時」實際變成 7 天。其餘列（缺 X、不要）的反證照舊只看年紀——全算進來就回到恆亮（L14-4）。
PROGRESS_LABELS: Mapping[str, str] = {"todo.disproof_touched": "反證觸及", "todo.confirm_touched": "加碼條件觸及",
                                      "todo.addon_unchecked": "加碼條件還沒查", "todo.leads": "使用者 go 的工單",
                                      "todo.semantic": "持股或可開名下的反證醒來待判",
                                      "todo.wake_hold": "持股或可開名下的叫醒擋下",
                                      "todo.expired": "持股或可開名下的反證到期沒判",
                                      "todo.narrative": "持股或可開名下的敘事反證待處置",
                                      "todo.old_gate_missing": "缺 X 還是舊門寫的"}
MAINTENANCE_NUDGE_DAYS = 7
#: `snapshot_progress` 的鍵——心跳快照「只存不比」的封閉清單由這裡導出（L16）。
SNAPSHOT_PROGRESS_KEYS: tuple[str, ...] = ("todo.progress", "todo.oldest_days")


def progress_summary(counts: Sequence[LedgerCount]) -> dict[str, Any]:
    """進展件數（任一進展格算不出 → None，未讀到不是 0）、明細、有工作的格裡最老幾天。短版「下一步貼」與心跳快照的
    `todo.progress`／`todo.oldest_days`（SessionStart 提示讀快照）同一份算法（L16）。"""
    rows = [r for r in counts if r.key in PROGRESS_LABELS]
    total = None if any(r.progress is None for r in rows) else sum(int(r.progress or 0) for r in rows)
    parts = [f"{PROGRESS_LABELS[r.key]} {r.progress}" for r in rows if r.progress]
    oldest = max((r.oldest_days for r in counts if r.count and r.oldest_days is not None), default=None)
    return {"progress": total, "parts": parts, "oldest_days": oldest}


def snapshot_progress(counts: Sequence[LedgerCount]) -> dict[str, int | None]:
    """心跳快照多存的兩個值（不進較昨 diff）：`phase_status_hint` 只讀得到快照，靠它們做同一個判斷。"""
    summary = progress_summary(counts)
    return dict(zip(SNAPSHOT_PROGRESS_KEYS, (summary["progress"], summary["oldest_days"]), strict=True))


def next_prompt(counts: Sequence[LedgerCount] | Mapping[str, int | None], *, decision_batch: str | None = None,
                phase_step: str | None = None, theme_due: bool = False) -> str:
    """下一步貼什麼——**只由計數機械導出**，而且有「沒有要貼的」分支（L14：恆亮的燈沒有資訊量）。

    順序：③ 有建議的批次行 → 研究格 > 0 而且（進展格非 0、或最老 ≥ 7 天、或進展算不出）推 `/research-drain`；
    研究格 > 0 但只剩維護 → 「只剩維護」（照 plan Q8 每週 2–3 次清）＋題材到期照提 → 研究全 0 但 Phase plan 有下一步推
    `/phase-run` → 題材掃描到期說「掃題材」→ 全 0「今天沒有要貼的」。"""
    if isinstance(counts, Mapping):
        values = dict(counts)
        # 快照沒有這兩個鍵（2026-11-03 之前的舊快照）→ 判不了是不是只剩維護，照舊推 drain
        summary = {"progress": values.get("todo.progress") if "todo.progress" in values else None, "parts": [],
                   "oldest_days": values.get("todo.oldest_days")}
    else:
        values = {r.key: r.count for r in counts}
        summary = progress_summary(counts)
    labels = {r.key: r.label for r in LEDGER}
    nonzero = [(k, v) for k, v in values.items() if k in labels and isinstance(v, int) and v > 0]
    unread = [k for k in LEDGER_KEYS if values.get(k) is None]
    parts: list[str] = []
    if decision_batch:
        parts.append(f"先貼 ③ 那一行：`{decision_batch}`")
    progress, oldest = summary["progress"], summary["oldest_days"]
    stale = oldest is not None and oldest >= MAINTENANCE_NUDGE_DAYS
    if nonzero and (progress is None or progress > 0 or stale):
        urgent = "（反證觸及：48 小時內）" if values.get("todo.disproof_touched") else ""
        clear = "、".join(f"{labels[k]} {v}" for k, v in nonzero)
        why = []
        if progress is None:
            why.append("進展格算不出，照舊推")
        elif progress:
            why.append(("進展：" + "、".join(summary["parts"])) if summary["parts"] else f"進展 {progress} 件")
        if stale:
            why.append(f"最老 {oldest} 天")
        parts.append(f"`/research-drain`{urgent}（{'；'.join(why)}）——要清的：{clear}")
    elif nonzero:
        clear = "、".join(f"{labels[k]} {v}" for k, v in nonzero)
        parts.append(f"只剩維護（沒有一格歸零會讓哪一檔離決定更近、最老不到 {MAINTENANCE_NUDGE_DAYS} 天："
                     f"照 plan Q8 每週 2–3 次清，今天不必為它開 `/research-drain`）——要清的：{clear}")
        if theme_due:
            parts.append("說「掃題材」（題材掃描已到期）")
    elif phase_step:
        parts.append(f"`/phase-run`（研究計數全 0；下一個 Step：{phase_step}）")
    elif theme_due:
        parts.append("說「掃題材」（研究計數全 0、題材掃描已到期）")
    if unread and not nonzero:
        parts.append("⚠ 有格未讀到，先確認 daily 是否正常：" + "、".join(labels[k] for k in unread))
    return "；然後 ".join(parts) if parts else "今天沒有要貼的（研究計數全 0、③ 沒有待決、Phase 沒有下一步）"


__all__ = ["BEHIND_KINDS", "COVERAGE", "DESTINATIONS", "LEDGER", "LEDGER_BY_KEY", "LEDGER_KEYS", "LedgerCount",
           "DECISION_ROWS", "LedgerRow", "MAINTENANCE_NUDGE_DAYS", "PROGRESS_LABELS", "SNAPSHOT_PROGRESS_KEYS",
           "active_hypotheses_without_watch", "collect", "decision_rows", "destination_label", "next_prompt",
           "orphan_wake_briefs",
           "progress_summary", "render_cells", "requires_user_without_pq2", "snapshot_progress"]
