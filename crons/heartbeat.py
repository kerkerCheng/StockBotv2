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

**段 2 的第一行是「較昨變動」（Phase 1 Step 1.8）。** 每次 daily 寫一份快照
（`library/private/heartbeat/snapshots/<日期>.json`，鍵是封閉清單 `SNAPSHOT_KEYS`、留 14 天），心跳只印跟上一份比
**變了的鍵**，其餘印「N 項相同」。快照是 derived、只給 diff 用，**不是** current-state authority（AGENTS：不建立
與待辦池競爭的第二個狀態源）。沒有上一份（第一天、或中間斷了很多天）就誠實印出來，不假裝有。

## 它明確不做的事

- **不寫任何 authority**，不碰 Neo4j、不連外、不讀憑證。寫入只有 `--out`（Markdown）、`--summary-out`
  （Discord 摘要行）與 `--write-snapshot`（快照，derived）三個，全部在 `library/private/heartbeat/` 底下。
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

    python -m crons.heartbeat                     # 印 Markdown 到 stdout（不寫快照）
    python -m crons.heartbeat --format json       # 機器可讀（測試與未來的 APP 用）
    python -m crons.heartbeat --out <path>        # 寫 UTF-8 檔，交給既有 publisher
    python -m crons.heartbeat --out <p> --summary-out <p2> --write-snapshot   # daily ⑱ 的用法
（`--weekly` 已於 Phase 1 Step 1.8 拿掉：帳號計分表每天印 tier 分布與較昨變化，完整表在 APP。）
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpha.absence import check_absence_kind  # noqa: E402
from query.graph_walk import QUESTION_TYPES as WALK_QUESTION_TYPES  # noqa: E402
# 候選板字彙取自零 I/O 的核心模組（不經 `alpha.providers`——那會在 import 期載入 Neo4j／Engine C／yfinance，
# 心跳的「某一格壞了其餘照發」在 import 期就失效；2026-09-29 3.6 審查）。
from alpha.candidates import GROUP_LABELS as CANDIDATE_GROUP_LABELS  # noqa: E402
from alpha.candidates import GROUPS as CANDIDATE_GROUPS  # noqa: E402
from alpha.candidates import SIDE_GROUPS as CANDIDATE_SIDE_GROUPS  # noqa: E402
from alpha.candidates import SIDE_LABELS as CANDIDATE_SIDE_LABELS  # noqa: E402

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
                    run_record_path: Path | None = None, capture_dir: Path | None = None) -> Section:
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
    # (c1) 台股季報股數（2026-10-05）：同月營收——MOPS 按季永久可查，所以不排程，心跳印落後幾季。
    try:
        section.lines.append(_tw_share_capital_line(now=now))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"季報股數盤點失敗：{type(exc).__name__}")
        section.lines.append(f"台股季報股數：{absence.reason}（{absence.kind}）")

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

    # (e)(f)(g) 備份、健康審查、invariants（Phase 1 Step 1.8）——daily ⑯⑭⑮ 的結果；心跳只讀，不重跑。
    for label, fn in (("備份", lambda: _backup_line(now=now)),
                      ("健康審查", lambda: _health_line(now=now, capture_dir=capture_dir)),
                      ("invariants", lambda: _invariants_line(now=now, capture_dir=capture_dir))):
        try:
            section.lines.append(fn())
        except Exception as exc:  # noqa: BLE001
            absence = Absence("upstream_unavailable", f"{label}盤點失敗：{type(exc).__name__}")
            section.lines.append(f"{label}：{absence.reason}（{absence.kind}）")
    return section


#: 備份超過幾天算舊（Discord 摘要行的紅旗也用它）。
BACKUP_STALE_DAYS = 7


def _backup_problems(status: Mapping[str, Any] | None) -> list[str]:
    """備份哪裡不對——段 1 那一行與 Discord 摘要行共用這一份判定（L16）。`None`＝這台沒有 private root，不算問題。

    ⚠ 2026-10-06 實測：原本只有「超過 7 天」會亮，於是 Drive `skipped` 連續 26 天、「還原驗證 有」指著一份
    早已輪替掉的備份，每天照印不亮（L14-4 恆亮）。會亮紅的舊 renderer（`briefing/render.py`）當時已沒有呼叫端，
    OPERATIONS 寫的「Drive 未上傳 🔴」描述的是它——同一個狀態兩份渲染、規則不同（L16），已刪掉舊的那份。
    """
    if status is None:
        return []
    if status.get("status") == "never":
        return ["從來沒有備份過"]
    if status.get("status") != "ok":
        return ["狀態檔讀不懂"]
    problems = []
    if int(status.get("age_days") or 0) > BACKUP_STALE_DAYS:
        problems.append(f"超過 {BACKUP_STALE_DAYS} 天")
    if status.get("drive_status") != "uploaded":
        problems.append("Drive 沒有這份")
    if not status.get("restore_verified_current"):
        problems.append("這份沒驗還原")
    return problems


def _backup_line(*, now: datetime) -> str:
    """`scripts/backup_private.py` 的狀態（Phase 1 Step 1.8）。loader 是 `briefing.sources.load_backup_status`；
    渲染只有這一份。daily ⑯ 備份（含 Drive）、⑯b 驗還原，所以正常的一天三格都不亮。"""
    from briefing.sources import load_backup_status

    status = load_backup_status(now=now)
    if status is None:
        return "備份：這台沒有 private root（method_not_applicable）"
    if status.get("status") == "never":
        return "⚠ **備份：從來沒有備份過**（`python scripts/backup_private.py run`）"
    if status.get("status") != "ok":
        return "⚠ **備份：狀態檔讀不懂**（upstream_unavailable）——視同沒有備份"
    age = int(status.get("age_days") or 0)
    drive = str(status.get("drive_status") or "unknown")
    if drive == "uploaded":
        drive_text = "Drive 已上傳"
    else:
        last = status.get("drive_last_uploaded_days")
        drive_text = f"Drive {drive}（最後成功上傳：{'本機沒有紀錄' if last is None else f'{last} 天前'}）"
    if status.get("restore_verified_current"):
        verify_text = "還原驗證 這份有"
    else:
        days = status.get("restore_verified_days")
        verify_text = f"還原驗證 這份沒有（{'從來沒有' if days is None else f'最後一次 {days} 天前'}）"
    line = (f"備份：最後 {age} 天前（{status.get('backup_id') or '?'}）｜{drive_text}｜{verify_text}"
            f"｜之後變動未備份 {status.get('unbacked_files', '?')} 檔")
    problems = _backup_problems(status)
    return f"⚠ **{line}——{'、'.join(problems)}**" if problems else line


def _capture(name: str, *, now: datetime, capture_dir: Path | None) -> tuple[Any, str | None]:
    """daily 的 capture 檔（`<name>_<本地日期>.json` 的 payload）。今天沒有是要說出來的狀態。"""
    path = (capture_dir or RUN_RECORD_DIR) / f"{name}_{now.astimezone().strftime('%Y-%m-%d')}.json"
    if not path.is_file():
        return None, "今天沒有紀錄（daily 沒跑到這一步或失敗）"
    try:
        envelope = _read_json(path)
    except (OSError, ValueError) as exc:
        return None, f"紀錄讀不到：{type(exc).__name__}"
    return (envelope or {}).get("payload"), None


def _health_line(*, now: datetime, capture_dir: Path | None) -> str:
    payload, problem = _capture("health", now=now, capture_dir=capture_dir)
    if problem:
        return f"⚠ 健康審查：{problem}"
    sections = [s for s in (payload or {}).get("sections") or [] if isinstance(s, Mapping)]
    red = [str(s.get("title")) for s in sections if s.get("level") == "red"]
    return (f"健康審查 {len(sections)} 節｜**🔴 {len(red)}**：" + "、".join(red) if red
            else f"健康審查 {len(sections)} 節｜🔴 0")


def _invariants_line(*, now: datetime, capture_dir: Path | None) -> str:
    payload, problem = _capture("invariants", now=now, capture_dir=capture_dir)
    if problem:
        return f"⚠ invariants：{problem}"
    checks = [c for c in payload or [] if isinstance(c, Mapping)]
    fail = [str(c.get("check")) for c in checks if c.get("status") == "FAIL"]
    skipped = [str(c.get("check")) for c in checks if c.get("status") == "SKIPPED"]
    line = (f"invariants {len(checks)} 項｜**FAIL {len(fail)}**：" + "、".join(fail) if fail
            else f"invariants {len(checks)} 項全部 PASS" if not skipped else f"invariants {len(checks)} 項｜FAIL 0")
    if skipped:
        line += f"｜SKIPPED {len(skipped)}：" + "、".join(skipped)
    return line


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


def _tw_share_capital_line(*, now: datetime) -> str:
    """台股季報股數的新鮮度（已定價①的市值序列靠它）。零網路——只讀本機 Engine C。

    `落後` 相對**法定期限**算（一般業季後 45 日、年報 3 個月）：8 月 10 日還沒有 Q2 是正常的，8 月 20 日還沒有才是落後。
    ⚠ 「還沒抓」與「抓到了但不能用」是兩件事、修法不同（L13-2）：落後由**已抓到的最新一季**（不分能不能用）算——只有
    `--sync` 修得了的才叫落後；最新一季被讀取端拒收的（核對沒過、同季衝突、期間內有分割）另列一句，`--sync` 修不了，
    讀取端接著用前一季。能不能用由 `engine_c.history.tw_shares_as_of` 判（與三題同一支，L16），這裡不另寫一套。
    （2026-10-05 R2 C1：舊版只看能用的列，3081.TWO 2026Q2 一被拒就每天假亮「落後 1 季」。）
    """

    from engine_c.db import get_conn
    from engine_c.history import tw_shares_as_of
    from engine_c.monthly_revenue import registry_taiwan_tickers
    from engine_c.tw_share_capital import latest_due_quarter, share_capital_series

    tickers = registry_taiwan_tickers()
    if not tickers:
        return "台股季報股數：registry 裡沒有台股（capability_absent）"
    today = now.astimezone().date()
    due_year, due_q = latest_due_quarter(today)
    conn = get_conn()
    try:
        latest: dict[str, tuple[int, int]] = {}
        latest_unusable: list[str] = []
        rejected = 0
        for ticker in tickers:
            rows = share_capital_series(conn, ticker)
            if not rows:
                continue
            year, quarter, period = max((int(r["fiscal_year"]), int(r["quarter"]), str(r["period_end"])[:10]) for r in rows)
            latest[ticker] = (year, quarter)
            known = tw_shares_as_of(conn, ticker, as_of=today)
            rejected += len({r["period_end"] for r in known["rejected"]})
            if period not in {str(c["period_end"])[:10] for c in known["cover"]}:
                latest_unusable.append(f"{ticker} {year}Q{quarter}")
    finally:
        conn.close()
    if not latest:
        return (f"台股季報股數 {len(tickers)} 檔｜**一筆都沒有**"
                "（跑 `python -m engine_c.tw_share_capital --backfill 14`）")
    oldest = min(latest.values())
    lag = (due_year * 4 + due_q) - (oldest[0] * 4 + oldest[1])
    empty = sorted(set(tickers) - set(latest))
    line = f"台股季報股數 {len(latest)}/{len(tickers)} 檔｜最舊 {oldest[0]}Q{oldest[1]}"
    if empty:
        line += f"｜**{len(empty)} 檔一筆都沒有**：" + "、".join(empty)
    if latest_unusable:
        line += "｜最新一季不能用（`--sync` 修不了，接著用前一季）：" + "、".join(latest_unusable)
    if rejected:
        line += f"｜不用的季共 {rejected} 筆"
    line += (f"｜⚠ 落後 {lag} 季（跑 `python -m engine_c.tw_share_capital --sync`）" if lag > 0
             else "｜已跟上法定期限")
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

