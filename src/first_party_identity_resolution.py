"""SUPERVISED_PRODUCTION_V1_FIRST_PARTY_IDENTITY_RESOLUTION_V1.

Provider-neutral deterministic identity bridge only.

The supervised provider layer is responsible for locating and reading a
current first-party employer/ATS posting.  This module never performs network,
browser, Gmail, or Google Sheets I/O.  It consumes:

1. one durable Slice-1 IDENTITY_RESOLUTION / VERIFICATION_REQUIRED LOG row; and
2. one bounded first-party posting observation.

Canonical operational identity remains owned by exact_role_identity.py.
This module never creates a company/title hash, treats a discovery-platform ID
as an employer requisition, or falls back to URL/fuzzy identity.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from exact_role_identity import resolve_exact_role_key  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REQUEST_SCHEMA_PATH = ROOT / "schemas" / "first_party_identity_resolution.schema.json"

ENGINE_BASELINE = "SUPERVISED_PRODUCTION_V1_FIRST_PARTY_IDENTITY_RESOLUTION_V1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _best_effort_discovery_lead_id(request: Mapping[str, Any] | Any) -> str | None:
    if not isinstance(request, Mapping):
        return None
    record = request.get("discovery_log_record")
    if not isinstance(record, Mapping):
        return None
    notes = record.get("Notes")
    if not isinstance(notes, str):
        return None
    try:
        parsed = json.loads(notes)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, Mapping):
        return None
    lead_id = parsed.get("discovery_lead_id")
    return lead_id if isinstance(lead_id, str) and lead_id.strip() else None


def compute_resolution_fingerprint(request: Mapping[str, Any] | Any) -> str:
    """Stable idempotency identity for one lead + first-party observation.

    Discovery LOG run/timestamp metadata is deliberately excluded when a
    durable discovery_lead_id can be recovered.  Rehydrating the same lead
    from the Sheet and replaying byte-equivalent first-party evidence therefore
    converges to the same fingerprint across sessions.
    """

    if isinstance(request, Mapping):
        lead_id = _best_effort_discovery_lead_id(request)
        first_party = request.get("first_party_observation")
        if lead_id is not None:
            payload: Any = {
                "discovery_lead_id": lead_id,
                "first_party_observation": first_party,
            }
        else:
            payload = dict(request)
    else:
        payload = {"malformed_request": repr(request)}
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"FPIR_V1::{digest}"


def _aware_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _normalize_exact_text(value: str) -> str:
    """Only the bounded normalization allowed by the frozen contract."""

    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.casefold().split())


def _normalized_evidence_text(value: str) -> str:
    # Preserve punctuation/content; only Unicode/case/whitespace normalization.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _schema_errors(request: Any) -> list[str]:
    validator = build_draft202012_validator(REQUEST_SCHEMA_PATH)
    errors = sorted(
        validator.iter_errors(request),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    rendered: list[str] = []
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        rendered.append(f"{path}: {error.message}")
    return rendered


def _parse_discovery_provenance(
    discovery_log_record: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    notes = discovery_log_record.get("Notes")
    try:
        parsed = json.loads(notes) if isinstance(notes, str) else None
    except json.JSONDecodeError:
        return None, ["DISCOVERY_LOG_NOTES_INVALID_JSON"]
    if not isinstance(parsed, Mapping):
        return None, ["DISCOVERY_LOG_NOTES_NOT_OBJECT"]

    provenance = dict(parsed)
    errors: list[str] = []
    required_strings = (
        "discovery_lead_id",
        "source_message_id",
        "observed_at",
        "employer_text",
        "role_text",
    )
    for field in required_strings:
        value = provenance.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"DISCOVERY_{field.upper()}_REQUIRED")

    urls = provenance.get("discovery_urls")
    if not isinstance(urls, list):
        errors.append("DISCOVERY_URLS_REQUIRED")
    elif any(not isinstance(url, str) or not url.strip() for url in urls):
        errors.append("DISCOVERY_URLS_INVALID")

    claims = provenance.get("source_claims")
    if not isinstance(claims, Mapping):
        errors.append("DISCOVERY_SOURCE_CLAIMS_REQUIRED")

    if _aware_datetime(provenance.get("observed_at")) is None:
        errors.append("DISCOVERY_OBSERVED_AT_INVALID")

    return (provenance if not errors else None), errors


def evaluate_first_party_identity_request(request: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Evaluate one durable unresolved observation against first-party evidence.

    Returns a deterministic outcome object.  PROCESSING_ERROR is reserved for
    malformed or internally contradictory resolver input.  Evidence that is
    well-formed but insufficient/ambiguous remains VERIFICATION_REQUIRED.
    """

    fingerprint = compute_resolution_fingerprint(request)
    schema_errors = _schema_errors(request)
    if schema_errors:
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "FIRST_PARTY_REQUEST_SCHEMA_INVALID",
            "errors": schema_errors,
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": _best_effort_discovery_lead_id(request),
            "operational_job_id": None,
        }

    assert isinstance(request, Mapping)
    discovery_record = request["discovery_log_record"]
    first_party = request["first_party_observation"]
    assert isinstance(discovery_record, Mapping)
    assert isinstance(first_party, Mapping)

    provenance, provenance_errors = _parse_discovery_provenance(discovery_record)
    if provenance_errors or provenance is None:
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": provenance_errors[0],
            "errors": provenance_errors,
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": _best_effort_discovery_lead_id(request),
            "operational_job_id": None,
        }

    lead_id = provenance["discovery_lead_id"]
    observed_at = first_party.get("observed_at")
    if _aware_datetime(observed_at) is None:
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "FIRST_PARTY_OBSERVED_AT_INVALID",
            "errors": ["first_party_observation.observed_at must include an explicit timezone offset"],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
        }

    discovery_role = provenance["role_text"]
    observed_role = first_party["observed_role_title"]
    if _normalize_exact_text(discovery_role) != _normalize_exact_text(observed_role):
        return {
            "outcome": "VERIFICATION_REQUIRED",
            "error_code": "ROLE_BINDING_MISMATCH",
            "errors": [],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    employer_binding = first_party["employer_binding_status"]
    if employer_binding != "VERIFIED":
        return {
            "outcome": "VERIFICATION_REQUIRED",
            "error_code": f"EMPLOYER_BINDING_{employer_binding}",
            "errors": [],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    requisition_status = first_party["requisition_status"]
    if requisition_status != "EXACT":
        code = (
            "EXACT_REQUISITION_MISSING"
            if requisition_status == "MISSING"
            else "EXACT_REQUISITION_AMBIGUOUS"
        )
        return {
            "outcome": "VERIFICATION_REQUIRED",
            "error_code": code,
            "errors": [],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    exact_employer_identity = first_party["exact_employer_identity"]
    exact_requisition_id = first_party["exact_requisition_id"]
    evidence = first_party["requisition_evidence"]
    assert isinstance(exact_employer_identity, str)
    assert isinstance(exact_requisition_id, str)
    assert isinstance(evidence, str)

    source_claims = provenance.get("source_claims")
    discovery_platform_ids: set[str] = set()
    if isinstance(source_claims, Mapping):
        for key in ("source_job_id", "job_id", "listing_id", "opportunity_id"):
            value = source_claims.get(key)
            if isinstance(value, str) and value.strip():
                discovery_platform_ids.add(value.strip().casefold())

    if exact_requisition_id.strip().casefold() in discovery_platform_ids:
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "DISCOVERY_PLATFORM_ID_FORBIDDEN",
            "errors": [
                "exact_requisition_id matches an identifier from third-party discovery provenance"
            ],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    if _normalized_evidence_text(exact_requisition_id) not in _normalized_evidence_text(evidence):
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "REQUISITION_EVIDENCE_MISMATCH",
            "errors": [
                "first_party_observation.requisition_evidence does not contain the supplied exact_requisition_id"
            ],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    operational_job_id = resolve_exact_role_key(
        exact_employer_identity,
        exact_requisition_id,
    )
    if operational_job_id is None:
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "EXACT_ROLE_KEY_UNRESOLVED",
            "errors": ["verified first-party identity did not produce an exact role key"],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    discovery_urls = provenance.get("discovery_urls") or []
    discovery_url = discovery_urls[0] if discovery_urls else None

    return {
        "outcome": "RESOLVED",
        "error_code": None,
        "errors": [],
        "resolution_fingerprint": fingerprint,
        "discovery_lead_id": lead_id,
        "operational_job_id": operational_job_id,
        "exact_employer_identity": exact_employer_identity,
        "exact_requisition_id": exact_requisition_id,
        "company": first_party["observed_employer_name"],
        "role": observed_role,
        "discovery_source": discovery_record["Source"],
        "discovery_url": discovery_url,
        "official_url": first_party["official_url"],
        "first_seen": provenance["observed_at"],
        "last_verified": observed_at,
        "discovery_provenance": provenance,
        "first_party_observation": dict(first_party),
    }
