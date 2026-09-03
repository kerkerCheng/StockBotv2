"""Anti-lookahead：歷史時間 T 的研究不得看到 T 之後才公開的資料。

⚠ **這一組測試是 Phase 6 的保險絲，Phase 1 就要裝。**
現況實測（`docs/refactor/current-architecture.md` §4.2）：Engine A 的 canonical edge
**完全沒有時間欄位**，屬性是對所有 assertion 的當前投影；唯一時間線索是
`CITES → SourceDoc.published_at`，覆蓋率只有 **382/662（58%）**。
在 as-of 投影做出來之前，任何回測嘗試都必須**大聲失敗**，而不是靜默看到未來。
"""
from __future__ import annotations

from datetime import date

import pytest

from alpha.contracts import (
    ConsensusSnapshot, EvidenceSelection, FundamentalsSnapshot, MarketSnapshot,
    ResearchContext, ScarcityInputs, StructuralContext, ValuationSnapshot,
    select_point_in_time_evidence,
)
from alpha.errors import ContractViolation, PointInTimeUnsupported
from alpha.identity import CompanyId, Ticker
from alpha.provider import AS_OF_METHODS
from alpha.testing import FakeGraphResearchProvider, as_of_capable, evidence

AS_OF = date(2026, 6, 30)

BEFORE = evidence("graph://assertion/before", published_at=date(2026, 5, 1))
ON_BOUNDARY = evidence("graph://assertion/boundary", published_at=AS_OF)
AFTER = evidence("sec://filing-2026-07-05", kind="source_doc",
                 published_at=date(2026, 7, 5))
UNDATED = evidence("graph://claim/undated", kind="graph_claim", published_at=None)


def _context(selection: EvidenceSelection, *, as_of: date | None) -> ResearchContext:
    return ResearchContext(
        ticker=Ticker("COHR"),
        company_id=CompanyId("co:coherent"),
        as_of=as_of,
        graph=StructuralContext(company_id=CompanyId("co:coherent")),
        structural=ScarcityInputs(),
        fundamentals=FundamentalsSnapshot(),
        market=MarketSnapshot(),
        consensus=ConsensusSnapshot(),
        valuation=ValuationSnapshot(),
        evidence_selection=selection,
    )


# ---------------------------------------------------------------------------
# 1. 篩選本身
# ---------------------------------------------------------------------------

def test_filing_published_after_as_of_is_excluded() -> None:
    """prompt §19 的原句：**7/5 才發布的 filing 不得出現在 6/30 的 ResearchContext**。"""
    selection = select_point_in_time_evidence([BEFORE, ON_BOUNDARY, AFTER], as_of=AS_OF)
    kept = {r.ref for r in selection.kept}
    assert kept == {BEFORE.ref, ON_BOUNDARY.ref}          # 當天發布的算數
    assert {r.ref for r in selection.excluded_future} == {AFTER.ref}

    context = _context(selection, as_of=AS_OF)
    assert AFTER.ref not in {r.ref for r in context.evidence_refs}


def test_missing_published_at_is_excluded_and_counted() -> None:
    """L11-5：**「我找不到日期」不等於「它發生在 T 之前」。**

    把未標日期的證據當成可用，等於讓回測看到未來；而排除卻不計數，
    會讓「as-of 之後證據變少」與「本來就沒證據」在下游同形（L13）。
    """
    selection = select_point_in_time_evidence([BEFORE, UNDATED], as_of=AS_OF)
    assert {r.ref for r in selection.kept} == {BEFORE.ref}
    assert {r.ref for r in selection.excluded_undated} == {UNDATED.ref}
    # INV-3：每個 filtering stage 都要能回答 input／accepted／filtered／reasons
    assert selection.input_count == 2
    assert selection.accepted_count == 1
    assert selection.filtered_count == 1
    assert selection.reasons() == {"published_after_as_of": 0, "undated": 1}


def test_current_view_does_not_filter() -> None:
    """`as_of=None` 是「當前視角」——不篩，也不假裝有做 point-in-time。"""
    selection = select_point_in_time_evidence([BEFORE, AFTER, UNDATED], as_of=None)
    assert selection.accepted_count == 3
    assert selection.filtered_count == 0


