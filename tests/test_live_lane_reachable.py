"""Live lane 必須在 production 形狀下真的走得到 ELIGIBLE。

2026-08-08 紅隊：`holdings_confirmations`、`live_choices`、`live_execution_reports`、
`prepared_actions` 在真實 store 全是 0 筆——整個 live 半邊從未被執行過。既有 e2e
（`test_decision_lab_e2e.py`）走的是 Sivers 形狀：research `SIVE.ST` 與 execution
`FRA:2DG` 不同 symbol、不同幣別，需要 execution_market ＋ execution_fx 兩份額外資料。

但投組裡多數標的（AXTI／META／AAOI／COHR）是**另一種形狀**：execution_symbol 等於
research_ticker、execution_currency 等於 holdings base_currency，因此 execution_market
走 deepcopy 複用、execution_fx 直接是 None。那條分支才是真的要用時會先跑到的路徑，
卻沒有測試鎖住它。

本測試不驗證投資判斷，只驗證「這條路通不通」——不要在真的想下單那天，才第一次發現
它壞在哪。
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.coverage import assess_coverage
from decision_lab.sizing import calculate_probe_limits
from tests.test_decision_context import NOW, complete_inputs
from tests.test_decision_execution import _store
from tests.test_probe_sizing import _assessment
from thesis.investment_policy import load_policy


def _same_symbol_payload() -> dict:
    """把 Sivers fixture（跨市場）改造成投組多數標的的形狀。

    ``complete_inputs`` 是 SIVE.ST／FRA:2DG 跨 symbol 跨幣別；AXTI／META／AAOI／COHR
    則是同 symbol 同幣別（USD），走的是 execution_market 複用與 execution_fx=None
    兩條完全不同的分支。
    """

    payload = deepcopy(complete_inputs())
    # 用 registry 裡真實的 co:axt 值，不要自造一組跟 registry 打架的 identity——
    # store 會驗證 bundle identity 與 cohort authority 一致（那道檢查是對的）。
    payload["identity"] = {
        "company_id": "co:axt",
        "research_ticker": "AXTI",
        "execution_symbol": "AXTI",
        "market_currency": "USD",
        "execution_currency": "USD",
        "execution_venue": "NASDAQ",
    }
    identity = payload["identity"]
    payload["financial"] = dict(payload["financial"]) | {"ticker": "AXTI"}
    payload["market"] = dict(payload["market"]) | {"ticker": "AXTI", "currency": "USD"}
    payload["fx"] = dict(payload["fx"]) | {"pair": "USD/USD", "rate": 1.0}
    # base_currency 必須與 execution_currency 相同，才會走到「免換匯」那條分支；
    # 缺它會落到 execution_fx_missing——那正是 production 不會發生、fixture 卻會的差異。
    payload["holdings"] = dict(payload["holdings"]) | {
        "base_currency": "USD",
        "nav_base": 100000.0,
        "rows": [
            dict(row)
            | {
                "ticker": identity["research_ticker"],
                "currency": "USD",
                # production 的 adapters.current_holdings 會帶這欄；sizing 用它算
                # 目前曝險，缺了就 holdings_market_value_missing。
                "market_value_base": 1000.0,
            }
            for row in payload["holdings"]["rows"]
        ],
    }
    # evidence 的 focus company 要跟著 identity 走，否則 coverage 會判
    # graph_company_missing（那是對的：圖裡談的不是這家公司）。
    evidence = dict(payload["evidence"])
    evidence["focus_company"] = dict(evidence.get("focus_company") or {}) | {
        "id": identity["company_id"]
    }
    evidence["entities"] = [{"id": identity["company_id"]}]
    payload["evidence"] = evidence
    payload.pop("execution_market", None)
    payload.pop("execution_fx", None)
    return payload


def test_same_symbol_same_currency_live_lane_reaches_eligible(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        payload = _same_symbol_payload()
        identity = payload["identity"]

        cohort_id = store.ensure_cohort(
            dedupe_key="live-lane-reachable",
            company_id=identity["company_id"],
            research_ticker=identity["research_ticker"],
        ).cohort_id
        # 持倉確認是使用者的聲明，是 live 唯一無法由系統自行滿足的前置條件。
        store.record_holdings_confirmation(
            # 有 nav_base／base_currency 時 digest 必須帶進去，否則確認的是另一個快照。
            holdings_snapshot_digest(
                [
                    {
                        k: v
                        for k, v in row.items()
                        if k in {"ticker", "shares", "currency", "market_value_base"}
                    }
                    for row in payload["holdings"]["rows"]
                ],
                nav_base=payload["holdings"]["nav_base"],
                base_currency=payload["holdings"]["base_currency"],
            ),
            confirmed_at="2026-07-21T09:00:00+00:00",
        )
        bundle = build_context_bundle(
            store,
            cohort_id=cohort_id,
            evaluation_at=NOW,
            policy_version=load_policy()["policy_version"],
            **payload,
        )

        assert bundle.payload["holdings"]["status"] == "confirmed"
        assert bundle.payload["execution_market"]["status"] == "available"

        coverage = assess_coverage(
            store,
            bundle,
            catalyst="next filing",
            disproof="commercial evidence fails",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
            execution_intent="live",
        )
        assert coverage.live_context_ready is True

        sizing = calculate_probe_limits(bundle, coverage, _assessment())

        assert sizing.live_status == "ELIGIBLE"
        assert sizing.live_supported_range[1] > 0
        assert sizing.live_supported_shares is not None
        # live 仍不得自動成立：supported range 是可評估上限，不是已核准部位。
        assert sizing.live_blockers == ()
    finally:
        store.close()


def test_missing_holdings_confirmation_is_the_only_thing_between_us_and_live(
    tmp_path: Path,
) -> None:
    """同一組輸入，只差使用者未確認持倉 → live 必須關閉且 range 歸零。

    這鎖住「live 是被人工 gate 擋住，不是被資料缺口擋住」——兩者在輸出上長得像，
    但前者等你一句話，後者等系統修東西。
    """

    store = _store(tmp_path)
    try:
        payload = _same_symbol_payload()
        identity = payload["identity"]
        cohort_id = store.ensure_cohort(
            dedupe_key="live-lane-unconfirmed",
            company_id=identity["company_id"],
            research_ticker=identity["research_ticker"],
        ).cohort_id
        bundle = build_context_bundle(
            store,
            cohort_id=cohort_id,
            evaluation_at=NOW,
            policy_version=load_policy()["policy_version"],
            **payload,
        )

        assert bundle.payload["holdings"]["status"] == "unconfirmed"
        assert "holdings_unconfirmed" in bundle.payload["holdings"]["blockers"]

        coverage = assess_coverage(
            store,
            bundle,
            catalyst="next filing",
            disproof="commercial evidence fails",
            expiry="2026-08-21T00:00:00+00:00",
            decision_relevance=8,
            falsifiability=8,
            information_value=7,
            execution_intent="live",
        )
        sizing = calculate_probe_limits(bundle, coverage, _assessment())

        assert coverage.live_context_ready is False
        assert sizing.live_status == "DATA_NEEDED"
        assert sizing.live_supported_range == (0.0, 0.0)
        assert "holdings_unconfirmed" in sizing.live_blockers
        # paper 不受持倉確認影響——它是模擬帳本，不需要真實持倉真相。
        assert sizing.paper_max_supported_position > 0
    finally:
        store.close()
