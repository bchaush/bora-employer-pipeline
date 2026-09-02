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


def apply_posting_state_routing(
    *,
    base_result: Mapping[str, Any],
    role_status: Any,
) -> dict[str, Any]:
    """Apply Blueprint Section 30 posting-state downgrade to an already-computed
    qualification decision (POSTING_STATE_DECISION_WIRING_V1).

    Posting reality and qualification truth are separate axes. This function
    runs strictly AFTER decide_lane_and_decision() has already produced its
    qualification-only result:

      - a qualification REJECT is never touched (a genuinely unqualified role
        stays REJECT regardless of posting freshness or its absence);
      - a decision that is already non-APPLY-like (e.g. an unrelated WATCH
        from information deficit) is never touched either -- posting-state
        routing only ever downgrades an APPLY-like result, and never
        rewrites an existing rationale;
      - role_status="VERIFIED_LIVE" or "LIKELY_LIVE" (and only those two
        exact strings) preserve an APPLY-like result unchanged;
      - every other role_status value downgrades an APPLY-like result
        (PRIORITY_APPLY/APPLY/EFFICIENT_APPLY) to WATCH -- never to REJECT.
        This deliberately includes: None/absent; the other canonical
        values UNCLEAR/POSSIBLY_STALE/CONFIRMED_CLOSED; an unrecognized
        string (e.g. "BOGUS"); and any non-string type (int/list/dict/
        bool). Missing or malformed posting-state evidence is treated the
        same as an explicit UNCLEAR -- the absence or invalidity of
        verification must not silently become a favorable actionable
        state (permanent project rule).
      - role_status is a str check gate BEFORE any set-membership test, so
        an unhashable raw value (e.g. a list) can never reach a hash-based
        lookup -- this function never raises for any input type. It never
        coerces or rewrites role_status itself; the surfaced role_status
        value is owned entirely by job_analysis.py.
      - Requirement-level matches, gaps, unknowns, and hard_blockers are
        never modified; only lane/decision/decision_rationale may change.
    """
    result = dict(base_result)

    if result.get("decision") not in _APPLY_LIKE_DECISIONS:
        return result
    if isinstance(role_status, str) and role_status in _LIVE_ROLE_STATES:
        return result

    if isinstance(role_status, str) and role_status in _POSTING_WATCH_STATES:
        reason = f"role_status={role_status}"
    elif isinstance(role_status, str):
        reason = f"role_status={role_status!r} is not a recognized posting-state value"
    elif role_status is None:
        reason = "role_status missing (no posting-state verification supplied)"
    else:
        reason = (
            f"role_status is not a valid posting-state string (got {type(role_status).__name__})"
        )

    result["lane"] = "WATCH"
    result["decision"] = "WATCH"
    result["decision_rationale"] = (
        f"{result.get('decision_rationale', '')} "
        f"Downgraded to WATCH: {reason} "
        "(Blueprint Section 30 -- posting status uncertain, unverified, or "
        "role not currently active; qualification result unchanged)."
    ).strip()
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
    mandatory = [
        r
        for r in requirements
        if r.get("importance") == "MANDATORY"
        and r.get("relevance") in {"HIGH", "MEDIUM"}
        and r.get("requirement_id") not in gated_requirement_ids
    ]
    preferred = [
        r
        for r in requirements
        if r.get("importance") == "PREFERRED"
        and r.get("relevance") in {"HIGH", "MEDIUM"}
        and r.get("requirement_id") not in gated_requirement_ids
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
