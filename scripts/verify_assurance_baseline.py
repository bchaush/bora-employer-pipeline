"""Canonical assurance verification runner.

REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_BASELINE_V1, per
docs/decisions/ADR-REPRODUCIBLE-CONSEQUENTIAL-ASSURANCE-BASELINE-V1.md §5.

Usage:
    python scripts/verify_assurance_baseline.py

Runs exactly three execution phases, in order:

  Phase 1 -- compile/syntax check (equivalent to
             `python -m compileall -q src tests`).
  Phase 2 -- discover and run all tests/*_test.py in deterministic sorted
             (lexicographic filename) order. Fails closed if zero tests
             are discovered, or if any mandatory assurance coverage
             anchor named below is absent from the discovered set.
             Application Gate Golden, posting-state, qualification-gate,
             and schema tests are NOT separate execution phases -- they
             already run as members of this Phase 2 discovery set (see
             the non-executed coverage checklist below).
  Phase 3 -- Job Analysis Golden runner (equivalent to
             `python golden-tests/run_job_analysis_golden_set.py`).

`scripts/generate_job_analysis_golden_fixtures.py` is deliberately never
executed by any phase -- it mutates fixtures and is not assurance.

Failure semantics (normative, ADR §5):
  - every child/subprocess failure propagates as a verification failure;
  - the runner terminates non-zero when any phase fails;
  - exit code 0 is permitted only when all three required phases succeed;
  - zero-test discovery in Phase 2 never produces success.

Cross-platform Python only -- no shell dependence, no reliance on a
developer-global PYTHONPATH, globally installed undeclared packages, local
caches, or pre-existing .pyc files (subprocess invocations use `-B` to
avoid writing/relying on bytecode caches for Phase 2/3 execution).

Non-executed coverage checklist (documentation aid only -- Phase 2's
fail-closed discovery/anchor check above is the actual enforcement
mechanism; the historical count of 59 discovered tests at ADR-authoring
time is descriptive only, never a hard-coded equality-to-59 success
condition -- legitimate future tests are discovered and run automatically):
  - Application Gate Golden 9/9 (tests/application_gate_golden_test.py)
  - posting-state regressions (tests/posting_state_decision_wiring_v1_test.py)
  - qualification-gate regressions
    (tests/alternative_qualification_branch_representation_v1_test.py)
  - existing schema tests (tests/*_schema_smoke_test.py)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
TESTS_DIR = ROOT / "tests"
GOLDEN_RUNNER = ROOT / "golden-tests" / "run_job_analysis_golden_set.py"

# Mandatory Phase-2 coverage anchors (ADR §5). If any of these is absent
# from the discovered tests/*_test.py set, Phase 2 fails closed before
# running anything -- this is an environment/setup-style failure, not an
# ordinary test failure.
MANDATORY_PHASE_2_ANCHORS: tuple[str, ...] = (
    "application_gate_golden_test.py",
    "posting_state_decision_wiring_v1_test.py",
    "alternative_qualification_branch_representation_v1_test.py",
    "application_schema_smoke_test.py",
    "claim_schema_smoke_test.py",
    "evidence_schema_smoke_test.py",
    "job_schema_smoke_test.py",
    "requirement_schema_smoke_test.py",
    "resume_schema_smoke_test.py",
)


def _run(cmd: list[str], *, label: str) -> tuple[bool, str]:
    """Run one subprocess to completion; never raises. Returns (ok, output)."""
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except Exception as exc:  # noqa: BLE001 -- any spawn/timeout failure is a verification failure
        return False, f"{label}: failed to execute subprocess: {exc!r}"
    output = (completed.stdout or "") + (completed.stderr or "")
    ok = completed.returncode == 0
    return ok, output


def phase_1_compile() -> bool:
    print("=== Phase 1: compile/syntax check ===")
    ok, output = _run(
        [sys.executable, "-m", "compileall", "-q", str(SRC_DIR), str(TESTS_DIR)],
        label="Phase 1 (compileall)",
    )
    if output.strip():
        print(output)
    if not ok:
        print("Phase 1 FAILED: compile/syntax check did not pass.")
        return False
    print("Phase 1 PASSED.")
    return True


def _discover_tests() -> list[Path]:
    return sorted(TESTS_DIR.glob("*_test.py"), key=lambda p: p.name)


def phase_2_tests() -> bool:
    print("=== Phase 2: standalone repository tests (tests/*_test.py) ===")
    discovered = _discover_tests()
    if not discovered:
        print("Phase 2 FAILED: zero tests discovered under tests/*_test.py.")
        return False

    discovered_names = {p.name for p in discovered}
    missing_anchors = [a for a in MANDATORY_PHASE_2_ANCHORS if a not in discovered_names]
    if missing_anchors:
        print(
            "Phase 2 FAILED: mandatory assurance coverage anchor(s) absent "
            f"from the discovered set: {missing_anchors}"
        )
        return False

    print(f"Discovered {len(discovered)} test file(s); all mandatory coverage anchors present.")

    failures: list[tuple[str, str]] = []
    for test_path in discovered:
        ok, output = _run(
            [sys.executable, "-B", str(test_path)],
            label=test_path.name,
        )
        if ok:
            print(f"PASS {test_path.name}")
        else:
            print(f"FAIL {test_path.name}")
            failures.append((test_path.name, output))

    if failures:
        print("\n=== Phase 2 FAILURE SUMMARY ===")
        for name, output in failures:
            print(f"--- {name} ---")
            print(output.strip())
        print(f"Phase 2 FAILED: {len(failures)}/{len(discovered)} test file(s) failed.")
        return False

    print(f"Phase 2 PASSED: {len(discovered)}/{len(discovered)} test file(s) passed.")
    return True


def phase_3_job_analysis_golden() -> bool:
    print("=== Phase 3: Job Analysis Golden runner ===")
    if not GOLDEN_RUNNER.exists():
        print(f"Phase 3 FAILED: golden runner not found at {GOLDEN_RUNNER}")
        return False
    ok, output = _run(
        [sys.executable, "-B", str(GOLDEN_RUNNER)],
        label="Phase 3 (Job Analysis Golden)",
    )
    if output.strip():
        print(output)
    if not ok:
        print("Phase 3 FAILED.")
        return False
    print("Phase 3 PASSED.")
    return True


def main() -> int:
    if not phase_1_compile():
        return 1
    if not phase_2_tests():
        return 1
    if not phase_3_job_analysis_golden():
        return 1
    print("\nALL PHASES PASSED: canonical assurance baseline verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
