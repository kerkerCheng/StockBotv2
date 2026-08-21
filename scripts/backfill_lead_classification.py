"""把既有 lead 補上 pq1 分類字彙（一次性 migration，可重跑）。

**只做確定性的那一類。** SEC Form 4 由 `source=edgar:*` ＋ 標題 `<TICKER> 4 filed <date>`
唯一識別，判定不需要語意——既有 triage 也已多次自行寫下同一結論（「個別 Form 4 資訊量低；
內部人交易應以彙總方式讀（Engine C 稀釋項），不逐筆進 pq1」，167 筆中 107 筆判 no_go）。

其餘一律留 `unknown`，交給 `skills/signal-triage` 的語意分類，**不用 regex 猜**。

⚠ **這不是「硬編排除 Form 4」**（`ROADMAP` 明文禁止的打地鼠）。差別在：
- 打地鼠＝在排序器裡寫 `if "Form 4" in title: sink`。`engine_b/priority.py` **沒有任何
  Form 4 知識**，可自行 grep 驗證。
- 本腳本＝用確定性規則產生**資料**，排序器只讀通用字彙。新的「一手＋持股＋無內容」類型
  出現時，由 triage 分類處理，不需要改程式。

每筆都標 `classified_by="backfill_deterministic_v1"`，與 triage 的語意分類可區分，
之後要稽核或回溯都認得出來。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_b import leads, priority  # noqa: E402

FORM4_TITLE = re.compile(r"^[A-Z0-9.]+\s+4\s+filed\s+\d{4}-\d{2}-\d{2}\s*$")


def is_form4(lead: dict) -> bool:
    return str(lead.get("source") or "").startswith("edgar:") and bool(
        FORM4_TITLE.match(str(lead.get("title") or ""))
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leads", default=str(leads.DEFAULT_LEADS_PATH))
    ap.add_argument("--apply", action="store_true", help="實際寫入；預設只報告")
    args = ap.parse_args()

    store = leads.load(args.leads)
    now = datetime.now(timezone.utc).isoformat()
    changed = 0
    for lead in store["leads"].values():
        if not is_form4(lead) or priority.classification(lead):
            continue
        triage = lead.setdefault("triage", {})
        triage["classification"] = {
            "content_type": "insider_transaction",
            "decision_impact": "confidence_only",
            "classified_by": "backfill_deterministic_v1",
            "classified_at": now,
            "reason": "個別 Form 4 不改變候選集合或排序；內部人交易應以彙總方式讀（Engine C 稀釋項）",
        }
        changed += 1

    total = len(store["leads"])
    unclassified = sum(1 for l in store["leads"].values() if not priority.classification(l))
    print(f"lead 總數 {total}｜本次補分類 {changed}｜仍未分類 {unclassified}")
    print("仍未分類者由 skills/signal-triage 的語意分類處理，本腳本不猜。")

    if args.apply and changed:
        leads.save(store, args.leads)
        print(f"已寫入 {args.leads}")
    elif not args.apply:
        print("（未加 --apply，沒有寫入）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
