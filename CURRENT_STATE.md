# Bora Employer Pipeline OS — Current State

Updated: 2026-08-26

## Current Phase

Governing Blueprint: **Final Locked Blueprint v3.1**.

AI/tool operating-model governance synchronization = **CLOSED**.

Claim Validation hardening = **CLOSED**.

Winter Walk Evidence Repository v1 Batch 1 = **CLOSED** (12 evidence records committed).

Repository-Level Evidence Integrity v1 = **CLOSED**.

Minimal Experience Registry v1 = **CLOSED**.

Claude final adversarial recheck: `CLAUDE_MINIMAL_EXPERIENCE_REGISTRY_FINAL_PASS`.

Runtime behavior on authoritative success: `EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED`.

Structure-only path reports: `EXPERIENCE_REFERENCE_NOT_CHECKED`.

Causal failures preserved: `EXPERIENCE_REGISTRY_INVALID` vs `EXPERIENCE_ID_NOT_FOUND`.

Canonical Experience records: **1** (`EXP_WW_001`).

Evidence records: **12** Winter Walk Batch 1 (all reference `EXP_WW_001`; byte-unchanged by this milestone).

No reusable claims created yet.

No production engine yet.

## Completed

* Locked Blueprint loaded into repository; governing version now **v3.1**.
* Blueprint hardenings added for:

  * market-softness diagnostic handling;
  * legal verification boundaries;
  * strict structured-output schema validation.
* Git repository initialized.
* `AGENTS.md` created and locked.
* Cursor selected as the primary builder.
* ChatGPT selected as primary architect/research/reasoning/sequencing and final-decision-guidance layer.
* Claude Code designated as independent coding/evidence reviewer, milestone auditor, and harder-code escalation.
* Gemini designated as occasional non-coding strategic/directional/research second opinion only (not part of the coding execution or coding-review loop).
* AI/tool operating-model governance sync closed:

  * synchronized `BLUEPRINT.md`, `AGENTS.md`, `.cursor/rules/architecture.mdc`, `GEMINI.md`, and `CLAUDE.md`;
  * Blueprint bumped v3.0 → v3.1;
  * `CLAUDE.md` retained as minimal Claude Code reviewer/auditor instructions pointing to `BLUEPRINT.md`;
  * no production architecture or evidence semantics changed.
* Schema Milestone 1 closed:

  * `schemas/job.schema.json`, `schemas/requirement.schema.json`, and `schemas/evidence.schema.json` complete.
  * `discovered_date` stored separately from `date_first_seen` (also preserves `board_posted_date` and `date_last_verified`).
  * `source_verification_status` split from `role_status` freshness.
  * Shared deterministic job-url validator centralized in `src/job_url_format.py` (`format: "job-url"`).
  * Shared Draft 2020-12 schema validator helper in `src/schema_validation.py` always attaches the job-url FormatChecker (prevents silent skip via plain `FormatChecker()`).
  * Job URLs accept http/https; reject credentials, bad schemes, empty host, and literal whitespace/control characters; percent-encoded paths remain valid.
  * Behavioral smoke tests for all three schemas under `tests/` — all passing.
* Claim Validation milestone closed (including post-close hardening):

  * `schemas/claim.schema.json` built.
  * Lineage validator built (`src/claim_lineage.py`).
  * State compatibility validator built (`src/claim_state_validation.py`).
  * Unified `validate_claim()` built (`src/claim_validation.py`).
  * Claim validation is citation-scoped: only Evidence_IDs cited by the claim affect claim validity.
  * Context conflicts (`allowed_contexts` ∩ `forbidden_contexts`) block reusable use via `CONTEXT_CONFLICT`.
  * Sequence duplicate Evidence_IDs intentionally fail closed as repository identity-integrity protection (including uncited duplicates in sequence-form indexes).
  * All 7 related test suites pass.
  * Post-close hardening: regression coverage for uncited sequence duplicates and CONTRADICTED claim-state non-reuse; evidence schema validator construction hoisted outside per-ID loop (no behavior change).
* Winter Walk Evidence Repository v1 Batch 1 closed:

  * 12 evidence records committed under `evidence/winter_walk/` (`WW_ARCH_001`, `WW_ARCH_002`, `WW_CTRL_001`, `WW_CTRL_002`, `WW_MAP_001`, `WW_ADOPT_001`, `WW_DATA_001`, `WW_DATA_002`, `WW_CONN_001`, `WW_SYNC_001`, `WW_FUQ_001`, `WW_TEST_001`).
  * Provenance-first extraction from current Apps Script (`CODES-UP TO DATE.txt`), Boston 2027 Workbook A/B exports, and locked `WinterWalk_Master_Blueprint.docx`.
  * Independent Claude Code semantic audit completed.
  * Three review corrections applied (`WW_DATA_001`, `WW_DATA_002`, `WW_TEST_001` capabilities/limitations).
  * Final residual wording fix applied (`WW_TEST_001` notes: PII absence check).
  * All 12 records pass evidence schema validation; all 7 existing test suites pass.
  * No open Batch 1 findings.
  * No reusable claims created; schemas and validators unchanged by Batch 1.
