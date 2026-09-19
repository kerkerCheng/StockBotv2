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
  外加本機 leads authority（`pending_leads.json` 的 `harvest_log`）與 tracked thesis lifecycle。
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

#: 「尚未交付的能力各自指到哪個 Phase」那張表**已經清空並移除**（2026-09-18）。
#:
#: 它原本有三筆，最後一筆是已交付的 Phase 3 計分表——也就是說它**一個 consumer 都沒有**，
#: 而三筆裡有兩筆是已交付的能力還掛著「還沒建」。兩個毛病是同一個形狀：這種表不會壞、
#: 不會報錯、測試不會紅（L17），所以只會安靜地每天印一句假話。
#:
#: ⚠ 下次真的有「還沒建的能力」要現形時，**把去向寫在印那一行的地方**，不要再回來建一張
#: 集中表——集中表與它的使用點分開，正是上面那兩個毛病的來源（INV-4：producer 指得出 consumer）。
#: 守門測試：`tests/test_wipeout_flags.py::test_heartbeat_does_not_claim_a_delivered_capability_is_still_missing`。


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


def _x_spend_cap() -> float:
    """X 的每月花費上限。讀不到就回 0（＝不印上限），**不猜一個數字**。"""
    try:
        raw = _read_json(ROOT / "crons" / "harvest_config.json") or {}
        return float((raw.get("x_accounts") or {}).get("monthly_spend_cap_usd") or 0)
    except (OSError, ValueError, TypeError):
        return 0.0


def build_freshness(*, now: datetime, state_dir: Path | None, leads_path: Path) -> Section:
    """harvest 來源 ok／fail、行情最新交易日、APP 今天有沒有 materialize。"""
    section = Section(1, SECTION_TITLES[0])

    # (a) harvest：每個來源最後一輪的結果。harvest_log 是 append-only 的執行紀錄。
    harvest_absence: Absence | None = None
    try:
        log = list((_read_json(leads_path) or {}).get("harvest_log") or [])
    except (OSError, ValueError) as exc:
        log = []
        harvest_absence = Absence("upstream_unavailable", f"leads 檔讀不到：{type(exc).__name__}")
    latest: dict[str, Mapping[str, Any]] = {}
    for row in log:
        source = str(row.get("source") or "?")
        latest[source] = row
    if latest:
        # ⚠ `budget_exhausted` 不算失敗——它是預算保護生效，不是來源壞掉（L12：兩種語意分開）。
        # 但它**必須自己有一行**，否則「這個月不再抓了」會安靜發生而使用者以為系統還在看。
        halted = sorted(s for s, r in latest.items() if r.get("result") == "budget_exhausted")
        bad = sorted(s for s, r in latest.items()
                     if r.get("result") not in ("ok", "budget_exhausted"))
        newest = max((str(r.get("run_at") or "") for r in latest.values()), default="")
        head = f"harvest 來源 {len(latest)} 個｜失敗 {len(bad)} 個"
        if bad:
            head += "：" + "、".join(bad)
        section.lines.append(f"{head}｜最後一輪 {_local_stamp(newest)}")
        month = now.astimezone(timezone.utc).strftime("%Y-%m")
        spend = sum(float(r.get("cost_usd") or 0)
                    for r in log
                    if str(r.get("source") or "").startswith("x:")
                    and str(r.get("run_at") or "")[:7] == month)
        cap = _x_spend_cap()
        if halted:
            section.lines.append(
                f"⚠ **本月 X 花費 ${spend:.2f} 已達上限**"
                + (f" ${cap:.2f}" if cap else "")
                + f"，停抓 {len(halted)} 個來源：" + "、".join(halted)
                + "（不是故障；解除上限前不會抓，也不會漏——since_id 沒有推進）")
        elif cap:
            section.lines.append(f"本月 X 花費 ${spend:.2f} / 上限 ${cap:.2f}")
    elif harvest_absence is not None:
        section.lines.append(f"harvest 來源：{harvest_absence.reason}（{harvest_absence.kind}）")
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

    # (c) 台股月營收：**刻意不進無人值守**（ROADMAP Phase 6）——它的歷史頁按年月永久可查，
    # 漏抓隨時補得回來（L10），與「漏一天就永久漏」的重訊性質相反。所以它不需要排程，
    # 需要的是**該補的時候自己說話**：心跳每天印最新月份與落後幾個月，讓它變成會自己
    # 出現的計數器而不是要人記得的段落（L14）。
    try:
        section.lines.append(_monthly_revenue_line(now=now))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"月營收盤點失敗：{type(exc).__name__}")
        section.lines.append(f"台股月營收：{absence.reason}（{absence.kind}）")

    # (d) APP：今天沒被 materialize 必須印出來（L12；AGENTS「APP 先讀得到，Daily 才能不印」）。
    # ⚠ 同一段裡的四件事互不相干，所以**各自降級**：APP 那一格壞掉不該把 harvest 與行情一起帶走。
    try:
        section.lines.append(_app_freshness_line(now=now, state_dir=state_dir))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"APP artifact 盤點失敗：{type(exc).__name__}")
        section.lines.append(f"APP materialize：{absence.reason}（{absence.kind}）")
    return section


