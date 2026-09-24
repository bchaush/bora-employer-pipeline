"""SUPERVISED_PRODUCTION_V1_SLICE_2: verified gates -> frozen Match Truth.

Provider-neutral orchestration only. This module consumes already-established
verified employer input and upstream gate outcomes. It does not create Employer
Truth, alter gate semantics, or redefine Match Truth.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from job_analysis import analyze_job  # noqa: E402

ENGINE_BASELINE = "SUPERVISED_PRODUCTION_V1_SLICE_2_GATES_MATCH_TRUTH_TO_SHEET"

# Canonical doctrine order, represented with bounded control-plane names.
GATE_ORDER = (
    "freshness",
    "geography",
    "employer_exclusions_start_horizon",
    "opt_screen",
    "candidate_conditions",
    "threshold_seniority_specialist",
    "actionability_conflicts",
    "crowding",
)
GATE_RESULTS = frozenset({"PASS", "HOLD", "REJECT", "NOT_EVALUATED"})
PROJECTED_GATES = {
    "freshness": "Freshness_State",
    "geography": "Geography_State",
    "opt_screen": "OPT_Screen_State",
    "candidate_conditions": "Candidate_Condition_State",
    "threshold_seniority_specialist": "Threshold_State",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def compute_employer_input_fingerprint(employer_verified_input: Mapping[str, Any]) -> str:
    """Hash the exact verified employer/analysis input without changing it."""
    if not isinstance(employer_verified_input, Mapping):
        return ""
    return hashlib.sha256(_canonical_bytes(dict(employer_verified_input))).hexdigest()


def compute_request_fingerprint(request: Mapping[str, Any]) -> str:
    """Idempotency key for the semantic Slice 2 request.

    Deliberately excludes discovery_claims and other unrelated wrapper keys:
    untrusted discovery observations cannot change verified analysis state.
    """
    if not isinstance(request, Mapping):
        return hashlib.sha256(_canonical_bytes({"malformed_request": repr(request)})).hexdigest()
    semantic = {
        "operational_job_id": request.get("operational_job_id"),
        "employer_verified_input": request.get("employer_verified_input"),
        "upstream_gates": request.get("upstream_gates"),
        "analysis_binding": request.get("analysis_binding"),
    }
    return hashlib.sha256(_canonical_bytes(semantic)).hexdigest()


def _valid_aware_datetime(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return value


def _validate_verified_input(value: Any) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(value, Mapping):
        return {}, ["EMPLOYER_VERIFIED_INPUT_REQUIRED"]
    item = dict(value)
    errors: list[str] = []
    for field in ("company", "role", "jd_text", "date_last_verified"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            errors.append(f"{field.upper()}_REQUIRED")
    if not isinstance(item.get("structured_extraction"), Mapping):
        errors.append("STRUCTURED_EXTRACTION_REQUIRED")
    if not isinstance(item.get("role_status"), str) or not item["role_status"].strip():
        errors.append("ROLE_STATUS_REQUIRED")
    if (
        not isinstance(item.get("source_verification_status"), str)
        or not item["source_verification_status"].strip()
    ):
        errors.append("SOURCE_VERIFICATION_STATUS_REQUIRED")
    official_url = item.get("official_url")
    if official_url is not None and (
        not isinstance(official_url, str) or not official_url.strip()
    ):
        errors.append("OFFICIAL_URL_INVALID")
    return item, errors


def _normalize_gates(raw: Any) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    supplied = dict(raw) if isinstance(raw, Mapping) else {}
    states: dict[str, str] = {}
    details: dict[str, dict[str, Any]] = {}

    for gate_name in GATE_ORDER:
        gate_raw = supplied.get(gate_name)
        if not isinstance(gate_raw, Mapping):
            states[gate_name] = "NOT_EVALUATED"
            details[gate_name] = {
                "result": "NOT_EVALUATED",
                "reason": "required upstream gate outcome missing",
                "provenance": None,
                "verification_source": None,
                "laundering_rejected": False,
            }
            continue

        claimed = gate_raw.get("result")
        reason = gate_raw.get("reason")
        provenance = gate_raw.get("provenance")
        verification_source = gate_raw.get("verification_source")
        laundering_rejected = verification_source != "AUTHORITATIVE"
        evidence_complete = (
            isinstance(reason, str)
            and bool(reason.strip())
            and isinstance(provenance, str)
            and bool(provenance.strip())
        )

        if claimed not in GATE_RESULTS:
            state = "NOT_EVALUATED"
        elif laundering_rejected or not evidence_complete:
            # An untrusted source or a label with no auditable reason/
            # provenance cannot become an upstream truth outcome.
            state = "NOT_EVALUATED"
        else:
            state = claimed

        states[gate_name] = state
        details[gate_name] = {
            "result": state,
            "claimed_result": claimed,
            "reason": reason.strip() if isinstance(reason, str) else "",
            "provenance": provenance.strip() if isinstance(provenance, str) else None,
            "verification_source": verification_source,
            "laundering_rejected": laundering_rejected,
            "evidence_complete": evidence_complete,
        }

    # Unexpected gate names are never silently treated as canonical gates.
    extras = sorted(str(k) for k in supplied.keys() if k not in GATE_ORDER)
    if extras:
        details["_unexpected_gates"] = {
            "result": "NOT_EVALUATED",
            "reason": "unexpected gate names supplied",
            "provenance": ",".join(extras),
            "verification_source": None,
            "laundering_rejected": False,
        }
    return states, details


def _projected_gate_states(states: Mapping[str, str]) -> dict[str, str]:
    return {jobs_field: states[gate_name] for gate_name, jobs_field in PROJECTED_GATES.items()}


def _first_blocking_gate(states: Mapping[str, str]) -> tuple[str | None, str | None]:
    for gate_name in GATE_ORDER:
        state = states[gate_name]
        if state != "PASS":
            return gate_name, state
    return None, None


def _binding_result(
    operational_job_id: str,
    employer_input: Mapping[str, Any],
    binding: Any,
) -> tuple[bool, str | None]:
    if not isinstance(binding, Mapping):
        return False, "ANALYSIS_BINDING_REQUIRED"
    if binding.get("operational_job_id") != operational_job_id:
        return False, "ANALYSIS_BINDING_JOB_ID_MISMATCH"
    expected = compute_employer_input_fingerprint(employer_input)
    if binding.get("content_fingerprint") != expected:
        return False, "ANALYSIS_BINDING_CONTENT_MISMATCH"
    return True, None


def _analysis_input(employer_input: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "company": employer_input["company"],
        "role": employer_input["role"],
        "jd_text": employer_input["jd_text"],
        "structured_extraction": dict(employer_input["structured_extraction"]),
        "role_status": employer_input.get("role_status"),
        "source_verification_status": employer_input.get("source_verification_status"),
        "date_last_verified": employer_input.get("date_last_verified"),
        "official_url": employer_input.get("official_url"),
    }
    pre = employer_input.get("pre_surfacing_verification")
    if isinstance(pre, Mapping):
        payload["pre_surfacing_verification"] = dict(pre)
        run_id = pre.get("operation_run_id")
        if isinstance(run_id, str) and run_id.strip():
            payload["operation_run_id"] = run_id
    return payload


def _last_verified_at(employer_input: Mapping[str, Any]) -> str | None:
    # Preserve the ledger's date-time contract. A date-only
    # date_last_verified is passed to Match Truth but never coerced into a
    # fabricated timestamp for JOBS.Last_Verified.
    pre = employer_input.get("pre_surfacing_verification")
    if isinstance(pre, Mapping):
        return _valid_aware_datetime(pre.get("observed_at"))
    return None


def evaluate_supervised_job(
    request: Mapping[str, Any],
    *,
    existing_job: Mapping[str, Any] | None,
    claim_index: Mapping[str, Any] | None = None,
    evidence_index: Mapping[str, Any] | None = None,
    claim_root: Path | None = None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    """Evaluate one already-resolved operational job without provider I/O."""

    operational_job_id = request.get("operational_job_id") if isinstance(request, Mapping) else None
    if not isinstance(operational_job_id, str) or not operational_job_id.strip():
        return {
            "outcome": "INPUT_ERROR",
            "operational_job_id": None,
            "error_code": "OPERATIONAL_JOB_ID_REQUIRED",
        }
    if not isinstance(existing_job, Mapping):
        return {
            "outcome": "INPUT_ERROR",
            "operational_job_id": operational_job_id,
            "error_code": "UNKNOWN_OPERATIONAL_JOB_ID",
        }
    if existing_job.get("Job_ID") != operational_job_id:
        return {
            "outcome": "INPUT_ERROR",
            "operational_job_id": operational_job_id,
            "error_code": "OPERATIONAL_JOB_ID_MISMATCH",
        }

    employer_input, verified_input_errors = _validate_verified_input(
        request.get("employer_verified_input")
    )
    gate_states, gate_details = _normalize_gates(request.get("upstream_gates"))
    if "_unexpected_gates" in gate_details:
        verified_input_errors.append("UNEXPECTED_GATE_NAMES")
    projected_states = _projected_gate_states(gate_states)
    binding_ok, binding_error = _binding_result(
        operational_job_id,
        employer_input,
        request.get("analysis_binding"),
    )
    primary_gate, primary_state = _first_blocking_gate(gate_states)

    content_fingerprint = compute_request_fingerprint(request)
    common = {
        "outcome": "PROJECT",
        "operational_job_id": operational_job_id,
        "content_fingerprint": content_fingerprint,
        "gate_states": projected_states,
        "gate_details": gate_details,
        "primary_blocking_gate": primary_gate,
        "binding_ok": binding_ok,
        "binding_error": binding_error,
        "verified_input_errors": verified_input_errors,
        "analysis_errors": [],
        "official_url": (
            employer_input.get("official_url")
            if isinstance(employer_input.get("official_url"), str)
            and employer_input.get("official_url").strip()
            else None
        ),
        "date_last_verified": employer_input.get("date_last_verified"),
        "last_verified_at": _last_verified_at(employer_input),
        "role_status": (
            employer_input.get("role_status")
            if isinstance(employer_input.get("role_status"), str)
            else None
        ),
    }

    if verified_input_errors or not binding_ok:
        return {
            **common,
            "outcome": "VERIFICATION_ERROR",
            "pipeline_state": "VERIFICATION_REQUIRED",
            "match_state": "NOT_REACHED",
            "decision": None,
            "error_code": binding_error or verified_input_errors[0],
        }

    if primary_gate is not None:
        pipeline = "UPSTREAM_REJECTED" if primary_state == "REJECT" else "VERIFICATION_REQUIRED"
        return {
            **common,
            "pipeline_state": pipeline,
            "match_state": "NOT_REACHED",
            "decision": None,
        }

    result = analyze_job(
        _analysis_input(employer_input),
        claim_index=claim_index,
        evidence_index=evidence_index,
        claim_root=claim_root,
        evidence_root=evidence_root,
    )
    if result.get("valid") is not True or not isinstance(result.get("analysis"), Mapping):
        return {
            **common,
            "pipeline_state": "PROCESSING_ERROR",
            "match_state": "PROCESSING_ERROR",
            "decision": None,
            "analysis_errors": list(result.get("errors") or []),
        }

    analysis = result["analysis"]
    # Explicitly keep operational and analysis identity separate. Binding is
    # to operational_job_id + exact verified input fingerprint; analyze_job's
    # generated job_id is provenance only and never selects a JOBS row.
    return {
        **common,
        "pipeline_state": "REVIEW_READY",
        "match_state": "ANALYZED",
        "decision": analysis.get("decision"),
        "role_status": analysis.get("role_status"),
        "analysis_job_id": analysis.get("job_id"),
        "analysis_lane": analysis.get("lane"),
    }
