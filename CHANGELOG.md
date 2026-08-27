# Bora Employer Pipeline OS — Change Log

This file records material changes to the system.

Do not use this file for every typo or formatting edit. Record changes that affect:

* architecture;
* data models;
* evidence rules;
* claim rules;
* resume logic;
* immigration/work-authorization handling;
* integrations;
* application workflow;
* safety controls;
* schemas;
* validators;
* production behavior.

---

## 2026-08-26 — Repository-Level Evidence Integrity v1 (IMPLEMENTED — PENDING CLAUDE CODE AUDIT)

**Reason**

Add the smallest deterministic repository-wide Evidence Repository integrity layer before reusable claims are created. This gate is deliberately separate from claim-scoped lineage validation.

**Changed**

* Added `src/evidence_repository.py`:
  * recursive deterministic `*.json` discovery under `evidence/`;
  * JSON parse integrity;
  * canonical `schemas/evidence.schema.json` validation via shared `build_draft202012_validator`;
  * global `evidence_id` uniqueness (no last-write-wins);
  * filename stem ↔ `evidence_id` exact match;
  * one-record-object-per-file shape enforcement;
  * fail-closed trusted index (`index` is `None` when invalid).
* Added `tests/evidence_repository_test.py` (PASS 1–10, 12; PASS 11 = existing claim suites).
* Current committed Winter Walk Batch 1 (12 records) passes repository validation.
* Claim-scoped validators unchanged (`NO CLAIM-SCOPED SEMANTIC CHANGE`).
* Unresolved: `EXPERIENCE_REGISTRY_DECISION_REQUIRED` — no authoritative Experience Registry; do not invent one; `experience_id` remains schema non-empty string only.

**Affected Areas**

* `src/evidence_repository.py` (new)
* `tests/evidence_repository_test.py` (new)
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Discovery convention v1: every `*.json` under the evidence root is a candidate record (no manifest). Non-record JSON in that tree will fail closed.
* Experience referential integrity is intentionally not enforced until a registry is approved.
* Milestone not CLOSED; Claude Code audit required.

**Tests / Verification**

* `tests/evidence_repository_test.py` — PASS
* All 7 existing suites — PASS (no regression)
* `git diff --check` — clean

**Approved By**

Implementation by Cursor; pending ChatGPT review and Claude Code audit

**Status**

IMPLEMENTED — PENDING CLAUDE CODE AUDIT (not CLOSED; not pushed pending ChatGPT review)

---

## 2026-08-26 — AI/Tool Operating-Model Governance Sync (Blueprint v3.1)

**Reason**

Bora explicitly approved a correction to the project's AI/tool operating model so future sessions do not inherit contradictory Gemini/Claude role instructions. ChatGPT review approved Blueprint version bump v3.0 → v3.1 and retention of `CLAUDE.md`.

**Changed**

* Locked Blueprint version updated to **v3.1**.
* Synchronized locked roles across `BLUEPRINT.md`, `AGENTS.md`, `.cursor/rules/architecture.mdc`, `GEMINI.md`, `CURRENT_STATE.md`, and `CLAUDE.md`.
* **ChatGPT** = primary architect / research / reasoning / sequencing / final decision guidance.
* **Cursor** = primary builder.
* **Claude Code** = independent coding/evidence reviewer, milestone auditor, and harder-code escalation (not a second primary builder).
* **Gemini** = occasional non-coding strategic / directional / research second opinion only; removed from the coding execution/coding-review loop and backup-builder role.
* Preserved: no multi-model runtime dependency; deterministic validators enforce; evidence wins; Bora decides.
* No production architecture change and no evidence-semantics change.
* Next technical milestone remains `REPOSITORY_LEVEL_EVIDENCE_INTEGRITY` (not started).

**Affected Areas**

