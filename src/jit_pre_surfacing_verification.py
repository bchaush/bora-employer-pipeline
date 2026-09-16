"""JIT_PRE_SURFACING_VERIFICATION_GATE_V1 -- deterministic, pure validation of an
ephemeral, caller-supplied ``job_input['pre_surfacing_verification']`` envelope.

Blueprint §135 (PRE_SURFACING_FIRST_PARTY_ACTIONABILITY_ENFORCEMENT_V1) already
requires role_status=="VERIFIED_LIVE" AND source_verification_status==
"VERIFIED_DIRECT" before an APPLY-like decision may survive
job_decision.apply_posting_state_routing(). September 15 Personal-v1 operating
runs proved those two caller-supplied strings alone are insufficient: they can
be asserted with no coupled evidence that THIS exact requisition, in THIS
operating run, was actually observed live, first-party, and actionable --
production analyze_job() returned APPLY for VERIFIED_LIVE + VERIFIED_DIRECT
with date_last_verified=None and no verification packet at all.

This module is the missing evidence check. It never calls a network or
browser, never invents a date, and never upgrades a decision or rewrites
qualification truth -- it only ever confirms or fails a caller-supplied
JIT_PRE_SURFACING_VERIFICATION_V1 envelope against the job_input's own
identity/run facts, and (via apply_pre_surfacing_verification_gate) downgrades
an already-computed APPLY-like decision to WATCH when that envelope is
missing, malformed, stale, identity-mismatched, non-first-party, dead,
non-actionable, of unknown/malformed recency, or has an unresolved material
conflict. ``resolved_conflicts`` cannot launder material conflicts: only an
explicit allowlist of benign informational resolution codes may pass; any
unknown/non-benign code or malformed shape fails closed, while a non-empty
``material_conflicts`` list always fails closed.

CONTINUATION HARD CORRECTION (post-architect adjudication): a bare
``recency_observation.state`` label was not real provenance -- a caller could
assert ``AUTHORITATIVE_LIVE_RELATIVE_AGE`` with no source, no timestamp, and
no value, and it passed. Recency provenance is now real structure: the
envelope's own ``observed_at`` must be a valid timezone-aware ISO-8601
timestamp; ``job_input['date_last_verified']`` must be a valid YYYY-MM-DD date
that agrees with the calendar date of that ``observed_at``; and
``recency_observation`` must itself carry a matching
``source_kind=="FIRST_PARTY_DIRECT"``, a matching ``observed_at`` (identical
to the envelope's own), and a state-specific value that is actually present
and internally consistent (see ``_evaluate_recency_observation``). No date
arithmetic beyond same-day/not-later-than comparison is performed, and no
posting date is ever inferred from an application window.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping


VERIFICATION_KIND = "JIT_PRE_SURFACING_VERIFICATION_V1"
_REQUIRED_SOURCE_KIND = "FIRST_PARTY_DIRECT"
_REQUIRED_APPLICATION_ROUTE_STATUS = "ACTIONABLE"
# Only recency states with real, checked structure (not merely a state
# label) may promote. Anything else -- including the explicit "UNKNOWN"
# state, a missing/malformed recency_observation, or an unrecognized state
# string -- fails closed. See _evaluate_recency_observation for the
# per-state structural requirements.
_ALLOWED_RECENCY_STATES = frozenset(
    {
        "AUTHORITATIVE_LIVE_RELATIVE_AGE",
        "AUTHORITATIVE_ABSOLUTE_DATE",
        "AUTHORITATIVE_APPLICATION_WINDOW",
    }
)

# Only these three decisions are ever eligible for downgrade -- mirrors
# job_decision.py's own _APPLY_LIKE_DECISIONS constant (duplicated locally,
# not imported, because job_decision.py is out of scope for this milestone).
_APPLY_LIKE_DECISIONS = frozenset({"PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"})

MISSING_REASON = "CURRENT_VERIFICATION_EVIDENCE_MISSING"
_RECENCY_MALFORMED_REASON = "VERIFICATION_RECENCY_UNKNOWN_OR_MALFORMED"

# resolved_conflicts is informational only, but only for explicitly known,
# benign codes -- a material conflict must never be laundered into
# resolved_conflicts to bypass the material_conflicts fail-closed check
# below. Any code outside this allow-list, or a malformed (non-list) shape,
# fails closed exactly like an unresolved material conflict.
_ALLOWED_RESOLVED_CONFLICT_CODES = frozenset(
    {"SEARCH_RECENCY_OVERRIDDEN_BY_CURRENT_FIRST_PARTY_RECENCY"}
)


def _normalized_nonempty(value: Any) -> str | None:
    """The stripped string, or None if not a string or empty after stripping."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _parse_timezone_aware_datetime(value: Any) -> datetime | None:
    """A valid, timezone-aware ISO-8601 timestamp, or None otherwise. Never raises."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        return None
    return parsed


def _parse_calendar_date(value: Any) -> date | None:
    """A valid YYYY-MM-DD date, or None otherwise. Never raises."""
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _evaluate_recency_observation(
    recency: Any,
    *,
    envelope_observed_at: Any,
    observation_date: date | None,
) -> str | None:
    """Return a reason code if ``recency`` is not real, checked provenance
    for one of the supported authoritative shapes, or None if it is valid.

    A bare state label is never sufficient: ``source_kind`` must be
    FIRST_PARTY_DIRECT and ``observed_at`` must match the envelope's own
    observed_at exactly, in addition to the state-specific value below.
    """
    if not isinstance(recency, Mapping):
        return _RECENCY_MALFORMED_REASON

    state = recency.get("state")
    if state not in _ALLOWED_RECENCY_STATES:
        return _RECENCY_MALFORMED_REASON
    if recency.get("source_kind") != _REQUIRED_SOURCE_KIND:
        return _RECENCY_MALFORMED_REASON
    if recency.get("observed_at") != envelope_observed_at:
        return _RECENCY_MALFORMED_REASON

    if state == "AUTHORITATIVE_LIVE_RELATIVE_AGE":
        posted_age_days = recency.get("posted_age_days")
        if isinstance(posted_age_days, bool) or not isinstance(posted_age_days, int):
            return _RECENCY_MALFORMED_REASON
        if posted_age_days < 0:
            return _RECENCY_MALFORMED_REASON
        return None

    if state == "AUTHORITATIVE_ABSOLUTE_DATE":
        posted_date = _parse_calendar_date(recency.get("posted_date"))
        if posted_date is None or observation_date is None:
            return _RECENCY_MALFORMED_REASON
        if posted_date > observation_date:
            return _RECENCY_MALFORMED_REASON
        return None

    if state == "AUTHORITATIVE_APPLICATION_WINDOW":
        # At least one bound must be a real date; no posting date is ever
        # inferred from either bound. A window must also be temporally
        # meaningful AT OBSERVATION TIME: an already-closed window
        # (close_date before the observation date) or a not-yet-open window
        # (opened_date after the observation date) is not current
        # actionability evidence, and inverted bounds are internally
        # inconsistent.
        opened_date = _parse_calendar_date(recency.get("opened_date"))
        close_date = _parse_calendar_date(recency.get("close_date"))
        if opened_date is None and close_date is None:
            return _RECENCY_MALFORMED_REASON
        if observation_date is None:
            return _RECENCY_MALFORMED_REASON
        if opened_date is not None and opened_date > observation_date:
            return _RECENCY_MALFORMED_REASON
        if close_date is not None and close_date < observation_date:
            return _RECENCY_MALFORMED_REASON
        if opened_date is not None and close_date is not None and opened_date > close_date:
            return _RECENCY_MALFORMED_REASON
        return None

    return _RECENCY_MALFORMED_REASON


def evaluate_pre_surfacing_verification(
    *,
    job_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate ``job_input['pre_surfacing_verification']`` against this exact
    job's own identity/run facts (``operation_run_id``, ``official_url``,
    ``company``, ``role``).

    Returns ``{"valid": bool, "reasons": [stable diagnostic reason codes]}``.
    Pure function of ``job_input`` alone -- never mutates it, never raises for
    any malformed shape (every unexpected type/value fails closed with a
    reason code instead of an exception).
    """
    envelope = job_input.get("pre_surfacing_verification")
    if not isinstance(envelope, Mapping):
        return {"valid": False, "reasons": [MISSING_REASON]}

    reasons: list[str] = []

    if envelope.get("verification_kind") != VERIFICATION_KIND:
        reasons.append("VERIFICATION_PACKET_MALFORMED: verification_kind")

    run_id = job_input.get("operation_run_id")
    if (
        not isinstance(run_id, str)
        or not run_id.strip()
        or envelope.get("operation_run_id") != run_id
    ):
        reasons.append("VERIFICATION_RUN_ID_MISMATCH")

    official_url = job_input.get("official_url")
    if (
        not isinstance(official_url, str)
        or not official_url.strip()
        or envelope.get("exact_url") != official_url
    ):
        reasons.append("VERIFICATION_URL_MISMATCH")

    normalized_company = _normalized_nonempty(job_input.get("company"))
    normalized_observed_company = _normalized_nonempty(envelope.get("observed_company"))
    if (
        normalized_company is None
        or normalized_observed_company is None
        or normalized_company != normalized_observed_company
    ):
        reasons.append("VERIFICATION_IDENTITY_MISMATCH: company")

    normalized_role = _normalized_nonempty(job_input.get("role"))
    normalized_observed_role = _normalized_nonempty(envelope.get("observed_role"))
    if (
        normalized_role is None
        or normalized_observed_role is None
        or normalized_role != normalized_observed_role
    ):
        reasons.append("VERIFICATION_IDENTITY_MISMATCH: role")

    if envelope.get("source_kind") != _REQUIRED_SOURCE_KIND:
        reasons.append("VERIFICATION_SOURCE_NOT_FIRST_PARTY")

    if envelope.get("substantive_role_content_present") is not True:
        reasons.append("VERIFICATION_ROLE_CONTENT_MISSING")

    if envelope.get("application_route_status") != _REQUIRED_APPLICATION_ROUTE_STATUS:
        reasons.append("VERIFICATION_APPLICATION_ROUTE_NOT_ACTIONABLE")

    observed_at = envelope.get("observed_at")
    observed_at_dt = _parse_timezone_aware_datetime(observed_at)
    if observed_at_dt is None:
        reasons.append("VERIFICATION_PROVENANCE_MISSING")

    date_last_verified = job_input.get("date_last_verified")
    date_last_verified_date = _parse_calendar_date(date_last_verified)
    if (
        date_last_verified_date is None
        or observed_at_dt is None
        or date_last_verified_date != observed_at_dt.date()
    ):
        reasons.append("VERIFICATION_DATE_LAST_VERIFIED_MISMATCH")

    recency_reason = _evaluate_recency_observation(
        envelope.get("recency_observation"),
        envelope_observed_at=observed_at,
        observation_date=observed_at_dt.date() if observed_at_dt is not None else None,
    )
    if recency_reason is not None:
        reasons.append(recency_reason)

    material_conflicts = envelope.get("material_conflicts")
    if not isinstance(material_conflicts, list):
        reasons.append("VERIFICATION_PACKET_MALFORMED: material_conflicts")
    elif material_conflicts:
        # A resolved weaker-source recency conflict (resolved_conflicts) is
        # informational only and never inspected here -- it may coexist with
        # a current first-party authoritative recency observation without
        # itself blocking. Only an unresolved material_conflicts entry fails
        # closed.
        reasons.append("VERIFICATION_MATERIAL_CONFLICT_UNRESOLVED")

    resolved_conflicts = envelope.get("resolved_conflicts")
    if not isinstance(resolved_conflicts, list):
        reasons.append("VERIFICATION_PACKET_MALFORMED: resolved_conflicts")
    elif any(code not in _ALLOWED_RESOLVED_CONFLICT_CODES for code in resolved_conflicts):
        # A material conflict must never be laundered into resolved_conflicts
        # to bypass the material_conflicts check above -- only explicitly
        # known, benign resolution codes are ever accepted here.
        reasons.append("VERIFICATION_RESOLVED_CONFLICT_NOT_ALLOWED")

    if reasons:
        return {"valid": False, "reasons": reasons}
    return {"valid": True, "reasons": []}


