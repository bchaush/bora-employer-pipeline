# Career OS System Eval-Set Architecture V1

Status: **COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY**
`implementation_authorized`: **false**. Phase F and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**.

This report is a READ_ONLY / DESIGN_ONLY analytical rendering over already-adjudicated Phase C/Phase D evidence (`docs/audits/CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1_REPORT.md`, `docs/audits/CAREER_OS_FAILURE_TAXONOMY_AND_EVALUATOR_COVERAGE_MAP_V1_REPORT.md`). It defines a repeatable **system-level eval-set architecture** — a case schema and case corpus — over that evidence. It invents no new evidence, no evaluator code, no `CAREER_OS_RUN_TRACE_V1` schema, no phase contract/typed envelope, no trace infrastructure, no database/UI, no model router, no LLM judge, and no new runtime agent. It authorizes no implementation and no later roadmap phase. Operator completion of this report is explicitly **not** Bora acceptance; those are separate, sequential events.

This revision applies a semantic correction identified by ChatGPT architectural adjudication of the original operator draft: it adds an explicit `case_role` taxonomy distinguishing confirmed-failure regressions from important workflows and positive-continuity references (the Hamel Husain / Shreya Shankar Stage-3 repeatable-eval-set distinction), adds a deterministic pass/fail pairing rule, normalizes every case row to a single, non-compound `current_executability` token, splits a previously combined two-identity row, corrects two cases that had understated the gap between a passing step diagnostic and unproven terminal coverage, adds an explicit non-executable human-handoff reference class, replaces a generic recency-suppression identity with the durable motivating example, and adds an explicit Family-6 non-admission note. No case's underlying evidence, provenance, or executability substance is invented or upgraded by this correction; only labeling, splitting, and normalization are performed.

## 0. Epistemic rules governing this report

Unchanged from Phase C/D and reused here without modification:

- Every material claim is labeled with one of: **OBSERVED**, **RECONSTRUCTED_FROM_DURABLE_EVIDENCE**, **EXPERIMENTAL_NON_CANONICAL**, or **MISSING**. No `UNKNOWN`/`MISSING` evidence state is upgraded, and no case is presented as executable where the underlying raw artifact is `MISSING`.
- **Severity/consequence-class vocabulary** (S3/S2/S1) is reused unchanged from Phase D; it remains a consequence class only, never a frequency/probability/incidence claim.
- This eval-set architecture is **provisional and non-saturated** — it is a repeatable case *schema* applied to the genuine corpus Phase C/D already inventoried, not a claim of completeness over every possible Career OS operating case.
- No numeric reliability, pass-rate, or production-incidence claim is made anywhere in this report.

## 1. Why a separate eval-set architecture is needed (not just the Phase D map)

Phase D answered "what fails, how severely, and is it covered." Phase D deliberately did not answer "what would a repeatable regression case for that failure actually look like, and can it run today." That second question is this report's sole subject. Per the governing ADR (`docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md`, Section 4, Phase E), the eval set must:

1. separate **end-to-end terminal-state correctness** from **step-level diagnostics**;
2. ground every case in confirmed provenance, never invented evidence;
3. distinguish cases that can actually be *executed now* from cases that are merely *designed* against reconstructed evidence, or are outright *blocked* by a missing artifact class;
4. keep objective lexical/structural/identity/state-transition checks deterministic-first, reserving any future calibrated LLM judge strictly for genuinely subjective residual quality after objective checks and human calibration;
5. keep CI regression evals conceptually distinct from live production monitoring/incidence, per the Hamel Husain / Shreya Shankar reference frame Phase D already adopted (`CAREER_OS_ADAPTATION`);
6. distinguish, per case, whether it names a **confirmed historical failure** admitted to this repeatable regression corpus because it is an important known failure case (this admission alone never implies the case is currently executable, runtime-covered, or protected by a current regression — current protection is determined separately by `current_executability`, `evaluator_type_owner`, and `diagnostic_layer`, per Section 7), an **important recurring workflow** that has not itself failed, or a **positive continuity/handoff reference** — a repeatable eval set is not only a failure corpus (Section 3a).

## 2. Terminal-state correctness vs. step-level diagnostics

**`TERMINAL_END_TO_END`** — did the *whole operating case* land on the correct final outcome for Bora (e.g. a role correctly suppressed as non-actionable before package time; a package correctly withheld until the recheck passes; a duplicate correctly never resurfacing; a controller run correctly reaching a SAFE, non-corrupting terminal state). This is the outcome Bora actually experiences.

**`STEP_LEVEL_DIAGNOSTIC`** — did one *intermediate* deterministic gate, function, or invariant fire correctly in isolation (e.g. `apply_posting_state_routing()` correctly refuses to preserve APPLY-like routing when the dual axis is unmet; `evaluate_resume_page_utilization()` correctly floors at 92% given real geometry input).

**The critical invariant this architecture enforces, verbatim from the milestone goal:** *a system case can fail terminally even when every step diagnostic it has available passes.* Concrete, evidence-grounded illustration (Family 1, Phase D §2): `posting_state_decision_wiring_v1_test.py` proves the two-axis routing gate fires correctly once `role_status`/`source_verification_status` are set (a passing `STEP_LEVEL_DIAGNOSTIC`) — but Phase D already found no automated evaluator that itself re-fetches the live posting and mechanically re-derives those two axis values (`EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY` for the full transition). A case whose axis-setting step is silently wrong (e.g. a human/ChatGPT session misjudges a dead page as `VERIFIED_LIVE`) can still pass the routing-gate diagnostic perfectly while the **terminal, end-to-end** outcome — "did Bora get correctly steered away from a dead posting" — fails. No eval-set architecture that only ran step diagnostics could ever surface that failure; a system-level case must independently assert the terminal outcome.

Every case row below therefore carries its own explicit `diagnostic_layer` field, and a case is never permitted to claim `TERMINAL_END_TO_END` coverage merely because its `STEP_LEVEL_DIAGNOSTIC` components pass. `current_executability` always records the terminal-outcome case classification, never a narrower step-level substitute for it. Where a case's only proven executable artifact is a step diagnostic, that fact is recorded solely in the optional `available_step_diagnostics` field (Section 3); it is never used to change or inflate `current_executability` itself, which continues to describe the unproven terminal path exactly as it stands, with no step-level fixture presented in its place.

## 3. Case-row schema (the repeatable unit of this eval set)

Every case in the corpus (Section 5) records exactly these fields; no case may omit one:

