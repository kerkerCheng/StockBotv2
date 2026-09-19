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
    assert all(r["has_overview"] is False and r["filter_reasons"] == ["no_bet", "no_catalyst_recorded"] for r in out["rows"])
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
    assert by["LITE"]["filter_reasons"] == ["no_catalyst_recorded"]        # links=() 且沒有 shape＝一條都沒記
    assert by["COHR"]["filter_reasons"] == ["payoff_not_positive"] and by["COHR"]["held"] and by["COHR"]["position"]["shares"] == 10
    assert by["MP"]["filter_reasons"] == ["catalyst_after_value_date"]     # 有指名假設，但日期晚於目標價日
    assert by["AXTI"]["passes_filter"] and by["AXTI"]["consensus_moved"] == 0.4
    assert out["top_pick"]["ticker"] == "AXTI" and out["top_pick"]["rank"] == 4
    f = out["filter"]
    assert f == {**f, "input": 4, "accepted": 1, "filtered": 3}
    assert set(f["reasons"]) == set(FILTER_REASONS)
    assert f["reasons"]["no_catalyst_recorded"] == 1 and f["reasons"]["catalyst_after_value_date"] == 1
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

# ---------------------------------------------------------------------------
# Q1（2026-09-17 使用者核准 A）：第二個宇宙——被門檻擋下、但已研究過的那些
# ---------------------------------------------------------------------------

def _filtered(ticker, *, sub=3, qual="qualified", anchor="tech:ai_switch",
              reason="substitutability_below_threshold"):
    return {"company_id": f"co:{ticker.lower()}", "ticker": ticker, "relation": "supplies_to",
            "bottleneck": "tech:x", "substitutability": sub, "threshold": 4,
            "qualification_status": qual, "evidence": "company_disclosure", "documents": 1,
            "chain": [anchor] if anchor else [], "demand_anchor": anchor,
            "demand_hops": 1 if anchor else None, "reasons": [reason]}


def _ranking_with_filtered(rows, filtered):
    payload = _ranking(rows)
    payload["filtered_rows"] = filtered
    payload["filter"] = {"input": len(rows) + len(filtered), "accepted": len(rows),
                         "filtered": len(filtered), "reasons": {}, "reason_labels": {}}
    return payload


def test_the_moat_basket_is_untouched_by_the_second_universe() -> None:
    """Q1 是**純加法**：`rows`／`filter`／`top_pick` 一個位元都不得因為多了第二個宇宙而變。"""
    rows = [_row(1, "LITE"), _row(2, "COHR")]
    before = build_basket_artifact(ranking=_ranking(rows), overviews={}, positions=None,
                                   generated_at=datetime(2026, 9, 17, tzinfo=timezone.utc))
    after = build_basket_artifact(
        ranking=_ranking_with_filtered(rows, [_filtered("3081.TWO"), _filtered("SHA0.DE")]),
        overviews={}, positions=None, generated_at=datetime(2026, 9, 17, tzinfo=timezone.utc))
    assert after["rows"] == before["rows"]
    assert after["filter"] == before["filter"]
    assert after["top_pick"] == before["top_pick"]
    assert after["bet_ledger"] == before["bet_ledger"]


def test_only_researched_edges_enter_the_second_universe() -> None:
    """`unfilled`（還沒有人研究過）不是候選，是研究缺口——它的去處是 pq1，不是籃子。"""
    ranking = _ranking_with_filtered([_row(1, "LITE")], [
        _filtered("3081.TWO"),
        _filtered("NEVER.RESEARCHED", sub=None, reason="substitutability_unfilled"),
    ])
    out = build_basket_artifact(ranking=ranking, overviews={}, positions=None)
    assert [r["ticker"] for r in out["volume_rows"]] == ["3081.TWO"]


def test_one_company_one_row_even_with_many_edges() -> None:
    ranking = _ranking_with_filtered([], [_filtered("LITE"), _filtered("LITE"), _filtered("GFS")])
    out = build_basket_artifact(ranking=ranking, overviews={}, positions=None)
    assert [r["ticker"] for r in out["volume_rows"]] == ["GFS", "LITE"]


