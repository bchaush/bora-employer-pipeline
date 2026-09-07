"""CAREER_OS_MILESTONE_CONTRACT_AND_STATE_VALIDATION_V1.

Deterministic local validator preventing a fresh agent session from
trusting stale repository continuity claims. Reproduced defect (see the
CANONICAL_STATE_RECOVERY_AND_MILESTONE_CONTRACT_V1 read-only audit):
`CURRENT_STATE.md` and `CURRENT_MILESTONE.md` are hand-maintained prose
that can silently drift arbitrarily far behind canonical `BLUEPRINT.md`
and canonical merged history, with no mechanical check anywhere in the
repository capable of detecting it.

ARCHITECTURE (locked by the preceding audit; do not redesign here):

Authority hierarchy (highest to lowest): (1) actual Git facts (HEAD,
branch, merge-base, dirty/clean, diff) -- always independently
re-derivable, never staleable; (2) GitHub facts (PR state, hosted CI
result) when online verification is explicitly invoked; (3) committed
semantic-state claims (`project_state.json`, a branch-scoped milestone
contract) -- checked against (1)/(2), never trusted at face value;
(4) prose history (`CURRENT_STATE.md`'s narrative body,
`CURRENT_MILESTONE.md`'s historical log, `CHANGELOG.md`) -- informational
only, never authoritative over (1)-(3). `BLUEPRINT.md`/`AGENTS.md`/
`.cursor/rules/*.mdc` remain governing doctrine (what must always be
true), not "current state," and are never superseded by this module.

`project_state.json` represents CANONICAL MERGED semantic state only. It
deliberately carries no current Git SHA (a self-referential canonical-SHA
claim inside a committed file is unstable -- the moment such a file
merges, it would be describing the very commit it is part of) and no
transient active-milestone/branch/builder field (active work belongs to
a branch-scoped milestone contract under `milestone_contracts/`, checked
against actual Git state, not to this canonical-main file). A clean
`main` checkout legitimately has no active milestone contract.

Branch-state detection is deliberately NARROW (V1): this module only ever
inspects the CURRENT working branch, never scans the repository for other
branches. It fails when the current branch has commits ahead of `main`
or an uncommitted working-tree change (i.e. milestone work is plausibly
in progress) but no governing `milestone_contracts/<branch>.json` exists,
or when that contract's own claims contradict actual Git state.
Repository-wide orphan-branch discovery is explicitly out of scope.

This module performs NO writes, invokes NO AI builder, and contains NO
autonomous retry/repair loop -- it is a pure, deterministic checker.
"""

from __future__ import annotations

import fnmatch
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from schema_validation import build_draft202012_validator

ROOT = Path(__file__).resolve().parents[1]
PROJECT_STATE_SCHEMA = ROOT / "schemas" / "project_state.schema.json"
MILESTONE_CONTRACT_SCHEMA = ROOT / "schemas" / "milestone_contract.schema.json"

DEFAULT_BRANCH = "main"

_BLUEPRINT_VERSION_PATTERN = re.compile(r"Final Locked Blueprint v(\d+\.\d+)")
_BLUEPRINT_SECTION_PATTERN = re.compile(r"^\*\*(\d+)\.\s", re.MULTILINE)

