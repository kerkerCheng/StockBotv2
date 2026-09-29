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


def fake_candidates_payload() -> dict:
    board = {
        "today": "2026-09-29",
        "groups": {"open": [], "missing": [], "priced_wait": [dict(_ROW)], "pass": [], "held": []},
        "side_groups": {"not_multiple": [], "edge_unmeasurable": [], "legacy": [], "precondition_failed": []},
        "counts": {"open": 0, "missing": 0, "priced_wait": 1, "pass": 0, "held": 0, "not_multiple": 0,
                   "edge_unmeasurable": 0, "legacy": 0, "precondition_failed": 0, "no_narrative": 2},
        "oldest_stall_days": {"open": None, "missing": None, "priced_wait": 0},
        "holdings": {"status": "ok", "reason": None, "unresolved": ["TYO:7803"], "beta_excluded": 3, "zero_shares": 0},
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
