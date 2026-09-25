"""`loader/migrate_relation_rejudge.py --additions`（2026-09-25，pq2 [651]／[652]）。

新增只准引用該抽取檔既有的 sources（quote 一字不動）、只接圖上既有節點、補宣告的端點照抄圖上現值，
改完要過 `loader/validate.py`，同一份 manifest 重跑冪等。夾具是一份真實抽取檔的複本；不連 Neo4j。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import loader.migrate_relation_rejudge as mig

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = "silicon_matter_sivers_ayar_2026_03_14.json"
GRAPH = {"co:globalfoundries": {"type": "Company", "name": "GlobalFoundries", "abstraction_level": "foundry_packaging",
                                "role": None, "aliases": ["GF"], "attributes": {"ticker": "GFS"}, "confidence": 0.9}}


@pytest.fixture()
def extractions(tmp_path, monkeypatch):
    shutil.copy(ROOT / "extractions" / FIXTURE, tmp_path / FIXTURE)
    # ⚠ 真實檔在 [654] 入圖（2026-09-25，4ab71d4）後已含這條 develops 邊，「新增」就變成無事可做、
    # 測試因此 KeyError（2026-09-26 Step 2.6 全套測試時發現）。夾具還原成入圖前的形狀，讓測試不隨 live 資料變。
    data = json.loads((tmp_path / FIXTURE).read_text(encoding="utf-8"))
    data["edges"] = [e for e in data["edges"]
                     if (e["src_id"], e["relation"], e["dst_id"]) != ("co:ayar_labs", "develops", "prod:supernova")]
    (tmp_path / FIXTURE).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    monkeypatch.setattr(mig, "EXTRACTIONS", tmp_path)
    return tmp_path


def _row(src="co:ayar_labs", dst="prod:supernova", relation="develops",
         sources=("silicon_matter_sivers_ayar_2026_03_14_s1",)):
    return {"file": FIXTURE, "edge": {"src_id": src, "relation": relation, "dst_id": dst,
                                      "source_ids": list(sources), "attributes": {}}}


def _props(ids):
    return {i: GRAPH[i] for i in ids if i in GRAPH}


def test_an_addition_only_adds_and_is_idempotent(extractions) -> None:
    before = json.loads((extractions / FIXTURE).read_text(encoding="utf-8"))
    p = mig.plan({}, [_row()], node_props=_props)
    spec = p["files"][FIXTURE]
    assert spec["added"] == 1 and spec["changed"] == 0 and not spec["removed_local_ids"]
    assert spec["new_edges"][:len(before["edges"])] == before["edges"], "既有的邊一條都不得動"
    new = spec["new_edges"][-1]
    assert new["id"] == mig.addition_local_id(new) and new["relation"] == "develops"

    # 寫回後重跑：同一份 manifest 不再新增（local id 由 src／relation／dst 決定）
    doc = dict(before, edges=spec["new_edges"], nodes=spec["new_nodes"])
    (extractions / FIXTURE).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    again = mig.plan({}, [_row()], node_props=_props)
    assert again["files"] == {} and again["additions_skipped"] == [f"{FIXTURE}:{new['id']}"]


def test_an_addition_may_not_bring_new_quotes(extractions) -> None:
    with pytest.raises(RuntimeError, match="Research Action"):
        mig.plan({}, [_row(sources=("some_other_doc_s1",))], node_props=_props)


def test_a_missing_endpoint_is_declared_from_the_graph_not_invented(extractions) -> None:
    p = mig.plan({}, [_row(src="co:globalfoundries")], node_props=_props)
    spec = p["files"][FIXTURE]
    assert spec["declared_nodes"] == ["co:globalfoundries"]
    declared = next(n for n in spec["new_nodes"] if n["id"] == "co:globalfoundries")
    assert {k: declared[k] for k in GRAPH["co:globalfoundries"]} == GRAPH["co:globalfoundries"], \
        "補宣告的節點必須照抄圖上現值——loader 對節點是覆寫，自己編一份會改掉節點屬性"
    assert declared["source_ids"] == ["silicon_matter_sivers_ayar_2026_03_14_s1"]


def test_an_endpoint_that_is_not_in_the_graph_is_rejected(extractions) -> None:
    with pytest.raises(RuntimeError, match="不在圖上"):
        mig.plan({}, [_row(src="co:nobody_knows")], node_props=_props)


def test_an_addition_to_a_file_that_does_not_exist_is_reported(extractions) -> None:
    row = dict(_row(), file="no_such_file.json")
    assert mig.plan({}, [row], node_props=_props)["not_found"] == ["no_such_file.json"]


def test_an_invalid_result_is_refused_before_anything_is_written(extractions) -> None:
    before = json.loads((extractions / FIXTURE).read_text(encoding="utf-8"))   # 夾具（不是真實檔，見 fixture）
    with pytest.raises(RuntimeError, match="驗證不過"):
        mig.plan({}, [_row(relation="not_a_relation")], node_props=_props)
    assert json.loads((extractions / FIXTURE).read_text(encoding="utf-8")) == before