#: ⚠ 2026-09-29（Phase 3 Step 3.6）：`_PRICED_IN_ABSENCE`／`_CANDIDATE_BOARD_ABSENCE`／`_WIPEOUT_ROLLUP_ABSENCE`
#: 三個缺席宣告退役——候選狀態板（`candidates` artifact）落地，它們宣告缺席的那三格改讀它：
#: 段 2 的候選各組檔數＋最老滯留、三題有值／缺席計數；段 4 的歸零旗標彙總。artifact 讀不到時照樣具名缺席
#: （`upstream_unavailable`，由 `_load_state` 宣告），不是整行消失。

#: 讀圖單位的短名（鍵＝`alpha.structure_reading.READING_UNITS`，測試守相等；L16）。
_UNIT_LABEL: dict[str, str] = {"layer": "層", "socket": "插槽"}



def _candidate_lines(state_dir: Path | None) -> list[str]:
    """段 2：候選各組檔數（**0 也印**、最老滯留逐狀態各印）＋持股讀不到／解析不到＋三題有值與缺席計數。
    只讀 `candidates` artifact（零網路；推導在 materialize）。**只數，不下結論**：三題那一行不得讀成「幾檔已定價」。"""
    board, absence = _load_state(state_dir, "candidates")
    if absence is not None:
        return [f"候選板：{absence.reason}（{absence.kind}）",
                f"三題：{absence.reason}（{absence.kind}）"]
    counts = board.get("counts") or {}
    oldest = board.get("oldest_stall_days") or {}

    def aged(key: str) -> str:
        n, d = counts.get(key, 0), oldest.get(key)
        return f"{n}（最老 {d} 天）" if n and d is not None else f"{n}"

    held = "未驗（持股未讀到）" if counts.get("held") is None else str(counts.get("held"))
    lines = [f"候選：可開 {aged('open')}｜缺 X {aged('missing')}｜等回落 {aged('priced_wait')}｜不要 {counts.get('pass', 0)}"
             f"｜已持有 {held}｜非倍率候選 {counts.get('not_multiple', 0)}｜邊緣無法量 {counts.get('edge_unmeasurable', 0)}"
             f"｜舊版 {counts.get('legacy', 0)}｜前提失效 {counts.get('precondition_failed', 0)}"
             f"｜無敘事 {counts.get('no_narrative', 0)}"]
    holdings = board.get("holdings") or {}
    if holdings.get("status") != "ok":
        lines.append(f"  持股未讀到，已持有判定暫停（upstream_unavailable）：{holdings.get('reason')}")
    else:
        # 常駐計數器（Phase 4 Step 4.7b）：0 也印。「使用者決定不研究」來自 config/holdings_coverage.json——
        # 舊 artifact 沒有這一欄就印「未讀到」，不壓成 0（L12）。
        unresolved = list(holdings.get("unresolved") or ())
        ignored = holdings.get("ignored")
        line = (f"  持股解析不到 {len(unresolved)}"
                f"（使用者決定不研究 {'未讀到' if ignored is None else len(ignored)}）")
        if unresolved:
            line += f"：{'、'.join(unresolved[:5])}（不猜；要不要登記是 identity 的決定）"
        if holdings.get("ignored_problem"):
            line += f"｜不研究名單讀不到（{holdings['ignored_problem']}）——全部照列解析不到"
        lines.append(line)
    ledger = board.get("ledger") or {}
    if ledger and not ledger.get("present"):
        lines.append("  敘事 ledger 目錄不存在（upstream_unavailable）——「無敘事」是讀不到，不是真的沒有")
    elif ledger.get("parse_errors"):
        lines.append(f"  敘事 ledger 有 {ledger['parse_errors']} 行解析不了（那幾份宣告沒進板）："
                     + "；".join(str(e) for e in (ledger.get("parse_error_examples") or [])[:2]))
    readings = board.get("readings") or {}
    if readings.get("parse_errors"):
        lines.append(f"  讀圖 ledger 有 {readings['parse_errors']} 行解析不了（騎它們的列會印 not_found）："
                     + "；".join(str(e) for e in (readings.get("parse_error_examples") or [])[:2]))
    roll = board.get("rollup") or {}
    own, nums, wipe = roll.get("priced_in_own") or {}, roll.get("in_numbers") or {}, roll.get("wipeout") or {}
    not_read = (roll.get("not_read") or {}).get("n") or 0
    lines.append(f"三題（{roll.get('universe', '?')} 檔）：已定價① 有值 {own.get('valued', '?')}／缺席 {own.get('absent_total', '?')}"
                 f"｜出現在數字裡 有值 {nums.get('valued', '?')}／缺席 {nums.get('absent_total', '?')}"
                 f"｜會死嗎 四盞非灰 {wipe.get('all_four_non_grey', '?')}"
                 + (f"｜**讀不到 {not_read} 檔**" if not_read else "")
                 + "　←只數有值與缺席，不是結論")
    return lines



def build_changes(*, now: datetime, state_dir: Path | None, thesis_path: Path,
                  diff_lines: Sequence[str] = (), leads_path: Path | None = None) -> Section:
    """較昨變動、watch 今日、反證、新點名、thesis、候選板缺席、讀圖（含重讀理由）、已定價缺席、beta。"""
    section = Section(2, SECTION_TITLES[1])
    section.lines.extend(diff_lines)

    # watch 今日（Phase 1 Step 1.8）：取代原本讀 watches artifact 的「本輪該查／已觸發未消費／到期」——
    # 「本輪該查」是 T2 主動輪詢的配額，而輪詢已不在 daily（1.2a）；其餘兩格在這一行，改讀 registry（零網路）。
    try:
        section.lines.append(_watch_today_line(now=now))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"watch 盤點失敗：{type(exc).__name__}")
        section.lines.append(f"watch：{absence.reason}（{absence.kind}）")

    # 反證（Phase 1 Step 1.5；A5）：在盯／觸及待處置／未盯分開印——「沒人盯」與「已觸發、等你處置」不得同形。
    try:
        section.lines.extend(_disproof_lines())
    except Exception as exc:  # noqa: BLE001 — 這一格壞掉不帶走整段
        absence = Absence("upstream_unavailable", f"反證計數失敗：{type(exc).__name__}")
        section.lines.append(f"反證：{absence.reason}（{absence.kind}）")

    # 新點名雷達（Phase 1 Step 1.8）：今天第一次被點名、registry 沒有的名字——依首次點名時間排，
    # **不依次數**（依次數的話 AMZN 這種常駐大名會恆亮，L14-4）。
    try:
        section.lines.append(_new_names_line(now=now, leads_path=leads_path))
    except Exception as exc:  # noqa: BLE001
        absence = Absence("upstream_unavailable", f"新點名盤點失敗：{type(exc).__name__}")
        section.lines.append(f"新點名：{absence.reason}（{absence.kind}）")

    # thesis 生命週期：非 active 的就是「有東西變了」（L7 的五態）。
    section.lines.append(_thesis_line(now=now, thesis_path=thesis_path))

    # ⚠ 2026-09-22（Phase 0 Step 0a.2）：原本這裡印「現價已高於目標價」，讀的是籃子 artifact
    # 的 `price_above_target`。目標價與籃子 filter 一起退役（ROADMAP Phase 0／G3）。
    # 2026-09-29（Phase 3 Step 3.6）：接手的候選狀態板落地——各組檔數與最老滯留（AGENTS「每個候選狀態的檔數與
    # 最老滯留天數」）；一個全域最老值會被「不要」長期霸占，所以逐狀態各印。
    candidate_lines = _candidate_lines(state_dir)
    section.lines.append(candidate_lines[0])
    section.lines.extend(line for line in candidate_lines[1:-1])

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
            # 單位拆分（Phase 2 Step 2.6；讀圖 v3 的 `unit`）：層與插槽各自現行、各自重讀，合成一個數會藏掉
            # 「插槽讀圖一份都還沒有」這件事。
            units = Counter(str(r.get("unit")) for r in readings.get("rows") or () if r.get("reading_id"))
            line = (f"結構讀圖 {total} 份（層 {units.get('layer', 0)}／插槽 {units.get('socket', 0)}）"
                    f"｜現行 {counts.get('current', 0)}"
                    f"｜**該重讀 {reread.get('n', 0)}**（stale {counts.get('stale', 0)}"
                    f"／過期 {counts.get('expired', 0)}；低級 {counts.get('stale_low', 0)} 不進佇列）")
            nodes = reread.get("nodes") or []
            if nodes:
                line += "：" + "、".join(str(n) for n in nodes[:5]) + ("…" if len(nodes) > 5 else "")
            section.lines.append(line)
            # 重讀理由（Phase 1 Step 1.5／1.7）：客戶出了新文件、反證被判觸及、反證等滿一輪都沒發生。
            for row in (readings.get("rows") or [])[:20]:
                reasons = [str(r) for r in (row.get("reread_reasons") or [])]
                if row.get("needs_reread") and reasons:
                    # 帶單位（R2-b N6）：同一個 prod 節點層與插槽各一份時，不說單位就不知道要重讀哪一份。
                    section.lines.append(f"  {row.get('node')}（{_UNIT_LABEL.get(str(row.get('unit')), row.get('unit'))}）"
                                         "該重讀：" + "；".join(reasons[:3])
                                         + (f"（另 {len(reasons) - 3} 條）" if len(reasons) > 3 else ""))
            triggers = readings.get("disproof_triggers") or {}
            if triggers.get("n"):
                section.lines.append(
                    f"其中 **{triggers['n']} 份同時是 disproof 觸發**（供給側多一家／反向路徑變動）："
                    + "、".join(str(n) for n in (triggers.get("nodes") or [])[:5])
                    + "——thesis 要不要改由人決定，系統只標記")

    # ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：原本這裡印「目標倍數背離 N 檔」（估值假設 ledger 的
    # target_pe 對今天的市場倍數）。目標倍數隨估值鏈退役；2026-09-29（Step 3.6）起由三題的有值／缺席計數取代。
    section.lines.append(candidate_lines[-1])

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
    if c.get("memo_unreadable"):
        lines.append(f"⚠ thesis memo 讀不到或「推翻」節解析不到 {len(c['memo_unreadable'])}："
                     f"{'、'.join(c['memo_unreadable'])}——它的反證沒算進預期（不是 0）")
    lines.append(f"反證：在盯 {c['watching']}（其中叫不醒 {unreachable}）｜**觸及待處置 {c['touched_pending']}**{waits}"
                 f"｜到期待複查 {c['expired_pending']}（併進 thesis 複查／節點重讀）"
                 f"｜未盯 {c['unwatched']}{orphan}（v1 讀圖散文 {c['v1_prose_readings']} 份不可機械數；凍結歷史 {frozen} 不盯）")
    # 加碼條件（Phase 7 Step 7.0d）：與反證分開數——它不是反證；觸及只提醒「結構確認了」，不是買進訊號
    k = disproof.confirm_counts(data.get("watches") or [])
    lines.append(f"加碼條件：在盯 {k['watching']}｜**觸及待處置 {k['touched_pending']}**（提醒，不是買進訊號）"
                 f"｜到期待重寫 {k['expired_pending']}（觸及與到期都進敘事重寫）")
    mismatch = c["thesis_sidecar_mismatch"]
    if mismatch:
        lines.append(f"⚠ **thesis sidecar 與 memo 不符 {len(mismatch)}**：{'、'.join(mismatch)}——memo 在 sidecar 產生之後"
                     "被手改過，它的反證不會自動登記：重跑 generator 更新 sidecar，或用 "
                     "`python -m engine_b.event_watch register-disproof` 手動登記")
    return lines


