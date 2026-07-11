---
date: 2026-07-11
topic: automation-reliability-workflow
---

# Automation Reliability Workflow — U7/U8 Redesign

## Summary

A reliability-first redesign of the U7/U8 automation layer: a weekly cloud routine harvests signals from both tracked themes and Engine B's curated feeds, triages them cheaply, and drafts full extractions for review. It reaches the user via GitHub, email, or phone notification regardless of whether a local session is open, and the final graph-write always stays a human-approved step.

---

## Problem Frame

The original U7/U8 design (see `docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md`) assumed `CronCreate` jobs and local `SessionStart` hooks could carry the "attention mechanism" pillar of the roadmap — reminding the user of stale theses and new signals without requiring them to remember to check in. Two facts broke that assumption during this brainstorm:

1. `CronCreate` jobs are session-only and auto-expire after 7 days recurring — unusable for genuinely unattended weekly/quarterly checks.
2. The user's real session-open cadence is irregular — sometimes weeks pass without opening this repo's Claude Code session. A `SessionStart` hook only fires if the user opens a session, which is exactly the behavior the mechanism is supposed to compensate for. A safety net that depends on the failure mode it's meant to catch isn't a safety net.

Separately, the user clarified their local machine stays on nearly continuously and their local Neo4j (self-hosted, not a managed cloud service) has no hibernation policy — a fact that reframes several downstream decisions about where the graph and financial data should live.

---

## Key Decisions

- **Reliability moves to the cloud+notification layer, not local hooks.** The `SessionStart` hooks built for U8 (thesis freshness) and U7b (PR digest) stay in place but are reframed as a convenience recap for whenever the user opens a session — not the mechanism guaranteeing the user is reached. That guarantee now lives in the weekly cloud routine opening GitHub PRs/Issues, which reach the user through GitHub/email/mobile notifications independent of local session state.

- **PR vs. Issue is chosen by artifact shape.** Findings with a mergeable artifact (a weekly report file) open as a GitHub PR. Pure alerts with no artifact (a stale thesis, a filtered-item audit note) open as a GitHub Issue instead.

- **The approval gate moves from "before extraction" to "before graph load."** The user is on a Claude subscription plan, so per-token API cost isn't the constraining factor it was assumed to be. Extraction now runs eagerly on every item that passes triage, so the review artifact the user sees is the actual drafted graph content (nodes/edges/quotes), not a prose summary. The human gate that matters — writing into Neo4j — is unconditional regardless of extraction cost.

- **Triage is deliberately lenient, and it must show its work.** A silently dropped good lead is worse than a wasted extraction. The triage step reports which raw items it filtered and why, so the user can audit or override it — the failure mode being guarded against is invisible loss of signal, not wasted compute.

- **New-company onboarding stays a deliberate, user-triggered action.** The routine only processes sources for companies/themes already tracked (`config/themes.txt`, `TICKER_MAP`). Discovering an entirely new company produces a suggestion in the report; it never triggers automatic extraction or onboarding for that company. Whether to add a new company to the graph at all remains the user's call, matching the existing `company-onboard` skill's trigger model.

- **`origin_entity` must reflect the true originator, not the relay.** When a harvested source is a curated account (e.g., aleabitoreddit) relaying a named third party's work (e.g., a sell-side analyst note), the true originator is the named third party — but only when independently traceable. When the primary document can't be located (the common case for paywalled research), the source is marked as a relay with the primary not independently located, rather than silently attributed as if it were a first-party citation.

- **Local self-hosted Neo4j has no hibernation risk; managed cloud hosting is deferred, not adopted.** The user's machine stays on nearly continuously and self-hosted Neo4j (unlike Neo4j Aura's managed free tier) has no auto-pause or auto-delete policy. Migrating Neo4j or Engine C to a managed cloud service (Aura, Neon, Supabase) is not being pursued yet — a network path from the cloud routine to the always-on local machine is the preferred direction to validate first. If that path proves infeasible, Neon is the preferred fallback over Supabase for Engine C specifically, because Neon auto-resumes on the next query (~1s) while Supabase requires manual dashboard unpause after inactivity — the latter reintroduces the exact "must remember to act" failure mode this whole redesign exists to remove.

- **Cadence stays weekly for now.** Increasing the routine's frequency has low downside (as long as it stays silent when nothing is found) and could catch signals faster, but the user's routine-usage-vs-subscription-quota economics aren't independently confirmed yet. Frequency stays weekly pending that validation.

---