def _monthly_revenue_line(*, now: datetime) -> str:
    """台股月營收的新鮮度。零網路——只讀本機 Engine C。

    `lag` 是相對**法定公告期限**算的，不是相對今天：某月的營收要到次月 10 日才全部公告，
    所以「9 月 5 日還沒有 8 月營收」是正常的，「9 月 17 日還沒有」才是落後。
    """

    from engine_c.db import get_conn
    from engine_c.monthly_revenue import (
        disclosure_deadline,
        monthly_revenue_series,
        registry_taiwan_tickers,
    )

    tickers = registry_taiwan_tickers()
    if not tickers:
        return "台股月營收：registry 裡沒有台股（capability_absent）"
    conn = get_conn()
    try:
        latest: dict[str, str] = {}
        empty: list[str] = []
        for ticker in tickers:
            payload = monthly_revenue_series(conn, ticker, limit=1)
            rows = payload.get("series") or []
            if not rows:
                empty.append(ticker)
                continue
            latest[ticker] = str(rows[0].get("data_month") or "")
    finally:
        conn.close()
    if not latest:
        return f"台股月營收 {len(tickers)} 檔｜**一筆都沒有**（跑 `python -m engine_c.monthly_revenue --backfill 24`）"
    newest = max(latest.values())
    oldest = min(latest.values())
    today = now.astimezone().date().isoformat()
    # 已經過了公告期限、卻還沒抓進來的月份數。0＝跟上了。
    lag = 0
    year, month = int(oldest[:4]), int(oldest[5:7])
    while lag <= 24:  # 防呆：不可能落後兩年以上還沒被人發現
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        deadline = disclosure_deadline(f"{year:04d}-{month:02d}")
        if deadline is None or deadline > today:
            break
        lag += 1
    line = f"台股月營收 {len(latest)}/{len(tickers)} 檔｜最新 {oldest}"
    if newest != oldest:
        line += f" ～ {newest}"
    if empty:
        line += f"｜**{len(empty)} 檔一筆都沒有**：" + "、".join(empty)
    line += (f"｜⚠ 落後 {lag} 個月（跑 `python -m engine_c.monthly_revenue --sync`）"
             if lag else "｜已跟上公告期限")
    return line


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
    """門檻跨越、反證觸發、催化劑到期、現價過目標價（提醒不是動作，D3）、結構讀圖 staleness。"""
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

    # 結構讀圖（Q5，2026-09-17）：讓它**不可能安靜腐壞**。心跳只讀已 materialize 的比對結果，
    # 不查圖、不重新推理——重讀是研究，只在互動 session（D12）。
    readings, readings_absence = _load_state(state_dir, "structure_readings")
    if readings_absence is not None:
        section.lines.append(f"結構讀圖：{readings_absence.reason}（{readings_absence.kind}）")
    else:
        counts = readings.get("counts") or {}
        total = sum(int(v or 0) for v in counts.values())
        if not total:
            section.lines.append("結構讀圖：**一份都還沒寫**（`python -m alpha structure-reading <node> --add`）")
        else:
            reread = readings.get("needs_reread") or {}
            line = (f"結構讀圖 {total} 份｜現行 {counts.get('current', 0)}"
                    f"｜**該重讀 {reread.get('n', 0)}**（stale {counts.get('stale', 0)}"
                    f"／過期 {counts.get('expired', 0)}；低級 {counts.get('stale_low', 0)} 不進佇列）")
            nodes = reread.get("nodes") or []
            if nodes:
                line += "：" + "、".join(str(n) for n in nodes[:5]) + ("…" if len(nodes) > 5 else "")
            section.lines.append(line)
            triggers = readings.get("disproof_triggers") or {}
            if triggers.get("n"):
                section.lines.append(
                    f"其中 **{triggers['n']} 份同時是 disproof 觸發**（供給側多一家／反向路徑變動）："
                    + "、".join(str(n) for n in (triggers.get("nodes") or [])[:5])
                    + "——thesis 要不要改由人決定，系統只標記")

    # 目標倍數背離（2026-09-19）：判準不會腐壞，被存下來的那個**數字**會。
    # ⚠ 這一格讀的是本機 ledger ＋ Engine C 快照，**零網路、零 LLM、不重新校準**；
    # 它只是把兩個既有數字相除後比一個門檻——與段 1 的月營收行同一種計算。
    section.lines.append(_target_multiple_drift_line())

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


