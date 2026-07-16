"""Live Phase I acceptance smoke for evidence-scoped conflict gating.

Creates one clearly namespaced temporary SIVE edge, verifies that an
unreferenced conflict does not block a memo while a cited high-risk conflict
does, and removes every temporary graph object in a finally block.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from neo4j import GraphDatabase

from thesis.evidence_manifest import (
    build_context_inventory,
    evaluate_evidence_gates,
    validate_envelope,
)


EDGE_KEY = "edge:phase1_sive_unreferenced_conflict_smoke"
VENDOR_ID = "test:phase1_sive_vendor"
ASSERTION_IDS = [
    "phase1_sive_conflict_true_e1",
    "phase1_sive_conflict_false_e1",
]


def _cleanup(session) -> None:
    session.run(
        "MATCH (a:EdgeAssertion) WHERE a.id IN $ids DETACH DELETE a",
        ids=ASSERTION_IDS,
    ).consume()
    session.run(
        "MATCH ()-[r]->() WHERE r.edge_key = $edge_key DELETE r",
        edge_key=EDGE_KEY,
    ).consume()
    session.run(
        "MATCH (n:Entity {id: $id}) DETACH DELETE n",
        id=VENDOR_ID,
    ).consume()


def _install(session) -> None:
    session.run(
        """
        MATCH (sivers:Entity {id: 'co:sivers_semiconductors'})
        MERGE (vendor:Entity {id: $vendor_id})
        SET vendor.name = 'Phase I Acceptance Test Vendor'
        MERGE (vendor)-[r:SUPPLIES_TO {edge_key: $edge_key}]->(sivers)
        SET r.id = $edge_key,
            r.relation = 'supplies_to',
            r.confidence = 1.0,
            r.attributes = '{}',
            r.open_conflict_attributes = ['sole_source'],
            r.attribute_resolution_meta_json = '{}'
        """,
        vendor_id=VENDOR_ID,
        edge_key=EDGE_KEY,
    ).consume()
    for assertion_id, value, source_id, source_doc_id in (
        (
            ASSERTION_IDS[0],
            True,
            "enablence_sivers_onet_ofc_pr_2026_03_17_s2",
            "enablence_sivers_onet_ofc_pr_2026_03_17",
        ),
        (
            ASSERTION_IDS[1],
            False,
            "sivers_ar_2025_photonics_excerpt_s8",
            "sivers_ar_2025_photonics_excerpt",
        ),
    ):
        session.run(
            """
            MATCH (sd:SourceDoc {id: $source_doc_id})
            MERGE (a:EdgeAssertion {id: $assertion_id})
            SET a.edge_key = $edge_key,
                a.src_id = $vendor_id,
                a.relation = 'supplies_to',
                a.dst_id = 'co:sivers_semiconductors',
                a.attributes = $attributes,
                a.confidence = 0.9,
                a.source_ids = [$source_id],
                a.source_doc_id = $source_doc_id
            MERGE (a)-[:CITES]->(sd)
            """,
            assertion_id=assertion_id,
            edge_key=EDGE_KEY,
            vendor_id=VENDOR_ID,
            attributes=json.dumps({"sole_source": value}),
            source_id=source_id,
            source_doc_id=source_doc_id,
        ).consume()


def _claim_item() -> dict:
    return {
        "evidence_ref": "E1",
        "type": "claim",
        "claim_id": "enablence_sivers_onet_ofc_pr_2026_03_17_cl1",
        "edge_key": None,
        "attributes": [],
        "assertion_ids": [],
        "source_ids": ["enablence_sivers_onet_ofc_pr_2026_03_17_s2"],
        "purpose": "control evidence",
    }


def main() -> int:
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("NEO4J_PASSWORD is required", file=sys.stderr)
        return 1
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )
    cleanup_verified = False
    try:
        with driver.session() as session:
            _cleanup(session)
            _install(session)

        inventory = build_context_inventory(
            driver,
            company_id="co:sivers_semiconductors",
            supply_limit=100,
        )
        if EDGE_KEY not in inventory["edges"]:
            raise AssertionError("temporary SIVE conflict edge was not inventoried")

        unreferenced = {
            "memo_markdown": "# Control memo [E1]",
            "evidence_items": [_claim_item()],
        }
        validation_a = validate_envelope(unreferenced, inventory)
        gate_a = evaluate_evidence_gates(validation_a, inventory)

        referenced = {
            "memo_markdown": "# Conflict memo [E1] [E2]",
            "evidence_items": [
                _claim_item(),
                {
                    "evidence_ref": "E2",
                    "type": "edge",
                    "claim_id": None,
                    "edge_key": EDGE_KEY,
                    "attributes": ["sole_source"],
                    "assertion_ids": [ASSERTION_IDS[0]],
                    "source_ids": [
                        "enablence_sivers_onet_ofc_pr_2026_03_17_s2"
                    ],
                    "purpose": "exercise high-risk conflict gate",
                },
            ],
        }
        validation_b = validate_envelope(referenced, inventory)
        gate_b = evaluate_evidence_gates(validation_b, inventory)

        if not validation_a["ok"] or not gate_a["promotion_pass"]:
            raise AssertionError("unreferenced conflict incorrectly blocked the memo")
        if not validation_b["ok"] or gate_b["promotion_pass"]:
            raise AssertionError("referenced high-risk conflict failed to block promotion")
        if not any(
            note.get("code") == "open_conflict"
            for note in gate_b["annotations"].get("E2", [])
        ):
            raise AssertionError("referenced conflict lacks an auditable annotation")

        print(
            json.dumps(
                {
                    "unreferenced_conflict_promotion_pass": gate_a["promotion_pass"],
                    "referenced_conflict_promotion_pass": gate_b["promotion_pass"],
                    "referenced_annotations": gate_b["annotations"].get("E2"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    finally:
        try:
            with driver.session() as session:
                _cleanup(session)
                remaining = session.run(
                    """
                    OPTIONAL MATCH ()-[r]->() WHERE r.edge_key = $edge_key
                    WITH count(r) AS relationships
                    OPTIONAL MATCH (a:EdgeAssertion) WHERE a.id IN $ids
                    RETURN relationships, count(a) AS assertions
                    """,
                    edge_key=EDGE_KEY,
                    ids=ASSERTION_IDS,
                ).single()
                cleanup_verified = bool(
                    remaining
                    and remaining["relationships"] == 0
                    and remaining["assertions"] == 0
                )
        finally:
            driver.close()
        if not cleanup_verified:
            print("WARNING: temporary graph cleanup could not be verified", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
