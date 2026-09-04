"""Live lane 必須在 production 形狀下真的走得通。

2026-08-08 紅隊：`holdings_confirmations`、`live_choices`、`live_execution_reports`、
`prepared_actions` 在真實 store 全是 0 筆——整個 live 半邊從未被執行過。既有 e2e
（`test_decision_lab_e2e.py`）走的是 Sivers 形狀：research `SIVE.ST` 與 execution
`FRA:2DG` 不同 symbol、不同幣別，需要 execution_market ＋ execution_fx 兩份額外資料。

但投組裡多數標的（AXTI／META／AAOI／COHR）是**另一種形狀**：execution_symbol 等於
research_ticker、execution_currency 等於 holdings base_currency，因此 execution_market
走 deepcopy 複用、execution_fx 直接是 None。那條分支才是真的要用時會先跑到的路徑，
卻沒有測試鎖住它。

⚠ U7（2026-08-28）改寫：原測試問的是「系統會不會把 live 判成 `ELIGIBLE` 並給出
supported range」。系統已不再判定 live 資格、也不再輸出區間——尺寸一律由使用者決定。
本檔想防的東西沒變（**不要在真的想下單那天，才第一次發現它壞在哪**），所以判準改成
真正走得通才成立的兩件事：

1. 一筆非零的 live 選擇可以被 `record_live_choice` 成功記下，並留下 `user_sized` 稽核；
2. 缺持股確認等情況會誠實留在 `live_blockers` 裡，而不是安靜消失或連坐研究面。

本測試不驗證投資判斷。
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from decision_lab.context import build_context_bundle, holdings_snapshot_digest
from decision_lab.coverage import assess_coverage
from decision_lab.execution import ExecutionError, assess_probe, record_live_choice
from decision_lab.sizing import calculate_probe_limits
from tests.test_decision_context import NOW, complete_inputs
from tests.test_decision_execution import _store
from tests.test_probe_sizing import _assessment
from risk.policy import load_policy


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
                # production 的 adapters.current_holdings 會帶這欄；缺了就
                # holdings_market_value_missing。
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


def _live_decision(store, payload: dict, *, key: str, confirm_holdings: bool):
    """把 same-symbol payload 一路跑到一筆已凍結的 system decision。"""

    identity = payload["identity"]
    cohort_id = store.ensure_cohort(
        dedupe_key=key,
        company_id=identity["company_id"],
        research_ticker=identity["research_ticker"],
    ).cohort_id
    if confirm_holdings:
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
    return bundle, coverage


def test_user_sized_live_choice_is_recordable_end_to_end(tmp_path: Path) -> None:
    """非零 live 選擇必須真的記得下來——這是 live 這條路唯一還會被走的一步。

    系統不再判定 live 資格，所以「走得通」的定義變成：使用者說一個尺寸，它能被寫成
    可稽核的 `live_choices` 列，且真實資本護欄（5% 單筆上限）仍然生效。
    """

    store = _store(tmp_path)
    try:
        payload = _same_symbol_payload()
        bundle, coverage = _live_decision(
            store, payload, key="live-lane-reachable", confirm_holdings=True
        )

        assert bundle.payload["holdings"]["status"] == "confirmed"
        assert bundle.payload["execution_market"]["status"] == "available"
        assert coverage.live_context_ready is True

        sizing = calculate_probe_limits(bundle, coverage, _assessment())
        # 執行面沒有缺口——這正是 2026-08-08 想確認的那條分支真的接得上。
        assert sizing.live_blockers == ()
        assert sizing.single_position_nav_cap == pytest.approx(0.05)

        decision = assess_probe(
            store,
            bundle,
            coverage,
            _assessment(),
            idempotency_key="live-lane-reachable",
            effective_at=NOW,
            execution_intent="live",
        )

        choice_id = record_live_choice(
            store,
            decision.decision_id,
            selected_weight=0.01,
            decided_at="2026-07-21T13:00:00+00:00",
            explicit=True,
            user_sized=True,
            reason="使用者自行決定的探索部位",
        )

        assert choice_id.startswith("lc_")
        recorded = store.latest_live_choice(decision.decision_id)
        assert recorded["choice_type"] == "user_sized"
        assert float(recorded["selected_weight"]) == pytest.approx(0.01)
        # 「系統沒有給過區間」與「區間是 0」不是同一件事（L12）：新 choice 在稽核欄
        # 寫 NULL，不得補一個 0 冒充「系統說上限是 0」。
        stored_upper = store._conn.execute(
            "SELECT system_supported_upper FROM live_choices WHERE choice_id = ?",
            (choice_id,),
        ).fetchone()["system_supported_upper"]
        assert stored_upper is None

        # 真正的資本護欄沒有跟著資本表達層一起被拆掉：已持有 1% ＋ 再買 4.5%
        # 會超過 5% 單筆上限，必須硬擋。
        with pytest.raises(ExecutionError, match="single position cap"):
            record_live_choice(
                store,
                decision.decision_id,
                selected_weight=0.045,
                decided_at="2026-07-21T14:00:00+00:00",
                explicit=True,
                user_sized=True,
                reason="刻意超過單筆上限",
            )
    finally:
        store.close()


def test_missing_holdings_confirmation_stays_a_visible_live_blocker(
    tmp_path: Path,
) -> None:
    """同一組輸入，只差使用者未確認持倉 → live 必須關閉且理由現形。

    這鎖住「live 是被人工 gate 擋住，不是被資料缺口擋住」——兩者在輸出上長得像，
    但前者等你一句話，後者等系統修東西。

    U7：原測試用 `live_status == "DATA_NEEDED"` ＋ `live_supported_range == (0, 0)`
    表達；系統不再判定 live 資格，同一件事改由 blocker 自己現形表達。
    """

    store = _store(tmp_path)
    try:
        payload = _same_symbol_payload()
        bundle, coverage = _live_decision(
            store, payload, key="live-lane-unconfirmed", confirm_holdings=False
        )

        assert bundle.payload["holdings"]["status"] == "unconfirmed"
        assert "holdings_unconfirmed" in bundle.payload["holdings"]["blockers"]
        assert coverage.live_context_ready is False

        sizing = calculate_probe_limits(bundle, coverage, _assessment())

        assert "holdings_unconfirmed" in sizing.live_blockers
        # 研究面不受持倉確認影響——它問的是證據，不是我的試算表。
        assert "holdings_unconfirmed" not in sizing.paper_blockers
    finally:
        store.close()
