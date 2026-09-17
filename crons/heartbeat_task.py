"""crons/heartbeat_task.py — Windows 工作排程的心跳進入點（2026-09-17 Phase 2 Step 2.2）。

## 為什麼是獨立排程，不是掛在 Codex daily 底下

D12 的硬規則是「**LLM 失敗心跳照發**」。掛在 Codex 底下的話，Codex 沒起來就沒有心跳——
而「Codex 沒起來」正是這個心跳要讓它看得見的失敗之一。獨立排程讓那條規則在**結構上**成立，
不是靠運氣。

## 為什麼不是 `.cmd`

第一版寫成批次檔，實跑直接解析失敗：`cmd.exe` 以 OEM codepage（本機 cp950）讀檔，
而檔案是 UTF-8，中文註解被拆成無效指令。Python 原生處理 UTF-8，且 repo 其他排程入口本來就是
Python——**不要為了「排程器習慣跑 .cmd」而讓一個檔案用一種讀不懂自己的編碼**。

## 它只做兩件事，兩件都是既有命令

1. `crons/heartbeat.py` 組出心跳並寫成 UTF-8 檔（零 LLM、零網路、不寫任何 authority）。
2. `scripts/publish_daily_brief.py --brief-file <同一個檔>`——**既有的** outbound publisher。

⚠ 刻意用檔案而不是管線：Windows PowerShell 5.1 的 `$OutputEncoding` 預設 ASCII，
中文會在 Python 讀到之前就被換掉（`docs/OPERATIONS.md` 既有坑）。

⚠ 刻意用 subprocess 呼叫 publisher 而不是 import：**outbound surface 只有一個入口**，
就是那支已經被 sandbox rule 與 OPERATIONS 記載的腳本。多一條 import 路徑等於多一個沒被記載的出口。

## 永遠 exit 0

心跳的下游是人眼，它一旦不發人就什麼都看不到；通知失敗依 `AGENTS.md` 是 best-effort，
**不得阻斷**（通知不是 authority）。失敗留在 `library/private/heartbeat/heartbeat_task.log`，
而且下一次心跳的段 1 會把「APP 不是今天的」這類狀態自己印出來。

註冊與查證命令見 `docs/OPERATIONS.md`「心跳」節。
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: 心跳產出與 log 都住 ignored private runtime——它不是 authority，不進 Git。
OUT_DIR = ROOT / "library" / "private" / "heartbeat"
LOG_PATH = OUT_DIR / "heartbeat_task.log"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PUBLISHER = ROOT / "scripts" / "publish_daily_brief.py"


def _log(message: str) -> None:
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    line = f"[{stamp}] {message}\n"
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass  # log 寫不進去也不得阻斷心跳本身
    sys.stderr.write(line)


def _run(argv: list[str], what: str) -> int:
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        _log(f"{what} 起不來：{type(exc).__name__}: {exc}")
        return 1
    for stream, label in ((completed.stdout, "out"), (completed.stderr, "err")):
        for raw in (stream or "").splitlines():
            if raw.strip():
                _log(f"  {what}.{label}: {raw}")
    _log(f"{what} exit={completed.returncode}")
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    weekly = "--weekly" in args
    dry_run = "--dry-run" in args  # 只產檔、不發送（註冊排程前的空跑檢查用）

    _log(f"心跳開始（weekly={weekly}, dry_run={dry_run}）")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    target = OUT_DIR / f"heartbeat_{today}.md"

    python = str(PYTHON) if PYTHON.is_file() else sys.executable
    build = [python, str(ROOT / "crons" / "heartbeat.py"), "--out", str(target)]
    if weekly:
        build.append("--weekly")
    _run(build, "heartbeat")

    if not target.is_file():
        # ⚠ 這一行是「沒發生」與「沒看到」的分界：沒有產出就明說沒有東西可發，
        # 不得靜默結束（L13-2）。
        _log(f"沒有產出 {target.name}——沒有東西可發")
        return 0

    if dry_run:
        _log(f"dry-run：已產出 {target.name}（{target.stat().st_size} bytes），不發送")
        return 0

    _run([python, str(PUBLISHER), "--brief-file", str(target),
          "--summary", "每日心跳" if not weekly else "每週心跳"], "publish")
    _log("心跳結束")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
