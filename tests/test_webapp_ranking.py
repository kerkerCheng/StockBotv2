"""`ranking` state artifact：**照抄 `rank_bottlenecks()` 的輸出**，不重排、不重算。

這裡守的是 B1 的驗收條件：APP 排序表與 `python -m query.bottleneck` 逐列 diff 0。
所有 fixture 離線（不連 Neo4j）：這一層的責任是「一份 rank_bottlenecks 結果 → 一份 artifact」，
綁在真實資料上只會讓測試在 DB 沒開時變成綠色的空跑（L13-2）。
"""
from __future__ import annotations

import json
import types
from datetime import date
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from query.bottleneck import (
    SORT_KEY_DESCRIPTIONS, known_limitations, project_assertions_as_of, rank_bottlenecks,
    render_markdown, structural_gap_notes,
)
from webapp.api import create_app
from webapp.contracts import (
    STATE_KINDS, STATE_SCHEMA_VERSIONS, ArtifactUnavailable, validate_state_artifact,
)
from webapp.materialize import build_ranking_artifact, materialize_view
from webapp.store import ArtifactStore, StateArtifactStore, resolve_state_dir

from test_bottleneck_ranking import _FakeRegistry
from test_webapp_materialize import fake_view

ROOT = Path(__file__).resolve().parents[1]

#: 測試自己的產業對照：不讀 config，避免 config 一改這裡就跟著動。
_SECTOR_MAP = {
    "sectors": {"AI 光互連／CPO": ["tech:ai_switch"], "記憶體": ["tech:hbm"]},
    "correlation_notes": ["AI 光互連與記憶體共享同一個 AI capex 需求錨。"],
}


class _LabelRegistry(_FakeRegistry):
    """多一個 `company()`：display_name 只有 Coherent 有；AXT 只有 name；lumentum 不在 registry。"""

    def company(self, company_id):
        for c in self._c:
            if c.company_id == company_id:
                display = {"co:coherent": "Coherent Corp."}.get(company_id)
                return types.SimpleNamespace(display_name=display, name=c.name)
        return None


def _attrs(**kw):
    return json.dumps({k: v for k, v in kw.items() if v is not None})


def _rows():
    return [
        # 可行動第 1：外部印證（origin 是 NVIDIA ≠ src）、sub 5、sole、距錨 2 跳
        {"src": "co:coherent", "relation": "supplies_to", "dst": "co:nvidia", "confidence": 0.9,
         "attributes": _attrs(substitutability=5, sole_source=True, qualification_status="qualified"),
         "origin": "NVIDIA", "source_doc_id": "doc_nvda_call", "published_at": "2026-06-01"},
        {"src": "co:nvidia", "relation": "supplies_to", "dst": "tech:ai_switch", "confidence": 0.9,
         "attributes": _attrs(), "origin": "NVIDIA", "source_doc_id": "doc_nvda_call",
         "published_at": "2026-06-01"},
        # 純結構第 1：sub 5、sole、直接接錨（1 跳）——但 origin 解析不到 registry，證據最弱
        {"src": "co:lumentum", "relation": "supplies_to", "dst": "tech:ai_switch", "confidence": 0.8,
         "attributes": _attrs(substitutability=5, sole_source=True, qualification_status="designed_in"),
         "origin": "Lumentum", "source_doc_id": "doc_lite_pr", "published_at": "2026-05-01"},
        # sole_source **未填**（None）——三態要活著；origin 是 Coherent ≠ src → 外部印證
        {"src": "co:axt", "relation": "supplies_to", "dst": "co:coherent", "confidence": 0.8,
         "attributes": _attrs(substitutability=4, qualification_status="qualified"),
         "origin": "Coherent", "source_doc_id": "doc_cohr_10k", "published_at": "2026-04-01"},
    ]


def fake_result(rows=None):
    return rank_bottlenecks(rows if rows is not None else _rows(), _LabelRegistry())


def fake_ranking_payload(rows=None, **kw):
    """一份最小但形狀正確的 `ranking` artifact（給本檔與 request-path 證明共用）。"""
    return build_ranking_artifact(fake_result(rows), registry=_LabelRegistry(),
                                  sector_map=_SECTOR_MAP, **kw)


# ---------------------------------------------------------------------------
# 照抄：順序、每一格、三態
# ---------------------------------------------------------------------------

