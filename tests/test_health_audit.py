"""Pure-function tests for query/health_audit.py (no Neo4j / SQLite needed)."""

from __future__ import annotations

import json
import sqlite3
from datetime import date

from query.health_audit import (
    active_edge_keys_from_manifests,
    engine_c_freshness,
    l7_field_gaps,
    lifecycle_due,
    load_resolution_hashes,
    split_conflicts_by_resolution,
    ticker_map_gaps,
)


def _entry(**overrides) -> dict:
    entry = {
        "status": "active",
        "memo": "thesis/x_lane_memo.md",
        "next_check": "2026-10-15",
        "check_interval_days": 90,
    }
    entry.update(overrides)
    return entry


def test_lifecycle_due_selects_expired_and_review_required() -> None:
    lifecycle = {
        "fresh": _entry(next_check="2026-12-01"),
        "expired": _entry(next_check="2026-07-01"),
        "today": _entry(next_check="2026-07-18"),
        "review": _entry(status="review_required", next_check="2026-08-27"),
        "broken_date": _entry(next_check="not-a-date"),
    }

    due_ids = [d["thesis_id"] for d in lifecycle_due(lifecycle, date(2026, 7, 18))]

    assert due_ids == ["broken_date", "expired", "review", "today"]


def test_l7_field_gaps_flags_missing_fields() -> None:
    complete = "**核查頻率與觸發動作：** 每週掃描；觸發 → 48 小時內人工決策。"
    assert l7_field_gaps(complete) == []

    missing_action = "核查頻率：每季一次。"
    assert l7_field_gaps(missing_action) == ["觸發後48h動作"]

    assert l7_field_gaps("完全沒寫") == ["核查頻率", "觸發後48h動作"]


def test_ticker_map_gaps_treats_none_mapping_as_covered() -> None:
    ticker_map = {"co:coherent": "COHR", "co:anthropic": None}
    company_ids = ["co:coherent", "co:anthropic", "co:newco"]

    assert ticker_map_gaps(company_ids, ticker_map) == ["co:newco"]


def test_active_edge_keys_from_manifests_reads_evidence_json(tmp_path) -> None:
    edge_key = "edge:" + "a" * 64
    (tmp_path / "x_lane_memo.evidence.json").write_text(
        json.dumps({"edges": [{"edge_key": edge_key}]}), encoding="utf-8"
    )
    (tmp_path / "broken.evidence.json").write_text("{not json", encoding="utf-8")

    assert active_edge_keys_from_manifests(tmp_path) == {edge_key}


def test_split_conflicts_by_resolution_honors_hash_match(tmp_path) -> None:
    conflicts = [
        {"conflict_id": "conflict_resolved", "candidate_set_hash": "hash1"},
        {"conflict_id": "conflict_stale", "candidate_set_hash": "hash2-new"},
        {"conflict_id": "conflict_open", "candidate_set_hash": "hash3"},
    ]
    (tmp_path / "conflict_resolved.json").write_text(
        json.dumps({"conflict_id": "conflict_resolved", "candidate_set_hash": "hash1"}),
        encoding="utf-8",
    )
    (tmp_path / "conflict_stale.json").write_text(
        json.dumps({"conflict_id": "conflict_stale", "candidate_set_hash": "hash2-old"}),
        encoding="utf-8",
    )

    unresolved, stale = split_conflicts_by_resolution(
        conflicts, load_resolution_hashes(tmp_path)
    )

    assert [c["conflict_id"] for c in unresolved] == ["conflict_open"]
    assert [c["conflict_id"] for c in stale] == ["conflict_stale"]


def test_engine_c_freshness_reports_stale_and_missing() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE financial_snapshots (ticker TEXT, snapshot_date TEXT)"
    )
    conn.executemany(
        "INSERT INTO financial_snapshots VALUES (?, ?)",
        [("COHR", "2026-07-17"), ("COHR", "2026-07-01"), ("LITE", "2026-06-01")],
    )

    result = engine_c_freshness(
        conn, ["COHR", "LITE", "AXTI"], today=date(2026, 7, 18), stale_days=7
    )

    assert result["stale"] == [("LITE", 47)]
    assert result["missing"] == ["AXTI"]
    assert result["tracked"] == 3
