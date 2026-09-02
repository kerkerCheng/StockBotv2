"""純讀、action-first 的 Engine D 今日摘要。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from identity.registry import IdentityRegistry, get_registry
from .action_card import assert_safe_payload, build_action_card, markdown_text
from .models import TERMINAL_LIFECYCLE_STATUSES
from .store import DecisionStore
from .workflow_ports import WorkflowDataProvider


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

    from .blockers import describe_blocker

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
        # MONITOR，統一待辦池才不會每天替它們配一個新 pq2 編號。
        sleeve = beta_aliases.get(ticker)
        ignore_reason = ignored.get(ticker)
        if sleeve:
            attention = "MONITOR"
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
            attention = "MONITOR"
            coverage = "user_ignored"
            reason = f"使用者指定不做 alpha 研究：{ignore_reason}"
            portfolio_action = "user_ignored_holding"
            blockers = []
            request = "無；要恢復追蹤請移除 config/holdings_coverage.json 的該筆登記。"
        else:
            attention = "REVIEW"
            coverage = "uncovered"
            reason = "Google Sheet 有 live 持股，但 Engine D 尚無對應 cohort／decision。"
            portfolio_action = "review_uncovered_holding"
            blockers = ["sheet_only_holding", "decision_missing"]
            request = "請先 evaluate-signal／onboard，讓這檔進入瓶頸排序。"

        result.append(
            {
                "cohort_id": None,
                "decision_id": None,
                "company_id": _public_company(company_id),
                "ticker": ticker,
                "sheet_only": True,
                "coverage": coverage,
                "attention": attention,
                "reason": reason,
                "alpha_thesis_change": {
                    "classification": "unknown",
                    "thesis_changed": False,
                },
                "beta_portfolio_risk": {
                    "portfolio_action": portfolio_action,
                    "classification": "unknown",
                },
                "blockers": blockers,
                "next_review_at": None,
                "disproof_condition": "",
                "user_response_needed": request,
            }
        )
    return result


def _alpha_position_events(
    store: Any,
    *,
    series_by_ticker: Mapping[str, Any] | None,
) -> list[dict[str, Any]] | None:
    """Alpha live 部位的事件 packet；surface 不提供這個能力時回 None。

    ⚠ 這條路徑存在的理由見 `alpha_event_monitor` 的模組 docstring：beta 的事件監控
    對 alpha 部位結構上恆不觸發。行情缺失、provider 失敗或未登記門檻都只降級成
    空 list，不阻斷 brief——事件監控是加值訊號，不是 brief 的前置條件。
    """

    positions_fn = getattr(store, "open_live_positions", None)
    if not callable(positions_fn):
        return None
    try:
        from thesis.investment_policy import load_policy

        from .alpha_event_monitor import alpha_event_search_requests, fetch_close_series

        positions = list(positions_fn())
        if not positions:
            return []
        policy = load_policy()
        monitor = policy.get("live_position_monitor") or {}
        series = series_by_ticker
        if series is None:
            series = fetch_close_series(
                (position.get("ticker") for position in positions),
                sessions=int(monitor.get("history_sessions") or 10),
            )
        return alpha_event_search_requests(
            positions, series_by_ticker=series or {}, policy=policy
        )
    except Exception:  # noqa: BLE001 — 監控失敗不得讓整份 brief 失敗
        return []


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
    alpha_series_by_ticker: Mapping[str, Any] | None = None,
    ranking: Mapping[str, Any] | None = None,
    nav_exposure: Mapping[str, Any] | None = None,
    identity_alignment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """掃描 cohorts／decisions 與當前 Sheet snapshot；不寫入任何 authority。

    `ranking`（`ranking_view.build_ranking_view` 的輸出）與 `nav_exposure`
    （`nav_exposure.build_nav_exposure` 的輸出）由呼叫端注入——前者需要 Neo4j、
    後者需要 Google Sheet，而這一層不得 import 任何一個。兩者缺席時首屏照常渲染，
    只是少了那兩區；不得因此讓整份 brief 失敗。
    """

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
    elif holdings_status not in {"available", "confirmed", "confirmed_empty"}:
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
            if holdings_status not in {"available", "confirmed", "confirmed_empty"}
            else set()
        )
    )
    # C-1（ROADMAP 2026-08-29）：研究完整（READY）且尚無 live choice 的 cohort，
    # 若同時不在瓶頸排序（substitutability 過濾會排除工業標的），就會兩邊都不在——
    # 「研究做完整之後標的反而消失」。這份常駐清單只呈現、不催辦、不建 pq2 編號。
    # ranking 未注入時為 None（無法比對，不與「沒有這類標的」的空 list 混用；L12）。
    if ranking:
        # 優先用截斷前的完整候選集合（ranking_view.company_ids）；舊 DTO 沒有這個
        # 欄位時退回 rows——此時只帶前 limit 名，排在其後的公司會被誤判成
        # 「不在排序」，寧可標示保守也不猜。
        _ranked_company_ids = set(ranking.get("company_ids") or []) or {
            str(row.get("company_id") or "")
            for key in ("actionable", "structural")
            for row in (ranking.get(key) or [])
        }
        ready_not_ranked: list[dict[str, Any]] | None = [
            {
                "company_id": item["company_id"],
                "weakest_axis": item.get("weakest_axis"),
                "attention": item["attention"],
            }
            for item in ranked
            if item.get("research_status") == "READY"
            and not item.get("live_user_choice")
            and item["company_id"] != "unresolved"
            and item["company_id"] not in _ranked_company_ids
        ]
    else:
        ready_not_ranked = None

    brief = {
        "schema_version": "engine-d-today-v1",
        "as_of": as_of,
        # 系統終點：瓶頸排序在前、NAV 比例在後。兩者都是注入的（見 docstring）。
        "ranking": dict(ranking) if ranking else None,
        "ready_not_ranked": ready_not_ranked,
        "nav_exposure": dict(nav_exposure) if nav_exposure else None,
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
        # `build_today_brief` 的 store contract 刻意是窄 duck-type（遠端受限 surface
        # 也要能產 brief），因此這裡不硬性要求該方法：提供就給數字，沒提供就是
        # None，由 renderer 略過。None 只有一個意思——「這個 surface 不提供」，
        # 不與「數字是 0」混用。
        "capital_expression": (
            counters() if callable(counters := getattr(store, "capital_expression_counters", None))
            else None
        ),
        # 公司三集合對齊常駐計數器（2026-09-02 使用者稽核定案）：圖∖registry 是
        # join-key 契約破口（應恆 0），registry∖圖 是登記未研究。None＝呼叫端未注入
        #（如遠端受限 surface），不與「對齊為 0」混用。
        "identity_alignment": (
            dict(identity_alignment) if identity_alignment is not None else None
        ),
        # Alpha live 部位的事件監控。與 `capital_expression` 同一個窄 duck-type
        # 契約：surface 不提供就是 None，不與「有部位但沒事」的空 list 混用。
        "alpha_position_events": _alpha_position_events(
            store, series_by_ticker=alpha_series_by_ticker
        ),
        # 備份計數器：private authority「最後一次備份 N 天前」必須自己出現在首屏
        # （L14——靠人記得跑 scripts/backup_private.py 的段落就是會被忘記的段落）。
        # None 只代表這個 surface 沒有 private root，不與「從未備份」混用（L12）。
        "backup_status": _backup_status_payload(),
        # 排序品質計數器（2026-09-02）：讀 outcome_if_settled_today 落的狀態檔，
        # 不在 brief 生成時重打行情 API。None＝從未量測（檔不存在），現形於缺席。
        "outcome_aggregate": _outcome_aggregate_payload(),
        "items": ranked,
    }
    assert_safe_payload(brief)
    return brief


def _outcome_aggregate_payload(private_root: Path | None = None) -> dict[str, Any] | None:
    """讀 `scripts/outcome_if_settled_today.py` 落的等權聚合狀態檔（2026-09-02）。

    None＝檔不存在或壞掉——renderer 顯示「未量測」提示，不靜默。"""
    if private_root is None:
        private_root = Path(__file__).resolve().parent.parent / "library" / "private"
    path = private_root / "decision_lab" / "outcome_aggregate.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {
            "date": str(raw["date"]),
            "n": int(raw["n"]),
            "equal_weight_absolute": float(raw["equal_weight_absolute"]),
            "equal_weight_excess": (
                float(raw["equal_weight_excess"])
                if raw.get("equal_weight_excess") is not None
                else None
            ),
            "benchmark": str(raw.get("benchmark") or ""),
        }
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _backup_status_payload(
    now: datetime | None = None, private_root: Path | None = None
) -> dict[str, Any] | None:
    """讀 `scripts/backup_private.py` 寫的 status 檔，轉成首屏計數器 payload。

    回傳值三分（L12——別把不同語意壓進同一訊號）：
    - ``None``：這個 surface 沒有 private root，renderer 整行略過；
    - ``{"status": "never"}``：有 private root 但從未備份；
    - ``{"status": "invalid"}``：status 檔存在但無法解讀——視同沒有備份現形，
      不得因為讀不到就安靜消失（那正是備份「安靜停掉」的形狀）。
    """
    if private_root is None:
        private_root = Path(__file__).resolve().parent.parent / "library" / "private"
    if not private_root.is_dir():
        return None
    status_path = private_root / "backups" / "last_backup.json"
    if not status_path.is_file():
        return {"status": "never"}
    try:
        raw = json.loads(status_path.read_text(encoding="utf-8"))
        created = datetime.fromisoformat(
            str(raw["created_at"]).replace("Z", "+00:00")
        )
    except (OSError, ValueError, KeyError, TypeError):
        return {"status": "invalid"}
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    drive = raw.get("drive") if isinstance(raw.get("drive"), dict) else {}
    verification = (
        raw.get("restore_verification")
        if isinstance(raw.get("restore_verification"), dict)
        else {}
    )
    return {
        "status": "ok",
        "age_days": max(0, (current - created).days),
        "backup_id": str(raw.get("backup_id") or ""),
        "drive_status": str((drive or {}).get("status") or "unknown"),
        "restore_verified": bool((verification or {}).get("verified_at")),
    }


def ranking_annotations(
    store: DecisionStore, *, as_of: str
) -> dict[str, dict[str, str]]:
    """排序表每列要標的最弱軸與 disproof，以 `co:*` 為鍵。

    住在這裡而不是 `ranking_view`：它只需要 Decision Store，而 `ranking_view` 是純轉換層。
    排序本身來自 Engine A（需要 Neo4j），由更外層合起來——見
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


