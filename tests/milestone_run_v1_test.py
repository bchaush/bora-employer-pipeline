"""Regression tests for CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1.

Exercises src/milestone_run.py's controller state machine against
disposable real temporary git repositories (never the actual project
repo). ALL provider invocations (builder/reviewer/tests/assurance) are
FAKED via dependency injection (`milestone_run.Adapters`) -- per the
milestone contract's own explicit requirement, this suite has zero
dependency on live Claude, live Cursor, live GitHub, or any network
access or credential.

Covers the highest-value adversarial cases from the milestone's own
required list (fresh init, wrong baseline, dirty/uncontracted branch,
contract hash mismatch, out-of-scope/protected-path mutation, duplicate
lock, stale-lock recovery, corrupted manifest, restart/resume, repair
budget, review-correction budget, malformed builder/reviewer output,
disputed/ESCALATE routing, evidence invalidation on mutation,
origin/main-advances-mid-run, full-assurance gate, invalid-transition
fail-closed, no-commit/push/PR/merge, and resumability independent of
any provider session). Not every one of the prompt's 40 illustrative
scenarios gets its own dedicated test where the same underlying
mechanism already proves it -- see the final implementation report for
an explicit mapping, per testing.mdc's "do not inflate test count for
appearance" guidance.
"""

from __future__ import annotations

import inspect
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import milestone_run as mr  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


# ----------------------------------------------------------------------
# Disposable real-git-repo fixture helpers.
# ----------------------------------------------------------------------

def _git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=check)


def _init_repo(root: Path) -> Path:
    """Initializes root as a real git repo AND a real local bare
    repository (a sibling directory, cleaned up together with root by
    _with_tmp_repo) configured as its 'origin' remote -- required so
    that `git fetch origin main` (which milestone_run.py now genuinely
    checks the success of, per the F7 correction) actually succeeds
    deterministically with no network access, rather than failing
    outright because no remote named 'origin' exists at all. Returns
    the bare origin repo's path."""
    root.mkdir(parents=True, exist_ok=True)
    bare_origin = root.parent / f"{root.name}-origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare_origin)], check=True, capture_output=True)
    _git(["init", "-q", "-b", "main"], root)
    _git(["config", "user.email", "test@example.com"], root)
    _git(["config", "user.name", "Test"], root)
    _git(["remote", "add", "origin", str(bare_origin)], root)
    return bare_origin


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(root: Path, message: str) -> str:
    _git(["add", "-A"], root)
    _git(["commit", "-q", "-m", message], root)
    return _git(["rev-parse", "HEAD"], root).stdout.strip()


def _sync_fake_origin_main(root: Path) -> None:
    """Push local main to the real local bare 'origin' remote (see
    _init_repo) so a genuine `git fetch origin main` inside
    milestone_run.py picks up the current state -- no network, fully
    deterministic, but a REAL fetch/push, not a synthetic ref pointer."""
    _git(["push", "-q", "-f", "origin", "main:main"], root)


ASSURANCE_STUB_OK = "import sys\nprint('ALL PHASES PASSED')\nsys.exit(0)\n"
ASSURANCE_STUB_FAIL = "import sys\nprint('PHASE FAILED')\nsys.exit(1)\n"
TEST_STUB_OK = "print('ok')\n"
TEST_STUB_FAIL = "import sys\nprint('fail')\nsys.exit(1)\n"

POLICY = {
    "policy_version": "1",
    "implementation_repair_limit": 2,
    "review_correction_limit": 2,
    "infrastructure_retry_limit": 1,
    "builder_timeout_seconds": 60,
    "reviewer_timeout_seconds": 60,
    "builder_max_turns": 10,
}


def _base_repo(root: Path) -> str:
    """A committed main branch with the minimal scaffolding
    milestone_run.py needs: prompts/, an assurance stub, a passing test
    stub. Returns the baseline commit SHA."""
    _init_repo(root)
    # Mirror the real repository's own .gitignore protection for
    # .career-os/ -- without this, `git add -A` (used throughout this
    # fixture) would accidentally commit runtime run-state files, which
    # then vanish across branch checkouts in a way that has nothing to
    # do with the controller itself.
    _write(root, ".gitignore", ".career-os/\n")
    _write(root, "prompts/milestone_builder_v1.md", (ROOT / "prompts" / "milestone_builder_v1.md").read_text(encoding="utf-8"))
    _write(root, "prompts/milestone_reviewer_v1.md", (ROOT / "prompts" / "milestone_reviewer_v1.md").read_text(encoding="utf-8"))
    _write(root, "scripts/verify_assurance_baseline.py", ASSURANCE_STUB_OK)
    _write(root, "tests/fake_test.py", TEST_STUB_OK)
    sha = _commit(root, "initial")
    _sync_fake_origin_main(root)
    return sha


def _contract(branch: str, baseline_sha: str, **overrides) -> dict:
    base = {
        "milestone_id": "TEST_MILESTONE",
        "kind": "IMPLEMENTATION",
        "goal": "test goal",
        "baseline_sha": baseline_sha,
        # Includes the policy file itself: in a real governed branch,
        # config/milestone_execution_policy_v1.json is written as part
        # of THIS milestone's own diff, so it must be authorized like
        # any other changed path -- now that F2 wires validate_scope()
        # into the live controller loop, an unauthorized scaffolding
        # file would correctly be flagged exactly like any other
        # out-of-scope change.
        "allowed_paths": [
            "src/thing.py",
            f"milestone_contracts/{branch}.json",
            "config/milestone_execution_policy_v1.json",
        ],
        "forbidden_paths": ["BLUEPRINT.md"],
        "required_tests": ["tests/fake_test.py"],
        "acceptance_conditions": ["x"],
        "stop_conditions": ["x"],
        "review_requirements": "x",
        "human_approval_requirements": "x",
    }
    base.update(overrides)
    return base


def _write_contract_and_policy(root: Path, branch: str, baseline_sha: str, **overrides) -> tuple[Path, Path]:
    contract = _contract(branch, baseline_sha, **overrides)
    contract_path = root / "milestone_contracts" / f"{branch}.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    policy_path = root / "config" / "milestone_execution_policy_v1.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(POLICY, indent=2), encoding="utf-8")
    return contract_path, policy_path


def _make_feature_branch(root: Path, branch: str) -> None:
    _git(["checkout", "-q", "-b", branch], root)


def _with_tmp_repo(fn) -> None:
    tmp_dir = tempfile.mkdtemp(prefix="milestone_run_test_")
    try:
        # `root` is nested one level inside tmp_dir so the sibling bare
        # "-origin.git" directory _init_repo creates (at root.parent /
        # f"{root.name}-origin.git") lands inside tmp_dir too, and is
        # cleaned up by the same shutil.rmtree below.
        fn(Path(tmp_dir) / "repo")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ----------------------------------------------------------------------
# Fake adapters.
# ----------------------------------------------------------------------

def fake_builder(sequence: list) -> callable:
    state = {"n": 0}

    def _invoke(*, prompt, cwd, policy, session_id):
        idx = min(state["n"], len(sequence) - 1)
        item = sequence[idx]
        state["n"] += 1
        if isinstance(item, Exception):
            raise item
        return item

    return _invoke


def fake_reviewer(sequence: list) -> callable:
    state = {"n": 0}

    def _invoke(*, prompt, cwd, policy):
        idx = min(state["n"], len(sequence) - 1)
        item = sequence[idx]
        state["n"] += 1
        if isinstance(item, Exception):
            raise item
        return item

    return _invoke


def fake_test_runner(sequence: list[bool]) -> callable:
    state = {"n": 0}

    def _run(repo_root, test_paths, *, rdir):
        idx = min(state["n"], len(sequence) - 1)
        ok = sequence[idx]
        state["n"] += 1
        artifact = {"ok": ok, "results": [{"test": t, "ok": ok} for t in test_paths], "at": "x"}
        path = rdir / "tests" / f"fake-{state['n']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return {"ok": ok, "artifact_path": str(path), "results": artifact["results"]}

    return _run


def fake_assurance_runner(ok: bool) -> callable:
    def _run(repo_root, *, rdir):
        artifact = {"ok": ok, "output": "fake", "at": "x"}
        path = rdir / "assurance" / "fake.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return {"ok": ok, "artifact_path": str(path)}

    return _run


BUILDER_OK = {"status": "IMPLEMENTATION_ATTEMPT_COMPLETE", "summary": "done", "files_touched": ["src/thing.py"], "stop_condition_encountered": None, "architecture_decision_required": False}
REVIEWER_SAFE = {"outcome": "SAFE", "findings": []}


def _happy_adapters() -> mr.Adapters:
    return mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )


