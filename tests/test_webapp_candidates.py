"""候選狀態板的 state artifact（Phase 3 Step 3.6）：契約、fake payload（給請求路徑測試用）、CLI 旗標、路由。"""
from __future__ import annotations

from datetime import datetime, timezone

from starlette.testclient import TestClient

from webapp.api import create_app
from webapp.contracts import STATE_KINDS, validate_state_artifact
from webapp.materialize import build_candidates_artifact
from webapp.store import StateArtifactStore

_ROW = {"ticker": "AXTI", "company_id": "co:axt", "brief_id": "ib_x", "record_version": "investor-brief/v2",
        "declared": "priced_wait", "declared_label": "已定價等回落", "derived": "priced_wait", "group": "priced_wait",
        "side": None, "reason": "貴", "preconditions": [], "rewrite": [],
        "edge": {"state": "edge", "label": "邊緣", "reasons": ["within_edge"], "market_cap_usd": 4.8e9, "analyst_count": 5,
                 "market_cap_label": "4.8B USD"},
        "held_source": None, "holdings_verified": True,
        "rides": [{"node": "mat:inp_substrate", "unit": "layer", "reading_id": "sr_x", "kind": "volume", "status": "current"}],
        "watch": {"watch_id": "ew_0148", "status": "active", "until": "2026-11-13", "expires": "2027-01-15"},
        "since": "2026-09-29T05:48:00+00:00", "stall_days": 0,
        "three_words": {"will_it_die": "黃（灰 1）", "priced_in": "是", "in_numbers": "是"}, "note": None}


def fake_candidates_payload(holdings: dict | None = None) -> dict:
    board = {
        "today": "2026-09-29",
        "groups": {"open": [], "missing": [], "priced_wait": [dict(_ROW)], "pass": [], "held": []},
        "side_groups": {"not_multiple": [], "edge_unmeasurable": [], "legacy": [], "precondition_failed": []},
        "counts": {"open": 0, "missing": 0, "priced_wait": 1, "pass": 0, "held": 0, "not_multiple": 0,
                   "edge_unmeasurable": 0, "legacy": 0, "precondition_failed": 0, "no_narrative": 2},
        "oldest_stall_days": {"open": None, "missing": None, "priced_wait": 0},
        "holdings": holdings if holdings is not None else {
            "status": "ok", "reason": None, "unresolved": ["7803.T"], "ignored": [], "ignored_problem": None,
            "beta_excluded": 3, "zero_shares": 0},
        "narrative_rewrite": [],
        "ledger": {"present": True, "tickers": 3, "parse_errors": 0, "parse_error_examples": []},
        "rollup": {"universe": 3, "lines": {},
                   "priced_in_own": {"valued": 1, "absent": {"upstream_unavailable": 2}, "absent_total": 2},
                   "in_numbers": {"valued": 2, "absent": {"upstream_unavailable": 1}, "absent_total": 1},
                   "wipeout": {"companies": 3, "lamps": {"red": 1, "amber": 4, "green": 3, "unlit": 4},
                               "unlit_by_kind": {"insufficient_evidence": 1, "not_yet_recorded": 3},
                               "red_tickers": ["COHR"], "all_four_non_grey": 0},
                   "not_read": {"n": 0, "tickers": [], "reasons": {}},
                   "edge": {"edge": 2, "not_edge": 1}},
        "universe": ["AXTI", "COHR", "LITE"],
        "no_narrative": [
            {"ticker": "COHR", "company_id": "co:coherent",
             "three_words": {"will_it_die": "紅", "priced_in": "未答", "in_numbers": "未答"}},
            {"ticker": "LITE", "company_id": "co:lumentum",
             "three_words": {"will_it_die": "黃（灰 1）", "priced_in": "未答", "in_numbers": "未答"}},
        ],
    }
    return build_candidates_artifact(board, generated_at=datetime(2026, 9, 29, tzinfo=timezone.utc))


def test_candidates_is_a_registered_kind_and_the_payload_validates() -> None:
    assert "candidates" in STATE_KINDS
    payload = fake_candidates_payload()
    assert validate_state_artifact("candidates", payload) is payload
    assert payload["counts"]["open"] == 0                              # 0 也印
    assert any("不是排序" in s for s in payload["this_is_not"])


def test_building_the_fake_does_not_preload_io_modules_the_request_path_sentinel_watches() -> None:
    """3.6 審查（評審 c0）：fixture 若經 `alpha.providers` 組 payload，會在哨兵取 `before` 之前就把 engine_c／
    yfinance／requests 載進來，請求路徑測試的「不得載入模型／IO」哨兵變瞎（通過與失效同形，L13）。
    用乾淨的直譯器量：只建這份 fake，不得載入任何一個被監看的模組。"""
    import subprocess
    import sys
    from pathlib import Path

    from test_webapp_request_path import FORBIDDEN_RUNTIME_MODULES

    root = Path(__file__).resolve().parents[1]
    code = ("import sys; sys.path[:0] = [r'%s', r'%s']; before = set(sys.modules); "
            "from test_webapp_candidates import fake_candidates_payload; fake_candidates_payload(); "
            "print('\\n'.join(sorted(set(sys.modules) - before)))" % (root, root / "tests"))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=root, check=True).stdout
    # 基準：既有的五份 state fake 都經 `webapp.materialize` 組 payload，那一個本來就會被預載（既有盲點，§14）；
    # 這條守的是**不得多預載**任何 IO／模型模組（engine_c、yfinance、requests、sqlite3、neo4j…）。
    loaded = [m for m in out.split() if m != "webapp.materialize"
              and any(m == f or m.startswith(f + ".") for f in FORBIDDEN_RUNTIME_MODULES)]
    assert not loaded, f"fake payload 預載了哨兵在看的模組：{loaded}"


