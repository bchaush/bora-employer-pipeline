# ADR-CAREER-OS-BOUNDED-AGENT-BUILD-LOOP-V1 — Bounded Local Milestone Controller

Status: Proposed (pending independent Cursor adversarial review + Bora approval)
Date: 2026-09-07
Approved by: Pending

## Context

Every Career OS engineering milestone so far has been driven by a human
(Bora) issuing a G-prompt per phase (implement, correct, review-handoff,
commit, push, PR) to a Claude Code session, with Cursor invoked
separately as adversarial reviewer. This works but requires Bora's
continuous presence and re-derivation of context on every turn. The
prior `CANONICAL_STATE_RECOVERY_AND_MILESTONE_CONTRACT_V1` audit and
`CAREER_OS_MILESTONE_CONTRACT_AND_STATE_VALIDATION_V1` implementation
established the missing piece for state continuity (`project_state.json`,
branch-scoped milestone contracts, `scripts/verify_milestone_state.py`).
This milestone builds the next piece: a local controller that can drive
ONE already-authorized milestone through build/test/review/assurance
without requiring Bora (or any single Claude/Cursor conversation) to
stay alive for the whole duration.

## Decision

Build `src/milestone_run.py` (a pure, dependency-injected state-machine
core) and `scripts/career_os_milestone.py` (a thin CLI wrapping it with
real Claude Code / Cursor Agent CLI adapters). The controller:

- Recomputes Git/GitHub reality on every `run`/`resume` call, never
  trusting a persisted manifest's historical claims (`revalidate_run()`).
- Persists durable run state under a gitignored `.career-os/runs/<run_id>/`
  directory via atomic file replacement (`os.replace`), with an explicit,
  fail-closed 11-phase state machine (`TRANSITIONS`) that raises
  `InvalidTransitionError` on any transition not explicitly listed.
- Uses an OS-level atomic-exclusive-create lock
  (`os.open(..., O_CREAT|O_EXCL)`) keyed to the governed branch, with
  explicit, human-invoked (`--recover-stale-lock`), archive-not-delete
  stale-lock recovery.
- Invalidates test/review evidence via a content-addressable diff
  fingerprint (`compute_diff_fingerprint`) covering both tracked changes
  since baseline and untracked file content — any working-tree mutation
  after a PASS forces a fresh re-check, never a stale reuse.
- Separates authority strictly: the builder (Claude Code, `-p
  --output-format json`) can only report an attempt status; deterministic
  tests decide test pass/fail; the reviewer (Cursor Agent CLI, `-p
  --mode ask --trust`) decides reviewer outcome only; canonical
  `scripts/verify_assurance_baseline.py` (unmodified, invoked as a
  subprocess, never duplicated) decides assurance; the controller only
  transitions phase when that phase's required evidence exists; Bora is
  the sole human approver, and V1 never commits/pushes/opens a
  PR/merges.
- Retry/timeout tuning lives in `config/milestone_execution_policy_v1.json`
  (separately versioned, snapshotted+hashed per run), never in the
  milestone contract itself, which defines only WHAT is authorized.

## Why

This is the smallest reliable design that satisfies the contract's own
acceptance conditions without inventing distributed locking, a database,
a web server, or a generic orchestration framework. Reusing
`career_os_state.validate_changed_paths()` (already-tested canonical
scope/protected-path machinery) for scope enforcement avoids a second,
divergent definition of "authorized path." Making test/assurance
execution injectable (`Adapters.test_runner`/`assurance_runner`), not
only the builder/reviewer, let the entire state machine be exercised
deterministically in `tests/milestone_run_v1_test.py` with zero live
provider/network dependency, per the contract's own explicit requirement.

## Alternatives Considered

- A single monolithic `run()` loop invoking providers inline with no
  phase-by-phase persistence — rejected: not restart-safe: a crash
  mid-attempt would lose all context about what had already happened.
- Storing the current canonical Git SHA in `project_state.json` for
  cross-checking — rejected per the prior milestone's own explicit,
  reaffirmed constraint (self-invalidating the instant such a file
  merges); this controller's own run manifests live outside `main`
  entirely (`.career-os/`, gitignored), so the concern does not even
  apply to them, but the principle is preserved consistently.
