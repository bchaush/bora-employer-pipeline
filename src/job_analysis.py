"""Job Analysis v1 — first vertical slice orchestrator.

Flow:
  job input + structured extraction
  → requirement normalization/classification
  → Evidence/Claim matching
  → gaps/unknowns
  → bounded lane/decision

Does not call paid model APIs. Structured extraction must be provided.
Does not generate résumés.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from claim_repository import validate_claim_repository
from evidence_repository import validate_evidence_repository
from experience_range import (
    evaluate_generic_experience_range,
    is_generic_experience_range_requirement,
)
from job_decision import decide_lane_and_decision
from job_id import generate_job_id
from requirement_match import infer_requirement_capabilities, match_requirements
from requirement_normalize import normalize_structured_requirements
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SCHEMA_PATH = ROOT / "schemas" / "job_analysis_result.schema.json"
REQUIREMENT_SCHEMA_PATH = ROOT / "schemas" / "requirement.schema.json"
EVIDENCE_MATCH_SCHEMA_PATH = ROOT / "schemas" / "evidence_match.schema.json"


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload = {"code": code}
    payload.update(fields)
    return payload


def _build_gaps_and_unknowns(
    requirements: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    match_by_req = {m["requirement_id"]: m for m in matches}
    gaps: list[str] = []
    unknowns: list[str] = []

    for requirement in requirements:
        req_id = requirement["requirement_id"]
        match = match_by_req.get(req_id)
        importance = requirement.get("importance")
        relevance = requirement.get("relevance")
        text = requirement.get("text")

        if match is None:
            if importance == "UNCLEAR" or relevance == "LOW":
                unknowns.append(f"{req_id}: no match produced ({text})")
            continue

        result = match.get("result")
        if result == "NONE" and importance == "MANDATORY" and relevance in {
            "HIGH",
            "MEDIUM",
        }:
            gaps.append(f"{req_id}: unsupported mandatory requirement - {text}")
        elif result == "NONE" and importance == "PREFERRED":
            gaps.append(f"{req_id}: preferred skill missing - {text}")
        elif result == "PARTIAL":
            note = match.get("transfer_note") or match.get("explanation")
            gaps.append(f"{req_id}: PARTIAL match - {text} ({note})")
        elif result == "UNKNOWN":
            unknowns.append(f"{req_id}: UNKNOWN match - {text}")
        elif importance == "UNCLEAR":
            unknowns.append(f"{req_id}: requirement importance UNCLEAR - {text}")

        # Seniority mismatch visibility
        sen = requirement.get("seniority_implication")
        if isinstance(sen, str) and any(
            token in sen.casefold()
            for token in ("senior", "staff", "principal", "lead")
        ):
            gaps.append(f"{req_id}: seniority mismatch signal - {sen}")

        # Unsupported technology visibility
        tech = requirement.get("technology")
        if isinstance(tech, list) and result == "NONE" and tech:
            gaps.append(
                f"{req_id}: unsupported technology {tech} for requirement - {text}"
            )

    # De-duplicate while preserving order.
    def _unique(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    return _unique(gaps), _unique(unknowns)


def analyze_job(
    job_input: Mapping[str, Any],
    *,
    claim_index: Optional[Mapping[str, Any]] = None,
    evidence_index: Optional[Mapping[str, Any]] = None,
    claim_root: Optional[Path] = None,
    evidence_root: Optional[Path] = None,
) -> dict[str, Any]:
    """Run the Job Analysis v1 vertical slice.

    Required job_input fields:
      - company (str)
      - role (str)
      - jd_text (str)
      - structured_extraction (mapping)  # AI/fixture-provided; not free-form parsing

    Optional:
      - fixture_key (str) for stable Job_ID
    """
    empty = {
        "valid": False,
        "analysis": None,
        "errors": [],
        "warnings": [],
    }

    if not isinstance(job_input, Mapping):
        empty["errors"].append(
            _error(
                "MALFORMED_JOB_INPUT",
                detail=f"job_input must be a mapping; got {type(job_input).__name__}",
            )
        )
        return empty

    company = job_input.get("company")
    role = job_input.get("role")
    jd_text = job_input.get("jd_text")
    if not isinstance(company, str) or not company.strip():
        empty["errors"].append(_error("MISSING_COMPANY", detail="company is required"))
    if not isinstance(role, str) or not role.strip():
        empty["errors"].append(_error("MISSING_ROLE", detail="role is required"))
    if not isinstance(jd_text, str) or not jd_text.strip():
        empty["errors"].append(_error("MISSING_JD_TEXT", detail="jd_text is required"))
    if empty["errors"]:
        return empty

    structured = job_input.get("structured_extraction")
    if structured is None:
        empty["errors"].append(
            _error(
                "EXTRACTION_REQUIRED",
                detail=(
                    "Job Analysis v1 requires structured_extraction. "
                    "Free-form JD parsing / paid model calls are out of scope."
                ),
            )
        )
        empty["warnings"].append("extraction_mode=EXTRACTION_REQUIRED")
        return empty

    fixture_key = job_input.get("fixture_key")
    job_id = generate_job_id(
        company=company,
        role=role,
        fixture_key=fixture_key if isinstance(fixture_key, str) else None,
    )

    # Load trusted indexes if not supplied.
    warnings: list[str] = []
    if evidence_index is None:
        evidence_result = validate_evidence_repository(evidence_root)
        if evidence_result.get("valid") is not True or evidence_result.get("index") is None:
            empty["errors"].append(
                _error(
                    "EVIDENCE_REPOSITORY_INVALID",
                    detail="trusted Evidence index unavailable",
                    evidence_errors=evidence_result.get("errors"),
                )
            )
            return empty
        evidence_index = evidence_result["index"]
    if claim_index is None:
        claim_result = validate_claim_repository(claim_root)
        if claim_result.get("valid") is not True or claim_result.get("index") is None:
            empty["errors"].append(
                _error(
                    "CLAIM_REPOSITORY_INVALID",
                    detail="trusted Claim index unavailable",
                    claim_errors=claim_result.get("errors"),
                )
            )
            return empty
        claim_index = claim_result["index"]

    normalized = normalize_structured_requirements(
        job_id=job_id,
        structured_extraction=structured,
    )
    if not normalized["valid"]:
        empty["errors"].extend(normalized["errors"])
        empty["warnings"].extend(normalized.get("warnings") or [])
        return empty
    warnings.extend(normalized.get("warnings") or [])

    requirements = normalized["requirements"]

    # EXPERIENCE_RANGE_SEMANTICS_V1: route GENERIC numeric experience-range
    # requirements (e.g. "0-2 years of work experience") to their own
    # narrow, honest evaluator instead of the generic capability matcher.
    # A requirement is routed here only when it names no technology, the
    # existing capability matcher recognizes nothing for it, and its text
    # is an exact match for a narrowly enumerated "years of work
    # experience" phrasing -- domain/platform-specific years requirements
    # (SAP, Salesforce, UAT, "customer-facing implementation experience",
    # etc.) are never routed and remain entirely owned by the unmodified
    # capability matcher below, including the closed named-platform
    # NONE_TRAPS protection. requirement_match.py itself is not modified.
    generic_range_requirements: list[dict[str, Any]] = []
    remaining_requirements: list[dict[str, Any]] = []
    for requirement in requirements:
        inferred_caps = infer_requirement_capabilities(requirement)
        if is_generic_experience_range_requirement(
            requirement, inferred_capabilities=inferred_caps
        ):
            generic_range_requirements.append(requirement)
        else:
            remaining_requirements.append(requirement)

    match_result = match_requirements(
        job_id=job_id,
        requirements=remaining_requirements,
        claim_index=claim_index,
        evidence_index=evidence_index,
    )
    if not match_result["valid"]:
        empty["errors"].extend(match_result["errors"])
        return empty

    experience_range_matches = [
        evaluate_generic_experience_range(
            job_id=job_id, requirement=requirement, match_index=index
        )
        for index, requirement in enumerate(generic_range_requirements)
    ]

    # Restore normalized-Requirement order (partitioning above splits the
    # single ordered `requirements` list in two): downstream consumers key
    # everything by requirement_id and are order-independent, but returning
    # `evidence_matches` in the same order as `requirements` keeps the two
    # arrays in deterministic external correspondence.
    combined_matches_by_req = {
        m["requirement_id"]: m
        for m in match_result["matches"] + experience_range_matches
    }
    matches = [
        combined_matches_by_req[requirement["requirement_id"]]
        for requirement in requirements
        if requirement["requirement_id"] in combined_matches_by_req
    ]
    gaps, unknowns = _build_gaps_and_unknowns(requirements, matches)

    decision = decide_lane_and_decision(
        requirements=requirements,
        matches=matches,
        gaps=gaps,
        unknowns=unknowns,
        seniority=normalized.get("seniority"),
        role_family=normalized.get("role_family"),
        role=role,
        jd_text=jd_text,
    )

    analysis = {
        "job_id": job_id,
        "company": company.strip(),
        "role": role.strip(),
        "role_family": normalized.get("role_family"),
        "seniority": normalized.get("seniority"),
        "requirements": requirements,
        "evidence_matches": matches,
        "gaps": gaps,
        "unknowns": unknowns,
        "lane": decision["lane"],
        "decision": decision["decision"],
        "warnings": warnings,
        "extraction_mode": "STRUCTURED_EXTRACTION_PROVIDED",
        "decision_rationale": decision["decision_rationale"],
    }

    # Schema-validate nested requirement + match records already validated;
    # validate top-level analysis shape.
    analysis_validator = build_draft202012_validator(ANALYSIS_SCHEMA_PATH)
    analysis_errors = [err.message for err in analysis_validator.iter_errors(analysis)]
    if analysis_errors:
        empty["errors"].append(
            _error("JOB_ANALYSIS_SCHEMA_INVALID", details=analysis_errors)
        )
        return empty

    # Nested requirement schema gate (defense in depth).
    req_validator = build_draft202012_validator(REQUIREMENT_SCHEMA_PATH)
    for requirement in requirements:
        req_errors = [err.message for err in req_validator.iter_errors(requirement)]
        if req_errors:
            empty["errors"].append(
                _error(
                    "REQUIREMENT_SCHEMA_INVALID",
                    requirement_id=requirement.get("requirement_id"),
                    details=req_errors,
                )
            )
    match_validator = build_draft202012_validator(EVIDENCE_MATCH_SCHEMA_PATH)
    for match in matches:
        match_errors = [err.message for err in match_validator.iter_errors(match)]
        if match_errors:
            empty["errors"].append(
                _error(
                    "EVIDENCE_MATCH_SCHEMA_INVALID",
                    match_id=match.get("match_id"),
                    details=match_errors,
                )
            )
    if empty["errors"]:
        return empty

    return {
        "valid": True,
        "analysis": analysis,
        "errors": [],
        "warnings": warnings,
        "hard_blockers": decision.get("hard_blockers") or [],
    }