def test_volume_candidates_must_already_be_shipping() -> None:
    """⚠ 這條**比護城河宇宙更嚴，不是放寬**：量的賭注要求需求來了吃得到。

    sub>=4 的護城河宇宙收得下 `qualifying`／未填；量的宇宙收不下。
    這就是「擴大宇宙不等於為了讓籃子非空而放寬條件」的機械證明。
    """
    ranking = _ranking_with_filtered([], [
        _filtered("SHIP", qual="qualified"), _filtered("DESIGNED", qual="designed_in"),
        _filtered("SAMPLING", qual="sampling"), _filtered("UNKNOWN", qual=None)])
    out = build_basket_artifact(ranking=ranking, overviews={}, positions=None)
    blocked = {r["ticker"]: r["filter_reasons"] for r in out["volume_rows"]}
    assert "not_shipping_yet" not in blocked["SHIP"] and "not_shipping_yet" not in blocked["DESIGNED"]
    assert "not_shipping_yet" in blocked["SAMPLING"] and "not_shipping_yet" in blocked["UNKNOWN"]


def test_a_company_already_in_the_moat_basket_is_not_a_new_candidate() -> None:
    """擴大宇宙對 GFS／LITE 是多幾條邊，不是多一家公司（2026-09-17 實測：12 家裡有 3 家是這種）。"""
    ranking = _ranking_with_filtered([_row(1, "LITE")], [_filtered("LITE"), _filtered("3081.TWO")])
    out = build_basket_artifact(ranking=ranking, overviews={}, positions=None)
    by_ticker = {r["ticker"]: r for r in out["volume_rows"]}
    assert "already_in_moat_basket" in by_ticker["LITE"]["filter_reasons"]
    assert "already_in_moat_basket" not in by_ticker["3081.TWO"]["filter_reasons"]


def test_volume_candidates_have_no_ranking_and_no_top_pick() -> None:
    """這些邊是被排序權威濾掉的——它們沒有名次。自己排一個就是自建第二套評分（AGENTS 明禁）。"""
    from webapp.basket import VOLUME_ORDER_NOTE

    ranking = _ranking_with_filtered([], [_filtered("ZZZ"), _filtered("AAA")])
    out = build_basket_artifact(ranking=ranking, overviews={}, positions=None)
    assert [r["ticker"] for r in out["volume_rows"]] == ["AAA", "ZZZ"], "字母序"
    assert "volume_top_pick" not in out, "量的候選刻意沒有首選"
    assert all("rank" not in r for r in out["volume_rows"]), "沒有名次就不要假裝有"
    assert out["volume_filter"]["order_note"] == VOLUME_ORDER_NOTE


def test_missing_criteria_are_said_out_loud() -> None:
    """D11 的覆蓋厚薄與瓶頸業務占營收今天沒有資料源——**明說，不假裝條件已經全上**（INV-3）。"""
    out = build_basket_artifact(ranking=_ranking_with_filtered([], [_filtered("X")]),
                                overviews={}, positions=None)
    missing = out["volume_filter"]["missing_criteria"]
    assert len(missing) == 2 and any("覆蓋厚薄" in m for m in missing)


def test_the_bet_contract_applies_to_the_second_universe_too() -> None:
    """Q2 的「有賭注 或 Abstention」對量的候選一樣成立——換個宇宙不換契約。"""
    ranking = _ranking_with_filtered([], [_filtered("A"), _filtered("B")])
    ov = {"payoff": {"status": "available", "absence_kind": None, "simple": {"value": 2.5}},
          "brief": {"our_bet": {"value": None}}}
    out = build_basket_artifact(ranking=ranking, overviews={"A": ov}, positions=None)
    by_ticker = {r["ticker"]: r for r in out["volume_rows"]}
    assert by_ticker["A"]["bet_state"] == "bet" and by_ticker["B"]["bet_state"] == "unanswered"
    assert out["volume_bet_ledger"]["unanswered"] == 1 and out["volume_bet_ledger"]["owed"] == ["B"]