* Repository-Level Evidence Integrity v1 closed:

  * Implementation commit `674784b`; hardening commit `09213b2`; closure commit `0dbc044`.
  * Independent Claude Code audit + required hardening + final recheck: `CLAUDE_EVIDENCE_INTEGRITY_FINAL_PASS`.
  * Deterministic Evidence Repository gate remains separate from claim-scoped validation.
* Minimal Experience Registry v1 closed:

  * Implementation commit `0806a99`; trust-boundary hardening `b9430b6`; closure commit follows.
  * Claude final adversarial recheck: `CLAUDE_MINIMAL_EXPERIENCE_REGISTRY_FINAL_PASS`.
  * `schemas/experience.schema.json` + canonical `experiences/EXP_WW_001.json` (`ORGANIZATIONAL_ENGAGEMENT`).
  * Opaque validator-issued `ValidatedExperienceRepository`; raw `experience_index=` bypass removed.
  * Authoritative Evidence validation enforces Experience references (`EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED`).
  * Structure-only Evidence path reports `EXPERIENCE_REFERENCE_NOT_CHECKED`.
  * Causal failures: `EXPERIENCE_REGISTRY_INVALID` vs `EXPERIENCE_ID_NOT_FOUND`.
  * All 11 test suites pass; 1 Experience + 12 Evidence records validate; Evidence JSON / Experience record / claim validators unchanged.
  * Ready as dependency for first reusable Claim Bank records (explicit approval still required before claim creation).
  * `NO_CLAIM_SCOPED_SEMANTIC_CHANGE`.

## Current Task

Next technical dependency: first reusable Claim Bank records — **NOT STARTED** (requires explicit approval).

`MINIMAL_EXPERIENCE_REGISTRY_V1` is **CLOSED** and is the approved Experience → Evidence dependency for claim creation.

## Not Built Yet

* Claims derived from Winter Walk evidence / Claim Bank v1 (**NEXT**; explicit approval required)
* Additional Experience records (MarketMind, Market Empire/FCAT, LoanIQ, TELUS, Bulmarma, D Commerce, etc.)
* Winter Walk Evidence Batch 2+
* Forbidden-claim registry implementation
* Deterministic fabricated-outcome / metric validators
* Production pipeline engine
* Job ingestion
* Job deduplication
* Role verification workflow
* Job requirement extraction
* OPT/work-authorization screening
* Evidence matching
* Fit routing
* Resume patch generation
* Resume rendering
* Resume diff review
* Networking research
* Application tracking
* Google Workspace integration
* External job-source integrations
* Automated monitoring

## Current Safety State

* No production application automation exists.
* No external integrations are connected.
* No job applications can be submitted automatically.
* No resume-generation pipeline exists yet.
* No reusable claims exist yet; Batch 1 evidence alone does not authorize resume wording.
* Winter Walk Batch 1 preserves UNKNOWN for daily production use, completed handoff, measured business impact, and live email sending unless separately evidenced.
* No runtime workflow depends on multi-model agreement; deterministic validators enforce invariants; evidence wins over model opinion; Bora retains consequential approval.
* No PII should be stored in this repository unless explicitly designed and approved later.
* No architectural dependency beyond the local repository has been approved.
* JSON Schema gates reject malformed structured records.
* Claim reusable-use requires schema + citation-scoped lineage + state compatibility + human approval + non-UNKNOWN/non-CONTRADICTED state + no context conflict.
* Semantic fabricated-outcome protection remains a later deterministic validator layer.
* Provenance spine now has Experience identity + Evidence integrity with referential enforcement: Experience → Evidence → (future) Claim.
* `EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED` on authoritative Evidence Repository validation.
* Experience Registry does not assert employment titles, dates, outcomes, or résumé content.

## Current Source of Truth

`BLUEPRINT.md` (**Final Locked Blueprint v3.1**)

If another project file conflicts with the Blueprint, stop and surface the conflict.

## Immediate Next Steps

1. First reusable Claim Bank records only after explicit approval (`CLAIM_BANK_V1` or equivalent).
2. Additional Experience IDs only when evidence or approved architecture requires them.
3. Forbidden-claim registry (only if approved).
4. Winter Walk Evidence Batch 2 (only if explicitly approved).

## Do Not Start Yet

Do not begin:

* claim creation without explicit approval;
* inventing additional Experience IDs without evidence/ADR need;
* Winter Walk Batch 2 without explicit approval;
* job scraping;
* job-board integrations;
* Google Sheets integration;
* Gmail integration;
* resume tailoring;
* AI job scoring;
* application automation;
* LinkedIn automation;
* MCP configuration;
* database selection;
* cloud infrastructure;
* production API integrations.

## Next Approved Task

First reusable Claim Bank records — **NOT STARTED**; requires explicit approval. Experience → Evidence spine is closed and ready as the dependency.
