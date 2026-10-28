"""「成績單」頁（2026-10-28 使用者照推薦：追蹤表與帳號計分表併成一頁；brainstorm 2026-10-28 定案 7）。

守四件事：
1. **照我們說過的話分組、組只有一份**：組＝敘事能宣告的四種候選狀態（`CANDIDATE_STATES_DECLARABLE`，0 也印）；
   字彙外或沒記下的狀態照列在後面——每一列恰好一組，不會從成績單安靜消失（INV-3）。
2. **不排、不算**：組內照 artifact 的列序（代號），不照報酬排（G1）；路由不算任何組平均；「現在」的狀態字跟著字彙走
   （撤回、舊版這兩個出口的標籤住 `alpha.candidates.PAPER_STATE_EXITS`，L16）。
3. **讀不到的分開說**：positions 讀不到＝503；計分表／讀圖讀不到＝那一段寫讀不到、別段照出；字彙表沒有分組＝照出現的狀態分、說原因。
4. **畫面**：導覽列 5 頁、`#/account-scorecard` 落到成績單那一段、計分表一帳號一列且三個基準並排、點圖不排序。
"""
from __future__ import annotations

import re
from pathlib import Path

from starlette.testclient import TestClient

from alpha.candidates import GROUP_LABELS, PAPER_STATE_EXITS
from alpha.narrative.contracts import CANDIDATE_STATES_DECLARABLE
from webapp.api import create_app
from webapp.materialize import write_vocabularies
from webapp.store import ArtifactStore, StateArtifactStore

from test_webapp_positions import fake_positions_payload

ROOT = Path(__file__).resolve().parents[1]


def _paper_row(ticker: str, anchor: str | None, current: str, ret: float | None) -> dict:
    return {"lane": "paper", "ticker": ticker, "company_id": f"co:{ticker.lower()}", "anchor_date": "2026-10-05",
            "anchor_state": anchor, "current_state": current, "absolute_return": ret, "pre_anchor_return": None,
            "excess_QQQ": None, "note": [] if ret is not None else ["還量不到"]}


PAPER = [
    _paper_row("AAA", "pass", "retracted", -0.2),
    _paper_row("BBB", "missing", "missing", 0.3),
    _paper_row("CCC", "pass", "pass", 0.1),
    _paper_row("DDD", "missing", "legacy_v1", None),
    _paper_row("EEE", "weird_state", "pass", 0.0),
    _paper_row("FFF", None, "retracted", None),
]


PREDICTIONS = {
    "counts": {"held": 1, "open": 0, "rewritten": 0, "non_assertion": 1}, "wrong_total": 1,
    "rows": [
        {"node": "mat:inp_epiwafer", "unit": "layer", "kind": "volume", "outcome": "held", "wrong_kind": None},
        {"node": "mat:zzz_unlabelled", "unit": "socket", "kind": "moat", "outcome": "reversed", "wrong_kind": "emerged_later"},
        {"node": "comp:x", "unit": "layer", "kind": "neither", "outcome": "non_assertion", "wrong_kind": None},
        {"node": "comp:y", "unit": "layer", "kind": "volume", "outcome": "mystery", "wrong_kind": None},
    ],
}


def _client(tmp_path, *, vocab: bool = True, scorecard: bool = True, readings: bool = True) -> TestClient:
    lanes = {"live": {"n": 0, "rows": [], "empty_text": "還沒有列"},
             "paper": {"n": len(PAPER), "measured": 4, "rows": PAPER, "measurement_start": "2026-10-05"}}
    state = StateArtifactStore(tmp_path / "state")
    state.write(fake_positions_payload(lanes=lanes))
    if vocab:
        write_vocabularies(ArtifactStore(tmp_path))
    if scorecard:
        from test_account_scorecard import fake_scorecard_payload
        state.write(fake_scorecard_payload(tmp_path / "scorecard"))
    if readings:
        from webapp.structure_readings import build_structure_readings_artifact
        state.write(build_structure_readings_artifact(rows=[], predictions=PREDICTIONS))
    return TestClient(create_app(tmp_path))


# ---------------------------------------------------------------------------
# 1. 照我們說過的話分組
# ---------------------------------------------------------------------------

def test_claims_partition_every_paper_row_and_the_declared_four_always_print(tmp_path) -> None:
    body = _client(tmp_path).get("/api/v1/report-card").json()
    claims = body["claims"]
    keys = [c["key"] for c in claims]
    assert keys[:4] == list(CANDIDATE_STATES_DECLARABLE)                      # 宣告得出的四種在前，0 也印
    assert [c["label"] for c in claims[:4]] == [GROUP_LABELS[k] for k in CANDIDATE_STATES_DECLARABLE]
    by = {c["key"]: c for c in claims}
    assert by["open"]["n"] == 0 and by["open"]["rows"] == []                 # 我們沒說過可開＝0，不是沒資料
    assert sorted(t for c in claims for t in (r["ticker"] for r in c["rows"])) == sorted(r["ticker"] for r in PAPER)
    assert "weird_state" in by and by["weird_state"]["declared"] is False    # 字彙外：照列，不消失
    assert by["unrecorded"]["rows"][0]["ticker"] == "FFF"                     # 沒記下：自己一組
    assert by["pass"]["n"] == 2 and by["pass"]["measured"] == 2
    assert by["missing"]["n"] == 2 and by["missing"]["measured"] == 1


# ---------------------------------------------------------------------------
# 2. 不排、不算
# ---------------------------------------------------------------------------

