# Legacy Corpus Storage-Permission Inventory

> Recorded: 2026-07-16

The 17 extraction JSON files and 10 raw text files that predate U11 do not carry
an explicit `storage_permission` or `permission_basis`. They remain individually
ignored by Git. This is an intentional fail-closed classification, not a claim
that every source forbids storage.

- No item was promoted merely because it is free, public-facing, or already paid
  for.
- The frozen Phase I extraction files were not edited, so the migration manifest
  and SIVE before/after acceptance remain reproducible.
- If a legacy document's license or authorization is later verified, migrate it
  explicitly with a reviewed permission basis and a canonical-hash guard; do not
  silently resend the same `doc_id` with a changed permission.
- All new remote intake documents must include permission metadata. `repo_full`
  and `repo_excerpt` publish into the Git ledger; `local_only` routes to ignored
  `library/private/`.

The authoritative legacy filename allow/deny boundary is the explicit list in
`.gitignore`. New lowercase, safe-ID extraction/raw filenames are unignored so
`pending_intake_files()` and precise-path finalize commits can see them.
