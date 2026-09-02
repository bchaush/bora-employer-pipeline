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
from job_decision import apply_posting_state_routing, decide_lane_and_decision
from job_id import generate_job_id
from requirement_match import infer_requirement_capabilities, match_requirements
from requirement_normalize import normalize_structured_requirements
from requirement_source_role import (
    CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN,
    derive_human_review_required,
    derive_qualification_gate,
    is_covered_by_citizenship_clearance_consumer,
)
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SCHEMA_PATH = ROOT / "schemas" / "job_analysis_result.schema.json"
REQUIREMENT_SCHEMA_PATH = ROOT / "schemas" / "requirement.schema.json"
EVIDENCE_MATCH_SCHEMA_PATH = ROOT / "schemas" / "evidence_match.schema.json"


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload = {"code": code}
    payload.update(fields)
    return payload


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _build_gaps_and_unknowns(
    requirements: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """`gaps`/`unknowns` -- a compatibility-name ALIAS for
    `qualification_gaps`/`qualification_unknowns` (same list objects; see
    analyze_job()). Their pre-SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1
    content is NOT preserved byte-for-byte: a ROLE_RESPONSIBILITY/AMBIGUOUS/
    APPLICATION_OR_LEGAL_GATE requirement is now explicitly excluded and
    must never be described here as an "unsupported mandatory requirement"
    or any other qualification-deficiency phrasing -- see
    _build_responsibility_views for its non-deficiency-framed output
    instead. Only requirements whose derived qualification_gate is YES
    participate. UNMIGRATED_EXTRACTION_AND_GOLDEN_COMPLETION_V1: a
    requirement with a missing/null/invalid source_semantic_role derives
    qualification_gate=AMBIGUOUS, never YES -- it does NOT participate here
    either (its ordinary canonical-artifact path is stopped even earlier,
    at requirement_normalize.py's ingestion gate, before this function ever
    runs; only a direct low-level caller that bypasses that gate could
    reach this function with such a row, and even then it is excluded, not
    silently gated).
    """
    match_by_req = {m["requirement_id"]: m for m in matches}
    gaps: list[str] = []
    unknowns: list[str] = []

    for requirement in requirements:
        if derive_qualification_gate(requirement.get("source_semantic_role")) != "YES":
            continue

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

    return _unique(gaps), _unique(unknowns)


def _build_responsibility_views(
    requirements: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """responsibility_observations / responsibility_evidence_unknowns
    (SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1).

    Every ROLE_RESPONSIBILITY or AMBIGUOUS requirement is preserved here
    with its already-established match result and cited evidence/claim
    information, never phrased as a candidate-entry deficiency. Each
    observation additionally carries capability_inference_state, a
    structured, matcher-bounded distinction between three genuinely
    different epistemic states -- NO_CAPABILITIES_INFERRED (the matcher
    never recognized any capability concept in this text at all; a much
    weaker "no evidence" claim than the next state),
    CAPABILITIES_INFERRED_NO_APPROVED_MATCH (capabilities were recognized
    and compared against approved Claims, with no match found), or
    APPROVED_MATCH_ESTABLISHED (a STRONG/SUPPORTED/PARTIAL match exists).
    A row with no cited evidence_ids/claim_ids at all (result NONE or
    UNKNOWN) is additionally surfaced in responsibility_evidence_unknowns,
    using explicitly matcher-bounded wording ("no established current
    approved match for this responsibility") -- never claiming no
    adjacent evidence exists, that the candidate lacks the capability, or
    that this is a development need or qualification gap. This module
    does not implement the global NONE-vs-UNKNOWN correction; it only
    ensures a responsibility row's current, bounded match state is never
    overstated.
    """
    match_by_req = {m["requirement_id"]: m for m in matches}
    observations: list[dict[str, Any]] = []
    evidence_unknowns: list[str] = []

    for requirement in requirements:
        role = requirement.get("source_semantic_role")
        if role not in ("ROLE_RESPONSIBILITY", "AMBIGUOUS"):
            continue

        req_id = requirement["requirement_id"]
        match = match_by_req.get(req_id)
        text = requirement.get("text")
        result = match.get("result") if isinstance(match, Mapping) else "UNKNOWN"
        evidence_ids = list(match.get("evidence_ids") or []) if isinstance(match, Mapping) else []
        claim_ids = list(match.get("claim_ids") or []) if isinstance(match, Mapping) else []
        explanation = (
            match.get("explanation") if isinstance(match, Mapping) else None
        ) or "no match produced"

        if result in ("STRONG", "SUPPORTED", "PARTIAL"):
            capability_inference_state = "APPROVED_MATCH_ESTABLISHED"
        elif not infer_requirement_capabilities(requirement):
            capability_inference_state = "NO_CAPABILITIES_INFERRED"
        else:
            capability_inference_state = "CAPABILITIES_INFERRED_NO_APPROVED_MATCH"

        observations.append(
            {
                "requirement_id": req_id,
                "text": text,
                "source_semantic_role": role,
                "result": result,
                "evidence_ids": evidence_ids,
                "claim_ids": claim_ids,
                "explanation": explanation,
                "human_review_required": derive_human_review_required(requirement),
                "capability_inference_state": capability_inference_state,
            }
        )

        if result in ("NONE", "UNKNOWN") and not evidence_ids and not claim_ids:
            evidence_unknowns.append(
                f"{req_id}: no established current approved match for this "
                f"responsibility - {text}"
            )

    return observations, _unique(evidence_unknowns)


def _build_legal_gate_views(
    requirements: list[dict[str, Any]],
    jd_text: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """application_or_legal_gate_observations / unresolved_gate_observations
    (SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1).

    Every APPLICATION_OR_LEGAL_GATE requirement is surfaced with proof that
    the named, tested job_decision.py JD-text-level citizenship/clearance
    consumer actually covers it for THIS job (re-checked here, not merely
    asserted at classification time). Every AMBIGUOUS requirement whose
    classification basis names it an unresolved legal/access gate (see
    requirement_source_role.py's UNRESOLVED_LEGAL_OR_ACCESS_GATE marker) is
    separately surfaced, human-review-required, never silently dropped from
    every consequential view. This module does not redesign
    application_gate.py or any immigration/work-authorization logic --
    application-form questions remain entirely owned by that separate
    system.
    """
    gate_observations: list[dict[str, Any]] = []
    unresolved_observations: list[dict[str, Any]] = []
    consumer_fired = bool(CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN.search(jd_text or ""))

    for requirement in requirements:
        role = requirement.get("source_semantic_role")
        req_id = requirement["requirement_id"]
        text = requirement.get("text")

        if role == "APPLICATION_OR_LEGAL_GATE":
            row_covered = is_covered_by_citizenship_clearance_consumer(
                requirement.get("source_text") or ""
            )
            gate_observations.append(
                {
                    "requirement_id": req_id,
                    "text": text,
                    "dedicated_consumer": "job_decision.detect_hard_blockers "
                    "citizenship/clearance JD-text check",
                    "consumer_covers_this_row": row_covered,
                    "consumer_fired_for_this_job": consumer_fired,
                }
            )
        elif role == "AMBIGUOUS" and isinstance(
            requirement.get("source_semantic_role_basis"), str
        ) and "UNRESOLVED_LEGAL_OR_ACCESS_GATE" in requirement["source_semantic_role_basis"]:
            unresolved_observations.append(
                {
                    "requirement_id": req_id,
                    "text": text,
                    "basis": requirement["source_semantic_role_basis"],
                    "human_review_required": True,
                }
            )

    return gate_observations, unresolved_observations


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
    # `gaps`/`unknowns` are a compatibility-NAME alias for
    # `qualification_gaps`/`qualification_unknowns` (the same list objects)
    # -- NOT a claim that their pre-SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1
    # content is preserved byte-for-byte. Their meaning is now explicitly
    # qualification-scoped: a ROLE_RESPONSIBILITY/AMBIGUOUS/
    # APPLICATION_OR_LEGAL_GATE requirement is excluded from both names,
    # where pre-milestone `gaps` included every such row under deficiency
    # framing. Responsibility and unresolved-gate content lives in the
    # separate responsibility_observations/responsibility_evidence_unknowns/
    # application_or_legal_gate_observations/unresolved_gate_observations
    # outputs below, never folded back into `gaps`/`unknowns`.
    gaps, unknowns = _build_gaps_and_unknowns(requirements, matches)
    qualification_gaps, qualification_unknowns = gaps, unknowns
    responsibility_observations, responsibility_evidence_unknowns = (
        _build_responsibility_views(requirements, matches)
    )
    application_or_legal_gate_observations, unresolved_gate_observations = (
        _build_legal_gate_views(requirements, jd_text)
    )

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

    # POSTING_STATE_DECISION_WIRING_V1: consume the canonical, already-classified
    # posting-state fields (schemas/job.schema.json, Schema Milestone 1) if the
    # caller supplied them on job_input. role_status is passed through to
    # apply_posting_state_routing() exactly as supplied -- including None,
    # an unrecognized string, or a non-canonical type -- and that function
    # treats anything other than an explicit "VERIFIED_LIVE"/"LIKELY_LIVE"
    # string as unverified, downgrading an APPLY-like decision to WATCH.
    # This means a caller that supplies no role_status at all is NOT
    # byte-identical to pre-milestone routing: an otherwise APPLY-like
    # qualification now routes to WATCH by default (permanent project
    # rule -- missing/invalid posting-state evidence must never silently
    # become a favorable actionable state). The surfaced role_status
    # output field is a separate concern: it is only ever the raw string
    # the caller supplied, or None -- never fabricated, never coerced to
    # a canonical value here. Posting state never alters qualification
    # evidence, requirement-level matches, gaps, unknowns, or
    # hard_blockers, and it never upgrades a decision or converts REJECT.
    role_status = job_input.get("role_status")
    source_verification_status = job_input.get("source_verification_status")
    date_last_verified = job_input.get("date_last_verified")
    decision = apply_posting_state_routing(base_result=decision, role_status=role_status)

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
        "qualification_gaps": qualification_gaps,
        "qualification_unknowns": qualification_unknowns,
        "responsibility_observations": responsibility_observations,
        "responsibility_evidence_unknowns": responsibility_evidence_unknowns,
        "application_or_legal_gate_observations": application_or_legal_gate_observations,
        "unresolved_gate_observations": unresolved_gate_observations,
        "lane": decision["lane"],
        "decision": decision["decision"],
        "warnings": warnings,
        "extraction_mode": "STRUCTURED_EXTRACTION_PROVIDED",
        "decision_rationale": decision["decision_rationale"],
        "role_status": role_status if isinstance(role_status, str) else None,
        "source_verification_status": (
            source_verification_status if isinstance(source_verification_status, str) else None
        ),
        "date_last_verified": date_last_verified if isinstance(date_last_verified, str) else None,
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
