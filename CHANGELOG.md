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
