"""敘事格引用的一手節錄 `library/raw/<檔名>`（2026-10-21 批次二 E12；failure log #50）。

短檢查敘事唯一的一手（公司自己的 10-K 節錄）本來就不在 evidence index 裡：寫入端收它、artifact 也原樣保留路徑，但
packet 的指示寫「必須是 evidence_index 的 key」、個股頁證據清單（`compose._evidence_for` 只查索引）列不出它。
規則與層說明的 `raw:<檔名>` 同一條：**寫入時檢查指得回、呈現時列出**。不是原始證據的引用（讀圖、三題成果）不列，
但報出來、不靜默（INV-3）。
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from briefing.alpha_view.contracts import EvidenceItem
from briefing.analyst_view import compose

RAW = "library/raw/klic_10k_fy2025_short_check_excerpt.txt"


def _item(ref: str) -> EvidenceItem:
    return EvidenceItem(ref=ref, kind="engine_c_snapshot", source_doc_id=None, origin_entity=None, url=None,
                        quote=None, published_at=None, retrieved_at=None, recorded_at=None, evidence_tier=None,
                        evidence_class=None, confidence=None, corroborating_origins=())


def _view(*refs: str):
    return SimpleNamespace(evidence=SimpleNamespace(index=tuple(_item(r) for r in refs)))


def _cells(*refs_per_cell):
    return [SimpleNamespace(evidence_refs=tuple(refs)) for refs in refs_per_cell]


SNAPSHOT = "engine_c://financial_snapshot/KLIC"
SOURCE = "graph://source/asmpt_2026_interim_results_wire_bonding"
READING = "sr_6dafc390612b7867"
DERIVED = "alpha://three_questions/v1/KLIC#own_history_pctile"


def test_the_evidence_list_lists_raw_excerpts_and_unindexed_graph_sources() -> None:
    cells = _cells((SNAPSHOT, RAW), (RAW, SOURCE))
    listed = compose._evidence_for(_view(SNAPSHOT), cells)
    assert [(i.ref, i.kind) for i in listed] == [
        (SNAPSHOT, "engine_c_snapshot"), (RAW, "external_document"), (SOURCE, "source_doc")]
    assert listed[2].source_doc_id == "asmpt_2026_interim_results_wire_bonding"


def test_refs_that_are_not_evidence_are_reported_not_dropped() -> None:
    cells = _cells((SNAPSHOT, READING), (DERIVED, RAW))
    view = _view(SNAPSHOT)
    assert {i.ref for i in compose._evidence_for(view, cells)} == {SNAPSHOT, RAW}
    assert compose._unlisted_refs(view, cells) == [READING, DERIVED]


def test_new_kinds_stay_inside_the_closed_evidence_kind_contract() -> None:
    from alpha.contracts import EVIDENCE_KINDS

    assert {compose._outside_index_kind(RAW), compose._outside_index_kind(SOURCE)} <= EVIDENCE_KINDS


def test_the_presentation_prefix_equals_the_narrative_contract() -> None:
    from alpha.narrative.contracts import RAW_EXCERPT_PREFIX

    assert compose._RAW_EXCERPT_PREFIX == RAW_EXCERPT_PREFIX


def test_the_write_side_rejects_raw_refs_that_do_not_point_to_a_file(tmp_path: Path) -> None:
    from alpha.providers.briefs import raw_excerpt_problems

    (tmp_path / "library" / "raw").mkdir(parents=True)
    (tmp_path / "library" / "raw" / "klic_10k_fy2025_short_check_excerpt.txt").write_text("x", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("x", encoding="utf-8")
    ok = SimpleNamespace(slots=[SimpleNamespace(key="story", evidence_refs=(RAW, SNAPSHOT))])
    assert raw_excerpt_problems(ok, root=tmp_path) == []
    missing = SimpleNamespace(slots=[SimpleNamespace(key="story", evidence_refs=("library/raw/nope.txt",))])
    assert "在 library/raw 找不到" in raw_excerpt_problems(missing, root=tmp_path)[0]
    escape = SimpleNamespace(slots=[SimpleNamespace(key="story", evidence_refs=("library/raw/../../secret.txt",))])
    assert raw_excerpt_problems(escape, root=tmp_path)


def test_the_packet_instruction_matches_the_write_side() -> None:
    from alpha.models.session_assessor import _brief_frame

    how = _brief_frame()["_how_to_use"]
    assert "library/raw/<檔名>" in how and "必須是 evidence_index 的 key" not in how
