"""Résumé module wording semantic checks (claim-bounded, not full NLP)."""

from __future__ import annotations

import re
from typing import Any, Mapping

from claim_semantic_guard import (
    _normalize,
    validate_claim_semantic_boundaries,
)


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


_DISTINCTIVE_SHORT_TOKENS = frozenset(
    {
        "bpmn",
        "ml",
        "qa",
        "uat",
        "gcp",
        "crm",
        "celonis",
        "uipath",
        "visio",
        "lucidchart",
        "lean",
        "sigma",
    }
)

_COMMON_FORBIDDEN_TOKENS = frozenset(
    {
        "process",
        "workflow",
        "mapping",
        "business",
        "enterprise",
        "formal",
        "modeling",
        "outcomes",
        "improvement",
        "quantified",
        "automated",
        "tools",
        "expertise",
        "leadership",
        "transformation",
        "organization",
        "wide",
        "telemetry",
        "mining",
        "diagram",
        "certification",
        "framework",
    }
)


def _significant_tokens(phrase: str) -> list[str]:
    return [
        token
        for token in re.split(r"[^\w]+", phrase)
        if token
        and (
            token in _DISTINCTIVE_SHORT_TOKENS
            or (len(token) >= 5 and token not in _COMMON_FORBIDDEN_TOKENS)
        )
    ]


def _forbidden_context_appears_in_wording(forbidden_context: str, wording: str) -> bool:
    phrase = _normalize(forbidden_context)
    wording_n = _normalize(wording)
    if not phrase or not wording_n:
        return False
    if phrase in wording_n:
        return True

    if "lean" in phrase and "six sigma" in phrase:
        if re.search(r"\blean\b", wording_n) and re.search(r"\bsix\s+sigma\b", wording_n):
            return True

    tokens = _significant_tokens(phrase)
    if not tokens:
        return False

    matched = [
        token
        for token in tokens
        if re.search(rf"\b{re.escape(token)}\b", wording_n)
    ]
    if len(matched) >= 2:
        return True
    if len(matched) == 1 and matched[0] in _DISTINCTIVE_SHORT_TOKENS:
        return True
    return False


def _cited_evidence_records(
    claim: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> list[dict[str, Any]]:
    cited: list[dict[str, Any]] = []
    evidence_ids = claim.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        return cited
    for evidence_id in evidence_ids:
        if not isinstance(evidence_id, str):
            continue
        record = evidence_index.get(evidence_id)
        if isinstance(record, Mapping):
            cited.append(dict(record))
    return cited


def validate_module_wording_semantics(
    module: Mapping[str, Any],
    *,
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Check module wording stays within cited Claim semantic boundaries."""
    module_id = module.get("module_id")
    wording = module.get("wording")
    claim_ids = module.get("claim_ids")

    errors: list[dict[str, Any]] = []
    if not isinstance(wording, str) or not wording.strip():
        return {
            "valid": False,
            "module_id": module_id,
            "errors": [
                _error("MISSING_MODULE_WORDING", module_id=module_id),
            ],
        }

    if not isinstance(claim_ids, list) or not claim_ids:
        return {
            "valid": False,
            "module_id": module_id,
            "errors": [
                _error("MISSING_CLAIM_LINEAGE", module_id=module_id),
            ],
        }

    for claim_id in claim_ids:
        if not isinstance(claim_id, str):
            continue
        claim = claim_index.get(claim_id)
        if not isinstance(claim, Mapping):
            errors.append(
                _error("MISSING_CLAIM_ID", module_id=module_id, claim_id=claim_id)
            )
            continue

        cited_records = _cited_evidence_records(claim, evidence_index)
        pseudo_claim = {
            "claim_id": claim_id,
            "wording": wording,
            "evidence_ids": claim.get("evidence_ids"),
            "evidence_state": claim.get("evidence_state"),
        }
        semantic_errors = validate_claim_semantic_boundaries(
            pseudo_claim, cited_records
        )
        for semantic_error in semantic_errors:
            errors.append(
                _error(
                    "RESUME_WORDING_SEMANTIC_VIOLATION",
                    module_id=module_id,
                    claim_id=claim_id,
                    underlying_code=semantic_error.get("code"),
                    rule_id=semantic_error.get("rule_id"),
                    matched_text=semantic_error.get("matched_text"),
                    detail=semantic_error.get("detail"),
                )
            )

        forbidden_contexts = claim.get("forbidden_contexts")
        claim_wording = str(claim.get("wording") or "")
        if isinstance(forbidden_contexts, list):
            for forbidden_context in forbidden_contexts:
                if not isinstance(forbidden_context, str):
                    continue
                if not _forbidden_context_appears_in_wording(forbidden_context, wording):
                    continue
                if _forbidden_context_appears_in_wording(
                    forbidden_context, claim_wording
                ):
                    continue
                errors.append(
                    _error(
                        "RESUME_FORBIDDEN_CONTEXT_LEAKAGE",
                        module_id=module_id,
                        claim_id=claim_id,
                        forbidden_context=forbidden_context,
                        detail=(
                            "module wording introduces a claim forbidden context "
                            "beyond approved claim wording"
                        ),
                    )
                )

    return {
        "valid": len(errors) == 0,
        "module_id": module_id,
        "errors": errors,
    }


def patch_contains_terminology_substitute(patch: Mapping[str, Any]) -> bool:
    operations = patch.get("operations")
    if not isinstance(operations, list):
        return False
    return any(
        isinstance(operation, Mapping)
        and operation.get("op") == "TERMINOLOGY_SUBSTITUTE"
        for operation in operations
    )
