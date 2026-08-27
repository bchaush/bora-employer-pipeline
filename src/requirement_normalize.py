"""Deterministic requirement normalization and importance classification.

Accepts a structured extraction payload (AI or fixture-provided) and
validates/normalizes it against the requirement schema.

Does not call an LLM. Does not invent requirements from free-form JD prose.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT_SCHEMA_PATH = ROOT / "schemas" / "requirement.schema.json"

_MANDATORY_CUES = re.compile(
    r"\b(?:must|minimum|need to|needs to|essential)\b|"
    r"(?<!not )\b(?:required|mandatory)\b",
    re.IGNORECASE,
)
_PREFERRED_CUES = re.compile(
    r"\b(?:preferred|nice to have|bonus|plus|optional|ideally|"
    r"ideal candidate)\b",
    re.IGNORECASE,
)
# Clause-scoped preferred + negated mandatory status (P-1 / R-1).
_PREFERRED_NOT_REQUIRED = re.compile(
    r"\bpreferred\b(?:[\w\s,/+\-]{0,64}?)\b(?:"
    r"but\s+not\s+required|"
    r"although\s+not\s+required|"
    r"though\s+not\s+required|"
    r"but\s+not\s+mandatory|"
    r"although\s+not\s+mandatory|"
    r"though\s+not\s+mandatory"
    r")\b"
    r"|"
    r"\bpreferred\b(?:[\w\s,/+\-]{0,24}?);\s*not\s+(?:required|mandatory)\b"
    r"|"
    r"\bnot\s+(?:required|mandatory)\b(?:[\w\s,/+\-]{0,32}?)\bbut\b(?:[\w\s,/+\-]{0,16}?)\bpreferred\b",
    re.IGNORECASE,
)
_NOISE_CUES = re.compile(
    r"\b(?:competitive benefits|equal opportunity|eeo|fast[- ]paced|"
    r"team player|self[- ]starter|passion for|thrives in|"
    r"culture fit|positive attitude)\b",
    re.IGNORECASE,
)
_SUBSTANTIVE_CUES = re.compile(
    r"\b(?:sql|python|java|salesforce|degree|bachelor|master|phd|"
    r"years?|experience|certif|cloud|aws|azure|analyst|engineer|"
    r"uat|csv|regulatory|security clearance|citizen)\b",
    re.IGNORECASE,
)


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload = {"code": code}
    payload.update(fields)
    return payload


def _split_clauses(text: str) -> list[str]:
    parts = re.split(r"[;\n]|(?<=\.)\s+", text)
    return [part.strip() for part in parts if part and part.strip()]


def _classify_clause(clause: str) -> str:
    """Classify one clause. Preferred-not-required is PREFERRED at clause scope."""
    if _PREFERRED_NOT_REQUIRED.search(clause):
        return "PREFERRED"
    has_pref = bool(_PREFERRED_CUES.search(clause))
    has_mand = bool(_MANDATORY_CUES.search(clause))
    if has_pref and has_mand:
        return "MIXED"
    if has_pref:
        return "PREFERRED"
    if has_mand:
        return "MANDATORY"
    return "OTHER"


def classify_importance_from_source(
    source_text: str,
    *,
    proposed: str | None = None,
    category: str | None = None,
) -> str:
    """Conservative importance classification from source wording.

    Mixed mandatory+preferred clauses about different credentials/skills
    return UNCLEAR rather than silently choosing PREFERRED.
    Preferred-not-required cues are evaluated per clause (R-1), not whole-text.
    HR/culture noise remains UNCLEAR even when prefixed with \"must\".
    """
    text = source_text if isinstance(source_text, str) else ""

    if category == "HR_NOISE":
        return "UNCLEAR"

    # Noise-dominant statements (culture/HR) stay UNCLEAR even with "must".
    if _NOISE_CUES.search(text) and not _SUBSTANTIVE_CUES.search(text):
        return "UNCLEAR"

    clauses = _split_clauses(text)
    if not clauses:
        clauses = [text]

    if len(clauses) >= 2:
        clause_labels = [_classify_clause(clause) for clause in clauses]
        unique = {label for label in clause_labels if label in {"MANDATORY", "PREFERRED"}}
        if "MIXED" in clause_labels or unique == {"MANDATORY", "PREFERRED"}:
            return "UNCLEAR"
        if unique == {"PREFERRED"}:
            return "PREFERRED"
        if unique == {"MANDATORY"}:
            return "MANDATORY"

    # Single clause (or all OTHER).
    label = _classify_clause(clauses[0] if len(clauses) == 1 else text)
    if label == "PREFERRED":
        return "PREFERRED"
    if label == "MANDATORY":
        return "MANDATORY"
    if label == "MIXED":
        return "UNCLEAR"

    has_pref = bool(_PREFERRED_CUES.search(text))
    has_mand = bool(_MANDATORY_CUES.search(text))
    if has_pref and not has_mand:
        return "PREFERRED"
    if has_pref and has_mand:
        return "UNCLEAR"
    if has_mand:
        return "MANDATORY"

    if proposed in {"MANDATORY", "PREFERRED", "UNCLEAR"}:
        return proposed
    return "UNCLEAR"


def normalize_structured_requirements(
    *,
    job_id: str,
    structured_extraction: Any,
) -> dict[str, Any]:
    """Validate and normalize a structured requirement extraction payload."""
    result: dict[str, Any] = {
        "valid": False,
        "job_id": job_id,
        "requirements": [],
        "role_family": None,
        "seniority": None,
        "errors": [],
        "warnings": [],
    }

    if not isinstance(structured_extraction, Mapping):
        result["errors"].append(
            _error(
                "MALFORMED_STRUCTURED_EXTRACTION",
                detail=(
                    "structured_extraction must be a mapping; "
                    f"got {type(structured_extraction).__name__}"
                ),
            )
        )
        return result

    role_family = structured_extraction.get("role_family")
    seniority = structured_extraction.get("seniority")
    result["role_family"] = role_family if isinstance(role_family, str) else None
    result["seniority"] = seniority if isinstance(seniority, str) else None

    raw_requirements = structured_extraction.get("requirements")
    if not isinstance(raw_requirements, list):
        result["errors"].append(
            _error(
                "MALFORMED_REQUIREMENTS",
                detail="structured_extraction.requirements must be a list",
            )
        )
        return result

    validator = build_draft202012_validator(REQUIREMENT_SCHEMA_PATH)
    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for index, item in enumerate(raw_requirements):
        if not isinstance(item, Mapping):
            result["errors"].append(
                _error(
                    "MALFORMED_REQUIREMENT",
                    index=index,
                    detail=f"requirement must be a mapping; got {type(item).__name__}",
                )
            )
            continue

        requirement = dict(item)
        requirement["job_id"] = job_id

        req_id = requirement.get("requirement_id")
        if not isinstance(req_id, str) or not req_id.strip():
            result["errors"].append(
                _error(
                    "MISSING_REQUIREMENT_ID",
                    index=index,
                    detail="requirement_id is required and must be a non-empty string",
                )
            )
            continue

        if req_id in seen_ids:
            result["errors"].append(
                _error(
                    "DUPLICATE_REQUIREMENT_ID",
                    requirement_id=req_id,
                    detail=f"requirement_id {req_id!r} appears more than once",
                )
            )
            continue
        seen_ids.add(req_id)

        source_text = requirement.get("source_text")
        proposed = requirement.get("importance")
        if proposed is not None and proposed not in {
            "MANDATORY",
            "PREFERRED",
            "UNCLEAR",
        }:
            result["errors"].append(
                _error(
                    "REQUIREMENT_SCHEMA_INVALID",
                    requirement_id=req_id,
                    details=[
                        f"importance {proposed!r} is not one of "
                        "['MANDATORY', 'PREFERRED', 'UNCLEAR']"
                    ],
                )
            )
            continue

        category = requirement.get("category")
        if isinstance(source_text, str):
            requirement["importance"] = classify_importance_from_source(
                source_text,
                proposed=proposed if isinstance(proposed, str) else None,
                category=category if isinstance(category, str) else None,
            )
        elif category == "HR_NOISE":
            requirement["importance"] = "UNCLEAR"

        if requirement.get("technology") is None:
            requirement["technology"] = []

        schema_errors = [err.message for err in validator.iter_errors(requirement)]
        if schema_errors:
            result["errors"].append(
                _error(
                    "REQUIREMENT_SCHEMA_INVALID",
                    requirement_id=req_id,
                    details=schema_errors,
                )
            )
            continue

        if (
            requirement.get("category") == "HR_NOISE"
            and requirement.get("importance") == "UNCLEAR"
        ):
            result["warnings"].append(
                f"Skipped non-material HR noise requirement {req_id}"
            )
            continue

        normalized.append(requirement)

    if result["errors"]:
        result["valid"] = False
        result["requirements"] = []
        return result

    normalized.sort(key=lambda item: item["requirement_id"])
    result["requirements"] = normalized
    result["valid"] = True
    return result