# Tier A/B "constitutional"/success-definition surfaces (per the audit's
# protection model). A changed path matching any of these requires an
# EXACT literal entry in the governing contract's allowed_paths -- a
# broad wildcard (e.g. "**/*.py") is never sufficient authorization for
# a protected path.
PROTECTED_EXACT_PATHS = frozenset(
    {
        "BLUEPRINT.md",
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "scripts/verify_assurance_baseline.py",
        ".github/workflows/assurance-baseline.yml",
        # "Protect the judge": this validator and its CLI entry point are
        # themselves the machinery that defines/enforces milestone-state
        # validation. An ordinary milestone must not be able to weaken
        # its own enforcement (e.g. silently loosen a protected-path
        # rule) merely by including these files under a broad wildcard
        # in allowed_paths -- exact literal contract authorization is
        # required, identical to every other protected surface.
        "src/career_os_state.py",
        "scripts/verify_milestone_state.py",
    }
)
# schemas/project_state.schema.json and schemas/milestone_contract.schema.json
# -- the judge's own schema contracts -- are already covered by the
# "schemas/" prefix below; no separate exact entry is needed for them.
PROTECTED_PATH_PREFIXES = (
    "docs/decisions/",
    "schemas/",
    "golden-tests/",
)
# Truth-layer / qualification-success-definition src surfaces.
PROTECTED_SRC_FILES = frozenset(
    {
        "src/job_analysis.py",
        "src/job_decision.py",
        "src/requirement_source_role.py",
        "src/application_logic.py",
        "src/qualification_gate.py",
        "src/experience_range.py",
        "src/domain_qualified_duration.py",
        "src/requirement_match.py",
        "src/requirement_normalize.py",
        "src/application_gate.py",
    }
)


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _posix(path: str) -> str:
    return path.replace("\\", "/")


def is_protected_path(path: str) -> bool:
    """True for a Tier A/B constitutional/success-definition surface."""
    posix_path = _posix(path)
    if posix_path in PROTECTED_EXACT_PATHS or posix_path in PROTECTED_SRC_FILES:
        return True
    return any(posix_path.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES)


def is_existing_test_surface(path: str) -> bool:
    """True for a path under tests/ or golden-tests/ whose MODIFICATION
    (not addition) requires explicit contract authorization -- adding a
    brand-new test file remains ordinary, always-allowed Tier D work."""
    posix_path = _posix(path)
    return (posix_path.startswith("tests/") and posix_path.endswith("_test.py")) or posix_path.startswith(
        "golden-tests/"
    )


def _matches_any_glob(path: str, patterns: list[str]) -> bool:
    posix_path = _posix(path)
    return any(fnmatch.fnmatch(posix_path, _posix(pattern)) for pattern in patterns)


def _run_git(args: list[str], *, cwd: Path) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001 -- any spawn/timeout failure is a query failure
        return False, f"failed to execute git {args!r}: {exc!r}"
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout or "").strip()
    # rstrip only the trailing newline -- NOT a full .strip(): git status
    # --porcelain's status-code column starts with a leading space for
    # some statuses (e.g. " M path"), and a leading-whitespace-eating
    # .strip() here would silently corrupt the first line's path when
    # callers slice by fixed column offset.
    return True, completed.stdout.rstrip("\n").rstrip("\r")


def get_current_branch(*, cwd: Path) -> str | None:
    ok, out = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return out if ok and out else None


def get_merge_base(*, cwd: Path, base: str = DEFAULT_BRANCH) -> str | None:
    ok, out = _run_git(["merge-base", "HEAD", base], cwd=cwd)
    return out if ok and out else None


def is_working_tree_dirty(*, cwd: Path) -> bool:
    ok, out = _run_git(["status", "--porcelain", "--untracked-files=all"], cwd=cwd)
    return bool(ok and out.strip())


def get_commits_ahead(*, cwd: Path, base: str = DEFAULT_BRANCH) -> int | None:
    ok, out = _run_git(["rev-list", "--count", f"{base}..HEAD"], cwd=cwd)
    if not ok or not out.isdigit():
        return None
    return int(out)


def get_changed_files(baseline_sha: str, *, cwd: Path) -> list[str] | None:
    """Repo-relative paths changed between baseline_sha and the current
    working tree, committed and uncommitted (including untracked new
    files) combined."""
    ok, out = _run_git(["diff", "--name-only", baseline_sha, "HEAD"], cwd=cwd)
    if not ok:
        return None
    committed = {line.strip() for line in out.splitlines() if line.strip()}

    ok2, out2 = _run_git(["status", "--porcelain", "--untracked-files=all"], cwd=cwd)
    if not ok2:
        return None
    uncommitted: set[str] = set()
    for line in out2.splitlines():
        if not line:
            continue
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ")[-1]
        uncommitted.add(path_part.strip())

    return sorted(committed | uncommitted)


