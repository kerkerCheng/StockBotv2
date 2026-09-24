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


def build_freshness(*, now: datetime, state_dir: Path | None, leads_path: Path,
                    run_record_path: Path | None = None) -> Section:
    """daily 執行紀錄、harvest 來源 ok／fail、行情最新交易日、APP 今天有沒有 materialize。"""
    section = Section(1, SECTION_TITLES[0])

    # (0) daily 執行紀錄（Phase 1 Step 1.2a）：失敗步驟逐條、排程比對、鎖、工作區。
    # ⚠ 心跳**只讀**這份紀錄——排程比對由 `crons/daily_task.py` 開 subprocess 查，心跳不得自己查。
    try:
        section.lines.extend(_daily_run_lines(now=now, record_path=run_record_path))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"daily 執行紀錄盤點失敗：{type(exc).__name__}")
        section.lines.append(f"daily 執行紀錄：{absence.reason}（{absence.kind}）")

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
        stale = _harvest_staleness(newest, now=now)
        if stale is not None:
            section.lines.append(stale)
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

    # (c2) FX 觀測新鮮度（2026-09-19）。**它是一個已知會過期、而且沒有人在補的東西**：
    # 四筆 fx_rate 觀測的 `_note` 逐字寫著「現價 bar_date 換了就要補新的一筆」，
    # 消費端只接受 ±3 天內（`alpha.fx.FX_AS_OF_TOLERANCE_DAYS`）——於是跨幣別標的會在
    # 觀測過期那天安靜地從「隱含報酬算得出來」退回「算不出來」，而**沒有任何地方印出這件事**。
    # 這裡不修它（補觀測是寫 append-only authority，要人核准），只讓它每天自己說話（L18-5）。
    try:
        section.lines.append(_fx_freshness_line(now=now))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"FX 觀測盤點失敗：{type(exc).__name__}")
        section.lines.append(f"FX 觀測：{absence.reason}（{absence.kind}）")

    # (d) APP：今天沒被 materialize 必須印出來（L12；AGENTS「APP 先讀得到，Daily 才能不印」）。
    # ⚠ 同一段裡的四件事互不相干，所以**各自降級**：APP 那一格壞掉不該把 harvest 與行情一起帶走。
    try:
        section.lines.append(_app_freshness_line(now=now, state_dir=state_dir))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"APP artifact 盤點失敗：{type(exc).__name__}")
        section.lines.append(f"APP materialize：{absence.reason}（{absence.kind}）")
    return section


#: daily 執行紀錄的位置（`crons/daily_task.py` 寫、心跳只讀）。
RUN_RECORD_DIR = ROOT / "library" / "private" / "heartbeat"


def run_record_path_for(now: datetime) -> Path:
    return RUN_RECORD_DIR / f"daily_run_{now.astimezone().strftime('%Y-%m-%d')}.json"


def _load_run_record(path: Path | None, *, now: datetime) -> tuple[Mapping[str, Any] | None, str | None]:
    """(紀錄, 問題)。今天沒有紀錄是一個**要說出來**的狀態，不是空白。"""
    target = path or run_record_path_for(now)
    if not target.is_file():
        return None, "今天沒有 daily 執行紀錄（daily 沒跑，或這份心跳不是 daily 產的）"
    try:
        record = _read_json(target)
    except (OSError, ValueError) as exc:
        return None, f"daily 執行紀錄讀不到：{type(exc).__name__}"
    if not isinstance(record, dict):
        return None, "daily 執行紀錄格式不對"
    return record, None


