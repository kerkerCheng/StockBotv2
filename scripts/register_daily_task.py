"""把 `config/daily_routine.json` 的 `schedule` 註冊成 Windows 工作——**改排程時間的唯一做法**。

Phase 1 Step 1.2a（A1）。事發 2026-09-12：時間有兩個 SSOT（config 與 OS 排程器）且沒有機械連結，
只改了排程器而 config 沒跟上，避讓窗兩個方向都錯。現在時間只住 config：本腳本由它導出工作的 XML，
`crons/daily_task.py` 每次開跑再拿實際註冊值與 config 比對（不一致時心跳段 1 亮 ⚠ 並印本命令）。

範本照舊心跳工作（Step 1.0 存於 `library/private/heartbeat/legacy_tasks/`）：`InteractiveToken`
（只在使用者已登入時執行——換成「不論是否登入」要存密碼，刻意不做）、`StartWhenAvailable`
（05:30 電腦沒開時開機後補跑）、`IgnoreNew`；入口一律 Python（`.cmd` 會被 cp950 讀壞）。
時限來自 config（舊心跳的 PT10M 一定不夠）。

用法：
    python scripts/register_daily_task.py                  # dry-run：印 XML 與和現行註冊值的差異
    python scripts/register_daily_task.py --apply          # 註冊 StockBotv2-Daily，並「停用」（不刪）舊兩個工作
    python scripts/register_daily_task.py --retire-legacy  # 新工作至少一次排程觸發成功後，刪舊兩個工作（Step 1.2b）
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from crons.daily_task import parse_task_xml  # noqa: E402
from engine_b.routine_config import load_schedule  # noqa: E402

#: 由 `StockBotv2-Daily` 取代的兩個舊工作。1.2a 只停用（回滾＝重新啟用），1.2b 才刪。
LEGACY_TASKS: tuple[str, ...] = ("StockBotv2-Heartbeat", "StockBotv2-FxSync")
ENTRYPOINT = r"crons\daily_task.py"

_TEMPLATE = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>StockBotv2 daily (Phase 1): the only unattended routine. Runs crons\\daily_task.py (fixed step list, zero-LLM heartbeat, Discord). Time and limit come from config/daily_routine.json; change them there and re-run scripts/register_daily_task.py --apply.</Description>
    <URI>\\{task_name}</URI>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT{limit}M</ExecutionTimeLimit>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <IdleSettings>
      <Duration>PT10M</Duration>
      <WaitTimeout>PT1H</WaitTimeout>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
  </Settings>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{start_boundary}</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>{python}</Command>
      <Arguments>{arguments}</Arguments>
      <WorkingDirectory>{repo}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def next_start_boundary(schedule: dict, *, now: datetime | None = None) -> str:
    """下一次觸發的時刻。⚠ 刻意不用「今天」：已過時間卻把起點設在今天，
    `StartWhenAvailable` 可能把它當成錯過的一次、註冊當下就補跑。"""
    tz = ZoneInfo(str(schedule["timezone"]))
    moment = (now or datetime.now(tz)).astimezone(tz)
    hour, minute = (int(p) for p in str(schedule["daily_local_time"]).split(":"))
    fire = moment.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if fire <= moment:
        fire += timedelta(days=1)
    return fire.isoformat(timespec="seconds")


def current_user() -> str:
    domain = os.environ.get("USERDOMAIN") or ""
    name = os.environ.get("USERNAME") or ""
    return f"{domain}\\{name}" if domain else name


def build_task_xml(schedule: dict, *, repo: Path = ROOT, user: str | None = None,
                   now: datetime | None = None) -> str:
    return _TEMPLATE.format(
        task_name=escape(str(schedule["task_name"])),
        user=escape(user or current_user()),
        limit=int(schedule["execution_time_limit_minutes"]),
        start_boundary=next_start_boundary(schedule, now=now),
        python=escape(str(repo / ".venv" / "Scripts" / "python.exe")),
        arguments=escape(ENTRYPOINT),
        repo=escape(str(repo)),
    )


def expected_fields(schedule: dict, *, repo: Path = ROOT) -> dict:
    return {
        "time": str(schedule["daily_local_time"]),
        "execution_time_limit_minutes": int(schedule["execution_time_limit_minutes"]),
        "command": str(repo / ".venv" / "Scripts" / "python.exe"),
        "arguments": ENTRYPOINT,
    }


def diff_fields(expected: dict, actual: dict | None) -> list[str]:
    if actual is None:
        return ["（尚未註冊）"]
    out = [f"{k}: {actual.get(k)!r} → {v!r}" for k, v in expected.items() if actual.get(k) != v]
    if actual.get("enabled") is False:
        out.append("enabled: False → True")
    return out


def _schtasks(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["schtasks", *args], capture_output=True, text=True,
                          encoding="mbcs", errors="replace", shell=False)


def query_actual(task_name: str) -> dict | None:
    from crons.daily_task import _query_task_xml

    text = _query_task_xml(task_name)
    return parse_task_xml(text) if text else None


def last_result_ok(task_name: str) -> tuple[bool, str]:
    """1.2b 的前提：新工作至少一次**排程觸發**成功（`Last Result: 0` 且確實跑過）。"""
    completed = _schtasks("/Query", "/TN", task_name, "/V", "/FO", "LIST")
    if completed.returncode != 0:
        return False, f"查不到 {task_name}"
    text = completed.stdout or ""
    last_result = re.search(r"Last Result:\s*(-?\d+)", text)
    last_run = re.search(r"Last Run Time:\s*(.+)", text)
    if not last_result or not last_run:
        return False, "schtasks 輸出裡找不到 Last Result／Last Run Time"
    if "1999" in last_run.group(1) or "N/A" in last_run.group(1):
        return False, f"{task_name} 還沒跑過（Last Run Time: {last_run.group(1).strip()}）"
    if last_result.group(1) != "0":
        return False, f"{task_name} 上次結果不是 0（{last_result.group(1)}）"
    return True, f"Last Run Time: {last_run.group(1).strip()}｜Last Result: 0"


def apply(schedule: dict) -> int:
    xml = build_task_xml(schedule)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "task.xml"
        path.write_text(xml, encoding="utf-16")
        completed = _schtasks("/Create", "/TN", str(schedule["task_name"]), "/XML", str(path), "/F")
    print((completed.stdout or completed.stderr or "").strip())
    if completed.returncode != 0:
        print(f"註冊失敗（exit {completed.returncode}）；舊工作不動", file=sys.stderr)
        return 1
    actual = query_actual(str(schedule["task_name"]))
    remaining = diff_fields(expected_fields(schedule), actual)
    if remaining:
        print("⚠ 註冊後讀回的值與 config 不一致：" + "；".join(remaining), file=sys.stderr)
        return 1
    print(f"✓ {schedule['task_name']} 與 config 一致：{expected_fields(schedule)}")
    for legacy in LEGACY_TASKS:
        result = _schtasks("/Change", "/TN", legacy, "/DISABLE")
        print(f"{legacy}：" + ("已停用" if result.returncode == 0 else
                              f"停用失敗或不存在（{(result.stderr or result.stdout).strip()}）"))
    return 0


def retire_legacy(schedule: dict) -> int:
    ok, why = last_result_ok(str(schedule["task_name"]))
    if not ok:
        print(f"不刪舊工作：{why}", file=sys.stderr)
        return 1
    print(why)
    for legacy in LEGACY_TASKS:
        result = _schtasks("/Delete", "/TN", legacy, "/F")
        print(f"{legacy}：" + ("已刪除" if result.returncode == 0 else
                              f"刪除失敗或不存在（{(result.stderr or result.stdout).strip()}）"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="註冊新工作並停用舊兩個")
    mode.add_argument("--retire-legacy", action="store_true", help="刪舊兩個工作（Step 1.2b）")
    args = parser.parse_args(argv)
    schedule = load_schedule()
    if args.apply:
        return apply(schedule)
    if args.retire_legacy:
        return retire_legacy(schedule)
    print(build_task_xml(schedule))
    actual = query_actual(str(schedule["task_name"]))
    diffs = diff_fields(expected_fields(schedule), actual)
    print("與現行註冊值的差異：" + ("無" if not diffs else "；".join(diffs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
