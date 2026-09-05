"""取數層：把各 authority 的**唯讀**輸出取好，交給 `builder.build_alpha_investment_view`。

這一支是整個 read model 唯一碰外部世界的地方（Neo4j／Engine C SQLite／Decision Store／
thesis JSON），角色同 `briefing/sources.py` 與 `engine_d_runtime/adapters.py`：
**碰 I/O 的住組裝層，純轉換住 domain。** 每個來源都 fail-soft——取不到就把原因交給
builder 標成 `missing`／附 reason，不讓整份 view 失敗，也不讓「取不到」與「沒有」同形。

不寫任何 authority、不 freeze context、不建 decision、不改 thesis。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from alpha.context import ContextBuild, build_research_context
from alpha.contracts import AlphaSignal
from alpha.errors import AlphaError, ContractViolation, PointInTimeUnsupported
from alpha.identity import CompanyId, Ticker
from alpha.models import compose_signal
from identity.registry import get_registry

from .builder import DecisionFacts, build_alpha_investment_view, compact_card
from .contracts import AlphaInvestmentView

_ROOT = Path(__file__).resolve().parents[2]
#: session 判斷檔的約定位置（private，不進 Git）。先找專用目錄，再找舊命名。
JUDGMENT_DIR = _ROOT / "library" / "private" / "alpha" / "judgments"
LEGACY_JUDGMENT_DIR = _ROOT / "library" / "private" / "alpha"
DECISION_DB = _ROOT / "library" / "private" / "decision_lab" / "decision_lab.db"
LIFECYCLE_PATH = _ROOT / "thesis" / "lifecycle.json"

#: 結構事件回看窗（天）。只影響 causal section 的事件／二階影響清單，不影響任何分數。
STRUCTURAL_EVENT_LOOKBACK_DAYS = 180


def resolve_company(ticker: str) -> tuple[Ticker, CompanyId]:
    """ticker → `CompanyId`，**經 registry，不猜**（INV-1）。"""
    registry = get_registry()
    wanted = ticker.strip().upper()
    company_id = registry.company_id_for_ticker(wanted)
    if not company_id:
        raise AlphaError(
            f"registry 找不到 research_ticker={ticker!r}。"
            "⚠ 「找不到」與「不存在」是兩個 claim——請先確認它是否需要 onboard"
        )
    return Ticker(str(registry.research_ticker(company_id) or wanted)), CompanyId(str(company_id))


def locate_judgment(ticker: str) -> Path | None:
    candidates = (
        JUDGMENT_DIR / f"{ticker.upper()}.json",
        LEGACY_JUDGMENT_DIR / f"{ticker.lower()}_judgment.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _compose_signal(
    build: ContextBuild, judgment_path: Path | None, *, allow_stale: bool,
) -> tuple[AlphaSignal | None, str | None]:
    """讀 session 判斷檔並組成 `AlphaSignal`；失敗回 `(None, 原因)`。"""
    if judgment_path is None:
        return None, "找不到 session 判斷檔（library/private/alpha/judgments/<TICKER>.json）"
    try:
        judgment = json.loads(judgment_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"判斷檔無法讀取：{type(exc).__name__}"
    try:
        return compose_signal(build, judgment, allow_stale_context=allow_stale), None
    except ContractViolation as exc:
        return None, f"判斷檔未通過契約驗證：{str(exc)[:200]}"


def _decision_facts(company_id: str, *, as_of: date | None) -> tuple[DecisionFacts | None, str | None]:
    """Engine D 的公開 cohort 事實。

    - **唯讀 sqlite 連線**（`mode=ro`），與 `scripts/catalyst_watch.py` 同一條窄路徑；
      不開可寫的 `DecisionStore`。
    - schema 知識住 Engine D 自己的 `decision_lab.coverage_queries.company_decision_facts`，
      這裡不寫 SQL；該函式只回研究欄位，部位／NAV／cap 一個都不會出現。
    - `as_of` 非 None 時做**歷史過濾**（Decision Store 每張表都帶時間戳，答得出「T 時刻
      知道什麼」），回傳值帶 `point_in_time_as_of`，builder 會核對它與 context.as_of 相符。
    """
    if not DECISION_DB.is_file():
        return None, "本機沒有 Decision Store"
    try:
        from decision_lab.coverage_queries import company_decision_facts

        conn = sqlite3.connect(f"file:{DECISION_DB.as_posix()}?mode=ro", uri=True)
    except Exception as exc:  # noqa: BLE001 — surface 缺席只降級
        return None, f"Decision Store 無法開啟：{type(exc).__name__}"
    conn.row_factory = sqlite3.Row
    try:
        facts = company_decision_facts(
            conn, company_id, as_of=as_of.isoformat() if as_of else None)
    except Exception as exc:  # noqa: BLE001
        return None, f"Decision Store 讀取失敗：{type(exc).__name__}"
    finally:
        conn.close()
    if facts is None:
        return None, (f"截至 as-of {as_of.isoformat()}，Engine D 尚無此公司的 cohort（歷史過濾後為空）"
                      if as_of else "Engine D 沒有這家公司的 cohort")
    point_in_time = dict(facts.pop("point_in_time", None) or {})
    facts["point_in_time_mode"] = point_in_time.get("mode")
    facts["point_in_time_as_of"] = point_in_time.get("as_of")
    allowed = {f.name for f in DecisionFacts.__dataclass_fields__.values()}
    return DecisionFacts(**{k: v for k, v in facts.items() if k in allowed}), None


def _thesis_lifecycle_entry(ticker: str) -> Mapping[str, Any] | None:
    if not LIFECYCLE_PATH.is_file():
        return None
    try:
        raw = json.loads(LIFECYCLE_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    for entry in raw.values():
        if isinstance(entry, Mapping) and str(entry.get("ticker") or "").upper() == ticker.upper():
            return entry
    return None


def _causal_inputs(graph: Any, company_id: CompanyId, *, as_of: date | None, today: date) -> dict[str, Any]:
    """依賴／替代路徑、供應鏈曝險、近 N 天結構事件與二階影響。每一項各自 fail-soft。"""
    out: dict[str, Any] = {
        "dependency_paths": (), "substitution_paths": (), "supply_exposure": (),
        "impacts": (), "structural_events": (), "causal_reason": None,
    }
    reasons: list[str] = []
    try:
        out["dependency_paths"] = tuple(graph.get_dependency_paths(company_id, as_of=as_of))
        out["substitution_paths"] = tuple(graph.get_substitution_paths(company_id, as_of=as_of))
        out["supply_exposure"] = tuple(graph.get_supply_exposure(company_id, direction="upstream", as_of=as_of)) \
            + tuple(graph.get_supply_exposure(company_id, direction="downstream", as_of=as_of))
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"路徑／曝險取得失敗：{type(exc).__name__}")
    since = (as_of or today) - timedelta(days=STRUCTURAL_EVENT_LOOKBACK_DAYS)
    try:
        own_events = tuple(graph.get_structural_changes_since(since, company_id=company_id))
        out["structural_events"] = own_events
        all_events = graph.get_structural_changes_since(since)
        impacts = []
        for event in all_events:
            for impact in (*graph.get_second_order_beneficiaries(event),
                           *graph.get_second_order_victims(event)):
                if str(impact.company_id) == str(company_id):
                    impacts.append(impact)
        out["impacts"] = tuple(impacts)
    except PointInTimeUnsupported as exc:
        reasons.append(f"結構事件需要 as-of 投影而投影不可用：{str(exc)[:120]}")
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"結構事件／二階影響取得失敗：{type(exc).__name__}")
    out["causal_reason"] = "；".join(reasons) or None
    return out


def _ranking_position(graph: Any, company_id: CompanyId, *, as_of: date | None) -> Mapping[str, Any] | None:
    try:
        rows = list(graph.get_bottlenecks(as_of=as_of))
    except Exception:  # noqa: BLE001
        return None
    rank = None
    for index, row in enumerate(rows, 1):
        if str(row.company_id) == str(company_id):
            rank = index
            break
    return {"actionable_rank": rank, "actionable_total": len(rows)}


def fetch_alpha_investment_view(
    ticker: str,
    *,
    as_of: date | None = None,
    judgment_path: Path | None = None,
    allow_stale_judgment: bool = True,
    include_causal: bool = True,
    today: date | None = None,
    graph_provider: Any = None,
    fundamentals_provider: Any = None,
) -> AlphaInvestmentView:
    """單一公司的完整 view。`graph_provider`／`fundamentals_provider` 可注入（測試用）。"""
    today = today or date.today()
    resolved_ticker, company_id = resolve_company(ticker)
    registry = get_registry()
    company = registry.company(str(company_id))
    identity = {
        "market_currency": getattr(company, "market_currency", None),
        "market_quote_unit": getattr(company, "market_quote_unit", None),
        "execution_venue": getattr(company, "execution_venue", None),
    }

    owns_graph = graph_provider is None
    if graph_provider is None:
        from alpha.providers.graph_neo4j import open_default_provider

        graph_provider = open_default_provider()
    if fundamentals_provider is None:
        from alpha.providers.fundamentals import EngineCFundamentalsProvider

        fundamentals_provider = EngineCFundamentalsProvider()
    try:
        build = build_research_context(
            ticker=resolved_ticker, company_id=company_id,
            graph_provider=graph_provider, fundamentals_provider=fundamentals_provider,
            as_of=as_of,
        )
        signal, signal_reason = _compose_signal(
            build, judgment_path or locate_judgment(str(resolved_ticker)),
            allow_stale=allow_stale_judgment,
        )
        revision_fn = getattr(fundamentals_provider, "estimate_revision", None)
        estimate_revision = revision_fn(resolved_ticker, as_of=as_of) if callable(revision_fn) else None
        causal = (_causal_inputs(graph_provider, company_id, as_of=as_of, today=today)
                  if include_causal else {"causal_reason": "本次未取因果路徑（--no-causal）"})
        ranking_position = _ranking_position(graph_provider, company_id, as_of=as_of)
    finally:
        if owns_graph:
            driver = getattr(graph_provider, "driver", None)
            close = getattr(driver, "close", None)
            if callable(close):
                close()

    decision_facts, decision_reason = _decision_facts(str(company_id), as_of=as_of)
    # thesis/lifecycle.json 與 catalyst_calendar.json 是當前狀態檔，沒有歷史；as-of 模式不讀，
    # builder 端也會再擋一次（雙保險，讓「忘了在這裡跳過」不會變成靜默的當前值）。
    checkpoints: list[Mapping[str, Any]] = []
    lifecycle_entry: Mapping[str, Any] | None = None
    if as_of is None:
        try:
            from thesis.lifecycle_schedule import checkpoints_by_ticker

            checkpoints = checkpoints_by_ticker().get(str(resolved_ticker), [])
        except Exception:  # noqa: BLE001
            checkpoints = []
        lifecycle_entry = _thesis_lifecycle_entry(str(resolved_ticker))
    checkpoint_source = "thesis://lifecycle.json" if lifecycle_entry else "thesis://catalyst_calendar.json"
    try:
        from engine_c.checklist import get_checklist

        checklist = get_checklist(str(resolved_ticker))
    except Exception as exc:  # noqa: BLE001
        checklist = {"engine_c_available": False, "note": f"checklist 讀取失敗：{type(exc).__name__}"}

    return build_alpha_investment_view(
        build=build, signal=signal, signal_reason=signal_reason,
        dependency_paths=causal.get("dependency_paths", ()),
        substitution_paths=causal.get("substitution_paths", ()),
        supply_exposure=causal.get("supply_exposure", ()),
        impacts=causal.get("impacts", ()), structural_events=causal.get("structural_events", ()),
        causal_reason=causal.get("causal_reason"),
        ranking_position=ranking_position, estimate_revision=estimate_revision,
        decision_facts=decision_facts, decision_facts_reason=decision_reason,
        catalyst_checkpoints=checkpoints, checkpoint_source=checkpoint_source,
        thesis_lifecycle=lifecycle_entry, checklist=checklist, identity=identity, today=today,
    )


def tickers_from_ranking(ranking: Mapping[str, Any] | None, *, limit: int = 5) -> list[str]:
    """由 `alpha.ranking.build_ranking_view` 的輸出取可行動排序前段的 ticker（去重、保序）。

    ⚠ 順序＝排序權威的順序，本函式不重排。
    """
    if not ranking:
        return []
    seen: list[str] = []
    for row in ranking.get("actionable") or []:
        ticker = row.get("ticker")
        if ticker and str(ticker) not in seen:
            seen.append(str(ticker))
        if len(seen) >= limit:
            break
    return seen


def fetch_alpha_cards(
    tickers: Iterable[str], *, today: date | None = None,
    graph_provider: Any = None, fundamentals_provider: Any = None,
) -> list[dict[str, Any]]:
    """Daily Brief 用：每檔一張精簡卡。單檔失敗只降級成 `status=unavailable` 那一列，
    不丟掉、不阻斷（INV-3）。

    provider **整批共用一份**：Neo4j provider 會把 `rank_bottlenecks()` 快取在 instance 上，
    每檔各開一個 driver 等於把 663 條 assertion 的排序算 N 次。呼叫端沒注入時這裡開一次、
    最後關一次。
    """
    tickers = list(tickers)
    if not tickers:
        return []
    owns_graph = graph_provider is None
    if graph_provider is None:
        try:
            from alpha.providers.graph_neo4j import open_default_provider

            graph_provider = open_default_provider()
        except Exception as exc:  # noqa: BLE001 — 圖開不了就每檔都 unavailable，原因帶著
            return [{"ticker": str(t), "status": "unavailable", "reason": type(exc).__name__}
                    for t in tickers]
    if fundamentals_provider is None:
        from alpha.providers.fundamentals import EngineCFundamentalsProvider

        fundamentals_provider = EngineCFundamentalsProvider()
    cards: list[dict[str, Any]] = []
    try:
        for ticker in tickers:
            try:
                view = fetch_alpha_investment_view(
                    str(ticker), today=today, include_causal=False,
                    graph_provider=graph_provider, fundamentals_provider=fundamentals_provider,
                )
                cards.append(compact_card(view))
            except Exception as exc:  # noqa: BLE001 — 一檔讀不到不讓整個摘要消失
                cards.append({"ticker": str(ticker), "status": "unavailable",
                              "reason": type(exc).__name__})
    finally:
        if owns_graph:
            driver = getattr(graph_provider, "driver", None)
            close = getattr(driver, "close", None)
            if callable(close):
                close()
    return cards


__all__ = [
    "DECISION_DB", "JUDGMENT_DIR", "LEGACY_JUDGMENT_DIR", "STRUCTURAL_EVENT_LOOKBACK_DAYS",
    "fetch_alpha_cards", "fetch_alpha_investment_view", "locate_judgment", "resolve_company",
    "tickers_from_ranking",
]
