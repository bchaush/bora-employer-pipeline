# ADR-CAREER-OS-MILESTONE-CONTRACT-AND-STATE-VALIDATION-V1 — Canonical Semantic State and Milestone Contract Architecture

Status: Approved
Date: 2026-09-07
Approved by: Bora (via bounded implementation authorization)

## Context

`CANONICAL_STATE_RECOVERY_AND_MILESTONE_CONTRACT_V1` (read-only architecture
audit) reproduced a real, mechanically-undetectable state-continuity
defect: `CURRENT_STATE.md` declared "Final Locked Blueprint v3.8" while
canonical `BLUEPRINT.md` was already v3.10 (missing Sections 137 and 138),
and `CURRENT_MILESTONE.md`'s top pointer was ten pull requests behind
canonical `main` (PR #7 vs PR #17). A near-identical drift had already
been manually corrected once before
(`POST_GOVERNANCE_CANONICAL_STATE_CONTINUITY_SYNC_V1`, PR #8,
2026-09-03) and recurred anyway, because `.cursor/rules/architecture.mdc`'s
own "State Changes" rule (update `CURRENT_STATE.md` on material change)
is enforced only by an implementing agent's memory each session, with no
deterministic backstop -- exactly the kind of prompt-only enforcement the
same file's "Deterministic Boundary" section says to avoid.

## Decision

Add the smallest deterministic local validator (`src/career_os_state.py`,
`scripts/verify_milestone_state.py`) plus two small artifacts it checks:

1. `project_state.json` (root) -- canonical MERGED semantic state only
   (Blueprint version, latest locked section number, latest closed
   milestone id/PR, current phase, next authorized action, last-updated
   date). Contains no current Git SHA and no transient active-milestone/
   branch field. `next_authorized_action` specifically MUST describe
   durable canonical-main authorization state only -- e.g. "no product
   implementation milestone is currently preselected" -- and must remain
   true after this very file's own merge; it must never describe a
   milestone as "in progress" (that is branch/contract state, not
   canonical-main state) and must never silently pre-authorize a future
   milestone that has not been separately, explicitly approved. Enforced
   by description text in `schemas/project_state.schema.json` (not a new
   runtime enum -- free text remains the smallest reliable
   representation; nothing here is mechanically parseable as a semantic
   claim beyond the version/section cross-checks already implemented).
2. A branch-scoped milestone contract at
   `milestone_contracts/<branch-name>.json`, authorizing one bounded
   milestone's `allowed_paths`/`forbidden_paths`/`baseline_sha`/etc.

`scripts/verify_assurance_baseline.py` gains a new Phase 0 that checks
`project_state.json`'s claims against actual `BLUEPRINT.md` content
(offline, no git-history dependency). The fuller branch/contract/path
check (`career_os_state.run_local_state_checks`) is exposed only through
`scripts/verify_milestone_state.py`, intended for local/developer/agent
use with full git history, not folded into the CI-run Assurance Baseline.

## Why

This is the smallest reliable choice that closes the reproduced defect
without inventing an autonomous builder loop, a new Truth-layer schema,
or a provider-integration surface (all explicitly out of scope). Reusing
the existing `jsonschema`/`build_draft202012_validator` infrastructure
(already a dependency, already the repo's schema-validation convention)
avoids adding anything new to `requirements.in`. Keeping the state file
free of any current SHA avoids a self-referential-invalidation trap (a
committed file cannot honestly describe the exact commit it is itself
part of); keeping active-milestone state on a branch-scoped contract
file, not the canonical-main state file, avoids conflating "what main
currently, durably is" with "what is in progress on some branch."

## Alternatives Considered

- Fold the full branch/contract check into the CI-run Assurance Baseline
  Phase 0 -- rejected: this workflow's checkout uses the default shallow,
  single-ref fetch (no `fetch-depth: 0`), under which `main` is not
  necessarily locally resolvable from an arbitrary PR checkout, so a
  merge-base-dependent check there would be flaky and could misleadingly
  imply enforcement this exact CI environment cannot reliably back up.
- Store the current canonical SHA inside `project_state.json` for a
  stronger self-check -- rejected per the milestone's own explicit
  constraint: unstable/self-invalidating the moment the file merges.
- Discover milestone contracts repository-wide (scan all branches) --
  rejected as broader than V1 needs; the reproduced defect and its fix
  are both about the CURRENT branch/session, not a repository-wide audit.
- A repository-wide `career-os` CLI framework -- rejected; a single
  focused script is the smallest reliable surface for this milestone.

## Risks / Tradeoffs

- `project_state.json` will itself go stale by exactly one PR immediately
  after this milestone's own merge (it cannot honestly describe its own
  future PR number in advance) -- a known, bounded, one-PR staleness
  window, not the unbounded drift the audit found; a trivial follow-up
  touch closes it.
- The full branch/contract check depends on git history being present
  locally (merge-base resolvable against `main`); this is always true for
  a real developer/agent working checkout but not for a shallow CI clone
  -- addressed by deliberately not running that fuller check inside CI in
  V1 (see Why).
- Protected-path detection is a fixed, hand-maintained list (Tier A/B
  surfaces); a newly added Truth-layer file would need a corresponding
  addition to `PROTECTED_SRC_FILES` to stay covered.

## Affected Areas

- `project_state.json` (new)
- `schemas/project_state.schema.json`, `schemas/milestone_contract.schema.json` (new)
- `src/career_os_state.py` (new)
- `scripts/verify_milestone_state.py` (new)
- `scripts/verify_assurance_baseline.py` (new Phase 0)
- `milestone_contracts/feature/career-os-milestone-contract-and-state-validation-v1.json` (new, this milestone's own dogfooded contract)
- `tests/career_os_state_v1_test.py` (new)
- `CURRENT_STATE.md`, `CURRENT_MILESTONE.md` (smallest catch-up + authority-demotion note)
- `CHANGELOG.md` (new entry)

## Verification Required

`tests/career_os_state_v1_test.py` (13 sections, including two regression
sections added after real bugs were found dogfooding this checker against
the actual repository); `python scripts/verify_milestone_state.py` exits
0 against this milestone's own contract; `python
scripts/verify_assurance_baseline.py` reports ALL PHASES PASSED including
the new Phase 0; existing recruiter-threshold and résumé test suites
unchanged and green; `git diff --check` clean.

## Rollback / Reversal

Revert the commit. `project_state.json`, the two new schemas, the new
`src/career_os_state.py`/`scripts/verify_milestone_state.py`, and the
`milestone_contracts/` directory are all additive and independently
removable; the `scripts/verify_assurance_baseline.py` Phase 0 addition is
a single self-contained function plus one call site, cleanly revertible
without affecting Phases 1-3. `CURRENT_STATE.md`/`CURRENT_MILESTONE.md`
catch-up edits are additive prose (a new note plus a new top block); no
existing historical text is deleted or rewritten.