def _local_day(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone().date()


def _woke_on(watch: dict, day: date) -> bool:
    """那一天醒過＝現行 `woken_by` 或任一筆 `reactivations[].woken_by` 的時間落在那一天（本地日期）。

    追源型與 pq2 型醒來後常在同一輪就排回、轉回 active，醒來紀錄移進 `reactivations`、`woken_by` 清成 null——
    只看現行 `woken_by` 的話，真的醒了也印「今日醒 0」（2026-09-24／25 兩天各醒 2／3 筆都印 0；L13 同形）。
    """
    stamps = [(watch.get("woken_by") or {}).get("at")]
    stamps += [(r.get("woken_by") or {}).get("at") for r in watch.get("reactivations") or [] if isinstance(r, dict)]
    return any(_local_day(s) == day for s in stamps)


def _watch_today_line(*, now: datetime) -> str:
    from engine_b import event_watch as ew

    data = ew.load_watches()
    watches = data.get("watches") or []
    today = now.astimezone().date()
    woken = sum(1 for w in watches if _woke_on(w, today))
    expired = sum(1 for w in watches if _local_day(w.get("expired_at")) == today)
    c = ew.counters(data)
    return (f"watch：今日醒 {woken}｜今日到期 {expired}｜已觸發未消化 {c['fired_unconsumed']}"
            f"｜語意標旗 {c['semantic_flagged']}｜**未檢 {c['semantic_pending_check']}**（判定只在互動："
            "`python -m engine_b.event_watch semantic-queue`）")


def _new_names_line(*, now: datetime, leads_path: Path | None) -> str:
    """今天第一次被點名、registry 沒有的名字（registry 是「圖裡沒有」的代理：圖裡的公司都在 registry）。"""
    from engine_b import leads as leads_mod

    store = leads_mod.load(leads_path) if leads_path is not None else leads_mod.load()
    rows = leads_mod.onboard_candidates(store)
    today = now.astimezone().date()
    fresh = sorted((r for r in rows if _local_day(r.get("first_seen")) == today),
                   key=lambda r: str(r.get("first_seen")))
    tail = f"｜累計被點名但未登記 {len(rows)}（`python -m engine_b.cli onboard-candidates`）"
    if not fresh:
        return "今天第一次被點名、registry 沒有的名字 0" + tail
    names = "、".join(f"{r.get('ticker')}（{' '.join(str(r.get('sample_title') or '').split())[:30]}）"
                     for r in fresh[:5])
    return (f"**今天第一次被點名、registry 沒有的名字 {len(fresh)}**：{names}"
            + (f"…另 {len(fresh) - 5} 個" if len(fresh) > 5 else "") + tail)


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

def _graph_walk_line(questions: Sequence[Mapping[str, Any]], absence: Absence | None) -> str:
    """「走圖：」接九型各自「中文短名 命中／母體」。讀不到 artifact 印 `upstream_unavailable`，不印 0（INV-3）。

    ⚠ 格式取自 `query.graph_walk.summary_line`（L16：走圖的呈現只有一份），心跳只讀 artifact、不查圖。
    """
    if absence is not None:
        return f"走圖：{absence.reason}（{absence.kind}）——不是「沒有洞」"
    from query.graph_walk import QUESTION_TYPE_KEYS, summary_line

    seen = [str(q.get("key")) for q in questions]
    line = "走圖：" + summary_line({"questions": questions})
    if seen != list(QUESTION_TYPE_KEYS):
        # artifact 的型別與現行字彙不一致（舊 artifact 或字彙改了沒重跑）——說出來，不假裝九格齊全。
        line += f"｜⚠ artifact 的型別與現行字彙不一致（{len(seen)} 型），請重跑 materialize --graph-walk"
    return line + "（consumer：research-drain 第三段）"


def _layer_stats_line(walk: Mapping[str, Any], absence: Absence | None) -> str:
    """「層：」一行——`graph_walk` artifact 的 `layer_stats.summary` 照抄（`query.layer_stats.summary_line` 是唯一格式）。

    三種缺席分開說（INV-3）：artifact 讀不到、artifact 是舊版沒有這一段（請重跑 materialize）、計數器自己算不出來
    （artifact 裡帶理由）。心跳不查圖、不重算。
    """
    if absence is not None:
        return f"層：{absence.reason}（{absence.kind}）——不是 0"
    layer = walk.get("layer_stats")
    if layer is None:
        return "層：graph_walk artifact 沒有 layer_stats（這份沒算層計數器）——請重跑 materialize --graph-walk；不是 0"
    if layer.get("summary"):
        return str(layer["summary"])
    from query.layer_stats import summary_line

    return summary_line(layer)


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
    # 走圖那一段（Phase 2 Step 2.6：取代 coverage／重複節點／讀圖待重讀三段）的 authority 是已 materialize 的
    # `graph_walk` artifact，不在 leads 目錄——照 observe 的注入慣例給值；讀不到就給 None
    # （「沒讀到」與「真的是 0」不得同形，INV-3）。心跳不查圖（零網路、零 LLM）。
    walk, walk_absence = _load_state(state_dir, "graph_walk")
    walk_questions = list(walk.get("questions") or ()) if walk_absence is None else []
    holes = None if walk_absence is not None else qs.graph_holes_count(walk_questions)
    # Phase 3 Step 3.6：敘事連結的反證來源已換版也是 narrative_rewrite 的工作（與 audit、候選推導同一個判定）。
    # 讀的是本機 ledger 與 registry（零網路）；讀不到只少這一格的注入，不帶走整段。
    breaks: list | None
    breaks_reason = None
    try:
        from alpha.providers.briefs import BRIEF_DIR
        from engine_b.disproof import current_briefs
        from engine_b.narrative_watches import link_breaks

        if not BRIEF_DIR.is_dir():
            raise FileNotFoundError("敘事 ledger 目錄不存在")
        breaks = link_breaks(current_briefs(), watches=watches)
    except Exception as exc:  # noqa: BLE001 — 讀不到＝未讀到，**不是 0**（INV-3；3.6 覆核）
        breaks, breaks_reason = None, f"{type(exc).__name__}: {str(exc)[:60]}"
    observation = qs.observe(
        leads=leads, watches=watches, todo_items=todo_items,
        forward_view_backlog=None, graph_holes=holes, narrative_link_breaks=breaks or (),
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
    # 預篩本輪結果與 LLM 額度（Phase 1 Step 1.4／1.3）——讀 daily 執行紀錄，心跳不重跑。
    try:
        section.lines.extend(_prescreen_and_quota_lines(now=moment, record_path=run_record_path))
    except Exception as exc:  # noqa: BLE001
        section.lines.append(f"預篩：盤點失敗（{type(exc).__name__}；upstream_unavailable）")
    # 外部雷達（Phase 7 Step 7.0f）：每天一行，沒跑也照印理由（八週試驗的停止條件要數它）
    try:
        section.lines.append(_radar_line(now=moment, record_path=run_record_path))
    except Exception as exc:  # noqa: BLE001
        section.lines.append(f"外部雷達：盤點失敗（{type(exc).__name__}；upstream_unavailable）")
    # T2 主動輪詢（2026-10-06 使用者指示）：1.2a 把 sweep 移出 daily 時這一格一起不見——09-21 之後兩週沒人跑，也沒有任何地方印。
    try:
        section.lines.append(_t2_line(now=moment, record_path=run_record_path))
    except Exception as exc:  # noqa: BLE001
        section.lines.append(f"T2 輪詢：盤點失敗（{type(exc).__name__}；upstream_unavailable）")

    # ⚠ `None` 是「本次沒讀到那個 authority」，不是 0——把它加成 0 會讓「沒讀到」與「真的沒有」
    # 同形（INV-3）。所以先分開，再讓沒讀到的段自己現形。
    pq1_keys = ("approved_work_orders", "triaged_go_leads", "fired_lead_requeue")
    pq1 = sum(counts[key] for key in pq1_keys if counts.get(key) is not None)
    unread = [key for key in pq1_keys if counts.get(key) is None]
    line = f"pq1 可做 {pq1}｜機械段待清 {observation['mechanical_total']}"
    # 研究 lead 裡有幾則是互動 session 從走圖起的（Phase 4 Step 4.5b；0 也印）——與分類層的分開計。
    by_classifier = observation.get("triaged_go_by_classifier") or {}
    line += "｜其中互動起的研究 lead " + str(sum(n for who, n in by_classifier.items()
                                                 if who.startswith("interactive:")))
    if unread:
        line += f"｜⚠ 未讀到 {len(unread)} 段：" + "、".join(unread)
    section.lines.append(line)
    # 走圖（Phase 2 Step 2.6）：九型各自「命中／母體」，**0 也印、不加總、不排序**（plan §0 第 7 條）。
    # consumer 是 research-drain（互動），不是 `engine_b.cli drain`，所以不加進 pq1 的數；但它是研究工作，
    # 不印在這裡會讓上一行的 0 被讀成「沒事做」。原本的「＋結構讀圖待重讀 N」由第 4 型承載。
    section.lines.append(_graph_walk_line(walk_questions, walk_absence))
    # 層計數器（Phase 4 Step 4.4c）：ROADMAP Phase 4 ①②③ 每天自己出現（L14：防呆是常駐計數器），同一份 artifact。
    section.lines.append(_layer_stats_line(walk, walk_absence))
    # 敘事該重寫（Phase 3 Step 3.4／3.6）：敘事來源 watch 醒來／觸及／到期未判＋敘事連結的反證來源已不在盯。
    # 研究工作（consumer＝research-drain），不加進 pq1；**0 也印**——不印會讓它安靜積著（L14）。
    rewrite = next((seg for seg in observation["segments"] if seg["key"] == "narrative_rewrite"), None)
    if rewrite is not None:
        section.lines.append(
            f"敘事該重寫 {'未讀到' if rewrite['count'] is None else rewrite['count']}"
            + (f"（其中連結斷 {len(breaks)}）" if breaks is not None
               else f"（**連結斷未讀到**：{breaks_reason}——上面的數不含它）")
            + (("：" + "、".join(str(e) for e in rewrite.get("examples") or ())) if rewrite.get("examples") else ""))

    # ⚠ 「球在使用者手上」有 SSOT——`engine_b.todo.actionable_items()`（它已經處理了
    # `waiting_on`＝等事件、已 dispatch 的 pq1 job 不重複詢問這兩種情形）。
    # 在這裡自己用 `dispatch_status` 重數一份就是 L16 的形狀：猜錯不會有東西壞掉，只會安靜偏掉。
    active = todo_mod.active_items(pool)
    actionable = todo_mod.actionable_items(pool)
    section.lines.append(
        f"**pq2 球在你手上 {len(actionable)}**｜池中未結案 {len(active)}"
        f"（差額＝等事件或已在 pq1 跑）"
    )
    # 逐筆（Phase 1 Step 1.8）：go／不含的字串取自 `todo.GO_AUTHORIZATION`（L16：不在這裡另寫一份），
    # 使用者不展開就知道 go 會做什麼、不會做什麼（AGENTS 收尾摘要契約）。
    section.lines.extend(_pq2_item_lines(actionable, todo_mod=todo_mod))
    # 等你提供的文件（2026-10-06 使用者指示；Phase 7 failure log #29）：拿不到的來源要開口、不 park。
    # 開了口的住 pq2 `source_trace_review`；這一行讓「等你拿文件」自己出現（L14），不靠人記得去翻 skill。
    # 與上面同一個 SSOT（`active_items`）——不另外從 lead registry 數 `trace_requires_user`（L16）。
    asking = [it for it in active if it.get("type") == "source_trace_review"]
    section.lines.append(
        f"**等你提供的文件 {len(asking)}**（pq2 `source_trace_review` 未結案；拿不到的來源要開口、不 park）"
        + (("：" + "、".join(f"[{it.get('n')}]" for it in asking[:6])) if asking else "")
    )

    # 到期（Phase 1 Step 1.7／1.8；A3、A7）：今日與累計分開，累計照處置封閉字彙逐格列——加起來要等於累計。
    section.lines.append(_expiry_line(watches, now=moment, event_watch=event_watch))
    line = f"事件監看總數 {len(watches)}"
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
    # 題材掃描（Phase 1 Step 1.8／1.9）：**每天都印**；≥ 門檻時粗體（訊息第一行另由 compose 放一份）。
    try:
        section.lines.append(theme_scan_line(now=moment)[0])
    except Exception as exc:  # noqa: BLE001
        section.lines.append(f"題材掃描：盤點失敗（{type(exc).__name__}；upstream_unavailable）")
    return section


#: pq2 逐筆最多印幾筆（其餘寫「其餘 N 筆」）。
PQ2_LIST_LIMIT = 10


def _pq2_item_lines(actionable: Sequence[Mapping[str, Any]], *, todo_mod: Any) -> list[str]:
    if not actionable:
        return []
    lines = []
    items = sorted(actionable, key=lambda i: int(i["n"]))
    for item in items[:PQ2_LIST_LIMIT]:
        auth = todo_mod.go_authorization(str(item.get("type")))
        title = " ".join(str(item.get("title") or "").split())
        lines.append(f"  [{item['n']}] {title[:70]}{'…' if len(title) > 70 else ''}"
                     f"｜go＝{auth['go_authorizes']}｜不含：{auth['go_excludes']}")
    if len(items) > PQ2_LIST_LIMIT:
        lines.append(f"  其餘 {len(items) - PQ2_LIST_LIMIT} 筆（`python -m engine_b.todo list`）")
    decisions = [int(i["n"]) for i in items if i.get("type") == "watch_decision"]
    others = [int(i["n"]) for i in items if i.get("type") != "watch_decision"]
    batch = "批次回覆：`<編號…> go <編號…> drop <編號…> pending`"
    if others:
        batch += f"（例：`{others[0]} go`）"
    if decisions:
        # 批次語法帶不了日期，watch_decision 的 bare go／bare pending 一定被拒（Step 1.7，第 2 輪 N-h）
        batch += (f"｜watch_decision {', '.join(map(str, decisions))} 在批次裡只能 drop；"
                  "續等：`python -m engine_b.todo resolve <n> --verb pending --until <日期>`；要研究就在互動 session 說")
    lines.append("  " + batch)
    return lines


#: 到期處置 kind → 心跳的短標籤。**鍵必須等於 `event_watch.EXPIRY_RESOLUTION_KINDS`**（測試守；L16）。
EXPIRY_KIND_LABELS: dict[str, str] = {
    "requeued_to_pq2": "翻回 pq2", "pq2_item_gone": "pq2 已結案", "trace_closed": "追源結案",
    "lead_already_terminal": "lead 早已終局", "lead_in_flight": "lead 在路上", "lead_closed": "lead 已結案",
    "lead_missing": "lead 不存在", "superseded_by_newer_watch": "已有新等待", "reading_expiry": "讀圖到期",
    "source_superseded": "來源已換版", "dropped": "放棄", "touched": "判定已發生",
    "narrative_rewritten": "敘事重寫已處置",
}


def _expiry_line(watches: Sequence[Mapping[str, Any]], *, now: datetime, event_watch: Any) -> str:
    """今日到期 a｜累計 b＝各處置 k 筆 ＋ 未處置（待決 watch_decision／等 thesis 複查／等重讀／等敘事重寫（Phase 3 Step 3.4）／其他）。"""
    expired = [w for w in watches if w.get("status") == "expired"]
    touched = [w for w in watches if (w.get("expiry_resolution") or {}).get("kind") == "touched"]
    today = now.astimezone().date()
    today_n = sum(1 for w in expired + touched if _local_day(w.get("expired_at")) == today)
    by_kind: dict[str, int] = {}
    unresolved: dict[str, int] = {}
    for w in expired + touched:
        kind = (w.get("expiry_resolution") or {}).get("kind")
        if kind:
            by_kind[kind] = by_kind.get(kind, 0) + 1
        else:
            cls = event_watch.expiry_class(w)
            unresolved[cls] = unresolved.get(cls, 0) + 1
    total = len(expired) + len(touched)
    done = "、".join(f"{EXPIRY_KIND_LABELS.get(k, k)} {n}" for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1]))
    pending = (f"待決 watch_decision {unresolved.get('decision', 0)}｜等 thesis 複查 {unresolved.get('thesis_review', 0)}"
               f"｜等重讀 {unresolved.get('reread', 0)}｜等敘事重寫 {unresolved.get('rewrite', 0)}")
    other = sum(n for cls, n in unresolved.items() if cls not in ("decision", "thesis_review", "reread", "rewrite"))
    if other:
        pending += f"｜其他未處置 {other}"
    exp = event_watch.expiry_counters({"watches": list(watches)}, today=today)
    return (f"watch 到期：今日 {today_n}｜累計 {total}（已處置：{done or '0'}；{pending}）"
            f"｜追源到期結案今日 {exp['trace_expired_closed_today']}")


