"""Unified deterministic claim validation gate.

Orchestrates, in order:
1. claim schema validation
2. lineage validation (claim_lineage) — cited Evidence_IDs only
3. evidence-state compatibility (claim_state_validation) — cited only
4. semantic boundary guard (claim_semantic_guard) — cited Evidence only
5. context-conflict check (allowed vs forbidden)
6. reusability / approval gate

Does not pre-validate the full evidence repository. Unrelated repository
records do not invalidate a claim. Does not mutate records or invent
fallback values.

Downstream requested-context consumption (forcing use only inside
allowed_contexts / outside forbidden_contexts at résumé render time) is
intentionally deferred until a résumé/application consumer exists.
Self-conflict of allowed ∩ forbidden remains enforced here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from claim_lineage import (
    EvidenceIndexInput,
    normalize_evidence_index,
    validate_claim_lineage,
)
from claim_semantic_guard import validate_claim_semantic_boundaries
from claim_state_validation import validate_claim_evidence_state_compatibility
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
CLAIM_SCHEMA_PATH = ROOT / "schemas" / "claim.schema.json"

# State-validator codes that block reusable use but do not, by themselves,
# make an archival claim record invalid.
REUSABILITY_ONLY_STATE_CODES = frozenset({"CLAIM_STATE_NOT_REUSABLE"})

REUSABLE_CLAIM_STATES = frozenset({"VERIFIED", "SUPPORTED", "OBSERVED"})
NON_REUSABLE_CLAIM_STATES = frozenset({"UNKNOWN", "CONTRADICTED"})


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _warning(code: str, **fields: Any) -> dict[str, Any]:
    return _error(code, **fields)


def _schema_error_messages(validator: Any, instance: Any) -> list[str]:
    return [error.message for error in validator.iter_errors(instance)]


def _empty_result(claim_id: Any = None) -> dict[str, Any]:
    return {
        "valid_record": False,
        "reusable": False,
        "claim_id": claim_id,
        "schema_valid": False,
        "lineage_valid": False,
        "state_valid": False,
        "human_approved": False,
        "errors": [],
        "warnings": [],
    }


def _context_conflicts(claim: Mapping[str, Any]) -> list[str]:
    allowed = claim.get("allowed_contexts")
    forbidden = claim.get("forbidden_contexts")
    if not isinstance(allowed, list) or not isinstance(forbidden, list):
        return []

    allowed_set = {item for item in allowed if isinstance(item, str)}
    forbidden_set = {item for item in forbidden if isinstance(item, str)}
    overlap = allowed_set.intersection(forbidden_set)
    return sorted(overlap)


def validate_claim(
    claim: Any,
    evidence_index: EvidenceIndexInput,
) -> dict[str, Any]:
    """Run the full deterministic claim validation pipeline.

    Returns
    -------
    dict
        valid_record:
            Structurally/lineage/state coherent enough to retain as a record.
            Archival UNKNOWN/CONTRADICTED claims may be valid_record while
            remaining non-reusable.
        reusable:
            Safe for downstream résumé/network/interview generation.
    """
    result = _empty_result()

    # ------------------------------------------------------------------
    # 1. CLAIM SCHEMA VALIDATION
    # ------------------------------------------------------------------
    if not isinstance(claim, Mapping):
        result["errors"].append(
            _error(
                "MALFORMED_CLAIM",
                detail=f"claim must be a mapping; got {type(claim).__name__}",
            )
        )
        return result

    claim_id = claim.get("claim_id")
    result["claim_id"] = claim_id if isinstance(claim_id, str) else None

    human_approval = claim.get("human_approval")
    result["human_approved"] = human_approval is True

    claim_state = claim.get("evidence_state")

    claim_validator = build_draft202012_validator(CLAIM_SCHEMA_PATH)
    claim_schema_errors = _schema_error_messages(claim_validator, claim)
    if claim_schema_errors:
        result["schema_valid"] = False
        result["errors"].append(
            _error(
                "CLAIM_SCHEMA_INVALID",
                details=claim_schema_errors,
            )
        )
    else:
        result["schema_valid"] = True

    # ------------------------------------------------------------------
    # 2. LINEAGE VALIDATION (cited Evidence_IDs only; includes cited schema)
    # ------------------------------------------------------------------
    lineage_result = validate_claim_lineage(
        claim,
        evidence_index,
        validate_schemas=True,
    )

    lineage_specific_errors: list[dict[str, Any]] = []
    for lineage_error in lineage_result.get("errors", []):
        # Claim schema was already evaluated in stage 1.
        if lineage_error.get("code") == "CLAIM_SCHEMA_INVALID":
            continue
        lineage_specific_errors.append(dict(lineage_error))
        result["errors"].append(dict(lineage_error))

    result["lineage_valid"] = (
        len(lineage_specific_errors) == 0
        and not lineage_result.get("missing_evidence_ids")
        and not lineage_result.get("duplicate_evidence_ids")
        and bool(lineage_result.get("resolved_evidence_ids"))
    )

    # ------------------------------------------------------------------
    # 3. STATE COMPATIBILITY (cited Evidence_IDs only)
    # ------------------------------------------------------------------
    state_result = validate_claim_evidence_state_compatibility(
        claim,
        evidence_index,
        validate_schemas=True,
    )

    blocking_state_errors: list[dict[str, Any]] = []
    for state_error in state_result.get("errors", []):
        code = state_error.get("code")
        if code in REUSABILITY_ONLY_STATE_CODES:
            result["warnings"].append(dict(state_error))
            continue

        # Skip codes already reported by schema/lineage stages.
        if code in {
            "CLAIM_SCHEMA_INVALID",
            "EVIDENCE_SCHEMA_INVALID",
            "MISSING_EVIDENCE_ID",
            "DUPLICATE_EVIDENCE_ID",
            "MALFORMED_EVIDENCE_INDEX",
            "DUPLICATE_EVIDENCE_ID_IN_INDEX",
            "EMPTY_EVIDENCE_IDS",
            "MISSING_EVIDENCE_IDS",
            "MALFORMED_EVIDENCE_IDS",
            "MALFORMED_EVIDENCE_ID",
            "MALFORMED_CLAIM",
        }:
            continue

        blocking_state_errors.append(dict(state_error))
        result["errors"].append(dict(state_error))

    if result["schema_valid"] and result["lineage_valid"]:
        result["state_valid"] = len(blocking_state_errors) == 0
    else:
        result["state_valid"] = False

    # ------------------------------------------------------------------
    # 4. SEMANTIC BOUNDARY GUARD (cited Evidence only)
    # ------------------------------------------------------------------
    cited_ids: list[str] = []
    raw_ids = claim.get("evidence_ids")
    if isinstance(raw_ids, list):
        cited_ids = [item for item in raw_ids if isinstance(item, str)]

    cited_index, _index_errors = normalize_evidence_index(
        evidence_index,
        cited_evidence_ids=cited_ids,
    )
    cited_records: list[Mapping[str, Any]] = []
    if cited_index is not None:
        for evidence_id in cited_ids:
            record = cited_index.get(evidence_id)
            if isinstance(record, Mapping):
                cited_records.append(record)

    semantic_errors = validate_claim_semantic_boundaries(claim, cited_records)
    semantic_blocking: list[dict[str, Any]] = []
    for semantic_error in semantic_errors:
        code = semantic_error.get("code")
        if code == "MALFORMED_CLAIM":
            # Already reported in schema/malformed stage when applicable.
            continue
        semantic_blocking.append(dict(semantic_error))
        result["errors"].append(dict(semantic_error))

    semantic_valid = len(semantic_blocking) == 0

    # ------------------------------------------------------------------
    # 5. CONTEXT CONFLICT (allowed ∩ forbidden)
    # ------------------------------------------------------------------
    conflicting_contexts = _context_conflicts(claim)
    context_conflict = len(conflicting_contexts) > 0
    if context_conflict:
        result["errors"].append(
            _error(
                "CONTEXT_CONFLICT",
                contexts=conflicting_contexts,
                detail=(
                    "the same context appears in allowed_contexts and "
                    "forbidden_contexts; contexts are not silently removed"
                ),
            )
        )

    # ------------------------------------------------------------------
    # 6. REUSABILITY / APPROVAL GATE
    # ------------------------------------------------------------------
    # Context conflict blocks reusable use but does not erase an otherwise
    # coherent archival/valid record. Semantic boundary failures invalidate
    # the record (fail closed) and therefore block reusable use.
    result["valid_record"] = (
        result["schema_valid"]
        and result["lineage_valid"]
        and result["state_valid"]
        and semantic_valid
    )

    if result["valid_record"]:
        if human_approval is not True:
            result["warnings"].append(
                _warning(
                    "NOT_HUMAN_APPROVED",
                    detail=(
                        "human_approval must be true for reusable approved "
                        "claim use"
                    ),
                )
            )

        if claim_state in NON_REUSABLE_CLAIM_STATES:
            if not any(
                warning.get("code") == "CLAIM_STATE_NOT_REUSABLE"
                for warning in result["warnings"]
            ):
                result["warnings"].append(
                    _warning(
                        "CLAIM_STATE_NOT_REUSABLE",
                        claim_state=claim_state,
                        detail=(
                            f"claim evidence_state {claim_state} may be "
                            "retained as an archival record but is never "
                            "reusable"
                        ),
                    )
                )

    result["reusable"] = (
        result["valid_record"]
        and human_approval is True
        and isinstance(claim_state, str)
        and claim_state in REUSABLE_CLAIM_STATES
        and not context_conflict
    )

    return result
