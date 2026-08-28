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

## 2026-08-28 — Approve Winter Walk master module wordings (WORDING_APPROVED_PENDING_METADATA_RESOLUTION)

**Reason**

Bora explicitly approved exact wording for all six Winter Walk résumé modules. Replace prior candidate text, re-validate, and record approval without modifying Claims/Evidence/Experience records.

**Changed**

* `resume/master/RESUME_MASTER_WW_V1.json` version 1 → 2 with Bora-approved exact wordings.
* Master `notes`: `WORDING_APPROVED` event recorded for all six modules (2026-08-28).
* Contact, formal title, date range remain `PENDING_BORA_REVIEW`.
* Tests updated for exact wording + approval record assertions.
* Status → **WORDING_APPROVED_PENDING_METADATA_RESOLUTION** (not CLOSED).

**Affected Areas**

* `resume/master/RESUME_MASTER_WW_V1.json`
* `tests/master_resume_winter_walk_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* `tests/master_resume_winter_walk_test.py` — PASS
* 17/17 test suites — PASS
* Golden runner (15/15) — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — unchanged

**Status**

WORDING_APPROVED_PENDING_METADATA_RESOLUTION

---

## 2026-08-28 — Implement master résumé Winter Walk v1 (IMPLEMENTED_PENDING_HUMAN_REVIEW)

**Reason**

Create the first real evidence-controlled résumé module set for trusted Winter Walk experience (`EXP_WW_001`) and prove real content passes the closed résumé architecture. Not the complete master résumé.

**Changed**

* Protected master content: `resume/master/RESUME_MASTER_WW_V1.json`.
* Six candidate bullets, one per approved reusable Claim (`CLAIM_WW_001`–`CLAIM_WW_006`).
* Immutable header placeholders (`PENDING_BORA_REVIEW`) for contact, formal title, date range.
* Tests: `tests/master_resume_winter_walk_test.py`.
* Status → **IMPLEMENTED_PENDING_HUMAN_REVIEW** (not CLOSED).

**Affected Areas**

* `resume/master/RESUME_MASTER_WW_V1.json`
* `tests/master_resume_winter_walk_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* `tests/master_resume_winter_walk_test.py` — PASS
* 17/17 established + new test suites — PASS
* Golden runner (15/15) — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — unchanged

**Status**

IMPLEMENTED_PENDING_HUMAN_REVIEW

---

## 2026-08-28 — Close résumé architecture v1 (CLOSED)

**Reason**

Claude Code final independent adversarial re-audit returned `CLAUDE_RESUME_ARCHITECTURE_V1_AUDIT_PASS`. All originally blocking findings F1–F6 verified fixed. Operationally close `RESUME_ARCHITECTURE_V1` without redesign or new scope.

**Changed**

* Status → **CLOSED**.
* Recorded audit trail: implement `1fbfa88`; remediate `c6ce4d2`; final pass `CLAUDE_RESUME_ARCHITECTURE_V1_AUDIT_PASS`.
* Documented non-blocking **R1**: `validation_digest` is a stale/mutation-detection aid, not cryptographic tamper-proofing; export safety rests on full revalidation at approval.
* Documentation-only closure commit.

**Affected Areas**

* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* 16/16 established test suites — PASS
* Golden runner (15/15) — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — PASS
* No changes to `experiences/`, `evidence/`, or `claims/`

**Status**

CLOSED

---

## 2026-08-28 — Remediate résumé architecture v1 audit findings (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Independent Claude adversarial audit (`CLAUDE_RESUME_ARCHITECTURE_V1_AUDIT_FINDINGS`) identified blocking trust-boundary, terminology semantic, immutability, and classification defects. Narrow remediation only; no architecture redesign.

**Changed**

* **F1:** `approve_derivative_for_export` now requires master + trusted indexes + explicit `human_approval=true`, full eligibility re-validation, and `validation_digest` mutation detection.
* **F2:** `TERMINOLOGY_SUBSTITUTE` runs claim semantic-boundary + forbidden-context checks; benign substitutions gate to `NEEDS_SEMANTIC_REVIEW`; `complete_semantic_review` clears before export.
* **F3:** Extended immutable validation to education entries (by `education_id`) and `modules[].immutable_snapshot`.
* **F4:** `UNKNOWN_MODULE_ID` for missing `SELECT_WORDING_VARIANT` / `TERMINOLOGY_SUBSTITUTE` targets.
* **F5:** `DUPLICATE_MODULE_ID` validation on master modules.
* **F6:** Separated factual (`errors`) vs style (`style_warnings`) validation paths.
* Added `resume_semantic.py`, `resume_digest.py`; updated derivative schema (`validation_digest`, `NEEDS_SEMANTIC_REVIEW`).
* Adversarial regression tests in `tests/resume_architecture_test.py`.

**Affected Areas**