def _pct(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "未知"
    return f"{value * 100:+.1f}%"


def _render_ranking(ranking: Mapping[str, Any] | None) -> list[str]:
    """瓶頸排序區——首屏第一塊。

    兩份排序並列且各自帶用途說明：它們回答不同問題、不可互換，並排放才看得出差異
    （可行動第 1 名與純結構第 1 名通常不同）。
    """
    if not ranking:
        return [
            "# 瓶頸排序",
            "",
            "⚠ 本次未提供排序資料（未注入 ranking）——不是「沒有候選」。",
            "",
        ]
    lines = ["# 瓶頸排序", ""]

    def _row_line(row: Mapping[str, Any]) -> str:
        ticker = markdown_text(row.get("ticker") or row.get("company_id") or "?")
        anchor_note = "" if not row.get("no_demand_anchor") else " 🔴無需求錨點"
        return (
            f"| {row.get('rank')} | {ticker}{anchor_note} "
            f"| {markdown_text(row.get('bottleneck') or '')} "
            f"| {row.get('substitutability') or '—'}"
            f"{'｜sole_source' if row.get('sole_source') else ''} "
            f"| {markdown_text(row.get('evidence') or '')} "
            f"| {markdown_text(row.get('weakest_axis') or '—')} |"
        )

    _TABLE_HEAD = [
        "| 全域# | 標的 | 卡在哪 | 替代難度 | 證據 | 最弱軸 |",
        "|---|---|---|---|---|---|",
    ]

    for key, label_key, total_key in (
        ("actionable", "actionable_purpose", "actionable_total"),
        ("structural", "structural_purpose", "structural_total"),
    ):
        lines.append(f"## {markdown_text(ranking.get(label_key) or key)}")
        lines.append("")
        # 族群分段視圖（2026-09-02 使用者定案）：各段有自己的第一名，# 欄保留全域名次
        # 供跨段比較。舊 DTO 沒有 *_by_sector 時回退到全域混排表。
        sectors = ranking.get(f"{key}_by_sector")
        if sectors:
            for seg in sectors:
                entries = seg.get("entries") or []
                if not entries:
                    continue
                seg_total = seg.get("total")
                more = (
                    f"（族群共 {seg_total}，顯示前 {len(entries)}）"
                    if isinstance(seg_total, int) and seg_total > len(entries)
                    else ""
                )
                lines.append(f"### {markdown_text(seg.get('sector') or '?')}{more}")
                lines.append("")
                lines += _TABLE_HEAD
                lines += [_row_line(row) for row in entries]
                lines.append("")
            total = ranking.get(total_key)
            if isinstance(total, int):
                lines.append(f"（全域候選共 {total}；# 欄為全域名次）")
            lines.append("")
            continue
        rows = ranking.get(key) or []
        if not rows:
            lines += ["（無候選）", ""]
            continue
        lines += _TABLE_HEAD
        lines += [_row_line(row) for row in rows]
        total = ranking.get(total_key)
        if isinstance(total, int) and total > len(rows):
            lines.append("")
            lines.append(f"（共 {total} 個候選，此處顯示前 {len(rows)}）")
        lines.append("")
    note = ranking.get("judgment_note")
    if note:
        lines += [f"⚠ {markdown_text(note)}", ""]
    for caveat in ranking.get("caveats") or []:
        lines.append(f"- {markdown_text(caveat)}")
    lines.append("")
    return lines


def _render_ready_not_ranked(rows: list[Any] | None) -> list[str]:
    """C-1 常駐清單：研究完整但不在瓶頸排序內——只呈現，不催辦。

    `None`（ranking 未注入、無法比對）時整區不渲染：成因已由排序區的
    「未提供排序資料」警告現形，這裡再印一次是重複噪音。空 list 仍要渲染
    「（無）」——常駐計數器的意義就是讓 0 也自己出現（L14）。
    """
    if rows is None:
        return []
    lines = ["## 研究完整但不在瓶頸排序內（常駐；只呈現，不催辦）", ""]
    if not rows:
        lines += ["（無）", ""]
        return lines
    for row in rows:
        axis = markdown_text(row.get("weakest_axis") or "—")
        lines.append(
            f"- {markdown_text(row.get('company_id') or '?')}（最弱軸：{axis}）"
            "——它的邊不在 substitutability≥4 的候選內（未填值或低替代難度），"
            "研究已完整，等事件即可；若認為它該進排序，該補的是邊上的 substitutability"
        )
    lines.append("")
    return lines


def _render_nav_exposure(nav: Mapping[str, Any] | None) -> list[str]:
    """持股 NAV 比例——排序之後。純呈現，不判斷失衡。

    ⚠ `None`（未注入）不得讓整區靜默消失。先前 `return []` 會讓「呼叫端沒給」與
    「這個人沒有持股」在畫面上完全同形——而使用者看這一區就是為了看曝險集中在哪，
    整區不見時他不會知道自己少看了什麼。排序區對 `None` 早就明說「未提供」，
    這裡沿用同一個處置。
    """
    if nav is None:
        return [
            "# 持股 NAV 比例",
            "",
            "⚠ 本次未提供持股資料（未注入 nav_exposure）——不是「沒有持股」。",
            "",
        ]
    if nav.get("status") != "available":
        failure = nav.get("failure")
        detail = f"（{markdown_text(failure)}）" if failure else ""
        return [
            "# 持股 NAV 比例",
            "",
            f"⚠ 持股讀不到{detail}——這不是「零曝險」。",
            "",
        ]
    lines = ["# 持股 NAV 比例", ""]
    lines.append("| 標的 | bucket | 佔 NAV |")
    lines.append("|---|---|---|")
    for position in nav.get("positions") or []:
        lines.append(
            f"| {markdown_text(position.get('ticker') or '?')} "
            f"| {markdown_text(position.get('bucket') or '')} "
            f"| {_pct(position.get('nav_pct'))} |"
        )
    lines.append("")
    buckets = nav.get("buckets") or {}
    if buckets:
        parts = "、".join(
            f"{markdown_text(name)} {_pct(share)}"
            for name, share in sorted(buckets.items(), key=lambda kv: -kv[1])
        )
        lines += [f"- bucket 分布：{parts}", ""]
    groups = nav.get("groups") or {}
    if groups:
        parts = "、".join(
            f"{markdown_text(name)} {_pct(share)}"
            for name, share in sorted(groups.items(), key=lambda kv: -kv[1])
        )
        lines += [f"- 相關性分組：{parts}", ""]
    return lines


def render_today_markdown(brief: Mapping[str, Any]) -> str:
    """由同一 public DTO 產生 Markdown；不接觸 private payload。

    每個 item 帶穩定編號 [N] 供對話式批次核准引用（plan R5）；顯示自追蹤變化%
    與 evidence_delta，不使用顏色維度（plan R15）。
    """

    assert_safe_payload(brief)
    blockers = "、".join(markdown_text(item) for item in brief.get("blockers") or []) or "無"
    # 首屏是瓶頸排序——系統的終點是「哪些標的值得看」，不是「今天要不要動作」。
    lines = _render_ranking(brief.get("ranking"))
    lines += _render_ready_not_ranked(brief.get("ready_not_ranked"))
    lines += _render_nav_exposure(brief.get("nav_exposure"))
    lines += [
        f"# 今天需要動作嗎？{'是' if brief['action_needed'] else '否'}",
        "",
        f"- 注意力：{'需要複查' if brief['attention'] == 'REVIEW' else '監控中'}",
        f"- 原因：{markdown_text(brief['reason'])}",
        f"- Blockers：{blockers}",
        f"- 下一個 review：{markdown_text(brief.get('next_review_at') or '尚未排定')}",
    ]
    # Alpha live 部位事件擺在首屏 counters 之前：它講的是**已經投出去的錢正在
    # 發生什麼**，優先於研究進展。exception-first——沒觸發就完全不出現，不佔版面。
    for event in brief.get("alpha_position_events") or []:
        ticker = markdown_text(event.get("ticker") or "未知標的")
        session = markdown_text(event.get("session_date") or "最近交易日")
        day = _pct(event.get("return_1d"))
        since = _pct(event.get("return_since_entry"))
        raw_weight = event.get("position_weight")
        weight = (
            f"{raw_weight * 100:.2f}%"
            if isinstance(raw_weight, (int, float)) and not isinstance(raw_weight, bool)
            else "未知"
        )
        lines.append(
            f"- 🔴 持倉事件：{ticker} 於 {session} 單日 {day}"
            f"（距進場 {since}，部位約 {weight} NAV）"
            "　→ 請對此標的做一次 WebSearch 找可能原因，結果未經查證、不建 lead"
        )
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
        legacy_eligible = int(counters.get("legacy_eligible_cohorts") or 0)
        line = (
            f"- 研究進展：上線標的 {eligible}/{total_cohorts} 檔"
            f"｜可量測 {measurable}/{anchored} 檔"
        )
        # 舊判準的殘量分開講，不加進上面那個數字——合起來會讓「換判準」看起來像「有進展」。
        if legacy_eligible:
            line += f"（另有 {legacy_eligible} 檔仍為 U7 前判準，reassess 後才會重算）"
        if eligible == 0 and total_cohorts and not legacy_eligible:
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
    # 公司對齊常駐計數器（2026-09-02）：洩漏（圖∖registry）應恆 0——非 0 逐一列出
    # 並附修法；registry∖圖 只計數現形。None＝surface 未注入，整行略過（≠對齊為 0）。
    alignment = brief.get("identity_alignment")
    if alignment:
        leaked = list(alignment.get("graph_not_in_registry") or ())
        unresearched = int(alignment.get("registry_not_in_graph_count") or 0)
        if leaked:
            names = "、".join(markdown_text(x) for x in leaked[:5])
            more = f" 等 {len(leaked)} 個" if len(leaked) > 5 else ""
            lines.append(
                f"- 🔴 公司對齊：圖中 {names}{more} 不在 registry——join-key 契約破口，"
                "補 `config/company_identity.json` 條目（private 也要 null 條目）"
            )
        else:
            lines.append(
                f"- 公司對齊：圖∖registry 0（✓）｜registry 已登記未入圖 {unresearched} 家"
                f"（圖 {alignment.get('graph_companies')}／registry "
                f"{alignment.get('registry_companies')}）"
            )
    # 排序品質計數器（2026-09-02）：等權聚合是排序準不準的裁判數字（L14 常駐）。
    agg = brief.get("outcome_aggregate")
    if agg:
        ex = agg.get("equal_weight_excess")
        ex_txt = (
            f"｜超額({markdown_text(agg.get('benchmark') or '?')}) {ex:+.1%}"
            if isinstance(ex, (int, float))
            else ""
        )
        lines.append(
            f"- 排序品質：推薦籃等權 {agg.get('n')} 檔 絕對 "
            f"{agg.get('equal_weight_absolute'):+.1%}{ex_txt}"
            f"（量測日 {markdown_text(agg.get('date') or '?')}；粗聚合非回測，"
            "前/後段對照待快照累積）"
        )
    elif "outcome_aggregate" in brief:
        lines.append(
            "- 排序品質：尚無量測——跑 `scripts/outcome_if_settled_today.py` 產生"
        )
    # 備份計數器：與 capital_expression 各自獨立呈現——surface 沒給就整行略過，
    # 「從未備份」與「狀態檔壞掉」都必須現形，不得靜默（L12／L14）。
    backup = brief.get("backup_status")
    if backup:
        backup_state = str(backup.get("status") or "")
        if backup_state == "never":
            lines.append(
                "- 🔴 最後一次備份：從未備份——跑 `python scripts/backup_private.py run`"
            )
        elif backup_state == "invalid":
            lines.append(
                "- 🔴 最後一次備份：狀態檔無法解讀（library/private/backups/"
                "last_backup.json），視同沒有備份處理"
            )
        else:
            age = int(backup.get("age_days") or 0)
            drive_status = str(backup.get("drive_status") or "unknown")
            notes = [
                "Drive ✓" if drive_status == "uploaded" else f"Drive 🔴 {markdown_text(drive_status)}",
                "restore 已驗證" if backup.get("restore_verified") else "restore 🔴 未驗證",
            ]
            marker = "🔴 " if age > 7 or drive_status != "uploaded" else ""
            lines.append(
                f"- {marker}最後一次備份：{age} 天前（{'，'.join(notes)}）"
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
            attention = "需要複查" if item.get("attention") == "REVIEW" else "監控中"
            perf = _pct(item.get("performance_since_tracked"))
            since_decision = _pct(item.get("performance_since_decision"))
            delta = markdown_text(item.get("evidence_delta") or "none")
            lines.append(
                f"- [{idx}] {attention} — {company}｜自追蹤 {perf}"
                f"（決策後 {since_decision}）｜證據 {delta}"
            )
            resp = markdown_text(item.get("user_response_needed") or "")
            if resp:
                lines.append(f"      → {resp}")
            # variant perception（2026-09-02）：REVIEW 項第一眼要看到「市場隱含 vs
            # 本 thesis」；沒寫就顯示（未寫）現形——那是待辦，不是可以省略的欄。
            vp = item.get("variant_perception")
            if "variant_perception" in item:
                if vp:
                    lines.append(f"      → 差異點：{markdown_text(str(vp))}")
                elif item.get("attention") == "REVIEW":
                    lines.append(
                        "      → 差異點：（未寫 variant perception——"
                        f"`decision_lab variant-perception {item.get('cohort_id')} --text …`）"
                    )
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