def _daily_run_lines(*, now: datetime, record_path: Path | None) -> list[str]:
    record, problem = _load_run_record(record_path, now=now)
    if record is None:
        return [f"⚠ {problem}"]
    steps = [row for row in record.get("steps") or [] if isinstance(row, Mapping)]
    ok = [r for r in steps if r.get("status") == "ok"]
    # 凡不是 ok／skipped 都算失敗（R2-a NB-1：capability_violation、rate_limited 原本漏算，段 1 印「失敗 0」、
    # 段 3 卻印「本輪失敗」——兩段同形矛盾，L13）。`running` 是心跳正在跑的那一步，不算。
    bad = [r for r in steps if r.get("status") not in ("ok", "skipped", "running", None)]
    skipped = [r for r in steps if r.get("status") == "skipped"]
    head = f"daily（run {str(record.get('run_id') or '?')[:8]}）：{len(ok)} 步完成"
    if bad:
        head += f"｜**失敗 {len(bad)}**：" + "、".join(
            f"{r.get('key')}（{r.get('status')}"
            + (f"，exit {r.get('exit')}" if r.get("exit") not in (None, 0) else "") + "）"
            for r in bad)
    else:
        head += "｜失敗 0"
    if skipped:
        reasons: dict[str, int] = {}
        for r in skipped:
            key = str(r.get("reason") or "?").split("：", 1)[0]
            reasons[key] = reasons.get(key, 0) + 1
        head += f"｜跳過 {len(skipped)}（" + "、".join(f"{k} {n}" for k, n in reasons.items()) + "）"
    lines = [head]
    violation = record.get("capability_violation")
    if isinstance(violation, Mapping):
        lines.append(f"⚠ **LLM 能力檢查不符（{violation.get('step')}）**：{'；'.join(violation.get('violations') or [])}"
                     "——輸出已丟棄、沒有寫入")
    if record.get("llm_config_error"):
        lines.append(f"⚠ LLM 設定讀不到或不合法：{record['llm_config_error']}——LLM 步驟全部跳過，其他步驟照跑")
    if record.get("pre_loop_error"):
        lines.append(f"⚠ **daily 進步驟迴圈前就失敗**：{record['pre_loop_error']}——今天只組了心跳")
    lock = record.get("writer_lock") or {}
    if isinstance(lock, Mapping) and lock.get("acquired") is False:
        lines.append(f"⚠ **沒拿到 writer lock**：{lock.get('reason')}——所有寫入步驟跳過")
    elif isinstance(lock, Mapping) and lock.get("renewal_failed_at"):
        lines.append(f"⚠ **writer lock 續期失敗（{lock.get('renewal_failed_at')}）**：{lock.get('reason')}"
                     "——其後的寫入步驟跳過")
    dirty = [p for p in record.get("dirty_paths") or [] if p]
    if dirty:
        total = record.get("dirty_count") or len(dirty)
        lines.append(f"⚠ 開跑時工作區不乾淨（{total} 個路徑）：" + "、".join(str(p) for p in dirty[:3]))
    check = record.get("schedule_check") or {}
    status = check.get("status") if isinstance(check, Mapping) else None
    expected = (check.get("expected") or {}) if isinstance(check, Mapping) else {}
    if status == "match":
        lines.append(f"排程設定與 config 一致（{expected.get('time')}／時限 "
                     f"{expected.get('execution_time_limit_minutes')} 分鐘）")
    elif status == "mismatch":
        lines.append(f"⚠ **排程設定與 config 不一致**：{'、'.join(check.get('diffs') or [])}"
                     f"（實際 {check.get('actual')}）｜修正：`{check.get('fix')}`")
    else:
        lines.append(f"⚠ 排程設定讀不到（unknown）：{(check or {}).get('reason') or '沒有比對結果'}")
    return lines


def _harvest_newest_at(raw: str) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _harvest_stale_hours() -> float | None:
    try:
        from engine_b.routine_config import load_schedule

        return float(load_schedule()["harvest_stale_hours"])
    except Exception:  # noqa: BLE001 — 讀不到門檻就不判過期（呼叫端照實說）
        return None


def harvest_age_hours(newest_raw: str, *, now: datetime) -> float | None:
    newest = _harvest_newest_at(newest_raw) if newest_raw else None
    if newest is None:
        return None
    return (now - newest).total_seconds() / 3600


