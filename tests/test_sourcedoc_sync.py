"""拆段判準唯一 owner `loader.is_legit_multi_section` 與 SourceDoc／抽取 JSON 一致性計數器（Phase 4 Step 4.2e）。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from loader.load_to_neo4j import is_legit_multi_section
from loader.sourcedoc_sync import drift, json_source_docs, summary_line


@pytest.mark.parametrize("sections, legit", [
    (["financials", "photonics"], True),
    (["asic_and_deployment", "counter_path", "x"], True),
    (["financials", None], False),          # 一份沒有 section → 不是拆段（audit 原本不報這種）
    (["financials", ""], False),
    (["financials", " financials "], False),  # 去空白後相同
    (["a", "b", "a"], False),               # 兩兩互異，不只比新的那份（loader 原本只比新 vs 舊）
    ([None, None], False),
])
def test_is_legit_multi_section_is_all_present_and_pairwise_distinct(sections, legit) -> None:
    assert is_legit_multi_section(sections) is legit


def test_the_three_call_sites_use_the_one_function() -> None:
    root = Path(__file__).resolve().parent.parent
    for rel in ("query/health_audit.py", "audit/checks.py"):
        text = (root / rel).read_text(encoding="utf-8")
        assert "is_legit_multi_section" in text, rel
        assert "def _is_legit_multi_section" not in text, rel
    loader = (root / "loader" / "load_to_neo4j.py").read_text(encoding="utf-8")
    assert "legit_multi_section = is_legit_multi_section(" in loader


def _write(directory: Path, name: str, doc_id: str, *, section=None, title="T") -> None:
    source_doc = {"doc_id": doc_id, "title": title}
    if section is not None:
        source_doc["section"] = section
    (directory / name).write_text(json.dumps({"source_doc": source_doc}), encoding="utf-8")


def test_drift_separates_rebuild_loss_from_graph_lag(tmp_path: Path) -> None:
    _write(tmp_path, "graph_only.json", "graph_only")                                   # JSON 沒 section
    _write(tmp_path, "base.json", "split", title="Parent title")
    _write(tmp_path, "split_addendum.json", "split", title="Parent title——addendum")    # 兩份 JSON 標題互異
    _write(tmp_path, "lag.json", "lag", section="photonics", title="Parent")            # JSON 對、圖落後
    _write(tmp_path, "same.json", "same", section="s", title="Same")
    rows = [
        {"id": "graph_only", "section": "asic", "title": "T"},
        {"id": "split", "section": None, "title": "Parent title——addendum"},
        {"id": "lag", "section": None, "title": "Parent——addendum"},
        {"id": "same", "section": "s", "title": "Same"},
        {"id": "no_json", "section": None, "title": "x"},
    ]
    result = drift(rows, json_source_docs(tmp_path))
    danger = {(d["doc_id"], d["field"], d["kind"]) for d in result["danger"]}
    stale = {(d["doc_id"], d["field"]) for d in result["stale"]}
    assert danger == {("graph_only", "section", "graph_only"), ("split", "title", "json_files_disagree")}
    assert stale == {("lag", "section"), ("lag", "title")}
    assert result["graph_without_json"] == ["no_json"]
    c = result["counts"]
    assert (c["danger"], c["danger_section"], c["danger_title"], c["stale"], c["stale_section"], c["stale_title"]) == (
        2, 1, 1, 2, 1, 1)
    assert "重建會遺失或不確定 2" in summary_line(result) and "圖落後 JSON 2" in summary_line(result)


def test_graph_without_json_and_unreadable_files_are_red_and_counted(tmp_path: Path) -> None:
    """R2-a N7：圖上有、沒有任何抽取檔（整份重建不回來）與讀不了的抽取檔，都是「重建會遺失」——紅、而且計數（INV-3）；
    圖落後 JSON 不紅。"""
    from loader.sourcedoc_sync import is_red

    _write(tmp_path, "lag.json", "lag", section="photonics", title="Parent")
    lag_only = drift([{"id": "lag", "section": None, "title": "Parent"}], json_source_docs(tmp_path))
    assert lag_only["stale"] and not is_red(lag_only)

    no_json = drift([{"id": "lag", "section": "photonics", "title": "Parent"}, {"id": "ghost", "section": None,
                                                                             "title": "x"}], json_source_docs(tmp_path))
    assert no_json["danger"] == [] and no_json["graph_without_json"] == ["ghost"] and is_red(no_json)

    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    broken = drift([{"id": "lag", "section": "photonics", "title": "Parent"}], json_source_docs(tmp_path))
    assert broken["unreadable_json"] == ["broken.json"] and broken["counts"]["unreadable_json"] == 1 and is_red(broken)
    assert "讀不了的抽取檔 1" in summary_line(broken)


def test_new_audit_check_is_registered() -> None:
    from audit import CHECKS_BY_NAME

    check = CHECKS_BY_NAME()["SourceDocSync"]
    assert check.invariant == "INV-6"
