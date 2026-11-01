"""crons/llm_quota.py — 讀 Claude 訂閱額度的**同一個數**（ROADMAP「週額度常駐計數器」③，2026-11-01 批次三 B）。

daily 的每次 `claude -p` 都把 `rate_limit_event` 的每個窗（`five_hour`／`seven_day`）記進執行紀錄
（`crons/llm_step.py::_rate_limit` 的 `windows`）。短版 ④ 每天那一行、心跳摘要行的旗、以及這個命令，讀的都是
`crons.heartbeat.quota_usage` 同一個函式——互動 session 開 workflow／大量 fan-out 前先跑它（2026-10-09、10-17 兩次
整批 agent 撞額度，之前沒有任何地方看得到「快用完了」）。

    python -m crons.llm_quota            # 今天（沒有就最近一份）daily 執行紀錄裡最後一次呼叫回報的用量
    python -m crons.llm_quota --probe    # 另跑一次最小的 `claude -p`（預設 haiku、effort low、零工具）讀**當下**的數；它自己也吃一點額度
    python -m crons.llm_quota --json

**只印不擋**：exit 永遠 0（讀不到也是 0，印出為什麼）；研究不因它停，daily 也不因它換模型。門檻
（`crons.heartbeat.QUOTA_FLAG_THRESHOLD`）只決定粗體與旗，量一個月再定。探針與 daily 同一組 argv、環境白名單、
能力檢查（`llm_argv`／`run_claude`），cwd 一樣要是 repo 外的空目錄；不寫任何 authority、不寫 daily 的執行紀錄。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crons import heartbeat as hb  # noqa: E402
from crons import llm_step  # noqa: E402

#: 探針：零工具、只回一個布林。schema 給 `--json-schema`（它是 `StructuredOutput` 工具的來源，與 daily 同形）。
PROBE_SCHEMA_TEXT = '{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"],"additionalProperties":false}'
PROBE_PROMPT = '只回 {"ok": true}。'
PROBE_MODEL = "haiku"
PROBE_EFFORT = "low"
PROBE_TIMEOUT_MINUTES = 2.0
#: 「最近一份」最多往回找幾天（再舊的數字已經是另一個 7 天窗的事）。
RECENT_DAYS = 7


def latest_record(*, now: datetime, record_dir: Path | None = None
                  ) -> tuple[Path | None, Mapping[str, Any] | None, str | None]:
    """今天的 daily 執行紀錄；沒有就往回找最近一份（最多 `RECENT_DAYS` 天）。回 (路徑, 紀錄, 問題)。"""
    directory = record_dir or hb.RUN_RECORD_DIR
    today = now.astimezone().date()
    for back in range(RECENT_DAYS + 1):
        path = directory / f"daily_run_{(today - timedelta(days=back)).isoformat()}.json"
        if path.is_file():
            record, problem = hb._load_run_record(path, now=now)
            return path, record, problem
    return None, None, f"最近 {RECENT_DAYS} 天沒有任何 daily 執行紀錄（{directory}）"


def probe(llm: Mapping[str, Any], *, model: str = PROBE_MODEL, effort: str = PROBE_EFFORT,
          timeout_minutes: float = PROBE_TIMEOUT_MINUTES,
          runner: Callable[..., llm_step.LlmOutcome] | None = None) -> dict[str, Any]:
    """跑一次最小的 `claude -p` 讀當下的額度。cwd 的檢查與 daily 同（repo 外的空目錄）；失敗回 status 與理由，不 raise。
    `rate_limit_event` 在 result 之前就到——額度被擋（rejected）時一樣讀得到兩個窗。"""
    cwd = Path(llm["cwd_path"])
    try:
        cwd.mkdir(parents=True, exist_ok=True)
        leftover = [p.name for p in cwd.iterdir()]
    except OSError as exc:
        return {"status": "failed", "error": f"llm.cwd 建不起來：{exc}", "rate_limit": None}
    if leftover:
        return {"status": "failed", "rate_limit": None,
                "error": f"llm.cwd 不是空目錄（{leftover[:3]}）——CLI 會把裡面的東西帶進 context"}
    argv = llm_step.llm_argv(llm["claude_path_resolved"], model, PROBE_SCHEMA_TEXT, effort=effort)
    run = runner or llm_step.run_claude
    outcome = run(PROBE_PROMPT, argv=argv, cwd=cwd, env=llm_step.llm_env(), timeout_minutes=timeout_minutes)
    return {"status": outcome.status, "error": outcome.error, "rate_limit": outcome.rate_limit,
            "model": outcome.model, "seconds": round(outcome.seconds, 1), "cost_usd": outcome.cost_usd}


def _local_text(stamp: Any) -> str:
    try:
        return datetime.fromisoformat(str(stamp)).astimezone().strftime("%m-%d %H:%M")
    except (TypeError, ValueError):
        return "時間沒記"


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probe", action="store_true",
                        help="另跑一次最小的 claude -p 讀當下的數（吃一點額度；與 daily 同一組 argv 與白名單）")
    parser.add_argument("--model", default=PROBE_MODEL, help=f"探針用的模型（預設 {PROBE_MODEL}；daily 的模型不受影響）")
    parser.add_argument("--json", action="store_true", help="機器可讀")
    parser.add_argument("--record-dir", type=Path, default=None,
                        help="daily 執行紀錄目錄（預設 library/private/heartbeat；測試用）")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    path, record, problem = latest_record(now=now, record_dir=args.record_dir)
    rows = {str(r.get("key")): r for r in (record or {}).get("steps") or [] if isinstance(r, Mapping)}
    usage = hb.quota_usage(rows)
    out: dict[str, Any] = {
        "record": str(path) if path else None,
        "record_date": path.stem.removeprefix("daily_run_") if path else None,
        "record_finished_at": (record or {}).get("finished_at"),
        "problem": problem, "usage": usage, "threshold": hb.QUOTA_FLAG_THRESHOLD, "flag": hb.quota_flag(usage),
        "line": hb.quota_usage_line(usage, now=now, record=record, record_problem=problem),
    }
    if args.probe:
        try:
            from engine_b.routine_config import load_llm

            result = probe(load_llm(), model=args.model)
        except Exception as exc:  # noqa: BLE001 — 設定讀不到、路徑不對都只是「探針沒跑成」，照印理由
            result = {"status": "failed", "error": f"{type(exc).__name__}: {exc}", "rate_limit": None}
        fresh = hb.quota_usage({"probe": {"calls": [{"rate_limit": result.get("rate_limit")}]}}, keys=("probe",))
        out["probe"] = {**result, "usage": fresh, "flag": hb.quota_flag(fresh),
                        "line": (hb.quota_usage_line(fresh, now=now) if fresh else
                                 f"探針沒有回報用量（{result.get('status')}：{result.get('error') or '—'}）")}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return 0
    print(out["line"])
    if path is not None:
        print(f"來源：daily 執行紀錄 {out['record_date']}（daily 結束 {_local_text(out['record_finished_at'])}；"
              f"之後互動 session 用掉的不在這個數裡——要當下的數加 --probe）")
    else:
        print(f"來源：{problem}")
    if args.probe:
        print(f"探針（當下）：{out['probe']['line']}")
    print(f"門檻 {hb.QUOTA_FLAG_THRESHOLD:.0%}：只印不擋——≥ 門檻時心跳摘要行加旗、短版 ④ 粗體；"
          "開 workflow／大量 fan-out 前先看這個數")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
