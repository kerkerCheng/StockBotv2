"""Action-first、純讀的 Decision Card structured primitive 與 Markdown renderer。"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from .adapters.market import sessions_between
from .blocker_severity import fatal_blockers
from .redaction import sensitive_payload_path
from .store import DecisionStore


class RedactionError(ValueError):
    """Payload contains a field that must never enter output or diagnostics。"""


_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#+.!|-])")


def markdown_text(value: Any) -> str:
    """將外部文字限制成單行並 escape Markdown／terminal control。"""

    text = _ANSI_ESCAPE.sub("", str(value)).replace("\r", " ").replace("\n", " ")
    text = "".join(character if character >= " " else " " for character in text)
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def assert_safe_payload(value: Any, path: str = "root") -> None:
    sensitive = sensitive_payload_path(value, path)
    if sensitive is not None:
        raise RedactionError(f"secret-bearing value rejected at {sensitive}")


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
    # 窗口必須是**追蹤期**（Shadow inception 起算），不是「自上次凍結 decision 以來」。
    # 後者會被 reassess 重設，等於讓分類窗口可以被自己的操作縮短到零：2026-08-08
    # 實測 co:axt 在 reassess 兩小時後被判 beta（自決策以來 +0.0% vs QQQ −1.2%），
    # 而它自追蹤以來是 +107%、超額 +101pp——正確但毫無資訊，且蓋掉了真正的事實。
    # 缺 Shadow 錨點時才退回決策錨點，兩側必須成對取用，不得混錨。
    shadow_security = _finite(change.get("shadow_return"))
    shadow_benchmark = _finite(change.get("benchmark_shadow_return"))
    if shadow_security is not None and shadow_benchmark is not None:
        security, benchmark = shadow_security, shadow_benchmark
    else:
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


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed


def _runtime_freshness(
    context: Mapping[str, Any], as_of: str
) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    now = _time(as_of, "as_of")
    policy = context.get("freshness_policy") or {}
    # 行情用「交易日」而不是「小時」量測。日線 bar 的 as_of 是交易日**當地午夜**，
    # 但它代表的是當天收盤（美股約 20:00 UTC）；拿它當觀測時刻做小時級減法，等於
    # 憑空多算約 20 小時的假過期。實測 co:axt 的決策凍結於 2026-08-06 12:41Z、
    # 凍入 08-05 的 bar，36 小時上限在 12:00Z 就到期——**決策在出生當下即已 stale**，
    # 三筆候選 cohort 同時中招。這會讓每份 brief 都在喊 refresh，而 refresh 完仍是紅的。
    #
    # FX 同源同病：provider 回的也是 yfinance 日線 bar，先前留在小時制的理由
    #（「FX 是連續報價」）是按概念推理而沒查資料源，已一併改為交易日。
    # 只有 financial 維持 days——它跟的是財報週期，本來就不是以交易日為心跳。
    specs = {
        "market": ("market_freshness_sessions", "sessions", "paper"),
        "fx": ("fx_freshness_sessions", "sessions", "paper"),
        "financial": ("financial_freshness_days", "days", "paper"),
        "execution_market": ("market_freshness_sessions", "sessions", "live"),
        "execution_fx": ("fx_freshness_sessions", "sessions", "live"),
        "holdings": ("holdings_freshness_days", "days", "live"),
    }
    result = _freshness(context)
    paper: list[str] = []
    live: list[str] = []
    for section, (policy_key, unit, lane) in specs.items():
        payload = context.get(section) or {}
        status = str(payload.get("status") or "missing")
        accepted = {"available"} if section != "holdings" else {
            "confirmed",
            "confirmed_empty",
        }
        if status not in accepted:
            continue
        source_time = _time(
            payload.get("as_of") or payload.get("confirmed_at"),
            f"{section}.as_of",
        )
        amount = _finite(policy.get(policy_key))
        if amount is None and unit == "sessions":
            # 舊 decision 凍的是改制前的 market_freshness_hours。凍結決策必須用它
            # **自己當時的 policy** 評估——那正是 policy_version 被凍進 context 的
            # 意義；若因為找不到新 key 就一律判 stale，等於用今天的規則追溯懲罰
            # 昨天的決策，而且會讓每份 brief 都在喊 refresh。
            legacy_key = (
                "fx_freshness_hours"
                if policy_key.startswith("fx_")
                else "market_freshness_hours"
            )
            legacy = _finite(policy.get(legacy_key))
            if legacy is not None and legacy > 0:
                amount, unit = legacy, "hours"
        if amount is None or amount <= 0 or source_time > now:
            stale = True
        elif unit == "sessions":
            stale = sessions_between(source_time, now) > amount
        else:
            limit = timedelta(**{unit: amount})
            stale = now - source_time > limit
        if stale:
            blocker = f"{section}_stale_since_decision"
            (paper if lane == "paper" else live).append(blocker)
            result[section]["status"] = "stale_since_decision"
    return result, tuple(sorted(paper)), tuple(sorted(live))


def build_action_card(
    store: DecisionStore,
    decision_id: str,
    *,
    as_of: str | None = None,
    change_context: Mapping[str, Any] | None = None,
    portfolio_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read one frozen decision and explain the next user-visible action。"""

    assert_safe_payload(change_context or {})
    assert_safe_payload(portfolio_context or {})
    decision = store.get_decision(decision_id)
    card_as_of = as_of or datetime.now(timezone.utc).isoformat()
    if _time(card_as_of, "as_of") < _time(decision["effective_at"], "decision.effective_at"):
        raise ValueError("Action Card as_of cannot predate the decision")
    payload = decision["payload"]
    sizing = payload["sizing"]
    coverage_id = str(
        (payload.get("request", {}).get("coverage") or {}).get("assessment_id") or ""
    )
    try:
        coverage_metadata = store.get_coverage_metadata(coverage_id)
        disproof_condition = coverage_metadata["disproof"]
    except (KeyError, TypeError):
        coverage_metadata = {}
        disproof_condition = ""
    # 有效期到了但沒人關，probe 會永遠停在 active 並每天占用注意力：`expiry` 只在
    # coverage 建立當下被檢查一次（expiry_invalid），之後沒有任何東西回頭看它。
    # 實測 co:iqe 的 expiry 是前一日、兩個 unresolved cohort 逾期六天，全都仍是
    # active。這裡只**呈現**、不自動關閉——自動關閉需要 expiry 本身先訂對（實測
    # co:axt 的 expiry 比它自己的催化劑早三個月，自動關會關掉一個還在跑的 thesis）。
    probe_expiry = str(coverage_metadata.get("expiry") or "")
    expiry_lapsed = False
    if probe_expiry:
        try:
            expiry_lapsed = _time(card_as_of, "as_of") > _time(probe_expiry, "expiry")
        except ValueError:
            expiry_lapsed = False
    execution_intent = str(payload.get("request", {}).get("execution_intent") or "live")
    paper_requested = execution_intent in {"paper", "live"}
    live_requested = execution_intent == "live"
    context = store.get_context_bundle(decision["context_digest"]).payload
    authority_company_id = str(context["identity"].get("company_id") or "")
    company_id = authority_company_id or "unresolved"
    paper_position = store.paper_position_state(authority_company_id)
    live_choice = store.latest_live_choice(decision_id)
    live_fill = store.latest_live_fill(decision_id)
    if (
        live_fill is not None
        and live_choice is not None
        and live_fill.get("choice_id") != live_choice.get("choice_id")
    ):
        live_fill = None
    lifecycle = store.current_lifecycle(decision["cohort_id"])
    lifecycle_started_at = store.lifecycle_epoch_started_at(
        decision["cohort_id"], lifecycle.epoch
    )
    revised_decision_stale = bool(
        lifecycle.epoch > 1
        and lifecycle_started_at
        and _time(decision["effective_at"], "decision.effective_at")
        < _time(lifecycle_started_at, "lifecycle.started_at")
    )
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
    freshness, current_paper_blockers, current_live_blockers = _runtime_freshness(
        context, card_as_of
    )
    if current_paper_blockers and paper_requested:
        paper_status = "DATA_NEEDED"
    if current_live_blockers and live_requested:
        live_status = "DATA_NEEDED"
    if not paper_requested:
        paper_status = "NOT_REQUESTED"
    if not live_requested:
        live_status = "NOT_REQUESTED"
    coverage_blockers = tuple(
        (payload.get("request", {}).get("coverage") or {}).get("blockers", [])
    )
    core_blockers = sorted(
        set(sizing.get("assessment_blockers", [])) | set(coverage_blockers)
    )
    # coverage.py 早已把 blocker 分成「致命」與「研究不完整」兩類，sizing 也依此
    # 決定 coverage_cap 要不要歸零。但 card 先前對整個 core_blockers 一視同仁判
    # REVIEW，等於把 sizing 已經放行的資本又在展示層擋掉一次——同一份清單被兩個
    # 子系統套了兩套嚴重度政策，而使用者只看得到嚴格的那一套。
    # 判準沿用 coverage 的分類：只有致命 coverage blocker 與 assessment blocker
    # 才強制 REVIEW。assessment blocker 一律算致命，因為任何一軸失效都會讓
    # axis_ceiling 取 min 後歸零，此時「研究不完整」的描述並不成立。
    research_incomplete_blockers = sorted(
        set(coverage_blockers) - set(fatal_blockers(coverage_blockers))
    )
    blocking_core_blockers = sorted(
        set(core_blockers) - set(research_incomplete_blockers)
    )

    if disproof_triggered:
        action = "REVIEW"
        urgency = "within_48h"
        if portfolio_status == "over_cap":
            factor = str((portfolio_context or {}).get("factor") or "unknown_factor")
            portfolio_action = f"reduce_or_hedge:{factor}"
        else:
            portfolio_action = "none"
        single_name_action = "mandatory_thesis_review"
        reason = "可證偽條件已被標記觸發，需要在 48 小時內重新審查。"
        next_action = "核對觸發證據；同時執行必要的投組降險，再決定 rejected 或 revised。"
    elif lifecycle.status in {"rejected", "expired"}:
        action = "REVIEW"
        urgency = "prompt"
        portfolio_action = "none"
        single_name_action = "terminal_unwind_review"
        reason = f"Probe 已進入 terminal 狀態 {lifecycle.status}，不得沿用舊建議新增部位。"
        next_action = "檢查 paper/live 殘餘部位並決定減碼、出場或僅保留歷史紀錄。"
    elif lifecycle.status == "promoted":
        action = "REVIEW"
        urgency = "next_review"
        portfolio_action = "none"
        single_name_action = "handoff_to_formal_lane"
        reason = "Probe 已升格；舊 Probe sizing 不再授權新交易。"
        next_action = "使用 formal Watchlist／Underwrite 規則重新產生部位建議。"
    elif revised_decision_stale:
        action = "REVIEW"
        urgency = "prompt"
        portfolio_action = "none"
        single_name_action = "reassess_revised_epoch"
        reason = "Thesis 已 revised；舊 epoch 的 decision 不再授權新交易。"
        next_action = "在新 epoch 重新 freeze context、coverage 與 sizing。"
    elif expiry_lapsed:
        action = "REVIEW"
        urgency = "prompt"
        portfolio_action = "none"
        single_name_action = "expiry_lapsed_close_or_extend"
        reason = f"Probe 有效期 {probe_expiry[:10]} 已過，催化劑未在期限內發生。"
        next_action = (
            "決定 close_probe（expired）或以新催化劑時點 reassess 延期；"
            "延期前先確認 expiry 不早於催化劑本身。"
        )
    elif blocking_core_blockers:
        action = "REVIEW"
        urgency = "next_review"
        portfolio_action = "none"
        single_name_action = "complete_research_work_order"
        reason = "研究 coverage 或 Confidence assessment 尚未完整。"
        next_action = "補齊 blockers 指向的 evidence／研究欄位後執行 reassess。"
    elif (current_paper_blockers and paper_requested) or (
        current_live_blockers and live_requested
    ):
        action = "REVIEW"
        urgency = "data_refresh"
        portfolio_action = "none"
        single_name_action = "refresh_and_reassess"
        reason = "凍結決策的必要市場、財務或持倉資料已過期。"
        next_action = "重新 freeze context 並 assess；舊 card 只保留歷史用途。"
    elif portfolio_status == "over_cap":
        factor = str((portfolio_context or {}).get("factor") or "unknown_factor")
        action = "HEDGE"
        urgency = "prompt"
        portfolio_action = f"reduce_or_hedge:{factor}"
        single_name_action = "hold_pending_portfolio_action"
        reason = str(
            (portfolio_context or {}).get("reason")
            or "投組曝險超過明確傳入的風險上限。"
        )
        next_action = f"決定要降低或對沖 {factor} 曝險；資料不足時不輸出單位數。"
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
    elif (
        live_status == "ELIGIBLE"
        and float(sizing["live_current_position"])
        > float(sizing["live_supported_range"][1]) + 1e-12
    ):
        action = "REVIEW"
        urgency = "prompt"
        portfolio_action = "none"
        single_name_action = "reduce_to_supported_range"
        reason = "目前 live 部位高於研究所支持的上限。"
        next_action = "檢視減碼或保留 override 的理由；系統不會自動下單。"
    elif (
        live_status == "ELIGIBLE"
        and float(sizing["live_supported_range"][0]) - 1e-12
        <= float(sizing["live_current_position"])
        <= float(sizing["live_supported_range"][1]) + 1e-12
    ):
        action = "NO_ACTION"
        urgency = "routine"
        portfolio_action = "none"
        single_name_action = "hold_within_supported_range"
        reason = "目前 live 部位已在研究支持區間內。"
        next_action = "維持部位並依 catalyst／expiry 日曆追蹤。"
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
    # core_blockers（assessment ∪ coverage）正是把 action 判成 REVIEW 的原因，
    # 必須出現在 card 自己的 blockers 裡。先前只放 assessment_blockers，於是
    # coverage blocker（如 financial_runway_manual_required）會驅動 REVIEW 卻不
    # 現身，下游只看得到 lane blocker，導致待辦池推導出「重新 reassess 即可」
    # 這種與真正缺口無關的等待理由。
    # 研究不完整的 blocker 不再驅動 REVIEW，但仍必須留在 blockers 裡——它們透過
    # axis_ceiling 影響尺寸，是「會改變輸出的輸入」，另以 research_incomplete_blockers
    # 標明它們沒有阻擋，否則下游只會看到一份混在一起的清單而無法分辨。
    blockers = sorted(
        set(core_blockers)
        | set(sizing.get("paper_blockers", []))
        | set(sizing.get("live_blockers", []))
        | set(current_paper_blockers)
        | set(current_live_blockers)
    )
    card = {
        "schema_version": "action-card-v1",
        "decision_id": decision_id,
        "decision_digest": decision["decision_digest"],
        "as_of": card_as_of,
        "company_id": company_id,
        "execution_intent": execution_intent,
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
            "started_at": lifecycle_started_at,
        },
        "disproof_condition": disproof_condition,
        # 有效期是決策的一部分，必須跟 disproof 一樣出現在 card 自己的欄位裡：
        # 只放進 reason 文字，下游任何覆蓋 reason 的地方都會把它弄丟。
        "probe_expiry": probe_expiry or None,
        "expiry_lapsed": expiry_lapsed,
        "weakest_link": {
            "axis": axis,
            "level": axis_result["level"],
            "reason": axis_result["reason"],
            "missing_data": axis_result["missing_data"],
        },
        "paper": {
            "status": paper_status,
            "funded": float(paper_position["weight"]) > 0,
            "event_id": paper_position["source_event_id"],
            "current_position": paper_position["weight"],
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
        "freshness": freshness,
        "blockers": blockers,
        "research_incomplete_blockers": research_incomplete_blockers,
        "sources": sources,
        "policy_version": sizing["policy_version"],
        "calculator_version": sizing["calculator_version"],
        "next_action": next_action,
    }
    assert_safe_payload(card)
    return card


