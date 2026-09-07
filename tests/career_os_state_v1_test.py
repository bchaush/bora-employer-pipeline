"""Regression tests for CAREER_OS_MILESTONE_CONTRACT_AND_STATE_VALIDATION_V1.

Root cause reproduced live (CANONICAL_STATE_RECOVERY_AND_MILESTONE_CONTRACT_V1
read-only audit): CURRENT_STATE.md declared "Final Locked Blueprint v3.8"
while canonical BLUEPRINT.md was already v3.10 (missing Sections 137 and
138), and CURRENT_MILESTONE.md's top pointer was ten pull requests behind
canonical main -- with no mechanical check anywhere in the repository
capable of detecting either drift.

src/career_os_state.py closes this gap with a pure, deterministic, local
validator. These tests build small, disposable, real git repositories
under a temp directory (never the actual project repo) so branch/
merge-base/diff logic is exercised against real Git behavior rather than
mocked -- consistent with `.cursor/rules/testing.mdc`'s preference for a
deterministic fixture over a live external service (a local temp git
repo is neither).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import career_os_state as cos  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def has_code(errors: list[dict], code: str) -> bool:
    return any(e.get("code") == code for e in errors)


# ----------------------------------------------------------------------
# Disposable real-git-repo fixture helpers.
# ----------------------------------------------------------------------

VALID_STATE = {
    "blueprint_version": "3.10",
    "latest_locked_section": 138,
    "latest_closed_milestone_id": "TEST_MILESTONE",
    "latest_closed_milestone_pr": 1,
    "current_phase": "TEST_PHASE",
    "next_authorized_action": "TEST_ACTION",
    "semantic_state_updated_at": "2026-09-07",
}

BLUEPRINT_TEXT = (
    "**BORA EMPLOYER PIPELINE OS**\n\n"
    "**Final Locked Blueprint v3.10**\n\n"
    "**1. FIRST SECTION**\n\nBody.\n\n"
    "**137. SOME SECTION**\n\nBody.\n\n"
    "**138. LATEST SECTION**\n\nBody.\n"
)


def _git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=check
    )


def _init_repo(root: Path) -> None:
    _git(["init", "-q", "-b", "main"], root)
    _git(["config", "user.email", "test@example.com"], root)
    _git(["config", "user.name", "Test"], root)


def _write(root: Path, rel_path: str, content: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(root: Path, message: str) -> str:
    _git(["add", "-A"], root)
    _git(["commit", "-q", "-m", message], root)
    return _git(["rev-parse", "HEAD"], root).stdout.strip()


def _write_state(root: Path, **overrides) -> None:
    state = dict(VALID_STATE)
    state.update(overrides)
    _write(root, "project_state.json", json.dumps(state))


def _base_repo(tmp_root: Path, *, state_overrides: dict | None = None) -> str:
    """A committed main branch with a valid BLUEPRINT.md + project_state.json.
    Returns the commit SHA."""
    _init_repo(tmp_root)
    _write(tmp_root, "BLUEPRINT.md", BLUEPRINT_TEXT)
    _write_state(tmp_root, **(state_overrides or {}))
    return _commit(tmp_root, "initial")


def _with_tmp_repo(fn) -> None:
    tmp_dir = tempfile.mkdtemp(prefix="career_os_state_test_")
    try:
        fn(Path(tmp_dir))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ======================================================================
# 1. Stale Blueprint version -> FAIL (STATE_BLUEPRINT_VERSION_MISMATCH).
# ======================================================================
def _test_1(root: Path) -> None:
    _base_repo(root, state_overrides={"blueprint_version": "3.8"})
    result = cos.validate_project_state(root=root)
    assert_true(result["valid"] is False, "stale Blueprint version (3.8 vs real 3.10) must fail")
    assert_true(
        has_code(result["errors"], "STATE_BLUEPRINT_VERSION_MISMATCH"),
        f"expected STATE_BLUEPRINT_VERSION_MISMATCH, got {result['errors']}",
    )


_with_tmp_repo(_test_1)
print("PASS 1: stale declared blueprint_version (3.8) vs real BLUEPRINT.md (3.10) fails with STATE_BLUEPRINT_VERSION_MISMATCH.")


# ======================================================================
# 2. latest_locked_section says 136 while Section 138 exists -> FAIL
# (STATE_LATEST_SECTION_MISMATCH).
# ======================================================================
def _test_2(root: Path) -> None:
    _base_repo(root, state_overrides={"latest_locked_section": 136})
    result = cos.validate_project_state(root=root)
    assert_true(result["valid"] is False, "stale latest_locked_section (136) while Section 138 exists must fail")
    assert_true(
        has_code(result["errors"], "STATE_LATEST_SECTION_MISMATCH"),
        f"expected STATE_LATEST_SECTION_MISMATCH, got {result['errors']}",
    )


_with_tmp_repo(_test_2)
print("PASS 2: declared latest_locked_section=136 while BLUEPRINT.md's highest heading is 138 fails with STATE_LATEST_SECTION_MISMATCH.")


# ======================================================================
# 3. Malformed project_state.json -> FAIL CLOSED (STATE_FILE_MALFORMED),
# both for invalid JSON and for a missing required field.
# ======================================================================
def _test_3a(root: Path) -> None:
    _init_repo(root)
    _write(root, "BLUEPRINT.md", BLUEPRINT_TEXT)
    _write(root, "project_state.json", "{not valid json")
    _commit(root, "initial")
    result = cos.validate_project_state(root=root)
    assert_true(result["valid"] is False, "invalid JSON must fail closed")
    assert_true(has_code(result["errors"], "STATE_FILE_MALFORMED"), f"got {result['errors']}")


def _test_3b(root: Path) -> None:
    _init_repo(root)
    _write(root, "BLUEPRINT.md", BLUEPRINT_TEXT)
    incomplete = dict(VALID_STATE)
    del incomplete["blueprint_version"]
    _write(root, "project_state.json", json.dumps(incomplete))
    _commit(root, "initial")
    result = cos.validate_project_state(root=root)
    assert_true(result["valid"] is False, "missing required field must fail closed")
    assert_true(has_code(result["errors"], "STATE_FILE_MALFORMED"), f"got {result['errors']}")


_with_tmp_repo(_test_3a)
_with_tmp_repo(_test_3b)
print("PASS 3: malformed project_state.json (invalid JSON, and a missing required field) both fail closed with STATE_FILE_MALFORMED.")


# ======================================================================
# 4. Non-main current milestone branch, ahead of main, with no valid
# contract -> FAIL (STATE_MILESTONE_CONTRACT_MISSING).
# ======================================================================
def _test_4(root: Path) -> None:
    _base_repo(root)
    _git(["checkout", "-q", "-b", "feature/no-contract"], root)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "add thing")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "milestone branch ahead of main with no contract must fail")
    assert_true(
        has_code(result["errors"], "STATE_MILESTONE_CONTRACT_MISSING"),
        f"expected STATE_MILESTONE_CONTRACT_MISSING, got {result['errors']}",
    )


_with_tmp_repo(_test_4)
print("PASS 4: a non-main branch with commits ahead of main and no milestone_contracts/<branch>.json fails with STATE_MILESTONE_CONTRACT_MISSING.")


# ======================================================================
# 5. Contract baseline_sha disagrees with the actual authorized
# merge-base -> FAIL (STATE_MILESTONE_CONTRACT_BASELINE_MISMATCH).
# ======================================================================
def _test_5(root: Path) -> None:
    _base_repo(root)
    branch = "feature/bad-baseline"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": "0" * 40,
        "allowed_paths": ["src/thing.py", f"milestone_contracts/{branch}.json"],
        "forbidden_paths": [],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "add thing + wrong-baseline contract")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "a contract whose baseline_sha is not the real merge-base must fail")
    assert_true(
        has_code(result["errors"], "STATE_MILESTONE_CONTRACT_BASELINE_MISMATCH"),
        f"expected STATE_MILESTONE_CONTRACT_BASELINE_MISMATCH, got {result['errors']}",
    )


_with_tmp_repo(_test_5)
print("PASS 5: a milestone contract whose baseline_sha does not equal the branch's actual merge-base with main fails with STATE_MILESTONE_CONTRACT_BASELINE_MISMATCH.")


# ======================================================================
# 6. A changed file outside allowed_paths -> FAIL (STATE_PATH_NOT_ALLOWED).
# ======================================================================
def _test_6(root: Path) -> None:
    base_sha = _base_repo(root)
    branch = "feature/out-of-scope"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": base_sha,
        "allowed_paths": [f"milestone_contracts/{branch}.json"],
        "forbidden_paths": [],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _write(root, "src/unauthorized_thing.py", "x = 1\n")
    _commit(root, "add contract + out-of-scope file")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "a changed file outside allowed_paths must fail")
    assert_true(
        has_code(result["errors"], "STATE_PATH_NOT_ALLOWED"),
        f"expected STATE_PATH_NOT_ALLOWED, got {result['errors']}",
    )


_with_tmp_repo(_test_6)
print("PASS 6: a changed file not matched by any allowed_paths glob fails with STATE_PATH_NOT_ALLOWED.")


# ======================================================================
# 7. A protected constitutional file changed without EXACT explicit
# authorization -> FAIL (STATE_PROTECTED_PATH_UNAUTHORIZED), even when a
# broad wildcard in allowed_paths would otherwise match it.
# ======================================================================
def _test_7(root: Path) -> None:
    base_sha = _base_repo(root)
    branch = "feature/protected-file"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": base_sha,
        # Deliberately broad wildcard -- must NOT be sufficient to
        # authorize a protected constitutional file.
        "allowed_paths": ["*", f"milestone_contracts/{branch}.json"],
        "forbidden_paths": [],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _write(root, "BLUEPRINT.md", BLUEPRINT_TEXT + "\nUnauthorized edit.\n")
    _commit(root, "add contract + unauthorized BLUEPRINT.md edit")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "an unauthorized change to a protected constitutional file must fail even under a broad wildcard")
    assert_true(
        has_code(result["errors"], "STATE_PROTECTED_PATH_UNAUTHORIZED"),
        f"expected STATE_PROTECTED_PATH_UNAUTHORIZED, got {result['errors']}",
    )


_with_tmp_repo(_test_7)
print("PASS 7: an unauthorized change to a protected constitutional file (BLUEPRINT.md) fails with STATE_PROTECTED_PATH_UNAUTHORIZED even though a broad '*' wildcard is present in allowed_paths.")


# ======================================================================
# 8. Modifying an EXISTING test file without authorization -> FAIL
# (STATE_EXISTING_TEST_MODIFIED_UNAUTHORIZED); adding a brand-new test
# file remains ordinary allowed work.
# ======================================================================
def _test_8(root: Path) -> None:
    _init_repo(root)
    _write(root, "BLUEPRINT.md", BLUEPRINT_TEXT)
    _write_state(root)
    _write(root, "tests/existing_test.py", "print('PASS existing')\n")
    base_sha = _commit(root, "initial with existing test")
    branch = "feature/modify-existing-test"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": base_sha,
        "allowed_paths": ["tests/*_test.py", f"milestone_contracts/{branch}.json"],
        "forbidden_paths": [],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _write(root, "tests/existing_test.py", "print('MODIFIED')\n")
    _write(root, "tests/brand_new_test.py", "print('PASS new')\n")
    _commit(root, "modify existing test + add new test")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "modifying an existing test file without explicit authorization must fail")
    assert_true(
        has_code(result["errors"], "STATE_EXISTING_TEST_MODIFIED_UNAUTHORIZED"),
        f"expected STATE_EXISTING_TEST_MODIFIED_UNAUTHORIZED, got {result['errors']}",
    )
    assert_true(
        not any(e.get("path") == "tests/brand_new_test.py" for e in result["errors"]),
        "adding a brand-new test file must never itself be flagged as unauthorized",
    )


_with_tmp_repo(_test_8)
print("PASS 8: modifying an existing test file without explicit contract authorization fails with STATE_EXISTING_TEST_MODIFIED_UNAUTHORIZED, while adding a brand-new test file in the same diff is unaffected.")


# ======================================================================
# 9. Clean canonical main state, no active contract -> PASS.
# ======================================================================
def _test_9(root: Path) -> None:
    _base_repo(root)
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is True, f"clean main checkout with no active milestone must pass, got {result['errors']}")


_with_tmp_repo(_test_9)
print("PASS 9: a clean main checkout with a correct project_state.json and no active milestone contract passes.")


# ======================================================================
# 10. Valid feature milestone, valid contract, fully in-scope diff -> PASS.
# ======================================================================
def _test_10(root: Path) -> None:
    base_sha = _base_repo(root)
    branch = "feature/valid-milestone"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST_VALID",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": base_sha,
        "allowed_paths": ["src/thing.py", f"milestone_contracts/{branch}.json"],
        "forbidden_paths": ["BLUEPRINT.md"],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "valid in-scope milestone work")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is True, f"a valid contract with a fully in-scope diff must pass, got {result['errors']}")


_with_tmp_repo(_test_10)
print("PASS 10: a valid milestone contract whose baseline_sha matches the real merge-base and whose entire diff is within allowed_paths passes.")


# ======================================================================
# 11. Malformed milestone contract (missing required field) -> FAIL
# CLOSED (MILESTONE_CONTRACT_MALFORMED), not silently ignored.
# ======================================================================
def _test_11(root: Path) -> None:
    base_sha = _base_repo(root)
    branch = "feature/malformed-contract"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {"milestone_id": "TEST"}  # missing every other required field
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "malformed contract")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "a malformed milestone contract must fail closed")
    assert_true(has_code(result["errors"], "MILESTONE_CONTRACT_MALFORMED"), f"got {result['errors']}")


_with_tmp_repo(_test_11)
print("PASS 11: a milestone contract missing required fields fails closed with MILESTONE_CONTRACT_MALFORMED.")

# ======================================================================
# 12. UNCOMMITTED modified tracked file (git status --porcelain's first
# line starts with a leading space, e.g. " M path") must be parsed with
# the correct path -- not off-by-one-character-corrupted. Regression for
# a real bug found dogfooding this checker against the actual repo: an
# earlier _run_git() implementation called .strip() on the WHOLE
# `git status --porcelain` output, silently eating that leading space
# and shifting every downstream column-offset slice by one character.
# ======================================================================
def _test_12(root: Path) -> None:
    base_sha = _base_repo(root)
    branch = "feature/uncommitted-modified-file"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": base_sha,
        "allowed_paths": ["BLUEPRINT.md", f"milestone_contracts/{branch}.json"],
        "forbidden_paths": [],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _commit(root, "add contract")
    # Modify an already-tracked file WITHOUT committing -- this is the
    # exact porcelain shape (" M BLUEPRINT.md") that exposed the bug.
    _write(root, "BLUEPRINT.md", BLUEPRINT_TEXT + "\nAuthorized uncommitted edit.\n")
    result = cos.run_local_state_checks(root=root)
    assert_true(
        result["valid"] is True,
        f"an uncommitted modification to an allowed, exact-authorized path must pass with the correct path parsed, got {result['errors']}",
    )


_with_tmp_repo(_test_12)
print("PASS 12: an uncommitted modification to a tracked file (porcelain status ' M path', leading space) is parsed with the correct, uncorrupted path.")


# ======================================================================
# 13. UNCOMMITTED new UNTRACKED DIRECTORY containing multiple files must
# have each individual file detected and checked -- not collapsed into a
# single directory-path entry. Regression for a real bug found
# dogfooding this checker: plain `git status --porcelain` (without
# --untracked-files=all) reports a wholly-new untracked directory as one
# line ("?? dir/"), which would let every file inside it silently bypass
# per-file allowed_paths/protected-path checking.
# ======================================================================
def _test_13(root: Path) -> None:
    base_sha = _base_repo(root)
    branch = "feature/uncommitted-new-dir"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": base_sha,
        "allowed_paths": ["new_stuff/allowed.py", f"milestone_contracts/{branch}.json"],
        "forbidden_paths": [],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _commit(root, "add contract")
    # A brand-new, entirely untracked directory with two files -- one
    # authorized, one not. Neither is committed.
    _write(root, "new_stuff/allowed.py", "x = 1\n")
    _write(root, "new_stuff/not_allowed.py", "y = 2\n")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "an unauthorized file inside a new untracked directory must still be individually detected")
    assert_true(
        has_code(result["errors"], "STATE_PATH_NOT_ALLOWED"),
        f"expected STATE_PATH_NOT_ALLOWED for the unauthorized file inside the new directory, got {result['errors']}",
    )
    assert_true(
        any(e.get("path") == "new_stuff/not_allowed.py" for e in result["errors"]),
        f"the specific unauthorized file path must be named, not collapsed into the directory itself, got {result['errors']}",
    )
    assert_true(
        not any(e.get("path") == "new_stuff/" for e in result["errors"]),
        f"the directory itself must never appear as a flagged path -- each file inside it must be checked individually, got {result['errors']}",
    )


_with_tmp_repo(_test_13)
print("PASS 13: a brand-new untracked directory's individual files are each checked separately (not collapsed into one directory-path entry) -- an unauthorized file inside it is correctly named and flagged.")

# ======================================================================
# 14. CANONICAL project_state MUST NOT CLAIM ACTIVE WORK -- the real,
# committed project_state.json's own next_authorized_action must use
# durable canonical-main wording, never describe transient/in-progress
# branch work. Mechanically checkable via a substring guard (no new
# runtime enum -- free text remains the smallest reliable
# representation; this proves the invariant on the actual shipped
# fixture, not merely a synthetic one).
# ======================================================================
def _test_14() -> None:
    real_state = json.loads((ROOT / "project_state.json").read_text(encoding="utf-8"))
    action = real_state["next_authorized_action"]
    assert_true(
        "in progress" not in action.lower(),
        f"next_authorized_action must never describe transient in-progress branch work, got {action!r}",
    )
    assert_true(
        "CAREER_OS_MILESTONE_CONTRACT_AND_STATE_VALIDATION_V1" not in action,
        f"next_authorized_action must not describe this (or any) specific milestone as active/current work, got {action!r}",
    )


_test_14()
print("PASS 14: the real, committed project_state.json's next_authorized_action uses durable canonical-main wording, never transient in-progress branch-work wording.")


# ======================================================================
# 15. PROTECT THE JUDGE -- the state-validation machinery itself
# (src/career_os_state.py, scripts/verify_milestone_state.py) cannot be
# modified by broad wildcard authorization alone; exact literal
# authorization is required, identical to every other protected surface.
# ======================================================================
def _test_15(root: Path) -> None:
    base_sha = _base_repo(root)
    branch = "feature/rewrite-the-judge"
    _git(["checkout", "-q", "-b", branch], root)
    contract = {
        "milestone_id": "TEST",
        "kind": "IMPLEMENTATION",
        "goal": "test",
        "baseline_sha": base_sha,
        # Deliberately broad wildcards -- must NOT authorize rewriting
        # the judge's own enforcement machinery.
        "allowed_paths": ["src/*.py", "scripts/*.py", f"milestone_contracts/{branch}.json"],
        "forbidden_paths": [],
        "required_tests": [],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    _write(root, f"milestone_contracts/{branch}.json", json.dumps(contract))
    _write(root, "src/career_os_state.py", "# a hypothetical weakened validator\n")
    _commit(root, "attempt to rewrite the judge under a broad wildcard")
    result = cos.run_local_state_checks(root=root)
    assert_true(result["valid"] is False, "modifying src/career_os_state.py under only a broad wildcard must fail")
    assert_true(
        has_code(result["errors"], "STATE_PROTECTED_PATH_UNAUTHORIZED"),
        f"expected STATE_PROTECTED_PATH_UNAUTHORIZED for src/career_os_state.py, got {result['errors']}",
    )


_with_tmp_repo(_test_15)
print("PASS 15: src/career_os_state.py (the judge itself) cannot be modified under a broad 'src/*.py' wildcard alone -- fails with STATE_PROTECTED_PATH_UNAUTHORIZED, requiring exact literal contract authorization like every other protected surface.")


# ======================================================================
# 16. CONTRACT-PATH TRAVERSAL cannot escape milestone_contracts/.
# ======================================================================
def _test_16a_traversal_escape(root: Path) -> None:
    """A branch name shaped to traverse out of milestone_contracts/ must
    fail closed (STATE_MILESTONE_CONTRACT_PATH_INVALID), never resolve
    to some other file outside that directory."""
    _base_repo(root)
    # A real git branch name cannot literally contain "..", but the
    # resolver itself must be safe regardless of how `branch` is
    # obtained -- test the resolver directly against an adversarial
    # value, exactly as required: "branch path attempting ../ escape".
    resolved = cos.resolve_milestone_contract_path("../../../etc/passwd", root=root)
    assert_true(resolved is None, f"a traversal-shaped branch name must resolve to None (fail closed), got {resolved}")


def _test_16b_ordinary_slash_branch(root: Path) -> None:
    """An ordinary branch name containing '/' (this repo's own
    convention, e.g. 'feature/xyz') must still resolve correctly under
    milestone_contracts/."""
    resolved = cos.resolve_milestone_contract_path("feature/some-milestone", root=root)
    expected = (root / "milestone_contracts" / "feature" / "some-milestone.json").resolve()
    assert_true(
        resolved == expected,
        f"an ordinary 'feature/xyz'-shaped branch name must resolve to milestone_contracts/feature/xyz.json, got {resolved}",
    )


def _test_16c_real_branch_resolves(root: Path) -> None:
    """The resolver must correctly resolve THIS repository's own actual
    current branch to its real, existing contract file."""
    real_root = ROOT
    branch = cos.get_current_branch(cwd=real_root)
    assert_true(branch is not None, "must be able to determine the real repository's current branch")
    resolved = cos.resolve_milestone_contract_path(branch, root=real_root)
    assert_true(resolved is not None, f"the real current branch {branch!r} must resolve to a valid (non-traversal) path")
    contracts_dir = (real_root / "milestone_contracts").resolve()
    assert_true(
        resolved.is_relative_to(contracts_dir),
        f"resolved path {resolved} must remain strictly under {contracts_dir}",
    )


_with_tmp_repo(_test_16a_traversal_escape)
_with_tmp_repo(_test_16b_ordinary_slash_branch)
_with_tmp_repo(_test_16c_real_branch_resolves)
print("PASS 16: contract-path resolution refuses a traversal-shaped branch name (fails closed to None), correctly resolves an ordinary 'feature/xyz'-shaped branch name, and correctly resolves this repository's own real current branch to its real contract path.")

print("ALL career_os_state_v1_test CHECKS PASSED")
