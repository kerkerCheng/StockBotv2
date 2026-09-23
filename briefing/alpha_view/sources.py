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
from alpha.fundamental.compare import verify_consensus_basis
from alpha.identity import CompanyId, Ticker
from alpha.models import compose_signal
from alpha.providers import assumptions as assumption_ledger
from alpha.providers import briefs as brief_ledger
from alpha.providers import abstentions as abstention_ledger
from identity.registry import get_registry

from .builder import DecisionFacts, build_alpha_investment_view, compact_card
from .changes import baseline_since, detect_changes, load_watches
from .contracts import AlphaInvestmentView
from .scenarios import SCENARIOS, scenario_changes

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


def _engine_c_financials(
    fundamentals_provider: Any, ticker: Ticker, *, as_of: date | None, today: date,
) -> dict[str, Any]:
    """Engine C 的基期觀測（`fiscal_year_results`）與會計年度別共識（`fiscal_consensus`）——**只取數，不算數**。

    ⚠ 2026-09-23（Phase 0 Step 0b.1b，C／H 組）：這裡原本是 `_fundamental_model()`——讀假設 ledger、
    取觀測／共識／指引，然後跑 `build_fundamental_model`（FY+1 因果橋）。橋退役了，**資料留**：
    基期觀測是報表幣別的身分來源（不得回退到報價幣別），共識是三題「已定價」要用的東西。
    模型原本做的 PIT 自我核對（INV-6）搬到這裡，一條不少：
    - 基期觀測的 `recorded_at` 晚於 T、或會計年度在 T 之後才結束 → 拒用；
    - 共識的 `captured_at`（bar_date）與 `fetched_at` 任一晚於 T → 排除並計數。
    口徑核實（`verify_consensus_basis`）是資料層的機械比對，不是判斷。
    provider 沒有這兩個方法（測試用的假 provider）→ 全空＋原因，read model 標 missing。
    """
    out: dict[str, Any] = {"actuals": None, "consensus": (), "bases": {}, "target_period": None, "reason": None,
                           "evidence": ()}
    fetch_results = getattr(fundamentals_provider, "fiscal_year_results", None)
    fetch_consensus = getattr(fundamentals_provider, "fiscal_consensus", None)
    fetch_guidance = getattr(fundamentals_provider, "company_guidance", None)
    fetch_interim = getattr(fundamentals_provider, "interim_period_results", None)
    if not (callable(fetch_results) and callable(fetch_consensus)):
        out["reason"] = "fundamentals provider 沒有 fiscal_year_results／fiscal_consensus 能力"
        return out
    cutoff = as_of or today
    notes: list[str] = []
    try:
        actuals, actuals_reason = fetch_results(ticker, as_of=as_of)
        consensus, consensus_reason = fetch_consensus(ticker, as_of=as_of)
        # 指引與目標年度已報導的 YTD 實績：**不進任何數字**，只讓假設的 `evidence_refs` 解析得到
        # （假設常引用它們；解析不到會被判 unresolved_evidence）。provider 沒這能力就空。
        guidance = fetch_guidance(ticker, as_of=as_of)[0] if callable(fetch_guidance) else ()
        interim = fetch_interim(ticker, as_of=as_of)[0] if callable(fetch_interim) else ()
    except Exception as exc:  # noqa: BLE001 — 取不到只讓那幾格 missing，不讓整份 view 失敗
        out["reason"] = f"Engine C 會計年度別資料讀取失敗：{type(exc).__name__}: {str(exc)[:120]}"
        return out
    if actuals is not None:
        if actuals.recorded_at is not None and actuals.recorded_at.date() > cutoff:
            actuals, actuals_reason = None, "基期觀測寫入時間晚於 as_of（lookahead，拒用；INV-6）"
        elif actuals.period.end > cutoff:
            actuals, actuals_reason = None, "基期會計年度在 as_of 之後才結束（lookahead，拒用；INV-6）"

    def _known_by_cutoff(item: Any) -> bool:
        captured = getattr(item, "captured_at", None)
        fetched = getattr(item, "fetched_at", None)
        if captured is not None and captured > cutoff:
            return False
        if fetched is not None and fetched.date() > cutoff:
            return False
        return True

    usable = tuple(c for c in (consensus or ()) if _known_by_cutoff(c))
    usable_guidance = tuple(g for g in (guidance or ()) if getattr(g, "issued_at", None) is None or g.issued_at <= cutoff)
    usable_interim = tuple(i for i in (interim or ())
                           if getattr(i, "period_end", None) is None or i.period_end <= cutoff)
    if len(usable) != len(consensus or ()):
        notes.append(f"{len(consensus) - len(usable)} 筆共識晚於 as_of（captured_at 或 fetched_at 在 T 之後），排除")
    # 「目標期間」＝最近一個已報導年度的下一年（與退役前的模型同一條規則：`actuals.period.shifted(1)`）；
    # 沒有基期觀測就取共識裡最早的那一期。它只用來挑共識時序（gap_closure），不推任何數字。
    target = actuals.period.shifted(1) if actuals is not None else (
        min((c.period for c in usable), key=lambda per: per.end) if usable else None)
    evidence: list[Any] = []
    for source in ((actuals.evidence if actuals is not None else ()), *(c.evidence for c in usable),
                   *(getattr(g, "evidence", ()) for g in usable_guidance),
                   *(getattr(i, "evidence", ()) for i in usable_interim)):
        evidence.extend(source)
    out.update(
        actuals=actuals, consensus=usable, target_period=target, evidence=tuple(evidence),
        bases={f"{c.metric}:{c.period.end.isoformat()}": verify_consensus_basis(c, actuals) for c in usable},
        reason=("；".join([*notes, *(r for r in (actuals_reason, consensus_reason) if r)]) or None),
    )
    return out


