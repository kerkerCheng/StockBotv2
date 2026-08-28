from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.models import CoverageResult
from decision_lab.sizing import AXES, LEVELS, AssessmentError, calculate_probe_limits
from decision_lab.store import DecisionStore
from storage.relational import initialize_private_root
from tests.test_decision_context import NOW, complete_inputs
from thesis.investment_policy import load_policy


def _store(tmp_path: Path) -> DecisionStore:
    repo = tmp_path / "repo"
    repo.mkdir()
    private_root = repo / "library" / "private"
    initialize_private_root(private_root, repo_root=repo)
    return DecisionStore.open(
        private_root / "decision_lab" / "decision_lab.db",
        private_root=private_root,
        repo_root=repo,
    )


def _assessment(*, commercial: str = "corroborated") -> dict:
    levels = {axis: "corroborated" for axis in AXES}
    levels["commercial_maturity"] = commercial
    refs = {
        "source_reliability": ["src:gf"],
        "technical_causal_link": ["edge:cw-laser"],
        "commercial_maturity": ["fixture://filing"],
        "financial_resilience": ["fixture://filing"],
        "valuation_payoff": ["fixture://market"],
    }
    return {
        axis: {
            "level": level,
            "evidence_refs": refs[axis],
            "reason": f"{axis} fixture assessment",
            "missing_data": [] if level == "corroborated" else ["named production order"],
        }
        for axis, level in levels.items()
    }


def _bundle(
    store: DecisionStore,
    *,
    inputs: dict | None = None,
    execution_market: dict | None = None,
    execution_fx: dict | None = None,
):
    payload = deepcopy(inputs or complete_inputs())
    cohort_id = store.ensure_cohort(
        dedupe_key="probe-sizing",
        company_id="co:sivers_semiconductors",
        research_ticker="SIVE.ST",
    ).cohort_id
    store.record_holdings_confirmation(
        holdings_snapshot_digest(
            payload["holdings"]["rows"],
            nav_base=payload["holdings"].get("nav_base"),
            base_currency=payload["holdings"].get("base_currency"),
        ),
        confirmed_at="2026-07-21T09:00:00+00:00",
    )
    return build_context_bundle(
        store,
        cohort_id=cohort_id,
        evaluation_at=NOW,
        policy_version=load_policy()["policy_version"],
        execution_market=execution_market,
        execution_fx=execution_fx,
        **payload,
    )


def _coverage(bundle, *, paper=True, live=True) -> CoverageResult:
    return CoverageResult(
        assessment_id="assessment:fixture",
        cohort_id=bundle.cohort_id,
        context_digest=bundle.digest,
        status="analyzable",
        blockers=(),
        paper_blockers=() if paper else ("market_stale",),
        live_blockers=() if live else ("holdings_unconfirmed",),
        paper_context_ready=paper,
        live_context_ready=live,
        work_order_id=None,
    )


