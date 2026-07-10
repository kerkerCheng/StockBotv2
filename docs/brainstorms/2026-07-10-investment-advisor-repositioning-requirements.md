# Requirements: StockBotv2 → Personal AI-Theme Investment Advisor

**Date:** 2026-07-10
**Status:** Draft — awaiting user confirmation
**Scope:** Deep — product (full repositioning)

---

## What We're Building

A personal investment advisor for AI-theme equities that works around the user's attention — not against it.

The system already has the right three-layer architecture (Skill / Knowledge Graph / Pipeline). What it lacks is: credible source depth per company, a portfolio context layer, a low-friction entry point for new ideas, and a proactive nudge mechanism for when the user isn't actively looking.

**Core value proposition:** Faster than manual research, more credible than pure LLM (source-traceable graph), more personal than generic AI (knows your portfolio and risk tolerance).

---

## User Profile

- Single user, local self-use
- Investment model: large-cap base (buy-and-hold, rarely exits) + high-risk AI-theme bucket for alpha
- Time horizon: long-term holds; exit signal = thesis invalidation (disproof_condition), not price targets
- Attention pattern: highly engaged when focused, easily absorbed by other priorities — system must work without demanding regular check-ins
- Portfolio data: maintained in Google Sheets (has done GCP API integration before)

---

## Goals

1. **Credible per-company research** — Answers about a company should be grounded in 3+ independent sources, not just the company's own IR material
2. **Personalized advice** — Position sizing and entry framing should account for the user's actual asset allocation and risk tolerance
3. **Low activation energy** — Seeing something interesting → system is researching it within 2–3 messages; no manual copy-paste, no pipeline commands
4. **Attention-aware nudges** — System proactively surfaces brief signals when the user is away; user can engage or ignore in one reply

---

## Success Criteria

- A company analysis can be generated and trusted: ≥3 independent `origin_entity` sources, no `gate_override` due to L8 weakness
- User can ask "how much should I put into SIVE?" and get an answer grounded in their actual Google Sheets data
- A new SNS-sourced idea can go from "I saw this on X" to "system is finding documents" in one conversation turn
- Weekly cron brief is ≤5 bullets, readable in 30 seconds, and requires only a one-word reply to trigger deeper research

---

## Scope

### In scope (priority order)

**1. Agentic Document Discovery**
When a company is mentioned, system auto-searches EDGAR + web + academic sources, formats relevant excerpts as structured raw input, and presents a shortlist for user approval. User confirms; system auto-runs extract → validate → load. Eliminates the "search and copy-paste into raw file" manual step. User still approves source independence before loading.

**2. Source Quality Gate (Audit Mechanism)**
A Lane Memo cannot be generated until the company has ≥3 independent `origin_entity` sources. If the threshold isn't met, the system says so explicitly and requests specific missing source types (e.g., "I need a customer-side document confirming sole-source status"). Cannot be bypassed via `gate_override` without explicit user acknowledgment of the weakness.

**3. CPO Theme Depth Sprint**
Bring SIVE + Coherent + Lumentum + 2 customer-side companies to credible standard (≥3 independent sources each, L8 satisfied). This is the first "complete module" that opens investment advice for the CPO theme.

**4. Google Sheets Portfolio Integration**
Pull the user's asset distribution and current high-risk bucket allocation via GCP API. Feed into a position-sizing skill that gives "given your current bucket utilization and this thesis's conviction level, here's a suggested allocation range."

**5. Engine B: Two-Mode Lead Intake**

*Mode 1 — User-initiated triage (pull):*
User pastes a tweet / headline / a few sentences. System responds in ≤3 turns with: signal classification (product news / supply chain / earnings / sentiment), relevance to existing graph, and a go/no-go on opening a research thread. If go: triggers agentic document discovery automatically.

*Mode 2 — Scheduled scan (push):*
CronCreate-based, two output tiers — both adjustable in depth and format:

- **Weekly 大週報** (main cadence): Covers all active themes for the week — new developments, earnings mentions, supply chain signals, anything that touches existing theses or surfaces new candidates. Length is calibrated to what actually happened that week; sparse weeks get a brief summary, eventful weeks get more. The goal is "worth sitting down for 5 minutes" when the user has time.