## Actors

- **A1. User** — reviews routine output (via GitHub or a continued Claude App conversation), approves or rejects graph loads, can escalate any report into a deeper conversation before deciding.
- **A2. Weekly cloud routine** — harvests, triages, extracts, opens PRs/Issues, and executes previously-approved loads on its next run.
- **A3. Local `SessionStart` hooks** — secondary, convenience-only recap (thesis freshness check, pending-PR digest) shown when the user opens a local session.
- **A4. GitHub** — the approval surface and notification channel (PR/Issue plus email/mobile notifications).
- **A5. Local Neo4j / Engine C** — the graph and financial data stores, reached by the cloud routine over a network path still to be validated (see Outstanding Questions).

---

## Key Flows

- **F1. Weekly harvest-to-review cycle**
  - **Trigger:** weekly schedule fires.
  - **Actors:** A2, A4.
  - **Steps:** harvest raw signals from tracked themes and Engine B feeds (attempting to trace relayed sources to their primary document) → triage each item leniently, recording what's filtered and why → extract full structured drafts for everything that passes triage → open a PR (report with artifact) or Issue (pure alert) → GitHub notifies the user.
  - **Outcome:** the user has a reviewable, structured draft waiting on GitHub, reached without needing an open local session.
  - **Covers:** R1, R3, R4, R5, R6, R7, R8, R9, R12, R13.

- **F2. Approval-to-load cycle**
  - **Trigger:** user approves an open PR/Issue (comment or direct instruction in a later conversation).
  - **Actors:** A1, A2, A5.
  - **Steps:** approval is recorded → the next weekly routine run picks up approved items and loads them into Neo4j.
  - **Outcome:** the graph updates without requiring an out-of-band trigger; no webhook or real-time processing exists for this step.
  - **Covers:** R10, R11.

- **F3. Deep-dive escalation**
  - **Trigger:** the user wants more scrutiny than the report alone provides before approving.
  - **Actors:** A1.
  - **Steps:** the user continues the conversation (in the Claude App or elsewhere) referencing the report content, asking follow-up questions exactly as in an interactive research session.
  - **Outcome:** an informed approve/reject decision, without the report itself needing to carry brainstorm-level detail.
  - **Covers:** R2.

---

## Requirements

**Reliability & notification**
- R1. The system reaches the user (via GitHub, email, or mobile notification) regardless of whether a local Claude Code session was opened that week.
- R2. Local `SessionStart` hooks (thesis-freshness check, PR digest) serve as a secondary convenience recap, not the primary reliability mechanism.
- R3. Weekly-scan findings with a mergeable artifact open as a GitHub PR; pure alerts with no artifact open as a GitHub Issue.

**Pipeline stages**
- R4. Stage 1 (harvest) runs web search across tracked themes (`config/themes.txt`) and Engine B's curated feeds every cycle.
- R5. Stage 1 attempts to trace a relayed source back to its primary document; failing to find the primary source is an accepted, common outcome, not a blocker.
- R6. Stage 2 (triage) is an automatic, low-cost judgment — defined in a dedicated skill — that decides whether a harvested item is relevant, novel, quotable, and a plausible new `origin_entity` before it proceeds to extraction.
- R7. Stage 2 triage is deliberately lenient, favoring false positives over silently dropping a good lead.
- R8. Every routine run reports which raw items triage filtered out and why.
- R9. Stage 3 (extract) runs automatically on every item that passes triage, producing a full structured draft rather than a prose summary.
- R10. Stage 4 (approval) is a mandatory human checkpoint before anything is written into Neo4j.
- R11. Approved items are loaded during the next weekly routine cycle; no separate real-time or webhook-triggered processing exists for this step.

**Scope guardrails**
- R12. The routine only processes sources for companies/themes already tracked; discovering an entirely new company produces a suggestion in the report, never automatic extraction or onboarding.
- R13. `origin_entity` reflects the true originator of a relayed source when traceable, and is marked as an untraced relay when it isn't.

**Security**
- R14. The local Neo4j password is rotated to a strong, random value before any network path exposes it to a cloud routine.
- R15. The cloud routine authenticates with a dedicated, least-privilege Neo4j account (read/write only, no admin/schema/delete rights) rather than the user's own admin credential.

---

## Acceptance Examples

