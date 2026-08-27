"""把既有 lead 補上 pq1 分類字彙（一次性 migration，可重跑）。

**只做確定性的那一類。** SEC Form 4 由 `source=edgar:*` ＋ 標題 `<TICKER> 4 filed <date>`
唯一識別，判定不需要語意——既有 triage 也已多次自行寫下同一結論（「個別 Form 4 資訊量低；
內部人交易應以彙總方式讀（Engine C 稀釋項），不逐筆進 pq1」，167 筆中 107 筆判 no_go）。

其餘一律留 `unknown`，交給 `skills/signal-triage` 的語意分類，**不用 regex 猜**。
active lead 若曾有合法 classification、只是 trace requeue 把它移進 history，則可
確定性還原原 receipt；這不是重新做語意判斷。

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
ACTIVE_STATUSES = leads.CLASSIFICATION_REQUIRED_STATUSES


def is_form4(lead: dict) -> bool:
    return str(lead.get("source") or "").startswith("edgar:") and bool(
        FORM4_TITLE.match(str(lead.get("title") or ""))
    )


def _validate(tags: dict) -> None:
    """字彙外的值一律拒絕。語意判斷可以錯，字彙不能自創——否則排序會靜默降級。"""

    priority.validate_classification(tags)
    if not str(tags.get("reason") or "").strip():
        raise ValueError("semantic backfill 必須附 reason")


def _restore_active_history(store: dict, *, now: str) -> int:
    """還原 trace requeue 遺失、但 history 已有的最近合法 receipt。"""

    changed = 0
    for lead in store["leads"].values():
        if lead.get("status") not in ACTIVE_STATUSES or priority.classification(lead):
            continue
        for entry in reversed(lead.get("triage_history") or []):
            record = dict(((entry.get("triage") or {}).get("classification") or {}))
            if not record:
                continue
            restored = priority.validate_classification(
                record,
                require_receipt=True,
            )
            restored["restored_at"] = now
            restored["restored_by"] = "backfill_history_restore_v1"
            lead.setdefault("triage", {})["classification"] = restored
            changed += 1
            break
    return changed


def _supplied_items(raw: object) -> dict[str, dict]:
    if not isinstance(raw, dict):
        raise ValueError("--from-json 必須是 JSON object")
    candidate = raw.get("items") if "items" in raw else raw
    if not isinstance(candidate, dict):
        raise ValueError("--from-json 的 items 必須是 object")
    return candidate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leads", default=str(leads.DEFAULT_LEADS_PATH))
    ap.add_argument("--apply", action="store_true", help="實際寫入；預設只報告")
    ap.add_argument(
        "--from-json",
        default=None,
        help=(
            "語意分類結果 JSON：{lead_id: {content_type, decision_impact, "
            "payment_direction?, reason}}。由 LLM 依 skills/signal-triage 的判準產生，"
            "本腳本只做確定性套用與字彙驗證——解析與授權分離（L15）。"
        ),
    )
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

    restored = _restore_active_history(store, now=now)
    changed += restored

    if args.from_json:
        supplied = _supplied_items(
            json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        )
        for lead_id, tags in supplied.items():
            lead = store["leads"].get(lead_id)
            if lead is None:
                raise KeyError(f"lead 不存在：{lead_id}")
            if lead.get("status") not in ACTIVE_STATUSES:
                raise ValueError(
                    f"semantic active backfill 拒絕非 active lead：{lead_id} status={lead.get('status')}"
                )
            _validate(tags)
            existing = priority.classification(lead)
            if existing:
                comparable_keys = (
                    "content_type", "decision_impact", "payment_direction", "reason",
                )
                if all(
                    existing.get(key) == tags.get(key)
                    for key in comparable_keys
                ):
                    continue
                raise ValueError(f"拒絕覆寫既有 classification：{lead_id}")
            record = {k: v for k, v in tags.items() if not k.startswith("_")}
            record["classified_by"] = "backfill_semantic_v1"
            record["classified_at"] = now
            record["backfill_ref"] = Path(args.from_json).name
            record = priority.validate_classification(record, require_receipt=True)
            lead.setdefault("triage", {})["classification"] = record
            changed += 1

    total = len(store["leads"])
    unclassified = sum(1 for l in store["leads"].values() if not priority.classification(l))
    active_gaps = leads.classification_gaps(store)
    print(
        f"lead 總數 {total}｜本次補分類 {changed}（history 還原 {restored}）｜"
        f"仍未分類 {unclassified}｜active 缺分類 {len(active_gaps)}"
    )
    if active_gaps:
        print(json.dumps({"active_gaps": active_gaps}, ensure_ascii=False, indent=2))
    print("仍未分類者由 skills/signal-triage 的語意分類處理，本腳本不猜。")

    if args.apply and changed:
        leads.save(store, args.leads)
        print(f"已寫入 {args.leads}")
    elif not args.apply:
        print("（未加 --apply，沒有寫入）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
