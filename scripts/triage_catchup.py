"""互動補跑分類（2026-10-07 使用者：「好像有蠻多還需要 triage 繼續吧」）——與 daily ⑥⑦a⑦b **同一條路**，只是現在跑。

為什麼不用互動的 `engine_b.cli triage` 一則一則下：那個入口的 `--classified-by` 只有 directed／graph_walk／triage_semantic_v1，
互動手判 88 則會被記成分類層判的，每日訊息①的「LLM／互動」就說錯了（L12）。這支照 daily 的做法：

  ⑥ `engine_b.cli list --status pending --by-priority --triage-batch --json`（上限照 `config/daily_routine.json` 的
     `triage.daily_limit`，CLI 自己截、把沒進批的數印出來——不靠 prompt 自律）
  ⑦a `claude -p` 零工具、只回 JSON（`crons/llm_step.llm_argv`、能力檢查、每批 `llm.triage_chunk_size` 則，任何一批不 ok
     就整次丟棄、不寫結果檔）
  ⑦b `engine_b.cli triage-apply --file … --batch … --run-id …`（逐則驗證後才寫 lead registry）

批次與結果檔只寫在 `--out`（不碰 daily 的執行紀錄與心跳檔）。**呼叫者必須持互動 writer lock**（⑦b 會寫 lead registry）。
互動用，不進 daily 的步驟清單（不是無人值守入口）。

    python scripts/writer_guard.py acquire --purpose "triage 補跑"
    python scripts/triage_catchup.py --out <暫存目錄>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="互動補跑分類：與 daily ⑥⑦a⑦b 同一條路（結果由 triage-apply 驗過才寫）")
    parser.add_argument("--out", type=Path, required=True, help="批次與結果檔寫在這裡（不碰 daily 的檔）")
    args = parser.parse_args(argv)

    from crons import llm_step
    from engine_b import writer_lock
    from engine_b.routine_config import load_llm

    holder = writer_lock.holder() or {}
    if holder.get("owner") != writer_lock.INTERACTIVE_OWNER or writer_lock.is_stale(holder):
        print("✗ 沒有持互動 writer lock——先 `python scripts/writer_guard.py acquire`（⑦b 會寫 lead registry）", file=sys.stderr)
        return 2
    llm = load_llm()
    if str(llm.get("executor")) != "claude":
        print(f"✗ llm.executor={llm.get('executor')}——分類層關著", file=sys.stderr)
        return 2
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    date = datetime.now().astimezone().strftime("%Y-%m-%d")

    # ⑥ 批次：CLI 自己截上限
    listed = subprocess.run([sys.executable, "-m", "engine_b.cli", "list", "--status", "pending", "--by-priority",
                             "--triage-batch", "--json"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if listed.returncode != 0:
        print(f"✗ 批次失敗：{listed.stderr.strip()[-300:]}", file=sys.stderr)
        return 1
    payload = json.loads(listed.stdout)
    batch_path = out / "triage_batch.json"
    batch_path.write_text(json.dumps({"schema": "daily-capture-v1", "run_id": run_id, "run_date": date,
                                      "step": "06_triage_batch", "exit": 0,
                                      "captured_at": datetime.now(timezone.utc).isoformat(), "payload": payload},
                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    items = [item for item in payload if isinstance(item, dict)]
    print(f"⑥ 批次 {len(items)} 則（{listed.stderr.strip().splitlines()[-1] if listed.stderr.strip() else '全部進批'}）")
    if not items:
        return 0

    # ⑦a 提議：與 daily 同一組 argv、能力檢查；任何一批不 ok 就整次丟棄
    cwd = Path(llm["cwd_path"])
    cwd.mkdir(parents=True, exist_ok=True)
    if any(cwd.iterdir()):
        print(f"✗ llm.cwd 不是空目錄：{cwd}——CLI 會把裡面的東西帶進 context", file=sys.stderr)
        return 2
    argv_llm = llm_step.llm_argv(llm["claude_path_resolved"], str(llm["claude_model"]),
                                 llm_step.schema_text(llm_step.TRIAGE_SCHEMA))
    size = int(llm["triage_chunk_size"])
    timeout = float(llm["triage_timeout_minutes"])
    proposals, sessions = [], []
    for start in range(0, len(items), size):
        chunk = items[start:start + size]
        outcome = llm_step.run_claude(llm_step.compose_triage_prompt(chunk), argv=argv_llm, cwd=cwd,
                                      env=llm_step.llm_env(), timeout_minutes=timeout)
        if outcome.status != "ok":
            print(f"✗ ⑦a 第 {start // size + 1} 批 {outcome.status}：{outcome.error}——整次丟棄、不寫結果檔", file=sys.stderr)
            return 1
        structured = outcome.structured
        if not isinstance(structured, dict) or not isinstance(structured.get("items"), list):
            print("✗ ⑦a structured_output 不是 {items: [...]}——整次丟棄", file=sys.stderr)
            return 1
        sessions.append(outcome.session_id)
        proposals += [{**item, "decided_by": f"claude-p:{outcome.session_id}"}
                      for item in structured["items"] if isinstance(item, dict)]
        print(f"⑦a 第 {start // size + 1} 批：{len(chunk)} 則 → 提議 {len(structured['items'])}")
    result_path = out / "triage_result.json"
    result_path.write_text(json.dumps({"schema": "llm-result-v1", "run_id": run_id, "run_date": date,
                                       "sessions": sessions, "items": proposals}, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    # ⑦b 套用：逐則驗證後才寫
    applied = subprocess.run([sys.executable, "-m", "engine_b.cli", "triage-apply", "--file", str(result_path),
                              "--batch", str(batch_path), "--run-id", run_id], cwd=ROOT, capture_output=True,
                             text=True, encoding="utf-8")
    print(applied.stdout.strip()[:1500])
    if applied.returncode != 0:
        print(f"✗ ⑦b：{applied.stderr.strip()[-500:]}", file=sys.stderr)
    return applied.returncode


if __name__ == "__main__":
    raise SystemExit(main())
