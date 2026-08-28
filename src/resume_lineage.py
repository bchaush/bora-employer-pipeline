"""Deterministic résumé module lineage validation against Claim/Evidence indexes."""

from __future__ import annotations

from typing import Any, Mapping

from claim_validation import validate_claim


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def validate_resume_module_lineage(
    module: Mapping[str, Any],
    *,
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    require_resume_context: bool = True,
) -> dict[str, Any]:
    """Validate Claim/Evidence lineage for one résumé module."""
    module_id = module.get("module_id")
    claim_ids = module.get("claim_ids")
    evidence_ids = module.get("evidence_ids")

    errors: list[dict[str, Any]] = []

    if not isinstance(claim_ids, list) or not claim_ids:
        errors.append(
            _error(
                "MISSING_CLAIM_LINEAGE",
                module_id=module_id,
                detail="factual résumé modules require at least one Claim_ID",
            )
        )
        return {"valid": False, "module_id": module_id, "errors": errors}

    resolved_evidence: set[str] = set()
    for claim_id in claim_ids:
        if not isinstance(claim_id, str):
            errors.append(
                _error("MALFORMED_CLAIM_ID", module_id=module_id, claim_id=claim_id)
            )
            continue
        claim = claim_index.get(claim_id)
        if not isinstance(claim, Mapping):
            errors.append(
                _error("MISSING_CLAIM_ID", module_id=module_id, claim_id=claim_id)
            )
            continue
        claim_result = validate_claim(claim, evidence_index)
        if not claim_result.get("reusable"):
            errors.append(
                _error(
                    "CLAIM_NOT_REUSABLE",
                    module_id=module_id,
                    claim_id=claim_id,
                    detail="module may only cite approved reusable claims",
                )
            )
        if require_resume_context:
            allowed = claim.get("allowed_contexts")
            if isinstance(allowed, list) and "resume" not in allowed:
                errors.append(
                    _error(
                        "CLAIM_RESUME_CONTEXT_FORBIDDEN",
                        module_id=module_id,
                        claim_id=claim_id,
                    )
                )
        cited = claim.get("evidence_ids")
        if isinstance(cited, list):
            for eid in cited:
                if isinstance(eid, str):
                    resolved_evidence.add(eid)

    if isinstance(evidence_ids, list):
        for eid in evidence_ids:
            if not isinstance(eid, str):
                continue
            if eid not in evidence_index:
                errors.append(
                    _error(
                        "MISSING_EVIDENCE_ID",
                        module_id=module_id,
                        evidence_id=eid,
                    )
                )
            elif eid not in resolved_evidence:
                errors.append(
                    _error(
                        "EVIDENCE_LINEAGE_MISMATCH",
                        module_id=module_id,
                        evidence_id=eid,
                        detail="evidence_id not derived from cited claims",
                    )
                )
    else:
        errors.append(
            _error(
                "MISSING_EVIDENCE_LINEAGE",
                module_id=module_id,
                detail="evidence_ids required for audit lineage",
            )
        )

    return {
        "valid": len(errors) == 0,
        "module_id": module_id,
        "errors": errors,
    }
