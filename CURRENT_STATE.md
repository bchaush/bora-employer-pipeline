# Bora Employer Pipeline OS — Current State

Updated: 2026-08-28

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

P-2 process-mapping evidence model (`P2_PROCESS_MAPPING_EVIDENCE_MODEL`) = **CLOSED**.

Résumé Architecture v1 (`RESUME_ARCHITECTURE_V1`) = **CLOSED**.

Winter Walk Protected Metadata Evidence v1 (`WINTER_WALK_PROTECTED_METADATA_EVIDENCE_V1`) = **CLOSED**.

MarketMind Evidence Extraction v1 (`MARKETMIND_EVIDENCE_EXTRACTION_V1`) = **CLOSED**.

MarketMind Claim Drafting v1 (`MARKETMIND_CLAIM_DRAFTING_V1`) = **CLAIM WORDING APPROVED — RÉSUMÉ MODULES NOT YET APPROVED** (Bora explicitly approved the exact existing wording of `CLAIM_MM_001`–`CLAIM_MM_005`; see `CLAIM_MM_WORDING_APPROVAL_V1` below).

Claim Actor Attribution Policy v1 (`CLAIM_ACTOR_ATTRIBUTION_POLICY_V1`) = **CLOSED** (P-1 HIGH semantic-guard remediation independently re-verified; see `CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_REMEDIATION_V1` below).

Claim Actor Attribution Semantic Guard Action-Term Coverage v1 (`CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_ACTION_TERM_COVERAGE_V1`) = **CLOSED** (independent Claude re-audit passed; extended action-term vocabulary to integrate/automate/separate/document/define; pushed).

MarketMind Résumé Module Drafting v1 (`MARKETMIND_RESUME_MODULE_DRAFTING_V1`) = **IMPLEMENTED — PENDING HUMAN REVIEW** (5 draft bullet modules created from the 5 approved MarketMind Claims; see below).