def test_group_rows_keep_the_artifact_order_and_no_average_is_computed(tmp_path) -> None:
    body = _client(tmp_path).get("/api/v1/report-card").json()
    by = {c["key"]: c for c in body["claims"]}
    assert [r["ticker"] for r in by["pass"]["rows"]] == ["AAA", "CCC"]       # 照 artifact 的列序，不照報酬（−20% 在 +10% 前）
    for c in body["claims"]:
        assert not any(k in c for k in ("mean", "median", "average", "rank")), c["key"]


def test_current_state_labels_follow_the_vocabulary(tmp_path) -> None:
    body = _client(tmp_path).get("/api/v1/report-card").json()
    rows = {r["ticker"]: r for c in body["claims"] for r in c["rows"]}
    assert rows["AAA"]["current_label"] == PAPER_STATE_EXITS["retracted"]
    assert rows["DDD"]["current_label"] == PAPER_STATE_EXITS["legacy_v1"]
    assert rows["CCC"]["current_label"] == GROUP_LABELS["pass"] and rows["BBB"]["anchor_label"] == GROUP_LABELS["missing"]


def test_predictions_group_by_outcome_and_only_the_unjudged_collapse_to_a_count(tmp_path) -> None:
    """圖預測對錯表：組序照預測表自己的字彙、字彙外的照列在後面；不算對錯的由 `UNJUDGED_OUTCOMES` 宣告（L16）；
    層名照中文名表、沒有就印代號（不猜）；有錯的那一組帶 `wrong`（畫面預設打開）。"""
    from alpha.structure_reading.predictions import OUTCOMES, UNJUDGED_OUTCOMES
    from webapp.materialize import node_labels_zh

    body = _client(tmp_path).get("/api/v1/report-card").json()
    groups = body["prediction_groups"]
    keys = [g["key"] for g in groups]
    assert keys == [k for k in OUTCOMES if k in {"held", "reversed", "non_assertion"}] + ["mystery"]
    by = {g["key"]: g for g in groups}
    assert {k for k, g in by.items() if not g["judged"]} == {k for k in by if k in UNJUDGED_OUTCOMES}
    assert by["reversed"]["wrong"] is True and by["held"]["wrong"] is False
    held = by["held"]["rows"][0]
    assert held["node_label"] == (node_labels_zh().get("mat:inp_epiwafer") or "mat:inp_epiwafer")
    assert by["reversed"]["rows"][0]["node_label"] == "mat:zzz_unlabelled"            # 沒有中文名：印代號，不猜
    assert held["kind_label"] != "volume"                                              # 讀法印中文
    assert sum(g["n"] for g in groups) == len(PREDICTIONS["rows"])                     # 一份不少


def test_the_outcome_script_only_emits_exits_the_vocabulary_names() -> None:
    """「現在」的出口由 outcome 腳本寫——它寫的每一個出口都必須在 `PAPER_STATE_EXITS` 裡（否則成績單印出英文鍵）。"""
    source = (ROOT / "scripts" / "outcome_if_settled_today.py").read_text(encoding="utf-8")
    block = source.split("current_state = (", 1)[1].split("\n        company_id", 1)[0]
    emitted = set(re.findall(r'"([a-z_0-9]+)"', block))
    assert emitted and emitted <= set(PAPER_STATE_EXITS), emitted


# ---------------------------------------------------------------------------
# 3. 讀不到的分開說
# ---------------------------------------------------------------------------

def test_missing_pieces_are_absences_and_missing_positions_is_503(tmp_path) -> None:
    body = _client(tmp_path, scorecard=False, readings=False).get("/api/v1/report-card").json()
    assert body["absences"]["account_scorecard"]["kind"] == "upstream_unavailable"
    assert body["absences"]["structure_readings"]["kind"] == "upstream_unavailable"
    assert body["claims"] and body["scorecard"] is None
    empty = TestClient(create_app(tmp_path / "nothing"))
    assert empty.get("/api/v1/report-card").status_code == 503


def test_without_the_vocabulary_groups_follow_the_data_and_say_why(tmp_path) -> None:
    body = _client(tmp_path, vocab=False).get("/api/v1/report-card").json()
    assert body["claims_absence"]["kind"] == "vocabulary_unavailable"
    assert {c["key"] for c in body["claims"]} == {"pass", "missing", "weird_state", "unrecorded"}   # 0 的組這次不印
    assert sum(c["n"] for c in body["claims"]) == len(PAPER)


# ---------------------------------------------------------------------------
# 4. 畫面
# ---------------------------------------------------------------------------

def test_frontend_report_card_page() -> None:
    static = ROOT / "webapp" / "static"
    source = (static / "app.js").read_text(encoding="utf-8")
    html = (static / "index.html").read_text(encoding="utf-8")
    labels = re.findall(r'<a href="#/[^"]*" data-view="[^"]+"[^>]*>([^<]+)</a>', html)
    assert labels == ["公司", "每日", "圖", "成績單", "資產配置"], labels
    assert 'href="#/account-scorecard"' not in html and 'href="#/positions"' in html
    assert "target === 'account-scorecard'" in source and "renderReportCard('accounts')" in source
    assert "function renderScorecard" not in source and "function renderPositions(" not in source
    assert "function renderReportCard(" in source and "function claimDots(" in source
    triple = source.split("function excessTriple(", 1)[1].split("\nfunction ", 1)[0]
    assert "benches.forEach" in triple                                         # 三個基準並排，不只印一個
    assert "'theme_cohort'" in source.split("function scorecardAccounts(", 1)[1].split("\nfunction ", 1)[0]
    assert ".sort(" not in source
