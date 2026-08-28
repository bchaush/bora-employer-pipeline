# Bora Employer Pipeline OS — Current State

Updated: 2026-08-27

## Current Phase

Governing Blueprint: **Final Locked Blueprint v3.1**.

AI/tool operating-model governance synchronization = **CLOSED**.

Claim Validation hardening = **CLOSED**.

Winter Walk Evidence Repository v1 Batch 1 = **CLOSED** (12 evidence records committed).

Repository-Level Evidence Integrity v1 = **CLOSED**.

Minimal Experience Registry v1 = **CLOSED**.

Claim Bank v1 first Winter Walk reusable claims = **CLOSED**.

Job Analysis v1 first vertical slice = **CLOSED**.

Job Analysis v1 Golden Set = **CLOSED**.

P-2 process-mapping evidence model = **P-2_EVIDENCE_MODEL_RESOLVED** (CLAIM_WW_006 approved for reusable use).

Canonical Experience records: **1** (`EXP_WW_001`).

Evidence records: **13** Winter Walk (`WW_ARCH_001`–`WW_TEST_001` Batch 1 plus `WW_PROC_001` for process mapping).

Claim records: **6** Winter Walk approved reusable claims under `claims/winter_walk/` (`CLAIM_WW_001`–`CLAIM_WW_006`); `human_approval=true` (`valid_record=true`, `reusable=true`).

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
* Claim Bank v1 first Winter Walk reusable claims implemented (not CLOSED):

  * 5 proposed claim records: `claims/winter_walk/CLAIM_WW_001.json` … `CLAIM_WW_005.json`.
  * Distinct capabilities: scope/requirements, fail-closed send controls, Drive CSV intake logging, form-to-evidence + approval sync, pilot/UAT documentation.
  * Existing claim schema + lineage + state + unified validators used; no new claim-repository validator (deferred; file uniqueness manual for v1).
  * All 5: `valid_record=true`, `human_approval=false`, `reusable=false` (`NOT_HUMAN_APPROVED`) pending Bora approval.
  * Evidence lineage and evidence-state compatibility verified against trusted Winter Walk Evidence index.
  * No Evidence/Experience/schema/validator changes; no unsupported outcomes or semantic upgrades.
  * Status: **IMPLEMENTED** (records present; Claim Bank not CLOSED).
* Claim Bank v1 required hardening implemented (not CLOSED):

  * Deterministic semantic boundary guard (`src/claim_semantic_guard.py`) wired into `validate_claim`; blocks known unsupported upgrades and fabricated quantified outcomes with `FORBIDDEN_SEMANTIC_PATTERN` (`valid_record=false`).
  * Guard is evidence-relative (not a global keyword blacklist): phrases allowed only when cited Evidence support corpus supports them.
  * Claim repository integrity (`src/claim_repository.py`): unique Claim_ID, filename↔ID match, schema, strict JSON, fail-closed index.
  * Real five claim wordings / lineage / states / contexts / `human_approval=false` unchanged.
  * Downstream requested-context consumption deferred until résumé/application consumer exists (self-conflict still enforced).
  * Status: **IMPLEMENTED** (Claim Bank not CLOSED).
* Claim Bank v1 final semantic hardening implemented (not CLOSED):

  * Negation/limitation leakage fixed: Evidence matches count as support only outside explicit negated/excluded local windows.
  * Quantified-outcome context leakage fixed: numbers must appear near matching outcome-category language (bare unrelated numbers do not authorize).
  * Trivial wording/formatting variant normalization added (lowercase, hyphen→space, bounded equivalent forms).
  * Real five Winter Walk claims unchanged; still `human_approval=false` / `reusable=false`.
  * Claim Repository remains valid (5 records; no module refactor).
  * Status: **IMPLEMENTED_PENDING_RECHECK** (superseded by closure below).
* Claim Bank v1 approval closure (**CLOSED**):

  * Bora explicitly approved `CLAIM_WW_001`–`CLAIM_WW_005` (`human_approval=true`).
  * All five validate as `valid_record=true` / `reusable=true` against trusted Evidence index.
  * Claim Repository integrity enforced (5 unique IDs; filename↔ID).
  * Semantic guard final Claude adversarial recheck: `CLAUDE_CLAIM_BANK_V1_FINAL_PASS`.
  * All 13 suites pass; Evidence/Experience unchanged; wording/lineage/states/contexts unchanged.
  * Downstream requested-context enforcement remains deferred until a résumé/application consumer exists.
  * Claim Repository result-type sealing remains deferred (no downstream sealed consumer yet).
  * Status: **CLOSED**.
* Job Analysis v1 first vertical slice (**CLOSED**):

  * First bounded trustworthy job-content analysis slice only (`analyze_job`): structured extraction → requirement normalize/classify → Evidence/Claim match → gaps/unknowns → lane/decision.
  * Schemas: `evidence_match.schema.json`, `job_analysis_result.schema.json` (nested `$ref` + positive-match provenance).
  * AI boundary: requires `structured_extraction` (no paid model API; no fake free-form JD parser).
  * Synthetic BSA fixture under `fixtures/jobs/JOB_FIXTURE_BSA_001/`.
  * Implementation commit: `b1a7302`. Remediation commit: `69df92f`.
  * First Claude Code adversarial audit: changes required (semantic-overmatch, decision-routing, classification, schema).
  * Second Claude Code adversarial audit: `CLAUDE_JOB_ANALYSIS_V1_FINAL_PASS`.
  * Deferred hardening at closure (safe-direction):
    * **P-1** — was `UNCLEAR` for `"X preferred, but not required"` at slice closure; **bounded fix landed in Golden Set milestone**.
    * **P-2** — generic `"business process mapping"` fails conservatively to `NONE` until evidence/claim semantics are reviewed deliberately (Claims/Evidence unchanged).
  * Experience/Evidence/Claim repositories unchanged; no résumé generation begun.
  * Status: **CLOSED**.
