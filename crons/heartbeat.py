"""crons/heartbeat.py — Daily 心跳：**零 LLM、零網路、固定五段**。

D12（2026-09-16 使用者定案）把 Daily 拆成三層——心跳／分類／研究。本檔是最底層的那一個，
規格住 `docs/ARCHITECTURE.md` §4.1。

## 它為什麼存在

現行 Daily 是一份由 LLM 組出來的 brief：LLM 沒起來、某個研究段落卡住、sandbox 擋掉一條命令，
**整份就不會發出**——而「今天沒發生事情」與「今天沒有人看」在 Discord 上長得一模一樣（L13-2：
成功與失敗在同一個訊號上同形）。心跳把「系統還活著、這些數字是多少」從研究流程裡拆出來：
它只讀本機已經存在的 authority 與 materialize 好的 state，**不判讀、不研究、不呼叫任何模型**。

## 三條不可退讓的規則

1. **五段永遠出現。** 任何一段的資料源壞掉，那一段印出降級行並宣告 `absence_kind`，
   其餘四段照印，行程式仍以 0 結束。**不得因為一段失敗就不發心跳。**
2. **「未 triage N」必印**，0 也要印——那正是 L13 說的「沒發生與沒看到不得同形」。
3. **缺席要分型。** 用的是既有的封閉字彙 `alpha.absence.ABSENCE_KINDS`（L16：分類有 SSOT
   就跟著它走，不要在這裡自創第二套），呈現層不得 parse 理由句去猜。

## 兩個容易被誤讀的設計

**`exit 0` 不是「掩蓋失敗」，是 fail visible。** 一般命令 fail closed（拒絕、非零 exit）是對的，
因為下游會拿它的輸出去做事；心跳的下游是人眼，**它一旦不發，人就什麼都看不到**。
所以它的失敗模式是「把失敗印在該印的那一行、並宣告 `absence_kind`」，不是「不發」。
（這與 INV-6 不衝突：INV-6 禁的是**靜默**回傳當前值，而這裡每一次降級都出現在輸出裡。）

**段 2「變了什麼」目前印的是狀態，不是 diff。** 門檻跨越／反證觸發／催化劑到期都是狀態
（今天成立就該說），但「現價過目標價」若連續三十天都是同兩檔，它就從訊息變成背景噪音。
真正的「較昨變動」需要昨天的心跳快照——**排程接上之前不存在昨天**，所以刻意不假裝有
（Step 2.2 接上排程後再補，屆時第一天仍然沒有昨天，那一天要誠實印出來）。

## 它明確不做的事

- **不寫任何 authority**，不碰 Neo4j、不連外、不讀憑證。唯一的寫入是 `--out` 指定的 Markdown 檔。
- **不自己發送。** outbound 仍走既有的 `scripts/publish_daily_brief.py`（那支是 fixed entry，
  且 Windows PowerShell 的 UTF-8 管線有坑，所以這裡只寫檔、由呼叫端帶 `--brief-file`）。
- **不重算任何排序或判讀。** 段 3 的佇列計數消費 `engine_b.queue_segments.observe()` 與
  `engine_b.todo.actionable_items()`；段 1／2／4 消費 `webapp` 已 materialize 的 state artifact，
  外加兩份 tracked authority（`pending_leads.json` 的 `harvest_log`、`thesis/lifecycle.json`）。
  **心跳不是第二個 current-state authority**，它是純消費端。
- **不 import `audit/`。** 那是 composition root，站在所有層之上；`crons` 是 core package，
  反向 import 會讓依賴方向倒過來（`tests/test_layer_separation.py::test_nothing_imports_audit`）。

## 今天的 consumer 是誰（INV-4：producer 指得出 consumer）

⚠ **2026-09-17（Step 2.1）交付時，唯一的 consumer 是「手動執行這條命令的人」**——
沒有任何排程會叫它。這不是漏掉，是刻意的順序：先有不依賴 LLM 的東西頂上，才拿得掉
LLM 那一層（反過來就是拆煞車不裝儀表板，L14-3）。**接上排程是 Step 2.2**，而它的載體
還要使用者決定（見 `docs/brainstorms/2026-09-17-alpha-edge-phase2-plan.md` §5）。
在那之前，ROADMAP Phase 2 的兩個驗收數字都**還沒變**——不得把「已交付」寫成「已生效」（L13）。

用法：

    python -m crons.heartbeat                     # 印 Markdown 到 stdout
    python -m crons.heartbeat --format json       # 機器可讀（測試與未來的 APP 用）
    python -m crons.heartbeat --weekly            # 第 5 段（帳號計分表）只在 weekly 有內容
    python -m crons.heartbeat --out <path>        # 寫 UTF-8 檔，交給既有 publisher
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha.absence import check_absence_kind  # noqa: E402

#: 段序是封閉字彙：**五段，不多不少**。ARCHITECTURE §4.1 是它的規格來源。
SECTION_TITLES: tuple[str, ...] = (
    "資料新鮮",
    "變了什麼",
    "佇列",
    "部位",
    "帳號計分表",
)

#: 尚未交付的能力各自指到哪個 Phase。寫在這裡是為了讓「還沒做」帶得出去向——
#: 只印「無資料」會讓使用者分不出「今天沒事」與「這件事我們根本還沒建」（AGENTS：缺席不得被壓成一句）。
PENDING_PHASE: Mapping[str, str] = {
    "power_law_stats": "ROADMAP Phase 5（D15 三個 power-law 統計量）",
    "zero_out_flags": "ROADMAP Phase 5（D2 歸零旗標與「alpha 全歸零淨值少幾 %」）",
    "account_scorecard": "ROADMAP Phase 3（D5 帳號登記表與每週計分表）",
}


@dataclass(frozen=True)
class Absence:
    """一段（或一段裡的一列）為什麼沒有值。`kind` 必在 `ABSENCE_KINDS` 內。"""

    kind: str
    reason: str

    def __post_init__(self) -> None:
        check_absence_kind(self.kind, "heartbeat absence_kind")

    def as_dict(self) -> dict[str, str]:
        return {"absence_kind": self.kind, "reason": self.reason}


@dataclass
class Section:
    order: int
    title: str
    lines: list[str] = field(default_factory=list)
    #: 整段沒有內容時的宣告；有內容時為 None。
    absence: Absence | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"order": self.order, "title": self.title, "lines": list(self.lines)}
        if self.absence is not None:
            payload["absence"] = self.absence.as_dict()
        return payload


def _pct(value: Any, digits: int = 2) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value * 100:.{digits}f}%"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 段 1｜資料新鮮
# ---------------------------------------------------------------------------

def _local_stamp(raw: str) -> str:
    """append-only log 的時戳存 UTC，但心跳整份是**本地時區**（標頭逐字寫著）。

    ⚠ 2026-09-17 實測：這一行直接印 UTC，把台北 09-16 05:33 的 harvest 顯示成
    `2026-09-15T21:33`，讀的人（包括下一個 session）會判成「前天沒跑」。
    同一份文件裡混兩個時區＝一個表示兩種語意（L12）。
    """
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return raw[:19] or "未知"


def build_freshness(*, now: datetime, state_dir: Path | None, leads_path: Path) -> Section:
    """harvest 來源 ok／fail、行情最新交易日、APP 今天有沒有 materialize。"""
    section = Section(1, SECTION_TITLES[0])

    # (a) harvest：每個來源最後一輪的結果。harvest_log 是 append-only 的執行紀錄。
    payload = _read_json(leads_path)
    log = payload.get("harvest_log") or []
    latest: dict[str, Mapping[str, Any]] = {}
    for row in log:
        source = str(row.get("source") or "?")
        latest[source] = row
    if latest:
        bad = sorted(s for s, r in latest.items() if r.get("result") != "ok")
        newest = max((str(r.get("run_at") or "") for r in latest.values()), default="")
        head = f"harvest 來源 {len(latest)} 個｜失敗 {len(bad)} 個"
        if bad:
            head += "：" + "、".join(bad)
        section.lines.append(f"{head}｜最後一輪 {_local_stamp(newest)}")
    else:
        section.lines.append("harvest 來源：**沒有任何執行紀錄**（harvest_log 為空）")

    # (b) 行情：逐檔心跳的最新完整交易日必須永遠看得到（AGENTS Beta 呈現契約）。
    beta, beta_absence = _load_state(state_dir, "beta")
    if beta_absence is not None:
        section.lines.append(f"行情：{beta_absence.reason}（{beta_absence.kind}）")
    else:
        instruments = beta.get("instruments") or []
        # `latest_close` 是一個物件，日期在 `session_date`——逐檔心跳必須明示**商品自身的**
        # 最新完整交易日（AGENTS Beta 呈現契約），所以印的是區間而不是「今天」。
        dates = sorted(
            {str((i.get("latest_close") or {}).get("session_date") or "")[:10] for i in instruments} - {""}
        )
        # `price_status` 的正常值是 `observed`；其餘（quarantined／insufficient_history／…）
        # 一律逐檔現形，不得靜默消失（INV-3）。
        degraded = sorted(
            f"{i.get('ticker')}（{i.get('price_status')}）"
            for i in instruments if str(i.get("price_status") or "") != "observed"
        )
        oldest = dates[0] if dates else "未知"
        newest_d = dates[-1] if dates else "未知"
        line = f"行情 {len(instruments)} 檔｜最新完整交易日 {oldest} ～ {newest_d}"
        line += f"｜降級 {len(degraded)} 檔" + ("：" + "、".join(degraded) if degraded else "")
        section.lines.append(line)

    # (c) APP：今天沒被 materialize 必須印出來（L12；AGENTS「APP 先讀得到，Daily 才能不印」）。
    # ⚠ 同一段裡的三件事互不相干，所以**各自降級**：APP 那一格壞掉不該把 harvest 與行情一起帶走。
    try:
        section.lines.append(_app_freshness_line(now=now, state_dir=state_dir))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"APP artifact 盤點失敗：{type(exc).__name__}")
        section.lines.append(f"APP materialize：{absence.reason}（{absence.kind}）")
    return section


def _app_freshness_line(*, now: datetime, state_dir: Path | None) -> str:
    from webapp.store import StateArtifactStore

    store = StateArtifactStore(state_dir) if state_dir is not None else StateArtifactStore()
    # 「今天」＝**本地**日曆日：心跳 07:00 台北跑，UTC 還停在昨天 23:00。用 UTC 判會把
    # 「昨天下午 materialize 的」算成今天的（2026-09-17 實測：明天 07:00 會把今天 14:44 那 6 份
    # 報成 fresh），於是 daily 再死一次也看不出來——成功與失敗在同一個訊號上同形（L13-2）。
    today = now.astimezone().date()
    fresh_today: list[str] = []
    stale: list[str] = []
    broken: list[str] = []
    for kind, payload, _freshness, reason in store.read_all():
        if reason is not None or payload is None:
            broken.append(f"{kind}（{reason}）")
            continue
        generated = str(payload.get("generated_at") or "")
        try:
            when = datetime.fromisoformat(generated.replace("Z", "+00:00"))
        except ValueError:
            broken.append(f"{kind}（generated_at 不是合法時戳）")
            continue
        (fresh_today if when.astimezone().date() >= today else stale).append(kind)
    missing = store.missing_kinds()

    parts = [f"APP artifact 今天已 materialize {len(fresh_today)} 份"]
    if stale:
        parts.append(f"**不是今天的 {len(stale)} 份**：" + "、".join(sorted(stale)))
    if missing:
        parts.append(f"從未 materialize {len(missing)} 份：" + "、".join(sorted(missing)))
    if broken:
        parts.append(f"讀不到 {len(broken)} 份：" + "、".join(sorted(broken)))
    return "｜".join(parts)


# ---------------------------------------------------------------------------
# 段 2｜變了什麼
# ---------------------------------------------------------------------------

def build_changes(*, now: datetime, state_dir: Path | None, thesis_path: Path) -> Section:
    """門檻跨越、反證觸發、催化劑到期、現價過目標價（提醒不是動作，D3）。"""
    section = Section(2, SECTION_TITLES[1])

    watches, absence = _load_state(state_dir, "watches")
    if absence is not None:
        section.lines.append(f"事件監看：{absence.reason}（{absence.kind}）")
    else:
        due = watches.get("due_this_round") or []
        fired = watches.get("fired_unconsumed") or []
        expired = watches.get("expired") or []
        section.lines.append(
            f"事件監看：本輪該查 {len(due)}｜已觸發未消費 {len(fired)}｜到期 {len(expired)}"
        )

    # thesis 生命週期：非 active 的就是「有東西變了」（L7 的五態）。
    section.lines.append(_thesis_line(now=now, thesis_path=thesis_path))

    basket, basket_absence = _load_state(state_dir, "basket")
    if basket_absence is not None:
        section.lines.append(f"現價過目標價：{basket_absence.reason}（{basket_absence.kind}）")
    else:
        rows = basket.get("rows") or []
        above = [str(r.get("company_label") or r.get("company_id")) for r in rows if r.get("price_above_target")]
        if above:
            section.lines.append(
                "現價已高於目標價（**提醒不是動作**，D3：`realized` 不觸發出場）："
                + "、".join(sorted(above))
            )
        else:
            section.lines.append("現價過目標價：0 檔")

    beta, beta_absence = _load_state(state_dir, "beta")
    if beta_absence is not None:
        section.lines.append(f"beta 門檻：{beta_absence.reason}（{beta_absence.kind}）")
    else:
        warnings = list(beta.get("warnings") or [])
        status = str(beta.get("report_status") or "?")
        line = f"beta 報告狀態 {status}｜警告 {len(warnings)} 條"
        if warnings:
            line += "：" + "、".join(str(w) for w in warnings)
        section.lines.append(line)
    return section


def _thesis_line(*, now: datetime, thesis_path: Path) -> str:
    payload = _read_json(thesis_path)
    entries = payload.values() if isinstance(payload, Mapping) else list(payload)
    today = now.date()
    by_status: dict[str, list[str]] = {}
    overdue: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        status = str(entry.get("status") or "?")
        ticker = str(entry.get("ticker") or "?")
        by_status.setdefault(status, []).append(ticker)
        due = _as_date(entry.get("next_check"))
        if due is not None and due <= today:
            overdue.append(f"{ticker}（{due.isoformat()}）")
    shape = "、".join(f"{k} {len(v)}" for k, v in sorted(by_status.items())) or "0"
    line = f"thesis：{shape}"
    if overdue:
        line += f"｜**該核查 {len(overdue)} 檔**：" + "、".join(sorted(overdue))
    else:
        line += "｜該核查 0 檔"
    return line


def _as_date(raw: Any) -> date | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 段 3｜佇列
# ---------------------------------------------------------------------------

def build_queue() -> Section:
    """新 lead N、**待 triage N（必印）**、pq1 可做 N、pq2 卡在你 N、expired N。

    ⚠ 計數一律消費 `engine_b.queue_segments.observe()`——段序是那裡的封閉字彙，
    心跳不自己數（L16：分類有 SSOT 時要跟著資料走，重造一份會立刻開始偏離）。
    """
    # ⚠ 讀取一律走 `engine_b` 自己的 loader，**不得走 `audit.sources`**——`audit/` 是
    # composition root，站在所有層之上，被任何層 import 就把依賴方向反過來了
    # （`tests/test_layer_separation.py::test_nothing_imports_audit`，2026-09-17 實測會紅）。
    from engine_b import event_watch, leads as leads_mod
    from engine_b import queue_segments as qs
    from engine_b import todo as todo_mod

    section = Section(3, SECTION_TITLES[2])

    leads = leads_mod.load().get("leads") or {}
    watches = event_watch.load_watches().get("watches") or []
    pool = todo_mod.load()
    todo_items = pool.get("items") or []
    observation = qs.observe(
        leads=leads, watches=watches, todo_items=todo_items,
        forward_view_backlog=None, coverage_gaps=None,
    )
    counts = {seg["key"]: seg["count"] for seg in observation["segments"]}

    pending_triage = counts.get("pending_triage")
    # **0 也要印**：沒有待 triage 與沒有人跑 triage 在數字上長得一樣，所以這一行是無條件的。
    section.lines.append(
        f"**未 triage {pending_triage if pending_triage is not None else '未讀到'}**"
        f"｜新 harvest lead 需要分流（零＝真的沒有，不是沒跑）"
    )

    # ⚠ `None` 是「本次沒讀到那個 authority」，不是 0——把它加成 0 會讓「沒讀到」與「真的沒有」
    # 同形（INV-3）。所以先分開，再讓沒讀到的段自己現形。
    pq1_keys = ("approved_work_orders", "triaged_go_leads", "fired_lead_requeue")
    pq1 = sum(counts[key] for key in pq1_keys if counts.get(key) is not None)
    unread = [key for key in pq1_keys if counts.get(key) is None]
    line = f"pq1 可做 {pq1}｜機械段待清 {observation['mechanical_total']}"
    if unread:
        line += f"｜⚠ 未讀到 {len(unread)} 段：" + "、".join(unread)
    section.lines.append(line)

    # ⚠ 「球在使用者手上」有 SSOT——`engine_b.todo.actionable_items()`（它已經處理了
    # `waiting_on`＝等事件、已 dispatch 的 pq1 job 不重複詢問這兩種情形）。
    # 在這裡自己用 `dispatch_status` 重數一份就是 L16 的形狀：猜錯不會有東西壞掉，只會安靜偏掉。
    active = todo_mod.active_items(pool)
    actionable = todo_mod.actionable_items(pool)
    section.lines.append(
        f"**pq2 球在你手上 {len(actionable)}**｜池中未結案 {len(active)}"
        f"（差額＝等事件或已在 pq1 跑）"
    )

    expired = sum(1 for w in watches if str(w.get("status") or "") == "expired")
    section.lines.append(f"到期歸檔 watch {expired}｜事件監看總數 {len(watches)}")

    if observation["unmapped"]:
        section.lines.append(
            f"⚠ 分不到段的狀態 {len(observation['unmapped'])} 筆——新工作類型沒有 consumer："
            + "、".join(observation["unmapped"][:5])
        )
    return section


# ---------------------------------------------------------------------------
# 段 4｜部位
# ---------------------------------------------------------------------------

def build_positions(*, state_dir: Path | None) -> Section:
    """alpha 占淨值、追蹤表、賭注帳、幾檔共用同一需求錨；未交付的兩格明確宣告 `capability_absent`。"""
    section = Section(4, SECTION_TITLES[3])

    beta, beta_absence = _load_state(state_dir, "beta")
    if beta_absence is not None:
        section.lines.append(f"alpha 占淨值：{beta_absence.reason}（{beta_absence.kind}）")
    else:
        sleeves = (beta.get("allocation") or {}).get("sleeves") or []
        alpha = next((s for s in sleeves if "瓶頸" in str(s.get("label") or "")), None)
        if alpha is None:
            section.lines.append("alpha 占淨值：配置表裡沒有 alpha sleeve（upstream_unavailable）")
        else:
            # D1：alpha 自 2026-09-16 起**只觀測不設目標**，所以這裡只印實際值不印 gap。
            section.lines.append(
                f"alpha（{alpha.get('label')}）占已投入非現金 {_pct(alpha.get('actual'))}"
                f"｜**只觀測不設目標**（D1）"
            )

    positions, pos_absence = _load_state(state_dir, "positions")
    if pos_absence is not None:
        section.lines.append(f"追蹤表：{pos_absence.reason}（{pos_absence.kind}）")
    else:
        aggregate = positions.get("aggregate") or {}
        counters = positions.get("counters") or {}
        section.lines.append(
            f"追蹤表 {aggregate.get('n', '?')} 檔｜等權絕對 {_pct(aggregate.get('absolute'))}"
            f"｜對 {aggregate.get('benchmark', '?')} 超額 {_pct(aggregate.get('excess'))}"
            f"｜正式結算過 {counters.get('measured_outcomes', '?')} 筆"
        )
        health = positions.get("anchor_health") or {}
        if health:
            section.lines.append(
                f"入圖前已漲（chasing）{health.get('chasing', '?')}/{health.get('paired', '?')} 檔"
            )

    # 賭注帳（Q2，2026-09-17）：籃子的每一列強制「有賭注 或 Abstention」。欠帳必須是一個
    # **會自己出現的常駐計數器**，不是要人打開 APP 翻表才看得到的東西（L14）。
    basket, basket_absence = _load_state(state_dir, "basket")
    if basket_absence is not None:
        section.lines.append(f"賭注帳：{basket_absence.reason}（{basket_absence.kind}）")
    else:
        ledger = basket.get("bet_ledger") or {}
        if not ledger:
            section.lines.append("賭注帳：這份 basket artifact 沒有 bet_ledger（upstream_unavailable）")
        else:
            owed = ledger.get("owed") or []
            line = (f"籃子 {ledger.get('input', '?')} 檔｜有賭注 {ledger.get('bet', '?')}"
                    f"｜刻意不主張 {ledger.get('abstained', '?')}"
                    f"｜**欠一個答案 {ledger.get('unanswered', '?')}**")
            if owed:
                line += "：" + "、".join(str(t) for t in owed[:8]) + ("…" if len(owed) > 8 else "")
            section.lines.append(line)

    ranking, rank_absence = _load_state(state_dir, "ranking")
    if rank_absence is not None:
        section.lines.append(f"需求錨集中度：{rank_absence.reason}（{rank_absence.kind}）")
    else:
        rows = ranking.get("rows") or []
        anchors: dict[str, int] = {}
        for row in rows:
            anchors[str(row.get("demand_anchor") or "（走不到錨）")] = (
                anchors.get(str(row.get("demand_anchor") or "（走不到錨）"), 0) + 1
            )
        top = sorted(anchors.items(), key=lambda kv: -kv[1])[:3]
        shape = "、".join(f"{k} {v}" for k, v in top)
        section.lines.append(
            f"可投資排序 {len(rows)} 列分佈在 {len(anchors)} 個需求錨（前三：{shape}）"
            f"——**N 檔不等於 N 個獨立機會**"
        )

    for key in ("power_law_stats", "zero_out_flags"):
        absence = Absence("capability_absent", f"還沒建，去向：{PENDING_PHASE[key]}")
        label = {"power_law_stats": "三個 power-law 統計量", "zero_out_flags": "歸零旗標與 alpha 全歸零淨值少幾 %"}[key]
        section.lines.append(f"{label}：{absence.reason}（{absence.kind}）")
    return section


# ---------------------------------------------------------------------------
# 段 5｜帳號計分表（weekly）
# ---------------------------------------------------------------------------

def build_scorecard(*, weekly: bool) -> Section:
    section = Section(5, SECTION_TITLES[4])
    if not weekly:
        section.absence = Absence("method_not_applicable", "計分表是 weekly 才算的，本輪是 daily")
        section.lines.append(f"{section.absence.reason}（{section.absence.kind}）")
        return section
    section.absence = Absence("capability_absent", f"還沒建，去向：{PENDING_PHASE['account_scorecard']}")
    section.lines.append(f"{section.absence.reason}（{section.absence.kind}）")
    section.lines.append(
        "⚠ 交付時必印**量測起始日與樣本數**，並印三個已知偏差（倖存者／後見之明／單邊上漲）"
    )
    return section


# ---------------------------------------------------------------------------
# 組裝
# ---------------------------------------------------------------------------

def _load_state(state_dir: Path | None, kind: str) -> tuple[Mapping[str, Any], Absence | None]:
    """讀一份 state artifact；讀不到就回 `upstream_unavailable`，**不丟例外**。

    這一層刻意吞掉 artifact 層的失敗：心跳的價值就在「某一格壞了其餘照發」。
    但它**不吞掉理由**——reason 逐字帶著 artifact 自己給的訊息。
    """
    from webapp.store import ArtifactUnavailable, StateArtifactStore

    store = StateArtifactStore(state_dir) if state_dir is not None else StateArtifactStore()
    try:
        payload, _freshness = store.read(kind)
    except ArtifactUnavailable as exc:
        return {}, Absence("upstream_unavailable", f"{kind} artifact 讀不到：{exc.reason}")
    except Exception as exc:  # noqa: BLE001 — 心跳不得因任何一格而整份不發
        return {}, Absence("upstream_unavailable", f"{kind} artifact 讀取失敗：{type(exc).__name__}")
    return payload, None


def _guard(order: int, title: str, fn: Callable[[], Section]) -> Section:
    """任何一段丟例外都降級成一行，**不讓整份心跳消失**（L13-2）。"""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"這一段組不出來：{type(exc).__name__}: {exc}")
        return Section(order, title, [f"{absence.reason}（{absence.kind}）"], absence)


def build_heartbeat(
    *,
    now: datetime | None = None,
    weekly: bool = False,
    state_dir: Path | None = None,
    leads_path: Path | None = None,
    thesis_path: Path | None = None,
) -> list[Section]:
    """固定五段，順序固定，**任何情況下都回五個 Section**。"""
    moment = now or datetime.now(timezone.utc)
    leads = leads_path or ROOT / "library" / "leads" / "pending_leads.json"
    thesis = thesis_path or ROOT / "thesis" / "lifecycle.json"
    sections = [
        _guard(1, SECTION_TITLES[0],
               lambda: build_freshness(now=moment, state_dir=state_dir, leads_path=leads)),
        _guard(2, SECTION_TITLES[1],
               lambda: build_changes(now=moment, state_dir=state_dir, thesis_path=thesis)),
        _guard(3, SECTION_TITLES[2], build_queue),
        _guard(4, SECTION_TITLES[3], lambda: build_positions(state_dir=state_dir)),
        _guard(5, SECTION_TITLES[4], lambda: build_scorecard(weekly=weekly)),
    ]
    assert len(sections) == len(SECTION_TITLES), "心跳必須固定五段"
    return sections


def render_markdown(sections: Sequence[Section], *, now: datetime | None = None, weekly: bool = False) -> str:
    moment = now or datetime.now(timezone.utc)
    kind = "Weekly" if weekly else "Daily"
    head = [
        f"# {kind} 心跳 — {moment.astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "> 零 LLM、零網路：只讀本機 authority 與已 materialize 的 state。**不判讀、不研究、不下單。**",
        "> 它回答「系統還活著、這些數字是多少」；要決定什麼、要研究什麼不在這裡。",
        "",
    ]
    body: list[str] = []
    for section in sections:
        body.append(f"## {section.order}. {section.title}")
        body.extend(f"- {line}" for line in section.lines)
        body.append("")
    return "\n".join(head + body).rstrip() + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daily 心跳（零 LLM、零網路、固定五段）")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--weekly", action="store_true", help="第 5 段（帳號計分表）只在 weekly 有內容")
    parser.add_argument("--out", type=Path, default=None,
                        help="把結果以 UTF-8 寫到這個檔（交給既有 publisher 的 --brief-file）")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    sections = build_heartbeat(now=now, weekly=args.weekly)
    if args.format == "json":
        text = json.dumps(
            {"generated_at": now.isoformat(), "weekly": args.weekly,
             "sections": [s.as_dict() for s in sections]},
            ensure_ascii=False, indent=2,
        ) + "\n"
    else:
        text = render_markdown(sections, now=now, weekly=args.weekly)

    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
        print(f"心跳已寫入 {args.out}（{len(text.encode('utf-8'))} bytes）", file=sys.stderr)
    else:
        sys.stdout.write(text)
    # **永遠 0**：心跳的失敗模式是「印出降級行」，不是「不發」。
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
