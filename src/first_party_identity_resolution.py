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
from urllib.parse import parse_qsl, unquote, urlparse

SRC_PATH = Path(__file__).resolve().parent
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from discovery_lead import (  # noqa: E402
    _parse_exact_employer_identity as _slice1_ats_employer_identity,
    _parse_exact_requisition_id as _slice1_ats_requisition_id,
)
from exact_role_identity import resolve_exact_role_key  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REQUEST_SCHEMA_PATH = ROOT / "schemas" / "first_party_identity_resolution.schema.json"

ENGINE_BASELINE = "SUPERVISED_PRODUCTION_V1_FIRST_PARTY_IDENTITY_RESOLUTION_V1"

# F7: known third-party discovery-platform hosts. Deterministic host check only;
# never treated as authoritative first-party Official_URL evidence.
THIRD_PARTY_DISCOVERY_HOSTS = frozenset(
    {
        "linkedin.com",
        "lnkd.in",
        "indeed.com",
        "joinhandshake.com",
        "handshake.com",
        "simplify.jobs",
    }
)

# Identifier evidence and discovery URLs need different boundary semantics:
# evidence rejects composite continuations, while URL slugs commonly delimit IDs
# with hyphens/underscores/dots.
_COMPOSITE_ID_SEPARATORS = frozenset(".-_/\\\u2010\u2011\u2012\u2013\u2014\u2015")


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


def _token_bounded_contains(haystack: str, token: str) -> bool:
    """Return True only for an exact evidence identifier, not a composite fragment."""

    normalized_token = _normalized_evidence_text(token)
    if not normalized_token:
        return False
    normalized_haystack = _normalized_evidence_text(haystack)
    start = 0
    while True:
        index = normalized_haystack.find(normalized_token, start)
        if index < 0:
            return False
        left = index - 1
        right = index + len(normalized_token)

        def _continues(position: int, direction: int) -> bool:
            if position < 0 or position >= len(normalized_haystack):
                return False
            char = normalized_haystack[position]
            if char.isalnum() or char == "_":
                return True
            if char in _COMPOSITE_ID_SEPARATORS:
                adjacent = position + direction
                return (
                    0 <= adjacent < len(normalized_haystack)
                    and normalized_haystack[adjacent].isalnum()
                )
            return False

        if not _continues(left, -1) and not _continues(right, 1):
            return True
        start = index + 1


def _bounded_unquote(value: str, *, rounds: int = 5) -> str:
    """Repeatedly percent-decode with a hard bound so encoded IDs cannot hide."""

    decoded = value
    for _ in range(rounds):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def _url_contains_identifier(url: str, identifier: str) -> bool:
    """URL slugs may delimit a platform ID with punctuation such as '-' or '_'."""

    normalized_identifier = _normalized_evidence_text(identifier)
    normalized_url = _normalized_evidence_text(_bounded_unquote(url))
    if not normalized_identifier:
        return False
    pattern = re.compile(
        rf"(?<![a-z0-9]){re.escape(normalized_identifier)}(?![a-z0-9])"
    )
    return pattern.search(normalized_url) is not None


def _source_claim_contains_identifier(value: Any, identifier: str) -> bool:
    if isinstance(value, Mapping):
        # A platform ID can be stashed as a mapping KEY (e.g.
        # {"<id>": True}) just as easily as a value; both must be scanned so
        # neither position becomes an undetected bypass.
        return any(
            _source_claim_contains_identifier(key, identifier)
            or _source_claim_contains_identifier(child, identifier)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_source_claim_contains_identifier(child, identifier) for child in value)
    if isinstance(value, str):
        # A platform ID may appear in source_claims either as an exact
        # evidence-style token or delimited within a URL/slug (e.g.
        # "LI-<id>", a full job-posting URL); both boundary styles must
        # be checked so neither encoding becomes an undetected bypass.
        return _token_bounded_contains(value, identifier) or _url_contains_identifier(
            value, identifier
        )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric_text = (
            str(int(value))
            if isinstance(value, float) and value.is_integer()
            else str(value)
        )
        return numeric_text.casefold() == identifier.strip().casefold()
    return False


# Bounds how many rounds of embedded-URL discovery/percent-decoding are
# followed for one discovery URL (e.g. a Gmail/Google redirect wrapper
# nesting another wrapper); prevents pathological/adversarial nesting from
# causing unbounded work.
_MAX_EMBEDDED_URL_DECODE_ROUNDS = 5