def _target_multiple_drift_line() -> str:
    """目標倍數與今天的市場倍數背離幾檔。**這一格壞掉不得把整段帶走**（L17-3③ 的對稱面）。"""
    try:
        from alpha.providers.valuation_drift import heartbeat_line, scan

        return heartbeat_line(scan())
    except Exception as exc:  # noqa: BLE001 — 讀不到 ledger／DB 是降級，不是心跳失敗
        return f"目標倍數背離：讀不到（{type(exc).__name__}）（upstream_missing）"


def _thesis_line(*, now: datetime, thesis_path: Path) -> str:
    # ⚠ 2026-09-17：段 1 早就寫著「同一段裡的事互不相干，所以各自降級」，但那個保護只做在
    # state artifact 上——tracked 檔讀不到時整段仍會被 _guard 帶走。對稱面沒做（L17-3）。
    try:
        payload = _read_json(thesis_path)
    except (OSError, ValueError) as exc:
        absence = Absence("upstream_unavailable", f"thesis lifecycle 讀不到：{type(exc).__name__}")
        return f"thesis：{absence.reason}（{absence.kind}）"
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

def build_queue(*, state_dir: Path | None = None) -> Section:
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

    leads_store = leads_mod.load()
    leads = leads_store.get("leads") or {}
    watches = event_watch.load_watches().get("watches") or []
    pool = todo_mod.load()
    todo_items = pool.get("items") or []
    # 結構讀圖那一段的 authority 是已 materialize 的 artifact，不在 leads 目錄——照 observe 的
    # 注入慣例給值；讀不到就給 None（「沒讀到」與「真的是 0」不得同形，INV-3）。
    readings, readings_absence = _load_state(state_dir, "structure_readings")
    stale_readings = None if readings_absence is not None else int(
        (readings.get("needs_reread") or {}).get("n") or 0)
    observation = qs.observe(
        leads=leads, watches=watches, todo_items=todo_items,
        forward_view_backlog=None, coverage_gaps=None,
        stale_structure_readings=stale_readings,
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
    # 結構讀圖那一段的 consumer 是 research-drain（互動），不是 `engine_b.cli drain`，所以
    # **不加進 pq1 的數**；但它確實是研究工作，只印在第 2 段會讓這裡的 0 被讀成「沒事做」。
    if stale_readings:
        line += f"｜＋結構讀圖待重讀 {stale_readings}（consumer：research-drain）"
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
    line = f"到期歸檔 watch {expired}｜事件監看總數 {len(watches)}"
    # ROADMAP Phase 6（D15，2026-09-17 使用者核准 A 案）：**沒有到期的等待**要自己出現。
    # 原提案是「parked 超過 60 天自動 expired」，實測推翻——479 筆 parked 裡 413 筆是
    # terminal trace_status（那是歸檔不是等待），而真正沒有任何機制會回來的只有個位數。
    # 所以落點不是新增一個 lead 狀態，是讓黑洞變成一個**會自己出現的計數器**（L14）。
    try:
        holes = leads_mod.parked_without_expiry(leads_store)
    except Exception as exc:  # noqa: BLE001 — 這一格壞掉不該把整段帶走
        line += f"｜⚠ 無到期的等待：盤點失敗（{type(exc).__name__}）"
    else:
        line += (f"｜⚠ **無到期的等待 {len(holes)}**（既沒有 watch、沒有 pq2 編號，"
                 f"trace 也沒有終局）：" + "、".join(h["source"] for h in holes[:4])
                 if holes else "｜無到期的等待 0")
    section.lines.append(line)

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
    """alpha 占淨值、追蹤表、power-law 三量、alpha 全歸零、歸零旗標帳、賭注帳、需求錨集中度。

    2026-09-18 起這一段**沒有** `capability_absent` 了——D15（power-law 三量）與 D2（歸零旗標、
    alpha 全歸零）都已交付。每一行改成「讀得到就印值、讀不到就說是哪一種讀不到」。
    """
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
                    f"｜**欠一個答案 {ledger.get('unanswered', '?')}**"
                    f"｜觀點已在 base、待決定 overlay {ledger.get('opinion_in_base', '?')}")
            if owed:
                line += "：" + "、".join(str(t) for t in owed[:8]) + ("…" if len(owed) > 8 else "")
            section.lines.append(line)
        # 量的候選（Q1）：**分開計數**——兩個宇宙問的是不同問題，合起來的數字沒有意義。
        # 多年視角（Phase 7 Step 7.4）：**常駐計數器**——「還有幾檔沒寫下目標年度」是待辦，
        # 而待辦要會自己出現，不是等人去翻（L14）。⚠ 心跳只**讀** artifact，不算橋。
        multi, multi_absence = _load_state(state_dir, "multi_year")
        if multi_absence is not None:
            section.lines.append(f"要幾倍：{multi_absence.reason}（{multi_absence.kind}）")
        else:
            counts = multi.get("counts") or {}
            owed = [r.get("ticker") for r in (multi.get("rows") or ())
                    if r.get("status") != "available"]
            line = (f"要幾倍（多年視角）{counts.get('input', '?')} 檔｜算得出 {counts.get('available', '?')}"
                    f"｜**還沒寫下目標年度 {counts.get('no_horizon', '?')}**")
            if owed:
                line += "：" + "、".join(str(t) for t in owed[:8]) + ("…" if len(owed) > 8 else "")
            section.lines.append(line)

        volume = basket.get("volume_filter") or {}
        volume_ledger = basket.get("volume_bet_ledger") or {}
        if volume:
            vline = (f"量的候選 {volume.get('input', '?')} 家（已研究、低於門檻）"
                     f"｜通過條件 {volume.get('accepted', '?')}"
                     f"｜**欠一個答案 {volume_ledger.get('unanswered', '?')}**"
                     f"｜觀點已在 base、待決定 overlay {volume_ledger.get('opinion_in_base', '?')}")
            owed = volume_ledger.get("owed") or []
            if owed:
                vline += "：" + "、".join(str(t) for t in owed[:6]) + ("…" if len(owed) > 6 else "")
            section.lines.append(vline)

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

    # 三個 power-law 統計量（D15，2026-09-18 交付）。**平均值看不到的那件事**：
    # 一檔扛全場時等權平均仍接近 0，所以這裡印的是恆等式的兩端，不是比例。
    if pos_absence is not None:
        section.lines.append(f"power-law 三量：{pos_absence.reason}（{pos_absence.kind}）")
    else:
        power = positions.get("power_law") or {}
        if not power:
            section.lines.append("power-law 三量：這份 positions artifact 沒有 power_law 鍵（upstream_unavailable）")
        else:
            top = power.get("top_contributor") or {}
            m12 = (power.get("maturity") or {}).get("12m") or {}
            # 分母 0 時 `share` 是 null 不是 0.0——「還沒有一檔滿一年」與「滿了但沒翻倍」是相反的結論。
            matured = m12.get("matured") or 0
            share = m12.get("share")
            maturity_text = (f"12 個月內達 2 倍 {m12.get('reached_2x', 0)}/{matured}"
                             f"（{_pct(share)}）" if matured else
                             f"**還沒有一檔滿 12 個月**（最長持有 {power.get('max_days_held', '?')} 天）")
            section.lines.append(
                f"power-law：籃子總報酬 {_pct(power.get('basket_total_return'))}"
                f"｜最大單檔 {top.get('ticker', '?')} {_pct(top.get('contribution'))}"
                f"／其餘 {top.get('rest_n', '?')} 檔 {_pct(top.get('rest_contribution'))}"
                f"｜曾達 2 倍 {power.get('reached_2x_ever', '?')}/{power.get('n', '?')}"
                f"（現價仍達 {power.get('reached_2x_now', '?')}）｜{maturity_text}")

    # alpha 全歸零淨值少幾 %（D2）。**純呈現、零門檻**：它就是 alpha 佔 NAV 的比例本身，
    # 不是建議、不是上限。沒有 alpha 部位時它是 0，而那是一個真實的答案不是缺席。
    if beta_absence is not None:
        section.lines.append(f"alpha 全歸零：{beta_absence.reason}（{beta_absence.kind}）")
    else:
        snapshot = (beta.get("risk") or {}).get("snapshot") or {}
        weight = snapshot.get("alpha_total_weight")
        if weight is None:
            section.lines.append("alpha 全歸零：風險快照沒有 alpha_total_weight（upstream_unavailable）")
        else:
            section.lines.append(
                f"**alpha 全歸零淨值少 {_pct(weight)}**（alpha 佔 NAV 的比例本身；純呈現、零門檻，"
                "尺寸仍由使用者決定）")

    # 歸零旗標（D2）：**盞數與檔數分開**——「一檔亮四盞」與「四檔各亮一盞」是兩件事。
    if basket_absence is not None:
        section.lines.append(f"歸零旗標：{basket_absence.reason}（{basket_absence.kind}）")
    else:
        ledger = basket.get("wipeout_ledger") or {}
        if not ledger:
            section.lines.append("歸零旗標：這份 basket artifact 沒有 wipeout_ledger（upstream_unavailable）")
        else:
            lamps = ledger.get("lamps") or {}
            line = (f"歸零旗標 {ledger.get('companies', '?')} 檔 × 4 盞："
                    f"紅 {lamps.get('red', 0)}｜黃 {lamps.get('amber', 0)}｜綠 {lamps.get('green', 0)}"
                    f"｜**灰（沒量到）{lamps.get('unlit', 0)}**——⚠ 灰不是綠")
            red = ledger.get("red_tickers") or []
            if red:
                line += "；有紅燈：" + "、".join(str(x) for x in red[:8]) + ("…" if len(red) > 8 else "")
            section.lines.append(line)
            missing_flags = ledger.get("no_flags_tickers") or []
            if missing_flags:
                section.lines.append(
                    f"歸零旗標算不出來的 {len(missing_flags)} 檔："
                    + "、".join(str(x) for x in missing_flags[:8])
                    + ("…" if len(missing_flags) > 8 else ""))
    return section


