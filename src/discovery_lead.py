"""SUPERVISED_PRODUCTION_V1_SLICE_1: Gmail alert observation -> DiscoveryLead.

The Gmail/provider adapter is responsible for reading raw mail and handing
this module a bounded, already-structured observation shape (see
RawMessageObservation below). This module never parses raw email HTML/MIME;
that fragile provider-specific work stays outside deterministic truth
semantics per docs/SUPERVISED_PRODUCTION_V1.md section 4.

Everything this module extracts (employer/role text, requisition text,
discovery URLs) is an untrusted source observation. It is never promoted to
Employer Truth or Match Truth here or anywhere downstream of this module.

Exact-role identity extraction is deterministic and fails closed: unknown ATS
URL shapes, missing requisition text, or ambiguous/contradictory requisition
candidates all resolve to None (unresolved) rather than a guess. This module
never uses company/title fuzzy identity or src/job_id.py.
"""

from __future__ import annotations

import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from job_url_format import is_allowed_job_url  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DISCOVERY_LEAD_SCHEMA_PATH = ROOT / "schemas" / "discovery_lead.schema.json"

SUPPORTED_SOURCES = frozenset({"GMAIL"})


class MalformedMessageError(ValueError):
    """Raised when a raw message observation does not meet the bounded shape.

    Carries a stable error_code so callers can surface a deterministic
    PROCESSING_ERROR without inventing free-text failure reasons.
    """

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


_ATS_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"https?://(?P<tenant>[a-z0-9\-]+)(?:\.[a-z0-9\-]+)?\.myworkdayjobs\.com", re.IGNORECASE),
        "WORKDAY:{tenant}",
    ),
    (
        re.compile(r"https?://(?:www\.|boards\.)?greenhouse\.io/(?P<board>[a-z0-9\-]+)", re.IGNORECASE),
        "GREENHOUSE:{board}",
    ),
    (
        re.compile(r"https?://jobs\.lever\.co/(?P<company>[a-z0-9\-]+)", re.IGNORECASE),
        "LEVER:{company}",
    ),
)

_REQUISITION_URL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"_(?P<req>R-?\d{4,}|JR\d{4,})(?:[/?]|$)", re.IGNORECASE),
    re.compile(r"/jobs?/(?P<req>\d{5,})(?:[/?]|$)", re.IGNORECASE),
    re.compile(
        r"/(?P<req>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:[/?]|$)",
        re.IGNORECASE,
    ),
)

_REQUISITION_TEXT_PATTERN = re.compile(
    r"\b(?:req(?:uisition)?|job)\s*(?:id|#|number)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-]{3,})\b",
    re.IGNORECASE,
)


def _normalize_discovery_urls(raw_urls: Sequence[Any] | None) -> list[str]:
    if not raw_urls:
        return []
    normalized: list[str] = []
    for url in raw_urls:
        if isinstance(url, str) and url.strip() and is_allowed_job_url(url):
            if url not in normalized:
                normalized.append(url)
    return normalized