def _iter_embedded_urls(url: str) -> list[str]:
    """Yield `url` plus bounded decoded/nested http(s) URL candidates.

    Redirect services may hide a destination in query values, percent-encoded
    path text, or wrapper-specific path syntax. Every decoded http(s) suffix is
    inspected so platform provenance cannot disappear behind the outer host.
    """

    seen: set[str] = {url}
    candidates: list[str] = [url]
    frontier = [url]
    for _ in range(_MAX_EMBEDDED_URL_DECODE_ROUNDS):
        if not frontier:
            break
        next_frontier: list[str] = []
        for candidate in frontier:
            decoded_candidate = _bounded_unquote(candidate, rounds=1)
            extracted: list[str] = []
            if decoded_candidate != candidate:
                extracted.append(decoded_candidate)
            for match in re.finditer(r"https?:[/\\]*", decoded_candidate, re.IGNORECASE):
                extracted.append(
                    _browser_normalize_special_url(decoded_candidate[match.start():])
                )
            try:
                parsed_candidate = urlparse(
                    _browser_normalize_special_url(decoded_candidate)
                )
                query_pairs = parse_qsl(parsed_candidate.query, keep_blank_values=True)
            except ValueError:
                query_pairs = []
            for _, raw_value in query_pairs:
                decoded_value = _bounded_unquote(raw_value, rounds=1)
                if re.match(r"^https?:", decoded_value, re.IGNORECASE):
                    extracted.append(_browser_normalize_special_url(decoded_value))
            for decoded_url in extracted:
                normalized_url = _browser_normalize_special_url(decoded_url)
                if normalized_url not in seen:
                    seen.add(normalized_url)
                    candidates.append(normalized_url)
                    next_frontier.append(normalized_url)
        frontier = next_frontier
    return candidates


def _provenance_contains_platform_identifier(
    provenance: Mapping[str, Any], identifier: str
) -> bool:
    source_claims = provenance.get("source_claims")
    if _source_claim_contains_identifier(source_claims, identifier):
        return True
    discovery_urls = provenance.get("discovery_urls")
    if not isinstance(discovery_urls, list):
        return False
    for url in discovery_urls:
        if not isinstance(url, str):
            continue
        for candidate in _iter_embedded_urls(url):
            if (
                _official_url_third_party_host(candidate) not in (None, "__invalid_host__")
                and _url_contains_identifier(candidate, identifier)
            ):
                return True
    return False


_SPECIAL_SCHEME_RE = re.compile(r"^(https?):", re.IGNORECASE)


def _browser_normalize_special_url(url: str) -> str:
    """Normalize backslash/slash authority-separator forms to their
    WHATWG-equivalent canonical form for special (http/https) schemes.

    Real browsers (and employer-site link resolution) collapse any run of
    leading '/'/'\\' immediately after the scheme colon into one authority
    boundary, then treat every remaining '\\' exactly like '/'. A naive
    `.replace("\\", "/")` does not reproduce this: a leading "://\\" becomes
    ":///" (an extra empty path segment) instead of the browser's "://",
    which makes `urlparse` return hostname=None for an otherwise
    well-formed, browser-parseable authority.
    """

    match = _SPECIAL_SCHEME_RE.match(url)
    if not match:
        return url
    scheme = match.group(1)
    rest = url[match.end():]
    after_slashes = rest.lstrip("/\\")
    if len(after_slashes) == len(rest):
        # WHATWG special schemes also treat "https:host/path" as an
        # authority-bearing absolute URL.
        after_slashes = rest
    return f"{scheme}://{after_slashes.replace(chr(92), '/')}"


def _canonical_http_host(parsed: Any) -> tuple[str | None, int | None]:
    """Return a browser-equivalent canonical ASCII host and parsed port."""

    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return None, None
    if not hostname:
        return None, port
    try:
        decoded_host = unicodedata.normalize("NFKC", unquote(hostname)).lower()
        # WHATWG domain/host parsing rejects these code points. Percent
        # decoding must not be allowed to introduce authority delimiters that
        # then pass through IDNA as if they were ordinary hostname text.
        if any(
            ord(char) <= 0x20 or char in '#/:<>?@[\\]^|'
            for char in decoded_host
        ):
            return None, port
        canonical_host = decoded_host.rstrip(".").encode("idna").decode("ascii")
    except (UnicodeError, ValueError):
        return None, port
    return canonical_host, port


