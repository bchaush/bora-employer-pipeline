"""Regression tests: REQUIREMENT_QUALIFIER_SEMANTICS_V1 qualifier semantics
through the actual Application Clause path (src/application_clause_match.py).

Cursor's independent review flagged SHARED_INFERENCE_UNTESTED_SURFACE:
application_clause_match.match_clause() reuses requirement_match.py's
infer_requirement_capabilities()/claim_capabilities()/_NONE_TRAPS directly,
but no test had exercised the new Q-1/Q-2 qualifier tags through that path.
This file closes that gap with the four cases the review required:

A. genuine "strong Excel" clause -> qualifier inference behaves as expected
B. "strong interest in Excel skills development" -> must NOT manufacture
   elevated Excel proficiency
C. genuine degree-from-top-tier-university clause -> institutional
   qualifier behaves as expected
D. cross-clause/non-credential top-tier-university wording -> must NOT
   manufacture institutional-quality qualifier

This is regression coverage only -- no Application Gate redesign. Approval
is simulated in-memory only (deep-copied claim index, human_approval
flipped locally); the real claim repository on disk is never touched.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_clause_match import match_clause  # noqa: E402
from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from requirement_match import load_reusable_claims  # noqa: E402


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


def _simulate_reusable(claim_id: str) -> list:
    """Return reusable claims with one claim locally approved in-memory only."""
    claim_index = copy.deepcopy(CLAIM_INDEX)
    claim_index[claim_id]["human_approval"] = True
    return load_reusable_claims(claim_index, EVIDENCE_INDEX)


# ======================================================================
# A. Genuine "strong Excel" clause through match_clause() -- qualifier
#    inference behaves as expected: base Excel capability supported,
#    elevated-proficiency qualifier unestablished -> PARTIAL.
# ======================================================================
reusable_excel = _simulate_reusable("CLAIM_DCOMMERCE_001")
clause_a = match_clause(
    clause_id="CLAUSE_A_STRONG_EXCEL",
    clause_text="strong Excel skills",
    reusable_claims=reusable_excel,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    clause_a["result"] == "PARTIAL",
    f"clause A ('strong Excel skills') must resolve PARTIAL through match_clause(), got {clause_a['result']}",
)
assert_true(
    "excel_elevated_proficiency_qualifier" in clause_a["explanation"],
    "clause A explanation must name the missing elevated-proficiency qualifier",
)
print("PASS A: genuine 'strong Excel skills' clause resolves PARTIAL through the Application Clause path.")


# ======================================================================
# B. "strong interest in Excel skills development" through match_clause()
#    -- must NOT manufacture elevated Excel proficiency (Cursor
#    SEMANTIC_PROXIMITY_FALSE_POSITIVE, application-clause surface).
# ======================================================================
clause_b = match_clause(
    clause_id="CLAUSE_B_INTEREST",
    clause_text="strong interest in Excel skills development",
    reusable_claims=reusable_excel,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    "excel_elevated_proficiency_qualifier" not in clause_b["explanation"],
    "clause B must not manufacture the elevated Excel-proficiency qualifier -- 'strong' modifies 'interest', not Excel proficiency",
)
assert_true(
    clause_b["result"] == "SUPPORTED",
    f"clause B must resolve SUPPORTED (baseline excel_proficiency only, full subset match against the base Excel claim), got {clause_b['result']}",
)
print("PASS B: 'strong interest in Excel skills development' does not manufacture the elevated-proficiency qualifier through the Application Clause path.")


# ======================================================================
# C. Genuine degree-from-top-tier-university clause through match_clause()
#    -- institutional qualifier behaves as expected: base credential
#    supported, institutional-quality qualifier unestablished -> PARTIAL.
# ======================================================================
reusable_degree = _simulate_reusable("CLAIM_EDU_UNWE_001")
clause_c = match_clause(
    clause_id="CLAUSE_C_TOP_TIER_DEGREE",
    clause_text="Bachelor's degree from a top-tier university",
    reusable_claims=reusable_degree,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    clause_c["result"] == "PARTIAL",
    f"clause C ('Bachelor's degree from a top-tier university') must resolve PARTIAL through match_clause(), got {clause_c['result']}",
)
assert_true(
    "institutional_quality_qualifier" in clause_c["explanation"],
    "clause C explanation must name the missing institutional-quality qualifier",
)
print("PASS C: genuine degree-from-top-tier-university clause resolves PARTIAL through the Application Clause path.")


# ======================================================================
# D. Cross-clause/non-credential top-tier-university wording through
#    match_clause() -- must NOT manufacture the institutional-quality
#    qualifier (Cursor CROSS_CLAUSE_QUALIFIER_CAPTURE, application-clause
#    surface).
# ======================================================================
clause_d = match_clause(
    clause_id="CLAUSE_D_CROSS_CLAUSE",
    clause_text="Bachelor's degree preferred; experience working with customers from top-tier universities",
    reusable_claims=reusable_degree,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    "institutional_quality_qualifier" not in clause_d["explanation"],
    "clause D must not manufacture the institutional-quality qualifier -- the top-tier universities mention is about customers, not the credential's source",
)
assert_true(
    clause_d["result"] == "SUPPORTED",
    f"clause D must resolve SUPPORTED (baseline bachelors_degree_credential only, full subset match against the base degree claim), got {clause_d['result']}",
)
print("PASS D: cross-clause 'customers from top-tier universities' wording does not manufacture the institutional-quality qualifier through the Application Clause path.")


# ======================================================================
# E. FALSE_CREDENTIAL_SOURCE_LINKAGE (Cursor final review) through
#    match_clause() -- "candidates", not the degree itself, are described
#    as coming from the top-tier institution. Must NOT manufacture the
#    institutional-quality qualifier, and must resolve SUPPORTED (full
#    baseline match), not falsely demoted to PARTIAL.
# ======================================================================
clause_e = match_clause(
    clause_id="CLAUSE_E_FALSE_LINKAGE",
    clause_text="Bachelor's degree required for candidates from top-tier universities",
    reusable_claims=reusable_degree,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    "institutional_quality_qualifier" not in clause_e["explanation"],
    "clause E must not manufacture the institutional-quality qualifier -- 'candidates', not the degree, come from the top-tier universities",
)
assert_true(
    clause_e["result"] == "SUPPORTED",
    f"clause E must resolve SUPPORTED (baseline bachelors_degree_credential only, not falsely demoted to PARTIAL), got {clause_e['result']}",
)
print("PASS E: 'Bachelor's degree required for candidates from top-tier universities' does not manufacture the institutional-quality qualifier or falsely demote the match through the Application Clause path.")


# ======================================================================
# Real disk claim state confirmed unaffected by any simulation performed
# in this file.
# ======================================================================
cl_after = validate_claim_repository()
for claim_id in ("CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001"):
    assert_true(
        cl_after["index"][claim_id]["human_approval"] is False,
        f"{claim_id} must remain human_approval=false on disk after simulation",
    )
print("PASS F: real claim repository on disk is unaffected by in-memory simulation.")

print("ALL application_clause_qualifier_semantics_v1_test CHECKS PASSED")
