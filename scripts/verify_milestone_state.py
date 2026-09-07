"""career-os milestone check -- CAREER_OS_MILESTONE_CONTRACT_AND_STATE_VALIDATION_V1.

Usage:
    python scripts/verify_milestone_state.py            # local, deterministic, offline
    python scripts/verify_milestone_state.py --online   # also verify GitHub PR-merge state

Runs the deterministic local state/milestone-contract checks in
src/career_os_state.py (see that module's docstring for the full
authority-hierarchy and protected-path design). Local mode never touches
the network and never invokes an AI builder. --online additionally
confirms project_state.json's latest_closed_milestone_pr is actually
MERGED on GitHub (via the gh CLI) -- kept as an explicit, separate,
opt-in mode so ordinary/CI runs stay fully offline and so GitHub Actions
never recursively depends on calling back out to GitHub from inside its
own run.

Exit code 0 only when every requested check passes.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from career_os_state import (  # noqa: E402
    run_local_state_checks,
    validate_project_state,
    verify_github_milestone_state,
)


def main(argv: list[str]) -> int:
    online = "--online" in argv

    print("=== career-os milestone check: local state validation ===")
    result = run_local_state_checks(root=ROOT)
    if result["errors"]:
        for error in result["errors"]:
            print(f"FAIL {error}")
    if not result["valid"]:
        print("Local state validation FAILED.")
        return 1
    print("Local state validation PASSED.")

    if online:
        print("=== career-os milestone check: GitHub online verification ===")
        state_result = validate_project_state(root=ROOT)
        state = state_result.get("state")
        if not isinstance(state, dict):
            print("FAIL: project_state.json could not be loaded for online verification.")
            return 1
        github_result = verify_github_milestone_state(state)
        if github_result["errors"]:
            for error in github_result["errors"]:
                print(f"FAIL {error}")
        if not github_result["valid"]:
            print("GitHub online verification FAILED.")
            return 1
        print("GitHub online verification PASSED.")

    print("\nMilestone/state check PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