# ---------------------------------------------------------------------------
# 段 5｜帳號計分表（weekly）
# ---------------------------------------------------------------------------

def build_scorecard(*, weekly: bool, state_dir: Path | None = None) -> Section:
    """D5 帳號計分表。**只讀已 materialize 的 artifact**——心跳零網路，價格不在這裡抓。

    要更新計分表跑 `python -m webapp materialize --scorecard`；心跳讀不到就誠實說讀不到，
    **不偷偷重建**（APP 呈現契約的同一條紀律）。
    """
    section = Section(5, SECTION_TITLES[4])
    if not weekly:
        section.absence = Absence("method_not_applicable", "計分表是 weekly 才算的，本輪是 daily")
        section.lines.append(f"{section.absence.reason}（{section.absence.kind}）")
        return section
    card, absence = _load_state(state_dir, "account_scorecard")
    if absence is not None or not card:
        section.absence = absence or Absence(
            "upstream_unavailable", "計分表 artifact 還沒 materialize 過")
        section.lines.append(f"{section.absence.reason}（{section.absence.kind}）")
        section.lines.append("→ 跑 `python -m webapp materialize --scorecard` 之後這一段才有內容")
        return section
    counts = card.get("tier_counts") or {}
    section.lines.append("tier 分佈：" + "／".join(f"{k} {v}" for k, v in counts.items())
                         + f"｜計分表 as-of {card.get('as_of')}")
    for account in card.get("accounts") or []:
        metrics = account.get("metrics") or {}
        first = (account.get("metrics_first_call_per_symbol") or {}).get("excess_returns") or {}
        section.lines.append(
            f"**{account.get('harvest_key')}**｜tier `{account.get('tier')}`｜"
            f"量測 {account.get('measurement_start')} → {account.get('measurement_end')}｜"
            f"具名點名 {account.get('named_calls')} 則／{account.get('distinct_symbols')} 檔")
        for key, cell in (metrics.get("excess_returns") or {}).items():
            line = f"  {key}：{_score_cell(cell)}"
            if key in first:
                line += f"｜每檔只算最早一次：{_score_cell(first[key])}"
            section.lines.append(line)
        for label, key in (("點名前 30 天漲幅", "prior_30d_move"), ("追源成功率", "trace_success_rate"),
                           ("假設命中率", "hypothesis_hit_rate"), ("no-go 率", "no_go_rate")):
            section.lines.append(f"  {label}：{_score_cell(metrics.get(key) or {})}")
    for bias in card.get("known_biases") or []:
        section.lines.append(f"⚠ {bias}")
    return section


def _score_cell(cell: Mapping[str, Any]) -> str:
    """一格：有值印值與 n，沒值印**為什麼沒值**。兩者不得同形。"""
    if cell.get("value") is None:
        return f"沒有值（{cell.get('absence_kind')}）——{str(cell.get('reason') or '')[:70]}"
    return f"{float(cell['value']) * 100:+.2f}%（n={cell.get('n')}）"


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
        _guard(3, SECTION_TITLES[2], lambda: build_queue(state_dir=state_dir)),
        _guard(4, SECTION_TITLES[3], lambda: build_positions(state_dir=state_dir)),
        _guard(5, SECTION_TITLES[4], lambda: build_scorecard(weekly=weekly, state_dir=state_dir)),
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