def test_rows_are_the_authority_output_verbatim_and_in_order() -> None:
    """B1 驗收：逐列 diff 0。artifact 的每一列、每一格都等於 rank_bottlenecks 的輸出。"""
    result = fake_result()
    payload = build_ranking_artifact(result, registry=_LabelRegistry(), sector_map=_SECTOR_MAP)
    assert len(result["rows"]) == 3
    assert [r["company_id"] for r in payload["rows"]] == [r["company_id"] for r in result["rows"]]
    assert [r["rank"] for r in payload["rows"]] == [1, 2, 3]
    for got, src in zip(payload["rows"], result["rows"]):
        for key, value in src.items():
            assert got[key] == value, key
    assert [r["company_id"] for r in payload["structural_rows"]] == [
        r["company_id"] for r in result["structural_rows"]]
    for got, src in zip(payload["structural_rows"], result["structural_rows"]):
        for key, value in src.items():
            assert got[key] == value, key


def test_numbers_are_copied_not_recomputed() -> None:
    """空跑檢查：若 materializer 自己算了什麼，這裡的 `is` 就不會成立。"""
    result = fake_result()
    payload = build_ranking_artifact(result, registry=_LabelRegistry(), sector_map=_SECTOR_MAP)
    for got, src in zip(payload["rows"], result["rows"]):
        for key in ("substitutability", "confidence", "documents", "demand_hops", "lead_time_weeks",
                    "sole_source", "evidence"):
            assert got[key] is src[key], key
        # 容器（chain／sources）會被 redact_private_paths 重建——那是設計，比內容不比身分。
        assert got["chain"] == src["chain"] and got["sources"] == src["sources"]
    assert payload["coverage"] == result["coverage"]


def test_sole_source_three_state_survives() -> None:
    """None＝圖上沒人對這條邊發言過，**不是 False**。壓成 bool 是 2026-09-05 修掉的 bug。"""
    payload = fake_ranking_payload()
    states = {r["company_id"]: r["sole_source"] for r in payload["rows"]}
    assert states["co:coherent"] is True
    assert states["co:axt"] is None
    assert "null" in payload["vocab"]["sole_source_states"]
    assert "未填不是否" in payload["vocab"]["sole_source_states"]["null"]


def test_actionable_and_structural_orders_differ_as_documented() -> None:
    """兩份排序回答不同問題：可行動看證據（coherent 先），純結構不看（lumentum 先）。"""
    payload = fake_ranking_payload()
    assert [r["company_id"] for r in payload["rows"]] == ["co:coherent", "co:axt", "co:lumentum"]
    assert payload["structural_rows"][0]["company_id"] == "co:lumentum"
    assert payload["top_pick"]["company_id"] == "co:coherent"
    assert payload["top_pick"]["rank"] == 1
    assert "不是回測" in payload["top_pick"]["note"]


# ---------------------------------------------------------------------------
# 固定文字與判準只有一份（L16）
# ---------------------------------------------------------------------------

def test_limitations_and_notes_travel_with_the_data() -> None:
    result = fake_result()
    payload = build_ranking_artifact(result, registry=_LabelRegistry(), sector_map=_SECTOR_MAP)
    md = render_markdown(result)
    assert payload["limitations"] == known_limitations(result["coverage"])
    for text in payload["limitations"]:
        assert text in md
    for text in payload["notes"]["two_rankings"]:
        assert text in md
    assert payload["notes"]["structural_table"] in md
    assert payload["title"] in md
    assert payload["vocab"]["sort_keys"] == {k: list(v) for k, v in SORT_KEY_DESCRIPTIONS.items()}


def test_structural_gap_note_matches_markdown_rule() -> None:
    """落差註記（可行動名次比純結構低 ≥2）只有一份判準：markdown 與 artifact 同源。"""
    result = fake_result()
    payload = build_ranking_artifact(result, registry=_LabelRegistry(), sector_map=_SECTOR_MAP)
    md = render_markdown(result)
    notes = structural_gap_notes(result, top_n=len(result["structural_rows"]))
    assert [r["gap_note"] or "" for r in payload["structural_rows"]] == [gap for _, _, gap in notes]
    assert [r["actionable_rank"] for r in payload["structural_rows"]] == [rank for _, rank, _ in notes]
    gaps = [r["gap_note"] for r in payload["structural_rows"] if r["gap_note"]]
    assert gaps, "fixture 必須造出至少一個落差，否則本測試是空跑"
    for gap in gaps:
        assert gap in md


def test_sector_groups_are_indexes_not_copies() -> None:
    payload = fake_ranking_payload()
    ranks = {r["rank"] for r in payload["rows"]}
    assert payload["sectors"], "fixture 全部走到 tech:ai_switch，應有一組"
    for sector in payload["sectors"]:
        assert set(sector["actionable_ranks"]) <= ranks
        assert sector["actionable_count"] == len(sector["actionable_ranks"])
        assert "rows" not in sector          # 分組是索引，不是第二份資料
    assert payload["sectors"][0]["sector"] == "AI 光互連／CPO"
    assert payload["sectors"][0]["structural_first"]["company_id"] == "co:lumentum"
    assert payload["empty_sectors"] == ["記憶體"]      # configured 但零列 → 現形
    assert payload["notes"]["no_anchor_reading"] is None   # 沒有無錨列就不印那段
    assert payload["correlation_notes"] == _SECTOR_MAP["correlation_notes"]


