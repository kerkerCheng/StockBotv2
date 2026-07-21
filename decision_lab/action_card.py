"""Action-first、純讀的 Decision Card structured primitive 與 Markdown renderer。"""
from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

from .store import DecisionStore


_SENSITIVE_KEY = re.compile(
    r"password|passwd|token|secret|credential|service.?account|dsn|private.?key",
    re.IGNORECASE,
)


class RedactionError(ValueError):
    """Payload contains a field that must never enter output or diagnostics。"""


def assert_safe_payload(value: Any, path: str = "root") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                raise RedactionError(f"secret-bearing field rejected at {path}.{key}")
            assert_safe_payload(child, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            assert_safe_payload(child, f"{path}[{index}]")


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _alpha_beta(change: Mapping[str, Any] | None) -> dict[str, Any]:
    if not change:
        return {
            "classification": "unknown",
            "thesis_changed": False,
            "security_return": None,
            "benchmark_return": None,
        }
    evidence_delta = str(change.get("evidence_delta") or "unknown")
    security = _finite(change.get("security_return"))
    benchmark = _finite(change.get("benchmark_return"))
    disproof = change.get("disproof_triggered") is True
    if disproof or evidence_delta in {"positive", "negative", "material"}:
        classification = "alpha"
    elif (
        evidence_delta == "none"
        and security is not None
        and benchmark is not None
        and security * benchmark >= 0
        and abs(security - benchmark) <= 0.03
    ):
        classification = "beta"
    else:
        classification = "mixed_or_unknown"
    return {
        "classification": classification,
        "thesis_changed": disproof or evidence_delta in {"positive", "negative", "material"},
        "security_return": security,
        "benchmark_return": benchmark,
        "evidence_delta": evidence_delta,
    }


def _freshness(context: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for section in (
        "financial",
        "market",
        "fx",
        "execution_market",
        "execution_fx",
        "holdings",
    ):
        payload = context.get(section) or {}
        result[section] = {
            "status": payload.get("status", "missing"),
            "as_of": payload.get("as_of") or payload.get("confirmed_at"),
        }
    return result


def build_action_card(
    store: DecisionStore,
    decision_id: str,
    *,
    change_context: Mapping[str, Any] | None = None,
    portfolio_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read one frozen decision and explain the next user-visible action。"""

    assert_safe_payload(change_context or {})
    assert_safe_payload(portfolio_context or {})
    decision = store.get_decision(decision_id)
    payload = decision["payload"]
    sizing = payload["sizing"]
    context = store.get_context_bundle(decision["context_digest"]).payload
    paper_event = store.paper_event_for_decision(decision_id)
    live_choice = store.latest_live_choice(decision_id)
    live_fill = store.latest_live_fill(decision_id)
    lifecycle = store.current_lifecycle(decision["cohort_id"])
    alpha_beta = _alpha_beta(change_context)
    disproof_triggered = bool(
        (change_context or {}).get("disproof_triggered")
        or lifecycle.status == "review_required"
    )
    if lifecycle.status == "review_required":
        alpha_beta["classification"] = "alpha"
        alpha_beta["thesis_changed"] = True
    portfolio_status = str((portfolio_context or {}).get("status") or "ok")
    live_status = str(sizing["live_status"])
    paper_status = str(sizing["paper_status"])

    if portfolio_status == "over_cap":
        factor = str((portfolio_context or {}).get("factor") or "unknown_factor")
        action = "HEDGE"
        urgency = "prompt"
        portfolio_action = f"reduce_or_hedge:{factor}"
        single_name_action = "hold_pending_portfolio_action"
        reason = str(
            (portfolio_context or {}).get("reason")
            or "投組 factor exposure 超過上限。"
        )
        next_action = f"決定要降低或對沖 {factor} 曝險；資料不足時不輸出單位數。"
    elif disproof_triggered:
        action = "REVIEW"
        urgency = "within_48h"
        portfolio_action = "none"
        single_name_action = "mandatory_thesis_review"
        reason = "可證偽條件已被標記觸發，需要在 48 小時內重新審查。"
        next_action = "核對觸發證據並決定 rejected、revised 或 promoted。"
    elif live_fill is not None:
        action = "NO_ACTION"
        urgency = "routine"
        portfolio_action = "none"
        single_name_action = "monitor_confirmed_live_execution"
        reason = "使用者已回報 live 成交；目前只監控 thesis、風險與資料例外。"
        next_action = "確認 Google Sheet 持股已更新，並依 review calendar 追蹤。"
    elif live_choice is not None and live_choice["choice_type"] == "skipped":
        action = "NO_ACTION"
        urgency = "routine"
        portfolio_action = "none"
        single_name_action = "respect_explicit_skip"
        reason = "使用者已明確選擇 0% live；system paper 仍獨立保留作 counterfactual。"
        next_action = "除非 evidence 或風險狀態改變，維持 skip 並等下一個 review 點。"
    elif live_choice is not None and float(live_choice["selected_weight"]) > 0:
        action = "TRADE"
        urgency = "awaiting_manual_execution"
        portfolio_action = "none"
        single_name_action = "execute_confirmed_live_choice"
        reason = "使用者已明確接受 live 配置，但尚未回報手動成交。"
        next_action = "手動下單後回報 execution reference；系統不會連接 broker。"
    elif live_status == "ELIGIBLE":
        action = "TRADE"
        urgency = "user_decision"
        portfolio_action = "none"
        single_name_action = "accept_skip_or_size_below_supported_range"
        reason = "研究與 live lane 資料完整；是否手動下單仍需使用者明確決定。"
        next_action = "選擇接受、低配或跳過；下單後回報成交 reference。"
    elif paper_status == "DATA_NEEDED" or live_status == "DATA_NEEDED":
        action = "REVIEW"
        urgency = "next_review"
        portfolio_action = "none"
        single_name_action = "supply_missing_data"
        reason = "至少一個 lane 的必要輸入不完整；paper 與 live 權限分開保留。"
        next_action = "補齊 blockers 中的 point-in-time 資料後重新 assess。"
    else:
        action = "NO_ACTION"
        urgency = "routine"
        portfolio_action = "none"
        single_name_action = "hold_or_shadow"
        reason = (
            "價格變化主要跟隨 benchmark，且沒有新的公司證據。"
            if alpha_beta["classification"] == "beta"
            else "沒有新的 evidence、風險上限或資料例外需要動作。"
        )
        next_action = "依 catalyst／expiry 日曆在下一個 review 點重查。"

    axis = sizing["weakest_axis"]
    axis_result = sizing["axis_results"][axis]
    sources = sorted(
        {
            reference
            for result in sizing["axis_results"].values()
            for reference in result.get("evidence_refs", [])
        }
    )
    live_shares = sizing.get("live_supported_shares")
    if live_status != "ELIGIBLE":
        live_shares = None
    blockers = sorted(
        set(sizing.get("assessment_blockers", []))
        | set(sizing.get("paper_blockers", []))
        | set(sizing.get("live_blockers", []))
    )
    card = {
        "schema_version": "action-card-v1",
        "decision_id": decision_id,
        "decision_digest": decision["decision_digest"],
        "company_id": context["identity"].get("company_id"),
        "action": action,
        "urgency": urgency,
        "scope": {
            "single_name": single_name_action,
            "portfolio": portfolio_action,
        },
        "reason": reason,
        "alpha_beta": alpha_beta,
        "lifecycle": {
            "epoch": lifecycle.epoch,
            "status": lifecycle.status,
            "review_due_at": lifecycle.review_due_at,
        },
        "weakest_link": {
            "axis": axis,
            "level": axis_result["level"],
            "reason": axis_result["reason"],
            "missing_data": axis_result["missing_data"],
        },
        "paper": {
            "status": paper_status,
            "funded": paper_event is not None,
            "event_id": paper_event["paper_event_id"] if paper_event else None,
            "target": sizing["paper_target"],
            "max_supported_position": sizing["paper_max_supported_position"],
        },
        "live": {
            "status": live_status,
            "supported_range": sizing["live_supported_range"],
            "supported_shares": live_shares,
            "approval_required": live_status == "ELIGIBLE" and live_choice is None,
            "user_choice": live_choice,
            "fill_reported": live_fill is not None,
        },
        "freshness": _freshness(context),
        "blockers": blockers,
        "sources": sources,
        "policy_version": sizing["policy_version"],
        "calculator_version": sizing["calculator_version"],
        "next_action": next_action,
    }
    assert_safe_payload(card)
    return deepcopy(card)


def render_markdown(card: Mapping[str, Any]) -> str:
    assert_safe_payload(card)
    weakest = card["weakest_link"]
    paper = card["paper"]
    live = card["live"]
    blockers = ", ".join(card["blockers"]) if card["blockers"] else "無"
    return "\n".join(
        [
            f"# {card['action']} — {card['company_id']} ({card['urgency']})",
            "",
            f"- 理由：{card['reason']}",
            f"- Alpha / Beta：{card['alpha_beta']['classification']}",
            f"- Weakest link：{weakest['axis']} / {weakest['level']} — {weakest['reason']}",
            f"- Paper：{paper['status']}；target={paper['target']:.4%}；funded={paper['funded']}",
            f"- Live：{live['status']}；range={tuple(live['supported_range'])}",
            f"- Blockers：{blockers}",
            "",
            f"## 下一步\n{card['next_action']}",
        ]
    )