* `BLUEPRINT.md`
* `AGENTS.md`
* `.cursor/rules/architecture.mdc`
* `GEMINI.md`
* `CLAUDE.md`
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Documentation/rules-only change. Does not alter schemas, validators, evidence, claims, or production code.
* Creating `CLAUDE.md` follows the existing `GEMINI.md` model-instruction-file convention and points to `BLUEPRINT.md` rather than duplicating it.
* Historical CHANGELOG entries describing the former Gemini/Claude architecture remain unchanged as historical records.

**Tests / Verification**

All 7 existing test suites pass (exit 0). Docs-only change.

**Approved By**

Bora; ChatGPT governance review

**Status**

Implemented — Blueprint v3.1 governance sync closed

---

## 2026-08-26 — Winter Walk Evidence Repository v1 Batch 1 Closed

**Reason**

Load the first provenance-governed Winter Walk evidence set into the repository before any claim creation or resume derivation.

**Changed**

* Added 12 Winter Walk evidence records under `evidence/winter_walk/` (`WW_ARCH_001`–`WW_ARCH_002`, `WW_CTRL_001`–`WW_CTRL_002`, `WW_MAP_001`, `WW_ADOPT_001`, `WW_DATA_001`–`WW_DATA_002`, `WW_CONN_001`, `WW_SYNC_001`, `WW_FUQ_001`, `WW_TEST_001`).
* Extracted from current accessible sources only: Apps Script (`CODES-UP TO DATE.txt`), Boston 2027 Workbook A/B exports, and locked `WinterWalk_Master_Blueprint.docx`.
* Independent Claude Code semantic audit completed; three review corrections applied (backup/restore reliability limitation, intake-pipeline limitation, Pilot_Results capability wording); final residual notes wording fix (`PII absence check`).
* Preserved UNKNOWN / non-claim boundaries for daily production use, completed organizational handoff, live email sending, continuous successful ingestion, measured hours/productivity, and fundraising/business impact.
* No claims created. No schemas or validators modified.

**Affected Areas**

* `evidence/winter_walk/*.json`
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Batch 1 is implementation/design/test evidence only. Runtime deployment cadence and outcomes remain unresolved until stronger sources exist.
* Evidence records cite external Level-0 artifacts not yet copied into the repo vault; provenance paths must remain stable for later claim review.

**Tests / Verification**

All 12 Batch 1 records pass evidence schema validation. All 7 existing test suites pass (exit 0).

**Approved By**

Bora

**Status**

Implemented — Winter Walk Evidence Repository v1 Batch 1 closed

---

## 2026-08-26 — Claim Validation Post-Close Hardening

**Reason**

Add locked-decision regression coverage and a small performance cleanup after Claim Validation closeout, without architecture redesign.

**Changed**

* Added lineage regression: sequence-form evidence index with a duplicate Evidence_ID that is not cited by the claim still fails closed (`DUPLICATE_EVIDENCE_ID_IN_INDEX`).
* Added direct state-validator unit coverage: claim `evidence_state = CONTRADICTED` returns `CLAIM_STATE_NOT_REUSABLE` / invalid-for-reuse.
* Hoisted `build_draft202012_validator(EVIDENCE_SCHEMA_PATH)` outside the per-Evidence_ID loop in `src/claim_state_validation.py` (performance cleanup only; no behavior change).
* No architecture change.

**Affected Areas**

* `tests/claim_lineage_test.py`
* `tests/claim_state_validation_test.py`
* `src/claim_state_validation.py`

**Risks / Tradeoffs**

* None material. Sequence uncited-duplicate fail-closed remains intentionally stricter than citation-scoped malformed-record ignoring.

**Tests / Verification**

All 7 related suites passed after hardening.

**Approved By**

Bora

**Status**

Implemented — Claim Validation post-close hardening complete

---

## 2026-08-26 — Claim Validation Milestone Closed

**Reason**

Complete deterministic Claim Validation before loading production evidence repository content or building resume/application generation.

**Changed**