def _read_abstentions(ticker: str) -> list[Any]:
    """`alpha/abstention/` 的 append-only ledger。**讀不到就是沒有**——

    不得因為讀取失敗而把「刻意不主張」降級成「還沒寫」：那正是這本 ledger 要消除的兩義。
    兩個消費端（估值層的 target_pe、研究層的 catalyst 軸）共用這一支，不各讀一份（L16）。
    """
    try:
        records, _errors = abstention_ledger.read_abstention_records(str(ticker))
        return list(records)
    except Exception:  # noqa: BLE001
        return []


# ⚠ **2026-09-23（Phase 0 Step 0b.1b，C／H 組）：`_valuation_model`／`_select_method`／`_has_method_records`／
# `_balance_input`／`_current_price`／`_implied_return_model` 整組退役**（估值假設 ledger、horizon ledger、
# fair value、隱含報酬的取數與執行，約 170 行）。`variant_absence`／`downside_absence`（E 組的兩種「沒有」）
# 同批移除——它們沒有呼叫端了。三本 ledger 檔案留在 `library/private/alpha/`（L10），但沒有任何消費端。


# ⚠ 2026-09-23（Phase 0 Step 0b.3）：`_ranking_position`（可行動排序名次）與 `tickers_from_ranking`
# （由排序前段挑 Alpha Card 的標的）隨跨檔排序退役（G1／L19）。


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
    ⚠ 2026-09-23（Phase 0 Step 0b.1b）：`sandbox_hurdle` 隨 F 組（entry criterion）退役，已無作用。
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
        "display_name": getattr(company, "display_name", None),
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
        try:
            records, _ = assumption_ledger.read_assumption_records(str(resolved_ticker))
        except Exception:  # noqa: BLE001 — 假設 ledger 讀不到只影響催化劑熟成度與 refresh，不讓 view 失敗
            records = []
        financials = _engine_c_financials(fundamentals_provider, resolved_ticker, as_of=as_of, today=today)
        # ---- V2（2026-09-15）gap closure：目標期間的共識 EPS 時序。provider 沒這能力就空。
        consensus_history: tuple = ()
        fetch_history = getattr(fundamentals_provider, "fiscal_consensus_history", None)
        if callable(fetch_history) and financials["target_period"] is not None:
            try:
                consensus_history, _history_reason = fetch_history(
                    resolved_ticker, metric="eps", period_end=financials["target_period"].end, as_of=as_of)
            except Exception:  # noqa: BLE001 — 拿不到時序只讓那一格 missing
                consensus_history = ()
        # ---- 論證層（2026-09-15）：節點人話名字＋claim 引文。provider 沒這能力（測試用假 provider）就空。
        narrative_context: Mapping[str, Any] = {}
        fetch_narrative = getattr(graph_provider, "get_narrative_context", None)
        if callable(fetch_narrative):
            try:
                node_ids = [str(e.get("target")) for e in build.context.graph.edges if e.get("target")]
                if build.context.structural.demand_anchor:
                    node_ids.append(str(build.context.structural.demand_anchor))
                narrative_context = fetch_narrative(company_id, node_ids=node_ids)
            except Exception as exc:  # noqa: BLE001 — 拿不到引文只讓論證層少引文，不讓 view 失敗
                narrative_context = {"error": f"{type(exc).__name__}: {str(exc)[:120]}"}
        # ⚠ **2026-09-23（Phase 0 Step 0b.1b）：E 組（賭注四價 overlay）整組退役。**
        # 原本這裡把整條估值鏈**再跑兩次**（variant／downside），算出「賭對了值多少／判斷錯了值多少」
        # 那四個價格。ROADMAP「個股頁」對照表把 `bet` 的四個價格列進「拿掉」；`bet` 面板已於 0b.1a
        # 改成純文字（讀短評的 `our_bet`）。
        # ⚠ **`bet/variant.overlay` 這本 append-only ledger 的資料留著**（L10：拿不回來的只能 append）
        # ——退役的是「拿它算四個價格」這件事，不是那些紀錄。Abstention（刻意不主張）同樣留著。
        abstention_records = _read_abstentions(str(resolved_ticker))
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
            since = baseline_since(judged_on, records)
            lifecycle_for_refresh = _thesis_lifecycle_entry(str(resolved_ticker)) if as_of is None else None
            try:
                refresh_changes, metric_observations, refresh_notes = detect_changes(
                    ticker=str(resolved_ticker), company_id=str(company_id), since=since, today=today,
                    as_of=as_of, fundamentals_provider=fundamentals_provider, graph_provider=graph_provider,
                    assumption_records=records, lifecycle_entry=lifecycle_for_refresh,
                    watches=(list(watches) if watches is not None else load_watches()),
                    ticker_obj=resolved_ticker)
            except Exception as exc:  # noqa: BLE001 — 偵測失敗不讓 view 失敗，但必須現形（not_run）
                refresh_changes, metric_observations = None, []
                refresh_notes = [f"變更偵測失敗：{type(exc).__name__}: {str(exc)[:120]}"]
        if sandbox_hurdle is not None:
            refresh_notes = [f"sandbox hurdle {float(sandbox_hurdle):+.1%} 只疊在記憶體（author=sandbox）：未寫入任何 authority、"
                             "不進變更偵測；ledger 裡的判準（若有）在本次視角被它取代", *refresh_notes]
        if scenario is not None:
            extra, extra_obs = scenario_changes(
                scenario, ticker=str(resolved_ticker), company_id=str(company_id), context=build.context,
                consensus=financials["consensus"], assumptions=records,
                base_period_end=(financials["actuals"].period.end if financials["actuals"] is not None else None),
                target_period=financials["target_period"], today=today)
            refresh_changes = list(refresh_changes or ()) + extra
            metric_observations = list(metric_observations) + extra_obs
            detection = "scenario"
            refresh_notes = [f"情境 {scenario}：在真實 state 上疊加假想變化（不寫任何 authority）", *refresh_notes]
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

    # D2（2026-09-18）歸零旗標：取數在 Engine C、判色在 `alpha.wipeout`、型別在 builder。
    # 取不到就帶著 reason 往下走——**燈滅與燈綠不得同形**（L12），所以這裡不回空 dict。
    try:
        from alpha.wipeout import wipeout_flags
        from engine_c.checklist import get_wipeout_inputs

        raw = get_wipeout_inputs(str(resolved_ticker))
        if raw.get("status") == "ok":
            wipeout = wipeout_flags(runway=raw.get("runway"), shares_series=raw.get("shares_series"),
                                    going_concern=raw.get("going_concern"), today=today or date.today())
            wipeout_reason = None
        else:
            wipeout, wipeout_reason = None, str(raw.get("reason") or "Engine C 觀測不可用")
    except Exception as exc:  # noqa: BLE001
        wipeout, wipeout_reason = None, f"歸零旗標取數失敗：{type(exc).__name__}"

    try:
        brief_records, brief_errors = brief_ledger.read_brief_records(str(resolved_ticker))
    except Exception as exc:  # noqa: BLE001 — 讀不到就是沒有短評，但要現形
        brief_records, brief_errors = [], [f"短評 ledger 讀取失敗：{type(exc).__name__}"]

    # ⚠ **2026-09-23（Phase 0 Step 0b.1b）：多年視角（要幾倍、哪一格得為真）整組退役。**
    # 它跑的是多年反向橋（`alpha/reverse` ＋ `briefing/multi_year`），ROADMAP Phase 0／D 組。
    # 接手「這個結構允不允許翻倍」的是讀圖（Phase 2）與財務三題（Phase 3），不是另一條橋。

    return build_alpha_investment_view(
        build=build, signal=signal, signal_reason=signal_reason,
        dependency_paths=causal.get("dependency_paths", ()),
        substitution_paths=causal.get("substitution_paths", ()),
        supply_exposure=causal.get("supply_exposure", ()),
        impacts=causal.get("impacts", ()), structural_events=causal.get("structural_events", ()),
        causal_reason=causal.get("causal_reason"),
        estimate_revision=estimate_revision,
        decision_facts=decision_facts, decision_facts_reason=decision_reason,
        catalyst_checkpoints=checkpoints, checkpoint_source=checkpoint_source,
        thesis_lifecycle=lifecycle_entry, checklist=checklist, identity=identity,
        base_actuals=financials["actuals"], fiscal_consensus=financials["consensus"],
        consensus_bases=financials["bases"], financials_reason=financials["reason"],
        financial_evidence=financials["evidence"], target_period=financials["target_period"],
        today=today,
        refresh_changes=refresh_changes, assumption_records=records,
        abstention_records=abstention_records,
        metric_observations=metric_observations, change_detection=detection,
        refresh_notes=refresh_notes,
        wipeout=wipeout, wipeout_reason=wipeout_reason,
        brief_records=brief_records, brief_parse_errors=brief_errors,
        narrative_context=narrative_context,
        consensus_history=consensus_history,
    )


def fetch_alpha_cards(
    tickers: Iterable[str], *, today: date | None = None,
    graph_provider: Any = None, fundamentals_provider: Any = None,
) -> list[dict[str, Any]]:
    """Daily Brief 用：每檔一張精簡卡。單檔失敗只降級成 `status=unavailable` 那一列，
    不丟掉、不阻斷（INV-3）。

    provider **整批共用一份**：Neo4j provider 會把 `structure_table()` 快取在 instance 上，
    每檔各開一個 driver 等於把 663 條 assertion 的表建 N 次。呼叫端沒注入時這裡開一次、
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
]