def theme_scan_line(*, now: datetime) -> tuple[str, bool]:
    """(那一行, 是否已達門檻)。門檻 `config/daily_routine.json` 的 `theme_scan.nudge_after_days`。"""
    from engine_b.routine_config import load_theme_scan
    from engine_b.theme_scan import last_scan

    threshold = load_theme_scan()["nudge_after_days"]
    scan = last_scan(today=now.astimezone().date())
    if scan["date"] is None:
        return (f"**距上次掃題材：從來沒掃過**（門檻 {threshold} 天；說「掃題材」啟動 `skills/theme-scan`）", True)
    days = int(scan["days"])
    if days >= threshold:
        return (f"**距上次掃題材 {days} 天**（{scan['date']}；門檻 {threshold} 天——說「掃題材」啟動 `skills/theme-scan`）",
                True)
    return (f"距上次掃題材 {days} 天（{scan['date']}；門檻 {threshold} 天）", False)


#: `rate_limit_info.status` 與 `rateLimitType` 的人話（2026-10-01 探針實測的值；認不得的照印原字）。
QUOTA_STATUS_WORDS: Mapping[str, str] = {"allowed_warning": "接近上限", "rejected": "已用完（本輪 LLM 步驟被擋）"}
QUOTA_WINDOW_WORDS: Mapping[str, str] = {"seven_day": " 7 天", "five_hour": " 5 小時", "seven_day_opus": " 7 天（Opus）",
                                         "seven_day_sonnet": " 7 天（Sonnet）"}


def _prescreen_and_quota_lines(*, now: datetime, record_path: Path | None) -> list[str]:
    record, problem = _load_run_record(record_path, now=now)
    if record is None:
        return [f"預篩：{problem}"]
    rows = {str(r.get("key")): r for r in record.get("steps") or [] if isinstance(r, Mapping)}
    lines = []
    apply = rows.get("10c_prescreen_apply")
    propose = rows.get("10b_prescreen_propose") or {}
    if apply is None and "10a_prescreen_prepare" not in rows:
        lines.append("預篩：執行紀錄裡沒有預篩步驟")
    elif apply is not None and apply.get("status") == "ok" and isinstance(apply.get("summary"), Mapping):
        s = apply["summary"]
        v = s.get("by_verdict") or {}
        lines.append(f"預篩 {s.get('batch', '?')}｜標旗 {s.get('flagged', '?')}（可能觸及 {v.get('likely_touches', 0)}"
                     f"／無關 {v.get('likely_unrelated', 0)}／看不出 {v.get('cannot_tell', 0)}）"
                     f"｜無全文 {s.get('no_text', '?')}｜無 fetcher {s.get('no_fetcher', '?')}"
                     f"｜截斷 {s.get('truncated', '?')}｜拒收 {s.get('rejected', '?')}")
    else:
        step = apply or propose
        lines.append(f"預篩：本輪沒完成（{(step or {}).get('status')}：{(step or {}).get('reason') or (step or {}).get('error') or '—'}）")
    # 額度：同一個狀態＋同一個窗只印一行（兩個 LLM 步驟看到的是同一個帳號額度），寫成人話：用了幾成、幾點重置、
    # 用完會怎樣（2026-10-01 使用者問「LLM 額度是什麼問題」——原本只印 allowed_warning、seven_day、重置 ?）。
    seen: dict[tuple[Any, Any], dict[str, Any]] = {}
    for key in ("01c_radar_propose", "07a_triage_propose", "10b_prescreen_propose"):
        for call in (rows.get(key) or {}).get("calls") or []:
            limit = (call or {}).get("rate_limit") or {}
            if limit and limit.get("status") not in (None, "allowed"):
                entry = seen.setdefault((limit.get("status"), limit.get("rateLimitType")), {"steps": [], **limit})
                if key not in entry["steps"]:
                    entry["steps"].append(key)
    for (status, kind), entry in seen.items():
        used = entry.get("utilization")
        used_text = f"已用 {used:.0%}" if isinstance(used, (int, float)) else "用量沒回報"
        reset = entry.get("resetsAt")
        try:
            reset_text = datetime.fromtimestamp(float(reset), timezone.utc).astimezone(now.tzinfo).strftime("%m-%d %H:%M")
        except (TypeError, ValueError, OverflowError, OSError):
            reset_text = "?"
        lines.append(f"⚠ **LLM 額度{QUOTA_STATUS_WORDS.get(str(status), '')}**（{status}）：Claude 訂閱"
                     f"{QUOTA_WINDOW_WORDS.get(str(kind), f' {kind or '?'} ')}額度{used_text}，{reset_text} 重置"
                     f"（{'、'.join(entry['steps'])}）——整個帳號的用量，含互動 session；用完時 daily 的分類、預篩與外部雷達"
                     "會暫停（記成 rate_limited），心跳照發")
    return lines


def radar_rejected(summary: Mapping[str, Any]) -> int:
    """外部雷達「拒收」的件數＝欄位不合法＋網址不在搜尋結果＋超過上限（**重複另計**，不算拒收）。段 3 那一行與快照共用。"""
    return sum(int(summary.get(k) or 0) for k in ("invalid", "url_not_in_search", "over_cap"))


def _radar_line(*, now: datetime, record_path: Path | None) -> str:
    """段 3「外部雷達：新 N｜重複 a｜拒收 b（網址不在搜尋結果 c、超過上限 d）｜提到在盯的條件 K｜沒有重要變化／沒跑（理由）」
    （Phase 7 Step 7.0f）。讀 daily 執行紀錄的套用步驟（①e 印出的 summary）；心跳不重跑、不讀 lead registry。"""
    record, problem = _load_run_record(record_path, now=now)
    if record is None:
        return f"外部雷達：{problem}"
    rows = {str(r.get("key")): r for r in record.get("steps") or [] if isinstance(r, Mapping)}
    apply = rows.get("01e_radar_apply")
    if apply is None and "01b_radar_prepare" not in rows:
        return "外部雷達：執行紀錄裡沒有雷達步驟"
    if apply is not None and apply.get("status") == "ok" and isinstance(apply.get("summary"), Mapping):
        s = apply["summary"]
        tail = "｜沒有重要變化" if s.get("no_material_change") and not s.get("new") else ""
        return (f"外部雷達：新 {s.get('new', '?')}｜重複 {s.get('duplicate', '?')}｜拒收 {radar_rejected(s)}"
                f"（網址不在搜尋結果 {s.get('url_not_in_search', '?')}、超過上限 {s.get('over_cap', '?')}"
                f"、欄位不合法 {s.get('invalid', '?')}）｜提到在盯的條件 {s.get('related', '?')}{tail}"
                f"｜搜尋 {s.get('searches', '?')} 次（只寫 secondary lead，不喚醒 watch）")
    step = next((rows[k] for k in ("01e_radar_apply", "01c_radar_propose", "01b_radar_prepare")
                 if k in rows and rows[k].get("status") != "ok"), None) or apply or {}
    return (f"外部雷達：沒跑（{step.get('key') or '?'} {step.get('status')}："
            f"{step.get('reason') or step.get('error') or '—'}）")


