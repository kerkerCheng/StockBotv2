"""試跑每日摘要（2026-10-07 使用者：「我們等等可以跑幾次來磨」）——雷達 → 每日摘要 → Discord 短版，**不碰真資料**。

與 daily 同一套 `claude -p` 參數、白名單與能力檢查（`crons/llm_step.py`），差別只在寫到哪裡：
lead registry 用**副本**（`--out` 目錄下的 `pending_leads.json`），雷達收據、摘要、短版都寫在 `--out`。
真的 registry、watch、pq2、心跳快照一個字都不寫。互動用，不進 daily 的步驟清單（不是無人值守入口）。

    python scripts/trial_daily_brief.py --out <暫存目錄>              # 雷達＋摘要＋短版（兩次 LLM 呼叫，吃額度）
    python scripts/trial_daily_brief.py --out <暫存目錄> --skip-radar # 只重跑摘要＋短版（用上一次的雷達收據）
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _run(llm: dict, prompt: str, *, argv_fn, schema, tools, observe=None, timeout: float) -> dict:
    from crons import llm_step

    cwd = Path(llm["cwd_path"])
    cwd.mkdir(parents=True, exist_ok=True)
    if any(cwd.iterdir()):
        raise SystemExit(f"llm.cwd 不是空目錄：{cwd}——CLI 會把裡面的東西帶進 context")
    argv = argv_fn(llm["claude_path_resolved"], str(llm["claude_model"]), llm_step.schema_text(schema))
    kwargs = {"tools": tools} if tools else {}
    if observe is not None:
        kwargs["observe"] = observe
    outcome = llm_step.run_claude(prompt, argv=argv, cwd=cwd, env=llm_step.llm_env(), timeout_minutes=timeout, **kwargs)
    if outcome.status != "ok":
        raise SystemExit(f"LLM 失敗：{outcome.status}：{outcome.error}")
    return {"structured": outcome.structured, "session_id": outcome.session_id}


def main(argv=None) -> int:
    from crons import heartbeat as hb
    from crons import llm_step
    from crons.daily_brief import compose_brief
    from engine_b import digest, radar
    from engine_b.routine_config import load_llm, load_radar

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True, help="暫存目錄（registry 副本、收據、摘要、短版都寫這裡）")
    parser.add_argument("--skip-radar", action="store_true", help="不跑雷達（用 --out 裡上一次的收據與 registry 副本）")
    args = parser.parse_args(argv)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    llm = load_llm()
    run_id = "trial-" + uuid.uuid4().hex[:12]
    leads_copy = out / "pending_leads.json"
    if not args.skip_radar or not leads_copy.is_file():
        shutil.copyfile(ROOT / "library" / "leads" / "pending_leads.json", leads_copy)
    now = datetime.now(timezone.utc)

    if not args.skip_radar:
        cfg = load_radar()
        batch = out / "radar_batch.json"
        radar.prepare(run_id, batch, max_items=int(cfg["max_items"]), market_topics=cfg["market_topics"],
                      max_market_items=int(cfg["max_market_items"]))
        requests = json.loads(batch.read_text(encoding="utf-8"))["requests"]
        collector = llm_step.SearchCollector()
        got = _run(llm, llm_step.compose_radar_prompt(requests), argv_fn=llm_step.radar_argv,
                   schema=llm_step.RADAR_SCHEMA, tools=llm_step.RADAR_TOOLS, observe=collector.observe,
                   timeout=float(cfg["timeout_minutes"]))
        result = out / "radar_proposals.json"
        result.write_text(json.dumps({"schema": "llm-result-v1", "run_id": run_id, "sessions": [got["session_id"]],
                                      "search": collector.as_record(),
                                      "no_material_change": bool((got["structured"] or {}).get("no_material_change")),
                                      "items": list((got["structured"] or {}).get("items") or [])},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
        applied = radar.apply(result, batch, run_id, store_path=leads_copy, receipt_dir=out)
        print("雷達：", json.dumps(applied["summary"], ensure_ascii=False))
        print("搜尋：", "｜".join(collector.queries))

    from engine_b import leads as leads_mod

    store = leads_mod.load(leads_copy)
    dbatch = out / "digest_batch.json"
    digest.prepare(run_id, dbatch, now=now, store=store, receipt_dir=out)
    requests = json.loads(dbatch.read_text(encoding="utf-8"))["requests"]
    if requests:
        got = _run(llm, llm_step.compose_digest_prompt(requests), argv_fn=llm_step.llm_argv,
                   schema=llm_step.DIGEST_SCHEMA, tools=None, timeout=float(llm.get("digest_timeout_minutes") or 5))
        dresult = out / "digest_proposals.json"
        dresult.write_text(json.dumps({"schema": "llm-result-v1", "run_id": run_id, "sessions": [got["session_id"]],
                                       "bullets": list((got["structured"] or {}).get("bullets") or [])},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
        applied = digest.apply(dresult, dbatch, run_id, out_dir=out)
        print("摘要：", json.dumps(applied["summary"], ensure_ascii=False))
    beat = hb.compose_heartbeat(now=now)
    brief = compose_brief(now=now, summary=beat.summary, snapshot=beat.snapshot,
                          run_record_path=hb.run_record_path_for(now), leads_path=leads_copy, heartbeat_dir=out)
    (out / "brief.md").write_text(brief, encoding="utf-8")
    print("\n" + brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