# ---------------------------------------------------------------------------
# 2. ResearchContext 不接受污染的證據
# ---------------------------------------------------------------------------

def test_context_rejects_leaked_future_evidence() -> None:
    """繞過篩選、直接把未來證據塞進 kept，`ResearchContext` 必須拒收。

    篩選函式是好公民走的路；這一條守的是**沒走那條路的人**。
    """
    with pytest.raises(ContractViolation, match="as-of"):
        _context(EvidenceSelection(kept=(BEFORE, AFTER)), as_of=AS_OF)


def test_context_rejects_leaked_undated_evidence() -> None:
    with pytest.raises(ContractViolation, match="as-of"):
        _context(EvidenceSelection(kept=(BEFORE, UNDATED)), as_of=AS_OF)


def test_digest_changes_when_as_of_changes() -> None:
    """同一批證據、不同 as_of ＝ 不同的研究視角 ＝ 不同的 digest。"""
    early = _context(select_point_in_time_evidence([BEFORE, AFTER], as_of=AS_OF),
                     as_of=AS_OF)
    late = _context(select_point_in_time_evidence([BEFORE, AFTER], as_of=date(2026, 8, 1)),
                    as_of=date(2026, 8, 1))
    assert early.digest != late.digest


# ---------------------------------------------------------------------------
# 3. 保險絲：不支援 as-of 時必須拋，不得靜默回傳當前資料
# ---------------------------------------------------------------------------

COMPANY = CompanyId("co:coherent")

#: 每個帶 `as_of` 的 provider 方法，配一個「除了 as_of 之外都合法」的呼叫。
AS_OF_CALLS = {
    "get_company_structural_context": lambda p, as_of: p.get_company_structural_context(
        COMPANY, as_of=as_of),
    "get_bottlenecks": lambda p, as_of: p.get_bottlenecks(as_of=as_of),
    "get_dependency_paths": lambda p, as_of: p.get_dependency_paths(COMPANY, as_of=as_of),
    "get_substitution_paths": lambda p, as_of: p.get_substitution_paths(
        COMPANY, as_of=as_of),
    "get_supply_exposure": lambda p, as_of: p.get_supply_exposure(
        COMPANY, direction="upstream", as_of=as_of),
}


def test_as_of_call_table_covers_every_as_of_method() -> None:
    """新增帶 `as_of` 的 provider 方法卻忘了測 → 這條會紅。"""
    assert set(AS_OF_CALLS) == set(AS_OF_METHODS)


@pytest.mark.parametrize("method", sorted(AS_OF_CALLS))
def test_as_of_raises_when_unsupported(method: str) -> None:
    """**L13：成功與失敗不得在同一個訊號上同形。**

    「回傳了資料」若同時代表「as-of 生效」與「as-of 被忽略」，回測就會靜默看到未來。
    Engine A 今天沒有 as-of 能力（`published_at` 覆蓋率 58%），所以這條保險絲
    現在就要在——而不是等 Phase 6 才想起來。
    """
    provider = FakeGraphResearchProvider(supports_as_of=False)
    with pytest.raises(PointInTimeUnsupported):
        AS_OF_CALLS[method](provider, AS_OF)


def test_unsupported_provider_still_answers_current_view() -> None:
    """保險絲只擋 as-of，不擋當前視角——否則等於把整個 provider 關掉。"""
    provider = FakeGraphResearchProvider(supports_as_of=False)
    rows = provider.get_bottlenecks()
    assert rows and rows[0].evidence


def test_as_of_capable_provider_actually_filters() -> None:
    """支援 as-of 的 provider 必須**真的篩**，不是把參數收下就算數。"""
    provider = as_of_capable(FakeGraphResearchProvider())
    context = provider.get_company_structural_context(
        CompanyId("co:coherent"), as_of=AS_OF
    )
    refs = {r.ref for r in context.evidence}
    assert "sec://0001-2026-07-05" not in refs      # 7/5 的 filing 不得出現
    assert "graph://claim/undated" not in refs      # 未標日期的也不得出現
    assert "graph://assertion/e1" in refs
