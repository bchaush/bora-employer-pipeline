# Career OS Assurance Architecture V1

Milestone ID: `CAREER_OS_ASSURANCE_ARCHITECTURE_V1`

Status: **COMPLETED_BY_OPERATOR / PENDING_BORA_ACCEPTANCE / READ_ONLY_DESIGN_ONLY**
`implementation_authorized`: **false**. Phase H and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**.
Bora explicitly authorized this phase on 2026-09-14, from two genuine recorded statements: before Phase F's acceptance closed, "once we are proper to standard and all u have my absolute authorization to start the next phase G"; and, after PR #57 merged, "done G lets keep going brother we got this beautiful work we are doing here." This report renders the substantive Phase G assurance architecture design. Operator completion is **not** Bora acceptance and does **not** authorize Phase H or implementation. See `CURRENT_EXECUTION_CHECKPOINT.json` for the live machine-readable handoff.

This report is a READ_ONLY / DESIGN_ONLY governance/test architecture rendering over the existing canonical assurance runtime (`scripts/verify_assurance_baseline.py`, `scripts/verify_milestone_state.py`) and one round of local timing profiling on this baseline/workspace. It defines a two-loop assurance architecture — **conceptually and as a governance/test contract only**: no new CI workflow, no new runner script, no change to `scripts/verify_assurance_baseline.py`, no database, no UI, no vendor, no orchestration runtime, no new agent, no model router, and no LLM judge. It invents no new evidence, re-adjudicates no Phase D/E/F substance, and authorizes no later roadmap phase or implementation.

## 0. Epistemic rules governing this report

Unchanged from Phase C/D/E/F and reused here without modification:

- Every material claim is one of **OBSERVED**, **RECONSTRUCTED_FROM_DURABLE_EVIDENCE**, **EXPERIMENTAL_NON_CANONICAL**, or **MISSING**. No evidence state is upgraded.
- **CI regression evals remain conceptually distinct from live production monitoring/incidence.** This report makes no production failure-rate or reliability claim anywhere.
- Timing measurements in this report are **OBSERVED, single-sample, local-machine diagnostic evidence** — never an SLA, never a numerical reliability claim, and never generalized as a permanent property of the codebase. A single sample cannot establish variance, percentile behavior, or long-run stability.

## 1. Current canonical assurance runtime (as it exists today — unchanged by this report)

The single authoritative local full-suite assurance gate is `python scripts/verify_assurance_baseline.py`, run in this exact order:

- **Phase 0** — offline, deterministic semantic-state validation (`project_state.json` vs. `BLUEPRINT.md`), no network calls, no git-history merge-base assumptions.
- **Phase 1** — compile/syntax check (`python -m compileall -q src tests`).
- **Phase 2** — fail-closed discovery and execution of every `tests/*_test.py` file in deterministic sorted order. Fails closed if zero tests are discovered or if any of the nine mandatory coverage anchors (`application_gate_golden_test.py`, `posting_state_decision_wiring_v1_test.py`, `alternative_qualification_branch_representation_v1_test.py`, and the six schema smoke tests) is missing from the discovered set.
- **Phase 3** — the Job Analysis Golden runner (`golden-tests/run_job_analysis_golden_set.py`).

Exit code 0 is permitted only when all four phases succeed. This is also the exact command the hosted GitHub Actions "Assurance Baseline" workflow runs on push/PR. This report changes none of this — it remains, unmodified, the single promotion-authoritative full assurance path.

Separately, `python scripts/verify_milestone_state.py` performs the fuller branch-scoped milestone-contract check (requiring local `main`/merge-base availability), intended for local/developer/agent use, distinct from the CI-run Phase 0 offline check inside `verify_assurance_baseline.py`.

## 2. Observed timing evidence (single sample, this baseline/workspace only)

The following was measured once, locally, on this exact repository state and machine, and is recorded as diagnostic evidence only — **not** an SLA, not a percentile claim, not a statement about every machine or every future commit:

