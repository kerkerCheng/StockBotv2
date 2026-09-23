"""`structure_table` state artifact：**照抄 `structure_table()` 的輸出**，不重排、不重算、沒有名次。

⚠ 2026-09-23（Phase 0 Step 0b.3）：本檔原名 `test_webapp_ranking.py`，守 `ranking` kind。跨檔排序退役後
守「兩份序不同」「落差註記」「產業分組」的 3 條隨機制退役，其餘判準一字未改（照抄、三態、固定文字一份、
fail closed、兩個 digest、store、API、前端不排序），主詞換成結構表；新增 1 條守退役後的形狀（沒有名次、
沒有首選、沒有兩份序）。
這裡守的是 B1 的驗收條件：APP 表與 `python -m query.bottleneck` 逐列 diff 0。
所有 fixture 離線（不連 Neo4j）：這一層的責任是「一份 structure_table 結果 → 一份 artifact」，
綁在真實資料上只會讓測試在 DB 沒開時變成綠色的空跑（L13-2）。
"""
from __future__ import annotations

import json
import types
from datetime import date
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from query.bottleneck import known_limitations, project_assertions_as_of, render_markdown, structure_table
from webapp.api import create_app
from webapp.contracts import (
    STATE_KINDS, STATE_SCHEMA_VERSIONS, ArtifactUnavailable, validate_state_artifact,
)
from webapp.materialize import build_structure_table_artifact, materialize_view
from webapp.store import ArtifactStore, StateArtifactStore, resolve_state_dir

from test_structure_table import _FakeRegistry
from test_webapp_materialize import fake_view

ROOT = Path(__file__).resolve().parents[1]

class _LabelRegistry(_FakeRegistry):
    """多一個 `company()`：display_name 只有 Coherent 有；AXT 只有 name；lumentum 不在 registry。

    ⚠ 這裡的 `name` 只用來測 `webapp/materialize.py` 標籤的 fallback 分支；真 registry 沒有
    `name` 欄位（假登記表的公司物件自 2026-09-16 起只有 `display_name`，見 `_FakeRegistry`）。
    """

    def company(self, company_id):
        for c in self._c:
            if c.company_id == company_id:
                display = {"co:coherent": "Coherent Corp."}.get(company_id)
                return types.SimpleNamespace(display_name=display, name=c.display_name)
        return None


def _attrs(**kw):
    return json.dumps({k: v for k, v in kw.items() if v is not None})


def _rows():
    return [
        # 外部印證（origin 是 NVIDIA ≠ src）、sub 5、sole、距錨 2 跳
        {"src": "co:coherent", "relation": "supplies_to", "dst": "co:nvidia", "confidence": 0.9,
         "attributes": _attrs(substitutability=5, sole_source=True, qualification_status="qualified"),
         "origin": "NVIDIA", "source_doc_id": "doc_nvda_call", "published_at": "2026-06-01"},
        {"src": "co:nvidia", "relation": "supplies_to", "dst": "tech:ai_switch", "confidence": 0.9,
         "attributes": _attrs(), "origin": "NVIDIA", "source_doc_id": "doc_nvda_call",
         "published_at": "2026-06-01"},
        # sub 5、sole、直接接錨（1 跳）——但 origin 解析不到 registry，證據最弱
        {"src": "co:lumentum", "relation": "supplies_to", "dst": "tech:ai_switch", "confidence": 0.8,
         "attributes": _attrs(substitutability=5, sole_source=True, qualification_status="designed_in"),
         "origin": "Lumentum", "source_doc_id": "doc_lite_pr", "published_at": "2026-05-01"},
        # sole_source **未填**（None）——三態要活著；origin 是 Coherent ≠ src → 外部印證
        {"src": "co:axt", "relation": "supplies_to", "dst": "co:coherent", "confidence": 0.8,
         "attributes": _attrs(substitutability=4, qualification_status="qualified"),
         "origin": "Coherent", "source_doc_id": "doc_cohr_10k", "published_at": "2026-04-01"},
    ]


def fake_result(rows=None):
    return structure_table(rows if rows is not None else _rows(), _LabelRegistry())


def fake_table_payload(rows=None, **kw):
    """一份最小但形狀正確的 `structure_table` artifact（給本檔與 request-path 證明共用）。"""
    return build_structure_table_artifact(fake_result(rows), registry=_LabelRegistry(), **kw)



# ---------------------------------------------------------------------------
# 照抄：順序、每一格、三態
# ---------------------------------------------------------------------------