- OS-level sandboxing (`agent --sandbox enabled`) as the sole reviewer
  safety boundary — empirically unavailable on this Windows machine
  (Cursor Agent CLI: "Sandbox requires macOS or Linux"). The reviewer
  boundary instead relies on `--mode ask` (empirically verified
  structurally enforced: an adversarial "please write this file" prompt
  under `--mode ask` was refused by the CLI itself, confirmed via
  `git status`/`git diff` showing zero mutation) plus the controller's
  own before/after diff-fingerprint verification as the deterministic
  backstop.
- A distributed/multi-machine lock — rejected as explicitly out of scope
  (V1 is single-machine, single-collaborator).

## Risks / Tradeoffs

- **Sandbox unavailable on Windows.** The reviewer boundary's primary
  enforcement is `--mode ask` (verified structurally, not merely
  documented) plus post-hoc diff verification, not OS sandboxing. On a
  macOS/Linux machine, `--sandbox enabled` could be added as an
  additional layer; V1 does not attempt this since it cannot be
  exercised or verified on the actual development machine.
- **Provider output is not guaranteed pure JSON.** Empirically, the
  Cursor Agent CLI prepended prose before its JSON object despite
  explicit instructions. `_extract_json()` performs lenient
  balanced-brace extraction rather than assuming `json.loads` on raw
  output succeeds outright.
- **One phase per `advance()` call, by design.** A single `run()`/`resume()`
  call performs many `advance()` iterations internally (bounded by
  `max_steps`), but each iteration does exactly one phase's unit of work
  before persisting. This is intentionally conservative (a crash mid-phase
  never loses more than one phase's progress) at the cost of more
  subprocess invocations than a coarser design.
- **Reviewer identity, not just merge state.** (Carried over, LOW,
  intentionally deferred per this milestone's own explicit instruction —
  see below.)

## Affected Areas

- `.gitignore` (additive `.career-os/` entry)
- `config/milestone_execution_policy_v1.json` (new)
- `prompts/milestone_builder_v1.md`, `prompts/milestone_reviewer_v1.md` (new)
- `schemas/milestone_run.schema.json`, `schemas/milestone_reviewer_result.schema.json` (new)
- `src/milestone_run.py` (new)
- `scripts/career_os_milestone.py` (new)
- `tests/milestone_run_v1_test.py` (new)
- `milestone_contracts/feature/career-os-bounded-agent-build-loop-v1.json` (new, this milestone's own governing contract)

## Verification Required

`tests/milestone_run_v1_test.py` (27 sections against disposable real
git repositories, all provider invocations faked); `tests/career_os_state_v1_test.py`
(unaffected, still green); `python scripts/verify_milestone_state.py`
(this branch's own diff validated against its own contract);
`python scripts/verify_assurance_baseline.py` (ALL PHASES PASSED,
including the new test file auto-discovered by Phase 2); `git diff --check`
clean; manual verification that no file outside `allowed_paths` changed
and no forbidden path was touched.

## Known, explicitly deferred limitations (per this milestone's own instruction)

1. **PR/milestone identity verification** — `career_os_state.verify_github_milestone_state()`
   (from the prior milestone, unmodified, forbidden path) checks only
   that a recorded PR number is `MERGED`, not that its title/content
   actually corresponds to the claimed milestone. Not addressed here;
   V1 never reaches PR creation at all.
2. **Local-main fetch discipline** — the controller fetches `origin/main`
   itself on every `compute_repo_facts()` call, closing the specific gap
   that caused a real incident earlier in this session (a stale local
   `main` ref), but still assumes the caller's git remote configuration
   itself is correct (a real `origin` pointing at the canonical GitHub
   repository).

## Rollback / Reversal

Revert the commit. Every file listed under Affected Areas is additive;
none modifies existing forbidden-path files. `.career-os/` is gitignored
and per-machine, so no committed state needs cleanup on rollback.