| Measurement | Observed value |
|---|---|
| Phase 1 compile | 3.118s |
| Phase 2 — 89 standalone tests, total | 416.406s |
| Phase 3 — golden runner | 1.248s |
| Recomputed sum of displayed rounded Phase 1 + Phase 2 + Phase 3 components | ~420.772s |
| Median standalone test | 0.447s |
| `milestone_run_v1_test.py` | 318.741s |
| `posting_state_decision_wiring_v1_test.py` | 35.100s |
| `career_os_state_v1_test.py` | 15.247s |
| `source_semantic_role_qualification_view_v1_test.py` | 5.089s |
| Tests observed >1s | 10 |
| Tests observed >5s | 4 |

The profiling helper also printed `ALL_TOTAL 418.172s`, but that aggregate is **RETIRED_AS_INVALID_EVIDENCE**: the helper reused the variable `dt` inside the per-test loop, so `ALL_TOTAL` added the final test duration instead of the compile duration. The `~420.772s` figure above is only a recomputed arithmetic sum of the displayed rounded component measurements (`3.118 + 416.406 + 1.248`), not a separately observed wall-clock timer.

`milestone_run_v1_test.py` alone accounts for roughly 76% of the observed Phase 2 total. It exercises controller/state-machine behavior against disposable real local Git repositories with faked providers — it is consequential meta/integration assurance coverage of the milestone controller's causal invariants, not disposable noise, and this report does not recommend weakening, excluding, or deleting it.

Separately, one hosted observation exists: GitHub Actions run `34915038186`, for the reviewed Phase G authorization head `3dd762e26edf9d4cf194ae70f65c08cafdb6f0a0`, completed successfully with the verify job finishing in roughly 47 seconds. **This single hosted-vs-local comparison (~47s hosted vs. ~420.772s recomputed displayed-component local sum) demonstrates that runtime is environment-sensitive, not that correctness or reliability differs between the two environments.** Both runs used the same canonical command and produced the same PASS/FAIL semantics; only wall-clock duration differed, plausibly due to hosted-runner hardware/caching/I/O characteristics distinct from this local development machine. No reliability or correctness inference is drawn from the duration gap in either direction.

## 3. The two-loop assurance architecture

This report defines two loops, both governance/test-contract concepts layered over the existing unmodified runtime — **not** a second canonical runner and **not** a global slow-test exclusion list.

### 3.1 Focused validation / iteration diagnostic (NON_AUTHORITATIVE)

A focused pass is milestone-scoped, explicitly non-authoritative feedback used after a mutation, run in this order:

1. The focused TEST SET: the active milestone contract's task-specific test commands from `required_tests`, after removing exactly these three envelope commands: `python scripts/verify_assurance_baseline.py`, `python scripts/verify_milestone_state.py`, and `git diff --check`; `required_tests` is the broader promotion-validation envelope and MUST NOT be inherited wholesale into the focused loop.
2. Two separate MECHANICAL ENVELOPE checks, run after the focused TEST SET: `python scripts/verify_milestone_state.py` and `git diff --check`.
3. Any additional test file directly relevant to the changed surface for that milestone, adjudicated per-milestone (not by a fixed global list).

This subtraction rule for the focused TEST SET is exact and fail-closed: the three envelope commands above are never members of the 11-command focused TEST SET, while every remaining task-specific test command in `required_tests` is part of the contract-declared focused TEST SET. These three envelope commands are not uniformly "promotion-only," and this report does not claim any of them can never be members of a broader focused-validation sequence — `python scripts/verify_milestone_state.py` and `git diff --check` are routinely run as MECHANICAL ENVELOPE checks during iteration, immediately after the focused TEST SET, not solely at the promotion boundary. `python scripts/verify_assurance_baseline.py` (Full Assurance) is different in kind: it is the sole promotion-authoritative full-suite gate (Section 3.2), and it alone must never enter the focused TEST SET and must never be re-added earlier in the iteration sequence in place of, or ahead of, its own promotion-boundary run. Additional causally relevant tests may be added for a mutation, but Full Assurance may not enter the focused TEST SET.