* Built `schemas/claim.schema.json` with Blueprint §15 claim fields and locked evidence states.
* Built lineage validator in `src/claim_lineage.py` (exact, case-sensitive Evidence_ID resolution; no silent repairs).
* Built state compatibility validator in `src/claim_state_validation.py`.
* Built unified `validate_claim()` in `src/claim_validation.py` with `valid_record` vs `reusable` distinction.
* Claim validation is citation-scoped: only Evidence_IDs cited by the claim are schema/state-checked; unrelated repository records do not invalidate the claim.
* Context conflicts block reusable use (`CONTEXT_CONFLICT`); contexts are not silently removed; human approval cannot override.
* Sequence duplicate Evidence_IDs intentionally fail closed as repository identity-integrity protection.
* CONTRADICTED claims remain schema-legal for archival/audit use but are never reusable.
* No production evidence repository content loaded yet.

**Affected Areas**

* `schemas/claim.schema.json`
* `src/claim_lineage.py`
* `src/claim_state_validation.py`
* `src/claim_validation.py`
* `tests/claim_schema_smoke_test.py`
* `tests/claim_lineage_test.py`
* `tests/claim_state_validation_test.py`
* `tests/claim_validation_test.py`

**Risks / Tradeoffs**

* Repository-wide evidence integrity remains deferred to a future repository validator.
* Fabricated-outcome / unsupported-metric truth checking remains outside this milestone.
* Sequence duplicate-ID fail-closed is intentionally stricter than citation-scoped malformed-record ignoring.

**Tests / Verification**

All 7 related suites passed:

* `python tests/claim_lineage_test.py`
* `python tests/claim_state_validation_test.py`
* `python tests/claim_validation_test.py`
* `python tests/claim_schema_smoke_test.py`
* `python tests/job_schema_smoke_test.py`
* `python tests/requirement_schema_smoke_test.py`
* `python tests/evidence_schema_smoke_test.py`

**Approved By**

Bora

**Status**

Implemented — Claim Validation milestone closed

**Next Milestone**

Await explicit approval (likely Evidence Repository content/loading, forbidden-claim registry, or repository-wide integrity validator)

---

## 2026-08-26 — Schema Milestone 1 Post-Close Hardening

**Reason**

Harden Schema Milestone 1 without redesign: shared Draft 2020-12 validator helper that always includes job-url enforcement, plus stronger requirement smoke coverage.

**Changed**

* Added `src/schema_validation.py` — loads Draft 2020-12 schemas and builds validators using `build_job_format_checker()` so production code cannot silently skip job-url checks with plain `FormatChecker()`.
* Strengthened `tests/requirement_schema_smoke_test.py` with missing-required-field and unexpected-additional-property rejection tests.
* Pointed `tests/job_schema_smoke_test.py` at the shared schema validator helper.
* URL acceptance rules remain solely in `src/job_url_format.py` (not duplicated).

**Affected Areas**

* `src/schema_validation.py`
* `tests/requirement_schema_smoke_test.py`
* `tests/job_schema_smoke_test.py`

**Risks / Tradeoffs**

* Evidence smoke test still constructs its own validator; it can migrate to the shared helper later without schema changes.
* Custom `job-url` format still requires importing the shared helper (or `build_job_format_checker`) in any new validation path.

**Tests / Verification**

All three smoke tests passed after hardening.

**Approved By**

Bora

**Status**

Implemented — Schema Milestone 1 hardening complete; no further Schema Milestone 1 work

**Next Milestone**

Evidence Repository + Claim Lineage Validator

---

## 2026-08-26 — Schema Milestone 1 Closed

**Reason**

Close Schema Milestone 1 with complete core schemas, axis separations, shared job-url validation, and passing smoke tests before starting Evidence Repository + Claim Lineage work.

**Changed**

* Job, requirement, and evidence Draft 2020-12 schemas complete.
* Job freshness dates keep `discovered_date` separate from `date_first_seen` (also preserves `board_posted_date` and `date_last_verified`).
* Direct-source verification (`source_verification_status`) split from role freshness (`role_status`).
* Shared deterministic job-url validator centralized in `src/job_url_format.py` and registered as format `job-url`.
* Job URLs accept http/https; reject embedded credentials, non-http(s) schemes, empty host, and literal whitespace/control characters; percent-encoded paths remain allowed.
* Strengthened job/requirement/evidence behavioral smoke tests; all passing.
* No production engine built in this milestone.

