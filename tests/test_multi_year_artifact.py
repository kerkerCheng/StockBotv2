"""多年視角必須是 **materialize 出來的 artifact**，不能在 request path 算（Phase 7 Step 7.4）。

APP 呈現契約逐字：request path **不得**跑 LLM、寫 authority、抓外部資料、**跑任何金融模型**。
多年橋就是金融模型（它跑一次真正的 `build_bridge` ＋ 二分法反解），
所以它的唯一合法位置是 `python -m webapp materialize --multi-year`。

⚠ **每一檔都進 rows，包括算不出來的**——三件事不得同形（INV-3）：
「artifact 讀不到」／「還沒有人寫下 `multiple_horizon`」／「這一檔沒有多年主張」。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

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
    assert payload["counts"] == {"input": 0, "available": 0, "no_horizon": 0,
                                 "no_judgment": 0, "method_not_applicable": 0,
                                 "other_missing": 0}


def test_an_unresolvable_ticker_becomes_a_row_not_an_exception() -> None:
    """單檔失敗**不得**讓整份 artifact 失敗——它變成一列帶理由的 missing。"""
    payload = build_multi_year_artifact(["ZZZZ-NOT-A-TICKER"])
    assert payload["counts"]["input"] == 1
    assert payload["counts"]["available"] == 0
    row = payload["rows"][0]
    assert row["status"] == "missing" and row["reason"]


def test_the_count_buckets_are_mutually_exclusive_and_exhaustive() -> None:
    """五格必須加總等於 input（INV-3）。

    2026-09-19 以前只有一格 `no_horizon`，而它數的是「所有非 available」——於是
    「連判斷檔都沒有」與「錨點是負的、方法不適用」全被心跳／APP／CLI 印成
    「還沒寫下目標年度」。**其中沒有一個是那個意思**，而讀的人會去做一件補不了的事。
    """
    payload = build_multi_year_artifact(["ZZZZ-NOT-A-TICKER"])
    c = payload["counts"]
    buckets = ("available", "no_horizon", "no_judgment",
               "method_not_applicable", "other_missing")
    for key in buckets:
        assert key in c, f"counts 缺 {key}——缺席少一種名字，下游就會把它併進別人那一格"
    assert sum(c[k] for k in buckets) == c["input"], (
        f"五格加總 {sum(c[k] for k in buckets)} != input {c['input']}"
        "——有一種狀態沒有自己的格子，它會安靜地被算成別的東西")


def test_a_loss_making_base_year_is_method_not_applicable_not_a_structural_verdict() -> None:
    """錨點 EPS ≤ 0 時**不得**印階梯。

    事發（2026-09-19，[633] 寫入 AXTI 的 FY2028 錨點當天）：AXT FY2025 非 GAAP 營益率
    −21.2%，而錨點取的是「沿用基期」，於是 FY2028 錨點 EPS ＝ −0.0789。四級階梯因此
    全部印「拉到極限也做不到」——**與同一檔 FY+1 反向橋的「2x available」方向相反**。

    那句話不是結構結論，是儀器在虧損期失效：反解此時問的是「從負數漲到正數要多少」。
    兩種語意在輸出上長得一模一樣（L12），而下游只會讀到後面那個。
    """
    from briefing.multi_year import MultiYearView, render_multi_year

    view = MultiYearView(
        ticker="TEST", company_id="co:test", horizon=date(2028, 12, 31),
        status="method_not_applicable", anchor_eps=-0.0789,
        reason="錨點 EPS 是 -0.0789（≤ 0）——基期在虧損，而錨點取的是「沿用基期」",
        ladder=())
    text = render_multi_year(view)
    assert "方法在這一檔不適用" in text, "不得說成「算不出來」——那是缺料，補了就有；這個補不了"
    assert "拉到極限也做不到" not in text, "虧損基期不得印階梯——每一級都會是它，而它會被讀成結構結論"
    assert view.ladder == (), "method_not_applicable 不建 ladder"


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