def test_rows_are_the_authority_output_verbatim_and_in_order() -> None:
    """B1 驗收：逐列 diff 0。artifact 的每一列、每一格都等於 structure_table 的輸出。

    ⚠ 沒有門檻了：`co:nvidia → tech:ai_switch` 那條 sub 未填的邊也在表上（4 列，不是 3）；
    順序是 (company_id, relation, bottleneck) 字典序，不是名次——列上沒有 `rank`。"""
    result = fake_result()
    payload = build_structure_table_artifact(result, registry=_LabelRegistry())
    assert len(result["rows"]) == 4
    assert [r["company_id"] for r in payload["rows"]] == [r["company_id"] for r in result["rows"]]
    assert [r["company_id"] for r in payload["rows"]] == ["co:axt", "co:coherent", "co:lumentum", "co:nvidia"]
    for got, src in zip(payload["rows"], result["rows"]):
        assert "rank" not in got
        for key, value in src.items():
            assert got[key] == value, key


def test_numbers_are_copied_not_recomputed() -> None:
    """空跑檢查：若 materializer 自己算了什麼，這裡的 `is` 就不會成立。"""
    result = fake_result()
    payload = build_structure_table_artifact(result, registry=_LabelRegistry())
    for got, src in zip(payload["rows"], result["rows"]):
        for key in ("substitutability", "confidence", "documents", "demand_hops", "lead_time_weeks",
                    "sole_source", "evidence"):
            assert got[key] is src[key], key
        # 容器（chain／sources）會被 redact_private_paths 重建——那是設計，比內容不比身分。
        assert got["chain"] == src["chain"] and got["sources"] == src["sources"]
    assert payload["coverage"] == result["coverage"]


def test_sole_source_three_state_survives() -> None:
    """None＝圖上沒人對這條邊發言過，**不是 False**。壓成 bool 是 2026-09-05 修掉的 bug。"""
    payload = fake_table_payload()
    states = {r["company_id"]: r["sole_source"] for r in payload["rows"]}
    assert states["co:coherent"] is True
    assert states["co:axt"] is None
    assert "null" in payload["vocab"]["sole_source_states"]
    assert "未填不是否" in payload["vocab"]["sole_source_states"]["null"]


def test_no_rank_no_top_pick_no_two_orders() -> None:
    """退役後的形狀（2026-09-23 Step 0b.3）：沒有首選、沒有兩份序、沒有產業分組、沒有門檻濾出的列；
    `population` 與 `anchor_gaps` 在，`this_is_not` 第一句就說它不是排序。"""
    payload = fake_table_payload()
    for retired in ("top_pick", "top_pick_absent_reason", "structural_rows", "sectors", "empty_sectors",
                    "filter", "filtered_rows", "correlation_notes"):
        assert retired not in payload, retired
    assert "sort_keys" not in payload["vocab"] and "min_substitutability" not in payload["vocab"]
    assert payload["population"]["accepted"] == 4 and payload["population"]["excluded"] == 0
    assert "anchor_gaps" in payload and payload["anchor_gaps"]["population"] > 0
    assert "不是排序" in payload["this_is_not"][0]
    assert "索引" in payload["notes"]["order"]


# ---------------------------------------------------------------------------
# 固定文字與判準只有一份（L16）
# ---------------------------------------------------------------------------

def test_limitations_and_notes_travel_with_the_data() -> None:
    result = fake_result()
    payload = build_structure_table_artifact(result, registry=_LabelRegistry())
    md = render_markdown(result)
    assert payload["limitations"] == known_limitations(result["coverage"])
    for text in payload["limitations"]:
        assert text in md
    assert payload["notes"]["order"] in md
    assert payload["notes"]["table"] in md
    assert payload["title"] in md
    assert payload["notes"]["no_anchor_reading"] is None   # fixture 全部走得到錨 → 不印那段


def test_company_label_comes_from_registry_never_guessed() -> None:
    payload = fake_table_payload()
    labels = {r["company_id"]: r["company_label"] for r in payload["rows"]}
    assert labels["co:coherent"] == "Coherent Corp."   # display_name
    assert labels["co:axt"] == "AXT"                   # 退回 name
    assert labels["co:lumentum"] is None               # registry 沒有 → None，不從 ID 造名字


def test_empty_table_is_honest_not_silent() -> None:
    """母體為空時 rows=[]、population 計數為 0，artifact 仍合法——「排不出來」那句隨首選退役。"""
    empty = build_structure_table_artifact(structure_table([], _LabelRegistry()), registry=_LabelRegistry())
    assert empty["rows"] == [] and empty["population"]["input"] == 0
    assert empty["anchor_gaps"]["population"] == 0
    validate_state_artifact("structure_table", empty)


