"""節點合併後，舊紀錄引用的別名 id 照 registry 換成 canonical 再解析（2026-10-29）。

事發：2026-10-17 使用者核准 [777]，`tech:inp_6inch_fab` 併進 `tech:six_inch_inp_production`。COHR 的 session 判斷檔與
兩條營運假設還引用 `graph://edge/co:coherent/depends_on/tech:inp_6inch_fab`——引用解析只認字面，於是整份判斷被拒
（「引用了不在 ResearchContext 裡的證據」）、兩條假設被判 invalidated，`tests/test_full_chain_acceptance.py` 7 條連鎖紅了
12 天、被當成「真資料漂移」。同一個缺口的第一例是讀圖過期檢查（failure log #75，10-21 修）——這是它的對稱面（L17）。

守四件事：
1. **不是放寬解析**：只換**整段等於**別名的 id，換完仍必須落在 index 裡；對照表不給就照舊嚴格。
2. **換過的要現形**（L12）：session 判斷記進 `metadata["renamed_refs"]`，假設記進 `selection.renamed`。
3. 沒有合併的判斷 metadata 一字不變（不多一個空鍵——否則每一份 artifact 的 digest 都會動）。
4. 兩個消費端共用同一支 `alpha.identity.canonical_evidence_ref`，不各寫一份。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.context import build_research_context
from alpha.contracts import EvidenceRef
from alpha.errors import ContractViolation
from alpha.fundamental.assumptions import select_assumptions
from alpha.identity import canonical_evidence_ref
from alpha.models import compose_signal
from alpha.testing import FakeGraphResearchProvider
from tests.fixtures_fundamental import INDEX, TARGET, TODAY, _assumption
from tests.test_alpha_vertical_slice import COMPANY, TICKER, _FakeFundamentals, _judgment

OLD = "graph://edge/co:coherent/depends_on/tech:inp_6inch_fab"
NEW = "graph://edge/co:coherent/depends_on/tech:six_inch_inp_production"
ALIASES = {"tech:inp_6inch_fab": "tech:six_inch_inp_production"}
_NEW_REF = EvidenceRef(ref=NEW, kind="graph_edge", evidence_class="externally_corroborated", evidence_tier=1,
                       published_at=date(2026, 5, 1))


def test_only_whole_segments_that_are_registered_aliases_are_rewritten() -> None:
    assert canonical_evidence_ref(OLD, ALIASES) == NEW
    assert canonical_evidence_ref(OLD, {"tech:inp_6inch": "tech:x"}) == OLD          # 子字串不算
    assert canonical_evidence_ref("graph://assertion/e1", ALIASES) == "graph://assertion/e1"
    assert canonical_evidence_ref("tech:inp_6inch_fab", ALIASES) == "tech:inp_6inch_fab"  # 不是 ref 就不動


def _build():
    return build_research_context(
        ticker=TICKER, company_id=COMPANY,
        graph_provider=FakeGraphResearchProvider(company_id=COMPANY, evidence_pool=(_NEW_REF,)),
        fundamentals_provider=_FakeFundamentals())


def _old_judgment():
    judgment = _judgment()
    judgment["axes"]["value_capture"]["evidence"] = [OLD]
    judgment["axes"]["expectation_gap"] = {"level": "unknown", "reason": "測試", "evidence": []}
    return judgment


def test_a_judgment_citing_a_merged_id_resolves_through_the_registry_and_says_so() -> None:
    with pytest.raises(ContractViolation, match="不在 ResearchContext"):
        compose_signal(_build(), _old_judgment())                                  # 沒給對照表：照舊嚴格
    signal = compose_signal(_build(), _old_judgment(), entity_aliases=ALIASES)
    assert signal.value_capture_score is not None
    assert signal.metadata["renamed_refs"] == [{"axis": "value_capture", "cited": OLD, "resolved": NEW}]


def test_a_rename_that_lands_outside_the_context_is_still_rejected() -> None:
    with pytest.raises(ContractViolation, match="不在 ResearchContext"):
        compose_signal(_build(), _old_judgment(), entity_aliases={"tech:inp_6inch_fab": "tech:somewhere_else"})


def test_a_judgment_without_merged_ids_keeps_its_metadata_unchanged() -> None:
    judgment = _judgment()
    judgment["axes"]["value_capture"]["evidence"] = [NEW]
    judgment["axes"]["expectation_gap"] = {"level": "unknown", "reason": "測試", "evidence": []}
    signal = compose_signal(_build(), judgment, entity_aliases=ALIASES)
    assert "renamed_refs" not in signal.metadata


def test_an_assumption_citing_a_merged_id_is_accepted_and_the_rename_is_recorded() -> None:
    record = _assumption("tax_rate", "total", 0.19, basis="heuristic_proxy", refs=(OLD,))
    index = {**INDEX, NEW: _NEW_REF}
    accepted, selection = select_assumptions([record], target=TARGET, as_of=None, today=TODAY, evidence_index=index)
    assert not accepted and selection.rejected[0][1].startswith("unresolved_evidence")
    accepted, selection = select_assumptions([record], target=TARGET, as_of=None, today=TODAY, evidence_index=index,
                                             entity_aliases=ALIASES)
    assert [a.assumption_id for a in accepted] == [record.assumption_id]
    assert selection.renamed == ((record.assumption_id, OLD, NEW),) and selection.rejected == ()
