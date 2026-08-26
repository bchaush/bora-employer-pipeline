# Bora Employer Pipeline OS — Current State

Updated: 2026-08-26

## Current Phase

Claim Validation milestone closed. No production evidence repository content loaded yet. No production engine yet.

## Completed

* Locked Blueprint v3.0 loaded into repository.
* Blueprint hardenings added for:

  * market-softness diagnostic handling;
  * legal verification boundaries;
  * strict structured-output schema validation.
* Git repository initialized.
* `AGENTS.md` created and locked.
* Cursor selected as the primary coding agent.
* ChatGPT selected as primary architect/research/reasoning layer.
* Gemini designated as independent verifier and backup.
* Claude designated as optional escalation/review only.
* Schema Milestone 1 closed:

  * `schemas/job.schema.json`, `schemas/requirement.schema.json`, and `schemas/evidence.schema.json` complete.
  * `discovered_date` stored separately from `date_first_seen` (also preserves `board_posted_date` and `date_last_verified`).
  * `source_verification_status` split from `role_status` freshness.
  * Shared deterministic job-url validator centralized in `src/job_url_format.py` (`format: "job-url"`).
  * Shared Draft 2020-12 schema validator helper in `src/schema_validation.py` always attaches the job-url FormatChecker (prevents silent skip via plain `FormatChecker()`).
  * Job URLs accept http/https; reject credentials, bad schemes, empty host, and literal whitespace/control characters; percent-encoded paths remain valid.
  * Behavioral smoke tests for all three schemas under `tests/` — all passing.
* Claim Validation milestone closed:

  * `schemas/claim.schema.json` built.
  * Lineage validator built (`src/claim_lineage.py`).
  * State compatibility validator built (`src/claim_state_validation.py`).
  * Unified `validate_claim()` built (`src/claim_validation.py`).
  * Claim validation is citation-scoped: only Evidence_IDs cited by the claim affect claim validity.
  * Context conflicts (`allowed_contexts` ∩ `forbidden_contexts`) block reusable use via `CONTEXT_CONFLICT`.
  * Sequence duplicate Evidence_IDs intentionally fail closed as repository identity-integrity protection.
  * All 7 related test suites pass.
  * No production evidence repository content loaded yet.

## Current Task

Await next approved implementation task after Claim Validation closeout.

## Not Built Yet

* Evidence repository content / loading
* Forbidden-claim registry implementation
* Repository-wide evidence integrity validator
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
* No PII should be stored in this repository unless explicitly designed and approved later.
* No architectural dependency beyond the local repository has been approved.
* JSON Schema gates reject malformed structured records.
* Claim reusable-use requires schema + citation-scoped lineage + state compatibility + human approval + non-UNKNOWN/non-CONTRADICTED state + no context conflict.
* Semantic fabricated-outcome protection remains a later deterministic validator layer.

## Current Source of Truth

`BLUEPRINT.md`

If another project file conflicts with the Blueprint, stop and surface the conflict.

## Immediate Next Steps

Await Bora's next approved task. Likely candidates:

1. Evidence repository content / loading conventions
2. Forbidden-claim registry
3. Repository-wide evidence integrity validator
4. Additional schemas only as explicitly approved

## Do Not Start Yet

Do not begin:

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

These begin only after the governed workbench is complete and the first implementation phase is approved.

## Next Approved Task

None assigned. Claim Validation milestone is closed. Await explicit approval for the next implementation task.
