"""crons/daily_task.py — **唯一的無人值守排程**（Phase 1 Step 1.2a，2026-09-24；A1、C1、C4、C6）。

由 Windows 工作 `StockBotv2-Daily` 每天觸發（時間只住 `config/daily_routine.json` 的 `schedule`，
註冊命令 `scripts/register_daily_task.py` 由它導出）。它取代三個東西：Codex daily automation（抓資料、
機械段、materialize）、`StockBotv2-Heartbeat`（心跳＋發送）、`StockBotv2-FxSync`（FX 同步）。

## 目標（C4）：心跳不靠 LLM；其他步驟可以用 LLM，但 LLM 只產出提議，由程式驗證後寫入

- **步驟清單是程式寫死的封閉清單 `DAILY_STEPS`**——LLM 不決定跑什麼。清單相等由
  `tests/test_daily_task.py` 逐項斷言（守門：不得出現 `webapp serve`、任意欄位寫入者、git 寫入、LLM CLI）。
- LLM 步驟只有 triage 的提議（⑦a）；它與寫入（⑦b，程式驗證後寫）分開，Step 1.3 才接上。
  `llm.executor=none` 時兩者記 `skipped`，這也是 R2-a 的回滾開關。
- 每步獨立 subprocess（`shell=False`、venv python、cwd＝repo root）＋timeout，**失敗記錄後繼續**（fail-soft）。

## 「LLM 失敗心跳照發」怎麼在同一個排程裡成立（`crons/heartbeat_task.py` 的第一條理由，Step 1.2b 刪檔時搬來）

舊心跳刻意是**獨立排程**，不掛在 Codex daily 底下：掛在 LLM 底下的話，LLM 沒起來就沒有心跳——而「LLM 沒起來」
正是心跳要讓人看得見的失敗之一。合併成一個排程之後，這條規則改由**這支程式本身**在結構上保證，不靠 LLM 起得來：
LLM 只是清單裡的步驟（⑦a、⑩b），各有 timeout、失敗只記錄；心跳與發送是 `essential` 步驟，deadline 之後仍會跑。
唯一例外是保險檢查觸發（見下）——那時連心跳都不跑，改由 `crons/routine_hint.py` 在開 session 時說。

## 為什麼永遠 exit 0（從 `crons/heartbeat_task.py` 搬來的理由）

心跳的下游是人眼，它一旦不發人就什麼都看不到；通知失敗依 `AGENTS.md` 是 best-effort，**不得阻斷**
（通知不是 authority）。失敗留在執行紀錄 `library/private/heartbeat/daily_run_<日期>.json`，
心跳段 1 逐條印出；今天沒有紀錄或紀錄說中止時，`crons/routine_hint.py` 在開 session 時說出來。

## 為什麼是 Python 不是 `.cmd`（同上）

`cmd.exe` 以 OEM codepage（本機 cp950）讀檔，而檔案是 UTF-8，中文註解被拆成無效指令——
不要為了「排程器習慣跑 .cmd」而讓一個檔案用一種讀不懂自己的編碼。

## 為什麼發送走 subprocess 不走 import（同上）

**outbound surface 只有一個入口**：`scripts/publish_daily_brief.py`。它的每一條限制（host、logical channel、
content class）由 `notifications/publisher.py` 強制，不靠 prompt。心跳一律以檔案交給它（`--brief-file`）：
Windows PowerShell 5.1 的管線會把中文換掉。

## daily 自己當掉就一則都沒有——所以有三道保證

1. **最外層保證**：進步驟迴圈之前的任何例外（config 解析、自我比對、import）都被接住並寫進紀錄，
   之後照樣組心跳＋發送。
2. **全域 deadline**：`execution_time_limit_minutes` 減去必要步驟（收尾、心跳、發送）的保留時間；
   到了就跳過剩下的非必要步驟，直接收尾組心跳。
3. **`crons/routine_hint.py`**：過了時間今天仍沒有紀錄 → 開 session 時第一句就說。

## 保險檢查（N4；主控制是 LLM 零工具＋每次 init 能力檢查，這一道是保險）

開頭記 `git rev-parse HEAD`＋`git status --porcelain`（不乾淨→照跑，段 1 亮 ⚠）。每個 LLM 步驟的前後
各記一份指紋（先 `.env`、`.git/config`、`.claude/settings.local.json` 的 sha256；`.git/config` 變了就**不再跑
任何 git**，因為 `core.fsmonitor` 等設定會讓 `git status` 執行外部程式；再跑帶 `-c core.fsmonitor=false`
的 git）。任何不同 → 跳過其後**所有**步驟，包括心跳與發送（心跳會 import 被改過的 tracked 檔），
紀錄標 `integrity_violation`。零工具下它理應永不觸發——觸發就是事故。

用法：
    python crons/daily_task.py              # 正常的每日動作（會真的發一則到 Discord）
    python crons/daily_task.py --dry-run    # 印步驟清單與 config 時間，不執行
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: 執行紀錄、心跳產出、批次檔都住 ignored private runtime——不是 authority，不進 Git。
OUT_DIR = ROOT / "library" / "private" / "heartbeat"
LOG_PATH = OUT_DIR / "daily_task.log"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
CONFIG_PATH = ROOT / "config" / "daily_routine.json"
RUN_RECORD_SCHEMA = "daily-run-v1"

#: 保險檢查比對的三個檔（N4；第 2 輪 X1）。`.claude/settings.local.json` 被 `.gitignore` 忽略，
#: 寫進去的 hook 下次開 session 會執行——所以它不能只靠 `git status` 看。
FINGERPRINT_FILES: tuple[str, ...] = (".env", ".git/config", ".claude/settings.local.json")
#: `claude -p` 的內建 `agents-md` plugin 會沿 cwd 往上找的指令檔（R2-a NB-11）——cwd 與上層一律不得有。
INSTRUCTION_FILES: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md")


def _dir_digest(path: Path) -> str | None:
    """目錄下每個檔（名稱＋sha256）的合併 digest；目錄不存在回 None。`.git/hooks` 被 git 忽略、卻會被執行。"""
    if not path.is_dir():
        return None
    digest = hashlib.sha256()
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        try:
            digest.update(hashlib.sha256(child.read_bytes()).digest())
        except OSError as exc:
            digest.update(f"unreadable:{type(exc).__name__}".encode("utf-8"))
    return digest.hexdigest()
GIT_SAFE = ("git", "-c", "core.fsmonitor=false")


@dataclass(frozen=True)
class DailyStep:
    """一步。`argv` 不含 interpreter（執行時補上 venv python）；`{…}` 是執行期代入的樣板。"""

    key: str
    label: str
    argv: tuple[str, ...]
    timeout_minutes: float
    writes: bool
    network: bool
    #: command｜capture（stdout JSON 以 run_id 封套寫進 private 檔）｜llm｜integrity｜apply｜heartbeat｜publish
    kind: str = "command"
    #: deadline 到了也要跑（收尾、心跳、發送）。
    essential: bool = False
    #: capture 的輸出檔名樣板（在 OUT_DIR 下）。
    capture: str | None = None
    #: 前置步驟（它不是 ok 就跳過這一步：LLM 不拿舊批次去跑、套用不套沒成功的提議）。
    requires: str | None = None
    #: LLM 步驟的任務（`triage`｜`prescreen`）——決定 prompt、schema、批次與結果檔、timeout 與分批大小。
    llm_task: str | None = None


#: ⚠ **封閉清單**：順序、argv、timeout、寫入與連網宣告都由 `tests/test_daily_task.py` 逐項斷言。
#: 改這裡＝改無人值守可執行面 → 同一個 change 做 sandbox impact review 五步（`docs/OPERATIONS.md`）。
#: 刻意不列：`catalyst_watch.py`、`engine_b.cli trace-backlog`、`harvest-health`（唯一消費者是退役的
#: LLM brief；心跳自己讀 harvest_log）、`event_watch sweep`（WebSearch 是研究，互動 session 做）。
DAILY_STEPS: tuple[DailyStep, ...] = (
    DailyStep("01_harvest", "harvest（X／EDGAR／MOPS／feeds）",
              ("crons/harvest_leads.py",), 20, True, True),
    DailyStep("02_engine_c_etl", "Engine C 行情與財務 ETL",
              ("engine_c/etl_yfinance.py",), 15, True, True),
    DailyStep("03_fx_sync", "FX 觀測同步（取代 StockBotv2-FxSync）",
              ("scripts/sync_fx_observations.py",), 5, True, True),
    DailyStep("04_beta_snapshot", "beta 技術面與曝險快照",
              ("scripts/daily_beta_snapshot.py", "--format", "markdown", "--risk-view", "changes"),
              10, True, True),
    DailyStep("05_outcome", "追蹤表與問責（outcome）",
              ("scripts/outcome_if_settled_today.py",), 10, True, True),
    # ⑥ 連網：`--by-priority` 以 strict 模式讀 Google Sheet 持股（R2-a NB-5）；Sheet 讀不到時它 exit 2、triage 記 batch_failed。
    DailyStep("06_triage_batch", "triage 批次（上限由 CLI 截斷）",
              ("-m", "engine_b.cli", "list", "--status", "pending", "--by-priority",
               "--triage-batch", "--json"),
              3, False, True, kind="capture", capture="triage_batch_{date}.json"),
    DailyStep("07a_triage_propose", "triage 提議（claude -p 零工具、只回 JSON）",
              (), 15, False, True, kind="llm", requires="06_triage_batch", llm_task="triage"),
    DailyStep("08_integrity_after_triage", "保險檢查（LLM 步驟前後指紋）",
              (), 1, False, False, kind="integrity", essential=True),
    DailyStep("07b_triage_apply", "triage 套用（程式逐則驗證後寫入）",
              ("-m", "engine_b.cli", "triage-apply", "--file", "{triage_result}",
               "--batch", "{triage_batch}", "--run-id", "{run_id}"),
              3, True, False, kind="apply", requires="07a_triage_propose"),
    DailyStep("07c_classification_health", "分類完整性檢查",
              ("-m", "engine_b.cli", "classification-health"), 2, False, False),
    DailyStep("09_consume_fired", "fired 追源 watch 排回 pq1",
              ("-m", "engine_b.cli", "consume-fired"), 3, True, False),
    DailyStep("10_todo_sync", "待辦池同步（含 watch 比對與到期）",
              ("-m", "engine_b.todo", "sync"), 5, True, False),
    # ⑩a–⑩c 語意預篩（Phase 1 Step 1.4；C7）：只標旗、不判定（G7）。⑩a 照抓全文（互動判定也用得到），
    # ⑩b／⑩c 跟著 `llm.executor`。⑩a 只寫 library/private（全文存檔、批次檔），不寫共用 state，所以不取鎖。
    DailyStep("10a_prescreen_prepare", "語意預篩：選醒來的語意 watch、以程式抓全文",
              ("-m", "engine_b.event_watch", "prescreen-prepare", "--run-id", "{run_id}",
               "--out", "{prescreen_batch}"), 10, False, True),
    DailyStep("10b_prescreen_propose", "語意預篩提議（claude -p 零工具、只回標旗 JSON）",
              (), 15, False, True, kind="llm", requires="10a_prescreen_prepare", llm_task="prescreen"),
    DailyStep("10b_integrity_after_prescreen", "保險檢查（LLM 步驟前後指紋）",
              (), 1, False, False, kind="integrity", essential=True),
    DailyStep("10c_prescreen_apply", "語意預篩套用（程式驗引文逐字後只寫 semantic_flag）",
              ("-m", "engine_b.event_watch", "prescreen-apply", "--file", "{prescreen_result}",
               "--batch", "{prescreen_batch}", "--run-id", "{run_id}"),
              3, True, False, kind="apply", requires="10b_prescreen_propose"),
    DailyStep("11_standing_go", "常規授權（封閉清單）",
              ("-m", "engine_b.todo", "standing-go", "--run"), 5, True, False),
    DailyStep("12_fiscal_year_backfill", "XBRL 基期補值（mechanical 欄位）",
              ("scripts/backfill_fiscal_year_results.py", "--write"), 10, True, True),
    DailyStep("13_materialize", "APP materialize",
              ("-m", "webapp", "materialize", "--tracked", "--registry-listed", "--structure-table",
               "--beta", "--coverage", "--watches", "--positions", "--structure-readings", "--scorecard"),
              25, True, True),
    DailyStep("14_health_audit", "健康審查",
              ("query/health_audit.py", "--local", "--json"),
              5, False, False, kind="capture", capture="health_{date}.json"),
    DailyStep("15_invariants", "六條 invariant",
              ("-m", "audit", "invariants", "--json"),
              5, False, False, kind="capture", capture="invariants_{date}.json"),
    DailyStep("16_backup", "本機備份（不含 Drive）",
              ("scripts/backup_private.py", "run", "--no-drive"), 15, True, False),
    DailyStep("17_finalize", "收尾（驗 state、釋放鎖、收工標記）",
              ("scripts/finalize_daily_state.py",), 2, True, False, essential=True),
    # ⑱ 同時寫 Discord 摘要行與今天的快照（Phase 1 Step 1.8）：兩者都在 library/private/heartbeat/，derived、不是 authority。
    DailyStep("18_heartbeat", "組心跳（零 LLM、零網路）",
              ("-m", "crons.heartbeat", "--out", "{brief}", "--summary-out", "{summary_file}", "--write-snapshot"),
              3, False, False, kind="heartbeat", essential=True),
    DailyStep("19_publish", "發送 Discord",
              ("scripts/publish_daily_brief.py", "--brief-file", "{brief}", "--summary", "{summary}"),
              3, False, True, kind="publish", essential=True),
)

#: 必要步驟在 deadline 之後仍要跑，所以要保留這麼多分鐘；另加 2 分鐘給行程本身。
RESERVE_SLACK_MINUTES = 2.0


def essential_reserve_minutes(steps: Sequence[DailyStep] = DAILY_STEPS) -> float:
    return sum(s.timeout_minutes for s in steps if s.essential) + RESERVE_SLACK_MINUTES


def step_timeout_minutes(step: DailyStep, llm: Mapping[str, Any] | None) -> float:
    """LLM 步驟的 timeout 住 config（`llm.<task>_timeout_minutes`）；其餘寫死在清單。"""
    if step.kind == "llm" and llm is not None and step.llm_task:
        return float(llm.get(f"{step.llm_task}_timeout_minutes") or step.timeout_minutes)
    return step.timeout_minutes


def total_timeout_minutes(steps: Sequence[DailyStep] = DAILY_STEPS,
                          llm: Mapping[str, Any] | None = None) -> float:
    return sum(step_timeout_minutes(s, llm) for s in steps)


# ---------------------------------------------------------------------------
# 執行期
# ---------------------------------------------------------------------------

@dataclass
class Completed:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[..., Completed]


def _default_runner(argv: Sequence[str], *, cwd: Path, timeout: float | None,
                    env: Mapping[str, str] | None = None) -> Completed:
    completed = subprocess.run(
        list(argv), cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, shell=False,
        env=dict(env) if env is not None else None,
    )
    return Completed(completed.returncode, completed.stdout or "", completed.stderr or "")


def _tail(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else "…" + text[-limit:]


@dataclass
class DailyRun:
    """一輪 daily 的全部可變狀態；測試以注入 runner／clock／路徑驅動它。"""

    root: Path = ROOT
    out_dir: Path = OUT_DIR
    config_path: Path = CONFIG_PATH
    python: str = ""
    runner: Runner = _default_runner
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    steps: Sequence[DailyStep] = DAILY_STEPS
    lock_path: Path | None = None
    marker_path: Path | None = None
    schtasks_query: Callable[[str], str | None] | None = None
    #: LLM 呼叫（預設 `crons.llm_step.run_claude`）；測試注入假的，不真的叫模型。
    llm_runner: Callable[..., Any] | None = None
    #: 子行程環境的來源（預設 os.environ）；測試用它證明白名單擋得住憑證。
    parent_env: Mapping[str, str] | None = None
    record: dict[str, Any] = field(default_factory=dict)
    schedule: dict[str, Any] | None = None
    llm: dict[str, Any] | None = None
    lock_ok: bool = False
    lock_reason: str | None = None
    fingerprint_before: dict[str, Any] | None = None
    aborted: str | None = None
    deadline: datetime | None = None

    # ---- 路徑與樣板 -----------------------------------------------------
    def __post_init__(self) -> None:
        if not self.python:
            self.python = str(PYTHON) if PYTHON.is_file() else sys.executable
        started = self.clock()
        local = started.astimezone()
        self.date = local.strftime("%Y-%m-%d")
        self.run_id = uuid.uuid4().hex
        self.record = {
            "schema": RUN_RECORD_SCHEMA,
            "run_id": self.run_id,
            "date": self.date,
            "started_at": started.isoformat(),
            "finished_at": None,
            "status": "running",
            "head": None,
            "dirty_paths": [],
            "schedule_check": {"status": "unknown", "reason": "尚未比對"},
            "writer_lock": None,
            "pre_loop_error": None,
            "integrity_violation": None,
            "deadline_at": None,
            "llm_executor": None,
            "steps": [],
        }

    @property
    def record_path(self) -> Path:
        return self.out_dir / f"daily_run_{self.date}.json"

    @property
    def brief_path(self) -> Path:
        return self.out_dir / f"heartbeat_{self.date}.md"

    def _summary_text(self) -> str:
        path = self.out_dir / f"heartbeat_{self.date}.summary.txt"
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            text = ""
        return text.splitlines()[0][:300] if text else "每日心跳"

    def _templates(self) -> dict[str, str]:
        return {
            "date": self.date,
            "run_id": self.run_id,
            "brief": str(self.brief_path),
            # ⑲ 的 --summary：⑱ 寫出的摘要行（`Daily <日期>｜球在你 N`＋紅旗）；⑱ 沒寫出來就退回固定字串
            "summary": self._summary_text(),
            "summary_file": str(self.out_dir / f"heartbeat_{self.date}.summary.txt"),
            "triage_batch": str(self.out_dir / f"triage_batch_{self.date}.json"),
            "triage_result": str(self.out_dir / f"triage_{self.date}.json"),
            "prescreen_batch": str(self.out_dir / f"prescreen_batch_{self.date}.json"),
            "prescreen_result": str(self.out_dir / f"prescreen_{self.date}.json"),
        }

    def _expand(self, argv: Sequence[str]) -> list[str]:
        values = self._templates()
        return [re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), m.group(0)), a) for a in argv]

    # ---- 紀錄 -----------------------------------------------------------
    def log(self, message: str) -> None:
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
        line = f"[{stamp}] {message}\n"
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            with (self.out_dir / "daily_task.log").open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass  # log 寫不進去也不得阻斷 daily 本身
        try:
            sys.stderr.write(line)
        except (OSError, UnicodeError):
            pass

    def save_record(self) -> None:
        try:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            tmp = self.record_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(tmp, self.record_path)
        except OSError as exc:
            self.log(f"執行紀錄寫不進去：{type(exc).__name__}: {exc}")

    def _step_row(self, step: DailyStep, **fields: Any) -> dict[str, Any]:
        row = {"key": step.key, "label": step.label, "kind": step.kind, "writes": step.writes,
               "network": step.network, "status": "pending"}
        row.update(fields)
        self.record["steps"].append(row)
        return row

    # ---- 子行程 ---------------------------------------------------------
    def _child_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["STOCKBOT_WRITER_OWNER"] = "scheduled"
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def _run(self, argv: Sequence[str], *, timeout_minutes: float,
             env: Mapping[str, str] | None = None) -> tuple[str, Completed | None, float, str | None]:
        """回傳 (status, completed, seconds, error)；status ∈ ok／failed／timeout／error。"""
        begun = datetime.now(timezone.utc)
        try:
            completed = self.runner(list(argv), cwd=self.root, timeout=timeout_minutes * 60,
                                    env=env if env is not None else self._child_env())
        except subprocess.TimeoutExpired:
            return "timeout", None, (datetime.now(timezone.utc) - begun).total_seconds(), \
                f"超過 {timeout_minutes:g} 分鐘"
        except Exception as exc:  # noqa: BLE001 — 起不來也只是這一步失敗
            return "error", None, (datetime.now(timezone.utc) - begun).total_seconds(), \
                f"{type(exc).__name__}: {exc}"
        seconds = (datetime.now(timezone.utc) - begun).total_seconds()
        return ("ok" if completed.returncode == 0 else "failed"), completed, seconds, None

    def _git(self, *args: str) -> str | None:
        status, completed, _s, _e = self._run([*GIT_SAFE, *args], timeout_minutes=1,
                                              env=dict(os.environ))
        if status != "ok" or completed is None:
            return None
        return completed.stdout.rstrip()  # porcelain 開頭的空白有語意，只削尾端

    # ---- 開頭：config、HEAD、自我比對、鎖 --------------------------------
    def prepare(self) -> None:
        from engine_b import routine_config

        self.schedule = routine_config.load_schedule(self.config_path)
        try:
            self.llm = routine_config.load_llm(self.config_path, repo_root=self.root)
            self.record["llm_executor"] = self.llm["executor"]
        except ValueError as exc:
            # LLM 設定壞掉只停 LLM 步驟（R2-a NB-12）：harvest、ETL、備份跟它無關，不陪葬。
            self.llm = None
            self.record["llm_executor"] = None
            self.record["llm_config_error"] = str(exc)
        started = datetime.fromisoformat(self.record["started_at"])
        limit = float(self.schedule["execution_time_limit_minutes"])
        self.deadline = started + timedelta(minutes=limit - essential_reserve_minutes(self.steps))
        self.record["deadline_at"] = self.deadline.isoformat()

        head = self._git("rev-parse", "HEAD")
        porcelain = self._git("status", "--porcelain")
        self.record["head"] = head
        lines = [] if not porcelain else porcelain.splitlines()
        self.record["dirty_paths"] = lines[:20]
        self.record["dirty_count"] = len(lines)  # 列表只留前 20 條，總數照實記（INV-3：不得靜默截斷）
        if porcelain is None:
            self.record["dirty_paths"] = ["（git status 讀不到）"]
            self.record["dirty_count"] = None

        self.record["schedule_check"] = self.compare_schedule()

        from engine_b.writer_lock import SCHEDULED_OWNER, WriterLockHeld, acquire

        try:
            acquire(SCHEDULED_OWNER, purpose="crons/daily_task.py", path=self.lock_path)
            self.lock_ok = True
            self.record["writer_lock"] = {"acquired": True}
        except WriterLockHeld as exc:
            self.lock_ok = False
            self.lock_reason = f"writer lock 由 {exc.holder.get('owner')!r} 持有中（expires_at={exc.holder.get('expires_at')}）"
            self.record["writer_lock"] = {"acquired": False, "reason": self.lock_reason,
                                          "holder": exc.holder}

    def compare_schedule(self) -> dict[str, Any]:
        """實際註冊值 vs config。**心跳只讀這份結果**，不得自己開 subprocess。"""
        assert self.schedule is not None
        name = str(self.schedule["task_name"])
        expected = {
            "time": str(self.schedule["daily_local_time"]),
            "execution_time_limit_minutes": int(self.schedule["execution_time_limit_minutes"]),
        }
        fix = "python scripts/register_daily_task.py --apply"
        query = self.schtasks_query or _query_task_xml
        try:
            xml_text = query(name)
        except Exception as exc:  # noqa: BLE001
            xml_text = None
            reason = f"{type(exc).__name__}: {exc}"
        else:
            reason = "schtasks 查不到這個工作"
        if not xml_text:
            return {"status": "unknown", "task_name": name, "expected": expected,
                    "reason": reason, "fix": fix}
        actual = parse_task_xml(xml_text)
        diffs = [k for k in ("time", "execution_time_limit_minutes") if actual.get(k) != expected[k]]
        if actual.get("enabled") is False:
            diffs.append("enabled")
        return {"status": "mismatch" if diffs else "match", "task_name": name,
                "expected": expected, "actual": actual, "diffs": diffs,
                **({"fix": fix} if diffs else {})}

    # ---- 保險檢查 -------------------------------------------------------
    def fingerprint(self, baseline: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """順序固定：先三個檔的 sha256；`.git/config` 相對 baseline 變了就**不跑 git**。"""
        files: dict[str, str | None] = {}
        for rel in FINGERPRINT_FILES:
            path = self.root / rel
            try:
                files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            except FileNotFoundError:
                files[rel] = None
            except OSError as exc:
                files[rel] = f"unreadable:{type(exc).__name__}"
        files[".git/hooks/*"] = _dir_digest(self.root / ".git" / "hooks")
        result: dict[str, Any] = {"files": files}
        if baseline is not None and baseline.get("files", {}).get(".git/config") != files[".git/config"]:
            result["git_skipped"] = ".git/config 變了——不再跑任何 git"
            return result
        result["status"] = self._git("status", "--porcelain")
        result["head"] = self._git("rev-parse", "HEAD")
        return result

    @staticmethod
    def fingerprint_diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[str]:
        changed = [f"file:{rel}" for rel in (*FINGERPRINT_FILES, ".git/hooks/*")
                   if before.get("files", {}).get(rel) != after.get("files", {}).get(rel)]
        if after.get("git_skipped"):
            return changed or ["file:.git/config"]
        if before.get("status") != after.get("status"):
            changed.append("git:status")
        if before.get("head") != after.get("head"):
            changed.append("git:HEAD")
        return changed

    # ---- 步驟 -----------------------------------------------------------
    def _skip_reason(self, step: DailyStep, now: datetime) -> str | None:
        if self.aborted:
            return self.aborted
        if not step.essential and self.deadline is not None and now >= self.deadline:
            return "deadline：已到全域 deadline，跳過非必要步驟"
        if step.kind in ("llm", "apply"):
            if self.llm is None:
                return f"llm_config_error：{self.record.get('llm_config_error')}"
            executor = self.llm.get("executor")
            if executor == "none":
                return "executor=none"
        if step.requires and self._status_of(step.requires) != "ok":
            if step.kind == "llm":
                return f"batch_failed：{step.requires} 沒有產出（不拿舊批次去跑）"
            return f"llm_not_ok：{step.requires} 沒有成功"
        if step.writes:
            if not self.lock_ok:
                return f"writer_lock：{self.lock_reason or '沒拿到鎖'}"
            from engine_b.writer_lock import SCHEDULED_OWNER, WriterLockHeld, acquire

            try:  # 同 owner＝續期（TTL 90 分鐘 < daily 估 60–90 分鐘；第 2 輪 N-g）
                acquire(SCHEDULED_OWNER, purpose="crons/daily_task.py", path=self.lock_path)
            except WriterLockHeld as exc:
                self.lock_ok = False
                self.lock_reason = f"續期失敗：鎖被 {exc.holder.get('owner')!r} 接手"
                self.record["writer_lock"] = {"acquired": True, "renewal_failed_at": step.key,
                                              "reason": self.lock_reason, "holder": exc.holder}
                return f"writer_lock：{self.lock_reason}"
        return None

    def _status_of(self, key: str) -> str | None:
        for row in self.record["steps"]:
            if row["key"] == key:
                return row.get("status")
        return None

    def run_step(self, step: DailyStep) -> None:
        now = self.clock()
        if step.kind == "llm" and not self.aborted:
            # 保險檢查的「前」快照：取在 LLM 步驟之前、⑥ 之後（批次檔在 library/private，不影響 git 指紋）。
            # ⚠ 已中止（例如前一個 LLM 步驟後 `.git/config` 變了）就**不再取**——取指紋會跑 git。
            self.fingerprint_before = self.fingerprint()
        reason = self._skip_reason(step, now)
        if reason is not None:
            self._step_row(step, status="skipped", reason=reason)
            self.log(f"{step.key} skipped：{reason}")
            return
        if step.kind == "integrity":
            self._integrity_step(step)
            return
        if step.kind == "llm":
            self._llm_propose(step, now)
            return
        timeout = step_timeout_minutes(step, self.llm)
        if not step.essential and self.deadline is not None:
            remaining = (self.deadline - now).total_seconds() / 60
            timeout = max(0.5, min(timeout, remaining))
        target: Path | None = None
        if step.kind == "capture" and step.capture:
            target = self.out_dir / step.capture.format(date=self.date)
            target.unlink(missing_ok=True)  # 失敗就沒有檔——下游不得拿舊檔去跑
        argv = [self.python, *self._expand(step.argv)]
        self.log(f"{step.key} 開始")
        status, completed, seconds, error = self._run(argv, timeout_minutes=timeout)
        row = self._step_row(step, status=status, seconds=round(seconds, 1),
                             exit=completed.returncode if completed else None)
        if error:
            row["error"] = error
        if completed is not None:
            row["stderr_tail"] = _tail(completed.stderr, 1500)
            row["stdout_tail"] = _tail(completed.stdout, 800)
        if target is not None and completed is not None:
            # stdout 是合法 JSON 就存（`audit invariants` 有 FAIL 時 exit 1，但那份結果正是要看的）；
            # 狀態仍照 exit code——下游（⑦a）只認 status == ok，不因為有檔就拿去跑。
            try:
                payload = json.loads(completed.stdout)
            except ValueError as exc:
                row["status"] = "failed"
                row["error"] = f"stdout 不是 JSON：{exc}"
            else:
                envelope = {"schema": "daily-capture-v1", "run_id": self.run_id, "run_date": self.date,
                            "step": step.key, "exit": completed.returncode,
                            "captured_at": datetime.now(timezone.utc).isoformat(), "payload": payload}
                target.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                row["capture"] = str(target)
                row.pop("stdout_tail", None)
        if step.kind == "apply" and completed is not None:
            try:
                applied = json.loads(completed.stdout.strip().splitlines()[0])
            except (ValueError, IndexError):
                applied = None
            if isinstance(applied, dict):
                row["summary"] = applied.get("summary")
                row["rejected"] = (applied.get("rejected") or [])[:30]
                row.pop("stdout_tail", None)
        if step.kind == "publish" and completed is not None:
            try:
                row["receipt"] = json.loads(completed.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                pass
        self.log(f"{step.key} {row['status']}（exit={row.get('exit')}，{seconds:.0f}s）")

    def _llm_task(self, task: str) -> dict[str, Any]:
        """兩個 LLM 任務的差異全部集中在這裡；呼叫、白名單、能力檢查與丟棄規則是同一套（C6）。"""
        from crons import llm_step

        paths = self._templates()
        assert self.llm is not None
        if task == "triage":
            return {"batch": Path(paths["triage_batch"]), "result": Path(paths["triage_result"]),
                    "batch_key": "payload", "out_key": "items", "schema": llm_step.TRIAGE_SCHEMA,
                    "compose": llm_step.compose_triage_prompt,
                    "chunk": int(self.llm["triage_chunk_size"]),
                    "stamp": lambda item, session: {**item, "decided_by": f"claude-p:{session}"}}
        if task == "prescreen":
            return {"batch": Path(paths["prescreen_batch"]), "result": Path(paths["prescreen_result"]),
                    "batch_key": "items", "out_key": "flags", "schema": llm_step.PRESCREEN_SCHEMA,
                    "compose": llm_step.compose_prescreen_prompt,
                    "chunk": int(self.llm["prescreen_chunk_size"]),
                    "stamp": lambda item, session: {**item, "session_id": session}}
        raise ValueError(f"未知 LLM 任務：{task}")

    def _llm_propose(self, step: DailyStep, now: datetime) -> None:
        """LLM 提議（⑦a triage、⑩b 預篩；C6）。任何一批能力不符或失敗 → **整步丟棄、不寫結果檔**（N4-7）。"""
        from crons import llm_step

        spec = self._llm_task(str(step.llm_task))
        result_path: Path = spec["result"]
        result_path.unlink(missing_ok=True)  # 先刪同日舊檔：這一次失敗就不留任何可被套用步驟吃到的東西
        row = self._step_row(step, status="running")
        self.log(f"{step.key} 開始")

        def fail(status: str, error: str) -> None:
            row["status"] = status
            row["error"] = error
            self.log(f"{step.key} {status}：{error}")

        try:
            envelope = json.loads(spec["batch"].read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return fail("failed", f"批次讀不到：{type(exc).__name__}: {exc}")
        if not isinstance(envelope, dict) or envelope.get("run_id") != self.run_id:
            return fail("failed", "批次的 run_id 不是這一輪的——不拿舊批次去跑")
        batch = [item for item in envelope.get(spec["batch_key"]) or [] if isinstance(item, dict)]
        assert self.llm is not None
        if not batch:
            self._write_llm_result(result_path, spec["out_key"], [])
            row.update(status="ok", proposed=0, note="批次為空，沒有呼叫模型")
            self.log(f"{step.key} ok：批次為空")
            return
        cwd = Path(self.llm["cwd_path"])
        try:
            cwd.mkdir(parents=True, exist_ok=True)
            leftover = [p.name for p in cwd.iterdir()]
        except OSError as exc:
            return fail("failed", f"llm.cwd 建不起來：{exc}")
        if leftover:
            return fail("failed", f"llm.cwd 不是空目錄（{leftover[:3]}）——CLI 會把裡面的東西帶進 context")
        instruction_files = [str(p / name) for p in (cwd, *cwd.parents) for name in INSTRUCTION_FILES
                             if (p / name).is_file()]
        if instruction_files:
            return fail("failed", f"llm.cwd 或上層目錄有指令檔 {instruction_files[:3]}——`agents-md@builtin` 會載入它們（R2-a NB-11）")
        argv = llm_step.llm_argv(self.llm["claude_path_resolved"], str(self.llm["claude_model"]),
                                 llm_step.schema_text(spec["schema"]))
        env = llm_step.llm_env(self.parent_env)
        runner = self.llm_runner or llm_step.run_claude
        timeout = step_timeout_minutes(step, self.llm)
        if self.deadline is not None:
            timeout = max(0.5, min(timeout, (self.deadline - now).total_seconds() / 60))
        size = spec["chunk"]
        calls: list[dict[str, Any]] = []
        proposals: list[dict[str, Any]] = []
        for start in range(0, len(batch), size):
            chunk = batch[start:start + size]
            outcome = runner(spec["compose"](chunk), argv=argv, cwd=cwd, env=env, timeout_minutes=timeout)
            calls.append(outcome.as_record())
            row["calls"] = calls
            if outcome.status == "capability_violation":
                self.record["capability_violation"] = {"step": step.key, "violations": outcome.violations,
                                                       "init_capabilities": calls[-1]["init_capabilities"]}
                return fail("capability_violation", "；".join(outcome.violations))
            if outcome.status != "ok":
                return fail(outcome.status, outcome.error or outcome.status)
            structured = outcome.structured
            if not isinstance(structured, dict) or not isinstance(structured.get(spec["out_key"]), list):
                return fail("failed", f"structured_output 不是 {{{spec['out_key']}: [...]}}")
            for item in structured[spec["out_key"]]:
                if isinstance(item, dict):
                    proposals.append(spec["stamp"](item, outcome.session_id))
        self._write_llm_result(result_path, spec["out_key"], proposals,
                               sessions=[c["session_id"] for c in calls])
        row.update(status="ok", proposed=len(proposals), batch=len(batch),
                   session_id=",".join(str(c["session_id"]) for c in calls))
        self.log(f"{step.key} ok：{len(batch)} 則、{len(calls)} 次呼叫")

    def _write_llm_result(self, path: Path, out_key: str, proposals: list[dict[str, Any]],
                          sessions: list[Any] | None = None) -> None:
        payload = {"schema": "llm-result-v1", "run_id": self.run_id, "run_date": self.date,
                   "sessions": sessions or [], out_key: proposals}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _integrity_step(self, step: DailyStep) -> None:
        before = self.fingerprint_before
        if before is None:
            self._step_row(step, status="skipped", reason="沒有「前」快照（LLM 步驟沒有經過）")
            return
        after = self.fingerprint(before)
        changed = self.fingerprint_diff(before, after)
        if changed:
            self.aborted = "integrity_violation：保險檢查的指紋變了，其後全部跳過（含心跳與發送）"
            self.record["integrity_violation"] = {"step": step.key, "changed": changed}
            self._step_row(step, status="violation", changed=changed)
            self.log(f"{step.key} VIOLATION：{changed}")
        else:
            self._step_row(step, status="ok")

    # ---- 主流程 ---------------------------------------------------------
    def run(self) -> dict[str, Any]:
        self.log(f"daily 開始（run_id={self.run_id}）")
        self.save_record()
        try:
            self.prepare()
        except Exception as exc:  # noqa: BLE001 — 最外層保證：之後照樣組心跳＋發送
            self.record["pre_loop_error"] = f"{type(exc).__name__}: {exc}"
            self.log(f"進步驟迴圈前失敗：{self.record['pre_loop_error']}")
            steps = [s for s in self.steps if s.kind in ("heartbeat", "publish")]
            for step in self.steps:
                if step not in steps:
                    self._step_row(step, status="skipped", reason="pre_loop_error")
        else:
            steps = list(self.steps)
        for step in steps:
            try:
                if step.kind == "heartbeat":
                    self.save_record()  # 心跳讀的是這份紀錄
                self.run_step(step)
            except Exception as exc:  # noqa: BLE001 — 單步失敗不阻斷後續
                self._step_row(step, status="error", error=f"{type(exc).__name__}: {exc}")
                self.log(f"{step.key} error：{type(exc).__name__}: {exc}")
            self.save_record()
        self.record["finished_at"] = self.clock().isoformat()
        if self.record["integrity_violation"]:
            self.record["status"] = "aborted_integrity"
        elif self.record["pre_loop_error"]:
            self.record["status"] = "pre_loop_error"
        else:
            self.record["status"] = "completed"
        self.save_record()
        self.log(f"daily 結束（status={self.record['status']}）")
        return self.record


def _query_task_xml(task_name: str) -> str | None:
    """`schtasks /Query /TN <name> /XML`；查不到回 None。輸出是系統 codepage 的文字（不是 UTF-16 檔）。"""
    completed = subprocess.run(["schtasks", "/Query", "/TN", task_name, "/XML"],
                               capture_output=True, timeout=60, shell=False)
    if completed.returncode != 0:
        return None
    raw = completed.stdout or b""
    for encoding in ("utf-16",) if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8", "mbcs", "cp950", "latin-1"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return None


_NS = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}


def _duration_minutes(value: str | None) -> int | None:
    """ISO 8601 duration（`PT3H`、`PT90M`、`PT1H30M`）→ 分鐘。"""
    if not value:
        return None
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value.strip())
    if not m:
        return None
    days, hours, minutes, _sec = (int(x) if x else 0 for x in m.groups())
    return days * 1440 + hours * 60 + minutes


def parse_task_xml(text: str) -> dict[str, Any]:
    """從 Task Scheduler XML 取出要比對的欄位（觸發時間、時限、命令、是否啟用）。"""
    body = re.sub(r"^\s*<\?xml[^>]*\?>", "", text.strip())
    root = ET.fromstring(body)
    start = root.findtext(".//t:Triggers/t:CalendarTrigger/t:StartBoundary", default=None, namespaces=_NS)
    limit = root.findtext(".//t:Settings/t:ExecutionTimeLimit", default=None, namespaces=_NS)
    enabled = root.findtext(".//t:Settings/t:Enabled", default=None, namespaces=_NS)
    command = root.findtext(".//t:Actions/t:Exec/t:Command", default=None, namespaces=_NS)
    arguments = root.findtext(".//t:Actions/t:Exec/t:Arguments", default=None, namespaces=_NS)
    time = None
    if start:
        m = re.search(r"T(\d{2}):(\d{2})", start)
        time = f"{m.group(1)}:{m.group(2)}" if m else None
    return {
        "time": time,
        "start_boundary": start,
        "execution_time_limit_minutes": _duration_minutes(limit),
        "enabled": None if enabled is None else enabled.strip().lower() == "true",
        "command": command,
        "arguments": arguments,
    }


def dry_run_text(config_path: Path = CONFIG_PATH) -> str:
    from engine_b import routine_config

    lines = []
    try:
        schedule = routine_config.load_schedule(config_path)
        llm = routine_config.load_llm(config_path)
        lines.append(f"排程：每日 {schedule['daily_local_time']}（{schedule['timezone']}）"
                     f"｜工作 {schedule['task_name']}｜時限 {schedule['execution_time_limit_minutes']} 分鐘"
                     f"｜預估 {schedule['expected_duration_minutes']} 分鐘")
        lines.append(f"LLM：executor={llm['executor']}｜model={llm['claude_model']}｜cwd={llm['cwd_path']}")
        lines.append(f"各步 timeout 加總 {total_timeout_minutes(DAILY_STEPS, llm):g} 分鐘"
                     f"｜必要步驟保留 {essential_reserve_minutes():g} 分鐘")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"⚠ config 讀不到：{type(exc).__name__}: {exc}")
    for step in DAILY_STEPS:
        flags = ("寫" if step.writes else "讀") + ("／連網" if step.network else "") \
            + ("／必要" if step.essential else "")
        cmd = " ".join(step.argv) if step.argv else f"（{step.kind}）"
        lines.append(f"  {step.key:28} {step.timeout_minutes:>5g} 分｜{flags}｜{cmd}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="唯一的無人值守排程：固定步驟清單＋心跳＋發送")
    parser.add_argument("--dry-run", action="store_true", help="印步驟清單與 config 時間，不執行")
    args = parser.parse_args(argv)
    if args.dry_run:
        sys.stdout.write(dry_run_text())
        return 0
    try:
        DailyRun().run()
    except Exception as exc:  # noqa: BLE001 — 永遠 exit 0：下游是人眼
        try:
            sys.stderr.write(f"daily_task 未預期例外：{type(exc).__name__}: {exc}\n")
        except (OSError, UnicodeError):
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
