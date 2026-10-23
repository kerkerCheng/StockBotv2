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


def test_semantic_backfill_accepts_lead_advanced_without_triage(tmp_path, monkeypatch) -> None:
    """`advance` 直接推進到 triaged_go 的 lead 帶 `triage: None`（鍵在、值是 None）——classification-health
    指名本腳本當它的消費端，所以本腳本必須吃得下這種 lead（2026-10-04 decompose 的 11 條在這裡 TypeError）。"""
    leads_path = tmp_path / "pending_leads.json"
    packet_path = tmp_path / "decompose_backfill.json"
    store = leads.empty_store()
    lead_id, _ = leads.register(store, source="decompose:test", url="decompose://test/layer")
    leads.advance(store, lead_id, "triaged_go")
    assert store["leads"][lead_id]["triage"] is None
    assert leads.classification_gaps(store)
    leads.save(store, leads_path)
    packet_path.write_text(json.dumps({lead_id: {
        "content_type": "structural_fact", "decision_impact": "candidate_set", "reason": "未知層：誰供應它",
    }}), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", [
        "backfill_lead_classification.py", "--leads", str(leads_path), "--from-json", str(packet_path), "--apply",
    ])
    assert backfill.main() == 0

    reloaded = leads.load(leads_path)
    record = reloaded["leads"][lead_id]["triage"]["classification"]
    assert record["decision_impact"] == "candidate_set"
    assert record["classified_by"] == "backfill_semantic_v1"
    assert leads.classification_gaps(reloaded) == []


def _parked_legacy(store, url: str, *, go: bool = True) -> str:
    """分類欄位出現前就停放的舊 lead：triage 沒有 classification、停放時帶追源 receipt（叫得回 pq1）。
    直接改 store，不走 `advance`——停放會順手建追源 watch，測試不碰真的 watch registry。"""
    lead_id, _ = leads.register(store, source="x:test", url=url)
    leads.triage(store, lead_id, go=go, tier=4, reason="legacy")
    lead = store["leads"][lead_id]
    lead["status"] = "parked"
    lead["refs"]["trace_status"] = "original_obtained"
    return lead_id


def test_dormant_gap_is_red_before_requeue_and_backfill_closes_it(tmp_path, monkeypatch, capsys) -> None:
    """2026-10-23：daily 分類檢查 10-17、10-20、10-22、10-23 都紅，每次是被 watch 叫回的另一則舊 lead。
    停放的那一池要在排回之前就現形、而且補得進去——否則每叫醒一則就紅一天。"""
    from engine_b import cli

    leads_path = tmp_path / "pending_leads.json"
    packet_path = tmp_path / "dormant_backfill.json"
    store = leads.empty_store()
    dormant = _parked_legacy(store, "https://x.com/test/status/dormant")
    filtered = _parked_legacy(store, "https://x.com/test/status/filtered", go=False)
    leads.save(store, leads_path)

    assert leads.classification_gaps(store) == []                                # active 一則都沒有……
    assert [g["lead_id"] for g in leads.dormant_classification_gaps(store)] == [dormant]   # ……休眠的照樣紅；no_go 不算
    assert cli.main(["--leads", str(leads_path), "classification-health"]) == 2
    health = json.loads(capsys.readouterr().out)
    assert health["status"] == "error" and health["dormant_unclassified_count"] == 1
    assert health["dormant_consumer"] and "--from-json" in health["dormant_consumer"]

    packet_path.write_text(json.dumps({dormant: {
        "content_type": "structural_fact", "decision_impact": "confidence_only", "reason": "停放前已讀原文",
    }}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "backfill_lead_classification.py", "--leads", str(leads_path), "--from-json", str(packet_path), "--apply",
    ])
    assert backfill.main() == 0
    assert "停放中叫得回來的缺分類 0" in capsys.readouterr().out

    reloaded = leads.load(leads_path)
    assert leads.dormant_classification_gaps(reloaded) == []
    assert cli.main(["--leads", str(leads_path), "classification-health"]) == 0
    capsys.readouterr()
    # 叫回 pq1 之後分類跟著走（requeue_trace 不寫 triage），active 也不紅
    leads.requeue_trace(reloaded, dormant, trigger="related_triaged_lead:lead_x", reason="共用實體")
    assert leads.classification_gaps(reloaded) == []

    # FILTER 照拒：no_go 不寫 classification
    packet_path.write_text(json.dumps({filtered: {
        "content_type": "sentiment", "decision_impact": "confidence_only", "reason": "x",
    }}), encoding="utf-8")
    try:
        backfill.main()
    except ValueError as exc:
        assert "非 no_go" in str(exc)
    else:
        raise AssertionError("no_go 的停放 lead 不得被補分類")
