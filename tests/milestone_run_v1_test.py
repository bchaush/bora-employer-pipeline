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


print("ALL milestone_run_v1_test CHECKS PASSED")
