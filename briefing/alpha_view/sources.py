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
from alpha.entry import (
    CRITERION_BASIS_INVESTOR_POLICY, EntryAssessmentResult, build_entry_assessment, entry_criterion_record,
    parse_entry_criterion_record,
)
from alpha.errors import AlphaError, ContractViolation, PointInTimeUnsupported
from alpha.fundamental import FundamentalModelResult, build_fundamental_model
from alpha.identity import CompanyId, Ticker
from alpha.implied_return import ImpliedReturnResult, build_implied_return
from alpha.models import compose_signal
from alpha.providers import assumptions as assumption_ledger
from alpha.providers import entry_criteria as entry_ledger
from alpha.providers import horizon_assumptions as horizon_ledger
from alpha.providers import valuation_assumptions as valuation_ledger
from alpha.refresh import build_instant
from alpha.valuation import CurrentPrice, ValuationResult, build_valuation
from identity.registry import get_registry

from .builder import DecisionFacts, build_alpha_investment_view, compact_card
from .changes import baseline_since, detect_changes, load_watches
from .contracts import AlphaInvestmentView
from .scenarios import SCENARIOS, rollover_actuals, scenario_changes

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


def _fundamental_model(
    build: ContextBuild, fundamentals_provider: Any, ticker: Ticker, company_id: CompanyId,
    *, as_of: date | None, today: date, actuals_override: Any = None,
) -> tuple[FundamentalModelResult | None, str | None, list[Any]]:
    """Causal Fundamental Model 的取數與執行（Phase 2）。

    - 觀測（`fiscal_year_results`）、指引（`company_guidance`）、會計年度別共識
      （`consensus_estimates`）全部由 Engine C provider 唯讀取出；假設由 private ledger
      （`alpha/providers/assumptions.py`）讀出。本檔不算任何數字——算術在 `alpha.fundamental`。
    - provider 沒有這三個方法（測試用的假 provider）→ `(None, 原因)`，read model 標 missing。
    - 任何一段失敗都 fail-soft，原因交給 builder。
    """
    fetch_results = getattr(fundamentals_provider, "fiscal_year_results", None)
    fetch_consensus = getattr(fundamentals_provider, "fiscal_consensus", None)
    fetch_guidance = getattr(fundamentals_provider, "company_guidance", None)
    records: list[Any] = []
    try:
        records, parse_errors = assumption_ledger.read_assumption_records(str(ticker))
    except Exception as exc:  # noqa: BLE001
        return None, f"假設 ledger 讀取失敗：{type(exc).__name__}", records
    if not all(callable(f) for f in (fetch_results, fetch_consensus, fetch_guidance)):
        return None, "fundamentals provider 沒有 fiscal_year_results／fiscal_consensus／company_guidance 能力", records
    try:
        actuals, actuals_reason = fetch_results(ticker, as_of=as_of)
        if actuals_override is not None:
            actuals, actuals_reason = actuals_override, None
        consensus, _consensus_reason = fetch_consensus(ticker, as_of=as_of)
        guidance, _guidance_reason = fetch_guidance(ticker, as_of=as_of)
        model = build_fundamental_model(
            company_id=str(company_id), ticker=str(ticker), as_of=as_of, today=today,
            actuals=actuals, actuals_reason=actuals_reason, consensus=consensus, guidance=guidance,
            assumption_records=records, parse_errors=parse_errors,
            evidence_index={ref.ref: ref for ref in build.context.evidence_refs},
        )
    except Exception as exc:  # noqa: BLE001 — 模型失敗只讓該區 missing，不讓整份 view 失敗
        return None, f"fundamental model 執行失敗：{type(exc).__name__}: {str(exc)[:160]}", records
    return model, None, records


