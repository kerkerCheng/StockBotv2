"""多年視角必須是 **materialize 出來的 artifact**，不能在 request path 算（Phase 7 Step 7.4）。

APP 呈現契約逐字：request path **不得**跑 LLM、寫 authority、抓外部資料、**跑任何金融模型**。
多年橋就是金融模型（它跑一次真正的 `build_bridge` ＋ 二分法反解），
所以它的唯一合法位置是 `python -m webapp materialize --multi-year`。

⚠ **每一檔都進 rows，包括算不出來的**——三件事不得同形（INV-3）：
「artifact 讀不到」／「還沒有人寫下 `multiple_horizon`」／「這一檔沒有多年主張」。
"""
from __future__ import annotations

from datetime import datetime, timezone

from briefing.multi_year import build_multi_year_artifact
from webapp.contracts import STATE_KINDS, STATE_REQUIRED_FIELDS


def test_the_kind_is_registered() -> None:
    assert "multi_year" in STATE_KINDS


def test_the_artifact_answers_every_required_question() -> None:
    payload = build_multi_year_artifact([], generated_at=datetime(2026, 9, 19, tzinfo=timezone.utc))
    for field in STATE_REQUIRED_FIELDS:
        assert field in payload, f"state artifact 缺必要欄位 {field}——partial write 一律拒收"
    assert payload["kind"] == "multi_year"
    assert payload["point_in_time"] == {"as_of": None, "mode": "current"}


def test_an_empty_universe_is_still_a_valid_artifact() -> None:
    """**「沒有標的」與「artifact 壞了」是兩件事。**"""
    payload = build_multi_year_artifact([])
    assert payload["rows"] == []
    assert payload["counts"] == {"input": 0, "available": 0, "no_horizon": 0}


def test_an_unresolvable_ticker_becomes_a_row_not_an_exception() -> None:
    """單檔失敗**不得**讓整份 artifact 失敗——它變成一列帶理由的 missing。"""
    payload = build_multi_year_artifact(["ZZZZ-NOT-A-TICKER"])
    assert payload["counts"]["input"] == 1
    assert payload["counts"]["available"] == 0
    row = payload["rows"][0]
    assert row["status"] == "missing" and row["reason"]


def test_it_says_out_loud_that_it_is_not_a_forecast() -> None:
    """「需要 EPS 25.39」很容易被讀成目標價——artifact 自己要把這件事講死。"""
    payload = build_multi_year_artifact([])
    assert "不是預測" in payload["this_is_not"]
    assert "由人判斷" in payload["this_is_not"]
    assert "不是預測" in payload["authority"]["note"]


def test_freshness_identity_ignores_price_noise() -> None:
    """認知狀態＝結論，不是小數。

    `required_eps` 每天跟著股價動，但「2 倍需要營收成長 4.65 倍、3 倍以上做不到」
    這個結論不會。把價格雜訊算進 identity 會讓它每天看起來「變了」。
    """
    payload = build_multi_year_artifact([])
    identity = payload["freshness_identity"]
    assert identity
    assert "required_eps" not in str(identity)