def render_markdown(card: Mapping[str, Any]) -> str:
    assert_safe_payload(card)
    weakest = card["weakest_link"]
    paper = card["paper"]
    live = card["live"]
    blockers = ", ".join(markdown_text(item) for item in card["blockers"]) if card["blockers"] else "無"
    incomplete = card.get("research_incomplete_blockers") or []
    incomplete_line = (
        ", ".join(markdown_text(item) for item in incomplete) if incomplete else "無"
    )
    return "\n".join(
        [
            f"# {markdown_text(card['action'])} — {markdown_text(card['company_id'])} ({markdown_text(card['urgency'])})",
            "",
            f"- 理由：{markdown_text(card['reason'])}",
            f"- Alpha / Beta：{markdown_text(card['alpha_beta']['classification'])}",
            f"- Disproof condition：{markdown_text(card.get('disproof_condition') or '未提供')}",
            f"- Weakest link：{markdown_text(weakest['axis'])} / {markdown_text(weakest['level'])} — {markdown_text(weakest['reason'])}",
            f"- Intent：{markdown_text(card.get('execution_intent', 'live'))}",
            # Alpha 呈現契約（2026-08-15）：不對人輸出建議尺寸。
            # 那個數字來自從未被 outcome 驗證的 axis_ceiling，且實測 6 個 ELIGIBLE
            # cohort 全是同一個 0.1%——常數不帶資訊，卻讓人以為系統在給建議。
            # 數值仍完整保留在 JSON（稽核與 outcome 量測要用），只是不再當行動指引呈現。
            f"- Paper 記分板：{markdown_text(paper['status'])}"
            f"（模擬部位持續累積，供 outcome 量測；不是建議部位）",
            "- Live：人工決定——系統不輸出建議尺寸",
            f"- Blockers：{blockers}",
            f"- 研究不完整（不阻擋，只縮小尺寸）：{incomplete_line}",
            "",
            f"## 下一步\n{markdown_text(card['next_action'])}",
        ]
    )
