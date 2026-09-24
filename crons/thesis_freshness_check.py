"""
thesis_freshness_check.py — SessionStart hook: 提醒哪些 thesis 已超過自己的核查週期。

核查週期跟著各 thesis 的 `check_interval_days`（L7：disproof 條件必附核查頻率），
不是一個全域天數——Sivers 是 30 天（disproof 是現金 runway，快變數），AXT 是 90 天
（disproof 是產能擴張／出口許可，慢變數）。`STALE_DAYS` 只是「沒有 lifecycle entry
的 memo」的預設值。

只讀本機 thesis/*_lane_memo.md，不碰 Neo4j / Engine C（見 U8 修訂設計，
docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md）。
完整核查（讀 disproof_condition → WebSearch → engine_c/checklist.py）由使用者
在對話中觸發，本 script 只負責「該不該現在問」。

日期來源優先序：
1. 檔案內 "**生成日期：** YYYY-MM-DD" 一行（新格式 Lane Memo 都有）
2. 沒有的話退回檔案 mtime（舊格式 Lane Memo，如 v1 檔案）

同一家公司多個版本（*_v1_*, *_v2_*）只取最新日期，不重複提醒。
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thesis.lifecycle_schedule import is_due  # noqa: E402

THESIS_DIR = ROOT / "thesis"
LIFECYCLE = ROOT / "thesis" / "lifecycle.json"
TODO_POOL = ROOT / "library" / "leads" / "todo_pool.json"
# 只作為「沒有 lifecycle entry 的 memo」的預設；有 entry 的一律跟 check_interval_days。
STALE_DAYS = 90

DATE_RE = re.compile(r"生成日期[:：]\s*(\d{4}-\d{2}-\d{2})")
COMPANY_RE = re.compile(r"^(?P<company>.+?)_v\d+_lane_memo$")


def _file_date(path: Path) -> date:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = DATE_RE.search(text)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def _check_intervals() -> dict[str, int]:
    """每條 thesis 自己宣告的核查週期；memo 檔的門檻應該跟著它走。

    核查頻率屬於 thesis 的一部分（L7 要求 disproof 條件必附核查頻率）：Sivers 是
    30 天因為它的 disproof 是現金 runway 這種快變數，AXT 是 90 天因為它的 disproof
    是產能擴張／出口許可這類慢變數。用一個全域常數去蓋掉這個差異，等於把「什麼時候
    該重看」從 thesis 的性質改成日曆的性質。

    ``STALE_DAYS`` 只留給**沒有 lifecycle entry 的 memo**當預設值。
    """

    try:
        data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    intervals: dict[str, int] = {}
    for tid, entry in (data.items() if isinstance(data, dict) else []):
        if not isinstance(entry, dict):
            continue
        raw = entry.get("check_interval_days")
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            continue
        if raw > 0:
            intervals[str(tid)] = int(raw)
    return intervals


def check() -> list[tuple[str, int]]:
    """回傳 [(company, days_since), ...]，只含超過該 thesis 自己核查週期的公司。"""
    latest_by_company: dict[str, date] = {}

    for path in sorted(THESIS_DIR.glob("*_lane_memo.md")):
        m = COMPANY_RE.match(path.stem)
        company = m.group("company") if m else path.stem
        d = _file_date(path)
        if company not in latest_by_company or d > latest_by_company[company]:
            latest_by_company[company] = d

    intervals = _check_intervals()
    today = date.today()
    stale = []
    for company, d in latest_by_company.items():
        days = (today - d).days
        if days > intervals.get(company, STALE_DAYS):
            stale.append((company, days))

    return sorted(stale, key=lambda x: -x[1])



class LifecycleUnreadable(RuntimeError):
    """lifecycle.json 讀不到——「讀不到」不得被當成「沒有到期」（R2-b 重審 RB-1 的同型）。"""


def _read_lifecycle(*, strict: bool) -> dict | None:
    try:
        data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        if strict:
            raise LifecycleUnreadable(f"{LIFECYCLE}：{type(exc).__name__}: {exc}") from exc
        return None
    if not isinstance(data, dict):
        if strict:
            raise LifecycleUnreadable(f"{LIFECYCLE} 不是 object")
        return None
    return data


def expired_disproof_by_thesis(data: dict | None = None, *, lifecycle: dict | None = None) -> dict[str, list[dict]]:
    """thesis 來源、到期未處置的語意條件，依 thesis id 分組（Phase 1 Step 1.7 設計 B：重問併進 thesis 複查）。"""
    lifecycle = _read_lifecycle(strict=False) if lifecycle is None else lifecycle
    if lifecycle is None:
        return {}
    if data is None:
        from engine_b.event_watch import load_watches

        data = load_watches()
    by_memo = {str(e.get("memo")): str(tid) for tid, e in lifecycle.items()
               if isinstance(e, dict) and e.get("memo") and e.get("status") != "retired"}
    out: dict[str, list[dict]] = {}
    for watch in (data or {}).get("watches") or []:
        ref = str(watch.get("source_ref") or "")
        if (watch.get("kind") != "semantic_condition" or not ref.startswith("thesis:")
                or watch.get("status") != "expired" or watch.get("expiry_resolution")):
            continue
        tid = by_memo.get(ref[len("thesis:"):].split("#", 1)[0])
        if tid:
            out.setdefault(tid, []).append(watch)
    return out


def upcoming_disproof_by_thesis(data: dict | None = None, *, lifecycle: dict, today: date) -> dict[str, list[dict]]:
    """thesis 來源、還在等（active／fired）且到期日落在「今天＋一個核查週期」之內的條件，依 thesis id 分組（NB3-3）。"""
    from datetime import timedelta

    if data is None:
        from engine_b.event_watch import load_watches

        data = load_watches()
    horizon: dict[str, tuple[str, str]] = {}
    for tid, e in lifecycle.items():
        if isinstance(e, dict) and e.get("memo") and e.get("status") != "retired":
            interval = e.get("check_interval_days")
            days = int(interval) if isinstance(interval, (int, float)) and not isinstance(interval, bool) and interval > 0 else 90
            horizon[str(e["memo"])] = (str(tid), (today + timedelta(days=days)).isoformat())
    out: dict[str, list[dict]] = {}
    for watch in (data or {}).get("watches") or []:
        ref = str(watch.get("source_ref") or "")
        if watch.get("kind") != "semantic_condition" or not ref.startswith("thesis:") \
                or watch.get("status") not in ("active", "fired"):
            continue
        hit = horizon.get(ref[len("thesis:"):].split("#", 1)[0])
        if hit and str(watch.get("expires")) <= hit[1]:
            out.setdefault(hit[0], []).append(watch)
    return out


def touched_disproof_by_thesis(data: dict | None = None) -> dict[str, list[dict]]:
    """判定觸及、還沒處置的 thesis 來源語意 watch，依 thesis id 分組（C3／A5；Phase 1 Step 1.5）。

    watch 的 `source_ref` 是 `thesis:<memo 路徑>#<n>`；memo 路徑對回 lifecycle 的現行 `memo` 得到 thesis id。
    「還沒處置」＝`judgment.handled` 為空——**不比 `last_checked` 日期**（`judgment.at` 是 UTC 日期時間、
    `last_checked` 是日期：照字串比同日複查後永遠清不掉；照日期比同日稍早已複查過的話這次觸及會靜默消失）。
    """
    try:
        lifecycle = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
        if data is None:
            from engine_b.event_watch import load_watches

            data = load_watches()
    except (OSError, ValueError):
        return {}
    by_memo = {str(e.get("memo")): str(tid) for tid, e in (lifecycle.items() if isinstance(lifecycle, dict) else [])
               if isinstance(e, dict) and e.get("memo")}
    out: dict[str, list[dict]] = {}
    for watch in (data or {}).get("watches") or []:
        judgment = watch.get("judgment") or {}
        ref = str(watch.get("source_ref") or "")
        if watch.get("kind") != "semantic_condition" or not ref.startswith("thesis:"):
            continue
        if judgment.get("touches") != "yes" or judgment.get("handled"):
            continue
        tid = by_memo.get(ref[len("thesis:"):].split("#", 1)[0])
        if tid:
            out.setdefault(tid, []).append(watch)
    return out


def lifecycle_due_detail(*, watch_data: dict | None = None, strict: bool = False) -> list[tuple[str, str, list[str]]]:
    """[(thesis_id, 原因, 涵蓋的反證 watch_id)]——排程到期、「反證被判觸及」、「反證等滿一輪都沒發生」**合併成同一筆**
    （同一 thesis 只會有一筆）。涵蓋的 watch_id 在那一筆 go／drop 時由 `engine_b.disproof.after_thesis_review` 處理
    （觸及→handled＋續盯；到期→續到下一個核查點）。

    `strict=True`（pq2 收集器用）：lifecycle 讀不到就 raise，讓這個來源本輪不算健康——否則「讀不到」會被當成
    「沒有到期」，已開的複查項目被標成可結案（R2-b 重審 RB-1 的同型）。"""
    data = _read_lifecycle(strict=strict)
    if data is None:
        return []
    today = date.today()
    reasons: dict[str, list[str]] = {}
    watch_ids: dict[str, list[str]] = {}
    for tid, entry in (data.items() if isinstance(data, dict) else []):
        if not isinstance(entry, dict):
            continue
        due_now, reason = is_due(entry, today=today)
        if due_now:
            reasons.setdefault(str(tid), []).append(reason)
    from engine_b.event_watch import condition_label

    for tid, watches in touched_disproof_by_thesis(watch_data).items():
        for watch in watches:
            reasons.setdefault(tid, []).append(
                f"反證被判觸及：{condition_label(watch.get('condition'))}｜48 小時動作：{watch.get('action_48h')}")
            watch_ids.setdefault(tid, []).append(str(watch["watch_id"]))
    # 排程到期的那一筆一併帶上「一個核查週期內會到期」的反證（NB3-3）：準時複查時條件就在同一次續盯，
    # 不會在隔天各自到期、另開一筆。
    for tid, watches in upcoming_disproof_by_thesis(watch_data, lifecycle=data, today=today).items():
        if tid not in reasons:
            continue
        reasons[tid].append(f"（複查時一併續盯 {len(watches)} 條反證）")
        watch_ids.setdefault(tid, []).extend(str(w["watch_id"]) for w in watches)
    for tid, watches in expired_disproof_by_thesis(watch_data, lifecycle=data).items():
        labels = "、".join(condition_label(w.get("condition"), 24) for w in watches[:3])
        more = f" 等 {len(watches)} 條" if len(watches) > 3 else ""
        reasons.setdefault(tid, []).append(
            f"反證等滿一輪都沒發生 {len(watches)} 條（{labels}{more}）——複查時一併決定："
            "memo 不改＝這一筆 go／drop 後自動續盯到下一個核查點；要放棄就改寫 memo")
        watch_ids.setdefault(tid, []).extend(str(w["watch_id"]) for w in watches)
    return [(tid, "；".join(why), sorted(watch_ids.get(tid, []))) for tid, why in reasons.items()]


def lifecycle_due() -> list[tuple[str, str]]:
    """讀 lifecycle.json，回 [(thesis_id, 原因)]——到期、review_required，或反證被判觸及未處置（包 `lifecycle_due_detail`）。
    這是 lifecycle 的權威到期訊號（memo 檔日期只是次要 fallback）。

    到期判準委派給 `thesis.lifecycle_schedule`：固定週期與催化劑取較早者。先前這裡
    只讀 `next_check`，而 `next_check` 是 `last_checked + check_interval_days` 機械算出
    的日曆——thesis 明明寫了裁決點（AXT 是 Q3 財報與 10-Q exhibit），排程卻讀不到。

    lifecycle 的正式狀態更新（disproof 評估、retired/revised）需人工判斷，本 hook
    只 surface 到期供你本機手動複查（plan R17）；不寫入。
    """
    return [(tid, why) for tid, why, _ids in lifecycle_due_detail()]


def active_lifecycle_todo_refs() -> set[str]:
    """Return lifecycle refs already surfaced by the unified approval inbox.

    SessionStart is only a fallback for newly due items. Once an item is in the
    todo pool, Daily Brief owns the user-facing reminder and the hook stays quiet.
    """

    try:
        data = json.loads(TODO_POOL.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return set()
    return {
        str(item.get("ref_id"))
        for item in items
        if isinstance(item, dict)
        and item.get("type") == "thesis_lifecycle"
        and not item.get("resolved_at")
        and item.get("ref_id")
    }


def main() -> int:
    stale = check()
    surfaced = active_lifecycle_todo_refs()
    due = [(tid, why) for tid, why in lifecycle_due() if tid not in surfaced]
    if not stale and not due:
        return 0  # 都新鮮，安靜過去，不輸出任何東西

    segments = []
    if due:
        parts = ", ".join(f"{tid}（{why}）" for tid, why in due)
        segments.append(f"⛔ lifecycle 到期複查：{parts}")
    stale = [(c, d) for c, d in stale if c not in {tid for tid, _ in due}]
    if stale:
        intervals = _check_intervals()
        parts = ", ".join(
            f"{company} {days}天／週期 {intervals.get(company, STALE_DAYS)}天"
            for company, days in stale
        )
        segments.append(f"📋 memo 已超過各自核查週期：{parts}")
    msg = "thesis-monitor: " + "；".join(segments) + " — 要現在複查嗎？"
    # 單一 agent-visible channel：systemMessage 與 additionalContext 同時輸出會
    # 讓 Codex desktop 顯示一次、agent 又轉述一次。只保留 additionalContext，
    # 由 agent 在第一則回覆呈現，跨介面仍一致且不重複。
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "【session 待辦摘要——請在你給使用者的第一則回覆開頭轉述】" + msg
            ),
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
