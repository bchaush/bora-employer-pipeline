"""SUPERVISED_PRODUCTION_V1_SLICE_1: deterministic JOBS + LOG mutation plans.

Pure functions only: this module never performs Gmail or Google Sheets I/O.
Callers (the supervised connector layer) read current JOBS/LOG state, pass it
in as `existing_state`, apply the returned mutation plan through the provider
adapter, and persist the returned `next_state` for the following run.

Idempotency: a DiscoveryLead whose discovery_lead_id already appears in
existing_state["processed_lead_ids"] produces no mutation at all on rerun --
not a duplicate success record, not a second JOBS row.

Convergence: multiple leads that resolve to the same exact-role key (whether
from the same batch or a prior run) update one JOBS row rather than creating
a second one. First_Seen is the earliest observation timestamp and
Last_Verified is the latest, independent of mailbox delivery order.

Unresolved-identity and malformed leads never create a JOBS row and never
silently disappear -- they always produce a LOG mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from exact_role_identity import resolve_exact_role_key  # noqa: E402
from supervised_analysis import (  # noqa: E402
    ENGINE_BASELINE as SLICE_2_ENGINE_BASELINE,
    compute_request_fingerprint,
    evaluate_supervised_job,
)

ENGINE_BASELINE = "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET"

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_LEDGER_MUTATION_SCHEMA_PATH = (
    ROOT / "schemas" / "production_ledger_mutation.schema.json"
)


def empty_state() -> dict[str, Any]:
    """Return an empty existing_state for a fresh ledger (no prior JOBS/LOG)."""
    return {"jobs": {}, "processed_lead_ids": [], "gate_match_fingerprints": {}}


def _lead_provenance(lead: Mapping[str, Any]) -> str:
    payload = {
        "discovery_lead_id": lead.get("discovery_lead_id"),
        "source_message_id": lead.get("source_message_id"),
        "source_thread_id": lead.get("source_thread_id"),
        "observed_at": lead.get("observed_at"),
        "discovery_urls": list(lead.get("discovery_urls") or []),
        "employer_text": lead.get("employer_text"),
        "role_text": lead.get("role_text"),
        "requisition_text": lead.get("requisition_text"),
        "source_claims": dict(lead.get("source_claims") or {}),
        "exact_employer_identity": lead.get("exact_employer_identity"),
        "exact_requisition_id": lead.get("exact_requisition_id"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def state_from_ledger_rows(
    jobs_rows: list[Mapping[str, Any]],
    log_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Rehydrate deterministic idempotency state from durable JOBS/LOG rows."""
    jobs: dict[str, dict[str, Any]] = {}
    for row in jobs_rows:
        job_id = row.get("Job_ID")
        if isinstance(job_id, str) and job_id:
            jobs[job_id] = dict(row)

    processed_lead_ids: set[str] = set()
    gate_match_fingerprints: dict[str, str] = {}
    for row in log_rows:
        notes = row.get("Notes")
        if not isinstance(notes, str):
            continue
        try:
            provenance = json.loads(notes)
        except json.JSONDecodeError:
            continue
        if not isinstance(provenance, Mapping):
            continue
        lead_id = provenance.get("discovery_lead_id")
        if isinstance(lead_id, str) and lead_id:
            processed_lead_ids.add(lead_id)
        gate_match_job_id = provenance.get("operational_job_id")
        gate_match_fingerprint = provenance.get("gate_match_fingerprint")
        if isinstance(gate_match_job_id, str) and gate_match_job_id and isinstance(
            gate_match_fingerprint, str
        ) and gate_match_fingerprint:
            gate_match_fingerprints[gate_match_job_id] = gate_match_fingerprint

    return {
        "jobs": jobs,
        "processed_lead_ids": sorted(processed_lead_ids),
        "gate_match_fingerprints": gate_match_fingerprints,
    }


