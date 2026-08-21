"""engine_b.cli — pending leads 的 list／triage／advance／annotate 命令列入口。

給 `/daily-brief` skill 一條 deterministic 持久化路徑：research agent 做語意
triage 判斷，這支 CLI 負責寫入狀態機（不讓 agent 手寫 JSON 冒險汙染 store）。
狀態語意與不變式（lead 狀態不影響 evidence tier）全在 engine_b/leads.py。

用法:
    python -m engine_b.cli register --source weekly --url <url> --title "..."
    python -m engine_b.cli list [--status pending]
    python -m engine_b.cli triage <lead_id> --go|--no-go --tier 3 --reason "有新角度"
    python -m engine_b.cli advance <lead_id> researching
    python -m engine_b.cli annotate <lead_id> --ref outcome=audio_obtained
    python -m engine_b.cli counts
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine_b import leads  # noqa: E402
from engine_b import priority  # noqa: E402
from engine_b import routine_config  # noqa: E402


class PriorityContextError(RuntimeError):
    """pq1 排序需要的 current-authority context 無法取得。"""


def _tracked(arg: str | None) -> frozenset[str]:
    return frozenset(t.strip().upper() for t in (arg or "").split(",") if t.strip())


def _chokepoint(*, strict: bool = False) -> tuple[frozenset[str], frozenset[str]]:
    """位於已知瓶頸上的公司（ticker 與 company_id）。

    2026-08-20 之前 pq1 排序完全不看瓶頸性——「AXT 供應 COHR 的 InP」與「財報季
    總評」只由 tier 與 flags 區分，而系統整個定位就是找瓶頸。這裡把
    `query/bottleneck.py` 已經算好的排序接進 priority。

    **只收 `demand_anchor` 非空的列**：依既有判準，連不到有人花錢的地方的瓶頸沒有
    投資意義（`rank_bottlenecks` 自己的排序鍵也把需求錨點可達性放第一）。
    與 `_held()` 同樣是唯讀輸入，取不到就回空集合讓排序退回原行為，不阻斷 drain。
    """

    try:
        import os

        from neo4j import GraphDatabase

        from identity.registry import get_registry
        from query import bottleneck

        password = os.environ.get("NEO4J_PASSWORD")
        if not password:
            raise PriorityContextError("缺少 NEO4J_PASSWORD，無法載入 chokepoint context")
        driver = GraphDatabase.driver(
            os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
        )
        try:
            with driver.session() as session:
                rows = bottleneck.fetch_assertions(session)
        finally:
            driver.close()
        result = bottleneck.rank_bottlenecks(rows, get_registry())
    except Exception as exc:
        if strict:
            if isinstance(exc, PriorityContextError):
                raise
            raise PriorityContextError("無法載入 Neo4j chokepoint context") from exc
        return frozenset(), frozenset()

    tickers: set[str] = set()
    company_ids: set[str] = set()
    for row in result.get("rows") or ():
        if not row.get("demand_anchor"):
            continue
        company_id = row.get("company_id")
        if company_id:
            company_ids.add(str(company_id))
        ticker = row.get("ticker")
        if ticker:
            ticker = str(ticker).upper()
            tickers.add(ticker)
            # registry 存 research ticker（SIVE.ST／6324.T），lead 的 cashtag 多是
            # 無交易所後綴的形式（$SIVE）——兩者都收，交集比對才不會漏。
            base = ticker.split(".", 1)[0]
            if base:
                tickers.add(base)
    return frozenset(tickers), frozenset(company_ids)


def _held(*, strict: bool = False) -> tuple[frozenset[str], frozenset[str]]:
    """Google Sheet 的實際持股（ticker 與 company_id）。

    `tracked_tickers` 由 lifecycle ＋ 未結案 cohort 導出，**不含持股**——因此在此
    之前，一檔真的有部位、卻還沒建 cohort 的標的在 pq1 排序上等於不存在。
    持股是唯讀輸入，取不到就回空集合（排序退回原行為），不阻斷 drain。
    """

    try:
        from fetchers.gsheets import fetch_portfolio

        rows = fetch_portfolio(strict_operational=True)
    except Exception as exc:
        if strict:
            raise PriorityContextError("無法載入 Google Sheet 持股 context") from exc
        return frozenset(), frozenset()
    tickers: set[str] = set()
    company_ids: set[str] = set()
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker and ticker != "—":
            tickers.add(ticker)
            # Sheet 用 execution symbol（FRA:2DG）；lead 的 cashtag 是 research
            # ticker（$SIVE）。兩者都收，交集比對才不會漏。
            if ":" in ticker:
                tickers.add(ticker.split(":", 1)[1])
        company_id = row.get("company_id") or row.get("neo4j_id")
        if company_id:
            company_ids.add(str(company_id))
    # 同一家公司三個字串：Sheet 是 execution symbol（FRA:2DG）、registry 是 research
    # ticker（SIVE.ST）、推文 cashtag 是 base（$SIVE）。lead 的 entities 是 harvest
    # 當時算的、不會重算，所以要從持股這一側補上 research ticker 與其 base 形式，
    # 否則「我持有的公司被點名」永遠比對不到。
    try:
        from identity.registry import get_registry

        registry = get_registry()
        for company_id in list(company_ids):
            company = registry.company(company_id)
            research = str(getattr(company, "research_ticker", "") or "").upper()
            if research:
                tickers.add(research)
                if "." in research:
                    tickers.add(research.split(".", 1)[0])
    except Exception:
        pass
    return frozenset(tickers), frozenset(company_ids)


def _cmd_list(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    rows = list(store["leads"].values())
    is_default_store = (
        Path(args.leads).resolve() == leads.DEFAULT_LEADS_PATH.resolve()
    )
    if args.status:
        rows = [l for l in rows if l["status"] == args.status]
    if args.by_priority:
        try:
            held_tickers, held_company_ids = _held(strict=is_default_store)
            choke_tickers, choke_company_ids = _chokepoint(strict=is_default_store)
        except PriorityContextError as exc:
            print(f"錯誤：pq1 priority context 無法讀取：{exc}", file=sys.stderr)
            return 2
        ranked = priority.rank_leads(
            rows,
            tracked_tickers=_tracked(args.tracked),
            held_tickers=held_tickers,
            held_company_ids=held_company_ids,
            chokepoint_tickers=choke_tickers,
            chokepoint_company_ids=choke_company_ids,
        )
        rows = [lead for _score, lead in ranked]
        scores = {lead["lead_id"]: score for score, lead in ranked}
    else:
        rows.sort(key=lambda l: (l.get("published_at") or "", l["lead_id"]), reverse=True)
        scores = {}
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("（無符合 leads）")
        return 0
    for l in rows:
        tri = l.get("triage") or {}
        tag = f" [{tri.get('decision')}·tier{tri.get('tier')}]" if tri else ""
        prefix = f"[{scores[l['lead_id']]:5.1f}] " if l["lead_id"] in scores else ""
        print(f"{prefix}{l['lead_id']}  {l['status']:15}{tag}  {l['source']}")
        print(f"    {l.get('title') or '(無標題)'}  {l.get('url')}")
    return 0


def _cmd_register(args: argparse.Namespace) -> int:
    """把 weekly／手動發現註冊成 pending lead，仍走 URL-hash 冪等入口。"""
    store = leads.load(args.leads)
    try:
        lead_id, is_new = leads.register(
            store,
            source=args.source,
            url=args.url,
            title=args.title,
            published_at=args.published_at,
        )
    except ValueError as exc:
        print(f"register 失敗：{exc}", file=sys.stderr)
        return 1
    leads.save(store, args.leads)
    print(f"{lead_id}  {'new' if is_new else 'existing'}")
    return 0


def _cmd_drain(args: argparse.Namespace) -> int:
    """列出 pq1 接下來的 bounded jobs，供 agent 逐個研究與 checkpoint。

    使用者明確 dispatch 的 Decision work order 優先，再用剩餘 budget 取
    triaged_go／researching leads。命令本身不執行語意研究。
    """
    store = leads.load(args.leads)
    config = routine_config.load_config(Path(args.routine_config))
    limit = (
        args.limit
        if args.limit is not None
        else int(config["pq1"]["drain_limit_per_run"])
    )
    tracked = (
        _tracked(args.tracked)
        if args.tracked is not None
        else routine_config.discover_tracked_tickers(config)
    )
    decision_jobs: list[dict] = []
    is_default_store = (
        Path(args.leads).resolve() == leads.DEFAULT_LEADS_PATH.resolve()
    )
    include_decisions = args.decision_work_orders == "include" or (
        args.decision_work_orders == "auto"
        and is_default_store
    )
    if include_decisions and limit:
        try:
            from decision_lab.bootstrap import open_default_store

            decision_store = open_default_store()
            try:
                decision_jobs = decision_store.rank_work_orders(capacity=limit)["selected"]
            finally:
                decision_store.close()
        except Exception as exc:
            if is_default_store:
                print(f"錯誤：Decision pq1 無法讀取：{exc}", file=sys.stderr)
                return 2
            print(f"警告：Decision pq1 無法讀取：{exc}", file=sys.stderr)

    candidates = [
        l for l in store["leads"].values()
        if l["status"] in ("triaged_go", "researching")
    ]
    try:
        held_tickers, held_company_ids = _held(strict=is_default_store)
        choke_tickers, choke_company_ids = _chokepoint(strict=is_default_store)
    except PriorityContextError as exc:
        print(f"錯誤：pq1 priority context 無法讀取：{exc}", file=sys.stderr)
        return 2
    ranked = priority.rank_leads(
        candidates,
        tracked_tickers=tracked,
        held_tickers=held_tickers,
        held_company_ids=held_company_ids,
        chokepoint_tickers=choke_tickers,
        chokepoint_company_ids=choke_company_ids,
    )
    lead_batch = ranked[:max(0, limit - len(decision_jobs))]
    if args.json:
        rows = [
            {"kind": "decision_work_order", "work_order": job}
            for job in decision_jobs
        ] + [
            {"kind": "lead", "score": score, "lead": lead}
            for score, lead in lead_batch
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not decision_jobs and not lead_batch:
        print("（pq1 佇列已空——無 dispatched work order 或可研究 lead）")
        return 0
    print(f"pq1 drain：接下來 {len(decision_jobs) + len(lead_batch)} 件：")
    for job in decision_jobs:
        print(
            f"  [USER-GO] {job['work_order_id']}  {job['status']:12}  "
            f"cohort={job['cohort_id']}"
        )
        print(f"            blockers={','.join(job.get('blockers') or [])}")
    for score, l in lead_batch:
        print(f"  [{score:5.1f}] {l['lead_id']}  {l['status']:12}  {l['source']}")
        print(f"           {l.get('title') or '(無標題)'}  {l.get('url')}")
    return 0


def _cmd_triage(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    flags = {
        "contradiction": args.contradiction,
        "novelty": args.novelty,
        "independent_source": args.independent,
    }
    try:
        leads.triage(
            store, args.lead_id,
            go=args.go, tier=args.tier, reason=args.reason,
            priority_flags=flags,
        )
    except (leads.LeadStateError, ValueError) as exc:
        print(f"triage 失敗：{exc}", file=sys.stderr)
        return 1
    leads.save(store, args.leads)
    print(f"✓ {args.lead_id} → {'triaged_go' if args.go else 'triaged_no_go'}")
    return 0


def _campaign_ids(lead: dict) -> frozenset[str]:
    raw = (lead.get("refs") or {}).get("campaign_ids") or []
    return frozenset(str(item) for item in raw if str(item).strip())


def _cmd_triage_campaign(args: argparse.Namespace) -> int:
    """單次 atomic save 套用具名 campaign 決策；不改 evidence tier。"""
    store = leads.load(args.leads)
    campaign_rows = {
        lead_id: lead
        for lead_id, lead in store["leads"].items()
        if args.campaign_id in _campaign_ids(lead)
    }
    requested = list(dict.fromkeys(args.go_id or []))
    invalid = [
        lead_id
        for lead_id in requested
        if lead_id not in campaign_rows
        or campaign_rows[lead_id]["status"] != "pending"
    ]
    if invalid:
        print(
            "campaign triage 失敗：go IDs 不屬於 pending campaign："
            + ",".join(invalid),
            file=sys.stderr,
        )
        return 1
    flags = {
        "contradiction": args.contradiction,
        "novelty": args.novelty,
        "independent_source": args.independent,
        "user_requested": True,
    }
    for lead_id in requested:
        leads.triage(
            store,
            lead_id,
            go=True,
            tier=args.tier,
            reason=args.reason,
            priority_flags=flags,
        )
    filtered = 0
    if args.filter_rest:
        for lead_id, lead in campaign_rows.items():
            if lead["status"] != "pending":
                continue
            leads.triage(
                store,
                lead_id,
                go=False,
                tier=4,
                reason=args.filter_reason,
            )
            filtered += 1
    leads.save(store, args.leads)
    print(
        json.dumps(
            {
                "campaign_id": args.campaign_id,
                "passed": len(requested),
                "filtered": filtered,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _cmd_advance(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    ref = {}
    if args.ref:
        for pair in args.ref:
            key, separator, value = pair.partition("=")
            if not separator or not key.strip():
                print(f"advance 失敗：ref 必須是非空 key=value：{pair}", file=sys.stderr)
                return 1
            ref[key.strip()] = value
    try:
        leads.advance(store, args.lead_id, args.to_status, ref=ref or None)
    except (leads.LeadStateError, ValueError) as exc:
        print(f"advance 失敗：{exc}", file=sys.stderr)
        return 1
    leads.save(store, args.leads)
    print(f"✓ {args.lead_id} → {args.to_status}")
    return 0


def _cmd_annotate(args: argparse.Namespace) -> int:
    """只補 refs，不藉 metadata 更新繞過封閉狀態機。"""
    store = leads.load(args.leads)
    refs = {}
    for pair in args.ref:
        key, separator, value = pair.partition("=")
        if not separator or not key.strip():
            print(f"annotate 失敗：ref 必須是非空 key=value：{pair}", file=sys.stderr)
            return 1
        refs[key.strip()] = value
    try:
        lead = leads.annotate_refs(store, args.lead_id, refs=refs)
    except (leads.LeadStateError, ValueError) as exc:
        print(f"annotate 失敗：{exc}", file=sys.stderr)
        return 1
    leads.save(store, args.leads)
    print(f"✓ {args.lead_id} metadata updated（status={lead['status']}）")
    return 0


def _cmd_counts(args: argparse.Namespace) -> int:
    store = leads.load(args.leads)
    counts = leads.status_counts(store)
    print(json.dumps(counts, ensure_ascii=False))
    return 0


def _cmd_harvest_health(args: argparse.Namespace) -> int:
    """列出最新一次仍未恢復的來源失敗，避免 blocked 被當成零新資料。"""

    store = leads.load(args.leads)
    unresolved = leads.unresolved_harvest_failures(store)
    print(json.dumps(unresolved, ensure_ascii=False, indent=2))
    return 0


def _cmd_trace_backlog(args: argparse.Namespace) -> int:
    """列出不會被一般 drain 撿回的 parked source-trace backlog。"""

    from engine_b.entities import lead_entities

    store = leads.load(args.leads)
    rows = leads.trace_backlog(store)
    if args.manual_only:
        rows = [row for row in rows if row["requires_user"]]
    # 帶上具名標的，讓「新 lead 是否與某個 parked 有關」可以確定性比對，
    # 而不是每次都靠讀 next_trigger 自由文字用語意判斷。
    for row in rows:
        lead = (store.get("leads") or {}).get(row["lead_id"]) or {}
        row["entities"] = sorted(lead_entities(lead))
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def _cmd_related(args: argparse.Namespace) -> int:
    """列出與指定 lead 相關的 lead：第一層具名標的、第二層註冊主題。"""

    from engine_b.entities import lead_entities, related_leads
    from engine_b.themes import lead_themes, related_by_theme

    store = leads.load(args.leads)
    statuses = tuple(args.status)
    try:
        by_entity = related_leads(store, args.lead_id, statuses=statuses)
        by_theme = related_by_theme(store, args.lead_id, statuses=statuses)
    except KeyError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    target = store["leads"][args.lead_id]
    entity_ids = {m["lead_id"] for m in by_entity}
    print(json.dumps(
        {
            "lead_id": args.lead_id,
            "entities": sorted(lead_entities(target)),
            "themes": sorted(lead_themes(target)),
            "statuses_searched": list(statuses),
            # 第一層：共用具名標的（精準，召回有限）
            "by_entity": by_entity,
            # 第二層：只共用主題、沒有共用標的——這些是第一層抓不到的
            "by_theme_only": [
                m for m in by_theme if m["lead_id"] not in entity_ids
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def _cmd_backfill_entities(args: argparse.Namespace) -> int:
    """替既有 lead 補上具名標的與主題標記（一次性；register 之後會自動帶）。"""

    from engine_b.entities import backfill_entities
    from engine_b.themes import backfill_themes

    store = leads.load(args.leads)
    entities = backfill_entities(store, rescan=args.rescan)
    themes = backfill_themes(store)
    if not args.dry_run and (entities or themes):
        leads.save(store, args.leads)
    verb = "將更新" if args.dry_run else "已更新"
    print(f"{verb} entities {entities} 筆、themes {themes} 筆")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="pending leads 狀態機命令列入口")
    ap.add_argument("--leads", default=str(leads.DEFAULT_LEADS_PATH),
                    help="pending_leads.json 路徑（預設本機 authority）")
    sub = ap.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("register", help="把 weekly／手動發現註冊成 pending lead")
    p_reg.add_argument("--source", required=True)
    p_reg.add_argument("--url", required=True)
    p_reg.add_argument("--title", default="")
    p_reg.add_argument("--published-at")
    p_reg.set_defaults(func=_cmd_register)

    p_list = sub.add_parser("list", help="列出 leads")
    p_list.add_argument("--status", help="只列某狀態（pending／triaged_go…）")
    p_list.add_argument("--by-priority", dest="by_priority", action="store_true",
                        help="依 priority 排序並顯示分數")
    p_list.add_argument("--tracked", help="逗號分隔的已追蹤 ticker（thesis 影響度）")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=_cmd_list)

    p_drain = sub.add_parser("drain", help="列出 pq1 接下來該處理的 leads（依 priority）")
    p_drain.add_argument("--limit", type=int, default=None,
                         help="本輪上限；省略時讀 config/daily_routine.json")
    p_drain.add_argument("--tracked", default=None,
                         help="逗號分隔的已追蹤 ticker；省略時由 lifecycle/cohort 自動導出")
    p_drain.add_argument("--routine-config", default=str(routine_config.DEFAULT_CONFIG))
    p_drain.add_argument(
        "--decision-work-orders", choices=("auto", "include", "skip"), default="auto",
        help="是否合併使用者已核准的 Decision gap jobs；custom leads 預設不混入 production store",
    )
    p_drain.add_argument("--json", action="store_true")
    p_drain.set_defaults(func=_cmd_drain)

    p_tri = sub.add_parser("triage", help="對 pending lead 下 go／no-go")
    p_tri.add_argument("lead_id")
    grp = p_tri.add_mutually_exclusive_group(required=True)
    grp.add_argument("--go", dest="go", action="store_true")
    grp.add_argument("--no-go", dest="go", action="store_false")
    p_tri.add_argument("--tier", type=int, required=True, help="1–4（來源分級，非 evidence tier）")
    p_tri.add_argument("--reason", required=True)
    p_tri.add_argument("--contradiction", action="store_true", help="矛盾/反證價值（priority）")
    p_tri.add_argument("--novelty", action="store_true", help="新穎性（priority）")
    p_tri.add_argument("--independent", action="store_true", help="新 origin_entity/獨立來源（priority）")
    p_tri.set_defaults(func=_cmd_triage)

    p_campaign = sub.add_parser(
        "triage-campaign",
        help="原子套用具名探索 campaign 的 PASS／FILTER 決策",
    )
    p_campaign.add_argument("--campaign-id", required=True)
    p_campaign.add_argument("--go-id", action="append", default=[])
    p_campaign.add_argument("--tier", type=int, default=4)
    p_campaign.add_argument("--reason", default="具體可追查 claim，進 scoped pq1")
    p_campaign.add_argument("--contradiction", action="store_true")
    p_campaign.add_argument("--novelty", action="store_true")
    p_campaign.add_argument("--independent", action="store_true")
    p_campaign.add_argument("--filter-rest", action="store_true")
    p_campaign.add_argument(
        "--filter-reason",
        default=(
            "campaign 全量盤點後屬重複敘事、短回覆、績效／市場情緒，"
            "或缺乏可追查的增量 claim"
        ),
    )
    p_campaign.set_defaults(func=_cmd_triage_campaign)

    p_adv = sub.add_parser("advance", help="一般狀態轉移")
    p_adv.add_argument("lead_id")
    p_adv.add_argument("to_status")
    p_adv.add_argument("--ref", action="append", help="key=value，記錄關聯（如 research_action_id=ra_x）")
    p_adv.set_defaults(func=_cmd_advance)

    p_ann = sub.add_parser("annotate", help="補充 metadata，不變更 lead status")
    p_ann.add_argument("lead_id")
    p_ann.add_argument("--ref", action="append", required=True,
                       help="key=value，可重複指定")
    p_ann.set_defaults(func=_cmd_annotate)

    p_cnt = sub.add_parser("counts", help="各狀態計數（JSON）")
    p_cnt.set_defaults(func=_cmd_counts)

    p_health = sub.add_parser(
        "harvest-health",
        help="列出最新仍未恢復的 harvest 失敗（JSON）",
    )
    p_health.set_defaults(func=_cmd_harvest_health)

    p_trace = sub.add_parser(
        "trace-backlog",
        help="列出 parked 的追源未果 backlog 與下一個 trigger（JSON）",
    )
    p_trace.add_argument(
        "--manual-only", action="store_true",
        help="只列需要使用者 access／付費／優先權決策的項目",
    )
    p_trace.set_defaults(func=_cmd_trace_backlog)

    p_related = sub.add_parser(
        "related",
        help="找出與指定 lead 共用具名標的的其他 lead（確定性比對，非語意推論）",
    )
    p_related.add_argument("lead_id")
    p_related.add_argument(
        "--status", nargs="+", default=["parked"],
        help="要搜尋的狀態，預設只找 parked",
    )
    p_related.set_defaults(func=_cmd_related)

    p_backfill = sub.add_parser(
        "backfill-entities",
        help="替既有 lead 補上具名標的標記（一次性）",
    )
    p_backfill.add_argument("--dry-run", action="store_true")
    p_backfill.add_argument(
        "--rescan",
        action="store_true",
        help=(
            "重算所有 lead 的 entities，而不只補從未算過的。"
            "registry 新增公司或 alias 後必須跑一次，否則舊 lead 永遠對不上新登記的公司。"
        ),
    )
    p_backfill.set_defaults(func=_cmd_backfill_entities)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