def _valuation_model(
    build: ContextBuild, fundamental_model: FundamentalModelResult | None, fundamental_reason: str | None,
    ticker: Ticker, company_id: CompanyId, *, as_of: date | None, today: date,
    identity: Mapping[str, Any],
) -> tuple[ValuationResult | None, str | None, list[Any]]:
    """Valuation Model v1（Step 1）的取數與執行。

    - 估值假設由 private ledger（`alpha/providers/valuation_assumptions.py`）讀出；
      內部 EPS 是已經跑好的 fundamental model；現價是 `build.context.market`（Engine C，已依 as-of 過濾）。
    - 本檔不算任何數字——算術在 `alpha.valuation`。任何一段失敗都 fail-soft，原因交給 builder。
    - 現價的報價單位取自 registry（`market_quote_unit`／`market_currency`）；不知道就留 None，
      估值層會拒絕算 gap（報價單位 ≠ 結算幣別，不猜）。
    """
    records: list[Any] = []
    try:
        records, parse_errors = valuation_ledger.read_valuation_assumption_records(str(ticker))
    except Exception as exc:  # noqa: BLE001
        return None, f"估值假設 ledger 讀取失敗：{type(exc).__name__}", records
    price = _current_price(build, identity)
    try:
        result = build_valuation(
            company_id=str(company_id), ticker=str(ticker), as_of=as_of, today=today,
            fundamental=fundamental_model, fundamental_reason=fundamental_reason,
            assumption_records=records, parse_errors=parse_errors,
            evidence_index={ref.ref: ref for ref in build.context.evidence_refs}, price=price,
        )
    except Exception as exc:  # noqa: BLE001 — 估值失敗只讓該區 missing，不讓整份 view 失敗
        return None, f"valuation model 執行失敗：{type(exc).__name__}: {str(exc)[:160]}", records
    return result, None, records


def _current_price(build: ContextBuild, identity: Mapping[str, Any]) -> CurrentPrice:
    """Engine C 現價（已依 as-of 過濾）；估值層與報酬層共用**同一個**物件，不各取一份。"""
    market = build.context.market
    return CurrentPrice(
        value=market.price, bar_date=market.bar_date,
        unit=(market.currency or identity.get("market_quote_unit") or identity.get("market_currency")),
        evidence_refs=tuple(r.ref for r in market.evidence),
        reason=None if market.price is not None else "Engine C 無現價快照",
    )


def _implied_return_model(
    build: ContextBuild, valuation: ValuationResult | None, valuation_reason: str | None,
    ticker: Ticker, company_id: CompanyId, *, as_of: date | None, today: date, identity: Mapping[str, Any],
) -> tuple[ImpliedReturnResult | None, str | None, list[Any]]:
    """Base-case Implied Return v1（Step 2）的取數與執行。

    - horizon 判斷由 private ledger（`alpha/providers/horizon_assumptions.py`）讀出；fair value 是已經跑好的
      valuation；現價與估值層共用同一個 `CurrentPrice`。本檔不算任何數字——算術在 `alpha.implied_return`。
    - 任何一段失敗都 fail-soft，原因交給 builder。
    """
    records: list[Any] = []
    try:
        records, parse_errors = horizon_ledger.read_horizon_assumption_records(str(ticker))
    except Exception as exc:  # noqa: BLE001
        return None, f"horizon 假設 ledger 讀取失敗：{type(exc).__name__}", records
    try:
        result = build_implied_return(
            company_id=str(company_id), ticker=str(ticker), as_of=as_of, today=today,
            valuation=valuation, valuation_reason=valuation_reason, horizon_records=records, parse_errors=parse_errors,
            evidence_index={ref.ref: ref for ref in build.context.evidence_refs}, price=_current_price(build, identity),
        )
    except Exception as exc:  # noqa: BLE001 — 報酬失敗只讓該區 missing，不讓整份 view 失敗
        return None, f"implied return model 執行失敗：{type(exc).__name__}: {str(exc)[:160]}", records
    return result, None, records


