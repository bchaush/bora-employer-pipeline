"""MANUAL_DISCOVERY_V1: bounded manual URL/screenshot nomination adapter.

No browser, OCR, screenshot parsing, network, Gmail, or Google Sheets I/O
occurs here. The operator/provider layer supplies one already-structured
manual nomination. This adapter converts it into the exact bounded observation
shape consumed by discovery_lead.extract_discovery_leads and
supervised_ingestion.process_batch.

Manual observations remain untrusted discovery provenance. They never become
Employer Truth, Match Truth, Pursuit Truth, or package authority here.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from job_url_format import is_allowed_job_url  # noqa: E402
from production_ledger import empty_state  # noqa: E402
from supervised_ingestion import process_batch  # noqa: E402


MANUAL_SOURCES = frozenset({"MANUAL_URL", "MANUAL_SCREENSHOT"})


class MalformedManualDiscoveryError(ValueError):
    """Stable fail-closed error for malformed manual nominations."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def _stable_source_message_id(source: str, source_reference: str) -> str:
    digest = hashlib.sha256(
        f"{source}|{source_reference}".encode("utf-8")
    ).hexdigest()[:20]
    return f"{source}_{digest.upper()}"


def _normalize_urls(
    source: str,
    discovery_url: str | Sequence[str] | None,
) -> list[str]:
    if discovery_url is None:
        urls: list[Any] = []
    elif isinstance(discovery_url, str):
        urls = [discovery_url]
    elif isinstance(discovery_url, Sequence) and not isinstance(
        discovery_url, (str, bytes)
    ):
        urls = list(discovery_url)
    else:
        raise MalformedManualDiscoveryError(
            "INVALID_DISCOVERY_URL",
            "discovery_url must be a string, a sequence of strings, or null",
        )

    normalized: list[str] = []
    for value in urls:
        if (
            not isinstance(value, str)
            or not value.strip()
            or not is_allowed_job_url(value.strip())
        ):
            raise MalformedManualDiscoveryError(
                "INVALID_DISCOVERY_URL",
                f"manual discovery URL is not an allowed absolute http/https job URL: {value!r}",
            )
        candidate = value.strip()
        if candidate not in normalized:
            normalized.append(candidate)

    if source == "MANUAL_URL" and len(normalized) != 1:
        raise MalformedManualDiscoveryError(
            "MANUAL_URL_REQUIRED",
            "MANUAL_URL intake requires exactly one allowed discovery URL",
        )

    return normalized


def build_manual_discovery_observation(
    *,
    source: str,
    observed_at: str,
    discovery_url: str | Sequence[str] | None = None,
    source_reference: str | None = None,
    employer_text: str | None = None,
    role_text: str | None = None,
    requisition_text: str | None = None,
    source_claims: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one bounded observation for the existing discovery conveyor.

    MANUAL_URL derives stable source identity from the exact supplied URL.
    MANUAL_SCREENSHOT requires an opaque stable source_reference supplied by
    the provider/operator boundary (for example a screenshot content hash or
    private-board item reference). Screenshot bytes are never parsed or stored.
    """

    if source not in MANUAL_SOURCES:
        raise MalformedManualDiscoveryError(
            "UNSUPPORTED_MANUAL_SOURCE",
            f"manual source must be one of {sorted(MANUAL_SOURCES)}, got {source!r}",
        )

    if not isinstance(observed_at, str) or not observed_at.strip():
        raise MalformedManualDiscoveryError(
            "MISSING_OBSERVED_AT",
            "observed_at must be a non-empty ISO-8601 string",
        )

    urls = _normalize_urls(source, discovery_url)

    if source == "MANUAL_URL":
        stable_reference = urls[0]
    else:
        if not isinstance(source_reference, str) or not source_reference.strip():
            raise MalformedManualDiscoveryError(
                "MISSING_SOURCE_REFERENCE",
                "MANUAL_SCREENSHOT requires a stable opaque source_reference",
            )
        stable_reference = source_reference.strip()

    if source_claims is None:
        claims: dict[str, Any] = {}
    elif isinstance(source_claims, Mapping):
        claims = dict(source_claims)
    else:
        raise MalformedManualDiscoveryError(
            "INVALID_SOURCE_CLAIMS",
            "source_claims must be a mapping or null",
        )

    if source == "MANUAL_SCREENSHOT":
        # Preserve the operator/provider-supplied opaque reference as untrusted
        # discovery provenance. It is never Employer Truth or canonical identity.
        claims["manual_source_reference"] = stable_reference

    return {
        "source": source,
        "source_message_id": _stable_source_message_id(source, stable_reference),
        "source_thread_id": None,
        "observed_at": observed_at,
        "postings": [
            {
                "employer_text": employer_text,
                "role_text": role_text,
                "requisition_text": requisition_text,
                "discovery_url": urls,
                "source_claims": claims,
            }
        ],
    }


def process_manual_nomination(
    *,
    existing_state: Mapping[str, Any] | None,
    run_id: str,
    processed_at: str,
    source: str,
    observed_at: str,
    discovery_url: str | Sequence[str] | None = None,
    source_reference: str | None = None,
    employer_text: str | None = None,
    role_text: str | None = None,
    requisition_text: str | None = None,
    source_claims: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Send one manual nomination through the existing Slice-1 conveyor."""

    observation = build_manual_discovery_observation(
        source=source,
        observed_at=observed_at,
        discovery_url=discovery_url,
        source_reference=source_reference,
        employer_text=employer_text,
        role_text=role_text,
        requisition_text=requisition_text,
        source_claims=source_claims,
    )

    return process_batch(
        [observation],
        existing_state if existing_state is not None else empty_state(),
        run_id=run_id,
        processed_at=processed_at,
    )