* `src/resume_validation.py`, `src/resume_patch_apply.py`, `src/resume_semantic.py`, `src/resume_digest.py`
* `schemas/resume_derivative.schema.json`
* `tests/resume_architecture_test.py`, `tests/resume_schema_smoke_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* `tests/resume_architecture_test.py` (A–L + F1–F5 adversarial) — PASS
* `tests/resume_schema_smoke_test.py` — PASS
* Full established suites + golden runner (15/15) — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — unchanged

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT (remediated; awaiting re-audit)

---

## 2026-08-28 — Implement résumé architecture v1 (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Establish the smallest evidence-first résumé-generation architecture (schemas, validators, patch/diff model, human review gate) without authoring Bora's master résumé or job-specific outputs.

**Changed**

* Added résumé schemas: `resume_module`, `resume_immutable_contact`, `resume_master`, `resume_patch`, `resume_derivative`.
* Added deterministic modules: `resume_lineage`, `resume_patch_apply`, `resume_diff`, `resume_style`, `resume_validation`.
* Synthetic claim-backed fixture: `fixtures/resume_architecture/synthetic_master.json`.
* Tests: `tests/resume_architecture_test.py` (A–L), `tests/resume_schema_smoke_test.py`.
* Status → **IMPLEMENTED_PENDING_EXTERNAL_AUDIT** (not CLOSED).

**Affected Areas**

* `schemas/resume_*.schema.json`
* `src/resume_*.py`
* `fixtures/resume_architecture/`
* `tests/resume_architecture_test.py`, `tests/resume_schema_smoke_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* `tests/resume_architecture_test.py` — PASS (A–L + human review gate)
* `tests/resume_schema_smoke_test.py` — PASS
* Full established suites (18) + golden runner (15/15) — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — unchanged

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT

---

## 2026-08-28 — Close P-2 process-mapping evidence model (CLOSED)

**Reason**

Claude Code final closure recheck returned `CLAUDE_P2_PROCESS_MAPPING_EVIDENCE_MODEL_FINAL_PASS`. Operationally close `P2_PROCESS_MAPPING_EVIDENCE_MODEL` without redesign, matcher changes, or résumé generation.

**Changed**

* Status → **CLOSED**.
* Recorded audit trail: implement `538fe16`; remediate `c9b3422`; approve `070dc9f`; wording fix `abf96d3`; reapprove `37fbba9`; Claude final pass `CLAUDE_P2_PROCESS_MAPPING_EVIDENCE_MODEL_FINAL_PASS`.
* `process_mapping` supported via `WW_PROC_001` → approved reusable `CLAIM_WW_006`.
* Evidence: 13. Reusable claims: 6. `GT_PROCESS_MAP_P2` = APPLY.
* Documentation-only closure commit.

**Affected Areas**

* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* Full established suites + golden runner (15/15) — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — PASS

**Status**

CLOSED

---

## 2026-08-28 — Reapprove corrected CLAIM_WW_006 (P-2_EVIDENCE_MODEL_RESOLVED)

**Reason**

Bora explicitly reapproved corrected `CLAIM_WW_006` for reusable use after evidence-bounded wording remediation (`data intake` removed).

**Changed**

* `CLAIM_WW_006`: `human_approval` false → true only (wording unchanged).
* Matcher positive `process_mapping` use enabled.
* `GT_PROCESS_MAP_P2`: REJECT/NONE → APPLY/STRONG with provenance.
* P-2 status: `P-2_EVIDENCE_MODEL_RESOLVED`.

**Affected Areas**

* `claims/winter_walk/CLAIM_WW_006.json`
* `golden-tests/job_analysis/GT_PROCESS_MAP_P2/expected.json`
* tests, golden runner, `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* Full established suites + golden runner — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — PASS

**Status**

P-2_EVIDENCE_MODEL_RESOLVED

---

## 2026-08-28 — Correct CLAIM_WW_006 evidence-bounded wording (P2_PROCESS_MAPPING_CLAIM_PENDING_REAPPROVAL)

**Reason**

Claude final P-2 closure recheck (`CLAUDE_P2_PROCESS_MAPPING_EVIDENCE_MODEL_CHANGES_REQUIRED`) found unsupported `data intake` in `CLAIM_WW_006` vs sole Evidence `WW_PROC_001`. Remove clause; reset approval; restore pending-approval Golden truth.

**Changed**

* `CLAIM_WW_006` wording: removed `data intake,` only; `human_approval` reset to false (prior approval invalidated).
* `WW_PROC_001` unchanged.
* Matcher logic unchanged; positive use blocked via reusable gate.
* `GT_PROCESS_MAP_P2`: APPLY → REJECT / `REQ_P2_MAP=NONE`.
* P-2 not CLOSED.

**Affected Areas**

* `claims/winter_walk/CLAIM_WW_006.json`
* `golden-tests/job_analysis/GT_PROCESS_MAP_P2/expected.json`
* tests, golden runner, `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* Full established suites + golden runner — PASS
* Repository: 1 Experience / 13 Evidence / 6 Claims (5 reusable) — PASS

**Status**

P2_PROCESS_MAPPING_CLAIM_PENDING_REAPPROVAL

---

## 2026-08-28 — Approve CLAIM_WW_006 for reusable use (P-2_EVIDENCE_MODEL_RESOLVED)

**Reason**

Bora explicitly approved `CLAIM_WW_006` for reusable use in a distinct approval step, following repository two-step claim convention after P-2 audit remediation.

**Changed**

* `CLAIM_WW_006`: `human_approval` false → true only.
* Matcher positive `process_mapping` use enabled via reusable claim gate.
* `GT_PROCESS_MAP_P2`: REJECT/NONE → APPLY/STRONG with provenance.
* P-2 status: `P-2_EVIDENCE_MODEL_RESOLVED`.
* Claim wording, lineage, contexts, and Evidence unchanged.

**Affected Areas**