# ---------------------------------------------------------------------------
# 契約：fail closed、兩個 digest
# ---------------------------------------------------------------------------

def test_state_kinds_are_a_closed_vocabulary() -> None:
    # 2026-09-22（Phase 0 Step 0a.2）：`basket` 與 `multi_year` 兩個 kind 退役，9 → 7。
    # 2026-09-23（Step 0b.3）：`ranking` → `structure_table`，仍是 7。
    # 這是**封閉字彙**的相等斷言，所以「有人把它加回來」與「有人新增一個沒登記的 kind」
    # 都會在這裡變紅——不必另外寫一條「不得出現」的斷言。
    assert STATE_KINDS == ("structure_table", "beta", "coverage", "watches", "positions",
                           "structure_readings", "account_scorecard")
    assert STATE_SCHEMA_VERSIONS["structure_table"] == "stockbot-app/structure_table/1"


def test_state_artifact_fails_closed() -> None:
    payload = fake_table_payload()
    assert validate_state_artifact("structure_table", payload) is payload
    with pytest.raises(ArtifactUnavailable, match="未登記"):
        validate_state_artifact("cashflow", payload)
    with pytest.raises(ArtifactUnavailable, match="未登記"):
        validate_state_artifact("ranking", payload)       # 退役的 kind 不再登記
    with pytest.raises(ArtifactUnavailable, match="kind"):
        validate_state_artifact("beta", payload)          # 已登記的 kind，但檔名與內容不一致
    with pytest.raises(ArtifactUnavailable, match="kind"):
        validate_state_artifact("structure_table", dict(payload, kind="coverage"))
    with pytest.raises(ArtifactUnavailable, match="schema"):
        validate_state_artifact("structure_table", dict(payload, schema_version="stockbot-app/structure_table/0"))
    with pytest.raises(ArtifactUnavailable, match="content_digest"):
        validate_state_artifact("structure_table", dict(payload, rows=[]))
    with pytest.raises(ArtifactUnavailable, match="缺必要欄位"):
        validate_state_artifact("structure_table", {k: v for k, v in payload.items() if k != "authority"})
    with pytest.raises(ArtifactUnavailable):
        validate_state_artifact("structure_table", "not an object")


def test_freshness_identity_tracks_cognition_not_document_counts() -> None:
    """多讀一份講同一條邊的文件 → documents +1、content 變，但認知狀態不變（L12）。"""
    a = fake_table_payload()
    extra = dict(_rows()[0], source_doc_id="doc_other", published_at="2026-06-02")
    b = fake_table_payload(rows=_rows() + [extra])
    docs = lambda payload: {r["company_id"]: r["documents"] for r in payload["rows"]}  # noqa: E731
    assert docs(b)["co:coherent"] == docs(a)["co:coherent"] + 1
    assert b["freshness_identity"] == a["freshness_identity"]
    assert b["content_digest"] != a["content_digest"]
    # 證據等級變了（lumentum 拿到客戶端 origin）→ 那一格變 → 認知狀態變（順序不變，它是索引）
    rows = _rows()
    rows[2] = dict(rows[2], origin="NVIDIA")
    c = fake_table_payload(rows=rows)
    assert c["freshness_identity"] != a["freshness_identity"]
    assert [r["company_id"] for r in c["rows"]] == [r["company_id"] for r in a["rows"]]


