"""Deterministic http/https URL checks for job official_url and discovery_url.

stdlib-only. Intended for reuse by smoke tests and future production validators.
Registered against jsonschema format name "job-url" (not the environment's
built-in "uri" checker). Only absolute http/https URLs with a non-empty host
are accepted. Embedded credentials and literal whitespace/control characters
are rejected. Valid percent-encoded characters remain allowed.
"""

from __future__ import annotations

from urllib.parse import urlparse

from jsonschema import FormatChecker


ALLOWED_JOB_URL_SCHEMES = frozenset({"http", "https"})
JOB_URL_FORMAT_NAME = "job-url"


def _contains_whitespace_or_control(value: str) -> bool:
    for char in value:
        codepoint = ord(char)
        if char.isspace() or codepoint < 32 or codepoint == 127:
            return True
    return False


def is_allowed_job_url(instance: object) -> bool:
    """Return True when instance is an allowed job URL, or not a string.

    Non-string values return True so null remains governed by the schema type
    union (string | null). String values must be absolute http/https URLs with
    a non-empty host, no embedded username/password, and no literal whitespace
    or control characters.
    """
    if not isinstance(instance, str):
        return True

    if _contains_whitespace_or_control(instance):
        return False

    parsed = urlparse(instance)
    scheme = parsed.scheme.lower()
    if scheme not in ALLOWED_JOB_URL_SCHEMES:
        return False

    # Require a real host. Empty netloc rejects http://, mailto:, javascript:, etc.
    if not parsed.netloc or parsed.hostname is None or parsed.hostname == "":
        return False

    # Reject embedded credentials such as https://user:pass@host/...
    if parsed.username is not None or parsed.password is not None:
        return False

    return True


def build_job_format_checker() -> FormatChecker:
    """Build a FormatChecker with the shared job URL rule registered as job-url."""
    format_checker = FormatChecker()
    format_checker.checks(JOB_URL_FORMAT_NAME)(is_allowed_job_url)
    return format_checker
