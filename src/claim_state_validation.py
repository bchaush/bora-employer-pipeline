"""Deterministic claim evidence_state compatibility validation.

Validates whether a claim's declared evidence_state is compatible with the
evidence_state values of the records it cites.

Does not rewrite or upgrade claim/evidence records. Does not treat
human_approval as an override. Matching of Evidence_IDs remains exact and
case-sensitive via claim_lineage.normalize_evidence_index.

Only cited evidence records are inspected. Unrelated repository records do
not affect claim-level state compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from claim_lineage import EvidenceIndexInput, normalize_evidence_index
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
CLAIM_SCHEMA_PATH = ROOT / "schemas" / "claim.schema.json"
EVIDENCE_SCHEMA_PATH = ROOT / "schemas" / "evidence.schema.json"

LOCKED_EVIDENCE_STATES = frozenset(
    {
        "VERIFIED",
        "SUPPORTED",
        "OBSERVED",
        "UNKNOWN",
        "CONTRADICTED",
    }
)

# Claim states that may pass compatibility checks, and the cited evidence
# states each may legally reference. CONTRADICTED is never allowed as a cited
# support state. A claim declared CONTRADICTED cannot pass this validator.
ALLOWED_CITED_STATES_BY_CLAIM_STATE = {
    "VERIFIED": frozenset({"VERIFIED"}),
    "SUPPORTED": frozenset({"VERIFIED", "SUPPORTED"}),
    "OBSERVED": frozenset({"VERIFIED", "SUPPORTED", "OBSERVED"}),
    "UNKNOWN": frozenset({"VERIFIED", "SUPPORTED", "OBSERVED", "UNKNOWN"}),
}


def _empty_result(
    claim_id: Any = None,
    claim_state: Any = None,
) -> dict[str, Any]:
    return {
        "valid": False,
        "claim_id": claim_id,
        "claim_state": claim_state,
        "cited_states": {},
        "errors": [],
    }


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _schema_error_messages(validator: Any, instance: Any) -> list[str]:
    return [error.message for error in validator.iter_errors(instance)]


def validate_claim_evidence_state_compatibility(
    claim: Any,
    evidence_index: EvidenceIndexInput,
    *,
    validate_schemas: bool = True,
) -> dict[str, Any]:
    """Validate claim evidence_state against cited evidence record states.

    Rules
    -----
    - Any cited CONTRADICTED evidence fails.
    - UNKNOWN evidence cannot support VERIFIED/SUPPORTED/OBSERVED claims.
    - VERIFIED claim requires all cited evidence VERIFIED.
    - SUPPORTED claim may cite VERIFIED or SUPPORTED only.
    - OBSERVED claim may cite VERIFIED, SUPPORTED, or OBSERVED.
    - UNKNOWN claim may cite any non-CONTRADICTED state.
    - human_approval never overrides incompatible states.
    """
    result = _empty_result()

    if not isinstance(claim, Mapping):
        result["errors"].append(
            _error(
                "MALFORMED_CLAIM",
                detail=f"claim must be a mapping; got {type(claim).__name__}",
            )
        )
        return result

    claim_id = claim.get("claim_id")
    claim_state = claim.get("evidence_state")
    result["claim_id"] = claim_id if isinstance(claim_id, str) else None
    result["claim_state"] = claim_state if isinstance(claim_state, str) else None

    if validate_schemas:
        claim_validator = build_draft202012_validator(CLAIM_SCHEMA_PATH)
        claim_schema_errors = _schema_error_messages(claim_validator, claim)
        if claim_schema_errors:
            result["errors"].append(
                _error(
                    "CLAIM_SCHEMA_INVALID",
                    details=claim_schema_errors,
                )
            )

    if not isinstance(claim_state, str) or claim_state not in LOCKED_EVIDENCE_STATES:
        result["errors"].append(
            _error(
                "MALFORMED_CLAIM_STATE",
                detail=(
                    "claim.evidence_state must be one of the locked evidence "
                    f"states; got {claim_state!r}"
                ),
            )
        )
        # Continue only if we can still inspect citations.

    evidence_ids = claim.get("evidence_ids")
    if evidence_ids is None:
        result["errors"].append(
            _error(
                "MISSING_EVIDENCE_IDS",
                detail="claim.evidence_ids is missing",
            )
        )
        return result

    if not isinstance(evidence_ids, list):
        result["errors"].append(
            _error(
                "MALFORMED_EVIDENCE_IDS",
                detail=(
                    "claim.evidence_ids must be a list; "
                    f"got {type(evidence_ids).__name__}"
                ),
            )
        )
        return result

    if len(evidence_ids) == 0:
        result["errors"].append(
            _error(
                "EMPTY_EVIDENCE_IDS",
                detail="claim.evidence_ids must contain at least one Evidence_ID",
            )
        )
        return result

    ordered_unique_ids: list[str] = []
    seen_ids: set[str] = set()
    for item in evidence_ids:
        if not isinstance(item, str) or item == "":
            result["errors"].append(
                _error(
                    "MALFORMED_EVIDENCE_ID",
                    detail="each Evidence_ID must be a non-empty string",
                    evidence_id=item,
                )
            )
            return result
        if item in seen_ids:
            result["errors"].append(
                _error(
                    "DUPLICATE_EVIDENCE_ID",
                    evidence_id=item,
                )
            )
            continue
        seen_ids.add(item)
        ordered_unique_ids.append(item)

    index, index_errors = normalize_evidence_index(
        evidence_index,
        cited_evidence_ids=ordered_unique_ids,
    )
    result["errors"].extend(index_errors)
    if index is None:
        return result

    cited_states: dict[str, str] = {}
    missing_ids: list[str] = []

    for evidence_id in ordered_unique_ids:
        record = index.get(evidence_id)
        if record is None:
            missing_ids.append(evidence_id)
            result["errors"].append(
                _error(
                    "MISSING_EVIDENCE_ID",
                    evidence_id=evidence_id,
                )
            )
            continue

        if validate_schemas:
            evidence_validator = build_draft202012_validator(EVIDENCE_SCHEMA_PATH)
            evidence_schema_errors = _schema_error_messages(
                evidence_validator,
                record,
            )
            if evidence_schema_errors:
                result["errors"].append(
                    _error(
                        "EVIDENCE_SCHEMA_INVALID",
                        evidence_id=evidence_id,
                        details=evidence_schema_errors,
                    )
                )
                continue

        evidence_state = record.get("evidence_state")
        if (
            not isinstance(evidence_state, str)
            or evidence_state not in LOCKED_EVIDENCE_STATES
        ):
            result["errors"].append(
                _error(
                    "MALFORMED_EVIDENCE_STATE",
                    evidence_id=evidence_id,
                    detail=(
                        "evidence.evidence_state must be one of the locked "
                        f"evidence states; got {evidence_state!r}"
                    ),
                )
            )
            continue

        cited_states[evidence_id] = evidence_state

    result["cited_states"] = cited_states

    if missing_ids:
        # Cannot prove compatibility without exact lineage.
        result["valid"] = False
        return result

    if claim_state == "CONTRADICTED":
        result["errors"].append(
            _error(
                "CLAIM_STATE_NOT_REUSABLE",
                detail=(
                    "a claim declared CONTRADICTED cannot pass evidence-state "
                    "compatibility validation for reusable claim use"
                ),
            )
        )
        result["valid"] = False
        return result

    allowed_cited_states = ALLOWED_CITED_STATES_BY_CLAIM_STATE.get(claim_state)
    if allowed_cited_states is None:
        # Already reported malformed claim state when applicable.
        result["valid"] = False
        return result

    for evidence_id, evidence_state in cited_states.items():
        if evidence_state == "CONTRADICTED":
            result["errors"].append(
                _error(
                    "CONTRADICTED_EVIDENCE",
                    evidence_id=evidence_id,
                    evidence_state=evidence_state,
                    claim_state=claim_state,
                    detail=(
                        "CONTRADICTED evidence can never support an approved "
                        "reusable claim"
                    ),
                )
            )
            continue

        if evidence_state not in allowed_cited_states:
            result["errors"].append(
                _error(
                    "INCOMPATIBLE_EVIDENCE_STATE",
                    evidence_id=evidence_id,
                    evidence_state=evidence_state,
                    claim_state=claim_state,
                    allowed_cited_states=sorted(allowed_cited_states),
                    detail=(
                        f"claim state {claim_state} is not compatible with "
                        f"cited evidence state {evidence_state}"
                    ),
                )
            )

    # human_approval is intentionally ignored as an override signal.
    # Presence/absence may exist on the claim but never relaxes state rules.

    result["valid"] = len(result["errors"]) == 0 and len(cited_states) > 0
    return result