MarketMind Résumé Module Wording Refinement v1 (`MARKETMIND_RESUME_MODULE_WORDING_REFINEMENT_V1`) = **IMPLEMENTED — PENDING HUMAN APPROVAL** (independent Cursor draft/architecture audit passed; Bora's wording review requested targeted refinements to 4 of the 5 draft wordings; see below).

Canonical Experience records: **2** (`EXP_WW_001`, `EXP_MM_001`).

Evidence records: **26** — 14 Winter Walk plus 12 MarketMind (`MM_SCOPE_001`–`MM_AUTHOR_001`; Bora-approved Evidence only).

Claim records: **11** total, all `human_approval=true` and `reusable=true` — 6 Winter Walk approved reusable claims (`CLAIM_WW_001`–`CLAIM_WW_006`) plus 5 MarketMind claims (`CLAIM_MM_001`–`CLAIM_MM_005`) whose exact existing wording Bora explicitly approved on 2026-08-28 (`CLAIM_MM_001`–`004` `evidence_state=VERIFIED`; `CLAIM_MM_005` `evidence_state=OBSERVED`, reusable per the existing, unmodified `REUSABLE_CLAIM_STATES` rule — the same rule that already made `CLAIM_WW_005` reusable). Approval covers only the exact stored wording, subject to cited substantive Evidence and existing Claim boundaries; it does not establish sole/exclusive/unaided authorship, production use, business outcomes, or an employment relationship. No MarketMind résumé module exists yet.

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
  * **P-2 fixed** via closed `P2_PROCESS_MAPPING_EVIDENCE_MODEL` milestone (`WW_PROC_001` → `CLAIM_WW_006`).
  * Claude final pass recorded (`CLAUDE_JOB_ANALYSIS_GOLDEN_SET_FINAL_PASS`).
  * No résumé-generation work begun.
  * Status: **CLOSED**.
* P-2 process-mapping evidence model (**CLOSED**):

  * `WW_PROC_001` (`process_mapping`) citing `WinterWalk_Master_Blueprint.docx` Section 1 Executive Summary.
  * `CLAIM_WW_006` with evidence-bounded wording; two-step human approval completed (implementation → wording remediation → Bora reapproval).
  * Matcher consumes approved `process_mapping` provenance; `GT_PROCESS_MAP_P2` routes APPLY.
  * Claude audits: remediation required (`CLAUDE_P2_PROCESS_MAPPING_EVIDENCE_MODEL_CHANGES_REQUIRED`); final closure `CLAUDE_P2_PROCESS_MAPPING_EVIDENCE_MODEL_FINAL_PASS`.
  * Evidence count: **13**. Reusable claims: **6** (`CLAIM_WW_001`–`CLAIM_WW_006`).
  * No résumé-generation work begun.
  * Status: **CLOSED**.
* Résumé Architecture v1 (`RESUME_ARCHITECTURE_V1`) (**CLOSED**):

  * Schemas: `resume_module`, `resume_immutable_contact`, `resume_master`, `resume_patch`, `resume_derivative`.
  * Deterministic validators: lineage (`resume_lineage`), patch apply + immutable guard (`resume_patch_apply`), diff (`resume_diff`), prose style (`resume_style`), semantic wording checks (`resume_semantic`), validation digest (`resume_digest`), unified gate (`resume_validation`).
  * Architecture guarantees now closed:
    * evidence/claim-backed résumé modules;
    * protected master model;
    * bounded derivative patching;
    * immutable-history enforcement (contact, experience, education, module snapshots);
    * end-to-end export approval revalidation (master + trusted indexes + explicit human approval);
    * semantic-review gating (`NEEDS_SEMANTIC_REVIEW` for terminology substitution);
    * style/provenance separation;
    * duplicate-module protection;
    * human approval before export.
  * Synthetic architecture fixture under `fixtures/resume_architecture/` (claim-backed; not Bora's résumé).
  * Tests A–L + adversarial remediations in `tests/resume_architecture_test.py`; schema smoke in `tests/resume_schema_smoke_test.py`.
  * Implementation commit `1fbfa88`; remediation commit `c6ce4d2`.
  * Claude audits: findings `CLAUDE_RESUME_ARCHITECTURE_V1_AUDIT_FINDINGS` (remediated); final pass `CLAUDE_RESUME_ARCHITECTURE_V1_AUDIT_PASS`.
  * **R1 (non-blocking):** `validation_digest` is a stale/mutation-detection aid for normal callers, not cryptographic tamper-proofing; export safety rests on full lineage, semantic, immutable, and schema revalidation at approval time.
  * No master résumé content, no job-specific résumé outputs, no rendering/export engine.
  * Experience/Evidence/Claim repository records unchanged.
  * Status: **CLOSED**.
* Master Résumé Winter Walk v1 (`MASTER_RESUME_WINTER_WALK_V1`) (**METADATA_RESOLVED_PENDING_EXPORT_PIPELINE**):

  * First real evidence-controlled résumé module set for `EXP_WW_001` only.
  * Protected master content: `resume/master/RESUME_MASTER_WW_V1.json` (version 5).
  * Six bullets (`MOD_WW_001_SCOPE` through `MOD_WW_006_PROCESS`), one per approved reusable Claim (`CLAIM_WW_001`–`CLAIM_WW_006`).
  * **Bora explicitly approved exact module wording on 2026-08-28** (recorded in master `notes` as `WORDING_APPROVED`; wording unchanged).
  * Partial metadata resolved via `WW_OFFER_001`: date range `Jun 2026 – Aug 2026`, employment category `INTERNSHIP`; exact end day unresolved (Aug 21 vs Aug 22).
  * Human-approved résumé display title `AI Researcher & Developer Intern` stored separately from source facts; `formal_title` remains `PENDING_BORA_REVIEW` (no source-verbatim formal title).
  * Source title facts preserved on master section: contractual position `Intern`; functional role `AI Researcher and Developer`.
  * **Bora-confirmed contact block resolved on 2026-08-28** (name, email, phone, location, LinkedIn stored in protected master contact; GitHub not in schema).
  * Display organization `Winter Walk`; legal organization `Winter Walk, Inc.` documented in Experience notes and Evidence.
  * No job-specific tailoring, no PDF/DOCX export pipeline, no other experiences ingested.
  * Tests: `tests/master_resume_winter_walk_test.py`, `tests/winter_walk_resume_title_resolution_test.py`, `tests/winter_walk_contact_resolution_test.py`.
  * Status: **METADATA_RESOLVED_PENDING_EXPORT_PIPELINE** (not CLOSED).
* Winter Walk Résumé Title Resolution v1 (`WINTER_WALK_RESUME_TITLE_RESOLUTION_V1`) (**CLOSED**):

  * Minimal architecture extension: `source_contractual_position`, `source_functional_role`, `display_title`, `display_title_approval` on experience sections; `display_title` on module immutable snapshots.
  * `formal_title` sentinel preserved; human-approved display label bound via `approved_display_title` approval metadata (`is_source_verbatim=false`).
  * Export gate accepts approved display title when source formal title unresolved.
  * Implementation commit `e3c83a1`; L-1 remediation commit `1ccad88` (module `immutable_snapshot.display_title` bound to section-approved `display_title` via `experience_id`).
  * Claude audit L-1 remediated; Claude final adversarial re-audit: `CLAUDE_WINTER_WALK_RESUME_TITLE_RESOLUTION_V1_FINAL_PASS` (no findings).
  * Experience/Evidence/Claims unchanged; six module wordings unchanged; display-title/source-title separation preserved.
  * Tests: `tests/winter_walk_resume_title_resolution_test.py`, `tests/resume_module_display_title_binding_test.py`.
  * **I-1 (non-blocking):** résumé protected-metadata export guard `immutable_snapshot` sentinel coverage for `degree_name`, `school_name`, `approved_metrics`, `approved_tools` remains a future note; not implemented in this milestone.
  * Status: **CLOSED**.

* Contact Block Resolution v1 (`CONTACT_BLOCK_RESOLUTION_V1`) (**CLOSED**):

  * Bora-confirmed protected contact facts stored in `RESUME_MASTER_WW_V1` contact block (version 5).
  * Protected-metadata export gate no longer blocked by unresolved `contact.name`; explicit `human_approval` still required for export.
  * `CONTACT_RESOLVED` in master `notes` is documentary only; validators do not use notes as approval oracle.
  * GitHub / first_name / last_name not added (not in contact schema).
  * Implementation commit `a6386b0`; Claude final adversarial audit: `CLAUDE_CONTACT_BLOCK_RESOLUTION_V1_FINAL_PASS` (no findings).
  * Experience/Evidence/Claims, six module wordings, and title metadata unchanged.
  * **I-1 (non-blocking):** future `immutable_snapshot` sentinel coverage documented; not implemented.
  * Tests: `tests/winter_walk_contact_resolution_test.py`; updates to related Winter Walk résumé tests.
  * Status: **CLOSED**.

## Current Task

`MASTER_RESUME_WINTER_WALK_V1` = **METADATA_RESOLVED_PENDING_EXPORT_PIPELINE**. Contact block closed; `formal_title` sentinel and exact end day remain unresolved. No résumé generation or job-specific tailoring started. Do not begin additional experience sections unless explicitly approved.
* Winter Walk Protected Metadata Evidence v1 (`WINTER_WALK_PROTECTED_METADATA_EVIDENCE_V1`) (**CLOSED**):

  * Documentary Evidence `WW_OFFER_001` ingested from signed unpaid internship offer letter (Bora-supplied; not stored in repository).
  * `EXP_WW_001` notes updated with legal org, internship category, contractual position, functional role, department, bounded dates.
  * Experience schema constraint: single `organization` field preserves display `Winter Walk`; legal name in notes/Evidence.
  * Trusted metadata state: legal/source organization `Winter Walk, Inc.`; display organization `Winter Walk`; unpaid internship documented; contractual position `Intern`; functional role `AI Researcher and Developer`; department `Development Department`; month-level résumé date `Jun 2026 – Aug 2026`; exact Aug 21 vs Aug 22 end day unresolved; protected `formal_title` unresolved; no synthetic composed title created.
  * Implementation commit `2ec0d6c`; M-1 export-gate remediation commit `b1e056d`.
  * Claude audit M-1 remediated: export approval rejects `PENDING_BORA_REVIEW` unresolved protected metadata (`UNRESOLVED_PROTECTED_METADATA`).
  * Claude final adversarial re-audit: `CLAUDE_WINTER_WALK_PROTECTED_METADATA_EVIDENCE_V1_FINAL_PASS` (M-1 independently verified fixed).
  * **I-1 (non-blocking):** résumé protected-metadata export guard currently checks the immutable_snapshot fields used by the active Winter Walk master, but future modules that populate `degree_name`, `school_name`, `approved_metrics`, or `approved_tools` must extend sentinel validation before relying on those fields for export. Current Winter Walk master does not populate the affected fields. Not a closure blocker; not implemented in this milestone.
  * No Claim records created or modified; no accomplishment Claims for metadata.
  * Tests: `tests/winter_walk_protected_metadata_evidence_test.py`, `tests/resume_export_protected_metadata_test.py`.
  * Status: **CLOSED**.

## Current Task

`MASTER_RESUME_WINTER_WALK_V1` = **METADATA_RESOLVED_PENDING_EXPORT_PIPELINE**. Module wording, offer-letter metadata, display title, and contact block resolved; `formal_title` sentinel and exact end day remain unresolved. Do not begin job-specific tailoring or additional experience sections unless explicitly approved.

## Not Built Yet

* Paid/model-backed requirement extraction provider
* Downstream requested-context enforcement at résumé/application consumption time
* Claim Repository result-type sealing (deferred; no sealed downstream consumer yet)
* Full OPT/immigration scoring inside job analysis
* Full long-term 20+ Golden Test expansion beyond the first 15-fixture set
* Additional Experience records / Evidence Batch 2+ / more Claim Bank records
* Broader forbidden-claim / general NLP truth engine (beyond bounded semantic guard)
* Production pipeline engine
* Résumé protected-metadata export guard I-1: extend `immutable_snapshot` sentinel validation for `degree_name`, `school_name`, `approved_metrics`, `approved_tools` before future education-bearing/tool-bearing modules rely on those fields (non-blocking; current Winter Walk master unaffected)
* Networking research
* Google Workspace / external integrations
* Automated monitoring

## Current Safety State

* No production application automation exists.
* No external integrations are connected.
* No job applications can be submitted automatically.
* Résumé architecture v1 closed; Winter Walk candidate master modules exist under `resume/master/`; no export pipeline yet.
* Six Winter Walk Claim Bank records are Bora-approved and reusable under production claim validation.
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
* Provenance spine: Experience → Evidence → Claim (approved reusable) → résumé module (architecture) → controlled patch → validation → human review → (future) export.
* `EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED` on authoritative Evidence Repository validation.
* Experience Registry does not assert employment titles, dates, outcomes, or résumé content.

## Current Source of Truth

`BLUEPRINT.md` (**Final Locked Blueprint v3.1**)

If another project file conflicts with the Blueprint, stop and surface the conflict.

## Immediate Next Steps

1. Bora explicitly approved the exact existing wording of `CLAIM_MM_001`–`CLAIM_MM_005` on 2026-08-28. All 11 Claims are now `human_approval=true` / reusable.
2. Five MarketMind résumé-module bullet drafts created in `resume/drafts/MARKETMIND_RESUME_MODULE_DRAFTS_V1.json` on 2026-08-28. Independent Cursor audit passed (`CURSOR_MARKETMIND_RESUME_MODULE_DRAFTING_FINAL_PASS`, no architecture remediation required). Bora's own wording review then requested targeted refinements to 4 of the 5 draft wordings (module 3 kept exactly as-is); refined wording applied 2026-08-28. Modules still await Bora's separate, explicit exact-wording approval before any is included in the protected master, a derivative, or an exported résumé.
3. No further semantic-guard or validator changes pending; `CLAIM_ACTOR_ATTRIBUTION_POLICY_V1` and its `CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_ACTION_TERM_COVERAGE_V1` follow-up are both closed and pushed.

## Do Not Start Yet

Do not merge the MarketMind draft modules into `resume/master/RESUME_MASTER_WW_V1.json`, generate résumé output, ingest Market Empire/LoanIQ, or begin job-specific tailoring without explicit approval. Claim wording approval is not résumé-module approval; résumé-module drafting/refinement is not résumé-module approval either.

## Next Approved Task

None started. `MARKETMIND_RESUME_MODULE_WORDING_REFINEMENT_V1` refined the wording of 4 of the 5 draft bullet modules per Bora's review; all five still pending explicit approval; no résumé module or job-specific tailoring work has begun.

---

## 2026-08-28 — MarketMind résumé-module wording refinement (`MARKETMIND_RESUME_MODULE_WORDING_REFINEMENT_V1`, IMPLEMENTED — PENDING HUMAN APPROVAL)

**Reason**

Independent Cursor re-audit of `MARKETMIND_RESUME_MODULE_DRAFTING_V1` returned `CURSOR_MARKETMIND_RESUME_MODULE_DRAFTING_FINAL_PASS` — no architecture remediation required. Bora's own human wording review then requested targeted refinements to the exact wording of the five draft modules, rather than approving the initial drafts as-is.

**Changed**

* `resume/drafts/MARKETMIND_RESUME_MODULE_DRAFTS_V1.json`: refined `wording` on `MOD_MM_001_SCOPE`, `MOD_MM_002_DETERMINISTIC_AI`, `MOD_MM_004_CONTROLS`, and `MOD_MM_005_TESTING`. `MOD_MM_003_INTEGRATION`'s wording was reviewed and kept exactly as-is. No module_id, Claim lineage, Evidence lineage, `allowed_role_families`, `capabilities`, `status` (`OPTIONAL`), or `human_approval` (`false`) changed on any module; container-level `status=DRAFT_PENDING_HUMAN_REVIEW`/`human_approval=false` unchanged.

**Not changed**

* Claims, Evidence, Experiences, Winter Walk Claims/modules, `resume/master/RESUME_MASTER_WW_V1.json`, schemas, requirement matcher, résumé validators. `EXP_MM_001` remains absent from the protected master.

**Verification**

* All 5 refined wordings independently re-validated via the real `validate_resume_module_lineage`, `validate_module_wording_semantics`, and `validate_resume_prose_style` functions — clean.
* No new proposition introduced beyond each wording's approved Claim; `CLAIM_MM_005`'s testing module remains free of pass-count, all-tests-pass, coverage-percentage, or production-reliability language.
* 26/26 test suites — PASS (no test hardcodes exact draft wording, so none required updating). Golden 15/15 — PASS. Repository: 2 Experience / 26 Evidence / 11 Claims / 11 reusable — unchanged.
* Drafts remain structurally outside the protected master; `human_approval=false` remains draft metadata only, not an enforced production security gate (the real safety boundary is structural absence from the master/export pipeline, as established in `MARKETMIND_RESUME_MODULE_DRAFTING_V1`).

**Status**

`MARKETMIND_RESUME_MODULE_WORDING_REFINEMENT_V1_IMPLEMENTED_PENDING_HUMAN_APPROVAL`. Not pushed. No module approved, no résumé generated, no job-specific tailoring begun.

---

## 2026-08-28 — MarketMind résumé-module drafting (`MARKETMIND_RESUME_MODULE_DRAFTING_V1`, IMPLEMENTED — PENDING HUMAN REVIEW)

**Reason**

Create résumé-module drafts from the five already-approved MarketMind Claims (`CLAIM_MM_001`–`CLAIM_MM_005`), consistent with the existing Winter Walk résumé-module architecture, without approving résumé wording, generating a résumé, or tailoring to a job.

**Created**

* `resume/drafts/MARKETMIND_RESUME_MODULE_DRAFTS_V1.json`: a draft container (`status=DRAFT_PENDING_HUMAN_REVIEW`, `human_approval=false`) holding 5 `resume_module`-shaped bullet drafts, one per approved MarketMind Claim:
  * `MOD_MM_001_SCOPE` ← `CLAIM_MM_001`
  * `MOD_MM_002_DETERMINISTIC_AI` ← `CLAIM_MM_002`
  * `MOD_MM_003_INTEGRATION` ← `CLAIM_MM_003`
  * `MOD_MM_004_CONTROLS` ← `CLAIM_MM_004`
  * `MOD_MM_005_TESTING` ← `CLAIM_MM_005`
* Each module: `claim_ids` cites exactly one approved MarketMind Claim, `evidence_ids` exactly matches that Claim's own cited Evidence, `status=OPTIONAL` (never `ACTIVE`), and a module-level `human_approval=false`.
* `tests/marketmind_resume_module_drafting_test.py`: proves each module's lineage, semantic-boundary, and prose-style validity via the real `validate_resume_module_lineage`/`validate_module_wording_semantics`/`validate_resume_prose_style` functions; scans for forbidden inflation language; confirms structural absence from the protected master; confirms byte-integrity of Winter Walk Claims, MarketMind Claims, and the master.

**Design decision — drafts kept out of the protected master**

The draft file is deliberately **not** merged into `resume/master/RESUME_MASTER_WW_V1.json` and is not referenced by any `experience_sections`/`bullet_module_ids` there. `resume_module.schema.json` has no module-level approval concept, so a flag alone inside the master would not be enforced by any existing validator (`build_resume_derivative`/`approve_derivative_for_export` would treat it identically to an approved module). Keeping the drafts in a separate, unreferenced file makes them structurally unreachable by the derivative/export pipeline today, which is a stronger guarantee than an unenforced status field would provide. Merging any of these modules into the master requires a future, separately-scoped milestone after Bora reviews and approves the exact wording.

**Not changed**

* Claims (`claims/marketmind/`, `claims/winter_walk/`), Evidence, Experiences, `resume/master/RESUME_MASTER_WW_V1.json`, schemas, requirement matcher, résumé validators.

**Verification**

* All 5 modules independently pass `validate_resume_module_lineage` (cite only approved, human-approved MarketMind Claims and their exact Evidence lineage), `validate_module_wording_semantics` (no forbidden-context leakage against each Claim's `forbidden_contexts`), and `validate_resume_prose_style` (no em dashes, no AI-filler phrasing).
* Explicit scan against the task's named forbidden phrases (production-grade, enterprise, predictive, AI-powered, autonomous, circuit breaker, sole developer, without AI assistance, 187 passing tests, customer/user/revenue/savings, etc.) — clean.
* `CLAIM_MM_005` module (OBSERVED) does not assert a pass count or "all tests passed."
* 26/26 test suites — PASS. Golden 15/15 — PASS. Repository: 2 Experience / 26 Evidence / 11 Claims / 11 reusable — unchanged.

**Status**

`MARKETMIND_RESUME_MODULE_DRAFTING_V1_IMPLEMENTED_PENDING_HUMAN_REVIEW`. Not pushed. No résumé module is approved. No résumé has been generated. No job-specific tailoring has begun.

---

## 2026-08-28 — Claim Actor Attribution Semantic Guard Action-Term Coverage v1 closure (CLOSED)

**Reason**

Independent Claude final re-audit of commit `f777c6a` (extended `_ATTRIBUTION_ACTION_TERM` to cover integrate/automate/separate/document/define) passed: fresh reproduction of "Single-handedly integrated...", "Solely automated...", and "Exclusively separated..." against valid Evidence and `human_approval=true` returns `valid_record=false`, `reusable=false`; plain "Integrated..."/"Automated..." wording remains valid and reusable. Zero drift confirmed on Winter Walk Claims/Evidence/Experiences/résumé master, and on the MarketMind Claims beyond the intended `human_approval` field, across the full `ecc0e22`–`f777c6a` chain.

**Verified unchanged across the full chain**

* All 6 Winter Walk Claims and all 26 Evidence records: byte-unchanged.
* All 5 MarketMind Claims: `human_approval=true`, `valid_record=true`, `reusable=true`; wording/lineage/`evidence_state` unchanged; `CLAIM_MM_005` still `OBSERVED`.

**Status**

`CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_ACTION_TERM_COVERAGE_V1` — **CLOSED**. `MARKETMIND_CLAIM_DRAFTING_V1` remains open pending résumé-module creation, which requires separate, explicit approval.

---

## 2026-08-28 — Claim Actor Attribution Semantic Guard Action-Term Coverage v1 (IMPLEMENTED — PENDING INDEPENDENT REAUDIT)

**Reason**

An adversarial probe run during the MarketMind approval-recording milestone found that `_ATTRIBUTION_ACTION_TERM` (the shared verb vocabulary added in the P-1 remediation) omitted "integrate," "automate," "separate," "document," and "define" — several of the ADR's own named conventional attribution verbs. `"Single-handedly integrated Google Places and Census ACS."` passed semantic validation with `human_approval=true`, an otherwise-valid substantive citation, and zero errors — the same class of gap the P-1 remediation closed for "built/implemented/architected/etc.," just not yet extended to these five additional verbs.

**Changed**

* `src/claim_semantic_guard.py`: extended `_ATTRIBUTION_ACTION_TERM` to add `integrat(?:e|ed|ing)`, `automat(?:e|ed|ing)`, `separat(?:e|ed|ing)`, `document(?:ed|ing)?`, `defin(?:e|ed|ing)`, alongside the existing verbs (built/build/develop/create/implement/architect/design/author). No new rule categories, no new error codes, no MarketMind-specific logic — the existing `sole_exclusive_unaided_authorship_overreach` rules simply now recognize these additional conventional verbs.
* `tests/claim_actor_attribution_policy_test.py`: added Section 6 — 5 new forbidden cases ("Single-handedly integrated...", "Solely automated...", "Exclusively separated...", "Documented the entire system alone.", "Single-handedly defined...") and 5 new safe cases (plain "Integrated...", "Automated...", "Separated...", "Documented...", "Defined..." wording), all run through the real `validate_claim()` with `human_approval=true`.

**Not changed**

* Claim/Evidence/Experience schemas; `claim_lineage.py`; `claim_state_validation.py`; `requirement_match.py`; all five MarketMind Claim files (wording, lineage, `evidence_state`, `human_approval=true`); all six Winter Walk Claims; Evidence; Experiences; protected résumé master; résumé modules.

**Verification**

* All 5 new forbidden cases blocked (`valid_record=false`, `reusable=false`, `FORBIDDEN_SEMANTIC_PATTERN`, category `sole_exclusive_unaided_authorship_overreach`).
* All 4 representative previously-covered forbidden cases ("Solely built...", "Exclusively implemented...", "...without AI assistance", "...with no collaborators") still blocked — no regression.
* All 7 required safe cases (plain "Integrated"/"Automated"/"Separated"/"Documented"/"Defined" wording, plus "Independently verified..." and "...independently of the LLM narrative layer") remain valid and reusable.
* All 11 real Claims re-verified unaffected: 6 Winter Walk and 5 MarketMind all `valid_record=true`/`reusable=true`; MarketMind wording/lineage/`evidence_state` byte-unchanged; `CLAIM_MM_005` still `OBSERVED` (not upgraded).
* 25/25 test suites — PASS. Golden 15/15 — PASS. Repository: 2 Experience / 26 Evidence / 11 Claims / 11 reusable — unchanged.

**Limitations**

Bounded deterministic pattern coverage for explicit sole/exclusive/unaided-authorship overreach combined with a wider (but still finite) set of conventional attribution verbs — not exhaustive natural-language authorship detection. A verb or phrasing outside this bounded vocabulary is not guaranteed to be caught.

**Status**

`CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_ACTION_TERM_COVERAGE_V1_IMPLEMENTED_PENDING_INDEPENDENT_REAUDIT`. Not pushed.

---

## 2026-08-28 — MarketMind Claim wording approval (`CLAIM_MM_WORDING_APPROVAL_V1`)

**Reason**

Bora explicitly reviewed and approved the exact existing wording of `CLAIM_MM_001` through `CLAIM_MM_005`, subject to their cited substantive Evidence and existing Claim boundaries (`allowed_contexts`/`forbidden_contexts`).

**Recorded**

* `human_approval: false → true` on all five MarketMind Claim files. No other field changed on any of them (wording, `evidence_ids`, `evidence_state`, `allowed_contexts`, `forbidden_contexts`, `date`, `version` all byte-unchanged).
* Approval means only that it is truthful for Bora to describe himself using the exact stored conventional actor-attribution wording. It does **not** establish sole authorship, exclusive implementation, absence of AI assistance, absence of collaborators, authorship of every line, production use, enterprise scale, business outcomes, users/adoption, or an employment relationship.
* `CLAIM_MM_001`–`004`: `evidence_state=VERIFIED`, `valid_record=true`, `reusable=true`.
* `CLAIM_MM_005`: `evidence_state=OBSERVED`, `valid_record=true`, `reusable=true` — reusable per the existing, unmodified `REUSABLE_CLAIM_STATES = {VERIFIED, SUPPORTED, OBSERVED}` rule (the same rule already governing the reusable `CLAIM_WW_005`, also `OBSERVED`). No validator logic was changed to produce this result; it is the pre-existing architecture's own determination.
* Reusable Claim count: **6 → 11** (all 11 Claims now reusable). This is a legitimate, validator-determined consequence of approval, not a hardcoded assumption.

**Test/golden updates (legitimate, not weakening)**

Several regression tests and the golden runner asserted the *prior* truth ("MarketMind claims remain unapproved," "reusable count = 6") as part of the now-closed drafting/policy milestones. Updated the specific outdated assertions in `tests/claim_actor_attribution_policy_test.py`, `tests/job_analysis_test.py`, `tests/marketmind_claim_drafting_test.py`, `tests/marketmind_evidence_extraction_test.py`, `tests/winter_walk_contact_resolution_test.py`, and `golden-tests/run_job_analysis_golden_set.py` to reflect the new, correct state (`human_approval=true`, reusable count 11). All lineage/state/schema/semantic-guard/byte-integrity assertions in these files were preserved unchanged.

**Verified unchanged**

* All five MarketMind Claim wording strings, `evidence_ids`, `evidence_state` — byte-identical to the closed drafting milestone.
* All 14 Winter Walk Evidence, all 12 MarketMind Evidence, both Experience records, all 6 Winter Walk Claims, the protected résumé master — byte-unchanged.
* No résumé module created. No schema changed. No requirement-matcher change.

**Semantic-guard finding — since remediated**

Adversarial re-testing during this milestone found a narrow gap: `_ATTRIBUTION_ACTION_TERM` (added in the P-1 remediation) omitted "integrate," "automate," "separate," "document," and "define" — several of the ADR's own named conventional verbs, one of which ("Integrated") is the literal first word of `CLAIM_MM_003`'s real, approved wording. This was fixed the same day in `CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_ACTION_TERM_COVERAGE_V1` (see entry below) before push — see that entry for the closed status. It never affected the actual approved wording of any of the five claims (none contain a forbidden qualifier).

---

## 2026-08-28 — Claim Actor Attribution Policy v1 closure (CLOSED)

**Reason**

Independent Claude final re-audit of `CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_REMEDIATION_V1` (commit `3902b86`) confirmed the P-1 HIGH finding is remediated: fresh reproduction of the exact bypass wording against `human_approval=true` and otherwise-valid Evidence/state now returns `valid_record=false`, `reusable=false`, `FORBIDDEN_SEMANTIC_PATTERN`. All 8 required forbidden cases and 6 required safe cases independently re-verified. Zero drift confirmed across the full `2baffc6`–`3902b86` chain on Winter Walk Claims/Evidence, MarketMind Evidence/Experience, and the protected résumé master. 25/25 tests, Golden 15/15, repository counts unchanged (2 Experience / 26 Evidence / 11 Claims / 6 reusable).

**Verified unchanged across the full chain**

* All 6 Winter Walk Claims: byte-unchanged, `valid_record=true`, `reusable=true`, `human_approval=true`.
* All 5 MarketMind Claims: wording/state/lineage unchanged, `valid_record=true`, `reusable=false`, `human_approval=false`.
* Evidence, Experiences, protected résumé master: byte-unchanged.

**Status**

`CLAIM_ACTOR_ATTRIBUTION_POLICY_V1` — **CLOSED**. `MARKETMIND_CLAIM_DRAFTING_V1` remains `IMPLEMENTED — PENDING HUMAN REVIEW`; no MarketMind Claim is approved or reusable. No résumé module or résumé output exists for MarketMind.

---

## 2026-08-28 — Claim Actor Attribution Semantic Guard Remediation v1 (IMPLEMENTED — PENDING CLAUDE REAUDIT)

**Reason**

Claude's `CLAIM_ACTOR_ATTRIBUTION_POLICY_V1` re-audit identified `P-1 — HIGH`: the semantic guard (`src/claim_semantic_guard.py`) had no rule enforcing the ADR's "Limits of Attribution." A synthetic Claim with valid substantive lineage, `evidence_state=VERIFIED`, and `human_approval=true`, worded to assert sole/exclusive/unaided authorship, passed with `valid_record=true`, `reusable=true`, zero errors — `human_approval` could bypass the ADR's explicit sole/exclusive/no-AI-assistance/no-collaborator limits.

**Changed**

* `src/claim_semantic_guard.py`: added an unconditional (Evidence-independent) rule set, `_ACTOR_ATTRIBUTION_OVERREACH_RULES` (category `sole_exclusive_unaided_authorship_overreach`), covering sole-authorship, single-handed, exclusive-authorship, "alone", no-AI-assistance, and no-collaborator wording. Unlike the existing evidence-relative `_BOUNDARY_RULES`, these patterns block regardless of cited Evidence content or `human_approval`, since no Evidence record in this architecture can license those propositions. Wired into `validate_claim_semantic_boundaries()`, which is already called by `validate_claim()` — no other validator touched.
* `tests/claim_actor_attribution_policy_test.py`: added 8 required forbidden-wording adversarial cases (including Claude's exact reproduction) and 6 required safe-wording non-match cases, all exercised through the real `validate_claim()` with `human_approval=true`.

**Not changed**

* Claim schema, Evidence schema, Experience schema, `claim_lineage.py`, `claim_state_validation.py`, `requirement_match.py`, all five MarketMind Claim files (wording/state/lineage/`human_approval`), all six Winter Walk Claims, Evidence, Experiences, protected résumé master, résumé modules.

**Verification**

* Human-approval bypass reproduced and blocked: valid Evidence + valid state + `human_approval=true` + forbidden wording → `valid_record=false`, `reusable=false`, `FORBIDDEN_SEMANTIC_PATTERN`.
* All 8 required forbidden cases (including the exact Claude regression) blocked; all 6 required safe cases pass.
* Adversarial self-check variants (`solely implemented`, `sole architect`, `single handedly built`, `singlehandedly built`, `built everything alone`, `without AI assistance`, `no artificial intelligence assistance`, `exclusive implementation`, etc.) all caught; safe variants (`Independently verified...`, `Implemented ... independently of the LLM layer`) all pass.
* All 11 real Claims re-validated: 6 Winter Walk remain `valid_record=true`/`reusable=true`/`human_approval=true`; 5 MarketMind remain `valid_record=true`/`reusable=false`/`human_approval=false`, wording/state/lineage byte-unchanged.
* 25/25 test suites pass; Golden 15/15; counts unchanged (Experience=2, Evidence=26, Claims=11, reusable=6).

**Limitations**

Bounded deterministic pattern coverage for obvious sole/exclusive/unaided-authorship overreach, not exhaustive natural-language authorship detection — consistent with the existing semantic guard's own documented scope.

**Status**

`CLAIM_ACTOR_ATTRIBUTION_SEMANTIC_GUARD_REMEDIATION_V1_IMPLEMENTED_PENDING_CLAUDE_REAUDIT`. `CLAIM_ACTOR_ATTRIBUTION_POLICY_V1` remains not fully closed until this reaudit passes.

---

## 2026-08-28 — Claim Actor Attribution Policy v1 (IMPLEMENTED — PENDING CLAUDE REAUDIT)

**Reason**

Claude remediation re-audit returned `ARCHITECTURE_DECISION_REQUIRED`: mixing `MM_AUTHOR_001` into substantive `evidence_ids` conflated authorship metadata with work facts and forced VERIFIED Claims to OBSERVED. Formalize the policy Winter Walk already follows in practice.

**Changed**

* `docs/decisions/ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md` — authoritative policy.
* `claims/marketmind/CLAIM_MM_001`–`CLAIM_MM_005`: removed `MM_AUTHOR_001` from substantive `evidence_ids`; restored `evidence_state` (`VERIFIED` on 001–004; `OBSERVED` on 005).
* `BLUEPRINT.md`, `AGENTS.md`, `.cursor/rules/truth.mdc` — minimal references.
* `tests/claim_actor_attribution_policy_test.py`; updated `tests/marketmind_claim_drafting_test.py`.

**Not changed**

* Claim wording, `human_approval=false`, reusability, `MM_AUTHOR_001` Evidence record, MarketMind Evidence otherwise, Experiences, Winter Walk Claims, master, validators, schemas.

**Status**

`CLAIM_ACTOR_ATTRIBUTION_POLICY_V1_IMPLEMENTED_PENDING_CLAUDE_REAUDIT`

---

## 2026-08-28 — MarketMind Claim Drafting v1 authorship-lineage remediation (SUPERSEDED)

**Reason**

Claude `CLAUDE_MARKETMIND_CLAIM_DRAFTING_V1_FINAL_PASS` required binding `MM_AUTHOR_001` to all five MarketMind draft claims for actor-attribution lineage.

**Changed**

* Added `MM_AUTHOR_001` to `evidence_ids` on `CLAIM_MM_001`–`CLAIM_MM_005` (wording unchanged).
* Adjusted `evidence_state` to `OBSERVED` on `CLAIM_MM_001`–`CLAIM_MM_004` for state-compatibility with cited `MM_AUTHOR_001` (`OBSERVED`).
* Updated `tests/marketmind_claim_drafting_test.py` authorship-lineage checks.

**Not changed**

* Claim wording, `human_approval=false`, reusability, Evidence, Experiences, Winter Walk, master.

**Status**

`MARKETMIND_CLAIM_DRAFTING_V1_REMEDIATED_PENDING_CLAUDE_REAUDIT` (superseded by `CLAIM_ACTOR_ATTRIBUTION_POLICY_V1`)

---

## 2026-08-28 — MarketMind Claim Drafting v1 (IMPLEMENTED — PENDING HUMAN REVIEW)

**Reason**

Draft the smallest useful set of reusable-claim candidates from Bora-approved MarketMind Evidence only.

**Changed**

* Added 5 MarketMind claim candidates under `claims/marketmind/` (`CLAIM_MM_001`–`CLAIM_MM_005`).
* Added `tests/marketmind_claim_drafting_test.py`.
* Updated claim-count regression checks (11 total claims; 6 reusable).

**Not changed**

* No Claim human approval; all MarketMind claims `human_approval=false`.
* No résumé modules, patches, or master changes.
* MarketMind Evidence, Experiences, Winter Walk Claims unchanged.

**Verification**

* 24/24 test suites — PASS
* Golden runner (15/15) — PASS
* Reusable Claims remain **6** (Winter Walk only)

**Status**

`MARKETMIND_CLAIM_DRAFTING_V1_IMPLEMENTED_PENDING_HUMAN_REVIEW`

---

## 2026-08-28 — MarketMind Evidence Extraction v1 (**CLOSED**)

**Reason**

Claude final adversarial audit `CLAUDE_MARKETMIND_EVIDENCE_EXTRACTION_V1_FINAL_PASS` independently verified MarketMind evidence extraction. Bora explicitly approved all 12 MarketMind Evidence records. Operational closure of evidence-extraction milestone.

**Implementation**

* Commit `0ff4885` — `feat: ingest MarketMind primary evidence`.
* `experiences/EXP_MM_001.json` (`PERSONAL_PROJECT`; identity only).
* 12 MarketMind Evidence records under `evidence/marketmind/` (`MM_SCOPE_001`–`MM_AUTHOR_001`).

**Human approval (Evidence only)**

Bora approval statement (2026-08-28):

> I approve the 12 MarketMind Evidence records MM_SCOPE_001 through MM_AUTHOR_001 as accurate, bounded factual evidence for this project. This approval does not approve any résumé wording or reusable Claim.

Approval scope: **Evidence records only**. No reusable MarketMind Claims approved. No résumé modules, bullets, or job-specific wording approved.

**Claude verdict**

`CLAUDE_MARKETMIND_EVIDENCE_EXTRACTION_V1_FINAL_PASS` — no blocking findings.

**Preserved boundaries**

* `MM_TEST_001` retains dated single-run observation (35 modules; 187 collected; 186 passed / 1 failed on 2026-08-28). Later external re-run `187/187 PASS` acknowledged as later verification only; does not rewrite `MM_TEST_001`.
* `MM_DEPLOY_001` remains dated liveness observation, not production deployment.
* `MM_AUTHOR_001` remains GitHub contributor observation only.
* No employer/client/sponsor/dates/business outcomes invented.
* **I-1 (non-blocking):** résumé protected-metadata `immutable_snapshot` sentinel coverage remains future work; not implemented.

**Not changed at closure**

* No code, Evidence, Claim, Experience, or résumé content changes.
* Winter Walk Experience/Evidence/Claims unchanged.
* Protected résumé master unchanged.
* External MarketMind project unchanged.

**Verification**

* 23/23 test suites — PASS
* Golden runner (15/15) — PASS
* Repository: 2 Experience / 26 Evidence / 6 reusable Claims

**Status**

`MARKETMIND_EVIDENCE_EXTRACTION_V1` = **CLOSED**

---

## 2026-08-28 — MarketMind Evidence Extraction v1 (IMPLEMENTED — PENDING HUMAN REVIEW)

**Reason**

Ingest MarketMind AI as an evidence-controlled project using only facts supported by verified primary artifacts from the marketmind-ai repository.

**Changed**

* Added canonical `experiences/EXP_MM_001.json` (`PERSONAL_PROJECT`; identity only).
* Added 12 MarketMind Evidence records under `evidence/marketmind/` (`MM_SCOPE_001`–`MM_AUTHOR_001`).
* Added `tests/marketmind_evidence_extraction_test.py`.
* Updated repository regression counts in related integrity tests.

**Not changed**

* No Claims, résumé modules, résumé patches, or protected master content.
* Winter Walk Experience/Evidence/Claims unchanged.
* Schemas unchanged.

**Verification**

* 23/23 test suites — PASS
* Golden runner (15/15) — PASS
* Repository after ingestion: 2 Experience / 26 Evidence / 6 reusable Claims.

**Status**

`MARKETMIND_EVIDENCE_EXTRACTION_V1_IMPLEMENTED_PENDING_HUMAN_REVIEW` (superseded by closure entry above)