| Field | Meaning |
|---|---|
| `case_id` | Stable, human-readable identifier. |
| `family` | Exactly one of: Phase D's six failure families (Section 1 there — `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`, `PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE`, `CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE`, `PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE`, `APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE`, `SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE`); `POSITIVE_CONTINUITY` for a clean-success/handoff case that does not correspond to a failure family; or `CROSS_CUTTING_RECENCY_SUPPRESSION`, admitted as an explicit eighth allowed value because REC-A is contract-required cross-cutting recency coverage that does not belong to any single Phase D family. No other family token is permitted. |
| `case_role` | Exactly one of `CONFIRMED_FAILURE_REGRESSION` (a real, durably confirmed/reconstructed historical failure admitted to the repeatable regression corpus because it is an important known failure case; the role alone does **not** imply the terminal claim is currently executable, runtime-covered, or protected by a current regression — current protection/coverage is determined separately by `current_executability` + `evaluator_type_owner` + `diagnostic_layer`, and only an `EXECUTABLE_NOW` `CONFIRMED_FAILURE_REGRESSION` case with matching coverage can claim a reproduced defect stays fixed today, per Section 7), `IMPORTANT_WORKFLOW` (a real, recurring operating workflow or doctrine-locked rule this corpus must repeatably exercise, with no confirmed failure event of its own preserved), or `POSITIVE_CONTINUITY_REFERENCE` (an observed clean success/handoff, never a failure). This is the Hamel Husain / Shreya Shankar Stage-3 distinction that a repeatable eval set is important workflows *plus* confirmed failures, not failures alone; a doctrine-only workflow candidate is never relabeled `CONFIRMED_FAILURE_REGRESSION` absent a durably preserved failure event. |
| `provenance_quality` | `OBSERVED` \| `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` \| `MISSING` (no case in this corpus is `EXPERIMENTAL_NON_CANONICAL`; see Section 4). |
| `operating_case_identity` | The exact real-world employer/requisition/run/artifact this case names — never a generic placeholder, and never two distinct identities combined into one row (Section 4 requires a separate row per distinct durable-evidence identity). |
| `expected_terminal_outcome` | The single correct end-to-end outcome Bora should experience, stated as a terminal-state assertion, not a step description. |
| `diagnostic_layer` | Begins with exactly one allowed enum token — `TERMINAL_END_TO_END` \| `STEP_LEVEL_DIAGNOSTIC` \| `BOTH` — never a compound/non-enum value combining two tokens in the leading position. A case that asserts both a step diagnostic and a separately-distinct terminal outcome (per Section 2) uses `BOTH` and states the two assertions as prose after the token, not as two leading tokens. |
| `evaluator_type_owner` | Reused unchanged from Phase D's coverage vocabulary: `RUNTIME_CONSEQUENTIAL_EVALUATOR`, `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION`, `HUMAN_SEMANTIC_ADJUDICATION`, `POTENTIAL_CALIBRATED_LLM_JUDGE`, `UNCOVERED_CONSEQUENTIAL_SURFACE`, or `EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY`, plus the concrete owning artifact (file/doctrine section) where one exists. |
| `current_executability` | Exactly **one** of `EXECUTABLE_NOW` \| `RECONSTRUCTION_BACKED_DESIGN_CASE` \| `BLOCKED_CANDIDATE` \| `HUMAN_CONFIRMED_REFERENCE` (Section 4). This field is never a slash/compound value; where a case has both an executable step diagnostic and a non-executable terminal claim, `current_executability` states the terminal-outcome class and the optional `available_step_diagnostics` field (below) separately records the step-level fact. |
| `blocking_evidence_gap` | The exact missing artifact class, if any, that prevents `EXECUTABLE_NOW`/`HUMAN_CONFIRMED_REFERENCE` status; `NONE` if not applicable. |
| `available_step_diagnostics` | *(optional)* Present only when a case's `current_executability` describes an unproven/non-executable terminal outcome while a narrower step-level diagnostic for the same case genuinely does run today. States that step diagnostic's own executability class and owning test file; never used to imply the terminal outcome is thereby covered. |

## 3a. Deterministic pass/fail pairing rule for admitted objective evaluators

Any objective/code-based evaluator admitted to a future repeatable executable set must have both a **PASS** example and a **FAIL** example for every condition/important edge case it claims to check — a deterministic evaluator with only one side proven is not yet a repeatable eval, only half of one. This report does not invent an operating case to fill a missing side. Where an already-existing test file provides a durable PASS/FAIL pair for a case's step-level diagnostic, that pairing is cited directly (never a newly authored fixture). Where a case names an objective condition but no runtime evaluator exists for either side, or only one side is provable, this corpus records that gap explicitly as a **missing counterpart requirement** rather than inventing a synthetic operating case to close it.

Pairing status for the cases in Section 5 that name an objective/code-based evaluator:

- **F1-A** (dual-axis routing gate, `tests/posting_state_decision_wiring_v1_test.py`): PASS/FAIL pair present — PASS A (both axes verified: APPLY-like routing preserved) vs. PASS B/K1 family (either or both axes unmet: routing downgraded to WATCH). Both sides are real, already-existing assertions; no new fixture is authored here.
- **F2-A** (page-utilization floor, `tests/resume_page_utilization_v1_test.py`): PASS/FAIL pair present — PASS 1 (93.4% utilization passes) vs. PASS 2 "ATOMINVEST REGRESSION" (50.5% utilization fails `RESUME_PAGE_UNDERUTILIZED`), plus the exact-threshold PASS 5 / just-below FAIL pair (PASS 6). Both sides are real, already-existing assertions.
- **REC-A** (recency band doctrine text, `tests/discovery_recency_hard_cutoff_v1_test.py`): PASS/FAIL pair present at the doctrine-text level — 21-day `FAR_STRETCH_WINDOW` survival (PASS) vs. 22-day `SUPPRESSED_WINDOW` suppression (FAIL/suppress), both already-existing doctrine-text assertions. No runtime PASS/FAIL pair exists for the actual live-suppression act (Section 5.5); that is recorded as a missing counterpart, not fabricated.
- **F1-C, F2-B, F2-C, F5-B**: no runtime evaluator of any kind exists for either side of the named objective condition (excluded-host routing; package-spawn-time gate; banned-vocabulary lexical scan; duplicate-suppression check). **Missing counterpart requirement recorded**: both a PASS (correct suppression/refusal) and a FAIL (incorrect pass-through) runtime fixture would be required before any of these could be admitted as `EXECUTABLE_NOW`; none is invented here, and each remains `BLOCKED_CANDIDATE` in Section 5.

## 4. Executability classes (never conflated)

