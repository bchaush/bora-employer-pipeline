"""Regression tests for REQUIREMENT_QUALIFIER_SEMANTICS_V1.

Covers the two demonstrated qualifier-overmatch defects:

- Q-1: "Bachelor's Degree (or higher) from top-tier university" -- the
  institutional-quality qualifier must not be silently treated as
  satisfied merely because the underlying degree fact is supported.
- Q-2: "strong Excel skills" -- the proficiency-intensity qualifier must
  not be silently treated as satisfied merely because ordinary
  professional Excel use is supported.

In both cases the truthful result is PARTIAL (base capability genuinely
supported; material qualifier genuinely unestablished), never SUPPORTED/
STRONG (would overclaim) and never NONE/UNKNOWN (would understate the real
partial signal that exists).

Approval is simulated in-memory only, via a deep-copied claim index with
human_approval flipped locally -- disk state (human_approval=false on the
real CLAIM_EDU_UNWE_001/CLAIM_DCOMMERCE_001 records) is never touched by
this file, confirmed explicitly at the end.

Exercises real production code (requirement_match.py) -- no logic is
duplicated here.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from requirement_match import (  # noqa: E402
    infer_requirement_capabilities,
    load_reusable_claims,
    match_requirement,
)


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


def _req(req_id: str, text: str, *, technology: list[str] | None = None) -> dict:
    return {
        "requirement_id": req_id,
        "text": text,
        "source_text": text,
        "domain": None,
        "category": None,
        "technology": technology or [],
        "relevance": "HIGH",
        "importance": "MANDATORY",
    }


def _simulate_approved_match(claim_id: str, requirement: dict) -> dict:
    """Match one requirement against a locally-approved copy of one claim.

    Never mutates the real claim repository on disk.
    """
    claim_index = copy.deepcopy(CLAIM_INDEX)
    claim_index[claim_id]["human_approval"] = True
    reusable = load_reusable_claims(claim_index, EVIDENCE_INDEX)
    return match_requirement(
        job_id="JOB_QUALIFIER_SIM",
        requirement=requirement,
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )


# ======================================================================
# A. Q-1 demonstrated case: institutional-quality qualifier.
# ======================================================================
req_degree_top_tier = _req(
    "REQ_A_DEGREE", "Bachelor's Degree (or higher) from top-tier university"
)
caps = infer_requirement_capabilities(req_degree_top_tier)
assert_true(
    caps == frozenset({"bachelors_degree_credential", "institutional_quality_qualifier"}),
    f"top-tier degree requirement must infer both tags; got {sorted(caps)}",
)
match_q1 = _simulate_approved_match("CLAIM_EDU_UNWE_001", req_degree_top_tier)
assert_true(
    match_q1["result"] == "PARTIAL",
    f"Q-1: supported degree + unestablished institutional-quality qualifier must be PARTIAL, got {match_q1['result']}",
)
assert_true(
    "institutional_quality_qualifier" in match_q1["explanation"],
    "Q-1 explanation must name the missing qualifier capability",
)
print("PASS A: Q-1 demonstrated case (top-tier university) resolves PARTIAL.")


# ======================================================================
# B. Plain bachelor's requirement -- baseline behavior unchanged.
# ======================================================================
req_plain_degree = _req("REQ_PLAIN_DEGREE", "Bachelor's degree")
caps_plain = infer_requirement_capabilities(req_plain_degree)
assert_true(
    caps_plain == frozenset({"bachelors_degree_credential"}),
    f"plain bachelor's requirement must not gain the institutional-quality tag; got {sorted(caps_plain)}",
)
match_plain_degree = _simulate_approved_match("CLAIM_EDU_UNWE_001", req_plain_degree)
assert_true(
    match_plain_degree["result"] == "SUPPORTED",
    f"plain bachelor's degree requirement must remain SUPPORTED (not demoted), got {match_plain_degree['result']}",
)
print("PASS B: plain bachelor's degree requirement is unaffected (still SUPPORTED).")


# ======================================================================
# C. "top tier university" (no hyphen) -- explicit variant coverage.
# ======================================================================
req_no_hyphen = _req(
    "REQ_NO_HYPHEN_DEGREE", "Bachelor's degree from top tier university"
)
caps_no_hyphen = infer_requirement_capabilities(req_no_hyphen)
assert_true(
    "institutional_quality_qualifier" in caps_no_hyphen,
    "unhyphenated 'top tier university' must still trigger the institutional-quality qualifier",
)
print("PASS C: unhyphenated 'top tier university' variant is recognized.")


# ======================================================================
# D. Q-2 demonstrated case: elevated Excel-proficiency qualifier.
# ======================================================================
req_strong_excel = _req(
    "REQ_A_EXCEL_DATA",
    "Genuinely comfortable working with data: strong Excel skills, and an "
    "interest in getting into the technical detail of how systems and data "
    "structures fit together",
    technology=["Excel"],
)
caps_excel = infer_requirement_capabilities(req_strong_excel)
assert_true(
    caps_excel == frozenset({"excel_proficiency", "excel_elevated_proficiency_qualifier"}),
    f"'strong Excel skills' requirement must infer both tags; got {sorted(caps_excel)}",
)
match_q2 = _simulate_approved_match("CLAIM_DCOMMERCE_001", req_strong_excel)
assert_true(
    match_q2["result"] == "PARTIAL",
    f"Q-2: supported Excel use + unestablished proficiency-intensity qualifier must be PARTIAL, got {match_q2['result']}",
)
assert_true(
    "excel_elevated_proficiency_qualifier" in match_q2["explanation"],
    "Q-2 explanation must name the missing qualifier capability",
)
print("PASS D: Q-2 demonstrated case (strong Excel skills) resolves PARTIAL.")


# ======================================================================
# E. Plain Excel requirements -- baseline behavior unchanged.
# ======================================================================
for plain_text in ("Excel skills required", "Excel experience"):
    req_plain_excel = _req("REQ_PLAIN_EXCEL", plain_text, technology=["Excel"])
    caps_plain_excel = infer_requirement_capabilities(req_plain_excel)
    assert_true(
        caps_plain_excel == frozenset({"excel_proficiency"}),
        f"plain Excel requirement {plain_text!r} must not gain the elevated-proficiency tag; got {sorted(caps_plain_excel)}",
    )
    match_plain_excel = _simulate_approved_match("CLAIM_DCOMMERCE_001", req_plain_excel)
    assert_true(
        match_plain_excel["result"] == "SUPPORTED",
        f"plain Excel requirement {plain_text!r} must remain SUPPORTED, got {match_plain_excel['result']}",
    )
print("PASS E: plain Excel requirements are unaffected (still SUPPORTED).")


# ======================================================================
# F. Unrelated "strong" language must not gain the Excel qualifier.
# ======================================================================
for unrelated in (
    "strong communication skills",
    "strong analytical skills",
    "strong stakeholder management",
    "strong attention to detail",
    "strong writing skills",
):
    caps_unrelated = infer_requirement_capabilities(_req("REQ_UNRELATED", unrelated))
    assert_true(
        "excel_elevated_proficiency_qualifier" not in caps_unrelated,
        f"{unrelated!r} must never trigger the Excel-bound elevated-proficiency qualifier",
    )
print("PASS F: unrelated 'strong X skills' language never triggers the Excel qualifier.")


# ======================================================================
# G. Unrelated "top-tier" context must not gain the institutional
#    qualifier -- it stays bound to an education-context noun.
# ======================================================================
caps_customer_service = infer_requirement_capabilities(
    _req("REQ_UNRELATED_TOPTIER", "top-tier customer service")
)
assert_true(
    "institutional_quality_qualifier" not in caps_customer_service,
    "'top-tier customer service' must never trigger the institutional-quality qualifier",
)
print("PASS G: unrelated 'top-tier' context (no education noun) does not trigger the qualifier.")


# ======================================================================
# H. Generic requirements-gathering control -- unaffected.
# ======================================================================
req_generic = _req("REQ_GENERIC_GATHER", "Gather business requirements from stakeholders")
reusable_real = load_reusable_claims(CLAIM_INDEX, EVIDENCE_INDEX)
match_generic = match_requirement(
    job_id="JOB_CONTROL",
    requirement=req_generic,
    reusable_claims=reusable_real,
    evidence_index=EVIDENCE_INDEX,
    match_index=0,
)
assert_true(
    match_generic["result"] == "STRONG",
    f"generic requirements-gathering control must remain STRONG via CLAIM_WW_001, got {match_generic['result']}",
)
print("PASS H: generic requirements-gathering control (Winter Walk) is unaffected.")


# ======================================================================
# I. MIT SAP FI/CO named-platform protection -- unaffected.
# ======================================================================
req_sap = _req(
    "REQ_C_SAP_FICO",
    "7+ years of SAP FI/CO experience in requirements gathering, deployment and support",
    technology=["SAP FI/CO"],
)
match_sap = match_requirement(
    job_id="JOB_CONTROL",
    requirement=req_sap,
    reusable_claims=reusable_real,
    evidence_index=EVIDENCE_INDEX,
    match_index=0,
)
assert_true(
    match_sap["result"] == "NONE",
    f"SAP FI/CO named-platform trap must remain NONE, got {match_sap['result']}",
)
print("PASS I: MIT SAP FI/CO named-platform protection is unaffected.")


# ======================================================================
# J. Real disk claim state is confirmed unaffected by any simulation
#    performed in this file.
# ======================================================================
cl_after = validate_claim_repository()
for claim_id in ("CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001"):
    assert_true(
        cl_after["index"][claim_id]["human_approval"] is False,
        f"{claim_id} must remain human_approval=false on disk after simulation",
    )
print("PASS J: real claim repository on disk is unaffected by in-memory simulation.")


# ======================================================================
# K. Q-1 regex-scope tightening -- positive credential-context variants.
# ======================================================================
q1_positive_variants = (
    "Bachelor's degree from a top-tier university",
    "Bachelor's degree from a top tier university",
    "degree from a top-tier institution",
    "credential from a top tier school",
)
for text in q1_positive_variants:
    caps_variant = infer_requirement_capabilities(_req("REQ_Q1_VARIANT", text))
    assert_true(
        "institutional_quality_qualifier" in caps_variant,
        f"{text!r} must trigger the institutional-quality qualifier",
    )
print("PASS K: Q-1 credential-context positive variants (top-tier university/institution, hyphenated and not) all trigger the qualifier.")


# ======================================================================
# L. Q-1 regex-scope tightening -- institution-as-object must NOT trigger
#    the qualifier merely because a "top tier <institution>" phrase is
#    present without a credential/degree connected to it via "from".
# ======================================================================
q1_negative_variants = (
    "worked with top-tier universities",
    "customers include top-tier universities",
    "selling software to top-tier institutions",
    "partnerships with top-tier colleges",
    "serving top-tier schools",
)
for text in q1_negative_variants:
    caps_variant = infer_requirement_capabilities(_req("REQ_Q1_NEGATIVE", text))
    assert_true(
        "institutional_quality_qualifier" not in caps_variant,
        f"{text!r} must NOT trigger the institutional-quality qualifier -- the institution is an object/customer/partner, not a credential source",
    )
print("PASS L: Q-1 institution-as-object/customer/partner phrasing never triggers the institutional-quality qualifier.")


# ======================================================================
# M. Q-2 regex-scope tightening -- positive skill/proficiency-bound
#    variants (all explicitly tested, none supported by proximity alone).
# ======================================================================
q2_positive_variants = (
    "strong Excel skills",
    "strong Microsoft Excel skills",
    "strong Excel proficiency",
)
for text in q2_positive_variants:
    caps_variant = infer_requirement_capabilities(_req("REQ_Q2_VARIANT", text))
    assert_true(
        "excel_elevated_proficiency_qualifier" in caps_variant,
        f"{text!r} must trigger the elevated Excel-proficiency qualifier",
    )
print("PASS M: Q-2 skill/proficiency-bound positive variants (strong Excel skills/proficiency, with or without 'Microsoft') all trigger the qualifier.")


# ======================================================================
# N. Q-2 regex-scope tightening -- interest/desire/preference/enthusiasm/
#    familiarity proximity to "excel" must NOT trigger the elevated
#    qualifier merely because "strong" and "excel" are nearby; an actual
#    skill/proficiency noun must follow "excel".
# ======================================================================
q2_negative_variants = (
    "strong interest in Excel",
    "strong desire to learn Excel",
    "strong preference for Excel",
    "strong enthusiasm for Excel",
    "strong familiarity with Excel",
)
for text in q2_negative_variants:
    caps_variant = infer_requirement_capabilities(_req("REQ_Q2_NEGATIVE", text))
    assert_true(
        "excel_elevated_proficiency_qualifier" not in caps_variant,
        f"{text!r} must NOT trigger the elevated Excel-proficiency qualifier -- no skill/proficiency noun follows 'excel'",
    )
    assert_true(
        "excel_proficiency" in caps_variant,
        f"{text!r} should still carry the baseline excel_proficiency tag (Excel is mentioned)",
    )
print("PASS N: Q-2 interest/desire/preference/enthusiasm/familiarity proximity to 'excel' never triggers the elevated-proficiency qualifier.")


# ======================================================================
# O. Q-1 CROSS_CLAUSE_QUALIFIER_CAPTURE -- independent Cursor review found
#    that the prior (regex-scope-tightened, pre-this-correction) pattern's
#    bounded-but-unbounded-by-punctuation filler could still bridge two
#    unrelated clauses: a credential mention in one clause and an
#    unconnected "top tier university/institution" mention (describing
#    customers/clients/candidates, not the credential's source) in a later
#    clause. These must NOT trigger institutional_quality_qualifier --
#    the credential requirement is independent of the later institution
#    reference.
# ======================================================================
q1_cross_clause_variants = (
    "Bachelor's degree preferred; experience working with customers from top-tier universities",
    "Bachelor's degree required. Candidates come from top-tier universities",
    "Bachelor's degree and experience with clients from top-tier universities",
    "Bachelor's degree preferred, with customers from top-tier institutions",
    "Master's preferred; our customers come from top-tier universities",
)
for text in q1_cross_clause_variants:
    caps_variant = infer_requirement_capabilities(_req("REQ_Q1_CROSS_CLAUSE", text))
    assert_true(
        "institutional_quality_qualifier" not in caps_variant,
        f"{text!r} must NOT trigger the institutional-quality qualifier -- the credential mention and the institution mention are in different, unrelated clauses",
    )
print("PASS O: Q-1 cross-clause credential/institution bridging (Cursor CROSS_CLAUSE_QUALIFIER_CAPTURE) no longer manufactures the qualifier.")


# ======================================================================
# P. Q-2 SEMANTIC_PROXIMITY_FALSE_POSITIVE -- independent Cursor review
#    found that the prior (regex-scope-tightened, pre-this-correction)
#    pattern's bounded pre-"excel" filler could still be satisfied by an
#    intervening noun that "strong" actually modifies (interest,
#    preference, understanding, candidates), while a skill noun happened
#    to follow "excel" elsewhere in the same sentence. These must NOT
#    trigger excel_elevated_proficiency_qualifier -- "strong" does not
#    modify Excel proficiency in any of these constructions.
# ======================================================================
q2_proximity_variants = (
    "strong interest in Excel skills development",
    "strong preference for Excel skills training",
    "strong understanding of Excel skills requirements",
    "strong candidates with Excel skills",
    "strong background; Excel skills preferred",
)
for text in q2_proximity_variants:
    caps_variant = infer_requirement_capabilities(_req("REQ_Q2_PROXIMITY", text))
    assert_true(
        "excel_elevated_proficiency_qualifier" not in caps_variant,
        f"{text!r} must NOT trigger the elevated Excel-proficiency qualifier -- 'strong' modifies a different noun, not Excel proficiency directly",
    )
print("PASS P: Q-2 semantic-proximity false positives (Cursor SEMANTIC_PROXIMITY_FALSE_POSITIVE) no longer manufacture the elevated-proficiency qualifier.")


# ======================================================================
# Q. Q-1 FALSE_CREDENTIAL_SOURCE_LINKAGE -- independent Cursor review found
#    that even the punctuation-and-token-count-bounded filler from the
#    prior correction could still be filled by a real intervening noun
#    phrase naming someone OTHER than the credential as what comes from
#    the institution (e.g. "candidates", "graduates") -- because that
#    phrase itself contained no forbidden punctuation and fit within the
#    token-count bound. The root problem was never the specific bound;
#    permitting ANY arbitrary semantic material between the credential
#    word and "from" is unsafe. The corrected pattern removes the
#    arbitrary filler entirely -- only one narrowly literal modifier,
#    "(or higher)", is permitted between the credential word and "from".
#    These must NOT trigger institutional_quality_qualifier.
# ======================================================================
q1_false_linkage_variants = (
    "Bachelor's degree required for candidates from top-tier universities",
    "Bachelor's degree preferred for graduates from top-tier universities",
)
for text in q1_false_linkage_variants:
    caps_variant = infer_requirement_capabilities(_req("REQ_Q1_FALSE_LINKAGE", text))
    assert_true(
        "institutional_quality_qualifier" not in caps_variant,
        f"{text!r} must NOT trigger the institutional-quality qualifier -- 'candidates'/'graduates', not the degree itself, are described as coming from the institution",
    )
    assert_true(
        "bachelors_degree_credential" in caps_variant,
        f"{text!r} should still carry the baseline bachelors_degree_credential tag",
    )
print("PASS Q: Q-1 false-credential-source-linkage cases (Cursor FALSE_CREDENTIAL_SOURCE_LINKAGE) no longer manufacture the institutional-quality qualifier.")


# ======================================================================
# R. Q-1 known bounded limitation: a comma directly after the credential
#    word, before "from" (e.g. "Bachelor's degree, from a top-tier
#    university") is an accepted conservative false-negative in V1 -- the
#    locality-only design intentionally misses this unusual formatting
#    variant rather than risk manufacturing a false qualifier by loosening
#    punctuation handling. Documented here, not fixed.
# ======================================================================
caps_comma_variant = infer_requirement_capabilities(
    _req("REQ_Q1_COMMA_LIMITATION", "Bachelor's degree, from a top-tier university")
)
assert_true(
    "institutional_quality_qualifier" not in caps_comma_variant,
    "known bounded limitation: a comma directly before 'from' is not recognized in V1 (documented, not a defect)",
)
print("PASS R: Q-1 comma-before-'from' formatting variant is a documented, accepted V1 limitation (conservative false-negative, not a false positive).")

print("ALL requirement_qualifier_semantics_v1_test CHECKS PASSED")
