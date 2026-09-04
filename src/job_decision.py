"""Bounded lane/decision routing for Job Analysis v1.

Explainable from hard blockers, mandatory coverage, role-family fit,
information sufficiency, and material preferred gaps.
Does not emit hire-probability percentages.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from requirement_source_role import (
    CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN,
    derive_qualification_gate,
)
from experience_range import parse_generic_experience_range
from domain_qualified_duration import parse_domain_qualified_duration


SUPPORTED_ROLE_FAMILY_TOKENS = (
    "business systems",
    "implementation",
    "data operations",
    "business process",
    "digital solutions",
    "technical operations",
    # Blueprint §6 primary targets — multi-word tokens only (not bare application/s).
    "application analyst",
    "applications analyst",
    "application support",
)


def _req_blob(requirement: Mapping[str, Any]) -> str:
    parts = [
        str(requirement.get("text") or ""),
        str(requirement.get("source_text") or ""),
        str(requirement.get("experience_level") or ""),
        str(requirement.get("seniority_implication") or ""),
    ]
    return " ".join(parts).casefold()


def detect_seniority_signals(*, role: str | None, jd_text: str, seniority: str | None) -> list[str]:
    """Defense-in-depth seniority detection from extraction + raw title/JD."""
    signals: list[str] = []
    sen = (seniority or "").casefold()
    title = (role or "").casefold()
    jd = jd_text.casefold() if isinstance(jd_text, str) else ""

    if any(
        token in sen
        for token in ("senior", "staff", "principal", "director", "manager")
    ):
        signals.append(f"extracted seniority indicates advanced level: {seniority}")

    if re.search(r"\b(senior|staff|principal|director)\b", title):
        signals.append(f"role title indicates advanced seniority: {role}")

    # Conservative 'lead' handling: only when clearly a title/role qualifier.
    if re.search(
        r"\blead\s+(business|systems|analyst|engineer|architect|developer)\b",
        title,
    ) or re.search(r"\b(lead\s+business\s+systems|business\s+systems\s+lead)\b", title):
        signals.append(f"role title indicates lead-level seniority: {role}")

    # Raw JD title-like lines (first ~400 chars) for mislabeled extraction.
    head = jd[:400]
    if re.search(
        r"\b(senior|staff|principal|director)\s+"
        r"(business\s+systems|analyst|engineer|architect|manager)\b",
        head,
    ):
        signals.append("raw JD title language indicates advanced seniority")

    if re.search(r"\b(5\+|7\+|10\+|eight|ten)\s*\+?\s*years?\b", jd) or re.search(
        r"\b(5|7|8|10)\+?\s*years?\b", jd
    ):
        if signals or any(
            token in sen for token in ("senior", "staff", "principal", "lead")
        ):
            signals.append("senior years-of-experience requirement present")

    return signals


def detect_hard_blockers(
    *,
    requirements: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
    seniority: str | None,
    role: str | None,
    jd_text: str,
    gated_requirement_ids: frozenset[str] = frozenset(),
    qualification_gate_blockers: Sequence[str] = (),
) -> list[str]:
    """Return human-readable hard blockers present in the analyzed role.

    ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1 (additive):
    ``gated_requirement_ids`` -- requirement_ids referenced by some
    qualification_gate (src/qualification_gate.py) -- are skipped by the
    ordinary per-row loop below, so they are never independently
    double-counted; they are evaluated only through their gate.
    ``qualification_gate_blockers`` are already-computed
    BLOCKED_BY_MATCHING_POLICY gate blocker strings, appended once each
    (never one blocker per underlying gated row). Both default to empty,
    so every existing caller and every ungrouped requirement retains
    today's exact behavior, byte-unchanged.
    """
    blockers: list[str] = []
    jd = jd_text.casefold() if isinstance(jd_text, str) else ""

    blockers.extend(
        detect_seniority_signals(role=role, jd_text=jd_text, seniority=seniority)
    )
    blockers.extend(qualification_gate_blockers)

    # SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1: this pattern is now
    # the single source of truth shared with requirement_source_role.py's
    # is_covered_by_citizenship_clearance_consumer() -- classification and
    # this blocker check can never drift apart.
    if CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN.search(jd):
        blockers.append("Citizenship or clearance requirement present in JD")

    match_by_req = {
        m["requirement_id"]: m for m in matches if isinstance(m.get("requirement_id"), str)
    }

    for requirement in requirements:
        if requirement.get("importance") != "MANDATORY":
            continue
        if requirement.get("relevance") != "HIGH":
            continue
        # SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1 /
        # UNMIGRATED_EXTRACTION_AND_GOLDEN_COMPLETION_V1: a requirement is
        # only eligible to independently produce a candidate-entry hard
        # blocker when its derived qualification gate is YES, which
        # requires an explicit, valid, persisted source_semantic_role ==
        # ENTRY_QUALIFICATION. A missing/null/invalid role derives
        # AMBIGUOUS here, NOT YES -- there is no backward-compatibility
        # carve-out; an absent role never independently gates, for any
        # caller (including one that bypasses
        # requirement_normalize.py/schema validation entirely). A
        # canonical artifact reaching ordinary analyze_job() production
        # routing with a missing/invalid role is stopped even earlier, at
        # requirement_normalize.py's ingestion gate, before this function
        # ever runs. ROLE_RESPONSIBILITY/APPLICATION_OR_LEGAL_GATE/
        # AMBIGUOUS rows never independently gate here either;
        # APPLICATION_OR_LEGAL_GATE rows remain covered by the separate,
        # pre-existing JD-text-level citizenship/clearance check below,
        # unchanged.
        if derive_qualification_gate(requirement.get("source_semantic_role")) != "YES":
            continue
        req_id = requirement.get("requirement_id")
        if isinstance(req_id, str) and req_id in gated_requirement_ids:
            # ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1: this row
            # is evaluated only through its qualification_gate (already
            # folded into qualification_gate_blockers above); never
            # independently double-counted here.
            continue
        match = match_by_req.get(req_id) if isinstance(req_id, str) else None
        result = match.get("result") if isinstance(match, Mapping) else None
        if result != "NONE":
            continue

        blob = _req_blob(requirement)
        # Platform / SWE / ML specifics (retain explicit messaging).
        if re.search(
            r"\b(production\s+ml|machine\s+learning|deep\s+learning|"
            r"software\s+engineer|backend\s+engineer)\b",
            blob,
        ):
            blockers.append(
                f"Unsupported deep SWE/ML mandatory HIGH requirement: {req_id}"
            )
            continue
        if re.search(
            r"\b(salesforce|google\s+cloud|gcp|workday|servicenow)\b",
            blob,
        ):
            blockers.append(
                f"Unsupported core platform specialization (mandatory HIGH): {req_id}"
            )
            continue

        # Generalized core mandatory HIGH / NONE blocker.
        blockers.append(
            f"Unsupported core mandatory HIGH requirement: {req_id}"
        )

    return blockers


def role_family_fit(role_family: str | None, role: str | None = None) -> bool:
    """True when extracted family or role title matches a supported multi-word token."""
    candidates = [
        (role_family or "").casefold(),
        (role or "").casefold(),
    ]
    return any(
        token in text
        for text in candidates
        for token in SUPPORTED_ROLE_FAMILY_TOKENS
    )


def is_information_deficit(
    *,
    requirements: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
) -> bool:
    """True when the JD lacks enough substance to confirm fit or incompatibility.

    INSUFFICIENT INFORMATION → WATCH (not REJECT).
    """
    substantive = [
        r
        for r in requirements
        if r.get("importance") in {"MANDATORY", "PREFERRED"}
        and r.get("relevance") in {"HIGH", "MEDIUM"}
    ]
    unclear = [r for r in requirements if r.get("importance") == "UNCLEAR"]
    low = [r for r in requirements if r.get("relevance") == "LOW"]

    if len(substantive) == 0:
        return True

    strongish = 0
    for match in matches:
        if match.get("result") in {"STRONG", "SUPPORTED", "PARTIAL"}:
            strongish += 1

    # Mostly noise / unclear with almost no substantive evaluable content.
    if len(substantive) <= 1 and (len(unclear) + len(low)) >= max(2, len(substantive)):
        if strongish == 0:
            return True

    if len(requirements) >= 3:
        unclear_ratio = len(unclear) / len(requirements)
        if unclear_ratio >= 0.5 and strongish == 0 and len(substantive) <= 2:
            return True

    return False


_APPLY_LIKE_DECISIONS = frozenset({"PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"})
_POSTING_WATCH_STATES = frozenset({"UNCLEAR", "POSSIBLY_STALE", "CONFIRMED_CLOSED"})
# Only these two canonical strings represent verified/likely-live posting
# reality; everything else -- None, any other canonical value, an
# unrecognized string, or a non-string type -- must never preserve an
# APPLY-like decision (SECOND BOUNDED CORRECTION).
_LIVE_ROLE_STATES = frozenset({"VERIFIED_LIVE", "LIKELY_LIVE"})


_VERIFIED_DIRECT_SOURCE = "VERIFIED_DIRECT"


def apply_posting_state_routing(
    *,
    base_result: Mapping[str, Any],
    role_status: Any,
    source_verification_status: Any = None,
) -> dict[str, Any]:
    """Apply Blueprint Section 30 posting-state downgrade to an already-computed
    qualification decision (POSTING_STATE_DECISION_WIRING_V1), extended by
    PRE_SURFACING_FIRST_PARTY_ACTIONABILITY_ENFORCEMENT_V1 (Blueprint §135)
    to require exact first-party actionability, not merely posting
    freshness, before preserving an APPLY-like result.

    Posting reality and qualification truth are separate axes. This function
    runs strictly AFTER decide_lane_and_decision() has already produced its
    qualification-only result:

      - a qualification REJECT is never touched (a genuinely unqualified role
        stays REJECT regardless of posting freshness or its absence);
      - a decision that is already non-APPLY-like (e.g. an unrelated WATCH
        from information deficit) is never touched either -- posting-state
        routing only ever downgrades an APPLY-like result, and never
        rewrites an existing rationale;
      - an APPLY-like result (PRIORITY_APPLY/APPLY/EFFICIENT_APPLY) is
        preserved unchanged ONLY when BOTH role_status=="VERIFIED_LIVE"
        AND source_verification_status=="VERIFIED_DIRECT" are true
        (Blueprint §135: role freshness alone is discovery/index-shaped
        evidence, not proof of exact current first-party actionability).
        role_status="LIKELY_LIVE" -- even paired with a fully
        VERIFIED_DIRECT source -- no longer crosses this gate; this is a
        deliberate, disclosed narrowing of POSTING_STATE_DECISION_WIRING_V1's
        original behavior (see tests/posting_state_decision_wiring_v1_test.py
        Section B for the documented migration).
      - every other combination downgrades an APPLY-like result to WATCH
        -- never to REJECT. This deliberately includes: either axis
        None/absent; role_status in UNCLEAR/POSSIBLY_STALE/CONFIRMED_CLOSED;
        source_verification_status in SOURCE_VERIFICATION_REQUIRED/
        DIRECT_SOURCE_UNAVAILABLE/UNKNOWN; an unrecognized string on either
        axis; and any non-string type on either axis. Missing or malformed
        posting/source evidence is treated the same as an explicit
        unverified value -- the absence or invalidity of verification must
        never silently become a favorable actionable state (permanent
        project rule).
      - both axes are compared with a str type-check gate BEFORE any
        equality/membership test, so an unhashable raw value (e.g. a list)
        on either axis can never reach a hash-based lookup or raise -- this
        function never raises for any input type on either axis. It never
        coerces or rewrites either input value, and never infers one axis
        from the other; the surfaced role_status/source_verification_status
        values are owned entirely by job_analysis.py.
      - Requirement-level matches, gaps, unknowns, and hard_blockers are
        never modified; only lane/decision/decision_rationale may change.
    """
    result = dict(base_result)

    if result.get("decision") not in _APPLY_LIKE_DECISIONS:
        return result

    role_status_ok = isinstance(role_status, str) and role_status == "VERIFIED_LIVE"
    source_ok = (
        isinstance(source_verification_status, str)
        and source_verification_status == _VERIFIED_DIRECT_SOURCE
    )
    if role_status_ok and source_ok:
        return result

    failed_axes: list[str] = []
    if not role_status_ok:
        if isinstance(role_status, str) and role_status in _POSTING_WATCH_STATES:
            failed_axes.append(f"role_status={role_status}")
        elif isinstance(role_status, str):
            failed_axes.append(f"role_status={role_status!r} is not VERIFIED_LIVE")
        elif role_status is None:
            failed_axes.append("role_status missing (no posting-state verification supplied)")
        else:
            failed_axes.append(
                f"role_status is not a valid posting-state string (got {type(role_status).__name__})"
            )
    if not source_ok:
        if isinstance(source_verification_status, str):
            failed_axes.append(
                f"source_verification_status={source_verification_status!r} is not VERIFIED_DIRECT"
            )
        elif source_verification_status is None:
            failed_axes.append(
                "source_verification_status missing (no first-party source verification supplied)"
            )
        else:
            failed_axes.append(
                "source_verification_status is not a valid verification string "
                f"(got {type(source_verification_status).__name__})"
            )
    reason = "; ".join(failed_axes)

    result["lane"] = "WATCH"
    result["decision"] = "WATCH"
    result["decision_rationale"] = (
        f"{result.get('decision_rationale', '')} "
        f"Downgraded to WATCH: {reason} "
        "(Blueprint §135 -- exact first-party current actionability requires "
        "BOTH role_status=VERIFIED_LIVE AND source_verification_status="
        "VERIFIED_DIRECT; qualification result unchanged)."
    ).strip()
    return result


_RECRUITER_THRESHOLD_LOWER_BOUND_MIN = 2


def apply_recruiter_threshold_guard(
    *,
    base_result: Mapping[str, Any],
    requirements: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
    gated_requirement_ids: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1: pursuit/surfacing-economics
    downgrade-only guard, strictly AFTER decide_lane_and_decision() and
    apply_posting_state_routing() have already produced their result.

    Root cause this function exists to fix: experience_range.py and
    domain_qualified_duration.py correctly and deliberately return UNKNOWN
    (never a fabricated NONE) for an explicit numeric experience-threshold
    requirement, because no canonical candidate-duration fact exists in
    this repository. But decide_lane_and_decision()'s threshold counters
    (`none`, `strong_or_supported`, `partial`) are blind to UNKNOWN --  an
    UNKNOWN mandatory-HIGH row contributes to none of them, so it exerts
    zero friction on PRIORITY_APPLY/APPLY routing. When Bora's evidence is
    otherwise strong, this silently promotes a role whose real recruiter
    threshold (e.g. "2-4 years of work experience", reproduced live at
    Bose Professional -- IT Business Analyst) was never actually resolved
    one way or the other.

    This function does NOT touch Qualification Truth, does NOT compute or
    infer a candidate experience duration, and does NOT convert UNKNOWN
    into NONE. It only caps how favorably an already-computed APPLY-like
    decision may be SURFACED for pursuit purposes, mirroring
    apply_posting_state_routing()'s own downgrade-only pattern exactly:

      - only an incoming decision of PRIORITY_APPLY, APPLY, or
        EFFICIENT_APPLY may be touched; WATCH, REJECT, and UNDECIDED are
        returned unchanged -- this guard can never introduce REJECT and
        never upgrades anything (permanent invariant: a threshold guard
        may only make pursuit more conservative, never more favorable).
        BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1 CURSOR CORRECTION: EARLIER
        drafts of this guard excluded EFFICIENT_APPLY from its early
        return, treating it as a universal floor this guard only ever
        caps DOWN TO and never itself touches. That was wrong for the
        >=3 tier specifically: an already-EFFICIENT_APPLY role with an
        unresolved mandatory lower_bound>=3 threshold must still be
        downgraded to WATCH (the >=3 tier consumes ALL APPLY-like
        decisions, EFFICIENT_APPLY included) -- otherwise a role could
        reach EFFICIENT_APPLY by some other path (e.g. a material
        preferred gap) and then silently dodge the >=3 tier's own
        conservative ceiling purely by already sitting at the exactly-2
        tier's floor. EFFICIENT_APPLY is now included in the incoming-
        decision check; see the exactly-2/>=3 tier logic below for the
        precise per-tier behavior on each incoming decision;
      - a requirement is examined only when importance=="MANDATORY" (a
        formally PREFERRED numeric threshold does not trigger this guard
        -- PREFERRED != CENTRAL is a judgment left to semantic review, not
        this deterministic gate) and its requirement_id is NOT in
        gated_requirement_ids (an alternative-qualification-branch row is
        already authoritatively represented by the existing
        qualification_gate architecture; this guard never re-litigates
        that);
      - a requirement triggers the guard only when its EvidenceMatch
        result=="UNKNOWN" AND evaluation_path is exactly
        "EXPERIENCE_RANGE_EVALUATOR" or "DOMAIN_QUALIFIED_DURATION_EVALUATOR"
        -- i.e. only the two existing, unmodified, deliberately-narrow
        evaluators' own honest-UNKNOWN output, never any other UNKNOWN
        source, and never a positively-established STRONG/SUPPORTED
        result (explicit supported satisfaction is never downgraded
        merely because a number appears in the JD);
      - the requirement's own `text` is re-parsed with the existing,
        unmodified parse_generic_experience_range()/
        parse_domain_qualified_duration() functions (the exact same
        parsers each evaluator already used to reach its own UNKNOWN) to
        read the employer's own stated lower_bound -- this is Employer
        Truth already captured, never a computed/inferred candidate fact;
      - lower_bound <= 1 (covers "0-2" -- no guard from years alone -- and
        "1-3", left explicitly case-by-case/discretionary, not an
        automatic trigger) never triggers the guard;
      - lower_bound == 2 exactly (covers "2-4" -- a RANGE parse's
        lower_bound, the Bose-style THRESHOLD STRETCH case) caps
        PRIORITY_APPLY/APPLY down to EFFICIENT_APPLY; an incoming
        EFFICIENT_APPLY is left unchanged (already at or below this
        tier's own ceiling -- there is nothing further to downgrade to
        for this tier alone, absent a >=3 row);
      - lower_bound >= 3 (covers "3+", "5+", "6+", "7+", "8+", "10+",
        etc. alike -- outside Bora's normal serious-pursuit pool per the
        locked operating calibration) caps PRIORITY_APPLY, APPLY, AND
        EFFICIENT_APPLY alike down to WATCH, the existing canonical
        conservative non-APPLY state -- this tier consumes every
        APPLY-like decision, never REJECT (this guard still never
        introduces REJECT).
        BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1 CORRECTION (second
        post-review pass): V1 of this guard capped every lower_bound>=2
        identically at EFFICIENT_APPLY. That fixed the monotonicity
        defect (no threshold routed more favorably than a smaller one)
        but under-corrected severity: an otherwise-strong, unkeyworded
        "10+ years of work experience" role could still remain
        APPLY-like (at EFFICIENT_APPLY), which does not match the
        approved operating calibration -- 3+ unsupported is outside
        Bora's normal serious-pursuit pool, and 5+/7+/10+ must not
        survive merely because no Senior keyword is present. Splitting
        the single cap into two conservative tiers (2 exactly ->
        EFFICIENT_APPLY; >=3 -> WATCH) preserves strict, non-inverting
        monotonicity (0-2/1-3 > 2 > 3+, each tier strictly more
        conservative than the last as the unresolved bound grows) while
        still never touching Qualification Truth, never fabricating a
        candidate-duration comparison, and never introducing REJECT or a
        new schema/enum -- WATCH is the same existing canonical
        conservative state decide_lane_and_decision() already produces
        elsewhere (e.g. information-deficit, unsupported-family routing).
        This still does not touch, duplicate, or weaken
        detect_seniority_signals -- a keyworded "Senior"/"Staff"/
        "Principal"/"Lead" case still REJECTs via that separate,
        untouched mechanism, unaffected by and independent of this guard;
      - when a requirement in each tier is present, the MORE conservative
        tier wins (a role with both an unresolved "2-4" row and an
        unresolved "5+" row routes to WATCH, not EFFICIENT_APPLY) --
        this guard only ever moves a result MORE conservative, never
        picks the more favorable of two triggered tiers;
      - requirement-level matches, gaps, unknowns, and hard_blockers are
        never modified; only lane/decision/decision_rationale may change.
    """
    result = dict(base_result)

    incoming_decision = result.get("decision")
    if incoming_decision not in ("PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"):
        return result

    match_by_req = {m.get("requirement_id"): m for m in matches if isinstance(m, Mapping)}
    tier_exactly_2_reasons: list[str] = []
    tier_3_plus_reasons: list[str] = []
    for requirement in requirements:
        if requirement.get("importance") != "MANDATORY":
            continue
        req_id = requirement.get("requirement_id")
        if not isinstance(req_id, str) or req_id in gated_requirement_ids:
            continue
        match = match_by_req.get(req_id)
        if not isinstance(match, Mapping) or match.get("result") != "UNKNOWN":
            continue
        evaluation_path = match.get("evaluation_path")
        if evaluation_path not in ("EXPERIENCE_RANGE_EVALUATOR", "DOMAIN_QUALIFIED_DURATION_EVALUATOR"):
            continue
        text = requirement.get("text")
        if not isinstance(text, str):
            continue
        parsed = parse_generic_experience_range(text) or parse_domain_qualified_duration(text)
        if parsed is None:
            continue
        lower_bound = parsed.get("lower_bound")
        if not isinstance(lower_bound, int):
            continue
        if lower_bound < _RECRUITER_THRESHOLD_LOWER_BOUND_MIN:
            continue
        reason = f"{req_id} (lower_bound={lower_bound} years, unresolved)"
        if lower_bound == _RECRUITER_THRESHOLD_LOWER_BOUND_MIN:
            tier_exactly_2_reasons.append(reason)
        else:
            tier_3_plus_reasons.append(reason)

    if tier_3_plus_reasons:
        result["lane"] = "WATCH"
        result["decision"] = "WATCH"
        result["decision_rationale"] = (
            f"{result.get('decision_rationale', '')} "
            "Capped to WATCH: unresolved explicit mandatory recruiter "
            "experience threshold(s) at 3+ years, outside Bora's normal "
            f"serious-pursuit pool ({'; '.join(tier_3_plus_reasons)}) -- "
            "BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1, pursuit/surfacing "
            "economics only; qualification result unchanged."
        ).strip()
        return result

    if tier_exactly_2_reasons and incoming_decision in ("PRIORITY_APPLY", "APPLY"):
        result["lane"] = "LANE_1_EFFICIENT_APPLY"
        result["decision"] = "EFFICIENT_APPLY"
        result["decision_rationale"] = (
            f"{result.get('decision_rationale', '')} "
            "Capped to EFFICIENT_APPLY: unresolved explicit mandatory recruiter "
            f"experience threshold(s) at Bora's early-career target pool boundary ("
            f"{'; '.join(tier_exactly_2_reasons)}) -- BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1, "
            "pursuit/surfacing economics only; qualification result unchanged."
        ).strip()
        return result

    # incoming_decision == "EFFICIENT_APPLY" with only tier_exactly_2_reasons
    # (no tier_3_plus_reasons, handled above): already at or below the
    # exactly-2 ceiling -- nothing further to downgrade.
    return result