def _harvest_staleness(newest_raw: str, *, now: datetime) -> str | None:
    """harvest 最後一輪超過 `harvest_stale_hours` → ⚠。2026-09-22 起 Codex 暫停，harvest 兩天沒跑而
    段 3 照印「未 triage 0」——那個 0 是「沒跑」不是「沒有」（L13 同形）。"""
    limit = _harvest_stale_hours()
    age = harvest_age_hours(newest_raw, now=now)
    if age is None:
        return None
    if limit is None:
        return f"harvest 新鮮度門檻讀不到（config schedule.harvest_stale_hours）｜最後一輪 {age:.0f} 小時前"
    if age > limit:
        return f"⚠ **harvest 已 {age:.0f} 小時沒跑**（門檻 {limit:g} 小時）——新文件沒有進來"
    return None


def _fx_freshness_line(*, now: datetime) -> str:
    """跨幣別換算用的 FX 觀測還在不在容忍窗內。零網路——只讀本機 Engine C。

    容忍窗的 SSOT 是 `alpha.fx.FX_AS_OF_TOLERANCE_DAYS`，**這裡不重寫那個 3**
    （重寫一份就會開始各自漂移，L16）。

    ⚠ 容忍窗比的是**現價 bar_date**，這裡用今天當參考——所以這行偏保守：它可能在
    bar_date 還沒推進時就先喊過期。保守的方向是對的（它只會讓人早點去看），
    但**這行不是判定，判定在 `alpha/fx.py`**，兩者不得互相冒充。
    """
    from alpha.fx import FX_AS_OF_TOLERANCE_DAYS
    from engine_c.db import get_conn

    conn = get_conn()
    try:
        rows = [tuple(r) for r in conn.execute(
            "SELECT ticker, as_of FROM manual_observations WHERE field_name = 'fx_rate'")]
    finally:
        conn.close()
    if not rows:
        return ("FX 觀測：一筆都沒有（capability_absent）——跨幣別標的沒有可稽核的換算依據"
                "（原消費端隱含報酬已於 2026-09-23 退役；Phase 3 三題接手）")
    today = now.astimezone().date()
    latest: dict[str, date] = {}
    for ticker, as_of in rows:
        try:
            when = datetime.fromisoformat(str(as_of).replace("Z", "+00:00")).date()
        except ValueError:
            continue
        key = str(ticker)
        if key not in latest or when > latest[key]:
            latest[key] = when
    if not latest:
        return "FX 觀測：有列但 as_of 全部不是合法時戳（upstream_unavailable）"
    stale = sorted(t for t, when in latest.items() if (today - when).days > FX_AS_OF_TOLERANCE_DAYS)
    newest = max(latest.values())
    line = (f"FX 觀測 {len(latest)} 檔｜最新 as_of {newest.isoformat()}"
            f"（{(today - newest).days} 天前，容忍 ±{FX_AS_OF_TOLERANCE_DAYS} 天）")
    if stale:
        line += (f"｜⚠ **{len(stale)} 檔已過窗，換算依據過期**："
                 + "、".join(stale)
                 + "——補一筆 `fx_rate` mechanical 觀測即可（寫 Engine C 要核准）")
    else:
        line += "｜全部在窗內"
    return line


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

#: 候選狀態板（Phase 3）還沒落地時，心跳用這一句宣告缺席。**kind 由產生缺席的程式自己宣告**
#: （L16），不由 renderer 猜；`not_yet_recorded` 是刻意的選擇——它**不是** settled，所以這一格
#: 會一直算成待辦、一直印出來，直到 Phase 3 真的把候選板做出來（L14：常駐計數器）。
_PRICED_IN_ABSENCE = Absence(
    "not_yet_recorded",
    "目標倍數背離計數器已於 2026-09-23 隨估值鏈退役；「已定價嗎」由 Phase 3 財務三題回答，主參照是自己的歷史、不設門檻",
)
_CANDIDATE_BOARD_ABSENCE = Absence(
    "not_yet_recorded",
    "籃子 filter、目標價與多年視角已於 Phase 0 退役；接手的候選狀態板要到 Phase 3 才落地")

