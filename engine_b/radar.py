"""外部雷達（Phase 7 Step 7.0f；使用者 2026-10-04 Q5）——daily ①b 準備、①e 套用。

LLM（①c，`crons/llm_step.py::radar_argv`，**只開 WebSearch**）只產出提議；這裡是兩端的程式：

- **prepare**：組 LLM 要的資料——`config/themes.txt` 的主題與關鍵字、在盯的語意 watch 條件原文與實體（讓它找得到
  「碰到哪條反證或加碼條件」的新聞）。**不讀 Sheet、持股、NAV**（`tests/test_radar.py` 以哨兵證明）。
  2026-10-21 起（雷達精進 C3）主題層加「讀過的層」每日輪替：今天輪到的 `ROTATION_K` 層（層名、讀圖供給側公司），
  條件只帶掛在這幾層的（短 id，程式對回原 id）；輪替算不出來就退回全量條件。
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
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
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


#: 「已收過」清單（2026-10-20）：前幾天收下的標題交給 LLM，同一件事換了網址或媒體不要再回——網址去重擋不住
#: （回放 10-14～10-20 收下的 43 則裡至少 5 則是同一件事，吃掉主題層的名額）。
RECENT_LOOKBACK_DAYS = 7
RECENT_CAP = 30


def recently_accepted(receipt_dir: Path, *, today: date, days: int = RECENT_LOOKBACK_DAYS,
                      cap: int = RECENT_CAP) -> list[dict[str, str]]:
    """前 `days` 天（不含今天）雷達收據收下的標題，新的在前，最多 `cap` 則。讀不到的收據略過（只少一份清單，不擋雷達）。"""
    rows: list[dict[str, str]] = []
    for back in range(1, days + 1):
        day = today - timedelta(days=back)
        try:
            receipt = json.loads((receipt_dir / f"radar_{day.isoformat()}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for item in receipt.get("accepted") or ():
            title = str(item.get("title") or "").strip()
            if title:
                rows.append({"date": day.isoformat(), "title": title})
    return rows[:cap]


#: 讀過的層每日輪替（雷達精進 C3，2026-10-21；使用者 10-20：與 themes.txt **並存**）：每天依日期序號固定輪到 K 個
#: 有現行讀圖的節點（58 層約 7 天輪完），只把掛在這幾層的在盯條件交給 LLM——全量 270 條（約 52 KB）一次搜不完，
#: 實際只挑幾條查（10-20 調查）。每天輪 max(ROTATION_K, ⌈層數÷ROTATION_DAYS⌉) 層——層數長了也是 7 天輪完
#: （10-21 試跑：58 層、每天 8 層，7 天只輪到 56）。掛不到任何層的條件另外每天輪 1/ROTATION_DAYS。
ROTATION_K = 8
ROTATION_DAYS = 7
SUPPLY_NAMES_PER_LAYER = 6


def rotation(nodes: Sequence[str], today: date, k: int = ROTATION_K) -> list[str]:
    """排好序的節點裡今天輪到的那 k 個：起點＝日期序號 × k（取模），連續取 k 個、繞回開頭。相鄰兩天銜接，⌈n/k⌉ 天輪完。"""
    ordered = sorted(set(nodes))
    if not ordered:
        return []
    start = (today.toordinal() * k) % len(ordered)
    return [ordered[(start + i) % len(ordered)] for i in range(min(k, len(ordered)))]


def _condition_nodes(watch: Mapping[str, Any], ctx: Any, *, reading_node: Mapping[str, str],
                     note_node: Mapping[str, str], rides: Mapping[str, Sequence[str]]) -> set[str]:
    """這條條件掛在哪幾層：讀圖反證 → 那份讀圖的節點；層說明的條件 → 那份說明的節點；敘事的條件 → 那份敘事騎的層
    （歸屬一律問 `narrative_watches.attributed_watches`，經 `impact.Context.watch_owner`）。"""
    ref = str(watch.get("source_ref") or "")
    head, _, rest = ref.partition(":")
    key = rest.split("#", 1)[0]
    nodes: set[str] = set()
    if head == "reading" and key in reading_node:
        nodes.add(reading_node[key])
    if head == "layer_note" and key in note_node:
        nodes.add(note_node[key])
    for ticker in ctx.watch_owner.get(str(watch.get("watch_id")), ()):
        nodes.update(rides.get(ticker, ()))
    return nodes


def layer_plan(ctx: Any, *, today: date, registry: Any, note_node: Mapping[str, str] | None = None,
               k: int = ROTATION_K) -> dict[str, Any]:
    """今天輪到的層（層名、供給側公司、掛在這幾層的條件）＋掛不到層的條件今天那一份。條件給 LLM 短 id（c01…），
    程式留 `condition_ids` 對回原 watch_id（#92：LLM 會把長 id 截掉）。"""
    from engine_b import event_watch as ew

    readings = ctx.readings
    reading_node = {str(getattr(r, "reading_id", "")): node for node, r in readings.items()}
    rides = {b.ticker: [r.node for r in b.rides or () if r.node in readings] for b in ctx.briefs}
    today_nodes = rotation(list(readings), today, max(k, math.ceil(len(readings) / ROTATION_DAYS)))
    picked: dict[str, list[str]] = {}
    orphans: list[Mapping[str, Any]] = []
    for w in ctx.watches:
        if w.get("kind") != ew.SEMANTIC_KIND or w.get("status") != "active":
            continue
        nodes = _condition_nodes(w, ctx, reading_node=reading_node, note_node=note_node or {}, rides=rides)
        if not nodes:
            orphans.append(w)
        elif nodes & set(today_nodes):
            picked[str(w.get("watch_id"))] = sorted(nodes & set(today_nodes))
    orphans.sort(key=lambda w: str(w.get("watch_id")))
    orphan_today = [w for i, w in enumerate(orphans) if i % ROTATION_DAYS == today.toordinal() % ROTATION_DAYS]
    by_id = {str(w.get("watch_id")): w for w in ctx.watches}
    chosen = sorted(picked) + [str(w.get("watch_id")) for w in orphan_today]
    condition_rows, id_map = [], {}
    for i, wid in enumerate(chosen, 1):
        w = by_id[wid]
        short = f"c{i:02d}"
        id_map[short] = wid
        condition_rows.append({"id": short, "role": "加碼條件（結構被確認）" if ew.is_confirm(w) else "反證（結構被推翻）",
                               "condition": str(w.get("condition") or ""), "layers": picked.get(wid, []),
                               "entities": [_company_label(registry, e) for e in w.get("entities") or ()]})
    layer_rows = []
    for node in today_nodes:
        supply = sorted(c for c, angles in (ctx.reading_entities.get(node) or {}).items() if "supply_side" in angles)
        names = [str(getattr(ctx.companies.get(c), "display_name", "") or c) for c in supply]
        layer_rows.append({"node": node, "name": ctx.node_names.get(node) or node,
                           "supply_side": names[:SUPPLY_NAMES_PER_LAYER],
                           "more_supply": max(len(names) - SUPPLY_NAMES_PER_LAYER, 0),
                           "conditions": sum(node in v for v in picked.values())})
    return {"layers": layer_rows, "conditions": condition_rows, "condition_ids": id_map, "pool": len(readings),
            "orphans": len(orphans), "orphans_today": len(orphan_today)}


