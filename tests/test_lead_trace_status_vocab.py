"""`trace_status` 封閉字彙與 onboard 候選。

回歸錨點是 2026-08-25 實測的兩個缺口：
1. `trace_status` 是自由字串，單一 session 內就長出 9 個同義詞；而 `trace_backlog`
   用 terminal 值決定 lead 去留——同義詞不會報錯，只會讓已完成的 lead 永遠掛著。
2. pq2 六個 collector 沒有一個負責「這家公司該不該註冊」，於是研究中點名卻不在
   registry 的公司沒有任何浮現路徑。
"""
from __future__ import annotations

import pytest

from engine_b import leads
from engine_b.lead_refs import (
    LeadRefError,
    get_trace_status_registry,
    validate_ref_updates,
)


def test_every_registered_status_declares_terminality() -> None:
    registry = get_trace_status_registry()
    assert registry.terminal
    assert registry.non_terminal
    # terminal 與非 terminal 不可重疊，否則 trace_backlog 的判斷沒有定義。
    assert not (registry.terminal & registry.non_terminal)


def test_write_rejects_retired_synonym_and_names_the_canonical_value() -> None:
    """同義詞之所以危險，是它讓寫的人以為表達了一個沒被記錄的區別。

    實例：`primary_source_obtained` 會落到終結的 `original_obtained`，
    但作者真正要表達的是非終結的 `awaiting_named_disclosure`。
    """

    with pytest.raises(LeadRefError, match="original_obtained"):
        validate_ref_updates({"trace_status": "primary_source_obtained"})


def test_write_rejects_typo_with_suggestion() -> None:
    with pytest.raises(LeadRefError, match="original_obtained"):
        validate_ref_updates({"trace_status": "original_obtaind"})


def test_registered_value_passes_through_unchanged() -> None:
    cleaned = validate_ref_updates({"trace_status": "awaiting_named_disclosure"})
    assert cleaned["trace_status"] == "awaiting_named_disclosure"


def test_migration_path_still_resolves_legacy_values() -> None:
    """既有資料要能被讀懂——遷移用 allow_alias=True，寫入用 False。"""

    registry = get_trace_status_registry()
    assert registry.resolve("primary_source_obtained") == "original_obtained"
    assert registry.resolve("quote_misattributed") == "contradicts"


def test_unknown_status_is_treated_as_non_terminal() -> None:
    """拼錯要讓 lead 留在 backlog 被看見，不是靜默消失（fail loud）。"""

    assert get_trace_status_registry().is_terminal("who_knows") is False


def _store(leads_map: dict) -> dict:
    return {"leads": leads_map, "harvest_log": [], "source_state": {}}


def _lead(lead_id: str, **kwargs) -> dict:
    base = {
        "lead_id": lead_id,
        "status": "parked",
        "title": "",
        "raw_text": "",
        "source": "",
        "url": "",
        "refs": {},
    }
    base.update(kwargs)
    return base


def test_terminal_status_leaves_trace_backlog() -> None:
    store = _store({
        "lead_done": _lead("lead_done", refs={"trace_status": "original_obtained"}),
        "lead_waiting": _lead(
            "lead_waiting",
            refs={"trace_status": "awaiting_named_disclosure"},
        ),
    })
    ids = {row["lead_id"] for row in leads.trace_backlog(store)}
    assert ids == {"lead_waiting"}


def test_onboard_candidate_from_plain_text_name() -> None:
    """cashtag regex 抓不到「Largan Precision (3008)」——正是促成本機制的案例。"""

    store = _store({
        "lead_fau": _lead(
            "lead_fau",
            title="FAU bottlenecks for CPO",
            refs={"onboard_candidate_names": ["Largan Precision (3008.TW)"]},
        )
    })
    rows = leads.onboard_candidates(store)
    manual = [row for row in rows if row["detected_by"] == "manual"]
    assert [row["ticker"] for row in manual] == ["Largan Precision (3008.TW)"]


def test_untriaged_and_rejected_leads_do_not_drive_onboarding() -> None:
    """沒被判斷過、或已判定不值得的 lead，不該推動 registry 變更。"""

    store = _store({
        "lead_pending": _lead(
            "lead_pending",
            status="pending",
            refs={"onboard_candidate_names": ["Never Seen Corp"]},
        ),
        "lead_no_go": _lead(
            "lead_no_go",
            status="triaged_no_go",
            refs={"onboard_candidate_names": ["Rejected Corp"]},
        ),
    })
    assert leads.onboard_candidates(store) == []