def decide_lane_and_decision(
    *,
    requirements: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
    gaps: Sequence[str],
    unknowns: Sequence[str],
    seniority: str | None,
    role_family: str | None,
    role: str | None,
    jd_text: str,
    gated_requirement_ids: frozenset[str] = frozenset(),
    qualification_gate_blockers: Sequence[str] = (),
) -> dict[str, Any]:
    """Compute lane, decision, and rationale from structured analysis facts."""
    blockers = detect_hard_blockers(
        requirements=requirements,
        matches=matches,
        seniority=seniority,
        role=role,
        jd_text=jd_text,
        gated_requirement_ids=gated_requirement_ids,
        qualification_gate_blockers=qualification_gate_blockers,
    )
    if blockers:
        return {
            "lane": "LANE_0_REJECT",
            "decision": "REJECT",
            "decision_rationale": "Hard blocker(s): " + "; ".join(blockers),
            "hard_blockers": blockers,
        }

    # Information deficit before unsupported-family reject (R-4).
    if is_information_deficit(requirements=requirements, matches=matches):
        return {
            "lane": "WATCH",
            "decision": "WATCH",
            "decision_rationale": (
                "Insufficient substantive JD information to confirm fit or "
                "incompatibility; routing to WATCH."
            ),
            "hard_blockers": [],
        }

    match_by_req = {
        m["requirement_id"]: m for m in matches if isinstance(m.get("requirement_id"), str)
    }

    # ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1: a gated row's raw
    # EvidenceMatch result (e.g. NONE pending Claim approval) must not
    # independently count toward none/high_none/strong_or_supported below --
    # it is represented only through its gate's own SUPPORTED/UNRESOLVED/
    # BLOCKED_BY_MATCHING_POLICY result (already folded into `blockers`
    # above via qualification_gate_blockers). Defaults to empty, so every
    # existing caller and every ungrouped requirement counts exactly as
    # before.
    # SOURCE_SEMANTIC_ROLE_THRESHOLD_COUNTING_PARITY_V1: mirror
    # detect_hard_blockers()'s own derive_qualification_gate(...) == "YES"
    # eligibility filter (see the per-row loop above) here too. Without it,
    # a ROLE_RESPONSIBILITY/APPLICATION_OR_LEGAL_GATE/AMBIGUOUS/missing-role
    # row -- already correctly excluded from the human-facing hard_blockers
    # list -- could still silently contaminate none/high_none/partial/
    # strong_or_supported/high_strong/distinct_high_claims/
    # material_preferred_missing/nonmaterial_preferred_missing below, and
    # therefore REJECT/WATCH/EFFICIENT_APPLY/APPLY/PRIORITY_APPLY routing,
    # with no trace of the real cause in hard_blockers or qualification_gaps.
    # Orthogonal to, and applied in addition to, the pre-existing
    # gated_requirement_ids exclusion.
    mandatory = [
        r
        for r in requirements
        if r.get("importance") == "MANDATORY"
        and r.get("relevance") in {"HIGH", "MEDIUM"}
        and r.get("requirement_id") not in gated_requirement_ids
        and derive_qualification_gate(r.get("source_semantic_role")) == "YES"
    ]
    preferred = [
        r
        for r in requirements
        if r.get("importance") == "PREFERRED"
        and r.get("relevance") in {"HIGH", "MEDIUM"}
        and r.get("requirement_id") not in gated_requirement_ids
        and derive_qualification_gate(r.get("source_semantic_role")) == "YES"
    ]

    strong_or_supported = 0
    partial = 0
    none = 0
    high_none = 0
    high_strong = 0
    # Distinct Claim provenance for HIGH mandatory STRONG/SUPPORTED matches.
    # Prevents PRIORITY gaming via requirement splitting against one claim.
    distinct_high_claims: set[str] = set()
    for requirement in mandatory:
        req_id = requirement.get("requirement_id")
        match = match_by_req.get(req_id) if isinstance(req_id, str) else None
        result = match.get("result") if isinstance(match, Mapping) else "UNKNOWN"
        if result in {"STRONG", "SUPPORTED"}:
            strong_or_supported += 1
            if requirement.get("relevance") == "HIGH":
                high_strong += 1
                if isinstance(match, Mapping):
                    for claim_id in match.get("claim_ids") or []:
                        if isinstance(claim_id, str) and claim_id.strip():
                            distinct_high_claims.add(claim_id)
        elif result == "PARTIAL":
            partial += 1
        elif result == "NONE":
            none += 1
            if requirement.get("relevance") == "HIGH":
                high_none += 1

    distinct_high_claim_count = len(distinct_high_claims)

    # Material preferred gaps use HIGH relevance (policy: not every preferred gap).
    material_preferred_missing = 0
    nonmaterial_preferred_missing = 0
    for requirement in preferred:
        req_id = requirement.get("requirement_id")
        match = match_by_req.get(req_id) if isinstance(req_id, str) else None
        result = match.get("result") if isinstance(match, Mapping) else "UNKNOWN"
        if result not in {"NONE", "UNKNOWN"}:
            continue
        if requirement.get("relevance") == "HIGH":
            material_preferred_missing += 1
        else:
            nonmaterial_preferred_missing += 1

    family_fit = role_family_fit(role_family, role=role)
    unclear_count = sum(1 for r in requirements if r.get("importance") == "UNCLEAR")

    # Any core mandatory HIGH gap blocks positive apply routing.
    if high_none >= 1:
        return {
            "lane": "LANE_0_REJECT",
            "decision": "REJECT",
            "decision_rationale": (
                "At least one core mandatory HIGH requirement has NONE coverage "
                f"(high_none={high_none})."
            ),
            "hard_blockers": [],
        }

    if not family_fit:
        # Confirmed bad fit: unsupported family PLUS substantive incompatible duties.
        if none >= 1 or high_none >= 1 or (strong_or_supported == 0 and len(mandatory) >= 2):
            return {
                "lane": "LANE_0_REJECT",
                "decision": "REJECT",
                "decision_rationale": (
                    f"Role family {role_family!r} is outside supported/adjacent "
                    "families with substantive incompatible or unsupported duties."
                ),
                "hard_blockers": [],
            }
        return {
            "lane": "WATCH",
            "decision": "WATCH",
            "decision_rationale": (
                f"Role family {role_family!r} is outside supported/adjacent families; "
                "not eligible for APPLY / EFFICIENT_APPLY / PRIORITY_APPLY."
            ),
            "hard_blockers": [],
        }

    if none >= 2 and strong_or_supported == 0:
        return {
            "lane": "LANE_0_REJECT",
            "decision": "REJECT",
            "decision_rationale": (
                "Multiple mandatory HIGH/MEDIUM requirements have NONE coverage "
                f"(none={none})."
            ),
            "hard_blockers": [],
        }

    if unclear_count >= 3 and strong_or_supported <= 1:
        return {
            "lane": "WATCH",
            "decision": "WATCH",
            "decision_rationale": (
                "Too many UNCLEAR requirements to route confidently; "
                f"unclear={unclear_count}."
            ),
            "hard_blockers": [],
        }

    # PRIORITY_APPLY: uncommon; exceptional breadth of distinct Claim provenance
    # (not raw requirement-row count). Duplicate splits of one claim do not qualify.
    #
    # Assumption (N-3): with the current approved Claim Bank, Claim IDs are a
    # usable proxy for distinct capability breadth because CLAIM_WW_001–005 have
    # non-overlapping capability ownership. If future overlapping claims appear,
    # this proxy may need revisit — do not invent that behavior preemptively.
    if (
        family_fit
        and distinct_high_claim_count >= 4
        and none == 0
        and partial == 0
        and material_preferred_missing == 0
        and strong_or_supported >= 4
    ):
        return {
            "lane": "LANE_2_PRIORITY_APPLY",
            "decision": "PRIORITY_APPLY",
            "decision_rationale": (
                "Exceptional core mandatory HIGH alignment across distinct Claim "
                f"provenance (distinct_high_claims={distinct_high_claim_count}, "
                f"high_strong={high_strong}) with no material preferred gaps."
            ),
            "hard_blockers": [],
        }

    # APPLY: strong core fit with a meaningful (material) preferred gap, or
    # strong coverage that is not quite exceptional.
    if family_fit and strong_or_supported >= 3 and none == 0 and material_preferred_missing >= 1:
        return {
            "lane": "LANE_1_EFFICIENT_APPLY",
            "decision": "APPLY",
            "decision_rationale": (
                "Strong core coverage with material preferred gap(s) "
                f"(material_preferred_missing={material_preferred_missing}); "
                "warrants normal deliberate tailoring."
            ),
            "hard_blockers": [],
        }

    if (
        family_fit
        and strong_or_supported >= 3
        and none == 0
        and material_preferred_missing == 0
        and (
            partial >= 1
            or distinct_high_claim_count < 4
            or nonmaterial_preferred_missing >= 2
        )
    ):
        return {
            "lane": "LANE_1_EFFICIENT_APPLY",
            "decision": "APPLY",
            "decision_rationale": (
                "Good evidence alignment without exceptional Priority breadth "
                f"(strong_or_supported={strong_or_supported}, "
                f"distinct_high_claims={distinct_high_claim_count}, "
                f"nonmaterial_preferred_missing={nonmaterial_preferred_missing})."
            ),
            "hard_blockers": [],
        }

    # EFFICIENT_APPLY: plausible, lower intensity / thinner coverage / several gaps.
    if family_fit and strong_or_supported >= 1 and none == 0:
        return {
            "lane": "LANE_1_EFFICIENT_APPLY",
            "decision": "EFFICIENT_APPLY",
            "decision_rationale": (
                "Plausible core eligibility with lower-intensity evidence alignment "
                f"(strong_or_supported={strong_or_supported}, "
                f"preferred_missing_total="
                f"{material_preferred_missing + nonmaterial_preferred_missing}); "
                "keep application cost low."
            ),
            "hard_blockers": [],
        }

    if unknowns and strong_or_supported == 0:
        return {
            "lane": "WATCH",
            "decision": "WATCH",
            "decision_rationale": "Coverage mostly unknown; watch pending clarification.",
            "hard_blockers": [],
        }

    return {
        "lane": "UNASSIGNED",
        "decision": "UNDECIDED",
        "decision_rationale": (
            "Insufficient structured coverage to assign a confident lane/decision."
        ),
        "hard_blockers": [],
    }