def build_request(*, themes: Mapping[str, Any], watches: Sequence[Mapping[str, Any]], registry: Any,
                  max_items: int, today: date, market_topics: Sequence[str] = (),
                  max_market_items: int = 0, recent: Sequence[Mapping[str, str]] = (),
                  plan: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """LLM 要的那一份資料。主題只帶公開的研究題目（描述、核心公司、關鍵字、反證關鍵字）；條件只帶在盯的語意 watch
    （反證與加碼條件）的原文、實體與角色；市場大事只帶 config 裡寫好的題目（2026-10-07）。
    `plan`（C3 輪替）有給時，條件只帶今天輪到的層掛的那些（短 id）；沒給（輪替算不出來）退回全量、照舊用 watch_id。
    **沒有任何持股、部位、私人路徑的欄位**。"""
    from engine_b import event_watch as ew

    theme_rows = [{"slug": slug, "description": t.description, "core_companies": list(t.tickers),
                   "keywords": list(t.keywords), "counter_keywords": list(t.counter_keywords)}
                  for slug, t in sorted(themes.items())]
    if plan is not None:
        condition_rows = [dict(r) for r in plan["conditions"]]
    else:
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
            "rotation_layers": [dict(r) for r in (plan or {}).get("layers") or ()],
            "watched_conditions": condition_rows,
            "market_topics": [str(t) for t in market_topics], "max_market_items": int(max_market_items),
            "recently_accepted": [dict(r) for r in recent]}


