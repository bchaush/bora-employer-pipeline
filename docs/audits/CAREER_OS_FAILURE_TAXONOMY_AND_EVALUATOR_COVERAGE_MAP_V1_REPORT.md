# Career OS Failure Taxonomy and Evaluator Coverage Map V1

Status: **COMPLETED_BY_OPERATOR / BORA_ACCEPTED (2026-09-11) / READ_ONLY_DESIGN_ONLY**
`implementation_authorized`: **false**. Phase E and every later roadmap phase: **PROPOSED_NOT_AUTHORIZED**.
Bora explicitly accepted this checkpoint/report on 2026-09-11, stating: "I am satisfied." See `CURRENT_EXECUTION_CHECKPOINT.json` for the live machine-readable handoff.

This report is a READ_ONLY / DESIGN_ONLY analytical rendering over already-adjudicated Phase B/C evidence (`docs/audits/CAREER_OS_EVAL_AND_HARNESS_AUDIT_V1_REPORT.md`, `docs/audits/CAREER_OS_TRACE_AND_FAILURE_CORPUS_INVENTORY_V1_REPORT.md`). It invents no new evidence, no evaluator code, no `CAREER_OS_RUN_TRACE_V1` design, no model router, no LLM judge, no database/UI, and no new runtime agent. It authorizes no implementation and no later roadmap phase.

## 0. Epistemic rules governing this report

- Every material claim below is labeled with one of: **OBSERVED**, **RECONSTRUCTED_FROM_DURABLE_EVIDENCE**, **EXPERIMENTAL_NON_CANONICAL**, or **MISSING**. No UNKNOWN or MISSING evidence state is upgraded.
- Where reference guidance is discussed, claims are labeled **SOURCE_DIRECT**, **CAREER_OS_ADAPTATION**, **OBSERVED_REPO_FACT**, or **OPEN_HYPOTHESIS**.
- **Severity is a consequence class only — never a frequency/probability/incidence claim.** No production failure rate is asserted anywhere in this report.
- This taxonomy is **provisional and non-saturated** — it reflects the genuine corpus Phase C inventoried, not a claim of completeness over every possible Career OS failure mode.

## 1. The six provisional failure families

