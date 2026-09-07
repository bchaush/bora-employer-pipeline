"""CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1 controller core.

The smallest deterministic, restart-safe local controller that executes
ONE already-authorized Career OS engineering milestone through:

  VERIFY REPO/REMOTE STATE -> LOAD/VERIFY CONTRACT -> ACQUIRE RUN LOCK ->
  INITIALIZE DURABLE RUN STATE -> BOUNDED CLAUDE-CODE BUILDER ->
  DETERMINISTIC TESTS -> BOUNDED REPAIR ON FAILURE -> REVALIDATE ACTUAL
  DIFF -> INDEPENDENT READ-ONLY CURSOR REVIEW -> BOUNDED CORRECTION OF
  REQUIRED FINDINGS -> RERUN TESTS -> FULL ASSURANCE BASELINE ->
  READY_FOR_HUMAN_APPROVAL.

This module OWNS PROCESS STATE. It never invents the next milestone,
never redefines milestone authority, and never commits, pushes, opens a
PR, or merges -- V1's only successful terminal state is
READY_FOR_HUMAN_APPROVAL, after which Bora remains the sole consequential
approver.

AUTHORITY SEPARATION (see the governing milestone contract and
BLUEPRINT.md/AGENTS.md, both forbidden paths for this milestone -- this
module never redefines them, only operationalizes an already-approved
contract):
  - Claude Code (the builder) can only report an implementation-attempt
    status. It cannot mark tests passed, mark review passed, or declare
    the milestone successful.
  - Deterministic tests (tests/*.py run via `python -B`) establish test
    pass/fail only.
  - Cursor (the reviewer) establishes reviewer outcome only, invoked
    read-only (`--mode ask`) and independently of any builder narrative.
  - `scripts/verify_assurance_baseline.py` (unmodified, unduplicated)
    establishes canonical repository assurance only.
  - This controller may transition phase only when the required evidence
    for that transition actually exists.
  - Bora is the final consequential approver; this module never commits,
    pushes, opens a PR, or merges.

PERSIST VS RECOMPUTE: historical run facts are persisted under a
gitignored local directory (`.career-os/`, see `.gitignore`); CURRENT
repository/Git/GitHub reality is always independently recomputed on
every `run`/`resume` call, never trusted merely because a manifest once
recorded it. See `revalidate_run()`.

EVIDENCE INVALIDATION: a successful test or review result is valid only
for the exact working-tree diff it evaluated (`compute_diff_fingerprint`).
Any working-tree mutation after a PASS invalidates that evidence; the
state machine's own phase actions always recompute before trusting
anything.

This module has ZERO dependency on a live Claude/Cursor session
surviving -- `builder_session_id`/`reviewer_session_id` are optional
accelerators only (passed to `--resume` when present), never required
for correctness. A fresh, from-scratch adapter invocation with no prior
session can always reconstruct the task from persisted run state plus
current repository/Git reality.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from career_os_state import validate_changed_paths  # noqa: E402 -- read-only reuse of existing canonical scope machinery
from schema_validation import build_draft202012_validator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT_DIRNAME = ".career-os"
MILESTONE_RUN_SCHEMA = ROOT / "schemas" / "milestone_run.schema.json"
MILESTONE_REVIEWER_RESULT_SCHEMA = ROOT / "schemas" / "milestone_reviewer_result.schema.json"
BUILDER_PROMPT_TEMPLATE = ROOT / "prompts" / "milestone_builder_v1.md"
REVIEWER_PROMPT_TEMPLATE = ROOT / "prompts" / "milestone_reviewer_v1.md"

DEFAULT_BRANCH = "main"

PHASES: tuple[str, ...] = (
    "INITIALIZING",
    "BUILDING",
    "TESTING",
    "REPAIRING",
    "REVIEWING",
    "CORRECTING_REVIEW",
    "ASSURING",
    "READY_FOR_HUMAN_APPROVAL",
    "HUMAN_REVIEW_REQUIRED",
    "ARCHITECTURE_DECISION_REQUIRED",
    "ABORTED",
)
TERMINAL_PHASES = frozenset(
    {"READY_FOR_HUMAN_APPROVAL", "HUMAN_REVIEW_REQUIRED", "ARCHITECTURE_DECISION_REQUIRED", "ABORTED"}
)

# Explicit durable transition table (Section 7). Any transition not
# listed here is illegal and fails closed -- see transition().
TRANSITIONS: dict[str, frozenset[str]] = {
    "INITIALIZING": frozenset({"BUILDING", "INITIALIZING", "HUMAN_REVIEW_REQUIRED"}),
    "BUILDING": frozenset({"TESTING", "BUILDING", "HUMAN_REVIEW_REQUIRED", "ARCHITECTURE_DECISION_REQUIRED"}),
    "TESTING": frozenset({"REVIEWING", "REPAIRING", "TESTING", "HUMAN_REVIEW_REQUIRED"}),
    "REPAIRING": frozenset({"TESTING", "REPAIRING", "HUMAN_REVIEW_REQUIRED", "ARCHITECTURE_DECISION_REQUIRED"}),
    "REVIEWING": frozenset({"ASSURING", "CORRECTING_REVIEW", "REVIEWING", "TESTING", "HUMAN_REVIEW_REQUIRED", "ARCHITECTURE_DECISION_REQUIRED"}),
    "CORRECTING_REVIEW": frozenset({"TESTING", "CORRECTING_REVIEW", "HUMAN_REVIEW_REQUIRED", "ARCHITECTURE_DECISION_REQUIRED"}),
    "ASSURING": frozenset({"READY_FOR_HUMAN_APPROVAL", "ASSURING", "TESTING", "HUMAN_REVIEW_REQUIRED"}),
    "READY_FOR_HUMAN_APPROVAL": frozenset(),
    "HUMAN_REVIEW_REQUIRED": frozenset(),
    "ARCHITECTURE_DECISION_REQUIRED": frozenset(),
    "ABORTED": frozenset(),
}
# Additive to the milestone prompt's own representative table, for three
# reasons none of which violates fail-closed semantics:
#   1. Self-loops (every non-terminal phase -> itself) represent "stay in
#      this phase and retry" after a bounded infrastructure hiccup
#      (Section 10.C/D and the F7 fetch-retry correction) -- the only way
#      a phase can legitimately re-persist itself. Every non-terminal
#      phase needs this now because the fetch-retry step (F7) runs
#      before phase-specific dispatch, regardless of which phase happens
#      to be current.
#   2. HUMAN_REVIEW_REQUIRED is reachable from every non-terminal phase
#      because revalidate_run() and validate_scope() -- Section 5's
#      "recompute reality on every advance() call, from whatever phase
#      the manifest currently records" -- both run BEFORE any
#      phase-specific action and can fail regardless of which phase
#      happens to be current; the alternative (letting a revalidation or
#      scope failure silently fall through without recording a stop)
#      would be worse than a slightly larger transition set.
#   3. REVIEWING->TESTING and ASSURING->TESTING (Cursor review correction
#      pass, findings F1/F5): a working-tree mutation detected between
#      TESTING and REVIEWING, or between the evidence ASSURING is meant
#      to certify and ASSURING's own actual execution, routes backward
#      to the earliest stage that must re-establish fresh evidence
#      (TESTING) rather than silently proceeding on stale evidence.


class MilestoneStateError(Exception):
    """A fail-closed controller error: something is wrong enough that no
    further automated progress is safe."""


class InvalidTransitionError(MilestoneStateError):
    pass


class LockHeldError(MilestoneStateError):
    def __init__(self, existing: Mapping[str, Any] | None):
        self.existing = existing
        super().__init__(f"governed branch/worktree lock already held: {existing}")


class InfrastructureError(Exception):
    """A transient failure invoking an external tool (builder/reviewer/
    git/tests) -- distinct from a fail-closed MilestoneStateError. Bounded
    by execution-policy retry limits, never retried unboundedly."""


class RecoverableSessionInfrastructureError(InfrastructureError):
    """CAREER_OS_BUILDER_SESSION_RECOVERY_AND_STRUCTURED_COMPLETION_V1.

    Raised only when a builder invocation's OUTER provider envelope
    parsed as strict JSON, was a mapping, carried a trustworthy string
    `session_id`, but the INNER structured builder result then failed
    extract_schema_valid_result() (missing, malformed, or ambiguous --
    e.g. Claude finished real work but replied in prose instead of the
    required JSON object). The session_id is real and resumable --
    silently discarding it would force the next attempt into a brand
    new session with no memory of already-completed work.

    Never raised for a malformed/unparseable outer envelope, a
    non-mapping envelope, or a missing/non-string session_id -- those
    remain plain InfrastructureError with no session recovery, since an
    untrusted envelope's session_id must never be invented or trusted."""

    def __init__(self, message: str, *, session_id: str):
        super().__init__(message)
        self.session_id = session_id


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Hashing / atomic persistence
# ----------------------------------------------------------------------

