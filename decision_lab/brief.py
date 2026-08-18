"""純讀、action-first 的 Engine D 今日摘要。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from identity.registry import IdentityRegistry, get_registry
from .action_card import assert_safe_payload, build_action_card, markdown_text
from .models import TERMINAL_LIFECYCLE_STATUSES
from .store import DecisionStore
from .workflow_ports import WorkflowDataProvider


_ACTION_PRIORITY = {"NO ACTION": 0, "TRADE": 1, "HEDGE": 2, "REVIEW": 3}
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
    action = str(card["action"])
    live = card.get("live") or {}
    if action == "TRADE" and live.get("user_choice") is None:
        return "請明確選擇接受、縮小或 skip；系統不會自動下單。"
    if action == "TRADE":
        return "請在手動下單後回報 fill；系統不會推定成交。"
    if action == "HEDGE":
        return "請決定降低或對沖哪一項投組曝險；資料不足時不輸出單位數。"
    if action == "REVIEW":
        return str(card.get("next_action") or "請完成 blocker 所列核查後再 reassess。")
    return "無；依下一個 review 時間監控即可。"


def _decision_item(
    card: Mapping[str, Any],
    current_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    lifecycle = card.get("lifecycle") or {}
    action = "NO ACTION" if card["action"] == "NO_ACTION" else card["action"]
    current_authority = current_authority or {}
    blockers = sorted(
        set(card.get("blockers") or [])
        | set(current_authority.get("blockers") or [])
    )
    if current_authority.get("blockers"):
        action = "REVIEW"
    # 閉環：因果結構有新證據（material）而 probe 目前無其他動作 → 提醒 reassess。
    evidence_delta = str(current_authority.get("evidence_delta") or "none")
    material_evidence = evidence_delta == "material"
    if material_evidence and action == "NO ACTION":
        action = "REVIEW"
    item = {
        "cohort_id": card.get("cohort_id"),
        "decision_id": card["decision_id"],
        "company_id": _public_company(card.get("company_id")),
        "recommended_action": action,
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
        "supported_sizing_range": (card.get("live") or {}).get(
            "supported_range", [0.0, 0.0]
        ),
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
        "next_review_at": lifecycle.get("review_due_at"),
        "disproof_condition": card.get("disproof_condition") or "",
        # 這些軸的 authority 現在拿得到了，值得重評估（只是提示，不自動改等級）。
        "reassessable_axes": list(current_authority.get("reassessable_axes") or []),
        # 缺這些 Engine C 人工觀測 ⇒ commercial_maturity 恆 unknown ⇒ 部位恆為 0。
        # 它們是硬性前置條件，不是選填清單項，必須在撞牆前就看得見。
        "missing_observations": list(current_authority.get("missing_observations") or []),
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
        item["reason"] = "目前 authority snapshot 不完整或失效，需先 REVIEW，不能沿用舊 sizing。"
    elif material_evidence:
        item["reason"] = "自上次決策後出現觸及 thesis 因果結構的新證據；建議 reassess 看 sizing/thesis 是否改變。"
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
        "recommended_action": "REVIEW",
        "reason": "Signal 已保存，但尚未形成可稽核的 system decision。",
        "alpha_thesis_change": {"classification": "unknown", "thesis_changed": False},
        "beta_portfolio_risk": {"portfolio_action": "none", "classification": "unknown"},
        "supported_sizing_range": [0.0, 0.0],
        "blockers": ["decision_missing"],
        "next_review_at": summary.get("review_due_at"),
        "disproof_condition": "",
        "user_response_needed": "請執行 reassess 或補齊 research work order。",
    }


def _beta_covered_aliases() -> dict[str, str]:
    """Sheet alias → sleeve，取自 beta policy（唯一 numeric SSOT）。

    讀不到就回空 dict：覆蓋資訊不可得時必須退回 REVIEW，寧可重複提醒，
    也不能因設定檔壞掉而讓未覆蓋持股從 pq2 靜默消失。
    """
    try:
        from .beta_policy import load_beta_policy

        policy = load_beta_policy()
    except Exception:
        return {}
    aliases: dict[str, str] = {}
    for instrument in policy.get("instruments") or []:
        sleeve = str(instrument.get("sleeve") or "")
        for alias in instrument.get("sheet_aliases") or ():
            aliases[str(alias).upper()] = sleeve
    return aliases


_COVERAGE_PATH = Path(__file__).resolve().parents[1] / "config" / "holdings_coverage.json"


def _ignored_holdings() -> dict[str, str]:
    """Sheet ticker → 使用者不做 alpha 研究的理由。讀不到同樣退回 REVIEW。"""
    try:
        value = json.loads(_COVERAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(value, dict):
        return {}
    ignored: dict[str, str] = {}
    for entry in value.get("ignored") or ():
        if not isinstance(entry, Mapping):
            continue
        ticker = str(entry.get("sheet_ticker") or "").strip().upper()
        if ticker:
            ignored[ticker] = str(entry.get("reason") or "使用者明確指示不做 alpha 研究。")
    return ignored


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


def _sheet_only_items(
    holdings: Mapping[str, Any] | None,
    *,
    cohort_company_ids: set[str],
    registry: IdentityRegistry,
) -> list[dict[str, Any]]:
    if not holdings or holdings.get("status") not in {
        "available",
        "confirmed",
        "confirmed_empty",
    }:
        return []
    beta_aliases = _beta_covered_aliases()
    ignored = _ignored_holdings()
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in holdings.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        shares = row.get("shares")
        if not isinstance(shares, (int, float)) or isinstance(shares, bool) or shares <= 0:
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        company_id = row.get("company_id") or (
            registry.company_id_for_ticker(ticker) if ticker else None
        )
        identity = str(company_id or (f"ticker:{ticker}" if ticker else "unresolved"))
        if identity in cohort_company_ids or identity in seen:
            continue
        seen.add(identity)

        # 已由別的機制負責的持股仍要在 brief 現形，但不是 alpha 待辦：改用
        # NO ACTION，統一待辦池才不會每天替它們配一個新 pq2 編號。
        sleeve = beta_aliases.get(ticker)
        ignore_reason = ignored.get(ticker)
        if sleeve:
            action = "NO ACTION"
            coverage = "beta_policy"
            reason = (
                f"由 beta policy 涵蓋（sleeve={sleeve}），"
                "配置與 timing 走 daily beta monitor，不需 alpha cohort。"
            )
            portfolio_action = "covered_by_beta_policy"
            # 沒有 alpha cohort 對這些持股是預期狀態，不是 blocker；覆蓋事實由
            # coverage 欄位承載，不讓它冒泡進全域 blockers 製造噪音。
            blockers = []
            request = "無；如需 single-name thesis 再另行 evaluate-signal 建 cohort。"
        elif ignore_reason:
            action = "NO ACTION"
            coverage = "user_ignored"
            reason = f"使用者指定不做 alpha 研究：{ignore_reason}"
            portfolio_action = "user_ignored_holding"
            blockers = []
            request = "無；要恢復追蹤請移除 config/holdings_coverage.json 的該筆登記。"
        else:
            action = "REVIEW"
            coverage = "uncovered"
            reason = "Google Sheet 有 live 持股，但 Engine D 尚無對應 cohort／decision。"
            portfolio_action = "review_uncovered_holding"
            blockers = ["sheet_only_holding", "decision_missing"]
            request = "請先 evaluate-signal／onboard；未完成前不提供 live sizing。"

        result.append(
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": _public_company(company_id),
                "ticker": ticker,
                "sheet_only": True,
                "coverage": coverage,
                "recommended_action": action,
                "reason": reason,
                "alpha_thesis_change": {
                    "classification": "unknown",
                    "thesis_changed": False,
                },
                "beta_portfolio_risk": {
                    "portfolio_action": portfolio_action,
                    "classification": "unknown",
                },
                "supported_sizing_range": [0.0, 0.0],
                "blockers": blockers,
                "next_review_at": None,
                "disproof_condition": "",
                "user_response_needed": request,
            }
        )
    return result


def build_today_brief(
    store: DecisionStore,
    *,
    as_of: str,
    current_holdings: Mapping[str, Any] | None = None,
    change_context_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    portfolio_context_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    current_authority_by_cohort: Mapping[str, Mapping[str, Any]] | None = None,
    provider: WorkflowDataProvider | None = None,
    registry: IdentityRegistry | None = None,
) -> dict[str, Any]:
    """掃描 cohorts／decisions 與當前 Sheet snapshot；不寫入任何 authority。"""

    _time(as_of, "as_of")
    assert_safe_payload(current_holdings or {})
    assert_safe_payload(change_context_by_cohort or {})
    assert_safe_payload(portfolio_context_by_cohort or {})
    registry = registry or get_registry()
    changes = dict(change_context_by_cohort or {})
    portfolios = dict(portfolio_context_by_cohort or {})
    current_authorities = dict(current_authority_by_cohort or {})
    summaries = store.list_operational_cohorts(as_of=as_of)
    if provider is not None and current_holdings is None:
        try:
            current_holdings = provider.current_holdings(evaluation_at=as_of)
        except Exception:
            current_holdings = {"status": "unavailable"}
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
    cohort_company_ids: set[str] = set()
    for summary in summaries:
        cohort_id = str(summary["cohort_id"])
        if summary.get("company_id"):
            # 終結的 cohort 仍要登記 company，避免它的 Sheet 持股被誤判成
            # sheet-only legacy holding。
            cohort_company_ids.add(str(summary["company_id"]))
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
        decision_item = _decision_item(card, current_authorities.get(cohort_id))
        if (
            decision_item["company_id"] == "unresolved"
            and summary.get("company_id_hint")
        ):
            decision_item["company_id_hint"] = str(summary["company_id_hint"])
        items.append(decision_item)

    items.extend(
        _sheet_only_items(
            current_holdings,
            cohort_company_ids=cohort_company_ids,
            registry=registry,
        )
    )
    holdings_status = str((current_holdings or {}).get("status") or "unavailable")
    if holdings_status not in {"available", "confirmed", "confirmed_empty"}:
        for item in items:
            blockers = set(item["blockers"])
            blockers.add(f"holdings_{holdings_status}")
            item["blockers"] = sorted(blockers)

    ranked = sorted(
        items,
        key=lambda item: (
            -_ACTION_PRIORITY[str(item["recommended_action"])],
            str(item.get("company_id") or ""),
            str(item.get("cohort_id") or ""),
        ),
    )
    for position, item in enumerate(ranked, 1):
        item["index"] = position  # 穩定編號，供對話式批次核准引用（plan R5）
    recommended = ranked[0]["recommended_action"] if ranked else "NO ACTION"
    if ranked:
        reason = ranked[0]["reason"]
    elif holdings_status not in {"available", "confirmed", "confirmed_empty"}:
        recommended = "REVIEW"
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
            if holdings_status not in {"available", "confirmed", "confirmed_empty"}
            else set()
        )
    )
    brief = {
        "schema_version": "engine-d-today-v1",
        "as_of": as_of,
        "action_needed": recommended != "NO ACTION",
        "recommended_action": recommended,
        "reason": reason,
        "alpha_thesis_changes": [item["alpha_thesis_change"] for item in ranked],
        "beta_portfolio_risk": [item["beta_portfolio_risk"] for item in ranked],
        "supported_sizing_range": [
            item["supported_sizing_range"] for item in ranked
        ],
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
        # `build_today_brief` 的 store contract 刻意是窄 duck-type（遠端受限 surface
        # 也要能產 brief），因此這裡不硬性要求該方法：提供就給數字，沒提供就是
        # None，由 renderer 略過。None 只有一個意思——「這個 surface 不提供」，
        # 不與「數字是 0」混用。
        "capital_expression": (
            counters() if callable(counters := getattr(store, "capital_expression_counters", None))
            else None
        ),
        "items": ranked,
    }
    assert_safe_payload(brief)
    return brief


def _pct(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "未知"
    return f"{value * 100:+.1f}%"


def render_today_markdown(brief: Mapping[str, Any]) -> str:
    """由同一 public DTO 產生 Markdown；不接觸 private payload。

    每個 item 帶穩定編號 [N] 供對話式批次核准引用（plan R5）；顯示自追蹤變化%
    與 evidence_delta，不使用顏色維度（plan R15）。
    """

    assert_safe_payload(brief)
    blockers = "、".join(markdown_text(item) for item in brief.get("blockers") or []) or "無"
    lines = [
        f"# 今天需要動作嗎？{'是' if brief['action_needed'] else '否'}",
        "",
        f"- 建議動作：{markdown_text(brief['recommended_action'])}",
        f"- 原因：{markdown_text(brief['reason'])}",
        f"- Blockers：{blockers}",
        f"- 下一個 review：{markdown_text(brief.get('next_review_at') or '尚未排定')}",
    ]
    counters = brief.get("capital_expression") or {}
    if counters:
        live = int(counters.get("live_range_nonzero") or 0)
        decisions = int(counters.get("decisions") or 0)
        measured = int(counters.get("measured_outcomes") or 0)
        outcomes = int(counters.get("outcomes") or 0)
        version = counters.get("calculator_version")
        current_total = int(counters.get("decisions_current_calculator") or 0)
        current_live = int(counters.get("live_range_nonzero_current") or 0)
        measurable = int(counters.get("shadow_measurable_cohorts") or 0)
        anchored = int(counters.get("shadow_anchored_cohorts") or 0)
        # 量測以 Shadow 錨點為準，不以 outcome_envelopes 為準：後者要人工 close 才有列，
        # 且 2026-08-15 實測 8 筆有 6 筆來自無 ticker 的廢棄 cohort，永遠算不出報酬。
        # 拿它當分母會每天喊「已量測 0/8」，而事實是 9 個有錨點的 cohort 全部可量測。
        eligible = int(counters.get("eligible_cohorts") or 0)
        total_cohorts = int(counters.get("total_cohorts") or 0)
        # 首屏只放使用者實際在盯的三條（ROADMAP 新 workstream）：廣度、量測。
        # 舊的「非零 live 區間 N/決策數」已移除：尺寸不再對人呈現（Alpha 呈現契約），
        # 且它的分母數的是歷來 decision，同一標的每 reassess 一次就 +1。
        # 單位是「有 identity 的公司」不是 cohort：無 company_id 的殘骸與同公司的
        # 重複 cohort 都不計，否則分母會謊報「還有救得回來的標的」。
        line = (
            f"- 研究進展：上線標的 {eligible}/{total_cohorts} 檔"
            f"｜可量測 {measurable}/{anchored} 檔"
        )
        if eligible == 0 and total_cohorts:
            line += "　⚠ 目前沒有任何可評估標的"
        lines.append(line)
        # 提醒各自一行：主行是狀態、子行是待處理項。串在同一行會長到手機讀不完，
        # 而且會讓「數字」與「要做的事」混在一起。exception-first，沒問題就不出現。
        #
        # 公司已上線但底下有重複 cohort：不影響上線比率，但要有人去合併／結案，
        # 否則 Decision Store 會長出兩條互不知道的軌跡（ROADMAP backlog）。
        # 以公司為單位計數是對的，但不能因此把它藏起來——那是把缺陷掃到地毯下。
        dupes = tuple(counters.get("duplicate_cohort_companies") or ())
        if dupes:
            names = "、".join(markdown_text(name) for name in dupes[:3])
            more = f" 等 {len(dupes)} 檔" if len(dupes) > 3 else ""
            lines.append(f"  - ⚠ {names}{more} 有重複 cohort，待合併")
        orphans = int(counters.get("orphan_cohorts") or 0)
        if orphans:
            lines.append(
                f"  - ℹ {orphans} 個無 identity 的 cohort 殘骸；不計入分母，"
                "但仍在 outcome_envelopes 裡（Decision Store append-only，不刪除）"
            )
        if measurable == 0:
            lines.append("  - ⚠ 判斷準不準仍無法用證據回答（無 Shadow 錨點）")
        elif measured == 0 and outcomes:
            # 有錨點就算得出報酬，但尚未有任何 probe 正式結案歸因。
            lines.append(
                f"  - ℹ 報酬可量測但尚無結案歸因（outcome_envelopes {measured}/{outcomes}）；"
                "跑 `scripts/outcome_if_settled_today.py` 看目前表現"
            )
    items = brief.get("items") or []
    if items:
        lines += ["", "## 項目（回覆用編號）"]
        for item in items:
            idx = item.get("index")
            # Sheet-only 持股常無 registry 對應，company_id 會是 unresolved；
            # 顯示 ticker 才看得出是哪一檔。
            label = item.get("company_id") or ""
            if str(label) in {"", "unresolved"} and item.get("ticker"):
                label = item["ticker"]
            company = markdown_text(label)
            action = markdown_text(item.get("recommended_action") or "")
            perf = _pct(item.get("performance_since_tracked"))
            since_decision = _pct(item.get("performance_since_decision"))
            delta = markdown_text(item.get("evidence_delta") or "none")
            lines.append(
                f"- [{idx}] {action} — {company}｜自追蹤 {perf}"
                f"（決策後 {since_decision}）｜證據 {delta}"
            )
            resp = markdown_text(item.get("user_response_needed") or "")
            if resp:
                lines.append(f"      → {resp}")
            disproof = markdown_text(item.get("disproof_condition") or "")
            if disproof:
                lines.append(f"      → Disproof：{disproof}")
    # ── live 入口 ──────────────────────────────────────────────────────────
    # 2026-08-18 紅隊審查 B8：`record-choice --user-sized` 蓋好了，但**沒有任何入口**
    # ——brief 不提、todo pool 不提、Action Card 不提，它是一個使用者必須自己記得的
    # CLI。`live_choices` 至今 0 筆，與「沒有這條路徑」在結果上不可區分（D13）。
    # 這一段把「要記得」變成「看得到」。
    #
    # ⚠ 這**不是**行動指引，不違反 Alpha 呈現契約：指令裡的 `--selected-weight` 刻意
    # 留空給使用者填，brief 不提供任何建議尺寸；系統也不判斷現在該不該買。
    # 它只解決一件事：真的決定要買的時候，有地方可以記錄，記分板才可能有資料。
    actionable = [
        item
        for item in items
        if item.get("decision_id")
        and str(item.get("company_id") or "") not in {"", "unresolved"}
    ]
    if actionable:
        lines += [
            "",
            "## 若你今天決定進場／加碼（指令，不是建議）",
            "",
            "尺寸由你決定；系統不建議金額，也不判斷時點。記錄下來只為了讓「判斷準不準」"
            "日後能用證據回答——目前 `live_choices` 仍是 0 筆，這個問題還無法回答。",
            "",
        ]
        for item in actionable[:8]:
            label = markdown_text(item.get("ticker") or item.get("company_id"))
            lines.append(
                f"- **{label}**：`python -m decision_lab record-choice "
                f"{item['decision_id']} --selected-weight <你的NAV占比> "
                f"--explicit --user-sized --reason \"<為什麼是這個尺寸>\" "
                f"--confirmation-ref \"<你的紀錄編號>\"`"
            )
        lines.append(
            "\n成交後再回報：`python -m decision_lab record-fill <decision_id> "
            "--execution-ref <券商成交編號> --shares <股數> --price <成交價> "
            "--currency <幣別> --explicit`"
        )
        lines.append(
            "⚠ decision 凍結超過 7 天會被拒絕（資本上限讀的是凍結當時的持股快照）；"
            "先跑 `decision_lab reassess` 重新凍結。"
        )

    pending_identity = brief.get("identity_registration_pending") or []
    if pending_identity:
        lines += [
            "",
            "## 結構性阻塞：等 registry 補可交易 ticker（研究無法解決）",
        ]
        for row in pending_identity:
            company = markdown_text(row.get("company_id") or "")
            action = markdown_text(row.get("blocking_action") or "")
            state = "已登記但無 ticker" if row.get("registered") else "尚未登記"
            lines.append(f"- {company}（{state}）→ {action}")
    lines += [
        "",
        "## 需要你回答或回報",
        "\n".join(
            f"- {markdown_text(item)}" for item in brief.get("user_response_needed") or []
        ) or "- 無",
    ]
    return "\n".join(lines)
