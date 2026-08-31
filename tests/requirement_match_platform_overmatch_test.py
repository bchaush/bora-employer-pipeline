"""Regression tests for JOB_ANALYSIS_REMEDIATION_V1: a named/deep enterprise-
platform requirement must not be silently satisfied by generic transferable
capability overlap (e.g. "requirements gathering" text coincidentally hitting
Winter Walk's requirements_elicitation capability).

Exercises the real, unmodified production matcher (src/requirement_match.py)
against the real trusted Claim/Evidence repositories -- no logic is
duplicated or reimplemented here.

Root defect reproduced (pre-fix): "7+ years of SAP FI/CO experience in
requirements gathering, deployment and support" matched STRONG via
CLAIM_WW_001/WW_ARCH_001 solely because of the phrase "requirements
gathering" -- the matcher never considered "SAP FI/CO" or "7+ years" at all.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from requirement_match import (  # noqa: E402
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
REUSABLE_CLAIMS = load_reusable_claims(CLAIM_INDEX, EVIDENCE_INDEX)


def run_match(requirement_id: str, text: str, *, technology: list[str] | None = None) -> dict:
    requirement = {
        "requirement_id": requirement_id,
        "text": text,
        "source_text": text,
        "domain": None,
        "category": "TECHNICAL",
        "technology": technology or [],
        "relevance": "HIGH",
        "importance": "MANDATORY",
    }
    return match_requirement(
        job_id="JOB_TEST",
        requirement=requirement,
        reusable_claims=REUSABLE_CLAIMS,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )


# ======================================================================
# 1. The demonstrated HIGH defect: SAP FI/CO deep/named-platform requirement
#    must NOT be STRONG/SUPPORTED from generic "requirements gathering" text.
# ======================================================================
sap_fico = run_match(
    "REQ_SAP_FICO",
    "7+ years of SAP FI/CO experience in requirements gathering, deployment and support",
    technology=["SAP FI/CO"],
)
assert_true(
    sap_fico["result"] not in {"STRONG", "SUPPORTED"},
    f"MIT SAP FI/CO requirement must not be STRONG/SUPPORTED from generic requirements-gathering overlap alone; got {sap_fico['result']} ({sap_fico['explanation']})",
)
assert_true(sap_fico["evidence_ids"] == [] and sap_fico["claim_ids"] == [], "no Winter Walk claim/evidence should be cited for an unsupported SAP FI/CO requirement")
print(f"PASS 1: SAP FI/CO deep requirement result={sap_fico['result']} (not STRONG/SUPPORTED); {sap_fico['explanation']}")


# ======================================================================
# 2. Legitimate generic requirements-elicitation requirement must still
#    positively match Winter Walk evidence (transferability preserved).
# ======================================================================
generic_req = run_match(
    "REQ_GENERIC_REQUIREMENTS",
    "Gather business requirements from stakeholders",
)
assert_true(
    generic_req["result"] in {"STRONG", "SUPPORTED"},
    f"a genuinely generic requirements-elicitation requirement must still match Winter Walk evidence; got {generic_req['result']}",
)
assert_true(generic_req["claim_ids"] == ["CLAIM_WW_001"], f"expected CLAIM_WW_001 provenance, got {generic_req['claim_ids']}")
print(f"PASS 2: generic requirements-elicitation requirement result={generic_req['result']} via {generic_req['claim_ids']} (transferability preserved)")


# ======================================================================
# 3. Named-platform requirement combined with coincidental generic overlap
#    must not become direct platform expertise (Salesforce case, mirrors
#    the pre-existing, already-correct trap mechanism this fix extends).
# ======================================================================
salesforce_combo = run_match(
    "REQ_SALESFORCE_COMBO",
    "Work with teams implementing Salesforce workflows, gathering requirements from stakeholders",
    technology=["Salesforce"],
)
assert_true(
    salesforce_combo["result"] == "NONE",
    f"Salesforce + coincidental requirements-gathering overlap must remain NONE, not become direct Salesforce expertise; got {salesforce_combo['result']}",
)
print(f"PASS 3: Salesforce + generic-overlap combo result={salesforce_combo['result']} (existing trap mechanism unaffected/consistent)")


# ======================================================================
# 4. A soft/preferred SAP mention with no SAP evidence: may remain NONE or
#    UNKNOWN per existing architecture, but must never become a false
#    direct positive.
# ======================================================================
soft_sap = run_match(
    "REQ_SAP_SOFT",
    "Exposure to SAP is a plus",
    technology=["SAP"],
)
assert_true(
    soft_sap["result"] not in {"STRONG", "SUPPORTED", "PARTIAL"},
    f"a soft/preferred SAP mention with no SAP evidence must never become a false direct/partial positive; got {soft_sap['result']}",
)
print(f"PASS 4: soft SAP exposure mention result={soft_sap['result']} (no false direct positive)")


# ======================================================================
# 5. Cross-platform consistency: Workday/ServiceNow/GCP traps must remain
#    unaffected by this change (same regex bucket extended, not replaced).
# ======================================================================
workday_case = run_match("REQ_WORKDAY", "5+ years of Workday HCM configuration and support")
assert_true(workday_case["result"] == "NONE", f"Workday requirement must remain trapped to NONE; got {workday_case['result']}")
gcp_case = run_match("REQ_GCP", "Experience with Google Cloud infrastructure")
assert_true(gcp_case["result"] == "NONE", f"GCP requirement must remain trapped to NONE; got {gcp_case['result']}")
print(f"PASS 5: Workday result={workday_case['result']}, GCP result={gcp_case['result']} (existing platform traps unaffected)")

print("ALL requirement_match_platform_overmatch_test CHECKS PASSED")