def test_multiple_positive_events_do_not_add_and_weakest_axis_governs(
    tmp_path: Path,
) -> None:
    """多附幾個正面引用不會讓那一軸變強，整筆評估仍由最弱軸代表。

    U7 之前這個契約是用額度表達的（最弱軸 → `axis_ceiling` → `paper_target`）；
    額度移除後判準沒變，只是改由 `weakest_axis` 與 `effective_level` 直接表達。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment(commercial="bounded_hypothesis")
        assessment["technical_causal_link"]["evidence_refs"] = [
            "co:sivers_semiconductors",
            "edge:cw-laser",
            "edge:alternative",
        ]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        assert result.weakest_axis == "commercial_maturity"
        assert result.axis_results["commercial_maturity"]["effective_level"] == (
            "bounded_hypothesis"
        )
        # 三個引用沒有讓這一軸升到 corroborated 之上——等級不會累加。
        assert result.axis_results["technical_causal_link"]["effective_level"] == (
            "corroborated"
        )
        # 額度欄位已隨資本表達層移除，不得悄悄長回來。
        assert "ceiling" not in result.axis_results["technical_causal_link"]
    finally:
        store.close()


@pytest.mark.parametrize("failure", ["unknown", "missing_ref"])
def test_unknown_or_unreferenced_required_axis_fails_closed(
    tmp_path: Path, failure: str
) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment()
        if failure == "unknown":
            assessment["financial_resilience"]["level"] = "unknown"
            assessment["financial_resilience"]["evidence_refs"] = []
            assessment["financial_resilience"]["missing_data"] = ["runway source"]
        else:
            assessment["valuation_payoff"]["evidence_refs"] = []

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        # 舊契約是「額度歸零＋action=SHADOW_ONLY」；U7 之後同一件事由研究完整度
        # 表達——最弱軸實質等級 unknown ⟹ 研究還沒到 READY。
        assert result.axis_results[result.weakest_axis]["effective_level"] == "unknown"
        assert result.research_status == "INCOMPLETE"
        assert result.assessment_blockers
    finally:
        store.close()


@pytest.mark.parametrize(
    "axis,invalid_ref",
    [
        ("source_reliability", "fixture://not-in-this-context"),
        ("valuation_payoff", "edge:cw-laser"),
    ],
)
def test_cross_context_or_wrong_authority_ref_fails_closed(
    tmp_path: Path, axis: str, invalid_ref: str
) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment()
        assessment[axis]["evidence_refs"] = [invalid_ref]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        assert result.axis_results[axis]["level"] == "unknown"
        assert f"assessment_context_mismatch:{axis}" in result.assessment_blockers
        assert result.research_status == "INCOMPLETE"
    finally:
        store.close()


def test_fatal_coverage_gap_cannot_be_overridden_by_high_axis_levels(
    tmp_path: Path,
) -> None:
    """五軸再漂亮，也不能蓋過「連在講哪家公司都不確定」。

    原版只把 status 設成 coverage_pending 而讓 blockers 留空，但真實流程裡
    status 是由 blockers 推導出來的，這個組合不會出現。改用真實的致命
    blocker，守的契約不變。

    U7 之後這個契約由 `research_status` 表達：致命 coverage blocker 讓研究狀態
    退回 INCOMPLETE。原本斷言的 `constraint_trace` 的 `coverage_gate` 項目隨
    `constraint_trace` 一起移除——那是額度的推導軌跡，不再存在。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        pending = _coverage(bundle)
        pending = CoverageResult(
            **{
                **pending.__dict__,
                "status": "coverage_pending",
                "blockers": ("identity_unresolved",),
            }
        )

        result = calculate_probe_limits(bundle, pending, _assessment())

        # 五軸全部 corroborated，仍不得判成 READY。
        assert all(
            axis["effective_level"] == "corroborated"
            for axis in result.axis_results.values()
        )
        assert result.research_status == "INCOMPLETE"
    finally:
        store.close()