def _parse_exact_employer_identity(discovery_urls: Sequence[str]) -> str | None:
    candidates: set[str] = set()
    for url in discovery_urls:
        for pattern, template in _ATS_PATTERNS:
            match = pattern.search(url)
            if match:
                candidates.add(template.format(**match.groupdict()).upper())
                break
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _parse_exact_requisition_id(
    discovery_urls: Sequence[str], requisition_text: str | None
) -> str | None:
    candidates: set[str] = set()
    for url in discovery_urls:
        for pattern in _REQUISITION_URL_PATTERNS:
            match = pattern.search(url)
            if match:
                candidates.add(match.group("req").upper())
    if isinstance(requisition_text, str) and requisition_text.strip():
        for match in _REQUISITION_TEXT_PATTERN.finditer(requisition_text):
            candidates.add(match.group(1).upper())
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def _require_bounded_message_shape(raw_message: Mapping[str, Any]) -> None:
    if not isinstance(raw_message, Mapping):
        raise MalformedMessageError(
            "UNSUPPORTED_MESSAGE_STRUCTURE", "raw_message must be a mapping"
        )

    source = raw_message.get("source")
    if source not in SUPPORTED_SOURCES:
        raise MalformedMessageError(
            "UNSUPPORTED_SOURCE", f"unsupported or missing source: {source!r}"
        )

    source_message_id = raw_message.get("source_message_id")
    if not isinstance(source_message_id, str) or not source_message_id.strip():
        raise MalformedMessageError(
            "MISSING_SOURCE_MESSAGE_ID", "source_message_id must be a non-empty string"
        )

    observed_at = raw_message.get("observed_at")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise MalformedMessageError(
            "MISSING_OBSERVED_AT", "observed_at must be a non-empty ISO-8601 string"
        )
    try:
        parsed_observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MalformedMessageError(
            "INVALID_OBSERVED_AT", f"observed_at is not ISO-8601: {observed_at!r}"
        ) from exc
    if parsed_observed_at.tzinfo is None or parsed_observed_at.utcoffset() is None:
        raise MalformedMessageError(
            "INVALID_OBSERVED_AT",
            f"observed_at must include an explicit timezone offset: {observed_at!r}",
        )

    postings = raw_message.get("postings")
    if not isinstance(postings, Sequence) or isinstance(postings, (str, bytes)) or not postings:
        raise MalformedMessageError(
            "UNSUPPORTED_MESSAGE_STRUCTURE", "postings must be a non-empty list"
        )
    for posting in postings:
        if not isinstance(posting, Mapping):
            raise MalformedMessageError(
                "UNSUPPORTED_MESSAGE_STRUCTURE", "each posting must be a mapping"
            )


def _discovery_lead_id(source: str, source_message_id: str, ordinal: int) -> str:
    digest = hashlib.sha256(f"{source}|{source_message_id}|{ordinal}".encode("utf-8")).hexdigest()[:16]
    return f"LEAD_{digest.upper()}"


def extract_discovery_leads(raw_message: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return one validated DiscoveryLead record per posting in raw_message.

    Raises MalformedMessageError when the bounded raw-message shape is not
    met. Never raises for ambiguous/missing identity fields within an
    otherwise well-formed posting; those resolve to VERIFICATION_REQUIRED.
    """

    _require_bounded_message_shape(raw_message)

    source = raw_message["source"]
    source_message_id = raw_message["source_message_id"]
    source_thread_id = raw_message.get("source_thread_id")
    if source_thread_id is not None and not isinstance(source_thread_id, str):
        source_thread_id = None
    observed_at = raw_message["observed_at"]

    validator = build_draft202012_validator(DISCOVERY_LEAD_SCHEMA_PATH)

    leads: list[dict[str, Any]] = []
    for ordinal, posting in enumerate(raw_message["postings"]):
        employer_text = posting.get("employer_text")
        role_text = posting.get("role_text")
        requisition_text = posting.get("requisition_text")
        source_claims = posting.get("source_claims")
        if not isinstance(source_claims, Mapping):
            source_claims = {}
        raw_urls = posting.get("discovery_url")
        if isinstance(raw_urls, str):
            raw_urls = [raw_urls]
        discovery_urls = _normalize_discovery_urls(raw_urls)

        exact_employer_identity = _parse_exact_employer_identity(discovery_urls)
        exact_requisition_id = _parse_exact_requisition_id(discovery_urls, requisition_text)
        identity_resolution_status = (
            "RESOLVED"
            if exact_employer_identity and exact_requisition_id
            else "VERIFICATION_REQUIRED"
        )

        lead: dict[str, Any] = {
            "discovery_lead_id": _discovery_lead_id(source, source_message_id, ordinal),
            "source": source,
            "source_message_id": source_message_id,
            "source_thread_id": source_thread_id,
            "observed_at": observed_at,
            "discovery_urls": discovery_urls,
            "employer_text": employer_text if isinstance(employer_text, str) else None,
            "role_text": role_text if isinstance(role_text, str) else None,
            "requisition_text": requisition_text if isinstance(requisition_text, str) else None,
            "source_claims": dict(source_claims),
            "exact_employer_identity": exact_employer_identity,
            "exact_requisition_id": exact_requisition_id,
            "identity_resolution_status": identity_resolution_status,
        }

        validator.validate(lead)
        leads.append(lead)

    return leads
