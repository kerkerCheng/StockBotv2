"""Derive single-origin and orphan graph evidence from SourceDoc/CITES."""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
if load_dotenv is not None:
    load_dotenv(ROOT / ".env")


# This constant is the shared query for local CLI and remote MCP run_read_query.
# Keep normalization in Cypher so cloud callers do not need a second copy.
SINGLE_ORIGIN_CYPHER = """
CALL () {
  MATCH (claim:Claim)
  OPTIONAL MATCH (claim_src:Entity)-[claim_edge]->(claim_dst:Entity)
  WHERE claim.subject_kind = 'edge'
    AND claim_edge.edge_key = claim.subject_edge_key
  OPTIONAL MATCH (claim)-[:CITES]->(source_doc:SourceDoc)
  WITH claim, claim_src, claim_dst,
       collect(DISTINCT source_doc.id) AS source_doc_ids,
       collect(DISTINCT source_doc.origin_entity) AS origin_entities
  WITH 'claim' AS kind,
       claim.id AS element_id,
       claim.statement AS summary,
       CASE
         WHEN claim.subject_kind = 'node' AND claim.subject_node_id STARTS WITH 'co:'
           THEN [claim.subject_node_id]
         WHEN claim.subject_kind = 'edge'
           THEN [company_id IN [claim_src.id, claim_dst.id]
                 WHERE company_id STARTS WITH 'co:' | company_id]
         ELSE []
       END AS company_ids,
       source_doc_ids,
       origin_entities,
       [] AS assertion_ids,
       CASE
         WHEN size(source_doc_ids) = 0 THEN 'claim_no_cites'
         WHEN size(origin_entities) = 0 THEN 'missing_origin_entity'
         ELSE null
       END AS orphan_reason
  RETURN kind, element_id, summary, company_ids, origin_entities,
         source_doc_ids, size(source_doc_ids) AS source_doc_count,
         assertion_ids, 0 AS assertion_count, orphan_reason

  UNION ALL

  MATCH (src:Entity)-[relationship]->(dst:Entity)
  WHERE relationship.edge_key IS NOT NULL
  OPTIONAL MATCH (assertion:EdgeAssertion {edge_key: relationship.edge_key})
  OPTIONAL MATCH (assertion)-[:CITES]->(source_doc:SourceDoc)
  WITH src, relationship, dst,
       collect(DISTINCT assertion.id) AS assertion_ids,
       collect(DISTINCT source_doc.id) AS source_doc_ids,
       collect(DISTINCT source_doc.origin_entity) AS origin_entities
  WITH 'edge' AS kind,
       relationship.edge_key AS element_id,
       src.id + ' -[' + relationship.relation + ']-> ' + dst.id AS summary,
       [company_id IN [src.id, dst.id]
        WHERE company_id STARTS WITH 'co:' | company_id] AS company_ids,
       origin_entities,
       source_doc_ids,
       assertion_ids,
       CASE
         WHEN size(assertion_ids) = 0 THEN 'relationship_no_assertion'
         WHEN size(source_doc_ids) = 0 THEN 'assertion_no_cites'
         WHEN size(origin_entities) = 0 THEN 'missing_origin_entity'
         ELSE null
       END AS orphan_reason
  RETURN kind, element_id, summary, company_ids, origin_entities,
         source_doc_ids, size(source_doc_ids) AS source_doc_count,
         assertion_ids, size(assertion_ids) AS assertion_count, orphan_reason
}
WITH *
WHERE size(origin_entities) <= 1
  AND ($company_id IS NULL OR $company_id = '' OR $company_id IN company_ids)
RETURN kind, element_id, summary, company_ids, origin_entities,
       source_doc_ids, source_doc_count, assertion_ids, assertion_count,
       orphan_reason
ORDER BY kind, element_id
"""


def classify_rows(rows) -> dict[str, list[dict]]:
    """Normalize query rows and retain only single-origin/orphan evidence."""

    single_origin: list[dict] = []
    orphans: list[dict] = []
    for raw_row in rows:
        row = dict(raw_row)
        row["origin_entities"] = sorted(set(row.get("origin_entities") or []))
        row["company_ids"] = sorted(set(row.get("company_ids") or []))
        if len(row["origin_entities"]) > 1:
            continue
        if row.get("orphan_reason") or not row["origin_entities"]:
            row["orphan_reason"] = row.get("orphan_reason") or "missing_origin_entity"
            orphans.append(row)
        else:
            single_origin.append(row)
    sort_key = lambda row: (row["company_ids"], row["kind"], row["element_id"])
    return {
        "single_origin": sorted(single_origin, key=sort_key),
        "orphans": sorted(orphans, key=sort_key),
    }


def _group_by_company(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        company_ids = row.get("company_ids") or ["(unscoped)"]
        for company_id in company_ids:
            groups[company_id].append(row)
    return dict(sorted(groups.items()))


def _render_section(title: str, rows: list[dict], *, orphan: bool = False) -> list[str]:
    lines = [f"## {title}", ""]
    if not rows:
        lines.append("_(none)_")
        return lines
    for company_id, company_rows in _group_by_company(rows).items():
        lines.extend([f"### `{company_id}`", ""])
        for row in company_rows:
            origins = ", ".join(row["origin_entities"]) or "none"
            suffix = (
                f"; orphan={row['orphan_reason']}"
                if orphan
                else f"; origin={origins}"
            )
            lines.append(
                f"- [{row['kind']}] `{row['element_id']}` — {row['summary']}"
                f" ({suffix.lstrip('; ')}; SourceDocs={row.get('source_doc_ids') or []}; "
                f"assertions={row.get('assertion_ids') or []})"
            )
        lines.append("")
    return lines


def render_report(result: dict[str, list[dict]], company_id: str | None) -> str:
    single_origin = result["single_origin"]
    orphans = result["orphans"]
    lines = [
        "# Single-Origin Evidence Report",
        "",
        f"Scope: `{company_id or 'all companies'}`",
        f"Single-origin evidence: {len(single_origin)}",
        f"Orphan provenance: {len(orphans)}",
        "",
    ]
    if not single_origin and not orphans:
        lines.append("No single-origin or orphan evidence.")
        return "\n".join(lines) + "\n"
    lines.extend(_render_section("Single-origin evidence", single_origin))
    lines.append("")
    lines.extend(_render_section("Orphan provenance", orphans, orphan=True))
    return "\n".join(lines).rstrip() + "\n"


def _driver():
    from neo4j import GraphDatabase

    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD is required")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), password),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company-id")
    args = parser.parse_args()
    driver = _driver()
    try:
        with driver.session() as session:
            rows = list(
                session.run(SINGLE_ORIGIN_CYPHER, company_id=args.company_id)
            )
    finally:
        driver.close()
    print(render_report(classify_rows(rows), args.company_id), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