* Job Analysis v1 Golden Set (**CLOSED**):

  * 15 synthetic Golden fixtures under `golden-tests/job_analysis/` with structured `expected.json` validated by `schemas/job_analysis_golden_case.schema.json`.
  * Runner: `golden-tests/run_job_analysis_golden_set.py`.
  * Families covered: Business Systems, Implementation, Data Operations, Business Process, Technical Operations, plus reject/trap families (SWE, ML, Marketing Analytics, Business Operations vague).
  * Semantic traps covered: U.S. regulatory NONE, UAT≠enterprise QA, Apps Script≠GCP, production ML, platform specialization, senior reject, generic lexical overlap / unrelated Analyst title, vague JD.
  * First Claude Golden audit: changes required (R-1–R-7). Gemini routing-policy review incorporated.
  * Remediation: clause-aware P-1; capability synonym recall; PRIORITY/APPLY/EFFICIENT/WATCH/REJECT calibration; info-deficit → WATCH; realistic fixture wording; golden schema tightening; workflow-automation precision.
  * Second Claude re-audit findings remediated: PRIORITY distinct-Claim breadth (anti requirement-splitting); expanded trusted synonym recall; Application Analyst / Application Support family tokens (Blueprint §6).
  * Final Claude residual findings remediated: N-1 synonym paraphrases (needs→requirements, structured/tabular ingest/load, validate pilot); N-2 plural `applications analyst`; N-3 Priority breadth assumption documented in code (no logic change).
  * **P-1 fixed** (clause-level; compound mixed clauses stay UNCLEAR).
  * **P-2 evidence model resolved**: `WW_PROC_001` + approved `CLAIM_WW_006` (`process_mapping`); Bora explicitly approved `CLAIM_WW_006` for reusable use (2026-08-28); matcher positive use enabled; `GT_PROCESS_MAP_P2` routes APPLY.
  * Claude P-2 audit remediation applied (`CLAUDE_P2_PROCESS_MAPPING_EVIDENCE_MODEL_CHANGES_REQUIRED`).
  * No résumé-generation work begun.
  * Status: **CLOSED**.

## Current Task

`P2_PROCESS_MAPPING_EVIDENCE_MODEL` = **P-2_EVIDENCE_MODEL_RESOLVED**.

Bora explicitly approved `CLAIM_WW_006` for reusable use. Six reusable Winter Walk claims. Awaiting explicit next approved task. Do not begin résumé generation unless explicitly approved.

## Not Built Yet

* Paid/model-backed requirement extraction provider
* Downstream requested-context enforcement at résumé/application consumption time
* Claim Repository result-type sealing (deferred; no sealed downstream consumer yet)
* Full OPT/immigration scoring inside job analysis
* Full long-term 20+ Golden Test expansion beyond the first 15-fixture set
* Additional Experience records / Evidence Batch 2+ / more Claim Bank records
* Broader forbidden-claim / general NLP truth engine (beyond bounded semantic guard)
* Production pipeline engine
* Resume patch generation / rendering / diff
* Networking research
* Google Workspace / external integrations
* Automated monitoring

## Current Safety State

* No production application automation exists.
* No external integrations are connected.
* No job applications can be submitted automatically.
* No resume-generation pipeline exists yet.
* Five Winter Walk Claim Bank records are Bora-approved and reusable under production claim validation.
* Winter Walk Batch 1 preserves UNKNOWN for daily production use, completed handoff, measured business impact, and live email sending unless separately evidenced.
* No runtime workflow depends on multi-model agreement; deterministic validators enforce invariants; evidence wins over model opinion; Bora retains consequential approval.
* No PII should be stored in this repository unless explicitly designed and approved later.
* No architectural dependency beyond the local repository has been approved.
* JSON Schema gates reject malformed structured records.
* Claim reusable-use requires schema + citation-scoped lineage + state compatibility + semantic boundary guard + human approval + non-UNKNOWN/non-CONTRADICTED state + no context conflict.
* Bounded deterministic semantic guard rejects known unsupported upgrades and fabricated quantified outcomes (`FORBIDDEN_SEMANTIC_PATTERN`).
* Semantic support requires positive (non-negated) Evidence context; unrelated bare numbers cannot authorize quantified outcomes.
* Claim repository identity integrity enforced (duplicate Claim_ID / filename mismatch fail closed).
* Downstream requested-context enforcement intentionally deferred until a résumé/application consumer exists.
* Provenance spine: Experience → Evidence → Claim (approved reusable) → (future) résumé module.
* `EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED` on authoritative Evidence Repository validation.
* Experience Registry does not assert employment titles, dates, outcomes, or résumé content.

## Current Source of Truth

`BLUEPRINT.md` (**Final Locked Blueprint v3.1**)

If another project file conflicts with the Blueprint, stop and surface the conflict.

## Immediate Next Steps

1. Await explicit approval for the next milestone (do not auto-start résumé generation).
2. Additional Experience/Evidence/Claims only when explicitly approved.

## Do Not Start Yet

Do not begin:

* résumé modules / resume generation;
* inventing additional Experience IDs without evidence/ADR need;
* Winter Walk Batch 2 without explicit approval;
* paid model provider wiring without approval;
* job scraping;
* Google Sheets / Gmail / LinkedIn automation;
* MCP / database / cloud infrastructure.

## Next Approved Task

None started. Awaiting Bora's explicit next approved task after P-2 resolution.
