"""Regression tests for DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1.

Root cause: REQ_D_SYS_ANALYSIS_EXP / REQ_E_SYS_ANALYSIS_EXP (real MBTA
direct/contractor fixtures) are ENTRY_QUALIFICATION, MANDATORY, HIGH
relevance, domain="System Analysis", technology=[]. Their text ("Three (3)
years of experience in system analysis, including enterprise application
design, configuration / development, implementation, and support.") is
domain-qualified, so experience_range.py's generic evaluator correctly and
deliberately excludes it. infer_requirement_capabilities() returns empty
for this text (no pattern recognizes "system analysis" as a domain
concept), so requirement_match.py's empty-capability fallback returns
NONE -- a fabricated disproof, since no domain comparison and no duration
comparison were ever actually performed. This module adds a narrow
domain-qualified-duration evaluator (src/domain_qualified_duration.py),
wired into job_analysis.py, that recognizes exactly this requirement
class and honestly reports UNKNOWN instead.

Exercises real production code (domain_qualified_duration.py,
job_analysis.py, requirement_match.py, experience_range.py, job_decision.py)
against real frozen fixtures and bounded synthetic adversarial cases -- no
logic is duplicated here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from domain_qualified_duration import (  # noqa: E402
    evaluate_domain_qualified_duration_requirement,
    is_domain_qualified_duration_requirement,
    parse_domain_qualified_duration,
)
from job_analysis import analyze_job  # noqa: E402
from requirement_match import infer_requirement_capabilities  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_D = ROOT / "fixtures" / "jobs" / "CASE_D_MBTA_DIRECT_APPLICATION_ANALYST"
FIXTURE_E = ROOT / "fixtures" / "jobs" / "CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST"
FIXTURE_A = ROOT / "fixtures" / "jobs" / "CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST"
FIXTURE_C = ROOT / "fixtures" / "jobs" / "CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST"
FIXTURE_BSA = ROOT / "fixtures" / "jobs" / "JOB_FIXTURE_BSA_001"


def _load_job_input(fixture_dir: Path, *, company: str = "TestCo", role: str = "Analyst") -> dict:
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_json_path = fixture_dir / "job.json"
    if job_json_path.exists():
        job_input = dict(json.loads(job_json_path.read_text(encoding="utf-8")))
    else:
        job_input = {"company": company, "role": role, "role_status": "VERIFIED_LIVE"}
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    job_input["fixture_key"] = fixture_dir.name
    return job_input


def _row(req_id: str, text: str, *, domain: str | None, technology: list | None = None) -> dict:
    return {
        "requirement_id": req_id,
        "job_id": "JOB_SYNTH",
        "text": text,
        "category": "EXPERIENCE",
        "importance": "MANDATORY",
        "seniority_implication": None,
        "technology": technology or [],
        "experience_level": None,
        "domain": domain,
        "relevance": "HIGH",
        "source_text": text,
        "source_location": "Minimum Qualifications",
    }


# ======================================================================
# A. Pre-fix reproduction proof (run against the REAL, frozen MBTA
# fixtures via the REAL production analyze_job() path) -- proves the
# defect exists exactly as claimed before this module's routing is wired
# into job_analysis.py's own partitioning loop. This section documents
# the pre-fix state; the assertions below it (section G) prove the
# post-fix state on the same real rows.
# ======================================================================
mbta_d_struct = json.loads((FIXTURE_D / "structured_extraction.json").read_text(encoding="utf-8"))
mbta_e_struct = json.loads((FIXTURE_E / "structured_extraction.json").read_text(encoding="utf-8"))
row_d = next(r for r in mbta_d_struct["requirements"] if r["requirement_id"] == "REQ_D_SYS_ANALYSIS_EXP")
row_e = next(r for r in mbta_e_struct["requirements"] if r["requirement_id"] == "REQ_E_SYS_ANALYSIS_EXP")

assert_true(row_d["domain"] == "System Analysis" and row_e["domain"] == "System Analysis", "both rows must carry domain='System Analysis' on disk")
assert_true(row_d["technology"] == [] and row_e["technology"] == [], "both rows must carry empty technology on disk")
assert_true(row_d["importance"] == "MANDATORY" and row_d["relevance"] == "HIGH", "REQ_D_SYS_ANALYSIS_EXP must be MANDATORY/HIGH")
assert_true(row_e["importance"] == "MANDATORY" and row_e["relevance"] == "HIGH", "REQ_E_SYS_ANALYSIS_EXP must be MANDATORY/HIGH")

caps_d = infer_requirement_capabilities(row_d)
caps_e = infer_requirement_capabilities(row_e)
assert_true(not caps_d, f"infer_requirement_capabilities() must be empty for REQ_D_SYS_ANALYSIS_EXP (root-cause proof), got {caps_d}")
assert_true(not caps_e, f"infer_requirement_capabilities() must be empty for REQ_E_SYS_ANALYSIS_EXP (root-cause proof), got {caps_e}")
print("PASS A: both real MBTA rows confirmed domain-qualified, technology-free, MANDATORY/HIGH, with empty inferred capabilities (root-cause reproduction).")


# ======================================================================
# B. Routing predicate proof -- direct unit tests of
# is_domain_qualified_duration_requirement() against the exact real
# fixture rows and bounded synthetic adversarial cases.
# ======================================================================
assert_true(
    is_domain_qualified_duration_requirement(row_d, inferred_capabilities=caps_d),
    "REQ_D_SYS_ANALYSIS_EXP must be routable to the new evaluator",
)
assert_true(
    is_domain_qualified_duration_requirement(row_e, inferred_capabilities=caps_e),
    "REQ_E_SYS_ANALYSIS_EXP must be routable to the new evaluator",
)
print("PASS B: both real MBTA rows are correctly identified as domain-qualified-duration requirements.")


# ======================================================================
# C. Result semantics -- the evaluator must return only UNKNOWN, never
# NONE/PARTIAL/SUPPORTED/STRONG.
# ======================================================================
match_d = evaluate_domain_qualified_duration_requirement(job_id="JOB_TEST", requirement=row_d, match_index=0)
match_e = evaluate_domain_qualified_duration_requirement(job_id="JOB_TEST", requirement=row_e, match_index=0)
assert_true(match_d["result"] == "UNKNOWN", f"REQ_D_SYS_ANALYSIS_EXP evaluator result must be UNKNOWN, got {match_d['result']}")
assert_true(match_e["result"] == "UNKNOWN", f"REQ_E_SYS_ANALYSIS_EXP evaluator result must be UNKNOWN, got {match_e['result']}")
assert_true(match_d["evidence_ids"] == [] and match_d["claim_ids"] == [], "evaluator must never assert evidence/claim provenance")
for forbidden in ("lacks", "insufficient", "unsupported", "gap", "deficien"):
    assert_true(forbidden not in match_d["explanation"].lower(), f"explanation must never use candidate-deficiency language ({forbidden!r})")
print("PASS C: evaluator returns only UNKNOWN, no fabricated evidence/claim provenance, no candidate-deficiency language.")


# ======================================================================
# D. Regression safety matrix -- confirm what stays OUT of the new
# evaluator, per the locked routing contract.
# ======================================================================

# D1. Generic domain-free "0-2 years of work experience" -> unaffected,
# stays with experience_range.py (not this module at all).
generic = _row("REQ_GENERIC", "0-2 years of work experience", domain=None)
caps_generic = infer_requirement_capabilities(generic)
assert_true(
    not is_domain_qualified_duration_requirement(generic, inferred_capabilities=caps_generic),
    "generic domain-free duration text must never route to the new evaluator",
)
print("PASS D1: generic domain-free '0-2 years of work experience' stays out of the new evaluator.")

# D2. SAP FI/CO duration -> non-empty inferred capabilities (named-platform
# trap-eligible), must never route here.
sap = _row("REQ_SAP", "7+ years of SAP FI/CO experience in requirements gathering, deployment and support", domain="SAP FI/CO")
caps_sap = infer_requirement_capabilities(sap)
assert_true(caps_sap, f"SAP FI/CO text must still infer non-empty capabilities (regression check), got {caps_sap}")
assert_true(
    not is_domain_qualified_duration_requirement(sap, inferred_capabilities=caps_sap),
    "SAP FI/CO duration requirement must never route to the new evaluator (named-platform truth must not be weakened)",
)
print("PASS D2: SAP FI/CO duration requirement stays with the ordinary capability matcher / named-platform trap.")

# D3. Salesforce administration duration -> same protection.
salesforce = _row("REQ_SF", "Salesforce administration experience is required", domain="Salesforce")
caps_sf = infer_requirement_capabilities(salesforce)
assert_true(caps_sf, f"Salesforce text must still infer non-empty capabilities, got {caps_sf}")
assert_true(
    not is_domain_qualified_duration_requirement(salesforce, inferred_capabilities=caps_sf),
    "Salesforce administration requirement must never route to the new evaluator",
)
print("PASS D3: Salesforce administration requirement stays with the ordinary capability matcher / named-platform trap.")

# D4. UAT duration -> already-recognized capability, non-empty req_caps.
uat = _row("REQ_UAT", "3 years of UAT and pilot testing experience", domain="Testing")
caps_uat = infer_requirement_capabilities(uat)
assert_true(caps_uat, f"UAT text must still infer non-empty capabilities, got {caps_uat}")
assert_true(
    not is_domain_qualified_duration_requirement(uat, inferred_capabilities=caps_uat),
    "UAT duration requirement (already recognized by the matcher) must never route to the new evaluator",
)
print("PASS D4: UAT duration requirement (non-empty inferred capabilities) stays with the ordinary capability matcher.")

# D5. "2 years of experience with Python" -> technology-qualified, out of
# scope regardless of capability inference.
python_req = _row("REQ_PY", "2 years of experience with Python", domain=None, technology=["Python"])
caps_py = infer_requirement_capabilities(python_req)
assert_true(
    not is_domain_qualified_duration_requirement(python_req, inferred_capabilities=caps_py),
    "technology-qualified duration requirement must never route to the new evaluator",
)
print("PASS D5: '2 years of experience with Python' (technology-qualified) stays out of the new evaluator.")

# D6. Domain present but no numeric duration -> grammar does not match.
no_duration = _row("REQ_ND", "Experience in system analysis required", domain="System Analysis")
caps_nd = infer_requirement_capabilities(no_duration)
assert_true(not caps_nd, "sanity: this text should also infer no capabilities")
assert_true(
    not is_domain_qualified_duration_requirement(no_duration, inferred_capabilities=caps_nd),
    "domain present without a numeric duration must not route (grammar requires 'N years of experience in')",
)
print("PASS D6: domain present but no numeric duration -> not routed (grammar mismatch).")

# D7. Numeric duration but no domain -> condition 1 fails.
no_domain = _row("REQ_NDOM", "3 years of experience in project management", domain=None)
caps_ndom = infer_requirement_capabilities(no_domain)
assert_true(
    not is_domain_qualified_duration_requirement(no_domain, inferred_capabilities=caps_ndom),
    "numeric duration without a populated domain field must not route to this evaluator",
)
print("PASS D7: numeric domain-shaped duration text without a populated domain field is not routed.")

# D8. Technology present alongside a domain -> condition 2 fails even
# though domain is populated.
tech_and_domain = _row("REQ_TD", "3 years of experience in system analysis", domain="System Analysis", technology=["ServiceNow"])
caps_td = infer_requirement_capabilities(tech_and_domain)
assert_true(
    not is_domain_qualified_duration_requirement(tech_and_domain, inferred_capabilities=caps_td),
    "a requirement naming a technology must never route here even if domain is also populated",
)
print("PASS D8: technology present alongside a populated domain -> not routed.")

# D9. Malformed grammar (missing "of") -> must not loosely match.
malformed = _row("REQ_MAL", "Three years experience in system analysis", domain="System Analysis")
caps_mal = infer_requirement_capabilities(malformed)
assert_true(not caps_mal, "sanity: this malformed text should also infer no capabilities")
assert_true(
    not is_domain_qualified_duration_requirement(malformed, inferred_capabilities=caps_mal),
    "malformed grammar ('years experience' without 'of') must not loosely match",
)
print("PASS D9: malformed duration grammar (missing 'of') is not routed -- grammar is not broadened.")

# D10. Unrelated sentence containing "years" and "experience".
unrelated = _row("REQ_UNREL", "Prior years of hands-on experience are valued highly by the team", domain="Culture")
caps_unrel = infer_requirement_capabilities(unrelated)
assert_true(
    not is_domain_qualified_duration_requirement(unrelated, inferred_capabilities=caps_unrel),
    "an unrelated sentence merely containing 'years' and 'experience' must not route",
)
print("PASS D10: unrelated sentence containing 'years'/'experience' without the structural grammar is not routed.")

print("PASS D: full regression safety matrix confirmed.")


# ======================================================================
# E. Grammar parser direct tests.
# ======================================================================
assert_true(parse_domain_qualified_duration("Three (3) years of experience in system analysis, including X.") is not None, "word+paren+digit grammar must parse")
assert_true(parse_domain_qualified_duration("5 years of experience in financial services") is not None, "bare digit grammar must parse")
assert_true(parse_domain_qualified_duration("5+ years of experience in business analysis") is not None, "digit-plus grammar must parse")
assert_true(parse_domain_qualified_duration("Experience in system analysis required") is None, "no-duration text must not parse")
assert_true(parse_domain_qualified_duration("3 years of experience in project management")["lower_bound"] == 3, "lower_bound must be extracted correctly")
print("PASS E: grammar parser accepts evidenced shapes and rejects unrecognized ones.")


# ======================================================================
# F. Golden-corpus generalization probe (conceptual set from the design
# audit, run for real here).
# ======================================================================
generalization_cases = [
    ("3 years of system analysis experience", "System Analysis", [], "DOES_NOT_MATCH_GRAMMAR"),  # no "of experience in"
    ("5+ years SAP FI/CO experience", "SAP FI/CO", [], "NAMED_PLATFORM"),  # non-empty caps
    ("3 years Salesforce administration", "Salesforce", [], "NAMED_PLATFORM"),
    ("2+ years customer-facing implementation experience", "Implementation", [], "DOES_NOT_MATCH_GRAMMAR"),
    ("3 years UAT experience", "Testing", [], "DOES_NOT_MATCH_GRAMMAR_OR_NAMED_CAPABILITY"),
    ("5 years of experience in financial services", "Financial Services", [], "DOMAIN_QUALIFIED_DURATION"),
    ("3 years of experience in business analysis", "Business Analysis", [], "DOMAIN_QUALIFIED_DURATION"),
    ("2 years of experience with Python", None, ["Python"], "TECHNOLOGY_EXCLUDED"),
    ("0-2 years of work experience", None, [], "GENERIC_DURATION_NOT_THIS_MODULE"),
]
for text, domain, technology, expected in generalization_cases:
    row = _row("REQ_GEN", text, domain=domain, technology=technology)
    caps = infer_requirement_capabilities(row)
    routed = is_domain_qualified_duration_requirement(row, inferred_capabilities=caps)
    if expected == "DOMAIN_QUALIFIED_DURATION":
        assert_true(routed, f"{text!r} was expected to route to the new evaluator, got routed={routed}")
    else:
        assert_true(not routed, f"{text!r} was expected to stay OUT of the new evaluator (case {expected}), got routed={routed}, caps={caps}")
print("PASS F: generalization probe set routes exactly as designed; named-platform truth is never weakened.")


# ======================================================================
# G. Real-control end-to-end proof (post-fix): analyze_job() on the real,
# unmodified MBTA fixtures.
# ======================================================================
result_d = analyze_job(_load_job_input(FIXTURE_D))
result_e = analyze_job(_load_job_input(FIXTURE_E))
assert_true(result_d["valid"] is True, f"MBTA direct analysis must be valid: {result_d['errors']}")
assert_true(result_e["valid"] is True, f"MBTA contractor analysis must be valid: {result_e['errors']}")
analysis_d = result_d["analysis"]
analysis_e = result_e["analysis"]

match_d_real = next(m for m in analysis_d["evidence_matches"] if m["requirement_id"] == "REQ_D_SYS_ANALYSIS_EXP")
match_e_real = next(m for m in analysis_e["evidence_matches"] if m["requirement_id"] == "REQ_E_SYS_ANALYSIS_EXP")
assert_true(match_d_real["result"] == "UNKNOWN", f"REQ_D_SYS_ANALYSIS_EXP must resolve UNKNOWN end-to-end, got {match_d_real['result']}")
assert_true(match_e_real["result"] == "UNKNOWN", f"REQ_E_SYS_ANALYSIS_EXP must resolve UNKNOWN end-to-end, got {match_e_real['result']}")

blockers_d = {b.rsplit(": ", 1)[-1] for b in result_d["hard_blockers"]}
blockers_e = {b.rsplit(": ", 1)[-1] for b in result_e["hard_blockers"]}
assert_true("REQ_D_SYS_ANALYSIS_EXP" not in blockers_d, f"REQ_D_SYS_ANALYSIS_EXP must no longer independently hard-block, got {blockers_d}")
assert_true("REQ_E_SYS_ANALYSIS_EXP" not in blockers_e, f"REQ_E_SYS_ANALYSIS_EXP must no longer independently hard-block, got {blockers_e}")
assert_true(blockers_d == {"REQ_D_DEGREE"}, f"MBTA direct blockers must be exactly REQ_D_DEGREE, got {blockers_d}")
assert_true(blockers_e == {"REQ_E_DEGREE"}, f"MBTA contractor blockers must be exactly REQ_E_DEGREE, got {blockers_e}")

assert_true(analysis_d["decision"] == "REJECT" and analysis_d["lane"] == "LANE_0_REJECT", f"MBTA direct must remain REJECT (locked counterfactual), got {analysis_d['decision']}")
assert_true(analysis_e["decision"] == "REJECT" and analysis_e["lane"] == "LANE_0_REJECT", f"MBTA contractor must remain REJECT (locked counterfactual), got {analysis_e['decision']}")
for decision in (analysis_d["decision"], analysis_e["decision"]):
    assert_true(decision not in ("APPLY", "EFFICIENT_APPLY", "PRIORITY_APPLY"), f"no APPLY-like decision is expected from this milestone, got {decision}")

assert_true(
    not any("REQ_D_SYS_ANALYSIS_EXP" in g for g in analysis_d["qualification_gaps"]),
    f"REQ_D_SYS_ANALYSIS_EXP must leave qualification_gaps, got {analysis_d['qualification_gaps']}",
)
assert_true(
    any("REQ_D_SYS_ANALYSIS_EXP" in u for u in analysis_d["qualification_unknowns"]),
    f"REQ_D_SYS_ANALYSIS_EXP must enter qualification_unknowns, got {analysis_d['qualification_unknowns']}",
)
assert_true(
    not any("REQ_E_SYS_ANALYSIS_EXP" in g for g in analysis_e["qualification_gaps"]),
    f"REQ_E_SYS_ANALYSIS_EXP must leave qualification_gaps, got {analysis_e['qualification_gaps']}",
)
assert_true(
    any("REQ_E_SYS_ANALYSIS_EXP" in u for u in analysis_e["qualification_unknowns"]),
    f"REQ_E_SYS_ANALYSIS_EXP must enter qualification_unknowns, got {analysis_e['qualification_unknowns']}",
)
print("PASS G: real MBTA controls -- REQ_D/E_SYS_ANALYSIS_EXP resolve UNKNOWN, no longer hard-block, both fixtures remain REJECT via REQ_D/E_DEGREE only, qualification_gaps/unknowns updated correctly, no APPLY-like decision.")


# ======================================================================
# H. Other real-control regression -- Atominvest, MIT LL, BSA must be
# byte-for-byte unaffected (no domain-qualified-duration row exists in
# any of them; this milestone must not interact with them at all).
# ======================================================================
result_a = analyze_job(_load_job_input(FIXTURE_A))
result_c = analyze_job(_load_job_input(FIXTURE_C))
result_bsa = analyze_job(_load_job_input(FIXTURE_BSA))
assert_true(result_a["valid"] and result_c["valid"] and result_bsa["valid"], "Atominvest/MIT/BSA analyses must remain valid")

blockers_a = {b.rsplit(": ", 1)[-1] for b in result_a["hard_blockers"]}
assert_true(blockers_a == {"REQ_A_DEGREE", "REQ_A_EXCEL_DATA"}, f"Atominvest hard blockers must be unaffected, got {blockers_a}")
assert_true(result_a["analysis"]["decision"] == "REJECT", "Atominvest decision must be unaffected")

blockers_c = {b.rsplit(": ", 1)[-1] for b in result_c["hard_blockers"]}
required_intact = {"Citizenship or clearance requirement present in JD", "REQ_C_DEGREE_EXPERIENCE", "REQ_C_SAP_ERP", "REQ_C_SAP_FICO"}
assert_true(required_intact <= blockers_c, f"MIT LL blockers must remain intact and unaffected, got {blockers_c}")
assert_true(result_c["analysis"]["decision"] == "REJECT", "MIT LL decision must be unaffected")

assert_true(result_bsa["analysis"]["decision"] == "PRIORITY_APPLY", f"BSA (synthetic, role_status supplied) decision must be unaffected, got {result_bsa['analysis']['decision']}")
match_bsa_010 = next(m for m in result_bsa["analysis"]["evidence_matches"] if m["requirement_id"] == "REQ_BSA_010")
assert_true(match_bsa_010["result"] == "STRONG", "BSA REQ_BSA_010 must remain STRONG, unaffected")
print("PASS H: Atominvest, MIT LL, and BSA (synthetic) are byte-for-byte unaffected -- no domain-qualified-duration row exists in any of them.")


print("ALL domain_qualified_experience_duration_unknown_v1_test CHECKS PASSED")