- **`EXECUTABLE_NOW`** — a real, currently-tracked, currently-runnable repository eval/diagnostic already exists for this case (the case can be run as `python tests/<file>` right now). This class covers both kinds of real, currently-runnable check this corpus admits: a `RUNTIME_CONSEQUENTIAL_EVALUATOR` exercising real `src/` production-path behavior, or a `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` exercising a real doctrine/contract/ledger-integrity check. `EXECUTABLE_NOW` is never itself narrowed to mean production-path `src/` behavior only, and `evaluator_type_owner` — not `current_executability` — is the authoritative classifier of which of those two coverage boundaries applies. **`EXECUTABLE_NOW` alone never implies runtime-consequential coverage, and never implies terminal end-to-end coverage** (Section 2); a case's `evaluator_type_owner` and `diagnostic_layer` fields, not its `current_executability` value, determine what kind of coverage it actually is. This is the only class that may be described as an existing regression fixture.
- **`RECONSTRUCTION_BACKED_DESIGN_CASE`** — the operating event is real (per Phase C's `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` label) and durable secondary evidence (merged-PR body, `CHANGELOG.md`/`CURRENT_STATE.md` narrative, milestone contract) is sufficient to *design* a future fixture's inputs/expected-outcome faithfully, but the raw trace, package artifact, or live page state needed to execute it as a fixture today is `MISSING` (gitignored `.career-os/` run artifacts, gitignored local PDF/DOCX packages, or a now-changed/removed live posting). This class is a design target for a future fixture; building it is not a Phase F step. Per the governing ADR (`docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md`), Phase F is trace/contract architecture and Phase G is assurance architecture — neither builds fixtures or runtime implementation. Any fixture or runtime implementation for a `RECONSTRUCTION_BACKED_DESIGN_CASE` belongs no earlier than a separately authorized Phase H bounded implementation milestone, itself subject to future authorization and not authorized by this report. This report designs none of Phase F, Phase G, or Phase H; it only identifies which cases would need such a fixture, should Phase H ever be separately authorized.
- **`BLOCKED_CANDIDATE`** — the case cannot be admitted as `EXECUTABLE_NOW` or `RECONSTRUCTION_BACKED_DESIGN_CASE` for either of two distinct reasons, both of which resolve to this same class: (a) the case names a genuine consequential surface Phase D already identified as `UNCOVERED_CONSEQUENTIAL_SURFACE` (e.g. runtime dedupe suppression, runtime recency-cutoff enforcement, package-time jargon-lexicon scanning) where **no runtime implementation exists at all** to test — the case cannot even be design-drafted against real code today, only against doctrine text; or (b) a runtime mechanism may exist elsewhere in the same failure mode, but the durable evidence surviving for *this specific case* is too incomplete to specify a faithful fixture's inputs and expected outcome (e.g. the exact page content needed to characterize the defect could not be re-established from any durable record reviewed, unlike a merely gitignored-but-reconstructable artifact). In either case the case cannot be design-drafted against real code or against faithfully reconstructed inputs today. Building a missing runtime mechanism (class (a)) is out of scope for this READ_ONLY/DESIGN_ONLY phase and is not authorized here; class (b) cases remain blocked regardless of future implementation because the founding evidence itself does not survive, not because a mechanism is missing.
- **`HUMAN_CONFIRMED_REFERENCE`** — the operating case's terminal outcome is a genuinely successful, durably confirmed event, but the terminal act itself is a human act (e.g. Bora's own submission click), not machine-executable in any form. This class is never a coverage gap and is never described as `EXECUTABLE_NOW`; only the *surrounding* ledger-integrity/schema check, if any, may separately be `EXECUTABLE_NOW` (recorded via `available_step_diagnostics`). This class exists so that a successful human handoff is neither miscast as an automated fixture nor treated as a failure.

Cases with a missing raw trace or missing package artifact are never described as `EXECUTABLE_NOW` fixtures in this corpus — each such case is explicitly `RECONSTRUCTION_BACKED_DESIGN_CASE`, `BLOCKED_CANDIDATE`, or `HUMAN_CONFIRMED_REFERENCE`, matching the acceptance condition this report is bound by. `current_executability` is always exactly one of these four tokens — never a slash/compound value; where two distinct facts are true of one case (a working step diagnostic alongside an unproven terminal path), the step-level fact moves to `available_step_diagnostics` instead of being combined into `current_executability`.

## 5. Case corpus

Cases are grouped by Phase D failure family, plus one positive-continuity group. Every case reuses only evidence and file names already named in Phase C/D or independently confirmed to exist in this repository during this design pass; no new evidence is invented. Each distinct durable-evidence operating identity is its own row — no case combines two distinct employer/requisition identities into a single row.

### 5.1 Family 1 — `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE` (negative cases)