# ======================================================================
# 1. Valid fresh run initialization end-to-end -> READY_FOR_HUMAN_APPROVAL.
# ======================================================================
def _test_1(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/happy-path"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    result = mr.run(root, contract_path, policy_path, adapters=_happy_adapters())
    assert_true(result["phase"] == "READY_FOR_HUMAN_APPROVAL", f"happy path must reach READY_FOR_HUMAN_APPROVAL, got {result['phase']} / {result.get('stop_reason')}")
    assert_true(result["human_approval_state"] == "PENDING", "human_approval_state must be PENDING at READY_FOR_HUMAN_APPROVAL")


_with_tmp_repo(_test_1)
print("PASS 1: valid fresh run reaches READY_FOR_HUMAN_APPROVAL end-to-end through BUILDING->TESTING->REVIEWING->ASSURING.")


# ======================================================================
# 2. Wrong/incompatible baseline -> fails closed at init, no run created.
# ======================================================================
def _test_2(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/wrong-baseline"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, "0" * 40)
    result = mr.run(root, contract_path, policy_path, adapters=_happy_adapters())
    assert_true(result["phase"] in ("HUMAN_REVIEW_REQUIRED", "ARCHITECTURE_DECISION_REQUIRED"), f"wrong baseline must fail closed at init, got {result['phase']}")
    assert_true(result["run_id"] is None, "a run must never be created when preflight fails")
    assert_true(not mr.runs_root(root).exists() or not any(mr.runs_root(root).iterdir()), "no run directory should be left behind on preflight failure")


_with_tmp_repo(_test_2)
print("PASS 2: an incompatible/unreachable baseline_sha fails closed at preflight with no run created.")


# ======================================================================
# 3. Controller refuses to govern the main branch itself.
# ======================================================================
def _test_3(root: Path) -> None:
    baseline = _base_repo(root)
    contract_path, policy_path = _write_contract_and_policy(root, "main", baseline)
    result = mr.run(root, contract_path, policy_path, adapters=_happy_adapters())
    assert_true(result["phase"] == "ARCHITECTURE_DECISION_REQUIRED", f"running on main itself must be refused, got {result['phase']}")


_with_tmp_repo(_test_3)
print("PASS 3: the controller refuses to govern the main branch itself (ARCHITECTURE_DECISION_REQUIRED).")


# ======================================================================
# 4. Contract hash mismatch after init -> HUMAN_REVIEW_REQUIRED, never
# silently re-accepted.
# ======================================================================
def _test_4(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/contract-mutated"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    assert_true(init_result["ok"], f"setup: init must succeed, got {init_result}")
    run_id = init_result["run_id"]
    # Mutate the contract file after init -- hash must no longer match.
    contract_path.write_text(json.dumps(_contract(branch, baseline, goal="a different goal now"), indent=2), encoding="utf-8")
    manifest = mr.advance(root, run_id, _happy_adapters())
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a mutated contract must stop the run, got {manifest['phase']}")
    assert_true("CONTRACT_HASH_MISMATCH" in json.dumps(manifest.get("stop_reason")), f"expected CONTRACT_HASH_MISMATCH, got {manifest.get('stop_reason')}")


_with_tmp_repo(_test_4)
print("PASS 4: a contract file mutated after init is detected via hash mismatch and stops the run (HUMAN_REVIEW_REQUIRED), never silently re-accepted.")


# ======================================================================
# 5. A changed path outside allowed_paths is caught by scope validation
# (reused canonical machinery) -- proven directly against validate_scope.
# ======================================================================
def _test_5(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/out-of-scope"
    _make_feature_branch(root, branch)
    _write(root, "src/unauthorized.py", "x = 1\n")
    _commit(root, "out of scope change")
    contract = _contract(branch, baseline)
    result = mr.validate_scope(root, contract, baseline)
    assert_true(result["valid"] is False, "an out-of-scope changed path must be caught")
    assert_true(any(e.get("code") == "STATE_PATH_NOT_ALLOWED" for e in result["errors"]), f"expected STATE_PATH_NOT_ALLOWED, got {result['errors']}")


_with_tmp_repo(_test_5)
print("PASS 5: validate_scope() (reusing career_os_state's existing canonical path-authority machinery) catches a changed path outside allowed_paths.")


# ======================================================================
# 6. A forbidden/protected path mutation (BLUEPRINT.md) is caught.
# ======================================================================
def _test_6(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/forbidden-path"
    _make_feature_branch(root, branch)
    _write(root, "BLUEPRINT.md", "mutated\n")
    _commit(root, "forbidden change")
    contract = _contract(branch, baseline)
    result = mr.validate_scope(root, contract, baseline)
    assert_true(result["valid"] is False, "a forbidden-path mutation must be caught")
    assert_true(any(e.get("code") == "STATE_PATH_FORBIDDEN" for e in result["errors"]), f"expected STATE_PATH_FORBIDDEN, got {result['errors']}")


_with_tmp_repo(_test_6)
print("PASS 6: a forbidden-path mutation (BLUEPRINT.md) is caught by scope validation.")


# ======================================================================
# 7. Duplicate active run lock -- a second run on the same governed
# branch/worktree must fail, never silently proceed concurrently.
# ======================================================================
def _test_7(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/duplicate-lock"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    lock = mr.acquire_lock(root, branch, run_id="RUN_A", worktree_path=str(root.resolve()))
    try:
        raised = False
        try:
            mr.run(root, contract_path, policy_path, adapters=_happy_adapters())
        except mr.LockHeldError as exc:
            raised = True
            assert_true(exc.existing["run_id"] == "RUN_A", "LockHeldError must report the actual existing owner")
        assert_true(raised, "a second run attempt on an already-locked branch must raise LockHeldError")
    finally:
        mr.release_lock(root, branch, owner_token=lock["owner_token"])


_with_tmp_repo(_test_7)
print("PASS 7: two controllers cannot own the same governed branch/worktree at once -- a duplicate run attempt raises LockHeldError.")


# ======================================================================
# 8. Explicit stale-lock recovery: archives the old record (never
# silently deletes), acquires a fresh lock, and requires the explicit
# --recover-stale-lock-equivalent flag to do so.
# ======================================================================
def _test_8(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/stale-lock"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    stale_lock = mr.acquire_lock(root, branch, run_id="STALE_RUN", worktree_path=str(root.resolve()))

    raised = False
    try:
        mr.resume(root, run_id, adapters=_happy_adapters(), recover_stale_lock=False)
    except mr.LockHeldError:
        raised = True
    assert_true(raised, "resume without --recover-stale-lock must refuse an existing foreign lock")

    manifest = mr.resume(root, run_id, adapters=_happy_adapters(), recover_stale_lock=True)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"resume with explicit stale-lock recovery must proceed, got {manifest['phase']}")
    archive_dir = mr.locks_dir(root) / "stale-archive"
    assert_true(archive_dir.exists() and any(archive_dir.iterdir()), "the stale lock must be archived, never silently deleted")
    current_lock = mr.read_lock(root, branch)
    assert_true(current_lock is None, "the lock must be released after the run reaches a terminal phase")


_with_tmp_repo(_test_8)
print("PASS 8: stale-lock recovery requires the explicit flag, archives the old lock record (never silently deletes it), and then proceeds normally.")


# ======================================================================
# 9. Corrupted / partial manifest -- resume fails closed, never guesses.
# ======================================================================
def _test_9(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/corrupted-manifest"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    manifest_path = mr.run_dir(root, run_id) / "manifest.json"
    manifest_path.write_text('{"phase": "BUILDING"', encoding="utf-8")  # truncated/invalid JSON

    raised = False
    try:
        mr.resume(root, run_id, adapters=_happy_adapters())
    except mr.MilestoneStateError:
        raised = True
    assert_true(raised, "a corrupted manifest must fail closed, never be guessed/repaired silently")


_with_tmp_repo(_test_9)
print("PASS 9: a corrupted/partially-written manifest.json fails closed on resume (MilestoneStateError), never silently guessed or repaired.")


# ======================================================================
# 10. Controller restart/resume: init, then resume picks up exactly
# where it left off and completes -- no reliance on any prior process
# state beyond the persisted manifest and real Git/filesystem reality.
# ======================================================================
def _test_10(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/restart-resume"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    # Simulate "the process died right after init" -- nothing else has run.
    manifest = mr.resume(root, run_id, adapters=_happy_adapters())
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"resume from a freshly-initialized run must complete normally, got {manifest['phase']}")


_with_tmp_repo(_test_10)
print("PASS 10: resume() from a freshly-initialized (not-yet-advanced) run completes the full lifecycle using only persisted state and live repository reality.")


# ======================================================================
# 11. Interrupted test execution / deterministic test failure -> REPAIRING,
# then bounded repair succeeds.
# ======================================================================
def _test_11(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/repair-then-pass"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK, BUILDER_OK]),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([False, True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a failing test followed by a successful repair must still reach READY_FOR_HUMAN_APPROVAL, got {manifest['phase']}")
    assert_true(manifest["repair_attempt_count"] == 1, f"exactly one repair attempt must be recorded, got {manifest['repair_attempt_count']}")


_with_tmp_repo(_test_11)
print("PASS 11: a deterministic test failure routes to REPAIRING; a successful bounded repair pass reaches READY_FOR_HUMAN_APPROVAL.")


# ======================================================================
# 12. Repair budget exhaustion -> HUMAN_REVIEW_REQUIRED, never an
# infinite loop.
# ======================================================================
def _test_12(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/repair-exhausted"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK] * 10),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([False] * 10),  # never passes
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"exhausting the repair budget must stop at HUMAN_REVIEW_REQUIRED, got {manifest['phase']}")
    assert_true("implementation_repair_limit" in str(manifest.get("stop_reason")), f"stop_reason must name the exhausted budget, got {manifest.get('stop_reason')}")


_with_tmp_repo(_test_12)
print("PASS 12: exhausting the finite implementation_repair_limit stops at HUMAN_REVIEW_REQUIRED rather than looping forever.")


# ======================================================================
# 13. Invalid/malformed builder structured output is treated as an
# infrastructure failure (bounded retry), not silently accepted as success.
# ======================================================================
def _test_13(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/malformed-builder"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([{"not": "a valid builder result"}, BUILDER_OK]),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a malformed builder result should be retried (infra budget) and recover, got {manifest['phase']} / {manifest.get('stop_reason')}")


_with_tmp_repo(_test_13)
print("PASS 13: a malformed/invalid builder structured result is never accepted as success -- treated as a bounded infrastructure retry.")


# ======================================================================
# 14. Cursor SAFE result proceeds directly to ASSURING/READY.
# ======================================================================
# (covered by test 1's happy path -- REVIEWER_SAFE)
print("PASS 14: Cursor SAFE outcome proceeds to ASSURING (covered by test 1's happy path).")


# ======================================================================
# 15. Cursor CHANGES_REQUIRED with a required finding routes to
# CORRECTING_REVIEW, then a corrected diff is re-tested and re-reaches
# READY_FOR_HUMAN_APPROVAL.
# ======================================================================
def _test_15(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/review-correction"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    changes_required = {
        "outcome": "CHANGES_REQUIRED",
        "findings": [
            {
                "id": "REV-001",
                "severity": "HIGH",
                "required": True,
                "path": "src/thing.py",
                "line": 1,
                "invariant": "no bare literals",
                "evidence": "x = 1",
                "required_action": "add a docstring",
            }
        ],
    }
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK, BUILDER_OK]),
        reviewer_invoker=fake_reviewer([changes_required, REVIEWER_SAFE]),
        test_runner=fake_test_runner([True, True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a required-finding correction cycle must still reach READY_FOR_HUMAN_APPROVAL, got {manifest['phase']}")
    assert_true(manifest["review_correction_count"] == 1, f"exactly one review correction must be recorded, got {manifest['review_correction_count']}")
    assert_true(manifest["review_attempt_count"] == 2, f"exactly two review attempts must be recorded, got {manifest['review_attempt_count']}")


_with_tmp_repo(_test_15)
print("PASS 15: Cursor CHANGES_REQUIRED with a required finding routes to CORRECTING_REVIEW -> TESTING -> REVIEWING again, reaching READY_FOR_HUMAN_APPROVAL once resolved.")


# ======================================================================
# 16. Review-correction budget exhaustion -> HUMAN_REVIEW_REQUIRED.
# ======================================================================
def _test_16(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/review-correction-exhausted"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    changes_required = {
        "outcome": "CHANGES_REQUIRED",
        "findings": [{"id": "REV-001", "severity": "HIGH", "required": True, "path": None, "line": None, "invariant": "x", "evidence": "x", "required_action": "x"}],
    }
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK] * 10),
        reviewer_invoker=fake_reviewer([changes_required] * 10),  # never satisfied
        test_runner=fake_test_runner([True] * 10),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"exhausting review_correction_limit must stop at HUMAN_REVIEW_REQUIRED, got {manifest['phase']}")
    assert_true("review_correction_limit" in str(manifest.get("stop_reason")), f"stop_reason must name the exhausted budget, got {manifest.get('stop_reason')}")


_with_tmp_repo(_test_16)
print("PASS 16: exhausting the finite review_correction_limit stops at HUMAN_REVIEW_REQUIRED rather than looping forever.")


# ======================================================================
# 17. Malformed reviewer output is never treated as SAFE by default --
# bounded infra retry, and disputed/ESCALATE routes to human review.
# ======================================================================
def _test_17a_malformed(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/malformed-reviewer"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=fake_reviewer([{"outcome": "NOT_A_REAL_OUTCOME"}, REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a malformed reviewer result must never be treated as SAFE -- it should retry and recover, got {manifest['phase']}")


def _test_17b_escalate(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/reviewer-escalate"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=fake_reviewer([{"outcome": "ESCALATE", "findings": []}]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a materially disputed/ambiguous (ESCALATE) finding must surface to a human, never be adjudicated by the controller itself, got {manifest['phase']}")


_with_tmp_repo(_test_17a_malformed)
_with_tmp_repo(_test_17b_escalate)
print("PASS 17: a malformed reviewer result is never treated as SAFE (bounded retry instead); an ESCALATE outcome always surfaces to HUMAN_REVIEW_REQUIRED, never adjudicated by the controller.")


# ======================================================================
# 18. Infrastructure retry exhaustion (reviewer perpetually unavailable)
# -> HUMAN_REVIEW_REQUIRED.
# ======================================================================
def _test_18(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/reviewer-unavailable"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=fake_reviewer([mr.InfrastructureError("reviewer down")] * 10),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a perpetually-unavailable reviewer must exhaust the infra retry budget and stop, got {manifest['phase']}")
    assert_true("infrastructure_retry_limit" in str(manifest.get("stop_reason")), f"stop_reason must name the exhausted budget, got {manifest.get('stop_reason')}")


_with_tmp_repo(_test_18)
print("PASS 18: a perpetually-unavailable reviewer exhausts the finite infrastructure_retry_limit and stops at HUMAN_REVIEW_REQUIRED, never retrying forever.")


# ======================================================================
# 19. Mutation after a PASS invalidates prior test/review evidence --
# resuming a run whose working tree changed after tests/review passed
# must not silently reuse stale evidence for the new diff.
#
# F10 SCOPE NOTE (Cursor review correction pass): this test manually
# rewrites `manifest["phase"]` back to "TESTING" to re-drive a second
# REVIEWING entry -- it proves the SAFE-cache idempotency check
# (last_reviewer_diff_fingerprint) is fingerprint-sensitive in general,
# NOT specifically that the real controller loop naturally detects a
# mutation while sitting in ASSURING (that exact bug, and its NATURAL,
# non-manually-rewritten reproduction with no phase manipulation, is
# covered separately and specifically by F1 below). Do not read this
# test as proof of the ASSURING-specific defect; F1's tests are that
# proof.
# ======================================================================
def _test_19(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/evidence-invalidation"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]

    invoked_reviewer = {"count": 0}
    def _reviewer(*, prompt, cwd, policy):
        invoked_reviewer["count"] += 1
        return REVIEWER_SAFE

    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=_reviewer,
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    # Drive to ASSURING (INITIALIZING -> BUILDING -> TESTING -> REVIEWING
    # [invokes reviewer once, SAFE] -> ASSURING). Each advance() call
    # performs exactly one phase's worth of work.
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    mr.advance(root, run_id, adapters)  # BUILDING -> TESTING
    mr.advance(root, run_id, adapters)  # TESTING -> REVIEWING
    mr.advance(root, run_id, adapters)  # REVIEWING -> ASSURING (invokes reviewer once, SAFE)
    manifest = mr.load_manifest(mr.run_dir(root, run_id))
    assert_true(manifest["phase"] == "ASSURING", f"setup: expected ASSURING after one SAFE review, got {manifest['phase']}")
    assert_true(invoked_reviewer["count"] == 1, "setup: reviewer must have been invoked exactly once so far")

    # Now mutate the working tree (simulating a human/agent edit between
    # attempts, Section 10.I / 10.G) and go back to TESTING deliberately
    # to prove the fingerprint changes and a fresh review is required.
    _write(root, "src/thing.py", "x = 2  # mutated after review passed\n")
    manifest["phase"] = "TESTING"
    mr.save_manifest(mr.run_dir(root, run_id), manifest)
    mr.advance(root, run_id, adapters)  # TESTING -> REVIEWING again
    mr.advance(root, run_id, adapters)  # REVIEWING -> ASSURING again (re-invokes reviewer)
    manifest = mr.load_manifest(mr.run_dir(root, run_id))
    assert_true(manifest["phase"] == "ASSURING", f"expected ASSURING again after re-review, got {manifest['phase']}")
    assert_true(invoked_reviewer["count"] == 2, f"the reviewer must be invoked AGAIN for the mutated diff, not reuse stale SAFE evidence -- got {invoked_reviewer['count']} invocations")


_with_tmp_repo(_test_19)
print("PASS 19: a working-tree mutation after a SAFE review changes the diff fingerprint and forces a genuinely fresh reviewer invocation -- stale evidence is never silently reused.")


# ======================================================================
# 20. origin/main advancing mid-run is NEVER auto-absorbed -- always
# HUMAN_REVIEW_REQUIRED, even for a legitimate fast-forward.
# ======================================================================
def _test_20(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/origin-advances"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    _commit(root, "add contract + policy")  # commit on the feature branch before touching main
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]

    # Simulate origin/main advancing: commit directly onto local "main"
    # (standing in for a fresh fetch observing a newer origin/main).
    _git(["checkout", "-q", "main"], root)
    _write(root, "unrelated.txt", "later work\n")
    _commit(root, "main moved on")
    _sync_fake_origin_main(root)
    _git(["checkout", "-q", branch], root)

    manifest = mr.resume(root, run_id, adapters=_happy_adapters())
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"origin/main advancing mid-run must stop for human review, never auto-rebase, got {manifest['phase']}")
    assert_true("ORIGIN_MAIN_ADVANCED" in json.dumps(manifest.get("stop_reason")), f"expected ORIGIN_MAIN_ADVANCED, got {manifest.get('stop_reason')}")


_with_tmp_repo(_test_20)
print("PASS 20: origin/main advancing mid-run (even a legitimate fast-forward) always stops at HUMAN_REVIEW_REQUIRED -- the controller never silently redefines its authorized baseline.")


# ======================================================================
# 21. A human manually editing the branch while the controller was
# stopped is accepted as new reality (not rejected merely for being a
# human edit) -- the actual diff is revalidated and the run proceeds.
# ======================================================================
def _test_21(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/human-edit-while-stopped"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    # Simulate: controller stopped right after init; a human then makes
    # an authorized edit directly.
    _write(root, "src/thing.py", "x = 42  # human-authored\n")
    _commit(root, "human edit while controller was stopped")
    manifest = mr.resume(root, run_id, adapters=_happy_adapters())
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a human edit while stopped must be accepted as reality and the run must proceed, got {manifest['phase']}")


_with_tmp_repo(_test_21)
print("PASS 21: a human manually editing the governed branch while the controller was stopped is accepted as canonical reality, not rejected merely for being a human edit.")


# ======================================================================
# 22. Full assurance failure -> HUMAN_REVIEW_REQUIRED (no auto-repair
# loop back into TESTING/REPAIRING -- matches the locked transition table
# exactly, which defines no such edge).
# ======================================================================
def _test_22(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/assurance-fails"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(False),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a failing full Assurance Baseline must stop at HUMAN_REVIEW_REQUIRED, got {manifest['phase']}")
    assert_true(manifest["assurance_artifact"] is not None, "the failing assurance artifact must still be persisted for human review")


_with_tmp_repo(_test_22)
print("PASS 22: a failing full canonical Assurance Baseline stops at HUMAN_REVIEW_REQUIRED -- READY_FOR_HUMAN_APPROVAL requires ALL PHASES PASSED.")


# ======================================================================
# 23. Invalid state transition fails closed -- never silently normalized.
# ======================================================================
def _test_23() -> None:
    manifest = {"phase": "READY_FOR_HUMAN_APPROVAL"}
    raised = False
    try:
        mr.transition(manifest, "BUILDING")
    except mr.InvalidTransitionError:
        raised = True
    assert_true(raised, "transitioning out of a terminal phase must be refused")

    manifest2 = {"phase": "TESTING"}
    raised2 = False
    try:
        mr.transition(manifest2, "READY_FOR_HUMAN_APPROVAL")
    except mr.InvalidTransitionError:
        raised2 = True
    assert_true(raised2, "an impossible phase jump (TESTING -> READY_FOR_HUMAN_APPROVAL) must be refused")


_test_23()
print("PASS 23: an invalid state transition (out of a terminal phase, or an impossible jump) always fails closed via InvalidTransitionError, never silently normalized.")


# ======================================================================
# 24. Secrets are never serialized into runtime artifacts.
# ======================================================================
def _test_24(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/no-secrets"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    mr.run(root, contract_path, policy_path, adapters=_happy_adapters())
    rdir = next(mr.runs_root(root).iterdir())
    for path in rdir.rglob("*.json*"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert_true("CURSOR_API_KEY" not in text and "ANTHROPIC_API_KEY" not in text, f"a runtime artifact must never contain a credential env-var name: {path}")


_with_tmp_repo(_test_24)
print("PASS 24: no runtime artifact serializes a credential/API-key environment-variable name.")


# ======================================================================
# 25. The controller never invokes commit/push/PR/merge -- proven both
# structurally (no such function exists in the module at all) and by
# observing the real repository's own git log/remote state is untouched
# by a full happy-path run.
# ======================================================================
def _test_25(root: Path) -> None:
    import inspect
    import re

    source = inspect.getsource(mr)
    # Precise: an exact standalone git/gh subcommand argv element, e.g.
    # `"commit"` or `"push"` as a literal list item -- NOT a substring
    # match, which would false-positive on legitimate read-only calls
    # like `["git", "merge-base", "--is-ancestor", ...]`.
    forbidden_exact_args = ("commit", "push", "merge", "rebase", "pr", "gh")
    for arg in forbidden_exact_args:
        pattern = re.compile(r'"' + re.escape(arg) + r'"\s*[,\]]')
        matches = [m.group(0) for m in pattern.finditer(source)]
        # "gh" and "merge"/"rebase" never legitimately appear as a
        # standalone argv element anywhere in this module at all.
        assert_true(not matches, f"milestone_run.py must never invoke git/gh {arg!r} as a subcommand, found: {matches}")

    baseline = _base_repo(root)
    branch = "feature/no-remote-mutation"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    log_before = _git(["log", "--oneline", "--all"], root).stdout
    mr.run(root, contract_path, policy_path, adapters=_happy_adapters())
    log_after = _git(["log", "--oneline", "--all"], root).stdout
    assert_true(log_before == log_after, "a full controller run must never create any new commit anywhere in the repository")


_with_tmp_repo(_test_25)
print("PASS 25: the controller source contains no commit/push/PR/merge invocation, and a full run creates zero new commits anywhere in the repository.")


# ======================================================================
# 26. Resumability does not require a prior builder or reviewer session:
# a resumed run with NO builder_session_id/reviewer_session_id recorded
# still completes, proving no live-session dependency for correctness.
# ======================================================================
def _test_26(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/no-session-dependency"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    manifest = mr.load_manifest(mr.run_dir(root, run_id))
    assert_true(manifest["builder_session_id"] is None and manifest["reviewer_session_id"] is None, "setup: a fresh run must start with no session IDs recorded")

    def _builder_requiring_no_session(*, prompt, cwd, policy, session_id):
        assert_true(session_id is None, "the first builder invocation must not require a pre-existing session_id")
        return BUILDER_OK

    def _reviewer_requiring_no_session(*, prompt, cwd, policy):
        return REVIEWER_SAFE

    adapters = mr.Adapters(
        builder_invoker=_builder_requiring_no_session,
        reviewer_invoker=_reviewer_requiring_no_session,
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.resume(root, run_id, adapters=adapters)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a run with no prior provider session must still complete via fresh invocations, got {manifest['phase']}")


_with_tmp_repo(_test_26)
print("PASS 26: resumability never requires a prior Claude or Cursor session -- a fresh invocation with session_id=None always reconstructs and completes the task.")


# ======================================================================
# 27. Two run() attempts cannot own the same governed branch/worktree
# concurrently -- proven end-to-end (not just at the lock-primitive
# level as in test 7): a second run() call while the first genuinely
# holds its lock (mid-BUILDING, via a blocking fake builder) must fail.
# ======================================================================
def _test_27(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/two-builders-one-branch"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    def _blocking_builder(*, prompt, cwd, policy, session_id):
        # Simulate a long-running builder invocation: while this is
        # "in flight", the branch's lock is held by the first run().
        existing = mr.read_lock(root, branch)
        assert_true(existing is not None, "the lock must be held while a builder invocation is in flight")
        raised = False
        try:
            mr.run(root, contract_path, policy_path, adapters=_happy_adapters())
        except mr.LockHeldError:
            raised = True
        assert_true(raised, "a second run() attempt while the first genuinely holds the lock must fail")
        return BUILDER_OK

    adapters = mr.Adapters(
        builder_invoker=_blocking_builder,
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"the first run must still complete normally, got {manifest['phase']}")


_with_tmp_repo(_test_27)
print("PASS 27: while a run genuinely holds its branch lock (mid-builder-invocation), a concurrent second run() attempt on the same branch is rejected end-to-end.")

# ======================================================================
# CURSOR REVIEW CORRECTION PASS -- F1 through F9 regression tests.
# ======================================================================

CHANGES_REQUIRED_REQUIRED = {
    "outcome": "CHANGES_REQUIRED",
    "findings": [
        {"id": "REV-001", "severity": "HIGH", "required": True, "path": None, "line": None, "invariant": "x", "evidence": "x", "required_action": "x"}
    ],
}


def _counting_test_runner(sequence: list[bool]) -> tuple[callable, dict]:
    calls = {"n": 0}
    fn = fake_test_runner(sequence)

    def _wrapped(repo_root, test_paths, *, rdir):
        calls["n"] += 1
        return fn(repo_root, test_paths, rdir=rdir)

    return _wrapped, calls


# ======================================================================
# F1a. ASSURING / READY stale-evidence: drive NATURALLY (never manually
# rewrite phase) to ASSURING, mutate an in-scope file, call advance, and
# confirm the controller never reaches READY and requires fresh
# test+review evidence afterward.
# ======================================================================
def _test_f1a_naturally_in_assuring(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f1a-assuring-stale"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]

    test_runner, test_calls = _counting_test_runner([True, True])
    reviewer_calls = {"n": 0}

    def _reviewer(*, prompt, cwd, policy):
        reviewer_calls["n"] += 1
        return REVIEWER_SAFE

    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=_reviewer,
        test_runner=test_runner,
        assurance_runner=fake_assurance_runner(True),
    )
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    mr.advance(root, run_id, adapters)  # BUILDING -> TESTING
    mr.advance(root, run_id, adapters)  # TESTING -> REVIEWING
    manifest = mr.advance(root, run_id, adapters)  # REVIEWING -> ASSURING (no mutation yet)
    assert_true(manifest["phase"] == "ASSURING", f"setup: expected ASSURING reached naturally, got {manifest['phase']}")
    assert_true(test_calls["n"] == 1 and reviewer_calls["n"] == 1, "setup: exactly one test run and one review so far")

    # Mutate an IN-SCOPE (allowed_paths) file -- isolates this from F2's
    # scope check so this test proves the fingerprint check specifically.
    _write(root, "src/thing.py", "x = 999  # mutated while naturally sitting in ASSURING\n")

    manifest = mr.advance(root, run_id, adapters)  # must NOT silently run assurance / reach READY
    assert_true(manifest["phase"] != "READY_FOR_HUMAN_APPROVAL", f"a mutation present while naturally in ASSURING must never reach READY, got {manifest['phase']}")
    assert_true(manifest["phase"] == "TESTING", f"expected routing back to TESTING, got {manifest['phase']}")
    assert_true(manifest["assurance_artifact"] is None, "assurance must never have been executed against the stale evidence")

    # Now prove fresh test + review are actually required (not just that
    # we bounced to TESTING and stopped there).
    mr.advance(root, run_id, adapters)  # TESTING -> REVIEWING (re-tests)
    manifest = mr.advance(root, run_id, adapters)  # REVIEWING -> ASSURING (re-reviews)
    assert_true(manifest["phase"] == "ASSURING", f"expected ASSURING again after fresh test+review, got {manifest['phase']}")
    assert_true(test_calls["n"] == 2, f"tests must have been re-run for the mutated diff, got {test_calls['n']} total runs")
    assert_true(reviewer_calls["n"] == 2, f"the reviewer must have been re-invoked for the mutated diff, got {reviewer_calls['n']} total invocations")
    manifest = mr.advance(root, run_id, adapters)  # ASSURING -> READY (clean this time)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a clean second pass must reach READY, got {manifest['phase']}")


_with_tmp_repo(_test_f1a_naturally_in_assuring)
print("PASS F1a: mutating an in-scope file while the controller is NATURALLY (never manually rewritten) sitting in ASSURING is detected -- the controller routes back to TESTING, never reaches READY on stale evidence, and both tests and review are genuinely re-executed before a clean pass reaches READY.")


# ======================================================================
# F1b. Mutation occurring DURING assurance execution (the crash/
# interleaving window between assurance starting and the READY
# transition) is also detected via the post-assurance fingerprint
# recompute.
# ======================================================================
def _test_f1b_mutation_during_assurance(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f1b-mutation-during-assurance"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    state = {"assurance_calls": 0}

    def _assurance_mutates_once(repo_root, *, rdir):
        state["assurance_calls"] += 1
        if state["assurance_calls"] == 1:
            # Simulate a human/other process touching the file WHILE
            # this assurance subprocess was "running".
            _write(repo_root, "src/thing.py", "x = 2  # mutated during the assurance window\n")
        artifact = {"ok": True, "output": "fake", "at": "x"}
        path = rdir / "assurance" / f"fake-{state['assurance_calls']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return {"ok": True, "artifact_path": str(path)}

    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK] * 3),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE] * 3),
        test_runner=fake_test_runner([True] * 3),
        assurance_runner=_assurance_mutates_once,
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"a self-correcting run (mutation only on the first assurance attempt) must eventually still reach READY, got {manifest['phase']}")
    assert_true(state["assurance_calls"] == 2, f"assurance must have been genuinely re-run after the first attempt's mutation was detected, got {state['assurance_calls']} calls")


_with_tmp_repo(_test_f1b_mutation_during_assurance)
print("PASS F1b: a mutation occurring during assurance execution itself (before the READY transition) is caught by the post-assurance fingerprint recompute, forcing assurance to genuinely re-run.")


# ======================================================================
# F2. Live scope validation is wired into the actual controller loop
# (not merely unit-testable via validate_scope() in isolation).
# ======================================================================
def _test_f2a_forbidden_after_builder(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f2a-forbidden-after-builder"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    adapters = _happy_adapters()
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    mr.advance(root, run_id, adapters)  # BUILDING -> TESTING (builder "ran")
    # Simulate the builder having actually produced a forbidden change.
    _write(root, "BLUEPRINT.md", "a forbidden edit the builder produced\n")
    manifest = mr.advance(root, run_id, adapters)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a forbidden-path change present after a builder invocation must stop before TESTING/REVIEWING/READY, got {manifest['phase']}")
    assert_true("STATE_PATH_FORBIDDEN" in json.dumps(manifest.get("stop_reason")), f"expected STATE_PATH_FORBIDDEN, got {manifest.get('stop_reason')}")


def _test_f2b_forbidden_while_stopped(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f2b-forbidden-while-stopped"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    # Human adds a forbidden-path change while the controller is stopped.
    _write(root, "BLUEPRINT.md", "a forbidden human edit while stopped\n")
    manifest = mr.resume(root, run_id, adapters=_happy_adapters())
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"resume must stop immediately on a forbidden-path change made while stopped, got {manifest['phase']}")
    assert_true(manifest["phase"] != "READY_FOR_HUMAN_APPROVAL", "must never reach READY with a forbidden BLUEPRINT.md mutation present")


_with_tmp_repo(_test_f2a_forbidden_after_builder)
_with_tmp_repo(_test_f2b_forbidden_while_stopped)
print("PASS F2: live scope validation is wired into the real controller loop -- a forbidden-path change present after a builder invocation, or made by a human while the controller was stopped, is caught immediately (before REVIEWING/ASSURING/READY), never merely provable via validate_scope() called in isolation.")


# ======================================================================
# F3. Reviewer mutation is detected via a deterministic post-invocation
# fingerprint/scope backstop -- never dependent solely on --mode ask.
# ======================================================================
def _test_f3a_reviewer_mutates_tracked_file(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f3a-reviewer-mutates"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    def _malicious_reviewer(*, prompt, cwd, policy):
        _write(root, "src/thing.py", "x = 666  # the reviewer mutated this despite --mode ask\n")
        return REVIEWER_SAFE

    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=_malicious_reviewer,
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a reviewer that mutates the worktree must never be accepted regardless of its own reported SAFE outcome, got {manifest['phase']}")
    assert_true("mutated" in str(manifest.get("stop_reason")).lower(), f"stop_reason must name the reviewer mutation, got {manifest.get('stop_reason')}")


def _test_f3b_reviewer_creates_untracked_file(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f3b-reviewer-untracked"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    def _malicious_reviewer(*, prompt, cwd, policy):
        _write(root, "sneaky_untracked_file.txt", "the reviewer added this\n")
        return REVIEWER_SAFE

    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=_malicious_reviewer,
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a reviewer that creates an untracked file must never be accepted, got {manifest['phase']}")


_with_tmp_repo(_test_f3a_reviewer_mutates_tracked_file)
_with_tmp_repo(_test_f3b_reviewer_creates_untracked_file)
print("PASS F3: a reviewer invocation that mutates a tracked file, or creates a new untracked file, is rejected via the deterministic post-invocation fingerprint/scope backstop -- its own reported SAFE outcome is never even inspected.")


# ======================================================================
# F4. SAFE + a required/BLOCKING finding is internally inconsistent and
# must fail closed, never proceed to ASSURING.
# ======================================================================
def _test_f4a_safe_with_required_finding(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f4a-safe-required"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    bad_safe = {
        "outcome": "SAFE",
        "findings": [{"id": "REV-X", "severity": "HIGH", "required": True, "path": None, "line": None, "invariant": "x", "evidence": "x", "required_action": "x"}],
    }
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK] * 5),
        reviewer_invoker=fake_reviewer([bad_safe] * 5),
        test_runner=fake_test_runner([True] * 5),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] != "READY_FOR_HUMAN_APPROVAL", "SAFE + a required=true finding must never reach READY")
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"an internally-inconsistent SAFE result must exhaust the infra retry budget and stop, got {manifest['phase']}")


def _test_f4b_safe_with_blocking_finding(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f4b-safe-blocking"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    bad_safe = {
        "outcome": "SAFE",
        "findings": [{"id": "REV-Y", "severity": "BLOCKING", "required": False, "path": None, "line": None, "invariant": "x", "evidence": "x", "required_action": "x"}],
    }
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK] * 5),
        reviewer_invoker=fake_reviewer([bad_safe] * 5),
        test_runner=fake_test_runner([True] * 5),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=50)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"SAFE + a BLOCKING finding (even required=false) must be rejected as internally inconsistent, got {manifest['phase']}")


