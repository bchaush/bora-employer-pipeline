"""SUPERVISED_PRODUCTION_V1_SLICE_1: canonical exact-role identity resolution.

This module is intentionally independent of src/job_id.py. It has no
`company`/`role` parameters and cannot produce or select a canonical
operational JOBS entity from fuzzy title/company text, a hash of
company+role, or a discovery URL alone. The only accepted inputs are the
exact employer/application-system identity and the exact requisition/
opportunity identifier already deterministically parsed by
discovery_lead.py. If either is missing, identity stays unresolved.
"""

from __future__ import annotations


def resolve_exact_role_key(
    exact_employer_identity: str | None,
    exact_requisition_id: str | None,
) -> str | None:
    """Return the canonical exact-role key, or None when unresolved.

    Both inputs must be non-empty strings. No fuzzy merge, normalization
    beyond whitespace/case, or fallback surrogate key is permitted here.
    """

    if not isinstance(exact_employer_identity, str) or not exact_employer_identity.strip():
        return None
    if not isinstance(exact_requisition_id, str) or not exact_requisition_id.strip():
        return None

    employer = exact_employer_identity.strip().upper()
    requisition = exact_requisition_id.strip().upper()
    return f"{employer}::{requisition}"
