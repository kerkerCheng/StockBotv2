"""`coverage` 與 `watches` state artifact：照抄各自 authority 的輸出，不重新分類、不排序。

fixture 全部離線（不連 Neo4j、不讀真實 registry）：這一層的責任是「一份掃描結果 → 一份 artifact」，
綁在真實資料上只會讓測試在 DB 沒開時變成綠色的空跑（L13-2）。
"""
from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from engine_b.event_watch import is_stalled, wake_target, watch_detail
from query.coverage_gaps import (
    BUCKET_NOTE, COVERAGE_TITLE, RESEARCH_QUESTION_TEMPLATE, bucketize, render_markdown,
    split_research_gaps,
)
from webapp.api import create_app
from webapp.contracts import STATE_KINDS, ArtifactUnavailable, validate_state_artifact
from webapp.materialize import (
    build_coverage_artifact, build_watches_artifact, materialize_view,
)
from webapp.store import ArtifactStore, StateArtifactStore

from test_webapp_materialize import fake_view

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# coverage
# ---------------------------------------------------------------------------

def _node(node, name, *, direct=(), indirect=(), status=None):
    from query.coverage_gaps import classify

    return {"node": node, "name": name, "direct": list(direct), "indirect": list(indirect),
            "status": status or classify(list(direct), list(indirect), node)}


def fake_scan():
    return [
        _node("tech:scale_up_cpo", "Scale-up CPO"),                                  # 真缺口
        _node("mat:exotic_substrate", "Exotic substrate"),                           # 真缺口
        _node("prod:tomahawk6", "Tomahawk 6"),                                       # 產品名詞（只計數）
        _node("tech:npo", "NPO", indirect=["co:lumentum"]),                          # 建模待補
        _node("tech:uhp_laser", "UHP laser", direct=["co:lumentum"]),                # 已覆蓋
        _node("policy:export_control", "Export control", status="concept"),          # 概念節點
    ]


def fake_coverage_payload(**kw):
    return build_coverage_artifact(fake_scan(), **kw)


def test_coverage_counts_and_buckets_are_the_scanner_output() -> None:
    rows = fake_scan()
    payload = build_coverage_artifact(rows)
    buckets = bucketize(rows)
    assert payload["counts"] == {
        "nodes": 6, "research_gap": 3, "modelling_gap": 1, "covered": 1, "concept": 1,
        "research_gap_real": 2, "research_gap_product_noise": 1,
    }
    assert [r["node"] for r in payload["modelling_gaps"]] == [r["node"] for r in buckets["modelling_gap"]]
    assert payload["title"] == COVERAGE_TITLE
    assert payload["notes"]["buckets"] == BUCKET_NOTE


def test_product_noise_is_counted_but_never_a_research_question() -> None:
    """🔴 桶混了兩種東西：`prod:` 是抽取副產品，不得列為研究題目（alpha-status 的判準）。"""
    payload = fake_coverage_payload()
    assert [r["node"] for r in payload["research_gaps"]] == ["tech:scale_up_cpo", "mat:exotic_substrate"]
    assert [r["node"] for r in payload["product_noise"]] == ["prod:tomahawk6"]
    assert all("question" in r for r in payload["research_gaps"])
    assert all("question" not in r for r in payload["product_noise"])
    assert payload["research_gaps"][0]["question"] == RESEARCH_QUESTION_TEMPLATE.format(node="tech:scale_up_cpo")


def test_split_is_a_prefix_match_not_a_judgement() -> None:
    real, noise = split_research_gaps(bucketize(fake_scan())["research_gap"])
    assert {r["node"] for r in real} == {"tech:scale_up_cpo", "mat:exotic_substrate"}
    assert {r["node"] for r in noise} == {"prod:tomahawk6"}


def test_fixed_text_has_one_home_and_the_markdown_prints_it() -> None:
    """限制文字與桶說明只有一份（L16）：markdown 與 artifact 同源。"""
    rows = fake_scan()
    payload = build_coverage_artifact(rows)
    md = "\n".join(render_markdown(rows))
    assert payload["title"] in md
    assert payload["notes"]["buckets"] in md


def test_coverage_scope_limit_travels_with_the_data() -> None:
    payload = fake_coverage_payload()
    # 兩個地方都要講：頁尾的「不是什麼」給看完的人，scope note 給只看首屏的人。
    assert "圖裡沒有的瓶頸不會出現在這裡" in " ".join(payload["this_is_not"])
    assert "從沒聽過的瓶頸" in payload["notes"]["scope"]
    assert "system-decompose" in payload["notes"]["scope"]


def test_coverage_identity_tracks_which_nodes_are_blank_not_their_names() -> None:
    a = fake_coverage_payload()
    rows = fake_scan()
    rows[0] = dict(rows[0], name="Scale-up CPO（改名）")
    b = build_coverage_artifact(rows)
    assert b["freshness_identity"] == a["freshness_identity"]
    assert b["content_digest"] != a["content_digest"]
    rows[0] = dict(rows[0], direct=["co:someone"], status="covered")
    c = build_coverage_artifact(rows)
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
    assert STATE_KINDS == ("ranking", "beta", "coverage", "watches")
    for kind, payload in (("coverage", fake_coverage_payload()), ("watches", fake_watches_payload())):
        assert validate_state_artifact(kind, payload) is payload
        with pytest.raises(ArtifactUnavailable, match="content_digest"):
            validate_state_artifact(kind, dict(payload, title="改過了"))


@pytest.fixture()
def client(tmp_path):
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    store = StateArtifactStore(tmp_path / "state")
    store.write(fake_coverage_payload())
    store.write(fake_watches_payload())
    return TestClient(create_app(tmp_path))


def test_endpoints_serve_the_artifacts_verbatim(client) -> None:
    cov = client.get("/api/v1/coverage").json()
    assert cov["kind"] == "coverage" and cov["counts"] == fake_coverage_payload()["counts"]
    assert cov["research_gaps"] == fake_coverage_payload()["research_gaps"]
    wat = client.get("/api/v1/watches").json()
    assert wat["kind"] == "watches" and wat["counters"] == fake_watches_payload()["counters"]
    assert wat["stalled"] == fake_watches_payload()["stalled"]


@pytest.mark.parametrize("kind", ["coverage", "watches"])
def test_absent_artifact_is_503_with_its_own_remedy(tmp_path, kind: str) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    response = TestClient(create_app(tmp_path)).get(f"/api/v1/{kind}")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["state_kind"] == kind and f"materialize --{kind}" in error["remedy"]
    assert not (tmp_path / "state" / f"{kind}.json").exists()


@pytest.mark.parametrize("kind", ["coverage", "watches"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_mutation_verbs_are_rejected(client, kind: str, method: str) -> None:
    assert client.request(method, f"/api/v1/{kind}").status_code == 405


def test_meta_declares_both(client) -> None:
    endpoints = client.get("/api/v1/meta").json()["endpoints"]
    assert "GET /api/v1/coverage" in endpoints and "GET /api/v1/watches" in endpoints


def test_frontend_has_both_views_and_no_ranking_of_gaps() -> None:
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderCoverage" in source and "function renderWatches" in source
    for token in (".sort(", "優先度", "最重要", "建議先做"):
        assert token not in source, token
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'href="#/coverage"' in html and 'href="#/watches"' in html
