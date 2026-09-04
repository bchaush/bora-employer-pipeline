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
from domain_qualified_duration import (
    evaluate_domain_qualified_duration_requirement,
    is_domain_qualified_duration_requirement,
)
from evidence_repository import validate_evidence_repository
from experience_range import (
    evaluate_generic_experience_range,
    is_generic_experience_range_requirement,
)
from job_decision import (
    apply_posting_state_routing,
    apply_recruiter_threshold_guard,
    decide_lane_and_decision,
)
from job_id import generate_job_id
from qualification_gate import (
    all_gates_leaf_ids,
    evaluate_qualification_gate,
    validate_gate_requirement_references,
    validate_gate_source_traceability,
)
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
QUALIFICATION_GATE_SCHEMA_PATH = ROOT / "schemas" / "qualification_gate.schema.json"


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
    gated_requirement_ids: frozenset[str] = frozenset(),
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

    ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1 (additive):
    ``gated_requirement_ids`` are excluded from independent gap/unknown
    emission here entirely (load-bearing output-suppression requirement --
    see the ADR's Verification Required). Their qualification-relevant
    output is instead the gate-level entries analyze_job() appends
    separately from each gate's own SUPPORTED/UNRESOLVED/
    BLOCKED_BY_MATCHING_POLICY result. Defaults to empty, so every existing
    caller/ungrouped requirement behaves byte-identically to before.
    """
    match_by_req = {m["requirement_id"]: m for m in matches}
    gaps: list[str] = []
    unknowns: list[str] = []

    for requirement in requirements:
        if derive_qualification_gate(requirement.get("source_semantic_role")) != "YES":
            continue
        req_id = requirement["requirement_id"]
        if req_id in gated_requirement_ids:
            continue
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

    # ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1: qualification_gates
    # is an additive, optional top-level array in structured_extraction.json
    # (Employer truth only -- see src/qualification_gate.py and the ADR).
    # Absent/empty for every job without alternative-branch employer logic
    # -- zero migration, zero behavior change for the 17 unaffected
    # fixtures. Each gate is validated here, fail-closed, before any
    # evaluation: schema shape, raw-source traceability against jd_text,
    # and referential integrity against this job's own Requirement IDs.
    qualification_gates_raw = structured.get("qualification_gates")
    qualification_gates: list[dict[str, Any]] = (
        list(qualification_gates_raw) if isinstance(qualification_gates_raw, list) else []
    )
    if qualification_gates:
        gate_validator = build_draft202012_validator(QUALIFICATION_GATE_SCHEMA_PATH)
        known_requirement_ids = [r["requirement_id"] for r in requirements]
        for gate in qualification_gates:
            if not isinstance(gate, Mapping):
                empty["errors"].append(
                    _error(
                        "MALFORMED_QUALIFICATION_GATE",
                        detail=f"qualification_gate must be a mapping; got {type(gate).__name__}",
                    )
                )
                continue
            schema_errors = [err.message for err in gate_validator.iter_errors(gate)]
            if schema_errors:
                empty["errors"].append(
                    _error(
                        "QUALIFICATION_GATE_SCHEMA_INVALID",
                        qualification_gate_id=gate.get("qualification_gate_id"),
                        details=schema_errors,
                    )
                )
                continue
            empty["errors"].extend(
                validate_gate_requirement_references(gate, known_requirement_ids)
            )
            empty["errors"].extend(validate_gate_source_traceability(gate, jd_text))
        if empty["errors"]:
            return empty

    gated_requirement_ids = all_gates_leaf_ids(qualification_gates)

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
    # DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1: route domain-QUALIFIED
    # numeric experience-duration requirements (e.g. "Three (3) years of
    # experience in system analysis, including...") to their own narrow,
    # honest evaluator, alongside (never merged into) the existing generic
    # (domain-free) experience-range path above. A requirement is routed
    # here only when it names a domain, names no technology, the existing
    # capability matcher recognizes nothing for it, and its text is an
    # exact match for a narrowly enumerated "N years of experience in
    # <domain>" phrasing -- named-platform requirements (SAP, Salesforce,
    # Workday, etc.) always have non-empty inferred capabilities and can
    # never reach this evaluator, so their NONE_TRAPS-backed
    # correctly-disproven NONE is never weakened. requirement_match.py and
    # experience_range.py are not modified.
    generic_range_requirements: list[dict[str, Any]] = []
    domain_qualified_duration_requirements: list[dict[str, Any]] = []
    remaining_requirements: list[dict[str, Any]] = []
    for requirement in requirements:
        inferred_caps = infer_requirement_capabilities(requirement)
        if is_generic_experience_range_requirement(
            requirement, inferred_capabilities=inferred_caps
        ):
            generic_range_requirements.append(requirement)
        elif is_domain_qualified_duration_requirement(
            requirement, inferred_capabilities=inferred_caps
        ):
            domain_qualified_duration_requirements.append(requirement)
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
    domain_qualified_duration_matches = [
        evaluate_domain_qualified_duration_requirement(
            job_id=job_id, requirement=requirement, match_index=index
        )
        for index, requirement in enumerate(domain_qualified_duration_requirements)
    ]

    # Restore normalized-Requirement order (partitioning above splits the
    # single ordered `requirements` list in two): downstream consumers key
    # everything by requirement_id and are order-independent, but returning
    # `evidence_matches` in the same order as `requirements` keeps the two
    # arrays in deterministic external correspondence.
    combined_matches_by_req = {
        m["requirement_id"]: m
        for m in match_result["matches"]
        + experience_range_matches
        + domain_qualified_duration_matches
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
    gaps, unknowns = _build_gaps_and_unknowns(
        requirements, matches, gated_requirement_ids=gated_requirement_ids
    )
    qualification_gaps, qualification_unknowns = gaps, unknowns
    responsibility_observations, responsibility_evidence_unknowns = (
        _build_responsibility_views(requirements, matches)
    )
    application_or_legal_gate_observations, unresolved_gate_observations = (
        _build_legal_gate_views(requirements, jd_text)
    )

    # ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1: evaluate each
    # qualification_gate against the just-computed match state (Match
    # truth), independently -- satisfaction of one gate never suppresses
    # or erases another. Gate SUPPORTED emits no gap/unknown noise for its
    # failed alternative branches (the employer only required one branch);
    # gate UNRESOLVED emits one qualification_unknowns entry; gate
    # BLOCKED_BY_MATCHING_POLICY emits one qualification_gaps entry AND one
    # hard_blockers entry (via qualification_gate_blockers below) -- never
    # one entry per underlying gated row.
    matches_by_req = {m["requirement_id"]: m for m in matches}
    qualification_gate_results: list[dict[str, Any]] = []
    qualification_gate_blockers: list[str] = []
    for gate in qualification_gates:
        gate_outcome = evaluate_qualification_gate(gate, matches_by_req)
        gate_id = gate.get("qualification_gate_id")
        source_text = gate.get("source_text")
        source_summary = " / ".join(source_text) if isinstance(source_text, list) else ""
        qualification_gate_results.append(
            {
                "qualification_gate_id": gate_id,
                "result": gate_outcome["result"],
                "leaf_support": gate_outcome["leaf_support"],
                "source_text": source_text,
                "source_location": gate.get("source_location"),
            }
        )
        if gate_outcome["result"] == "BLOCKED_BY_MATCHING_POLICY":
            blocker_text = (
                f"{gate_id}: qualification gate blocked by matching policy - "
                f"{source_summary} (branch leaf states: {gate_outcome['leaf_support']})"
            )
            qualification_gate_blockers.append(blocker_text)
            qualification_gaps.append(blocker_text)
        elif gate_outcome["result"] == "UNRESOLVED":
            qualification_unknowns.append(
                f"{gate_id}: qualification gate unresolved - {source_summary} "
                f"(branch leaf states: {gate_outcome['leaf_support']})"
            )
        # SUPPORTED: no gap/unknown entry -- the employer only required one
        # branch, and it was cleared; failed alternatives are not gaps.

    decision = decide_lane_and_decision(
        requirements=requirements,
        matches=matches,
        gaps=gaps,
        unknowns=unknowns,
        seniority=normalized.get("seniority"),
        role_family=normalized.get("role_family"),
        role=role,
        jd_text=jd_text,
        gated_requirement_ids=gated_requirement_ids,
        qualification_gate_blockers=qualification_gate_blockers,
    )

    # POSTING_STATE_DECISION_WIRING_V1: consume the canonical, already-classified
    # posting-state fields (schemas/job.schema.json, Schema Milestone 1) if the
    # caller supplied them on job_input. role_status and
    # source_verification_status are each passed through to
    # apply_posting_state_routing() independently and exactly as supplied
    # -- including None, an unrecognized string, or a non-canonical type on
    # either axis. Strengthened by LIVE_ROLE_VERIFIED_ACTIONABILITY_GATE_V1
    # / Blueprint §135 (PRE_SURFACING_FIRST_PARTY_ACTIONABILITY_ENFORCEMENT_V1):
    # an already-computed APPLY-like decision now survives only when BOTH
    # role_status == "VERIFIED_LIVE" AND source_verification_status ==
    # "VERIFIED_DIRECT" are true. Missing, malformed, or any other value on
    # EITHER axis alone -- including role_status="LIKELY_LIVE" even when
    # source_verification_status="VERIFIED_DIRECT" -- fails closed,
    # downgrading an APPLY-like decision to WATCH by default (permanent
    # project rule -- missing/invalid posting/source evidence must never
    # silently become a favorable actionable state). Neither axis is ever
    # inferred from, or coerced into, the other. The surfaced role_status/
    # source_verification_status output fields are a separate concern:
    # each is only ever the raw string the caller supplied, or None --
    # never fabricated, never coerced to a canonical value here.
    # Posting/source verification affects actionable routing only -- it
    # never alters qualification evidence, requirement-level matches,
    # gaps, unknowns, or hard_blockers, and it never upgrades a decision
    # or converts REJECT (a qualification REJECT remains REJECT under
    # every posting/source combination).
    role_status = job_input.get("role_status")
    source_verification_status = job_input.get("source_verification_status")
    date_last_verified = job_input.get("date_last_verified")
    decision = apply_posting_state_routing(
        base_result=decision,
        role_status=role_status,
        source_verification_status=source_verification_status,
    )

    # BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1: a further, independent,
    # downgrade-only pursuit/surfacing-economics layer. Runs after posting-
    # state routing so both layers compose (either may downgrade; neither
    # can undo the other's downgrade). Applies when an unresolved
    # MANDATORY, ungated, EXPERIENCE_RANGE_EVALUATOR/
    # DOMAIN_QUALIFIED_DURATION_EVALUATOR requirement states an explicit
    # lower-bound experience threshold of 2+ years, in two conservative
    # tiers: lower_bound==2 exactly caps PRIORITY_APPLY/APPLY at
    # EFFICIENT_APPLY (an incoming EFFICIENT_APPLY is left unchanged);
    # lower_bound>=3 caps PRIORITY_APPLY/APPLY/EFFICIENT_APPLY alike down
    # to WATCH (this tier consumes every APPLY-like decision). Never
    # touches Qualification Truth, never computes a candidate duration,
    # never converts UNKNOWN to NONE, never introduces REJECT. See
    # src/job_decision.py::apply_recruiter_threshold_guard for the full
    # invariant list.
    decision = apply_recruiter_threshold_guard(
        base_result=decision,
        requirements=requirements,
        matches=matches,
        gated_requirement_ids=gated_requirement_ids,
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
        "qualification_gaps": qualification_gaps,
        "qualification_unknowns": qualification_unknowns,
        "responsibility_observations": responsibility_observations,
        "responsibility_evidence_unknowns": responsibility_evidence_unknowns,
        "application_or_legal_gate_observations": application_or_legal_gate_observations,
        "unresolved_gate_observations": unresolved_gate_observations,
        "qualification_gate_results": qualification_gate_results,
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