def apply_pre_surfacing_verification_gate(
    *,
    base_result: Mapping[str, Any],
    job_input: Mapping[str, Any],
    role_status: Any,
    source_verification_status: Any,
) -> dict[str, Any]:
    """Downgrade-only gate, strictly AFTER
    job_decision.apply_posting_state_routing() has already produced its
    result.

    Only reachable when both posting-state axes already independently
    cleared the §135 gate (role_status=="VERIFIED_LIVE" AND
    source_verification_status=="VERIFIED_DIRECT") and the decision is still
    APPLY-like -- every other axis combination was already downgraded to
    WATCH upstream and is left untouched here. When reached, favorable
    caller strings alone are no longer sufficient: a current-run
    JIT_PRE_SURFACING_VERIFICATION_V1 envelope proving exact identity,
    actionability, recency provenance, and conflict resolution is also
    required, or the decision downgrades to WATCH.

    Never modifies requirements, evidence_matches, gaps, unknowns, or
    hard_blockers -- only lane/decision/decision_rationale/warnings. Never
    upgrades a decision and never introduces REJECT.
    """
    result = dict(base_result)

    if result.get("decision") not in _APPLY_LIKE_DECISIONS:
        return result
    if not (role_status == "VERIFIED_LIVE" and source_verification_status == "VERIFIED_DIRECT"):
        return result

    evaluation = evaluate_pre_surfacing_verification(job_input=job_input)
    if evaluation["valid"]:
        return result

    reasons = evaluation["reasons"]
    result["lane"] = "WATCH"
    result["decision"] = "WATCH"
    result["decision_rationale"] = (
        f"{result.get('decision_rationale', '')} "
        f"Downgraded to WATCH: {'; '.join(reasons)} "
        "(JIT_PRE_SURFACING_VERIFICATION_GATE_V1 -- favorable role_status/"
        "source_verification_status strings alone do not establish current-run "
        "first-party actionability; qualification result unchanged)."
    ).strip()
    result["warnings"] = list(result.get("warnings") or []) + reasons
    return result