def _entry_model(
    build: ContextBuild, implied_return: ImpliedReturnResult | None, implied_return_reason: str | None,
    ticker: Ticker, company_id: CompanyId, *, as_of: date | None, today: date, identity: Mapping[str, Any],
    sandbox_hurdle: float | None = None,
) -> tuple[EntryAssessmentResult | None, str | None, list[Any]]:
    """Entry Logic v1（Step 3）的取數與執行。

    - 要求報酬判準由 private ledger（`alpha/providers/entry_criteria.py`）讀出；implied return 是已經跑好的結果。
      本檔不算任何數字——算術在 `alpha.entry`。任何一段失敗都 fail-soft，原因交給 builder。
    - `sandbox_hurdle`：**非持久**驗算——只在記憶體疊一筆 `author=sandbox` 的判準交給模型，**不寫 ledger、不進
      變更偵測**（ledger 的 append 入口也拒收 sandbox）。回傳的第三個值仍是 ledger 裡的真紀錄。
    """
    records: list[Any] = []
    try:
        records, parse_errors = entry_ledger.read_entry_criterion_records(str(ticker))
    except Exception as exc:  # noqa: BLE001
        return None, f"entry criterion ledger 讀取失敗：{type(exc).__name__}", records
    model_records = list(records)
    if sandbox_hurdle is not None:
        try:
            sandbox = parse_entry_criterion_record(entry_criterion_record(
                company_id=str(company_id), ticker=str(ticker), value=float(sandbox_hurdle),
                basis=CRITERION_BASIS_INVESTOR_POLICY, rationale="sandbox 驗算（非持久；未寫入 ledger，不是使用者宣告的政策）",
                author="sandbox", created_at=build_instant(as_of or today)))
        except ContractViolation as exc:
            return None, f"sandbox hurdle 不合法：{exc}", records
        model_records.append(sandbox)
    try:
        result = build_entry_assessment(
            company_id=str(company_id), ticker=str(ticker), as_of=as_of, today=today,
            implied_return=implied_return, implied_return_reason=implied_return_reason,
            criterion_records=model_records, parse_errors=parse_errors, price=_current_price(build, identity),
        )
    except Exception as exc:  # noqa: BLE001 — entry 失敗只讓該區 missing，不讓整份 view 失敗
        return None, f"entry model 執行失敗：{type(exc).__name__}: {str(exc)[:160]}", records
    return result, None, records


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
    detect_refresh: bool = True,
    scenario: str | None = None,
    watches: Sequence[Mapping[str, Any]] | None = None,
    sandbox_hurdle: float | None = None,
) -> AlphaInvestmentView:
    """單一公司的完整 view。`graph_provider`／`fundamentals_provider` 可注入（測試用）。

    Step 0.5：預設跑 authority 變更偵測（`changes.detect_changes`）並把 `ChangeEvent` 交給 builder；
    `scenario` 指定時在真實 state 上疊一件假想變化（`scenarios.py`），refresh section 標 `scenario`。
    Step 3：`sandbox_hurdle` 只在記憶體疊一筆非持久的 entry criterion 驗算，不寫任何 authority。
    """
    if scenario is not None and scenario not in SCENARIOS:
        raise AlphaError(f"未知情境 {scenario!r}；已知 {SCENARIOS}")
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
        fundamental_model, fundamental_reason, records = _fundamental_model(
            build, fundamentals_provider, resolved_ticker, company_id, as_of=as_of, today=today)
        if scenario == "fiscal_rollover" and fundamental_model is not None and fundamental_model.target_period:
            # 會計期間推進不是一件事件，是「時間走到了目標期間之後、實際值出爐」。模型的 PIT 自我核對會
            # 正確拒絕「今天就有 FY2027 實際值」，所以情境必須把 today 推進到該年度結束後（財報約 45 天後）。
            today = max(today, fundamental_model.target_period.end + timedelta(days=45))
            override = rollover_actuals(fundamental_model, today=today)
            if override is not None:
                fundamental_model, fundamental_reason, records = _fundamental_model(
                    build, fundamentals_provider, resolved_ticker, company_id, as_of=as_of, today=today,
                    actuals_override=override)
        valuation_model, valuation_reason, valuation_records = _valuation_model(
            build, fundamental_model, fundamental_reason, resolved_ticker, company_id, as_of=as_of, today=today,
            identity=identity)
        implied_return_model, implied_return_reason, horizon_records = _implied_return_model(
            build, valuation_model, valuation_reason, resolved_ticker, company_id, as_of=as_of, today=today,
            identity=identity)
        entry_model, entry_reason, entry_records = _entry_model(
            build, implied_return_model, implied_return_reason, resolved_ticker, company_id, as_of=as_of, today=today,
            identity=identity, sandbox_hurdle=sandbox_hurdle)
        # ---- Refresh：由 authority 時序導出 ChangeEvent（只偵測，不判 impact）---------------------
        refresh_changes = None
        metric_observations: list[Any] = []
        refresh_notes: list[str] = []
        detection = None
        if detect_refresh:
            judged_on = None
            if signal is not None:
                raw = (signal.metadata or {}).get("judged_at")
                try:
                    judged_on = date.fromisoformat(str(raw)[:10]) if raw else signal.as_of
                except ValueError:
                    judged_on = signal.as_of
            since = baseline_since(judged_on, [*records, *valuation_records, *horizon_records, *entry_records])
            lifecycle_for_refresh = _thesis_lifecycle_entry(str(resolved_ticker)) if as_of is None else None
            try:
                refresh_changes, metric_observations, refresh_notes = detect_changes(
                    ticker=str(resolved_ticker), company_id=str(company_id), since=since, today=today,
                    as_of=as_of, fundamentals_provider=fundamentals_provider, graph_provider=graph_provider,
                    assumption_records=records, lifecycle_entry=lifecycle_for_refresh,
                    watches=(list(watches) if watches is not None else load_watches()),
                    ticker_obj=resolved_ticker, valuation_records=valuation_records,
                    horizon_records=horizon_records, entry_records=entry_records)
            except Exception as exc:  # noqa: BLE001 — 偵測失敗不讓 view 失敗，但必須現形（not_run）
                refresh_changes, metric_observations = None, []
                refresh_notes = [f"變更偵測失敗：{type(exc).__name__}: {str(exc)[:120]}"]
        if sandbox_hurdle is not None:
            refresh_notes = [f"sandbox hurdle {float(sandbox_hurdle):+.1%} 只疊在記憶體（author=sandbox）：未寫入任何 authority、"
                             "不進變更偵測；ledger 裡的判準（若有）在本次視角被它取代", *refresh_notes]
        if scenario is not None:
            extra, extra_obs = scenario_changes(
                scenario, ticker=str(resolved_ticker), company_id=str(company_id), context=build.context,
                model=fundamental_model, today=today)
            refresh_changes = list(refresh_changes or ()) + extra
            metric_observations = list(metric_observations) + extra_obs
            detection = "scenario"
            refresh_notes = [f"情境 {scenario}：在真實 state 上疊加假想變化（不寫任何 authority）"
                             + (f"；today 推進到 {today}（目標年度結束後 45 天）" if scenario == "fiscal_rollover" else ""),
                             *refresh_notes]
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
        thesis_lifecycle=lifecycle_entry, checklist=checklist, identity=identity,
        fundamental_model=fundamental_model, fundamental_model_reason=fundamental_reason,
        valuation=valuation_model, valuation_reason=valuation_reason, valuation_records=valuation_records,
        implied_return=implied_return_model, implied_return_reason=implied_return_reason, horizon_records=horizon_records,
        entry=entry_model, entry_reason=entry_reason, entry_records=entry_records,
        today=today,
        refresh_changes=refresh_changes, assumption_records=records,
        metric_observations=metric_observations, change_detection=detection,
        refresh_notes=refresh_notes,
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
