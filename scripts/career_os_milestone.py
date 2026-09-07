"""CAREER_OS_BOUNDED_AGENT_BUILD_LOOP_V1 CLI entry point.

Usage:
    python scripts/career_os_milestone.py run <contract-path>
    python scripts/career_os_milestone.py resume <run-id> [--recover-stale-lock]

V1 has no installed console command (`career-os milestone ...`) --
these two script entrypoints are the smallest sufficient surface; a
packaged CLI is unnecessary complexity for a single-repository local
controller.

This script wires the REAL builder (Claude Code CLI) and reviewer
(Cursor Agent CLI) adapters from src/milestone_run.py. It never commits,
pushes, opens a pull request, or merges -- V1's only successful terminal
state is READY_FOR_HUMAN_APPROVAL.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from milestone_run import (  # noqa: E402
    Adapters,
    LockHeldError,
    real_claude_builder_invoker,
    real_cursor_reviewer_invoker,
    resume as resume_milestone,
    run as run_milestone,
)

DEFAULT_POLICY_PATH = ROOT / "config" / "milestone_execution_policy_v1.json"


def _real_adapters() -> Adapters:
    return Adapters(
        builder_invoker=real_claude_builder_invoker,
        reviewer_invoker=real_cursor_reviewer_invoker,
    )


def _print_review_package(manifest: dict) -> None:
    print(json.dumps(manifest, indent=2, sort_keys=True))


def cmd_run(args: argparse.Namespace) -> int:
    contract_path = Path(args.contract_path)
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    try:
        manifest = run_milestone(ROOT, contract_path, DEFAULT_POLICY_PATH, adapters=_real_adapters())
    except LockHeldError as exc:
        print(f"LOCK_HELD: {exc.existing}")
        return 2
    _print_review_package(manifest)
    return 0 if manifest.get("phase") == "READY_FOR_HUMAN_APPROVAL" else 1


def cmd_resume(args: argparse.Namespace) -> int:
    try:
        manifest = resume_milestone(
            ROOT, args.run_id, adapters=_real_adapters(), recover_stale_lock=args.recover_stale_lock
        )
    except LockHeldError as exc:
        print(f"LOCK_HELD: {exc.existing}")
        print("Pass --recover-stale-lock only if you have independently confirmed the prior owner is no longer active.")
        return 2
    _print_review_package(manifest)
    return 0 if manifest.get("phase") == "READY_FOR_HUMAN_APPROVAL" else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="career_os_milestone")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Start a new milestone run from a contract file.")
    run_parser.add_argument("contract_path")
    run_parser.set_defaults(func=cmd_run)

    resume_parser = sub.add_parser("resume", help="Resume an existing milestone run by run_id.")
    resume_parser.add_argument("run_id")
    resume_parser.add_argument(
        "--recover-stale-lock",
        action="store_true",
        default=False,
        help="Explicitly take over a lock left by a run that is no longer active. Never silently deletes the old lock.",
    )
    resume_parser.set_defaults(func=cmd_resume)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
