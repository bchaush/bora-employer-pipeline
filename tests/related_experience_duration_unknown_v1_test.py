"""Regression tests for PATHWARD_RELATED_EXPERIENCE_MAXIMUM_V1.

Root cause: the real, live Pathward, N.A. Partner Quality Specialist I
posting states "Typically requires less than one year of related
experience." (REQ_PW_EXP). This text names no technology, no capability
pattern, and no structured domain, so requirement_match.py's
empty-capability fallback returns NONE -- a fabricated disproof, since no
comparison against candidate duration or candidate relatedness was ever
actually performed, and "related experience" is deliberately not treated
as a synonym for the generic "work experience" already owned by
experience_range.py, nor forced into domain_qualified_duration.py's
domain-qualified grammar (the employer's own text names no domain). This
module adds a narrow related-experience-duration evaluator
(src/related_experience_duration.py), wired into job_analysis.py, that
recognizes exactly this requirement class and honestly reports UNKNOWN
instead.

Exercises real production code (related_experience_duration.py,
job_analysis.py, requirement_match.py, experience_range.py,
domain_qualified_duration.py, job_decision.py) against bounded synthetic
cases mirroring the live Pathward text -- no logic is duplicated here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domain_qualified_duration import is_domain_qualified_duration_requirement  # noqa: E402
from experience_range import is_generic_experience_range_requirement  # noqa: E402
from job_analysis import _build_gaps_and_unknowns, analyze_job  # noqa: E402
from job_decision import detect_hard_blockers  # noqa: E402
from related_experience_duration import (  # noqa: E402
    evaluate_related_experience_duration_requirement,
    is_related_experience_duration_requirement,
    parse_related_experience_duration,
)
from requirement_match import infer_requirement_capabilities  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def _req(
    text: str,
    *,
    technology: list | None = None,
    domain: str | None = None,
    req_id: str = "REQ_ROUTING_TEST",
    importance: str = "MANDATORY",
) -> dict:
    # Mirrors experience_range_semantics_v1_test.py's `_req` helper: a
    # full, schema-shaped requirement row stamped ENTRY_QUALIFICATION so
    # this file's subject (related-experience-duration routing) is never
    # hidden behind an unrelated source-semantic-role classification gap.
    return {
        "requirement_id": req_id,
        "text": text,
        "source_text": text,
        "source_location": "Requirements",
        "domain": domain,
        "category": "EXPERIENCE",
        "technology": technology or [],
        "experience_level": None,
        "seniority_implication": None,
        "relevance": "HIGH",
        "importance": importance,
        "source_semantic_role": "ENTRY_QUALIFICATION",
        "source_semantic_role_basis": "legacy test fixture -- pre-migration adjudication for a related-experience-duration-style requirement.",
        "explicit_prerequisite_language_present": True,
        "duplicated_under_requirements": False,
        "source_semantic_role_classifier_version": "SOURCE_SEMANTIC_ROLE_CLASSIFIER_V1",
    }


PATHWARD_TEXT = "Typically requires less than one year of related experience."


# ======================================================================
# A. Pre-fix reproduction proof -- confirm the real Pathward text names
#    no technology and infers no capabilities (root-cause conditions for
#    the fabricated NONE this milestone fixes).
# ======================================================================
pw_row = _req(PATHWARD_TEXT, req_id="REQ_PW_EXP")
pw_caps = infer_requirement_capabilities(pw_row)
assert_true(not pw_caps, f"Pathward text must infer no capabilities (root-cause proof), got {pw_caps}")
assert_true(pw_row["technology"] == [], "Pathward row must carry empty technology")
assert_true(pw_row["domain"] is None, "Pathward row must carry no structured domain")
print("PASS A: real Pathward text confirmed technology-free, domain-free, with empty inferred capabilities (root-cause reproduction).")


# ======================================================================
# B. Routing predicate proof + parsed-structure proof on the exact
#    Pathward text.
# ======================================================================
assert_true(
    is_related_experience_duration_requirement(pw_row, inferred_capabilities=pw_caps),
    "REQ_PW_EXP must be routable to the new evaluator",
)
pw_parsed = parse_related_experience_duration(PATHWARD_TEXT)
assert_true(pw_parsed is not None, "Pathward text must parse")
assert_true(pw_parsed["lower_bound"] == 0, f"Pathward lower_bound must be 0, got {pw_parsed}")
assert_true(pw_parsed["upper_bound"] == 1, f"Pathward upper_bound must be 1, got {pw_parsed}")
assert_true(pw_parsed["upper_bound_inclusive"] is False, f"Pathward upper_bound_inclusive must be False (exclusive 'less than'), got {pw_parsed}")
print("PASS B: real Pathward text is routed to the new evaluator and parses to lower_bound=0/upper_bound=1/exclusive.")


# ======================================================================
# C. Result semantics -- the evaluator must return only UNKNOWN, never
#    NONE/PARTIAL/SUPPORTED/STRONG, carry no fabricated provenance, and
#    state both open questions (candidate duration + relatedness).
# ======================================================================
pw_match = evaluate_related_experience_duration_requirement(job_id="JOB_PW_TEST", requirement=pw_row, match_index=0)
assert_true(pw_match["result"] == "UNKNOWN", f"REQ_PW_EXP evaluator result must be UNKNOWN, got {pw_match['result']}")
assert_true(pw_match["evidence_ids"] == [] and pw_match["claim_ids"] == [], "evaluator must never assert evidence/claim provenance")
assert_true(pw_match["evaluation_path"] == "RELATED_EXPERIENCE_DURATION_EVALUATOR", f"evaluation_path must be RELATED_EXPERIENCE_DURATION_EVALUATOR, got {pw_match['evaluation_path']}")
explanation_lower = pw_match["explanation"].lower()
assert_true("duration" in explanation_lower, "explanation must address candidate duration")
assert_true("relat" in explanation_lower, "explanation must address relatedness")
for forbidden in ("lacks", "insufficient", "unsupported", "gap", "deficien"):
    assert_true(forbidden not in explanation_lower, f"explanation must never use candidate-deficiency language ({forbidden!r})")
print("PASS C: evaluator returns only UNKNOWN, no fabricated evidence/claim provenance, states both open questions, no deficiency language.")


# ======================================================================
# D. Required positive grammar controls (locked contract).
# ======================================================================
positive_cases = {
    "Typically requires less than one year of related experience.": {"lower_bound": 0, "upper_bound": 1, "upper_bound_inclusive": False},
    "less than 1 year of related experience": {"lower_bound": 0, "upper_bound": 1, "upper_bound_inclusive": False},
    "fewer than one year of related experience": {"lower_bound": 0, "upper_bound": 1, "upper_bound_inclusive": False},
    "up to 1 year of related experience": {"lower_bound": 0, "upper_bound": 1, "upper_bound_inclusive": True},
    "0-1 years of related experience": {"lower_bound": 0, "upper_bound": 1, "upper_bound_inclusive": True},
    "0–1 years of related experience": {"lower_bound": 0, "upper_bound": 1, "upper_bound_inclusive": True},
}
for text, expected in positive_cases.items():
    parsed = parse_related_experience_duration(text)
    assert_true(parsed is not None, f"{text!r} must parse as a related-experience duration")
    for key, value in expected.items():
        assert_true(parsed[key] == value, f"{text!r}: expected {key}={value}, got {parsed[key]}")
    row = _req(text)
    caps = infer_requirement_capabilities(row)
    assert_true(
        is_related_experience_duration_requirement(row, inferred_capabilities=caps),
        f"{text!r} must route to the new evaluator",
    )
    match = evaluate_related_experience_duration_requirement(job_id="JOB_TEST", requirement=row, match_index=0)
    assert_true(match["result"] == "UNKNOWN", f"{text!r} must resolve UNKNOWN, got {match['result']}")
print("PASS D: all required positive related-experience-duration grammar controls parse, route, and resolve UNKNOWN.")


# ======================================================================
# E. Protected negatives -- must never route to the new evaluator.
# ======================================================================
protected_negatives = (
    ("less than one year of Salesforce administration experience", None, ["Salesforce"]),
    ("less than one year of UAT experience", None, None),
    ("less than one year of financial-services experience", None, None),
    ("less than one year of regulatory compliance experience", None, None),
    ("less than one year of customer-facing implementation experience", None, None),
    ("less than one year of work experience", None, None),
    ("less than one year of experience", None, None),
)
for text, domain, technology in protected_negatives:
    row = _req(text, domain=domain, technology=technology)
    caps = infer_requirement_capabilities(row)
    assert_true(
        not is_related_experience_duration_requirement(row, inferred_capabilities=caps),
        f"{text!r} must NOT be routed to the related-experience-duration evaluator",
    )
print("PASS E: all protected-negative phrasings (Salesforce, UAT, financial-services, regulatory compliance, customer-facing implementation, generic work experience, bare experience) stay out of the new evaluator.")


# ======================================================================
# F. Ownership-boundary controls -- generic "up to 1 year of work
#    experience" stays owned by experience_range.py; a domain-qualified
#    related-experience row (employer explicitly names a domain) stays
#    owned by domain_qualified_duration.py, not this module.
# ======================================================================
generic_control = _req("up to 1 year of work experience")
generic_caps = infer_requirement_capabilities(generic_control)
assert_true(
    is_generic_experience_range_requirement(generic_control, inferred_capabilities=generic_caps),
    "generic 'up to 1 year of work experience' must remain owned by experience_range.py",
)
assert_true(
    not is_related_experience_duration_requirement(generic_control, inferred_capabilities=generic_caps),
    "generic 'up to 1 year of work experience' must never route to the new evaluator",
)

domain_related = _req("less than one year of related experience", domain="Financial Services")
domain_related_caps = infer_requirement_capabilities(domain_related)
assert_true(
    not is_related_experience_duration_requirement(domain_related, inferred_capabilities=domain_related_caps),
    "a related-experience row with an explicit structured domain must stay OUT of this evaluator",
)
print("PASS F: generic work-experience and explicitly domain-qualified related-experience rows remain with their existing owners.")


# ======================================================================
# G. Scope controls -- positive-minimum related-experience text and
#    inverted/non-zero-based ranges are out of scope for V1.
# ======================================================================
positive_minimum = _req("3+ years of related experience")
positive_minimum_caps = infer_requirement_capabilities(positive_minimum)
assert_true(
    not is_related_experience_duration_requirement(positive_minimum, inferred_capabilities=positive_minimum_caps),
    "a positive-minimum 'related experience' condition must not be recognized by V1",
)
assert_true(parse_related_experience_duration("3+ years of related experience") is None, "positive-minimum related-experience text must not parse")

for bad_range in ("1-2 years of related experience", "2-1 years of related experience"):
    assert_true(parse_related_experience_duration(bad_range) is None, f"{bad_range!r} must not parse as a zero-based band")
print("PASS G: positive-minimum and non-zero-based/inverted related-experience ranges are correctly out of scope for V1.")


# ======================================================================
# H. Unrelated sentence containing "related"/"experience"/"years".
# ======================================================================
unrelated = _req("Prior related industry experience is valued by the team")
unrelated_caps = infer_requirement_capabilities(unrelated)
assert_true(
    not is_related_experience_duration_requirement(unrelated, inferred_capabilities=unrelated_caps),
    "an unrelated sentence merely containing 'related'/'experience' must not route",
)
print("PASS H: unrelated sentence containing 'related'/'experience' without the structural grammar is not routed.")


# ======================================================================
# I. PREFERRED-importance control -- never becomes a hard blocker or gap,
#    resolves as an unknown.
# ======================================================================
preferred_row = _req(PATHWARD_TEXT, req_id="REQ_PREF_TEST", importance="PREFERRED")
preferred_caps = infer_requirement_capabilities(preferred_row)
assert_true(
    is_related_experience_duration_requirement(preferred_row, inferred_capabilities=preferred_caps),
    "PREFERRED related-experience-duration requirement must still be routed to the evaluator",
)
match_pref = evaluate_related_experience_duration_requirement(job_id="JOB_PREF_TEST", requirement=preferred_row, match_index=0)
assert_true(match_pref["result"] == "UNKNOWN", "PREFERRED related-experience-duration requirement must resolve UNKNOWN")
gaps, unknowns = _build_gaps_and_unknowns([preferred_row], [match_pref])
assert_true(gaps == [], f"PREFERRED related-experience-duration requirement must not produce a gap; got {gaps}")
assert_true(len(unknowns) == 1, f"PREFERRED related-experience-duration requirement must be reported as an unknown; got {unknowns}")
print("PASS I: PREFERRED related-experience-duration requirement resolves UNKNOWN and never becomes a gap.")


# ======================================================================
# J. MANDATORY/HIGH REQ_PW_EXP-shaped row: gaps/unknowns and
#    detect_hard_blockers() confirm it never becomes a gap or hard
#    blocker.
# ======================================================================
gaps_pw, unknowns_pw = _build_gaps_and_unknowns([pw_row], [pw_match])
assert_true(gaps_pw == [], f"REQ_PW_EXP must never produce a qualification gap; got {gaps_pw}")
assert_true(len(unknowns_pw) == 1, f"REQ_PW_EXP must be reported as a qualification unknown; got {unknowns_pw}")

blockers_pw = detect_hard_blockers(
    requirements=[pw_row],
    matches=[pw_match],
    seniority=None,
    role="Partner Quality Specialist I",
    jd_text=PATHWARD_TEXT,
)
assert_true(
    not any("REQ_PW_EXP" in b for b in blockers_pw),
    f"REQ_PW_EXP must never appear as a hard blocker; got {blockers_pw}",
)
print("PASS J: MANDATORY/HIGH REQ_PW_EXP-shaped row is absent from qualification_gaps and hard_blockers.")


# ======================================================================
# K. Real end-to-end proof: analyze_job() on a synthetic job input
#    carrying the exact live Pathward requirement text, alongside an
#    ordinary supported requirement -- proves REQ_PW_EXP resolves
#    UNKNOWN/RELATED_EXPERIENCE_DURATION_EVALUATOR through the real
#    production path, is absent from qualification_gaps/hard_blockers,
#    and manufactures no positive candidate support.
# ======================================================================
JD_TEXT = (
    "Partner Quality Specialist I\n\n"
    "Qualifications:\n"
    "- Typically requires less than one year of related experience.\n"
    "- Excellent written and verbal communication skills.\n"
)

pathward_structured = {
    "role_family": "Quality Assurance",
    "seniority": "ENTRY",
    "requirements": [
        _req(PATHWARD_TEXT, req_id="REQ_PW_EXP"),
        _req(
            "Excellent written and verbal communication skills.",
            req_id="REQ_PW_COMMS",
            importance="PREFERRED",
        ),
    ],
}

pathward_job_input = {
    "company": "Pathward, N.A.",
    "role": "Partner Quality Specialist I",
    "jd_text": JD_TEXT,
    "structured_extraction": pathward_structured,
    "fixture_key": "PATHWARD_RELATED_EXPERIENCE_MAXIMUM_V1_SYNTH",
    "role_status": "VERIFIED_LIVE",
    "source_verification_status": "VERIFIED_DIRECT",
    "operation_run_id": "RUN_PATHWARD_RELATED_EXPERIENCE_MAXIMUM_V1",
    "official_url": "https://careers.example.test/jobs/pathward-partner-quality-specialist-i",
    "date_last_verified": "2026-09-15",
    "pre_surfacing_verification": {
        "verification_kind": "JIT_PRE_SURFACING_VERIFICATION_V1",
        "operation_run_id": "RUN_PATHWARD_RELATED_EXPERIENCE_MAXIMUM_V1",
        "observed_at": "2026-09-15T12:00:00-04:00",
        "source_kind": "FIRST_PARTY_DIRECT",
        "exact_url": "https://careers.example.test/jobs/pathward-partner-quality-specialist-i",
        "observed_company": "Pathward, N.A.",
        "observed_role": "Partner Quality Specialist I",
        "substantive_role_content_present": True,
        "application_route_status": "ACTIONABLE",
        "recency_observation": {
            "state": "AUTHORITATIVE_ABSOLUTE_DATE",
            "source_kind": "FIRST_PARTY_DIRECT",
            "observed_at": "2026-09-15T12:00:00-04:00",
            "posted_date": "2026-09-14",
        },
        "material_conflicts": [],
        "resolved_conflicts": [],
    },
}

result_pw = analyze_job(pathward_job_input)
assert_true(result_pw["valid"] is True, f"synthetic Pathward analysis must be valid: {result_pw['errors']}")
analysis_pw = result_pw["analysis"]

match_pw_real = next(m for m in analysis_pw["evidence_matches"] if m["requirement_id"] == "REQ_PW_EXP")
assert_true(match_pw_real["result"] == "UNKNOWN", f"REQ_PW_EXP must resolve UNKNOWN end-to-end, got {match_pw_real['result']}")
assert_true(
    match_pw_real["evaluation_path"] == "RELATED_EXPERIENCE_DURATION_EVALUATOR",
    f"REQ_PW_EXP evaluation_path must be RELATED_EXPERIENCE_DURATION_EVALUATOR end-to-end, got {match_pw_real['evaluation_path']}",
)

assert_true(
    not any("REQ_PW_EXP" in g for g in analysis_pw["qualification_gaps"]),
    f"REQ_PW_EXP must leave qualification_gaps, got {analysis_pw['qualification_gaps']}",
)
assert_true(
    any("REQ_PW_EXP" in u for u in analysis_pw["qualification_unknowns"]),
    f"REQ_PW_EXP must enter qualification_unknowns, got {analysis_pw['qualification_unknowns']}",
)
assert_true(
    not any("REQ_PW_EXP" in b for b in result_pw["hard_blockers"]),
    f"REQ_PW_EXP must never independently hard-block, got {result_pw['hard_blockers']}",
)
assert_true(
    match_pw_real["evidence_ids"] == [] and match_pw_real["claim_ids"] == [],
    "REQ_PW_EXP must never carry fabricated Evidence/Claim provenance end-to-end",
)
print("PASS K: real end-to-end analyze_job() on the exact live Pathward requirement text resolves UNKNOWN/RELATED_EXPERIENCE_DURATION_EVALUATOR, absent from qualification_gaps and hard_blockers, with no fabricated provenance.")


# ======================================================================
# L. Real end-to-end regression -- the same synthetic job's
#    domain-qualified and generic experience-range ownership boundaries
#    are unaffected by this module's routing addition.
# ======================================================================
assert_true(
    is_domain_qualified_duration_requirement(
        _req("Three (3) years of experience in system analysis, including support.", domain="System Analysis"),
        inferred_capabilities=frozenset(),
    ),
    "domain_qualified_duration.py ownership must remain unaffected by this module",
)
assert_true(
    is_generic_experience_range_requirement(
        _req("0-2 years of work experience"),
        inferred_capabilities=frozenset(),
    ),
    "experience_range.py ownership must remain unaffected by this module",
)
print("PASS L: domain_qualified_duration.py and experience_range.py ownership boundaries remain unaffected.")


print("ALL related_experience_duration_unknown_v1_test CHECKS PASSED")
