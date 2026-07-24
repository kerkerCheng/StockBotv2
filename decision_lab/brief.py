"""純讀、action-first 的 Engine D 今日摘要。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from identity.registry import IdentityRegistry, get_registry
from thesis.investment_policy import load_policy

from .action_card import assert_safe_payload, build_action_card, markdown_text
from .store import DecisionStore
from .workflow_ports import WorkflowDataProvider


_ACTION_PRIORITY = {"NO ACTION": 0, "TRADE": 1, "HEDGE": 2, "REVIEW": 3}


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
        # Shadow-first：自追蹤（凍結決策時＝Shadow inception）到現在的價格變化。
        "performance_since_tracked": current_authority.get("security_return"),
        "evidence_delta": evidence_delta,
        "blockers": blockers,
        "next_review_at": lifecycle.get("review_due_at"),
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


def _current_authority_context(
    store: DecisionStore,
    provider: WorkflowDataProvider,
    summary: Mapping[str, Any],
    *,
    as_of: str,
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
    change = {
        "security_return": security_return,
        "benchmark_return": None,
        "evidence_delta": evidence_delta,
        "disproof_triggered": False,
        "fx_return": fx_return,
    }
    return (
        {
            "blockers": sorted(set(blockers)),
            "security_return": security_return,
            "fx_return": fx_return,
            "evidence_delta": evidence_delta,
        },
        change,
    )


def _portfolio_contexts(
    holdings: Mapping[str, Any] | None,
    summaries: Sequence[Mapping[str, Any]],
    *,
    registry: IdentityRegistry,
) -> dict[str, dict[str, Any]]:
    if not holdings or holdings.get("status") not in {
        "available",
        "confirmed",
        "confirmed_empty",
    }:
        return {}
    nav = holdings.get("nav_base")
    if isinstance(nav, bool) or not isinstance(nav, (int, float)) or nav <= 0:
        return {}
    factor_values: dict[str, float] = {}
    for row in holdings.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        value = row.get("market_value_base")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            continue
        company_id = row.get("company_id")
        if not company_id and isinstance(row.get("ticker"), str):
            company_id = registry.company_id_for_ticker(str(row["ticker"]))
        for factor in registry.factor_tags(str(company_id or "")):
            factor_values[factor] = factor_values.get(factor, 0.0) + float(value)
    caps = load_policy()["factor_exposure_caps"]
    over = {
        factor: value / float(nav)
        for factor, value in factor_values.items()
        if factor in caps and value / float(nav) > float(caps[factor])
    }
    result: dict[str, dict[str, Any]] = {}
    for summary in summaries:
        company_id = str(summary.get("company_id") or "")
        breached = sorted(set(registry.factor_tags(company_id)) & set(over))
        if breached:
            result[str(summary["cohort_id"])] = {
                "status": "over_cap",
                "factor": breached[0],
                "reason": f"目前 {breached[0]} factor exposure 超過 versioned policy 上限。",
            }
    return result


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
        "user_response_needed": "請執行 reassess 或補齊 research work order。",
    }


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
        result.append(
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": _public_company(company_id),
                "recommended_action": "REVIEW",
                "reason": "Google Sheet 有 live 持股，但 Engine D 尚無對應 cohort／decision。",
                "alpha_thesis_change": {
                    "classification": "unknown",
                    "thesis_changed": False,
                },
                "beta_portfolio_risk": {
                    "portfolio_action": "review_uncovered_holding",
                    "classification": "unknown",
                },
                "supported_sizing_range": [0.0, 0.0],
                "blockers": ["sheet_only_holding", "decision_missing"],
                "next_review_at": None,
                "user_response_needed": "請先 evaluate-signal／onboard；未完成前不提供 live sizing。",
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
        for summary in summaries:
            authority, derived_change = _current_authority_context(
                store, provider, summary, as_of=as_of
            )
            current_authorities.setdefault(str(summary["cohort_id"]), authority)
            changes.setdefault(str(summary["cohort_id"]), derived_change)
    derived_portfolios = _portfolio_contexts(
        current_holdings, summaries, registry=registry
    )
    for cohort_id, context in derived_portfolios.items():
        portfolios.setdefault(cohort_id, context)
    items: list[dict[str, Any]] = []
    cohort_company_ids: set[str] = set()
    for summary in summaries:
        cohort_id = str(summary["cohort_id"])
        if summary.get("company_id"):
            cohort_company_ids.add(str(summary["company_id"]))
        decision_id = summary.get("latest_decision_id")
        if decision_id is None:
            items.append(_pending_item(summary))
            continue
        card = build_action_card(
            store,
            str(decision_id),
            as_of=as_of,
            change_context=changes.get(cohort_id),
            portfolio_context=portfolios.get(cohort_id),
        )
        card["cohort_id"] = cohort_id
        items.append(_decision_item(card, current_authorities.get(cohort_id)))

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
        "user_response_needed": [
            item["user_response_needed"]
            for item in ranked
            if item["user_response_needed"].startswith("請")
        ],
        "items": ranked,
    }
    assert_safe_payload(brief)
    return brief


def render_today_markdown(brief: Mapping[str, Any]) -> str:
    """由同一 public DTO 產生 Markdown；不接觸 private payload。"""

    assert_safe_payload(brief)
    blockers = "、".join(markdown_text(item) for item in brief.get("blockers") or []) or "無"
    response = "\n".join(
        f"- {markdown_text(item)}" for item in brief.get("user_response_needed") or []
    ) or "- 無"
    return "\n".join(
        [
            f"# 今天需要動作嗎？{'是' if brief['action_needed'] else '否'}",
            "",
            f"- 建議動作：{markdown_text(brief['recommended_action'])}",
            f"- 原因：{markdown_text(brief['reason'])}",
            f"- Blockers：{blockers}",
            f"- 下一個 review：{markdown_text(brief.get('next_review_at') or '尚未排定')}",
            "",
            "## 需要你回答或回報",
            response,
        ]
    )