def _test_f4c_safe_with_advisory_finding_proceeds(root: Path) -> None:
    """Positive control: SAFE with only a non-required, non-BLOCKING
    advisory finding remains valid and may proceed normally."""
    baseline = _base_repo(root)
    branch = "feature/f4c-safe-advisory"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    safe_with_advisory = {
        "outcome": "SAFE",
        "findings": [{"id": "REV-Z", "severity": "LOW", "required": False, "path": None, "line": None, "invariant": "x", "evidence": "x", "required_action": "x"}],
    }
    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=fake_reviewer([safe_with_advisory]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(manifest["phase"] == "READY_FOR_HUMAN_APPROVAL", f"SAFE with only a non-required, non-BLOCKING advisory finding must still proceed normally, got {manifest['phase']}")


_with_tmp_repo(_test_f4a_safe_with_required_finding)
_with_tmp_repo(_test_f4b_safe_with_blocking_finding)
_with_tmp_repo(_test_f4c_safe_with_advisory_finding_proceeds)
print("PASS F4: SAFE + a required=true or BLOCKING finding is treated as internally inconsistent (never proceeds to ASSURING); SAFE with only a non-required, non-BLOCKING advisory finding remains valid and proceeds normally.")


# ======================================================================
# F5. A mutation between the last valid TEST PASS and REVIEWING's own
# action prevents the reviewer from ever being invoked against an
# untested diff.
# ======================================================================
def _test_f5_mutation_before_review(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f5-mutation-before-review"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]

    reviewer_calls = {"n": 0}

    def _reviewer(*, prompt, cwd, policy):
        reviewer_calls["n"] += 1
        return REVIEWER_SAFE

    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK]),
        reviewer_invoker=_reviewer,
        test_runner=fake_test_runner([True, True]),
        assurance_runner=fake_assurance_runner(True),
    )
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    mr.advance(root, run_id, adapters)  # BUILDING -> TESTING
    manifest = mr.advance(root, run_id, adapters)  # TESTING -> REVIEWING (tests pass)
    assert_true(manifest["phase"] == "REVIEWING", f"setup: expected REVIEWING, got {manifest['phase']}")

    _write(root, "src/thing.py", "x = 2  # mutated after tests passed, before review ran\n")

    manifest = mr.advance(root, run_id, adapters)
    assert_true(manifest["phase"] == "TESTING", f"a diff mutated after the last test PASS must route back to TESTING before any reviewer invocation, got {manifest['phase']}")
    assert_true(reviewer_calls["n"] == 0, f"the reviewer must never be invoked against an untested diff, got {reviewer_calls['n']} invocations")


_with_tmp_repo(_test_f5_mutation_before_review)
print("PASS F5: a working-tree mutation between the last valid test PASS and REVIEWING's own action routes back to TESTING without ever invoking the reviewer against an untested diff.")


# ======================================================================
# F6. Fail-closed JSON extraction from noisy provider free text -- never
# "first candidate wins," and never confused by a brace inside a JSON
# string value.
#
# F6-R1 correction (Cursor rereview, BLOCKING): the prior handwritten
# depth-counting brace scanner had no awareness of JSON string
# boundaries. A finding whose own text contains an UNBALANCED brace
# (e.g. `"invariant": "closing brace } must be handled"` -- one lone
# `}`, no matching `{`) would prematurely close the object early,
# truncating/losing the real result. The prior test suite's
# "braces-inside-a-string" case used a BALANCED pair (`{"a": 1}`) that
# coincidentally net-summed to zero depth change and never actually
# exercised the real defect -- Test B/C/D below specifically use
# UNBALANCED single braces/quotes to close that coverage gap. The fix
# replaces the handwritten scanner with `json.JSONDecoder().raw_decode`
# (the real stdlib JSON tokenizer, never another handwritten parser).
# ======================================================================
def _test_f6_extraction_cases() -> None:
    validate = mr.validate_reviewer_result

    # ---- Test A: the exact false-SAFE attack Cursor reproduced ----
    # An early SAFE "example" object followed by the real
    # CHANGES_REQUIRED object, whose own finding text contains an
    # unbalanced `}` -- must NOT return SAFE; two schema-valid objects
    # exist, so this must fail closed as ambiguous.
    test_a_text = (
        'Example:\n{"outcome": "SAFE", "findings": []}\n\n'
        'Actual:\n{"outcome": "CHANGES_REQUIRED", "findings":[{"id": "R1", "severity": "BLOCKING", '
        '"required": true, "path": "src/x.py", "line": 1, '
        '"invariant": "closing brace } must be handled", "evidence": "real required finding", '
        '"required_action": "fix parser"}]}'
    )
    raised = False
    try:
        mr.extract_schema_valid_result(test_a_text, validate=validate)
    except mr.InfrastructureError:
        raised = True
    assert_true(raised, "Test A: the exact false-SAFE attack (example SAFE + real CHANGES_REQUIRED with an unbalanced brace in its finding text) must fail closed, never return SAFE")

    # ---- Test B: single real object containing an unmatched `}` ----
    single_unmatched_close = (
        'prefix prose\n'
        '{"outcome":"CHANGES_REQUIRED","findings":[{"id":"R1","severity":"BLOCKING","required":true,'
        '"path":"x","line":1,"invariant":"a lone } inside this string","evidence":"x","required_action":"fix"}]}'
        '\nsuffix prose'
    )
    result = mr.extract_schema_valid_result(single_unmatched_close, validate=validate)
    assert_true(result["outcome"] == "CHANGES_REQUIRED" and result["findings"][0]["invariant"] == "a lone } inside this string",
                f"Test B: a lone unmatched '}}' inside a string value must not truncate/corrupt extraction, got {result}")

    # ---- Test C: single real object containing an unmatched `{` ----
    single_unmatched_open = (
        'prefix prose\n'
        '{"outcome":"CHANGES_REQUIRED","findings":[{"id":"R1","severity":"BLOCKING","required":true,'
        '"path":"x","line":1,"invariant":"a lone { inside this string","evidence":"x","required_action":"fix"}]}'
        '\nsuffix prose'
    )
    result = mr.extract_schema_valid_result(single_unmatched_open, validate=validate)
    assert_true(result["outcome"] == "CHANGES_REQUIRED" and result["findings"][0]["invariant"] == "a lone { inside this string",
                f"Test C: a lone unmatched '{{' inside a string value must not break extraction, got {result}")

    # ---- Test D: escaped quote + brace sequence inside a string ----
    escaped_quote_and_brace = (
        '{"outcome":"CHANGES_REQUIRED","findings":[{"id":"R1","severity":"BLOCKING","required":true,'
        '"path":"x","line":1,"invariant":"a \\"quoted\\" phrase then a lone } brace","evidence":"x","required_action":"fix"}]}'
    )
    result = mr.extract_schema_valid_result(escaped_quote_and_brace, validate=validate)
    assert_true(
        result["outcome"] == "CHANGES_REQUIRED" and result["findings"][0]["invariant"] == 'a "quoted" phrase then a lone } brace',
        f"Test D: an escaped quote immediately followed by an unbalanced brace inside a string must parse correctly, got {result}",
    )

    # ---- Test E: malformed candidate before one valid result ----
    safe = {"outcome": "SAFE", "findings": []}
    safe_text = json.dumps(safe)
    result = mr.extract_schema_valid_result('{"not": valid json here}' + safe_text, validate=validate)
    assert_true(result == safe, "Test E: a malformed candidate preceding a valid one must be skipped, not cause overall failure")

    # ---- Test F: two schema-valid conflicting results -> fail closed ----
    changes_required = {
        "outcome": "CHANGES_REQUIRED",
        "findings": [{"id": "R1", "severity": "HIGH", "required": True, "path": "src/x.py", "line": 1, "invariant": "x", "evidence": "x", "required_action": "x"}],
    }
    conflicting_text = safe_text + " ... on reflection ... " + json.dumps(changes_required)
    raised = False
    try:
        mr.extract_schema_valid_result(conflicting_text, validate=validate)
    except mr.InfrastructureError:
        raised = True
    assert_true(raised, "Test F: two conflicting schema-valid candidates (an early SAFE and a later CHANGES_REQUIRED) must fail closed, never silently resolve to whichever came first")

    # ---- Test G: strict full-document JSON happy path ----
    result = mr.extract_schema_valid_result(safe_text, validate=validate)
    assert_true(result == safe, "Test G: strict full-document JSON happy path must parse directly")

    # ---- Test H: known Claude provider envelope still unwraps correctly ----
    builder_ok = {
        "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
        "summary": "noop",
        "files_touched": [],
        "stop_condition_encountered": None,
        "architecture_decision_required": False,
    }
    envelope_text = json.dumps({"is_error": False, "session_id": "abc-123", "result": json.dumps(builder_ok), "type": "result"})
    envelope = mr._parse_strict_json(envelope_text)
    result = mr.extract_schema_valid_result(envelope["result"], validate=mr.validate_builder_result)
    assert_true(result["status"] == "IMPLEMENTATION_ATTEMPT_COMPLETE", f"Test H: the known Claude envelope shape must still unwrap correctly after the parser fix, got {result}")

    # ---- Test I: known Cursor/noisy-output case still behaves correctly ----
    result = mr.extract_schema_valid_result("I'll read that schema file and return only the requested JSON.\n" + safe_text, validate=validate)
    assert_true(result == safe, f"Test I: the known Cursor noisy-prose-then-JSON shape must still extract correctly, got {result}")

    # ---- Zero schema-valid candidates -> fail closed (retained) ----
    raised = False
    try:
        mr.extract_schema_valid_result("no JSON object anywhere in this text", validate=validate)
    except mr.InfrastructureError:
        raised = True
    assert_true(raised, "zero schema-valid candidates must fail closed")


_test_f6_extraction_cases()
print("PASS F6: fail-closed JSON extraction (json.JSONDecoder().raw_decode-based, never a handwritten brace/string scanner) correctly rejects the exact reproduced false-SAFE attack, correctly handles unmatched braces/escaped-quotes inside string values, a malformed candidate preceding a valid one, the strict happy path, the real Claude envelope shape, and known noisy-prose cases -- and still fails closed on both zero and multiple conflicting schema-valid candidates.")