* `claims/winter_walk/CLAIM_WW_006.json` (`human_approval`, `date`)
* `golden-tests/job_analysis/GT_PROCESS_MAP_P2/expected.json`
* tests, golden runner, `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* Full established suites + golden runner — PASS
* Repository: 1 Experience / 13 Evidence / 6 reusable Claims — PASS

**Status**

P-2_EVIDENCE_MODEL_RESOLVED

---

## 2026-08-28 — Remediate P-2 process-mapping audit P-1–P-4 (P2_PROCESS_MAPPING_CLAIM_PENDING_HUMAN_APPROVAL)

**Reason**

Claude Code audit returned `CLAUDE_P2_PROCESS_MAPPING_EVIDENCE_MODEL_CHANGES_REQUIRED`. Correct provenance, remove `workflow_analysis` overreach, restore two-step human-approval convention, and align Golden/matcher with pending-approval truth.

**Changed**

* `WW_PROC_001`: Master Blueprint Section 1 Executive Summary citation only; `process_mapping` only; removed connector/sync and unsupported terminology.
* `CLAIM_WW_006`: corrected wording; removed `workflow analysis`; `human_approval=false`.
* Matcher: `workflow_analysis` patterns removed; process-mapping vocabulary dormant until reusable approval; semantic traps expanded (BPMN 2.0, Lean, value stream mapping, process reengineering).
* `GT_PROCESS_MAP_P2`: restored REJECT / `REQ_P2_MAP=NONE`.
* Status: `P2_PROCESS_MAPPING_CLAIM_PENDING_HUMAN_APPROVAL` (not `P-2_EVIDENCE_MODEL_RESOLVED`).

**Affected Areas**

* `evidence/winter_walk/WW_PROC_001.json`, `claims/winter_walk/CLAIM_WW_006.json`
* `src/requirement_match.py`, golden fixture, tests, docs

**Tests / Verification**

* Full established suites + golden runner — PASS
* Repository: 1 Experience / 13 Evidence / 6 Claims (5 reusable) — PASS

**Status**

P2_PROCESS_MAPPING_CLAIM_PENDING_HUMAN_APPROVAL

---

## 2026-08-27 — Implement P-2 process-mapping evidence model (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Resolve `P-2_EVIDENCE_MODEL_DEFERRED` for canonical capability `process_mapping` via one new Winter Walk Evidence record and one new Claim, with minimum matcher/test updates. ChatGPT evidence audit + Gemini `P2_CLAIM_SUPPORTED_AS_WRITTEN` review. Evidence/claim model only — no résumé generation.

**Changed**

* Added `WW_PROC_001` (`process_mapping`, `workflow analysis`) citing `WinterWalk_Master_Blueprint.docx`.
* Added `CLAIM_WW_006` with bounded allowed/forbidden contexts; `human_approval=true` per Bora milestone authorization.
* Matcher: removed P-2 NONE trap; expanded bounded process/workflow mapping patterns; added BPMN / Lean-Six-Sigma / process-mining traps.
* `GT_PROCESS_MAP_P2` expected decision REJECT → APPLY (legitimate evidence-model change).
* P-2 status: `P-2_EVIDENCE_MODEL_RESOLVED` (pending external audit).
* Unrelated Batch 1 Evidence/Claims unchanged.

**Affected Areas**

* `evidence/winter_walk/WW_PROC_001.json`
* `claims/winter_walk/CLAIM_WW_006.json`
* `src/requirement_match.py`
* `golden-tests/job_analysis/GT_PROCESS_MAP_P2/expected.json`
* tests (repository counts, job analysis P2 adversarial, semantic guard)
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* Full established suites + golden runner — PASS
* Repository regression: 1 Experience / 13 Evidence / 6 reusable Claims — PASS

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT

---

## 2026-08-27 — Close Job Analysis v1 Golden Set (CLOSED)

**Reason**

Claude Code final closure recheck returned `CLAUDE_JOB_ANALYSIS_GOLDEN_SET_FINAL_PASS`. Operationally close `JOB_ANALYSIS_V1_GOLDEN_SET` without redesign, matching changes, Claim/Evidence mutation, P-2 resolution, or résumé generation.

**Changed**

* Status → **CLOSED**.
* Recorded audit trail: add `0dfd80b`; harden `e707ff6`; T-1/T-2/T-3 remediate `d10e2e4`; N-1/N-2 remediate `a496415`; Claude final pass `CLAUDE_JOB_ANALYSIS_GOLDEN_SET_FINAL_PASS`.
* **P-2** remains explicitly deferred as `P-2_EVIDENCE_MODEL_DEFERRED` (known next-milestone issue; not solved).
* Documentation-only closure; no matcher/decision/schema/code changes in this commit.

**Affected Areas**

* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* Full established suites + golden runner (15/15) — PASS
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS
* No Experience / Evidence / Claim JSON changes

**Status**

CLOSED

---

## 2026-08-27 — Remediate Golden Set residual N-1/N-2 (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Claude Code FINAL re-audit returned `CLAUDE_JOB_ANALYSIS_GOLDEN_SET_CHANGES_REQUIRED` for residual synonym recall (N-1) and plural Business Applications Analyst family naming (N-2). Apply smallest bounded remediation. Do not resolve P-2. Do not redesign Priority logic (N-3 documented only).

**Changed**

* N-1: bounded paraphrases for turn/capture needs→requirements, clarify workflow changes with users, ingest/load structured/tabular source files/data, validate-a-pilot UAT context; precision guards retained.
* N-2: `applications analyst` token (plural) for Business Applications Analyst; bare application/applications still unsupported.
* N-3: code comment only — distinct Claim IDs proxy capability breadth under current non-overlapping Claim Bank.
* P-2 remains `P-2_EVIDENCE_MODEL_DEFERRED`.
* Status remains **IMPLEMENTED_PENDING_EXTERNAL_AUDIT**.

**Affected Areas**

* `src/requirement_match.py`, `src/job_decision.py`
* `tests/job_analysis_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* All prior suites + golden runner — PASS
* New N-1/N-2 adversarial cases — PASS
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT (remediated; pending re-audit)