#: T2 輪詢在 daily 執行紀錄裡的四步（⑩d–⑩g）；套用那一步印出 summary。
T2_STEP_KEYS: tuple[str, ...] = ("10d_poll_prepare", "10e_poll_propose", "10g_poll_apply")


def _t2_run_text(*, now: datetime, record_path: Path | None) -> str:
    """今天這一輪 daily 的 T2 做了什麼（讀執行紀錄的 ⑩g summary；心跳不重跑、不讀收據）。"""
    record, problem = _load_run_record(record_path, now=now)
    if record is None:
        return f"本輪：{problem}"
    rows = {str(r.get("key")): r for r in record.get("steps") or [] if isinstance(r, Mapping)}
    apply = rows.get("10g_poll_apply")
    if apply is None and "10d_poll_prepare" not in rows:
        return "本輪：執行紀錄裡沒有 T2 步驟"
    if apply is not None and apply.get("status") == "ok" and isinstance(apply.get("summary"), Mapping):
        s = apply["summary"]
        if s.get("batch") == 0:
            return "本輪：沒有到期該查的等待（沒有呼叫模型）"
        return (f"本輪查 {s.get('checked', '?')}／{s.get('batch', '?')} 條｜新命中 {s.get('hits_new', '?')} 則"
                f"｜拒收 {s.get('rejected', '?')}（沒真的查 {s.get('not_searched', '?')}、網址不在搜尋結果 "
                f"{s.get('url_not_in_search', '?')}、重複 {s.get('duplicate_hit', '?')}、超過上限 {s.get('over_cap', '?')}）"
                f"｜搜尋 {s.get('searches', '?')} 次")
    propose = rows.get("10e_poll_propose") or {}
    if propose.get("status") == "ok" and propose.get("proposed") == 0 and "批次為空" in str(propose.get("note") or ""):
        return "本輪：沒有到期該查的等待（沒有呼叫模型）"
    step = next((rows[k] for k in T2_STEP_KEYS if k in rows and rows[k].get("status") != "ok"), None) or apply or {}
    return (f"本輪沒跑完（{step.get('key') or '?'} {step.get('status')}："
            f"{step.get('reason') or step.get('error') or '—'}）")


