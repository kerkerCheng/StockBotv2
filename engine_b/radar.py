"""外部雷達（Phase 7 Step 7.0f；使用者 2026-10-04 Q5）——daily ①b 準備、①e 套用。

LLM（①c，`crons/llm_step.py::radar_argv`，**只開 WebSearch**）只產出提議；這裡是兩端的程式：

- **prepare**：組 LLM 要的資料——`config/themes.txt` 的主題與關鍵字、在盯的語意 watch 條件原文與實體（讓它找得到
  「碰到哪條反證或加碼條件」的新聞）。**不讀 Sheet、持股、NAV、私人路徑**（`tests/test_radar.py` 以哨兵證明）。
- **apply**：程式驗證後寫成 lead。每一條拒收都有理由、照數（INV-3）：
  ①網址必須出現在**同一次執行**的搜尋結果裡（daily 從 stream 收、寫進結果檔的 `search.urls`——不信 LLM 自己報）；
  ②正規化網址後與 lead registry 去重（`leads.register` 是去重的唯一入口；已登記的不碰——誰先登記照實留著，
  7.5 檢查點要分得出「別的管道更早」）；③每日上限 `radar.max_items`（超過的計數、不寫）；④`published_at` 讀不懂或晚於
  今天就 null（不拿抓取日冒充，INV-6）；⑤實體以名冊寫法解析，解析不到留原字。
  寫成 `source=web_radar:<主題>`、`source_class=secondary`；lead 的標題取**搜尋結果的標題**（不是 LLM 寫的）、
  LLM 寫的那一句事實放 `refs.radar_fact`（標明是 LLM 摘要，不冒充原文——L18）。
  **不喚醒語意 watch**：語意 watch 的 T0 只認 `source_class=primary`（`engine_b/event_watch.py`）。
  收據 `library/private/heartbeat/radar_<日期>.json`（收／拒與理由）。

triage 批次裡雷達的 lead 排在所有非雷達 lead 之後才截上限（`engine_b/cli.py`）——它不會擠掉 harvest 的 lead。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "library" / "private" / "heartbeat"
BATCH_SCHEMA = "radar-batch-v1"
RECEIPT_SCHEMA = "radar-receipt-v1"
#: 雷達 lead 的 `source` 前綴（L16：判斷「這是不是雷達的 lead」只住 `is_radar_lead`）。
SOURCE_PREFIX = "web_radar:"
NEW_THEME = "new"
#: 一則提議落在哪一層（封閉字彙；2026-10-07 使用者：「不能見樹不見林」）：
#: market＝AI capex 市場層的大事（不限在盯公司）；theme＝我們在追的主題；watch＝碰到在盯的條件。兩層各有上限。
SCOPES: Mapping[str, str] = {"market": "市場大事", "theme": "我們在追的主題", "watch": "碰到在盯的條件"}
#: 拒收理由（封閉字彙；收據與心跳照這幾個字數）。
REJECT_REASONS: Mapping[str, str] = {
    "invalid": "欄位不合法（網址或事實是空的、型別不對）",
    "url_not_in_search": "網址不在這一次執行的搜尋結果裡",
    "duplicate": "lead registry 已有這個網址（或同一批重複）",
    "over_cap": "超過每日上限（市場大事 radar.max_market_items；其餘 radar.max_items）",
}


def is_radar_lead(lead: Mapping[str, Any]) -> bool:
    return str(lead.get("source") or "").startswith(SOURCE_PREFIX)


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------

def _company_label(registry: Any, entity: str) -> str:
    company = registry.company(entity) if str(entity).startswith("co:") else None
    name = getattr(company, "display_name", None) if company is not None else None
    return f"{name}（{entity}）" if name else str(entity)


def build_request(*, themes: Mapping[str, Any], watches: Sequence[Mapping[str, Any]], registry: Any,
                  max_items: int, today: date, market_topics: Sequence[str] = (),
                  max_market_items: int = 0) -> dict[str, Any]:
    """LLM 要的那一份資料。主題只帶公開的研究題目（描述、核心公司、關鍵字、反證關鍵字）；條件只帶在盯的語意 watch
    （反證與加碼條件）的原文、實體與角色；市場大事只帶 config 裡寫好的題目（2026-10-07）。
    **沒有任何持股、部位、私人路徑的欄位**。"""
    from engine_b import event_watch as ew

    theme_rows = [{"slug": slug, "description": t.description, "core_companies": list(t.tickers),
                   "keywords": list(t.keywords), "counter_keywords": list(t.counter_keywords)}
                  for slug, t in sorted(themes.items())]
    condition_rows = []
    for w in watches:
        if w.get("kind") != ew.SEMANTIC_KIND or w.get("status") != "active":
            continue
        condition_rows.append({
            "watch_id": str(w.get("watch_id")),
            "role": "加碼條件（結構被確認）" if ew.is_confirm(w) else "反證（結構被推翻）",
            "condition": str(w.get("condition") or ""),
            "entities": [_company_label(registry, e) for e in w.get("entities") or ()],
        })
    condition_rows.sort(key=lambda r: r["watch_id"])
    return {"today": today.isoformat(), "max_items": int(max_items), "themes": theme_rows,
            "watched_conditions": condition_rows,
            "market_topics": [str(t) for t in market_topics], "max_market_items": int(max_market_items)}


def prepare(run_id: str, out: Path, *, max_items: int, today: date | None = None,
            themes: Mapping[str, Any] | None = None, watches: Sequence[Mapping[str, Any]] | None = None,
            registry: Any = None, market_topics: Sequence[str] = (), max_market_items: int = 0) -> dict[str, Any]:
    from engine_b import event_watch as ew
    from engine_b.themes import load_themes
    from identity.registry import get_registry

    today = today or datetime.now().astimezone().date()
    request = build_request(themes=themes if themes is not None else load_themes(),
                            watches=watches if watches is not None else (ew.load_watches().get("watches") or []),
                            registry=registry or get_registry(), max_items=max_items, today=today,
                            market_topics=market_topics, max_market_items=max_market_items)
    envelope = {"schema": BATCH_SCHEMA, "run_id": run_id, "run_date": today.isoformat(), "requests": [request]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"themes": len(request["themes"]), "watched_conditions": len(request["watched_conditions"]),
            "max_items": request["max_items"], "market_topics": len(request["market_topics"]),
            "max_market_items": request["max_market_items"]}


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

def _published(value: Any, *, today: date) -> tuple[str | None, bool]:
    """(ISO 日期或 None, 是否讀不懂)。讀不懂、或晚於今天（未來日期不是發布日）一律 None——不拿今天冒充（INV-6）。"""
    if value is None:
        return None, False
    try:
        day = date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None, True
    return (None, True) if day > today else (day.isoformat(), False)


def resolve_entities(names: Iterable[str], registry: Any) -> tuple[list[str], list[str]]:
    """(解析到的 co:*, 原字)。名字只來自 `query.bottleneck.company_name_forms`（名字比對的唯一來源），完全相符才算；
    兩家共用的寫法（`shared_name_forms`）不算——不猜（L15）。解析不到的照原字留著，不丟。"""
    from query.bottleneck import company_name_forms, shared_name_forms

    shared = shared_name_forms(registry)
    forms: dict[str, str] = {}
    for company in registry.companies:
        for form in company_name_forms(company):
            key = form.casefold()
            if key not in shared:
                forms.setdefault(key, company.company_id)
    found: list[str] = []
    raw: list[str] = []
    for name in names:
        text = str(name or "").strip()
        if not text:
            continue
        raw.append(text)
        cid = forms.get(text.casefold())
        if cid and cid not in found:
            found.append(cid)
    return found, raw


def apply(result_path: Path, batch_path: Path, run_id: str, *, store_path: Path | None = None,
          receipt_dir: Path = OUT_DIR, today: date | None = None, registry: Any = None,
          now: datetime | None = None) -> dict[str, Any]:
    """驗證後寫 lead，回傳 `{summary, rejected}`（daily 的套用步驟把最後一行 JSON 收進執行紀錄）。"""
    from engine_b import leads
    from engine_b.themes import load_themes
    from identity.registry import get_registry

    result = json.loads(result_path.read_text(encoding="utf-8"))
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if result.get("run_id") != run_id or batch.get("run_id") != run_id:
        raise ValueError("結果檔或批次檔的 run_id 不是這一輪的——不套用舊檔")
    request = (batch.get("requests") or [{}])[0]
    max_items = int(request.get("max_items") or 0)
    max_market = int(request.get("max_market_items") or 0)
    known_watches = {str(c.get("watch_id")) for c in request.get("watched_conditions") or ()}
    known_themes = set(load_themes())
    search = result.get("search") or {}
    allowed: dict[str, str] = {}
    titles: dict[str, str] = {}
    raw_titles = search.get("titles") or {}
    for url in search.get("urls") or ():
        try:
            key = leads.normalize_url(str(url))
        except ValueError:          # 正規化不了的網址（空字串、壞的 netloc）不進允許清單——LLM 提它也會被拒
            continue
        allowed[key] = str(url)
        if str(raw_titles.get(url) or "").strip():
            titles[key] = str(raw_titles[url]).strip()
    today = today or datetime.now().astimezone().date()
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    registry = registry or get_registry()
    path = Path(store_path) if store_path else leads.DEFAULT_LEADS_PATH
    store = leads.load(path)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    counts = {"proposed": 0, "new": 0, **{k: 0 for k in REJECT_REASONS}, "published_unparsed": 0,
              "theme_unknown": 0, "relates_to_unknown": 0, "related": 0, "scope_unknown": 0,
              "new_market": 0, "new_theme": 0, "new_watch": 0}
    seen: set[str] = set()
    for item in result.get("items") or ():
        counts["proposed"] += 1
        url = str((item or {}).get("url") or "").strip() if isinstance(item, Mapping) else ""
        fact = str(item.get("fact") or "").strip() if isinstance(item, Mapping) else ""
        # 哪一層（2026-10-07）：讀不懂的照數、當成主題那一層（不得安靜變成市場大事去吃另一份上限）
        scope = str(item.get("scope") or "").strip() if isinstance(item, Mapping) else ""
        if scope not in SCOPES:
            counts["scope_unknown"] += int(bool(url and fact))
            scope = "theme"

        def reject(reason: str, **extra: Any) -> None:
            counts[reason] += 1
            rejected.append({"url": url or None, "reason": reason, "detail": REJECT_REASONS[reason], **extra})

        if not url or not fact:
            reject("invalid")
            continue
        try:
            key = leads.normalize_url(url)
        except ValueError:
            reject("invalid")
            continue
        if key not in allowed:
            reject("url_not_in_search")
            continue
        lead_id = leads.lead_id_for(url)
        if key in seen or lead_id in store["leads"]:
            reject("duplicate", lead_id=lead_id)
            continue
        seen.add(key)
        # 兩層各算各的上限：市場大事不擠掉在追的題目，反過來也一樣
        if (scope == "market" and counts["new_market"] >= max_market) or \
                (scope != "market" and counts["new_theme"] + counts["new_watch"] >= max_items):
            reject("over_cap", scope=scope)
            continue
        published, unparsed = _published(item.get("published_at"), today=today)
        counts["published_unparsed"] += int(unparsed)
        theme = str(item.get("theme") or "").strip()
        if theme != NEW_THEME and theme not in known_themes:
            counts["theme_unknown"] += 1
            theme = NEW_THEME
        relates = [str(w) for w in item.get("relates_to") or () if str(w) in known_watches]
        counts["relates_to_unknown"] += len([w for w in item.get("relates_to") or () if str(w) not in known_watches])
        company_ids, raw_names = resolve_entities(item.get("entities") or (), registry)
        lead_id, is_new = leads.register(store, source=f"{SOURCE_PREFIX}{theme}", url=allowed[key],
                                         title=titles.get(key) or str(item.get("title") or "").strip(),
                                         published_at=published, seen_at=stamp, source_class="secondary")
        if not is_new:                       # register 說已存在（並發寫入的極端情形）——照重複算，不碰它
            reject("duplicate", lead_id=lead_id)
            continue
        refs: dict[str, Any] = {"radar_run": run_id, "radar_fact": fact, "radar_scope": scope}
        for ref_key, value in (("radar_why", item.get("why")), ("radar_publisher", item.get("publisher"))):
            if str(value or "").strip():
                refs[ref_key] = str(value).strip()
        if relates:
            refs["relates_to"] = relates
        if raw_names:
            refs["radar_entities"] = raw_names
        if company_ids:
            refs["radar_company_ids"] = company_ids
        leads.annotate_refs(store, lead_id, refs=refs)
        counts["new"] += 1
        counts[f"new_{scope}"] += 1
        counts["related"] += int(bool(relates))
        # 收據帶標題（搜尋結果的，不是 LLM 寫的）與 LLM 那一句事實——每日摘要照印，不必回頭讀 registry
        accepted.append({"lead_id": lead_id, "url": allowed[key], "theme": theme, "published_at": published,
                         "relates_to": relates, "scope": scope, "title": titles.get(key) or None,
                         "fact": fact, "why": str(item.get("why") or "").strip() or None,
                         "publisher": str(item.get("publisher") or "").strip() or None})
    if accepted:
        leads.save(store, path)
    summary = {**counts, "rejected": len(rejected), "no_material_change": bool(result.get("no_material_change")),
               "searches": search.get("searches"), "search_urls": len(allowed), "max_items": max_items,
               "max_market_items": max_market}
    receipt = {"schema": RECEIPT_SCHEMA, "run_id": run_id, "date": today.isoformat(), "summary": summary,
               "accepted": accepted, "rejected": rejected, "queries": list(search.get("queries") or ()),
               "sessions": list(result.get("sessions") or ())}
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / f"radar_{today.isoformat()}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"summary": summary, "rejected": rejected}


# ---------------------------------------------------------------------------
# CLI（daily 的 ①b／①e 呼叫；互動 session 試跑時加 --leads 指到副本）
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    from engine_b.routine_config import load_radar

    parser = argparse.ArgumentParser(prog="python -m engine_b.radar")
    sub = parser.add_subparsers(dest="command", required=True)
    p_prep = sub.add_parser("prepare", help="組雷達的批次檔（主題＋在盯的條件；不讀持股）")
    p_prep.add_argument("--run-id", required=True)
    p_prep.add_argument("--out", type=Path, required=True)
    p_apply = sub.add_parser("apply", help="驗證雷達的提議後寫成 secondary lead")
    p_apply.add_argument("--file", type=Path, required=True)
    p_apply.add_argument("--batch", type=Path, required=True)
    p_apply.add_argument("--run-id", required=True)
    p_apply.add_argument("--leads", type=Path, default=None, help="lead registry 路徑（試跑用副本；預設真實那份）")
    p_apply.add_argument("--receipt-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        radar = load_radar()
        out = prepare(args.run_id, args.out, max_items=int(radar["max_items"]),
                      market_topics=radar.get("market_topics") or (),
                      max_market_items=int(radar.get("max_market_items") or 0))
        print(json.dumps({"summary": out}, ensure_ascii=False))
        return 0
    out = apply(args.file, args.batch, args.run_id, store_path=args.leads, receipt_dir=args.receipt_dir)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["BATCH_SCHEMA", "NEW_THEME", "RECEIPT_SCHEMA", "REJECT_REASONS", "SCOPES", "SOURCE_PREFIX", "apply",
           "build_request", "is_radar_lead", "main", "prepare", "resolve_entities"]