def _timestamp_key(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _earliest_timestamp(left: str, right: str) -> str:
    return left if _timestamp_key(left) <= _timestamp_key(right) else right


def _latest_timestamp(left: str, right: str) -> str:
    return left if _timestamp_key(left) >= _timestamp_key(right) else right


def _log_mutation(
    *,
    run_id: str,
    timestamp: str,
    stage: str,
    source: str,
    job_id: str | None,
    status: str,
    error_code: str | None,
    notes: str,
    engine_baseline: str = ENGINE_BASELINE,
) -> dict[str, Any]:
    return {
        "Run_ID": run_id,
        "Timestamp": timestamp,
        "Stage": stage,
        "Source": source,
        "Job_ID": job_id,
        "Status": status,
        "Error_Code": error_code,
        "Engine_Baseline": engine_baseline,
        "Notes": notes,
    }


def build_mutation_plan(
    discovery_leads: list[Mapping[str, Any]],
    existing_state: Mapping[str, Any] | None,
    *,
    run_id: str,
    processed_at: str,
) -> dict[str, Any]:
    """Build the JOBS + LOG mutation plan for a batch of DiscoveryLead records.

    Returns {"jobs_mutations": [...], "log_mutations": [...], "next_state": {...}}.
    `next_state` is the ledger snapshot after applying the returned mutations
    and must be persisted by the caller for idempotent future runs.
    """

    base_state = existing_state if existing_state is not None else empty_state()
    jobs: dict[str, dict[str, Any]] = {
        key: dict(value) for key, value in base_state.get("jobs", {}).items()
    }
    processed_lead_ids: set[str] = set(base_state.get("processed_lead_ids", []))

    jobs_mutations: list[dict[str, Any]] = []
    log_mutations: list[dict[str, Any]] = []

    for lead in discovery_leads:
        lead_id = lead["discovery_lead_id"]
        if lead_id in processed_lead_ids:
            continue

        if lead.get("raw_status") == "MALFORMED":
            log_mutations.append(
                _log_mutation(
                    run_id=run_id,
                    timestamp=processed_at,
                    stage="INGESTION",
                    source=lead.get("source", "GMAIL"),
                    job_id=None,
                    status="PROCESSING_ERROR",
                    error_code=lead.get("error_code", "MALFORMED_INPUT"),
                    notes=json.dumps({
                        "discovery_lead_id": lead_id,
                        "source_message_id": lead.get("source_message_id"),
                        "error_message": lead.get("error_message", "malformed message observation"),
                    }, sort_keys=True, separators=(",", ":")),
                )
            )
            processed_lead_ids.add(lead_id)
            continue

        source = lead["source"]
        exact_employer_identity = lead.get("exact_employer_identity")
        exact_requisition_id = lead.get("exact_requisition_id")
        exact_role_key = resolve_exact_role_key(exact_employer_identity, exact_requisition_id)

        if lead.get("identity_resolution_status") != "RESOLVED" or exact_role_key is None:
            log_mutations.append(
                _log_mutation(
                    run_id=run_id,
                    timestamp=processed_at,
                    stage="IDENTITY_RESOLUTION",
                    source=source,
                    job_id=None,
                    status="VERIFICATION_REQUIRED",
                    error_code=None,
                    notes=_lead_provenance(lead),
                )
            )
            processed_lead_ids.add(lead_id)
            continue

        discovery_urls = lead.get("discovery_urls") or []
        discovery_url = discovery_urls[0] if discovery_urls else None
        employer_text = lead.get("employer_text")
        role_text = lead.get("role_text")
        observed_at = lead.get("observed_at")

        existing_job = jobs.get(exact_role_key)
        if existing_job is None:
            job_row = {
                "Op": "CREATE",
                "Job_ID": exact_role_key,
                "Company": employer_text,
                "Role": role_text,
                "Discovery_Source": source,
                "Discovery_URL": discovery_url,
                "Official_URL": None,
                "First_Seen": observed_at,
                "Last_Verified": observed_at,
                "Pipeline_State": "NORMALIZED",
            }
            jobs[exact_role_key] = job_row
            jobs_mutations.append(dict(job_row))
            log_notes = _lead_provenance(lead)
        else:
            merged = dict(existing_job)
            merged["Op"] = "UPDATE"
            merged["First_Seen"] = _earliest_timestamp(merged["First_Seen"], observed_at)
            merged["Last_Verified"] = _latest_timestamp(merged["Last_Verified"], observed_at)
            if merged.get("Discovery_URL") is None and discovery_url is not None:
                merged["Discovery_URL"] = discovery_url
            if merged.get("Company") is None and employer_text is not None:
                merged["Company"] = employer_text
            if merged.get("Role") is None and role_text is not None:
                merged["Role"] = role_text
            jobs[exact_role_key] = merged
            jobs_mutations.append(dict(merged))
            log_notes = _lead_provenance(lead)

        log_mutations.append(
            _log_mutation(
                run_id=run_id,
                timestamp=processed_at,
                stage="LEDGER_PERSISTENCE",
                source=source,
                job_id=exact_role_key,
                status="NORMALIZED",
                error_code=None,
                notes=log_notes,
            )
        )
        processed_lead_ids.add(lead_id)

    return {
        "jobs_mutations": jobs_mutations,
        "log_mutations": log_mutations,
        "next_state": {
            "jobs": jobs,
            "processed_lead_ids": sorted(processed_lead_ids),
            "gate_match_fingerprints": dict(base_state.get("gate_match_fingerprints", {})),
        },
    }


def build_gate_match_mutation_plan(
    requests: list[Mapping[str, Any]],
    existing_state: Mapping[str, Any] | None,
    *,
    run_id: str,
    processed_at: str,
    claim_index: Mapping[str, Any] | None = None,
    evidence_index: Mapping[str, Any] | None = None,
    claim_root: Path | None = None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    """SUPERVISED_PRODUCTION_V1_SLICE_2 entry point: build the JOBS + LOG
    mutation plan that projects gate outcomes and (when authorized) the
    existing Match Truth core's output onto already Slice-1-resolved
    operational JOBS rows.

    Never creates a JOBS row: a request whose operational_job_id has no
    existing row in existing_state["jobs"] fails closed to a PROCESSING_ERROR
    LOG entry with no JOBS mutation. Idempotent: reprocessing a request whose
    full content (operational_job_id + employer_verified_input +
    upstream_gates + analysis_binding) is byte-identical to the last applied
    state for that operational Job_ID produces no mutation at all.

    Returns {"jobs_mutations": [...], "log_mutations": [...], "next_state": {...}}.
    """
    from schema_validation import build_draft202012_validator  # local import; avoids cycle at module load

    base_state = existing_state if existing_state is not None else empty_state()
    jobs: dict[str, dict[str, Any]] = {
        key: dict(value) for key, value in base_state.get("jobs", {}).items()
    }
    processed_lead_ids: set[str] = set(base_state.get("processed_lead_ids", []))
    gate_match_fingerprints: dict[str, str] = dict(
        base_state.get("gate_match_fingerprints", {})
    )

    jobs_mutations: list[dict[str, Any]] = []
    log_mutations: list[dict[str, Any]] = []

    for request in requests:
        operational_job_id = (
            request.get("operational_job_id") if isinstance(request, Mapping) else None
        )
        request_fingerprint = compute_request_fingerprint(request)

        if isinstance(operational_job_id, str) and operational_job_id.strip():
            prior_fingerprint = gate_match_fingerprints.get(operational_job_id)
            if prior_fingerprint == request_fingerprint:
                # Idempotent no-op: this exact verified employer/gate/analysis
                # state has already been converged onto this operational row.
                continue

        existing_job = (
            jobs.get(operational_job_id) if isinstance(operational_job_id, str) else None
        )

        outcome = evaluate_supervised_job(
            request,
            existing_job=existing_job,
            claim_index=claim_index,
            evidence_index=evidence_index,
            claim_root=claim_root,
            evidence_root=evidence_root,
        )

        if outcome["outcome"] == "INPUT_ERROR":
            log_mutations.append(
                _log_mutation(
                    run_id=run_id,
                    timestamp=processed_at,
                    stage="GATE_MATCH_PROJECTION",
                    source="SUPERVISED_ANALYSIS",
                    job_id=outcome.get("operational_job_id"),
                    status="PROCESSING_ERROR",
                    error_code=outcome["error_code"],
                    notes=json.dumps(
                        {"operational_job_id": outcome.get("operational_job_id")},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    engine_baseline=SLICE_2_ENGINE_BASELINE,
                )
            )
            # Do not persist an idempotency fingerprint for a missing/invalid
            # operational row: the same request must become processable if a
            # later Slice 1 run establishes that exact-role JOBS entity.
            continue

        if outcome["outcome"] == "VERIFICATION_ERROR":
            log_mutations.append(
                _log_mutation(
                    run_id=run_id,
                    timestamp=processed_at,
                    stage="GATE_MATCH_PROJECTION",
                    source="SUPERVISED_ANALYSIS",
                    job_id=operational_job_id,
                    status="VERIFICATION_REQUIRED",
                    error_code=outcome["error_code"],
                    notes=json.dumps(
                        {
                            "operational_job_id": operational_job_id,
                            "gate_match_fingerprint": outcome["content_fingerprint"],
                            "gate_details": outcome["gate_details"],
                            "binding_ok": outcome["binding_ok"],
                            "binding_error": outcome["binding_error"],
                            "verified_input_errors": outcome["verified_input_errors"],
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                        default=str,
                    ),
                    engine_baseline=SLICE_2_ENGINE_BASELINE,
                )
            )
            gate_match_fingerprints[operational_job_id] = request_fingerprint
            continue

        merged = dict(existing_job)
        merged["Op"] = "UPDATE"
        merged["Pipeline_State"] = outcome["pipeline_state"]
        merged["Match_State"] = outcome["match_state"]
        merged["Decision"] = outcome["decision"]
        merged["Role_Status"] = outcome["role_status"]
        for jobs_field, gate_result in outcome["gate_states"].items():
            merged[jobs_field] = gate_result

        # Official_URL is populated only from explicit verified employer
        # input, never from Discovery_URL/discovery claims; when this run
        # supplies none, a previously verified value (if any) is preserved
        # rather than wiped to null.
        if outcome["official_url"] is not None:
            merged["Official_URL"] = outcome["official_url"]
        elif "Official_URL" not in merged:
            merged["Official_URL"] = None

        # Preserve the ledger's date-time contract. Slice 2 updates
        # Last_Verified only from a real timezone-aware current-run
        # verification timestamp (for example the pre-surfacing envelope's
        # observed_at). A date-only Employer Truth field is never coerced
        # into a fabricated midnight timestamp.
        if outcome["last_verified_at"] is not None:
            merged["Last_Verified"] = outcome["last_verified_at"]

        jobs[operational_job_id] = merged
        jobs_mutations.append(dict(merged))

        error_code = (
            "MATCH_TRUTH_ANALYSIS_INVALID"
            if outcome["pipeline_state"] == "PROCESSING_ERROR"
            else None
        )
        log_notes = json.dumps(
            {
                "operational_job_id": operational_job_id,
                "gate_match_fingerprint": outcome["content_fingerprint"],
                "gate_details": outcome["gate_details"],
                "primary_blocking_gate": outcome["primary_blocking_gate"],
                "binding_ok": outcome["binding_ok"],
                "binding_error": outcome["binding_error"],
                "verified_input_errors": outcome["verified_input_errors"],
                "analysis_errors": outcome["analysis_errors"],
                "pipeline_state": outcome["pipeline_state"],
                "match_state": outcome["match_state"],
                "analysis_decision": outcome.get("decision"),
                "analysis_job_id": outcome.get("analysis_job_id"),
                "analysis_lane": outcome.get("analysis_lane"),
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        log_mutations.append(
            _log_mutation(
                run_id=run_id,
                timestamp=processed_at,
                stage="GATE_MATCH_PROJECTION",
                source="SUPERVISED_ANALYSIS",
                job_id=operational_job_id,
                status=outcome["pipeline_state"],
                error_code=error_code,
                notes=log_notes,
                engine_baseline=SLICE_2_ENGINE_BASELINE,
            )
        )

        gate_match_fingerprints[operational_job_id] = request_fingerprint

    plan = {
        "jobs_mutations": jobs_mutations,
        "log_mutations": log_mutations,
    }
    validator = build_draft202012_validator(PRODUCTION_LEDGER_MUTATION_SCHEMA_PATH)
    validator.validate(plan)

    return {
        "jobs_mutations": jobs_mutations,
        "log_mutations": log_mutations,
        "next_state": {
            "jobs": jobs,
            "processed_lead_ids": sorted(processed_lead_ids),
            "gate_match_fingerprints": gate_match_fingerprints,
        },
    }
