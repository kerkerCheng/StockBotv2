"""純讀的 Engine D 決策摘要 pane。

## B6 之後這一支管什麼

**只管決策：** 掃 operational cohorts、與 current authority 比對 frozen context、
組出帶穩定編號的 pq2 待辦清單與首屏聚合。它**不再是全系統儀表板**——瓶頸排序、
NAV 比例、備份狀態、排序品質那些 pane 各自回到自己的 domain
（`alpha/brief.py`、`portfolio/brief.py`、`briefing/sources.py`），
組裝與 markdown 在 `briefing/`。

拆的理由不是行數，是 `engine-d-decomposition.md` §0 第 3 點記下的成因：
**「使用者說『這個也放進來』時，最短路徑就是在 brief.py 加一段」**——只要組裝點
還在這裡，它就會再長回 1,462 行。現在這裡看不到 Neo4j、Google Sheet、beta policy，
所以長不出那些東西。

## `sheet_only_items` 為什麼是必填參數

Sheet 持股的覆蓋分類（beta 涵蓋／使用者指定不研究／無人負責）已搬到
`portfolio.brief.build_sheet_only_items`。它走的是 pq2 收集鏈
`engine_b todo sync → briefing.public_view → build_today_brief`，**漏掉就等於
持股從待辦池靜默消失**。所以它刻意不給預設值：新增第三條呼叫路徑時會是
`TypeError`，而不是一份看起來正常、少了幾檔持股的 brief（L13：成功與未執行
不得同形）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from identity.registry import IdentityRegistry, get_registry
from .action_card import assert_safe_payload, build_action_card
from .models import TERMINAL_LIFECYCLE_STATUSES
from .store import DecisionStore
from .workflow_ports import WorkflowDataProvider

USABLE_HOLDINGS_STATUSES = frozenset({"available", "confirmed", "confirmed_empty"})


def _evidence_gap_order(item: Mapping[str, Any]) -> tuple[int, int, str, str]:
    """首屏排序鍵：證據最弱的排前面。

    先前用 `_ACTION_PRIORITY = {"NO ACTION": 0, "TRADE": 1, "HEDGE": 2, "REVIEW": 3}`
    ——那是資本語意的排序（要不要交易），而系統終點已經改成瓶頸排序、不給額度。
    現在問的是「哪一檔最需要補證據」，答案就是最弱軸的等級。

    未知等級排最前：寧可多看一眼，也不要讓一個算不出等級的項目沉到底部。

    ⚠ 讀 `weakest_effective_level`，不是宣告的 `weakest_level`。`weakest_axis_of` 的
    docstring 明文記過這個坑：`_validate_assessment` 在 fatal_axis_blocker 時讓該軸
    失效卻**不動宣告 level**，所以一個「宣告 corroborated、引用不成立」的軸用 raw
    level 排序會被排到最後面——而它其實是最該先看的。
    """
    from .sizing import AXES, LEVELS

    level = str(item.get("weakest_effective_level") or item.get("weakest_level") or "")
    axis = str(item.get("weakest_axis") or "")
    return (
        LEVELS.index(level) if level in LEVELS else -1,
        AXES.index(axis) if axis in AXES else -1,
        str(item.get("company_id") or ""),
        str(item.get("cohort_id") or ""),
    )
# 已結案的 probe 不再進今日待辦；`revised` 刻意不在內（新 epoch 需 reassess）。
# 字彙集中在 models，避免 workflow／brief 兩處各自複製而漂移。
_TERMINAL_LIFECYCLE = TERMINAL_LIFECYCLE_STATUSES


def _time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed


def _public_company(company_id: Any) -> str:
    return str(company_id or "unresolved")


def _user_request(card: Mapping[str, Any]) -> str:
    if str(card.get("attention")) == "REVIEW":
        return str(card.get("next_action") or "請完成 blocker 所列核查後再 reassess。")
    return "無；依下一個 review 時間監控即可。"


def _blockers_by_mode(blockers: Sequence[str]) -> dict[str, list[str]]:
    """依 `resolution_mode` 分組。唯一權威是 `config/decision_blockers.json`。

    只有 `user_decision` 那組真的需要人動手；`system_internal` 多半 reassess
    就消失，`awaiting_external` 要等世界先發生事。把這三者混成一張 blocker 清單，
    下游只能靠猜，而猜錯的方向永遠是「看起來需要更多研究」。
    """

    from shared.blockers import describe_blocker

    grouped: dict[str, list[str]] = {}
    for code in sorted({str(b) for b in blockers if b}):
        mode = getattr(describe_blocker(code), "resolution_mode", "user_decision")
        grouped.setdefault(str(mode), []).append(code)
    return grouped


def _decision_item(
    card: Mapping[str, Any],
    current_authority: Mapping[str, Any] | None = None,
    *,
    variant_perception: str | None = None,
) -> dict[str, Any]:
    lifecycle = card.get("lifecycle") or {}
    attention = str(card["attention"])
    current_authority = current_authority or {}
    blockers = sorted(
        set(card.get("blockers") or [])
        | set(current_authority.get("blockers") or [])
    )
    if current_authority.get("blockers"):
        attention = "REVIEW"
    # 閉環：因果結構有新證據（material）而 probe 目前沒有其他理由被看 → 提醒 reassess。
    evidence_delta = str(current_authority.get("evidence_delta") or "none")
    material_evidence = evidence_delta == "material"
    if material_evidence and attention == "MONITOR":
        attention = "REVIEW"
    item = {
        "cohort_id": card.get("cohort_id"),
        "decision_id": card["decision_id"],
        "company_id": _public_company(card.get("company_id")),
        # `attention` 取代 U7 之前的 `recommended_action`（NO ACTION／REVIEW／TRADE／
        # HEDGE）。系統不再建議動作，只回答「今天要不要看這一檔」。
        "attention": attention,
        # 最弱軸跟著 item 走，消費端不必自己再查一次 decision（L16）。pq2 的研究缺口
        # 項目就是由它導出：「補哪一檔的哪一軸」比「REVIEW — co:xxx」可執行得多。
        "weakest_axis": (card.get("weakest_link") or {}).get("axis"),
        "weakest_level": (card.get("weakest_link") or {}).get("level"),
        # 宣告等級與實質等級都跟著 item 走，消費端不必自己再查 decision（L16）。
        "weakest_effective_level": (card.get("weakest_link") or {}).get("effective_level"),
        "weakest_missing_data": (card.get("weakest_link") or {}).get("missing_data") or [],
        "reason": card["reason"],
        "alpha_thesis_change": card.get("alpha_beta") or {"classification": "unknown"},
        "beta_portfolio_risk": {
            "portfolio_action": (card.get("scope") or {}).get("portfolio", "none"),
            "classification": (card.get("alpha_beta") or {}).get(
                "classification", "unknown"
            ),
            "security_return": current_authority.get("security_return"),
            "fx_return": current_authority.get("fx_return"),
        },
        # 兩個時刻不是同一件事，先前把它們寫成同一個欄位，等於把最重要的那段藏起來。
        #
        # `performance_since_tracked` 錨在 **Shadow inception**——訊號第一次進來的
        # 那一刻。它衡量的是**資訊價值**：從我們知道這件事開始，股價走了多少。
        # `performance_since_decision` 錨在決策凍結時，衡量決策之後的表現。
        #
        # 兩者之間就是「從看到到研究完」的區間，也正是 gate 代價的所在：co:axt 的
        # Shadow 錨在 2026-07-28（42.76），決策要到 08-06 才凍（行情 08-05、68.61）——
        # 中間 9 天、78 個百分點，只看 since_decision 完全看不到。
        "performance_since_tracked": current_authority.get("shadow_return"),
        "performance_since_decision": current_authority.get("security_return"),
        # 超額報酬各自對齊自己的錨點；**未做風險調整**，見 _benchmark_return。
        "benchmark_symbol": current_authority.get("benchmark_symbol"),
        "excess_since_tracked": _ratio_diff(
            current_authority.get("shadow_return"),
            current_authority.get("benchmark_shadow_return"),
        ),
        "excess_since_decision": _ratio_diff(
            current_authority.get("security_return"),
            current_authority.get("benchmark_return"),
        ),
        "evidence_delta": evidence_delta,
        "blockers": blockers,
        # ⚠ blocker code 單獨出現時，讀者無從知道它該由誰動手，於是每個消費端都會
        # 自己再猜一份分類——2026-08-26 一天內發生兩次（`engine_b.todo` 手寫
        # stale 清單、以及口頭把 co:axt 的 system_internal blocker 誤判成 bug）。
        # 分類本身早就有 SSOT（`config/decision_blockers.json` 的 resolution_mode），
        # 缺的只是**沒有跟著資料一起送出來**。附上它，消費端就沒有動機自己猜。
        "blockers_by_mode": _blockers_by_mode(blockers),
        "next_review_at": lifecycle.get("review_due_at"),
        "disproof_condition": card.get("disproof_condition") or "",
        # variant perception 跟著 item 走（2026-09-02「cohort 是終點」定案）：
        # 「市場隱含 X／本 thesis 認為 Y」是這一檔存在的理由，REVIEW 時第一眼要看到。
        # None＝從未寫過——渲染端顯示「（未寫）」現形，不隱藏。
        "variant_perception": variant_perception,
        # 這些軸的 authority 現在拿得到了，值得重評估（只是提示，不自動改等級）。
        "reassessable_axes": list(current_authority.get("reassessable_axes") or []),
        # 缺這些 Engine C 人工觀測 ⇒ commercial_maturity 恆 unknown ⇒ 部位恆為 0。
        # 它們是硬性前置條件，不是選填清單項，必須在撞牆前就看得見。
        "missing_observations": list(current_authority.get("missing_observations") or []),
        # 研究完整度與 live 選擇跟著 item 走（L16）：C-1 的「研究完整但不在瓶頸排序內」
        # 常駐清單靠這兩個欄位計算，消費端不必回頭再查 card。
        "research_status": str((card.get("research") or {}).get("status") or ""),
        "live_user_choice": bool((card.get("live") or {}).get("user_choice")),
        "probe_expiry": card.get("probe_expiry"),
        "expiry_lapsed": bool(card.get("expiry_lapsed")),
        "user_response_needed": (
            "請修復 current authority blocker 並執行 reassess。"
            if current_authority.get("blockers")
            else "有觸及 thesis 因果結構的新證據，建議 reassess。"
            if material_evidence
            else _user_request(card)
        ),
    }
    if current_authority.get("blockers"):
        item["reason"] = "目前 authority snapshot 不完整或失效，需先複查，不能沿用舊評估。"
    elif material_evidence:
        item["reason"] = "自上次決策後出現觸及 thesis 因果結構的新證據；建議 reassess 看最弱軸／thesis 是否改變。"
    return item


def _evidence_refs(evidence: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    for item in evidence.get("sources") or []:
        if isinstance(item, Mapping):
            value = item.get("id") or item.get("source_uri")
        else:
            value = item
        if isinstance(value, str) and value:
            refs.add(value)
    for field in ("causal_paths", "counter_paths"):
        for item in evidence.get(field) or []:
            if isinstance(item, Mapping):
                value = item.get("id") or item.get("edge_key")
            else:
                value = item
            if isinstance(value, str) and value:
                refs.add(value)
    return refs


def _causal_refs(evidence: Mapping[str, Any]) -> set[str]:
    """只取 thesis 結構 refs（causal/counter path），不含週邊 source。

    閉環精度（plan R12）：新證據標 material 的條件是它觸及 probe 的因果結構，
    而非只是這家公司多了一條 source。
    """
    refs: set[str] = set()
    for field in ("causal_paths", "counter_paths"):
        for item in evidence.get(field) or []:
            if isinstance(item, Mapping):
                value = item.get("id") or item.get("edge_key")
            else:
                value = item
            if isinstance(value, str) and value:
                refs.add(value)
    return refs


def _ratio(current: Any, previous: Any) -> float | None:
    if (
        isinstance(current, bool)
        or isinstance(previous, bool)
        or not isinstance(current, (int, float))
        or not isinstance(previous, (int, float))
        or previous == 0
    ):
        return None
    return float(current) / float(previous) - 1.0


# 哪一軸依賴哪些 authority section。這不是新字彙——它是
# `sizing.AXIS_REFERENCE_AUTHORITIES` 的 snapshot-section 投影：那份對照表管的是
# 「這一軸的 evidence_ref 可以引用哪些 authority」，這裡管的是「那些 authority
# 現在拿不拿得到」。兩者必須同步修改。
_AXIS_AUTHORITY_SECTIONS = {
    "source_reliability": ("evidence",),
    "technical_causal_link": ("evidence",),
    "commercial_maturity": ("evidence", "financial"),
    "financial_resilience": ("financial",),
    "valuation_payoff": ("financial", "market", "fx"),
}
_AVAILABLE_STATUSES = frozenset({"available", "observed"})


def _reassessable_axes(
    frozen_assessment: Mapping[str, Any], snapshot: Any
) -> list[str]:
    """哪些 `unknown` 軸的 authority 現在拿得到了——亦即「可以重評估了」。

    軸在被評成 `unknown` 時會誠實記下 `missing_data`，但那是自由文字，沒有任何
    地方拿它去問「這項現在拿得到了嗎」。實測 co:sivers 的 `valuation_payoff` 因
    SIVE.ST 行情被 quarantine 而判 unknown（2026-07-28），quarantine 在 2026-08-05
    的幣別修正後就解除了，卻沒有任何東西回頭看它——該標的因此在一個**已經修好的
    問題**上又卡了三天，而使用者實際持有它。

    這裡不解析自由文字（那會變成猜測），只用既有的軸→authority 對應做確定性比對：
    軸是 unknown、而它依賴的 authority 現在全部 available ⇒ 值得重評估。
    這只是**提示**，不自動改任何軸的等級。
    """

    reassessable: list[str] = []
    for axis, sections in _AXIS_AUTHORITY_SECTIONS.items():
        entry = frozen_assessment.get(axis)
        if not isinstance(entry, Mapping) or entry.get("level") != "unknown":
            continue
        ready = True
        # commercial_maturity 的 authority 不是「financial 這個 section 拿不拿得到」，
        # 而是「那兩筆人工觀測在不在」。用 section 層級判會產生自相矛盾的輸出：
        # 2026-08-08 實測 co:iqe 同時被標成「commercial_maturity 可重評估」與
        # 「缺 customer_concentration／backlog」——同一份 brief 兩個欄位互相打臉。
        if axis == "commercial_maturity" and _missing_observations(snapshot):
            continue
        for section in sections:
            payload = getattr(snapshot, section, None) or {}
            status = str(payload.get("status") or "")
            if section == "evidence":
                # evidence 沒有 available/observed，用 coverage 的說法：
                # 只要不是缺席或空圖就算拿得到。
                ready = ready and status not in {
                    "",
                    "unresolved_identity",
                    "graph_unavailable",
                    "graph_empty",
                    "graph_company_missing",
                }
            else:
                ready = ready and status in _AVAILABLE_STATUSES
        if ready:
            reassessable.append(axis)
    return sorted(reassessable)


# 這兩項是 `commercial_maturity` 唯一的 authority 來源（見 sizing.AXIS_REFERENCE_
# AUTHORITIES 的說明）。缺任一項該軸就恆為 unknown，五軸取 min ⇒ supported range 恆為 0。
# 2026-08-08 實測相關性 100%：有這兩筆的 cohort 全部有部位，沒有的全部是 0。
_POSITION_BLOCKING_OBSERVATIONS = ("customer_concentration", "backlog")


def _missing_observations(snapshot: Any) -> list[str]:
    """哪些 Engine C 人工觀測缺席，而它們正擋著這個 cohort 拿到任何部位。

    先前只能靠「做完 assessment 拿到 0」才發現——那是撞牆後才知道牆在哪。
    這裡讓它在 brief 就現形，成為明確的 pq2 待辦而不是隱藏前置條件。
    """

    checklist = ((getattr(snapshot, "financial", None) or {}).get("checklist")) or {}
    missing: list[str] = []
    for name in _POSITION_BLOCKING_OBSERVATIONS:
        status = str((checklist.get(name) or {}).get("status") or "missing")
        if status not in {"ok", "manual_reviewed"}:
            missing.append(name)
    return missing


def _ratio_diff(security: Any, benchmark: Any) -> float | None:
    """原始超額報酬（未風險調整）。任一側缺就回 None，不用 0 冒充 benchmark。"""
    if not isinstance(security, (int, float)) or isinstance(security, bool):
        return None
    if not isinstance(benchmark, (int, float)) or isinstance(benchmark, bool):
        return None
    return float(security) - float(benchmark)


def _benchmark_return(
    provider: WorkflowDataProvider, symbol: str, since: str, as_of: str, cache: dict
) -> float | None:
    """Benchmark 自 ``since`` 到現在的報酬；同一次 brief 內以 (symbol, 錨點日) 快取。

    比較必須錨在**同一個時刻**才有意義：`security_return` 錨在決策凍結時的行情，
    `shadow_return` 錨在訊號進來時，兩者要各自配一個對齊的 benchmark 報酬。用同一個
    benchmark 數字去減兩個不同起點的個股報酬，會產生看起來精確的錯誤答案。

    ⚠ 這裡算的是**原始超額報酬，未做風險調整**。用一檔十天能漲 107%、也能跌 40% 的
    小型股贏過指數，不必然是技巧，可能只是承擔了更多波動。樣本夠長之前不做 beta
    調整，但輸出必須標明未調整。
    """

    anchor_day = str(since)[:10]
    key = (symbol, anchor_day)
    if key not in cache:
        try:
            cache[key] = provider.benchmark_return(
                symbol=symbol, since=since, evaluation_at=as_of
            )
        except Exception:
            cache[key] = None
    return cache[key]


def _current_authority_context(
    store: DecisionStore,
    provider: WorkflowDataProvider,
    summary: Mapping[str, Any],
    *,
    as_of: str,
    benchmark_cache: dict | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """讀 current authorities 並與 frozen context 比較；不建立新 decision。"""

    cohort_id = str(summary["cohort_id"])
    try:
        identity = provider.resolve_identity(
            company_id_hint=summary.get("company_id"),
            ticker_hint=summary.get("research_ticker"),
        )
        snapshot = provider.snapshot(identity=identity, evaluation_at=as_of)
    except Exception:
        return (
            {"blockers": ["current_authorities_unavailable"]},
            {},
        )
    blockers = [order.code for order in snapshot.work_orders]
    latest = store.latest_decision_for_cohort(cohort_id, as_of=as_of)
    if latest is None:
        return ({"blockers": sorted(set(blockers))}, {})
    frozen = store.get_context_bundle(str(latest["context_digest"])).payload
    current_market = snapshot.market
    current_fx = snapshot.fx
    security_return = _ratio(
        current_market.get("price"), (frozen.get("market") or {}).get("price")
    )
    # Shadow 錨點是訊號第一次進來時的價格，與決策凍結時的價格是兩個不同的時刻。
    # 幣別必須一致才可比——Shadow 存的是結算幣別，current_market 亦然。
    try:
        shadow = store.get_shadow(cohort_id)
    except KeyError:
        shadow = None
    shadow_return = None
    if (
        shadow is not None
        and shadow.status == "observed"
        and shadow.currency == current_market.get("currency")
    ):
        shadow_return = _ratio(current_market.get("price"), shadow.price)

    # Benchmark：alpha 歸因的比較基準，預設 QQQ（見 CompanyIdentity.benchmark_symbol）。
    # 兩個錨點各配一個，否則「超額報酬」會用錯起點。
    cache = benchmark_cache if benchmark_cache is not None else {}
    company = get_registry().company(str(summary.get("company_id") or ""))
    benchmark_symbol = getattr(company, "benchmark_symbol", "QQQ") if company else "QQQ"
    benchmark_return = None
    benchmark_shadow_return = None
    frozen_as_of = (frozen.get("market") or {}).get("as_of")
    if security_return is not None and frozen_as_of:
        benchmark_return = _benchmark_return(
            provider, benchmark_symbol, str(frozen_as_of), as_of, cache
        )
    if shadow_return is not None and shadow is not None and shadow.as_of:
        benchmark_shadow_return = _benchmark_return(
            provider, benchmark_symbol, str(shadow.as_of), as_of, cache
        )
    fx_return = _ratio(
        current_fx.get("rate"), (frozen.get("fx") or {}).get("rate")
    )
    # 閉環精度（R12）：因果結構變＝material（建議 reassess）；只有週邊 source
    # 變＝peripheral（記錄但不強制）；都沒變＝none。純價格波動不進 evidence_delta。
    frozen_evidence = frozen.get("evidence") or {}
    if _causal_refs(frozen_evidence) != _causal_refs(snapshot.evidence):
        evidence_delta = "material"
    elif _evidence_refs(frozen_evidence) != _evidence_refs(snapshot.evidence):
        evidence_delta = "peripheral"
    else:
        evidence_delta = "none"
    frozen_assessment = (latest["payload"].get("request") or {}).get("assessment") or {}
    reassessable = _reassessable_axes(frozen_assessment, snapshot)
    missing_observations = _missing_observations(snapshot)
    change = {
        "security_return": security_return,
        "shadow_return": shadow_return,
        "benchmark_return": benchmark_return,
        "benchmark_shadow_return": benchmark_shadow_return,
        "benchmark_symbol": benchmark_symbol,
        "evidence_delta": evidence_delta,
        "disproof_triggered": False,
        "fx_return": fx_return,
    }
    return (
        {
            "blockers": sorted(set(blockers)),
            "security_return": security_return,
            "shadow_return": shadow_return,
            "benchmark_return": benchmark_return,
            "benchmark_shadow_return": benchmark_shadow_return,
            "benchmark_symbol": benchmark_symbol,
            "fx_return": fx_return,
            "evidence_delta": evidence_delta,
            "reassessable_axes": reassessable,
            "missing_observations": missing_observations,
        },
        change,
    )


def _pending_item(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cohort_id": summary["cohort_id"],
        "decision_id": None,
        "company_id": _public_company(summary.get("company_id")),
        "attention": "REVIEW",
        "reason": "Signal 已保存，但尚未形成可稽核的 system decision。",
        "alpha_thesis_change": {"classification": "unknown", "thesis_changed": False},
        "beta_portfolio_risk": {"portfolio_action": "none", "classification": "unknown"},
        "blockers": ["decision_missing"],
        "next_review_at": summary.get("review_due_at"),
        "disproof_condition": "",
        "user_response_needed": "請執行 reassess 或補齊 research work order。",
    }


def cohort_company_ids(store: DecisionStore, *, as_of: str) -> set[str]:
    """哪些公司已經有 cohort 在負責——投組覆蓋分類要的唯一 Engine D 輸入。

    ⚠ **終結的 cohort 也算數。** 它的公司不再是今日待辦，但它的 Sheet 持股也不是
    「沒人負責的 legacy holding」——漏掉這條會讓已 promote／reject 的標的每天重新
    以 sheet-only 身分冒出來配一個新 pq2 編號。

    這個規則只有一份（L16：分類有 SSOT 就要送到需要它的地方），
    `portfolio.brief.build_sheet_only_items` 消費它而不自己再推導一次。
    """

    return {
        str(summary["company_id"])
        for summary in store.list_operational_cohorts(as_of=as_of)
        if summary.get("company_id")
    }


def identity_registration_pending(
    summaries: Sequence[Mapping[str, Any]],
    registry: IdentityRegistry,
) -> list[dict[str, Any]]:
    """列出「研究對象已知、但 registry 還沒有可交易 ticker」的未終結 cohort。

    這類 cohort 的 `market_missing`／`fx_missing`／`financial_missing` **不是研究不足**，
    而是在該公司取得可交易 ticker 並手動登記進 `config/company_identity.json` 之前，
    結構上無法評估——`bind_cohort_identity` 要求 company_id 與 research_ticker 成對。
    再 dispatch 幾輪 bounded research 也不會改變任何一項。

    為什麼要一個確定性檢查：先前這件事只存在於 brief 作者寫的自然語言裡（[74] Agility
    Robotics）。作者換人或那天忘了寫，這個前提就悄悄消失，而它是該項目能否真正解鎖的
    唯一關鍵動作——與 SIVE 2026-08-27 同屬「已知關鍵動作＋零自動監測」。
    """

    pending: list[dict[str, Any]] = []
    for summary in summaries:
        if str(summary.get("lifecycle_status") or "") in _TERMINAL_LIFECYCLE:
            continue
        if summary.get("research_ticker"):
            continue
        company_id = str(
            summary.get("company_id") or summary.get("company_id_hint") or ""
        ).strip()
        if not company_id:
            # 連研究對象都不知道是另一種問題（identity 完全未解析），不在本檢查範圍。
            continue
        company = registry.company(company_id)
        if company is not None and company.research_ticker:
            # registry 有 ticker 卻沒綁上，是 binding 沒跑，不是待登記——不同問題。
            continue
        pending.append({
            "cohort_id": str(summary.get("cohort_id") or ""),
            "company_id": company_id,
            "registered": company is not None,
            "blocking_action": (
                f"在 config/company_identity.json 為 {company_id} 補上可交易 "
                "research_ticker（該公司需先完成上市／掛牌）"
            ),
        })
    return sorted(pending, key=lambda row: row["company_id"])


def build_decision_brief(
    store: DecisionStore,
    *,
    as_of: str,
    sheet_only_items: Sequence[Mapping[str, Any]],
    current_holdings: Mapping[str, Any] | None = None,
    change_context_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    portfolio_context_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    current_authority_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    provider: WorkflowDataProvider | None = None,
) -> dict[str, Any]:
    """掃描 cohorts／decisions 與注入的 sheet-only 覆蓋項；不寫入任何 authority。

    `sheet_only_items` 由 `portfolio.brief.build_sheet_only_items` 產生（見模組
    docstring 為何它必填）。其餘 pane（排序、NAV、備份、排序品質）不在這裡——
    它們由 `briefing/today.py` 組裝。
    """

    _time(as_of, "as_of")
    assert_safe_payload(current_holdings or {})
    assert_safe_payload(change_context_by_cohort or {})
    assert_safe_payload(portfolio_context_by_cohort or {})
    changes = dict(change_context_by_cohort or {})
    portfolios = dict(portfolio_context_by_cohort or {})
    current_authorities = dict(current_authority_by_cohort or {})
    summaries = store.list_operational_cohorts(as_of=as_of)
    if provider is not None:
        # 同一次 brief 內共用 benchmark 快取：多個 cohort 常錨在同一個交易日，
        # 不共用會對同一支 benchmark 重複抓十幾次。
        benchmark_cache: dict = {}
        for summary in summaries:
            authority, derived_change = _current_authority_context(
                store, provider, summary, as_of=as_of, benchmark_cache=benchmark_cache
            )
            current_authorities.setdefault(str(summary["cohort_id"]), authority)
            changes.setdefault(str(summary["cohort_id"]), derived_change)
    items: list[dict[str, Any]] = []
    for summary in summaries:
        cohort_id = str(summary["cohort_id"])
        # 已終結的 probe 不再是今日待辦（promoted／rejected／expired）。`revised`
        # 不算終結——它開新 epoch 且需要 reassess，仍要出現。
        if str(summary.get("lifecycle_status") or "") in _TERMINAL_LIFECYCLE:
            continue
        decision_id = summary.get("latest_decision_id")
        if decision_id is None:
            pending = _pending_item(summary)
            if pending["company_id"] == "unresolved" and summary.get("company_id_hint"):
                pending["company_id_hint"] = str(summary["company_id_hint"])
            items.append(pending)
            continue
        card = build_action_card(
            store,
            str(decision_id),
            as_of=as_of,
            change_context=changes.get(cohort_id),
            portfolio_context=portfolios.get(cohort_id),
        )
        card["cohort_id"] = cohort_id
        # variant perception 窄 duck-type（同 capital_expression 契約）：surface
        # 沒有這個方法就是 None（未提供），不與「沒寫過」混用——渲染端兩者都顯示
        # 「（未寫）」是可接受的合流：對使用者的動作都是「該去寫」。
        _vp_fn = getattr(store, "latest_variant_perception", None)
        _vp_row = _vp_fn(str(cohort_id)) if callable(_vp_fn) else None
        decision_item = _decision_item(
            card,
            current_authorities.get(cohort_id),
            variant_perception=(
                str(_vp_row["variant_perception"]) if _vp_row else None
            ),
        )
        if (
            decision_item["company_id"] == "unresolved"
            and summary.get("company_id_hint")
        ):
            decision_item["company_id_hint"] = str(summary["company_id_hint"])
        items.append(decision_item)

    items.extend(dict(item) for item in sheet_only_items)
    holdings_status = str((current_holdings or {}).get("status") or "unavailable")
    if holdings_status not in USABLE_HOLDINGS_STATUSES:
        for item in items:
            blockers = set(item["blockers"])
            blockers.add(f"holdings_{holdings_status}")
            item["blockers"] = sorted(blockers)

    ranked = sorted(items, key=_evidence_gap_order)
    for position, item in enumerate(ranked, 1):
        item["index"] = position  # 穩定編號，供對話式批次核准引用（plan R5）
    # ⚠ 對**整份清單**聚合，不是取 `ranked[0]`。`ranked` 的排序鍵是最弱軸等級
    # （「先看誰」），與「今天要不要動作」完全無關——實測 2026-08-29：26 個項目裡
    # 12 個 REVIEW，而排在第一的是一檔 beta policy 涵蓋的 Sheet 持股（MONITOR），
    # 於是首屏印出「今天需要動作嗎？否」，把 48 小時 disproof 項一起蓋掉。
    # 展示順序與注意力是兩個問題，不該共用同一個表示（L12）。
    first_review = next((i for i in ranked if i["attention"] == "REVIEW"), None)
    attention = "REVIEW" if first_review is not None else "MONITOR"
    if first_review is not None:
        reason = first_review["reason"]
    elif ranked:
        reason = ranked[0]["reason"]
    elif holdings_status not in USABLE_HOLDINGS_STATUSES:
        attention = "REVIEW"
        reason = "Google Sheet current holdings 無法讀取；無法完成今日投組覆蓋檢查。"
    else:
        reason = "沒有 active Signal cohort、paper/live exception 或待回報交易。"

    review_times = [
        str(item["next_review_at"])
        for item in ranked
        if item.get("next_review_at")
    ]
    blockers = sorted(
        {str(blocker) for item in ranked for blocker in item.get("blockers") or []}
        | (
            {f"holdings_{holdings_status}"}
            if holdings_status not in USABLE_HOLDINGS_STATUSES
            else set()
        )
    )

    brief = {
        "schema_version": "engine-d-today-v1",
        "as_of": as_of,
        "action_needed": attention != "MONITOR",
        "attention": attention,
        "reason": reason,
        "alpha_thesis_changes": [item["alpha_thesis_change"] for item in ranked],
        "beta_portfolio_risk": [item["beta_portfolio_risk"] for item in ranked],
        "blockers": blockers,
        "next_review_at": min(review_times) if review_times else None,
        # 結構性阻塞：研究做再多也解不開，只有補 registry ticker 能解。
        "identity_registration_pending": identity_registration_pending(
            summaries, get_registry()
        ),
        "user_response_needed": [
            item["user_response_needed"]
            for item in ranked
            if item["user_response_needed"].startswith("請")
        ],
        # 兩個常駐計數器：讓開發迴圈（loop #2）的進展每天自己出現在使用者眼前，
        # 而不必記得回去讀 brainstorm。只要還是 0，就代表系統仍未輸出過資本、
        # 或仍無法用證據回答「判斷準不準」。詳見 store.capital_expression_counters。
        #
        # `build_decision_brief` 的 store contract 刻意是窄 duck-type（遠端受限
        # surface 也要能產 brief），因此這裡不硬性要求該方法：提供就給數字，沒提供
        # 就是 None，由 renderer 略過。None 只有一個意思——「這個 surface 不提供」，
        # 不與「數字是 0」混用。
        "capital_expression": (
            counters() if callable(counters := getattr(store, "capital_expression_counters", None))
            else None
        ),
        "items": ranked,
    }
    assert_safe_payload(brief)
    return brief


def ranking_annotations(
    store: DecisionStore, *, as_of: str
) -> dict[str, dict[str, str]]:
    """排序表每列要標的最弱軸與 disproof，以 `co:*` 為鍵。

    住在這裡而不是 `alpha.ranking`：它只需要 Decision Store，而 `alpha.ranking`
    是純轉換層。排序本身來自 Engine A（需要 Neo4j），由更外層合起來——見
    `engine_d_runtime.adapters.fetch_ranking_view`。

    查不到就不放這個鍵。`build_ranking_view` 對缺項留 `None`，那和「確實沒有 disproof」
    是不同的訊號，不得用空字串把兩者壓成同一個（L12）。
    """

    weakest: dict[str, str] = {}
    disproofs: dict[str, str] = {}
    for summary in store.list_operational_cohorts(as_of=as_of):
        company = str(summary.get("company_id") or "")
        decision_id = summary.get("latest_decision_id")
        if not company or decision_id is None:
            continue
        # 已結案的 probe 不代表這家公司現在的狀態；它的最弱軸會是一段凍結的歷史。
        if str(summary.get("lifecycle_status") or "") in TERMINAL_LIFECYCLE_STATUSES:
            continue
        try:
            payload = store.get_decision(str(decision_id))["payload"]
        except (KeyError, TypeError, ValueError):
            continue
        # ⚠ last-wins，不是 first-wins。`list_operational_cohorts` 由舊到新，先前用
        # `company not in weakest` 等於同公司多 cohort 時取**最舊**的那個——它的最弱軸
        # 可能已經被補掉了。store.py 對「同公司多 cohort 取最新 decision」早有明文約定
        # （ROADMAP 記載 co:lumentum 正是這個形狀），這裡沿用同一條。
        sizing = payload.get("sizing") or {}
        axis = sizing.get("weakest_axis")
        if axis:
            weakest[company] = str(axis)
        coverage_id = str(
            (payload.get("request", {}).get("coverage") or {}).get("assessment_id") or ""
        )
        if not coverage_id:
            continue
        try:
            condition = str(store.get_coverage_metadata(coverage_id)["disproof"] or "")
        except (KeyError, TypeError, ValueError):
            continue
        if condition.strip():
            disproofs[company] = condition.strip()
    return {"weakest_axes": weakest, "disproofs": disproofs}