**Affected Areas**

* `schemas/job.schema.json`
* `schemas/requirement.schema.json`
* `schemas/evidence.schema.json`
* `src/job_url_format.py`
* `tests/job_schema_smoke_test.py`
* `tests/requirement_schema_smoke_test.py`
* `tests/evidence_schema_smoke_test.py`

**Risks / Tradeoffs**

* `source_verification_status` values remain implementation vocabulary, not Blueprint-locked terminology.
* Fabricated-outcome / unsupported-metric protection remains intentionally outside JSON Schema; deferred to a later deterministic claim/outcome validator.
* `format: "job-url"` is custom and depends on the shared FormatChecker; production validators must import `build_job_format_checker()`.

**Tests / Verification**

Final smoke-test run passed:

* `python tests/job_schema_smoke_test.py`
* `python tests/requirement_schema_smoke_test.py`
* `python tests/evidence_schema_smoke_test.py`

**Approved By**

Bora

**Status**

Implemented — Schema Milestone 1 closed

**Next Milestone**

Evidence Repository + Claim Lineage Validator

---

## 2026-08-26 — Schema Milestone 1 (Initial)

**Reason**

Establish canonical Draft 2020-12 JSON Schemas and behavioral smoke tests for the first core structured records before production feature work.

**Changed**

* Added `schemas/job.schema.json` with:

  * separate `discovered_date`, `date_first_seen`, `board_posted_date`, and `date_last_verified`;
  * independent `role_status` (freshness) and `source_verification_status` (direct-source) axes;
  * locked E-Verify vocabulary that rejects `NOT_ENROLLED`.
* Added `schemas/requirement.schema.json`.
* Added `schemas/evidence.schema.json`.
* Added behavioral smoke tests:

  * `tests/job_schema_smoke_test.py`
  * `tests/requirement_schema_smoke_test.py`
  * `tests/evidence_schema_smoke_test.py`

**Affected Areas**

* schemas;
* validators / smoke tests;
* job freshness and source-verification data model.

**Risks / Tradeoffs**

* `source_verification_status` values are implementation vocabulary, not Blueprint-locked terminology.
* Fabricated-outcome / unsupported-metric protection is intentionally not enforced by JSON Schema; it belongs in a later deterministic claim/outcome validator.
* Early job URL checking used a test-local FormatChecker before centralization into `src/job_url_format.py`.

**Tests / Verification**

All three smoke tests passed:

* `python tests/job_schema_smoke_test.py`
* `python tests/requirement_schema_smoke_test.py`
* `python tests/evidence_schema_smoke_test.py`

**Approved By**

Bora

**Status**

Superseded by Schema Milestone 1 Closed entry above

---

## 2026-08-25 — Workbench Initialization

### Added

* Initialized Git repository.
* Added canonical `BLUEPRINT.md`.
* Added `AGENTS.md` operating contract.
* Added `CURRENT_STATE.md`.

### Blueprint Hardening

Added or reinforced:

* external market-softness diagnostic handling;
* `LEGAL_VERIFICATION_REQUIRED` boundary for unresolved consequential immigration/work-authorization interpretation;
* strict JSON Schema validation before structured AI output reaches downstream rendering or production components.

### Architecture Status

Locked tool roles:

* ChatGPT — architecture, research, semantic reasoning, quality decisions
* Cursor — primary implementation and repository agent
* Gemini — independent verifier and backup
* Claude — optional escalation/review only

### Current Status

Workbench setup in progress.

No production features or external integrations have been built yet.

---

## Change Entry Template

Copy this section for future material changes.

### YYYY-MM-DD — Short Change Name

**Reason**

Why the change was required.

**Changed**

* item
* item

**Affected Areas**

* files/modules/rules

**Risks / Tradeoffs**

* risk or tradeoff

**Tests / Verification**

* what was tested or reviewed

**Approved By**

Bora

**Status**

Approved / Implemented / Reverted
