# Bora Employer Pipeline OS — Current State

Updated: 2026-08-26

## Current Phase

Schema Milestone 1 complete. Core structured-record schemas and behavioral smoke tests are in place.

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
* Schema Milestone 1:

  * `schemas/job.schema.json` — job record with separate freshness dates, independent `role_status` and `source_verification_status` axes, and locked E-Verify vocabulary (no `NOT_ENROLLED`).
  * `schemas/requirement.schema.json` — requirement record with Blueprint-aligned importance states.
  * `schemas/evidence.schema.json` — evidence truth-layer record with Blueprint-aligned evidence states.
  * Behavioral smoke tests for all three schemas under `tests/`.

## Current Task

Await next approved implementation task after Schema Milestone 1 closeout.

## Not Built Yet

* Evidence repository content
* Claim bank
* Forbidden-claim registry implementation
* Deterministic claim/outcome validators (beyond JSON Schema)
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
* JSON Schema gates reject malformed structured records; semantic fabricated-outcome protection remains a later deterministic validator layer.

## Current Source of Truth

`BLUEPRINT.md`

If another project file conflicts with the Blueprint, stop and surface the conflict.

## Immediate Next Steps

Await Bora's next approved task. Likely candidates after Schema Milestone 1:

1. Additional schemas (claims, fit, resume patch, etc.) as approved.
2. Deterministic validators beyond JSON Schema.
3. Repository data directories and identifier conventions.
4. First local ingestion/validation workflow.

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

None assigned. Schema Milestone 1 is closed. Await explicit approval for the next implementation task.