#: 歸零旗標的**彙總**計數暫停（逐檔的燈沒停，見個股頁 wipeout 面板）。
_WIPEOUT_ROLLUP_ABSENCE = Absence(
    "upstream_unavailable",
    "四盞燈的彙總原本由籃子 artifact 產生，籃子已退役；Phase 3 候選板接手前沒有上游")


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

    # 反證（Phase 1 Step 1.5；A5）：在盯／觸及待處置／未盯分開印——「沒人盯」與「已觸發、等你處置」不得同形。
    try:
        section.lines.extend(_disproof_lines())
    except Exception as exc:  # noqa: BLE001 — 這一格壞掉不帶走整段
        absence = Absence("upstream_unavailable", f"反證計數失敗：{type(exc).__name__}")
        section.lines.append(f"反證：{absence.reason}（{absence.kind}）")

    # thesis 生命週期：非 active 的就是「有東西變了」（L7 的五態）。
    section.lines.append(_thesis_line(now=now, thesis_path=thesis_path))

    # ⚠ 2026-09-22（Phase 0 Step 0a.2）：原本這裡印「現價已高於目標價」，讀的是籃子 artifact
    # 的 `price_above_target`。目標價與籃子 filter 一起退役（ROADMAP Phase 0／G3），接手的是
    # Phase 3 的候選狀態板。**這一行不得整段消失**：拿掉的內容換成一行缺席宣告，因為五段永遠
    # 出現，而「這一格沒有了」與「這一格是 0」是相反的結論（INV-3）。
    section.lines.append(
        f"候選狀態板未落地（{_CANDIDATE_BOARD_ABSENCE.kind}）：{_CANDIDATE_BOARD_ABSENCE.reason}")

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

    # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：原本這裡印「目標倍數背離 N 檔」（估值假設 ledger 的
    # target_pe 對今天的市場倍數）。目標倍數隨估值鏈退役，接手的是財務三題的「已定價嗎」（Phase 3）。
    # **這一行不得整段消失**：換成缺席宣告（INV-3），三題落地後由它們的計數器取代。
    section.lines.append(
        f"已定價嗎（財務三題）未落地（{_PRICED_IN_ABSENCE.kind}）：{_PRICED_IN_ABSENCE.reason}")

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


def _disproof_lines() -> list[str]:
    """反證計數一行＋（>0 才印、每天印）thesis sidecar 與 memo 不符一行（第 4 輪 N4-11：快照鍵只在有變時印，
    持續不符只會出現一天，所以這一行不走 diff）。全部本機讀取：registry、lifecycle、memo、讀圖 ledger、
    harvest 設定、凍結舊店（唯讀）——零網路。"""
    from engine_b import disproof
    from engine_b import event_watch as ew

    data = ew.load_watches()
    try:
        coverage: frozenset[str] | None = ew.primary_coverage()
    except Exception:  # noqa: BLE001 — 涵蓋面算不出來就是「未算」，不是 0
        coverage = None
    c = disproof.disproof_counts(data.get("watches") or [], readings=disproof.current_readings(),
                                 coverage=coverage, frozen_history=disproof.frozen_history_count())
    unreachable = "未算" if c["unreachable"] is None else c["unreachable"]
    frozen = "讀不到" if c["frozen_history"] is None else c["frozen_history"]
    waits = f"（等：{'、'.join(c['touched_waits_on'])}）" if c.get("touched_waits_on") else ""
    orphan = f"｜⚠ 孤兒觸及 {c['orphan_touched']}（來源已不在預期裡）" if c.get("orphan_touched") else ""
    lines = []
    if c.get("lifecycle_unreadable"):
        lines.append("⚠ **thesis/lifecycle.json 讀不到**——thesis 反證沒算（不是 0），對帳本輪不動任何等待；"
                     "修好檔案（`python -m json.tool thesis/lifecycle.json`）")
    lines.append(f"反證：在盯 {c['watching']}（其中叫不醒 {unreachable}）｜**觸及待處置 {c['touched_pending']}**{waits}"
                 f"｜到期待複查 {c['expired_pending']}（併進 thesis 複查／節點重讀）"
                 f"｜未盯 {c['unwatched']}{orphan}（v1 讀圖散文 {c['v1_prose_readings']} 份不可機械數；凍結歷史 {frozen} 不盯）")
    mismatch = c["thesis_sidecar_mismatch"]
    if mismatch:
        lines.append(f"⚠ **thesis sidecar 與 memo 不符 {len(mismatch)}**：{'、'.join(mismatch)}——memo 在 sidecar 產生之後"
                     "被手改過，它的反證不會自動登記：重跑 generator 更新 sidecar，或用 "
                     "`python -m engine_b.event_watch register-disproof` 手動登記")
    return lines


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

