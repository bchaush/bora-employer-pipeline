"""Deterministic Job_ID generation for analysis inputs."""

from __future__ import annotations

import hashlib
import re


def _slug(value: str, *, max_len: int = 32) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().upper()).strip("_")
    if not cleaned:
        return "UNKNOWN"
    return cleaned[:max_len]


def generate_job_id(
    *,
    company: str,
    role: str,
    fixture_key: str | None = None,
) -> str:
    """Return a stable Job_ID.

    Prefer an explicit fixture_key when provided (test/dev fixtures).
    Otherwise derive a short deterministic hash from company + role.
    """
    if isinstance(fixture_key, str) and fixture_key.strip():
        return f"JOB_{_slug(fixture_key, max_len=48)}"

    digest = hashlib.sha256(
        f"{company.strip().casefold()}|{role.strip().casefold()}".encode("utf-8")
    ).hexdigest()[:10].upper()
    return f"JOB_{_slug(company, max_len=16)}_{_slug(role, max_len=16)}_{digest}"
