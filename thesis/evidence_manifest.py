"""Build and validate the evidence contract behind a Lane Memo.

The model may draft prose and select evidence, but it cannot invent graph IDs or
choose the report grade.  This module resolves every selected item against the
exact inventory supplied to that model and applies evidence-scoped quality
gates afterwards.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "schema" / "thesis_evidence_manifest.schema.json"
EXTRACTIONS_DIR = ROOT / "extractions"
HIGH_RISK_ATTRIBUTES = {
    "sole_source",
    "substitutability",
    "structural_lead_time_weeks",
}
_EVIDENCE_REF_RE = re.compile(r"\[(E[1-9][0-9]*)\]")


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _record_dict(record: Any) -> dict[str, Any]:
    if hasattr(record, "data"):
        return record.data()
    return dict(record)


def _load_source_quotes(extractions_dir: Path = EXTRACTIONS_DIR) -> dict[str, dict]:
    """Load immutable quote text from replayable extraction artifacts."""

    sources: dict[str, dict] = {}
    for path in sorted(extractions_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        source_doc = payload.get("source_doc") or {}
        doc_id = source_doc.get("doc_id")
        for source in payload.get("sources") or []:
            source_id = source.get("id")
            if not source_id:
                continue
            sources[source_id] = {
                "id": source_id,
                "locator": source.get("locator"),
                "quote": source.get("quote"),
                "source_doc_id": doc_id,
                "origin_entity": source_doc.get("origin_entity"),
                "extraction_path": path.relative_to(ROOT).as_posix(),
            }
    return sources


def build_context_inventory(
    driver,
    *,
    company_id: str | None = None,
    supply_limit: int = 50,
    claim_limit: int = 20,
    extractions_dir: Path = EXTRACTIONS_DIR,
) -> dict:
    """Return the stable-ID graph inventory that is sent to the model."""

    focus_company: dict[str, Any] | None = None
    with driver.session() as session:
        if company_id:
            record = session.run(
                "MATCH (n:Entity {id: $id}) RETURN n.id AS id, n.name AS name",
                id=company_id,
            ).single()
            if record:
                focus_company = _record_dict(record)
            edge_records = session.run(
                """
                MATCH (focus:Entity {id: $company_id})-[r]-(other:Entity)
                WHERE r.edge_key IS NOT NULL
                  AND NOT focus:Claim AND NOT other:Claim
                WITH startNode(r) AS src, r, endNode(r) AS dst
                RETURN r.edge_key AS edge_key,
                       src.id AS src_id, src.name AS src_name,
                       type(r) AS relation,
                       dst.id AS dst_id, dst.name AS dst_name,
                       r.attributes AS attributes,
                       r.open_conflict_attributes AS open_conflict_attributes,
                       r.attribute_resolution_meta_json AS attribute_resolution_meta
                ORDER BY coalesce(r.confidence, 0) DESC, r.edge_key
                LIMIT $limit
                """,
                company_id=company_id,
                limit=supply_limit,
            )
        else:
            edge_records = session.run(
                """
                MATCH (src:Entity)-[r]->(dst:Entity)
                WHERE r.edge_key IS NOT NULL
                  AND NOT src:Claim AND NOT dst:Claim
                RETURN r.edge_key AS edge_key,
                       src.id AS src_id, src.name AS src_name,
                       type(r) AS relation,
                       dst.id AS dst_id, dst.name AS dst_name,
                       r.attributes AS attributes,
                       r.open_conflict_attributes AS open_conflict_attributes,
                       r.attribute_resolution_meta_json AS attribute_resolution_meta
                ORDER BY coalesce(r.confidence, 0) DESC, r.edge_key
                LIMIT $limit
                """,
                limit=supply_limit,
            )

        edges: dict[str, dict] = {}
        related_node_ids: set[str] = set()
        for raw in edge_records:
            row = _record_dict(raw)
            key = row["edge_key"]
            edges[key] = {
                "edge_key": key,
                "src_id": row["src_id"],
                "src_name": row["src_name"],
                "relation": row["relation"],
                "dst_id": row["dst_id"],
                "dst_name": row["dst_name"],
                "attributes": _json_object(row.get("attributes")),
                "open_conflict_attributes": sorted(
                    row.get("open_conflict_attributes") or []
                ),
                "attribute_resolution_meta": _json_object(
                    row.get("attribute_resolution_meta")
                ),
                "assertions": {},
            }
            related_node_ids.update((row["src_id"], row["dst_id"]))

        edge_keys = list(edges)
        if edge_keys:
            assertion_records = session.run(
                """
                MATCH (a:EdgeAssertion)
                WHERE a.edge_key IN $edge_keys
                OPTIONAL MATCH (a)-[:CITES]->(sd:SourceDoc)
                RETURN a.id AS id, a.edge_key AS edge_key,
                       a.attributes AS attributes, a.source_ids AS source_ids,
                       a.source_doc_id AS source_doc_id,
                       sd.origin_entity AS origin_entity,
                       properties(sd) AS source_doc
                ORDER BY a.edge_key, a.id
                """,
                edge_keys=edge_keys,
            )
            for raw in assertion_records:
                row = _record_dict(raw)
                edge = edges.get(row["edge_key"])
                if not edge:
                    continue
                edge["assertions"][row["id"]] = {
                    "id": row["id"],
                    "attributes": _json_object(row.get("attributes")),
                    "source_ids": row.get("source_ids") or [],
                    "source_doc_id": row.get("source_doc_id"),
                    "origin_entity": row.get("origin_entity"),
                    "source_doc": row.get("source_doc") or {},
                }

        claim_records = session.run(
            """
            MATCH (c:Claim)
            WHERE ($company_id IS NULL)
               OR c.subject_node_id IN $node_ids
               OR c.subject_edge_key IN $edge_keys
            OPTIONAL MATCH (c)-[:CITES]->(sd:SourceDoc)
            RETURN c.id AS id, c.statement AS statement,
                   c.demand_proof_level AS demand_proof_level,
                   c.disproof_condition AS disproof_condition,
                   c.confidence AS confidence, c.source_ids AS source_ids,
                   c.source_doc_id AS source_doc_id,
                   c.subject_kind AS subject_kind,
                   c.subject_node_id AS subject_node_id,
                   c.subject_edge_key AS subject_edge_key,
                   sd.origin_entity AS origin_entity,
                   properties(sd) AS source_doc
            ORDER BY coalesce(c.confidence, 0) DESC, c.id
            LIMIT $limit
            """,
            company_id=company_id,
            node_ids=sorted(related_node_ids | ({company_id} if company_id else set())),
            edge_keys=edge_keys,
            limit=claim_limit,
        )
        claims: dict[str, dict] = {}
        for raw in claim_records:
            row = _record_dict(raw)
            claims[row["id"]] = row
            claims[row["id"]]["source_ids"] = row.get("source_ids") or []
            claims[row["id"]]["source_doc"] = row.get("source_doc") or {}

        origin_records = session.run(
            """
            MATCH (sd:SourceDoc)
            WHERE sd.origin_entity IS NOT NULL
            RETURN DISTINCT sd.origin_entity AS origin_entity
            ORDER BY origin_entity
            """
        )
        company_origins = [r["origin_entity"] for r in origin_records]

    quote_lookup = _load_source_quotes(extractions_dir)
    source_docs: dict[str, dict] = {}
    for claim in claims.values():
        source_doc_id = claim.get("source_doc_id")
        if source_doc_id:
            source_docs[source_doc_id] = copy.deepcopy(claim.get("source_doc") or {})
    for edge in edges.values():
        for assertion in edge["assertions"].values():
            source_doc_id = assertion.get("source_doc_id")
            if source_doc_id:
                source_docs[source_doc_id] = copy.deepcopy(
                    assertion.get("source_doc") or {}
                )
    needed_source_ids: set[str] = set()
    for claim in claims.values():
        needed_source_ids.update(claim["source_ids"])
    for edge in edges.values():
        for assertion in edge["assertions"].values():
            needed_source_ids.update(assertion["source_ids"])

    sources: dict[str, dict] = {}
    for source_id in sorted(needed_source_ids):
        source = copy.deepcopy(quote_lookup.get(source_id) or {"id": source_id})
        if not source.get("source_doc_id"):
            for claim in claims.values():
                if source_id in claim["source_ids"]:
                    source["source_doc_id"] = claim.get("source_doc_id")
                    source["origin_entity"] = claim.get("origin_entity")
                    source["source_doc"] = claim.get("source_doc") or {}
                    break
            else:
                for edge in edges.values():
                    match = next(
                        (
                            assertion
                            for assertion in edge["assertions"].values()
                            if source_id in assertion["source_ids"]
                        ),
                        None,
                    )
                    if match:
                        source["source_doc_id"] = match.get("source_doc_id")
                        source["origin_entity"] = match.get("origin_entity")
                        source["source_doc"] = match.get("source_doc") or {}
                        break
        source_doc_id = source.get("source_doc_id")
        if source_doc_id in source_docs:
            source["source_doc"] = copy.deepcopy(source_docs[source_doc_id])
            source["origin_entity"] = source["source_doc"].get(
                "origin_entity", source.get("origin_entity")
            )
        sources[source_id] = source

    return {
        "focus_company": focus_company,
        "company_origin_entities": company_origins,
        "claims": claims,
        "edges": edges,
        "sources": sources,
    }


def inventory_to_markdown(inventory: dict) -> str:
    """Render only IDs and evidence facts the model is allowed to cite."""

    lines = ["## 可引用 Evidence Inventory（不得使用清單外 ID）"]
    focus = inventory.get("focus_company") or {}
    if focus:
        lines.append(f"Focus company: {focus.get('name')} (`{focus.get('id')}`)")

    lines.append("\n### Claims")
    for claim in inventory.get("claims", {}).values():
        lines.append(
            f"- claim_id=`{claim['id']}`: {claim.get('statement')} "
            f"| source_ids={claim.get('source_ids') or []} "
            f"| origin={claim.get('origin_entity')}"
        )
        for source_id in claim.get("source_ids") or []:
            source = inventory.get("sources", {}).get(source_id, {})
            lines.append(
                f"  - source_id=`{source_id}` locator={source.get('locator')} "
                f"quote={json.dumps(source.get('quote'), ensure_ascii=False)} "
                f"source_under_audit={bool((source.get('source_doc') or {}).get('source_under_audit'))}"
            )

    lines.append("\n### Canonical edges and per-document assertions")
    for edge in inventory.get("edges", {}).values():
        lines.append(
            f"- edge_key=`{edge['edge_key']}`: {edge.get('src_name')} "
            f"--[{edge.get('relation')}]--> {edge.get('dst_name')} "
            f"| canonical_attributes={edge.get('attributes') or {}} "
            f"| open_conflicts={edge.get('open_conflict_attributes') or []} "
            f"| resolution_meta={edge.get('attribute_resolution_meta') or {}}"
        )
        for assertion in edge.get("assertions", {}).values():
            lines.append(
                f"  - assertion_id=`{assertion['id']}` "
                f"attributes={assertion.get('attributes') or {}} "
                f"source_ids={assertion.get('source_ids') or []} "
                f"origin={assertion.get('origin_entity')}"
            )
            for source_id in assertion.get("source_ids") or []:
                source = inventory.get("sources", {}).get(source_id, {})
                lines.append(
                    f"    - source_id=`{source_id}` locator={source.get('locator')} "
                    f"quote={json.dumps(source.get('quote'), ensure_ascii=False)} "
                    f"source_under_audit={bool((source.get('source_doc') or {}).get('source_under_audit'))}"
                )
    return "\n".join(lines) + "\n"


def validate_envelope(envelope: Any, inventory: dict) -> dict:
    """Validate schema, Markdown refs, and every graph/provenance join."""

    errors: list[str] = []
    resolved: list[dict] = []
    try:
        schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
        schema_errors = sorted(
            Draft202012Validator(schema).iter_errors(envelope),
            key=lambda error: list(error.path),
        )
        errors.extend(
            f"Schema {'.'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in schema_errors
        )
    except (OSError, ValueError) as exc:
        errors.append(f"Evidence schema unavailable: {exc}")

    if not isinstance(envelope, dict):
        return {"ok": False, "errors": errors or ["Envelope must be an object"], "resolved_evidence": []}

    items = envelope.get("evidence_items")
    markdown = envelope.get("memo_markdown")
    if not isinstance(items, list) or not isinstance(markdown, str):
        return {"ok": False, "errors": errors, "resolved_evidence": []}

    manifest_refs = [item.get("evidence_ref") for item in items if isinstance(item, dict)]
    if len(manifest_refs) != len(set(manifest_refs)):
        errors.append("evidence_ref values must be unique")
    markdown_refs = set(_EVIDENCE_REF_RE.findall(markdown))
    manifest_ref_set = {ref for ref in manifest_refs if isinstance(ref, str)}
    missing_in_markdown = manifest_ref_set - markdown_refs
    missing_in_manifest = markdown_refs - manifest_ref_set
    if missing_in_markdown:
        errors.append(f"evidence_ref not cited in Markdown: {sorted(missing_in_markdown)}")
    if missing_in_manifest:
        errors.append(f"Markdown references absent from manifest: {sorted(missing_in_manifest)}")

    for item in items:
        if not isinstance(item, dict):
            continue
        ref = item.get("evidence_ref") or "<unknown>"
        item_type = item.get("type")
        source_ids = item.get("source_ids") or []
        resolved_sources: list[dict] = []
        if item_type == "claim":
            claim = inventory.get("claims", {}).get(item.get("claim_id"))
            if not claim:
                errors.append(f"{ref}: claim_id is outside this context: {item.get('claim_id')}")
                continue
            invalid_sources = set(source_ids) - set(claim.get("source_ids") or [])
            if invalid_sources:
                errors.append(f"{ref}: sources do not belong to claim: {sorted(invalid_sources)}")
            for source_id in source_ids:
                source = inventory.get("sources", {}).get(source_id)
                if not source:
                    errors.append(f"{ref}: source_id is outside this context: {source_id}")
                else:
                    if not str(source.get("quote") or "").strip():
                        errors.append(f"{ref}: source_id has no verbatim quote: {source_id}")
                    resolved_sources.append(copy.deepcopy(source))
            resolved.append(
                {
                    "evidence_ref": ref,
                    "item": copy.deepcopy(item),
                    "claim": copy.deepcopy(claim),
                    "sources": resolved_sources,
                }
            )
            continue

        if item_type != "edge":
            continue
        edge = inventory.get("edges", {}).get(item.get("edge_key"))
        if not edge:
            errors.append(f"{ref}: edge_key is outside this context: {item.get('edge_key')}")
            continue
        assertions = edge.get("assertions", {})
        chosen_assertions: list[dict] = []
        for assertion_id in item.get("assertion_ids") or []:
            assertion = assertions.get(assertion_id)
            if not assertion:
                errors.append(f"{ref}: assertion does not belong to edge: {assertion_id}")
            else:
                chosen_assertions.append(copy.deepcopy(assertion))
        allowed_sources = {
            source_id
            for assertion in chosen_assertions
            for source_id in assertion.get("source_ids") or []
        }
        invalid_sources = set(source_ids) - allowed_sources
        if invalid_sources:
            errors.append(f"{ref}: sources do not belong to selected assertions: {sorted(invalid_sources)}")
        for source_id in source_ids:
            source = inventory.get("sources", {}).get(source_id)
            if not source:
                errors.append(f"{ref}: source_id is outside this context: {source_id}")
            else:
                if not str(source.get("quote") or "").strip():
                    errors.append(f"{ref}: source_id has no verbatim quote: {source_id}")
                resolved_sources.append(copy.deepcopy(source))
        known_attributes = set(edge.get("attributes") or {})
        known_attributes.update(edge.get("open_conflict_attributes") or [])
        known_attributes.update(edge.get("attribute_resolution_meta") or {})
        for assertion in chosen_assertions:
            known_attributes.update(assertion.get("attributes") or {})
        invalid_attributes = set(item.get("attributes") or []) - known_attributes
        if invalid_attributes:
            errors.append(f"{ref}: attributes are not evidenced on edge: {sorted(invalid_attributes)}")
        resolved.append(
            {
                "evidence_ref": ref,
                "item": copy.deepcopy(item),
                "edge": copy.deepcopy(edge),
                "assertions": chosen_assertions,
                "sources": resolved_sources,
            }
        )

    return {"ok": not errors, "errors": errors, "resolved_evidence": resolved}


def _normalise_entity(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def evaluate_evidence_gates(validation: dict, inventory: dict) -> dict:
    """Apply promotion gates only to evidence actually selected by the memo."""

    annotations: dict[str, list[dict]] = {}
    blockers: list[str] = []
    if not validation.get("ok"):
        blockers.extend(f"Manifest integrity: {error}" for error in validation.get("errors") or [])
        return {
            "promotion_pass": False,
            "promotion_blockers": blockers,
            "annotations": annotations,
        }

    focus_name = (inventory.get("focus_company") or {}).get("name")
    for resolved in validation.get("resolved_evidence") or []:
        ref = resolved["evidence_ref"]
        notes: list[dict] = []
        audited_docs: set[str] = set()
        for source in resolved.get("sources") or []:
            source_doc = source.get("source_doc") or {}
            if not source_doc.get("source_under_audit"):
                continue
            source_doc_id = source.get("source_doc_id") or source_doc.get("id")
            if source_doc_id in audited_docs:
                continue
            audited_docs.add(source_doc_id)
            notes.append(
                {
                    "code": "source_under_audit",
                    "severity": "blocker",
                    "source_doc_id": source_doc_id,
                    "message": (
                        f"SourceDoc {source_doc_id} 正在可信度審查："
                        f"{source_doc.get('audit_note') or '原因見 source-audit ledger'}"
                    ),
                }
            )
            blockers.append(f"{ref}: SourceDoc {source_doc_id} is under audit")

        edge = resolved.get("edge")
        if not edge:
            if notes:
                annotations[ref] = notes
            continue
        item = resolved["item"]
        requested = set(item.get("attributes") or [])

        open_conflicts = set(edge.get("open_conflict_attributes") or [])
        for attribute in sorted(requested & open_conflicts):
            severity = "blocker" if attribute in HIGH_RISK_ATTRIBUTES else "warning"
            notes.append(
                {
                    "code": "open_conflict",
                    "severity": severity,
                    "attribute": attribute,
                    "message": f"{edge['edge_key']} 的 {attribute} 有未決證據衝突",
                }
            )
            if attribute in HIGH_RISK_ATTRIBUTES:
                blockers.append(f"{ref}: {edge['edge_key']} open conflict on {attribute}")

        for attribute in sorted(requested & HIGH_RISK_ATTRIBUTES):
            if attribute in open_conflicts:
                continue
            meta = (edge.get("attribute_resolution_meta") or {}).get(attribute) or {}
            if meta.get("status") == "approved" and meta.get("action") == "unknown":
                notes.append(
                    {
                        "code": "resolved_unknown",
                        "severity": "blocker",
                        "attribute": attribute,
                        "message": f"{edge['edge_key']} 的 {attribute} 已決議為 unknown",
                    }
                )
                blockers.append(f"{ref}: {edge['edge_key']} {attribute} resolved unknown")

        attrs = edge.get("attributes") or {}
        uses_bottleneck = (
            ("sole_source" in requested and attrs.get("sole_source") is True)
            or (
                "substitutability" in requested
                and isinstance(attrs.get("substitutability"), (int, float))
                and attrs["substitutability"] >= 4
            )
        )
        if uses_bottleneck:
            origins = {
                _normalise_entity(source.get("origin_entity"))
                for source in resolved.get("sources") or []
                if source.get("origin_entity")
            }
            self_reporters = {
                _normalise_entity(edge.get("src_name")),
                _normalise_entity(focus_name),
            }
            self_reporters.discard("")
            if len(origins) == 1 and origins.issubset(self_reporters):
                notes.append(
                    {
                        "code": "single_origin_self_report",
                        "severity": "weak",
                        "message": "瓶頸主張只由供應方／被分析公司單一自報來源支持",
                    }
                )
                blockers.append(f"{ref}: single-origin self-report bottleneck evidence")

        if notes:
            annotations[ref] = notes

    return {
        "promotion_pass": not blockers,
        "promotion_blockers": blockers,
        "annotations": annotations,
    }


def gate_notes_markdown(gate: dict) -> str:
    """Format evidence annotations for an auditable Research Note footer."""

    if not gate.get("annotations") and not gate.get("promotion_blockers"):
        return ""
    lines = ["## Evidence Gate Notes"]
    for ref, notes in gate.get("annotations", {}).items():
        for note in notes:
            icon = "⛔" if note.get("severity") == "blocker" else "⚠"
            lines.append(f"- {icon} [{ref}] {note.get('message')} (`{note.get('code')}`)")
    if gate.get("promotion_blockers"):
        lines.append("\n本報告因上述 evidence gate 未通過，維持 Research Note。")
    return "\n".join(lines) + "\n"