def sha256_of_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_json(path: Path, obj: Any) -> None:
    """Write JSON atomically: a crash mid-write leaves either the old
    valid file or nothing at the real path, never a partially written
    file accepted as valid."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _load_json_file(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 -- malformed/missing is a data fact, not a crash
        return None


# ----------------------------------------------------------------------
# Git primitives (independent, minimal -- career_os_state.py is a
# forbidden path for this milestone; these are read-only git queries,
# duplicated narrowly rather than importing that module's private
# helpers, to keep module boundaries clean).
# ----------------------------------------------------------------------

def _run_git(args: list[str], *, cwd: Path, timeout: int = 30) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"failed to execute git {args!r}: {exc!r}"
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout or "").strip()
    return True, completed.stdout.rstrip("\n").rstrip("\r")


def _run_subprocess(args: list[str], *, cwd: Path, timeout: int = 600) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s running {args!r}"
    except Exception as exc:  # noqa: BLE001
        return False, f"failed to execute {args!r}: {exc!r}"
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode == 0, output


def get_current_branch(*, cwd: Path) -> str | None:
    ok, out = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if ok and out and out != "HEAD":
        return out
    env_branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME")
    return env_branch or (out if ok and out else None)


def _is_ancestor(cwd: Path, ancestor: str, descendant: str) -> bool:
    try:
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=str(cwd), capture_output=True, timeout=30,
        )
    except Exception:  # noqa: BLE001
        return False
    return completed.returncode == 0


def compute_repo_facts(repo_root: Path, *, fetch: bool = True) -> dict[str, Any]:
    """Recompute (never trust cached) current Git reality.

    F7 correction: `fetch_ok` is surfaced explicitly. A failed `git
    fetch origin main` must never be silently swallowed in favor of
    whatever stale `refs/remotes/origin/main` value happens to already
    exist locally -- callers MUST check `fetch_ok` (when `fetch=True`)
    before trusting `origin_main`."""
    fetch_ok = True
    if fetch:
        fetch_ok, _ = _run_git(["fetch", "origin", "main"], cwd=repo_root, timeout=60)
    branch = get_current_branch(cwd=repo_root)
    head_ok, head = _run_git(["rev-parse", "HEAD"], cwd=repo_root)
    origin_ok, origin_main = _run_git(["rev-parse", "origin/main"], cwd=repo_root)
    dirty_ok, dirty_out = _run_git(["status", "--porcelain", "--untracked-files=all"], cwd=repo_root)
    return {
        "branch": branch,
        "head": head if head_ok else None,
        "origin_main": origin_main if origin_ok else None,
        "dirty": bool(dirty_ok and dirty_out.strip()),
        "fetch_ok": fetch_ok,
    }


def compute_diff_fingerprint(repo_root: Path, baseline_sha: str) -> str:
    """Deterministic fingerprint of everything that differs from
    baseline_sha in the current working tree -- committed AND
    uncommitted tracked changes, plus the actual byte content of every
    untracked file (git diff alone does not show untracked file
    content). Any working-tree mutation changes this fingerprint;
    evidence tied to a stale fingerprint is never reused.

    F11 (LOW, fixed): plain `git diff` alone is insufficient to
    distinguish two DIFFERENT tracked-binary contents that both differ
    from baseline -- git's textual binary-diff header ("Binary files a/x
    and b/x differ") is a fixed string carrying no content-specific
    information, so a tracked binary changing from content A to content
    B (both non-baseline) could otherwise leave the fingerprint
    unchanged between two reads. `git diff --raw` additionally includes
    the actual before/after blob SHA-1 for every changed tracked path,
    which does distinguish them; it is cheap, deterministic, and adds no
    new dependency."""
    ok_diff, diff_out = _run_git(["diff", baseline_sha, "--", "."], cwd=repo_root, timeout=60)
    ok_raw, raw_out = _run_git(["diff", "--raw", baseline_sha, "--", "."], cwd=repo_root, timeout=60)
    ok_status, status_out = _run_git(["status", "--porcelain", "--untracked-files=all"], cwd=repo_root)
    parts = [
        diff_out if ok_diff else "<git-diff-failed>",
        raw_out if ok_raw else "<git-diff-raw-failed>",
    ]
    if ok_status:
        for line in status_out.splitlines():
            if line.startswith("??"):
                rel = line[3:].strip()
                try:
                    content = (repo_root / rel).read_bytes()
                    parts.append(f"UNTRACKED:{rel}:{sha256_of_bytes(content)}")
                except OSError:
                    parts.append(f"UNTRACKED:{rel}:<unreadable>")
    return sha256_of_text("\n".join(parts))


# ----------------------------------------------------------------------
# Contract / policy
# ----------------------------------------------------------------------

def load_contract(contract_path: Path) -> dict[str, Any]:
    return json.loads(contract_path.read_text(encoding="utf-8"))


def contract_hash(contract_path: Path) -> str:
    return sha256_of_text(contract_path.read_text(encoding="utf-8"))


def load_policy(policy_path: Path) -> dict[str, Any]:
    return json.loads(policy_path.read_text(encoding="utf-8"))


def policy_hash(policy_path: Path) -> str:
    return sha256_of_text(policy_path.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------
# Run directory layout / manifest
# ----------------------------------------------------------------------

def runs_root(repo_root: Path) -> Path:
    return repo_root / RUN_ROOT_DIRNAME / "runs"


def run_dir(repo_root: Path, run_id: str) -> Path:
    return runs_root(repo_root) / run_id


def locks_dir(repo_root: Path) -> Path:
    return repo_root / RUN_ROOT_DIRNAME / "locks"


def generate_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]


def validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return {"valid": False, "errors": [_error("MANIFEST_MALFORMED", detail="manifest must be an object")]}
    validator = build_draft202012_validator(MILESTONE_RUN_SCHEMA)
    if not validator.is_valid(manifest):
        return {
            "valid": False,
            "errors": [_error("MANIFEST_MALFORMED", detail=m) for m in (e.message for e in validator.iter_errors(manifest))],
        }
    return {"valid": True, "errors": []}


def load_manifest(rdir: Path) -> dict[str, Any] | None:
    return _load_json_file(rdir / "manifest.json")


def save_manifest(rdir: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    manifest = dict(manifest)
    manifest["updated_at"] = _now_iso()
    result = validate_manifest(manifest)
    if not result["valid"]:
        raise MilestoneStateError(f"refusing to persist invalid manifest: {result['errors']}")
    atomic_write_json(rdir / "manifest.json", manifest)
    return manifest


def append_event(rdir: Path, event: Mapping[str, Any]) -> None:
    path = rdir / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(event)
    payload.setdefault("ts", _now_iso())
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def transition(manifest: Mapping[str, Any], new_phase: str, *, stop_reason: str | None = None) -> dict[str, Any]:
    current = manifest["phase"]
    allowed = TRANSITIONS.get(current, frozenset())
    if new_phase not in allowed:
        raise InvalidTransitionError(f"illegal transition {current} -> {new_phase}")
    updated = dict(manifest)
    updated["phase"] = new_phase
    if stop_reason is not None:
        updated["stop_reason"] = stop_reason
    return updated


# ----------------------------------------------------------------------
# Locking (Section 9) -- local, atomic-exclusive-create, explicit
# fail-closed stale-lock recovery only.
# ----------------------------------------------------------------------

def _sanitize_branch_for_filename(branch: str) -> str:
    return branch.replace("/", "__")


def lock_path(repo_root: Path, branch: str) -> Path:
    return locks_dir(repo_root) / f"{_sanitize_branch_for_filename(branch)}.lock.json"


def read_lock(repo_root: Path, branch: str) -> dict[str, Any] | None:
    return _load_json_file(lock_path(repo_root, branch))


def acquire_lock(repo_root: Path, branch: str, *, run_id: str, worktree_path: str) -> dict[str, Any]:
    path = lock_path(repo_root, branch)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": run_id,
        "branch": branch,
        "worktree": worktree_path,
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "owner_token": uuid.uuid4().hex,
        "acquired_at": _now_iso(),
    }
    try:
        # O_CREAT|O_EXCL is an atomic exclusive create on both POSIX and
        # Windows -- the correct primitive for "exactly one owner".
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise LockHeldError(read_lock(repo_root, branch))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(record, indent=2, sort_keys=True))
    return record


def release_lock(repo_root: Path, branch: str, *, owner_token: str) -> None:
    path = lock_path(repo_root, branch)
    current = read_lock(repo_root, branch)
    if current is None:
        return
    if current.get("owner_token") != owner_token:
        raise MilestoneStateError("refusing to release a lock this run does not own")
    path.unlink(missing_ok=True)


def takeover_stale_lock(repo_root: Path, branch: str, *, new_run_id: str, worktree_path: str) -> dict[str, Any]:
    """Explicit, human-requested stale-lock recovery (`resume --recover-stale-lock`).
    Never silently deletes -- archives the old lock record first."""
    existing = read_lock(repo_root, branch)
    path = lock_path(repo_root, branch)
    if existing is not None:
        archive_dir = locks_dir(repo_root) / "stale-archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"{_sanitize_branch_for_filename(branch)}.{uuid.uuid4().hex[:8]}.json"
        atomic_write_json(archive_path, {**existing, "recovered_at": _now_iso(), "recovered_by_run_id": new_run_id})
        path.unlink(missing_ok=True)
    return acquire_lock(repo_root, branch, run_id=new_run_id, worktree_path=worktree_path)


# ----------------------------------------------------------------------
# Preflight / init / revalidation
# ----------------------------------------------------------------------

def init_run(repo_root: Path, contract_path: Path, policy_path: Path) -> dict[str, Any]:
    """Preflight, then (only if preflight passes) create a fresh run
    directory + manifest. Never creates a partial run on preflight
    failure."""
    contract = load_contract(contract_path)
    facts = compute_repo_facts(repo_root)

    if not facts["fetch_ok"]:
        # F7: never authorize a fresh run against a possibly-stale
        # origin/main -- a failed fetch is a preflight failure, not
        # something to silently fall back past.
        return {"ok": False, "escalation": "HUMAN_REVIEW_REQUIRED", "errors": [_error("PREFLIGHT_FETCH_FAILED")]}

    if facts["branch"] is None or facts["origin_main"] is None:
        return {"ok": False, "escalation": "HUMAN_REVIEW_REQUIRED", "errors": [_error("PREFLIGHT_GIT_QUERY_FAILED", facts=facts)]}

    if facts["branch"] == DEFAULT_BRANCH:
        return {
            "ok": False,
            "escalation": "ARCHITECTURE_DECISION_REQUIRED",
            "errors": [_error("PREFLIGHT_WRONG_BRANCH", detail="controller must run on a governed feature branch, not main")],
        }

    if not _is_ancestor(repo_root, contract["baseline_sha"], facts["origin_main"]):
        return {
            "ok": False,
            "escalation": "HUMAN_REVIEW_REQUIRED",
            "errors": [
                _error(
                    "PREFLIGHT_BASELINE_INCOMPATIBLE",
                    authorized_baseline=contract["baseline_sha"],
                    origin_main=facts["origin_main"],
                )
            ],
        }

    run_id = generate_run_id()
    rdir = run_dir(repo_root, run_id)
    rdir.mkdir(parents=True, exist_ok=False)
    for sub in ("state-checks", "builder", "tests", "reviews", "assurance"):
        (rdir / sub).mkdir(parents=True, exist_ok=True)

    atomic_write_json(rdir / "contract.snapshot.json", contract)
    atomic_write_json(rdir / "execution-policy.snapshot.json", load_policy(policy_path))

    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "milestone_id": contract["milestone_id"],
        "contract_path": str(contract_path.resolve().relative_to(repo_root.resolve())).replace("\\", "/"),
        "contract_sha256": contract_hash(contract_path),
        "execution_policy_sha256": policy_hash(policy_path),
        "authorized_baseline_sha": contract["baseline_sha"],
        "origin_main_observed_sha": facts["origin_main"],
        "working_branch": facts["branch"],
        "worktree_path": str(repo_root.resolve()),
        "phase": "INITIALIZING",
        "implementation_attempt_count": 0,
        "repair_attempt_count": 0,
        "review_attempt_count": 0,
        "review_correction_count": 0,
        "infrastructure_retry_count": 0,
        "builder_session_id": None,
        "reviewer_session_id": None,
        "diff_fingerprint": None,
        "last_test_artifact": None,
        "last_valid_test_artifact": None,
        "last_valid_test_diff_fingerprint": None,
        "last_reviewer_artifact": None,
        "last_reviewer_diff_fingerprint": None,
        "assurance_artifact": None,
        "stop_reason": None,
        "human_approval_state": "NOT_REQUESTED",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    save_manifest(rdir, manifest)
    append_event(rdir, {"event": "RUN_INITIALIZED", "run_id": run_id, "branch": facts["branch"]})
    return {"ok": True, "run_id": run_id}


def revalidate_run(repo_root: Path, manifest: Mapping[str, Any], *, fetch: bool = True) -> dict[str, Any]:
    """Re-verify EVERY fact this run depends on against live reality.
    Never trust the manifest's own historical claims.

    `fetch=False` lets a caller that already performed its own
    fetch-with-explicit-retry-handling this same advance() call (see
    F7) avoid a redundant second `git fetch`."""
    errors: list[dict[str, Any]] = []

    contract_path = repo_root / manifest["contract_path"]
    if not contract_path.exists():
        return {"valid": False, "errors": [_error("CONTRACT_MISSING", path=str(contract_path))]}
    current_contract_hash = contract_hash(contract_path)
    if current_contract_hash != manifest["contract_sha256"]:
        return {
            "valid": False,
            "errors": [
                _error(
                    "CONTRACT_HASH_MISMATCH",
                    expected=manifest["contract_sha256"],
                    actual=current_contract_hash,
                )
            ],
        }
    contract = load_contract(contract_path)

    if str(repo_root.resolve()) != manifest["worktree_path"]:
        errors.append(
            _error("WORKTREE_IDENTITY_MISMATCH", expected=manifest["worktree_path"], actual=str(repo_root.resolve()))
        )

    facts = compute_repo_facts(repo_root, fetch=fetch)
    if fetch and not facts["fetch_ok"]:
        return {"valid": False, "errors": [_error("REVALIDATION_FETCH_FAILED")]}
    if facts["branch"] != manifest["working_branch"]:
        errors.append(_error("BRANCH_IDENTITY_MISMATCH", expected=manifest["working_branch"], actual=facts["branch"]))
    if facts["origin_main"] != manifest["origin_main_observed_sha"]:
        # Section 10.H: origin/main advancing mid-run is NEVER
        # auto-absorbed, even as a legitimate fast-forward.
        errors.append(
            _error(
                "ORIGIN_MAIN_ADVANCED",
                observed_at_init=manifest["origin_main_observed_sha"],
                current=facts["origin_main"],
            )
        )

    return {"valid": len(errors) == 0, "errors": errors, "facts": facts, "contract": contract}


# ----------------------------------------------------------------------
# Scope validation (reuses existing canonical machinery, Section 5)
# ----------------------------------------------------------------------

def validate_scope(repo_root: Path, contract: Mapping[str, Any], baseline_sha: str) -> dict[str, Any]:
    return validate_changed_paths(contract, baseline_sha, cwd=repo_root)


# ----------------------------------------------------------------------
# Builder / reviewer result validation
# ----------------------------------------------------------------------

def validate_builder_result(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {"valid": False, "errors": [_error("BUILDER_RESULT_MALFORMED", detail="not an object")]}
    if raw.get("status") not in ("IMPLEMENTATION_ATTEMPT_COMPLETE", "STOPPED"):
        return {"valid": False, "errors": [_error("BUILDER_RESULT_MALFORMED", detail=f"invalid status {raw.get('status')!r}")]}
    return {"valid": True, "errors": []}


def validate_reviewer_result(raw: Any) -> dict[str, Any]:
    """F4 correction: schema validity alone is not sufficient. A
    provider's own outcome classification is never trusted blindly --
    `outcome: "SAFE"` is internally inconsistent (and therefore treated
    as malformed, same as a schema failure) if it is accompanied by any
    finding marked `required: true` or `severity: "BLOCKING"`."""
    if not isinstance(raw, Mapping):
        return {"valid": False, "errors": [_error("REVIEWER_RESULT_MALFORMED", detail="not an object")]}
    validator = build_draft202012_validator(MILESTONE_REVIEWER_RESULT_SCHEMA)
    if not validator.is_valid(raw):
        return {
            "valid": False,
            "errors": [_error("REVIEWER_RESULT_MALFORMED", detail=m) for m in (e.message for e in validator.iter_errors(raw))],
        }
    if raw.get("outcome") == "SAFE":
        for finding in raw.get("findings", []):
            if isinstance(finding, Mapping) and (finding.get("required") is True or finding.get("severity") == "BLOCKING"):
                return {
                    "valid": False,
                    "errors": [
                        _error(
                            "REVIEWER_RESULT_MALFORMED",
                            detail=f"SAFE outcome is internally inconsistent with a required=true or BLOCKING finding: {finding!r}",
                        )
                    ],
                }
    return {"valid": True, "errors": []}


def required_findings(reviewer_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [f for f in reviewer_result.get("findings", []) if f.get("required") is True]


# ----------------------------------------------------------------------
# Deterministic test / assurance execution
# ----------------------------------------------------------------------

def run_required_tests(repo_root: Path, test_paths: Sequence[str], *, rdir: Path) -> dict[str, Any]:
    results = []
    all_ok = True
    for rel in test_paths:
        ok, output = _run_subprocess([sys.executable, "-B", rel], cwd=repo_root, timeout=600)
        results.append({"test": rel, "ok": ok, "output": output[-4000:]})
        all_ok = all_ok and ok
    artifact = {"ok": all_ok, "results": results, "at": _now_iso()}
    artifact_path = rdir / "tests" / f"{uuid.uuid4().hex[:8]}.json"
    atomic_write_json(artifact_path, artifact)
    return {"ok": all_ok, "artifact_path": str(artifact_path), "results": results}


def run_assurance(repo_root: Path, *, rdir: Path) -> dict[str, Any]:
    ok, output = _run_subprocess(
        [sys.executable, "-B", "scripts/verify_assurance_baseline.py"], cwd=repo_root, timeout=600
    )
    artifact = {"ok": ok, "output": output[-8000:], "at": _now_iso()}
    artifact_path = rdir / "assurance" / f"{uuid.uuid4().hex[:8]}.json"
    atomic_write_json(artifact_path, artifact)
    return {"ok": ok, "artifact_path": str(artifact_path)}


# ----------------------------------------------------------------------
# Builder / reviewer adapters -- REAL invocations (used only by the CLI
# at actual runtime). Unit tests inject fakes via Adapters below and
# never exercise these functions directly.
# ----------------------------------------------------------------------

def _parse_strict_json(text: str) -> Any:
    """Strict full-document JSON parse only -- NO fuzzy extraction.
    Used for a provider's own OUTER envelope, which `--output-format
    json` contractually guarantees is a single well-formed JSON document
    on a successful (exit 0) invocation -- empirically confirmed against
    both the real Claude Code CLI and the real Cursor Agent CLI. If the
    outer envelope is not strict JSON, that is a genuine infrastructure
    problem worth failing on, not something to fuzzy-parse around."""
    if not isinstance(text, str):
        raise InfrastructureError(f"expected a string to parse as the provider envelope, got {type(text).__name__}")
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise InfrastructureError(f"provider envelope is not strict JSON ({exc}): {text[:500]!r}")


def _find_all_balanced_json_objects(text: str) -> list[Any]:
    """Every top-level JSON object in text, found via
    `json.JSONDecoder().raw_decode` from each candidate `{` offset --
    NEVER a handwritten brace/string scanner. Used ONLY as the
    noisy-free-text fallback for a provider's own result field (never
    for the outer envelope, which is always parsed strictly by
    `_parse_strict_json`).

    F6-R1 correction (Cursor rereview, BLOCKING): the prior
    implementation counted raw `{`/`}` characters without any awareness
    of JSON string boundaries. A `}` appearing inside a JSON string
    VALUE (e.g. a reviewer finding's own `"invariant": "closing brace }
    must be handled"`) was miscounted as closing the object, truncating
    the real result and leaving only whatever shorter, earlier, often
    unrelated object the premature close happened to complete --
    reproducible exactly as an attacker-controlled or merely
    coincidental "false SAFE" result. `raw_decode` is the real stdlib
    JSON tokenizer: it correctly consumes escaped quotes/backslashes,
    Unicode, and nested objects/arrays exactly as the JSON grammar
    defines them, so a brace inside a string is never mistaken for
    structural syntax."""
    decoder = json.JSONDecoder()
    candidates: list[Any] = []
    idx = 0
    length = len(text)
    while idx < length:
        brace_pos = text.find("{", idx)
        if brace_pos == -1:
            break
        try:
            obj, end = decoder.raw_decode(text, brace_pos)
        except json.JSONDecodeError:
            idx = brace_pos + 1
            continue
        candidates.append(obj)
        idx = end
    return candidates


def extract_schema_valid_result(text: str, *, validate: Callable[[Any], dict[str, Any]]) -> Any:
    """F6 correction. Fail-closed extraction of exactly ONE structured
    result matching `validate` from a provider's free-text result field.

    Reproduced defect this replaces: a prior "first balanced JSON object
    wins" strategy would accept an early, schema-valid SAFE object even
    when a later, ALSO schema-valid (but conflicting) CHANGES_REQUIRED
    object appeared further in the same text -- i.e. prose containing
    both an example/draft SAFE reply and the provider's actual final
    CHANGES_REQUIRED reply could silently resolve to SAFE. This function
    never picks a winner by position:
      1. if the WHOLE text is itself strict JSON and schema-valid,
         accept it (the normal, non-noisy case);
      2. otherwise, collect every balanced {...} candidate, keep only
         the ones that are schema-valid;
      3. exactly one schema-valid candidate -> accept it;
      4. zero -> InfrastructureError (malformed -- bounded retry);
      5. two or more -> InfrastructureError (ambiguous/conflicting --
         never guess which one is authoritative; bounded retry)."""
    if not isinstance(text, str):
        raise InfrastructureError(f"expected a string provider result field, got {type(text).__name__}")
    stripped = text.strip()
    try:
        whole = json.loads(stripped)
        if validate(whole)["valid"]:
            return whole
    except json.JSONDecodeError:
        pass

    candidates = _find_all_balanced_json_objects(stripped)
    valid_candidates = [c for c in candidates if validate(c)["valid"]]
    if len(valid_candidates) == 1:
        return valid_candidates[0]
    if not valid_candidates:
        raise InfrastructureError(f"no schema-valid structured result found in provider output: {stripped[:500]!r}")
    raise InfrastructureError(
        f"{len(valid_candidates)} conflicting schema-valid structured results found in provider output -- "
        f"refusing to guess which is authoritative: {stripped[:500]!r}"
    )


def _find_binary(name: str, extra_candidates: Sequence[str] = ()) -> str:
    found = shutil.which(name)
    if found:
        return found
    for candidate in extra_candidates:
        if Path(candidate).exists():
            return candidate
    raise InfrastructureError(f"required executable {name!r} not found on PATH")


def _find_claude_binary() -> str:
    """Resolve the Claude Code executable, preferring the native
    `claude.exe` over the npm-generated `claude.cmd`/`claude.CMD`
    wrapper on Windows.

    ARGV-W1 correction (Cursor review, HIGH): empirically reproduced --
    on Windows, `shutil.which("claude")` resolves to `claude.CMD`
    (PATHEXT resolution order). That wrapper re-parses argv through
    `cmd.exe`'s `%*` expansion, which does NOT preserve embedded
    newlines: a real multiline builder prompt ("line one\\nline
    two\\nline three") arrived at Claude as only "line one" -- silently
    truncated, with no error at all. The native `claude.exe` (verified
    directly) preserves the exact same multiline prompt byte-for-byte.
    Since every real controller builder prompt is multiline
    (`prompts/milestone_builder_v1.md` is a multi-section template), the
    `.cmd` wrapper is never an acceptable substitute when a native
    executable is available.

    npm installs a bundled native binary for this package at a
    deterministic path RELATIVE TO THE WRAPPER'S OWN DIRECTORY --
    `<wrapper_dir>/node_modules/@anthropic-ai/claude-code/bin/claude.exe`
    (confirmed by reading the actual installed `claude.cmd` contents,
    which itself invokes exactly this relative path). This is not a
    machine-specific absolute path: it is derived from wherever
    `shutil.which` actually found the wrapper, so it works on any
    machine with the same npm global-install layout.

    If `which` resolves directly to a non-`.cmd` executable (already the
    case on non-Windows, and would remain so if a future Windows install
    ever ships a bare `claude.exe` on PATH), it is used unchanged --
    non-Windows behavior is untouched.

    Fail-closed: if only the `.cmd`/`.CMD` wrapper can be found and the
    expected native sibling executable does not exist at that
    deterministic relative path, this raises InfrastructureError rather
    than silently falling back to a wrapper known to corrupt multiline
    prompt content -- "no usable Claude executable" now specifically
    means "none that can carry the real prompt intact", not merely
    "PATH resolved to nothing"."""
    found = shutil.which("claude")
    if not found:
        raise InfrastructureError("required executable 'claude' not found on PATH")
    found_path = Path(found)
    if found_path.suffix.lower() != ".cmd":
        return found
    native = found_path.parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    if native.exists():
        return str(native)
    raise InfrastructureError(
        f"only the argv-corrupting claude.cmd wrapper was found ({found}); "
        f"the expected native executable {native} does not exist -- refusing to invoke "
        "a wrapper known to truncate multiline prompt content"
    )


def real_claude_builder_invoker(
    *, prompt: str, cwd: Path, policy: Mapping[str, Any], session_id: str | None
) -> dict[str, Any]:
    """Invoke Claude Code as the bounded builder: non-interactive
    (--print), structured JSON output, restricted tool authority (no
    Bash beyond what --allowedTools grants), never --dangerously-skip-permissions.

    F9 correction (empirically verified against the real installed
    Claude Code CLI, `claude -p --output-format json`, a harmless
    non-mutating invocation, NOT counted as milestone review): the
    top-level envelope is `{"result": "<free text>", "session_id": ...,
    ...many other provider metadata fields...}` -- it is NOT the
    builder's own structured result object. A prior implementation
    returned the raw outer envelope directly, which would never satisfy
    validate_builder_result() (no "status" field) against any real
    invocation. The builder's own JSON reply must be extracted from the
    envelope's `result` STRING field.

    CAREER_OS_CLAUDE_BUILDER_ARGV_ORDERING_FIX_V1 (reproduced on the
    first real controller run, corrected twice):

    Pass 1 -- `--allowedTools <tools...>` is a Commander.js VARIADIC
    option -- it greedily consumes every subsequent positional argument
    as an additional tool-name value. Placing the prompt after
    `--allowedTools` left the CLI with zero positional prompt arguments,
    always failing with "Input must be provided either through stdin or
    as a prompt argument when using --print". First-fix attempt: move
    the prompt to be the very first argument, before every flag.

    Pass 2 (Cursor rereview, ARGV-W1/leading-dash finding) -- moving the
    prompt first is insufficient on its own: a prompt whose own text
    happens to begin with `-` or `--` (a real possibility for a builder
    prompt, since it is assembled from a template and not otherwise
    constrained) is misparsed as an option token by the CLI's argument
    parser regardless of position, verified directly (`-reply...` was
    read as an attempted short option; `--reply...` produced "unknown
    option"). The corrected shape instead places every flag first, then
    the literal `--` positional-terminator token, then the prompt last.
    `--` is Commander.js's (and the general POSIX convention's) standard
    signal that everything following is positional data, never an
    option -- this was verified directly to correctly and simultaneously
    handle: a normal prompt, a multiline prompt, a prompt beginning with
    `-`, a prompt beginning with `--`, a prompt containing the literal
    substring "--allowedTools" embedded in its own text, and a Unicode
    prompt -- all six arrived at Claude character-for-character intact.
    `--` also correctly terminates `--allowedTools`'s own variadic
    collection, so the original Pass-1 defect remains fixed too. No
    `shell=True`, no command-string quoting, and no stdin-based
    invocation was needed -- argv-based invocation with a trailing `--`
    satisfies the full contract.

    CAREER_OS_BUILDER_SESSION_RECOVERY_AND_STRUCTURED_COMPLETION_V1
    (reproduced on the second real controller run, run_id
    20260907T193310Z-f6a756d2: the builder genuinely performed substantial
    real work across 3 independent attempts, but each attempt's final
    reply was conversational prose rather than the required structured
    JSON result, so extract_schema_valid_result() raised on all three --
    and, before this fix, each retry silently discarded a perfectly good,
    resumable session_id and started over from zero): once the OUTER
    envelope has parsed as strict JSON and is confirmed to be a mapping
    carrying a trustworthy string session_id, a failure extracting the
    INNER structured result is raised as RecoverableSessionInfrastructureError
    (carrying that session_id) instead of a plain InfrastructureError, so
    the caller can resume the same session with a narrow completion-only
    instruction instead of starting a fresh one. A malformed/unparseable
    outer envelope, or one with no trustworthy session_id, is never
    upgraded this way -- it remains a plain, non-recoverable
    InfrastructureError, exactly as before.

    SR-WS-1 (Cursor correction pass): a whitespace-only session_id
    (e.g. "   ") is stripped before the recoverability check, and the
    stripped value is what gets carried forward -- never treated as
    recoverable, never trusted, never reaches --resume."""
    claude_bin = _find_claude_binary()
    args = [
        claude_bin,
        "-p",
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        "Read,Write,Edit,Glob,Grep",
    ]
    if session_id:
        args += ["--resume", session_id]
    args += ["--", prompt]
    ok, output = _run_subprocess(args, cwd=cwd, timeout=int(policy["builder_timeout_seconds"]))
    if not ok:
        raise InfrastructureError(f"builder invocation failed: {output[-2000:]}")
    envelope = _parse_strict_json(output)
    if not isinstance(envelope, Mapping) or not isinstance(envelope.get("result"), str):
        raise InfrastructureError(f"builder envelope missing string 'result' field: {envelope!r}")
    envelope_session_id = envelope.get("session_id")
    # SR-WS-1 (Cursor correction pass): a whitespace-only session_id
    # (e.g. "   ") is not a real session identity and must never be
    # treated as recoverable or ever reach --resume. Use the stripped,
    # canonical value both for the recoverability check and for the
    # value actually carried forward.
    recoverable_session_id: str | None = None
    if isinstance(envelope_session_id, str):
        stripped_session_id = envelope_session_id.strip()
        if stripped_session_id:
            recoverable_session_id = stripped_session_id
    try:
        result = extract_schema_valid_result(envelope["result"], validate=validate_builder_result)
    except InfrastructureError as exc:
        if recoverable_session_id is not None:
            raise RecoverableSessionInfrastructureError(str(exc), session_id=recoverable_session_id) from exc
        raise
    if envelope.get("session_id"):
        result = dict(result)
        result["session_id"] = envelope["session_id"]
    return result


def real_cursor_reviewer_invoker(*, prompt: str, cwd: Path, policy: Mapping[str, Any]) -> dict[str, Any]:
    """Invoke Cursor Agent CLI as the independent read-only reviewer:
    non-interactive (-p), read-only (--mode ask, empirically verified
    structurally enforced -- see the ADR), workspace-trusted (this
    repository, not an arbitrary directory), structured JSON output.
    Never --force/--yolo."""
    agent_bin = _find_binary(
        "agent",
        extra_candidates=[str(Path.home() / "AppData" / "Local" / "cursor-agent" / "agent.cmd")],
    )
    args = [
        agent_bin,
        "-p",
        "--output-format",
        "json",
        "--mode",
        "ask",
        "--trust",
        "--workspace",
        str(cwd),
        prompt,
    ]
    ok, output = _run_subprocess(args, cwd=cwd, timeout=int(policy["reviewer_timeout_seconds"]))
    if not ok:
        raise InfrastructureError(f"reviewer invocation failed: {output[-2000:]}")
    envelope = _parse_strict_json(output)
    result_text = envelope.get("result") if isinstance(envelope, Mapping) else None
    if not isinstance(result_text, str):
        raise InfrastructureError(f"reviewer envelope missing string 'result' field: {envelope!r}")
    return extract_schema_valid_result(result_text, validate=validate_reviewer_result)


BuilderInvoker = Callable[..., dict[str, Any]]
ReviewerInvoker = Callable[..., dict[str, Any]]
TestRunner = Callable[..., dict[str, Any]]
AssuranceRunner = Callable[..., dict[str, Any]]


@dataclass
class Adapters:
    """Injectable provider adapters. Unit tests supply fakes for all
    four (never requiring live Claude/Cursor/network availability, per
    the milestone contract's own explicit requirement); the CLI supplies
    the real_* / run_required_tests / run_assurance functions above by
    default."""

    builder_invoker: BuilderInvoker
    reviewer_invoker: ReviewerInvoker
    test_runner: TestRunner = run_required_tests
    assurance_runner: AssuranceRunner = run_assurance


# ----------------------------------------------------------------------
# Prompt building
# ----------------------------------------------------------------------

def _format_list(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "(none)"


def build_builder_prompt(
    contract: Mapping[str, Any],
    *,
    deterministic_failures: str = "(none -- first attempt)",
    reviewer_findings_text: str = "(none -- this is not a correction pass)",
) -> str:
    template = BUILDER_PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return template.format(
        milestone_id=contract["milestone_id"],
        goal=contract["goal"],
        allowed_paths=_format_list(contract["allowed_paths"]),
        forbidden_paths=_format_list(contract["forbidden_paths"]),
        deterministic_failures=deterministic_failures,
        reviewer_findings=reviewer_findings_text,
    )


def build_resumed_completion_prompt(contract: Mapping[str, Any]) -> str:
    """CAREER_OS_BUILDER_SESSION_RECOVERY_AND_STRUCTURED_COMPLETION_V1.

    Used ONLY for a bounded resumed retry after a RecoverableSessionInfrastructureError
    (a real, valid session whose prior turn finished in prose instead of
    the required structured result). Deliberately narrow and
    completion-focused -- it must never re-issue the full original task
    prompt (that would blindly rerun already-completed work as if
    nothing happened) and must never authorize broader scope than the
    original invocation already carried. Does not require a change to
    prompts/milestone_builder_v1.md: the full task context already lives
    inside the resumed Claude session itself via --resume."""
    return (
        f"You are still the BOUNDED IMPLEMENTATION BUILDER for milestone "
        f"{contract['milestone_id']!r}, resuming this exact same session.\n\n"
        "Your previous turn in this session did real work but did not end "
        "with the required structured completion result -- it ended in "
        "prose instead of the required JSON object.\n\n"
        "Do NOT restart, redo, or broaden the task. Do NOT make any further "
        "code changes beyond what is strictly necessary to finish what you "
        "had already started. Briefly inspect the current state of your own "
        "prior work if needed, then reply with ONLY the required builder "
        "result JSON object as your final output -- no prose before or "
        "after it. The object must have a top-level \"status\" field equal "
        "to exactly \"IMPLEMENTATION_ATTEMPT_COMPLETE\" (if your changes are "
        "in place) or \"STOPPED\" (if you must stop without completing, in "
        "which case also include \"stop_condition_encountered\" describing "
        "why, and \"architecture_decision_required\": true only if that stop "
        "is because a material architecture decision is required)."
    )


def build_reviewer_prompt(
    contract: Mapping[str, Any], *, diff: str, test_evidence: str, governance_excerpt: str
) -> str:
    template = REVIEWER_PROMPT_TEMPLATE.read_text(encoding="utf-8")
    return template.format(
        milestone_id=contract["milestone_id"],
        goal=contract["goal"],
        baseline_sha=contract["baseline_sha"],
        allowed_paths=_format_list(contract["allowed_paths"]),
        forbidden_paths=_format_list(contract["forbidden_paths"]),
        diff=diff[-20000:],
        test_evidence=test_evidence[-6000:],
        governance_excerpt=governance_excerpt,
    )


# ----------------------------------------------------------------------
# Single-phase state-machine step
# ----------------------------------------------------------------------

def _apply_infra_retry(manifest: dict[str, Any], policy: Mapping[str, Any], phase: str, exc: Exception) -> dict[str, Any]:
    manifest["infrastructure_retry_count"] += 1
    if manifest["infrastructure_retry_count"] > int(policy.get("infrastructure_retry_limit", 0)):
        return transition(manifest, "HUMAN_REVIEW_REQUIRED", stop_reason=f"infrastructure_retry_limit exhausted: {exc}")
    return transition(manifest, phase)  # self-loop retry


def advance(repo_root: Path, run_id: str, adapters: Adapters) -> dict[str, Any]:
    """Execute exactly ONE phase's worth of work and persist the result.
    Idempotent-safe to call repeatedly: a crash mid-phase simply means
    the phase's own action is redone on the next call, never silently
    skipped or guessed.

    CENTRALIZED INVARIANT SEQUENCE (Cursor review correction pass;
    replaces four disconnected conditionals that could drift apart with
    one shared ordering, applied at the top of EVERY call regardless of
    current phase):
      1. fetch origin/main (bounded infra retry on failure -- F7);
      2. revalidate_run() -- contract hash, branch/worktree identity,
         origin/main drift (immediate stop, never retried -- these are
         real fact mismatches, not transient infrastructure hiccups);
      3. validate_scope() -- every currently changed path against
         allowed_paths/forbidden_paths/protected-path rules (immediate
         stop -- F2);
      4. recompute the diff fingerprint fresh.
    Only after all four does phase-specific action run, and several
    phase actions perform their OWN additional fingerprint check against
    the specific evidence they are about to rely on (F1/F5)."""
    rdir = run_dir(repo_root, run_id)
    manifest = load_manifest(rdir)
    if manifest is None:
        raise MilestoneStateError(f"no manifest for run_id {run_id}")
    validity = validate_manifest(manifest)
    if not validity["valid"]:
        raise MilestoneStateError(f"corrupted manifest, refusing to proceed: {validity['errors']}")

    if manifest["phase"] in TERMINAL_PHASES:
        return manifest  # no-op: nothing left to advance

    policy = _load_json_file(rdir / "execution-policy.snapshot.json") or {}
    phase = manifest["phase"]

    # Step 1 (F7): fetch is consequential and bounded-retryable -- never
    # silently fall back to a stale cached origin/main.
    fetch_ok, _fetch_out = _run_git(["fetch", "origin", "main"], cwd=repo_root, timeout=60)
    if not fetch_ok:
        manifest = _apply_infra_retry(manifest, policy, phase, InfrastructureError("git fetch origin main failed"))
        manifest = save_manifest(rdir, manifest)
        append_event(rdir, {"event": "INFRASTRUCTURE_ERROR", "detail": "git fetch origin main failed", "phase": phase})
        return manifest

    # Step 2: identity/contract revalidation -- immediate stop, never retried.
    revalidation = revalidate_run(repo_root, manifest, fetch=False)
    if not revalidation["valid"]:
        manifest = transition(manifest, "HUMAN_REVIEW_REQUIRED", stop_reason=json.dumps(revalidation["errors"]))
        manifest = save_manifest(rdir, manifest)
        append_event(rdir, {"event": "REVALIDATION_FAILED", "errors": revalidation["errors"]})
        return manifest
    contract = revalidation["contract"]
    baseline_sha = manifest["authorized_baseline_sha"]

    # Step 3 (F2): centralized scope/path-authority invariant, checked
    # before every phase's own action, every single advance() call --
    # not merely unit-tested against validate_scope() in isolation.
    scope_result = validate_scope(repo_root, contract, baseline_sha)
    if not scope_result["valid"]:
        manifest = transition(manifest, "HUMAN_REVIEW_REQUIRED", stop_reason=json.dumps(scope_result["errors"]))
        manifest = save_manifest(rdir, manifest)
        append_event(rdir, {"event": "SCOPE_VIOLATION", "errors": scope_result["errors"]})
        return manifest

    # Step 4: fresh fingerprint, every call.
    current_fingerprint = compute_diff_fingerprint(repo_root, baseline_sha)
    manifest["diff_fingerprint"] = current_fingerprint

    try:
        if phase == "INITIALIZING":
            manifest = transition(manifest, "BUILDING")

        elif phase == "BUILDING":
            manifest = _do_builder_phase(
                repo_root, rdir, manifest, contract, policy, adapters,
                counter_field="implementation_attempt_count",
                deterministic_failures="(none -- first attempt)",
                reviewer_findings_text="(none -- this is not a correction pass)",
                on_success_phase="TESTING",
            )

        elif phase == "REPAIRING":
            manifest["repair_attempt_count"] += 1
            if manifest["repair_attempt_count"] > int(policy.get("implementation_repair_limit", 0)):
                manifest = transition(manifest, "HUMAN_REVIEW_REQUIRED", stop_reason="implementation_repair_limit exhausted")
            else:
                failures_text = _load_last_test_failure_text(rdir, manifest)
                manifest = _do_builder_phase(
                    repo_root, rdir, manifest, contract, policy, adapters,
                    counter_field=None,
                    deterministic_failures=failures_text,
                    reviewer_findings_text="(none -- this is a test-repair pass)",
                    on_success_phase="TESTING",
                )

        elif phase == "CORRECTING_REVIEW":
            findings_text = _load_last_reviewer_findings_text(rdir, manifest)
            manifest = _do_builder_phase(
                repo_root, rdir, manifest, contract, policy, adapters,
                counter_field=None,
                deterministic_failures="(none -- addressing reviewer findings)",
                reviewer_findings_text=findings_text,
                on_success_phase="TESTING",
            )

        elif phase == "TESTING":
            result = adapters.test_runner(repo_root, contract["required_tests"], rdir=rdir)
            append_event(rdir, {"event": "TESTS_RUN", "ok": result["ok"], "artifact": result["artifact_path"]})
            manifest["last_test_artifact"] = result["artifact_path"]
            if result["ok"]:
                manifest["last_valid_test_artifact"] = result["artifact_path"]
                manifest["last_valid_test_diff_fingerprint"] = current_fingerprint
                manifest = transition(manifest, "REVIEWING")
            else:
                manifest = transition(manifest, "REPAIRING")

        elif phase == "REVIEWING":
            if current_fingerprint != manifest.get("last_valid_test_diff_fingerprint"):
                # F5: the diff drifted since the last test PASS -- never
                # review a diff that was never actually tested. Route
                # back to TESTING; no reviewer invocation, no counters
                # bumped for this no-op entry.
                append_event(rdir, {"event": "REVIEW_SKIPPED_STALE_TEST_EVIDENCE", "current_fingerprint": current_fingerprint})
                manifest = transition(manifest, "TESTING")
            elif manifest.get("last_reviewer_diff_fingerprint") == current_fingerprint and manifest.get("last_reviewer_artifact"):
                # Idempotent re-entry: this exact already-tested diff was
                # already reviewed SAFE (or CHANGES_REQUIRED-with-no-
                # required-findings); do not re-invoke the reviewer.
                manifest["review_attempt_count"] += 1
                manifest = transition(manifest, "ASSURING")
            else:
                manifest["review_attempt_count"] += 1
                manifest = _do_reviewer_phase(repo_root, rdir, manifest, contract, policy, adapters, current_fingerprint)

        elif phase == "ASSURING":
            if (
                current_fingerprint != manifest.get("last_valid_test_diff_fingerprint")
                or current_fingerprint != manifest.get("last_reviewer_diff_fingerprint")
            ):
                # F1: the diff drifted since the evidence this ASSURING
                # entry would otherwise certify -- never run assurance
                # against untested/unreviewed content. Route back to the
                # earliest necessary validation stage (TESTING; a fresh
                # review is naturally required again downstream since
                # last_reviewer_diff_fingerprint will no longer match).
                append_event(
                    rdir,
                    {
                        "event": "ASSURANCE_SKIPPED_STALE_EVIDENCE",
                        "current_fingerprint": current_fingerprint,
                        "last_valid_test_diff_fingerprint": manifest.get("last_valid_test_diff_fingerprint"),
                        "last_reviewer_diff_fingerprint": manifest.get("last_reviewer_diff_fingerprint"),
                    },
                )
                manifest = transition(manifest, "TESTING")
            else:
                result = adapters.assurance_runner(repo_root, rdir=rdir)
                manifest["assurance_artifact"] = result["artifact_path"]
                append_event(rdir, {"event": "ASSURANCE_RUN", "ok": result["ok"], "artifact": result["artifact_path"]})
                if not result["ok"]:
                    manifest = transition(manifest, "HUMAN_REVIEW_REQUIRED", stop_reason="full assurance baseline failed")
                else:
                    # F1: re-verify nothing mutated DURING assurance
                    # (which can take real wall-clock time) before
                    # entering the terminal READY state.
                    post_fingerprint = compute_diff_fingerprint(repo_root, baseline_sha)
                    if post_fingerprint != current_fingerprint:
                        append_event(
                            rdir,
                            {
                                "event": "POST_ASSURANCE_MUTATION_DETECTED",
                                "pre_fingerprint": current_fingerprint,
                                "post_fingerprint": post_fingerprint,
                            },
                        )
                        manifest = transition(manifest, "TESTING")
                    else:
                        manifest["human_approval_state"] = "PENDING"
                        manifest = transition(manifest, "READY_FOR_HUMAN_APPROVAL")

        else:
            raise MilestoneStateError(f"unknown phase {phase!r}")

    except InvalidTransitionError:
        raise
    except InfrastructureError as exc:
        manifest = _apply_infra_retry(manifest, policy, phase, exc)
        append_event(rdir, {"event": "INFRASTRUCTURE_ERROR", "detail": str(exc), "phase": phase})

    manifest = save_manifest(rdir, manifest)
    return manifest


def _pending_recovered_session_id(rdir: Path) -> str | None:
    """CAREER_OS_BUILDER_SESSION_RECOVERY_AND_STRUCTURED_COMPLETION_V1.

    Deliberately NOT a manifest field (schemas/milestone_run.schema.json
    is `additionalProperties: false` and out of scope for this bounded
    milestone). Derived instead from this run's own local, gitignored,
    append-only events.jsonl -- read fully, in order, every call:
    a BUILDER_SESSION_RECOVERED event sets the pending session_id (its
    own session_id field, defensively re-validated as a non-empty
    stripped string -- SR-WS-1); any subsequent BUILDER_INVOKED event
    (the adapter genuinely returned, successfully or not) clears it,
    since that attempt already consumed the recovery. The LATEST state
    after a full scan governs, so a stale recovery event followed by a
    real invocation never resurrects as pending, and of several recovery
    events only the latest still-pending one is authoritative.

    SR-CRASH-1 (Cursor correction pass): this is also the sole source of
    truth used to RECONSTRUCT a lost session_id after a process crash
    between the durable event write and the durable manifest save --
    events.jsonl is written (fsync'd via a normal file append) before
    _do_builder_phase ever raises back out to advance()'s manifest save,
    so a crash in that narrow window leaves the event durably recorded
    even if the manifest itself never got the chance to persist it. On
    the next advance() (a fresh process, per the resume() contract), this
    function is consulted again and the caller self-heals the manifest
    field from it -- the recovery invariant depends only on this durable
    log, never on any single in-memory write having completed."""
    events_path = rdir / "events.jsonl"
    if not events_path.exists():
        return None
    pending: str | None = None
    with events_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except ValueError:
                continue
            name = evt.get("event")
            if name == "BUILDER_SESSION_RECOVERED":
                sid = evt.get("session_id")
                pending = sid.strip() if isinstance(sid, str) and sid.strip() else None
            elif name == "BUILDER_INVOKED":
                pending = None
    return pending


def _do_builder_phase(
    repo_root: Path,
    rdir: Path,
    manifest: dict[str, Any],
    contract: Mapping[str, Any],
    policy: Mapping[str, Any],
    adapters: Adapters,
    *,
    counter_field: str | None,
    deterministic_failures: str,
    reviewer_findings_text: str,
    on_success_phase: str,
) -> dict[str, Any]:
    recovered_session_id = _pending_recovered_session_id(rdir)
    if recovered_session_id and manifest.get("builder_session_id") != recovered_session_id:
        # SR-CRASH-1 self-heal: the durable event log carries a pending
        # recovered session that the manifest itself never recorded
        # (e.g. a crash between the event write and the manifest save on
        # a prior process). Restore it now so the invariant holds
        # regardless of exactly where a prior process was interrupted --
        # this mutation is picked up by advance()'s own save_manifest()
        # call at the end of this same advance() invocation.
        manifest["builder_session_id"] = recovered_session_id
        append_event(rdir, {"event": "BUILDER_SESSION_RECONSTRUCTED", "session_id": recovered_session_id})

    effective_session_id = manifest.get("builder_session_id")
    if recovered_session_id:
        # A bounded resumed retry aimed only at finishing already-started
        # work and emitting the required structured result -- never the
        # full original task prompt, which would blindly rerun work that
        # (per the recovered session's own last turn) already happened.
        prompt = build_resumed_completion_prompt(contract)
    else:
        prompt = build_builder_prompt(
            contract, deterministic_failures=deterministic_failures, reviewer_findings_text=reviewer_findings_text
        )
    try:
        raw = adapters.builder_invoker(
            prompt=prompt, cwd=repo_root, policy=policy, session_id=effective_session_id
        )
    except RecoverableSessionInfrastructureError as exc:
        manifest["builder_session_id"] = exc.session_id
        append_event(rdir, {"event": "BUILDER_SESSION_RECOVERED", "session_id": exc.session_id, "detail": str(exc)})
        raise

    validity = validate_builder_result(raw)
    artifact_path = rdir / "builder" / f"{uuid.uuid4().hex[:8]}.json"
    atomic_write_json(artifact_path, raw if isinstance(raw, Mapping) else {"raw": raw})
    append_event(rdir, {"event": "BUILDER_INVOKED", "valid": validity["valid"], "artifact": str(artifact_path)})
    if not validity["valid"]:
        raise InfrastructureError(f"builder returned malformed result: {validity['errors']}")

    if counter_field:
        manifest[counter_field] += 1
    if raw.get("session_id"):
        manifest["builder_session_id"] = raw["session_id"]

    if raw.get("status") == "STOPPED":
        target = "ARCHITECTURE_DECISION_REQUIRED" if raw.get("architecture_decision_required") else "HUMAN_REVIEW_REQUIRED"
        return transition(manifest, target, stop_reason=f"builder stopped: {raw.get('stop_condition_encountered')}")

    return transition(manifest, on_success_phase)


def _do_reviewer_phase(
    repo_root: Path,
    rdir: Path,
    manifest: dict[str, Any],
    contract: Mapping[str, Any],
    policy: Mapping[str, Any],
    adapters: Adapters,
    current_fingerprint: str,
) -> dict[str, Any]:
    diff_ok, diff_text = _run_git(["diff", manifest["authorized_baseline_sha"], "--", "."], cwd=repo_root, timeout=60)
    test_artifact = _load_json_file(Path(manifest["last_valid_test_artifact"])) if manifest.get("last_valid_test_artifact") else None
    test_evidence = json.dumps(test_artifact, indent=2) if test_artifact else "(no test artifact available)"
    governance_excerpt = (
        "This repository's Career OS truth architecture separates Qualification Truth, "
        "Employer Truth, Candidate Truth, and Match Truth from pursuit/presentation doctrine "
        "(BLUEPRINT.md, not modifiable by this milestone). Constitutional files (BLUEPRINT.md, "
        "AGENTS.md, existing Truth-layer schemas/runtime, Golden Test expectations) must never "
        "be silently weakened. Flag any diff touching a path outside the contract's allowed_paths, "
        "any weakened/deleted test, or any silently altered Golden Test expectation."
    )
    prompt = build_reviewer_prompt(
        contract, diff=diff_text if diff_ok else "(diff unavailable)", test_evidence=test_evidence, governance_excerpt=governance_excerpt
    )
    baseline_sha = manifest["authorized_baseline_sha"]
    raw = adapters.reviewer_invoker(prompt=prompt, cwd=repo_root, policy=policy)

    # F3 correction: the reviewer boundary must not rely solely on
    # --mode ask (documented, and empirically verified structurally
    # enforced -- see the ADR -- but never treated as the SOLE
    # enforcement mechanism). Recompute the actual repository fingerprint
    # and scope AFTER the reviewer invocation returns, compare against
    # the fingerprint immediately BEFORE invoking it, and reject the
    # review outright -- never even inspecting its outcome -- if
    # anything changed.
    post_fingerprint = compute_diff_fingerprint(repo_root, baseline_sha)
    post_scope = validate_scope(repo_root, contract, baseline_sha)
    if post_fingerprint != current_fingerprint or not post_scope["valid"]:
        append_event(
            rdir,
            {
                "event": "REVIEWER_MUTATION_DETECTED",
                "pre_fingerprint": current_fingerprint,
                "post_fingerprint": post_fingerprint,
                "scope_errors": post_scope.get("errors", []),
            },
        )
        return transition(
            manifest,
            "HUMAN_REVIEW_REQUIRED",
            stop_reason="reviewer invocation mutated the governed worktree -- rejected for governance purposes, never accepted regardless of its own reported outcome",
        )

    validity = validate_reviewer_result(raw)
    artifact_path = rdir / "reviews" / f"{uuid.uuid4().hex[:8]}.json"
    atomic_write_json(artifact_path, raw if isinstance(raw, Mapping) else {"raw": raw})
    append_event(rdir, {"event": "REVIEWER_INVOKED", "valid": validity["valid"], "artifact": str(artifact_path)})
    if not validity["valid"]:
        raise InfrastructureError(f"reviewer returned malformed result: {validity['errors']}")

    # last_reviewer_artifact always points at the MOST RECENT reviewer
    # result regardless of outcome (so a correction pass can read back
    # the required findings); last_reviewer_diff_fingerprint is set only
    # when the diff is actually considered resolved (SAFE, or
    # CHANGES_REQUIRED with no REQUIRED findings) -- an unresolved
    # CHANGES_REQUIRED diff must never satisfy the idempotent-reentry
    # SAFE-cache check above.
    manifest["last_reviewer_artifact"] = str(artifact_path)

    outcome = raw["outcome"]
    if outcome == "SAFE":
        manifest["last_reviewer_diff_fingerprint"] = current_fingerprint
        return transition(manifest, "ASSURING")

    if outcome == "ESCALATE":
        # The controller must never itself adjudicate a disputed/ambiguous
        # finding -- surface it to Bora.
        return transition(manifest, "HUMAN_REVIEW_REQUIRED", stop_reason=f"reviewer escalated: {raw.get('findings')}")

    # CHANGES_REQUIRED
    reqs = required_findings(raw)
    if not reqs:
        # No REQUIRED findings -- treat as effectively safe-with-notes.
        manifest["last_reviewer_diff_fingerprint"] = current_fingerprint
        return transition(manifest, "ASSURING")

    manifest["review_correction_count"] += 1
    if manifest["review_correction_count"] > int(policy.get("review_correction_limit", 0)):
        return transition(manifest, "HUMAN_REVIEW_REQUIRED", stop_reason="review_correction_limit exhausted")
    return transition(manifest, "CORRECTING_REVIEW")


def _load_last_test_failure_text(rdir: Path, manifest: Mapping[str, Any]) -> str:
    path = manifest.get("last_test_artifact")
    if not path:
        return "(no test artifact available)"
    data = _load_json_file(Path(path))
    return json.dumps(data, indent=2) if data else "(unreadable test artifact)"


def _load_last_reviewer_findings_text(rdir: Path, manifest: Mapping[str, Any]) -> str:
    path = manifest.get("last_reviewer_artifact")
    if not path:
        return "(no reviewer findings artifact available)"
    data = _load_json_file(Path(path))
    if not data:
        return "(unreadable reviewer artifact)"
    return json.dumps(required_findings(data), indent=2)


# ----------------------------------------------------------------------
# Top-level run / resume
# ----------------------------------------------------------------------

def run(
    repo_root: Path,
    contract_path: Path,
    policy_path: Path,
    *,
    adapters: Adapters,
    max_steps: int = 200,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    facts = compute_repo_facts(repo_root)
    branch = facts.get("branch")
    if branch and branch != DEFAULT_BRANCH:
        existing = read_lock(repo_root, branch)
        if existing is not None:
            raise LockHeldError(existing)

    init_result = init_run(repo_root, contract_path, policy_path)
    if not init_result["ok"]:
        return {"phase": init_result["escalation"], "errors": init_result["errors"], "run_id": None}

    run_id = init_result["run_id"]
    lock = acquire_lock(repo_root, branch, run_id=run_id, worktree_path=str(repo_root.resolve()))
    try:
        manifest = _drive(repo_root, run_id, adapters, max_steps=max_steps)
    finally:
        release_lock(repo_root, branch, owner_token=lock["owner_token"])
    return manifest


def resume(
    repo_root: Path,
    run_id: str,
    *,
    adapters: Adapters,
    max_steps: int = 200,
    recover_stale_lock: bool = False,
) -> dict[str, Any]:
    rdir = run_dir(repo_root, run_id)
    manifest = load_manifest(rdir)
    if manifest is None:
        raise MilestoneStateError(f"no manifest found for run_id {run_id!r}")
    validity = validate_manifest(manifest)
    if not validity["valid"]:
        raise MilestoneStateError(f"corrupted manifest, cannot resume: {validity['errors']}")
    if manifest["phase"] in TERMINAL_PHASES:
        return manifest

    branch = manifest["working_branch"]
    existing = read_lock(repo_root, branch)
    # F8 correction: a lock represents ONE ACTIVE CONTROLLER PROCESS's
    # ownership, never merely "this run_id". A prior implementation
    # trusted an existing lock whose run_id happened to match this
    # resume() call's run_id and silently reused it without any
    # ownership/liveness check -- but resume() is, by construction,
    # always a NEW process invocation reconstructing a run from disk; it
    # never already holds the lock from a live in-memory reference. Any
    # existing lock file at this point -- matching run_id or not -- was
    # created by some OTHER invocation (still genuinely running, or
    # orphaned by a crash) and must never be silently reused. Liveness
    # cannot be safely established cross-platform in V1, so an existing
    # lock always requires the explicit --recover-stale-lock takeover
    # (which itself remains atomic via acquire_lock's O_CREAT|O_EXCL --
    # only one of two simultaneous recovery attempts can win).
    if existing is not None:
        if not recover_stale_lock:
            raise LockHeldError(existing)
        lock = takeover_stale_lock(repo_root, branch, new_run_id=run_id, worktree_path=str(repo_root.resolve()))
    else:
        lock = acquire_lock(repo_root, branch, run_id=run_id, worktree_path=str(repo_root.resolve()))

    try:
        manifest = _drive(repo_root, run_id, adapters, max_steps=max_steps)
    finally:
        release_lock(repo_root, branch, owner_token=lock["owner_token"])
    return manifest


def _drive(repo_root: Path, run_id: str, adapters: Adapters, *, max_steps: int) -> dict[str, Any]:
    rdir = run_dir(repo_root, run_id)
    manifest = load_manifest(rdir)
    for _ in range(max_steps):
        manifest = advance(repo_root, run_id, adapters)
        if manifest["phase"] in TERMINAL_PHASES:
            return manifest
    return manifest