def test_company_label_comes_from_registry_never_guessed() -> None:
    payload = fake_ranking_payload()
    labels = {r["company_id"]: r["company_label"] for r in payload["rows"]}
    assert labels["co:coherent"] == "Coherent Corp."   # display_name
    assert labels["co:axt"] == "AXT"                   # 退回 name
    assert labels["co:lumentum"] is None               # registry 沒有 → None，不從 ID 造名字


def test_empty_ranking_is_honest_not_silent() -> None:
    empty = build_ranking_artifact(
        {"rows": [], "structural_rows": [],
         "coverage": {"assertions": 0, "canonical_edges": 0, "edges_with_substitutability": 0,
                      "substitutability_coverage": 0.0, "edges_with_lead_time": 0,
                      "self_reported_share": 0.0, "duplicate_collapse": 0}},
        registry=_LabelRegistry(), sector_map=_SECTOR_MAP)
    assert empty["top_pick"] is None
    assert "排不出來" in empty["top_pick_absent_reason"]
    assert empty["empty_sectors"] == ["AI 光互連／CPO", "記憶體"]
    validate_state_artifact("ranking", empty)


# ---------------------------------------------------------------------------
# 契約：fail closed、兩個 digest
# ---------------------------------------------------------------------------

def test_state_kinds_are_a_closed_vocabulary() -> None:
    assert STATE_KINDS == ("ranking", "beta", "coverage", "watches")
    assert STATE_SCHEMA_VERSIONS["ranking"] == "stockbot-app/ranking/1"


def test_state_artifact_fails_closed() -> None:
    payload = fake_ranking_payload()
    assert validate_state_artifact("ranking", payload) is payload
    with pytest.raises(ArtifactUnavailable, match="未登記"):
        validate_state_artifact("positions", payload)
    with pytest.raises(ArtifactUnavailable, match="kind"):
        validate_state_artifact("beta", payload)          # 已登記的 kind，但檔名與內容不一致
    with pytest.raises(ArtifactUnavailable, match="kind"):
        validate_state_artifact("ranking", dict(payload, kind="coverage"))
    with pytest.raises(ArtifactUnavailable, match="schema"):
        validate_state_artifact("ranking", dict(payload, schema_version="stockbot-app/ranking/0"))
    with pytest.raises(ArtifactUnavailable, match="content_digest"):
        validate_state_artifact("ranking", dict(payload, rows=[]))
    with pytest.raises(ArtifactUnavailable, match="缺必要欄位"):
        validate_state_artifact("ranking", {k: v for k, v in payload.items() if k != "authority"})
    with pytest.raises(ArtifactUnavailable):
        validate_state_artifact("ranking", "not an object")


def test_freshness_identity_tracks_cognition_not_document_counts() -> None:
    """多讀一份講同一條邊的文件 → documents +1、content 變，但認知狀態不變（L12）。"""
    a = fake_ranking_payload()
    extra = dict(_rows()[0], source_doc_id="doc_other", published_at="2026-06-02")
    b = fake_ranking_payload(rows=_rows() + [extra])
    assert b["rows"][0]["documents"] == a["rows"][0]["documents"] + 1
    assert b["freshness_identity"] == a["freshness_identity"]
    assert b["content_digest"] != a["content_digest"]
    # 證據等級變了（lumentum 拿到客戶端 origin）→ 順序變 → 認知狀態變
    rows = _rows()
    rows[2] = dict(rows[2], origin="NVIDIA")
    c = fake_ranking_payload(rows=rows)
    assert c["freshness_identity"] != a["freshness_identity"]


def test_as_of_projection_counts_are_carried_not_dropped() -> None:
    projection = project_assertions_as_of(_rows(), date(2026, 5, 15))
    result = rank_bottlenecks(list(projection.rows), _LabelRegistry())
    payload = build_ranking_artifact(result, registry=_LabelRegistry(), sector_map=_SECTOR_MAP,
                                     as_of=date(2026, 5, 15), projection=projection)
    assert payload["as_of"] == "2026-05-15"
    assert payload["point_in_time"]["mode"] == "as_of"
    assert payload["point_in_time"]["excluded"] == {"published_after_as_of": 2, "undated": 0}
    assert payload["point_in_time"]["input_count"] == 4


# ---------------------------------------------------------------------------
# store
# ---------------------------------------------------------------------------