# ======================================================================
# F7. A fetch failure must fail closed (bounded infra retry), never
# silently fall back to a stale cached origin/main.
# ======================================================================
def _test_f7_fetch_failure(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f7-fetch-failure"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    original_origin_main = mr.load_manifest(mr.run_dir(root, run_id))["origin_main_observed_sha"]

    # Break the origin remote so `git fetch origin main` genuinely fails,
    # while a stale refs/remotes/origin/main ref still resolves locally.
    _git(["remote", "set-url", "origin", str(root / "does-not-exist.git")], root)

    manifest = mr.resume(root, run_id, adapters=_happy_adapters(), max_steps=10)
    assert_true(manifest["phase"] == "HUMAN_REVIEW_REQUIRED", f"a perpetually failing fetch must exhaust the bounded infra retry budget and stop, got {manifest['phase']}")
    assert_true("fetch" in str(manifest.get("stop_reason")).lower(), f"stop_reason must name the fetch failure, got {manifest.get('stop_reason')}")
    assert_true(
        manifest["origin_main_observed_sha"] == original_origin_main,
        "the run's recorded origin_main_observed_sha must never be silently advanced using a stale local ref while fetch itself was failing",
    )


_with_tmp_repo(_test_f7_fetch_failure)
print("PASS F7: a failing `git fetch origin main` is treated as a bounded, retryable infrastructure failure -- it never silently falls back to a stale cached origin/main value, and exhausts to HUMAN_REVIEW_REQUIRED rather than proceeding.")


# ======================================================================
# F8. A lock represents ONE ACTIVE CONTROLLER PROCESS's ownership, never
# merely a matching run_id.
# ======================================================================
def _test_f8a_same_run_id_concurrent_resume(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/f8a-same-run-id"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    # A lock exists for this EXACT run_id (simulating another live
    # process/invocation that is still actively driving this same run).
    lock = mr.acquire_lock(root, branch, run_id=run_id, worktree_path=str(root.resolve()))
    try:
        raised = False
        try:
            mr.resume(root, run_id, adapters=_happy_adapters())
        except mr.LockHeldError:
            raised = True
        assert_true(raised, "a second resume() call must be rejected even when the existing lock's run_id matches -- a lock represents process ownership, never merely run_id identity")
    finally:
        mr.release_lock(root, branch, owner_token=lock["owner_token"])


def _test_f8b_double_stale_recovery(root: Path) -> None:
    """Genuine concurrency, not merely sequential calls: two OS threads
    race to acquire_lock() on the exact same (repo_root, branch) path,
    synchronized to start as close to simultaneously as possible via a
    barrier. Sequential calls would trivially "succeed" every time (each
    would simply see no lock present, or take over the previous one) --
    that would prove nothing about the atomicity claim. Only a real race
    on the same underlying os.open(O_CREAT|O_EXCL) call exercises it."""
    baseline = _base_repo(root)
    branch = "feature/f8b-double-recovery"
    _make_feature_branch(root, branch)
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]

    results: list[str] = []
    barrier = threading.Barrier(2)

    def _attempt(label: str) -> None:
        barrier.wait()
        try:
            mr.acquire_lock(root, branch, run_id=run_id, worktree_path=str(root.resolve()))
            results.append(f"{label}:ACQUIRED")
        except mr.LockHeldError:
            results.append(f"{label}:REJECTED")

    t1 = threading.Thread(target=_attempt, args=("A",))
    t2 = threading.Thread(target=_attempt, args=("B",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    acquired = [r for r in results if r.endswith("ACQUIRED")]
    rejected = [r for r in results if r.endswith("REJECTED")]
    assert_true(len(results) == 2, f"both threads must complete, got {results}")
    assert_true(len(acquired) == 1, f"exactly one of two simultaneous acquire_lock() calls on the same path must succeed, got {results}")
    assert_true(len(rejected) == 1, f"exactly one of two simultaneous acquire_lock() calls must be rejected, got {results}")

    lock = mr.read_lock(root, branch)
    assert_true(lock is not None, "the winning lock must remain in place")
    mr.release_lock(root, branch, owner_token=lock["owner_token"])


_with_tmp_repo(_test_f8a_same_run_id_concurrent_resume)
_with_tmp_repo(_test_f8b_double_stale_recovery)
print("PASS F8: a lock represents one active controller PROCESS's ownership, never merely a matching run_id -- a second resume() with the SAME run_id is still rejected, and two simultaneous stale-lock recovery attempts cannot both succeed.")


# ======================================================================
# F9. The builder adapter correctly unwraps the REAL Claude Code CLI
# envelope shape (empirically captured during this correction pass, NOT
# counted as milestone review).
# ======================================================================
def _test_f9_real_claude_envelope_shape() -> None:
    real_envelope_text = json.dumps(
        {
            "is_error": False,
            "duration_api_ms": 2697,
            "num_turns": 1,
            "stop_reason": "end_turn",
            "session_id": "26820f02-3268-4c12-9468-c18b82fe5ffd",
            "total_cost_usd": 0.185917,
            "usage": {"input_tokens": 2, "output_tokens": 74},
            "subtype": "success",
            "result": json.dumps(
                {
                    "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
                    "summary": "noop",
                    "files_touched": [],
                    "stop_condition_encountered": None,
                    "architecture_decision_required": False,
                }
            ),
            "type": "result",
        }
    )
    envelope = mr._parse_strict_json(real_envelope_text)
    assert_true(isinstance(envelope.get("result"), str), "the real envelope's own 'result' field must be a string, not the builder's structured object directly")
    result = mr.extract_schema_valid_result(envelope["result"], validate=mr.validate_builder_result)
    assert_true(result["status"] == "IMPLEMENTATION_ATTEMPT_COMPLETE", f"must correctly unwrap the real Claude Code CLI envelope shape, got {result}")


_test_f9_real_claude_envelope_shape()
print("PASS F9: the builder adapter correctly unwraps the empirically-verified real Claude Code CLI envelope shape (outer envelope's 'result' field is a free-text string containing the builder's own JSON reply, not the structured result directly).")


# ======================================================================
# ALSO TEST: untracked/deleted/staged mutations all change the diff
# fingerprint (evidence invalidation depends on this).
# ======================================================================
def _test_also_fingerprint_sensitivity(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/fingerprint-sensitivity"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")

    fp_clean = mr.compute_diff_fingerprint(root, baseline)

    _write(root, "src/new_untracked.py", "y = 1\n")
    fp_untracked_added = mr.compute_diff_fingerprint(root, baseline)
    assert_true(fp_untracked_added != fp_clean, "adding a new untracked file must change the fingerprint")
    (root / "src" / "new_untracked.py").unlink()

    (root / "src" / "thing.py").unlink()
    fp_deleted = mr.compute_diff_fingerprint(root, baseline)
    assert_true(fp_deleted != fp_clean, "deleting a tracked file must change the fingerprint")
    _write(root, "src/thing.py", "x = 1\n")

    _write(root, "src/thing.py", "x = 1\nstaged_change = True\n")
    _git(["add", "src/thing.py"], root)
    fp_staged = mr.compute_diff_fingerprint(root, baseline)
    assert_true(fp_staged != fp_clean, "a staged (but uncommitted) change must change the fingerprint")


_with_tmp_repo(_test_also_fingerprint_sensitivity)
print("PASS ALSO-1: untracked-file addition, tracked-file deletion, and a staged-but-uncommitted change each independently change the diff fingerprint.")


# ======================================================================
# ALSO TEST: infrastructure_retry_count and other counters survive a
# resume() (i.e. a fresh process invocation reconstructing from disk).
# ======================================================================
def _test_also_counters_survive_resume(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/counters-survive-resume"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]

    adapters = mr.Adapters(
        builder_invoker=fake_builder([mr.InfrastructureError("boom"), BUILDER_OK]),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    manifest = mr.advance(root, run_id, adapters)  # BUILDING fails once -> self-loop, retry_count=1
    assert_true(manifest["infrastructure_retry_count"] == 1, f"setup: expected infrastructure_retry_count=1, got {manifest['infrastructure_retry_count']}")

    # Simulate a fresh process: resume() re-reads the manifest from disk.
    manifest2 = mr.resume(root, run_id, adapters=adapters)
    assert_true(manifest2["phase"] == "READY_FOR_HUMAN_APPROVAL", f"resume must complete the run using the persisted retry count, got {manifest2['phase']}")
    assert_true(manifest2["infrastructure_retry_count"] == 1, f"the retry count from before the simulated process boundary must be preserved, not reset, got {manifest2['infrastructure_retry_count']}")


_with_tmp_repo(_test_also_counters_survive_resume)
print("PASS ALSO-2: infrastructure_retry_count (and other run counters) persist correctly across a resume() call simulating a fresh process boundary -- never silently reset.")


# ======================================================================
# ALSO TEST: no new unbounded loop -- a perpetually-mutating adversarial
# scenario (external mutation between every TESTING/REVIEWING pass)
# still terminates within max_steps, never runs forever. Documented
# limitation: this specific TESTING<->REVIEWING bounce has no dedicated
# budget/counter of its own beyond the outer max_steps bound (see the
# correction report's Known Limitations).
# ======================================================================
def _test_also_no_unbounded_loop(root: Path) -> None:
    baseline = _base_repo(root)
    branch = "feature/no-unbounded-loop"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    def _reviewer_that_causes_perpetual_bounce(*, prompt, cwd, policy):
        # Every time REVIEWING's own action actually runs, mutate the
        # tree AFTER the fact is impossible from here (this fake IS the
        # reviewer) -- instead exercise the bound via the test_runner,
        # which mutates on every call, perpetually invalidating its own
        # evidence before REVIEWING can ever see a stable fingerprint.
        return REVIEWER_SAFE

    call_count = {"n": 0}

    def _perpetually_mutating_test_runner(repo_root, test_paths, *, rdir):
        call_count["n"] += 1
        _write(repo_root, "src/thing.py", f"x = {call_count['n']}  # perpetually mutated\n")
        artifact = {"ok": True, "results": [], "at": "x"}
        path = rdir / "tests" / f"fake-{call_count['n']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact), encoding="utf-8")
        return {"ok": True, "artifact_path": str(path), "results": []}

    adapters = mr.Adapters(
        builder_invoker=fake_builder([BUILDER_OK] * 100),
        reviewer_invoker=_reviewer_that_causes_perpetual_bounce,
        test_runner=_perpetually_mutating_test_runner,
        assurance_runner=fake_assurance_runner(True),
    )
    manifest = mr.run(root, contract_path, policy_path, adapters=adapters, max_steps=30)
    assert_true(manifest["phase"] not in ("READY_FOR_HUMAN_APPROVAL",), "a perpetually-mutating scenario must never spuriously reach READY")
    assert_true(call_count["n"] <= 30, f"the run must terminate within the max_steps bound, never execute unboundedly, got {call_count['n']} test-runner calls")


_with_tmp_repo(_test_also_no_unbounded_loop)
print("PASS ALSO-3: a perpetually-mutating adversarial scenario (evidence invalidated on every single pass) terminates within the max_steps bound rather than running forever -- documented limitation: this specific bounce has no dedicated budget of its own beyond max_steps.")


# ======================================================================
# CAREER_OS_CLAUDE_BUILDER_ARGV_ORDERING_FIX_V1 -- regression coverage.
#
# Pass 1 defect: --allowedTools <tools...> is a Commander.js VARIADIC
# option in the real Claude Code CLI -- it greedily consumes every
# subsequent positional argument, including the prompt, as an additional
# tool-name value. Placing the prompt after --allowedTools left the CLI
# with zero positional prompt arguments, always failing with "Input must
# be provided either through stdin or as a prompt argument when using
# --print". First-fix attempt: move the prompt to be the very first
# argument, before every flag.
#
# Pass 2 defect (Cursor rereview, ARGV-W1 leading-dash finding):
# prompt-first is insufficient -- a prompt beginning with '-' or '--' is
# misparsed as an option token regardless of position, independently
# reproduced against the real CLI both before and after this correction.
# The final fix places every flag first, then the literal '--'
# positional-terminator, then the prompt last -- verified directly
# against the real CLI to correctly handle a normal prompt, a multiline
# prompt, a leading-dash prompt, a leading-double-dash prompt, a prompt
# containing the literal substring "--allowedTools", and a Unicode
# prompt, all six intact.
#
# ARGV-W1 also required correcting binary resolution: on Windows,
# shutil.which("claude") resolves to the argv-corrupting claude.CMD
# wrapper (which truncates multiline prompts at the first newline via
# cmd.exe's %* re-expansion -- independently reproduced: a real 3-line
# prompt arrived as only "line one"). _find_claude_binary() now prefers
# the native claude.exe sibling when available and fails closed
# (InfrastructureError) rather than silently using a wrapper known to
# corrupt prompt content.
# ======================================================================

def _write_fake_claude_shim(tmp_dir: Path) -> Path:
    """A small fake 'claude'-like CLI (a plain Python script) that MODELS
    the real CLI's argument-parsing behavior -- variadic --allowedTools
    consumption, a '--' positional terminator, and rejection of an
    unrecognized leading-dash token before '--' is seen -- not a mock of
    milestone_run.py's own code. This proves the constructed argv is
    actually correct at the real subprocess/argv-parsing boundary, not
    merely via a static list assertion. The positional prompt (found
    either before any flag, in the ORIGINAL prompt-first shape, or after
    '--', in the CORRECTED shape) is echoed back byte-for-byte inside a
    valid envelope for exact content-fidelity checks.

    IMPORTANT: this returns the bare `.py` script path -- callers MUST
    invoke it as a genuine native process (`[sys.executable, path, ...]`,
    see `_native_run_subprocess`), never wrapped in a `.cmd`/`.bat`
    shim. An earlier version of this fixture wrapped the script in a
    `claude.cmd` file to mirror the real npm-installed layout, but that
    accidentally routed every invocation through cmd.exe's own `%*`
    argument re-expansion -- which mangles embedded newlines completely
    independently of anything in milestone_run.py, exactly the same
    Windows batch-file limitation ARGV-W1's production fix exists to
    route AROUND (by always preferring a native executable). Testing
    through that same limitation here would confound the test with an
    unrelated fixture bug rather than exercising the corrected code
    path, which -- after the ARGV-W1 fix -- never invokes a `.cmd`
    wrapper for real work in the first place."""
    fake_py = tmp_dir / "fake_claude.py"
    fake_py.write_text(
        "import sys, json\n"
        "args = sys.argv[1:]\n"
        "VALUE_FLAGS = {'--output-format', '--permission-mode', '--resume'}\n"
        "NOARG_FLAGS = {'-p'}\n"
        "i = 0\n"
        "prompt = None\n"
        "saw_terminator = False\n"
        "error = None\n"
        "while i < len(args):\n"
        "    tok = args[i]\n"
        "    if not saw_terminator and tok == '--':\n"
        "        saw_terminator = True; i += 1; continue\n"
        "    if not saw_terminator and tok in NOARG_FLAGS:\n"
        "        i += 1; continue\n"
        "    if not saw_terminator and tok in VALUE_FLAGS:\n"
        "        i += 2; continue\n"
        "    if not saw_terminator and tok == '--allowedTools':\n"
        "        i += 1\n"
        "        # VARIADIC: consume every following token until '--', a\n"
        "        # recognized flag, or end -- the real CLI's actual\n"
        "        # documented behavior, and the exact mechanism of the bug.\n"
        "        while i < len(args) and args[i] != '--' and args[i] not in VALUE_FLAGS and args[i] not in NOARG_FLAGS and args[i] != '--allowedTools':\n"
        "            i += 1\n"
        "        continue\n"
        "    if not saw_terminator and tok.startswith('-') and tok not in NOARG_FLAGS and tok not in VALUE_FLAGS:\n"
        "        error = f\"error: unknown option '{tok}'\"\n"
        "        break\n"
        "    if prompt is None:\n"
        "        prompt = tok\n"
        "    i += 1\n"
        "if error is not None:\n"
        "    sys.stderr.write(error + '\\n')\n"
        "    sys.exit(1)\n"
        "if prompt is None:\n"
        "    sys.stderr.write('Error: Input must be provided either through stdin or as a prompt argument when using --print\\n')\n"
        "    sys.exit(1)\n"
        "envelope = {\n"
        "    'is_error': False,\n"
        "    'session_id': 'fake-session-id',\n"
        "    'result': json.dumps({\n"
        "        'status': 'IMPLEMENTATION_ATTEMPT_COMPLETE',\n"
        "        'summary': 'fake shim received prompt',\n"
        "        'files_touched': [],\n"
        "        'stop_condition_encountered': None,\n"
        "        'architecture_decision_required': False,\n"
        "        '_echoed_prompt': prompt,\n"
        "    }),\n"
        "    'type': 'result',\n"
        "}\n"
        "sys.stdout.reconfigure(encoding='utf-8')\n"
        "print(json.dumps(envelope))\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    return fake_py


def _native_run_subprocess(fake_py: Path):
    """Wraps the REAL mr._run_subprocess_streams so that whatever
    placeholder `claude_bin` string real_claude_builder_invoker()
    constructed argv with is replaced, at the last moment, by a genuine
    native-process invocation of the fake CLI script -- `[sys.executable,
    fake_py]`, a real PE executable, no cmd.exe indirection -- while every
    other constructed argv element (flags, --allowedTools value, the '--'
    terminator, the prompt itself) passes through completely unchanged.
    This exercises the real argv-construction code in
    real_claude_builder_invoker() end-to-end through a real subprocess
    boundary, structurally equivalent to how the corrected production
    code invokes a native claude.exe."""
    original = mr._run_subprocess_streams

    def _wrapped(args, *, cwd, timeout=600):
        native_args = [sys.executable, str(fake_py)] + list(args[1:])
        return original(native_args, cwd=cwd, timeout=timeout)

    return _wrapped


# Requirement ARGV-T1, cases A-H: exact character-for-character prompts.
ARGV_FIDELITY_CASES: dict[str, str] = {
    "A_spaces": "plain prompt with several   embedded   spaces",
    "B_newlines": "line one\nline two\n\nline four after a blank line\nline five",
    "C_braces_quotes": 'prompt with {curly braces} and "double quotes" and \'single quotes\'',
    "D_command_like": "prompt; rm -rf /  && echo pwned # command-like text that must never be interpreted",
    "E_literal_allowedtools_token": "this text contains the literal token --allowedTools embedded inside it",
    "F_commas": "prompt, with, several, embedded, commas, like, a, tool, list",
    "G_leading_dash": "--this prompt itself begins with a double dash and must not be parsed as an option",
    "H_unicode": "Unicode payload: \u00e9\u00e8\u00fc\u00f1 \u4e2d\u6587\u5b57\u7b26 \U0001F600\U0001F680 \u0645\u0631\u062d\u0628\u0627",
}


def _test_argv_ordering_boundary_shim_exact_fidelity() -> None:
    """Requirement ARGV-T1: assert EXACT character-for-character equality
    between the expected prompt and the prompt actually received at the
    fake CLI boundary, for every case A-H -- not merely 'some prompt
    survived'. Fails on any lost, inserted, reordered, normalized, or
    otherwise altered character."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="claude_shim_fidelity_test_"))
    try:
        fake_py = _write_fake_claude_shim(tmp_dir)
        original_find_claude_binary = mr._find_claude_binary
        original_run_subprocess_streams = mr._run_subprocess_streams
        mr._find_claude_binary = lambda: "claude-placeholder"
        mr._run_subprocess_streams = _native_run_subprocess(fake_py)
        try:
            for label, expected_prompt in ARGV_FIDELITY_CASES.items():
                result = mr.real_claude_builder_invoker(
                    prompt=expected_prompt, cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None
                )
                assert_true(
                    result.get("summary") == "fake shim received prompt",
                    f"Case {label}: the prompt must be received as the genuine positional prompt, got {result}",
                )
                received_prompt = result.get("_echoed_prompt")
                assert_true(
                    received_prompt == expected_prompt,
                    f"Case {label}: the prompt must arrive EXACTLY character-for-character intact.\nExpected: {expected_prompt!r}\nReceived: {received_prompt!r}",
                )
        finally:
            mr._find_claude_binary = original_find_claude_binary
            mr._run_subprocess_streams = original_run_subprocess_streams
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


_test_argv_ordering_boundary_shim_exact_fidelity()
print("PASS ARGV-FIX-1: cases A-H (spaces, newlines, braces/quotes, command-like text, a literal '--allowedTools' substring, commas, a leading-dash prompt, and Unicode) all arrive at the fake CLI boundary EXACTLY character-for-character intact -- not merely 'some prompt survived'.")


def _test_argv_ordering_boundary_shim_negative_controls() -> None:
    """Negative controls: prove the shim itself genuinely reproduces (a)
    the ORIGINAL Pass-1 bug (prompt after --allowedTools, no terminator)
    and (b) the Pass-1-fix's own insufficiency (a leading-dash prompt
    placed FIRST, without a '--' terminator) -- confirming this exact
    test harness would have caught both real defects, not merely that
    the current (corrected) production code happens to pass."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="claude_shim_regression_test_"))
    try:
        fake_py = _write_fake_claude_shim(tmp_dir)

        # (a) original Pass-1 defect: prompt after --allowedTools, no '--'.
        # Invoked as a genuine native process ([sys.executable, fake_py,
        # ...]), same as the fidelity test -- no cmd.exe indirection.
        broken_args_pass1 = [
            sys.executable, str(fake_py), "-p", "--output-format", "json", "--permission-mode", "acceptEdits",
            "--allowedTools", "Read,Write,Edit,Glob,Grep", "this prompt must be swallowed",
        ]
        ok, output = mr._run_subprocess(broken_args_pass1, cwd=Path("."), timeout=30)
        assert_true(not ok, "the shim must reproduce the ORIGINAL Pass-1 failure when the prompt is placed after --allowedTools with no terminator")
        assert_true(
            "Input must be provided either through stdin or as a prompt argument" in output,
            f"the shim must reproduce the exact real CLI Pass-1 error message, got {output!r}",
        )

        # (b) Pass-1-fix insufficiency: leading-dash prompt placed FIRST,
        # before any flag, with no '--' terminator -- this is exactly
        # the shape the first (insufficient) correction used.
        broken_args_pass1fix = [
            sys.executable, str(fake_py), "--this leading-dash prompt would be placed first", "-p",
            "--output-format", "json", "--permission-mode", "acceptEdits",
            "--allowedTools", "Read,Write,Edit,Glob,Grep",
        ]
        ok2, output2 = mr._run_subprocess(broken_args_pass1fix, cwd=Path("."), timeout=30)
        assert_true(not ok2, "the shim must reproduce the Pass-1-fix's own insufficiency: a leading-dash prompt placed first, with no '--' terminator, must still fail")
        assert_true(
            "unknown option" in output2,
            f"a leading-dash prompt placed first without a terminator must be rejected as an unrecognized option, got {output2!r}",
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


_test_argv_ordering_boundary_shim_negative_controls()
print("PASS ARGV-FIX-1-NEG: negative controls confirm this test harness would have caught BOTH the original Pass-1 defect (prompt swallowed by --allowedTools) AND the Pass-1-fix's own insufficiency (a leading-dash prompt placed first without a '--' terminator is still misparsed as an option).")


def _test_argv_static_structure_and_flags() -> None:
    """Requirements #1, #3, #4, #5, #6, #7: static assertions on the
    constructed argv and unchanged surrounding behavior, using a
    recording fake subprocess runner (fast, no real process needed)."""
    recorded: dict[str, Any] = {}
    original_run_subprocess_streams = mr._run_subprocess_streams

    def _recording_run_subprocess(args, *, cwd, timeout=600):
        recorded["args"] = list(args)
        recorded["timeout"] = timeout
        return True, json.dumps(
            {
                "is_error": False,
                "session_id": "rec-session",
                "result": json.dumps(
                    {
                        "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
                        "summary": "ok",
                        "files_touched": [],
                        "stop_condition_encountered": None,
                        "architecture_decision_required": False,
                    }
                ),
                "type": "result",
            }
        ), ""

    mr._run_subprocess_streams = _recording_run_subprocess
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    try:
        mr.real_claude_builder_invoker(
            prompt="a real prompt", cwd=Path("."), policy={"builder_timeout_seconds": 123}, session_id=None
        )
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary

    args = recorded["args"]
    # The prompt must be the LAST argv element, immediately preceded by
    # a literal '--' terminator, so it can never be swallowed by
    # --allowedTools's variadic consumption nor misparsed as an option
    # even if it begins with '-' or '--'.
    assert_true(args[-1] == "a real prompt", f"the prompt must be the final argv element, got {args}")
    assert_true(args[-2] == "--", f"the prompt must be immediately preceded by a literal '--' terminator, got {args}")
    allowed_tools_idx = args.index("--allowedTools")
    assert_true(allowed_tools_idx < len(args) - 2, f"--allowedTools must appear before the '--' terminator, got {args}")

    # 3. allowed tools unchanged (same five tools, whatever separator convention).
    tools_value = args[allowed_tools_idx + 1]
    tools_set = {t.strip() for t in tools_value.replace(",", " ").split()}
    assert_true(tools_set == {"Read", "Write", "Edit", "Glob", "Grep"}, f"the allowed tool set must remain exactly Read/Write/Edit/Glob/Grep, got {tools_set}")

    # 4. --output-format json still present.
    assert_true("--output-format" in args and args[args.index("--output-format") + 1] == "json", "the --output-format json flag must remain present")

    # 5. --permission-mode unchanged.
    assert_true("--permission-mode" in args and args[args.index("--permission-mode") + 1] == "acceptEdits", "the --permission-mode flag must remain acceptEdits, unchanged")

    # 6. timeout behavior unchanged -- the policy's builder_timeout_seconds is forwarded as-is.
    assert_true(recorded["timeout"] == 123, f"builder_timeout_seconds must still be forwarded to the subprocess call unchanged, got {recorded['timeout']}")

    # No shell invocation is ever introduced -- args[0] is a plain
    # executable path/string, and _run_subprocess_streams never sets
    # shell=True anywhere in this module.
    # Scoped to the actual subprocess.run() call sites (_run_git,
    # _run_subprocess_streams, _is_ancestor -- _run_subprocess itself now
    # just delegates to _run_subprocess_streams and no longer calls
    # subprocess.run directly) rather than the whole module -- scanning
    # the whole module would false-positive on this very docstring's own
    # prose explaining that shell=True was NOT used.
    for fn in (mr._run_git, mr._run_subprocess, mr._run_subprocess_streams, mr._is_ancestor):
        assert_true("shell=True" not in inspect.getsource(fn) and "shell = True" not in inspect.getsource(fn), f"{fn.__name__} must never introduce a shell=True subprocess invocation")


_test_argv_static_structure_and_flags()
print("PASS ARGV-FIX-2: static argv assertions confirm the prompt is the final argv element immediately preceded by a literal '--' terminator (never swallowed by --allowedTools, never misparsed even if it begins with '-'), --allowedTools/--output-format/--permission-mode are unchanged, builder_timeout_seconds is still forwarded unchanged, and no shell=True invocation exists anywhere in the module.")


def _test_argv_fix_fail_closed_on_nonzero_and_malformed() -> None:
    """Requirement #7: a nonzero subprocess exit, and a malformed
    envelope, must both still fail closed (InfrastructureError) -- the
    argv/binary-resolution correction must not have weakened this
    existing behavior."""
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"

    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (False, "", "simulated nonzero exit")
    raised = False
    try:
        mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
    except mr.InfrastructureError:
        raised = True
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
    assert_true(raised, "a nonzero subprocess exit must still raise InfrastructureError (fail closed), unchanged by this correction")

    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (True, "not even json", "")
    raised = False
    try:
        mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
    except mr.InfrastructureError:
        raised = True
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary
    assert_true(raised, "a malformed (non-JSON) envelope must still raise InfrastructureError (fail closed), unchanged by this correction")


_test_argv_fix_fail_closed_on_nonzero_and_malformed()
print("PASS ARGV-FIX-3: a nonzero subprocess exit and a malformed envelope both still fail closed with InfrastructureError, unchanged by this correction.")


# ======================================================================
# ARGV-W1: binary-resolution correction (native claude.exe preferred
# over the argv-corrupting claude.CMD wrapper on Windows).
# ======================================================================
def _test_argv_w1_prefers_native_exe_over_cmd_wrapper() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="claude_binres_test_"))
    try:
        wrapper_dir = tmp_dir / "npmglobal"
        wrapper_dir.mkdir(parents=True)
        cmd_path = wrapper_dir / "claude.cmd"
        cmd_path.write_text("@echo off\r\n", encoding="utf-8")
        native_dir = wrapper_dir / "node_modules" / "@anthropic-ai" / "claude-code" / "bin"
        native_dir.mkdir(parents=True)
        native_path = native_dir / "claude.exe"
        native_path.write_text("", encoding="utf-8")

        original_which = mr.shutil.which
        mr.shutil.which = lambda name: str(cmd_path) if name == "claude" else original_which(name)
        try:
            resolved = mr._find_claude_binary()
        finally:
            mr.shutil.which = original_which
        assert_true(
            Path(resolved) == native_path,
            f"when a native claude.exe sibling exists next to the claude.cmd wrapper, it must be preferred over the wrapper, got {resolved}",
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _test_argv_w1_fails_closed_when_only_wrapper_exists() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="claude_binres_failclosed_test_"))
    try:
        wrapper_dir = tmp_dir / "npmglobal"
        wrapper_dir.mkdir(parents=True)
        cmd_path = wrapper_dir / "claude.cmd"
        cmd_path.write_text("@echo off\r\n", encoding="utf-8")
        # Deliberately do NOT create the native sibling executable.

        original_which = mr.shutil.which
        mr.shutil.which = lambda name: str(cmd_path) if name == "claude" else original_which(name)
        try:
            raised = False
            try:
                mr._find_claude_binary()
            except mr.InfrastructureError:
                raised = True
            assert_true(raised, "when only the argv-corrupting claude.cmd wrapper exists (no native sibling), resolution must fail closed rather than silently use the wrapper")
        finally:
            mr.shutil.which = original_which
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _test_argv_w1_non_windows_style_path_passthrough() -> None:
    """A which() result that is not a .cmd (e.g. a bare POSIX script, or
    an already-native .exe) is used unchanged -- non-Windows behavior,
    and an already-native Windows result, are both untouched."""
    original_which = mr.shutil.which
    mr.shutil.which = lambda name: "/usr/local/bin/claude" if name == "claude" else original_which(name)
    try:
        resolved = mr._find_claude_binary()
    finally:
        mr.shutil.which = original_which
    assert_true(resolved == "/usr/local/bin/claude", f"a non-.cmd which() result must be used unchanged, got {resolved}")


_test_argv_w1_prefers_native_exe_over_cmd_wrapper()
_test_argv_w1_fails_closed_when_only_wrapper_exists()
_test_argv_w1_non_windows_style_path_passthrough()
print("PASS ARGV-W1: _find_claude_binary() prefers a native claude.exe sibling over the claude.cmd wrapper when available, fails closed (InfrastructureError) when only the corrupting wrapper exists with no native sibling, and leaves an already-non-.cmd which() result (POSIX script or already-native executable) unchanged.")


# ======================================================================
# CAREER_OS_BUILDER_SESSION_RECOVERY_AND_STRUCTURED_COMPLETION_V1
#
# Reproduced on the second real controller run (run_id
# 20260907T193310Z-f6a756d2): the builder genuinely did substantial real
# work across 3 independent attempts, but each attempt's final reply was
# conversational prose rather than the required structured JSON result,
# so extract_schema_valid_result() raised on all three -- and, before
# this fix, each retry silently discarded a perfectly good, resumable
# session_id and started a brand new session from zero, with no memory
# of the already-completed work.
#
# Covers the milestone's 12 numbered required scenarios; mapping (not
# every scenario needs a fully separate test where the same underlying
# mechanism already proves it, per this file's own docstring):
#   SR-1  -> (1)
#   SR-2  -> (2), (5)
#   SR-3  -> (3)
#   SR-4  -> (4)
#   SR-5  -> (6)
#   SR-6  -> (7)
#   SR-7  -> (8)
#   SR-8  -> (9)
#   SR-9  -> (10)
#   SR-10 -> (11)
#   SR-11 -> (12)
#
# BOUNDED CORRECTION PASS (Cursor CHANGES_REQUIRED, findings SR-CRASH-1
# and SR-WS-1) -- mapping to that correction pass's own 12 numbered
# required regression tests:
#   SR-CRASH-1  -> (1) crash/desync recovery, (2) resumed invocation
#                  receives exact recovered session id, (3) narrow
#                  resumed-completion prompt used after reconstruction
#   SR-CRASH-1b -> (4) stale recovered event + BUILDER_INVOKED -> no
#                  false pending recovery
#   SR-CRASH-1c -> (5) multiple recovery events -> latest still-pending
#                  one governs
#   SR-WS-1a    -> (6) whitespace-only session id -> plain
#                  InfrastructureError
#   SR-WS-1b    -> (7) leading/trailing whitespace -> stripped canonical
#                  id persisted/resumed
#   SR-WS-1c    -> (8) missing/non-string/empty session id -> fail-closed
#                  (already covered for the None/missing case by SR-6;
#                  extended here to the empty-string and non-string forms
#                  named explicitly in SR-WS-1's own examples)
#   (9) malformed outer envelope cannot seed recovery -- already covered
#       by SR-5, unaffected by this correction, not duplicated here
#   (10) conflicting inner structured results still fail closed --
#        already covered by SR-8, unaffected by this correction
#   (11) normal successful builder path unchanged -- already covered by
#        SR-9, re-exercised implicitly by SR-CRASH-1's own happy-path tail
#   (12) REPAIRING / CORRECTING_REVIEW session lifecycle unchanged --
#        already covered by SR-10; the crash-reconstruction path only
#        engages via _pending_recovered_session_id(), which SR-10's own
#        scenario never populates, so that coverage still applies
#        unmodified
# ======================================================================

def _recording_fake_builder(sequence: list) -> callable:
    """Like fake_builder(), but also records every call's (prompt,
    session_id) so a test can assert exactly what was sent on a
    resumed retry, not merely what was returned."""
    calls: list[dict] = []

    def _invoke(*, prompt, cwd, policy, session_id):
        calls.append({"prompt": prompt, "session_id": session_id})
        idx = min(len(calls) - 1, len(sequence) - 1)
        item = sequence[idx]
        if isinstance(item, Exception):
            raise item
        return item

    _invoke.calls = calls
    return _invoke


def _test_sr1_recoverable_on_valid_envelope_invalid_inner() -> None:
    """(1) A valid outer provider envelope carrying a trustworthy
    session_id, but an inner result that fails schema-valid extraction
    (Claude finished real work but replied in prose, not JSON), must
    fail closed as RecoverableSessionInfrastructureError -- never a
    plain InfrastructureError that would silently discard the session."""
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (
        True,
        json.dumps(
            {
                "is_error": False,
                "session_id": "sess-recoverable-1",
                "result": "Audit complete. The report is done and everything checks out.",
                "type": "result",
            }
        ),
        "",
    )
    try:
        raised = None
        try:
            mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
        except mr.RecoverableSessionInfrastructureError as exc:
            raised = exc
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary
    assert_true(raised is not None, "an inner-validation failure accompanying a valid session_id must raise RecoverableSessionInfrastructureError")
    assert_true(raised.session_id == "sess-recoverable-1", f"the recoverable exception must carry the real session_id forward, got {getattr(raised, 'session_id', None)}")


_test_sr1_recoverable_on_valid_envelope_invalid_inner()
print("PASS SR-1: a valid outer envelope with a trustworthy session_id but a failed inner-result extraction raises RecoverableSessionInfrastructureError carrying that exact session_id, never a plain InfrastructureError that would discard it.")


def _test_sr2_retry_receives_and_resumes_recovered_session(root: Path) -> None:
    """(2) The very next retry after a recoverable failure receives the
    exact recovered session_id. (5) A successful resumed retry
    transitions normally onward to TESTING."""
    baseline = _base_repo(root)
    branch = "feature/sr2-retry-session"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    builder = _recording_fake_builder(
        [mr.RecoverableSessionInfrastructureError("prose instead of json", session_id="sess-abc"), BUILDER_OK]
    )
    adapters = mr.Adapters(
        builder_invoker=builder,
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    manifest = mr.advance(root, run_id, adapters)  # BUILDING raises recoverable -> self-loop
    assert_true(manifest["phase"] == "BUILDING", f"a recoverable session failure must self-loop back to BUILDING, got {manifest['phase']}")
    assert_true(manifest["builder_session_id"] == "sess-abc", f"the recovered session_id must be persisted onto the manifest, got {manifest.get('builder_session_id')}")

    expected_contract = _contract(branch, baseline)
    expected_resumed_prompt = mr.build_resumed_completion_prompt(expected_contract)

    manifest = mr.advance(root, run_id, adapters)  # BUILDING retries, resumed
    assert_true(len(builder.calls) == 2, f"expected exactly 2 builder calls by now, got {len(builder.calls)}")
    assert_true(builder.calls[1]["session_id"] == "sess-abc", f"the resumed retry must receive the exact recovered session_id, got {builder.calls[1]['session_id']}")
    assert_true(builder.calls[1]["prompt"] == expected_resumed_prompt, "the resumed retry must use the narrow completion-focused prompt, not the full original task prompt")
    assert_true(manifest["phase"] == "TESTING", f"a successful resumed retry must transition normally onward to TESTING, got {manifest['phase']}")


_with_tmp_repo(_test_sr2_retry_receives_and_resumes_recovered_session)
print("PASS SR-2: after a recoverable session failure, the recovered session_id is persisted onto the manifest, the very next retry both receives that exact session_id and uses the narrow resumed-completion prompt, and a successful resumed retry transitions normally onward to TESTING.")


def _test_sr3_resumed_invocation_includes_resume_flag() -> None:
    """(3) The resumed invocation's constructed argv actually includes
    `--resume <session_id>` at the real adapter/CLI-argv level, not just
    the manifest bookkeeping level."""
    recorded_calls: list[list] = []
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"

    def _recording_run_subprocess(args, *, cwd, timeout=600):
        recorded_calls.append(list(args))
        return True, json.dumps(
            {
                "is_error": False,
                "session_id": "sess-resume-3",
                "result": json.dumps(
                    {
                        "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
                        "summary": "done",
                        "files_touched": [],
                        "stop_condition_encountered": None,
                        "architecture_decision_required": False,
                    }
                ),
                "type": "result",
            }
        ), ""

    mr._run_subprocess_streams = _recording_run_subprocess
    try:
        mr.real_claude_builder_invoker(
            prompt="resumed completion prompt", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id="sess-resume-3"
        )
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary

    args = recorded_calls[0]
    assert_true("--resume" in args, f"a resumed invocation must include --resume, got {args}")
    resume_idx = args.index("--resume")
    assert_true(args[resume_idx + 1] == "sess-resume-3", f"--resume must be immediately followed by the exact recovered session_id, got {args}")
    assert_true(resume_idx < len(args) - 2, f"--resume <id> must appear before the '--' terminator and the prompt, got {args}")


_test_sr3_resumed_invocation_includes_resume_flag()
print("PASS SR-3: a resumed builder invocation's constructed argv actually includes --resume immediately followed by the exact recovered session_id, positioned before the '--' terminator and the prompt.")


def _test_sr4_resumed_prompt_is_narrow_and_completion_focused() -> None:
    """(4) The resumed retry's own instruction text is completion-focused
    and does not authorize broader/new work -- distinct in both content
    and identity from the full original task prompt."""
    contract = _contract("feature/sr4-narrow-prompt", "0" * 40)
    resumed_prompt = mr.build_resumed_completion_prompt(contract)
    full_prompt = mr.build_builder_prompt(contract)

    assert_true(resumed_prompt != full_prompt, "the resumed completion prompt must not be identical to the full original task prompt")
    assert_true("IMPLEMENTATION_ATTEMPT_COMPLETE" in resumed_prompt, "the resumed prompt must name the exact required success status literal")
    assert_true("STOPPED" in resumed_prompt, "the resumed prompt must name the exact required stop status literal")
    assert_true("Do NOT restart" in resumed_prompt or "do not restart" in resumed_prompt.lower(), "the resumed prompt must explicitly forbid restarting/broadening the task")
    assert_true(contract["milestone_id"] in resumed_prompt, "the resumed prompt must still identify the correct milestone")
    # It must not re-carry a fresh copy of the full allowed/forbidden path
    # boilerplate -- that context already lives inside the resumed
    # session itself; re-issuing it would look like (and could be
    # misread as) a fresh, broader task specification.
    assert_true(contract["goal"] not in resumed_prompt, "the resumed prompt must not restate the full original goal text as if reissuing the whole task")


_test_sr4_resumed_prompt_is_narrow_and_completion_focused()
print("PASS SR-4: the resumed-retry prompt is narrow and completion-focused -- it names the exact required JSON status literals, explicitly forbids restarting/broadening the task, and is textually distinct from the full original task prompt.")


def _test_sr5_malformed_envelope_no_recovery() -> None:
    """(6) An outer envelope that is not even valid JSON must remain an
    ordinary, non-recoverable InfrastructureError -- untrusted output
    must never be upgraded into a session-recovery path."""
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (True, "not even json", "")
    try:
        raised_type = None
        try:
            mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
        except mr.InfrastructureError as exc:
            raised_type = type(exc)
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary
    assert_true(raised_type is mr.InfrastructureError, f"a malformed (non-JSON) outer envelope must raise plain InfrastructureError, never the recoverable subtype, got {raised_type}")


_test_sr5_malformed_envelope_no_recovery()
print("PASS SR-5: a malformed (non-JSON) outer provider envelope remains a plain, non-recoverable InfrastructureError -- ordinary bounded infrastructure retry, no session recovery.")


def _test_sr6_no_session_id_no_invented_recovery() -> None:
    """(7) A valid, well-formed envelope with no session_id at all must
    never invent or trust a session -- fail closed as a plain, ordinary
    InfrastructureError."""
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (
        True, json.dumps({"is_error": False, "result": "just prose, no json, and no session_id field at all", "type": "result"}), ""
    )
    try:
        raised_type = None
        try:
            mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
        except mr.InfrastructureError as exc:
            raised_type = type(exc)
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary
    assert_true(raised_type is mr.InfrastructureError, f"a valid envelope with no session_id must never invent/trust a session -- plain InfrastructureError only, got {raised_type}")


_test_sr6_no_session_id_no_invented_recovery()
print("PASS SR-6: a valid, well-formed envelope carrying no session_id at all never invents or trusts a session -- plain InfrastructureError, fail closed, unchanged.")


def _test_sr7_recoverable_failure_never_treated_as_success(root: Path) -> None:
    """(8) An invalid inner result -- even a recoverable one, even with
    real in-scope file changes already present in the working tree --
    must NEVER be treated as success. The run must stay bounded in
    BUILDING (self-looping, retry-counted) and never reach TESTING or
    any terminal success state merely because files changed."""
    baseline = _base_repo(root)
    branch = "feature/sr7-no-fake-success"
    _make_feature_branch(root, branch)
    # A real, substantial, in-scope file change already sitting in the
    # working tree -- exactly the misleading signal a naive "did files
    # change?" heuristic could be fooled by.
    _write(root, "src/thing.py", "x = 1\nsubstantial_change = True\n")
    _commit(root, "in-scope work that looks complete")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    adapters = mr.Adapters(
        builder_invoker=fake_builder([mr.RecoverableSessionInfrastructureError("prose, not json", session_id="sess-sr7")]),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    manifest = mr.advance(root, run_id, adapters)  # BUILDING: recoverable failure
    assert_true(manifest["phase"] == "BUILDING", f"a recoverable inner-validation failure must never be treated as success merely because in-scope files already changed, got {manifest['phase']}")
    assert_true(manifest["last_valid_test_artifact"] is None, "no test evidence must exist -- TESTING was never legitimately reached")
    assert_true(manifest["infrastructure_retry_count"] == 1, f"the failure must still count against the bounded infrastructure retry budget, got {manifest['infrastructure_retry_count']}")


_with_tmp_repo(_test_sr7_recoverable_failure_never_treated_as_success)
print("PASS SR-7: a recoverable inner-validation failure is never treated as success merely because substantial in-scope file changes already exist in the working tree -- the run stays bounded in BUILDING, counted against the infrastructure retry budget, never fast-forwarded to TESTING or success.")


def _test_sr8_ambiguous_inner_result_still_recoverable_fail_closed() -> None:
    """(9) Two conflicting schema-valid inner objects must still fail
    closed (never guess which is authoritative) -- and, since a
    trustworthy session_id accompanies them, the failure must still be
    recoverable rather than discarding a real session over ambiguity."""
    first = {
        "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
        "summary": "first",
        "files_touched": [],
        "stop_condition_encountered": None,
        "architecture_decision_required": False,
    }
    second = {
        "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
        "summary": "second, on reflection",
        "files_touched": [],
        "stop_condition_encountered": None,
        "architecture_decision_required": False,
    }
    ambiguous_result_text = json.dumps(first) + " ... on reflection, actually ... " + json.dumps(second)
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (
        True, json.dumps({"is_error": False, "session_id": "sess-ambiguous", "result": ambiguous_result_text, "type": "result"}), ""
    )
    try:
        raised = None
        try:
            mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
        except mr.InfrastructureError as exc:
            raised = exc
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary
    assert_true(isinstance(raised, mr.RecoverableSessionInfrastructureError), f"two conflicting schema-valid inner objects must still fail closed, and (given a trustworthy session_id) remain recoverable, got {type(raised)}")
    assert_true(raised.session_id == "sess-ambiguous", f"the ambiguous-result failure must still preserve the real session_id, got {getattr(raised, 'session_id', None)}")


_test_sr8_ambiguous_inner_result_still_recoverable_fail_closed()
print("PASS SR-8: two conflicting schema-valid inner result objects still fail closed (never guessing which is authoritative), and -- since a trustworthy session_id accompanies them -- the failure remains recoverable rather than discarding a real session merely because of ambiguity.")


def _test_sr9_normal_first_attempt_unchanged(root: Path) -> None:
    """(10) A normal first-attempt builder invocation is completely
    unaffected by the session-recovery machinery: session_id=None, the
    full original task prompt is used, and the happy path still reaches
    READY_FOR_HUMAN_APPROVAL exactly as before."""
    baseline = _base_repo(root)
    branch = "feature/sr9-first-attempt-unchanged"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    builder = _recording_fake_builder([BUILDER_OK])
    result = mr.run(
        root,
        contract_path,
        policy_path,
        adapters=mr.Adapters(
            builder_invoker=builder,
            reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
            test_runner=fake_test_runner([True]),
            assurance_runner=fake_assurance_runner(True),
        ),
    )
    assert_true(result["phase"] == "READY_FOR_HUMAN_APPROVAL", f"the happy path must still reach READY_FOR_HUMAN_APPROVAL unchanged, got {result['phase']}")
    assert_true(builder.calls[0]["session_id"] is None, "the first-ever builder invocation must not require a pre-existing session_id")
    expected_contract = _contract(branch, baseline)
    expected_prompt = mr.build_builder_prompt(expected_contract)
    assert_true(builder.calls[0]["prompt"] == expected_prompt, "a normal first attempt must use the full original task prompt, not the narrow resumed-completion prompt")


_with_tmp_repo(_test_sr9_normal_first_attempt_unchanged)
print("PASS SR-9: a normal first-attempt builder invocation is completely unaffected by the session-recovery machinery -- session_id=None, the full original task prompt is used, and the happy path still reaches READY_FOR_HUMAN_APPROVAL exactly as before.")


def _test_sr10_repairing_and_correcting_review_unaffected(root: Path) -> None:
    """(11) REPAIRING and CORRECTING_REVIEW's own existing session
    threading and full-context prompting must not regress: a session_id
    established by a genuinely successful builder turn is correctly
    carried forward into a REPAIRING retry and a CORRECTING_REVIEW pass,
    and both use the full (non-narrow) builder prompt, since no
    recoverable-session-failure ever occurred on this run."""
    baseline = _base_repo(root)
    branch = "feature/sr10-repair-correction-unaffected"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    builder_ok_with_session = dict(BUILDER_OK, session_id="sess-normal")
    builder = _recording_fake_builder([builder_ok_with_session, BUILDER_OK, BUILDER_OK])
    changes_required_with_finding = {
        "outcome": "CHANGES_REQUIRED",
        "findings": [
            {"id": "R1", "severity": "HIGH", "required": True, "path": "src/thing.py", "line": 1, "invariant": "x", "evidence": "x", "required_action": "fix x"}
        ],
    }
    adapters = mr.Adapters(
        builder_invoker=builder,
        reviewer_invoker=fake_reviewer([changes_required_with_finding, REVIEWER_SAFE]),
        test_runner=fake_test_runner([False, True, True]),
        assurance_runner=fake_assurance_runner(True),
    )
    result = mr.run(root, contract_path, policy_path, adapters=adapters)
    assert_true(result["phase"] == "READY_FOR_HUMAN_APPROVAL", f"expected the run to complete through REPAIRING and CORRECTING_REVIEW to READY_FOR_HUMAN_APPROVAL, got {result['phase']} / {result.get('stop_reason')}")
    assert_true(len(builder.calls) == 3, f"expected exactly 3 builder calls (BUILDING, REPAIRING, CORRECTING_REVIEW), got {len(builder.calls)}")

    resumed_marker = "resuming this exact same session"
    assert_true(builder.calls[0]["session_id"] is None, "the first BUILDING call must not require a pre-existing session_id")
    assert_true(builder.calls[1]["session_id"] == "sess-normal", f"the REPAIRING call must resume the session established by the successful BUILDING turn, got {builder.calls[1]['session_id']}")
    assert_true(resumed_marker not in builder.calls[1]["prompt"], "REPAIRING must use the normal full builder prompt (with deterministic failures), not the narrow session-recovery completion prompt")
    assert_true(builder.calls[2]["session_id"] == "sess-normal", f"the CORRECTING_REVIEW call must also resume the same established session, got {builder.calls[2]['session_id']}")
    assert_true(resumed_marker not in builder.calls[2]["prompt"], "CORRECTING_REVIEW must use the normal full builder prompt (with reviewer findings), not the narrow session-recovery completion prompt")


_with_tmp_repo(_test_sr10_repairing_and_correcting_review_unaffected)
print("PASS SR-10: REPAIRING and CORRECTING_REVIEW correctly resume the session established by a genuinely successful builder turn and use the normal full builder prompt -- unaffected by, and never confused with, the new narrow session-recovery completion path.")


def _test_sr11_no_session_persisted_on_ordinary_infra_error(root: Path) -> None:
    """(12) An ordinary (non-recoverable) infrastructure error -- the
    state-machine-level consequence of an untrusted/malformed outer
    envelope -- must never result in an invented session_id being
    persisted onto the manifest."""
    baseline = _base_repo(root)
    branch = "feature/sr11-no-invented-session"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)
    adapters = mr.Adapters(
        builder_invoker=fake_builder([mr.InfrastructureError("malformed envelope, no session"), BUILDER_OK]),
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING
    manifest = mr.advance(root, run_id, adapters)  # BUILDING raises ordinary InfrastructureError -> self-loop
    assert_true(manifest["phase"] == "BUILDING", f"an ordinary infra error must self-loop back to BUILDING, got {manifest['phase']}")
    assert_true(manifest["builder_session_id"] is None, f"a plain (non-recoverable) infrastructure error must never persist an invented session_id, got {manifest.get('builder_session_id')}")


_with_tmp_repo(_test_sr11_no_session_persisted_on_ordinary_infra_error)
print("PASS SR-11: an ordinary (non-recoverable) infrastructure error never results in an invented session_id being persisted onto the manifest.")


# ======================================================================
# SR-CRASH-1 / SR-WS-1 (bounded correction pass, Cursor CHANGES_REQUIRED)
# ======================================================================

def _test_sr_crash1_reconstructs_lost_session_after_crash(root: Path) -> None:
    """SR-CRASH-1: a process crash between the durable event write and
    the durable manifest save can leave events.jsonl carrying a real
    recovered session_id while manifest.json still has
    builder_session_id=null. The very next advance() (a fresh process,
    per the resume() contract) must reconstruct and use that exact
    session_id -- both for the invocation (--resume-equivalent at the
    adapter boundary) and for selecting the narrow resumed-completion
    prompt -- never silently falling back to a fresh/full invocation."""
    baseline = _base_repo(root)
    branch = "feature/sr-crash1-reconstruct"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    builder = _recording_fake_builder([BUILDER_OK])
    adapters = mr.Adapters(
        builder_invoker=builder,
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING

    # Simulate the exact crash window SR-CRASH-1 describes: the durable
    # event was written, but the manifest save that should have followed
    # it never completed.
    rdir = mr.run_dir(root, run_id)
    mr.append_event(rdir, {"event": "BUILDER_SESSION_RECOVERED", "session_id": "session-crash-recovery"})
    manifest = mr.load_manifest(rdir)
    assert_true(manifest["builder_session_id"] is None, "setup: the manifest must still show no session_id, simulating a crash before its own save completed")

    expected_contract = _contract(branch, baseline)
    expected_resumed_prompt = mr.build_resumed_completion_prompt(expected_contract)

    manifest = mr.advance(root, run_id, adapters)  # a fresh advance(), as if from a restarted process
    assert_true(len(builder.calls) == 1, f"expected exactly one builder call, got {len(builder.calls)}")
    assert_true(builder.calls[0]["session_id"] == "session-crash-recovery", f"the reconstructed session_id must be used for this invocation, got {builder.calls[0]['session_id']}")
    assert_true(builder.calls[0]["prompt"] == expected_resumed_prompt, "a reconstructed pending recovery must use the narrow resumed-completion prompt, never the full fresh-task prompt")
    assert_true(manifest["builder_session_id"] == "session-crash-recovery", f"the manifest must be self-healed with the reconstructed session_id, got {manifest.get('builder_session_id')}")
    assert_true(manifest["phase"] == "TESTING", f"a successful reconstructed-session invocation must transition normally onward, got {manifest['phase']}")


_with_tmp_repo(_test_sr_crash1_reconstructs_lost_session_after_crash)
print("PASS SR-CRASH-1: a process crash leaving events.jsonl with a durably-recorded BUILDER_SESSION_RECOVERED but manifest.builder_session_id still null is reconstructed on the next advance() -- the exact session_id is both used for the invocation and the narrow resumed-completion prompt, and the manifest is self-healed.")


def _test_sr_crash1_stale_event_not_resurrected_after_invocation(root: Path) -> None:
    """A BUILDER_SESSION_RECOVERED event followed by a genuine
    BUILDER_INVOKED event must not resurrect as pending on a later
    advance() -- pending recovery is cleared the moment an invocation
    actually completes, crash-reconstruction included."""
    baseline = _base_repo(root)
    branch = "feature/sr-crash1-stale-not-resurrected"
    _make_feature_branch(root, branch)
    _write(root, "src/thing.py", "x = 1\n")
    _commit(root, "in-scope work")
    contract_path, policy_path = _write_contract_and_policy(root, branch, baseline)

    builder = _recording_fake_builder([BUILDER_OK])
    adapters = mr.Adapters(
        builder_invoker=builder,
        reviewer_invoker=fake_reviewer([REVIEWER_SAFE]),
        test_runner=fake_test_runner([True]),
        assurance_runner=fake_assurance_runner(True),
    )
    init_result = mr.init_run(root, contract_path, policy_path)
    run_id = init_result["run_id"]
    rdir = mr.run_dir(root, run_id)
    mr.advance(root, run_id, adapters)  # INITIALIZING -> BUILDING

    # A stale recovery event from an earlier (already-resolved) attempt,
    # followed by proof that attempt actually completed.
    mr.append_event(rdir, {"event": "BUILDER_SESSION_RECOVERED", "session_id": "stale-session-should-not-resurrect"})
    mr.append_event(rdir, {"event": "BUILDER_INVOKED", "valid": True, "artifact": "irrelevant"})
    assert_true(mr._pending_recovered_session_id(rdir) is None, "a BUILDER_SESSION_RECOVERED event followed by a genuine BUILDER_INVOKED must not read back as still pending")

    manifest = mr.advance(root, run_id, adapters)
    assert_true(builder.calls[0]["session_id"] is None, f"the invocation must not resurrect the stale session, got {builder.calls[0]['session_id']}")
    expected_contract = _contract(branch, baseline)
    expected_full_prompt = mr.build_builder_prompt(expected_contract)
    assert_true(builder.calls[0]["prompt"] == expected_full_prompt, "the invocation must use the normal full prompt, not the narrow resumed-completion prompt, since no recovery is genuinely pending")
    assert_true(manifest["builder_session_id"] is None, f"the manifest must not be healed with a stale, already-resolved session_id, got {manifest.get('builder_session_id')}")


_with_tmp_repo(_test_sr_crash1_stale_event_not_resurrected_after_invocation)
print("PASS SR-CRASH-1b: a stale BUILDER_SESSION_RECOVERED event followed by a genuine BUILDER_INVOKED never resurrects as pending recovery on a later advance() -- no stale session reconstruction, normal full prompt used.")


def _test_sr_crash1_latest_pending_recovery_governs() -> None:
    """When multiple BUILDER_SESSION_RECOVERED events exist without any
    intervening BUILDER_INVOKED, only the LATEST one's session_id
    governs -- never an earlier, superseded one."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="sr_crash1_multi_"))
    try:
        rdir = tmp_dir / "run"
        rdir.mkdir(parents=True)
        mr.append_event(rdir, {"event": "BUILDER_SESSION_RECOVERED", "session_id": "first-superseded-session"})
        mr.append_event(rdir, {"event": "BUILDER_SESSION_RECOVERED", "session_id": "second-latest-session"})
        pending = mr._pending_recovered_session_id(rdir)
        assert_true(pending == "second-latest-session", f"only the LATEST still-pending recovery event's session_id must govern, got {pending!r}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


_test_sr_crash1_latest_pending_recovery_governs()
print("PASS SR-CRASH-1c: when multiple BUILDER_SESSION_RECOVERED events exist without an intervening BUILDER_INVOKED, only the latest one's session_id governs.")


def _test_sr_ws1_whitespace_only_session_id_not_recoverable() -> None:
    """SR-WS-1: a whitespace-only session_id ("   ") must never be
    treated as recoverable -- plain InfrastructureError only, never
    RecoverableSessionInfrastructureError, never persisted, never
    reaching --resume."""
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (
        True, json.dumps({"is_error": False, "session_id": "   ", "result": "prose, not json", "type": "result"}), ""
    )
    try:
        raised_type = None
        try:
            mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
        except mr.InfrastructureError as exc:
            raised_type = type(exc)
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary
    assert_true(raised_type is mr.InfrastructureError, f"a whitespace-only session_id must never be recoverable -- expected plain InfrastructureError, got {raised_type}")


_test_sr_ws1_whitespace_only_session_id_not_recoverable()
print("PASS SR-WS-1a: a whitespace-only session_id (\"   \") is never treated as recoverable -- plain InfrastructureError, fail closed, exactly like a missing session_id.")


def _test_sr_ws1_leading_trailing_whitespace_stripped() -> None:
    """A valid session_id surrounded by incidental whitespace
    (" session-with-padding ") must still be recoverable, and the
    STRIPPED canonical value is what gets carried forward and would
    reach --resume."""
    original_run_subprocess_streams = mr._run_subprocess_streams
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    mr._run_subprocess_streams = lambda args, *, cwd, timeout=600: (
        True, json.dumps({"is_error": False, "session_id": "  session-with-padding  ", "result": "prose, not json", "type": "result"}), ""
    )
    try:
        raised = None
        try:
            mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
        except mr.RecoverableSessionInfrastructureError as exc:
            raised = exc
    finally:
        mr._run_subprocess_streams = original_run_subprocess_streams
        mr._find_claude_binary = original_find_claude_binary
    assert_true(raised is not None, "a session_id with incidental surrounding whitespace must still be recoverable")
    assert_true(raised.session_id == "session-with-padding", f"the STRIPPED canonical session_id must be what is carried forward, got {raised.session_id!r}")


_test_sr_ws1_leading_trailing_whitespace_stripped()
print("PASS SR-WS-1b: a session_id with incidental leading/trailing whitespace is still recoverable, and the stripped canonical value (not the raw padded string) is what gets carried forward.")


def _test_sr_ws1_invalid_session_id_forms_all_fail_closed() -> None:
    """Every non-recoverable session_id form from SR-WS-1's own worked
    examples (empty string, absent/None, a non-string type) must remain
    plain InfrastructureError -- never recoverable."""
    invalid_session_ids = ["", None, 123]
    for bad_id in invalid_session_ids:
        original_run_subprocess_streams = mr._run_subprocess_streams
        original_find_claude_binary = mr._find_claude_binary
        mr._find_claude_binary = lambda: "claude-binary-path"
        envelope = {"is_error": False, "result": "prose, not json", "type": "result"}
        if bad_id is not None:
            envelope["session_id"] = bad_id
        mr._run_subprocess_streams = lambda args, *, cwd, timeout=600, _envelope=envelope: (True, json.dumps(_envelope), "")
        try:
            raised_type = None
            try:
                mr.real_claude_builder_invoker(prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None)
            except mr.InfrastructureError as exc:
                raised_type = type(exc)
        finally:
            mr._run_subprocess_streams = original_run_subprocess_streams
            mr._find_claude_binary = original_find_claude_binary
        assert_true(raised_type is mr.InfrastructureError, f"session_id form {bad_id!r} must never be recoverable, got {raised_type}")


_test_sr_ws1_invalid_session_id_forms_all_fail_closed()
print("PASS SR-WS-1c: empty-string, absent/None, and non-string session_id forms all remain plain InfrastructureError -- never recoverable, matching SR-WS-1's own worked examples.")


# ======================================================================
# CAREER_OS_PROVIDER_ENVELOPE_STDOUT_STDERR_SEPARATION_V1 (reproduced on
# the fresh canary run 20260907T220348Z-3dacfcfd, FIXED below): the old
# `_run_subprocess` used to do `output = (completed.stdout or "") +
# (completed.stderr or "")` -- it concatenated stdout and stderr into a
# single string BEFORE either provider adapter's strict outer-envelope
# parse. A provider that writes its single well-formed JSON envelope to
# stdout (the documented `--output-format json` contract) and ALSO writes
# incidental warning/diagnostic text to stderr on an otherwise-successful
# (exit 0) invocation used to have that diagnostic text appended directly
# onto the tail of an otherwise-valid JSON document, so
# `_parse_strict_json`'s `json.loads` failed with `json.JSONDecodeError:
# Extra data ...` -- a genuine, valid provider result discarded as an
# infrastructure failure purely because of transport-boundary
# contamination, not any real defect in the provider's own structured
# reply.
#
# Fix: `real_claude_builder_invoker`/`real_cursor_reviewer_invoker` now
# call `_run_subprocess_streams` (stdout/stderr kept separate) and
# `_parse_provider_outer_envelope` (strict stdout-only parse; stderr
# folded into the error message only on failure, never parsed).
#
# These tests patch `mr.subprocess.run` itself (a fake subprocess, exactly
# at the real OS boundary `_run_subprocess_streams` calls) rather than
# `mr._run_subprocess_streams`, so the real merge-free logic in
# `_run_subprocess_streams`/`_parse_provider_outer_envelope` is genuinely
# exercised end-to-end -- every OTHER test in this file mocks
# `mr._run_subprocess_streams` directly at a higher level and therefore
# never exercises the actual `subprocess.run` boundary these two
# functions sit on top of, which is exactly why this defect reached a
# real canary run undetected in the first place.
# ======================================================================

class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_subprocess_run(returncode: int, stdout: str, stderr: str):
    def _run(args, *, cwd=None, capture_output=None, text=None, timeout=None, **kwargs):
        return _FakeCompletedProcess(returncode, stdout, stderr)
    return _run


_VALID_BUILDER_ENVELOPE = {
    "is_error": False,
    "session_id": "canary-session-id",
    "type": "result",
    "result": json.dumps({
        "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
        "summary": "fake builder finished",
        "files_touched": [],
        "stop_condition_encountered": None,
        "architecture_decision_required": False,
    }),
}
_VALID_BUILDER_STDOUT = json.dumps(_VALID_BUILDER_ENVELOPE)

# Case letters below intentionally track the acceptance conditions named
# directly in milestone_contracts/feature/career-os-provider-envelope-stdout-stderr-separation-v1.json
# (the boundary must distinguish exit code/stdout/stderr; stdout-only
# strict parsing; stderr never interpreted as provider data but remains
# useful diagnostics; nonzero exit always fails even over valid-looking
# stdout; empty/warning/multiline stderr must not affect a valid result).
# Cases proven identically true both before and after the fix (D, F, G, H)
# are included to prove the fix must not weaken them while closing B/C --
# they deliberately reuse the same harness rather than duplicating a
# separate suite.
#
# Full case index A-M (every lettered case below is executed by an
# assertion; none is a label without a corresponding check):
#   A - valid stdout, empty stderr (baseline happy path)
#   B - valid stdout, single-line warning stderr (THE reproduced defect shape)
#   C - valid stdout, multiline stderr (defect shape, multiple stderr lines)
#   D - nonzero exit over valid-looking stdout (must still fail)
#   E - empty stdout, nonzero exit, stderr diagnostic (must fail; stderr surfaces)
#   F - malformed stdout, empty stderr (must fail closed)
#   G - trailing-contaminated stdout itself, not stderr (must still fail closed --
#       negative control proving the fix is a strict boundary correction, never a
#       fuzzy tolerance of trailing garbage; this is the stdout-contamination
#       negative control the milestone contract requires)
#   H - multiple JSON documents on stdout itself (must still fail closed -- the
#       second stdout-contamination negative control the milestone contract
#       requires)
#   I - malformed stdout with stderr diagnostic present (must fail on stdout;
#       stderr diagnostic must still surface in the raised error)
#   J - empty stdout with stderr diagnostic present, exit 0 (must fail on stdout;
#       stderr diagnostic must still surface in the raised error)
#   K - Cursor reviewer adapter shares the identical boundary (see
#       `_test_provider_envelope_stdout_stderr_transport_boundary_cursor_reviewer`
#       below), and remains read-only/strict (--mode ask, never --force/--yolo)
#   L - adversarial stderr lock (empty stdout, and separately malformed stdout)
#       with a FULLY VALID provider JSON envelope on stderr: stderr must never be
#       interpreted as provider data even when it is itself well-formed and
#       parseable -- both must still fail closed on stdout alone
#   M - adversarial stderr lock: valid stdout AND a conflicting, independently
#       valid JSON envelope on stderr (different session_id/result) -- the
#       returned result must reflect stdout's envelope only, never stderr's
_BUILDER_TRANSPORT_CASES: dict[str, dict[str, Any]] = {
    "A_valid_stdout_empty_stderr": dict(
        returncode=0, stdout=_VALID_BUILDER_STDOUT, stderr="", expect_ok=True,
    ),
    "B_valid_stdout_warning_stderr": dict(
        # THE reproduced defect: one valid JSON envelope on stdout, one
        # line of incidental diagnostic text on stderr, exit 0.
        returncode=0, stdout=_VALID_BUILDER_STDOUT,
        stderr="Warning: deprecated flag used\n", expect_ok=True,
    ),
    "C_valid_stdout_multiline_stderr": dict(
        returncode=0, stdout=_VALID_BUILDER_STDOUT,
        stderr="notice: telemetry disabled\nnotice: cache miss\n", expect_ok=True,
    ),
    "D_nonzero_exit_valid_looking_stdout": dict(
        returncode=1, stdout=_VALID_BUILDER_STDOUT, stderr="fatal: crashed after writing partial output\n",
        expect_ok=False, expect_error_substring="fatal: crashed",
    ),
    "E_empty_stdout_nonzero_exit_stderr_diagnostic": dict(
        returncode=2, stdout="", stderr="Fatal: authentication expired\n",
        expect_ok=False, expect_error_substring="authentication expired",
    ),
    "F_malformed_stdout_empty_stderr": dict(
        returncode=0, stdout="not even json", stderr="", expect_ok=False, expect_error_substring="not strict JSON",
    ),
    "G_trailing_contaminated_stdout_itself": dict(
        # The contamination is inside stdout itself (not stderr) -- this
        # must remain a failure even after stdout/stderr separation ships,
        # proving the fix is a strict boundary correction, never a fuzzy
        # tolerance of trailing garbage.
        returncode=0, stdout=_VALID_BUILDER_STDOUT + " <<unexpected trailing text>>", stderr="",
        expect_ok=False, expect_error_substring="not strict JSON",
    ),
    "H_multiple_json_documents_on_stdout": dict(
        returncode=0, stdout=_VALID_BUILDER_STDOUT + "\n" + _VALID_BUILDER_STDOUT, stderr="",
        expect_ok=False, expect_error_substring="not strict JSON",
    ),
    "I_malformed_stdout_with_stderr_diagnostic": dict(
        # Malformed stdout AND non-empty stderr, exit 0: must still fail
        # closed on the malformed stdout, and the stderr diagnostic must
        # still be visible in the raised error (never silently dropped),
        # even though it plays no part in the (failed) parse itself.
        returncode=0, stdout="not even json", stderr="notice: something happened during the run\n",
        expect_ok=False, expect_error_substring=("not strict JSON", "notice: something happened during the run"),
    ),
    "J_empty_stdout_with_stderr_diagnostic_exit_zero": dict(
        # Empty stdout on an exit-0 invocation, with stderr diagnostic
        # text present: still fails closed (empty stdout is not valid
        # JSON), and the stderr diagnostic must still surface in the
        # raised error.
        returncode=0, stdout="", stderr="notice: nothing to report\n",
        expect_ok=False, expect_error_substring=("not strict JSON", "notice: nothing to report"),
    ),
    "L_empty_stdout_valid_envelope_on_stderr": dict(
        # Adversarial stderr lock (R3a): stdout is empty but stderr itself
        # carries a FULLY VALID, well-formed provider JSON envelope. Even
        # though stderr is perfectly parseable JSON, it must never be
        # treated as provider data -- this must still fail closed on the
        # empty stdout alone.
        returncode=0, stdout="", stderr=json.dumps(_VALID_BUILDER_ENVELOPE),
        expect_ok=False, expect_error_substring="not strict JSON",
    ),
    "L_malformed_stdout_valid_envelope_on_stderr": dict(
        # Adversarial stderr lock (R3a), malformed-stdout variant: stdout
        # is malformed but stderr carries a fully valid provider JSON
        # envelope. Must still fail closed on the malformed stdout alone
        # -- a valid envelope landing on the wrong stream is never a
        # rescue path.
        returncode=0, stdout="not even json", stderr=json.dumps(_VALID_BUILDER_ENVELOPE),
        expect_ok=False, expect_error_substring="not strict JSON",
    ),
    "M_valid_stdout_conflicting_valid_envelope_on_stderr": dict(
        # Adversarial stderr lock (R3b): stdout carries the real, valid
        # envelope AND stderr independently carries a different, also
        # well-formed valid envelope (different session_id and result).
        # The returned result must reflect stdout's envelope only -- the
        # success-path assertions below already check
        # session_id == "canary-session-id", which only stdout's envelope
        # carries, so this proves stderr's conflicting envelope never wins.
        returncode=0, stdout=_VALID_BUILDER_STDOUT,
        stderr=json.dumps({
            **_VALID_BUILDER_ENVELOPE,
            "session_id": "IMPOSTER-session-id-from-stderr",
            "result": json.dumps({
                "status": "IMPLEMENTATION_ATTEMPT_COMPLETE",
                "summary": "STDERR ENVELOPE MUST NEVER WIN",
                "files_touched": [],
                "stop_condition_encountered": None,
                "architecture_decision_required": False,
            }),
        }),
        expect_ok=True,
    ),
}


def _test_pre_fix_reproduction_historical_boundary_extra_data_signature() -> None:
    """R2: deterministic, executable proof of the actual historical defect
    signature -- NOT commentary. This reconstructs the exact pre-fix
    `_run_subprocess` concatenation shape (`(stdout or "") + (stderr or
    "")`, no separator -- see the historical git diff this milestone
    corrects) directly from the same valid builder envelope + diagnostic
    stderr text used as case B above (the exact defect shape from the
    reproduced canary runs), and asserts that parsing that historical
    concatenation with the unchanged `_parse_strict_json` full-document
    parser fails with the real `json.JSONDecodeError` 'Extra data'
    signature -- the literal error class that made the canary runs
    (20260907T180932Z-656eae27, 20260907T193310Z-f6a756d2,
    20260907T220348Z-3dacfcfd) fail. It then proves the FIX actually
    closes this exact reproduction by parsing the identical stdout/stderr
    pair through the current `_parse_provider_outer_envelope` boundary
    (stdout/stderr kept separate) and confirming it succeeds -- so this
    is a before/after pair over the same inputs, not just an isolated
    failure assertion."""
    stdout = _VALID_BUILDER_STDOUT
    stderr = "Warning: deprecated flag used\n"
    historical_combined_output = (stdout or "") + (stderr or "")
    try:
        mr._parse_strict_json(historical_combined_output)
    except mr.InfrastructureError as exc:
        assert_true(
            "Extra data" in str(exc),
            "pre-fix reproduction did not reproduce the historical 'Extra data' "
            f"json.JSONDecodeError signature; got: {exc}",
        )
    else:
        assert_true(
            False,
            "pre-fix reproduction is invalid: concatenating a valid stdout envelope "
            "with non-empty stderr text (the historical _run_subprocess shape) must "
            "fail strict JSON parsing, but it succeeded -- this reproduction no "
            "longer demonstrates the defect it claims to demonstrate",
        )
    fixed_parse = mr._parse_provider_outer_envelope(stdout, stderr)
    assert_true(
        isinstance(fixed_parse, dict) and fixed_parse.get("session_id") == "canary-session-id",
        "the corrected stdout-only boundary must successfully parse the identical "
        f"stdout/stderr pair that failed when concatenated, got: {fixed_parse!r}",
    )


_test_pre_fix_reproduction_historical_boundary_extra_data_signature()
print("PASS PROVIDER-ENVELOPE-TRANSPORT-0 (R2 pre-fix reproduction): concatenating valid builder stdout with diagnostic stderr text using the exact historical _run_subprocess shape deterministically reproduces the real json.JSONDecodeError 'Extra data' signature from the canary runs, and the corrected stdout-only boundary parses the identical inputs successfully.")


def _test_provider_envelope_stdout_stderr_transport_boundary() -> None:
    original_run = mr.subprocess.run
    original_find_claude_binary = mr._find_claude_binary
    mr._find_claude_binary = lambda: "claude-binary-path"
    try:
        for label, case in _BUILDER_TRANSPORT_CASES.items():
            mr.subprocess.run = _fake_subprocess_run(case["returncode"], case["stdout"], case["stderr"])
            try:
                result = mr.real_claude_builder_invoker(
                    prompt="x", cwd=Path("."), policy={"builder_timeout_seconds": 30}, session_id=None
                )
            except mr.InfrastructureError as exc:
                if case["expect_ok"]:
                    assert_true(
                        False,
                        f"Case {label}: REGRESSION -- a valid JSON provider envelope on stdout plus non-JSON "
                        "diagnostic text on stderr must not fail strict outer-envelope parsing (this is the "
                        "CAREER_OS_PROVIDER_ENVELOPE_STDOUT_STDERR_SEPARATION_V1 defect: stdout+stderr must "
                        f"never be concatenated before parsing), but got: {exc}",
                    )
                expected_substrings = case["expect_error_substring"]
                if isinstance(expected_substrings, str):
                    expected_substrings = (expected_substrings,)
                for expected_substring in expected_substrings:
                    assert_true(
                        expected_substring in str(exc),
                        f"Case {label}: expected {expected_substring!r} in the raised error, got: {exc}",
                    )
            else:
                assert_true(
                    case["expect_ok"],
                    f"Case {label}: expected an InfrastructureError (fail-closed) but the call succeeded with {result!r}",
                )
                assert_true(
                    result.get("status") == "IMPLEMENTATION_ATTEMPT_COMPLETE",
                    f"Case {label}: a valid builder envelope on stdout must still yield the real builder result "
                    f"regardless of stderr content, got {result!r}",
                )
                assert_true(
                    result.get("session_id") == "canary-session-id",
                    f"Case {label}: session_id from the valid outer envelope must still be carried forward, got {result!r}",
                )
    finally:
        mr.subprocess.run = original_run
        mr._find_claude_binary = original_find_claude_binary


_test_provider_envelope_stdout_stderr_transport_boundary()
print("PASS PROVIDER-ENVELOPE-TRANSPORT-1: cases A-J, L, M establish and adversarially lock the stdout/stderr subprocess transport boundary for the builder adapter -- valid stdout survives empty/warning/multiline stderr (A, B, C -- B/C are the exact CAREER_OS_PROVIDER_ENVELOPE_STDOUT_STDERR_SEPARATION_V1 defect shape), nonzero exit always fails even over valid-looking stdout (D), stderr remains useful diagnostic evidence on empty-stdout/nonzero-exit failures (E) and on malformed/empty stdout at exit 0 (I, J), malformed/trailing-contaminated/multiple-document stdout itself still fails closed (F, G, H -- G and H are the deterministic stdout-only contamination negative controls), and stderr is never treated as provider data even when stderr itself is a fully valid, well-formed JSON envelope, whether stdout is empty/malformed (L) or stdout is itself valid and stderr's envelope conflicts with it (M). Case K (Cursor reviewer adapter shares the identical boundary) is proven separately below.")


_VALID_REVIEWER_ENVELOPE = {
    "is_error": False,
    "type": "result",
    "result": json.dumps({"outcome": "SAFE", "findings": []}),
}
_VALID_REVIEWER_STDOUT = json.dumps(_VALID_REVIEWER_ENVELOPE)


def _test_case_k_provider_envelope_stdout_stderr_transport_boundary_cursor_reviewer() -> None:
    """Case K. The acceptance condition names BOTH 'Claude and Cursor
    provider outer-envelope parsing' -- the reviewer adapter shares the
    exact same `_run_subprocess_streams`/`_parse_provider_outer_envelope`
    boundary, so the same fix (and the same regression risk) applies to
    it too. Also locks in that the reviewer invocation remains
    read-only/strict: `--mode ask` (never a mutating mode) and no
    `--force`/`--yolo` appear anywhere in the constructed argv."""
    original_run = mr.subprocess.run
    original_find_binary = mr._find_binary
    recorded_args: list[list[str]] = []
    mr._find_binary = lambda name, extra_candidates=(): "agent-binary-path"

    def _recording_fake_run(args, *, cwd=None, capture_output=None, text=None, timeout=None, **kwargs):
        recorded_args.append(list(args))
        return _FakeCompletedProcess(0, _VALID_REVIEWER_STDOUT, "Warning: deprecated flag used\n")

    mr.subprocess.run = _recording_fake_run
    try:
        try:
            result = mr.real_cursor_reviewer_invoker(prompt="x", cwd=Path("."), policy={"reviewer_timeout_seconds": 30})
        except mr.InfrastructureError as exc:
            assert_true(
                False,
                "REGRESSION: the Cursor reviewer adapter's valid JSON stdout envelope plus stderr diagnostic "
                f"text must not fail strict outer-envelope parsing, but got: {exc}",
            )
        else:
            assert_true(result.get("outcome") == "SAFE", f"a valid reviewer envelope on stdout must still yield the real reviewer result regardless of stderr content, got {result!r}")
        args = recorded_args[0]
        assert_true("--mode" in args and args[args.index("--mode") + 1] == "ask", f"the Cursor reviewer must always invoke --mode ask (read-only), got {args}")
        assert_true("--force" not in args and "--yolo" not in args, f"the Cursor reviewer must never pass --force/--yolo, got {args}")
    finally:
        mr.subprocess.run = original_run
        mr._find_binary = original_find_binary


_test_case_k_provider_envelope_stdout_stderr_transport_boundary_cursor_reviewer()
print("PASS PROVIDER-ENVELOPE-TRANSPORT-2 (case K): the Cursor reviewer adapter shares the identical stdout/stderr transport boundary as the Claude builder adapter (valid stdout survives stderr diagnostic text), and remains read-only/strict (--mode ask, never --force/--yolo).")


def _test_cursor_reviewer_prompt_transport_is_stdin_not_argv() -> None:
    """CAREER_OS_CURSOR_REVIEWER_STDIN_TRANSPORT_V1: on Windows, `agent`
    resolves to `agent.cmd`, a cmd.exe wrapper subject to cmd.exe's
    ~8191-character total command-line length limit -- a real review
    prompt (a full diff plus template text) routinely exceeds that and
    fails every time with 'The command line is too long.' regardless of
    quoting. The fix must move the prompt off argv entirely, onto the
    child process's stdin, while every other flag (--mode ask, --trust,
    --workspace, --output-format json) stays exactly as before."""
    original_run = mr.subprocess.run
    original_find_binary = mr._find_binary
    recorded: dict[str, Any] = {}
    mr._find_binary = lambda name, extra_candidates=(): "agent-binary-path"

    huge_prompt = "X" * 20000  # far larger than cmd.exe's ~8191-char argv limit

    def _recording_fake_run(args, *, cwd=None, capture_output=None, text=None, encoding=None, timeout=None, input=None, **kwargs):
        recorded["args"] = list(args)
        recorded["input"] = input
        recorded["encoding"] = encoding
        return _FakeCompletedProcess(0, _VALID_REVIEWER_STDOUT, "")

    mr.subprocess.run = _recording_fake_run
    try:
        result = mr.real_cursor_reviewer_invoker(prompt=huge_prompt, cwd=Path("."), policy={"reviewer_timeout_seconds": 30})
        assert_true(result.get("outcome") == "SAFE", f"a valid reviewer envelope must still be returned when the prompt is transported via stdin, got {result!r}")

        args = recorded["args"]
        assert_true(
            huge_prompt not in args,
            "REGRESSION: the reviewer prompt must never appear as a positional argv element -- "
            "that is exactly the defect that overflows cmd.exe's command-line length limit on Windows",
        )
        assert_true(
            recorded.get("input") == huge_prompt,
            f"the reviewer prompt must be transported via the child process's stdin (subprocess.run(..., input=prompt)), got input={recorded.get('input')!r}",
        )
        assert_true(
            recorded.get("encoding") == "utf-8",
            f"stdin transport must pin encoding='utf-8' explicitly (not rely on the platform default text-mode encoding) so non-ASCII prompt content is not corrupted on Windows, got encoding={recorded.get('encoding')!r}",
        )
        # every other flag must remain exactly as before.
        assert_true("--mode" in args and args[args.index("--mode") + 1] == "ask", f"--mode ask must remain present, got {args}")
        assert_true("--trust" in args, f"--trust must remain present, got {args}")
        assert_true("--workspace" in args, f"--workspace must remain present, got {args}")
        assert_true("--output-format" in args and args[args.index("--output-format") + 1] == "json", f"--output-format json must remain present, got {args}")
    finally:
        mr.subprocess.run = original_run
        mr._find_binary = original_find_binary


_test_cursor_reviewer_prompt_transport_is_stdin_not_argv()
print("PASS CURSOR-REVIEWER-STDIN-TRANSPORT-1: a large review prompt (20000 chars, far exceeding cmd.exe's ~8191-char argv limit) is transported to the Cursor reviewer via stdin, never as a positional argv element, while --mode ask/--trust/--workspace/--output-format json remain unchanged.")


def _test_cursor_reviewer_short_prompt_transport_is_stdin_not_argv() -> None:
    """CAREER_OS_CURSOR_REVIEWER_STDIN_TRANSPORT_V1 (REV-001): the stdin
    transport fix must not be conditional on prompt size -- a short
    prompt (well under cmd.exe's ~8191-char limit, and previously legal
    as a positional argv element) must ALSO be transported via stdin,
    never argv, with the exact same bytes/characters preserved. This
    guards against a fix that only routes large prompts through stdin
    while silently leaving small prompts on argv."""
    original_run = mr.subprocess.run
    original_find_binary = mr._find_binary
    recorded: dict[str, Any] = {}
    mr._find_binary = lambda name, extra_candidates=(): "agent-binary-path"

    short_prompt = "review this small diff please"

    def _recording_fake_run(args, *, cwd=None, capture_output=None, text=None, encoding=None, timeout=None, input=None, **kwargs):
        recorded["args"] = list(args)
        recorded["input"] = input
        recorded["encoding"] = encoding
        return _FakeCompletedProcess(0, _VALID_REVIEWER_STDOUT, "")

    mr.subprocess.run = _recording_fake_run
    try:
        result = mr.real_cursor_reviewer_invoker(prompt=short_prompt, cwd=Path("."), policy={"reviewer_timeout_seconds": 30})
        assert_true(result.get("outcome") == "SAFE", f"a valid reviewer envelope must still be returned for a short stdin-transported prompt, got {result!r}")

        args = recorded["args"]
        assert_true(
            short_prompt not in args,
            "REGRESSION: a short reviewer prompt must never appear as a positional argv element either -- "
            "the stdin fix must not be conditional on prompt length",
        )
        assert_true(
            recorded.get("input") == short_prompt,
            f"the short reviewer prompt must be transported via the child process's stdin with exact characters preserved, got input={recorded.get('input')!r}",
        )
        assert_true(
            recorded.get("encoding") == "utf-8",
            f"stdin transport must pin encoding='utf-8' explicitly, got encoding={recorded.get('encoding')!r}",
        )
        assert_true("--force" not in args and "--yolo" not in args, f"--force/--yolo must remain absent, got {args}")
        assert_true("--mode" in args and args[args.index("--mode") + 1] == "ask", f"--mode ask must remain present, got {args}")
        assert_true("--trust" in args, f"--trust must remain present, got {args}")
        assert_true("--workspace" in args, f"--workspace must remain present, got {args}")
        assert_true("--output-format" in args and args[args.index("--output-format") + 1] == "json", f"--output-format json must remain present, got {args}")
    finally:
        mr.subprocess.run = original_run
        mr._find_binary = original_find_binary


_test_cursor_reviewer_short_prompt_transport_is_stdin_not_argv()
print("PASS CURSOR-REVIEWER-STDIN-TRANSPORT-2: a short review prompt (well under the cmd.exe argv limit) is also transported to the Cursor reviewer via stdin with exact characters preserved, never as a positional argv element, while --mode ask/--trust/--workspace/--output-format json remain unchanged and --force/--yolo remain absent.")


def _test_cursor_reviewer_non_ascii_prompt_transport_preserves_exact_characters_via_utf8() -> None:
    """CAREER_OS_CURSOR_REVIEWER_STDIN_TRANSPORT_V1 (REV-001): reviewer
    prompts are built from UTF-8 templates/diffs and can contain
    non-ASCII characters. Prior argv transport went through
    CreateProcessW (Unicode) without re-encoding via a legacy code
    page; the stdin transport must not regress this -- it must pin
    encoding='utf-8' on the subprocess.run call so non-ASCII prompt
    content is not corrupted or rejected under Windows' default
    locale encoding (often cp1252)."""
    original_run = mr.subprocess.run
    original_find_binary = mr._find_binary
    recorded: dict[str, Any] = {}
    mr._find_binary = lambda name, extra_candidates=(): "agent-binary-path"

    non_ascii_prompt = "reviewer prompt with non-ASCII: café, über, 日本語, — em dash"

    def _recording_fake_run(args, *, cwd=None, capture_output=None, text=None, encoding=None, timeout=None, input=None, **kwargs):
        recorded["args"] = list(args)
        recorded["input"] = input
        recorded["encoding"] = encoding
        return _FakeCompletedProcess(0, _VALID_REVIEWER_STDOUT, "")

    mr.subprocess.run = _recording_fake_run
    try:
        result = mr.real_cursor_reviewer_invoker(prompt=non_ascii_prompt, cwd=Path("."), policy={"reviewer_timeout_seconds": 30})
        assert_true(result.get("outcome") == "SAFE", f"a valid reviewer envelope must still be returned for a non-ASCII stdin-transported prompt, got {result!r}")

        args = recorded["args"]
        assert_true(
            non_ascii_prompt not in args,
            "REGRESSION: a non-ASCII reviewer prompt must never appear as a positional argv element either",
        )
        assert_true(
            recorded.get("input") == non_ascii_prompt,
            f"the non-ASCII reviewer prompt must reach subprocess.run's input= boundary with exact characters preserved, got input={recorded.get('input')!r}",
        )
        assert_true(
            recorded.get("encoding") == "utf-8",
            f"stdin transport must pin encoding='utf-8' explicitly so non-ASCII prompt content is not corrupted on Windows, got encoding={recorded.get('encoding')!r}",
        )
    finally:
        mr.subprocess.run = original_run
        mr._find_binary = original_find_binary


_test_cursor_reviewer_non_ascii_prompt_transport_preserves_exact_characters_via_utf8()
print("PASS CURSOR-REVIEWER-STDIN-TRANSPORT-3: a non-ASCII review prompt is transported to the Cursor reviewer via stdin with exact characters preserved and encoding='utf-8' explicitly pinned, never as a positional argv element.")


def _test_reviewer_prompt_carries_stage_boundary_and_later_gate_non_substitution_language() -> None:
    """CAREER_OS_REVIEWER_POST_REVIEW_GATE_SEPARATION_V1: the reviewer
    prompt must tell Cursor that later controller/human gates (full
    Assurance, final release diff-check, human approval, release
    verification) intentionally have not happened yet and their absence
    from the review packet is not grounds for CHANGES_REQUIRED -- while
    also explicitly preserving those gates as mandatory, SAFE as not a
    substitute for them, and Cursor's authority to flag any diff that
    weakens/removes/bypasses/misorders them."""
    text = (ROOT / "prompts" / "milestone_reviewer_v1.md").read_text(encoding="utf-8")

    assert_true("CHANGES_REQUIRED" in text, "setup: prompt must still define the CHANGES_REQUIRED outcome")
    assert_true(
        "solely because" in text and "CHANGES_REQUIRED" in text,
        "the prompt must instruct the reviewer not to return CHANGES_REQUIRED solely because later-gate evidence is absent",
    )
    for later_gate_term in ("Assurance", "human approval", "release"):
        assert_true(later_gate_term in text, f"the prompt must name the later gate {later_gate_term!r} explicitly")
    assert_true(
        "mandatory" in text,
        "the prompt must state that later gates remain mandatory regardless of this review's outcome",
    )
    assert_true(
        "substitute" in text,
        "the prompt must state that a SAFE outcome here is never a substitute for the later gates",
    )
    assert_true(
        any(term in text for term in ("weakens", "weaken")) and any(term in text for term in ("bypass", "bypasses")) and any(term in text for term in ("misorder", "misorders")),
        "the prompt must preserve the reviewer's authority to flag a diff that weakens, bypasses, or misorders the later gates",
    )


_test_reviewer_prompt_carries_stage_boundary_and_later_gate_non_substitution_language()
print("PASS REVIEWER-GATE-SEPARATION-1: the reviewer prompt carries the stage-boundary instruction (no CHANGES_REQUIRED solely for absent later-gate evidence) while preserving later gates as mandatory, non-substitutable, and still flaggable if weakened/bypassed/misordered.")


print("ALL milestone_run_v1_test CHECKS PASSED")