**Case `F1-A` — MGB RQ4075857 pre-surfacing actionability gap**
- `case_id`: `F1-A`
- `family`: `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (PR #14; `CURRENT_STATE.md` 2026-09-07 catch-up entry; `tests/posting_state_decision_wiring_v1_test.py` case 3).
- `operating_case_identity`: Mass General Brigham, requisition RQ4075857.
- `expected_terminal_outcome`: a role with `role_status=LIKELY_LIVE` and unresolved/absent `source_verification_status=VERIFIED_DIRECT` must never surface as an APPLY-like recommendation to Bora.
- `diagnostic_layer`: `BOTH` — the step diagnostic (dual-axis gate) and the terminal outcome (no false-APPLY surface) are conceptually distinct assertions of this case, per Section 2's invariant.
- `evaluator_type_owner`: `RUNTIME_CONSEQUENTIAL_EVALUATOR` for the dual-axis gate itself — `apply_posting_state_routing()` (`src/job_decision.py`), exercised by `tests/posting_state_decision_wiring_v1_test.py`; `EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY` for the full live-fetch/transition boundary (Phase D §2, reaffirmed unchanged).
- `current_executability`: `RECONSTRUCTION_BACKED_DESIGN_CASE` — this reflects the case's **terminal** claim only. Phase D §2 explicitly found no automated evaluator that itself re-fetches the live posting and mechanically re-derives `role_status`/`source_verification_status`; `posting_state_decision_wiring_v1_test.py` is a real production-path `STEP_LEVEL_DIAGNOSTIC` once those axes are already set by a human/ChatGPT session, not terminal end-to-end coverage, and is never described as such in this corpus.
- `available_step_diagnostics`: `EXECUTABLE_NOW` — the two-axis routing-gate diagnostic (`tests/posting_state_decision_wiring_v1_test.py`) is a real, currently-tracked fixture exercising `apply_posting_state_routing()` today; see Section 3a for its PASS/FAIL pairing.
- `blocking_evidence_gap`: no `src/` runtime evaluator that re-fetches the live posting and mechanically re-derives both axes automatically (Phase D §2).

**Case `F1-B` — Point32Health R9102 HTTP-200 dead-page false positive**
- `case_id`: `F1-B`
- `family`: `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (`AGENTS.md` Package-Time Recheck doctrine; PR #30).
- `operating_case_identity`: Point32Health, requisition R9102.
- `expected_terminal_outcome`: a requisition returning HTTP 200 with `TITLE_MATCH=False` must not continue to present as actionable at package time.
- `diagnostic_layer`: `TERMINAL_END_TO_END` — the observed defect was specifically that step-level signals (HTTP 200, surviving requisition token) looked fine while the terminal actionability judgment was wrong.
- `evaluator_type_owner`: `EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY` — the package-time recheck (`BLUEPRINT.md` §141.13-§141.15) is a human/ChatGPT-session act at package time, not a mechanically re-fetching runtime evaluator (per Phase D §2's coverage-gap finding).
- `current_executability`: `RECONSTRUCTION_BACKED_DESIGN_CASE` — the original live page state that produced the false positive is not preserved (`MISSING`); a future fixture would need a frozen snapshot of the dead-page HTML, which does not exist in repository history.
- `blocking_evidence_gap`: no preserved raw page snapshot/trace for the original R9102 defect instance.
- **Non-contradiction note (preserved from Phase C):** the same requisition also appears as OBSERVED item 11 of the 14-entry submitted-application ledger (Section 5.7 below) — the dead-page false positive and the later successful submission are two distinct, non-contradictory events; this corpus does not collapse them, matching Phase C's own treatment.

**Case `F1-C` — MassDOT 260005JH excluded application-route host**
- `case_id`: `F1-C`
- `family`: `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (`BLUEPRINT.md` §138.6.1; PR #35).
- `operating_case_identity`: MassDOT, IT Data Analyst I, requisition 260005JH, application route `massanf.taleo.net`.
- `expected_terminal_outcome`: a requisition whose only available application path is a locked excluded host must be routed away from that route rather than attempted against it.
- `diagnostic_layer`: `TERMINAL_END_TO_END`.
- `evaluator_type_owner`: `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` — the excluded-host list is a doctrine lock (`BLUEPRINT.md` §138.6.1); no runtime `src/` function was found during this design pass that mechanically consults the excluded-host list against a live discovered application route.
- `current_executability`: `BLOCKED_CANDIDATE` — no runtime enforcement mechanism exists to test; only the doctrine-text lock is checkable today. See Section 3a for the missing PASS/FAIL counterpart.
- `blocking_evidence_gap`: no `src/` runtime consumer of the excluded-host list was found in this repository during this design pass.

**Case `F1-D` — Fresenius Medical Care R0266808 stale-role identity failure**
- `case_id`: `F1-D`
- `family`: `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` — the exact dead-page text ("The page you are looking for doesn't exist") for this requisition is durably re-establishable per Phase C §2.
- `operating_case_identity`: Fresenius Medical Care, requisition R0266808.
- `expected_terminal_outcome`: an indexed/employer-owned requisition that actually returns an explicit dead-page state must never be treated as `VERIFIED_LIVE`.
- `diagnostic_layer`: `TERMINAL_END_TO_END`.
- `evaluator_type_owner`: `HUMAN_SEMANTIC_ADJUDICATION` at the time of the original defect (the fix sharpened `VERIFIED_LIVE`'s definition, per Phase C §2), now partially superseded by the dual-axis `RUNTIME_CONSEQUENTIAL_EVALUATOR` (Case `F1-A`) for the narrower axis-gate portion of this failure mode.
- `current_executability`: `RECONSTRUCTION_BACKED_DESIGN_CASE` — the dead-page text is durably preserved in Phase C's report, sufficient to design a future fixture faithfully, but no raw crawl/fetch trace survives to execute it today.
- `blocking_evidence_gap`: no raw crawl/fetch trace for this case (`MISSING`, per Phase C §2).

**Case `F1-E` — MGB RQ4055007 stale-role identity failure**
- `case_id`: `F1-E`
- `family`: `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION` — this was part of the same confirmed defect class that motivated `LIVE_ROLE_VERIFIED_ACTIONABILITY_GATE_V1` (PR #12); the failure itself is confirmed even though this specific requisition's page content cannot be re-established.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE`, explicitly weaker than Case `F1-D`: per Phase C, the exact first-party requisition content for MGB RQ4055007 could not be re-established from durable records reviewed.
- `operating_case_identity`: Mass General Brigham, requisition RQ4055007.
- `expected_terminal_outcome`: an indexed/employer-owned requisition that actually returns an explicit dead-page state must never be treated as `VERIFIED_LIVE`.
- `diagnostic_layer`: `TERMINAL_END_TO_END`.
- `evaluator_type_owner`: `HUMAN_SEMANTIC_ADJUDICATION` at the time of the original defect, now partially superseded by the dual-axis `RUNTIME_CONSEQUENTIAL_EVALUATOR` (Case `F1-A`) for the narrower axis-gate portion of this failure mode.
- `current_executability`: `BLOCKED_CANDIDATE` — unlike Case `F1-D`, this requisition's exact page state could not be re-established from durable records at all (Phase C's own finding); no fixture can even be design-drafted from what survives.
- `blocking_evidence_gap`: no raw crawl/fetch trace (`MISSING`, per Phase C §2); the exact page content is additionally unrecoverable even as reconstructed narrative.

### 5.2 Family 2 — `PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE` (negative cases)

**Case `F2-A` — Atominvest under-filled résumé**
- `case_id`: `F2-A`
- `family`: `PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (PR #16; `BLUEPRINT.md` §137).
- `operating_case_identity`: Atominvest, Implementation Analyst.
- `expected_terminal_outcome`: an exported résumé must meet the 92%-of-page-height meaningful-content floor before being presented to Bora as final.
- `diagnostic_layer`: `BOTH` — the geometry-floor check is a real step diagnostic; the terminal claim (did the *actual exported artifact* meet the floor) remains open, per Phase D §3's finding that no observed rendered-geometry producer feeds real geometry into the validator for every export.
- `evaluator_type_owner`: `RUNTIME_CONSEQUENTIAL_EVALUATOR` for `evaluate_resume_page_utilization()` (`src/resume_page_utilization.py`) itself; `EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY` for the full export path (Phase D §3, reaffirmed here unchanged).
- `current_executability`: `RECONSTRUCTION_BACKED_DESIGN_CASE` — this reflects the case's **terminal**, full render-to-validator claim only. The original under-filled DOCX artifact is `MISSING` (gitignored), and no observed rendered-geometry producer is proven to feed every real export into the validator. `evaluate_resume_page_utilization()` is a real executable `STEP_LEVEL_DIAGNOSTIC` once geometry is supplied; it does not, by itself, establish `EXECUTABLE_NOW` terminal coverage, and this corpus never states otherwise.
- `available_step_diagnostics`: `EXECUTABLE_NOW` — the geometry-floor function (`src/resume_page_utilization.py`) is exercised by a real, currently-tracked deterministic test (`tests/resume_page_utilization_v1_test.py`); see Section 3a for its PASS/FAIL pairing.
- `blocking_evidence_gap`: original package artifact (`MISSING`, gitignored per `.gitignore`); no observed rendered-geometry producer wiring, per Phase D §3.

**Case `F2-B` — Santander premature package generation**
- `case_id`: `F2-B`
- `family`: `PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (PR #30, governed run `20260909T172902Z-7add4b47`).
- `operating_case_identity`: governed closure run `20260909T172902Z-7add4b47` / Santander premature-package-generation case (role name not durably preserved in records reviewed, so the run identity is the stable reference, not an invented role title).
- `expected_terminal_outcome`: no résumé/cover-letter package may be generated before the exact first-party requisition is proven actionable in the current operating session.
- `diagnostic_layer`: `TERMINAL_END_TO_END`.
- `evaluator_type_owner`: `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` — `resume_package_spawn_gate_v1_test.py` self-describes as doctrine-record consistency, not automated package-time runtime validation (Phase D §3, reaffirmed unchanged).
- `current_executability`: `BLOCKED_CANDIDATE` — no runtime package-spawn-time gate implementation exists to test end-to-end; only the doctrine-shape test is checkable today. See Section 3a for the missing PASS/FAIL counterpart.
- `blocking_evidence_gap`: no proven automated runtime enforcement of the package-spawn gate at generation time (Phase D §3 coverage gap, reaffirmed unchanged).

**Case `F2-C` — DraftKings résumé drift / internal-jargon leakage**
- `case_id`: `F2-C`
- `family`: `PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (PR #30, same governed run as `F2-B`).
- `operating_case_identity`: governed closure run `20260909T172902Z-7add4b47` / DraftKings résumé-drift-and-jargon-leakage case (role name not durably preserved in records reviewed, so the run identity is the stable reference, not an invented role title).
- `expected_terminal_outcome`: candidate-facing package text must never leak internal Career-OS/governance vocabulary, and résumé content must not drift from the canonical gold family.
- `diagnostic_layer`: `TERMINAL_END_TO_END`.
- `evaluator_type_owner`: split, unchanged from Phase D §3 — the enumerable banned-term/internal-vocabulary lexical check is `UNCOVERED_CONSEQUENTIAL_SURFACE` (deterministic-first by nature; no such automated evaluator is proven to run at package-spawn time); gold-family *style/structural fidelity* drift beyond an objective lexical/structural diff is the genuinely subjective residual currently held by `HUMAN_SEMANTIC_ADJUDICATION`, and is the sole surface in this entire corpus named as a `POTENTIAL_CALIBRATED_LLM_JUDGE` future candidate (Section 6).
- `current_executability`: `BLOCKED_CANDIDATE` — neither the lexical banned-term scan nor style-fidelity has any runtime evaluator (human or automated-at-package-time) proven wired at generation time beyond final human QA. See Section 3a for the missing PASS/FAIL counterpart.
- `blocking_evidence_gap`: no deterministic lexical evaluator proven to run automatically at package-spawn time (Phase D §3, reaffirmed unchanged); original drifted résumé artifact is `MISSING` (gitignored).

### 5.3 Family 3 / 4 — `CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE` / `PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE` (positive controller/provider-integrity cases)

**Case `F3-A` — Controller/reviewer integrity findings F1-F9**
- `case_id`: `F3-A`
- `family`: `CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (`CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1`, PR #19 — attribution locked exactly per Phase D's own semantic correction; no closure-run ID from a separately-scoped session is conflated into this provenance).
- `operating_case_identity`: `CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1` / PR #19 F1-F9 finding set (stale-evidence detection, live scope-validation wiring, reviewer-mutation detection, internally-inconsistent SAFE-result rejection, test/review same-diff enforcement, fail-closed JSON extraction, fetch-failure fail-closed handling, lock-ownership-not-run-identity correction, real CLI envelope parsing), treated as one durable milestone artifact.
- `expected_terminal_outcome`: the controller/reviewer state machine reaches a SAFE, non-corrupting terminal state for each of these nine previously-reproduced defect conditions, with no evidence-lineage corruption and no silent reviewer-state mutation.
- `diagnostic_layer`: `BOTH`.
- `evaluator_type_owner`: `RUNTIME_CONSEQUENTIAL_EVALUATOR` — `milestone_run_v1_test.py` substantially exercises real controller/state-machine behavior across these boundaries (Phase D §4, reaffirmed unchanged).
- `current_executability`: `EXECUTABLE_NOW`.
- `blocking_evidence_gap`: `NONE` for the reproduced-and-closed defect classes; Phase D's own coverage-gap caveat is preserved unchanged — strong regression coverage of *known* reproduced defects does not itself establish coverage of unknown future controller defects, and this is a CI-regression fact, not a live-monitoring claim (Section 7).

**Case `F4-A` — Provider stdout/stderr transport defect**
- `case_id`: `F4-A`
- `family`: `PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE`
- `case_role`: `CONFIRMED_FAILURE_REGRESSION`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` (`CAREER_OS_PROVIDER_ENVELOPE_STDOUT_STDERR_SEPARATION_V1`, PR #22; canary run `20260907T220348Z-3dacfcfd`).
- `operating_case_identity`: exact canary run `20260907T220348Z-3dacfcfd` / `CAREER_OS_PROVIDER_ENVELOPE_STDOUT_STDERR_SEPARATION_V1` milestone.
- `expected_terminal_outcome`: valid structured JSON on stdout parses successfully regardless of concurrent diagnostic text on stderr; malformed/trailing/multi-document stdout and nonzero exits continue to fail closed.
- `diagnostic_layer`: `BOTH`.
- `evaluator_type_owner`: `RUNTIME_CONSEQUENTIAL_EVALUATOR` — `milestone_run_v1_test.py` session/transport-boundary coverage (Phase D §5, reaffirmed unchanged).
- `current_executability`: `EXECUTABLE_NOW`.
- `blocking_evidence_gap`: `NONE` for this specific reproduced-and-closed defect; general transport-health observability beyond reproduced cases remains `MISSING` (Phase D §5, unchanged).

### 5.4 Family 5 — `APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE` (mixed positive ledger-integrity / blocked runtime-suppression cases)

**Case `F5-A` — Submitted-opportunity ledger integrity**
- `case_id`: `F5-A`
- `family`: `APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE`
- `case_role`: `IMPORTANT_WORKFLOW` — this is a real, recurring integrity check the corpus must repeatably exercise; no failure event of the ledger itself is preserved.
- `provenance_quality`: `OBSERVED` — `docs/application/BORA_APPLICATION_HISTORY_V1.json` is a genuine, directly-confirmed, currently-tracked 14-entry ledger.
- `operating_case_identity`: the canonical `docs/application/BORA_APPLICATION_HISTORY_V1.json` / `BORA_APPLICATION_HISTORY_V1` ledger artifact itself, as one durable, concretely-named artifact.
- `expected_terminal_outcome`: the ledger remains structurally valid and internally consistent as the canonical Submitted Application Truth source.
- `diagnostic_layer`: `STEP_LEVEL_DIAGNOSTIC`.
- `evaluator_type_owner`: `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` — `tests/application_history_registry_v1_test.py` (Phase D §6, reaffirmed unchanged).
- `current_executability`: `EXECUTABLE_NOW`.
- `blocking_evidence_gap`: `NONE`.

**Case `F5-B` — Exact employer+requisition duplicate suppression at discovery/package time (representative replay: Public Consulting Group JR102087)**
- `case_id`: `F5-B`
- `family`: `APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE`
- `case_role`: `IMPORTANT_WORKFLOW` — no real duplicate-submission failure event is preserved in durable records; this case represents the recurring suppression workflow the doctrine requires, not a confirmed operating failure. It is not relabeled `CONFIRMED_FAILURE_REGRESSION` absent such an event.
- `provenance_quality`: `OBSERVED` for the doctrine lock (`BLUEPRINT.md` §138.15, `SUBMITTED_OPPORTUNITY_DEDUPE_V1`) and for the representative identity itself (Public Consulting Group, Apprentice Business Analyst, requisition JR102087, `docs/application/BORA_APPLICATION_HISTORY_V1.json` item 12); no runtime suppression-check instance is `OBSERVED` or reconstructable, because Phase D found none was ever implemented.
- `operating_case_identity`: Public Consulting Group, Apprentice Business Analyst, requisition JR102087 — used as the representative replay identity for a hypothetical re-submission attempt against an already-submitted ledger entry, consistent with the ledger and doctrine. **No real duplicate-submission failure event against this or any requisition is preserved in durable records; this report does not present a generic future duplicate as a confirmed operating failure.**
- `expected_terminal_outcome`: a re-discovered or re-packaged Public Consulting Group JR102087 opportunity is suppressed before it reaches Bora-facing discovery or package generation, because the ledger already records it as `SUBMITTED`.
- `diagnostic_layer`: `TERMINAL_END_TO_END` — this is precisely the case type Section 2's invariant warns about: the doctrine text and the ledger are both real and checkable, but there is no step diagnostic to even run for the actual suppression act, so the terminal outcome is entirely unproven either way.
- `evaluator_type_owner`: `UNCOVERED_CONSEQUENTIAL_SURFACE` for the runtime suppression check itself, at the actual discovery/package boundary (Phase D §6's key finding, reaffirmed unchanged and never overclaimed here).
- `current_executability`: `BLOCKED_CANDIDATE` — this is explicitly the most consequential unproven-runtime-coverage gap Phase D named; this report does not design a fixture for a mechanism that does not exist, and does not claim runtime dedupe coverage exists. See Section 3a for the missing PASS/FAIL counterpart.
- `blocking_evidence_gap`: no `src/` runtime implementation of the exact-employer+requisition suppression check was found during this design pass (matching Phase D's own finding exactly).

### 5.5 Recency-suppression cross-cutting case (grounded in real repository doctrine, distinct from the six Phase D families)

**Case `REC-A` — 22+ day hard-cutoff recency suppression (motivating identity: Public Consulting Group JR102087)**
- `case_id`: `REC-A`
- `family`: `CROSS_CUTTING_RECENCY_SUPPRESSION`
- `case_role`: `IMPORTANT_WORKFLOW` — no durable evidence supports a confirmed recency-suppression failure event for this or any specific requisition; this case is labeled `IMPORTANT_WORKFLOW`, not `CONFIRMED_FAILURE_REGRESSION`, because Phase C/D preserve no such failure to point to. The 21-day pass / 22+-day suppress edge pairing below is preserved exactly as existing doctrine tests state it, as step diagnostics, never as an invented real operating event.
- `provenance_quality`: `OBSERVED` — `BLUEPRINT.md`'s recency bands (`GOLD_WINDOW` 0-7 days, `STRETCH_WINDOW` 8-14 days, `FAR_STRETCH_WINDOW` 15-21 days, `SUPPRESSED_WINDOW` 22+ days) and `.cursor/rules/role-selection.mdc`'s identical bands are real, currently-tracked doctrine text, exercised by the real test files `tests/discovery_recency_hard_cutoff_v1_test.py`, `tests/discovery_recency_visibility_gate_v1_test.py`, and `tests/discovery_recency_work_format_priority_lock_v1_test.py`.
- `operating_case_identity`: Public Consulting Group, Apprentice Business Analyst, requisition JR102087 (`docs/application/BORA_APPLICATION_HISTORY_V1.json` item 12) is used as the durable motivating live example for this doctrine — a genuine, ledger-confirmed operating identity rather than a generic "any discovered role" placeholder. This case does not claim JR102087 itself was ever suppressed or delayed by the recency cutoff; it uses the identity only to ground the case in a real, non-generic operating record, consistent with the ledger.
- `expected_terminal_outcome`: a role at 22+ days is suppressed from normal Bora-facing serious discovery and package generation; a role at exactly 21 days still survives as `FAR_STRETCH_WINDOW`.
- `diagnostic_layer`: `BOTH` — `TERMINAL_END_TO_END` for the actual live suppression act; `STEP_LEVEL_DIAGNOSTIC` for the doctrine-text band-boundary checks that exist today.
- `evaluator_type_owner`: `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` — the three existing tests check `BLUEPRINT.md`/`role-selection.mdc` prose band text, not a runtime function that computes a live posting's age and mechanically applies the cutoff; no such `src/` runtime consumer was found during this design pass.
- `current_executability`: `BLOCKED_CANDIDATE` — this reflects the case's **terminal**, live-suppression claim, for the same reason as Case `F5-B`: no runtime enforcement mechanism exists to test end-to-end.
- `available_step_diagnostics`: `EXECUTABLE_NOW` — the doctrine-text band-boundary regression (`tests/discovery_recency_hard_cutoff_v1_test.py` and the two sibling files above) is real and already runs today, preserving the 21-day-survives / 22-day-suppresses edge pairing exactly as existing doctrine states it (Section 3a).
- `blocking_evidence_gap`: no `src/` runtime function found that computes live posting age and applies the 22-day cutoff automatically.

### 5.6 Family 6 — admission note (no operating case admitted)

`SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE` (Phase D failure family 6) has **no admitted operating case in this repeatable corpus.** Phase D §7-§8 records exactly one instance for this family, the Antigravity benchmark #1 case, and labels it strictly `EXPERIMENTAL_NON_CANONICAL` — never treated as authoritative and granting no authority over taxonomy, severity, or evaluator design. Because this corpus admits only `OBSERVED` or `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` cases (Section 0, Section 4), and Family 6 currently has only `EXPERIMENTAL_NON_CANONICAL` evidence, no Family-6 case is promoted into this repeatable corpus. This preserves the six-family taxonomy (all six families remain named and real) without laundering experimental evidence into a repeatable-eval-set case row. A future Family-6 case may be admitted only if a genuine `OBSERVED`/`RECONSTRUCTED_FROM_DURABLE_EVIDENCE` production instance is later found; this report does not construct one.

### 5.7 Positive continuity / clean-handoff cases

**Case `POS-A` — Fourteen-entry submitted-application ledger (clean successful handoff)**
- `case_id`: `POS-A`
- `family`: `POSITIVE_CONTINUITY`
- `case_role`: `POSITIVE_CONTINUITY_REFERENCE`.
- `provenance_quality`: `OBSERVED` — the full 14-entry `docs/application/BORA_APPLICATION_HISTORY_V1.json` ledger, `evidence_basis: BORA_DIRECT_CONFIRMATION` for every entry (The Brattle Group; Daley and Associates; Harvard Medical School Program Coordinator ×2 plus Harvard T.H. Chan Coordinator I plus Harvard Integrated Life Sciences Business Systems Analyst; MassDOT IT Data Analyst I; Mass General Brigham Financial Coordinator; Morgan Stanley Financial Analyst; Northeastern Cash Management Accountant; Point32Health Business Analyst; Public Consulting Group Apprentice Business Analyst; Road Scholar Coordinator; The Chicago School Operations Analyst).
- `operating_case_identity`: the canonical 14-entry `BORA_APPLICATION_HISTORY_V1` ledger, treated as a single aggregate artifact/reference set (not itemized per entry).
- `expected_terminal_outcome`: a genuine survivor role reaches a confirmed human submission handoff, durably recorded as Application Truth.
- `diagnostic_layer`: `TERMINAL_END_TO_END` — this is, by construction, the successful terminal state every negative case above is measured against.
- `evaluator_type_owner`: `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` for the ledger's own structural integrity (`tests/application_history_registry_v1_test.py`); the submission act itself is a human (Bora) act, a coverage/observability boundary rather than a machine-evaluated event (per Phase D §9's cross-cutting limitation, reaffirmed unchanged — this report does not invent a failure from a successful handoff).
- `current_executability`: `HUMAN_CONFIRMED_REFERENCE` — the 14 submitted applications are `OBSERVED` terminal references, but the human submission act is not machine-executable in any form; this case is never described as `EXECUTABLE_NOW` for the submission act itself.
- `available_step_diagnostics`: `EXECUTABLE_NOW` — the ledger's own structural/schema integrity is exercised by a real, currently-tracked test (`tests/application_history_registry_v1_test.py`); only that integrity layer, not the human submission act, is machine-executable.
- `blocking_evidence_gap`: `NONE` — this is a positive case, not a coverage gap; `HUMAN_CONFIRMED_REFERENCE` is a by-design classification, not a missing artifact.

**Case `POS-B` — Controller/reviewer clean SAFE terminal run**
- `case_id`: `POS-B`
- `family`: `POSITIVE_CONTINUITY`
- `case_role`: `POSITIVE_CONTINUITY_REFERENCE`.
- `provenance_quality`: `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` — the reviewer stdin-transport closure (`CAREER_OS_CURSOR_REVIEWER_STDIN_TRANSPORT_V1`, PR #23, run `20260908T184816Z-d3a8a974`), final Cursor review SAFE with zero findings.
- `operating_case_identity`: exact run `20260908T184816Z-d3a8a974` / `CAREER_OS_CURSOR_REVIEWER_STDIN_TRANSPORT_V1` closure.
- `expected_terminal_outcome`: the controller/reviewer loop reaches a genuinely clean terminal state — no reviewer-mutation, no evidence-integrity violation, and an independent SAFE verdict.
- `diagnostic_layer`: `BOTH`.
- `evaluator_type_owner`: `RUNTIME_CONSEQUENTIAL_EVALUATOR` (`milestone_run_v1_test.py`) plus `HUMAN_SEMANTIC_ADJUDICATION` (Cursor's own independent review act, which is not itself a machine-checked assertion).
- `current_executability`: `RECONSTRUCTION_BACKED_DESIGN_CASE` — this reflects the case's specific historical Cursor SAFE verdict, whose raw reviewer transcript is `MISSING` (gitignored — only the merged-PR body's durable citation of the verdict survives).
- `available_step_diagnostics`: `EXECUTABLE_NOW` — the general controller/reviewer regression suite (`milestone_run_v1_test.py`) is real and runs today, independent of this specific historical verdict's missing transcript.
- `blocking_evidence_gap`: raw reviewer transcript for run `20260908T184816Z-d3a8a974` is `MISSING` (gitignored `.career-os/`).

## 6. Deterministic-first objective checks and the future calibrated LLM judge

Unchanged in substance from Phase D §11, restated here as this eval-set's own operating rule: every objective lexical, structural, identity, or state-transition rule named anywhere in this corpus (banned/internal vocabulary scanning, requisition/title identity matching, dead-page text detection, ledger schema validation, recency band-boundary text) is **deterministic-first**. No case in this corpus specifies an LLM judge for any of these. The only surface in this entire corpus named as a `POTENTIAL_CALIBRATED_LLM_JUDGE` future candidate is Case `F2-C`'s gold-family style/structural fidelity residual — and only for the genuinely subjective portion left over *after* an objective lexical/structural diff-against-gold-reference check and human calibration, never as a substitute for the objective banned-term scan or for Family 6's architecture-fidelity enforcement (Phase D §11, reused verbatim). No LLM judge design, prompt, rubric, or implementation is authorized or specified by this report. This remains a future candidate only, contingent on a separately authorized architecture phase.

## 7. CI regression evals vs. live production monitoring/incidence

This distinction, already locked in Phase D (§4, §9, §10), governs this eval-set architecture unchanged: every `EXECUTABLE_NOW` case in Section 5 is a **CI regression eval**, but what it proves is case-role-sensitive, not uniform across the corpus. An `EXECUTABLE_NOW` case whose `case_role` is `CONFIRMED_FAILURE_REGRESSION` (e.g. Cases `F3-A`, `F4-A`) proves that a specific, already-reproduced defect class stays fixed when the existing deterministic test suite runs. An `EXECUTABLE_NOW` case whose `case_role` is `IMPORTANT_WORKFLOW` or `POSITIVE_CONTINUITY_REFERENCE` (e.g. Case `F5-A`'s ledger-integrity check, or the `available_step_diagnostics` recorded for `REC-A` and `POS-A`/`POS-B`) exercises an important deterministic doctrine, contract, or data-integrity condition every run, but does not itself imply that a previously-reproduced defect event is being kept fixed — no such failure event is preserved for those cases (Section 5.4, Section 5.5), and this report never states or implies otherwise. None of these cases, individually or in aggregate, constitute or imply a **live production monitoring/incidence** layer: no case here measures how often a given failure mode actually recurs during real, ongoing Career OS operation, and this report makes no production failure-rate claim anywhere. A future live-monitoring layer, if ever justified, is a separate, not-yet-proposed architecture item and is explicitly not designed, specified, or authorized here.

## 8. Summary case-inventory table

| Case | Family | Case role | Provenance | Diagnostic layer | Executability | Available step diagnostics | Evaluator type |
|---|---|---|---|---|---|---|---|
| F1-A MGB RQ4075857 | 1 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | BOTH | RECONSTRUCTION_BACKED_DESIGN_CASE | EXECUTABLE_NOW (dual-axis gate) | RUNTIME_CONSEQUENTIAL_EVALUATOR |
| F1-B Point32Health R9102 | 1 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | TERMINAL_END_TO_END | RECONSTRUCTION_BACKED_DESIGN_CASE | — | EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY |
| F1-C MassDOT 260005JH | 1 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | TERMINAL_END_TO_END | BLOCKED_CANDIDATE | — | DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION |
| F1-D Fresenius R0266808 | 1 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | TERMINAL_END_TO_END | RECONSTRUCTION_BACKED_DESIGN_CASE | — | HUMAN_SEMANTIC_ADJUDICATION |
| F1-E MGB RQ4055007 | 1 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED (weaker) | TERMINAL_END_TO_END | BLOCKED_CANDIDATE | — | HUMAN_SEMANTIC_ADJUDICATION |
| F2-A Atominvest | 2 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | BOTH | RECONSTRUCTION_BACKED_DESIGN_CASE | EXECUTABLE_NOW (geometry function) | RUNTIME_CONSEQUENTIAL_EVALUATOR |
| F2-B Santander | 2 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | TERMINAL_END_TO_END | BLOCKED_CANDIDATE | — | DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION |
| F2-C DraftKings | 2 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | TERMINAL_END_TO_END | BLOCKED_CANDIDATE | — | UNCOVERED_CONSEQUENTIAL_SURFACE / HUMAN_SEMANTIC_ADJUDICATION |
| F3-A Controller F1-F9 | 3 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | BOTH | EXECUTABLE_NOW | — | RUNTIME_CONSEQUENTIAL_EVALUATOR |
| F4-A Provider transport | 4 | CONFIRMED_FAILURE_REGRESSION | RECONSTRUCTED | BOTH | EXECUTABLE_NOW | — | RUNTIME_CONSEQUENTIAL_EVALUATOR |
| F5-A Ledger integrity | 5 | IMPORTANT_WORKFLOW | OBSERVED | STEP_LEVEL_DIAGNOSTIC | EXECUTABLE_NOW | — | DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION |
| F5-B Duplicate suppression (PCG JR102087 replay) | 5 | IMPORTANT_WORKFLOW | OBSERVED (doctrine+identity) / none (runtime) | TERMINAL_END_TO_END | BLOCKED_CANDIDATE | — | UNCOVERED_CONSEQUENTIAL_SURFACE |
| REC-A Recency hard cutoff (PCG JR102087 identity) | (cross-cutting) | IMPORTANT_WORKFLOW | OBSERVED | BOTH | BLOCKED_CANDIDATE | EXECUTABLE_NOW (doctrine text) | DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION |
| Family 6 | 6 | (none admitted) | EXPERIMENTAL_NON_CANONICAL only | — | not admitted | — | — |
| POS-A 14-entry ledger | positive continuity | POSITIVE_CONTINUITY_REFERENCE | OBSERVED | TERMINAL_END_TO_END | HUMAN_CONFIRMED_REFERENCE | EXECUTABLE_NOW (ledger integrity) | DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION |
| POS-B Clean SAFE controller run | positive continuity | POSITIVE_CONTINUITY_REFERENCE | RECONSTRUCTED | BOTH | RECONSTRUCTION_BACKED_DESIGN_CASE (verdict) | EXECUTABLE_NOW (suite) | RUNTIME_CONSEQUENTIAL_EVALUATOR / HUMAN_SEMANTIC_ADJUDICATION |

## 9. Not done / not authorized by this report

- No `CAREER_OS_RUN_TRACE_V1` schema, trace contract, typed envelope, or trace infrastructure.
- No database, UI, orchestration automation, new agent, or model router.
- No LLM judge design, prompt, rubric, or implementation — only a named future candidate surface, per Section 6.
- No new fixture files, evaluator code, or test files beyond this report's own dedicated regression (`tests/career_os_system_eval_set_architecture_v1_test.py`).
- No production Career OS behavior, schema, Candidate/Employer/Match/Pursuit truth, or package-generation logic changed.
- No claim that any `RECONSTRUCTION_BACKED_DESIGN_CASE` or `BLOCKED_CANDIDATE` in Section 5 is currently executable; each is explicitly not presented as an existing fixture.
- No claim that `posting_state_decision_wiring_v1_test.py` (Case `F1-A`) or `evaluate_resume_page_utilization()` (Case `F2-A`) constitute terminal end-to-end coverage; each is explicitly a `STEP_LEVEL_DIAGNOSTIC` recorded via `available_step_diagnostics`, never `current_executability: EXECUTABLE_NOW` for the terminal claim.
- No confirmed duplicate-submission failure event or confirmed recency-suppression failure event is invented; Cases `F5-B` and `REC-A` are labeled `IMPORTANT_WORKFLOW`, not `CONFIRMED_FAILURE_REGRESSION`, for exactly this reason.
- No Family-6 (`SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE`) operating case is admitted to this repeatable corpus; Section 5.6 records why.
- No generic "any discovered role" or "any future employer" placeholder identity is admitted as an operating case identity in this corpus; every admitted case names a concrete, durably-evidenced identity.
- No production failure-rate or incidence claim, per Section 7.
- Phase F and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**; this report does not authorize Phase F or implementation.

## 10. Acceptance

This report's substantive Phase E work is **COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE**. Operator completion does not constitute Bora's acceptance; those are separate, sequential events, exactly as Phase D's own report stated for itself. `implementation_authorized` remains **false**. No later phase is authorized by this report; Phase F and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED** absent a separate, future, explicit Bora authorization.