If the changed causal surface includes `milestone_run`/controller logic, `milestone_run_v1_test.py` must be run directly in the focused loop even though it is slow — focused scope is defined by causal relevance, never by wall-clock cost.

A focused pass — the focused TEST SET plus the two mechanical envelope checks — authorizes only further local iteration. **It never means "Assurance passed" and never grants freeze/commit/push/PR/merge authority on its own.** No message emitted by a focused pass may claim canonical full-suite success.

### 3.2 Full assurance (the sole promotion-authoritative gate — unchanged)

`python scripts/verify_assurance_baseline.py` (Section 1) remains the single authoritative local full-suite assurance gate and the hosted CI command, completely unmodified by this report. It remains mandatory before immutable freeze/review/promotion, and it must be re-run and pass after the final mutation preceding freeze, even if every prior mutation already passed focused validation and/or a prior full assurance run.

### 3.3 Non-negotiable semantics (binding on both loops)

- Every mutation invalidates any previously inherited focused or full "green" result — neither loop's result carries forward across a subsequent change.
- Full assurance is required again after the final mutation before freeze, regardless of how many focused passes preceded it.
- Focused validation may be used before full assurance to save iteration time, but may never substitute for full assurance at any promotion boundary (commit/push/PR/merge/freeze).
- Test classification into the focused loop is never based on a permanent, machine-specific wall-clock threshold, and no global slow-test exclusion list is created. The four tests observed >5s in Section 2 are not hardcoded anywhere as globally excludable — a future commit's causal-relevance analysis, not last measured duration, decides focused-loop membership.
- New tests continue to enter the authoritative full suite automatically through `scripts/verify_assurance_baseline.py`'s existing fail-closed `tests/*_test.py` discovery — this report adds no opt-out mechanism.
- The nine mandatory Phase 2 coverage anchors are not weakened, removed, or made optional by this architecture.
- Cursor's independent adversarial review of immutable reviewed bytes continues to occur after full assurance passes, unchanged.
- Hosted CI continues to run the identical canonical full command as additive confirmation of the exact reviewed head, unchanged.

## 4. Why the evidence earns loop separation but not a second canonical runner or exclusion manifest

The Section 2 evidence shows one concrete iteration cost (`milestone_run_v1_test.py` dominating local Phase 2 runtime at ~319s of the observed 416.406s Phase 2 test total) that plausibly discourages frequent local re-running of the entire suite during active iteration on unrelated milestone work. That single, concrete, reproducible cost justifies formally naming a lighter, milestone-scoped, explicitly non-authoritative focused loop (Section 3.1) so iteration can proceed without re-running unrelated slow tests every edit.

It does **not** yet earn a second canonical "fast assurance" command or a mutable slow-test exclusion list, for three reasons grounded directly in the evidence and the governing ADR's Phase G scope:

1. **Single-sample evidence cannot support a permanent classification.** One local timing run establishes that this run was slow on this machine at this moment — it does not establish that `milestone_run_v1_test.py` (or any other test) will remain the dominant cost after future changes, nor that the same four tests will remain the slowest ones. A hardcoded exclusion list built from one sample would silently stop reflecting reality the moment the codebase or environment changed, while still being trusted as if it were current.
2. **A second canonical fast-runner risks becoming a weaker substitute for full assurance**, which the governing ADR explicitly forbids (Section 4, Phase G scope: "a faster tier must never silently become a weaker substitute for required full assurance"). Any named alternate "pass" command creates exactly the confusion this report exists to prevent — a green result from a narrower command being mistaken for canonical full-suite success at a promotion boundary.
3. **The hosted-vs-local comparison (Section 2) shows the slowness is environment-sensitive**, not an intrinsic, uncorrectable property of the test suite. A ~47s hosted run against the identical canonical command on a comparable reviewed head suggests the local ~420.772s recomputed displayed-component sum (Section 2; an arithmetic recomputation, never an observed wall-clock timer) may substantially reflect this particular development machine's characteristics rather than a structural defect requiring a second runner to work around.

Given these three points, the correct V1 architecture is process separation (Section 3.1/3.2) rather than tooling proliferation. Further tooling investment (timing observability, targeted optimization, or, only if still warranted after both, a named non-authoritative fast command) is deferred to Phase H, where it can be justified by repeated measurement rather than one sample (Section 5).

