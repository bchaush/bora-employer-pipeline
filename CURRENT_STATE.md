# Bora Employer Pipeline OS — Current State

Updated: 2026-08-25

## Current Phase

Workbench setup and repository governance.

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

## Current Task

Complete repository workbench setup before any production feature development begins.

## Not Built Yet

* Evidence repository
* Claim bank
* Forbidden-claim registry implementation
* Job ingestion
* Job deduplication
* Role verification
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

## Current Source of Truth

`BLUEPRINT.md`

If another project file conflicts with the Blueprint, stop and surface the conflict.

## Immediate Next Steps

1. Create repository folder structure.
2. Create `CHANGELOG.md`.
3. Create `GEMINI.md`.
4. Create `.cursor/rules/`.
5. Add initial rule files.
6. Create `docs/decisions/`.
7. Create schemas, tests, evidence, claims, prompts, source, golden-test, and log directories.
8. Make the first clean Git commit.

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

Create the repository skeleton and persistent agent-rule structure.
