"""Regression tests for EDUCATION_FLOOR_SEMANTICS_V1.

Root cause: the real, live Mercer Advisors Portfolio Operations Specialist
posting states "High school diploma required." (REQ_MERCER_HS). No
capability pattern recognizes "high school diploma" at all, so the
unmodified capability matcher's empty-capability fallback would return a
fabricated NONE -- even though the candidate's only trusted awarded-
education fact, EDU_BRANDEIS_AWARDED_ATTESTATION_001 (an awarded Brandeis
M.S., OBSERVED-tier human attestation), is well above a high school floor.
This module adds a narrow education-floor evaluator
(src/education_floor.py), wired into job_analysis.py, that recognizes
exactly five plain positive minimum-education-level grammars and reports
SUPPORTED by ordered level -- never asserting literal possession of any
lower credential -- while leaving every field-of-study, accreditation,
equivalency, document-production, school-specific, license/certification,
doctoral/professional, and compound degree+experience phrasing, and every
explicit qualification-gate leaf, entirely with its existing owner.

Exercises real production code (education_floor.py, job_analysis.py,
requirement_match.py, qualification_gate.py, job_decision.py) against
bounded synthetic cases mirroring the live Mercer Advisors text -- no
logic is duplicated here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from education_floor import (  # noqa: E402
    EDUCATION_LEVEL_ORDER,
    evaluate_education_floor_requirement,
    is_education_floor_requirement,
    parse_education_floor,
)
from evidence_repository import validate_evidence_repository  # noqa: E402
from job_analysis import _build_gaps_and_unknowns, analyze_job  # noqa: E402
from job_decision import detect_hard_blockers  # noqa: E402
from requirement_match import infer_requirement_capabilities  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


ev_result = validate_evidence_repository()
assert_true(ev_result["valid"] is True, "evidence repository must be valid")
cl_result = validate_claim_repository()
assert_true(cl_result["valid"] is True, "claim repository must be valid")
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = cl_result["index"]

BRANDEIS_EVIDENCE_ID = "EDU_BRANDEIS_AWARDED_ATTESTATION_001"
UNWE_CLAIM_ID = "CLAIM_EDU_UNWE_001"


def _req(
    text: str,
    *,
    technology: list | None = None,
    domain: str | None = None,
    req_id: str = "REQ_ROUTING_TEST",
    importance: str = "MANDATORY",
    relevance: str = "HIGH",
) -> dict:
    # Mirrors related_experience_duration_unknown_v1_test.py's `_req`
    # helper: a full, schema-shaped requirement row stamped
    # ENTRY_QUALIFICATION so this file's subject (education-floor routing)
    # is never hidden behind an unrelated source-semantic-role
    # classification gap.
    return {
        "requirement_id": req_id,
        "text": text,
        "source_text": text,
        "source_location": "Requirements",
        "domain": domain,
        "category": "EDUCATION",
        "technology": technology or [],
        "experience_level": None,
        "seniority_implication": None,
        "relevance": relevance,
        "importance": importance,
        "source_semantic_role": "ENTRY_QUALIFICATION",
        "source_semantic_role_basis": "legacy test fixture -- pre-migration adjudication for an education-floor-style requirement.",
        "explicit_prerequisite_language_present": True,
        "duplicated_under_requirements": False,
        "source_semantic_role_classifier_version": "SOURCE_SEMANTIC_ROLE_CLASSIFIER_V1",
    }


POSITIVE_GRAMMARS = {
    "High school diploma required.": "HIGH_SCHOOL",
    "High school diploma or GED required.": "HIGH_SCHOOL",
    "Associate degree required.": "ASSOCIATE",
    "Bachelor's degree required.": "BACHELOR",
    "Master's degree required.": "MASTER",
}


# ======================================================================
# A. All five positives -- with the canonical awarded Brandeis M.S., every
#    positive grammar parses, routes, and resolves SUPPORTED, citing only
#    EDU_BRANDEIS_AWARDED_ATTESTATION_001, with minimum-level-satisfaction
#    phrasing (never possession of a literal lower credential).
# ======================================================================
for index, (text, expected_level) in enumerate(POSITIVE_GRAMMARS.items()):
    parsed = parse_education_floor(text)
    assert_true(parsed is not None, f"{text!r} must parse as an education floor")
    assert_true(
        parsed["required_level"] == expected_level,
        f"{text!r}: expected required_level={expected_level}, got {parsed['required_level']}",
    )

    row = _req(text, req_id=f"REQ_POS_{index}")
    caps = infer_requirement_capabilities(row)
    assert_true(
        is_education_floor_requirement(row, inferred_capabilities=caps, gated=False),
        f"{text!r} must route to EDUCATION_FLOOR_EVALUATOR",
    )

    match = evaluate_education_floor_requirement(
        job_id="JOB_TEST",
        requirement=row,
        match_index=0,
        evidence_index=EVIDENCE_INDEX,
    )
    assert_true(match["result"] == "SUPPORTED", f"{text!r} must resolve SUPPORTED, got {match['result']}")
    assert_true(
        match["evaluation_path"] == "EDUCATION_FLOOR_EVALUATOR",
        f"{text!r}: evaluation_path must be EDUCATION_FLOOR_EVALUATOR, got {match['evaluation_path']}",
    )
    assert_true(
        match["evidence_ids"] == [BRANDEIS_EVIDENCE_ID],
        f"{text!r}: evidence_ids must be exactly [{BRANDEIS_EVIDENCE_ID}], got {match['evidence_ids']}",
    )
    assert_true(match["claim_ids"] == [], f"{text!r}: claim_ids must be empty, got {match['claim_ids']}")
    explanation_lower = match["explanation"].lower()
    assert_true(
        "minimum" in explanation_lower and "level" in explanation_lower,
        f"{text!r}: explanation must be phrased as minimum-level satisfaction, got {match['explanation']!r}",
    )
print("PASS A: all five positive education-floor grammars resolve SUPPORTED with the awarded Brandeis M.S., citing only the canonical evidence, phrased as minimum-level satisfaction.")


# ======================================================================
# B. Ordered level sanity + below-floor / no-evidence states resolve
#    safely (never a crash, never fabricated support).
# ======================================================================
assert_true(
    EDUCATION_LEVEL_ORDER["HIGH_SCHOOL"]
    < EDUCATION_LEVEL_ORDER["ASSOCIATE"]
    < EDUCATION_LEVEL_ORDER["BACHELOR"]
    < EDUCATION_LEVEL_ORDER["MASTER"],
    "internal ordering must be HIGH_SCHOOL < ASSOCIATE < BACHELOR < MASTER",
)

# No-evidence state: an empty evidence_index must never fabricate support.
no_evidence_row = _req("Bachelor's degree required.", req_id="REQ_NO_EVIDENCE")
no_evidence_match = evaluate_education_floor_requirement(
    job_id="JOB_TEST",
    requirement=no_evidence_row,
    match_index=0,
    evidence_index={},
)
assert_true(
    no_evidence_match["result"] == "NONE",
    f"missing canonical evidence must resolve NONE, got {no_evidence_match['result']}",
)
assert_true(
    no_evidence_match["evidence_ids"] == [] and no_evidence_match["claim_ids"] == [],
    "NONE result must carry no fabricated provenance",
)
assert_true(
    no_evidence_match["evaluation_path"] == "EDUCATION_FLOOR_EVALUATOR",
    "NONE result must still be attributed to EDUCATION_FLOOR_EVALUATOR",
)
print("PASS B: internal level ordering confirmed; missing canonical evidence resolves NONE safely, with no fabricated provenance and no crash.")


# ======================================================================
# C. Protected negatives -- must never route to EDUCATION_FLOOR_EVALUATOR.
# ======================================================================
protected_negatives = (
    # Field-of-study qualifier.
    "Bachelor's degree in Business Analytics required.",
    # Accreditation/institution/ranking qualifier.
    "Bachelor's degree from an accredited institution.",
    "Bachelor's degree from a top-ranked university required.",
    # U.S./foreign equivalency.
    "Bachelor's degree or U.S. equivalent required.",
    # Diploma/transcript/proof document-production wording.
    "Proof of high school diploma required.",
    "Official transcript required upon hire.",
    # School-specific wording.
    "Bachelor's degree from Brandeis University required.",
    # Licenses/certifications.
    "Series 65 license required.",
    "CPA certification required.",
    # Doctoral/professional degrees.
    "Doctoral degree required.",
    "PhD required.",
    "Juris Doctor required.",
    # Compound degree+experience.
    "Bachelor's degree plus 3 years of experience required.",
    "Bachelor's degree with three (3) or more years of experience required.",
)
for text in protected_negatives:
    row = _req(text, req_id="REQ_NEG_TEST")
    caps = infer_requirement_capabilities(row)
    assert_true(
        not is_education_floor_requirement(row, inferred_capabilities=caps, gated=False),
        f"{text!r} must NOT be routed to EDUCATION_FLOOR_EVALUATOR",
    )
    assert_true(
        parse_education_floor(text) is None
        or not caps.issubset({"bachelors_degree_credential"}),
        f"{text!r} must be excluded either by non-parsing text or by extra inferred capability tags",
    )

# Rows carrying an unrelated inferred technology/domain capability.
tech_row = _req("Salesforce experience required.", technology=["Salesforce"], req_id="REQ_NEG_TECH")
tech_caps = infer_requirement_capabilities(tech_row)
assert_true(
    not is_education_floor_requirement(tech_row, inferred_capabilities=tech_caps, gated=False),
    "an unrelated technology-capability row must never route to EDUCATION_FLOOR_EVALUATOR",
)

domain_row = _req(
    "Three (3) years of experience in system analysis, including support.",
    domain="System Analysis",
    req_id="REQ_NEG_DOMAIN",
)
domain_caps = infer_requirement_capabilities(domain_row)
assert_true(
    not is_education_floor_requirement(domain_row, inferred_capabilities=domain_caps, gated=False),
    "an unrelated domain-qualified row must never route to EDUCATION_FLOOR_EVALUATOR",
)
print("PASS C: all protected negatives (field-of-study, accreditation/institution/ranking, equivalency, document-production, school-specific, license/certification, doctoral/professional, compound degree+experience, unrelated technology/domain rows) stay out of EDUCATION_FLOOR_EVALUATOR.")


# ======================================================================
# D. Gated-row exclusion -- an explicit qualification-gate leaf must never
#    route to EDUCATION_FLOOR_EVALUATOR, even when its own text is an
#    otherwise-exact positive grammar match.
# ======================================================================
gated_row = _req("Bachelor's degree required.", req_id="REQ_GATED")
gated_caps = infer_requirement_capabilities(gated_row)
assert_true(
    is_education_floor_requirement(gated_row, inferred_capabilities=gated_caps, gated=False),
    "sanity: the same text must route when NOT gated",
)
assert_true(
    not is_education_floor_requirement(gated_row, inferred_capabilities=gated_caps, gated=True),
    "an explicit qualification-gate leaf must never route to EDUCATION_FLOOR_EVALUATOR",
)
print("PASS D: an explicit qualification-gate leaf never routes to EDUCATION_FLOOR_EVALUATOR, regardless of its own text.")


# ======================================================================
# E. No lower-credential fabrication -- explanation text for a HIGH_SCHOOL
#    floor satisfied by the M.S. must never claim literal possession of a
#    high school diploma.
# ======================================================================
hs_row = _req("High school diploma required.", req_id="REQ_HS_FAB_CHECK")
hs_match = evaluate_education_floor_requirement(
    job_id="JOB_TEST",
    requirement=hs_row,
    match_index=0,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(hs_match["result"] == "SUPPORTED", "sanity: HIGH_SCHOOL floor must resolve SUPPORTED with the M.S.")
hs_explanation_lower = hs_match["explanation"].lower()
for forbidden in ("possesses a high school diploma", "holds a high school diploma", "high school diploma is possessed"):
    assert_true(
        forbidden not in hs_explanation_lower,
        f"explanation must never assert literal possession of the lower credential ({forbidden!r})",
    )
assert_true(
    "minimum" in hs_explanation_lower and "level" in hs_explanation_lower,
    "explanation must be phrased as minimum-level satisfaction",
)
print("PASS E: a HIGH_SCHOOL floor satisfied by the awarded M.S. never fabricates literal possession of the lower credential.")


# ======================================================================
# F. UNWE claim must never be cited -- CLAIM_EDU_UNWE_001 is not trusted
#    V1 candidate evidence for this evaluator.
# ======================================================================
for text in POSITIVE_GRAMMARS:
    row = _req(text, req_id="REQ_UNWE_CHECK")
    match = evaluate_education_floor_requirement(
        job_id="JOB_TEST", requirement=row, match_index=0, evidence_index=EVIDENCE_INDEX
    )
    assert_true(
        UNWE_CLAIM_ID not in match["claim_ids"] and UNWE_CLAIM_ID not in match["evidence_ids"],
        f"{text!r}: CLAIM_EDU_UNWE_001 must never be cited by EDUCATION_FLOOR_EVALUATOR",
    )
print("PASS F: CLAIM_EDU_UNWE_001 is never cited by EDUCATION_FLOOR_EVALUATOR for any positive grammar.")


# ======================================================================
# G. PREFERRED-importance control -- never becomes a hard blocker or gap.
# ======================================================================
preferred_row = _req("Master's degree required.", req_id="REQ_PREF_TEST", importance="PREFERRED")
preferred_caps = infer_requirement_capabilities(preferred_row)
assert_true(
    is_education_floor_requirement(preferred_row, inferred_capabilities=preferred_caps, gated=False),
    "PREFERRED education-floor requirement must still be routed to the evaluator",
)
match_pref = evaluate_education_floor_requirement(
    job_id="JOB_PREF_TEST", requirement=preferred_row, match_index=0, evidence_index=EVIDENCE_INDEX
)
assert_true(match_pref["result"] == "SUPPORTED", "PREFERRED education-floor requirement must still resolve SUPPORTED")
gaps, unknowns = _build_gaps_and_unknowns([preferred_row], [match_pref])
assert_true(gaps == [], f"SUPPORTED PREFERRED education-floor requirement must not produce a gap; got {gaps}")
assert_true(unknowns == [], f"SUPPORTED PREFERRED education-floor requirement must not produce an unknown; got {unknowns}")
print("PASS G: PREFERRED education-floor requirement resolves SUPPORTED and never becomes a gap or unknown.")


# ======================================================================
# H. MANDATORY/HIGH REQ_MERCER_HS-shaped row: gaps/unknowns and
#    detect_hard_blockers() confirm it never becomes a gap or hard
#    blocker.
# ======================================================================
mercer_hs_row = _req("High school diploma required.", req_id="REQ_MERCER_HS")
mercer_hs_match = evaluate_education_floor_requirement(
    job_id="JOB_MERCER_TEST", requirement=mercer_hs_row, match_index=0, evidence_index=EVIDENCE_INDEX
)
gaps_hs, unknowns_hs = _build_gaps_and_unknowns([mercer_hs_row], [mercer_hs_match])
assert_true(gaps_hs == [], f"REQ_MERCER_HS must never produce a qualification gap; got {gaps_hs}")
assert_true(unknowns_hs == [], f"REQ_MERCER_HS must never produce a qualification unknown; got {unknowns_hs}")

blockers_hs = detect_hard_blockers(
    requirements=[mercer_hs_row],
    matches=[mercer_hs_match],
    seniority=None,
    role="Portfolio Operations Specialist",
    jd_text="High school diploma required.",
)
assert_true(
    not any("REQ_MERCER_HS" in b for b in blockers_hs),
    f"REQ_MERCER_HS must never appear as a hard blocker; got {blockers_hs}",
)
print("PASS H: MANDATORY/HIGH REQ_MERCER_HS-shaped row is absent from qualification_gaps, qualification_unknowns, and hard_blockers.")


# ======================================================================
# I. Real end-to-end proof: analyze_job() on a synthetic job input
#    mirroring the exact live Mercer Advisors Portfolio Operations
#    Specialist posting -- REQ_MERCER_HS resolves SUPPORTED/
#    EDUCATION_FLOOR_EVALUATOR using only the Brandeis evidence and
#    disappears from qualification gaps/hard blockers, while the
#    independent REQ_MERCER_COMM requirement remains NONE and a hard
#    blocker, and the overall decision remains REJECT.
# ======================================================================
JD_TEXT = (
    "Portfolio Operations Specialist\n\n"
    "Qualifications:\n"
    "- High school diploma required.\n"
    "- Excellent written and verbal communication skills required.\n"
)

mercer_structured = {
    "role_family": "Operations",
    "seniority": "ENTRY",
    "requirements": [
        _req("High school diploma required.", req_id="REQ_MERCER_HS"),
        _req(
            "Excellent written and verbal communication skills required.",
            req_id="REQ_MERCER_COMM",
        ),
    ],
}

mercer_job_input = {
    "company": "Mercer Advisors",
    "role": "Portfolio Operations Specialist",
    "jd_text": JD_TEXT,
    "structured_extraction": mercer_structured,
    "fixture_key": "EDUCATION_FLOOR_SEMANTICS_V1_SYNTH",
    "role_status": "VERIFIED_LIVE",
    "source_verification_status": "VERIFIED_DIRECT",
    "operation_run_id": "RUN_EDUCATION_FLOOR_SEMANTICS_V1",
    "official_url": "https://careers.example.test/jobs/mercer-portfolio-operations-specialist",
    "date_last_verified": "2026-09-16",
    "pre_surfacing_verification": {
        "verification_kind": "JIT_PRE_SURFACING_VERIFICATION_V1",
        "operation_run_id": "RUN_EDUCATION_FLOOR_SEMANTICS_V1",
        "observed_at": "2026-09-16T12:00:00-04:00",
        "source_kind": "FIRST_PARTY_DIRECT",
        "exact_url": "https://careers.example.test/jobs/mercer-portfolio-operations-specialist",
        "observed_company": "Mercer Advisors",
        "observed_role": "Portfolio Operations Specialist",
        "substantive_role_content_present": True,
        "application_route_status": "ACTIONABLE",
        "recency_observation": {
            "state": "AUTHORITATIVE_ABSOLUTE_DATE",
            "source_kind": "FIRST_PARTY_DIRECT",
            "observed_at": "2026-09-16T12:00:00-04:00",
            "posted_date": "2026-09-15",
        },
        "material_conflicts": [],
        "resolved_conflicts": [],
    },
}

result_mercer = analyze_job(mercer_job_input)
assert_true(result_mercer["valid"] is True, f"synthetic Mercer analysis must be valid: {result_mercer['errors']}")
analysis_mercer = result_mercer["analysis"]

match_hs_real = next(m for m in analysis_mercer["evidence_matches"] if m["requirement_id"] == "REQ_MERCER_HS")
assert_true(match_hs_real["result"] == "SUPPORTED", f"REQ_MERCER_HS must resolve SUPPORTED end-to-end, got {match_hs_real['result']}")
assert_true(
    match_hs_real["evaluation_path"] == "EDUCATION_FLOOR_EVALUATOR",
    f"REQ_MERCER_HS evaluation_path must be EDUCATION_FLOOR_EVALUATOR end-to-end, got {match_hs_real['evaluation_path']}",
)
assert_true(
    match_hs_real["evidence_ids"] == [BRANDEIS_EVIDENCE_ID],
    f"REQ_MERCER_HS must cite only {BRANDEIS_EVIDENCE_ID} end-to-end, got {match_hs_real['evidence_ids']}",
)
assert_true(match_hs_real["claim_ids"] == [], "REQ_MERCER_HS must never cite a claim_id end-to-end")

assert_true(
    not any("REQ_MERCER_HS" in g for g in analysis_mercer["qualification_gaps"]),
    f"REQ_MERCER_HS must be absent from qualification_gaps, got {analysis_mercer['qualification_gaps']}",
)
assert_true(
    not any("REQ_MERCER_HS" in u for u in analysis_mercer["qualification_unknowns"]),
    f"REQ_MERCER_HS must be absent from qualification_unknowns, got {analysis_mercer['qualification_unknowns']}",
)
assert_true(
    not any("REQ_MERCER_HS" in b for b in result_mercer["hard_blockers"]),
    f"REQ_MERCER_HS must never appear in hard_blockers, got {result_mercer['hard_blockers']}",
)

match_comm_real = next(m for m in analysis_mercer["evidence_matches"] if m["requirement_id"] == "REQ_MERCER_COMM")
assert_true(match_comm_real["result"] == "NONE", f"REQ_MERCER_COMM must remain NONE end-to-end, got {match_comm_real['result']}")
assert_true(
    any("REQ_MERCER_COMM" in b for b in result_mercer["hard_blockers"]),
    f"REQ_MERCER_COMM must remain an independent hard blocker, got {result_mercer['hard_blockers']}",
)
assert_true(
    any("REQ_MERCER_COMM" in g for g in analysis_mercer["qualification_gaps"]),
    f"REQ_MERCER_COMM must remain a qualification gap, got {analysis_mercer['qualification_gaps']}",
)

assert_true(
    analysis_mercer["decision"] == "REJECT",
    f"overall decision must remain REJECT (driven by the independent REQ_MERCER_COMM blocker), got {analysis_mercer['decision']}",
)
print("PASS I: real end-to-end analyze_job() on the exact live Mercer Advisors requirement text resolves REQ_MERCER_HS SUPPORTED/EDUCATION_FLOOR_EVALUATOR using only the Brandeis evidence, absent from qualification gaps/hard blockers, while the independent REQ_MERCER_COMM requirement remains NONE/hard blocker and the overall decision remains REJECT.")


# ======================================================================
# J. Real end-to-end regression -- existing bachelor's capability matching
#    and alternative-qualification-gate behavior remain unaffected by this
#    module's routing addition, using the same synthetic job shape.
# ======================================================================
accredited_row = _req("Bachelor's degree from an accredited institution.", req_id="REQ_ACCREDITED")
accredited_caps = infer_requirement_capabilities(accredited_row)
assert_true(
    "bachelors_degree_credential" in accredited_caps,
    "existing bachelor's-degree capability inference must remain unaffected",
)
assert_true(
    not is_education_floor_requirement(accredited_row, inferred_capabilities=accredited_caps, gated=False),
    "an accreditation-qualified bachelor's row must remain owned by the unmodified capability matcher",
)
print("PASS J: existing bachelor's-degree capability matching and accreditation-qualifier ownership boundaries remain unaffected.")


# ======================================================================
# K. Routing-leakage repair: an exact floor grammar with explicit
#    specialization metadata (domain or technology) must never route,
#    regardless of text/inferred-capability state.
# ======================================================================
leak_domain_row = _req(
    "Bachelor's degree required.", domain="Finance", req_id="REQ_LEAK_DOMAIN"
)
leak_domain_caps = infer_requirement_capabilities(leak_domain_row)
assert_true(
    not is_education_floor_requirement(
        leak_domain_row, inferred_capabilities=leak_domain_caps, gated=False
    ),
    "plain Bachelor's floor + domain='Finance' must NOT ROUTE",
)

leak_tech_row = _req(
    "Bachelor's degree required.", technology=["Excel"], req_id="REQ_LEAK_TECH"
)
leak_tech_caps = infer_requirement_capabilities(leak_tech_row)
assert_true(
    not is_education_floor_requirement(
        leak_tech_row, inferred_capabilities=leak_tech_caps, gated=False
    ),
    "plain floor + non-empty technology metadata must NOT ROUTE",
)
print("PASS K: an exact floor grammar carrying explicit domain or technology specialization metadata never routes to EDUCATION_FLOOR_EVALUATOR.")


# ======================================================================
# L. Evidence-semantic overtrust repair: SUPPORT requires the trusted
#    evidence record itself to prove the bounded canonical award semantic
#    -- never evidence_id presence alone.
# ======================================================================
def _award_match(evidence_index: dict, req_id: str = "REQ_EVIDENCE_CHECK") -> dict:
    row = _req("Master's degree required.", req_id=req_id)
    return evaluate_education_floor_requirement(
        job_id="JOB_TEST", requirement=row, match_index=0, evidence_index=evidence_index
    )


CANONICAL_EXPERIENCE_ID = "EXP_EDU_BRANDEIS_001"
CANONICAL_EVIDENCE = EVIDENCE_INDEX[BRANDEIS_EVIDENCE_ID]

# L1. Trusted evidence ID present but with a semantically invalid fact.
bad_fact_evidence = dict(CANONICAL_EVIDENCE)
bad_fact_evidence["fact"] = "Bora attended a seminar about business analytics."
match_bad_fact = _award_match({BRANDEIS_EVIDENCE_ID: bad_fact_evidence}, "REQ_BAD_FACT")
assert_true(
    match_bad_fact["result"] == "NONE",
    f"trusted evidence ID with semantically invalid fact must NOT SUPPORT, got {match_bad_fact['result']}",
)

# L2. Mismatched experience_id.
bad_exp_evidence = dict(CANONICAL_EVIDENCE)
bad_exp_evidence["experience_id"] = "EXP_UNRELATED_999"
match_bad_exp = _award_match({BRANDEIS_EVIDENCE_ID: bad_exp_evidence}, "REQ_BAD_EXP")
assert_true(
    match_bad_exp["result"] == "NONE",
    f"mismatched experience_id must NOT SUPPORT, got {match_bad_exp['result']}",
)

# L3. Non-affirmative/corrupted evidence_state.
bad_state_evidence = dict(CANONICAL_EVIDENCE)
bad_state_evidence["evidence_state"] = "CONTRADICTED"
match_bad_state = _award_match({BRANDEIS_EVIDENCE_ID: bad_state_evidence}, "REQ_BAD_STATE")
assert_true(
    match_bad_state["result"] == "NONE",
    f"non-affirmative/corrupted evidence_state must NOT SUPPORT, got {match_bad_state['result']}",
)

# L3a. Evidence-state exactness repair: V1 is tied to the current canonical
# record itself, which is exactly OBSERVED-tier. A synthetic copy claiming a
# HIGHER trust tier (VERIFIED/SUPPORTED) than the real canonical record
# currently holds must NOT SUPPORT -- no Candidate Truth upgrade occurred.
# UNKNOWN and a missing evidence_state must likewise NOT SUPPORT. Only exact
# OBSERVED (the real canonical record's own tier) may SUPPORT.
for non_observed_state in ("VERIFIED", "SUPPORTED", "UNKNOWN", "CONTRADICTED"):
    state_evidence = dict(CANONICAL_EVIDENCE)
    state_evidence["evidence_state"] = non_observed_state
    match_state = _award_match(
        {BRANDEIS_EVIDENCE_ID: state_evidence}, f"REQ_STATE_{non_observed_state}"
    )
    assert_true(
        match_state["result"] == "NONE",
        f"evidence_state={non_observed_state!r} must NOT SUPPORT (V1 requires exactly OBSERVED), got {match_state['result']}",
    )

missing_state_evidence = dict(CANONICAL_EVIDENCE)
del missing_state_evidence["evidence_state"]
match_missing_state = _award_match(
    {BRANDEIS_EVIDENCE_ID: missing_state_evidence}, "REQ_MISSING_STATE"
)
assert_true(
    match_missing_state["result"] == "NONE",
    f"missing evidence_state must NOT SUPPORT, got {match_missing_state['result']}",
)

observed_control_evidence = dict(CANONICAL_EVIDENCE)
observed_control_evidence["evidence_state"] = "OBSERVED"
match_observed_control = _award_match(
    {BRANDEIS_EVIDENCE_ID: observed_control_evidence}, "REQ_OBSERVED_CONTROL"
)
assert_true(
    match_observed_control["result"] == "SUPPORTED",
    f"exact OBSERVED canonical control must SUPPORT, got {match_observed_control['result']}",
)
assert_true(
    match_observed_control["evidence_ids"] == [BRANDEIS_EVIDENCE_ID],
    f"exact OBSERVED canonical control must cite only {BRANDEIS_EVIDENCE_ID}, got {match_observed_control['evidence_ids']}",
)
print("PASS L3a: evidence_state exactness is repaired -- VERIFIED, SUPPORTED, UNKNOWN, CONTRADICTED, and a missing evidence_state all resolve NONE, while the exact OBSERVED canonical control remains SUPPORTED.")

# L3b. unsafe_for_external_use=false.
unsafe_evidence = dict(CANONICAL_EVIDENCE)
unsafe_evidence["safe_for_external_use"] = False
match_unsafe = _award_match({BRANDEIS_EVIDENCE_ID: unsafe_evidence}, "REQ_UNSAFE")
assert_true(
    match_unsafe["result"] == "NONE",
    f"safe_for_external_use=false must NOT SUPPORT, got {match_unsafe['result']}",
)

# L4. Missing awarded record entirely.
match_missing = _award_match({}, "REQ_MISSING_RECORD")
assert_true(
    match_missing["result"] == "NONE",
    f"missing awarded record must NOT SUPPORT, got {match_missing['result']}",
)

# L5. Valid canonical Brandeis M.S. control -- Mercer HS remains SUPPORTED,
#     citing only EDU_BRANDEIS_AWARDED_ATTESTATION_001.
match_control = _award_match(EVIDENCE_INDEX, "REQ_CONTROL_VALID")
assert_true(
    match_control["result"] == "SUPPORTED",
    f"valid canonical Brandeis M.S. control must resolve SUPPORTED, got {match_control['result']}",
)
assert_true(
    match_control["evaluation_path"] == "EDUCATION_FLOOR_EVALUATOR",
    "valid canonical control must cite EDUCATION_FLOOR_EVALUATOR",
)
assert_true(
    match_control["evidence_ids"] == [BRANDEIS_EVIDENCE_ID],
    f"valid canonical control must cite only {BRANDEIS_EVIDENCE_ID}, got {match_control['evidence_ids']}",
)
print("PASS L: evidence-semantic overtrust is repaired -- SUPPORT requires the trusted evidence record itself to prove the bounded canonical award semantic (invalid fact, mismatched experience_id, non-affirmative state, unsafe_for_external_use=false, and missing record all resolve NONE), while the valid canonical control remains SUPPORTED citing only the canonical evidence_id.")


# ======================================================================
# M. Below-floor deterministic level-comparison boundary: BACHELOR
#    (candidate's established level would be) vs required MASTER resolves
#    false/NONE at the ordered-level-comparison boundary, without
#    inventing any canonical lower-degree evidence record.
# ======================================================================
assert_true(
    EDUCATION_LEVEL_ORDER["BACHELOR"] < EDUCATION_LEVEL_ORDER["MASTER"],
    "BACHELOR must compare strictly below MASTER in the ordered floor",
)
assert_true(
    not (EDUCATION_LEVEL_ORDER["BACHELOR"] >= EDUCATION_LEVEL_ORDER["MASTER"]),
    "BACHELOR must not meet-or-exceed a required MASTER floor",
)
print("PASS M: the deterministic level-comparison boundary (BACHELOR vs required MASTER) is explicitly confirmed false, without inventing any canonical lower-degree record.")


# ======================================================================
# N. No lower-credential possession claim anywhere in explanations, across
#    every positive grammar and the invalid-evidence NONE explanations
#    produced in section L.
# ======================================================================
forbidden_possession_phrases = (
    "possesses a",
    "holds a",
    "is possessed",
    "candidate holds",
    "candidate possesses",
)
for text in POSITIVE_GRAMMARS:
    row = _req(text, req_id="REQ_NOFAB_CHECK")
    m = evaluate_education_floor_requirement(
        job_id="JOB_TEST", requirement=row, match_index=0, evidence_index=EVIDENCE_INDEX
    )
    explanation_lower = m["explanation"].lower()
    for phrase in forbidden_possession_phrases:
        assert_true(
            phrase not in explanation_lower,
            f"{text!r}: explanation must never claim lower-credential possession ({phrase!r})",
        )
for m in (match_bad_fact, match_bad_exp, match_bad_state, match_unsafe, match_missing):
    explanation_lower = m["explanation"].lower()
    for phrase in forbidden_possession_phrases:
        assert_true(
            phrase not in explanation_lower,
            f"NONE explanation must never claim lower-credential possession ({phrase!r}); got {m['explanation']!r}",
        )
print("PASS N: no explanation, across every positive grammar and every invalid-evidence NONE path, ever claims possession of a lower credential.")


# ======================================================================
# O. Negation/denial-wrapper repair: a fact carrying the approved award
#    phrase inside a negated or denied wrapper, or otherwise-altered/
#    unrelated award wording, must NEVER SUPPORT -- only the current
#    canonical record's exact whole-fact identity (after semantically
#    inert case/whitespace normalization only) may SUPPORT.
# ======================================================================

# O1. Negated prefix.
negated_prefix_evidence = dict(CANONICAL_EVIDENCE)
negated_prefix_evidence["fact"] = (
    "It is false that his Brandeis University Master of Science in "
    "Business Analytics is officially completed and awarded."
)
match_negated_prefix = _award_match(
    {BRANDEIS_EVIDENCE_ID: negated_prefix_evidence}, "REQ_NEGATED_PREFIX"
)
assert_true(
    match_negated_prefix["result"] == "NONE",
    f"negated-prefix fact must NOT SUPPORT, got {match_negated_prefix['result']}",
)

# O2. Denial suffix.
denial_suffix_evidence = dict(CANONICAL_EVIDENCE)
denial_suffix_evidence["fact"] = (
    "His Brandeis University Master of Science in Business Analytics is "
    "officially completed and awarded -- this statement is not true."
)
match_denial_suffix = _award_match(
    {BRANDEIS_EVIDENCE_ID: denial_suffix_evidence}, "REQ_DENIAL_SUFFIX"
)
assert_true(
    match_denial_suffix["result"] == "NONE",
    f"denial-suffix fact must NOT SUPPORT, got {match_denial_suffix['result']}",
)

# O3. Altered/unrelated award wording (contains degree-adjacent words but is
#     not the canonical atomic fact sentence).
altered_wording_evidence = dict(CANONICAL_EVIDENCE)
altered_wording_evidence["fact"] = (
    "Bora is currently enrolled in a Brandeis University Master of Science "
    "in Business Analytics program and expects to complete it eventually."
)
match_altered_wording = _award_match(
    {BRANDEIS_EVIDENCE_ID: altered_wording_evidence}, "REQ_ALTERED_WORDING"
)
assert_true(
    match_altered_wording["result"] == "NONE",
    f"altered/unrelated award wording must NOT SUPPORT, got {match_altered_wording['result']}",
)

# O4. Malformed/mismatched identity, state, and safety fields, reusing
#     section L's dedicated per-field checks (already asserted NONE above):
#     bad_fact_evidence (invalid fact), bad_exp_evidence (mismatched
#     experience_id), bad_state_evidence (non-affirmative evidence_state),
#     unsafe_evidence (safe_for_external_use=False) -- confirmed again here
#     as part of this adversarial group.
for m, label in (
    (match_bad_fact, "invalid fact"),
    (match_bad_exp, "mismatched experience_id"),
    (match_bad_state, "non-affirmative evidence_state"),
    (match_unsafe, "safe_for_external_use=False"),
):
    assert_true(
        m["result"] == "NONE",
        f"malformed/mismatched evidence ({label}) must NOT SUPPORT, got {m['result']}",
    )

# O5. Exact real canonical Brandeis award record -- must SUPPORT.
match_real_canonical = _award_match(EVIDENCE_INDEX, "REQ_REAL_CANONICAL")
assert_true(
    match_real_canonical["result"] == "SUPPORTED",
    f"the exact real canonical Brandeis award record must SUPPORT, got {match_real_canonical['result']}",
)
assert_true(
    match_real_canonical["evidence_ids"] == [BRANDEIS_EVIDENCE_ID],
    f"the exact real canonical Brandeis award record must cite only {BRANDEIS_EVIDENCE_ID}, got {match_real_canonical['evidence_ids']}",
)

print("PASS O: a negated-prefix fact, a denial-suffix fact, and altered/unrelated award wording all resolve NONE (never SUPPORTED by mere substring containment of the approved phrase), malformed/mismatched identity/state/safety fields remain NONE, and the exact real canonical Brandeis award record remains SUPPORTED citing only the canonical evidence_id.")


# ======================================================================
# P. Domain/technology leakage regressions and below-floor deterministic
#    ordering regression remain green (re-confirming sections K and M,
#    which this repair must not have disturbed).
# ======================================================================
leak_domain_row_p = _req(
    "Bachelor's degree required.", domain="Finance", req_id="REQ_LEAK_DOMAIN_P"
)
leak_domain_caps_p = infer_requirement_capabilities(leak_domain_row_p)
assert_true(
    not is_education_floor_requirement(
        leak_domain_row_p, inferred_capabilities=leak_domain_caps_p, gated=False
    ),
    "domain-leakage regression: plain Bachelor's floor + domain='Finance' must still NOT ROUTE",
)

leak_tech_row_p = _req(
    "Bachelor's degree required.", technology=["Excel"], req_id="REQ_LEAK_TECH_P"
)
leak_tech_caps_p = infer_requirement_capabilities(leak_tech_row_p)
assert_true(
    not is_education_floor_requirement(
        leak_tech_row_p, inferred_capabilities=leak_tech_caps_p, gated=False
    ),
    "technology-leakage regression: plain floor + non-empty technology metadata must still NOT ROUTE",
)

assert_true(
    EDUCATION_LEVEL_ORDER["BACHELOR"] < EDUCATION_LEVEL_ORDER["MASTER"]
    and not (EDUCATION_LEVEL_ORDER["BACHELOR"] >= EDUCATION_LEVEL_ORDER["MASTER"]),
    "below-floor deterministic ordering regression: BACHELOR vs required MASTER must still resolve false/NONE at the boundary",
)
print("PASS P: domain/technology leakage regressions and the below-floor deterministic ordering regression remain green after this repair.")


print("ALL education_floor_semantics_v1_test CHECKS PASSED")
