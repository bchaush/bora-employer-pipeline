# ADR — Reproducible Consequential Assurance Baseline v1

Status: **PROPOSED_FOR_IMPLEMENTATION_REVIEW**
Date: 2026-09-02
Approved by: Bora / ChatGPT Work (architecture decision milestone; independent Cursor implementation review pending)

## Context

The repository currently has strong manually executed assurance: 59
standalone unit/regression/adversarial `tests/*_test.py` scripts (confirmed
by direct listing), a Job Analysis Golden suite (15/15), an Application Gate
Golden suite (9/9), posting-state regressions, qualification-gate
regressions, compile/syntax verification, and multiple independent
adversarial reviews (Cursor) prior to every consequential commit.

But this assurance is not yet:

- reproducibly reconstructable from repo-declared dependencies;
- executable through one canonical cross-platform command;
- automatically run on proposed repository changes;
- guaranteed to exercise all identified P0 causal integration invariants
  (e.g. gated-Requirement double-counting, invalid trusted-state
  short-circuiting, qualification-gate referential/provenance fail-closed
  behavior, Application Gate/qualification-gate independence);
- proven in a clean GitHub-hosted environment.

This is **assurance debt**, not a reproduced business-logic defect. No prior
audit in this repository's history (`POST_QUALIFICATION_GATE_REAL_MARKET_
BOTTLENECK_AUDIT_V1`, `DEGREE_CREDENTIAL_CANDIDATE_EVIDENCE_ADJUDICATION_V1`,
`SYSTEM_WIDE_TRUST_AND_CONSISTENCY_AUDIT_V1`) reproduced a live employer/
candidate/match/pursuit decision defect traceable to missing assurance
infrastructure; the gap is that current correctness is proven only on one
developer's machine, not independently, repeatably, and automatically.

**Directly observed, current facts (confirmed by direct inspection at HEAD
`cc496a0e456bd2d3dbc01337ed6b54e41bc8ec26`)**:

- Complete-suite verified runtime: **Python 3.14.6**.
- Third-party (non-stdlib, non-local-module) imports across `src/`,
  `tests/`, `scripts/`: exactly **`jsonschema`** and **`referencing`**.
  Every other imported name is either a Python standard-library module or a
  local repository module.
- No `requirements*.txt`, `requirements.in`, `pyproject.toml`, `setup.py`,
  or `Pipfile` exists anywhere in the repository today.
- No `.github/workflows/` directory exists today.
- No `.gitattributes` exists today.
- `tests/*_test.py`: exactly 59 files, matching the "59 standalone test
  scripts" figure carried in `CURRENT_STATE.md`.

### Locked terminology (permanent — do not remove)

**`REPRODUCIBILITY_UNVERIFIED`** — not `REPRODUCIBILITY_BROKEN`. The current
development environment passes every existing check; what has not yet
happened is a clean, second, GitHub-hosted environment reconstructing the
same environment solely from canonical repository-declared dependency data
and reproducing the same results. This ADR exists to close that specific,
narrow gap — not to imply the pipeline is currently unreliable.

## Decision

Adopt the architecture below exactly as converged by
`SYSTEM_WIDE_TRUST_AND_CONSISTENCY_AUDIT_V1` and recorded as
`ASSURANCE_BASELINE_IMPLEMENTATION_READY_AFTER_ARCHITECTURE_CORRECTION`.
This ADR faithfully records that already-adjudicated design; it does not
redesign it.

### 1. Locked purpose

The milestone exists only to make **current approved semantics**:

1. reproducibly installable/reconstructable;
2. executable through one cross-platform canonical verification command;
3. automatically checked in GitHub CI;
4. better protected by the missing P0 causal-integration tests identified
   below;
5. minimally protected against newline/provenance environmental drift.

It must **not** add new Employer/Candidate/Match/Pursuit/Application
semantics.

### 2. Locked bounded implementation surface

Future implementation (not this ADR/pointer step) is bounded to exactly:

- **A. Dependency declaration** — `requirements.in` (human-maintained direct
  dependencies only) and `requirements-lock.txt` (complete resolved
  transitive dependency environment, exact versions).
- **B. Canonical verification runner** — `scripts/verify_assurance_baseline.py`.
- **C. CI** — `.github/workflows/assurance-baseline.yml`.
- **D. P0 causal integration assurance** — `tests/p0_causal_invariants_v1_test.py`.
- **E. Optional narrow newline/provenance test** — only if independently
  necessary and deterministic.
- **F. Minimal documentation** — canonical verification command,
  `analyze_job()`'s actual outer runtime-envelope contract, milestone/state
  bookkeeping.

Any implementation need outside this surface: **STOP AND REPORT** before
expanding scope. This ADR authorizes no implementation itself.

### 3. Dependency architecture

Directly observed direct third-party dependencies today: `jsonschema`,
`referencing`. No dependency is invented beyond what is actually imported.

Locked environment model:

- `requirements.in` = human-maintained direct dependencies only.
- `requirements-lock.txt` = the complete resolved transitive dependency
  environment with exact versions. It must **not** contain only the two
  direct packages if they carry transitive dependencies of their own — a
  partially pinned dependency set must never be labeled reproducible.

Explicitly not selected for V1: Poetry, uv, Hatch, PDM, pip-tools, or any
other package manager (unless implementation discovers a concrete necessity
and separately stops for approval); a `pyproject.toml` `[project]` packaging
conversion; `pylock.toml`; hash-enforced dependency installation (deferred
until clean cross-platform environment reconstruction is first proven). No
fake installable-package architecture is introduced merely to hold
dependency metadata.

### 4. Python version truth

Observed complete-suite runtime is Python 3.14.6. CI must not claim 3.11 or
3.12 support merely from syntax compatibility — **syntax-compatible !=
runtime-verified**. Initial CI target must reproduce the verified runtime
family first: Python 3.14.6, if GitHub's `setup-python` action can
reproducibly provide that exact patch version. If the exact patch is
unavailable on the GitHub runner at implementation time: **STOP AND
REPORT** — do not silently broaden or downgrade the version. Future
compatibility testing on Python 3.12 or any other version is separate,
future work that must independently earn `VERIFIED` status by running the
complete assurance suite; it is not authorized by this ADR.

### 5. Canonical verification command

One command: `python scripts/verify_assurance_baseline.py`. It runs exactly
**three** execution phases, in order.

**Phase 1 — compile/syntax**

```
python -m compileall -q src tests
```

**Phase 2 — standalone repository tests**

Discover all `tests/*_test.py` files and run them in deterministic sorted
(lexicographic filename) order.

The runner MUST fail closed if:

- zero tests are discovered; or
- any mandatory assurance test/suite expected to be part of Phase 2 is
  absent from the discovered set.

The ADR identifies, at minimum, these mandatory Phase-2 coverage anchors
(confirmed present in the repository at ADR authoring time):

- `tests/application_gate_golden_test.py`
- `tests/posting_state_decision_wiring_v1_test.py`
- `tests/alternative_qualification_branch_representation_v1_test.py`
- the existing schema smoke/validation tests (confirmed present:
  `tests/application_schema_smoke_test.py`,
  `tests/claim_schema_smoke_test.py`,
  `tests/evidence_schema_smoke_test.py`,
  `tests/job_schema_smoke_test.py`,
  `tests/requirement_schema_smoke_test.py`,
  `tests/resume_schema_smoke_test.py`)

Application Gate, posting-state, qualification-gate, and schema tests are
**not** separate execution phases — they already execute as members of the
`tests/*_test.py` discovery set in Phase 2. Instead, Phase 2 carries a
**non-executed coverage checklist** (a documentation/verification aid, not
an additional run) stating that the discovered Phase-2 set must cover:

- Application Gate Golden 9/9;
- posting-state regressions;
- qualification-gate regressions;
- existing schema tests.

If a future repository change removes or renames any of the named
mandatory coverage-anchor files without providing an equivalent
replacement discoverable under `tests/*_test.py`, the runner's fail-closed
discovery check (above) is the enforcement mechanism — the checklist itself
does not re-verify file existence at runtime beyond that discovery check.

**Phase 3 — Job Analysis Golden**

```
python golden-tests/run_job_analysis_golden_set.py
```

**Not executed by any phase**: `scripts/generate_job_analysis_golden_fixtures.py`
— that script mutates fixtures and is not assurance.

**Failure semantics (normative)**:

- every child/subprocess failure must propagate as a verification failure;
- the runner must terminate non-zero when any phase fails;
- exit code `0` is permitted only when all three required phases complete
  successfully;
- zero-test discovery in Phase 2 must never produce success.

The runner must be cross-platform Python, not shell-only. It must not rely
on a developer-global `PYTHONPATH`, globally installed undeclared packages,
local caches, or pre-existing `.pyc` files. Normal test failures within
Phase 2 should be collected and summarized where practical, rather than
hiding every remaining failure after the first one; environment/setup
failures (e.g. Phase 1 compile failure, zero-discovery) may fail
immediately without proceeding to later phases.

**P0 coverage clarification**: `tests/p0_causal_invariants_v1_test.py`
(§7) is intended to cover missing **integration-level** causal gaps only.
Existing causal invariants already defended by
`posting_state_decision_wiring_v1_test.py`,
`alternative_qualification_branch_representation_v1_test.py`, and other
existing milestone regression tests remain part of assurance through
Phase 2 and are **not** required to be duplicated in the new P0 file
merely for duplication's sake. In particular, the following remain
preserved by their existing tests, not re-authored: posting-state routing
not rewriting qualification truth; `NONE_TRAP` as the only gated path to
`BLOCKED_BY_MATCHING_POLICY`; `NO_CAPABILITY_OVERLAP`/
`NO_CAPABILITY_COVERAGE` remaining `UNRESOLVED`; missing/unrecognized
`evaluation_path` never becoming favorable.

### 6. CI architecture

One minimal GitHub Actions workflow, `.github/workflows/assurance-baseline.yml`,
triggered on `pull_request` and `push` to `main` only — no deployment/CD.

- Least-privilege workflow permissions.
- Clean GitHub-hosted runner environment.
- Dependency installation only from the canonical dependency lock
  (`requirements-lock.txt`).
- Exact same verification command used locally
  (`python scripts/verify_assurance_baseline.py`).
- GitHub Action dependencies pinned to **verified full commit SHAs**, not
  mutable refs such as `actions/checkout@v7`/`actions/setup-python@v7` —
  comments may record the corresponding official release tag alongside the
  pinned SHA. Before any implementation commit, Action SHA provenance must
  be independently verified against the official GitHub Actions
  repositories/releases; this ADR does not itself select or verify any
  specific SHA.
- No third-party Actions beyond the minimum needed, unless separately
  justified at implementation time.
- No security scanner, CodeQL, Semgrep, mutation testing, coverage tool, or
  architecture linter is bundled into V1.

CI existence is explicitly distinct from branch enforcement: after the
workflow is pushed and proven passing, whether its check becomes a required
status check is a separate, future repository-governance action. Branch
protection/ruleset state remains **`BRANCH_PROTECTION_UNVERIFIED`** and is
unchanged by this ADR.

### 7. P0 causal integration tests

`tests/p0_causal_invariants_v1_test.py` closes only verified integration-level
gaps, at minimum proving:

- **A.** Gated `Requirement` leaves cannot independently re-enter
  `hard_blockers`, mandatory/HIGH-`NONE` counts, `qualification_gaps`, or
  `qualification_unknowns`.
- **B.** Invalid/unavailable trusted Claim or Evidence repository state
  cannot produce or improve a consequential decision.
- **C.** Invalid qualification-gate Requirement references fail before
  consequential decision/routing.
- **D.** Invalid qualification-gate source provenance fails before
  consequential decision/routing.
- **E.** Application Gate truth remains independent from qualification-gate
  result, if testable through existing public interfaces with zero
  production change.

Tests assert causal state, not only a final enum: decision, `hard_blockers`,
`qualification_gate_results`, `evidence_matches`/`evaluation_path`, and the
absence of forbidden causal effects, as relevant per test. Thresholds and
production logic are not rewritten merely to make a test convenient. If a
proposed test exposes a real current production defect, implementation must
**STOP AND REPORT** — not silently fix it inside assurance work.

### 8. Newline / cross-platform boundary

The repository currently has no `.gitattributes`. Qualification-gate source
traceability already normalizes whitespace (per the closed
`ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1` ADR §3). If
implementation confirms the narrow CRLF/LF provenance invariant is useful, a
deterministic regression test may prove equivalent whitespace-normalized
source text remains traceable. No OS test matrix is added merely for
appearance. `.gitattributes` is not added unless a reproduced need is shown
during implementation and separately approved.

### 9. `analyze_job()` outer envelope

Current actual runtime envelope, to be documented (not schema-enforced) by
this milestone:

```
{
  "valid": bool,
  "analysis": dict | None,
  "errors": list,
  "warnings": list,
  "hard_blockers": list[str]
}
```

The inner `analysis` object is already validated against
`job_analysis_result.schema.json`; `hard_blockers` is intentionally outside
that inner schema. V1 may document this runtime contract in prose. No outer
JSON Schema, `TypedDict`, or `mypy` enforcement is authorized merely for
symmetry — that remains deferred unless a real consumer need is reproduced.

### 10. Future pipeline contract preservation (design record only)

The assurance baseline must not implement any of the following stages, but
must not adopt architecture that forecloses them later:

```
analyze_job(Job_ID)
-> pursuit approval
-> generate_resume(Job_ID)
-> application package
-> submission snapshot
-> application tracking
-> follow-up engine
-> outcome learning
```

Carried forward as future product requirements (no implementation in this
milestone):

1. Candidate truth must be versionable where state can change.
2. Generated packages must reference exact Employer/Candidate truth
   versions.
3. Submitted application packages must become immutable historical
   snapshots.
4. Resume factual content must retain Evidence/Claim lineage through
   rendering.
5. Rendered artifacts must eventually be validated, not merely source
   patches.
6. Application-answer reuse must be context/freshness/human-review aware.
7. Follow-up logic must be event/state driven, not universal fixed cadence.
8. New inbound events can supersede pending follow-up actions.
9. Rejected/withdrawn/closed opportunities cancel stale follow-up.
10. External communication remains Bora-controlled.
11. Outcome learning may tune strategy but never weaken truth constraints.
12. Later Candidate updates cannot rewrite historical submission truth.

### 11. Explicit exclusions

Not bundled into this milestone: Master's credential capability/matcher;
Bachelor's abbreviation ("BS"/"B.S."/"BA") parsing; experience-grammar
broadening; global NONE-vs-UNKNOWN remediation; immigration/work-
authorization decision consumer; legal-employer schema redesign; E-Verify/
sponsorship/I-983 policy; Claim creation or approval; Claim-to-capability
wiring; resume generation; package generation; follow-up automation;
networking automation; outcome learning; new pursuit thresholds; role-
discovery changes; employer-market expansion. (These match the deferred/
non-goal items already identified across `POST_QUALIFICATION_GATE_REAL_
MARKET_BOTTLENECK_AUDIT_V1` and `DEGREE_CREDENTIAL_CANDIDATE_EVIDENCE_
ADJUDICATION_V1` — none are reopened here.)

### 12. Canonical continuity / new-chat recovery

This milestone must preserve the project's existing authority model. Future
ChatGPT Work / Claude / Cursor sessions must not recover project state from
conversational memory alone. Before any consequential conclusion or
implementation, canonical state must be recovered, in order, from: (1)
`AGENTS.md`, (2) `BLUEPRINT.md`, (3) `CURRENT_STATE.md`, (4)
`CURRENT_MILESTONE.md`, (5) applicable approved ADRs, (6) applicable tool-
specific rules/instructions, (7) current Git branch/HEAD/origin state, (8)
relevant prior project-chat context only after canonical repo recovery. If
prior conversation text conflicts with current repository state, **current
canonical repository state wins**. A new session should be able to produce
a short recovered-state summary (canonical SHA; current/closed milestone;
active implementation authorization if any; locked architecture decisions;
explicitly deferred/non-goal items; any contradiction requiring
adjudication) without duplicating the entire Blueprint into new handoff
documents. This is a permanent governance property, not scoped to this
milestone alone, but is recorded here because this milestone is explicitly
about assurance/reproducibility of canonical state.

## Why

Smallest reliable choice given the confirmed facts: only two real
third-party dependencies exist, so a lockfile-based (not a new packaging
tool) reproducibility model is proportionate; the existing 59-script/Golden-
suite assurance is already comprehensive in content, so the milestone need
only make it reproducible and automatic, not redesign what it tests; the
one real, currently-uncovered risk class (gated-Requirement double-counting,
invalid-trusted-state short-circuiting, gate referential/provenance
fail-closed behavior, Application Gate independence) is exactly the set of
invariants the two most recent architecture milestones
(`ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1`,
`DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1`) introduced and which no
existing test file was purpose-built to defend as integration-level
invariants (each existing test targets its own milestone's fixtures, not
the cross-cutting causal guarantees as a named, standalone assurance
surface).

## Alternatives Considered

- **Adopt a full packaging tool (Poetry/uv/Hatch/PDM/pip-tools) now.**
  Rejected: only two real third-party dependencies exist today; a lockfile
  pair (`requirements.in`/`requirements-lock.txt`) is the smallest reliable
  mechanism that still satisfies full transitive-dependency reproducibility,
  without introducing a new tool dependency, packaging metadata surface, or
  migration cost this repository has never needed.
- **Skip a dedicated `requirements-lock.txt` and just pin the two direct
  packages.** Rejected: explicitly would falsely label a partially pinned
  dependency set as reproducible if either package carries transitive
  dependencies of its own — the whole point of this milestone.
- **Target a version range (e.g. "3.11+") instead of the exact verified
  patch.** Rejected: syntax-compatibility is not runtime-verification;
  claiming broader support than what has actually been run end-to-end would
  reintroduce exactly the kind of unverified assumption this milestone
  exists to eliminate.
- **Bundle CodeQL/Semgrep/coverage/mutation testing/an architecture linter
  into V1.** Rejected: none of these were requested, none address the
  specific reproducibility gap identified, and each would expand scope
  beyond the locked bounded implementation surface without a reproduced
  need.
- **Make the new CI check a required branch-protection status check as part
  of this milestone.** Rejected: CI existence and branch enforcement are
  different governance actions; enforcing before the workflow is proven
  passing on GitHub would risk blocking merges on an unverified check.
- **Add an OS test matrix or `.gitattributes` preemptively.** Rejected: no
  reproduced cross-platform failure exists yet; adding either now would be
  speculative infrastructure, not a response to a demonstrated need.

## Risks / Tradeoffs

- If GitHub's `setup-python` cannot reproduce the exact Python 3.14.6 patch,
  implementation must stop and report rather than silently substituting a
  nearby version — this could delay closure until GitHub's runner catalog
  catches up, which is an accepted tradeoff for runtime-truth accuracy over
  speed.
- Pinning GitHub Actions to full commit SHAs (rather than mutable tags)
  requires manual provenance verification against upstream releases at
  implementation time and periodic manual review to pick up security
  patches — a deliberate reproducibility/security tradeoff in favor of
  supply-chain determinism.
- The P0 causal integration tests (§7) may, by design, expose a real
  production defect neither prior audit reproduced; if so, implementation
  must stop rather than fix it inline, which could stall this milestone's
  closure pending a separate adjudication — an accepted tradeoff to avoid
  smuggling a business-logic change into an assurance-only milestone.
- Documenting (not schema-enforcing) the `analyze_job()` outer envelope
  leaves it informally, not mechanically, guaranteed — accepted because no
  real external consumer need for formal enforcement has been reproduced.

## Affected Areas

This ADR is a **proposed implementation surface only** — nothing below is
implemented by this ADR/pointer step itself.

- New: `requirements.in`, `requirements-lock.txt`
- New: `scripts/verify_assurance_baseline.py`
- New: `.github/workflows/assurance-baseline.yml`
- New: `tests/p0_causal_invariants_v1_test.py`
- Possibly new: one narrow newline/provenance regression test, only if a
  reproduced need is confirmed during implementation
- Documentation: canonical verification command, `analyze_job()` outer
  envelope contract, milestone/state bookkeeping
- Not modified: any production business-logic module in `src/`, any
  schema, any Claim/Evidence/Experience/résumé record, any existing
  fixture, any existing test file's assertions (existing tests may be
  *run* by the new runner, not rewritten)

## Verification Required

- `python scripts/verify_assurance_baseline.py` exits `0` locally after a
  clean-environment dependency install from `requirements-lock.txt` alone.
- All 59 existing `tests/*_test.py` scripts pass under the canonical
  runner.
- Job Analysis Golden suite: 15/15.
- Application Gate Golden suite: 9/9.
- Posting-state regressions: pass.
- Qualification-gate regressions: pass.
- New `tests/p0_causal_invariants_v1_test.py` (§7, A–E) passes and asserts
  causal state, not only a final enum.
- GitHub-hosted CI (`assurance-baseline.yml`) passes on the exact pushed
  implementation SHA — GitHub itself must execute the workflow
  successfully before this milestone is considered closed; local-only
  passing is not sufficient closure evidence.
- `requirements-lock.txt` contains the full resolved transitive dependency
  set, not only `jsonschema`/`referencing` themselves, unless those two
  packages are independently confirmed to have zero transitive
  dependencies at lock time.
- GitHub Action SHA pins independently verified against official
  Actions-repository releases before the implementation commit.
- No production business semantics changed; no unauthorized scope
  expansion beyond §2's bounded surface.

## Rollback / Reversal

Delete `requirements.in`, `requirements-lock.txt`,
`scripts/verify_assurance_baseline.py`,
`.github/workflows/assurance-baseline.yml`,
`tests/p0_causal_invariants_v1_test.py`, and any narrow newline/provenance
test added under §8. No existing production code, schema, Claim, Evidence,
Experience, résumé record, or fixture depends on any of this — the existing
59 test scripts and Golden suites remain independently runnable exactly as
they are today, with or without the new runner/CI wrapper around them.

## Non-Goals

No new Employer/Candidate/Match/Pursuit/Application semantics. No Master's
credential capability/matcher. No Bachelor's-abbreviation parsing. No
experience-grammar broadening. No global NONE-vs-UNKNOWN remediation. No
immigration/work-authorization decision consumer. No legal-employer schema
redesign. No E-Verify/sponsorship/I-983 policy. No Claim creation, approval,
or Claim-to-capability wiring. No resume/package generation. No follow-up
or networking automation. No outcome learning. No new pursuit thresholds.
No role-discovery changes. No employer-market expansion. No security
scanner/CodeQL/Semgrep/mutation-testing/coverage/architecture-linter
bundling. No branch-protection/required-status-check change. No OS test
matrix. No `.gitattributes` addition absent a reproduced need. No packaging-
tool adoption (Poetry/uv/Hatch/PDM/pip-tools) absent a reproduced necessity.
No `pyproject.toml` `[project]` conversion. No `pylock.toml`. No
hash-enforced dependency installation in V1.