def _t2_line(*, now: datetime, record_path: Path | None = None) -> str:
    """段 3「T2 輪詢：本輪查 N／M 條｜新命中 K 則｜拒收…｜**命中待檢 P**｜可輪詢｜該查｜最後一次｜每日上限」。

    兩個問題分開答（同分類層那一行）：今天 daily 的 ⑩d–⑩g 做了什麼（執行紀錄）、等待登記現在的狀態
    （`engine_b.event_watch.t2_status`——與 `sweep` 同一份篩選，L16）。`stale`（有該查的、卻超過 `min_recheck_days`
    沒有任何一次輪詢＝輪詢沒在跑）時粗體並進 Discord 摘要行。命中只掛在等待上，判定只在互動。"""
    from engine_b import event_watch as ew

    s = ew.t2_status(ew.load_watches(), today=now.astimezone().date())
    if not s["enabled"]:
        return "T2 輪詢：關閉（`config/event_watch.json` 的 enabled／sweep_budget_per_run）"
    last = "從來沒有" if s["last_run"] is None else f"{s['last_run']}（{s['last_run_days']} 天前）"
    oldest = f"（最久 {s['oldest_due_days']} 天沒查）" if s["due"] and s["oldest_due_days"] is not None else ""
    if s["hits_pending"]:
        pending = (f"**命中待檢 {s['hits_pending']}**（{s['hits_pending_watches']} 條等待；最老 {s['oldest_hit_days']} 天；"
                   "判定只在互動：`python -m engine_b.watch_poll queue`）")
    else:
        pending = "命中待檢 0"
    line = (f"T2 輪詢：{_t2_run_text(now=now, record_path=record_path)}｜{pending}"
            f"｜可輪詢 {s['eligible']}｜該查 {s['due']}{oldest}｜最後一次 {last}｜每日上限 {s['budget']}")
    return f"⚠ **{line}**" if s["stale"] else line


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
    from engine_b.event_watch import _triage_written_by_requeue
    from engine_b.leads import SEMANTIC_CLASSIFIER
    from engine_b.queue_segments import classifier_of

    stamps = []
    interactive = 0
    for lead in leads.values():
        triage = (lead or {}).get("triage") or {}
        # 三種寫 triage 時間、卻不是分類層跑過的寫入者（L12：一個欄位兩種語意）：
        # harvest 的機械 FILTER（Form 4，寫入端標 `harvest:`）、**舊式**追源重排（2026-09-26 前會把 receipt
        # 改寫成排回那天；判別沿用 event_watch 的同一個函式，不另寫一份）、互動 session 自己鑄自己 triage 的
        # lead（`classified_by` 不是分類層，Phase 4 Step 4.5b）——後者另計、不算「分類層上次成功」。
        if str(triage.get("decided_by") or "").startswith("harvest:") or _triage_written_by_requeue(lead or {}):
            continue
        if classifier_of(lead or {}) not in (SEMANTIC_CLASSIFIER, "unclassified"):
            interactive += 1
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
    # 互動 triage 另計（0 也印——它不印，就分不出「分類層有在出貨」與「是 session 自己在鑄」）。
    tail += f"｜互動 triage {interactive} 則（不算分類層）"
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
    # NAV（Phase 1 Step 1.8）：bucket 分布、最大單筆占 NAV——**只呈現**，完整表在 APP positions。
    # producer 是 `webapp materialize --positions`（讀 Sheet readonly）；心跳零網路，只讀 artifact。
    if pos_absence is not None:
        section.lines.append(f"NAV：{pos_absence.reason}（{pos_absence.kind}）")
    else:
        section.lines.append(_nav_line(positions.get("nav_exposure")))
    if pos_absence is not None:
        section.lines.append(f"追蹤表：{pos_absence.reason}（{pos_absence.kind}）")
    else:
        aggregate = positions.get("aggregate") or {}
        counters = positions.get("counters") or {}
        lanes = positions.get("lanes")
        # 三條 lane（Phase 5 Step 5.2）：分母分開——live 量買得準不準、paper 量判斷準不準、history 只是歷史。
        section.lines.append(_lane_count_line(lanes, positions.get("theme_cohort")))
        history_excess = ((lanes or {}).get("history") or {}).get("theme_cohort_excess") or {}
        section.lines.append(
            f"追蹤表 {aggregate.get('n', '?')} 檔｜等權絕對 {_pct(aggregate.get('absolute'))}"
            f"｜對 {aggregate.get('benchmark', '?')} 超額 {_pct(aggregate.get('excess'))}"
            + (f"｜對主題等權組超額 {_cohort_excess_text(history_excess)}" if lanes is not None else "")
            + f"｜正式結算過 {counters.get('measured_outcomes', '?')} 筆"
        )
        health = positions.get("anchor_health") or {}
        if health:
            paper_chase = ((lanes or {}).get("paper") or {}).get("chase")
            section.lines.append(
                f"入圖前已漲（chasing）{health.get('chasing', '?')}/{health.get('paired', '?')} 檔"
                + (f"｜敘事前已漲（paper）{paper_chase.get('chasing', '?')}/{paper_chase.get('paired', '?')} 檔"
                   if paper_chase else "")
            )

    # ⚠ 2026-09-22（Phase 0 Step 0a.2）：這裡原本有四行，全部讀籃子／多年視角 artifact——
    # 賭注帳（Q2）、量的候選（Q1）、要幾倍（Step 7.4）、歸零旗標彙總。
    # 2026-09-29（Phase 3 Step 3.6）：「賭注帳／量的候選／要幾倍」那一行**刪除**——三個機制都已退役
    # （賭注帳＝估值鏈的賭注 overlay、量的候選＝籃子 filter、要幾倍＝多年反向橋；ROADMAP Phase 0／G1、G3），
    # 接手它們位置的候選狀態板印在段 2，不在這裡再印一次。歸零旗標彙總改讀候選板 artifact 的 rollup。
    board, board_absence = _load_state(state_dir, "candidates")
    if board_absence is not None:
        section.lines.append(f"歸零旗標彙總：{board_absence.reason}（{board_absence.kind}）"
                             "　←逐檔那盞燈仍在個股頁，停的只有這個彙總計數")
    else:
        # 歸零旗標帳（ARCHITECTURE §4.1 段 4）：**盞數與有紅燈的檔數分開**——「一檔亮四盞」與「四檔各亮一盞」
        # 是兩件事；⚠ 灰＝沒量到，不是綠，灰依 kind 分開印（缺席不得壓成一種）。取每檔「最差色」會把灰吞掉
        # （一綠三灰算成綠），2026-09-29 3.6 審查抓到後改回這個形狀。
        roll = board.get("rollup") or {}
        wipe = roll.get("wipeout") or {}
        lamps = wipe.get("lamps") or {}
        kinds = wipe.get("unlit_by_kind") or {}
        line = (f"歸零旗標 {wipe.get('companies', '?')} 檔 × 4 盞：紅 {lamps.get('red', '?')}｜黃 {lamps.get('amber', '?')}"
                f"｜綠 {lamps.get('green', '?')}｜**灰（沒量到）{lamps.get('unlit', '?')}**"
                + (f"（{'、'.join(f'{k} {v}' for k, v in kinds.items())}）" if kinds else "")
                + "——⚠ 灰不是綠")
        red = list(wipe.get("red_tickers") or ())
        if red:
            line += "；有紅燈 " + str(len(red)) + " 檔：" + "、".join(red[:8]) + ("…" if len(red) > 8 else "")
        section.lines.append(line)
        not_read = (roll.get("not_read") or {}).get("tickers") or []
        if not_read:
            section.lines.append(f"歸零旗標讀不到 {len(not_read)} 檔：" + "、".join(not_read[:8])
                                 + ("…" if len(not_read) > 8 else "") + "（理由在候選板 artifact 的 rollup.not_read）")

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
        # Phase 6 Step 6.7a：錨逐列（先從瓶頸節點走、走不到才退回公司）。退回公司的列數跟著印，
        # 讓「這個錨是節點自己接到的」與「只是公司接到的」不在同一個計數裡同形（L12）；
        # 列上沒有 `anchor_basis` 的舊 artifact 照實說是公司側，不印成「公司層 0 列」。
        if rows and not any("anchor_basis" in row for row in rows):
            basis = "；錨是公司側（artifact 早於逐列錨）"
        else:
            basis = f"；公司層 {sum(1 for row in rows if row.get('anchor_basis') == 'company')} 列"
        section.lines.append(
            f"結構表 {len(rows)} 條邊分佈在 {len(anchors)} 個需求錨（前三：{shape}{basis}）"
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
        # paper／live 各一行三量＋對主題等權組超額（history 就是上面那一行）。空 lane 印「還沒有列」，不印 0%。
        lanes = positions.get("lanes")
        if lanes is not None:
            for lane in ("paper", "live"):
                section.lines.append(_lane_power_line(lane, (lanes or {}).get(lane)))
    # 圖預測對錯表（Phase 5 Step 5.4）：讀圖 artifact 的 `predictions` 照抄一行；只印不判、不排序。
    section.lines.append(_predictions_line(state_dir))

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


#: 段 4 的 lane 名稱（人讀）。**定義住 outcome 腳本的 `LANE_LABELS`**，這裡只是一行裡的短標。
_LANE_SHORT = {"history": "history（舊店入圖日）", "paper": "paper（第一份 v2 敘事日起）", "live": "live（trade_log 成交）"}


def _lane_count_line(lanes: Mapping[str, Any] | None, cohort: Mapping[str, Any] | None) -> str:
    """「追蹤表 history N｜paper N｜live N」——三條 lane 的列數一行；artifact 沒有 `lanes` 是缺席，不是 0。"""
    if lanes is None:
        return "追蹤表三條 lane：這份 positions artifact 還沒有 lanes（下一次 materialize --positions 補上；不是 0）"
    live = lanes.get("live") or {}

    def count(lane: str) -> str:
        entry = lanes.get(lane) or {}
        return "讀不到" if entry.get("absence") else str(entry.get("n", "?"))

    text = (f"追蹤表 history {count('history')}｜paper {count('paper')}"
            f"｜live {count('live')}（beta 事件 {live.get('beta_events', '?')} 不進 lane）")
    cohort = cohort or {}
    if cohort.get("absence"):
        text += f"｜主題等權組：{cohort['absence'].get('kind')}（超額缺席，不是 0）"
    elif isinstance(cohort.get("cohorts"), list):
        # 多主題等權組 S1（2026-10-06）：每一列只跟自己所屬的組比——這一格只印「有幾組」，組名與缺席名單在 APP。
        text += f"｜主題等權組 {len(cohort['cohorts'])} 組（每列只比自己的組）"
    elif cohort:
        text += "｜主題等權組：artifact 早於每列分組（下一次 materialize --positions 補上）"
    return text


def _cohort_excess_text(excess: Mapping[str, Any]) -> str:
    if not excess or not excess.get("n"):
        return f"還沒有值（{(excess or {}).get('of', 0)} 列量得到報酬）"
    return f"{_pct(excess.get('mean'))}（{excess.get('n')}/{excess.get('of')} 列）"


def _lane_power_line(lane: str, entry: Mapping[str, Any] | None) -> str:
    """一條 lane 一行：三量（D15）＋對主題等權組的超額。空 lane 印 outcome 腳本給的那句「還沒有列」。"""
    label = _LANE_SHORT[lane]
    if not entry:
        return f"{label}：artifact 沒有這條 lane（upstream_unavailable）——不是 0"
    if entry.get("absence"):
        absence = entry["absence"]
        return f"{label}：{absence.get('reason')}（{absence.get('kind')}）——不是 0，也不是「還沒有列」"
    if not entry.get("n"):
        return f"{label}：{entry.get('empty_text') or '還沒有列'}"
    power = entry.get("power_law") or {}
    if not power.get("n"):
        return (f"{label}：{entry.get('n')} 列、量得到報酬的 0 列（缺席：{'、'.join(entry.get('absences') or ()) or '—'}）"
                "——不是 0%")
    top = power.get("top_contributor") or {}
    m12 = (power.get("maturity") or {}).get("12m") or {}
    maturity_text = (f"12 個月內達 2 倍 {m12.get('reached_2x', 0)}/{m12.get('matured')}（{_pct(m12.get('share'))}）"
                     if m12.get("matured") else
                     f"還沒有一檔滿 12 個月（最長持有 {power.get('max_days_held', '?')} 天）")
    return (f"{label}：{power.get('n')} 檔｜量測起始 {power.get('measurement_start', '?')}"
            f"｜等權總報酬 {_pct(power.get('basket_total_return'))}"
            f"｜最大單檔 {top.get('ticker', '?')} {_pct(top.get('contribution'))}"
            f"／其餘 {top.get('rest_n', '?')} 檔 {_pct(top.get('rest_contribution'))}"
            f"｜曾達 2 倍 {power.get('reached_2x_ever', '?')}/{power.get('n', '?')}"
            f"（現價仍達 {power.get('reached_2x_now', '?')}）｜{maturity_text}"
            f"｜對主題等權組超額 {_cohort_excess_text(entry.get('theme_cohort_excess') or {})}")


_WRONG_OUTCOMES = ("reversed", "disproof_touched", "retracted")


def _predictions_line(state_dir: Path | None) -> str:
    """「圖預測：對 N｜錯 M（當時已有 a／之後才出現 b／未定日 c）｜現行 K｜到期未重讀 J｜改寫 R｜非斷言 Z」。
    讀不到 artifact、artifact 還沒有這段、as-of 視角拒絕——三種缺席各自說，都不印 0（INV-3）。"""
    payload, absence = _load_state(state_dir, "structure_readings")
    if absence is not None:
        return f"圖預測：{absence.reason}（{absence.kind}）"
    table = payload.get("predictions")
    if table is None:
        return "圖預測：這份 structure_readings artifact 還沒有 predictions（下一次 materialize --structure-readings 補上；不是 0）"
    if table.get("absence"):
        return f"圖預測：{table['absence'].get('reason')}（{table['absence'].get('kind')}）——不是 0"
    counts = table.get("counts") or {}
    kinds = {k: sum(int((counts.get(o) or {}).get(k) or 0) for o in _WRONG_OUTCOMES)
             for k in ("already_available", "emerged_later", "undated", "upstream_unavailable")}
    text = (f"圖預測：對 {counts.get('held', 0)}｜錯 {table.get('wrong_total', 0)}（當時已有 {kinds['already_available']}"
            f"／之後才出現 {kinds['emerged_later']}／未定日 {kinds['undated']}"
            + (f"／日期讀不到 {kinds['upstream_unavailable']}" if kinds["upstream_unavailable"] else "") + "）"
            f"｜現行 {counts.get('open', 0)}｜到期未重讀 {counts.get('expired_unread', 0)}"
            f"｜改寫 {counts.get('rewritten', 0)}｜非斷言 {counts.get('non_assertion', 0)}")
    if table.get("earliest_open_expiry"):
        text += f"｜現行最早到期 {table['earliest_open_expiry']}"
    if table.get("unreadable_nodes"):
        text += f"｜⚠ ledger 有壞行的節點 {len(table['unreadable_nodes'])} 個不在表內"
    return text


def _nav_line(nav: Mapping[str, Any] | None) -> str:
    if nav is None:
        return "NAV：這份 positions artifact 還沒有 nav_exposure（upstream_unavailable；下一次 materialize --positions 補上）"
    if nav.get("status") != "available":
        return (f"NAV：持股讀不到（{nav.get('status')}"
                + (f"：{nav.get('failure')}" if nav.get("failure") else "")
                + (f"；{'、'.join(map(str, nav.get('blockers') or []))}" if nav.get("blockers") else "")
                + "）——不是「沒有持股」")
    buckets = sorted((nav.get("buckets") or {}).items(), key=lambda kv: -float(kv[1]))
    largest = nav.get("largest") or {}
    shape = "、".join(f"{k} {_pct(v, 1)}" for k, v in buckets) or "—"
    line = (f"NAV：{shape}｜最大單筆 {largest.get('ticker', '—')} {_pct(largest.get('nav_pct'), 1)}"
            f"（{nav.get('positions', '?')} 檔；只呈現，完整表在 APP positions）")
    if any("槓桿" in str(k) for k, _v in buckets):
        # AGENTS：兩個槓桿指標不得混用——bucket 名稱照 Sheet，這一格是 nominal_weight，不是 effective_weight
        line += "｜「槓桿」格＝投入槓桿 ETF 的資金占 NAV，不是乘上倍數後的曝險"
    return line


# ---------------------------------------------------------------------------
# 段 5｜帳號計分表（每天）
# ---------------------------------------------------------------------------

def build_scorecard(*, state_dir: Path | None = None, previous: Mapping[str, Any] | None = None) -> Section:
    """D5 帳號計分表：**每天印** tier 分布＋較昨變化（Phase 1 Step 1.8；原本只在 weekly）。完整表在 APP。

    **只讀已 materialize 的 artifact**——心跳零網路，價格不在這裡抓（daily ⑬ 跑 `materialize --scorecard`）；
    讀不到就誠實說讀不到，**不偷偷重建**（APP 呈現契約的同一條紀律）。`previous` 是上一份快照的值。
    """
    section = Section(5, SECTION_TITLES[4])
    card, absence = _load_state(state_dir, "account_scorecard")
    if absence is not None or not card:
        section.absence = absence or Absence(
            "upstream_unavailable", "計分表 artifact 還沒 materialize 過")
        section.lines.append(f"{section.absence.reason}（{section.absence.kind}）")
        section.lines.append("→ 跑 `python -m webapp materialize --scorecard` 之後這一段才有內容")
        return section
    counts = card.get("tier_counts") or {}
    line = ("tier 分佈：" + "／".join(f"{k} {v}" for k, v in counts.items())
            + f"｜{len(card.get('accounts') or [])} 個帳號｜計分表 as-of {card.get('as_of')}")
    if previous is None:
        line += "｜較昨：尚無上一份快照"
    else:
        moved = [f"{t} {previous.get(f'tier.{t}')}→{counts.get(t)}" for t in SCORECARD_TIERS
                 if previous.get(f"tier.{t}") != counts.get(t)]
        line += "｜較昨：" + ("、".join(moved) if moved else "沒有變化")
    section.lines.append(line)
    biases = list(card.get("known_biases") or [])
    section.lines.append("完整表（每個帳號的量測窗、點名數、超額報酬、追源成功率）在 APP 帳號計分表頁"
                         + (f"｜已知偏差 {len(biases)} 條（也在 APP）" if biases else "")
                         + f"｜{_scorecard_cohort_cell(card)}")
    return section


def _scorecard_cohort_cell(card: Mapping[str, Any]) -> str:
    """段 5 的一格（Phase 5 Step 5.5）：計分表的第三個基準（主題等權組）**有沒有**——不印數字（數字在 APP）。
    「無」帶缺席種類；artifact 早於 5.5 沒有這一段＝照實說，不壓成「無」（L12：兩種沒有不同形）。"""
    block = card.get("theme_cohort")
    if not isinstance(block, Mapping):
        return "主題等權組基準：計分表 artifact 早於這一格"
    absence = block.get("absence")
    if absence:
        return f"主題等權組基準：無（{(absence or {}).get('kind')}）"
    if not isinstance(block.get("cohorts"), list):
        return "主題等權組基準：計分表 artifact 早於每則點名分組（下一次 materialize --scorecard 補上）"
    return f"主題等權組基準：有（{len(block['cohorts'])} 組，每則點名只比自己的組）"


# ---------------------------------------------------------------------------
# 快照與較昨變動（Phase 1 Step 1.8）
# ---------------------------------------------------------------------------

SNAPSHOT_DIR = ROOT / "library" / "private" / "heartbeat" / "snapshots"
SNAPSHOT_RETENTION_DAYS = 14

#: 快照的鍵用到的封閉字彙——**與各自的 SSOT 相等**（測試守；L16）。
LEAD_STATUSES: tuple[str, ...] = ("pending", "triaged_go", "triaged_no_go", "researching", "action_prepared",
                                  "applied", "parked")          # engine_b.leads.ALL_STATUSES
THESIS_STATUSES: tuple[str, ...] = ("active", "watch", "review_required", "realized", "revised",
                                    "retired")                  # thesis.pending_lifecycle.ALLOWED_TRANSITIONS
SCORECARD_TIERS: tuple[str, ...] = ("probation", "measured", "trusted")   # engine_b.signal_source_registry.TIERS

#: 快照的鍵是**封閉清單**（鍵 → 人讀標籤）。改這裡就是改 diff 的語意，要一起改測試。
SNAPSHOT_KEYS: dict[str, str] = {
    "watch.active": "watch 在等", "watch.fired": "watch 已觸發未消化", "watch.expired": "watch 已到期",
    "watch.consumed": "watch 已收",
    "semantic.active": "語意 watch 在盯", "semantic.pending_check": "語意 watch 未檢",
    "semantic.flagged": "語意 watch 標旗",
    # T2 主動輪詢（2026-10-06）：該查幾條（輪詢跑過那天降）、命中待檢幾則（判定做了那天降）——較昨 diff 看得到兩邊有沒有在動。
    "t2.due": "T2 該查", "t2.hits_pending": "T2 命中待檢",
    "pq2.open": "pq2 未結案", "pq2.actionable": "pq2 球在你",
    # 等你提供的文件（2026-10-06 使用者指示；Phase 7 failure log #29）：拿不到的來源要開口、不 park，
    # 開了口的住 pq2 `source_trace_review`——第一次有人開口的那天，較昨 diff 看得到。
    "pq2.source_trace_review": "等你提供的文件",
    **{f"lead.{s}": f"lead {s}" for s in LEAD_STATUSES},
    "reading.current": "讀圖現行", "reading.needs_reread": "讀圖該重讀",
    # 走圖九型各自的命中（Phase 2 Step 2.6）——由封閉字彙導出，不抄一份（L16）；各自一鍵、不加總。
    **{f"walk.{q.key}": f"走圖 {q.short}" for q in WALK_QUESTION_TYPES},
    **{f"thesis.{s}": f"thesis {s}" for s in THESIS_STATUSES},
    "disproof.watching": "反證在盯", "disproof.unreachable": "反證叫不醒",
    "disproof.touched_pending": "反證觸及待處置", "disproof.expired_pending": "反證到期待複查",
    "disproof.unwatched": "反證未盯", "thesis.sidecar_mismatch": "thesis sidecar 不符",
    # 加碼條件（Phase 7 Step 7.0d）：與反證分開——第一條加碼條件寫下、第一次觸及的那天，較昨 diff 看得到
    "confirm.watching": "加碼條件在盯", "confirm.touched_pending": "加碼條件觸及待處置",
    "confirm.expired_pending": "加碼條件到期待重寫",
    "prescreen.no_text": "預篩無全文", "prescreen.no_fetcher": "預篩無 fetcher",
    # 外部雷達（Phase 7 Step 7.0f）：上線那天與八週試驗期間，較昨 diff 看得到它每天收了幾則、拒了幾則
    "radar.new": "外部雷達新 lead", "radar.duplicate": "外部雷達重複", "radar.rejected": "外部雷達拒收",
    "radar.related": "外部雷達提到在盯的條件",
    "health.red": "健康紅燈", "invariants.fail": "invariants FAIL",
    **{f"tier.{t}": f"帳號 {t}" for t in SCORECARD_TIERS},
    # 候選板（Phase 3 Step 3.6）：每一組一鍵——由候選推導的封閉字彙導出，不抄一份（L16）。
    **{f"candidate.{g}": f"候選 {CANDIDATE_GROUP_LABELS[g]}" for g in CANDIDATE_GROUPS},
    **{f"candidate.{g}": f"候選 {CANDIDATE_SIDE_LABELS[g]}" for g in CANDIDATE_SIDE_GROUPS},
    "candidate.no_narrative": "候選 無敘事",
    # 追蹤表三條 lane（Phase 5 Step 5.2）：列數與曾達 2 倍——較昨 diff 看得到第一筆回填、第一份新敘事、第一個 2 倍。
    "positions.lane.paper.n": "追蹤表 paper 列數", "positions.lane.live.n": "追蹤表 live 列數",
    **{f"positions.lane.{lane}.reached_2x_ever": f"{lane} 曾達 2 倍" for lane in ("history", "paper", "live")},
    # 圖預測對錯表（Phase 5 Step 5.4）：第一筆對／錯出現的那天，較昨 diff 看得到。
    "predictions.held": "圖預測 對", "predictions.wrong": "圖預測 錯",
    "predictions.expired_unread": "圖預測 到期未重讀",
}
#: 較昨變動一行最多列幾項（其餘寫「另 N 項」）。
DIFF_LIMIT = 12


def collect_snapshot(*, now: datetime, state_dir: Path | None, leads_path: Path, thesis_path: Path,
                     run_record_path: Path | None, capture_dir: Path | None) -> dict[str, int | None]:
    """每個鍵各自讀、各自降級：讀不到就是 None（「沒讀到」不是 0，INV-3）。"""
    values: dict[str, int | None] = {key: None for key in SNAPSHOT_KEYS}

    def guard(fn: Callable[[], Mapping[str, Any]]) -> None:
        try:
            values.update({k: (None if v is None else int(v)) for k, v in fn().items() if k in SNAPSHOT_KEYS})
        except Exception:  # noqa: BLE001 — 一組讀不到不帶走其他組
            pass

    def watches() -> dict[str, Any]:
        from engine_b import event_watch as ew

        data = ew.load_watches()
        rows = data.get("watches") or []
        c = ew.counters(data)
        out = {f"watch.{s}": sum(1 for w in rows if w.get("status") == s)
               for s in ("active", "fired", "expired", "consumed")}
        out.update({"semantic.active": c["semantic_active"], "semantic.pending_check": c["semantic_pending_check"],
                    "semantic.flagged": c["semantic_flagged"]})
        return out

    def t2() -> dict[str, Any]:
        # 獨立一組：T2 設定讀壞了不該把整組 watch 鍵一起拖成「未讀到」
        from engine_b import event_watch as ew

        s = ew.t2_status(ew.load_watches(), today=now.astimezone().date())
        return {"t2.due": s["due"], "t2.hits_pending": s["hits_pending"]}

    def pq2() -> dict[str, Any]:
        from engine_b import todo as todo_mod

        pool = todo_mod.load()
        active = todo_mod.active_items(pool)
        return {"pq2.open": len(active), "pq2.actionable": len(todo_mod.actionable_items(pool)),
                "pq2.source_trace_review": sum(1 for it in active if it.get("type") == "source_trace_review")}

    def lead_states() -> dict[str, Any]:
        leads = (_read_json(leads_path) or {}).get("leads") or {}
        return {f"lead.{s}": sum(1 for lead in leads.values() if (lead or {}).get("status") == s)
                for s in LEAD_STATUSES}

    def readings() -> dict[str, Any]:
        payload, absence = _load_state(state_dir, "structure_readings")
        if absence is not None:
            return {}
        return {"reading.current": (payload.get("counts") or {}).get("current"),
                "reading.needs_reread": (payload.get("needs_reread") or {}).get("n")}

    def walk() -> dict[str, Any]:
        payload, absence = _load_state(state_dir, "graph_walk")
        if absence is not None:
            return {}
        return {f"walk.{q.get('key')}": q.get("hit_n") for q in payload.get("questions") or ()
                if not q.get("absence")}

    def thesis() -> dict[str, Any]:
        payload = _read_json(thesis_path)
        entries = [e for e in (payload.values() if isinstance(payload, Mapping) else []) if isinstance(e, Mapping)]
        return {f"thesis.{s}": sum(1 for e in entries if e.get("status") == s) for s in THESIS_STATUSES}

    def disproof_counts() -> dict[str, Any]:
        from engine_b import disproof
        from engine_b import event_watch as ew

        try:
            coverage: frozenset[str] | None = ew.primary_coverage()
        except Exception:  # noqa: BLE001
            coverage = None
        c = disproof.disproof_counts(ew.load_watches().get("watches") or [], readings=disproof.current_readings(),
                                     coverage=coverage)
        if c.get("lifecycle_unreadable"):
            return {}
        return {"disproof.watching": c["watching"], "disproof.unreachable": c["unreachable"],
                "disproof.touched_pending": c["touched_pending"], "disproof.expired_pending": c["expired_pending"],
                "disproof.unwatched": c["unwatched"], "thesis.sidecar_mismatch": len(c["thesis_sidecar_mismatch"])}

    def confirm_counts() -> dict[str, Any]:
        # Phase 7 Step 7.0d：加碼條件三格（與段 2 那一行同一個函式）；不吃 lifecycle，讀不到 registry 才缺席
        from engine_b import disproof
        from engine_b import event_watch as ew

        k = disproof.confirm_counts(ew.load_watches().get("watches") or [])
        return {"confirm.watching": k["watching"], "confirm.touched_pending": k["touched_pending"],
                "confirm.expired_pending": k["expired_pending"]}

    def prescreen() -> dict[str, Any]:
        record, _problem = _load_run_record(run_record_path, now=now)
        step = next((r for r in (record or {}).get("steps") or []
                     if isinstance(r, Mapping) and r.get("key") == "10c_prescreen_apply"), None)
        summary = (step or {}).get("summary") or {}
        return {"prescreen.no_text": summary.get("no_text"), "prescreen.no_fetcher": summary.get("no_fetcher")}

    def radar() -> dict[str, Any]:
        # Phase 7 Step 7.0f：外部雷達的四格（與段 3 那一行讀同一個套用步驟的 summary）；沒跑＝缺席，不是 0
        record, _problem = _load_run_record(run_record_path, now=now)
        step = next((r for r in (record or {}).get("steps") or []
                     if isinstance(r, Mapping) and r.get("key") == "01e_radar_apply"), None)
        summary = (step or {}).get("summary") if (step or {}).get("status") == "ok" else None
        if not isinstance(summary, Mapping):
            return {}
        return {"radar.new": summary.get("new"), "radar.duplicate": summary.get("duplicate"),
                "radar.rejected": radar_rejected(summary), "radar.related": summary.get("related")}

    def captures() -> dict[str, Any]:
        out: dict[str, Any] = {}
        health, problem = _capture("health", now=now, capture_dir=capture_dir)
        if problem is None:
            out["health.red"] = sum(1 for s in (health or {}).get("sections") or [] if s.get("level") == "red")
        checks, problem = _capture("invariants", now=now, capture_dir=capture_dir)
        if problem is None:
            out["invariants.fail"] = sum(1 for c in checks or [] if c.get("status") == "FAIL")
        return out

    def tiers() -> dict[str, Any]:
        card, absence = _load_state(state_dir, "account_scorecard")
        if absence is not None or not card:
            return {}
        counts = card.get("tier_counts") or {}
        return {f"tier.{t}": counts.get(t) for t in SCORECARD_TIERS}

    def candidates() -> dict[str, Any]:
        board, absence = _load_state(state_dir, "candidates")
        if absence is not None:
            return {}
        counts = board.get("counts") or {}
        return {f"candidate.{k}": counts.get(k) for k in (*CANDIDATE_GROUPS, *CANDIDATE_SIDE_GROUPS, "no_narrative")}

    def positions() -> dict[str, Any]:
        payload, absence = _load_state(state_dir, "positions")
        lanes = None if absence is not None else payload.get("lanes")
        if not lanes:
            return {}                        # 舊 artifact 沒有 lanes：讀不到＝None，不是 0
        def read(lane: str) -> Mapping[str, Any]:
            entry = lanes.get(lane) or {}
            return {} if entry.get("absence") else entry     # 組不出來的 lane：None（未讀到），不是 0

        out: dict[str, Any] = {f"positions.lane.{lane}.n": read(lane).get("n") for lane in ("paper", "live")}
        out.update({f"positions.lane.{lane}.reached_2x_ever": (read(lane).get("power_law") or {}).get("reached_2x_ever")
                    for lane in ("history", "paper", "live")})
        return out

    def predictions() -> dict[str, Any]:
        payload, absence = _load_state(state_dir, "structure_readings")
        table = None if absence is not None else payload.get("predictions")
        if not table or table.get("absence"):
            return {}                        # 讀不到／舊 artifact／as-of 拒絕：None（未讀到），不是 0
        counts = table.get("counts") or {}
        return {"predictions.held": counts.get("held"), "predictions.wrong": table.get("wrong_total"),
                "predictions.expired_unread": counts.get("expired_unread")}

    for fn in (watches, t2, pq2, lead_states, readings, walk, thesis, disproof_counts, confirm_counts, prescreen, radar,
               captures, tiers, candidates, positions, predictions):
        guard(fn)
    return values


def load_previous_snapshot(snapshot_dir: Path, *, today: date) -> tuple[dict[str, Any] | None, str | None]:
    """今天之前最新的一份（不一定是昨天——中間斷了就比最近那一份，並印出日期）。"""
    best: tuple[str, Path] | None = None
    for path in (snapshot_dir.glob("*.json") if snapshot_dir.is_dir() else ()):
        stem = path.stem
        if len(stem) == 10 and stem < today.isoformat() and (best is None or stem > best[0]):
            best = (stem, path)
    if best is None:
        return None, None
    try:
        payload = _read_json(best[1])
    except (OSError, ValueError):
        return None, None
    values = (payload or {}).get("values")
    return (values if isinstance(values, dict) else None), best[0]


def snapshot_diff_lines(current: Mapping[str, Any], previous: Mapping[str, Any] | None,
                        *, previous_date: str | None, today: date) -> list[str]:
    if previous is None:
        return ["較昨變動：尚無上一份快照（第一次產生；之後每天逐項比對，只印變了的）"]
    label = "較昨" if previous_date == (today.fromordinal(today.toordinal() - 1)).isoformat() else f"較 {previous_date} "

    def fmt(value: Any) -> str:
        return "未讀到" if value is None else str(value)

    # 新鍵（上一份快照裡根本沒有這個鍵）＝**首日**，不是「未讀到→N」的變動（Phase 3 Step 3.6，L11-6 ④）：
    # 把它算成變動，新增一組鍵的那天較昨會被灌滿、真正的變動被擠到「另 N 項」。
    first_day = [k for k in SNAPSHOT_KEYS if k not in previous]
    changed = [(k, previous.get(k), current.get(k)) for k in SNAPSHOT_KEYS
               if k in previous and previous.get(k) != current.get(k)]
    same = len(SNAPSHOT_KEYS) - len(changed) - len(first_day)
    tail = f"｜首日 {len(first_day)} 項（今天起比對：{'、'.join(SNAPSHOT_KEYS[k] for k in first_day[:4])}" \
           f"{'…' if len(first_day) > 4 else ''}）" if first_day else ""
    if not changed:
        return [f"{label}變動 0（{same} 項都相同）{tail}"]
    shown = "、".join(f"{SNAPSHOT_KEYS[k]} {fmt(a)}→{fmt(b)}" for k, a, b in changed[:DIFF_LIMIT])
    more = f"…另 {len(changed) - DIFF_LIMIT} 項" if len(changed) > DIFF_LIMIT else ""
    return [f"**{label}變動 {len(changed)} 項**：{shown}{more}｜其餘 {same} 項相同{tail}"]


def write_snapshot(snapshot_dir: Path, *, today: date, now: datetime, values: Mapping[str, Any]) -> Path:
    """寫今天的快照、刪掉超過保留天數的舊檔。快照是 derived，只給 diff 用。"""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    target = snapshot_dir / f"{today.isoformat()}.json"
    target.write_text(json.dumps({"schema": "heartbeat-snapshot-v1", "date": today.isoformat(),
                                  "generated_at": now.isoformat(), "values": dict(values)},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cutoff = today.fromordinal(today.toordinal() - SNAPSHOT_RETENTION_DAYS).isoformat()
    for path in snapshot_dir.glob("*.json"):
        if len(path.stem) == 10 and path.stem < cutoff:
            path.unlink(missing_ok=True)
    return target


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


@dataclass
class Heartbeat:
    """一次心跳的全部產出：五段、這次的快照值、訊息最上面的橫幅、Discord 摘要行。"""

    sections: list[Section]
    snapshot: dict[str, int | None]
    banner: list[str]
    summary: str


def compose_heartbeat(
    *,
    now: datetime | None = None,
    state_dir: Path | None = None,
    leads_path: Path | None = None,
    thesis_path: Path | None = None,
    run_record_path: Path | None = None,
    capture_dir: Path | None = None,
    snapshot_dir: Path | None = None,
) -> Heartbeat:
    """固定五段，順序固定，**任何情況下都回五個 Section**；另組快照、橫幅與摘要行（各自降級）。"""
    moment = now or datetime.now(timezone.utc)
    today = moment.astimezone().date()
    leads = leads_path or ROOT / "library" / "leads" / "pending_leads.json"
    thesis = thesis_path or ROOT / "thesis" / "lifecycle.json"
    snapshots = snapshot_dir or SNAPSHOT_DIR
    try:
        snapshot = collect_snapshot(now=moment, state_dir=state_dir, leads_path=leads, thesis_path=thesis,
                                    run_record_path=run_record_path, capture_dir=capture_dir)
    except Exception:  # noqa: BLE001
        snapshot = {key: None for key in SNAPSHOT_KEYS}
    try:
        previous, previous_date = load_previous_snapshot(snapshots, today=today)
    except Exception:  # noqa: BLE001
        previous, previous_date = None, None
    diff = snapshot_diff_lines(snapshot, previous, previous_date=previous_date, today=today)
    sections = [
        _guard(1, SECTION_TITLES[0],
               lambda: build_freshness(now=moment, state_dir=state_dir, leads_path=leads,
                                       run_record_path=run_record_path, capture_dir=capture_dir)),
        _guard(2, SECTION_TITLES[1],
               lambda: build_changes(now=moment, state_dir=state_dir, thesis_path=thesis, diff_lines=diff,
                                     leads_path=leads_path)),
        _guard(3, SECTION_TITLES[2], lambda: build_queue(state_dir=state_dir, now=moment,
                                                         run_record_path=run_record_path)),
        _guard(4, SECTION_TITLES[3], lambda: build_positions(state_dir=state_dir)),
        _guard(5, SECTION_TITLES[4], lambda: build_scorecard(state_dir=state_dir, previous=previous)),
    ]
    assert len(sections) == len(SECTION_TITLES), "心跳必須固定五段"
    banner: list[str] = []
    try:
        theme_line, nudge = theme_scan_line(now=moment)
        if nudge:
            banner.append(theme_line)   # ≥ 門檻：移到訊息第一行（段 3 照樣印）
    except Exception:  # noqa: BLE001
        theme_line, nudge = "", False
    try:
        summary = summary_line(now=moment, snapshot=snapshot, run_record_path=run_record_path, leads_path=leads,
                               theme_nudge=nudge, theme_line=theme_line)
    except Exception as exc:  # noqa: BLE001
        summary = f"Daily {today.isoformat()}｜⚠ 摘要行組不出來（{type(exc).__name__}）"
    return Heartbeat(sections=sections, snapshot=snapshot, banner=banner, summary=summary)


def build_heartbeat(**kwargs: Any) -> list[Section]:
    """固定五段（`compose_heartbeat` 的五段部分；舊呼叫端與測試用）。"""
    return compose_heartbeat(**kwargs).sections


def summary_line(*, now: datetime, snapshot: Mapping[str, Any], run_record_path: Path | None, leads_path: Path,
                 theme_nudge: bool, theme_line: str) -> str:
    """Discord 摘要行（`publish --summary`）：`Daily <日期>｜球在你 N` ＋ 紅旗。紅旗全部來自已讀到的狀態，不另判讀。"""
    today = now.astimezone().date().isoformat()
    actionable = snapshot.get("pq2.actionable")
    head = f"Daily {today}｜球在你 {'未讀到' if actionable is None else actionable}"
    flags: list[str] = []
    try:
        log = list((_read_json(leads_path) or {}).get("harvest_log") or [])
        newest = max((str(r.get("run_at") or "") for r in log), default="")
        age = harvest_age_hours(newest, now=now)
        limit = _harvest_stale_hours()
        if age is None or (limit is not None and age > limit):
            flags.append("harvest 沒跑")
    except Exception:  # noqa: BLE001
        flags.append("harvest 狀態讀不到")
    record, _problem = _load_run_record(run_record_path, now=now)
    if record is None:
        flags.append("今天沒有 daily 執行紀錄")
    else:
        steps = [r for r in record.get("steps") or [] if isinstance(r, Mapping)]
        bad = [r for r in steps if r.get("status") not in ("ok", "skipped", "running", None)]
        if bad:
            flags.append(f"daily 失敗 {len(bad)} 步")
        llm = [r for r in steps if r.get("kind") == "llm"]
        if record.get("capability_violation"):
            flags.append("LLM 能力檢查不符")
        elif any(r.get("status") not in ("ok", "skipped") for r in llm):
            flags.append("LLM 步驟失敗")
        elif llm and all(r.get("status") == "skipped" and "executor=none" in str(r.get("reason") or "") for r in llm):
            flags.append("LLM 關閉（executor=none）")
        if (record.get("schedule_check") or {}).get("status") == "mismatch":
            flags.append("排程不一致")
    touched = snapshot.get("disproof.touched_pending")
    if touched:
        flags.append(f"反證觸及待處置 {touched}")
    red = snapshot.get("health.red")
    if red:
        flags.append(f"健康紅燈 {red}")
    if theme_nudge:
        flags.append(theme_line.replace("**", "").split("（", 1)[0])
    try:
        from briefing.sources import load_backup_status

        problems = _backup_problems(load_backup_status(now=now))
        if problems:
            flags.append("備份：" + "、".join(problems))
    except Exception:  # noqa: BLE001
        flags.append("備份狀態讀不到")
    try:
        from engine_b import event_watch as ew

        t2 = ew.t2_status(ew.load_watches(), today=now.astimezone().date())
        if t2["stale"]:
            flags.append("T2 輪詢從沒跑過" if t2["last_run_days"] is None
                         else f"T2 輪詢 {t2['last_run_days']} 天沒跑")
    except Exception:  # noqa: BLE001
        flags.append("T2 輪詢狀態讀不到")
    return head + "".join(f"｜⚠ {flag}" for flag in flags)


def render_markdown(sections: Sequence[Section], *, now: datetime | None = None,
                    banner: Sequence[str] = ()) -> str:
    moment = now or datetime.now(timezone.utc)
    head = [
        f"# Daily 心跳 — {moment.astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        *(f"> ⚠ {line}" for line in banner),
        *([""] if banner else []),
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
    parser.add_argument("--out", type=Path, default=None,
                        help="把結果以 UTF-8 寫到這個檔（交給既有 publisher 的 --brief-file）")
    parser.add_argument("--summary-out", type=Path, default=None,
                        help="把 Discord 摘要行寫到這個檔（daily ⑲ 帶進 publish --summary）")
    parser.add_argument("--write-snapshot", action="store_true",
                        help="寫今天的快照（daily ⑱ 才帶；互動手跑不帶，免得蓋掉 daily 的那一份）")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    beat = compose_heartbeat(now=now)
    sections = beat.sections
    if args.format == "json":
        text = json.dumps(
            {"generated_at": now.isoformat(), "banner": beat.banner, "summary": beat.summary,
             "snapshot": beat.snapshot, "sections": [s.as_dict() for s in sections]},
            ensure_ascii=False, indent=2,
        ) + "\n"
    else:
        text = render_markdown(sections, now=now, banner=beat.banner)
    if args.summary_out is not None:
        args.summary_out.write_text(beat.summary + "\n", encoding="utf-8")
    if args.write_snapshot:
        try:
            write_snapshot(SNAPSHOT_DIR, today=now.astimezone().date(), now=now, values=beat.snapshot)
        except OSError as exc:
            print(f"⚠ 快照寫不進去（明天的較昨變動會說沒有上一份）：{exc}", file=sys.stderr)

    if args.out is not None:
        args.out.write_text(text, encoding="utf-8")
        print(f"心跳已寫入 {args.out}（{len(text.encode('utf-8'))} bytes）", file=sys.stderr)
    else:
        sys.stdout.write(text)
    # **永遠 0**：心跳的失敗模式是「印出降級行」，不是「不發」。
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
