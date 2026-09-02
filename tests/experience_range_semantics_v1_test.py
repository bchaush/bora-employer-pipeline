"""Regression tests for EXPERIENCE_RANGE_SEMANTICS_V1.

Frozen Atominvest's "0-2 years of work experience" (REQ_A_EXPERIENCE_LEVEL)
was routed through the generic capability matcher, which correctly infers
zero capability tags (there is no skill/tool/domain to prove), and then
falls back to NONE for a MANDATORY+HIGH requirement -- a false hard blocker,
since the range's lower bound (0) is trivially satisfied by any candidate
and no code in this repository computes a canonical candidate
years-of-experience figure at all.

This file proves, test-first, that the defect is real through the actual
production analyze_job() path, then proves the new src/experience_range.py
module (routed from src/job_analysis.py; requirement_match.py itself is
untouched) resolves it honestly: UNKNOWN, never a fabricated NONE, and never
a fabricated positive. It also proves domain/platform-specific years
requirements (SAP, Salesforce, UAT, "customer-facing implementation
experience") are never hijacked into this evaluator.

Exercises real production code -- no logic is duplicated here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from experience_range import (  # noqa: E402
    evaluate_generic_experience_range,
    is_generic_experience_range_requirement,
    parse_generic_experience_range,
)
from job_analysis import analyze_job  # noqa: E402
from requirement_match import infer_requirement_capabilities  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_A = ROOT / "fixtures" / "jobs" / "CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST"
FIXTURE_C = ROOT / "fixtures" / "jobs" / "CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST"


def _load_job_input(fixture_dir: Path) -> dict:
    job = json.loads((fixture_dir / "job.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_input = dict(job)
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    return job_input


# ======================================================================
# A. Frozen Atominvest REQ_A_EXPERIENCE_LEVEL through the real analyze_job()
#    path resolves UNKNOWN, and no longer contributes a hard blocker; the
#    other genuine blockers remain (SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1,
#    post-dating this milestone, later removed REQ_A_CONFIG_IMPLEMENTATION/
#    REQ_A_QA_TROUBLESHOOTING as responsibility-sourced false blockers,
#    leaving REQ_A_DEGREE/REQ_A_EXCEL_DATA); overall routing is unchanged
#    (LANE_0_REJECT/REJECT), because claims remain unapproved.
# ======================================================================
result_a = analyze_job(_load_job_input(FIXTURE_A))
assert_true(result_a["valid"] is True, f"Atominvest analysis must be valid: {result_a['errors']}")
analysis_a = result_a["analysis"]
matches_by_req = {m["requirement_id"]: m for m in analysis_a["evidence_matches"]}
assert_true(
    matches_by_req["REQ_A_EXPERIENCE_LEVEL"]["result"] == "UNKNOWN",
    f"REQ_A_EXPERIENCE_LEVEL must resolve UNKNOWN, got {matches_by_req['REQ_A_EXPERIENCE_LEVEL']['result']}",
)
assert_true(
    "CANDIDATE_EXPERIENCE_DURATION_NOT_YET_CANONICAL" in matches_by_req["REQ_A_EXPERIENCE_LEVEL"]["explanation"],
    "REQ_A_EXPERIENCE_LEVEL explanation must state candidate duration is not canonical",
)
hard_blockers = result_a["hard_blockers"]
assert_true(
    not any("REQ_A_EXPERIENCE_LEVEL" in b for b in hard_blockers),
    f"REQ_A_EXPERIENCE_LEVEL must no longer appear as a hard blocker; got {hard_blockers}",
)
expected_remaining = {
    "REQ_A_DEGREE",
    "REQ_A_EXCEL_DATA",
}
remaining_blocked_ids = {b.rsplit(": ", 1)[-1] for b in hard_blockers}
assert_true(
    remaining_blocked_ids == expected_remaining,
    f"remaining blockers must be exactly {expected_remaining}, got {remaining_blocked_ids}",
)
assert_true(
    analysis_a["lane"] == "LANE_0_REJECT" and analysis_a["decision"] == "REJECT",
    f"Atominvest overall routing must remain LANE_0_REJECT/REJECT, got {analysis_a['lane']}/{analysis_a['decision']}",
)
print("PASS A: frozen Atominvest REQ_A_EXPERIENCE_LEVEL resolves UNKNOWN (not NONE), no longer a hard blocker; the other 4 blockers and overall REJECT routing are unchanged.")


# ======================================================================
# B. Range-parser positive cases (Section 15).
# ======================================================================
positive_cases = {
    "0-2 years of work experience": {"lower_bound": 0, "upper_bound": 2, "range_type": "RANGE"},
    "0–2 years of work experience": {"lower_bound": 0, "upper_bound": 2, "range_type": "RANGE"},
    "1-3 years of work experience": {"lower_bound": 1, "upper_bound": 3, "range_type": "RANGE"},
    "2+ years of work experience": {"lower_bound": 2, "upper_bound": None, "range_type": "MINIMUM"},
    "at least 3 years of work experience": {"lower_bound": 3, "upper_bound": None, "range_type": "MINIMUM"},
    "up to 2 years of work experience": {"lower_bound": 0, "upper_bound": 2, "range_type": "MAXIMUM"},
    "no more than 3 years of work experience": {"lower_bound": 0, "upper_bound": 3, "range_type": "MAXIMUM"},
}
for text, expected in positive_cases.items():
    parsed = parse_generic_experience_range(text)
    assert_true(parsed is not None, f"{text!r} must parse as a generic experience range")
    for key, value in expected.items():
        assert_true(
            parsed[key] == value,
            f"{text!r}: expected {key}={value}, got {parsed[key]}",
        )
print("PASS B: all 7 required generic experience-range positive parsing cases resolve correctly.")


# ======================================================================
# C. Routing negatives (Section 16 + Cursor-expanded coverage) --
#    domain/platform-specific years requirements must never be routed to
#    the generic evaluator.
# ======================================================================
def _req(text: str, technology: list | None = None, domain: str | None = None) -> dict:
    # SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1: this file's synthetic
    # rows are all years-of-experience/domain-specific-experience wording --
    # genuine entry-qualification territory, unrelated to responsibility-duty
    # semantics. Stamped ENTRY_QUALIFICATION explicitly (a missing role now
    # derives AMBIGUOUS/non-blocking, which would hide this file's actual
    # subject -- generic-experience-range routing -- behind an unrelated
    # classification gap).
    return {
        "requirement_id": "REQ_ROUTING_TEST",
        "text": text,
        "source_text": text,
        "source_location": "Requirements",
        "domain": domain,
        "category": "EXPERIENCE",
        "technology": technology or [],
        "relevance": "HIGH",
        "importance": "MANDATORY",
        "source_semantic_role": "ENTRY_QUALIFICATION",
        "source_semantic_role_basis": "legacy test fixture -- pre-migration adjudication for a years-of-experience-style requirement.",
        "explicit_prerequisite_language_present": True,
        "duplicated_under_requirements": False,
        "source_semantic_role_classifier_version": "SOURCE_SEMANTIC_ROLE_CLASSIFIER_V1",
    }


routing_negatives = (
    ("5+ years of SAP FI/CO experience", ["SAP FI/CO"]),
    ("3 years of Salesforce administration", ["Salesforce"]),
    ("2+ years of customer-facing implementation experience", None),
    ("3 years of UAT experience", None),
    ("2 years of financial services experience", None),
    ("3+ years of banking experience", None),
    ("2 years of project management experience", None),
    ("4 years of software development experience", None),
)
for text, tech in routing_negatives:
    requirement = _req(text, tech)
    caps = infer_requirement_capabilities(requirement)
    routed = is_generic_experience_range_requirement(requirement, inferred_capabilities=caps)
    assert_true(
        routed is False,
        f"{text!r} must NOT be routed to the generic experience-range evaluator",
    )
print("PASS C: domain/platform-specific and function-specific years requirements (SAP, Salesforce, customer-facing implementation, UAT, financial services, banking, project management, software development) are never hijacked into the generic evaluator.")


# ======================================================================
# D. MIT SAP FI/CO named-platform protection unaffected by the new
#    evaluator (frozen fixture, real analyze_job() path).
# ======================================================================
result_c = analyze_job(_load_job_input(FIXTURE_C))
assert_true(result_c["valid"] is True, f"MIT analysis must be valid: {result_c['errors']}")
analysis_c = result_c["analysis"]
matches_by_req_c = {m["requirement_id"]: m for m in analysis_c["evidence_matches"]}
assert_true(
    matches_by_req_c["REQ_C_SAP_FICO"]["result"] == "NONE",
    f"MIT REQ_C_SAP_FICO must remain NONE, got {matches_by_req_c['REQ_C_SAP_FICO']['result']}",
)
assert_true(
    analysis_c["lane"] == "LANE_0_REJECT" and analysis_c["decision"] == "REJECT",
    "MIT overall routing must remain LANE_0_REJECT/REJECT",
)
print("PASS D: frozen MIT SAP FI/CO named-platform protection is unaffected by the new evaluator.")


# ======================================================================
# E. PREFERRED generic-range requirement never becomes a new hard
#    blocker -- resolves UNKNOWN and is reported as an unknown, not a gap.
# ======================================================================
from job_analysis import _build_gaps_and_unknowns  # noqa: E402

preferred_req = _req("0-2 years of work experience")
preferred_req["importance"] = "PREFERRED"
caps_pref = infer_requirement_capabilities(preferred_req)
assert_true(
    is_generic_experience_range_requirement(preferred_req, inferred_capabilities=caps_pref),
    "PREFERRED generic experience-range requirement must still be routed to the evaluator",
)
match_pref = evaluate_generic_experience_range(job_id="JOB_PREF_TEST", requirement=preferred_req, match_index=0)
assert_true(match_pref["result"] == "UNKNOWN", "PREFERRED generic experience-range requirement must resolve UNKNOWN")
gaps, unknowns = _build_gaps_and_unknowns([preferred_req], [match_pref])
assert_true(gaps == [], f"PREFERRED generic experience-range requirement must not produce a gap; got {gaps}")
assert_true(len(unknowns) == 1, f"PREFERRED generic experience-range requirement must be reported as an unknown; got {unknowns}")
print("PASS E: PREFERRED generic experience-range requirement resolves UNKNOWN and never becomes a hard blocker.")


# ======================================================================
# F. Generic requirements-gathering control (Winter Walk) unaffected --
#    confirms routing does not interfere with ordinary capability matching.
# ======================================================================
generic_req = _req("Gather business requirements from stakeholders")
caps_generic = infer_requirement_capabilities(generic_req)
assert_true(
    is_generic_experience_range_requirement(generic_req, inferred_capabilities=caps_generic) is False,
    "generic requirements-gathering text must not be routed to the experience-range evaluator",
)
print("PASS F: generic requirements-gathering text is correctly excluded from experience-range routing.")


# ======================================================================
# G. BOUNDED CORRECTION -- structured domain-metadata non-hijack (Cursor
#    DEFECT 1: STRUCTURED_DOMAIN_METADATA_FALSE_REROUTE). A requirement
#    whose raw text reads as plain "N years of work experience" but whose
#    structured `domain` field names a specialization must NOT be routed
#    to the generic evaluator -- the specialization lives in metadata the
#    raw text alone does not carry.
# ======================================================================
domain_specialization_variants = (
    ("3+ years of work experience", "Financial Services"),
    ("3+ years of work experience", "Implementation"),
)
for text, domain in domain_specialization_variants:
    requirement = _req(text, domain=domain)
    caps = infer_requirement_capabilities(requirement)
    routed = is_generic_experience_range_requirement(requirement, inferred_capabilities=caps)
    assert_true(
        routed is False,
        f"{text!r} with domain={domain!r} must NOT be routed -- structured domain metadata specializes the requirement even though the raw text is generic",
    )
# The same plain text with domain=None must still route -- confirms the
# guard is domain-specific, not a blanket rejection of otherwise-generic text.
control_requirement = _req("3+ years of work experience", domain=None)
control_caps = infer_requirement_capabilities(control_requirement)
assert_true(
    is_generic_experience_range_requirement(control_requirement, inferred_capabilities=control_caps) is True,
    "the same plain 'years of work experience' text with domain=None must still route (the guard targets domain specialization, not generic text itself)",
)
print("PASS G: structured domain-metadata specialization (Financial Services, Implementation) correctly prevents false rerouting; the same text with domain=None still routes.")


# ======================================================================
# H. BOUNDED CORRECTION -- inverted range rejection (Cursor DEFECT 2:
#    INVERTED_RANGE_ACCEPTED). "3-1 years" and "5-0 years" are malformed,
#    not valid ranges with swapped bounds -- the parser must refuse to
#    recognize them rather than silently correcting or accepting them.
# ======================================================================
for text in ("3-1 years of work experience", "5-0 years of work experience"):
    assert_true(
        parse_generic_experience_range(text) is None,
        f"{text!r} is an inverted range and must not parse",
    )
    requirement = _req(text)
    caps = infer_requirement_capabilities(requirement)
    assert_true(
        is_generic_experience_range_requirement(requirement, inferred_capabilities=caps) is False,
        f"{text!r} is an inverted range and must not be routed to the generic evaluator",
    )
print("PASS H: inverted ranges ('3-1 years', '5-0 years') are correctly refused, not silently corrected or accepted.")


# ======================================================================
# I. Valid equal-bound and zero-bound ranges remain recognized (boundary
#    cases adjacent to the inverted-range fix -- lower_bound <= upper_bound
#    must still accept lower == upper).
# ======================================================================
equal_range = parse_generic_experience_range("2-2 years of work experience")
assert_true(
    equal_range is not None and equal_range["lower_bound"] == 2 and equal_range["upper_bound"] == 2,
    f"'2-2 years of work experience' must parse as a valid equal-bound range; got {equal_range}",
)
zero_range = parse_generic_experience_range("0-0 years of work experience")
assert_true(
    zero_range is not None and zero_range["lower_bound"] == 0 and zero_range["upper_bound"] == 0,
    f"'0-0 years of work experience' must parse as a valid zero-bound range; got {zero_range}",
)
print("PASS I: valid equal-bound ('2-2 years') and zero-bound ('0-0 years') ranges remain correctly recognized.")


# ======================================================================
# J. Ordering: evidence_matches are returned in normalized-Requirement
#    order despite the internal partition/rejoin, and every match
#    corresponds 1:1 to a unique Requirement_ID -- proven through the
#    real analyze_job() path against the frozen Atominvest fixture (which
#    genuinely contains one generic experience-range requirement mixed
#    among ordinary capability-matched ones).
# ======================================================================
requirement_ids_in_order = [r["requirement_id"] for r in analysis_a["requirements"]]
match_ids_in_order = [m["requirement_id"] for m in analysis_a["evidence_matches"]]
assert_true(
    len(match_ids_in_order) == len(set(match_ids_in_order)),
    "evidence_matches Requirement_IDs must be unique",
)
assert_true(
    match_ids_in_order == [rid for rid in requirement_ids_in_order if rid in set(match_ids_in_order)],
    f"evidence_matches must be returned in normalized-Requirement order; got {match_ids_in_order}",
)
print(f"PASS J: {len(requirement_ids_in_order)} normalized Requirements produced {len(match_ids_in_order)} unique, order-preserving EvidenceMatches.")

print("ALL experience_range_semantics_v1_test CHECKS PASSED")
