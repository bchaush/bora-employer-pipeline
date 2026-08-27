"""Bounded lane/decision routing for Job Analysis v1.

Explainable from hard blockers, mandatory coverage, role-family fit, and gaps.
Does not emit hire-probability percentages.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


SUPPORTED_ROLE_FAMILY_TOKENS = (
    "business systems",
    "implementation",
    "data operations",
    "business process",
    "digital solutions",
    "technical operations",
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
) -> list[str]:
    """Return human-readable hard blockers present in the analyzed role."""
    blockers: list[str] = []
    jd = jd_text.casefold() if isinstance(jd_text, str) else ""

    blockers.extend(
        detect_seniority_signals(role=role, jd_text=jd_text, seniority=seniority)
    )

    if re.search(
        r"\b(us\s+citizen|u\.s\.\s+citizen|security clearance|secret clearance|"
        r"top secret|must be a citizen)\b",
        jd,
    ):
        blockers.append("Citizenship or clearance requirement present in JD")

    match_by_req = {
        m["requirement_id"]: m for m in matches if isinstance(m.get("requirement_id"), str)
    }

    for requirement in requirements:
        if requirement.get("importance") != "MANDATORY":
            continue
        if requirement.get("relevance") != "HIGH":
            continue
        req_id = requirement.get("requirement_id")
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
        if re.search(r"\b(salesforce|google\s+cloud|gcp)\b", blob):
            blockers.append(
                f"Unsupported core platform specialization (mandatory HIGH): {req_id}"
            )
            continue

        # Generalized core mandatory HIGH / NONE blocker.
        blockers.append(
            f"Unsupported core mandatory HIGH requirement: {req_id}"
        )

    return blockers


def role_family_fit(role_family: str | None) -> bool:
    family = (role_family or "").casefold()
    return any(token in family for token in SUPPORTED_ROLE_FAMILY_TOKENS)


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
) -> dict[str, Any]:
    """Compute lane, decision, and rationale from structured analysis facts."""
    blockers = detect_hard_blockers(
        requirements=requirements,
        matches=matches,
        seniority=seniority,
        role=role,
        jd_text=jd_text,
    )
    if blockers:
        return {
            "lane": "LANE_0_REJECT",
            "decision": "REJECT",
            "decision_rationale": "Hard blocker(s): " + "; ".join(blockers),
            "hard_blockers": blockers,
        }

    match_by_req = {
        m["requirement_id"]: m for m in matches if isinstance(m.get("requirement_id"), str)
    }

    mandatory = [
        r
        for r in requirements
        if r.get("importance") == "MANDATORY" and r.get("relevance") in {"HIGH", "MEDIUM"}
    ]
    preferred = [
        r
        for r in requirements
        if r.get("importance") == "PREFERRED" and r.get("relevance") in {"HIGH", "MEDIUM"}
    ]

    strong_or_supported = 0
    partial = 0
    none = 0
    high_none = 0
    for requirement in mandatory:
        req_id = requirement.get("requirement_id")
        match = match_by_req.get(req_id) if isinstance(req_id, str) else None
        result = match.get("result") if isinstance(match, Mapping) else "UNKNOWN"
        if result in {"STRONG", "SUPPORTED"}:
            strong_or_supported += 1
        elif result == "PARTIAL":
            partial += 1
        elif result == "NONE":
            none += 1
            if requirement.get("relevance") == "HIGH":
                high_none += 1

    preferred_missing = 0
    for requirement in preferred:
        req_id = requirement.get("requirement_id")
        match = match_by_req.get(req_id) if isinstance(req_id, str) else None
        result = match.get("result") if isinstance(match, Mapping) else "UNKNOWN"
        if result in {"NONE", "UNKNOWN"}:
            preferred_missing += 1

    family_fit = role_family_fit(role_family)
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
        if none >= 1 or strong_or_supported == 0:
            return {
                "lane": "LANE_0_REJECT",
                "decision": "REJECT",
                "decision_rationale": (
                    f"Role family {role_family!r} is outside supported/adjacent "
                    "families and lacks sufficient transferable coverage."
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

    if (
        family_fit
        and strong_or_supported >= 2
        and none == 0
        and partial <= 1
        and preferred_missing <= 1
    ):
        return {
            "lane": "LANE_2_PRIORITY_APPLY",
            "decision": "PRIORITY_APPLY",
            "decision_rationale": (
                "Strong Business Systems/Implementation-family coverage with "
                f"{strong_or_supported} STRONG/SUPPORTED mandatory matches and "
                "no hard mandatory NONE gaps."
            ),
            "hard_blockers": [],
        }

    if family_fit and strong_or_supported >= 1 and none == 0 and preferred_missing >= 1:
        return {
            "lane": "LANE_1_EFFICIENT_APPLY",
            "decision": "EFFICIENT_APPLY",
            "decision_rationale": (
                "Core mandatory coverage present; preferred skill(s) missing "
                f"(preferred_missing={preferred_missing}) but role remains viable."
            ),
            "hard_blockers": [],
        }

    if family_fit and strong_or_supported >= 1 and none == 0:
        return {
            "lane": "LANE_1_EFFICIENT_APPLY",
            "decision": "APPLY",
            "decision_rationale": (
                "Adequate mandatory coverage for an APPLY decision "
                f"(strong_or_supported={strong_or_supported}, mandatory_none={none}, "
                f"gaps={len(gaps)}, unknowns={len(unknowns)})."
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
