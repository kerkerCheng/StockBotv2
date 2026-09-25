"""心跳的走圖行與讀圖單位拆分（Phase 2 Step 2.6）。

守的是 plan §7「心跳」那一段：段 3 一行「走圖：」接九型各自「中文短名 命中／母體」，**0 也印**；
artifact 讀不到時印 `upstream_unavailable` 不印 0（INV-3）；段 2 讀圖行加單位拆分（層 N／插槽 M），
重讀理由帶單位（R2-b N6）。**心跳不查圖**——只讀已 materialize 的 artifact。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from crons import heartbeat as hb
from query.graph_walk import QUESTION_TYPES, QUESTION_TYPE_KEYS
from webapp.materialize import build_graph_walk_artifact
from webapp.store import StateArtifactStore
from webapp.structure_readings import build_structure_readings_artifact

from test_graph_walk import run_walk

NOW = datetime(2026, 9, 26, 0, 30, tzinfo=timezone.utc)


def _state_with_walk(tmp_path: Path, **overrides) -> Path:
    state = tmp_path / "state"
    StateArtifactStore(state).write(build_graph_walk_artifact(run_walk(**overrides)))
    return state


def test_walk_line_prints_every_type_including_zero_and_no_total(tmp_path: Path) -> None:
    state = _state_with_walk(tmp_path, leads={})
    lines = hb.build_queue(state_dir=state, now=NOW).lines
    walk = next(line for line in lines if line.startswith("走圖："))
    for qt in QUESTION_TYPES:
        assert f"{qt.short} " in walk, qt.key
    assert "lead 點名不在圖 0／0" in walk          # 0 也印
    assert "合計" not in walk and "總" not in walk  # 不加總（plan §0 第 7 條）
    # 原本 pq1 那一行的「＋結構讀圖待重讀 N」改由走圖第 4 型承載，不在兩處各印一次。
    pq1 = next(line for line in lines if line.startswith("pq1 可做"))
    assert "結構讀圖待重讀" not in pq1


def test_walk_line_says_unread_instead_of_zero_when_the_artifact_is_missing(tmp_path: Path) -> None:
    empty = tmp_path / "state"
    empty.mkdir()
    lines = hb.build_queue(state_dir=empty, now=NOW).lines
    walk = next(line for line in lines if line.startswith("走圖："))
    assert "upstream_unavailable" in walk and "不是「沒有洞」" in walk
    assert "0／" not in walk


def test_walk_line_flags_an_artifact_whose_types_differ_from_the_vocabulary() -> None:
    questions = [q for q in build_graph_walk_artifact(run_walk())["questions"] if q["key"] != "duplicate_node"]
    assert "不一致" in hb._graph_walk_line(questions, None)
    full = build_graph_walk_artifact(run_walk())["questions"]
    assert "不一致" not in hb._graph_walk_line(full, None)


def test_snapshot_has_one_key_per_walk_type_and_reads_the_artifact(tmp_path: Path) -> None:
    assert [k for k in hb.SNAPSHOT_KEYS if k.startswith("walk.")] == [f"walk.{k}" for k in QUESTION_TYPE_KEYS]
    state = _state_with_walk(tmp_path)
    values = hb.collect_snapshot(now=NOW, state_dir=state, leads_path=tmp_path / "none.json",
                                 thesis_path=tmp_path / "none.json", run_record_path=None, capture_dir=tmp_path)
    walk = build_graph_walk_artifact(run_walk())["counts"]
    assert all(values[f"walk.{k}"] == walk[k]["hit_n"] for k in QUESTION_TYPE_KEYS)
    empty = hb.collect_snapshot(now=NOW, state_dir=tmp_path / "nothing", leads_path=tmp_path / "none.json",
                                thesis_path=tmp_path / "none.json", run_record_path=None, capture_dir=tmp_path)
    assert all(empty[f"walk.{k}"] is None for k in QUESTION_TYPE_KEYS)   # 讀不到是 None，不是 0


def test_unit_labels_equal_the_reading_units_vocabulary() -> None:
    from alpha.structure_reading import READING_UNITS

    assert set(hb._UNIT_LABEL) == set(READING_UNITS)


def test_reading_line_splits_by_unit_and_reread_reasons_carry_the_unit(tmp_path: Path) -> None:
    state = tmp_path / "state"
    rows = [
        {"node": "mat:inp_substrate", "unit": "layer", "reading_id": "sr_1", "status": "current",
         "needs_reread": False, "reread_reasons": []},
        {"node": "prod:supernova", "unit": "socket", "reading_id": "sr_2", "status": "current",
         "needs_reread": True, "reread_reasons": ["客戶 co:ayar_labs 出了新文件 lead_x"]},
        {"node": "prod:els_8ch_module", "unit": "socket", "reading_id": "sr_3", "status": "current",
         "needs_reread": False, "reread_reasons": []},
    ]
    StateArtifactStore(state).write(build_structure_readings_artifact(rows=rows))
    text = "\n".join(hb.build_changes(now=NOW, state_dir=state, thesis_path=tmp_path / "none.json").lines)
    assert "結構讀圖 3 份（層 1／插槽 2）" in text
    assert "prod:supernova（插槽）該重讀：客戶 co:ayar_labs" in text