def test_state_store_round_trip(tmp_path) -> None:
    store = StateArtifactStore(tmp_path)
    payload = fake_ranking_payload()
    path = store.write(payload)
    assert path.name == "ranking.json" and path.parent == tmp_path
    assert not list(tmp_path.glob(".*.tmp"))
    got, fresh = store.read("ranking")
    assert got == payload and fresh.state == "fresh"
    assert store.kinds() == ["ranking"] and store.missing_kinds() == ["beta", "coverage", "watches"]
    with pytest.raises(ArtifactUnavailable, match="未登記"):
        store.read("positions")
    with pytest.raises(ArtifactUnavailable, match="尚未 materialize"):
        store.read("beta")
    with pytest.raises(ArtifactUnavailable):
        store.path_for("../ranking")


def test_state_store_reports_missing_and_broken_separately(tmp_path) -> None:
    store = StateArtifactStore(tmp_path)
    assert store.kinds() == [] and store.missing_kinds() == ["ranking", "beta", "coverage", "watches"]
    with pytest.raises(ArtifactUnavailable, match="尚未 materialize"):
        store.read("ranking")
    (tmp_path / "ranking.json").write_text('{"kind": "ranking", "rows": [', encoding="utf-8")
    rows = list(store.read_all())
    assert rows[0][0] == "ranking" and rows[0][1] is None and "半份" in rows[0][3]


def test_resolve_state_dir_has_one_rule(tmp_path, monkeypatch) -> None:
    assert resolve_state_dir(tmp_path, None) == tmp_path / "state"
    assert resolve_state_dir(tmp_path, tmp_path / "elsewhere") == tmp_path / "elsewhere"
    monkeypatch.setenv("STOCKBOT_APP_STATE_DIR", str(tmp_path / "env"))
    assert resolve_state_dir(None, None) == tmp_path / "env"


def test_analyst_store_does_not_see_the_state_subdir(tmp_path) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    StateArtifactStore(tmp_path / "state").write(fake_ranking_payload())
    assert ArtifactStore(tmp_path).tickers() == ["COHR"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    StateArtifactStore(tmp_path / "state").write(fake_ranking_payload())
    return TestClient(create_app(tmp_path))


def test_ranking_endpoint_serves_the_artifact_verbatim(client) -> None:
    body = client.get("/api/v1/ranking").json()
    payload = fake_ranking_payload()
    assert body["kind"] == "ranking"
    assert body["rows"] == payload["rows"]
    assert body["structural_rows"] == payload["structural_rows"]
    assert body["limitations"] == payload["limitations"]
    assert body["freshness"]["state"] == "fresh"
    assert body["correlation_warning"]
    assert body["analyst_view_tickers"] == ["COHR"]      # 只是列目錄，讓前端知道哪檔可點


def test_ranking_absent_is_503_with_remedy_and_never_rebuilt(tmp_path) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    client = TestClient(create_app(tmp_path))
    response = client.get("/api/v1/ranking")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["kind"] == "artifact_unavailable" and "materialize --ranking" in error["remedy"]
    assert not (tmp_path / "state" / "ranking.json").exists()


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_ranking_rejects_mutation_verbs(client, method: str) -> None:
    assert client.request(method, "/api/v1/ranking").status_code == 405


def test_meta_and_health_declare_the_state_kinds(client) -> None:
    meta = client.get("/api/v1/meta").json()
    assert "GET /api/v1/ranking" in meta["endpoints"]
    assert any("不重算排序" in s for s in meta["not_offered"])
    assert client.get("/api/v1/health").json()["state_kinds"] == ["ranking"]


def test_status_and_verify_commands_include_state(tmp_path, capsys) -> None:
    from webapp.__main__ import main
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    StateArtifactStore(tmp_path / "state").write(fake_ranking_payload())
    assert main(["status", "--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "ranking" in out and "可行動 3 條" in out
    assert main(["verify", "--dir", str(tmp_path)]) == 0
    assert "2/2" in capsys.readouterr().out
    assert main(["status", "--dir", str(tmp_path), "--format", "json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert [s["kind"] for s in doc["state"]] == ["ranking"]
    assert doc["state_missing"] == ["beta", "coverage", "watches"]


# ---------------------------------------------------------------------------
# 前端
# ---------------------------------------------------------------------------

def test_frontend_ranking_view_never_sorts_or_scores() -> None:
    """畫面只改資訊階層：不得重排、不得算分、不得補權重。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderRanking" in source
    assert ".sort(" not in source
    for token in ("weighted", "weights", "score =", "* 0."):
        assert token not in source, token
    assert "RANK_VOCAB.sole_source_states" in source     # 三態說明來自 artifact，不是前端自寫
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'href="#/ranking"' in html