def test_the_cli_flag_matches_the_kind() -> None:
    from webapp.__main__ import _STATE_FLAGS

    assert "candidates" in _STATE_FLAGS


def test_the_route_serves_the_artifact_verbatim(tmp_path) -> None:
    StateArtifactStore(tmp_path / "state").write(fake_candidates_payload())
    client = TestClient(create_app(tmp_path))
    body = client.get("/api/v1/candidates").json()
    assert body["kind"] == "candidates" and body["groups"]["priced_wait"][0]["ticker"] == "AXTI"
    missing = TestClient(create_app(tmp_path / "empty")).get("/api/v1/candidates")
    assert missing.status_code == 503 and "可開為 0" in missing.json()["error"]["note"]


def test_materialize_candidates_keeps_an_explicit_empty_universe(monkeypatch, tmp_path) -> None:
    """`tickers=[]`＝指定了、而且是空的；不得悄悄換成預設目錄（`--dir` 指到別處時會讀到真實清單）。"""
    import alpha.providers.candidates as cand
    from webapp import materialize as mat
    from webapp.store import ArtifactStore

    seen = []

    def fake_load(universe, context=None, structure=None):
        seen.append(list(universe))
        payload = fake_candidates_payload()
        return {k: payload[k] for k in ("groups", "side_groups", "counts", "oldest_stall_days", "holdings",
                                        "narrative_rewrite", "ledger", "rollup", "universe", "today")}

    monkeypatch.setattr(cand, "load_board", fake_load)
    monkeypatch.setattr(mat, "_graph_node_names", lambda ids: {})          # 測試不連真的圖
    monkeypatch.setattr(ArtifactStore, "tickers", lambda self: ["SHOULD_NOT_BE_USED"])
    mat.materialize_candidates(tickers=[], store=StateArtifactStore(tmp_path))
    mat.materialize_candidates(tickers=None, store=StateArtifactStore(tmp_path))
    assert seen == [[], ["SHOULD_NOT_BE_USED"]]


def test_the_no_narrative_list_travels_with_the_board_and_counts_as_cognition() -> None:
    """2026-09-30：不上板的那幾檔照抄進 artifact（計數旁邊列得出是誰）；燈變色＝認知變了，freshness 跟著變。"""
    payload = fake_candidates_payload()
    assert [r["ticker"] for r in payload["no_narrative"]] == ["COHR", "LITE"]
    assert payload["counts"]["no_narrative"] == len(payload["no_narrative"])
    board = {k: v for k, v in payload.items()}
    board["no_narrative"] = [dict(payload["no_narrative"][0], three_words={"will_it_die": "黃", "priced_in": "未答",
                                                                           "in_numbers": "未答"}),
                             payload["no_narrative"][1]]
    again = build_candidates_artifact(board, generated_at=datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert again["freshness_identity"] != payload["freshness_identity"]


def test_frontend_lists_no_narrative_tickers_and_says_how_to_get_on_the_board() -> None:
    """2026-10-07：清單住首頁「沒有敘事」那一組（`alpha.candidates.LIST_GROUPS`）；候選板只留一句與連結（重複的摺疊拿掉）。"""
    from pathlib import Path

    from alpha.candidates import LIST_GROUPS

    source = (Path(__file__).resolve().parents[1] / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "沒有敘事、不上板" in source and "要讓一檔上板，路是研究它、寫敘事" in source
    assert "首頁「沒有敘事」那一組" in source
    assert "no_narrative" in LIST_GROUPS                                   # 首頁真的有那一組（不是連到空的地方）


def test_board_rides_get_node_names_from_the_graph_and_fall_back_to_ids(monkeypatch) -> None:
    """候選板「押在哪一格」補節點名（圖裡的 name）；圖讀不到就不補（畫面照印 ID）、不擋組板。"""
    from webapp import materialize as mat

    payload = fake_candidates_payload()
    board = {"groups": payload["groups"], "side_groups": payload["side_groups"]}
    monkeypatch.setattr(mat, "_graph_node_names", lambda ids: {"mat:inp_substrate": "Indium Phosphide (InP) substrate"})
    mat._attach_ride_node_names(board)
    assert board["groups"]["priced_wait"][0]["rides"][0]["node_name"] == "Indium Phosphide (InP) substrate"

    fresh = fake_candidates_payload()
    board = {"groups": fresh["groups"], "side_groups": fresh["side_groups"]}

    def down(ids):
        raise RuntimeError("neo4j down")

    monkeypatch.setattr(mat, "_graph_node_names", down)
    mat._attach_ride_node_names(board)
    assert "node_name" not in board["groups"]["priced_wait"][0]["rides"][0]