def get_added_files(baseline_sha: str, *, cwd: Path) -> set[str]:
    """Paths newly added relative to baseline_sha -- committed additions
    plus untracked/staged-new working-tree files."""
    ok, out = _run_git(["diff", "--name-only", "--diff-filter=A", baseline_sha, "HEAD"], cwd=cwd)
    added: set[str] = {line.strip() for line in out.splitlines() if line.strip()} if ok else set()

    ok2, out2 = _run_git(["status", "--porcelain", "--untracked-files=all"], cwd=cwd)
    if ok2:
        for line in out2.splitlines():
            if not line:
                continue
            if line.startswith("??") or line.startswith("A "):
                added.add(line[3:].strip())
    return added


def _load_json_file(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 -- any read/parse failure is treated as malformed
        return None


def validate_project_state(*, root: Path) -> dict[str, Any]:
    """Validate project_state.json's own schema, then cross-check its
    claims against actual BLUEPRINT.md content. Fails closed on any
    malformed/missing input."""
    project_state_path = root / "project_state.json"
    blueprint_path = root / "BLUEPRINT.md"

    if not project_state_path.exists():
        return {"valid": False, "errors": [_error("STATE_FILE_MISSING", path="project_state.json")], "state": None}

    state = _load_json_file(project_state_path)
    if not isinstance(state, dict):
        return {
            "valid": False,
            "errors": [_error("STATE_FILE_MALFORMED", detail="project_state.json must be a valid JSON object")],
            "state": None,
        }

    validator = build_draft202012_validator(PROJECT_STATE_SCHEMA)
    if not validator.is_valid(state):
        return {
            "valid": False,
            "errors": [_error("STATE_FILE_MALFORMED", detail=msg) for msg in (e.message for e in validator.iter_errors(state))],
            "state": state,
        }

    errors: list[dict[str, Any]] = []

    if not blueprint_path.exists():
        errors.append(_error("STATE_BLUEPRINT_MISSING"))
        return {"valid": False, "errors": errors, "state": state}

    blueprint_text = blueprint_path.read_text(encoding="utf-8")

    version_match = _BLUEPRINT_VERSION_PATTERN.search(blueprint_text)
    if version_match is None:
        errors.append(_error("STATE_BLUEPRINT_VERSION_UNPARSEABLE"))
    elif version_match.group(1) != state["blueprint_version"]:
        errors.append(
            _error(
                "STATE_BLUEPRINT_VERSION_MISMATCH",
                declared=state["blueprint_version"],
                actual=version_match.group(1),
            )
        )

    section_numbers = [int(m) for m in _BLUEPRINT_SECTION_PATTERN.findall(blueprint_text)]
    if not section_numbers:
        errors.append(_error("STATE_BLUEPRINT_SECTIONS_UNPARSEABLE"))
    else:
        actual_latest = max(section_numbers)
        if actual_latest != state["latest_locked_section"]:
            errors.append(
                _error(
                    "STATE_LATEST_SECTION_MISMATCH",
                    declared=state["latest_locked_section"],
                    actual=actual_latest,
                )
            )

    return {"valid": len(errors) == 0, "errors": errors, "state": state}


def milestone_contract_path_for_branch(branch: str, *, root: Path) -> Path:
    """The naive (unvalidated) contract path for a branch name. Callers
    that need a safe path MUST use resolve_milestone_contract_path
    instead -- this function exists only to describe the naming
    convention, never to be trusted directly against an untrusted branch
    name."""
    return root / "milestone_contracts" / f"{branch}.json"


def resolve_milestone_contract_path(branch: str, *, root: Path) -> Path | None:
    """Resolve the contract path for a branch, refusing to return a path
    that would escape milestone_contracts/ via path traversal (e.g. a
    branch name containing '..' segments, or an absolute-path-like
    segment). Returns None (fail closed) rather than silently
    normalizing an ambiguous/malicious branch name into some other,
    unintended, valid-looking contract path."""
    contracts_dir = (root / "milestone_contracts").resolve()
    candidate = milestone_contract_path_for_branch(branch, root=root).resolve()
    try:
        candidate.relative_to(contracts_dir)
    except ValueError:
        return None
    return candidate


def validate_contract_schema(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        return {
            "valid": False,
            "errors": [_error("MILESTONE_CONTRACT_MALFORMED", detail="contract must be a JSON object")],
        }
    validator = build_draft202012_validator(MILESTONE_CONTRACT_SCHEMA)
    if not validator.is_valid(contract):
        return {
            "valid": False,
            "errors": [
                _error("MILESTONE_CONTRACT_MALFORMED", detail=msg) for msg in (e.message for e in validator.iter_errors(contract))
            ],
        }
    return {"valid": True, "errors": []}


def validate_changed_paths(contract: Mapping[str, Any], baseline_sha: str, *, cwd: Path) -> dict[str, Any]:
    """Enforce allowed_paths/forbidden_paths plus the two stronger
    protected-surface rules (constitutional files; modification, not
    addition, of an existing test/golden-test file) against every path
    changed since baseline_sha."""
    changed = get_changed_files(baseline_sha, cwd=cwd)
    if changed is None:
        return {"valid": False, "errors": [_error("STATE_GIT_QUERY_FAILED", detail="could not compute changed files")]}

    added = get_added_files(baseline_sha, cwd=cwd)
    allowed_paths: list[str] = list(contract.get("allowed_paths", []))
    forbidden_paths: list[str] = list(contract.get("forbidden_paths", []))
    allowed_exact = {_posix(p) for p in allowed_paths}

    errors: list[dict[str, Any]] = []
    for path in changed:
        if _matches_any_glob(path, forbidden_paths):
            errors.append(_error("STATE_PATH_FORBIDDEN", path=path))
            continue
        if not _matches_any_glob(path, allowed_paths):
            errors.append(_error("STATE_PATH_NOT_ALLOWED", path=path))
            continue
        if is_protected_path(path) and _posix(path) not in allowed_exact:
            errors.append(_error("STATE_PROTECTED_PATH_UNAUTHORIZED", path=path))
            continue
        if is_existing_test_surface(path) and path not in added and _posix(path) not in allowed_exact:
            errors.append(_error("STATE_EXISTING_TEST_MODIFIED_UNAUTHORIZED", path=path))

    return {"valid": len(errors) == 0, "errors": errors}


def run_local_state_checks(*, root: Path = ROOT) -> dict[str, Any]:
    """The full local, deterministic, offline check set. Never invokes
    GitHub, never invokes an AI builder, never mutates anything.

    Returns {"valid": bool, "errors": [...]}.
    """
    errors: list[dict[str, Any]] = []

    state_result = validate_project_state(root=root)
    errors.extend(state_result["errors"])

    branch = get_current_branch(cwd=root)
    if branch is None:
        errors.append(_error("STATE_GIT_QUERY_FAILED", detail="could not determine current branch"))
        return {"valid": len(errors) == 0, "errors": errors}

    if branch == DEFAULT_BRANCH:
        # A clean main checkout legitimately has no active milestone
        # contract -- nothing further to check.
        return {"valid": len(errors) == 0, "errors": errors}

    dirty = is_working_tree_dirty(cwd=root)
    ahead = get_commits_ahead(cwd=root)
    milestone_work_in_progress = dirty or (ahead is not None and ahead > 0)
    if not milestone_work_in_progress:
        # Branch exists but has no work on it yet relative to main --
        # nothing to authorize.
        return {"valid": len(errors) == 0, "errors": errors}

    contract_path = resolve_milestone_contract_path(branch, root=root)
    if contract_path is None:
        errors.append(
            _error(
                "STATE_MILESTONE_CONTRACT_PATH_INVALID",
                branch=branch,
                detail="branch name resolves to a contract path outside milestone_contracts/ -- refusing to normalize a traversal-shaped branch name",
            )
        )
        return {"valid": len(errors) == 0, "errors": errors}

    if not contract_path.exists():
        errors.append(
            _error(
                "STATE_MILESTONE_CONTRACT_MISSING",
                branch=branch,
                detail=(
                    "current branch has commits ahead of main or an uncommitted "
                    f"working-tree change but no governing milestone_contracts/{branch}.json exists"
                ),
            )
        )
        return {"valid": len(errors) == 0, "errors": errors}

    contract = _load_json_file(contract_path)
    if contract is None:
        errors.append(
            _error(
                "MILESTONE_CONTRACT_MALFORMED",
                detail="milestone contract file could not be parsed as JSON",
            )
        )
        return {"valid": len(errors) == 0, "errors": errors}

    schema_result = validate_contract_schema(contract)
    if not schema_result["valid"]:
        errors.extend(schema_result["errors"])
        return {"valid": len(errors) == 0, "errors": errors}

    merge_base = get_merge_base(cwd=root)
    if merge_base is None:
        errors.append(_error("STATE_GIT_QUERY_FAILED", detail="could not compute merge-base with main"))
        return {"valid": len(errors) == 0, "errors": errors}

    if contract["baseline_sha"] != merge_base:
        errors.append(
            _error(
                "STATE_MILESTONE_CONTRACT_BASELINE_MISMATCH",
                declared_baseline_sha=contract["baseline_sha"],
                actual_merge_base=merge_base,
            )
        )
        # Baseline is wrong -- do not additionally evaluate paths against
        # a baseline_sha that is not actually the branch's authorized
        # merge-base; report the baseline defect alone.
        return {"valid": False, "errors": errors}

    path_result = validate_changed_paths(contract, contract["baseline_sha"], cwd=root)
    errors.extend(path_result["errors"])

    return {"valid": len(errors) == 0, "errors": errors}


def _run_gh(args: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["gh", *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"failed to execute gh {args!r}: {exc!r}"
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout or "").strip()
    return True, completed.stdout.strip()


def verify_github_milestone_state(state: Mapping[str, Any]) -> dict[str, Any]:
    """OPTIONAL, network-dependent verification -- never invoked by
    run_local_state_checks(), the default CLI mode, or
    scripts/verify_assurance_baseline.py. Must be explicitly requested
    (e.g. the CLI's --online flag) so ordinary local/CI runs stay fully
    deterministic and offline, and so GitHub Actions never recursively
    depends on calling back out to GitHub from inside its own run.

    Confirms latest_closed_milestone_pr is actually MERGED on GitHub.
    """
    pr_number = state.get("latest_closed_milestone_pr")
    if pr_number is None:
        return {"valid": True, "errors": []}

    ok, out = _run_gh(["pr", "view", str(pr_number), "--json", "state"])
    if not ok:
        return {"valid": False, "errors": [_error("STATE_GITHUB_QUERY_FAILED", detail=out)]}

    payload = _load_json_from_str(out)
    if not isinstance(payload, dict):
        return {"valid": False, "errors": [_error("STATE_GITHUB_QUERY_FAILED", detail="malformed gh output")]}

    if payload.get("state") != "MERGED":
        return {
            "valid": False,
            "errors": [
                _error(
                    "STATE_GITHUB_PR_NOT_MERGED",
                    pr=pr_number,
                    actual_state=payload.get("state"),
                )
            ],
        }
    return {"valid": True, "errors": []}


def _load_json_from_str(text: str) -> Any | None:
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return None