## 5. Ranked recommendations for future Phase H (not implemented here)

**A. Timing observability on the existing full runner (highest priority).** Add standardized per-phase/per-test duration output to `scripts/verify_assurance_baseline.py`'s existing Phase 2/Phase 3 execution, without changing pass/fail semantics, coverage, ordering requirements, discovery, or promotion authority. Purely diagnostic output. This directly answers whether Section 2's single sample is representative, at near-zero architectural risk.

**B. Targeted optimization of `milestone_run_v1_test.py`'s own execution, if repeated measurement confirms it remains dominant.** If Recommendation A's ongoing timing data repeatedly shows `milestone_run_v1_test.py` (or its disposable real local Git repository / faked-provider fixture setup) dominating local runtime across multiple runs and machines, optimize that test's or controller-fixture's execution in a separate, bounded Phase H milestone. Any such optimization must preserve its adversarial scenario coverage and causal invariants unchanged, and must prove semantic equivalence with full assurance via dedicated regressions before it is trusted.

**C. A named non-authoritative fast-diagnostic command, only after A and B, and only if a material bottleneck still remains.** If repeated timing evidence after A and B still demonstrates a material iteration bottleneck, a broader fast-runner command may be considered — but only if it is explicitly named and surfaced as `NON_AUTHORITATIVE_FOCUSED_DIAGNOSTIC`, and it can never emit the canonical full-success terminal message (`"ALL PHASES PASSED: canonical assurance baseline verified."`) or any message that could be mistaken for it.

These are recommendations for a future, separately authorized Phase H bounded implementation milestone. None is selected, scheduled, or implemented by this report.

## 6. Explicit non-recommendations for V1

This report does not recommend, select, or authorize, now or as an implicit next step:

- parallel test execution;
- test sharding;
- cache-based test skipping;
- a pytest/framework migration for speed alone;
- deleting, weakening, or excluding `milestone_run_v1_test.py`;
- a mutable fast allowlist/denylist whose green status could be mistaken for promotion assurance;
- a second CI workflow that bypasses the canonical full command;
- any numerical reliability claim drawn from the Section 2 timings.

## 7. Not done / not authorized by this report

- No change to `scripts/verify_assurance_baseline.py`, `scripts/verify_milestone_state.py`, or any `.github/workflows/*` file.
- No new runner script, CI workflow, database, UI, vendor, storage engine, orchestration runtime, provider abstraction, new agent, model router, or LLM judge.
- No production Career OS behavior, `src/` code, schema, Candidate/Employer/Match/Pursuit truth, application history, package generation, or submission logic changed.
- No mandatory Phase 2 coverage anchor weakened, removed, or made optional.
- No global slow-test exclusion list, permanent wall-clock threshold, or mutable fast allowlist/denylist created.
- No numeric reliability, pass-rate, or production-incidence claim anywhere in this report; the Section 2 timings are labeled observed single-sample diagnostic evidence only.
- No re-adjudication of Phase D's six failure families, Phase E's exact 15-case corpus, or Phase F's conceptual run-trace/phase-contract architecture — each is consumed here as context only, unchanged.
- Phase H and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**; this report does not authorize Phase H or implementation.

## 8. State transition on operator completion

This report's substantive Phase G work is **COMPLETED_BY_OPERATOR** and is **PENDING_BORA_ACCEPTANCE**. `implementation_authorized` remains **false**. Phase H and every later roadmap phase remain **PROPOSED_NOT_AUTHORIZED**. Operator completion is explicitly **not** Bora acceptance and does **not** authorize Phase H or implementation. The exact next allowed action is Bora's acceptance or correction of this Phase G design; that acceptance, if given, itself authorizes no next phase — Bora must separately choose and explicitly authorize Phase H or any other next bounded governance action before it begins. Per this milestone's own review requirements, Cursor's independent adversarial review of the frozen exact diff is required before any commit/push/PR, and Cursor may not repair its own findings.