def test_non_fatal_coverage_gaps_do_not_downgrade_research_status(
    tmp_path: Path,
) -> None:
    """功課沒做完不等於研究不可用——非致命的 coverage gap 不得把狀態打下來。

    原本的說法是「只降尺寸，不禁止參與」；U7 移除尺寸後，這條契約剩下的、
    也是唯一還可測的那一半是：`sizing` 級 blocker 不會讓 `research_status`
    掉出 READY，只有致命 blocker 才會（見上一個測試）。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        pending = _coverage(bundle)
        pending = CoverageResult(
            **{
                **pending.__dict__,
                "status": "coverage_pending",
                "blockers": (
                    "financial_runway_manual_required",
                    "independent_source_missing",
                    "counter_path_missing",
                ),
            }
        )

        result = calculate_probe_limits(bundle, pending, _assessment())

        assert result.research_status == "READY"
    finally:
        store.close()


# 2026-08-28（U7）刪除 `test_paper_book_remaining_can_bind_below_axis_ceiling`：
# 它唯一斷言的是 probe book 剩餘額度會綁在 axis ceiling 之下，而
# `single_probe_nav_cap`／`probe_book_nav_cap`／`constraint_trace` 已隨資本表達層
# 一起移除，系統不再由五軸換算任何額度。


def test_live_current_position_sums_every_listing_of_the_same_company(
    tmp_path: Path,
) -> None:
    """同一家公司的多個掛牌要合併成一個既有部位。

    原測試名為「paper 與 live 使用不同的 NAV 分母與執行流動性」，但 paper 端的
    NAV 分母與 live 端的 ADV／FX 換算都只服務額度計算，已於 U7 移除；留下的是
    `live_current_position`——它不是建議尺寸，是使用者手動記錄 live 選擇時的
    既有部位。
    """
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "FRA:2DG",
                "shares": 10.0,
                "currency": "EUR",
                "company_id": "co:sivers_semiconductors",
                "market_value_base": 10.0,
            },
            {
                "ticker": "SIVE.ST",
                "shares": 20.0,
                "currency": "SEK",
                "company_id": "co:sivers_semiconductors",
                "market_value_base": 20.0,
            },
        ]
    )
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    execution_market = {
        "status": "observed",
        "ticker": "FRA:2DG",
        "price": 10.0,
        "currency": "EUR",
        "adv20": 100.0,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "unit_status": "ok",
        "source": "fixture://fra-market",
    }
    execution_fx = {
        "status": "observed",
        "pair": "EUR/USD",
        "rate": 1.2,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "source": "fixture://eur-usd",
    }
    try:
        bundle = _bundle(
            store,
            inputs=inputs,
            execution_market=execution_market,
            execution_fx=execution_fx,
        )

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        # FRA:2DG 10 + SIVE.ST 20，同屬 co:sivers_semiconductors，除以 NAV 10,000。
        assert result.live_current_position == pytest.approx(0.003)
        # execution context 齊備時不得留下缺料 blocker。
        assert "execution_market_missing" not in result.live_blockers
        assert "execution_fx_missing" not in result.live_blockers
    finally:
        store.close()


def test_cash_rows_do_not_block_live_sizing_as_unmapped_holdings(
    tmp_path: Path,
) -> None:
    """Sheet 現金列計入 NAV，但沒有 company／factor 可解析，不得 fail closed。"""
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "—",
                "shares": 0.0,
                "currency": "USD",
                "market_value_base": 31_700.0,
                "is_cash": True,
            },
            {
                "ticker": "FRA:2DG",
                "shares": 10.0,
                "currency": "EUR",
                "company_id": "co:sivers_semiconductors",
                "market_value_base": 10.0,
            },
        ]
    )
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert not any(
            blocker.startswith("holdings_company_mapping_unresolved")
            for blocker in result.live_blockers
        )
        # 現金不得計入任何 factor 曝險。
        assert result.live_current_position == pytest.approx(0.001)
    finally:
        store.close()


def test_unmapped_non_cash_holding_no_longer_creates_mapping_blocker(tmp_path: Path) -> None:
    """未知持股改成警告層，不得讓已刪除的 factor mapping 重新擋住 live sizing。"""
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "MYSTERY",
                "shares": 5.0,
                "currency": "USD",
                "market_value_base": 500.0,
            },
        ]
    )
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert not any("mapping_unresolved" in blocker for blocker in result.live_blockers)
    finally:
        store.close()


def test_single_position_cap_surfaces_as_live_blocker(tmp_path: Path) -> None:
    """單筆 5% NAV 上限是真實風控，U7 不動它——只是改由 live blocker 現形。"""
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "FRA:2DG",
                "company_id": "co:sivers_semiconductors",
                "shares": 100.0,
                "currency": "EUR",
                "market_value_base": 600.0,
            }
        ]
    )
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)
        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert result.live_current_position >= result.single_position_nav_cap
        assert "single_position_nav_cap_reached" in result.live_blockers
    finally:
        store.close()


def test_portfolio_etf_leverage_cap_surfaces_as_live_blocker(tmp_path: Path) -> None:
    from decision_lab.beta_policy import load_beta_policy

    # TQQQ 是 3x：持有金額取兩個 cap 各自所需的較大者再加一，確保兩者都越界。
    # 依 policy 推導而非寫死數字，改 cap 時測試不會腐爛。
    risk = load_beta_policy()["risk"]
    nav = 10_000.0
    tqqq_value = max(
        nav * risk["leveraged_nominal_cap"],
        nav * risk["leveraged_effective_cap"] / 3.0,
    ) + 1.0
    store = _store(tmp_path)
    inputs = complete_inputs(
        rows=[
            {
                "ticker": "TQQQ",
                "shares": 10.0,
                "currency": "USD",
                "market_value_base": tqqq_value,
            },
            {
                "ticker": "FRA:2DG",
                "company_id": "co:sivers_semiconductors",
                "shares": 10.0,
                "currency": "EUR",
                "market_value_base": 10.0,
            },
        ]
    )
    inputs["holdings"].update({"nav_base": nav, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)
        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert "etf_leverage_nominal_cap_reached" in result.live_blockers
        assert "etf_leverage_effective_cap_reached" in result.live_blockers
    finally:
        store.close()


def test_research_listing_market_data_cannot_substitute_for_execution_listing_adv(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs(rows=[])
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "USD"})
    try:
        bundle = _bundle(store, inputs=inputs)

        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        # 研究面資料齊備（研究掛牌 SIVE.ST 的行情在 context 裡），但那份行情不能
        # 冒充執行掛牌的流動性——執行面仍必須留下缺料 blocker。
        assert result.research_status == "READY"
        assert "execution_market_missing" in result.live_blockers
    finally:
        store.close()


def test_live_fx_must_translate_execution_currency_into_holdings_base(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    inputs = complete_inputs(rows=[])
    inputs["holdings"].update({"nav_base": 10_000.0, "base_currency": "TWD"})
    execution_market = {
        "status": "observed",
        "ticker": "FRA:2DG",
        "price": 10.0,
        "currency": "EUR",
        "adv20": 100.0,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "unit_status": "ok",
        "source": "fixture://fra-market",
    }
    wrong_fx = {
        "status": "observed",
        "pair": "EUR/USD",
        "rate": 1.2,
        "as_of": "2026-07-21T10:00:00+00:00",
        "fetched_at": "2026-07-21T10:01:00+00:00",
        "source": "fixture://eur-usd",
    }
    try:
        bundle = _bundle(
            store,
            inputs=inputs,
            execution_market=execution_market,
            execution_fx=wrong_fx,
        )
        result = calculate_probe_limits(bundle, _coverage(bundle), _assessment())

        assert "execution_fx_pair_mismatch" in result.live_blockers
    finally:
        store.close()


def test_sizing_is_content_deterministic_and_rejects_context_mismatch(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        result_a = calculate_probe_limits(bundle, _coverage(bundle), _assessment())
        result_b = calculate_probe_limits(bundle, _coverage(bundle), _assessment())
        assert result_a == result_b

        mismatched = _coverage(bundle)
        mismatched = CoverageResult(
            **{**mismatched.__dict__, "context_digest": "different"}
        )
        with pytest.raises(AssessmentError, match="context"):
            calculate_probe_limits(bundle, mismatched, _assessment())
    finally:
        store.close()


# ── 2026-08-13：引用解析、至少一個合格引用、以及單調性 ─────────────────────────
#
# 三者都源自同一個實測：73 筆決策中「做了研究卻有軸 unknown」的 20 筆裡，33 個
# unknown 軸有 22 個是被配線改寫的，不是研究者宣告的。內容對、來源真的存在，
# 罰的卻是引用格式與多附的脈絡引用。


def test_reference_resolves_by_unique_prefix_without_penalty(tmp_path: Path) -> None:
    """引用少了後綴不該被罰——遇到就解析，不是打折。

    實例：研究者寫 `yfinance://history`，而 reference index 的 key 是
    `yfinance://history/AAOI`。先前 exact 比對失敗 → level 被改寫成 unknown →
    ceiling 0 → 整筆決策資本歸零。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        index = bundle.payload["reference_index"]
        full_key = next(
            key
            for key, entry in index.items()
            if "market" in set((entry or {}).get("authorities") or ())
        )
        assert len(full_key) > 4, "需要一個夠長的 key 才能測前綴解析"
        assessment = _assessment()
        assessment["valuation_payoff"]["evidence_refs"] = [full_key[:-2]]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        axis = result.axis_results["valuation_payoff"]
        assert axis["level"] == "corroborated", "解析成功就不該改寫等級"
        assert "assessment_context_mismatch:valuation_payoff" not in result.assessment_blockers
        # 解析必須留痕，不得靜默修好。
        assert full_key in axis["reference_resolutions"][full_key[:-2]]
    finally:
        store.close()


