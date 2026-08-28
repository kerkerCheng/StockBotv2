"""五軸 Confidence Envelope：算出最弱軸與研究完整度。**不產生任何額度。**

2026-08-28（U7）之前，本模組同時做兩件事：驗證五軸證據、以及把最弱軸的等級換算成
`axis_ceiling` → `paper_target`／`live_supported_range`。後者已整組移除——系統終點是
`query/bottleneck.py` 的瓶頸度排序，不是資本額度。

⚠ 模組名、`calculate_probe_limits` 與 `ProbeSizingResult` 刻意保留舊名：decision payload
的 `"sizing"` key 必須留給既有 128 筆歷史 decision（Decision Store 是 append-only 的
private authority，依 L10 不做破壞性 migration）。只改一半的名字會讓同一件事有兩套詞彙，
比一個略舊的名字更難讀。
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from identity.registry import IdentityRegistry, get_registry
from thesis.investment_policy import PolicyError, load_policy, validate_policy

from .beta_policy import load_beta_policy
from .blocker_severity import fatal_blockers
from .models import ContextBundle, CoverageResult, ProbeSizingResult
from .portfolio_risk import build_portfolio_components


AXES = (
    "source_reliability",
    "technical_causal_link",
    "commercial_maturity",
    "financial_resilience",
    "valuation_payoff",
)
LEVELS = ("unknown", "bounded_hypothesis", "corroborated")

# 每一軸對應的「該補什麼」。最弱軸是排序的瓶頸，也是提高排序的唯一路徑，所以這句話
# 就是 pq2 項目的內容——使用者要看到的是「補 COHR 的 counter-path」，不是
# 「REVIEW — co:coherent」那種沒有成因的文字。
#
# ⚠ 與 AXES 綁在一起放，是為了讓新增一軸時被強迫決定它的研究動作（同
# schema/vocab.json 的 counter_path_relation 模式）。`tests/test_weakest_axis.py`
# 斷言兩者的鍵完全一致。
AXIS_RESEARCH_PROMPT: dict[str, str] = {
    "source_reliability": "補獨立來源：找客戶端或第三方文件，把供應商自報升級成外部印證",
    "technical_causal_link": "補 counter-path：什麼會讓這條因果鏈斷掉（第二供應源、客戶自製、技術替代）",
    "commercial_maturity": "補客戶端商業承諾：訂單、產能協議或預付款等付錢方向的證據",
    "financial_resilience": "補 Engine C 財務觀測：客戶集中度、backlog、runway 等人工欄位",
    "valuation_payoff": "補估值錨點：市值、分析師覆蓋與隱含假設，回答股價已經定價了什麼",
}


def weakest_axis_of(axes: Mapping[str, Mapping[str, Any]]) -> str:
    """回傳證據最弱的那一軸。

    以 `effective_level` 次序為主鍵，同階時退到 `AXES` 的宣告次序
    （`source_reliability` 優先）。

    ⚠ 不能改用宣告的 `level`：`_validate_assessment` 在 `fatal_axis_blocker`
    （例如 evidence_missing）時把該軸判為失效卻**不動 level**，所以一個宣告
    corroborated 但引用不成立的軸，raw level 仍是 corroborated。用 raw level 排序
    會漏掉它，`test_probe_sizing.py::...[missing_ref]` 立刻紅。`effective_level`
    就是把那個隱含資訊顯性化的欄位。
    """
    def rank(axis: str) -> tuple[int, int]:
        level = str(axes[axis].get("effective_level") or axes[axis]["level"])
        # 未登記的等級視為最弱：寧可多提醒一次，也不要讓拼錯的值看起來佐證完整。
        order = LEVELS.index(level) if level in LEVELS else -1
        return (order, AXES.index(axis))

    return min(AXES, key=rank)
AXIS_REFERENCE_AUTHORITIES = {
    "source_reliability": frozenset(
        {"graph_source_assertion", "source_trace"}
    ),
    "technical_causal_link": frozenset(
        {"graph_entity", "graph_causal", "graph_source_assertion"}
    ),
    # ⚠ 這裡刻意**不含** `graph_commercial`。該 authority 對應 evidence payload 的
    # `commercial_assertions`，而全 repo 只有消費端（context._build_reference_index）、
    # 沒有任何生產端——engine_d_runtime 的 _read_graph 產出 entities／edges／claims／
    # assertions／sources／causal_paths／counter_paths，就是不產 commercial_assertions。
    # 宣告它會讓這一軸看起來有三條路可走，實際只有兩條，而兩條都要求 Engine C 的
    # `manual_reviewed` 觀測（manual_required 時 source 為 None，不進 reference index）。
    # 2026-08-08 實測：有那兩筆觀測的 cohort 全部 bounded_hypothesis、有部位；
    # 沒有的全部 unknown、部位 0——相關性 100%。閘門的真實高度必須等於宣告的高度。
    # 若日後真的讓 graph 產出 commercial_assertions，再把它加回來。
    "commercial_maturity": frozenset({"engine_c_backlog", "engine_c_customer"}),
    "financial_resilience": frozenset(
        {"engine_c_financial", "engine_c_manual"}
    ),
    "valuation_payoff": frozenset(
        {"engine_c_valuation", "market", "fx"}
    ),
}


class AssessmentError(ValueError):
    """Confidence assessment 或其凍結 context 不可安全計算。"""


def _finite(value: Any, *, non_negative: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or (non_negative and parsed < 0):
        return None
    return parsed


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise AssessmentError(f"{field} must be a list")
    result = tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    if len(result) != len(value):
        raise AssessmentError(f"{field} must contain non-empty strings")
    return result


def _resolve_reference(
    reference: str, reference_index: Mapping[str, Any]
) -> tuple[str, str] | None:
    """把 evidence_ref 解析成 reference index 的 key；回傳 (key, 解析方式)。

    2026-08-13：先前只做 exact 比對，於是 ``yfinance://history`` 對不上 index 裡的
    ``yfinance://history/AAOI``——**一個少了 ticker 後綴的引用字串，讓整筆決策的資本
    歸零**（實測 22 次，佔「做了研究卻有軸 unknown」的三分之二）。內容是對的，
    來源真的存在，罰的卻是格式。正解是遇到就解析，不是打折。

    只做**無歧義**解析，不猜：exact 命中優先；否則該 ref 必須恰好是 index 中
    **唯一一個** key 的前綴。兩個以上候選就不解析——寧可報 mismatch，也不挑一個。

    ⚠ 解析只認身分，不看 authority。挑 key 時若偏好「該軸接受的 authority」，
    等於讓引用去尋找能通過的權威，那正是這道檢查要防的 authority laundering
    （L8／L11）。因此順序固定為：先解析身分 → 再查 authority，兩者不得互相影響。
    """
    if reference in reference_index:
        return reference, "exact"
    trimmed = reference.rstrip("/")
    if trimmed != reference and trimmed in reference_index:
        return trimmed, "trailing_slash"
    candidates = [key for key in reference_index if key.startswith(reference)]
    if len(candidates) == 1:
        return candidates[0], "unique_prefix"
    return None


def describe_axis_references(
    reference_index: Mapping[str, Any],
) -> dict[str, tuple[dict[str, Any], ...]]:
    """每個軸有哪些引用真的支撐得了它——寫 assessment 前該先看的東西。

    2026-08-14 實測：LITE 的 `commercial_maturity` 與 `financial_resilience` 雙雙
    歸零，而 index 裡明明有合格的 key。引用寫的是**同一份 10-Q、同一個 SEC
    accession**，字面卻和 index 的 key 差了一段描述（一邊寫 `filed 2026-05-06`、
    一邊寫 `Note 17, …, https://…`），分歧在字串中段，三種解析都不命中。

    根源不是 gate 太嚴，是寫 assessment 的人看不到 index 有哪些 key 可用、只能猜。
    攤開可用 key 讓身分在源頭就確定，比事後放寬比對安全：解析規則不動，也就沒有
    「引用去尋找能通過的權威」的空間（L15）。
    """

    options: dict[str, tuple[dict[str, Any], ...]] = {}
    for axis, wanted in AXIS_REFERENCE_AUTHORITIES.items():
        rows: list[dict[str, Any]] = []
        for key, entry in reference_index.items():
            authorities = tuple(sorted(set((entry or {}).get("authorities") or ())))
            if set(authorities) & wanted:
                rows.append({"reference": key, "authorities": authorities})
        options[axis] = tuple(sorted(rows, key=lambda row: row["reference"]))
    return options


def diagnose_assessment_references(
    assessment: Mapping[str, Any],
    reference_index: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """逐軸說明每個 evidence_ref 被判成什麼，以及該軸會不會因此歸零。

    刻意只回報、不修改：解析與權限規則仍然只有 `_validate_assessment` 一份，
    這裡重用同一支 `_resolve_reference`，避免診斷和實際判準各講一套。
    """

    report: dict[str, dict[str, Any]] = {}
    for axis in AXES:
        raw = assessment.get(axis)
        if not isinstance(raw, Mapping):
            continue
        wanted = AXIS_REFERENCE_AUTHORITIES[axis]
        accepted: list[str] = []
        context_only: list[dict[str, Any]] = []
        for reference in raw.get("evidence_refs") or []:
            if not isinstance(reference, str) or not reference.strip():
                continue
            reference = reference.strip()
            resolved = _resolve_reference(reference, reference_index)
            if resolved is None:
                context_only.append({"reference": reference, "why": "unresolved"})
                continue
            key, how = resolved
            entry = reference_index.get(key)
            authorities = tuple(sorted(set((entry or {}).get("authorities") or ())))
            if set(authorities) & wanted:
                accepted.append(reference)
            else:
                context_only.append({
                    "reference": reference,
                    "why": "authority_mismatch",
                    "resolved_to": key,
                    "resolved_how": how,
                    "authorities": authorities,
                })
        report[axis] = {
            "declared_level": raw.get("level"),
            "accepted_refs": tuple(accepted),
            "rejected_refs": tuple(context_only),
            "accepts_authorities": tuple(sorted(wanted)),
            # 這一軸的實質等級會不會被打回 unknown（宣告的等級不算數）。
            "would_downgrade_to_unknown": not accepted and raw.get("level") != "unknown",
        }
    return report


def _validate_assessment(
    assessment: Mapping[str, Any],
    reference_index: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], tuple[str, ...]]:
    if not isinstance(assessment, Mapping) or set(assessment) != set(AXES):
        raise AssessmentError("assessment must contain exactly the five confidence axes")
    normalized: dict[str, dict[str, Any]] = {}
    blockers: list[str] = []
    for axis in AXES:
        raw = assessment[axis]
        if not isinstance(raw, Mapping):
            raise AssessmentError(f"{axis} must be an object")
        missing_keys = {"level", "evidence_refs", "reason", "missing_data"} - set(raw)
        if missing_keys:
            raise AssessmentError(f"{axis} missing fields: {', '.join(sorted(missing_keys))}")
        level = raw["level"]
        if level not in LEVELS:
            raise AssessmentError(f"{axis}.level is invalid")
        refs = _string_list(raw["evidence_refs"], f"{axis}.evidence_refs")
        missing_data = _string_list(raw["missing_data"], f"{axis}.missing_data")
        reason = raw["reason"]
        if not isinstance(reason, str) or not reason.strip():
            blockers.append(f"{axis}_reason_missing")
        resolutions: dict[str, str] = {}
        if level == "unknown":
            blockers.append(f"{axis}_unknown")
        elif not refs:
            blockers.append(f"{axis}_evidence_missing")
        else:
            # 判準是「**至少有一個**引用落在該軸接受的 authority」，不是「每一個都要」。
            # 先前是 any(失敗) → 整軸歸零，於是 META 的 technical_causal_link 有
            # co:meta 與 meta_vistara_isca_2026 兩個合格引用，只因為多附了一個
            # prod:vistara 就被打成 unknown；AXTI 的 financial_resilience 有合格的
            # yfinance.info，卻因為多附兩份 8-K 脈絡而歸零。
            # 那不是 authority laundering——laundering 是「**沒有**合格來源卻假裝有」，
            # 而那個情況（零個合格引用）仍然歸零。多附的脈絡引用改列 context_only，
            # 必須在輸出現形供人稽核，但不再有歸零的權力。
            accepted: list[str] = []
            context_only: list[str] = []
            for reference in refs:
                resolved = _resolve_reference(reference, reference_index)
                if resolved is None:
                    context_only.append(reference)
                    continue
                key, how = resolved
                if how != "exact":
                    # 解析過程必須留痕：會改變輸出的輸入要出現在輸出自己的證據欄位。
                    resolutions[reference] = f"{key} ({how})"
                entry = reference_index.get(key)
                if isinstance(entry, Mapping) and (
                    set(entry.get("authorities") or ()) & AXIS_REFERENCE_AUTHORITIES[axis]
                ):
                    accepted.append(reference)
                else:
                    context_only.append(reference)
            if not accepted:
                blockers.append(f"assessment_context_mismatch:{axis}")
        if level == "corroborated" and missing_data:
            blockers.append(f"{axis}_corroboration_incomplete")
        context_mismatch = f"assessment_context_mismatch:{axis}" in blockers
        # 單調性：宣告較高信心不得被判得比宣告較低信心更弱。
        # 先前 `corroborated + missing_data` 直接打成失效，比誠實降級成
        # bounded_hypothesis **更差**——於是評估者學會迴避那個組合（實測 72 筆出現
        # 0 次），規則在暗中形塑了評估行為。現在 missing_data 只把 corroborated
        # 壓回下一階，不打成 unknown。
        fatal_axis_blocker = any(
            blocker.startswith(f"{axis}_") and not blocker.endswith("_corroboration_incomplete")
            for blocker in blockers
        )
        # 實質等級：宣告的 level 打上「證據引用是否真的成立」之後的結果。
        # ⚠ 這不等於下面那個 `level` 欄位——後者只在 context_mismatch 時降為 unknown，
        # 而 fatal_axis_blocker（例如 evidence_missing）會讓該軸失效卻**不動 level**。
        # 最弱軸的排序只看 effective_level（見 weakest_axis_of）。
        if context_mismatch or fatal_axis_blocker:
            effective_level = "unknown"
        elif f"{axis}_corroboration_incomplete" in blockers:
            effective_level = LEVELS[max(0, LEVELS.index(level) - 1)]
        else:
            effective_level = level
        normalized[axis] = {
            "level": "unknown" if context_mismatch else level,
            "effective_level": effective_level,
            "evidence_refs": refs,
            "reason": reason.strip() if isinstance(reason, str) else "",
            "missing_data": missing_data,
        }
        if resolutions:
            normalized[axis]["reference_resolutions"] = resolutions
        if level != "unknown" and refs:
            # 稽核用：哪些引用真的支撐了這一軸、哪些只是脈絡。不得只留下結論。
            normalized[axis]["accepted_refs"] = tuple(accepted)
            if context_only:
                normalized[axis]["context_only_refs"] = tuple(context_only)
    return normalized, tuple(sorted(set(blockers)))


def _live_portfolio(
    payload: Mapping[str, Any],
    *,
    registry: IdentityRegistry,
    focus_company_id: str,
    execution_symbol: str,
    research_ticker: str,
) -> tuple[float, list[str], float]:
    holdings = payload["holdings"]
    nav = _finite(holdings.get("nav_base"), non_negative=True)
    if nav is None or nav <= 0:
        return 0.0, ["live_nav_missing"], 0.0
    current_value = 0.0
    blockers: list[str] = []
    for row in holdings.get("rows") or []:
        # 現金已計入 NAV，且沒有 company／factor 曝險；不跳過的話會被誤報成
        # 對應不到公司的持股而擋住 live sizing。
        if row.get("is_cash"):
            continue
        ticker = str(row.get("ticker") or "").upper()
        company_id = row.get("company_id")
        if company_id is None and ticker in {execution_symbol.upper(), research_ticker.upper()}:
            company_id = focus_company_id
        if company_id is None:
            company_id = registry.company_id_for_ticker(ticker)
        value = _finite(row.get("market_value_base"), non_negative=True)
        if value is None:
            blockers.append(f"holdings_market_value_missing:{ticker}")
            continue
        if company_id == focus_company_id:
            current_value += value
    return nav, blockers, current_value / nav


def calculate_probe_limits(
    bundle: ContextBundle,
    coverage: CoverageResult,
    assessment: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
    registry: IdentityRegistry | None = None,
    paper_exposure_override: Mapping[str, Any] | None = None,
) -> ProbeSizingResult:
    """Pure calculation：驗證五軸、找出最弱軸、彙整 blocker。不保存 decision。

    2026-08-28 起不再輸出 `axis_ceiling`／`paper_target`／`live_supported_range`／
    `constraint_trace`。唯一留下的兩個數字（`live_current_position`、
    `single_position_nav_cap`）是使用者手動記錄 live 選擇時的既有部位與政策參考線，
    不是系統建議的尺寸。
    """

    if coverage.cohort_id != bundle.cohort_id or coverage.context_digest != bundle.digest:
        raise AssessmentError("coverage and context bundle do not match")
    current_policy = validate_policy(policy) if policy is not None else load_policy()
    probe = current_policy.get("probe_lane")
    if not isinstance(probe, Mapping):
        raise PolicyError("validated policy has no probe_lane")
    payload = bundle.payload
    if payload.get("policy_version") != current_policy["policy_version"]:
        raise AssessmentError("context policy version does not match calculator policy")
    registry = registry or get_registry()
    reference_index = payload.get("reference_index")
    if not isinstance(reference_index, Mapping):
        reference_index = {}
    axes, assessment_blockers = _validate_assessment(assessment, reference_index)
    weakest_axis = weakest_axis_of(axes)
    identity = payload["identity"]
    company_id = str(identity.get("company_id") or "")
    execution_symbol = str(identity.get("execution_symbol") or "")
    research_ticker = str(identity.get("research_ticker") or "")

    # `paper_blockers` 與 `live_blockers` 保留原名與原 lane 分類（`blocker_severity`
    # 與 `config/decision_blockers.json` 都以它們為鍵），但語意已與資本無關：前者是
    # **研究資料**是否齊全（行情／FX／財務），後者是**執行面**是否齊全（持股／
    # execution 行情）。兩者都不再換算成任何額度。
    paper = paper_exposure_override or payload["paper_exposure"]
    paper_blockers = list(coverage.paper_blockers)
    if identity.get("status") != "resolved" or not company_id:
        paper_blockers.append("identity_unresolved")
    if not coverage.paper_context_ready or paper.get("status") != "available":
        paper_blockers.extend(paper.get("blockers") or ["paper_context_not_ready"])

    live_blockers = list(coverage.live_blockers)
    if identity.get("status") != "resolved" or not company_id:
        live_blockers.append("identity_unresolved")
    if not coverage.live_context_ready:
        live_blockers.append("live_context_not_ready")
    holdings = payload["holdings"]
    if holdings.get("status") not in {"confirmed", "confirmed_empty"}:
        live_blockers.extend(holdings.get("blockers") or ["holdings_not_confirmed"])
    live_nav, portfolio_blockers, live_current = _live_portfolio(
        payload,
        registry=registry,
        focus_company_id=company_id,
        execution_symbol=execution_symbol,
        research_ticker=research_ticker,
    )
    live_blockers.extend(portfolio_blockers)
    single_position_nav_cap = float(current_policy["single_position_nav_cap"])
    if live_current >= single_position_nav_cap:
        live_blockers.append("single_position_nav_cap_reached")
    try:
        if live_nav <= 0:
            raise ValueError("live nav unavailable")
        beta_policy = load_beta_policy()
        leverage = build_portfolio_components(
            holdings.get("rows") or [],
            beta_policy,
            nav_base=holdings.get("nav_base"),
            base_currency=holdings.get("base_currency"),
            strict_reconciliation=False,
            registry=registry,
        )
        nominal_weight = float(leverage["leveraged_nominal_base"]) / live_nav
        effective_weight = float(leverage["leveraged_effective_base"]) / live_nav
        if nominal_weight >= float(beta_policy["risk"]["leveraged_nominal_cap"]):
            live_blockers.append("etf_leverage_nominal_cap_reached")
        if effective_weight >= float(beta_policy["risk"]["leveraged_effective_cap"]):
            live_blockers.append("etf_leverage_effective_cap_reached")
    except (KeyError, OSError, TypeError, ValueError):
        live_blockers.append("portfolio_leverage_unavailable")
    execution_market = payload.get("execution_market") or {}
    execution_fx = payload.get("execution_fx") or {}
    if execution_market.get("status") != "available":
        live_blockers.extend(execution_market.get("blockers") or ["execution_market_missing"])
    if execution_fx.get("status") != "available":
        live_blockers.extend(execution_fx.get("blockers") or ["execution_fx_missing"])

    # 研究完整度三態。判準與舊 `paper_status` 的 ELIGIBLE 一一對應，只是不再經過
    # 資本換算：舊的 `paper_max > 0` 需要 axis_ceiling > 0（⟺ 最弱軸的 effective_level
    # 不是 unknown）且 coverage 無致命 blocker，兩個條件原樣保留；被拿掉的
    # `probe_book_remaining` 是純資本額度。
    #
    # ⚠ **已知的名實落差，刻意留著等量測。** 第一條是 `if paper_blockers`，不分嚴重度，
    # 而 `coverage.apply_execution_intent` 會把 diagnostic 級的
    # `execution_intent_research_only`／`_paper_only` 塞進 `paper_blockers`——於是任何
    # `research` intent 的評估恆為 `DATA_NEEDED`，與研究本身完整與否無關。
    # 這是 U7 之前 `paper_status` 就有的行為，改名之後才變刺眼。
    # 正確的判準應該是 `fatal_blockers(paper_blockers, lane="paper")`，但改它會直接抬高
    # daily brief 的「上線標的 N/M」計數器——那是**放閘**，依 L14 必須先量測再動，
    # 不能夾帶在一次移除重構裡。要動就另案，並先記下改動前後的筆數差。
    if paper_blockers:
        research_status = "DATA_NEEDED"
    elif (
        fatal_blockers(coverage.blockers)
        or str(axes[weakest_axis]["effective_level"]) == "unknown"
    ):
        research_status = "INCOMPLETE"
    else:
        research_status = "READY"

    return ProbeSizingResult(
        cohort_id=bundle.cohort_id,
        context_digest=bundle.digest,
        policy_version=current_policy["policy_version"],
        rubric_version=probe["rubric_version"],
        calculator_version=probe["calculator_version"],
        identity_registry_version=registry.version,
        weakest_axis=weakest_axis,
        axis_results=axes,
        assessment_blockers=assessment_blockers,
        research_status=research_status,
        paper_blockers=tuple(sorted(set(paper_blockers))),
        live_blockers=tuple(sorted(set(live_blockers))),
        live_current_position=live_current,
        single_position_nav_cap=single_position_nav_cap,
    )
