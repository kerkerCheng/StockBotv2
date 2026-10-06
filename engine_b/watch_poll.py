"""T2 輪詢進 daily（2026-10-06 使用者指示）——⑩d `prepare`、⑩g `apply`；互動 session 用 `queue` 看、`judge` 判。

為什麼存在：T2（等待登記的主動輪詢）在 Phase 1 Step 1.2a 移出 daily、改成「互動 session 跑 `event_watch sweep`」，
之後沒有任何 skill 叫人跑、心跳也不印——09-21 之後兩週沒人輪詢（Phase 7 cases.md），10-05 補跑時兩條在等的一手早已
出現（NVDA 擔保 8-K 是 08-17，那則線索等了 49 天才接回）。可輪詢的等待裡多數已 stalled（被動層不會再叫醒，只剩它或到期）。

形狀照外部雷達（`engine_b/radar.py`）與語意預篩（`engine_b/semantic_prescreen.py`）：

- **prepare**：挑法與互動 `sweep` 同一份（`event_watch.sweep_due`；每日上限 `sweep_budget_per_run`）。每條只帶等待本身的
  題目——在等什麼、查詢提示、要對照的事實、實體名、原本在追的那則線索的標題、已掛過的網址。
  **不讀 Sheet、持股、NAV、私人路徑**（`tests/test_watch_poll.py` 以哨兵證明）。
- **⑩e**：`claude -p` 只開 WebSearch——與雷達同一組 argv、能力期望與搜尋結果收集器（`crons/llm_step.py`，不另開一份）。
- **apply**：程式驗證後寫，每一條拒收都有理由、照數（INV-3）。歸屬只認**負責這條等待的那一次呼叫**（daily 每次呼叫一個
  收集器、逐次寫進 `search_calls`；預設每條一次呼叫——2026-10-06 R2 條件 1：整輪共用時 B 照抄 A 的查詢詞與網址也會過）：
  ①回答出自那次呼叫；②回報的查詢詞至少一個是那次呼叫真的送出的，否則這條**不算查過**、明天再查；③網址必須在那次呼叫的
  搜尋結果裡；④同一條等待已掛過的網址不重複；⑤每條每輪最多 `poll_hits_per_watch` 則。沒有逐次紀錄的結果檔不套用。
  查過的記 `poll.last_checked`；命中只追加進 `poll.hits`——
  **不改 status、不叫醒、不寫 lead**（判定只在互動，同預篩的「只標旗不判定」，G7）。
- **judge**（互動）：觸及＝叫醒那條等待（`woken_by.kind=poll_hit`），之後照它的喚醒目標走既有的路；無關＝只記判定。

收據 `library/private/heartbeat/watch_poll_<日期>.json`（收／拒與理由）。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "library" / "private" / "heartbeat"
BATCH_SCHEMA = "watch-poll-batch-v1"
RECEIPT_SCHEMA = "watch-poll-receipt-v1"
#: 拒收理由（封閉字彙；收據與心跳照這幾個字數）。
REJECT_REASONS: Mapping[str, str] = {
    "invalid": "欄位不合法（watch_id、網址或摘要是空的、型別不對）",
    "not_in_batch": "watch_id 不在本輪批次",
    "duplicate_answer": "同一條等待回了不只一次（全部不收）",
    "not_active": "等待在套用前已不是 active",
    "wrong_call": "回答不是出自負責這條等待的那一次呼叫",
    "not_searched": "回報的查詢詞沒有一個是負責這條的那次呼叫真的送出的——這條不算查過，明天再查",
    "url_not_in_search": "網址不在負責這條的那次呼叫的搜尋結果裡",
    "duplicate_hit": "這條等待已經掛過這個網址",
    "over_cap": "超過每條等待每輪的命中上限",
}
#: 原本在追的那則線索的標題塞進 prompt 的長度上限（脈絡，不是證據）。
LEAD_TITLE_MAX = 160


def _entity_label(registry: Any, entity: str) -> str:
    company = registry.company(entity) if str(entity).startswith("co:") else None
    name = getattr(company, "display_name", None) if company is not None else None
    return f"{name}（{entity}）" if name else str(entity)


def _allowed_urls(record: Mapping[str, Any], leads_mod: Any) -> tuple[dict[str, str], dict[str, str]]:
    """一次呼叫的搜尋結果 → (正規化網址 → 原網址, 正規化網址 → 搜尋結果的標題)。正規化不了的不進允許清單。"""
    allowed: dict[str, str] = {}
    titles: dict[str, str] = {}
    raw_titles = record.get("titles") or {}
    for url in record.get("urls") or ():
        try:
            key = leads_mod.normalize_url(str(url))
        except ValueError:
            continue
        allowed[key] = str(url)
        if str(raw_titles.get(url) or "").strip():
            titles[key] = str(raw_titles[url]).strip()
    return allowed, titles


def _query_key(text: Any) -> str:
    """查詢詞比對只忽略大小寫與空白差異——模型照抄時多一個空格不該讓「真的查過」變成「沒查」。"""
    return " ".join(str(text or "").split()).casefold()


# ---------------------------------------------------------------------------
# prepare（⑩d）
# ---------------------------------------------------------------------------

def build_items(data: Mapping[str, Any], *, registry: Any, leads_store: Mapping[str, Any], today: date,
                max_items: int) -> list[dict[str, Any]]:
    """LLM 要的那一份資料：每條到期該查的等待一筆。**沒有任何持股、部位、私人路徑的欄位**。"""
    from engine_b import event_watch as ew

    items = []
    for watch in ew.sweep_due(data, today=today):
        poll = watch.get("poll") or {}
        lead = leads_store.get(str(watch.get("wake_lead") or "")) or {}
        items.append({
            "watch_id": str(watch["watch_id"]),
            "waiting_for": ew.watch_detail(watch),
            "query_hint": str(poll.get("query_hint") or ""),
            "fact": str(watch.get("fact") or ""),
            "entities": [_entity_label(registry, e) for e in watch.get("entities") or ()],
            "tracing_lead_title": " ".join(str(lead.get("title") or "").split())[:LEAD_TITLE_MAX],
            "watching_since": str(watch.get("created_at") or "")[:10],
            "last_checked": poll.get("last_checked"),
            "already_seen_urls": [str(h["url"]) for h in poll.get("hits") or ()
                                  if isinstance(h, Mapping) and h.get("url")],
            "max_items": int(max_items),
        })
    return items


def prepare(run_id: str, out: Path, *, today: date | None = None, data: Mapping[str, Any] | None = None,
            registry: Any = None, leads_store: Mapping[str, Any] | None = None) -> dict[str, Any]:
    from engine_b import event_watch as ew
    from identity.registry import get_registry

    today = today or ew._today()
    data = data if data is not None else ew.load_watches()
    cfg = ew.load_config()
    lead_note = None
    if leads_store is None:
        from engine_b import leads

        try:
            leads_store = leads.load()["leads"]
        except Exception as exc:  # noqa: BLE001 — 線索讀不到只少一格脈絡，照實記，不擋輪詢
            leads_store, lead_note = {}, f"{type(exc).__name__}: {exc}"
    items = build_items(data, registry=registry or get_registry(), leads_store=leads_store, today=today,
                        max_items=int(cfg["poll_hits_per_watch"]))
    status = ew.t2_status(data, today=today)
    counts = {"enabled": status["enabled"], "eligible": status["eligible"], "due": status["due"],
              "selected": len(items), "not_in_batch": max(0, status["due"] - len(items)),
              "budget": status["budget"], "hits_per_watch": int(cfg["poll_hits_per_watch"])}
    if lead_note:
        counts["leads_unreadable"] = lead_note
    envelope = {"schema": BATCH_SCHEMA, "run_id": run_id, "run_date": today.isoformat(),
                "hits_per_watch": int(cfg["poll_hits_per_watch"]), "items": items, "counts": counts}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return counts


# ---------------------------------------------------------------------------
# apply（⑩g）
# ---------------------------------------------------------------------------

def apply(result_path: Path, batch_path: Path, run_id: str, *, watches_path: Path | None = None,
          receipt_dir: Path = OUT_DIR, today: date | None = None) -> dict[str, Any]:
    """驗證後只寫 `poll.last_checked` 與 `poll.hits`，回傳 `{summary, rejected}`（daily 的套用步驟收最後一行 JSON 的第一行）。"""
    from engine_b import event_watch as ew
    from engine_b import leads
    # 模型說的日期怎麼讀，與雷達同一份：讀不懂或晚於今天一律 None，不拿今天冒充（INV-6；L16）
    from engine_b.radar import _published as claimed_date

    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    batch = json.loads(Path(batch_path).read_text(encoding="utf-8"))
    if result.get("run_id") != run_id or batch.get("run_id") != run_id:
        raise ValueError("結果檔或批次檔的 run_id 不是這一輪的——不套用舊檔")
    today = today or ew._today()
    cap = int(batch.get("hits_per_watch") or 0)
    in_batch = {str(i.get("watch_id")): i for i in batch.get("items") or () if isinstance(i, Mapping)}
    search = result.get("search") or {}
    # ⚠ 歸屬只認「負責這條等待的那一次呼叫」（2026-10-06 R2 條件 1）：整輪的聯集只驗得出「今天有沒有人搜過這個字串」，
    # B 照抄 A 的查詢詞與網址也會過。沒有逐次紀錄就不套用（fail closed）。
    calls = result.get("search_calls")
    if not isinstance(calls, list):
        raise ValueError("結果檔沒有逐次呼叫的搜尋紀錄（search_calls）——驗不出哪一筆是為了哪一條等待搜的，不套用")
    scopes: dict[str, dict[str, Any]] = {}
    for call in calls:
        if not isinstance(call, Mapping):
            continue
        allowed, titles = _allowed_urls(call, leads)
        scope = {"issued": {_query_key(q) for q in call.get("queries") or ()}, "allowed": allowed,
                 "titles": titles, "session_id": call.get("session_id")}
        for watch_id in call.get("items") or ():
            scopes[str(watch_id)] = scope
    path = Path(watches_path) if watches_path else ew.WATCHES_PATH
    data = ew.load_watches(path)
    by_id = {str(w.get("watch_id")): w for w in data["watches"]}

    answers = [a for a in result.get("results") or ()]
    times_answered = Counter(str(a.get("watch_id") or "").strip() for a in answers if isinstance(a, Mapping))
    counts = {"answered": 0, "checked": 0, "claimed_found": 0, "watches_with_new_hits": 0, "hits_new": 0,
              "published_unparsed": 0, **{k: 0 for k in REJECT_REASONS}, "unanswered": 0}
    rejected: list[dict[str, Any]] = []
    written: list[dict[str, Any]] = []
    checked: list[str] = []
    answered: set[str] = set()

    def reject(reason: str, watch_id: str | None, url: str | None = None) -> None:
        counts[reason] += 1
        rejected.append({"watch_id": watch_id, "url": url, "reason": reason, "detail": REJECT_REASONS[reason]})

    for answer in answers:
        if not isinstance(answer, Mapping):
            reject("invalid", None)
            continue
        watch_id = str(answer.get("watch_id") or "").strip()
        if not watch_id:
            reject("invalid", None)
            continue
        if watch_id not in in_batch:
            reject("not_in_batch", watch_id)
            continue
        answered.add(watch_id)
        if times_answered[watch_id] > 1:
            reject("duplicate_answer", watch_id)
            continue
        counts["answered"] += 1
        watch = by_id.get(watch_id)
        if watch is None or watch.get("status") != "active":
            reject("not_active", watch_id)
            continue
        scope = scopes.get(watch_id)
        if scope is None:                    # 批次裡有它、卻沒有任何一次呼叫負責它——沒有東西可以證明它被查過
            reject("not_searched", watch_id)
            continue
        if scope["session_id"] and answer.get("session_id") and answer.get("session_id") != scope["session_id"]:
            reject("wrong_call", watch_id)
            continue
        queries = [q for q in answer.get("queries") or () if isinstance(q, str) and q.strip()]
        if not any(_query_key(q) in scope["issued"] for q in queries):
            reject("not_searched", watch_id)
            continue
        ew.mark_checked(data, watch_id, today=today)
        checked.append(watch_id)
        counts["checked"] += 1
        counts["claimed_found"] += int(answer.get("found") is True)
        seen: set[str] = set()
        for hit in (watch.get("poll") or {}).get("hits") or ():
            try:
                seen.add(leads.normalize_url(str((hit or {}).get("url") or "")))
            except ValueError:
                continue
        new_here = 0
        for item in answer.get("items") or ():
            url = str((item or {}).get("url") or "").strip() if isinstance(item, Mapping) else ""
            summary = str(item.get("summary") or "").strip() if isinstance(item, Mapping) else ""
            if not url or not summary:
                reject("invalid", watch_id, url or None)
                continue
            try:
                key = leads.normalize_url(url)
            except ValueError:
                reject("invalid", watch_id, url)
                continue
            if key not in scope["allowed"]:
                reject("url_not_in_search", watch_id, url)
                continue
            if key in seen:
                reject("duplicate_hit", watch_id, url)
                continue
            if new_here >= cap:
                reject("over_cap", watch_id, url)
                continue
            claimed, unparsed = claimed_date(item.get("published_at"), today=today)
            counts["published_unparsed"] += int(unparsed)
            title = scope["titles"].get(key)
            ew.record_poll_hit(data, watch_id, url=scope["allowed"][key],
                               title=title or str(item.get("title") or "").strip(),
                               summary=summary, why=str(item.get("why") or "").strip(),
                               claimed_published_at=claimed, run_id=run_id,
                               session_id=answer.get("session_id"))
            seen.add(key)
            new_here += 1
            counts["hits_new"] += 1
            written.append({"watch_id": watch_id, "url": scope["allowed"][key], "title": title or None,
                            "claimed_published_at": claimed})
        counts["watches_with_new_hits"] += int(bool(new_here))
    counts["unanswered"] = len(set(in_batch) - answered)
    if checked:
        ew.save_watches(data, path)
    summary = {"batch": len(in_batch), **counts, "rejected": len(rejected), "searches": search.get("searches"),
               "search_urls": len(search.get("urls") or ()), "hits_per_watch": cap, "calls": len(calls),
               # 一次呼叫負責幾條（>1 時同一次呼叫裡的照抄驗不出來；預設 1，見 config/daily_routine.json）
               "max_watches_per_call": max((len(c.get("items") or ()) for c in calls if isinstance(c, Mapping)),
                                           default=0)}
    receipt = {"schema": RECEIPT_SCHEMA, "run_id": run_id, "date": today.isoformat(), "summary": summary,
               "checked": checked, "hits": written, "rejected": rejected,
               "unanswered": sorted(set(in_batch) - answered), "queries": list(search.get("queries") or ()),
               "sessions": list(result.get("sessions") or ())}
    receipt_dir = Path(receipt_dir)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / f"watch_poll_{today.isoformat()}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"summary": summary, "rejected": rejected[:30]}


# ---------------------------------------------------------------------------
# 互動：queue／judge
# ---------------------------------------------------------------------------

def queue_lines(data: Mapping[str, Any], leads_store: Mapping[str, Any]) -> list[str]:
    """待判定的 T2 命中，依最早命中時間排（**不是排序權**，只是讀的順序）。"""
    from engine_b import event_watch as ew

    rows = []
    for watch in data["watches"]:
        hits = ew.pending_hits(watch)
        if hits:
            rows.append((min(str(h.get("at") or "") for h in hits), watch, hits))
    if not rows:
        return ["（沒有待判定的 T2 命中）"]
    rows.sort(key=lambda row: row[0])
    lines: list[str] = []
    for _, watch, hits in rows:
        wid = str(watch["watch_id"])
        lines.append(f"{wid}｜{ew.watch_detail(watch)}｜觸及會叫醒：{ew.wake_target(watch)['label']}"
                     f"｜expires {watch.get('expires')}")
        hint = (watch.get("poll") or {}).get("query_hint")
        if hint:
            lines.append(f"  查詢提示：{hint}")
        if watch.get("fact"):
            lines.append(f"  要對照的事實：{watch['fact']}")
        lead = leads_store.get(str(watch.get("wake_lead") or "")) or {}
        if lead:
            lines.append(f"  原本在追：{lead.get('title') or watch.get('wake_lead')}｜{lead.get('url') or '—'}")
        for hit in hits:
            lines.append(f"  命中 {str(hit.get('at') or '')[:10]}｜{hit.get('title') or '（搜尋結果沒有標題）'}")
            lines.append(f"    {hit.get('url')}")
            dated = (f"｜文件日期（模型說的）：{hit['claimed_published_at']}"
                     if hit.get("claimed_published_at") else "")
            lines.append(f"    模型摘要（不是原文）：{hit.get('summary')}{dated}")
            if hit.get("why"):
                lines.append(f"    為什麼可能相關（模型說的）：{hit['why']}")
        lines.append(f"  判定（先讀原文再判）：python -m engine_b.watch_poll judge {wid} --url <網址> "
                     "--touches yes|no --note \"…\" [--quote \"文件逐字\"]")
    return lines


# ---------------------------------------------------------------------------
# CLI（daily 的 ⑩d／⑩g 呼叫；互動 session 用 queue／judge；試跑加 --watches 指到副本、--today 快轉）
# ---------------------------------------------------------------------------

def _day(raw: str | None) -> date | None:
    return date.fromisoformat(raw) if raw else None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m engine_b.watch_poll",
                                     description="T2 輪詢：daily 查、只掛命中；判定在互動")
    sub = parser.add_subparsers(dest="command", required=True)
    p_prep = sub.add_parser("prepare", help="daily ⑩d：挑到期該查的等待、寫輪詢批次（不讀持股）")
    p_prep.add_argument("--run-id", required=True)
    p_prep.add_argument("--out", type=Path, required=True)
    p_prep.add_argument("--today", default=None, help="YYYY-MM-DD（試跑時間快轉用；預設排程時區的今天）")
    p_prep.add_argument("--watches", type=Path, default=None, help="watch registry 路徑（試跑用副本；預設真實那份）")
    p_apply = sub.add_parser("apply", help="daily ⑩g：驗證後只記查過、只掛命中（不改狀態）")
    p_apply.add_argument("--file", type=Path, required=True)
    p_apply.add_argument("--batch", type=Path, required=True)
    p_apply.add_argument("--run-id", required=True)
    p_apply.add_argument("--watches", type=Path, default=None, help="watch registry 路徑（試跑用副本；預設真實那份）")
    p_apply.add_argument("--receipt-dir", type=Path, default=OUT_DIR)
    p_apply.add_argument("--today", default=None, help="YYYY-MM-DD（試跑時間快轉用）")
    sub.add_parser("queue", help="互動：列待判定的 T2 命中（標題、網址、模型摘要與判定命令）")
    p_judge = sub.add_parser("judge", help="互動：判定一則 T2 命中（觸及＝叫醒那條等待；無關＝只記判定）")
    p_judge.add_argument("watch_id")
    p_judge.add_argument("--url", required=True)
    p_judge.add_argument("--touches", required=True, choices=("yes", "no"))
    p_judge.add_argument("--note", required=True)
    p_judge.add_argument("--quote", default="", help="文件逐字（--touches yes 時必填）")
    args = parser.parse_args(argv)

    from engine_b import event_watch as ew

    if args.command == "prepare":
        out = prepare(args.run_id, args.out, today=_day(args.today),
                      data=ew.load_watches(args.watches) if args.watches else None)
        print(json.dumps({"summary": out}, ensure_ascii=False))
        return 0
    if args.command == "apply":
        out = apply(args.file, args.batch, args.run_id, watches_path=args.watches, receipt_dir=args.receipt_dir,
                    today=_day(args.today))
        print(json.dumps(out, ensure_ascii=False))
        s = out["summary"]
        print(f"T2 輪詢 {s['batch']}｜查過 {s['checked']}｜新命中 {s['hits_new']}（{s['watches_with_new_hits']} 條）"
              f"｜拒收 {s['rejected']}（沒真的查 {s['not_searched']}、網址不在搜尋結果 {s['url_not_in_search']}、"
              f"重複 {s['duplicate_hit']}、超過上限 {s['over_cap']}）｜沒回 {s['unanswered']}", file=sys.stderr)
        return 0
    data = ew.load_watches()
    if args.command == "queue":
        from engine_b.leads import load as load_leads

        try:
            leads_store = load_leads()["leads"]
        except Exception:  # noqa: BLE001 — 讀不到只少「原本在追」那一行
            leads_store = {}
        print("\n".join(queue_lines(data, leads_store)))
        return 0
    judgment = ew.judge_poll_hit(data, args.watch_id, url=args.url, touches=args.touches == "yes",
                                 note=args.note, quote=args.quote or None)
    ew.save_watches(data)
    if args.touches == "yes":
        watch = next(w for w in data["watches"] if w["watch_id"] == args.watch_id)
        print(f"✓ {args.watch_id} 判定觸及（{judgment['at']}）→ 叫醒：{ew.wake_target(watch)['label']}")
        print("（下一步照喚醒目標走：追源線索跑 `python -m engine_b.cli consume-fired` 排回 pq1；"
              "pq2 型跑 `python -m engine_b.todo sync` 翻回球在你；假設型照段 0b 對照）")
    else:
        print(f"✓ {args.watch_id} 這則判定無關，等待照舊（{judgment['at']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["BATCH_SCHEMA", "RECEIPT_SCHEMA", "REJECT_REASONS", "apply", "build_items", "main", "prepare",
           "queue_lines"]