def build_queue(*, state_dir: Path | None = None, now: datetime | None = None,
                run_record_path: Path | None = None) -> Section:
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
    # 分類層的每日硬上限（Step 2.3，2026-09-19）。**跟著未 triage 數一起印**——
    # 只看「未 triage 41」看不出它是「今天暴量」還是「積了三天」，而那兩件事的下一步不同。
    try:
        from engine_b.routine_config import triage_daily_limit

        limit: int | None = triage_daily_limit()
    except Exception:  # noqa: BLE001 — 讀不到上限不讓整段消失
        limit = None
    over = (isinstance(pending_triage, int) and isinstance(limit, int)
            and limit > 0 and pending_triage > limit)
    # **0 也要印**：沒有待 triage 與沒有人跑 triage 在數字上長得一樣，所以這一行是無條件的。
    # ⚠ 原本這裡寫死「零＝真的沒有，不是沒跑」——2026-09-22 起 harvest 停了兩天，那句話每天都是假的
    # （L13 同形）。現在由 harvest 的新鮮度決定怎麼說：過期時 0 不代表沒有新文件。
    moment = now or datetime.now(timezone.utc)
    newest_raw = max((str(r.get("run_at") or "") for r in leads_store.get("harvest_log") or []),
                     default="")
    age = harvest_age_hours(newest_raw, now=moment)
    stale_limit = _harvest_stale_hours()
    if age is None:
        meaning = "｜⚠ harvest 沒有執行紀錄——0 不代表沒有新文件"
    elif stale_limit is not None and age > stale_limit:
        meaning = f"｜⚠ **harvest {age / 24:.0f} 天沒跑——0 不代表沒有新文件**"
    else:
        meaning = "｜新 harvest lead 需要分流"
    section.lines.append(
        f"**未 triage {pending_triage if pending_triage is not None else '未讀到'}**"
        + meaning
        + (f"｜分類層每日上限 {limit}" if isinstance(limit, int) else "｜分類層上限未讀到")
        + ("　←**超過上限，今天清不完**" if over else "")
    )
    section.lines.append(_classification_line(leads=leads, now=moment, record_path=run_record_path))

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
    # Phase 1 Step 1.7（A3）：到期不是丟——每筆 expired 落在某個處置裡；沒落的（多半是 A3 之前的歷史到期）照數
    exp = event_watch.expiry_counters({"watches": watches})
    line = (f"watch 到期 {expired}（待決 watch_decision {exp['expiry_decision_pending']}｜"
            f"等 thesis 複查 {exp['expiry_thesis_review_pending']}｜等重讀 {exp['expiry_reread_pending']}｜"
            f"追源到期結案 {exp['trace_expired_closed']}（今日 {exp['trace_expired_closed_today']}）｜"
            f"未處置 {exp['expiry_unresolved']}）｜事件監看總數 {len(watches)}")
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


