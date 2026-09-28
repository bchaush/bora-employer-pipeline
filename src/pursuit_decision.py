"""CAREER_OS_PURSUIT_DECISION_PERSISTENCE_V1: Bora PURSUE/WATCH/REJECT decisions.

Pure functions only: this module performs no Gmail, Sheets, Drive, browser,
network, or submission I/O. Callers read current JOBS/LOG rows, pass them in,
apply the returned mutation plan through the provider adapter, and never
edit LOG history.

Truth boundaries:
- Pursuit Truth (this module) is distinct from Match Truth and Application
  Truth. A human decision never rewrites system Decision/lane, creates an
  APPLICATIONS row, or touches application history.
- A system recommendation is never Bora authorization; a decision can only be
  supplied by an explicit caller request with a valid PURSUE/WATCH/REJECT.
- PURSUE never authorizes submission. Manual SUBMIT stays Bora-controlled.

Authority surface: `derive_current_pursuit_state()` is the ONLY authorizing
surface. `JOBS.Bora_Decision` is a display projection of the latest persisted
decision and may go stale; it is never read by any authorization logic here.

Persistence fails closed (raises PursuitDecisionError, producing no plan and
therefore zero JOBS/LOG mutation) on unknown or noncanonical Job_ID, invalid
decision, reviewed-context mismatch, or a wrong/missing supersedes_event_id.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from schema_validation import build_draft202012_validator  # noqa: E402

ENGINE_BASELINE = "CAREER_OS_PURSUIT_DECISION_PERSISTENCE_V1"
LOG_STAGE = "PURSUIT_DECISION"
LOG_SOURCE = "BORA"
LOG_STATUS = "NORMALIZED"
DECIDED_BY = "BORA"
EVENT_ID_PREFIX = "PDE_V1::"
VALID_DECISIONS = ("PURSUE", "WATCH", "REJECT")

STATE_NO_DECISION = "NO_DECISION"
STATE_STALE = "STALE_RECONFIRMATION_REQUIRED"

# Explicit JOBS truth bound into the context fingerprint. Bora_Decision is
# deliberately excluded (a decision must not invalidate itself). Missing
# fields are explicit nulls, never guessed.
CONTEXT_FIELDS = (
    "Job_ID",
    "Official_URL",
    "Last_Verified",
    "Pipeline_State",
    "Freshness_State",
    "Geography_State",
    "OPT_Screen_State",
    "Candidate_Condition_State",
    "Threshold_State",
    "Role_Status",
    "Match_State",
    "Decision",
)

ROOT = Path(__file__).resolve().parents[1]
PURSUIT_DECISION_SCHEMA_PATH = ROOT / "schemas" / "pursuit_decision.schema.json"
PURSUIT_DECISION_MUTATION_SCHEMA_PATH = (
    ROOT / "schemas" / "pursuit_decision_mutation.schema.json"
)


class PursuitDecisionError(ValueError):
    """Fail-closed rejection. `error_code` is a stable machine-readable code."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(f"{error_code}: {message}")
        self.error_code = error_code


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_context_fingerprint(jobs_row: Mapping[str, Any]) -> str:
    """Deterministic fingerprint of the explicit JOBS context Bora reviews."""
    job_id = jobs_row.get("Job_ID")
    if not isinstance(job_id, str) or not job_id:
        raise PursuitDecisionError("MISSING_JOB_ID", "JOBS row has no Job_ID")
    return _sha256_hex(_canonical_json({f: jobs_row.get(f) for f in CONTEXT_FIELDS}))


def compute_event_id(
    *,
    job_id: str,
    decision: str,
    decision_context_fingerprint: str,
    supersedes_event_id: str | None,
    decision_run_id: str,
) -> str:
    """'PDE_V1::' + SHA-256 over exactly the five identity fields.

    decided_at and reason_note are deliberately excluded.
    """
    material = {
        "Job_ID": job_id,
        "decision": decision,
        "decision_context_fingerprint": decision_context_fingerprint,
        "supersedes_event_id": supersedes_event_id,
        "decision_run_id": decision_run_id,
    }
    return EVENT_ID_PREFIX + _sha256_hex(_canonical_json(material))


