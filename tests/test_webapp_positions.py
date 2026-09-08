"""`positions` state artifact：照抄 outcome 腳本與 Decision Store 計數器，不重算、不重排語意。

守的是這一頁最容易被讀錯的兩件事：
① **兩種報酬的錨點語意不同**——shadow 以入圖日為錨，不含進場判斷，不構成選股能力的證據；
② **樣本效度先於數字**——錨點跨度短就不得視為 N 個獨立樣本。
fixture 離線（不連 yfinance、不開 Decision Store）。
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from webapp.api import create_app
from webapp.contracts import STATE_KINDS, ArtifactUnavailable, validate_state_artifact
from webapp.materialize import build_positions_artifact, materialize_view
from webapp.store import ArtifactStore, StateArtifactStore

from test_webapp_materialize import fake_view

ROOT = Path(__file__).resolve().parents[1]

_COUNTERS = {
    "eligible_cohorts": 21, "legacy_eligible_cohorts": 3, "total_cohorts": 28,
    "shadow_measurable_cohorts": 19, "shadow_anchored_cohorts": 28,
    "outcomes": 8, "measured_outcomes": 8, "live_choices": 1, "live_fills": 1,
    "duplicate_cohort_companies": 0, "orphan_cohorts": 9,
}


def _row(ticker, absolute, *, pre=None, excess=None, anchor="2026-08-18", current="2026-09-08"):
    return {"ticker": ticker, "company_id": f"co:{ticker.lower()}",
            "anchor_date": date.fromisoformat(anchor), "current_date": date.fromisoformat(current),
            "anchor_raw": 316.23, "anchor_ccy": "USD", "anchor_source": f"shadow@{anchor}",
            "current_raw": 281.86, "pre_anchor_return": pre, "absolute_return": absolute,
            "bench_QQQ": 0.002, "excess_QQQ": excess, "bench_SOXX": -0.02, "note": []}


def fake_results():
    return [
        _row("COHR", -0.109, pre=0.104, excess=-0.111),
        _row("AXTI", 0.442, pre=-0.39, excess=0.377, anchor="2026-07-28"),
        _row("SIVE.ST", None, pre=None, excess=None),      # 無報酬：不得被當成 0
    ]


def fake_live_rows():
    return [{"ticker": "COHR", "company_id": "co:cohr", "executed_at": date(2026, 8, 18),
             "price": 316.23, "shares": 10.0, "currency": "USD", "current": 281.86,
             "current_currency": "USD", "live_return": -0.1087, "shadow_return": -0.109}]


def fake_health(**kw):
    base = {"paired": 20, "judgment_anchors": 0, "first": date(2026, 7, 21), "last": date(2026, 9, 1),
            "span_days": 42, "weeks": 7, "span_warn_days": 90, "pre_median": 0.008,
            "post_median": 0.036, "chasing": 8, "chasing_tickers": ["COHR", "AEVA"],
            "pre_anchor_days": 30}
    base.update(kw)
    return base


_KEEP = object()


def fake_positions_payload(*, results=None, health=_KEEP, live_rows=None, **kw):
    rows = fake_results() if results is None else results
    return build_positions_artifact(
        rows, [{"ticker": "UNITREE", "cohort_id": "dc_x", "status": "unavailable"}],
        has_benchmark=True,
        aggregate={"n": 2, "absolute": 0.1665, "excess": 0.133, "benchmark": "QQQ",
                   "measured": 2, "total": len(rows)},
        health=fake_health() if health is _KEEP else health,
        live_rows=fake_live_rows() if live_rows is None else live_rows,
        paper_only=["AXTI", "SIVE.ST"], counters=_COUNTERS, benchmarks=("QQQ", "SOXX"), **kw)


# ---------------------------------------------------------------------------
# 照抄與序列化
# ---------------------------------------------------------------------------

def test_every_number_is_copied_and_dates_are_serialised() -> None:
    results = fake_results()
    payload = fake_positions_payload(results=results)
    by_ticker = {r["ticker"]: r for r in payload["rows"]}
    for src in results:
        got = by_ticker[src["ticker"]]
        assert got["absolute_return"] is src["absolute_return"]
        assert got["pre_anchor_return"] is src["pre_anchor_return"]
        assert got["excess_return"] is src["excess_QQQ"]
        assert got["anchor_date"] == src["anchor_date"].isoformat()
    assert payload["counters"]["eligible_cohorts"] == 21
    assert payload["aggregate"]["absolute"] == 0.1665


def test_rows_are_sorted_by_return_and_missing_sorts_last_not_as_zero() -> None:
    """沒有報酬的列不得被當成 0 排進中間——那會讓「沒量到」看起來像「持平」。"""
    payload = fake_positions_payload()
    assert [r["ticker"] for r in payload["rows"]] == ["AXTI", "COHR", "SIVE.ST"]
    assert payload["rows"][-1]["absolute_return"] is None


def test_two_anchor_semantics_are_stated_not_merged() -> None:
    payload = fake_positions_payload()
    assert "以**實際成交價**為錨點" in payload["notes"]["two_anchors"]
    assert "不構成選股能力的證據" in payload["notes"]["two_anchors"]
    live = payload["live"]["rows"][0]
    assert live["live_return"] != live["shadow_return"], "兩種報酬不得共用一個數字"
    joined = " ".join(payload["this_is_not"])
    assert "不是績效報告" in joined and "入圖日" in joined


def test_sample_validity_travels_with_the_numbers() -> None:
    """樣本效度必須跟著數字走——否則有效 n≈1 的觀測會被讀成 N 個獨立驗證。"""
    payload = fake_positions_payload()
    health = payload["anchor_health"]
    assert health["judgment_anchors"] == 0
    assert health["span_days"] < health["span_warn_days"]
    assert health["first"] == "2026-07-21" and health["last"] == "2026-09-01"
    assert "不得視為 N 個獨立樣本" in payload["notes"]["sample_validity"]
    assert "不是等更久" in payload["notes"]["judgment_anchor"]


def test_monitoring_gap_is_surfaced_not_assumed_covered() -> None:
    payload = fake_positions_payload()
    assert "不在" in payload["notes"]["monitoring"] and "event_search_requests" in payload["notes"]["monitoring"]


def test_identity_tracks_which_cohorts_are_measured_not_the_prices() -> None:
    a = fake_positions_payload()
    moved = fake_results()
    moved[0] = dict(moved[0], absolute_return=-0.5, excess_QQQ=-0.5)
    b = fake_positions_payload(results=moved)
    assert b["freshness_identity"] == a["freshness_identity"], "價格動了不算認知變了"
    assert b["content_digest"] != a["content_digest"]
    c = fake_positions_payload(live_rows=[])
    assert c["freshness_identity"] != a["freshness_identity"], "多／少一筆真實成交是認知變了"


def test_kind_registered_and_validates() -> None:
    assert "positions" in STATE_KINDS
    payload = fake_positions_payload()
    assert validate_state_artifact("positions", payload) is payload
    with pytest.raises(ArtifactUnavailable, match="content_digest"):
        validate_state_artifact("positions", dict(payload, rows=[]))


def test_no_health_section_when_nothing_is_paired() -> None:
    payload = fake_positions_payload(health=None)
    assert payload["anchor_health"] is None


# ---------------------------------------------------------------------------
# 抽取後的純函式：markdown 與 APP 讀同一份
# ---------------------------------------------------------------------------

def test_outcome_script_exposes_the_shared_pure_helpers() -> None:
    """`collect`／`equal_weight_aggregate`／`live_lane_rows`／`anchor_health` 是共用入口。

    ⚠ 它們存在的理由是 L16：同一份計算有第二個消費端時，兩邊要讀**同一個函式**——
    APP 端另算一份的話，第二份會立刻開始偏離。
    """
    source = (ROOT / "scripts" / "outcome_if_settled_today.py").read_text(encoding="utf-8")
    for fn in ("def collect(", "def equal_weight_aggregate(", "def live_lane_rows(", "def anchor_health("):
        assert fn in source, fn
    # main() 只剩「collect → render」，沒有第二份邏輯
    body = source.split("def main() -> int:", 1)[1].split("\ndef ", 1)[0]
    assert "collect(" in body and "_render(" in body
    assert "yf." not in body and "_load_shadows" not in body


def test_materialize_positions_is_read_only() -> None:
    """materialize 只呼叫 collect()，不呼叫 render——所以不 append 排序快照、不寫聚合檔。"""
    source = (ROOT / "webapp" / "materialize.py").read_text(encoding="utf-8")
    block = source.split("def materialize_positions(", 1)[1].split("\ndef ", 1)[0]
    assert "outcome.collect()" in block
    for forbidden in ("_render", "_append_ranking_snapshot", "_persist_aggregate"):
        assert forbidden not in block, f"materialize 不得觸發寫入：{forbidden}"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    StateArtifactStore(tmp_path / "state").write(fake_positions_payload())
    return TestClient(create_app(tmp_path))


def test_endpoint_serves_the_artifact_verbatim(client) -> None:
    body = client.get("/api/v1/positions").json()
    payload = fake_positions_payload()
    assert body["kind"] == "positions"
    assert body["rows"] == payload["rows"] and body["live"] == payload["live"]
    assert body["counters"] == payload["counters"]
    assert body["analyst_view_tickers"] == ["COHR"]


def test_absent_is_503_with_its_own_remedy(tmp_path) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    response = TestClient(create_app(tmp_path)).get("/api/v1/positions")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["state_kind"] == "positions" and "materialize --positions" in error["remedy"]
    assert "還沒有任何真實部位" in error["note"]


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_mutation_verbs_rejected(client, method: str) -> None:
    assert client.request(method, "/api/v1/positions").status_code == 405


def test_meta_declares_positions(client) -> None:
    assert "GET /api/v1/positions" in client.get("/api/v1/meta").json()["endpoints"]


def test_frontend_puts_sample_validity_before_the_numbers() -> None:
    """排版順序本身是判準：真實部位 → 樣本效度 → 計數器 → 聚合 → 逐檔。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderPositions" in source
    block = source.split("async function renderPositions", 1)[1]
    block = re.split(r"\\n(?:async )?function ", block, maxsplit=1)[0]
    validity = block.index("這批數字能證明什麼")
    aggregate = block.index("推薦籃子整體")
    assert validity < aggregate, "樣本效度必須排在聚合數字之前"
    for token in ("該買", "建議買", "績效", ".sort("):
        assert token not in block, token
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'href="#/positions"' in html