def test_as_of_projection_counts_are_carried_not_dropped() -> None:
    projection = project_assertions_as_of(_rows(), date(2026, 5, 15))
    result = structure_table(list(projection.rows), _LabelRegistry())
    payload = build_structure_table_artifact(result, registry=_LabelRegistry(),
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
    payload = fake_table_payload()
    path = store.write(payload)
    assert path.name == "structure_table.json" and path.parent == tmp_path
    assert not list(tmp_path.glob(".*.tmp"))
    got, fresh = store.read("structure_table")
    assert got == payload and fresh.state == "fresh"
    assert store.kinds() == ["structure_table"]
    assert store.missing_kinds() == ["beta", "coverage", "watches", "positions",
                                     "structure_readings", "account_scorecard"]
    with pytest.raises(ArtifactUnavailable, match="未登記"):
        store.read("cashflow")
    with pytest.raises(ArtifactUnavailable, match="尚未 materialize"):
        store.read("beta")
    with pytest.raises(ArtifactUnavailable):
        store.path_for("../ranking")


def test_state_store_reports_missing_and_broken_separately(tmp_path) -> None:
    store = StateArtifactStore(tmp_path)
    assert store.kinds() == []
    assert store.missing_kinds() == ["structure_table", "beta", "coverage", "watches", "positions",
                                     "structure_readings", "account_scorecard"]
    with pytest.raises(ArtifactUnavailable, match="尚未 materialize"):
        store.read("structure_table")
    (tmp_path / "structure_table.json").write_text('{"kind": "structure_table", "rows": [', encoding="utf-8")
    rows = list(store.read_all())
    assert rows[0][0] == "structure_table" and rows[0][1] is None and "半份" in rows[0][3]


def test_resolve_state_dir_has_one_rule(tmp_path, monkeypatch) -> None:
    assert resolve_state_dir(tmp_path, None) == tmp_path / "state"
    assert resolve_state_dir(tmp_path, tmp_path / "elsewhere") == tmp_path / "elsewhere"
    monkeypatch.setenv("STOCKBOT_APP_STATE_DIR", str(tmp_path / "env"))
    assert resolve_state_dir(None, None) == tmp_path / "env"


def test_analyst_store_does_not_see_the_state_subdir(tmp_path) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    StateArtifactStore(tmp_path / "state").write(fake_table_payload())
    assert ArtifactStore(tmp_path).tickers() == ["COHR"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    StateArtifactStore(tmp_path / "state").write(fake_table_payload())
    return TestClient(create_app(tmp_path))


def test_structure_table_endpoint_serves_the_artifact_verbatim(client) -> None:
    body = client.get("/api/v1/structure-table").json()
    payload = fake_table_payload()
    assert body["kind"] == "structure_table"
    assert body["rows"] == payload["rows"]
    assert body["population"] == payload["population"]
    assert body["limitations"] == payload["limitations"]
    assert body["freshness"]["state"] == "fresh"
    assert body["correlation_warning"]
    assert body["analyst_view_tickers"] == ["COHR"]      # 只是列目錄，讓前端知道哪檔可點


def test_structure_table_absent_is_503_with_remedy_and_never_rebuilt(tmp_path) -> None:
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    client = TestClient(create_app(tmp_path))
    response = client.get("/api/v1/structure-table")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["kind"] == "artifact_unavailable" and "materialize --structure-table" in error["remedy"]
    assert not (tmp_path / "state" / "structure_table.json").exists()
    # 退役的路由不再存在：不是 503（讀不到），是 404（沒有這條路）
    assert client.get("/api/v1/ranking").status_code == 404


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_structure_table_rejects_mutation_verbs(client, method: str) -> None:
    assert client.request(method, "/api/v1/structure-table").status_code == 405


def test_meta_and_health_declare_the_state_kinds(client) -> None:
    meta = client.get("/api/v1/meta").json()
    assert "GET /api/v1/structure-table" in meta["endpoints"]
    assert "GET /api/v1/ranking" not in meta["endpoints"]
    assert any("不重算、不排序" in s for s in meta["not_offered"])
    assert client.get("/api/v1/health").json()["state_kinds"] == ["structure_table"]


def test_status_and_verify_commands_include_state(tmp_path, capsys) -> None:
    from webapp.__main__ import main
    ArtifactStore(tmp_path).write(materialize_view(fake_view("COHR")))
    StateArtifactStore(tmp_path / "state").write(fake_table_payload())
    assert main(["status", "--dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "structure_table" in out and "4 條邊" in out and "可行動" not in out
    assert main(["verify", "--dir", str(tmp_path)]) == 0
    assert "2/2" in capsys.readouterr().out
    assert main(["status", "--dir", str(tmp_path), "--format", "json"]) == 0
    doc = json.loads(capsys.readouterr().out)
    assert [s["kind"] for s in doc["state"]] == ["structure_table"]
    assert doc["state_missing"] == ["beta", "coverage", "watches", "positions",
                                   "structure_readings", "account_scorecard"]


# ---------------------------------------------------------------------------
# 前端
# ---------------------------------------------------------------------------

def test_frontend_structure_table_view_never_sorts_or_scores() -> None:
    """畫面只改資訊階層：不得重排、不得算分、不得補權重、不得有名次欄或首選。"""
    source = (ROOT / "webapp" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderStructureTable" in source
    for retired in ("function renderRanking", "function renderBasket", "function renderMultiYear",
                    "top_pick", "structural_rows", "actionable_rank"):
        assert retired not in source, retired
    assert ".sort(" not in source
    for token in ("weighted", "weights", "score =", "* 0."):
        assert token not in source, token
    assert "TABLE_VOCAB.sole_source_states" in source     # 三態說明來自 artifact，不是前端自寫
    html = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'href="#/structure-table"' in html and "#/ranking" not in html
