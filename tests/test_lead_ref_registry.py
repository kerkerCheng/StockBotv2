"""Lead refs 封閉字彙：防止 metadata 寫得進、讀取端卻永遠看不到。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine_b import leads
from engine_b.lead_refs import (
    LeadRefError,
    LeadRefRegistry,
    get_lead_ref_registry,
    validate_ref_updates,
)


ROOT = Path(__file__).resolve().parent.parent


def test_shipped_registry_covers_every_existing_authority_key() -> None:
    """既有資料裡出現過的每個 ref key 都必須已登記。

    刻意不斷言 key 的精確數量：用已登記的 key 寫 metadata 是日常操作，
    只要有 lead 第一次用到某個既有 key，distinct 數就會變，硬編碼的計數
    因此會在完全正常的使用下誤報，而它並不比覆蓋關係多擋任何東西
    （寫入端另有 validate_ref_updates 當第一道攔截）。
    """
    registry = get_lead_ref_registry()
    store = json.loads(
        (ROOT / "library" / "leads" / "pending_leads.json").read_text(encoding="utf-8")
    )
    existing = {
        key
        for lead in store["leads"].values()
        for key in (lead.get("refs") or {})
    }
    assert existing, "應至少讀到一個既有 ref key"
    unregistered = sorted(existing - set(registry.keys))
    assert not unregistered, (
        f"未登記的 ref key：{unregistered}；請先在 config/lead_ref_keys.json 登記用途"
    )


def test_unknown_key_is_rejected_with_nearest_registered_name() -> None:
    with pytest.raises(LeadRefError) as excinfo:
        validate_ref_updates({"park_reason": "typo"})
    message = str(excinfo.value)
    assert "parked_reason" in message
    assert "config/lead_ref_keys.json" in message


def test_registry_validates_value_types() -> None:
    assert validate_ref_updates({"outcome": "original_obtained"}) == {
        "outcome": "original_obtained"
    }
    assert validate_ref_updates({"campaign_ids": ["c1", "c2"]}) == {
        "campaign_ids": ["c1", "c2"]
    }
    with pytest.raises(LeadRefError, match="list"):
        validate_ref_updates({"campaign_ids": "c1"})


def test_advance_rejects_unknown_ref_before_mutating_status() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="test", url="https://example.com/lead")
    leads.triage(store, lead_id, go=True, tier=3, reason="test")

    with pytest.raises(LeadRefError):
        leads.advance(store, lead_id, "researching", ref={"park_reason": "typo"})

    assert store["leads"][lead_id]["status"] == "triaged_go"
    assert store["leads"][lead_id]["refs"] == {}


def test_registry_rejects_duplicate_or_unknown_value_type() -> None:
    with pytest.raises(LeadRefError, match="未知 value_type"):
        LeadRefRegistry.from_payload(
            {
                "version": 1,
                "categories": {
                    "test": {
                        "key": {"value_type": "object", "description": "x"}
                    }
                },
            }
        )


def test_a_raw_evidence_ref_must_be_a_single_path_at_write_time() -> None:
    """2026-10-07 事發：`trace_attempts_ref` 寫成「library/raw/…txt（說明）、…」——寫入時照收，當天 daily 的備份才
    fail closed（備份分不出說明與路徑注入）。寫入端與備份端同一條判斷（`state_files.raw_evidence_ref`）：
    以 library/raw/ 開頭就必須是單一安全路徑；說明寫在前面（「已查：…」）或另放就照收。"""
    with pytest.raises(LeadRefError, match="單一路徑"):
        validate_ref_updates({"trace_attempts_ref": "library/raw/aaoi_8_k_20260821.txt（ATM 6 億美元）、aaoi_8_k_20260910.txt"})
    with pytest.raises(LeadRefError, match="單一路徑"):
        validate_ref_updates({"trace_trigger_entities": ["AAOI", "library/raw/../secrets.txt"]})
    assert validate_ref_updates({"trace_attempts_ref": "library/raw/aaoi_8_k_20260821.txt"}) == {
        "trace_attempts_ref": "library/raw/aaoi_8_k_20260821.txt"}
    prose = "已查：library/raw/aaoi_8_k_20260821.txt（ATM 6 億美元）、aaoi_8_k_20260910.txt（購地）"
    assert validate_ref_updates({"trace_attempts_ref": prose}) == {"trace_attempts_ref": prose}


def test_advance_with_an_unsafe_raw_ref_leaves_the_lead_untouched() -> None:
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="test", url="https://example.com/lead")
    leads.triage(store, lead_id, go=True, tier=3, reason="test")
    with pytest.raises(LeadRefError):
        leads.advance(store, lead_id, "parked", ref={"trace_attempts_ref": "library/raw/a.txt 另見 b.txt"})
    assert store["leads"][lead_id]["status"] == "triaged_go"
    assert store["leads"][lead_id]["refs"] == {}