def _ats_identity_url(official_url: str) -> str:
    """Return canonical browser-equivalent scheme/authority/path for ATS parsing."""

    normalized = _browser_normalize_special_url(official_url)
    try:
        parsed = urlparse(normalized)
    except ValueError:
        return normalized
    hostname, port = _canonical_http_host(parsed)
    if hostname is None:
        return normalized
    default_port = 443 if parsed.scheme.lower() == "https" else 80
    netloc = hostname if port in (None, default_port) else f"{hostname}:{port}"
    return parsed._replace(netloc=netloc, query="", fragment="").geturl()


def _official_url_third_party_host(official_url: str) -> str | None:
    """F7: fail closed if the outer URL or any embedded destination is third-party."""

    for index, candidate in enumerate(_iter_embedded_urls(official_url)):
        try:
            parsed_candidate = urlparse(_browser_normalize_special_url(candidate))
        except ValueError:
            return "__invalid_host__"
        hostname, _ = _canonical_http_host(parsed_candidate)
        if not hostname:
            return "__invalid_host__"
        for denied_host in THIRD_PARTY_DISCOVERY_HOSTS:
            if hostname == denied_host or hostname.endswith(f".{denied_host}"):
                return denied_host
    return None


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

    # Durable discovery provenance is untrusted input. A malformed outer or
    # embedded URL must fail this request closed instead of escaping urlparse
    # and aborting the surrounding batch.
    for discovery_url in provenance.get("discovery_urls") or []:
        if (
            isinstance(discovery_url, str)
            and _official_url_third_party_host(discovery_url) == "__invalid_host__"
        ):
            return {
                "outcome": "PROCESSING_ERROR",
                "error_code": "DISCOVERY_URL_UNPARSEABLE",
                "errors": ["discovery provenance contains an unparseable URL"],
                "resolution_fingerprint": fingerprint,
                "discovery_lead_id": lead_id,
                "operational_job_id": None,
                "discovery_provenance": provenance,
                "first_party_observation": dict(first_party),
            }

    observed_at = first_party.get("observed_at")
    first_party_observed_at = _aware_datetime(observed_at)
    if first_party_observed_at is None:
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "FIRST_PARTY_OBSERVED_AT_INVALID",
            "errors": ["first_party_observation.observed_at must include an explicit timezone offset"],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
        }

    # A posting cannot have been first-party-verified before it was even
    # discovered; an earlier first-party timestamp is temporally impossible.
    discovery_observed_at = _aware_datetime(provenance["observed_at"])
    assert discovery_observed_at is not None
    if first_party_observed_at < discovery_observed_at:
        return {
            "outcome": "VERIFICATION_REQUIRED",
            "error_code": "FIRST_PARTY_OBSERVED_AT_PRECEDES_DISCOVERY",
            "errors": [],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
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

    discovery_employer_text = provenance["employer_text"]
    observed_employer_name = first_party["observed_employer_name"]
    assert isinstance(observed_employer_name, str)
    if _normalize_exact_text(discovery_employer_text) != _normalize_exact_text(observed_employer_name):
        return {
            "outcome": "VERIFICATION_REQUIRED",
            "error_code": "EMPLOYER_BINDING_CONTRADICTS_DISCOVERY",
            "errors": [
                "first_party_observation.observed_employer_name contradicts the discovery lead's employer_text"
            ],
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

    # Canonical exact-role keys must never diverge merely because the supplied
    # requisition uses a compatibility Unicode representation.
    if unicodedata.normalize("NFKC", exact_requisition_id) != exact_requisition_id:
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "EXACT_REQUISITION_ID_NON_CANONICAL",
            "errors": ["exact_requisition_id must already be in canonical NFKC form"],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    official_url = first_party["official_url"]
    assert isinstance(official_url, str)
    ats_identity_url = _ats_identity_url(official_url)
    ats_qualified_employer_identity = _slice1_ats_employer_identity([ats_identity_url])

    discovery_exact_employer = provenance.get("exact_employer_identity")
    if isinstance(discovery_exact_employer, str) and discovery_exact_employer.strip():
        if ats_qualified_employer_identity is not None:
            ats_bare_employer = ats_qualified_employer_identity.split(":", 1)[-1]
            allowed_ats_employer_forms = {
                _normalize_exact_text(ats_qualified_employer_identity),
                _normalize_exact_text(ats_bare_employer),
            }
            discovery_employer_matches = (
                _normalize_exact_text(discovery_exact_employer)
                in allowed_ats_employer_forms
            )
            supplied_employer_matches = (
                _normalize_exact_text(exact_employer_identity)
                in allowed_ats_employer_forms
            )
            discovery_employer_contradiction = not (
                discovery_employer_matches and supplied_employer_matches
            )
        else:
            discovery_employer_contradiction = (
                _normalize_exact_text(discovery_exact_employer)
                != _normalize_exact_text(exact_employer_identity)
            )
        if discovery_employer_contradiction:
            return {
                "outcome": "VERIFICATION_REQUIRED",
                "error_code": "DISCOVERY_EXACT_EMPLOYER_CONTRADICTION",
                "errors": [],
                "resolution_fingerprint": fingerprint,
                "discovery_lead_id": lead_id,
                "operational_job_id": None,
                "discovery_provenance": provenance,
                "first_party_observation": dict(first_party),
            }

    discovery_exact_requisition = provenance.get("exact_requisition_id")
    if (
        isinstance(discovery_exact_requisition, str)
        and discovery_exact_requisition.strip()
        and not _provenance_contains_platform_identifier(
            provenance, discovery_exact_requisition
        )
        and _normalize_exact_text(discovery_exact_requisition)
        != _normalize_exact_text(exact_requisition_id)
    ):
        return {
            "outcome": "VERIFICATION_REQUIRED",
            "error_code": "DISCOVERY_EXACT_REQUISITION_CONTRADICTION",
            "errors": [],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    if _provenance_contains_platform_identifier(provenance, exact_requisition_id):
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

    if not _token_bounded_contains(evidence, exact_requisition_id):
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

    official_url = first_party["official_url"]
    assert isinstance(official_url, str)
    third_party_host = _official_url_third_party_host(official_url)
    if third_party_host is not None:
        error_message = (
            "official_url does not resolve to a usable authoritative host"
            if third_party_host == "__invalid_host__"
            else (
                f"official_url host '{third_party_host}' is a known third-party discovery "
                "platform, not an authoritative first-party source"
            )
        )
        return {
            "outcome": "PROCESSING_ERROR",
            "error_code": "OFFICIAL_URL_THIRD_PARTY_HOST_FORBIDDEN",
            "errors": [error_message],
            "resolution_fingerprint": fingerprint,
            "discovery_lead_id": lead_id,
            "operational_job_id": None,
            "discovery_provenance": provenance,
            "first_party_observation": dict(first_party),
        }

    # The same exact ATS posting must converge onto Slice-1's own
    # ATS-qualified employer namespace. ATS parsing uses only the normalized
    # scheme/authority/path, never query or fragment text.
    if ats_qualified_employer_identity is not None:
        ats_bare_employer = ats_qualified_employer_identity.split(":", 1)[-1]
        allowed_ats_employer_forms = {
            _normalize_exact_text(ats_qualified_employer_identity),
            _normalize_exact_text(ats_bare_employer),
        }
        for candidate_label, candidate_value in (
            ("exact_employer_identity", exact_employer_identity),
            ("discovery exact_employer_identity", discovery_exact_employer),
        ):
            if (
                isinstance(candidate_value, str)
                and candidate_value.strip()
                and _normalize_exact_text(candidate_value)
                not in allowed_ats_employer_forms
            ):
                return {
                    "outcome": "VERIFICATION_REQUIRED",
                    "error_code": "ATS_EMPLOYER_IDENTITY_CONTRADICTION",
                    "errors": [
                        f"URL-derived ATS employer identity '{ats_qualified_employer_identity}' "
                        f"conflicts with supplied {candidate_label} '{candidate_value}'"
                    ],
                    "resolution_fingerprint": fingerprint,
                    "discovery_lead_id": lead_id,
                    "operational_job_id": None,
                    "discovery_provenance": provenance,
                    "first_party_observation": dict(first_party),
                }

        # Discovery text is provenance, not ATS URL identity authority. Only
        # the authoritative Official_URL may establish an ATS requisition.
        ats_derived_requisition_id = _slice1_ats_requisition_id(
            [ats_identity_url], None
        )
        if (
            ats_derived_requisition_id is not None
            and _normalize_exact_text(ats_derived_requisition_id)
            != _normalize_exact_text(exact_requisition_id)
        ):
            return {
                "outcome": "VERIFICATION_REQUIRED",
                "error_code": "ATS_REQUISITION_ID_CONTRADICTION",
                "errors": [
                    f"URL-derived ATS requisition ID '{ats_derived_requisition_id}' conflicts "
                    f"with supplied exact_requisition_id '{exact_requisition_id}'"
                ],
                "resolution_fingerprint": fingerprint,
                "discovery_lead_id": lead_id,
                "operational_job_id": None,
                "discovery_provenance": provenance,
                "first_party_observation": dict(first_party),
            }

    operational_job_id = resolve_exact_role_key(
        ats_qualified_employer_identity or exact_employer_identity,
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
