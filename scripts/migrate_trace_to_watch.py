"""一次性遷移（[321]）：trace backlog → Event Watch registry。

把 `trace_backlog()` 列出的等待條件轉成 watch，讓兩套等待引擎收斂成單一入口。
遷移的實質收益是 **trace 繼承 `expires`**：原本 consumed-marker 用完即靜默沉底
（實測 10/50 已不可能再被喚醒，而 `auto_trigger_reachable` 對它們全回 true），
有到期日之後，標的用完只是「停滯」，到期仍會強制現形讓人決定。

kind 映射（消重複，不搬重複）：
    primary_source_signal → entity_filing_signal   （判準本就相同：tier-1 ＋ entities 交集）
    related_entity_signal → related_entity_signal  （原樣，含 consumed-marker）

`trace_requires_user=true` 的**不建 watch**：它走 pq2 人工決定路徑（[193]），
本來就不靠自動觸發，建 watch 只會讓它同時出現在兩個地方。

冪等：同一 lead 已有未 consumed 的 watch 就跳過。可安全重跑。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine_b import event_watch as ew  # noqa: E402
from engine_b.leads import load as load_leads, trace_backlog  # noqa: E402

# 一個財報週期（90 天）＋緩衝。最常見的等待模式是「下一份季報會不會揭露」，
# 等滿一輪還沒出現就該讓人重新決定，而不是無聲續等。
DEFAULT_TTL_DAYS = 120


def _parked_day(lead: dict) -> date | None:
    stamp = (lead.get("triage") or {}).get("decided_at") or lead.get("first_seen") or ""
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="遷移 trace backlog 到 Event Watch registry")
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS)
    parser.add_argument("--apply", action="store_true", help="實際寫入；預設 dry-run")
    args = parser.parse_args()

    store = load_leads()
    rows = trace_backlog(store)
    data = ew.load_watches()
    existing = {
        str(w.get("wake_lead"))
        for w in data.get("watches", [])
        if w.get("wake_lead") and w.get("status") != "consumed"
    }

    created, skipped, manual = [], [], []
    for row in rows:
        lead_id = row["lead_id"]
        if row["requires_user"]:
            manual.append(lead_id)
            continue
        if lead_id in existing:
            skipped.append(lead_id)
            continue
        lead = store["leads"][lead_id]
        refs = lead.get("refs") or {}
        raw_kind = str(refs.get("trace_trigger_kind") or "").strip() or "related_entity_signal"
        kind = "entity_filing_signal" if raw_kind == "primary_source_signal" else raw_kind

        entities = list(refs.get("trace_trigger_entities") or ())
        if not entities:
            from engine_b.entities import lead_entities

            entities = sorted(lead_entities(lead))
        if not entities:
            # 沒有具名標的的不建 watch——那不是「等不到」，是根本沒有觸發條件。
            # 它會在 trace_backlog 以 wake_state=unwatched 現形，由人決定處置。
            skipped.append(f"{lead_id}(無標的)")
            continue

        parked = _parked_day(lead) or date.today()
        expires = (parked + timedelta(days=args.ttl_days)).isoformat()
        consumed = list(refs.get("trace_requeue_consumed_entities") or ())
        # 已停滯的（標的全消化）開啟主動輪詢：被動層救不了它們，
        # 這正是 T2 sweep 存在的理由。其餘維持被動，不佔輪詢預算。
        stalled = bool(entities) and not {
            e for e in entities if e.strip().upper() not in {c.strip().upper() for c in consumed}
        }

        if args.apply:
            ew.add_watch(
                data,
                kind=kind,
                wake_lead=lead_id,
                expires=expires,
                entities=entities,
                consumed_entities=consumed,
                poll_eligible=stalled,
                poll_query_hint=str(refs.get("trace_next_trigger") or "")[:200],
                note=f"[321] 由 trace backlog 遷移；trace_status={row['trace_status']}",
                created_at=parked.isoformat() + "T00:00:00+00:00",
            )
        created.append(f"{lead_id} {kind}{' +poll' if stalled else ''} exp={expires}")

    print(f"backlog 共 {len(rows)} 筆")
    print(f"  建立 watch：{len(created)}")
    print(f"  跳過（已有 watch／無標的）：{len(skipped)}")
    print(f"  requires_user 走 pq2 不建 watch：{len(manual)} {manual}")
    for line in created:
        print("   +", line)
    if skipped:
        print("  skipped:", skipped)

    if args.apply:
        ew.save_watches(data)
        print("\n已寫入 library/leads/event_watches.json")
        print("counters:", ew.counters(data))
    else:
        print("\n(dry-run；加 --apply 實際寫入)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
