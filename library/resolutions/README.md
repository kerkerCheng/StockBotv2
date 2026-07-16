# Edge resolution ledger

This directory contains only approved, version-controlled decisions for derived
`edge_key + attribute` conflicts. The open queue is computed from
EdgeAssertions; it is not persisted here.

Rules:

- One file per conflict: `<conflict_id>.json`.
- Files must pass `schema/edge_resolution.schema.json`.
- A resolution is valid only while its `candidate_set_hash` matches the live
  assertions. New or removed evidence makes it stale and reopens the conflict.
- LLMs may propose a decision but must not write files here directly.
- Only `loader/edge_resolution.py approve` may publish an explicitly
  human-approved proposal and rerun the canonical projector.
- Git history is the decision audit trail; do not maintain a second conflict
  registry or hand-edit canonical relationship attributes.