def test_ambiguous_reference_is_not_guessed(tmp_path: Path) -> None:
    """兩個以上候選就不解析——寧可報 mismatch，也不挑一個。"""
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment()
        # `fixture://` 同時是 fixture://filing 與 fixture://market 的前綴 → 歧義。
        assessment["valuation_payoff"]["evidence_refs"] = ["fixture://"]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        assert "assessment_context_mismatch:valuation_payoff" in result.assessment_blockers
    finally:
        store.close()


def test_extra_context_refs_do_not_zero_an_axis_that_has_valid_grounding(
    tmp_path: Path,
) -> None:
    """判準是「至少一個合格」，不是「每一個都要」。

    實例：META 的 technical_causal_link 有 `co:meta` 與 `meta_vistara_isca_2026`
    兩個合格引用，只因為多附了一個 `prod:vistara` 就被整軸打成 unknown；
    AXTI 的 financial_resilience 有合格的 `yfinance.info`，卻因為多附兩份 8-K
    脈絡引用而歸零。多附脈絡不是 authority laundering。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment()
        valid = assessment["valuation_payoff"]["evidence_refs"][0]
        assessment["valuation_payoff"]["evidence_refs"] = [valid, "prod:not-in-index"]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        axis = result.axis_results["valuation_payoff"]
        assert axis["level"] == "corroborated"
        assert "assessment_context_mismatch:valuation_payoff" not in result.assessment_blockers
        # 但不合格的那個必須現形供人稽核，不得靜默吞掉。
        assert axis["accepted_refs"] == (valid,)
        assert axis["context_only_refs"] == ("prod:not-in-index",)
    finally:
        store.close()


def test_zero_valid_refs_still_fails_closed(tmp_path: Path) -> None:
    """放寬只針對「多附脈絡」；**沒有任何**合格來源仍是 laundering，仍歸零。"""
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)
        assessment = _assessment()
        assessment["valuation_payoff"]["evidence_refs"] = ["prod:a", "prod:b"]

        result = calculate_probe_limits(bundle, _coverage(bundle), assessment)

        assert result.axis_results["valuation_payoff"]["level"] == "unknown"
        assert "assessment_context_mismatch:valuation_payoff" in result.assessment_blockers
        assert result.research_status == "INCOMPLETE"
    finally:
        store.close()


def test_declaring_corroborated_never_yields_less_than_bounded_hypothesis(
    tmp_path: Path,
) -> None:
    """單調性：宣告較高信心不得被判得比宣告較低信心更弱。

    先前 `corroborated + missing_data` → ceiling 0，比誠實降級成
    `bounded_hypothesis`（同一批待補項，0.002）**更差**。後果是評估者學會迴避那個
    組合——73 筆歷史決策中該組合出現 **0 次**，規則在暗中形塑了評估行為。
    也因為出現 0 次，這條修正無法用歷史資料驗證，只能由本測試鎖住。

    U7 之後額度不存在，但同一條單調性仍活在 `effective_level`：
    `corroborated + missing_data` 只被壓回下一階，不打成 unknown。
    """
    store = _store(tmp_path)
    try:
        bundle = _bundle(store)

        honest = _assessment()
        honest["valuation_payoff"]["missing_data"] = ["downside case 未建"]
        declared_high = calculate_probe_limits(bundle, _coverage(bundle), honest)

        conservative = _assessment()
        conservative["valuation_payoff"]["level"] = "bounded_hypothesis"
        conservative["valuation_payoff"]["missing_data"] = ["downside case 未建"]
        declared_low = calculate_probe_limits(bundle, _coverage(bundle), conservative)

        high_level = declared_high.axis_results["valuation_payoff"]["effective_level"]
        low_level = declared_low.axis_results["valuation_payoff"]["effective_level"]
        assert high_level == "bounded_hypothesis"
        assert LEVELS.index(high_level) >= LEVELS.index(
            low_level
        ), "宣告 corroborated 不得比宣告 bounded_hypothesis 更差"
        assert declared_high.research_status == declared_low.research_status
    finally:
        store.close()


def test_describe_axis_references_lists_only_qualifying_keys() -> None:
    """寫 assessment 的人看不到 index，只能猜引用字串——這是歸零的真正源頭。"""

    from decision_lab.sizing import describe_axis_references

    index = {
        "yfinance.info": {"authorities": ["engine_c_financial"]},
        "LITE 10-Q Note 17": {"authorities": ["engine_c_customer", "engine_c_manual"]},
        "co:lumentum": {"authorities": ["graph_entity"]},
    }

    options = describe_axis_references(index)

    assert [row["reference"] for row in options["commercial_maturity"]] == [
        "LITE 10-Q Note 17"
    ]
    assert [row["reference"] for row in options["technical_causal_link"]] == [
        "co:lumentum"
    ]
    # 該軸完全沒有合格來源時要回空，讓呼叫端能說「改引用救不了」。
    assert options["valuation_payoff"] == ()


def test_diagnose_reports_why_each_ref_was_rejected() -> None:
    """診斷必須分辨『解析不到』與『解析到了但 authority 不對』——兩者的修法不同。"""

    from decision_lab.sizing import diagnose_assessment_references

    index = {
        "LITE 10-Q Note 17": {"authorities": ["engine_c_customer"]},
        "lumentum_els_order": {"authorities": ["graph_source_assertion"]},
    }
    assessment = {
        axis: {
            "level": "bounded_hypothesis",
            "evidence_refs": [],
            "reason": "x",
            "missing_data": [],
        }
        for axis in AXES
    }
    assessment["commercial_maturity"]["evidence_refs"] = [
        "LITE 10-Q, filed 2026-05-06",  # 同一份文件的另一種寫法 → 解析不到
        "lumentum_els_order",           # 解析得到，但 authority 不被這一軸接受
    ]

    report = diagnose_assessment_references(assessment, index)["commercial_maturity"]

    # U7 改名：`would_zero_out` 講的是額度歸零，而額度已不存在；同一件事現在的
    # 名字是「這一軸的實質等級會被打回 unknown」。
    assert report["would_downgrade_to_unknown"] is True
    assert report["accepted_refs"] == ()
    reasons = {row["reference"]: row["why"] for row in report["rejected_refs"]}
    assert reasons["LITE 10-Q, filed 2026-05-06"] == "unresolved"
    assert reasons["lumentum_els_order"] == "authority_mismatch"


def test_diagnose_marks_axis_safe_when_one_ref_qualifies() -> None:
    """判準是『至少一個合格』，多附脈絡引用不得讓整軸歸零。"""

    from decision_lab.sizing import diagnose_assessment_references

    index = {
        "LITE 10-Q Note 17": {"authorities": ["engine_c_customer"]},
        "lumentum_els_order": {"authorities": ["graph_source_assertion"]},
    }
    assessment = {
        axis: {
            "level": "bounded_hypothesis",
            "evidence_refs": [],
            "reason": "x",
            "missing_data": [],
        }
        for axis in AXES
    }
    assessment["commercial_maturity"]["evidence_refs"] = [
        "LITE 10-Q Note 17",
        "lumentum_els_order",
    ]

    report = diagnose_assessment_references(assessment, index)["commercial_maturity"]

    assert report["would_downgrade_to_unknown"] is False
    assert report["accepted_refs"] == ("LITE 10-Q Note 17",)
