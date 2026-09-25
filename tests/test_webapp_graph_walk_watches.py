"""`graph_walk` 與 `watches` state artifact：照抄各自 authority 的輸出，不重新分類、不排序。

fixture 全部離線（不連 Neo4j、不讀真實 registry）：這一層的責任是「一份走圖結果 → 一份 artifact」，
綁在真實資料上只會讓測試在 DB 沒開時變成綠色的空跑（L13-2）。
⚠ 2026-09-26（Phase 2 Step 2.6）：本檔原為 `test_webapp_coverage_watches.py`；`coverage` kind 由 `graph_walk` 取代。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from engine_b.event_watch import is_stalled, wake_target, watch_detail
from query.coverage_gaps import bucketize, split_research_gaps
from webapp.api import create_app
from webapp.contracts import STATE_KINDS, ArtifactUnavailable, validate_state_artifact
from webapp.materialize import (
    build_graph_walk_artifact, build_watches_artifact, materialize_view,
)
from webapp.store import ArtifactStore, StateArtifactStore

from test_graph_walk import fake_coverage, run_walk
from test_webapp_materialize import fake_view

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# graph_walk
# ---------------------------------------------------------------------------

def fake_duplicate_buckets():
    """重複節點候選的假資料——用真實抓到的那一對（逐字是同一句話）當樣本。"""
    from query.duplicate_nodes import bucketize as dup_bucketize, pair_candidates

    quote = "our Reliant® product line offers new and refurbished non-leading edge products"
    rows = [
        {"node": "prod:reliant", "name": "Reliant", "abstraction_level": "equipment_epitaxy",
         "degree": 2, "quotes": [{"quote": quote, "locator": "10-K Business", "doc": "doc:1"}]},
        {"node": "prod:reliant_product_line", "name": "Reliant Product Line",
         "abstraction_level": "equipment_epitaxy", "degree": 3,
         "quotes": [{"quote": quote, "locator": "10-K MD&A", "doc": "doc:1"}]},
    ]
    return dup_bucketize(pair_candidates(rows), {}), len(rows)


def fake_walk_result(**overrides):
    buckets, total = fake_duplicate_buckets()
    overrides.setdefault("duplicate_buckets", buckets)
    overrides.setdefault("duplicate_node_total", total)
    return run_walk(**overrides)


def fake_graph_walk_payload(**kw):
    return build_graph_walk_artifact(fake_walk_result(), **kw)


def test_graph_walk_artifact_copies_every_type_and_adds_no_total() -> None:
    result = fake_walk_result()
    payload = fake_graph_walk_payload()
    assert [q["key"] for q in payload["questions"]] == [q["key"] for q in result["questions"]]
    assert payload["counts"] == {q["key"]: {"hit_n": q["hit_n"], "scope_n": q["scope_n"]}
                                 for q in result["questions"]}
    # 每型各自一格——artifact 上沒有任何加總欄位（plan §0 第 7 條）。
    assert not {"total", "hits_total", "nodes"} & set(payload) and not {"total"} & set(payload["counts"])
    assert payload["graph_nodes"] == result["graph_nodes"]
    assert payload["this_is_not"] == result["this_is_not"]


def test_duplicate_hits_keep_their_verbatim_on_both_sides() -> None:
    """L18：重複節點候選的逐字是這一型存在的全部理由——artifact 不得把它壓成 id。"""
    hit = next(q for q in fake_graph_walk_payload()["questions"] if q["key"] == "duplicate_node")["hits"][0]
    assert hit["pair"] == ["prod:reliant", "prod:reliant_product_line"]
    assert hit["left"]["quotes"][0]["quote"].startswith("our Reliant")
    assert hit["right"]["quote_count"] is None or hit["right"]["quotes"]


def test_product_noise_is_counted_but_never_a_research_question() -> None:
    """🔴 桶混了兩種東西：`prod:` 是抽取副產品，不得列為研究題目（alpha-status 的判準）。"""
    q = next(q for q in fake_graph_walk_payload()["questions"] if q["key"] == "no_supplier")
    assert [h["subject"] for h in q["hits"]] == ["tech:gap", "tech:isolated"]
    assert q["extra"]["product_noise"] == ["prod:noise"]


def test_split_is_a_prefix_match_not_a_judgement() -> None:
    real, noise = split_research_gaps(bucketize(fake_coverage())["research_gap"])
    assert {r["node"] for r in real} == {"tech:gap", "tech:isolated"}
    assert {r["node"] for r in noise} == {"prod:noise"}


def test_graph_walk_scope_limit_travels_with_the_data() -> None:
    payload = fake_graph_walk_payload()
    text = " ".join(payload["this_is_not"])
    assert "圖裡既有的節點" in text and "system-decompose" in text
    assert "不是排序" in text


def test_graph_walk_identity_tracks_who_is_hit_not_the_wording() -> None:
    a = fake_graph_walk_payload()
    result = fake_walk_result()
    reworded = dict(result, questions=[dict(q, hits=[dict(h, text=h["text"] + "（改字）") for h in q["hits"]])
                                      for q in result["questions"]])
    b = build_graph_walk_artifact(reworded)
    assert b["freshness_identity"] == a["freshness_identity"]
    assert b["content_digest"] != a["content_digest"]
    c = build_graph_walk_artifact(fake_walk_result(leads={}))
    assert c["freshness_identity"] != a["freshness_identity"]


# ---------------------------------------------------------------------------
# watches
# ---------------------------------------------------------------------------

def _watch(watch_id, kind, *, status="active", entities=(), consumed=(), poll=False,
           wake_lead=None, wake_pq2=None, expires="2026-12-31"):
    return {"watch_id": watch_id, "kind": kind, "status": status, "entities": list(entities),
            "consumed_entities": list(consumed), "poll": {"eligible": poll}, "created_at": "2026-08-31",
            "expires": expires, "wake_lead": wake_lead, "wake_pq2": wake_pq2,
            "query_hint": "hint" if poll else None}


def fake_watch_data():
    return {"watches": [
        _watch("ew_0001", "related_entity_signal", entities=["NVDA"], wake_lead="lead_a", poll=True),
        _watch("ew_0002", "related_entity_signal", entities=["AAOI"], consumed=["AAOI"], wake_pq2=134),
        _watch("ew_0003", "entity_filing_signal", entities=["TSM"], wake_lead="lead_b"),
        _watch("ew_0004", "fact_verification", status="fired", wake_lead="lead_c"),
        _watch("ew_0005", "date", status="expired", wake_pq2=81),
        _watch("ew_0006", "date", status="consumed", wake_pq2=80),
    ]}


def fake_backlog():
    return [
        {"lead_id": "lead_x", "title": "停滯的追源", "wake_state": "stalled", "trace_status": "partial",
         "expires": "2026-12-01", "next_trigger": "等某某財報"},
        {"lead_id": "lead_y", "title": "沒人在等的", "wake_state": "unwatched", "trace_status": "isolated_tier_3"},
        {"lead_id": "lead_z", "title": "還在等", "wake_state": "watching", "trace_status": "partial"},
    ]


def fake_watches_payload(**kw):
    return build_watches_artifact(
        fake_watch_data(), config={"enabled": True, "sweep_budget_per_run": 2, "min_recheck_days": 3},
        backlog=fake_backlog(), due=[fake_watch_data()["watches"][0]], **kw)


def test_counters_come_from_the_registry_not_recounted() -> None:
    from engine_b.event_watch import counters

    payload = fake_watches_payload()
    assert payload["counters"] == counters(fake_watch_data())
    assert payload["counters"]["active"] == 3
    assert payload["counters"]["stalled"] == 1
    assert payload["counters"]["fired_unconsumed"] == 1


def test_stalled_is_surfaced_as_its_own_group_not_buried() -> None:
    """停滯＝被動層不會再醒，規則要求當場處置——不能混在 active 裡看不見。"""
    payload = fake_watches_payload()
    assert [row["watch_id"] for row in payload["stalled"]] == ["ew_0002"]
    assert all(is_stalled(w) == (w["watch_id"] == "ew_0002")
               for w in fake_watch_data()["watches"] if w["status"] == "active")
    assert "停滯不等於死亡" in payload["notes"]["stalled"]


def test_detail_and_target_come_from_event_watch_not_a_second_table() -> None:
    payload = fake_watches_payload()
    source = {w["watch_id"]: w for w in fake_watch_data()["watches"]}
    for row in payload["active"]:
        assert row["detail"] == watch_detail(source[row["watch_id"]])
        assert row["target"] == wake_target(source[row["watch_id"]])
    assert payload["active"][0]["target"]["kind"] == "lead"
    assert payload["active"][1]["target"]["kind"] == "pq2"


def test_backlog_only_lists_what_needs_a_person() -> None:
    payload = fake_watches_payload()
    assert [row["lead_id"] for row in payload["trace_backlog"]["needs_attention"]] == ["lead_x", "lead_y"]
    assert payload["trace_backlog"]["total"] == 3
    assert "黑洞" in payload["trace_backlog"]["wake_state_labels"]["unwatched"]


def test_watches_artifact_is_read_only_by_construction() -> None:
    payload = fake_watches_payload()
    joined = " ".join(payload["this_is_not"])
    assert "不寫任何東西" in joined and "不喚醒" in joined


def test_watches_identity_ignores_last_checked() -> None:
    a = fake_watches_payload()
    data = fake_watch_data()
    data["watches"][0]["poll"]["last_checked"] = "2026-09-08"
    b = build_watches_artifact(data, config={"enabled": True, "sweep_budget_per_run": 2, "min_recheck_days": 3},
                               backlog=fake_backlog(), due=[])
    assert b["freshness_identity"] == a["freshness_identity"]
    data["watches"][2]["status"] = "fired"
    c = build_watches_artifact(data, config={"enabled": True, "sweep_budget_per_run": 2, "min_recheck_days": 3},
                               backlog=fake_backlog(), due=[])
    assert c["freshness_identity"] != a["freshness_identity"]


# ---------------------------------------------------------------------------
# 契約與 API
# ---------------------------------------------------------------------------

def test_both_kinds_are_registered_and_validate() -> None:
    # ⚠ 這一串刻意硬編：新增 state kind 就該讓這個測試紅一次，逼人確認
    # 「它的 CLI flag 加了嗎、materializer 有嗎、心跳／APP 讀得到嗎」。
    # 2026-09-22 Step 0a.2：basket／multi_year 退役，9 → 7。2026-09-23 Step 0b.3：ranking → structure_table。
    # 2026-09-26 Step 2.6：coverage → graph_walk（kind 數不變）。
    assert STATE_KINDS == ("structure_table", "beta", "graph_walk", "watches", "positions",
                           "structure_readings", "account_scorecard")
    for kind, payload in (("graph_walk", fake_graph_walk_payload()), ("watches", fake_watches_payload())):
        assert validate_state_artifact(kind, payload) is payload
        with pytest.raises(ArtifactUnavailable, match="content_digest"):
            validate_state_artifact(kind, dict(payload, title="改過了"))


@pytest.fixture()
def client(tmp_path):
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    store = StateArtifactStore(tmp_path / "state")
    store.write(fake_graph_walk_payload())
    store.write(fake_watches_payload())
    return TestClient(create_app(tmp_path))


def test_endpoints_serve_the_artifacts_verbatim(client) -> None:
    walk = client.get("/api/v1/graph-walk").json()
    assert walk["kind"] == "graph_walk" and walk["counts"] == fake_graph_walk_payload()["counts"]
    assert walk["questions"] == fake_graph_walk_payload()["questions"]
    # 舊路由已退役：不留別名（留著就是一條沒人用、卻仍放行的入口）。
    assert client.get("/api/v1/coverage").status_code == 404
    wat = client.get("/api/v1/watches").json()
    assert wat["kind"] == "watches" and wat["counters"] == fake_watches_payload()["counters"]
    assert wat["stalled"] == fake_watches_payload()["stalled"]


@pytest.mark.parametrize("kind", ["graph_walk", "watches"])
def test_absent_artifact_is_503_with_its_own_remedy(tmp_path, kind: str) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    route = kind.replace("_", "-")
    response = TestClient(create_app(tmp_path)).get(f"/api/v1/{route}")
    assert response.status_code == 503
    error = response.json()["error"]
    # 提示要印人能貼的旗標（連字號），不是 kind 名（底線）。
    assert error["state_kind"] == kind and f"materialize --{route}" in error["remedy"]
    assert not (tmp_path / "state" / f"{kind}.json").exists()


@pytest.mark.parametrize("kind", ["graph-walk", "watches"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_mutation_verbs_are_rejected(client, kind: str, method: str) -> None:
    assert client.request(method, f"/api/v1/{kind}").status_code == 405


def test_meta_declares_both(client) -> None:
    endpoints = client.get("/api/v1/meta").json()["endpoints"]
    assert "GET /api/v1/graph-walk" in endpoints and "GET /api/v1/watches" in endpoints
    assert "GET /api/v1/coverage" not in endpoints


def test_frontend_has_both_views_and_no_ranking_of_gaps() -> None:
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderGraphWalk" in source and "function renderWatches" in source
    assert "function renderCoverage" not in source
    for token in (".sort(", "優先度", "最重要", "建議先做"):
        assert token not in source, token
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'href="#/graph-walk"' in html and 'href="#/watches"' in html
    assert 'href="#/coverage"' not in html