def _classification_line(*, leads: Mapping[str, Any], now: datetime, record_path: Path | None) -> str:
    """分類層：<本輪結果>｜上次成功：<時間>（N 天前）。

    本輪結果讀 daily 執行紀錄的 triage 步驟（⑦a 提議、⑦b 套用）；「上次成功」取 lead store 裡最新的
    `triage.decided_at`——兩個問題分開答：今天有沒有跑、以及最後一次真的分出東西是什麼時候。
    """
    record, problem = _load_run_record(record_path, now=now)
    if record is None:
        result = problem or "今天沒有 daily 執行紀錄"
    else:
        rows = {str(r.get("key")): r for r in record.get("steps") or [] if isinstance(r, Mapping)}
        propose = rows.get("07a_triage_propose") or {}
        apply = rows.get("07b_triage_apply") or {}
        status = propose.get("status")
        if status == "skipped":
            result = f"本輪沒跑（{propose.get('reason')}）"
        elif status == "ok" and apply.get("status") == "ok":
            summary = apply.get("summary") or {}
            result = "本輪完成" + (
                f"：處理 {summary.get('processed')}、PASS {summary.get('pass')}、FILTER {summary.get('filter')}"
                f"、拒收 {summary.get('rejected')}" if summary else "")
            if propose.get("session_id"):
                result += f"｜session {propose.get('session_id')}"
        elif status is None:
            result = "執行紀錄裡沒有 triage 步驟"
        else:
            detail = propose.get("reason") or propose.get("error") or apply.get("reason") or apply.get("error")
            result = (f"**本輪失敗**（提議 {status}／套用 {apply.get('status')}"
                      + (f"：{detail}" if detail else "") + "）")
    from engine_b.event_watch import _is_trace_requeue

    stamps = []
    for lead in leads.values():
        triage = (lead or {}).get("triage") or {}
        # 兩種寫 triage 時間、卻不是分類層跑過的寫入者（L12：一個欄位兩種語意）：
        # harvest 的機械 FILTER（Form 4，寫入端標 `harvest:`）與追源重排（consume-fired 把 receipt
        # 改寫成今天；判別沿用 event_watch 的同一個函式，不另寫一份）。
        if str(triage.get("decided_by") or "").startswith("harvest:") or _is_trace_requeue(lead or {}):
            continue
        raw = str(triage.get("decided_at") or "")
        stamp = _harvest_newest_at(raw) if raw else None
        if stamp is not None:
            stamps.append(stamp)
    if stamps:
        last = max(stamps)
        days = (now - last).total_seconds() / 86400
        tail = f"｜上次成功：{last.astimezone().strftime('%Y-%m-%d %H:%M')}（{days:.0f} 天前）"
    else:
        tail = "｜上次成功：沒有任何 triage 紀錄"
    return f"分類層：{result}{tail}"


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

    # ⚠ 2026-09-22（Phase 0 Step 0a.2）：這裡原本有四行，全部讀籃子／多年視角 artifact——
    # 賭注帳（Q2）、量的候選（Q1）、要幾倍（Step 7.4）、歸零旗標彙總。前三個機制退役
    # （ROADMAP Phase 0／G3），第四個是**活的量測**但它唯一的 producer 是籃子 artifact，
    # 所以彙總跟著暫停到 Phase 3 候選板接手；**逐檔那盞燈沒有停**，它住在個股頁的
    # `wipeout` 面板（0b.1 明列為核心面板），APP 首屏照亮。
    # 兩行都是明示缺席而不是整段消失：不印，與印 0，導向相反的行動（INV-3、L14）。
    section.lines.append(
        f"賭注帳／量的候選／要幾倍：{_CANDIDATE_BOARD_ABSENCE.reason}"
        f"（{_CANDIDATE_BOARD_ABSENCE.kind}）")
    section.lines.append(
        f"歸零旗標彙總：{_WIPEOUT_ROLLUP_ABSENCE.reason}（{_WIPEOUT_ROLLUP_ABSENCE.kind}）"
        "　←逐檔那盞燈仍在個股頁，停的只有這個彙總計數")

    # ⚠ 2026-09-23（Step 0b.3）：原本讀 `ranking` kind 的可行動排序列；跨檔排序退役後改讀 `structure_table`
    # 的逐邊列（含未填與低分的邊）。這一行量的是**相關性**（N 檔不等於 N 個獨立機會），不是排序。
    table, table_absence = _load_state(state_dir, "structure_table")
    if table_absence is not None:
        section.lines.append(f"需求錨集中度：{table_absence.reason}（{table_absence.kind}）")
    else:
        rows = table.get("rows") or []
        anchors: dict[str, int] = {}
        for row in rows:
            anchors[str(row.get("demand_anchor") or "（走不到錨）")] = (
                anchors.get(str(row.get("demand_anchor") or "（走不到錨）"), 0) + 1
            )
        top = sorted(anchors.items(), key=lambda kv: -kv[1])[:3]
        shape = "、".join(f"{k} {v}" for k, v in top)
        section.lines.append(
            f"結構表 {len(rows)} 條邊分佈在 {len(anchors)} 個需求錨（前三：{shape}）"
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

    # 賭注收斂（V4，2026-09-19）：**不依賴賣出的驗證序列**。等權報酬與 power-law 都以股價
    # 為錨點，而本圖標的同漲同跌；共識修正不受 beta 污染，也不需要賣出就能驗證。
    # ⚠ 這裡只**讀** artifact，不算任何東西。
    if pos_absence is not None:
        section.lines.append(f"賭注收斂：{pos_absence.reason}（{pos_absence.kind}）")
    else:
        conv = positions.get("bet_convergence") or {}
        if not conv:
            section.lines.append("賭注收斂：這份 positions artifact 沒有 bet_convergence 鍵（upstream_unavailable）")
        elif not conv.get("n_bets"):
            # 「還沒有人下注」與「下了注但共識沒動」是相反的結論，不得印成同一個 0%（L12）。
            section.lines.append(
                f"賭注收斂：**還沒有任何一檔寫下賭注**（掃過 {conv.get('scanned', '?')} 檔）"
                "——這不是 0%，是還沒有分子也沒有分母")
        else:
            lo, hi = conv.get("shortest_window_days"), conv.get("longest_window_days")
            window_text = (f"｜已觀測 {lo}–{hi} 天" if lo is not None else "")
            waiting = conv.get("not_yet_observable") or 0
            waiting_text = (f"｜**賭注寫下後還沒有共識抓取 {waiting}**" if waiting else "")
            section.lines.append(
                f"賭注收斂（共識朝我們移動了嗎）：有賭注 {conv.get('n_bets', '?')} 檔"
                f"｜朝我們 {conv.get('toward_us', '?')}｜反向 {conv.get('away_from_us', '?')}"
                f"｜共識沒動 {conv.get('unchanged', '?')}{waiting_text}{window_text}"
                "　←窗短時「沒動」幾乎是必然，不是市場否定了我們")

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
    run_record_path: Path | None = None,
) -> list[Section]:
    """固定五段，順序固定，**任何情況下都回五個 Section**。"""
    moment = now or datetime.now(timezone.utc)
    leads = leads_path or ROOT / "library" / "leads" / "pending_leads.json"
    thesis = thesis_path or ROOT / "thesis" / "lifecycle.json"
    sections = [
        _guard(1, SECTION_TITLES[0],
               lambda: build_freshness(now=moment, state_dir=state_dir, leads_path=leads,
                                       run_record_path=run_record_path)),
        _guard(2, SECTION_TITLES[1],
               lambda: build_changes(now=moment, state_dir=state_dir, thesis_path=thesis)),
        _guard(3, SECTION_TITLES[2], lambda: build_queue(state_dir=state_dir, now=moment,
                                                         run_record_path=run_record_path)),
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
