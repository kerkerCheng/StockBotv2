# Phase I SIVE Engine A Acceptance

> Status: **PASS — Phase I exit acceptance complete**
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

### U4 single-origin checkpoint (2026-07-16)

- The graph-derived SIVE report contains 24 unique single-origin Claims/edges
  and zero provenance orphans.
- Spot checks matched the graph: Sivers → GlobalFoundries is issuer self-report,
  Sivers → Ayar Labs is aleabitoreddit-only, and Sivers → Enablence/O-Net ELS is
  supported by an Enablence-origin document.
- Win Semiconductor → Sivers does not appear as single-origin because its two
  assertions cite distinct Sivers and aleabitoreddit SourceDocs. Adding a second
  origin therefore removes an element automatically without editing a list.
- Local CLI and remote MCP use the same exported Cypher constant; no additional
  mutable report or MCP write surface was introduced.

### U5 evidence-manifest checkpoint (2026-07-16)

- `generate_lane_memo.py` now accepts a provider-independent JSON envelope and
  validates every Claim, edge, EdgeAssertion, source ID, quote, and `[E#]`
  reference against the exact inventory supplied for that run. Report grade is
  written by the application after validation; the drafting model cannot choose
  it.
- The networked Anthropic transport was not used for this acceptance because the
  desktop security boundary did not authorize sending the private graph/corpus
  to an external Anthropic tenant. The same generator was run through its local
  `--envelope-file` transport, with this Codex session supplying the JSON draft.
  Schema validation, graph reconciliation, evidence gates, sidecar generation,
  and output grading are identical between transports.
- The actual SIVE memo cites eight evidence items spanning six SourceDocs and
  four distinct origins: Enablence Technologies, Sivers Semiconductors,
  Lumentum, and damnang_substack. Every item resolves to a verbatim quote and a
  graph SourceDoc. Sources with only a locator/paraphrase and no verbatim quote
  are rejected as memo evidence.
- A migration regression was caught during acceptance: the active
  `sivers_ar_2025` credibility audit had existed only in the old memo/graph and
  was lost by disk replay. It is now durable in
  `library/source_audits/sivers_2025_annual_report.json`, independently of the
  frozen extraction corpus, and projected onto both affected SourceDocs. Citing
  either SourceDoc automatically blocks promotion and adds an auditable note.
- The regenerated memo validates successfully, but its evidence promotion gate
  fails by design because E4/E5 cite the audited Sivers photonics annual-report
  SourceDoc and E8 cites the audited financial extraction. E4 also carries the
  non-blocking open `qualification_status` conflict warning. Financial checklist
  and L9 also remain incomplete, so the application correctly emits
  `[Research Note]`.
- Live SIVE smoke test: a temporary `sole_source` conflict edge was added to the
  company subgraph. With the edge absent from the manifest, promotion passed;
  adding it as E2 made promotion fail with `open_conflict`. The script removed
  the temporary relationship, assertions, and node in `finally` and verified
  cleanup.

### Regenerated memo identity

| Item | Value |
|---|---|
| Memo | `thesis/sivers_phase1_after_lane_memo.md` |
| Memo SHA-256 | `3706EB302C379E23AE86FA9C1B2C7F5D029B075853CE3F74031521F0E5971A39` |
| Sidecar | `thesis/sivers_phase1_after_lane_memo.evidence.json` |
| Sidecar SHA-256 | `A085C9C4DD29EB15A09F22729B7D9D20C6A93CC5592E965F5B7A5E5158AA95CE` |
| Output type | `Research Note` |
| Manifest validation | pass; 8/8 items resolved, zero errors |
| Evidence promotion gate | fail closed; 3 cited items use active-audit SourceDocs |
| Open cited conflict | E4, Win Semiconductor → Sivers `qualification_status` |
| Approved edge resolutions | none |

### Standard question — after answer

**Question:** 目前 SIVE 的 CPO／ELS thesis：哪些已確認、哪些是單源自報、哪些證據受 audit？

**After answer:**

- **Confirmed:** an Enablence-origin announcement confirms the Sivers/O-Net/
  Enablence 8-channel ELS product and explicitly names Sivers laser arrays in
  the module. This confirms product integration and partner roles, not a
  hyperscaler design win, committed volume, or sole-source status. Lumentum's
  own six-quarter estimate for new InP-fab contribution independently supports
  the long capacity cycle, but does not prove Sivers demand.
- **Single-origin/self-report:** Sivers' CW-laser shortage expectation, GF SCALE
  route-to-market, WIN volume-ramp readiness, and FY2025 margin narrative remain
  supplier-origin statements unless a customer or independent primary source
  confirms them. No cited or canonical SIVE edge establishes `sole_source=true`.
- **Under audit/conflict:** E4 and E5 trace to
  `sivers_ar_2025_photonics_excerpt`; E8 traces to
  `sivers_ar_2025_financials`. Both SourceDocs inherit the active July 12 audit
  ledger and therefore block promotion. WIN → Sivers qualification remains an
  explicit `qualified` versus `qualifying` conflict rather than being selected
  by confidence or load order. No resolution has been approved.
- **Research conclusion:** Sivers has progressed from an issuer-only CPO story
  to externally confirmed module integration, but customer qualification,
  foundry ramp, revenue conversion, and margin conversion are still separate
  gates. The thesis remains useful as a monitored Research Note and has not
  earned Watchlist/Investment promotion.

### Acceptance decision

| Criterion | Result | Evidence |
|---|---|---|
| Every before source ID accounted for | PASS | All 209 frozen-manifest source IDs reconcile; the SIVE before set is a subset, with no silent loss |
| Single-origin, self-report, audit, and conflicts remain visible | PASS | U4 report, source-audit projection, E4/E5/E8 gate annotations, 19 derived conflicts |
| Every memo warning traces through `[E#]` to evidence | PASS | Sidecar validation 8/8; quote and full SourceDoc metadata embedded |
| Unreferenced conflict does not block; cited high-risk conflict does | PASS | `scripts/phase1_sive_conflict_smoke.py` live result `true` then `false` |
| Research answer remains useful after adding quality warnings | PASS | Memo states thesis, strongest evidence, counterevidence, disproof, catalysts, and variant perception |
| No unexpected evidence loss or wrong canonical attribute | PASS | Zero manifest reconciliation gaps; conflicts absent from canonical values until resolved |

**Final result: PASS.** Phase I's repaired measurement system preserves the
frozen corpus, exposes rather than hides evidence quality problems, and still
produces a decision-useful SIVE research answer. M1 may now start with AXT as the
first new onboarding target; this acceptance does not itself add AXT or change
the frozen SIVE comparison corpus.