def _default_plan_context() -> tuple[Any, dict[str, str]]:
    from engine_b.disproof import current_layer_notes
    from engine_b.impact import load_context

    notes = current_layer_notes()
    return load_context(), {str(getattr(n, "note_id", "")): node for node, n in notes.items()}


def prepare(run_id: str, out: Path, *, max_items: int, today: date | None = None,
            themes: Mapping[str, Any] | None = None, watches: Sequence[Mapping[str, Any]] | None = None,
            registry: Any = None, market_topics: Sequence[str] = (), max_market_items: int = 0,
            receipt_dir: Path = OUT_DIR, plan_context: Any = None) -> dict[str, Any]:
    """`plan_context`：回傳 `(impact.Context, note_id→節點)` 的函式（預設讀現行敘事、讀圖、層說明；測試注入）。
    輪替算不出來不擋雷達：退回全量條件、錯誤寫進批次與 summary（失敗要說出來，L13）。"""
    from engine_b import event_watch as ew
    from engine_b.themes import load_themes
    from identity.registry import get_registry

    today = today or datetime.now().astimezone().date()
    registry = registry or get_registry()
    plan, plan_error = None, None
    try:
        ctx, note_node = (plan_context or _default_plan_context)()
        plan = layer_plan(ctx, today=today, registry=registry, note_node=note_node)
    except Exception as exc:  # noqa: BLE001 — 輪替壞了雷達照跑（退回全量條件）
        plan_error = f"{type(exc).__name__}: {str(exc)[:160]}"
    request = build_request(themes=themes if themes is not None else load_themes(),
                            watches=watches if watches is not None else (ew.load_watches().get("watches") or []),
                            registry=registry, max_items=max_items, today=today,
                            market_topics=market_topics, max_market_items=max_market_items,
                            recent=recently_accepted(receipt_dir, today=today), plan=plan)
    # 短 id 對照與輪替池大小放在 requests 外面——LLM 只看 requests，不必看到原 id
    envelope = {"schema": BATCH_SCHEMA, "run_id": run_id, "run_date": today.isoformat(), "requests": [request],
                "condition_ids": dict((plan or {}).get("condition_ids") or {}), "rotation_pool": (plan or {}).get("pool"),
                "rotation_error": plan_error}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"themes": len(request["themes"]), "watched_conditions": len(request["watched_conditions"]),
            "max_items": request["max_items"], "market_topics": len(request["market_topics"]),
            "max_market_items": request["max_market_items"], "recently_accepted": len(request["recently_accepted"]),
            "rotation_layers": len(request["rotation_layers"]), "rotation_pool": (plan or {}).get("pool"),
            "orphan_conditions": (plan or {}).get("orphans"), "rotation_error": plan_error}


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


def _resolve_watch_id(given: str, known: set[str]) -> str | None:
    """LLM 回報的 watch id → registry 的真 id。完整相符直接收；LLM 常把日期尾綴截掉（`ew_0421` 對 `ew_0421_2026-10-07`），
    恰好對到一條才收、對到兩條以上不猜（L15）。2026-10-20 前只認完整 id：10-05 起 26 條全被當成對不上丟掉（L17）。"""
    if given in known:
        return given
    hits = [k for k in known if k.startswith(given + "_")]
    return hits[0] if len(hits) == 1 else None


_SHORT_ID = re.compile(r"^c0*(\d+)$")


