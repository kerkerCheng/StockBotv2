# Phase I SIVE Engine A Acceptance

> Status: before snapshot captured; after run pending  
> Snapshot date: 2026-07-16  
> Company ID: `co:sivers_semiconductors`

This report fixes the SIVE baseline before the U2/U3/U3b identity, provenance,
and edge-attribute migration. The after run must use the same frozen extraction
manifest and the same standard research question. No AXT or other new document
may be added to the comparison corpus.

## Before snapshot

### Lane Memo identity

| Item | Value |
|---|---|
| File | `thesis/sivers_v2_lane_memo.md` |
| Last commit touching the file | `6eecffd678c32e5d7d14d309f0d8be5593f8b05c` |
| SHA-256 | `B2F2A866590223AE92503FF272E007B01EB85DA5E0F06B4BE2472996889ACA4B` |
| Output type | `Research Note` |
| Thesis status | `review_required` |

The memo says L8 was manually overridden at `1/3 origin_entity`. The current
disk-scanning implementation now reports `4/3` because additional extractions
have since been added. This drift is itself part of the baseline: neither result
proves that the evidence actually cited by a memo has independent support.

### Comparison corpus

The before scope is the seven extraction files in which
`co:sivers_semiconductors` occurs as a node, edge endpoint, or Claim subject.
This is the corpus that the U2 migration manifest must freeze.

| Extraction file | `doc_id` | Nodes | Edges | Claims |
|---|---|---:|---:|---:|
| `extractions/enablence_sivers_onet_els_2026.json` | `enablence_sivers_onet_els_2026` | 4 | 3 | 0 |
| `extractions/enablence_sivers_onet_ofc_pr_2026_03_17.json` | `enablence_sivers_onet_ofc_pr_2026_03_17` | 6 | 5 | 1 |
| `extractions/silicon_matter_ayar_labs.json` | `aleabitoreddit_sivers_cpo_customer_map` | 4 | 3 | 3 |
| `extractions/silicon_matter_sivers_ayar_2026_03_14.json` | `silicon_matter_sivers_ayar_2026_03_14` | 5 | 3 | 1 |
| `extractions/sivers_ar_2025.json` | `sivers_ar_2025_photonics_excerpt` | 17 | 21 | 5 |
| `extractions/sivers_ar_2025_financials.json` | `sivers_ar_2025_financials` | 1 | 0 | 3 |
| `extractions/sivers_gf_pr_2026_06_02.json` | `sivers_gf_pr_2026_06_02` | 5 | 4 | 1 |
| **Input totals** | **7 documents** | **42** | **39** | **14** |

Corpus identity diagnostics:

- 42 node inputs reduce to 28 distinct node IDs.
- 39 edge inputs reduce to 37 distinct `(src_id, relation, dst_id)` triples,
  but use only 21 distinct document-local edge IDs.
- 14 Claim inputs use only five local IDs: `cl1` through `cl5`.
- Corpus objects reference 45 distinct quote-level `source_ids`.

### Current graph materialization

To avoid guessing from names, an object is counted here when its `source_ids`
overlap the 45 quote IDs referenced by the comparison corpus. Claims are counted
separately from domain nodes.

| Graph object | Count | Source-ID references | Distinct SIVE source IDs represented |
|---|---:|---:|---:|
| Domain nodes (`Entity`, excluding `Claim`) | 22 | 26 | 19 |
| Relationships | 39 | 58 | 32 |
| Claims | 5 | 9 | 8 |
| **Union across all three** | — | — | **35 / 45** |

The graph therefore cannot account for ten source IDs that are referenced by
the disk corpus:

- `aleabitoreddit_sivers_s2`
- `sivers_ar_2025_financials_s1`
- `sivers_ar_2025_financials_s4`
- `sivers_ar_2025_financials_s5`
- `sivers_ar_2025_financials_s6`
- `sivers_ar_2025_financials_s7`
- `sivers_ar_2025_financials_s8`
- `sivers_ar_2025_financials_s9`
- `sivers_ar_2025_photonics_excerpt_s1`
- `sivers_ar_2025_photonics_excerpt_s16`

This is a characterization result, not a migration exception list. U2/U3 must
replay from the frozen disk corpus, and the after reconciliation must either find
every one of the 45 IDs on a Claim or EdgeAssertion or record an explicit,
reviewed exception.

### Current `_check_source_diversity` result

The pre-U3 implementation scanned 17 files in `extractions/`, found seven that
refer to SIVE, and returned:

```text
distinct origin_entity: 4 / 3 — pass
Enablence Technologies
Sivers Semiconductors
aleabitoreddit
silicon_matter_substack
```

This is only a company-wide document count. It does not establish that the
specific Claims or edge attributes selected for a memo have three independent
origins. It also treats a participating partner's press release as a distinct
origin even when it is not independent customer-demand evidence.

### Standard question — current answer

**Question:** 目前 SIVE 的 CPO／ELS thesis：哪些已確認、哪些是單源自報、哪些證據受 audit？

**Current answer:**

- **Confirmed only at the collaboration/product-demonstration level:** the
  corpus contains Enablence-origin documents describing the Sivers/O-Net/
  Enablence ELS module, and a `silicon_matter_substack` extraction describing
  Sivers laser arrays in Ayar Labs' SuperNova module. These support that products
  and integrations have been announced or demonstrated. They do not confirm a
  hyperscaler design win, committed volume, sole-source status, or durable
  customer demand. The Ayar Claim itself says primary-source confirmation is
  still outstanding.
