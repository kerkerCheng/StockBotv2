"""籃子頁（V3，2026-09-15）：`webapp/basket.py` 純 join ＋ filter 式首選。

守的是四件事：
1. **順序照抄**：列＝ranking 可行動排序去重，一個位元不重排；沒有任何加權。
2. **首選是 filter 不是分數**：三條規則；沒有一檔通過就 top_pick=null ＋ 理由計數（INV-3：input／accepted／filtered／reasons）。
3. **缺席不同形**：沒 overview 的檔還在列上（has_overview=false）、理由是 no_bet；沒有 positions artifact 也能建。
4. **API**：/api/v1/basket 是 GET、照抄；state kind 是封閉字彙。
"""
from __future__ import annotations

from datetime import datetime, timezone

from webapp.basket import FILTER_REASONS, build_basket_artifact
from webapp.contracts import STATE_KINDS, validate_state_artifact


def _ranking(rows):
    return {"as_of": None, "generated_at": "2026-09-15T00:00:00+00:00", "point_in_time": {"as_of": None, "mode": "current"},
            "rows": rows, "sectors": [{"sector": "AI 光互連", "actionable_ranks": [1, 2, 4]}, {"sector": "稀土", "actionable_ranks": [3]}],
            "correlation_notes": ["同漲同跌"]}


def _row(rank, ticker, bottleneck="tech:x"):
    return {"rank": rank, "ticker": ticker, "company_id": f"co:{ticker.lower()}", "company_label": ticker,
            "bottleneck": bottleneck, "relation": "supplies_to", "evidence": "externally_corroborated", "evidence_label": "外部印證"}


def _overview(*, payoff=None, links=(), value_date="2027-06-30", our_bet=None, moved=None):
    ripeness = None
    if links:
        ripeness = {"value": {"counts": {"total": len(links), "linked": len(links), "resolved": 0, "due": 0, "pending": len(links)},
                              "links": [{"expected_at": d, "state": s, "resolves": ["oa_x"]} for d, s in links]}}
    return {
        "company_label": "X", "readiness": {"state": "ready"}, "opinion_stance": {"value": "independent"},
        "price": {"value": 100.0, "quote_unit": "USD"},
        "future_target": {"value": 120.0, "value_date": {"value": value_date}},
        "implied_return": {"simple": {"value": 0.2}},
        "payoff": {"status": "available" if payoff is not None else "missing", "absence_kind": None if payoff is not None else "not_yet_recorded",
                   "simple": {"value": payoff}},
        "brief": {"our_bet": {"value": our_bet}},
        "ripeness": ripeness,
        "gap_closure": {"value": {"base": {"closed_fraction": moved, "n_points": 3}} if moved is not None else None},
        "target_reached": {"value": {"any_reached": False}},
    }


def test_rows_follow_the_ranking_order_deduplicated_and_never_rescored() -> None:
    ranking = _ranking([_row(1, "LITE"), _row(2, "COHR"), _row(3, "MP"), _row(4, "COHR", "tech:y")])
    out = build_basket_artifact(ranking=ranking, overviews={}, positions=None, generated_at=datetime(2026, 9, 15, tzinfo=timezone.utc))
    assert [r["ticker"] for r in out["rows"]] == ["LITE", "COHR", "MP"]
    assert [r["rank"] for r in out["rows"]] == [1, 2, 3]
    assert [r["sector"] for r in out["rows"]] == ["AI 光互連", "AI 光互連", "稀土"]
    assert all(r["has_overview"] is False and r["filter_reasons"] == ["no_bet", "no_catalyst_in_horizon"] for r in out["rows"])
    assert out["top_pick"] is None and "還沒寫賭注（variant 假設） 3 檔" in out["top_pick_absent_reason"]
    validate_state_artifact("basket", out)


def test_top_pick_is_the_first_in_structural_order_that_passes_all_three_rules() -> None:
    ranking = _ranking([_row(1, "LITE"), _row(2, "COHR"), _row(3, "MP"), _row(4, "AXTI")])
    overviews = {
        "LITE": _overview(payoff=0.3, links=()),                                        # 有賭注、正，但沒裁決點
        "COHR": _overview(payoff=-0.085, links=(("2026-12-01", "pending"),)),           # payoff 為負
        "MP": _overview(payoff=0.25, links=(("2027-09-01", "pending"),), value_date="2027-06-30"),   # 裁決點在目標價日期之後
        "AXTI": _overview(payoff=0.2, links=(("2026-10-30", "due"),), our_bet="賭 InP 放量", moved=0.4),
    }
    out = build_basket_artifact(ranking=ranking, overviews=overviews, positions={"live": {"rows": [{"ticker": "COHR", "shares": 10, "price": 316.23, "currency": "USD", "executed_at": "2026-08-18", "live_return": -0.157}]}})
    by = {r["ticker"]: r for r in out["rows"]}
    assert by["LITE"]["filter_reasons"] == ["no_catalyst_in_horizon"]
    assert by["COHR"]["filter_reasons"] == ["payoff_not_positive"] and by["COHR"]["held"] and by["COHR"]["position"]["shares"] == 10
    assert by["MP"]["filter_reasons"] == ["no_catalyst_in_horizon"]
    assert by["AXTI"]["passes_filter"] and by["AXTI"]["consensus_moved"] == 0.4
    assert out["top_pick"]["ticker"] == "AXTI" and out["top_pick"]["rank"] == 4
    f = out["filter"]
    assert f == {**f, "input": 4, "accepted": 1, "filtered": 3}
    assert set(f["reasons"]) == set(FILTER_REASONS) and f["reasons"]["no_catalyst_in_horizon"] == 2
    assert "不是買進指令" in out["top_pick"]["note"]


def test_state_kind_is_registered_and_api_serves_it(tmp_path) -> None:
    assert "basket" in STATE_KINDS
    from starlette.testclient import TestClient

    from webapp.api import create_app
    from webapp.store import StateArtifactStore

    state_dir = tmp_path / "state"
    store = StateArtifactStore(state_dir)
    ranking = _ranking([_row(1, "LITE")])
    store.write(build_basket_artifact(ranking=ranking, overviews={}, positions=None))
    client = TestClient(create_app(tmp_path, state_dir))
    got = client.get("/api/v1/basket")
    assert got.status_code == 200 and got.json()["top_pick"] is None and got.json()["rows"][0]["ticker"] == "LITE"
    assert client.post("/api/v1/basket").status_code == 405
