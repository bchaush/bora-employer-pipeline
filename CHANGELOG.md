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