- **Single-origin or issuer/participant self-report:** Sivers sampling to
  multiple transceiver manufacturers, expected 2027+ production, the Sivers +
  O-Net end-2026 readiness target, a future CW-laser shortage, and the GF SCALE
  route-to-market are not independently confirmed customer commitments in the
  current graph. No SIVE edge has verified `sole_source`; competitor
  qualification and confirmed customer BOM position remain unknown.
- **Under audit:** the strongest memo evidence from
  `sivers_ar_2025_photonics_excerpt`—including `_s5`, `_s9`, and `_s12`—inherits
  the active source audit caused by the revenue-recognition allegations,
  going-concern concern, and pending restatement. The thesis therefore remains
  `review_required`; those issuer statements must not be promoted merely because
  their stored `confidence` or `demand_proof_level` is high.
- **Current graph limitation:** Claim ID collapse makes the answer noisier than
  the corpus warrants. Fourteen input Claims have materialized as five Claim
  nodes, and the same statements appear attached to unrelated subjects. The
  current `4/3` L8 pass is therefore not sufficient evidence that any particular
  memo assertion is independently corroborated.

## After snapshot

Pending completion of U2, U3, U3b, U4, and U5.

### U2 replay checkpoint (2026-07-16)

- Neo4j dump: `C:/tmp/StockBotv2-backups/phase1-before-u2-20260716/neo4j.dump`
- Dump SHA-256: `9F818726DD502D17C60A52F58A2BC69B7FB67BF2ABA60294411D5A5A74ACF0A2`
- Frozen corpus manifest: `loader/manifests/phase1-engine-a-corpus.json`
- Manifest SHA-256: `bed31eba0216f658ec414afe83298951e9e21d1cf23336c50e5d28a7549ade6e`
- Replayed inputs: 17 documents, 208 node inputs, 249 edge inputs,
  56 Claim inputs, and 209 distinct referenced source IDs.
- Preflight repaired 24 manifest-only source IDs. It also found 21 graph-only
  legacy IDs; every matching graph object was inspected and the exact set was
  approved in `phase1-engine-a-reconciliation-exceptions.json` before replay.
- Post-replay: 209 canonical relationships, zero duplicate canonical triples,
  249 EdgeAssertions with zero duplicate IDs, 56 Claims, no bare `cl1`, and all
  209 manifest source IDs represented with no graph-only or manifest-only IDs.
- Nine Claims target edges through `subject_edge_key`; none incorrectly creates
  an `ABOUT` relationship to a domain node.
- Canonical relationship attributes are intentionally empty until U3b projects
  conflict-safe materialized values from EdgeAssertions.

### U3 SourceDoc/CITES checkpoint (2026-07-16)

- Backfilled exactly 17 SourceDocs from the unchanged U2 manifest.
- All 249 EdgeAssertions and 56 Claims have exactly one `CITES` relationship;
  there are no missing or duplicate citations.
- Three metadata spot checks matched the extraction ground truth:
  `sivers_ar_2025_photonics_excerpt` → `Sivers Semiconductors`,
  `enablence_sivers_onet_els_2026` → `Enablence Technologies`, and
  `silicon_matter_sivers_ayar_2026_03_14` → `silicon_matter_substack`.
- Graph-backed SIVE L8 reports seven evidence SourceDocs and four distinct
  non-null origins, exactly matching the pre-migration disk-scan result.
- A rollback-only permission smoke using the cloud-routine Neo4j account could
  create SourceDoc, EdgeAssertion, and CITES, confirming that the new name tokens
  are usable by the remote loader without granting admin/delete authority.

### U3b conflict/projector checkpoint (2026-07-16)

- Derived the complete queue from 249 EdgeAssertions: 19 open conflicts across
  209 canonical edges (`qualification_status`: 12, `substitutability`: 4,
  `ramp_execution`: 3). No mutable conflict registry was created.
- Projected 178 unambiguous attributes. All 19 conflicting attributes are absent
  from canonical values and listed in `open_conflict_attributes`; overlap between
  open attributes and materialized values is zero.
- No real conflict was auto-approved. The resolution ledger is currently empty;
  unit coverage proves approved choose/unknown decisions, stale candidate hashes,
  missing assertion/source IDs, missing human approval, and split-scope handoff.
- The one conflict directly incident to Sivers is Win Semiconductor → Sivers
  `qualification_status` (`qualified` from aleabitoreddit versus `qualifying`
  from the audited Sivers annual-report corpus). It remains open rather than
  being hidden by load order or confidence.
- `evidence-conflict-resolution` was validated with the skill tooling and synced
  to both Claude and Codex adapters. It may produce proposals but cannot directly
  edit the versioned resolution ledger or Neo4j.

The after section must record:

- the exact frozen manifest identity and hashes;
- post-migration SourceDoc, EdgeAssertion, Claim, canonical relationship, and
  quote-source reconciliation counts;
- graph-backed L8 results for the evidence actually cited by the memo;
- open/unknown edge-attribute conflicts and any approved resolutions;
- the regenerated memo and `.evidence.json` sidecar hashes;
- the answer to the same standard question above;
- a pass/fail decision against every Phase I acceptance criterion.
