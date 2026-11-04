"""routine_hint.py — SessionStart hook：今天的 daily 沒跑完就在開 session 時第一句說出來。

daily（`crons/daily_task.py`）是唯一的心跳來源——**它自己當掉就一則都沒有**，而「沒收到心跳」
在 Discord 上是沉默，不會自己出現（L13-2：沒發生與沒看到同形）。所以開 session 時補一道：

- 本地時間已過 `daily_local_time`＋`expected_duration_minutes`，今天卻沒有 `daily_run_<日期>.json`；或
- 紀錄裡有 `integrity_violation`（保險檢查觸發、已中止，心跳與發送都沒跑）、或紀錄停在 `running`。

**紀錄資料夾本身不存在＝讀不到，不是「沒跑」**（2026-11-04；L11-5「我找不到」與「它不存在」是兩個 claim）：雲端 session 的容器
沒有 `library/private/heartbeat`，原本每開一次雲端 session 就喊一次「daily 沒跑」——11-01、11-02、11-04 都被轉述成事故，喊久了
真的沒跑那天就沒人信（L14-4 恆亮）。改成 `records_unreadable_note`：Claude 雲端（`CLAUDE_CODE_REMOTE=true`）印一行說明、
不要求轉述；其他情況照樣要求轉述，但寫「讀不到」——本機（跑 daily 的那台）看到它，是紀錄資料夾不見了。

另外**每次開 session 都印一行「距上次掃題材 N 天」**（Phase 1 Step 1.9，定案 B：session 開頭常駐）——weekly 退役後
題材掃描只在互動 session 由使用者發起，沒有排程會提醒它；天數 ≥ `config/daily_routine.json` 的
`theme_scan.nudge_after_days` 時改成要求轉述的版本。

兩邊都掛（`.claude/settings.json` 與 `.codex/hooks.json`，provider-neutral）；無人值守的 `claude -p`
以 `--setting-sources ""`＋`disableAllHooks` 跑，不會觸發。只讀、不連外；任何例外安靜跳過
（hook 絕不能讓 session 開不起來）。只輸出 additionalContext 一個通道（同 `thesis_freshness_check.py`：
兩個通道同時輸出會讓 Codex desktop 顯示一次、agent 又轉述一次）。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CONFIG = ROOT / "config" / "daily_routine.json"
RUN_DIR = ROOT / "library" / "private" / "heartbeat"


def daily_problem(*, now: datetime | None = None, config_path: Path = CONFIG,
                  run_dir: Path = RUN_DIR) -> str | None:
    """回傳要說的原因；沒事回 None。紀錄資料夾不存在＝這台機器判斷不了，也回 None（由 `records_unreadable_note` 說）。"""
    if not run_dir.is_dir():
        return None
    schedule = json.loads(config_path.read_text(encoding="utf-8"))["schedule"]
    tz = ZoneInfo(str(schedule["timezone"]))
    moment = (now or datetime.now(tz)).astimezone(tz)
    hour, minute = (int(p) for p in str(schedule["daily_local_time"]).split(":"))
    due = moment.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(
        minutes=float(schedule["expected_duration_minutes"]))
    record_path = run_dir / f"daily_run_{moment.strftime('%Y-%m-%d')}.json"
    if not record_path.is_file():
        if moment >= due:
            return (f"今天（{moment:%Y-%m-%d}）沒有 daily 執行紀錄，已過預計完成時間 {due:%H:%M}"
                    "——daily 沒跑（電腦沒開？工作被停用？）。查：schtasks /Query /TN "
                    f"{schedule.get('task_name', 'StockBotv2-Daily')} /FO LIST /V")
        return None
    record = json.loads(record_path.read_text(encoding="utf-8"))
    violation = record.get("integrity_violation")
    if violation:
        return (f"保險檢查觸發、daily 已中止（心跳與發送都沒跑）：指紋變了 {violation.get('changed')}"
                "——這是事故，先查是誰改了這些檔")
    if record.get("status") == "running" and moment >= due:
        return (f"daily 執行紀錄停在 running（開始於 {record.get('started_at')}）——"
                "daily 可能被中途殺掉，今天的心跳可能沒發")
    # 心跳或發送沒成功＝Discord 沒收到（R2-a NB-3）：這種失敗在 Discord 上是沉默，只能在這裡說
    steps = {str(s.get("key")): s for s in record.get("steps") or [] if isinstance(s, dict)}
    for key, label in (("18_heartbeat", "心跳"), ("19_publish", "Discord 發送")):
        step = steps.get(key)
        if step is not None and step.get("status") != "ok":
            return f"daily 的{label}沒有成功（{step.get('status')}：{step.get('error') or step.get('reason') or ''}）——今天可能沒收到訊息"
    receipt = (steps.get("19_publish") or {}).get("receipt") or {}
    if receipt and receipt.get("status") not in (None, "sent"):
        return f"daily 的 Discord 發送回 {receipt.get('status')}（{receipt.get('error_code')}）——今天可能沒收到訊息"
    return None


def records_unreadable_note(run_dir: Path = RUN_DIR, *, environ: Mapping[str, str] | None = None) -> str | None:
    """紀錄資料夾不存在時要說的那一句；資料夾在就回 None（照 `daily_problem` 判）。"""
    if run_dir.is_dir():
        return None
    try:
        where = run_dir.relative_to(ROOT).as_posix()
    except ValueError:
        where = str(run_dir)
    env = os.environ if environ is None else environ
    if str(env.get("CLAUDE_CODE_REMOTE") or "").strip().lower() == "true":
        return (f"daily 執行紀錄：雲端 session 讀不到（這台機器沒有 `{where}`）——不代表 daily 沒跑；"
                "要確認看本機收到的短版")
    return (f"【請在第一則回覆開頭轉述】這台機器讀不到 daily 執行紀錄（`{where}` 不存在）——不代表 daily 沒跑；"
            "若這是跑 daily 的那台本機，就是紀錄資料夾不見了，先查 library/private 是否完整")


def theme_scan_hint(*, today=None, config_path: Path = CONFIG, reports_dir: Path | None = None) -> tuple[str, bool]:
    """(那一行, 是否達門檻)。達門檻（或從沒掃過）→ 要求轉述；否則是一行普通的常駐計數。"""
    from engine_b.routine_config import load_theme_scan
    from engine_b.theme_scan import REPORTS_DIR, last_scan

    threshold = load_theme_scan(config_path)["nudge_after_days"]
    scan = last_scan(reports_dir=reports_dir or REPORTS_DIR, today=today)
    if scan["date"] is None:
        return (f"【請在第一則回覆開頭轉述】從來沒掃過題材（門檻 {threshold} 天）——說「掃題材」啟動題材掃描", True)
    days = int(scan["days"])
    if days >= threshold:
        return (f"【請在第一則回覆開頭轉述】已 {days} 天沒掃題材（上次 {scan['date']}，門檻 {threshold} 天）"
                "——說「掃題材」啟動題材掃描", True)
    return (f"距上次掃題材 {days} 天（上次 {scan['date']}，門檻 {threshold} 天）", False)


def main() -> int:
    # 兩件事各自降級：任何一件讀不到就安靜跳過那一件（hook 絕不能讓 session 開不起來）。
    # 只用 additionalContext 一個通道（見模組 docstring）；兩件事合成同一段文字。
    messages: list[str] = []
    try:
        note = records_unreadable_note(RUN_DIR)
        if note:
            messages.append(note)
        else:
            problem = daily_problem(run_dir=RUN_DIR)
            if problem:
                messages.append(f"【請在第一則回覆開頭轉述】今天的 daily 沒有跑完：{problem}")
    except Exception:  # noqa: BLE001
        pass
    try:
        messages.append(theme_scan_hint()[0])
    except Exception:  # noqa: BLE001
        pass
    if not messages:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(messages),
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # noqa: BLE001
        sys.exit(0)