def _require_aware_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise PursuitDecisionError("INVALID_TIMESTAMP", f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PursuitDecisionError("INVALID_TIMESTAMP", f"{field} is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PursuitDecisionError("INVALID_TIMESTAMP", f"{field} must be timezone-aware")


def _identity_view(event: Mapping[str, Any]) -> dict[str, Any]:
    """Everything that must match for two events to be the same event.

    decided_at is wall-clock and excluded from identity and conflict checks.
    """
    return {k: v for k, v in event.items() if k != "decided_at"}


def _parse_decision_log_rows(
    log_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return validated decision events keyed by event_id.

    Consumes ONLY rows with the exact Stage and Engine_Baseline. Every other
    LOG row is ignored. A malformed/tampered row in our namespace fails
    closed: silently skipping it could hide a later REJECT/WATCH and let an
    older PURSUE look current.
    """
    validator = build_draft202012_validator(PURSUIT_DECISION_SCHEMA_PATH)
    events: dict[str, dict[str, Any]] = {}
    for row in log_rows:
        if row.get("Stage") != LOG_STAGE or row.get("Engine_Baseline") != ENGINE_BASELINE:
            continue
        try:
            event = json.loads(row.get("Notes"))
        except (TypeError, json.JSONDecodeError) as exc:
            raise PursuitDecisionError("MALFORMED_DECISION_EVENT", "Notes is not JSON") from exc
        if not isinstance(event, dict):
            raise PursuitDecisionError("MALFORMED_DECISION_EVENT", "Notes is not an object")
        errors = list(validator.iter_errors(event))
        if errors:
            raise PursuitDecisionError("MALFORMED_DECISION_EVENT", errors[0].message)
        _require_aware_timestamp(event["decided_at"], "decided_at")
        if row.get("Job_ID") != event["Job_ID"]:
            raise PursuitDecisionError("MALFORMED_DECISION_EVENT", "row Job_ID != event Job_ID")
        if event["reviewed_context_fingerprint"] != event["decision_context_fingerprint"]:
            raise PursuitDecisionError(
                "MALFORMED_DECISION_EVENT", "reviewed and decision context fingerprints differ"
            )
        expected_id = compute_event_id(
            job_id=event["Job_ID"],
            decision=event["decision"],
            decision_context_fingerprint=event["decision_context_fingerprint"],
            supersedes_event_id=event["supersedes_event_id"],
            decision_run_id=event["decision_run_id"],
        )
        if event["event_id"] != expected_id:
            raise PursuitDecisionError(
                "EVENT_ID_MISMATCH", "event_id does not match its identity material"
            )
        existing = events.get(event["event_id"])
        if existing is not None:
            if _identity_view(existing) != _identity_view(event):
                raise PursuitDecisionError(
                    "EVENT_ID_CONFLICT", "same event_id with conflicting payload in LOG"
                )
            continue  # exact duplicate LOG row: same event
        events[event["event_id"]] = event
    return events


def _chain_for_job(events: Mapping[str, dict[str, Any]], job_id: str) -> list[dict[str, Any]]:
    """Order one Job_ID's events by explicit supersession links (root first).

    Fails closed on branching, orphans, cycles, or multiple roots: history is a
    single linear chain or it is not trusted.
    """
    mine = {eid: e for eid, e in events.items() if e["Job_ID"] == job_id}
    if not mine:
        return []
    roots = [e for e in mine.values() if e["supersedes_event_id"] is None]
    if len(roots) != 1:
        raise PursuitDecisionError("BROKEN_DECISION_CHAIN", "expected exactly one root event")
    children: dict[str, dict[str, Any]] = {}
    for e in mine.values():
        parent = e["supersedes_event_id"]
        if parent is None:
            continue
        if parent not in mine:
            raise PursuitDecisionError("BROKEN_DECISION_CHAIN", "supersedes an unknown event")
        if parent in children:
            raise PursuitDecisionError("BROKEN_DECISION_CHAIN", "history branches")
        children[parent] = e
    ordered = [roots[0]]
    while ordered[-1]["event_id"] in children:
        ordered.append(children[ordered[-1]["event_id"]])
        if len(ordered) > len(mine):
            raise PursuitDecisionError("BROKEN_DECISION_CHAIN", "cycle")
    if len(ordered) != len(mine):
        raise PursuitDecisionError("BROKEN_DECISION_CHAIN", "disconnected events")
    return ordered


def derive_current_pursuit_state(
    current_jobs_row: Mapping[str, Any],
    decision_log_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The sole authorizing pursuit surface. Pure and deterministic.

    Derived only from the current JOBS context plus the append-only
    PURSUIT_DECISION LOG history. JOBS.Bora_Decision is never consulted.
    `authorizes_pursuit` is True only for a non-stale latest PURSUE.
    """
    job_id = current_jobs_row.get("Job_ID")
    current_fingerprint = compute_context_fingerprint(current_jobs_row)
    chain = _chain_for_job(_parse_decision_log_rows(decision_log_rows), job_id)
    result: dict[str, Any] = {
        "job_id": job_id,
        "state": STATE_NO_DECISION,
        "latest_decision": None,
        "latest_event_id": None,
        "history_event_ids": [e["event_id"] for e in chain],
        "authorizes_pursuit": False,
    }
    if not chain:
        return result
    latest = chain[-1]
    result["latest_decision"] = latest["decision"]
    result["latest_event_id"] = latest["event_id"]
    if latest["decision_context_fingerprint"] != current_fingerprint:
        result["state"] = STATE_STALE
        return result
    result["state"] = latest["decision"]
    result["authorizes_pursuit"] = latest["decision"] == "PURSUE"
    return result


def build_decision_mutation_plan(
    request: Mapping[str, Any],
    jobs_rows: Sequence[Mapping[str, Any]],
    log_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the JOBS + LOG mutation plan for one Bora decision.

    request keys: job_id, decision, reviewed_context_fingerprint,
    decision_run_id, decided_at, supersedes_event_id (None when this is the
    first decision for the job), optional reason_note.

    Returns {"jobs_mutations": [...], "log_mutations": [...]}; both empty for
    an exact replay of an already-persisted event. Raises PursuitDecisionError
    (no mutation of any kind) on every fail-closed condition.
    """
    job_id = request.get("job_id")
    decision = request.get("decision")
    reviewed = request.get("reviewed_context_fingerprint")
    run_id = request.get("decision_run_id")
    decided_at = request.get("decided_at")
    supersedes = request.get("supersedes_event_id")
    reason_note = request.get("reason_note")

    if decision not in VALID_DECISIONS:
        raise PursuitDecisionError("INVALID_DECISION", "decision must be PURSUE, WATCH, or REJECT")
    if not isinstance(run_id, str) or not run_id:
        raise PursuitDecisionError("MISSING_DECISION_RUN_ID", "decision_run_id is required")
    if reason_note is not None and not isinstance(reason_note, str):
        raise PursuitDecisionError("INVALID_REASON_NOTE", "reason_note must be a string or null")
    _require_aware_timestamp(decided_at, "decided_at")
    if not isinstance(reviewed, str) or len(reviewed) != 64:
        raise PursuitDecisionError(
            "MISSING_REVIEWED_CONTEXT_FINGERPRINT", "reviewed_context_fingerprint is required"
        )

    # Exact canonical membership: exact string equality, no normalization.
    if not isinstance(job_id, str) or not job_id:
        raise PursuitDecisionError("UNKNOWN_JOB_ID", "job_id is required")
    matches = [r for r in jobs_rows if r.get("Job_ID") == job_id]
    if not matches:
        raise PursuitDecisionError("UNKNOWN_JOB_ID", "job_id is not an existing canonical JOBS row")
    if len(matches) > 1:
        raise PursuitDecisionError("AMBIGUOUS_JOB_ID", "duplicate JOBS rows for job_id")
    jobs_row = matches[0]

    chain = _chain_for_job(_parse_decision_log_rows(log_rows), job_id)
    known = {e["event_id"]: e for e in chain}

    event_id = compute_event_id(
        job_id=job_id,
        decision=decision,
        decision_context_fingerprint=reviewed,
        supersedes_event_id=supersedes,
        decision_run_id=run_id,
    )

    # Exact replay of an already-persisted event is a no-op.
    if event_id in known:
        if known[event_id]["reason_note"] != reason_note:
            raise PursuitDecisionError(
                "EVENT_ID_CONFLICT", "same event_id reused with a conflicting payload"
            )
        return {"jobs_mutations": [], "log_mutations": []}

    current_fingerprint = compute_context_fingerprint(jobs_row)
    if reviewed != current_fingerprint:
        raise PursuitDecisionError(
            "STALE_REVIEWED_CONTEXT",
            "JOBS context changed after Bora's review; re-review and resubmit",
        )

    latest_id = chain[-1]["event_id"] if chain else None
    if supersedes != latest_id:
        raise PursuitDecisionError(
            "SUPERSEDES_MISMATCH",
            "supersedes_event_id must equal the current latest event (null when none)",
        )

    event = {
        "Job_ID": job_id,
        "decision": decision,
        "decided_at": decided_at,
        "decided_by": DECIDED_BY,
        "decision_run_id": run_id,
        "reason_note": reason_note,
        "reviewed_context_fingerprint": reviewed,
        "decision_context_fingerprint": current_fingerprint,
        "event_id": event_id,
        "supersedes_event_id": supersedes,
    }
    plan = {
        "jobs_mutations": [{"Op": "UPDATE", "Job_ID": job_id, "Bora_Decision": decision}],
        "log_mutations": [
            {
                "Run_ID": run_id,
                "Timestamp": decided_at,
                "Stage": LOG_STAGE,
                "Source": LOG_SOURCE,
                "Job_ID": job_id,
                "Status": LOG_STATUS,
                "Error_Code": None,
                "Engine_Baseline": ENGINE_BASELINE,
                "Notes": _canonical_json(event),
            }
        ],
    }
    build_draft202012_validator(PURSUIT_DECISION_MUTATION_SCHEMA_PATH).validate(plan)
    return plan
