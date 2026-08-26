"""Deterministic claim → evidence lineage validation.

Answers only whether every Evidence_ID referenced by a claim exists exactly
in the provided evidence index and whether basic lineage integrity holds.

Claim-level validation schema-checks only cited evidence records. Unrelated
repository records do not invalidate the claim. Matching is exact and
case-sensitive.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Optional, Sequence, Union

from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
CLAIM_SCHEMA_PATH = ROOT / "schemas" / "claim.schema.json"
EVIDENCE_SCHEMA_PATH = ROOT / "schemas" / "evidence.schema.json"

EvidenceIndexInput = Union[
    Mapping[str, Any],
    Sequence[Any],
]


def _empty_result(claim_id: Any = None) -> dict[str, Any]:
    return {
        "valid": False,
        "claim_id": claim_id,
        "resolved_evidence_ids": [],
        "missing_evidence_ids": [],
        "duplicate_evidence_ids": [],
        "errors": [],
    }


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _schema_error_messages(validator: Any, instance: Any) -> list[str]:
    return [error.message for error in validator.iter_errors(instance)]


def normalize_evidence_index(
    evidence_index: EvidenceIndexInput,
    *,
    cited_evidence_ids: Optional[Iterable[str]] = None,
) -> tuple[dict[str, Mapping[str, Any]] | None, list[dict[str, Any]]]:
    """Normalize an evidence mapping or sequence into an exact-ID index.

    When cited_evidence_ids is provided, only those IDs are retained for claim
    validation. Unrelated malformed records are ignored. Sequence-wide
    duplicate Evidence_IDs still fail closed.

    Returns (index, errors). index is None when normalization fails closed.
    """
    errors: list[dict[str, Any]] = []
    cited: set[str] | None
    if cited_evidence_ids is None:
        cited = None
    else:
        cited = {evidence_id for evidence_id in cited_evidence_ids}

    if evidence_index is None:
        errors.append(
            _error(
                "MALFORMED_EVIDENCE_INDEX",
                detail="evidence_index is null",
            )
        )
        return None, errors

    if isinstance(evidence_index, (str, bytes)):
        errors.append(
            _error(
                "MALFORMED_EVIDENCE_INDEX",
                detail="evidence_index must be a mapping or sequence of records",
            )
        )
        return None, errors

    if isinstance(evidence_index, Mapping):
        index: dict[str, Mapping[str, Any]] = {}
        for key, value in evidence_index.items():
            if cited is not None and key not in cited:
                # Unrelated repository records do not affect this claim.
                continue

            if not isinstance(key, str) or key == "":
                errors.append(
                    _error(
                        "MALFORMED_EVIDENCE_INDEX",
                        detail="evidence_index keys must be non-empty strings",
                    )
                )
                return None, errors
            if not isinstance(value, Mapping):
                errors.append(
                    _error(
                        "MALFORMED_EVIDENCE_INDEX",
                        detail=(
                            "evidence_index values must be mappings; "
                            f"invalid value for key {key!r}"
                        ),
                        evidence_id=key,
                    )
                )
                return None, errors

            record_id = value.get("evidence_id")
            if record_id is not None and record_id != key:
                errors.append(
                    _error(
                        "MALFORMED_EVIDENCE_INDEX",
                        detail=(
                            "evidence_index key does not exactly match "
                            f"record evidence_id: key={key!r} "
                            f"evidence_id={record_id!r}"
                        ),
                        evidence_id=key,
                    )
                )
                return None, errors

            index[key] = value
        return index, errors

    if isinstance(evidence_index, Sequence):
        index = {}
        seen_ids: set[str] = set()
        for position, item in enumerate(evidence_index):
            if not isinstance(item, Mapping):
                if cited is None:
                    errors.append(
                        _error(
                            "MALFORMED_EVIDENCE_INDEX",
                            detail=(
                                "evidence_index sequence items must be mappings; "
                                f"invalid item at position {position}"
                            ),
                        )
                    )
                    return None, errors
                # Unidentifiable malformed item cannot be attributed to a cited
                # Evidence_ID; ignore for claim-scoped validation.
                continue

            evidence_id = item.get("evidence_id")
            if not isinstance(evidence_id, str) or evidence_id == "":
                if cited is None:
                    errors.append(
                        _error(
                            "MALFORMED_EVIDENCE_INDEX",
                            detail=(
                                "evidence records must include a non-empty string "
                                f"evidence_id; invalid item at position {position}"
                            ),
                        )
                    )
                    return None, errors
                continue

            if evidence_id in seen_ids:
                errors.append(
                    _error(
                        "DUPLICATE_EVIDENCE_ID_IN_INDEX",
                        evidence_id=evidence_id,
                    )
                )
                return None, errors
            seen_ids.add(evidence_id)

            if cited is not None and evidence_id not in cited:
                continue

            index[evidence_id] = item
        return index, errors

    errors.append(
        _error(
            "MALFORMED_EVIDENCE_INDEX",
            detail=(
                "evidence_index must be a mapping or sequence of records; "
                f"got {type(evidence_index).__name__}"
            ),
        )
    )
    return None, errors


def validate_claim_lineage(
    claim: Any,
    evidence_index: EvidenceIndexInput,
    *,
    validate_schemas: bool = True,
) -> dict[str, Any]:
    """Validate exact Evidence_ID lineage for one claim against an evidence index.

    Parameters
    ----------
    claim:
        Claim record mapping. Expected to already be schema-valid, but malformed
        input still fails closed.
    evidence_index:
        Either a mapping of evidence_id -> evidence record, or a sequence of
        evidence records. IDs are matched exactly and case-sensitively.
    validate_schemas:
        When True, the claim and *cited* evidence records are checked against
        the approved Draft 2020-12 schemas.
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
    result["claim_id"] = claim_id if isinstance(claim_id, str) else None

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
            # Continue collecting lineage-specific failures when possible.

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

    seen: MutableMapping[str, int] = {}
    duplicate_evidence_ids: list[str] = []
    ordered_unique_ids: list[str] = []

    for item in evidence_ids:
        if not isinstance(item, str) or item == "":
            result["errors"].append(
                _error(
                    "MALFORMED_EVIDENCE_ID",
                    detail="each Evidence_ID must be a non-empty string",
                    evidence_id=item,
                )
            )
            continue

        if item in seen:
            seen[item] += 1
            if item not in duplicate_evidence_ids:
                duplicate_evidence_ids.append(item)
        else:
            seen[item] = 1
            ordered_unique_ids.append(item)

    result["duplicate_evidence_ids"] = list(duplicate_evidence_ids)
    for evidence_id in duplicate_evidence_ids:
        result["errors"].append(
            _error(
                "DUPLICATE_EVIDENCE_ID",
                evidence_id=evidence_id,
            )
        )

    index, index_errors = normalize_evidence_index(
        evidence_index,
        cited_evidence_ids=ordered_unique_ids,
    )
    result["errors"].extend(index_errors)
    if index is None:
        return result

    missing_evidence_ids: list[str] = []
    resolved_evidence_ids: list[str] = []

    for evidence_id in ordered_unique_ids:
        if evidence_id in index:
            resolved_evidence_ids.append(evidence_id)
        else:
            missing_evidence_ids.append(evidence_id)
            result["errors"].append(
                _error(
                    "MISSING_EVIDENCE_ID",
                    evidence_id=evidence_id,
                )
            )

    result["resolved_evidence_ids"] = resolved_evidence_ids
    result["missing_evidence_ids"] = missing_evidence_ids

    if validate_schemas:
        evidence_validator = build_draft202012_validator(EVIDENCE_SCHEMA_PATH)
        for evidence_id in resolved_evidence_ids:
            record = index[evidence_id]
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

    result["valid"] = (
        len(result["errors"]) == 0
        and len(missing_evidence_ids) == 0
        and len(duplicate_evidence_ids) == 0
        and len(resolved_evidence_ids) == len(ordered_unique_ids)
        and len(ordered_unique_ids) > 0
    )
    return result
