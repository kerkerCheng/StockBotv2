"""別的會計年度的共識變動，不該把校準在 0y 的判斷標成「需複查」（2026-09-19，七缺陷之 2 的後半）。

事發：`THESIS_POLICY[consensus] = review_required` 不看年度，而 `price/pe_forward` 推出來的
代理量是 **+1y**——於是每次 forward year rollover（每年必然發生一次），每一檔都會收到一個
與自己 base 無關的年度觸發的複查要求。實測 16 檔有 2 檔正在收這種通知（LITE、AXTI），
**而 AXTI 是已研究到底的兩檔之一——假警報正落在最該信任的那兩份判讀上。**

⚠ **這不是把跨年度的訊號拿掉。** 被降級的事件仍然計數（`excluded_changes`）、仍然逐條進
`notes`。COHR 的 thesis 講 FY28 而模型只有 FY27 一格——那個缺口的解是多年橋（ROADMAP Phase 7），
不是讓一個對每一檔都會亮的訊號一直響（L14-4：恆亮＝零鑑別力）。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alpha.refresh import (
    ARTIFACT_AXIS, CONSENSUS, FINANCIAL_ACTUAL, KIND_JUDGMENT, THESIS_ARTIFACT_ID,
    ArtifactDependency, ChangeEvent, resolve_refresh,
)
from alpha.refresh.resolver import BASE_FISCAL_LABEL, _is_off_year_consensus

TODAY = date(2026, 9, 19)
JUDGED_AT = datetime(2026, 9, 10, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 18, tzinfo=timezone.utc)


def _event(**kw) -> ChangeEvent:
    base = dict(change_type=CONSENSUS, ticker="LITE", company_id="co:lumentum",
                authority="engine_c://consensus_estimates",
                changed_ref="engine_c://consensus_estimate/LITE/revenue/2028-06-30",
                observed_at=LATER, detail="FY2028 revenue 共識 +1.8%")
    base.update(kw)
    return ChangeEvent(**base)


def _artifacts() -> list[ArtifactDependency]:
    return [
        ArtifactDependency(artifact_type="thesis", artifact_id=THESIS_ARTIFACT_ID, label="thesis",
                           kind=KIND_JUDGMENT, established_at=JUDGED_AT),
        ArtifactDependency(artifact_type=ARTIFACT_AXIS, artifact_id="expectation_gap", label="Q4",
                           kind=KIND_JUDGMENT, established_at=JUDGED_AT),
    ]


def _run(*changes: ChangeEvent):
    return resolve_refresh(ticker="LITE", company_id="co:lumentum", artifacts=_artifacts(),
                           changes=list(changes), today=TODAY)


def test_the_predicate_only_fires_on_a_named_other_year() -> None:
    assert BASE_FISCAL_LABEL == "0y"
    assert _is_off_year_consensus(_event(fiscal_relative_label="+1y"))
    assert not _is_off_year_consensus(_event(fiscal_relative_label="0y"))
    # 拿不到年度 → 照舊觸發（fail open：少報一個真變動比靜默吞掉更糟）
    assert not _is_off_year_consensus(_event(fiscal_relative_label=None))
    # 只對 consensus 生效
    assert not _is_off_year_consensus(_event(change_type=FINANCIAL_ACTUAL, fiscal_relative_label="+1y"))


def test_an_other_year_consensus_move_does_not_force_a_review() -> None:
    report = _run(_event(fiscal_relative_label="+1y"))
    assert report.artifact(f"thesis:{THESIS_ARTIFACT_ID}").state == "current"
    assert report.artifact("axis:expectation_gap").state == "current"


def test_it_is_counted_and_spelled_out_not_silently_dropped() -> None:
    """INV-3：被降級的不得消失——要進計數，也要進 notes。"""
    report = _run(_event(fiscal_relative_label="+1y"))
    assert report.excluded_changes.get("consensus_other_fiscal_year") == 1
    assert any("印出來但不觸發複查" in n and "+1y" in n for n in report.notes)
    assert any("Phase 7" in n for n in report.notes)      # 缺口的去向指得出來（INV-4）


def test_the_base_year_still_forces_a_review() -> None:
    """**這個 gate 必須會滅**（L14-4）：0y 的共識變動照舊觸發。"""
    report = _run(_event(fiscal_relative_label="0y"))
    assert report.artifact(f"thesis:{THESIS_ARTIFACT_ID}").state == "review_required"


def test_an_unlabelled_consensus_move_still_forces_a_review() -> None:
    report = _run(_event(fiscal_relative_label=None))
    assert report.artifact(f"thesis:{THESIS_ARTIFACT_ID}").state == "review_required"


def test_other_change_classes_are_untouched() -> None:
    report = _run(_event(change_type=FINANCIAL_ACTUAL, fiscal_relative_label="+1y",
                         changed_ref="engine_c://manual_observation/mo_x"))
    assert report.artifact(f"thesis:{THESIS_ARTIFACT_ID}").state == "review_required"
    assert "consensus_other_fiscal_year" not in report.excluded_changes
