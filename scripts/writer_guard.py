"""互動 session 對本機排程的單向避讓檢查。

`AGENTS.md`：「同一 working tree 只讓一個 agent 寫入……排程與互動 session 也算兩個
writer，不能重疊。」但在 2026-08-31 之前，這條規則的執行力**只有「人要記得」**——
06:30 這個時間只存在於散文與 OS 排程器設定，程式看不到，於是程式也不可能自己避開。
repo 內 `filelock`／`flock`／pidfile 全部 0 命中，沒有任何互斥機制。

兩側寫的是同一組檔：`library/leads/pending_leads.json`、`todo_pool.json`、
`event_watches.json`，外加 git commit／push。重疊時最危險的不是報錯，是**靜默的
lost update**——daily 剛 harvest 進來的 lead 被互動 session 用舊記憶體狀態覆蓋掉，
沒有任何東西會叫。

⚠ **這是單向避讓，不是互斥鎖。** 只有互動側會呼叫本檢查；daily 那側要加同樣的檢查
必須動它的 sandbox allowlist（見 ROADMAP）。單向仍然有效，因為 daily 有界且時間可預測——
互動 session 讓開就不會撞。

用法：
    python scripts/writer_guard.py check      # 現在可否開始長時間寫入（exit 2＝不可）
    python scripts/writer_guard.py verify --since <HEAD-sha>   # 期間有沒有別的 writer 動過
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "daily_routine.json"

# 兩側都會寫的 authority 檔。verify 只看 git 是否動過它們——
# 逐檔 hash 對 CLI 這種短命行程沒有意義，真正的危險窗口是整段 run。
SHARED_PATHS = (
    "library/leads/pending_leads.json",
    "library/leads/todo_pool.json",
    "library/leads/event_watches.json",
)


def _load_schedule() -> dict:
    raw = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    schedule = raw.get("schedule")
    if not isinstance(schedule, dict):
        # fail closed：讀不到時間窗就當成不安全，不猜一個預設值。
        raise SystemExit("config/daily_routine.json 缺 schedule 區塊；無法判斷排程時間窗")
    return schedule


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    return (result.stdout or "").strip()


def _window(schedule: dict, now: datetime) -> tuple[datetime, datetime]:
    """回傳今日 daily 的避讓窗 [start, end)。"""
    hour, minute = (int(part) for part in str(schedule["daily_local_time"]).split(":"))
    margin = timedelta(minutes=float(schedule["guard_margin_minutes"]))
    duration = timedelta(minutes=float(schedule["expected_duration_minutes"]))
    fire = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return fire - margin, fire + duration + margin


def cmd_check(args: argparse.Namespace) -> int:
    schedule = _load_schedule()
    tz = ZoneInfo(str(schedule["timezone"]))
    now = datetime.now(tz)
    start, end = _window(schedule, now)

    reasons: list[str] = []
    if start <= now < end:
        reasons.append(
            f"現在（{now:%H:%M} {schedule['timezone']}）落在 daily 避讓窗 "
            f"{start:%H:%M}–{end:%H:%M} 內"
        )

    # 長時間 run 會不會跨進窗內——這是本檢查最有價值的一項：
    # 起跑時安全不代表跑到一半安全，而跑到一半才撞上最難收拾。
    horizon = timedelta(minutes=float(args.minutes))
    finish = now + horizon
    next_start = start if now < start else start + timedelta(days=1)
    if finish >= next_start:
        reasons.append(
            f"預計 {args.minutes} 分鐘的 run 會跨進 {next_start:%m-%d %H:%M} 開始的避讓窗"
        )

    dirty = _git("status", "--porcelain")
    if dirty:
        reasons.append(
            "working tree 不乾淨——另一個 writer 可能正在進行中，或上一輪沒收乾淨"
        )

    payload = {
        "safe": not reasons,
        "now_local": now.isoformat(),
        "timezone": str(schedule["timezone"]),
        "daily_window": [start.isoformat(), end.isoformat()],
        "planned_minutes": args.minutes,
        "head": _git("rev-parse", "HEAD"),
        "reasons": reasons,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["safe"] else 2


def cmd_verify(args: argparse.Namespace) -> int:
    """期間有沒有**別人**動過共用 authority 檔。"""
    head = _git("rev-parse", "HEAD")
    moved = head != args.since
    foreign: list[str] = []
    if moved:
        log = _git(
            "log", "--format=%H%x1f%s", f"{args.since}..{head}", "--", *SHARED_PATHS
        )
        for line in filter(None, log.splitlines()):
            sha, _, subject = line.partition("\x1f")
            # 排程的 state publisher 用固定 subject；互動 session 的 commit 由呼叫端自己認得。
            if subject.startswith("chore(daily)"):
                foreign.append(f"{sha[:7]} {subject}")

    payload = {
        "clean": not foreign,
        "since": args.since,
        "head": head,
        "head_moved": moved,
        "foreign_commits": foreign,
        "hint": (
            "偵測到排程的 state publisher 在期間提交過共用檔——"
            "重新讀 todo_pool.json／pending_leads.json 再繼續，不要沿用記憶中的狀態"
            if foreign
            else "期間沒有排程側的共用檔提交"
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["clean"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="現在可否開始長時間寫入")
    check.add_argument(
        "--minutes",
        type=float,
        default=120,
        help="預計這段 run 會跑多久（分鐘）；用來判斷會不會跨進避讓窗",
    )
    check.set_defaults(func=cmd_check)

    verify = sub.add_parser("verify", help="期間有沒有別的 writer 動過共用檔")
    verify.add_argument("--since", required=True, help="開跑時的 HEAD sha")
    verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
