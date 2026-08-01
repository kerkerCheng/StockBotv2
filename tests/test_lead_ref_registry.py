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
    registry = get_lead_ref_registry()
    store = json.loads(
        (ROOT / "library" / "leads" / "pending_leads.json").read_text(encoding="utf-8")
    )
    existing = {
        key
        for lead in store["leads"].values()
        for key in (lead.get("refs") or {})
    }
    assert len(existing) == 56, "新增歷史鍵時必須同步登記用途"
    assert existing <= set(registry.keys)
    assert len(registry.keys) >= 56


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