- **30-second brief** (event-triggered): Fires ad-hoc when a high-signal event is detected mid-week — e.g., a major earnings call mentions a company in the graph, a thesis disproof condition is potentially triggered, or a significant news item breaks. Format: 1–2 sentences + one Y/N action. User can engage in one reply or ignore.

Both tiers run against a user-maintained theme list (lightweight text file: active themes + key companies). Depth and frequency are tunable.

**6. Thesis Lifecycle Monitoring**
Tied to the existing disproof_condition system. Scheduled reminder (CronCreate or conversational check-in) prompts review of active theses quarterly. Format: "SIVE thesis is 3 months old. Disproof condition: [X]. Has anything triggered this? Y to review, N to snooze 4 weeks."

**7. Second Vertical Slice**
Pick a non-CPO AI theme (humanoid robotics or energy — to be decided when CPO module is complete). Run the full stack: document discovery → graph → Lane Memo → quality gate. Validates that the methodology is portable across themes, not a CPO-specific artifact. Required before L9 investment advice opens fully.

### Out of scope / deferred

- **Engine B SNS API direct integration (X/Threads)**: API cost prohibitive; `last30days` covers theme-level social signals adequately for the push use case
- **Automated independent source judgment**: L8 quality gate remains human-approved by design — this is a feature, not a gap
- **Full sector map / cross-company report template**: Post-Phase 2 (after depth per company is solid)
- **Underwrite Sheet output tier**: Deferred until Watchlist has enough depth
- **Engine B personal X feed**: System scans themes, not the user's personalized timeline

---

## Design Principles

**Attention-aware, not attention-demanding.** Every output has a clear default action (ignore = snooze) and an easy engagement path (one reply = system continues). No output should require the user to "sit down and focus" just to acknowledge it.

**Quality gate is not optional.** The audit mechanism blocks Lane Memo generation below the source threshold. This is a hard constraint, not a soft warning. Bypassing it degrades the entire advice layer.

**Machine does search and format; human judges independence.** The L8 problem (self-report bias) cannot be automated away. The system surfaces candidates; the user approves source independence. This boundary is intentional.

**Each theme is a self-contained module.** CPO, humanoid robotics, energy — each gets the same stack (discovery → graph → audit → memo → advice). Advice for a theme opens only when that theme's module meets the quality threshold.

---

## Key Assumptions (unverified)

- GCP API credentials for Google Sheets are accessible or can be re-established (user has done this before)
- EDGAR earnings call transcripts: fetchers/edgar.py covers SEC filings, but earnings call verbatim transcripts are typically on Seeking Alpha / Rev.com, not EDGAR directly — the agentic document discovery strategy needs to account for this gap
- CronCreate requires the Claude Code daemon to be running locally; truly background execution on Windows may need additional setup (Windows Task Scheduler as trigger)
- `last30days` skill's 3 active sources cover sufficient social signal for theme-level scanning; if not, source list can be extended

---

## What's Already Built (relevant to this plan)

- Engine A: Neo4j graph with extract → validate → load pipeline
- Engine C: SQLite financial snapshots, `checklist.py` (5-item Watchlist Gate), `etl_yfinance.py`
- Existing skills: `investment-research`, `lead-intake`, `blind-spot-audit`
- `fetchers/edgar.py`: EDGAR filing fetcher
- Thesis lifecycle: `disproof_condition` system in schema, `thesis/preconditions.py` for L9 gate
- Two Lane Memos: CPO (cpo_v1_lane_memo.md), SIVE (sivers_v1_lane_memo.md — currently gate_override due to L8)
- A→C join key: architecture defined, gap D6 (ticker not yet in Neo4j Company nodes) pending

---

## Outstanding Questions (for planning)

- Which AI theme for the second vertical slice — humanoid robotics or energy? (Can decide when CPO module is complete)
- Exact source strategy for earnings call transcripts (not in EDGAR): which services / APIs are accessible and free?
- CronCreate output routing: push notification vs. file-based vs. next-session injection — what's reliable on Windows?
- Theme keyword list format: simple text file in repo, or something queryable?
