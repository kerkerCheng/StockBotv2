"""反證登記與計數（Phase 1 Step 1.5；G7、G8、C3）——**等待只住 Event Watch registry**。

## thesis 的反證怎麼進 registry：`todo sync` 對帳，不掛在任何寫入動作上

memo 換版一律是手改 `thesis/lifecycle.json` 的 `memo`（沒有任何程式寫這一欄；`apply_proposal` 只寫
status／last_checked／next_check），所以「換 memo 的那一刻」沒有程式可以掛 hook。改成每次 `todo sync`
（daily ⑩ 與互動都會跑）對帳一次，**冪等**：

0. **lifecycle 讀不到 → 這一輪什麼都不動**（fail closed，R2-b 重審 RB-1：原本讀不到回 `{}`，所有 thesis 都被當成
   「memo 不是現行」，1.6 手動登記的 16 條被收掉且永遠不會重登）。memo 讀不到或「推翻」節解析不到 → 那一份不動。
1. **條件以文字認、不以位置認**（RB-2／NB2-14）：現行 memo「推翻」節的條目（`disproof_items`）是唯一的位置來源。
   指向這份 memo 的每一筆還在處理中的 watch（`_live`）以正規化文字對回現在的 index——位置變了就改 `source_ref`
   （留 `relinks` 歷史；registry 可重建，L10），文字不在了就收（active／fired → consume；到期未處置 → `source_superseded`）。
   這一步對結構化與手動登記一視同仁。
2. 現行 memo 的 sidecar 有 `disproof_conditions`、且 `memo_sha256` 等於 memo 以**同一算法**（CRLF→LF）重算的值
   → 每一條（以文字對到 memo 的 index）確保有一筆 `_live` 的語意 watch；沒有才登記。hash 不符 → 不登記、
   計數 `thesis_sidecar_mismatch`（fail closed，不猜）。單條登記失敗記進 `errors`，不拖垮整輪。
3. 還在處理中的語意 watch 指向**非現行** memo（換版）或 retired thesis → 收（同 1 的收法）。

`_live`＝在盯（active／fired）、到期待複查（expired 未處置）、觸及待處置（consumed 且判定觸及、未處置）。
已處置的到期（`source_superseded` 等）**不算**——memo A→B→A 換回來時要能重登（NB2-6）。

## 到期與觸及之後（Phase 1 Step 1.7，使用者 2026-09-24 選 B）

thesis 來源的條件到期**不鑄 `watch_decision`**：它以理由列進那份 thesis 的複查項目（`thesis_lifecycle`，同一 thesis
只會有一筆）；使用者對那一筆 `go`／`drop` 時 `after_thesis_review` 把它名下到期的條件續到下一個核查點、把判定觸及的
標 handled 並（memo 仍現行時）開一筆新的續盯——結構化與手動登記的行為一致（NB2-5）。要放棄條件＝改寫 memo。
讀圖來源的條件到期列進該節點的重讀理由，重讀（新讀圖取代）時收掉換新。

## 計數（心跳段 2、audit 共用）——以**條件**為單位，四格加總＝預期（NB2-4）

預期條件＝非 retired thesis 現行 memo「推翻」節的條目＋各節點現行 **v2** 讀圖的 `disproof[]`，以（來源、正規化文字）認。
每個條件落在恰一格，優先序：**觸及待處置**（A5，不得併進未盯）＞**到期待複查**（等 thesis 複查或節點重讀）＞
**在盯**（其中**叫不醒**＝沒有一手來源會產出帶它實體的 lead）＞**未盯**。不在預期裡的觸及另計**孤兒觸及**。
另報 v1 讀圖散文份數（不可機械數）與凍結歷史（舊店 `coverage_assessments` 的反證，不盯）。lifecycle 讀不到 → 標
`lifecycle_unreadable`，thesis 那一半沒算（不是 0）。
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


def load_lifecycle(path: Path = LIFECYCLE) -> dict[str, Any] | None:
    """讀 lifecycle；**讀不到或不是 object 回 None**（不是 `{}`——空的與壞掉的是兩件事，RB-1）。"""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


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


def _interval(entry: Mapping[str, Any]) -> int:
    interval = entry.get("check_interval_days")
    return int(interval) if isinstance(interval, (int, float)) and not isinstance(interval, bool) and interval > 0 else 90


def _default_expires(entry: Mapping[str, Any], condition: str, *, today: date) -> str:
    """結構化條目沒寫 expires 時：下一個核查點＋一個核查週期（≈ 今天＋兩個週期），且不早於條件自己寫的日期。"""
    candidate = today + timedelta(days=2 * _interval(entry))
    written = ew.condition_dates(condition)
    if written and max(written) >= candidate:
        candidate = max(written) + timedelta(days=30)
    return candidate.isoformat()


def review_horizon(entry: Mapping[str, Any], *, today: date) -> date:
    """thesis 複查之後條件續盯到哪天：下一個核查點（沒寫或已過就用今天）＋一個核查週期。"""
    try:
        nxt = date.fromisoformat(str(entry.get("next_check"))[:10])
    except ValueError:
        nxt = today
    return max(nxt, today) + timedelta(days=_interval(entry))


def rearm_until(entry: Mapping[str, Any], condition: str, *, today: date) -> date:
    """續盯到哪天：`review_horizon`，且不早於條件自己寫的完整日期＋30 天（同 `_default_expires` 的規則；NB3-1）。"""
    horizon = review_horizon(entry, today=today)
    written = ew.condition_dates(condition)
    return max([horizon, *(d + timedelta(days=30) for d in written)])


def _touched_pending(watch: Mapping[str, Any]) -> bool:
    judgment = watch.get("judgment") or {}
    return judgment.get("touches") == "yes" and not judgment.get("handled")


def _live(watch: Mapping[str, Any]) -> bool:
    """還在處理中：在盯、到期待複查（expired 未處置）、觸及待處置。已處置的到期不算（NB2-6）。"""
    status = watch.get("status")
    if status in ("active", "fired"):
        return True
    if status == "expired":
        return not watch.get("expiry_resolution")
    return status == "consumed" and _touched_pending(watch)


def _relink(watch: dict[str, Any], ref: str) -> None:
    watch["relinks"] = [*(watch.get("relinks") or []), {"at": _now(), "from": watch.get("source_ref"), "to": ref}]
    watch["source_ref"] = ref
    watch["disproof_ref"] = ref


def _retire_watch(data: dict[str, Any], watch: dict[str, Any], note: str) -> bool:
    """來源不再有這個條件：active／fired → consume；到期未處置 → `source_superseded`。觸及待處置的不動（複查項目接著）。"""
    if watch.get("status") in ("active", "fired"):
        _close(watch, note)
        return True
    if watch.get("status") == "expired" and not watch.get("expiry_resolution"):
        ew.resolve_expiry(data, watch["watch_id"], {"kind": "source_superseded", "note": note})
        return True
    return False


def reconcile_thesis_disproof(data: dict[str, Any], *, lifecycle: Mapping[str, Any] | None = None,
                              root: Path = ROOT, today: date | None = None) -> dict[str, Any]:
    """冪等對帳；只改 `data`（呼叫端存檔）。見模組 docstring 0–3。"""
    from thesis.memo_structure import disproof_items, memo_file_sha256

    lifecycle = load_lifecycle() if lifecycle is None else lifecycle
    today = today or datetime.now(timezone.utc).date()
    summary: dict[str, Any] = {"registered": [], "consumed": [], "relinked": [], "sidecar_mismatch": [],
                               "no_structured": [], "errors": [], "lifecycle_unreadable": False}
    if lifecycle is None:
        summary["lifecycle_unreadable"] = True
        summary["errors"].append({"ref": "thesis/lifecycle.json",
                                  "error": "lifecycle 讀不到——本輪不收、不登記任何 thesis 反證（fail closed）"})
        return summary
    current: dict[str, str] = {}
    retired: dict[str, str] = {}
    semantic = [w for w in data["watches"] if w.get("kind") == ew.SEMANTIC_KIND]
    for tid, entry in lifecycle.items():
        if not isinstance(entry, dict) or not entry.get("memo"):
            continue
        memo = str(entry["memo"])
        if entry.get("status") == "retired":
            retired[memo] = str(tid)
            continue
        current[memo] = str(tid)
        memo_path = root / memo
        try:
            items = [normalize(x) for x in disproof_items(memo_path.read_text(encoding="utf-8"))]
        except OSError:
            summary["errors"].append({"ref": f"thesis:{memo}", "error": "memo 讀不到——本輪不動這份 memo 的等待"})
            continue
        if not items:
            summary["errors"].append({"ref": f"thesis:{memo}",
                                      "error": "memo「推翻」節解析不到條目——本輪不動這份 memo 的等待"})
            continue
        # 1. 條件以文字認位置（對結構化與手動登記一視同仁）
        for watch in semantic:
            if memo_ref(watch.get("source_ref") or "") != memo or not _live(watch):
                continue
            text = normalize(watch.get("condition"))
            if text in items:
                ref = f"thesis:{memo}#{items.index(text) + 1}"
                if watch.get("source_ref") != ref:
                    _relink(watch, ref)
                    summary["relinked"].append(watch["watch_id"])
            elif _retire_watch(data, watch, "memo 原地重產／改寫，條件已不在「推翻」節"):
                summary["consumed"].append(watch["watch_id"])
        # 2. 結構化反證：沒有 _live 的才登記
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
        for cond in conditions:
            if not isinstance(cond, dict):
                continue
            text = normalize(cond.get("condition"))
            if text not in items:
                summary["errors"].append({"ref": f"thesis:{memo}",
                                          "error": f"sidecar 條件不在 memo「推翻」節：{text[:40]}"})
                continue
            ref = f"thesis:{memo}#{items.index(text) + 1}"
            if any(_live(w) and memo_ref(w.get("source_ref") or "") == memo and normalize(w.get("condition")) == text
                   for w in data["watches"] if w.get("kind") == ew.SEMANTIC_KIND):
                continue
            try:
                watch = ew.add_watch(
                    data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref,
                    expires=str(cond.get("expires") or _default_expires(entry, str(cond.get("condition")), today=today)),
                    entities=list(cond.get("entities") or ()), condition=str(cond.get("condition")),
                    check_frequency=str(cond.get("check_frequency")), action_48h=str(cond.get("action_48h")),
                    quote_locator="memo「推翻」那一節", note=f"todo sync 對帳：thesis {tid} 現行 memo 的第 {ref.rsplit('#', 1)[1]} 條",
                    today=today,
                )
            except ew.EventWatchError as exc:
                # 一條壞掉不得拖垮整輪對帳（R2-b B1-4）
                summary["errors"].append({"ref": ref, "error": str(exc)})
                continue
            summary["registered"].append(watch["watch_id"])
    # 3. 換版／retire
    for watch in semantic:
        memo = memo_ref(watch.get("source_ref") or "")
        if memo is None or memo in current:
            continue
        note = "thesis retired" if memo in retired else "memo 已不是 lifecycle 的現行 memo（superseded）"
        if _retire_watch(data, watch, note):
            summary["consumed"].append(watch["watch_id"])
    return summary


def after_thesis_review(data: dict[str, Any], watch_ids: Sequence[str], *, n: int | None, verb: str, stamp: str,
                        lifecycle: Mapping[str, Any] | None = None, today: date | None = None) -> dict[str, list[str]]:
    """`thesis_lifecycle` 那一筆 go／drop 之後（Phase 1 Step 1.7 設計 B；C3）——只改 `data`，呼叫端存檔。

    - 判定觸及、未處置 → 標 `judgment.handled`；memo 仍現行且同條件沒有別的 `_live` watch → 開一筆新的續盯
      （到期＝`review_horizon`；結構化與手動登記一致，NB2-5）。
    - 到期未處置 → 續到 `review_horizon`（同一筆 watch 回 active、歷史附加）。memo 已不是現行 → 記 `source_superseded`。
    - 還在等（active／fired）而被列進來的（排程到期時一併帶上的，NB3-3）→ 延到 `rearm_until`（只延不縮）。
    lifecycle 讀不到 → **什麼都不做**（觸及也不標 handled：標了就不會再列出，續盯又做不了——那一條會從「在盯」掉到
    「未盯」；留著，下一筆複查項目會再列出，多問一次；R2-b 第三輪 NB3-1）。"""
    lifecycle = load_lifecycle() if lifecycle is None else lifecycle
    today = today or datetime.now(timezone.utc).date()
    out: dict[str, list[str]] = {"handled": [], "rewatched": [], "renewed": [], "extended": [], "superseded": [],
                                 "errors": []}
    ids = set(watch_ids)
    if lifecycle is None:
        out["errors"].append("lifecycle 讀不到——這一筆複查的反證本輪不處理，下一筆複查項目會再列出")
        return out
    by_memo = {str(e.get("memo")): e for e in lifecycle.values()
               if isinstance(e, dict) and e.get("memo") and e.get("status") != "retired"}
    for watch in list(data["watches"]):
        if watch.get("watch_id") not in ids or watch.get("kind") != ew.SEMANTIC_KIND:
            continue
        memo = memo_ref(watch.get("source_ref") or "")
        entry = by_memo.get(memo) if memo else None
        if _touched_pending(watch):
            watch["judgment"]["handled"] = {"n": n, "verb": verb, "at": stamp}
            out["handled"].append(watch["watch_id"])
            if entry is None:
                continue
            text = normalize(watch.get("condition"))
            if any(_live(w) and w is not watch and memo_ref(w.get("source_ref") or "") == memo
                   and normalize(w.get("condition")) == text for w in data["watches"]
                   if w.get("kind") == ew.SEMANTIC_KIND):
                continue
            try:
                new = ew.add_watch(
                    data, kind=ew.SEMANTIC_KIND, disproof_ref=watch["source_ref"], source_ref=watch["source_ref"],
                    expires=rearm_until(entry, str(watch.get("condition")), today=today).isoformat(),
                    entities=list(watch.get("entities") or ()),
                    condition=str(watch.get("condition")), check_frequency=str(watch.get("check_frequency")),
                    action_48h=str(watch.get("action_48h")), quote_locator=str(watch.get("quote_locator") or ""),
                    node=str(watch.get("node") or ""), note=f"thesis 複查（[{n}] {verb}）後續盯；原 {watch['watch_id']}",
                    today=today)
                out["rewatched"].append(new["watch_id"])
            except ew.EventWatchError as exc:
                out["errors"].append(f"{watch['watch_id']}：{exc}")
        elif watch.get("status") in ("active", "fired"):
            if entry is not None:
                ew.extend(data, watch["watch_id"], n=n, note=f"thesis 複查（[{n}] {verb}）一併續盯",
                          until=rearm_until(entry, str(watch.get("condition")), today=today).isoformat())
                out["extended"].append(watch["watch_id"])
        elif watch.get("status") == "expired" and not watch.get("expiry_resolution"):
            if entry is None:
                ew.resolve_expiry(data, watch["watch_id"], {"kind": "source_superseded",
                                                            "note": "thesis 複查時 memo 已不是現行"})
                out["superseded"].append(watch["watch_id"])
                continue
            try:
                ew.renew(data, watch["watch_id"], n=n,
                         until=rearm_until(entry, str(watch.get("condition")), today=today).isoformat())
                out["renewed"].append(watch["watch_id"])
            except ew.EventWatchError as exc:
                out["errors"].append(f"{watch['watch_id']}：{exc}")
    return out


def source_is_current(watch: Mapping[str, Any], *, lifecycle: Mapping[str, Any] | None = None,
                      readings: Mapping[str, Any] | None = None) -> bool:
    """語意 watch 的來源還是不是現行（NB-4、NB2-1）。讀不到 lifecycle → False（fail closed：不能確認就不放行）。

    thesis 來源：memo 是某個非 retired thesis 的現行 memo。讀圖來源：reading_id 是該節點現行讀圖。其餘（假設型）→ True。"""
    ref = str(watch.get("source_ref") or "")
    memo = memo_ref(ref)
    if memo is not None:
        lifecycle = load_lifecycle() if lifecycle is None else lifecycle
        if lifecycle is None:
            return False
        return any(isinstance(e, dict) and str(e.get("memo")) == memo and e.get("status") != "retired"
                   for e in lifecycle.values())
    if ref.startswith("reading:"):
        reading_id = ref[len("reading:"):].split("#", 1)[0]
        readings = current_readings() if readings is None else readings
        return any(getattr(r, "reading_id", None) == reading_id for r in readings.values())
    return True


def _close(watch: dict[str, Any], note: str) -> None:
    watch["status"] = "consumed"
    watch["closed"] = {"at": _now(), "note": note}


# ---------------------------------------------------------------------------
# 計數
# ---------------------------------------------------------------------------

_PRIORITY = {"touched": 3, "expired": 2, "watching": 1}


def disproof_counts(watches: Sequence[Mapping[str, Any]], *, lifecycle: Mapping[str, Any] | None = None,
                    readings: Mapping[str, Any] | None = None, coverage: frozenset[str] | None = None,
                    frozen_history: int | None = None, root: Path = ROOT) -> dict[str, Any]:
    """心跳段 2 與 audit 共用。以條件為單位（見模組 docstring）；`coverage` 沒給 → 叫不醒記 None。"""
    from thesis.memo_structure import disproof_items, memo_file_sha256

    lifecycle = load_lifecycle() if lifecycle is None else lifecycle
    expected: dict[tuple[str, str], str] = {}   # (來源, 正規化文字) → 它在等哪裡
    mismatch: list[str] = []
    unreadable_memos: list[str] = []   # 讀不到或「推翻」節解析不到——它的條件沒算進預期（不是 0；NB3-8）
    for tid, entry in (lifecycle or {}).items():
        if not isinstance(entry, dict) or not entry.get("memo") or entry.get("status") == "retired":
            continue
        memo = str(entry["memo"])
        try:
            text = (root / memo).read_text(encoding="utf-8")
        except OSError:
            unreadable_memos.append(str(tid))
            continue
        items = disproof_items(text)
        if not items:
            unreadable_memos.append(str(tid))
        for item in items:
            expected[(f"thesis:{memo}", normalize(item))] = f"thesis {tid} 複查"
        sidecar = _sidecar(root / memo)
        if sidecar and sidecar.get("disproof_conditions"):
            try:
                if memo_file_sha256(root / memo) != sidecar.get("memo_sha256"):
                    mismatch.append(str(tid))
            except OSError:
                mismatch.append(str(tid))
    v1_prose = 0
    for node, reading in (readings or {}).items():
        if str(getattr(reading, "record_version", "")).endswith("/v2"):
            for entry in tuple(getattr(reading, "disproof", ()) or ()):
                expected[(f"reading:{reading.reading_id}", normalize(getattr(entry, "condition", "")))] = f"{node} 重讀"
        else:
            v1_prose += 1
    state: dict[tuple[str, str], tuple[str, Mapping[str, Any]]] = {}
    orphan_touched = 0
    for watch in watches:
        if watch.get("kind") != ew.SEMANTIC_KIND:
            continue
        if _touched_pending(watch):
            cat = "touched"
        elif watch.get("status") == "expired" and not watch.get("expiry_resolution"):
            cat = "expired"
        elif watch.get("status") in ("active", "fired"):
            cat = "watching"
        else:
            continue
        key = (str(watch.get("source_ref") or "").split("#", 1)[0], normalize(watch.get("condition")))
        if lifecycle is None and key[0].startswith("thesis:"):
            continue   # lifecycle 讀不到時 thesis 那一半是「沒算」，不是孤兒（NB3-8）
        if key not in expected:
            orphan_touched += cat == "touched"
            continue
        if _PRIORITY[cat] > _PRIORITY.get(state.get(key, ("", {}))[0], 0):
            state[key] = (cat, watch)
    by_cat = {cat: [(key, w) for key, (c, w) in state.items() if c == cat] for cat in _PRIORITY}
    return {
        "expected": len(expected),
        "watching": len(by_cat["watching"]),
        "unreachable": (None if coverage is None else
                        sum(1 for _key, w in by_cat["watching"] if not ew.is_reachable(w, coverage))),
        "touched_pending": len(by_cat["touched"]),
        "touched_waits_on": sorted({expected[key] for key, _w in by_cat["touched"]}),
        "expired_pending": len(by_cat["expired"]),
        "unwatched": len(expected) - len(state),
        "orphan_touched": orphan_touched,
        "v1_prose_readings": v1_prose,
        "frozen_history": frozen_history,
        "thesis_sidecar_mismatch": mismatch,
        "memo_unreadable": unreadable_memos,
        "lifecycle_unreadable": lifecycle is None,
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


__all__ = ["after_thesis_review", "current_readings", "disproof_counts", "frozen_history_count", "load_lifecycle",
           "memo_ref", "normalize", "reconcile_thesis_disproof", "review_horizon", "source_is_current"]