- **AE1. Covers R5, R13.** Given a tweet that screenshots a named sell-side analyst's note about a tracked company, when the primary analyst report can't be located independently, then the extracted claim's `origin_entity` is recorded as the analyst house with a note that it was relayed and the primary document wasn't independently located — not recorded as a clean first-party citation.
- **AE2. Covers R7, R8.** Given a harvested item that triage judges low-relevance, when the weekly routine report is generated, then the item appears in a "filtered out" list with a stated reason, rather than disappearing silently.
- **AE3. Covers R12.** Given a web search result that names a company not present in `config/themes.txt` or `TICKER_MAP`, when the routine processes it, then the report suggests the company as a candidate for onboarding and does not run extraction against it.
- **AE4. Covers R9, R10.** Given an item that passes triage, when the routine drafts its extraction, then the draft is attached to the PR/Issue for review, and no write to Neo4j occurs until the user approves it.

---

## Scope Boundaries

**Deferred for later**
- Migrating Neo4j or Engine C to managed cloud hosting (Aura, Neon, Supabase) — only revisited if the network-tunnel path to the always-on local machine proves infeasible.
- Real-time or webhook-triggered processing of approvals (e.g., GitHub Actions) — approved items wait for the next weekly cycle.
- Increasing routine frequency beyond weekly — deferred pending empirical confirmation of how routine usage draws against the user's subscription quota.

**Outside this product's identity**
- Paid X API access for Engine B — SubStack/web-search coverage is already treated as sufficient (existing CLAUDE.md decision, reaffirmed here).
- Fully autonomous graph writes with no human gate — the L8 source-independence judgment stays a human checkpoint regardless of extraction cost.

---

## Dependencies / Assumptions

- Assumes the user's local machine remains reachable for a cloud routine to reach it over a network tunnel — not yet validated end-to-end.
- Assumes Anthropic's cloud-routine "Custom" network access (`allowed_hosts`) can reach a self-hosted tunnel endpoint — current public platform bug reports describe custom domains not being reliably enforced.
- Assumes GitHub is connected to this repository before any routine can be created.
- Assumes routine execution draws against the same Claude subscription usage pool as interactive sessions — not independently confirmed.

---

## Outstanding Questions

**Deferred to planning**
- **First validation step, before anything else is built:** confirm whether a cloud routine's "Custom" network access actually reaches a self-hosted tunnel (e.g., Cloudflare Tunnel) in practice — the platform has open bug reports on custom-domain enforcement. Until confirmed, treat local-tunnel reachability as an assumption, not a decision; if it fails, the fallback is managed cloud hosting (Aura/Neon/Supabase) at real recurring cost.
- Confirm whether any mechanism exists for passing credentials to a cloud routine beyond embedding a value in the routine's own configuration; if none, proceed with a dedicated least-privilege Neo4j account per R15.
- Exact tunnel technology and setup steps for reaching the local machine from a cloud routine.
- Whether and when Engine C needs to move off local SQLite/Postgres.
- Whether weekly cadence should later increase, once routine-usage economics are confirmed.

---

## Sources & Research

- `docs/plans/2026-07-10-006-feat-personal-investment-advisor-roadmap-plan.md` — U7/U8/U7b sections this brainstorm revises
- `CLAUDE.md` — L1 (core-component tooling maturity), L6 (anti-hallucination / verbatim quotes), L8 (source independence as a human gate)
- `skills/lead-intake/SKILL.md` — Fast Path triage model the Stage 2 triage skill is expected to mirror
- `skills/company-onboard/SKILL.md` — existing onboarding flow; new-company decisions continue to route through it
- [Aura Instance Access Issues: Pausing, Resuming, and Auto Delete Policy](https://support.neo4j.com/s/article/17480821630355--Aura-Instance-Access-Issues-Understanding-Pausing-Resuming-and-Auto-Delete-Policy) — Neo4j Aura Free 72h pause / 90-day delete policy
- [Neo4j Software Pricing & Plans 2026](https://www.vendr.com/marketplace/neo4j) — Aura Professional cost floor (~$65-85/month)
- [Supabase Project Pausing docs](https://supabase.com/docs/guides/platform/free-project-pausing) — 7-day inactivity pause, manual dashboard unpause required
- [Neon vs Supabase Free Tier Comparison — 2026](https://agentdeals.dev/neon-vs-supabase) — Neon's auto-resume-on-query behavior vs Supabase's manual unpause
- [Cloud environment setup — Claude Platform Docs](https://platform.claude.com/docs/en/managed-agents/environments) — confirms `networking` (unrestricted/limited + `allowed_hosts`) and `packages` are the only documented environment config fields; no secrets/env-var field