The taxonomy uses six families. Existing repo evidence required only a naming refinement (mapping Phase C's qualitative open-coding tags onto these six families), not a new family.

1. `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`
2. `PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE`
3. `CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE`
4. `PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE`
5. `APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE`
6. `SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE`

Severity vocabulary (consequence class, not likelihood):
- **S3** = `INTEGRITY_OR_USER_ACTION_CRITICAL`
- **S2** = `USER_FACING_OR_WORKFLOW_HIGH`
- **S1** = `FAIL_CLOSED_OPERATIONAL`

Coverage vocabulary:
- `RUNTIME_CONSEQUENTIAL_EVALUATOR` — a deterministic evaluator/regression that exercises actual production-path logic at the consequential decision boundary (i.e., the regression calls or is wired into the real `src/` function that makes or gates the consequential decision, not a description of it). This label is a claim about **CI/regression coverage of production-path code**, and explicitly does **not** imply live production monitoring, incidence measurement, or any claim about how often the covered path actually executes correctly in a real operating session. CI regression coverage and live monitoring are kept distinct throughout this report (`CAREER_OS_ADAPTATION` of the Hamel Husain / Shreya Shankar CI-vs-monitoring distinction; see §10).
- `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` — a deterministic test that validates doctrine text, contract shape, canonical-data/ledger integrity, or internal consistency, without itself exercising the production decision path at the consequential boundary.
- `HUMAN_SEMANTIC_ADJUDICATION`
- `POTENTIAL_CALIBRATED_LLM_JUDGE`
- `UNCOVERED_CONSEQUENTIAL_SURFACE`
- `EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY`

---

## 2. Failure family 1 — `LIVE_OPPORTUNITY_ACTIONABILITY_IDENTITY_ROUTE_FAILURE`

**Failure class/subclass:** a role/requisition surfaces as actionable (APPLY-like) when the exact current first-party posting is stale, dead, retitled, or otherwise fails to establish current actionability (role/title identity, requisition identity, substantive current content, and a live application route).

**Evidence/provenance:** `RECONSTRUCTED_FROM_DURABLE_EVIDENCE`, cited in Phase C to merged-PR bodies, `CHANGELOG.md`, `CURRENT_STATE.md`, and milestone contracts for: MGB RQ4055007, Fresenius R0266808, MGB RQ4075857, Point32Health R9102, and the MassDOT 260005JH application-route case. No raw trace/log artifact for these cases is available in-repo (`MISSING`); the reconstruction is from durable secondary evidence, not raw session logs.

**Consequence/severity rationale:** **S3 — `INTEGRITY_OR_USER_ACTION_CRITICAL`**. A false-positive actionable surface can lead Bora toward wasted or misdirected human action (package generation or submission attempt against a dead/mismatched route). Severity reflects the class of consequence if it recurs uncaught, not an observed or estimated rate of recurrence.

**Observable signal:** an HTTP 200 response, a surviving requisition token, an ATS shell, or an Apply-like control present while the underlying role/requisition identity, content, or route has actually changed or died.

**Current coverage type:** `RUNTIME_CONSEQUENTIAL_EVALUATOR` for the narrow dual-axis gate. `apply_posting_state_routing()` (`src/job_decision.py`) is a real production routing function requiring **both** `role_status == "VERIFIED_LIVE"` **and** `source_verification_status == "VERIFIED_DIRECT"` before preserving APPLY-like routing, and `posting_state_decision_wiring_v1_test.py` exercises this production code path. `live_actionability_semantic_quorum_v1_test.py` is a **separate, doctrine-only** regression describing the §135/§135.1 full end-user-transition semantic quorum (job-detail identity + actual application-transition resolution); it does **not** exercise a runtime validator that independently re-derives transition success — it is `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION`, not a runtime evaluator. These two tests must not be conflated: one proves production routing behavior around the two-axis gate; the other proves the doctrine text/contract shape is present and internally consistent.

**Evaluator owner/system boundary:** `src/job_decision.py` (deterministic axis gate) plus human/ChatGPT re-verification of the full end-to-end transition per `BLUEPRINT.md` §135.1/§141.13 (a human/semantic act performed each operating session, not a machine-checked runtime assertion of "the browser reached page X").

**Coverage gap:** there is no automated runtime evaluator that itself re-fetches the live posting and mechanically re-derives `role_status`/`source_verification_status`; the actual end-user transition re-check is a human/ChatGPT-in-session act, evaluated only by the doctrine-shape regression, not by an executable end-to-end check. This is `EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY` for the full live-fetch/transition boundary, while remaining `RUNTIME_CONSEQUENTIAL_EVALUATOR` for the narrower two-axis routing gate once the axes are set.

**End-to-end/handoff coverage:** **missing.** No automated evaluator proves, end-to-end and unattended, that a stale/dead live posting is caught before human package/submission time; this depends on human/ChatGPT session discipline plus the two downstream deterministic gates (routing axis gate; package-time recheck below).

---

## 3. Failure family 2 — `PACKAGE_SPAWN_AND_CANDIDATE_ARTIFACT_QUALITY_FAILURE`

**Failure class/subclass:** a generated résumé/cover-letter package is spawned prematurely (before actionability is re-proven), or drifts from the canonical gold family, under-fills content, or leaks internal Career-OS/governance language into candidate-facing text.

**Evidence/provenance:** `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` — Atominvest (under-filled one-page résumé, corrected manually by Bora), Santander (package generated before the exact first-party requisition was proven actionable), and DraftKings (résumé drift from the canonical gold family plus internal-jargon leakage). Cited to merged-PR bodies, `CHANGELOG.md`, and milestone contracts, not raw package-generation traces (`MISSING`).

**Consequence/severity rationale:** **S2 — `USER_FACING_OR_WORKFLOW_HIGH`**. A degraded or premature package is user-facing (Bora must manually catch and correct it before submission) and creates real workload, but does not by itself corrupt persisted truth/evidence state the way an integrity failure would.

**Observable signal:** page-height/meaningful-content ratio below the 92% floor; DOCX content diverging from the gold-reference family; internal-system vocabulary appearing in candidate-facing text; package artifacts existing before the current-session actionability recheck passed.

**Current coverage type:**
- Atominvest under-fill: `RUNTIME_CONSEQUENTIAL_EVALUATOR` exists — `evaluate_resume_page_utilization()` (`src/resume_page_utilization.py`) is a real, pure-geometry deterministic validator wired as an optional `page_geometry` parameter on `resume_validation.py`'s export-approval gate, enforcing the 92% floor. **However**, based on current repository/BLUEPRINT evidence reviewed in Phase D, there is **no observed rendered-geometry producer that mechanically feeds real page-geometry into this validator for every actual export** — the validator itself is real and runs correctly on the geometry it is given, but end-to-end production coverage (a real DOCX/PDF render pipeline invoking it on every export) is not established. Classification: `EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY` for the full export path; `RUNTIME_CONSEQUENTIAL_EVALUATOR` for the geometry-input-to-floor-check function itself.
- Santander/DraftKings (package-spawn gate, gold-family drift, jargon leakage): `resume_package_spawn_gate_v1_test.py` explicitly self-describes as a **doctrine-record consistency test**, not automated package-time runtime validation. Classification: `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION`, not `RUNTIME_CONSEQUENTIAL_EVALUATOR`. The consequential package-time gate (§141.13-§141.15, `docs/resume/BORA_PACKAGE_SPAWN_GATE_V1.json`, `.cursor/rules/resume.mdc`) is enforced operationally through Cursor-rule-guided human/agent discipline at generation time, not proven runtime-covered by an automated test that itself spawns a package and asserts the gate fired.

**Evaluator owner/system boundary:** `src/resume_page_utilization.py` + `resume_validation.py` (deterministic, narrow); `.cursor/rules/resume.mdc` operational discipline plus human/Bora final visual QA. Internal-jargon-leakage detection checks candidate-facing text against an enumerable, objectively-specifiable banned-term/internal-vocabulary list — this is `UNCOVERED_CONSEQUENTIAL_SURFACE` for a deterministic lexical evaluator (no such automated evaluator is proven to run at package-spawn time), not a genuinely subjective surface, and is deterministic-first by nature. Gold-family style/structural fidelity drift, beyond what an objective lexical/structural diff-against-gold-reference check can establish, is the genuinely subjective residual currently held by `HUMAN_SEMANTIC_ADJUDICATION`.

**Coverage gap:** no proven automated runtime coverage that a real export pipeline actually invokes the page-utilization validator on every artifact; no deterministic lexical evaluator proven to run automatically against the banned-term/internal-vocabulary list for jargon-leakage detection at package-spawn time (an objectively-specifiable gap: `UNCOVERED_CONSEQUENTIAL_SURFACE`); no automated coverage of gold-family style/structural fidelity drift beyond objective checks (the genuinely subjective residual: `HUMAN_SEMANTIC_ADJUDICATION`) — none of these are execution-proven.

**End-to-end/handoff coverage:** **missing** for both the render-to-validator wiring and the package-spawn-gate runtime enforcement; human final QA (Bora reviewing the actual rendered artifact) is the last line of defense and is a boundary limitation, not itself a documented failure.

---

## 4. Failure family 3 — `CONTROLLER_REVIEWER_EVIDENCE_INTEGRITY_FAILURE`

**Failure class/subclass:** controller/reviewer state-machine defects that could corrupt evidence lineage, mutate reviewer state incorrectly, or violate SAFE/consistency invariants (Phase C findings F1–F9).

**Evidence/provenance:** `RECONSTRUCTED_FROM_DURABLE_EVIDENCE` for the F1–F9 findings, attributed to `CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1` (PR #19), matching the canonical Phase C report's provenance for these findings. Governed closure runs `20260909T172902Z-7add4b47`, `20260908T184816Z-d3a8a974`, and `20260909T040202Z-811bdf0a` are separately-scoped closure evidence for other governed sessions; they are **not** the source of F1–F9 and are not conflated with this Family 3 evidence. Raw per-run traces beyond `CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1` / PR #19 are `MISSING` (gitignored `.career-os/` artifacts).

**Consequence/severity rationale:** **S3 — `INTEGRITY_OR_USER_ACTION_CRITICAL`**. Controller/reviewer defects touch evidence lineage and state-machine consistency directly — the highest-consequence class in this taxonomy, independent of how often such a defect might recur.

**Observable signal:** stale-evidence acceptance, incorrect reviewer-state mutation, SAFE-consistency violation, or a no-commit/no-push boundary breach.

**Current coverage type:** `RUNTIME_CONSEQUENTIAL_EVALUATOR`. `milestone_run_v1_test.py` substantially exercises real controller/state-machine behavior: stale-evidence handling, reviewer mutation, SAFE consistency, assurance/fetch/locking/session/transport boundaries, and the no-commit/no-push invariant. This is genuine regression coverage of real controller logic, not a doctrine-only shape test.

**Evaluator owner/system boundary:** the controller/reviewer test suite itself (`milestone_run_v1_test.py`), deterministic by construction.

**Coverage gap:** strong CI/regression coverage of *known, already-reproduced* defect classes (F1–F9) does not establish coverage of unknown future controller defects, and there is no live production incidence/frequency monitoring layer — this is a CI-regression-vs-production-monitoring distinction (Hamel Husain / Shreya Shankar reference frame, `CAREER_OS_ADAPTATION`), not a claim that the controller is unmonitored in some deficient way beyond what any CI-only regression suite provides.

**End-to-end/handoff coverage:** regression coverage is strong for the reproduced cases; end-to-end live-run observability (raw traces) beyond the cited closure-run citations is `MISSING`.

---

## 5. Failure family 4 — `PROVIDER_SESSION_TRANSPORT_RECOVERABILITY_FAILURE`

**Failure class/subclass:** provider/session stdout-stderr or stdin transport defects that could interrupt or corrupt a controller-mediated agent session.

**Evidence/provenance:** `RECONSTRUCTED_FROM_DURABLE_EVIDENCE`, citing run `20260907T220348Z-3dacfcfd` (the transport defect itself) and historical runs `20260907T180932Z-656eae27` and `20260907T193310Z-f6a756d2`, with the reviewer stdin-transport closure separately cited at run `20260908T184816Z-d3a8a974` (a non-defect governed closure run, not a second defect).

**Consequence/severity rationale:** **S1 — `FAIL_CLOSED_OPERATIONAL`**. A transport failure halts or degrades a session operationally; it is disruptive to workflow continuity but does not by itself corrupt persisted evidence/truth state the way family 3 does, provided the system fails closed (which the cited closure indicates it did).

**Observable signal:** stdout/stderr stream desynchronization or stdin transport failure during a controller-mediated provider session.

**Current coverage type:** `RUNTIME_CONSEQUENTIAL_EVALUATOR` for the reproduced-and-closed cases — `milestone_run_v1_test.py` covers session/transport boundaries as part of its controller regression coverage (see family 3).

**Evaluator owner/system boundary:** controller/session-transport layer, deterministic regression suite.

**Coverage gap:** coverage exists for the specific reproduced transport defect and its closure; there is no broader live monitoring of transport health across all provider sessions in production use (an observability gap, not a proven current failure).

**End-to-end/handoff coverage:** the specific defect's regression is closed; general transport-health observability beyond reproduced cases is `MISSING`.

---

## 6. Failure family 5 — `APPLICATION_LIFECYCLE_DUPLICATE_CONTINUITY_FAILURE`

**Failure class/subclass:** a duplicate application attempt against an employer+requisition pair that already has Submitted Application Truth, or loss of continuity for an in-progress application across sessions.

**Evidence/provenance:** `OBSERVED` for the ledger itself — `docs/application/BORA_APPLICATION_HISTORY_V1.json` (`BORA_APPLICATION_HISTORY_V1`) is a genuine, directly-confirmed 14-entry corpus, and its own internal integrity (schema/structure) is deterministically validated. The doctrine that exact employer+requisition duplicates must be suppressed (`SUBMITTED_OPPORTUNITY_DEDUPE_V1`, `BLUEPRINT.md` §138.15) is doctrine-locked and `OBSERVED` as written doctrine.

**Consequence/severity rationale:** **S2 — `USER_FACING_OR_WORKFLOW_HIGH`**. A duplicate submission wastes Bora's and an employer's time and is reputationally undesirable, but does not corrupt evidence lineage the way a family-3 defect would.

**Observable signal:** the same employer+exact-requisition pair being surfaced or packaged again after historical Submitted Application Truth already exists for it.

**Current coverage type:** **This is the key finding that must not be overclaimed.** The ledger's own data-integrity (schema/structure validation) and the `SUBMITTED_OPPORTUNITY_DEDUPE_V1` doctrine lock are both `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` — deterministic tests that validate ledger/data integrity and doctrine text/contract shape, not a runtime evaluator wired into the actual `src/` decision path. Current repo evidence, as reviewed, does **not** establish a consequential `src/` runtime implementation that actually performs the exact-employer+requisition suppression check against the ledger at discovery/package time. The doctrine text is locked and clear; a runtime dedupe *implementation* proven to run on every discovery/package pass is **not established** by current evidence. Classification: `UNCOVERED_CONSEQUENTIAL_SURFACE` for the runtime suppression check itself, at the actual discovery/package consequential runtime boundary; `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION` for the ledger integrity and doctrine-lock layer.

**Evaluator owner/system boundary:** doctrine owner is `BLUEPRINT.md` §138.15 / `AGENTS.md`; the ledger integrity validator is a `DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION`; the actual suppression check at discovery/package time is currently a human/ChatGPT-session discipline act (load the ledger, apply the check manually), not a proven automated runtime gate.

**Coverage gap:** no automated runtime evaluator proven to intercept a duplicate opportunity before it reaches Bora-facing discovery or package generation. **Do not claim runtime dedupe coverage exists** — this report explicitly does not.

**End-to-end/handoff coverage:** **missing.** This is the most consequential unproven-runtime-coverage gap in this taxonomy, precisely because the doctrine is strong and the ledger is real, but the closing mechanism between them is not proven to be code rather than session discipline.

---

## 7. Failure family 6 — `SEMANTIC_CONTRACT_ARCHITECTURE_FIDELITY_FAILURE`

**Failure class/subclass:** a builder produces output that passes focused regressions and/or the full deterministic suite yet violates the semantic intent, architecture boundary, or milestone contract it was supposed to implement — a fidelity failure invisible to purely mechanical pass/fail checks.

**Evidence/provenance:** `EXPERIMENTAL_NON_CANONICAL` — the sole cited instance is the Antigravity benchmark #1 case (see §8 below). This is the one failure family in this taxonomy whose only current evidentiary instance is explicitly non-canonical; it is retained as a named family because the failure mode it names (test-green, architecture-false) is a real and general risk class independently recognized by the IndyDevDan/Hamel Husain/Cole Medin reference frames (`CAREER_OS_ADAPTATION`), not because Career OS has an `OBSERVED` production instance of it yet.

**Consequence/severity rationale:** **S2 — `USER_FACING_OR_WORKFLOW_HIGH`** as a general class (a wrong architectural change reaching production would require rework and could reintroduce a previously solved defect), though the only concrete instance on file is experimental/non-canonical and never reached production.

**Observable signal:** a diff that passes its own focused tests, the full assurance suite, and any golden set, while a human/adjudicator determines the change contradicts the milestone's actual semantic/architecture intent.

**Current coverage type:** `HUMAN_SEMANTIC_ADJUDICATION`. No sufficient deterministic evaluator is established today for this class — the sole cited instance (§8) shows a defective builder pass can satisfy the deterministic suite while still violating milestone contract fidelity. The evaluator that currently catches it is Cursor's independent adversarial review plus ChatGPT/Bora semantic adjudication of contract fidelity, not an automated test.

**Evaluator owner/system boundary:** Cursor independent adversarial review (mandatory before commit/push per `AGENTS.md`/`CLAUDE.md`) plus ChatGPT architectural adjudication.

**Coverage gap:** no sufficient deterministic evaluator is established today (a green suite can coexist with the false-positive condition this family names). `UNCOVERED_CONSEQUENTIAL_SURFACE` with respect to any *automated* evaluator; the existing human/adversarial-review layer is the current governing coverage. Future deterministic structural/contract-fidelity evaluators may be designed to cover subsets of this class, but this Phase D report neither designs nor authorizes any such evaluator.

**End-to-end/handoff coverage:** covered by process (mandatory Cursor review before commit/push) but not by any executable evaluator; this is an intentional, structural limitation, not an oversight.

---

## 8. Antigravity benchmark #1 (EXPERIMENTAL_NON_CANONICAL only)

This entry is recorded strictly as **EXPERIMENTAL_NON_CANONICAL**. It is never treated as authoritative and grants no authority over taxonomy, severity, or evaluator design in this report.

- Adjudication: `FAILS_BOUNDED_BUILDER_QUALIFICATION_CASE_1` / `IMPLEMENTATION_PLAUSIBLE_BUT_SEMANTICALLY_MISALIGNED`.
- Historical baseline: `7c7d4daa373c7e8f0bd7843eee4b65823980c9dc`
- Tracked diff SHA-256: `8539e9f13482465bd149abd051a3522548f8569e0864b2f7b6e3b5a44978409c`
- Focused test SHA-256: `437ad3c6612d1c19ecf66071212c7895f6f3bbaac0ea522bd8c9ddfb05ff0f42`

**Lesson (the only thing this case is used for):** a candidate implementation can pass its own focused regressions, the full deterministic assurance suite, and a golden set, while still violating milestone semantics or architecture fidelity. This is the concrete motivating instance for failure family 6 above. It grants **zero** builder authority — it is not evidence that any other tool, model, or process is qualified or disqualified for anything beyond this one documented, non-canonical case.

---

## 9. Cross-cutting limitations (recorded separately from the six failure families)

These are observability/process limitations, not failure events in themselves:

- **Missing raw traces.** `.career-os/` run artifacts and local PDF/DOCX package artifacts are gitignored and therefore `MISSING` from repository history except where separately, durably cited (closure-run IDs). This limits how many of the above findings can be verified beyond the cited durable secondary evidence.
- **No live incidence/frequency monitoring.** This report makes no claim about how often any failure class actually recurs in live operation — severity above is a consequence class only. There is currently no production monitoring layer that would make an incidence claim possible.
- **No claim of production failure rates.** Explicitly not asserted anywhere in this report.
- **Human submission-confirmation boundary.** Final submission is a human (Bora) act; a successful human handoff is a coverage/observability boundary, not a documented failure — this report does not invent a failure from a successful handoff.
- **Possible future durable experimental-run receipts** — recorded here only as `OPEN_HYPOTHESIS`. This report does not design, specify, or schema any receipt infrastructure, and does not perform an experimental-run-receipts audit.
- **`CAREER_OS_RUN_TRACE_V1`** — mentioned here only as a known missing/future out-of-scope observability architecture item (see ADR `docs/decisions/ADR-CAREER-OS-EVAL-HARNESS-SEQUENCE-V1.md` Phase F). This report does not design, specify, schema, or authorize it.

## 10. Reference-framework conformance (no new doctrine added)

- **IndyDevDan** (`CAREER_OS_ADAPTATION`): deterministic control-plane ownership and bounded agent/builder-grader separation are visible in the existing controller/reviewer split and the mandatory Cursor-review gate; this report reaffirms that a passing test suite does not equal a correct or non-defective gate (family 6), and that the gate itself can be defective — a possibility this report does not resolve, only names.
- **Hamel Husain / Shreya Shankar** (`CAREER_OS_ADAPTATION`): this report is built from genuine traces/durable secondary evidence and Phase C's prior human open-coding, per their guidance to ground taxonomy in real error analysis rather than speculative categories. It preserves their CI-regression-vs-live-monitoring distinction explicitly (family 3, family 4) and names, without designing, the one place a potential calibrated LLM judge could someday apply: genuinely subjective residual surfaces such as gold-family style/naturalness fidelity in family 2, evaluated only after objective lexical/structural checks — not internal-jargon-leakage detection against an enumerable banned-term vocabulary, which is deterministic-first — recorded strictly as a **future candidate only**, never implemented or specified here.
- **Cole Medin** (`CAREER_OS_ADAPTATION`): this report itself is an artifact of Plan → Implement → Validate separation (Phase B plan/audit → Phase C real-trace inventory → this Phase D taxonomy), stored as durable Git/checkpoint memory rather than conversational memory. No machinery is proposed merely because it could theoretically exist; each gap above is named without a proposed build.

## 11. Potential calibrated LLM judge — future candidate only

The only surfaces named above as candidates for a future calibrated LLM judge are genuinely subjective residual surfaces that remain *after* objective lexical/structural checks and human calibration: package gold-family style/naturalness fidelity drift (family 2), and possibly future subjective quality review of family 6-style semantic-fidelity findings once objective structural/contract checks have been exhausted. Internal-jargon-leakage detection against an enumerable banned-term/internal-vocabulary list is deterministic-first, not an LLM-judge candidate: a `POTENTIAL_CALIBRATED_LLM_JUDGE` must never be positioned as a shortcut for objective banned-term rules or for family 6's architecture-fidelity enforcement. **No LLM judge design, prompt, rubric, or implementation is authorized or specified by this report.** This remains an `OPEN_HYPOTHESIS` future candidate, contingent on a separately authorized architecture phase.

## 12. Summary coverage table

| Family | Severity | Coverage type | Runtime evaluator proven? |
|---|---|---|---|
| 1. Live opportunity actionability/route | S3 | Mixed: RUNTIME_CONSEQUENTIAL_EVALUATOR (axis gate) + EVALUATOR_PRESENT_NOT_AT_CONSEQUENTIAL_BOUNDARY (full transition) | Partial |
| 2. Package spawn/artifact quality | S2 | Mixed: RUNTIME_CONSEQUENTIAL_EVALUATOR (page-utilization function) + DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION (spawn gate) + UNCOVERED_CONSEQUENTIAL_SURFACE (jargon lexical evaluator, deterministic-first) + HUMAN_SEMANTIC_ADJUDICATION (gold-family style fidelity) | Partial |
| 3. Controller/reviewer evidence integrity | S3 | RUNTIME_CONSEQUENTIAL_EVALUATOR | Yes (known cases) |
| 4. Provider/session transport | S1 | RUNTIME_CONSEQUENTIAL_EVALUATOR | Yes (known case) |
| 5. Application lifecycle duplicate/continuity | S2 | UNCOVERED_CONSEQUENTIAL_SURFACE (runtime dedupe) + DETERMINISTIC_DOCTRINE_OR_CONTRACT_REGRESSION (ledger/doctrine) | No (runtime dedupe not established) |
| 6. Semantic contract/architecture fidelity | S2 | HUMAN_SEMANTIC_ADJUDICATION | No (no sufficient deterministic evaluator established today) |

## 13. Explicit non-recommendations

Per the build-economy gate (`BLUEPRINT.md`) and this report's own read-only/design-only bound, this report does **not** recommend or authorize: `CAREER_OS_RUN_TRACE_V1` or any trace infrastructure; a database or UI surface; a model router; an LLM judge implementation; orchestration automation; a new runtime agent; a context-surface refactor (`CLAUDE.md`/`.cursor/**`/`.claude/**`); or any Phase E or later roadmap-phase work. Any future architecture addressing the gaps named above (most notably family 5's unproven runtime dedupe, and family 2's unproven render-to-validator wiring) requires its own separately authorized phase.

## 14. Disposition

Phase D substantive read-only/design-only work is **COMPLETED_BY_OPERATOR** and is **BORA_ACCEPTED (2026-09-11)**: Bora explicitly accepted this checkpoint/report by stating "I am satisfied." This acceptance does not constitute Bora's acceptance of any Phase E or later roadmap phase; no Phase E or implementation work may begin without a separate, later Bora authorization.
