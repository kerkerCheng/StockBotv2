"""pq1 classification migration 的 deterministic／semantic 分工。"""
from __future__ import annotations

import json
import sys

from engine_b import leads
from scripts import backfill_lead_classification as backfill


def test_active_backfill_restores_history_and_applies_audited_packet(
    tmp_path, monkeypatch, capsys
) -> None:
    leads_path = tmp_path / "pending_leads.json"
    packet_path = tmp_path / "active_backfill.json"
    store = leads.empty_store()
    restored_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/restored"
    )
    supplied_id, _ = leads.register(
        store, source="x:test", url="https://x.com/test/status/supplied"
    )
    leads.triage(store, restored_id, go=True, tier=4, reason="legacy")
    leads.triage(store, supplied_id, go=True, tier=4, reason="legacy")
    store["leads"][restored_id]["triage_history"] = [{
        "status": "parked",
        "triage": {
            "classification": {
                "content_type": "structural_fact",
                "decision_impact": "candidate_set",
                "classified_by": "semantic_v1",
                "classified_at": "2026-08-21T00:00:00+00:00",
                "reason": "既有語意 receipt",
            }
        },
    }]
    leads.save(store, leads_path)
    packet_path.write_text(json.dumps({
        "schema_version": 1,
        "items": {
            supplied_id: {
                "content_type": "financial_fact",
                "decision_impact": "confidence_only",
                "reason": "受控語意 backfill",
            }
        },
    }), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", [
        "backfill_lead_classification.py",
        "--leads", str(leads_path),
        "--from-json", str(packet_path),
        "--apply",
    ])
    assert backfill.main() == 0

    reloaded = leads.load(leads_path)
    restored = reloaded["leads"][restored_id]["triage"]["classification"]
    supplied = reloaded["leads"][supplied_id]["triage"]["classification"]
    assert restored["restored_by"] == "backfill_history_restore_v1"
    assert supplied["classified_by"] == "backfill_semantic_v1"
    assert supplied["backfill_ref"] == packet_path.name
    assert leads.classification_gaps(reloaded) == []
    assert "active 缺分類 0" in capsys.readouterr().out

    # 完全相同的 migration packet 可安全重跑；不得把 idempotent replay 當覆寫衝突。
    assert backfill.main() == 0
    assert "本次補分類 0" in capsys.readouterr().out
