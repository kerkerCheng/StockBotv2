"""敘事（短評 v2）的等待——**watch 歸屬的唯一 SSOT**、寫入即登記、換版與撤回收舊、重寫時逐條處置（Phase 3 Step 3.4）。

## 歸屬：以來源判，不以 `entities`

一家公司的 watch＝
- 本公司 thesis（lifecycle 裡 ticker 相同、非 retired）的 `thesis:<memo>#n`；
- 現行敘事 `rides[]` 各讀圖的 `reading:<id>#n`；
- 現行敘事 `disproof[].link_source_ref` 指向的來源（包括沒騎的讀圖，例：COHR 連結 InP 讀圖的反證）；
- 本公司任何一版敘事的 `brief:<brief_id>#n`；
- `wake_brief == 本公司`。

`entities` 記的是**條件牽涉誰**（AXT 的第 3 條反證 entities 是 JX／住友），拿它判歸屬會把別人的條件算成自己的。
**`candidate_state.watch_id` 本身不構成歸屬**——否則「watch 必須歸屬本檔」的驗證是循環定義（plan §5 第 8 點）。

候選狀態推導（3.6）、個股頁 downside（3.7）、成交收據（3.8）與敘事寫入端（`alpha/providers/briefs.py`）都呼叫這裡。

## 換版與撤回不吞掉「該重寫」的 watch

醒來（fired）、被判觸及、到期未判的敘事來源 watch 是**下一次重寫要處置的工作**（佇列段 `narrative_rewrite`）。
換版與撤回只收 active 的；其餘留著，下一次寫入必須在 `acknowledged_touched[]` 逐條處置（不列就拒收）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from engine_b import event_watch as ew
from engine_b.queue_segments import is_narrative_watch, narrative_rewrite_state


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _src(watch: Mapping[str, Any]) -> str:
    return str(watch.get("source_ref") or "")


def thesis_memos(ticker: str, lifecycle: Mapping[str, Any] | None) -> set[str]:
    """本公司 thesis 的 memo 路徑（lifecycle 以 ticker 對；retired 的不算）。"""
    wanted = str(ticker).strip().upper()
    return {str(e["memo"]) for e in (lifecycle or {}).values()
            if isinstance(e, Mapping) and e.get("memo") and str(e.get("ticker") or "").upper() == wanted
            and e.get("status") != "retired"}


def attributed_watches(company_id: str, ticker: str, *, watches: Sequence[Mapping[str, Any]],
                       lifecycle: Mapping[str, Any] | None, brief_ids: Iterable[str],
                       current_brief: Any = None) -> list[Mapping[str, Any]]:
    """這家公司的 watch（見模組 docstring 的五條來源）。`current_brief`：現行的 v2 敘事（`InvestorBrief`）或 None。"""
    memo_prefixes = tuple(f"thesis:{m}#" for m in thesis_memos(ticker, lifecycle))
    ride_prefixes = tuple(f"reading:{r.reading_id}#" for r in getattr(current_brief, "rides", ()) or ())
    links = {str(d.link_source_ref) for d in getattr(current_brief, "disproof", ()) or () if d.link_source_ref}
    brief_prefixes = tuple(f"brief:{b}#" for b in brief_ids)
    out = []
    for watch in watches:
        src = _src(watch)
        if (watch.get("wake_brief") == company_id
                or (memo_prefixes and src.startswith(memo_prefixes))
                or (ride_prefixes and src.startswith(ride_prefixes))
                or src in links
                or (brief_prefixes and src.startswith(brief_prefixes))):
            out.append(watch)
    return out


def narrative_watches_of(company_id: str, *, watches: Sequence[Mapping[str, Any]],
                         brief_ids: Iterable[str]) -> list[Mapping[str, Any]]:
    """本公司名下**所有版本**的敘事來源 watch（`brief:` 語意＋`wake_brief`）。"""
    prefixes = tuple(f"brief:{b}#" for b in brief_ids)
    return [w for w in watches if w.get("wake_brief") == company_id or (prefixes and _src(w).startswith(prefixes))]


def pending_rewrite(company_id: str, *, watches: Sequence[Mapping[str, Any]],
                    brief_ids: Iterable[str]) -> list[Mapping[str, Any]]:
    """本公司名下處於「該重寫」狀態（醒來／觸及／到期未判）的敘事來源 watch——下一次寫入必須逐條處置。"""
    return [w for w in narrative_watches_of(company_id, watches=watches, brief_ids=brief_ids)
            if narrative_rewrite_state(w) is not None]


def blocking_for_open(company_id: str, ticker: str, *, watches: Sequence[Mapping[str, Any]],
                      lifecycle: Mapping[str, Any] | None, brief_ids: Iterable[str],
                      current_brief: Any = None, acknowledged: Iterable[str] = ()) -> list[str]:
    """「可開」前提③：歸屬本檔的 watch 裡，還有沒有醒來待判、觸及待處置、到期未判的（敘事來源的已在本版處置的不算）。
    回傳人讀的理由清單（空＝沒有擋的）。"""
    acked = set(acknowledged)
    reasons = []
    for w in attributed_watches(company_id, ticker, watches=watches, lifecycle=lifecycle, brief_ids=brief_ids,
                                current_brief=current_brief):
        wid = str(w.get("watch_id"))
        if is_narrative_watch(w):
            state = narrative_rewrite_state(w)
            if state is not None and wid not in acked:
                reasons.append(f"{wid}（敘事來源，{state}，本版沒處置）")
            continue
        judgment = w.get("judgment") or {}
        if w.get("status") == "fired" and w.get("kind") == ew.SEMANTIC_KIND:
            reasons.append(f"{wid}（{_src(w)}：醒來待判）")
        elif judgment.get("touches") == "yes" and not judgment.get("handled"):
            reasons.append(f"{wid}（{_src(w)}：判定觸及、待處置）")
        elif w.get("status") == "expired" and not w.get("expiry_resolution") and w.get("kind") == ew.SEMANTIC_KIND:
            reasons.append(f"{wid}（{_src(w)}：到期未判）")
    return reasons


# ---------------------------------------------------------------------------
# 寫入後的 hook（由 `alpha/providers/briefs.py` 在 append 成功後呼叫；冪等）
# ---------------------------------------------------------------------------

def _close_active(data: dict[str, Any], prefixes: tuple[str, ...], note: str, summary: list[str]) -> None:
    for watch in data["watches"]:
        if not _src(watch).startswith(prefixes) or watch.get("status") != "active":
            continue
        watch["status"] = "consumed"
        watch["closed"] = {"at": _now(), "note": note}
        summary.append(str(watch["watch_id"]))


def _apply_ack(data: dict[str, Any], watch_id: str, disposition: str, note: str, brief_id: str) -> str:
    """把一條處置寫成那筆 watch 既有的收據：fired → consumed＋closed；觸及 → `judgment.handled`；到期 → `expiry_resolution`。"""
    watch = next((w for w in data["watches"] if w.get("watch_id") == watch_id), None)
    if watch is None:
        raise ew.EventWatchError(f"acknowledged_touched 指向不存在的 watch：{watch_id}")
    state = narrative_rewrite_state(watch)
    receipt = {"at": _now(), "kind": "narrative_ack", "disposition": disposition, "note": note, "brief_id": brief_id}
    if state == "fired":
        if disposition == "thesis_changed" and watch.get("kind") == ew.SEMANTIC_KIND:
            watch["judgment"] = {"at": receipt["at"], "touches": "yes", "note": note, "quote": note,
                                 "lead_id": (watch.get("woken_by") or {}).get("lead_id"),
                                 "handled": {"at": receipt["at"], "verb": disposition, "brief_id": brief_id}}
        watch["status"] = "consumed"
        watch["closed"] = receipt
    elif state == "touched":
        watch["judgment"]["handled"] = {"at": receipt["at"], "verb": disposition, "brief_id": brief_id, "note": note}
    elif state == "expired":
        ew.resolve_expiry(data, watch_id, {"kind": "narrative_rewritten", "disposition": disposition, "note": note,
                                           "brief_id": brief_id})
    else:
        raise ew.EventWatchError(f"{watch_id} 不在「該重寫」的狀態（{watch.get('status')}），不需要處置")
    return state


def register_brief_watches(record: Any, *, data: dict[str, Any], company_brief_ids: Iterable[str]) -> dict[str, list[str]]:
    """一筆敘事紀錄 append 成功之後：①換版／撤回收掉舊版還 active 的 `brief:` watch（只收 active）；
    ②`acknowledged_touched` 逐條寫處置收據；③這一版 `disproof[]` 沒有 `link_source_ref` 的每條登記一筆語意 watch
    （`brief:<brief_id>#<n>`；同鍵已存在就不重登）。`record` 是已解析的 `InvestorBrief`。"""
    summary: dict[str, list[str]] = {"registered": [], "consumed": [], "acknowledged": [], "linked": []}
    brief_id = str(record.brief_id)
    older = [b for b in company_brief_ids if b != brief_id]
    if record.retracted:
        if record.supersedes_id:
            _close_active(data, (f"brief:{record.supersedes_id}#",), f"retracted by {brief_id}", summary["consumed"])
        return summary
    if older:
        _close_active(data, tuple(f"brief:{b}#" for b in older), f"superseded by {brief_id}", summary["consumed"])
    for ack in record.acknowledged_touched:
        _apply_ack(data, ack.watch_id, ack.disposition, ack.note, brief_id)
        summary["acknowledged"].append(ack.watch_id)
    for index, item in enumerate(record.disproof, 1):
        if item.link_source_ref:
            summary["linked"].append(str(item.link_source_ref))
            continue
        ref = f"brief:{brief_id}#{index}"
        if any(_src(w) == ref for w in data["watches"]):
            continue
        watch = ew.add_watch(
            data, kind=ew.SEMANTIC_KIND, disproof_ref=ref, source_ref=ref, expires=item.expires.isoformat(),
            entities=list(item.entities), condition=item.condition, check_frequency=item.check_frequency,
            action_48h=item.action_48h, quote_locator=f"narrative disproof[{index}]（source {item.source}）",
            note=f"敘事 {brief_id}（{record.ticker}）的第 {index} 條反證")
        summary["registered"].append(str(watch["watch_id"]))
    return summary


__all__ = ["attributed_watches", "blocking_for_open", "narrative_watches_of", "pending_rewrite",
           "register_brief_watches", "thesis_memos"]