---

## 2026-08-27 — Remediate Golden Set T-1/T-2/T-3 (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Second Claude Code adversarial audit returned `CLAUDE_JOB_ANALYSIS_GOLDEN_SET_CHANGES_REQUIRED` for PRIORITY requirement-splitting gaming, synonym recall gaps, and missing Application Analyst family recognition. Apply smallest bounded remediation. Do not resolve P-2 via Claim/Evidence invention.

**Changed**

* T-1: PRIORITY_APPLY now requires ≥4 distinct HIGH-mandatory Claim provenance IDs (not raw requirement-row count); duplicate splits of one claim cannot game Priority.
* T-2: bounded synonym expansions for requirements/needs, data load/import/ingest/consolidate, acceptance-test cycles; precision guards retained.
* T-3: `application analyst` / `application support` added to supported role-family tokens (Blueprint §6); bare `application` not supported.
* P-2 remains `P-2_EVIDENCE_MODEL_DEFERRED` (Claims/Evidence unchanged).
* Status remains **IMPLEMENTED_PENDING_EXTERNAL_AUDIT**.

**Affected Areas**

* `src/job_decision.py`, `src/requirement_match.py`
* `tests/job_analysis_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* All prior suites + golden runner — PASS
* New T-1/T-2/T-3 adversarial cases — PASS
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT (remediated; pending re-audit)

---

## 2026-08-27 — Harden job analysis golden set (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Claude Code Golden Set adversarial audit required R-1–R-7 remediation. Incorporate approved ChatGPT + Gemini V1 routing-policy clarification without redesign, Claim/Evidence mutation, or résumé generation.

**Changed**

* R-1: clause-aware preferred-not-required classification; compound mixed clauses stay UNCLEAR; `not required`/`not mandatory` no longer false-fire as mandatory cues.
* R-2: bounded synonym recall for existing capabilities (requirements, ingestion/import, UAT/acceptance testing, fail-closed controls); explanations retain raw→canonical→provenance.
* R-3: PRIORITY/APPLY/EFFICIENT calibration using material (HIGH) preferred gaps vs trivial gaps; Priority uncommon.
* R-4: information-deficit → WATCH; confirmed mismatch → REJECT.
* R-5: rewritten realistic Golden fixture wording; narrowed expected decisions.
* R-6: golden schema `key_matches.minProperties`, `semantic_boundaries.minItems`, `acceptable_decisions.maxItems=2`.
* R-7: bare `workflow automation` no longer yields STRONG without operational/evidence/approval context.
* P-2 remains evidence-model deferred (vocabulary recognized; no Claim owns `process_mapping`; Claims/Evidence unchanged).
* Status remains **IMPLEMENTED_PENDING_EXTERNAL_AUDIT**.

**Affected Areas**

* `src/requirement_normalize.py`, `src/requirement_match.py`, `src/job_decision.py`
* `schemas/job_analysis_golden_case.schema.json`
* `golden-tests/job_analysis/**`, `golden-tests/run_job_analysis_golden_set.py`
* `scripts/generate_job_analysis_golden_fixtures.py`
* `tests/job_analysis_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Tests / Verification**

* All prior suites + `job_analysis_test.py` + golden runner — PASS
* Routing coverage: PRIORITY_APPLY, APPLY, EFFICIENT_APPLY, WATCH, REJECT all observed
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT (remediated; pending re-audit)

---

## 2026-08-27 — Add job analysis golden set (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Build the first representative Golden Test set for the closed job-analysis engine to validate generalization across Bora’s real target job universe before résumé generation depends on it.

**Changed**

* Added 15 synthetic Golden fixtures under `golden-tests/job_analysis/` with structured `expected.json`.
* Added `schemas/job_analysis_golden_case.schema.json` and runner `golden-tests/run_job_analysis_golden_set.py`.
* Added fixture generator `scripts/generate_job_analysis_golden_fixtures.py` (maintenance aid).
* Bounded P-1 hardening: `"preferred, but not required"` → `PREFERRED` without breaking mixed mandatory/preferred degree clauses.
* P-2 remains deferred and is explicitly exposed by `GT_PROCESS_MAP_P2` (Claims/Evidence unchanged).
* Experience / Evidence / Claim repositories unchanged; no résumé generation begun.
* Status: **IMPLEMENTED_PENDING_EXTERNAL_AUDIT** (not CLOSED; not pushed pending audit).

**Affected Areas**

* `golden-tests/`
* `schemas/job_analysis_golden_case.schema.json`
* `scripts/generate_job_analysis_golden_fixtures.py`
* `src/requirement_normalize.py` (P-1 only)
* `tests/job_analysis_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Risks / Tradeoffs**

* First Golden Set is 15 fixtures (not full long-term 20+ Blueprint expansion).
* P-2 continues to fail closed until deliberate Evidence/Claim review.
* Golden expectations encode Blueprint-aligned behavior, not arbitrary current drift.

**Tests / Verification**

* All prior suites + `job_analysis_test.py` — PASS
* `golden-tests/run_job_analysis_golden_set.py` — PASS (15/15)
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT

---

## 2026-08-27 — Close first job analysis vertical slice (CLOSED)

**Reason**

Claude Code second adversarial audit returned `CLAUDE_JOB_ANALYSIS_V1_FINAL_PASS`. Operationally close `JOB_ANALYSIS_V1_FIRST_VERTICAL_SLICE` without redesign, semantic changes, or résumé generation.

**Changed**

* Status → **CLOSED**.
* Recorded audit trail: implementation `b1a7302`; remediation `69df92f`; first Claude audit required changes; second Claude audit `CLAUDE_JOB_ANALYSIS_V1_FINAL_PASS`.
* Deferred hardening tracked (not fixed at closure):
  * **P-1** — `"X preferred, but not required"` → currently `UNCLEAR` (safe-direction accuracy limitation).
  * **P-2** — generic `"business process mapping"` → currently `NONE` until evidence/claim semantics reviewed deliberately.
* Milestone scope remains the first bounded trustworthy job-content analysis slice only.
* No Experience / Evidence / Claim JSON, wording, lineage, approvals, semantic guard, or Claim Repository implementation changes.
* No résumé generation begun.

**Affected Areas**

* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Tests / Verification**

* All established suites + `job_analysis_test.py` — PASS
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS
* Trust checks: `REQ_BSA_006=NONE`; Product Management cannot APPLY; MANDATORY+HIGH+NONE blocks apply; senior-title defense; positive-match provenance; nested schema validation — PASS
* `git diff --check` — clean

**Status**

CLOSED

---

## 2026-08-27 — Harden first job analysis slice (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

First Claude Code adversarial audit of `JOB_ANALYSIS_V1_FIRST_VERTICAL_SLICE` found semantic-overmatch, decision-routing, classification, and schema issues. Apply the smallest bounded remediation without redesign, résumé generation, or Claim/Evidence/Experience mutation.

**Changed**

* Regulatory false PARTIAL removed: Winter Walk software-control evidence no longer supports U.S. regulatory / SEC / SOX requirements; `REQ_BSA_006` → NONE with current repository.
* Matching hardened to capability-gated alignment; generic lexical overlap alone cannot produce STRONG/SUPPORTED/PARTIAL.
* Role-family gate enforced on PRIORITY_APPLY / APPLY / EFFICIENT_APPLY; unsupported families route WATCH/REJECT.
* Core mandatory HIGH + NONE generalized as hard blocker beyond Salesforce/GCP/ML keyword lists.
* Seniority defense-in-depth from role title + raw JD head (conservative `lead`).
* Classification: mixed mandatory/preferred clauses → UNCLEAR; HR/culture “must” noise → UNCLEAR; `ideal candidate` preferred cue.
* `job_analysis_result.schema.json` nested `$ref` to requirement + evidence_match schemas; local schema registry for `$ref` resolution.
* `evidence_match.schema.json` requires provenance for positive match results (Python check retained).
* BSA fixture REQ_BSA_002 wording aligned to supported workflow-automation / approval-sync claim capability (no process-mapping false positive).
* Adversarial tests expanded; Experience/Evidence/Claim JSON unchanged.
* Status remains **IMPLEMENTED_PENDING_EXTERNAL_AUDIT** (not CLOSED; awaiting second Claude re-audit).

**Affected Areas**

* `src/requirement_match.py`, `src/job_decision.py`, `src/requirement_normalize.py`, `src/job_analysis.py`, `src/schema_validation.py`
* `schemas/evidence_match.schema.json`, `schemas/job_analysis_result.schema.json`
* `fixtures/jobs/JOB_FIXTURE_BSA_001/`
* `tests/job_analysis_test.py`
* `CURRENT_STATE.md`, `CHANGELOG.md`

**Risks / Tradeoffs**

* V1 fails closed on ambiguous relevance (NONE/UNKNOWN preferred over overclaim).
* Capability tags are a small explicit set for Winter Walk + known traps — not a general ontology.
* Fixture REQ_BSA_002 adjusted so happy-path BSA still exercises supported capabilities after process-mapping trap.

**Tests / Verification**

* All prior suites + `job_analysis_test.py` (including remediation adversarial cases) — PASS
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT (remediated; pending re-audit)

---

## 2026-08-27 — Job Analysis v1 first vertical slice (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Build the smallest trustworthy first `analyze_job` pipeline: structured requirement extraction boundary, Evidence/Claim matching, gaps/unknowns, and inspectable lane/decision — without résumé generation or paid model APIs.

**Changed**

* Added `schemas/evidence_match.schema.json` and `schemas/job_analysis_result.schema.json`.
* Added `src/job_analysis.py`, `job_id.py`, `requirement_normalize.py`, `requirement_match.py`, `job_decision.py`.
* Added synthetic BSA fixture `fixtures/jobs/JOB_FIXTURE_BSA_001/`.
* Added `tests/job_analysis_test.py` covering fit, preferred gaps, Salesforce reject, senior reject, U.S. regulatory PARTIAL, UAT≠QA, Apps Script≠Google Cloud, production ML, UNCLEAR, missing Evidence, schema/duplicate failures.
* Experience / Evidence / Claim records unchanged.
* Status: **IMPLEMENTED_PENDING_EXTERNAL_AUDIT** (not CLOSED; not pushed pending audit).

**Affected Areas**

* `schemas/evidence_match.schema.json` (new)
* `schemas/job_analysis_result.schema.json` (new)
* `src/job_*.py`, `src/requirement_*.py` (new)
* `fixtures/jobs/JOB_FIXTURE_BSA_001/` (new)
* `tests/job_analysis_test.py` (new)
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Matching is bounded/deterministic lexical+trap logic over approved Claims/Evidence — not general NLP.
* Structured extraction must be supplied; live model extraction deferred.
* Full immigration/company scoring and résumé patch not in this slice.

**Tests / Verification**

* Prior 13 suites — PASS
* `job_analysis_test.py` — PASS
* Repository regression: 1 Experience / 12 Evidence / 5 reusable Claims — PASS

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT

---

## 2026-08-27 — Claim Bank v1 approval closure (CLOSED)

**Reason**

Bora explicitly approved the five existing Winter Walk Claim Bank records for reuse after Claude final pass (`CLAUDE_CLAIM_BANK_V1_FINAL_PASS`).

**Changed**

* `CLAIM_WW_001`–`CLAIM_WW_005`: `human_approval` false → true only.
* All five validate `valid_record=true` / `reusable=true`.
* Claim Repository remains valid (5 records).
* Semantic guard hardening previously passed final Claude adversarial recheck.
* All 13 suites pass.
* Evidence/Experience unchanged; no wording/lineage/state/context changes.
* Downstream requested-context enforcement remains deferred until a résumé/application consumer exists.
* Claim Repository result-type sealing remains deferred.
* Status: **CLOSED**.

**Affected Areas**

* `claims/winter_walk/CLAIM_WW_001.json` … `CLAIM_WW_005.json` (`human_approval` only)
* `tests/claim_semantic_guard_test.py` (real-claim regression expectations synced to approved/reusable)
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Reusable claims are available for future résumé modules; no résumé consumer exists yet.

**Tests / Verification**

* Production `validate_claim` on all five — reusable PASS
* Claim / Experience / Evidence repositories — PASS
* All 13 suites — PASS

**Status**

CLOSED

---

## 2026-08-27 — Claim Bank v1 final semantic hardening (IMPLEMENTED_PENDING_RECHECK)

**Reason**

Close Claude-identified semantic-guard blockers: negation/limitation leakage, unrelated-number outcome leakage, and trivial wording/formatting variant bypasses.

**Changed**

* Evidence phrase matches now require non-negated local context before counting as positive support.
* Quantified outcomes require number + matching outcome-category cues in Evidence (bare unrelated numbers fail).
* Normalization: lowercase, hyphen→space, whitespace collapse; expanded bounded equivalent forms for enterprise SaaS/architecture, production ML, enterprise QA families.
* Real five Winter Walk claims unchanged; still pending Bora approval.
* Claim Repository unchanged and remains valid.
* Status: **IMPLEMENTED_PENDING_RECHECK** (Claim Bank not CLOSED; not pushed).

**Affected Areas**

* `src/claim_semantic_guard.py`
* `tests/claim_semantic_guard_test.py`
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Guard remains bounded pattern-based, not general NLP.
* Prefer fail-closed overaccept of material overclaims; genuine positive Evidence can still authorize matching wording.

**Tests / Verification**

* All 13 established suites — PASS
* Negation six, unrelated-number, variant, original six, positive-support, real five regressions — PASS

**Status**

IMPLEMENTED_PENDING_RECHECK

---

## 2026-08-26 — Claim Bank v1 required hardening (IMPLEMENTED_PENDING_FINAL_AUDIT)

**Reason**

Close the production gap where schema/lineage/state-valid claims with `human_approval=true` could still reuse fabricated/forbidden wording, and add Claim Bank repository identity integrity.

**Changed**

* Added bounded deterministic semantic boundary guard (`src/claim_semantic_guard.py`); wired into unified `validate_claim`.
* Known unsupported upgrades and fabricated quantified outcomes now fail with `FORBIDDEN_SEMANTIC_PATTERN` (`valid_record=false`, therefore `reusable=false`); `human_approval=true` cannot rescue them.
* Guard is evidence-relative: phrases allowed only when cited Evidence support corpus supports them (not a global keyword blacklist).
* Added Claim repository integrity (`src/claim_repository.py`): unique Claim_ID, filename↔ID, schema, strict JSON (no duplicate keys / last-write-wins), fail-closed trusted index.
* Real five Winter Walk claims unchanged (wording, lineage, states, contexts, `human_approval=false`).
* Downstream requested-context consumption intentionally deferred until résumé/application consumer exists; allowed/forbidden self-conflict remains enforced.
* Status: **IMPLEMENTED_PENDING_FINAL_AUDIT** (Claim Bank not CLOSED; not pushed pending final audit).

**Affected Areas**

* `src/claim_semantic_guard.py` (new)
* `src/claim_repository.py` (new)
* `src/claim_validation.py`
* `tests/claim_semantic_guard_test.py` (new)
* `tests/claim_repository_test.py` (new)
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Semantic guard covers known high-risk patterns only; not general NLP truth verification.
* Requested-context enforcement at consumption time remains deferred.

**Tests / Verification**

* New semantic + claim repository suites — PASS
* Existing claim / Evidence / Experience / schema smoke suites — PASS
* Real repositories: 1 Experience, 12 Evidence, 5 Claims; real claims `valid_record=true` / `reusable=false`

**Status**

IMPLEMENTED_PENDING_FINAL_AUDIT

---

## 2026-08-26 — Claim Bank v1 first Winter Walk reusable claims (IMPLEMENTED_PENDING_EXTERNAL_AUDIT)

**Reason**

Create the smallest trustworthy first set of Winter Walk Claim Bank records using the existing claim schema/validators against the trusted Winter Walk Evidence Repository.

**Changed**

* Added 5 proposed claims under `claims/winter_walk/`: `CLAIM_WW_001`–`CLAIM_WW_005`.
* Capabilities covered: scope/requirements boundaries; fail-closed send controls; Drive CSV intake logging; form-to-evidence + approval sync; pilot/UAT documentation.
* Used existing claim schema + lineage + state + unified `validate_claim` (no new validators; no claim-repository integrity module yet).
* All claims: lineage and evidence-state compatible; `human_approval=false` → `valid_record=true`, `reusable=false` pending Bora approval.
* No Evidence/Experience/schema/claim-validator changes.
* Status: **IMPLEMENTED_PENDING_EXTERNAL_AUDIT** (not CLOSED; not pushed pending review/audit).

**Affected Areas**

* `claims/winter_walk/*.json` (new)
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Claim repository-level uniqueness/filename integrity is deferred (file-level uniqueness for these 5 IDs only).
* Semantic anti-equivalence is enforced by wording discipline + forbidden_contexts, not a separate forbidden-claim registry yet.
* Claims are not reusable until Bora sets `human_approval=true`.

**Tests / Verification**

* Claim suites (schema, lineage, state, unified) — PASS
* Per-claim `validate_claim` against trusted Evidence index — valid_record PASS; reusable false as designed
* Adversarial: missing Evidence_ID, UNKNOWN/CONTRADICTED/incompatible state, schema-invalid — fail closed

**Status**

IMPLEMENTED_PENDING_EXTERNAL_AUDIT

---

## 2026-08-26 — Minimal Experience Registry v1 CLOSED

**Reason**

Operationally close `MINIMAL_EXPERIENCE_REGISTRY_V1` after implementation (`0806a99`), trust-boundary hardening (`b9430b6`), and Claude Code final adversarial recheck (`CLAUDE_MINIMAL_EXPERIENCE_REGISTRY_FINAL_PASS`).

**Changed**

* Milestone status set to **CLOSED** in `CURRENT_STATE.md`.
* Documented locked trust boundary: validator-issued `ValidatedExperienceRepository` only; raw `experience_index=` bypass removed.
* Documented structure-only vs authoritative Evidence status separation (`EXPERIENCE_REFERENCE_NOT_CHECKED` vs `EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED`).
* Documented preserved causal failures (`EXPERIENCE_REGISTRY_INVALID` vs `EXPERIENCE_ID_NOT_FOUND`).
* Closure validation: all 11 suites PASS; real Experience count 1 (`EXP_WW_001`); real Evidence count 12 with referential integrity enforced.
* No claim-scoped semantic change; no Evidence JSON changes; no Experience record/schema changes in this closure commit.
* Ready as dependency for first reusable Claim Bank records (creation still requires explicit approval).

**Affected Areas**

* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Status**

CLOSED

---

## 2026-08-26 — Experience Registry trust-boundary hardening

**Reason**

Claude Code audit returned `MINIMAL_EXPERIENCE_REGISTRY_AUDIT_FAIL` with two blockers: arbitrary raw Experience-index injection, and structure-only Evidence validation falsely advertising `EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED`.

**Changed**

* `validate_experience_repository` now returns opaque `ValidatedExperienceRepository` (validator-issued only; public construction rejected).
* Removed public `experience_index=` bypass from Evidence validation; accept only `experience_result=` as validator-issued type, or load/validate Experience Registry via `experience_root=`.
* Structure-only Evidence path reports `EXPERIENCE_REFERENCE_NOT_CHECKED`.
* Authoritative failure reports `EXPERIENCE_REFERENCE_CHECK_FAILED` (never ENFORCED on failure).
* Tests: removed hand-built FIXTURE_EXPERIENCE_INDEX; structural vs authoritative paths made explicit; added trust-boundary adversarial suite.
* Milestone remains **IMPLEMENTED — PENDING CLAUDE CODE RECHECK** (not CLOSED).
* No claims; no claim-scoped semantic change; Experience schema/record and committed Evidence JSON unchanged.

**Affected Areas**

* `src/experience_repository.py`
* `src/evidence_repository.py`
* `tests/evidence_repository_test.py`
* `tests/evidence_experience_reference_test.py`
* `tests/experience_trust_boundary_test.py` (new)
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Status**

IMPLEMENTED — PENDING CLAUDE CODE RECHECK (not CLOSED; not pushed)

---

## 2026-08-26 — Minimal Experience Registry v1 (IMPLEMENTED — PENDING CLAUDE CODE AUDIT)

**Reason**

Resolve `EXPERIENCE_REGISTRY_DECISION_REQUIRED` with the smallest canonical Experience identity source and wire Evidence → Experience referential integrity before reusable claims.

**Changed**

* Added `schemas/experience.schema.json` (Draft 2020-12; `additionalProperties: false`).
* Added canonical `experiences/EXP_WW_001.json` (`ORGANIZATIONAL_ENGAGEMENT`; identity only).
* Added `src/experience_repository.py` (repository integrity parallel to Evidence).
* Updated `src/evidence_repository.py` so authoritative validation requires a trusted Experience index; missing IDs → `EXPERIENCE_ID_NOT_FOUND`; invalid registry → `EXPERIENCE_REGISTRY_INVALID`.
* Explicit structure-only path retained: `validate_evidence_repository_structure`.
* Status: `EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED` (implemented repository behavior).
* Milestone: **IMPLEMENTED — PENDING CLAUDE CODE AUDIT** (not CLOSED).
* No claims created; claim validators untouched (`NO_CLAIM_SCOPED_SEMANTIC_CHANGE`).
* No additional Experience IDs beyond `EXP_WW_001`.

**Affected Areas**

* `schemas/experience.schema.json`
* `experiences/EXP_WW_001.json`
* `src/experience_repository.py`
* `src/evidence_repository.py`
* `tests/experience_repository_test.py`
* `tests/evidence_experience_reference_test.py`
* `tests/evidence_repository_test.py`
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Small intentional duplication between experience and evidence repository validators (no mega-framework yet).
* Winter Walk classified as `ORGANIZATIONAL_ENGAGEMENT`, not employment or project subtype.

**Tests / Verification**

* Experience registry suite — PASS
* Evidence referential suite — PASS
* Evidence repository suite — PASS
* All 7 prior suites — PASS
* Real Experience count 1; real Evidence count 12; both trusted indexes produced

**Approved By**

Architecture approved by ChatGPT review; implementation by Cursor; pending Claude Code audit

**Status**

IMPLEMENTED — PENDING CLAUDE CODE AUDIT (not CLOSED; not pushed pending ChatGPT review)

---

## 2026-08-26 — Repository-Level Evidence Integrity v1 CLOSED

**Reason**

Close `REPOSITORY_LEVEL_EVIDENCE_INTEGRITY_V1` after Cursor implementation, required hardening, and independent Claude Code final recheck (`CLAUDE_EVIDENCE_INTEGRITY_FINAL_PASS`; no blockers; no remaining required hardening).

**Changed**

* Milestone status set to **CLOSED** in `CURRENT_STATE.md`.
* Implementation trail preserved: `674784b` (implementation), `09213b2` (hardening).
* Repository now deterministically enforces: recursive deterministic evidence JSON discovery; JSON parse integrity; duplicate JSON object-key rejection; canonical evidence-schema validation; global `Evidence_ID` uniqueness; filename stem ↔ `evidence_id` exact consistency; one canonical evidence record per JSON file; machine-readable error codes; fail-closed trusted index; missing-root failure; root-is-file failure; deliberate structurally-valid empty-root behavior.
* Current real Evidence Repository: 12 Winter Walk Batch 1 records; all pass; trusted index contains all 12.
* No reusable claims created; claim-scoped validation semantics unchanged (`NO_CLAIM_SCOPED_SEMANTIC_CHANGE`).
* `EXPERIENCE_REGISTRY_DECISION_REQUIRED` remains OPEN and is explicitly not part of this closed milestone.
* Next technical dependency recorded as `MINIMAL_EXPERIENCE_REGISTRY_V1` (not started; architecture not yet approved beyond the need for a canonical Experience reference source).

**Affected Areas**

* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Experience referential integrity remains deferred; evidence records may carry `experience_id` strings that are not yet registry-validated.

**Tests / Verification**

* `tests/evidence_repository_test.py` — PASS
* All 7 existing suites — PASS
* Real `evidence/` validation — valid; 12 records; trusted index length 12
* `git diff --check` — clean

**Approved By**

Claude Code final audit PASS; ChatGPT closure instruction

**Status**

CLOSED

---

## 2026-08-26 — Evidence Integrity v1 hardening (duplicate JSON keys + empty-root policy)

**Reason**

Claude Code audit returned `EVIDENCE_INTEGRITY_AUDIT_PASS_WITH_REQUIRED_HARDENING` with no blockers and exactly two required hardenings before closure.

**Changed**

* Reject duplicate JSON object keys during evidence load via `object_pairs_hook` (`EVIDENCE_JSON_DUPLICATE_KEY`; fail closed; no last-key-wins).
* Document and lock empty evidence-root policy: structurally valid with `records_checked=0` and `index={}`; non-empty sufficiency remains a separate caller/milestone concern.
* Tests: PASS 13 (duplicate non-identity key via raw JSON text); PASS 14 (empty TemporaryDirectory).
* Milestone remains **PENDING FINAL CLAUDE CODE RECHECK** (not CLOSED).
* `EXPERIENCE_REGISTRY_DECISION_REQUIRED` unchanged; no claims created; claim validators untouched.

**Affected Areas**

* `src/evidence_repository.py`
* `tests/evidence_repository_test.py`
* `CURRENT_STATE.md`
* `CHANGELOG.md`

**Risks / Tradeoffs**

* Duplicate-key detection applies to every JSON object in the file (including nested objects), which is the intended fail-closed integrity behavior.
* Empty-root structural validity must not be confused with application-level evidence sufficiency.

**Tests / Verification**

* `tests/evidence_repository_test.py` — PASS (including PASS 13–14)
* All 7 existing suites — PASS
* `git diff --check` — clean

**Approved By**

Hardening scope approved via Claude audit + ChatGPT implementation instruction; pending Claude recheck

**Status**

IMPLEMENTED — PENDING FINAL CLAUDE CODE RECHECK (not CLOSED; not pushed)

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
