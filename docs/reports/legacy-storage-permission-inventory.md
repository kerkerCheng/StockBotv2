# Legacy Corpus Storage-Permission Inventory

> Audited and migrated: 2026-07-16

The 17 extraction JSON files and 10 raw text files that predate U11 have now
been classified under the repository storage policy. The classification is
based on the source owner's reuse terms or on a verified issuer/publisher
original, not on whether the material was free, public-facing, or paid for.

## Outcome

- 6 extractions are `repo_full`: one CC BY paper, two issuer-hosted versions of
  the same joint press release, two extractions from Sivers' official annual
  report, and one Sivers official press release.
- 1 extraction is `repo_excerpt`: the aleabitoreddit Substack item retains only
  its URL, metadata, three short attributed quotations (165 characters total),
  and derived graph assertions. The full article is not stored in Git.
- 10 extractions are `local_only`: five Motley Fool transcripts, two Seeking
  Alpha transcripts/presentations, one Optica article, and two analyst articles
  without a verified reuse license/source URL.
- 3 of the 10 raw text files are Git-eligible: the CC BY paper excerpt, the
  issuer-hosted Enablence/Sivers/O-Net release summary, and the attributed Sivers
  annual-report excerpt. The Sivers raw metadata sidecar is eligible as well.
- `extractions/lumentum_q2fy26_cpo_raw.txt` is a failed/raw LLM response derived
  from a local-only Motley Fool source and remains ignored.

This is a Git-ledger backfill, not a new Research Action finalize or a Neo4j
reload. The migration manifest preserves each legacy extraction's actual path;
several predate the current `extractions/{doc_id}.json` naming contract and must
not be passed to `resolve_action_paths()` as though they were new intake files.

## Per-document decisions

| Extraction | Permission | Git | Basis |
|---|---|---:|---|
| `broadcom_q2fy26_cpo.json` | `local_only` | No | Motley Fool permits one intact personal copy but prohibits other storing/posting/abstracts without permission. |
| `coherent_ofc_march25.json` | `local_only` | No | Seeking Alpha limits copied content to personal use and requires consent for republication/distribution. |
| `coherent_q2fy26_cpo.json` | `local_only` | No | Motley Fool restriction. |
| `coherent_q3fy26_cpo.json` | `local_only` | No | Seeking Alpha restriction. |
| `cpo_chip_package_paper.json` | `repo_full` | Yes | Micromachines article is CC BY 4.0; attribution, source URL, and license link are retained. |
| `damnang_poet_ofc2026_review_2026_03.json` | `local_only` | No | No verified creator reuse license or canonical source URL. |
| `enablence_sivers_onet_els_2026.json` | `repo_full` | Yes | Official joint issuer release on Sivers' newsroom and Enablence's press index; canonical source changed away from PR Newswire. |
| `enablence_sivers_onet_ofc_pr_2026_03_17.json` | `repo_full` | Yes | Same official joint issuer release. |
| `lumentum_q2fy26_cpo.json` | `local_only` | No | Motley Fool restriction. |
| `lumentum_q3fy26_cpo.json` | `local_only` | No | Motley Fool restriction. |
| `nvidia_q1fy27.json` | `local_only` | No | Motley Fool restriction. |
| `silicon_matter_ayar_labs.json` | `repo_excerpt` | Yes | URL + metadata + limited attributed quotations and derived assertions only; no full article. |
| `silicon_matter_celestial_marvell.json` | `local_only` | No | Optica prohibits using site material in another website or networked computer environment without permission. |
| `silicon_matter_sivers_ayar_2026_03_14.json` | `local_only` | No | No verified creator reuse license or canonical source URL. |
| `sivers_ar_2025.json` | `repo_full` | Yes | Official annual report on the issuer's own domain; repository stores attributed research excerpts. |
| `sivers_ar_2025_financials.json` | `repo_full` | Yes | Same official annual report. |
| `sivers_gf_pr_2026_06_02.json` | `repo_full` | Yes | Issuer-authored release on Sivers' official newsroom. |

## Audit sources

- Motley Fool terms: <https://www.fool.com/legal/terms-and-conditions/fool-rules/>
- Seeking Alpha terms: <https://about.seekingalpha.com/terms>
- Micromachines open-access policy: <https://www.mdpi.com/journal/micromachines/about>
- Sivers/O-Net/Enablence issuer release: <https://www.sivers-semiconductors.com/press/sivers-semiconductors-o-net-and-enablence-technologies-announce-external-light-sources-for-ai-datacenters/>
- Enablence press index: <https://www.enablence.com/press-releases/>
- Sivers 2025 annual report: <https://www.sivers-semiconductors.com/wp-content/uploads/2026/05/Sivers_annualreport_2025_2.pdf>
- Sivers/GlobalFoundries issuer release: <https://www.sivers-semiconductors.com/press/sivers-globalfoundries-advance-ai-data-center-optical-solutions/>
- Optica terms: <https://www.optica.org/about/policies/terms_of_use/>
- aleabitoreddit article: <https://aleabitoreddit.substack.com/p/sivers-semi-sive-the-cpo-laser-supplier>

## Migration integrity

The original Phase I frozen manifest remains unchanged as the pre-migration
snapshot. `loader/manifests/legacy-storage-permission-migration.json` records
each extraction's pre-migration and post-migration SHA-256, resulting permission,
and Git eligibility. Post-migration hashes use staged Git-blob bytes for
Git-eligible files, so line-ending conversion cannot invalidate the ledger; hashes
for `local_only` files preserve the exact local working-file bytes. Local-only
legacy files remain at their established paths behind explicit `.gitignore` deny
entries so existing local replay references do not break; all new `local_only`
intake continues to route to `library/private/`.