def _resolve_condition(given: str, id_map: Mapping[str, str], known: set[str]) -> str | None:
    """短 id（c07；寫成 c7 也認）→ 原 watch_id；不是短 id 就照舊比對原 id（含截掉日期尾綴的前綴，#92）。"""
    short = _SHORT_ID.match(given.strip())
    if short:
        return id_map.get(f"c{int(short.group(1)):02d}")
    return _resolve_watch_id(given, known)


def rotation_coverage(receipt_dir: Path, *, today: date, todays: Sequence[str], days: int = ROTATION_DAYS) -> set[str]:
    """近 `days` 天（含今天）雷達輪到過的層（驗收 3：有現行讀圖的節點 7 天內都被輪到）。讀不到的收據略過。"""
    covered = set(todays)
    for back in range(1, days):
        try:
            receipt = json.loads((receipt_dir / f"radar_{(today - timedelta(days=back)).isoformat()}.json")
                                 .read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        covered.update(str(n) for n in receipt.get("rotation") or ())
    return covered


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
    id_map = {str(k): str(v) for k, v in (batch.get("condition_ids") or {}).items()}
    known_watches = {str(c.get("watch_id")) for c in request.get("watched_conditions") or () if c.get("watch_id")}
    known_watches |= set(id_map.values())
    rotation_nodes = [str(r.get("node")) for r in request.get("rotation_layers") or () if r.get("node")]
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
              "theme_unknown": 0, "relates_to_unknown": 0, "relates_to_resolved_prefix": 0, "related": 0,
              "scope_unknown": 0, "layer_unknown": 0, "new_layer": 0,
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
        resolved = [(str(w), _resolve_condition(str(w), id_map, known_watches)) for w in item.get("relates_to") or ()]
        relates = list(dict.fromkeys(r for _, r in resolved if r))
        # 輪替層（C3）：只認今天輪到的那幾層；寫錯的照數、不寫進 refs
        layer = str(item.get("layer") or "").strip() if isinstance(item, Mapping) else ""
        if layer and layer not in rotation_nodes:
            counts["layer_unknown"] += 1
            layer = ""
        counts["relates_to_unknown"] += sum(1 for _, r in resolved if not r)
        counts["relates_to_resolved_prefix"] += sum(1 for w, r in resolved if r and r != w)
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
        if layer:
            refs["radar_layer"] = layer
        if raw_names:
            refs["radar_entities"] = raw_names
        if company_ids:
            refs["radar_company_ids"] = company_ids
        leads.annotate_refs(store, lead_id, refs=refs)
        counts["new"] += 1
        counts[f"new_{scope}"] += 1
        counts["related"] += int(bool(relates))
        counts["new_layer"] += int(bool(layer))
        # 收據帶標題（搜尋結果的，不是 LLM 寫的）與 LLM 那一句事實——每日摘要照印，不必回頭讀 registry
        accepted.append({"lead_id": lead_id, "url": allowed[key], "theme": theme, "published_at": published,
                         "relates_to": relates, "scope": scope, "layer": layer or None, "title": titles.get(key) or None,
                         "fact": fact, "why": str(item.get("why") or "").strip() or None,
                         "publisher": str(item.get("publisher") or "").strip() or None})
    if accepted:
        leads.save(store, path)
    summary = {**counts, "rejected": len(rejected), "no_material_change": bool(result.get("no_material_change")),
               "searches": search.get("searches"), "search_urls": len(allowed), "max_items": max_items,
               "max_market_items": max_market, "rotation_layers": len(rotation_nodes),
               "rotation_pool": batch.get("rotation_pool"), "rotation_error": batch.get("rotation_error"),
               "rotation_covered_7d": len(rotation_coverage(receipt_dir, today=today, todays=rotation_nodes))}
    receipt = {"schema": RECEIPT_SCHEMA, "run_id": run_id, "date": today.isoformat(), "summary": summary,
               "rotation": rotation_nodes,
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


__all__ = ["BATCH_SCHEMA", "NEW_THEME", "RECEIPT_SCHEMA", "REJECT_REASONS", "ROTATION_DAYS", "ROTATION_K", "SCOPES",
           "SOURCE_PREFIX", "apply", "build_request", "is_radar_lead", "layer_plan", "main", "prepare", "resolve_entities",
           "rotation", "rotation_coverage"]
