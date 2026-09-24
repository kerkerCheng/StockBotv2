"""反證登記與計數（Phase 1 Step 1.5；G7、G8、C3）——**等待只住 Event Watch registry**。

## thesis 的反證怎麼進 registry：`todo sync` 對帳，不掛在任何寫入動作上

memo 換版一律是手改 `thesis/lifecycle.json` 的 `memo`（沒有任何程式寫這一欄；`apply_proposal` 只寫
status／last_checked／next_check），所以「換 memo 的那一刻」沒有程式可以掛 hook。改成每次 `todo sync`
（daily ⑩ 與互動都會跑）對帳一次，**冪等**：

1. 非 retired 的 thesis、現行 memo 的 sidecar（`memo_path.with_suffix(".evidence.json")`）有 `disproof_conditions`、
   且 sidecar 的 `memo_sha256` 等於 memo 以**同一算法**（`thesis.memo_structure.memo_text_sha256`，CRLF→LF）
   重算的值 → 每一條確保有一筆語意 watch，去重鍵＝（`source_ref`、正規化後的條件文字）——memo 原地重產
   （同路徑）而條件換了時，舊的 consume、新的登記（第 4 輪 N4-12）。hash 不符 → **不登記**、計數
   `thesis_sidecar_mismatch`（fail closed，不猜）。
2. 在盯的語意 watch 指向**非現行** memo → consume（note 寫明）；thesis 已 retired → consume。
3. 現行 memo 沒有結構化反證（例如 2026-09-24 的三份）→ 不登記，**也不 consume** 指向它的手動登記
   （Step 1.6 由強模型以 `register-disproof` 逐條補的那些）。

## 計數（心跳段 2、audit 共用）

預期條目＝非 retired thesis 現行 memo「推翻」那一節的條目（`thesis:<memo>#1..n`）＋ 各節點現行 **v2** 讀圖的
`disproof[]`（`reading:<id>#1..n`）。五個數：**在盯**（active／fired 的語意 watch 指向預期條目）、
**觸及待處置**（判定觸及、還沒處置；A5——不得併進「未盯」）、**未盯**（預期扣掉前兩者）、
**叫不醒**（在盯之中、沒有任何一手來源會產出帶它實體的 lead）；另報 v1 讀圖散文份數（不可機械數）
與凍結歷史（舊店 `coverage_assessments` 的反證，不盯）。
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from engine_b import event_watch as ew

ROOT = Path(__file__).resolve().parent.parent
LIFECYCLE = ROOT / "thesis" / "lifecycle.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(text: str | None) -> str:
    """去重與比對用的正規化——只處理空白（與預篩引文比對同一個函式）。"""
    from engine_b.semantic_prescreen import normalize_whitespace

    return normalize_whitespace(text)


def load_lifecycle(path: Path = LIFECYCLE) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _sidecar(memo_path: Path) -> dict[str, Any] | None:
    path = memo_path.with_suffix(".evidence.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def memo_ref(source_ref: str) -> str | None:
    """`thesis:<memo 路徑>#<n>` → memo 路徑；不是 thesis 來源回 None。"""
    if not str(source_ref).startswith("thesis:"):
        return None
    return str(source_ref)[len("thesis:"):].split("#", 1)[0]


def _default_expires(entry: Mapping[str, Any], condition: str, *, today: date) -> str:
    """結構化條目沒寫 expires 時：下一個核查點＋一個核查週期（≈ 今天＋兩個週期），且不早於條件自己寫的日期。"""
    interval = entry.get("check_interval_days")
    days = int(interval) if isinstance(interval, (int, float)) and not isinstance(interval, bool) and interval > 0 else 90
    candidate = today + timedelta(days=2 * days)
    written = ew.condition_dates(condition)
    if written and max(written) >= candidate:
        candidate = max(written) + timedelta(days=30)
    return candidate.isoformat()


def reconcile_thesis_disproof(data: dict[str, Any], *, lifecycle: Mapping[str, Any] | None = None,
                              root: Path = ROOT, today: date | None = None) -> dict[str, Any]:
    """冪等對帳；只改 `data`（呼叫端存檔）。回傳摘要（登記、收掉、hash 不符、沒有結構化反證）。"""
    from thesis.memo_structure import memo_file_sha256

    lifecycle = load_lifecycle() if lifecycle is None else lifecycle
    today = today or datetime.now(timezone.utc).date()
    summary: dict[str, Any] = {"registered": [], "consumed": [], "sidecar_mismatch": [], "no_structured": []}
    current: dict[str, str] = {}
    retired: dict[str, str] = {}
    for tid, entry in lifecycle.items():
        if not isinstance(entry, dict) or not entry.get("memo"):
            continue
        memo = str(entry["memo"])
        if entry.get("status") == "retired":
            retired[memo] = str(tid)
            continue
        current[memo] = str(tid)
        memo_path = root / memo
        sidecar = _sidecar(memo_path)
        conditions = (sidecar or {}).get("disproof_conditions")
        if not conditions:
            summary["no_structured"].append(str(tid))
            continue
        try:
            same = memo_file_sha256(memo_path) == sidecar.get("memo_sha256")
        except OSError:
            same = False
        if not same:
            summary["sidecar_mismatch"].append(str(tid))
            continue
        wanted = {normalize(c.get("condition")) for c in conditions if isinstance(c, dict)}
        for index, cond in enumerate(conditions, 1):
            if not isinstance(cond, dict):
                continue
            ref = f"thesis:{memo}#{index}"
            watching = [w for w in data["watches"] if w.get("kind") == ew.SEMANTIC_KIND
                        and w.get("source_ref") == ref and w.get("status") in ("active", "fired")]
            if any(normalize(w.get("condition")) == normalize(cond.get("condition")) for w in watching):
                continue
            watch = ew.add_watch(
                data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref,
                expires=str(cond.get("expires") or _default_expires(entry, str(cond.get("condition")), today=today)),
                entities=list(cond.get("entities") or ()), condition=str(cond.get("condition")),
                check_frequency=str(cond.get("check_frequency")), action_48h=str(cond.get("action_48h")),
                quote_locator="memo「推翻」那一節", note=f"todo sync 對帳：thesis {tid} 現行 memo 的第 {index} 條",
                today=today,
            )
            summary["registered"].append(watch["watch_id"])
        # 同一份現行 memo、條件已不在 sidecar 的（原地重產、反證換了）→ 收掉
        for watch in data["watches"]:
            if (watch.get("kind") == ew.SEMANTIC_KIND and memo_ref(watch.get("source_ref") or "") == memo
                    and watch.get("status") in ("active", "fired")
                    and normalize(watch.get("condition")) not in wanted):
                _close(watch, "memo 原地重產、條件已變")
                summary["consumed"].append(watch["watch_id"])
    for watch in data["watches"]:
        memo = memo_ref(watch.get("source_ref") or "")
        if memo is None or watch.get("kind") != ew.SEMANTIC_KIND or memo in current:
            continue
        note = "thesis retired" if memo in retired else "memo 已不是 lifecycle 的現行 memo（superseded）"
        if watch.get("status") in ("active", "fired"):
            _close(watch, note)
            summary["consumed"].append(watch["watch_id"])
        elif watch.get("status") == "expired" and not watch.get("expiry_resolution"):
            # Phase 1 Step 1.7：到期待決的條件，它的 memo 已不是現行 → 記處置，不再鑄 watch_decision 問一個沒有對象的問題
            ew.resolve_expiry(data, watch["watch_id"], {"kind": "source_superseded", "note": note})
            summary["consumed"].append(watch["watch_id"])
    return summary


def _close(watch: dict[str, Any], note: str) -> None:
    watch["status"] = "consumed"
    watch["closed"] = {"at": _now(), "note": note}


# ---------------------------------------------------------------------------
# 計數
# ---------------------------------------------------------------------------

def _touched_pending(watch: Mapping[str, Any]) -> bool:
    judgment = watch.get("judgment") or {}
    return judgment.get("touches") == "yes" and not judgment.get("handled")


def disproof_counts(watches: Sequence[Mapping[str, Any]], *, lifecycle: Mapping[str, Any] | None = None,
                    readings: Mapping[str, Any] | None = None, coverage: frozenset[str] | None = None,
                    frozen_history: int | None = None, root: Path = ROOT) -> dict[str, Any]:
    """心跳段 2 與 audit 共用。`readings`＝{node: 現行 StructureReading}；`coverage` 沒給 → 叫不醒記 None。"""
    from thesis.memo_structure import disproof_items, memo_file_sha256

    lifecycle = load_lifecycle() if lifecycle is None else lifecycle
    expected: set[str] = set()
    mismatch: list[str] = []
    for tid, entry in lifecycle.items():
        if not isinstance(entry, dict) or not entry.get("memo") or entry.get("status") == "retired":
            continue
        memo = str(entry["memo"])
        try:
            text = (root / memo).read_text(encoding="utf-8")
        except OSError:
            continue
        expected |= {f"thesis:{memo}#{n}" for n in range(1, len(disproof_items(text)) + 1)}
        sidecar = _sidecar(root / memo)
        if sidecar and sidecar.get("disproof_conditions"):
            try:
                if memo_file_sha256(root / memo) != sidecar.get("memo_sha256"):
                    mismatch.append(str(tid))
            except OSError:
                mismatch.append(str(tid))
    v1_prose = 0
    for node, reading in (readings or {}).items():
        disproof = tuple(getattr(reading, "disproof", ()) or ())
        if str(getattr(reading, "record_version", "")).endswith("/v2"):
            expected |= {f"reading:{reading.reading_id}#{n}" for n in range(1, len(disproof) + 1)}
        else:
            v1_prose += 1
    semantic = [w for w in watches if w.get("kind") == ew.SEMANTIC_KIND]
    watching = [w for w in semantic if w.get("status") in ("active", "fired") and w.get("source_ref") in expected]
    touched = [w for w in semantic if _touched_pending(w)]
    covered = {w.get("source_ref") for w in watching} | {w.get("source_ref") for w in touched}
    return {
        "expected": len(expected),
        "watching": len(watching),
        "unreachable": (None if coverage is None else
                        sum(1 for w in watching if not ew.is_reachable(w, coverage))),
        "touched_pending": len(touched),
        "unwatched": len(expected - covered),
        "v1_prose_readings": v1_prose,
        "frozen_history": frozen_history,
        "thesis_sidecar_mismatch": mismatch,
    }


def current_readings() -> dict[str, Any]:
    """各節點現行讀圖（讀 ledger；經 alpha.providers）。"""
    from alpha.providers.structure_readings import known_nodes, read_reading_records
    from alpha.structure_reading import select_reading

    out: dict[str, Any] = {}
    for node in known_nodes():
        records, _errors = read_reading_records(node)
        reading = select_reading(records, today=date.today())
        if reading is not None:
            out[node] = reading
    return out


def frozen_history_count() -> int | None:
    """舊店（凍結唯讀）每家最新一份 coverage assessment 裡寫了反證的家數——**不盯**，只印數。"""
    try:
        from decision_lab.bootstrap import open_readonly_store
        from decision_lab.coverage_queries import latest_coverage_assessments

        store = open_readonly_store()
        try:
            rows = latest_coverage_assessments(store._conn)  # noqa: SLF001 — 唯讀連線
        finally:
            store.close()
    except Exception:  # noqa: BLE001 — 讀不到就是 None（沒算不是 0）
        return None
    return sum(1 for row in rows if str(row.get("disproof") or "").strip())


__all__ = ["current_readings", "disproof_counts", "frozen_history_count", "load_lifecycle", "memo_ref",
           "normalize", "reconcile_thesis_disproof"]
