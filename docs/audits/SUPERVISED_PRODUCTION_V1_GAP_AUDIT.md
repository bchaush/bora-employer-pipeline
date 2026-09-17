# Supervised Production V1 Gap Audit

Status: READ-ONLY CANONICAL AUDIT COMPLETE
Date: 2026-09-16
Canonical baseline audited: `d16c4473d3fb1505a95c5a95c90c766a0a4afd5c`
Audit authority: repository truth outranks chat history and uploaded historical copies.

## Purpose

Compare the live canonical repository against the proposed Career OS supervised-production loop without authorizing product implementation.

Target loop:

`Scout -> Normalize -> Cheap Gates -> Verify -> Match Truth -> Bora Review -> Golden Package -> Application Ledger`

Permanent human gates remain:

`PURSUE?` and `SUBMIT?`

## Canonical conflict resolved

The uploaded August blueprint is v3.0. Canonical `BLUEPRINT.md` is v3.13 and wins.
Canonical v3.13 records the Brandeis MS as completed/awarded by direct attestation while STEM/CIP designation remains not independently ingested.
No production contract may reintroduce the older v3.0 `MSBA (STEM)` statement as established Candidate Truth.
## Gap classification

### REUSE

- `schemas/job.schema.json`: mature canonical Job record with source, freshness, OPT, E-Verify, evidence-match, decision, resume, application, and outcome fields.
- `src/job_analysis.py`, `src/job_decision.py`, qualification/evidence evaluators: current Judge / Match Truth core.
- `schemas/application_*.schema.json` and application evaluators: route/question/application truth contracts already exist.
- `docs/application/BORA_APPLICATION_HISTORY_V1.json`: exact employer + exact requisition application-history dedupe and lifecycle continuity.
- Resume truth stack: patching, lineage, immutable metadata, presentation views, validation, diff, page-utilization, and protected master structures. The current text renderer is TEST-ONLY and must not be represented as a production DOCX/PDF package generator.
- Assurance, Golden tests, milestone-state validation, immutable-candidate review doctrine, and protected-path governance.
- `ADR-PURSUIT-APPROVAL-BOUNDARY-V1.md`: architecture already separates system recommendation from Bora pursuit authorization and final submission.

### ADAPT

- Blueprint already locks `DiscoveryLead` as the untrusted discovery boundary concept. Slice 1 should adapt/implement that seam rather than invent a parallel lead model; no production `DiscoveryLead` persistence/schema is currently implemented.
- Existing application-history JSON should become an input to the operational ledger rather than be replaced or fuzzy-matched.
- Resume components are reusable, but no single production `generate_resume(Job_ID)` / Golden Package orchestration entrypoint currently exists.
- Existing application schemas are reusable, but there is no production persistence/writer path for `ApplicationAttempt` or `Job.application_status`.
- Existing deterministic gates should be composed into a batch runner; do not rewrite gate semantics inside Sheet/Vercel code.
### MISSING

- Durable operational Sheet/control-plane state for `JOBS`, `APPLICATIONS`, and `LOG`.
- Durable canonical persistence for newly learned human eligibility/logistical facts (for example the directly attested `driver_license = NO`) so unattended production never depends on chat memory.
- Gmail alert ingestion -> normalized discovery leads -> dedupe -> Sheet persistence.
- A production `process_batch(...)` orchestration path. Blueprint requires it; canonical code does not implement it.
- A durable opportunity-level Bora pursuit decision record/consumer. The architecture is already defined; implementation is intentionally deferred.
- A bounded package orchestration entrypoint triggered only after pursuit approval, including production DOCX/PDF generation/export and Drive persistence; current resume text rendering is TEST-ONLY and no production `generate_resume(Job_ID)` / complete Golden Package exporter exists.
- Drive package persistence + links written back to the operational ledger.
- Production run IDs, source-level run metrics, retry/error state, and daily compact review output.
- Thin Vercel control-plane deployment, only after the Sheet vertical slice proves the loop.

### DO NOT BUILD

- A new Match Truth brain, generalized semantic rewrite, or preemptive evaluator family.
- A second truth database or Postgres/Supabase/Firebase for V1.
- A custom job board, universal ATS scraper, custom autofill, or autonomous submitter.
- Business logic that exists only in a Vercel UI.
- A hard dependency on Claude, Firecrawl, Handshake, Simplify, Vercel, or any other commodity provider as part of the truth core.
- Any automatic interpretation that upgrades nomination/source claims into Employer Truth.

## Connected-surface observations

Google Drive/Sheets connection is live, but no existing Career OS spreadsheet was found under obvious Career OS / Employer Pipeline names or in the accessible spreadsheet inventory.
Vercel tool connection is present, but the current account surface returned no visible teams/projects and no local `.vercel/project.json` exists in the Career OS workspaces.
Neither observation blocks the first vertical slice; both reinforce Sheet-first, Vercel-later sequencing.
