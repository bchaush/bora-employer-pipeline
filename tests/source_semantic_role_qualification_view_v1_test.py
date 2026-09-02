"""Regression tests for SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1 and its
SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1 follow-up.

Root cause (original milestone): job_decision.detect_hard_blockers()
previously treated every importance=MANDATORY, relevance=HIGH, result=NONE
Requirement identically as a candidate-entry hard blocker, with no
distinction between a genuine entry qualification (JD "Requirements"/
"Minimum Qualifications" section) and an ordinary post-hire duty (JD "What
You'll Be Doing"/"Responsibilities"/"Primary Duties" section, which never
carries prior-possession language). Confirmed live, real-fixture instances:
CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST's REQ_A_CONFIG_IMPLEMENTATION and
REQ_A_QA_TROUBLESHOOTING, and CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST's
REQ_C_REGRESSION_TESTING.

Bounded correction (this file's current version) closes three compliance
gaps a follow-up audit found in the first implementation:

1. PERSISTENCE: classification is now backfilled into every frozen
   structured_extraction.json Requirement row and CONSUMED unchanged at
   runtime (requirement_source_role.resolve_persisted_or_fallback()) --
   never silently recomputed by analyze_job(). classify_source_semantic_roles()
   itself is reserved for extraction/ingestion/backfill/drift-detection.
2. MISSING/INVALID SAFETY: a missing or invalid persisted role now derives
   AMBIGUOUS (never blocks, always human_review_required), never a silent
   YES -- for every caller, including one that bypasses normalization.
3. APPLICATION_OR_LEGAL_GATE: only routed there when provably covered by a
   named, tested dedicated consumer (job_decision.py's JD-text-level
   citizenship/clearance check, sharing requirement_source_role.py's
   CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN as its single source of
   truth). License/certification prerequisites route to ENTRY_QUALIFICATION.
   Uncovered citizenship/clearance/access language resolves AMBIGUOUS and
   surfaces in unresolved_gate_observations -- never silently dropped.
4. WORDING: responsibility_evidence_unknowns no longer claims "no adjacent
   evidence" -- explicitly matcher-bounded wording, plus a structured
   capability_inference_state distinguishing "matcher inferred nothing" from
   "capabilities inferred, no approved match" from "an approved match exists".

Exercises real production code (requirement_source_role.py,
requirement_normalize.py, job_decision.py, job_analysis.py) against real
frozen (now-backfilled) fixtures and bounded synthetic adversarial cases --
no logic is duplicated here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from job_analysis import analyze_job  # noqa: E402
from job_decision import detect_hard_blockers  # noqa: E402
from requirement_normalize import normalize_structured_requirements  # noqa: E402
from requirement_source_role import (  # noqa: E402
    CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN,
    classify_source_semantic_roles,
    derive_human_review_required,
    derive_qualification_gate,
    is_covered_by_citizenship_clearance_consumer,
    resolve_persisted_or_fallback,
)
from schema_validation import build_draft202012_validator  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_A = ROOT / "fixtures" / "jobs" / "CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST"
FIXTURE_C = ROOT / "fixtures" / "jobs" / "CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST"
FIXTURE_BSA = ROOT / "fixtures" / "jobs" / "JOB_FIXTURE_BSA_001"
FIXTURE_D = ROOT / "fixtures" / "jobs" / "CASE_D_MBTA_DIRECT_APPLICATION_ANALYST"
FIXTURE_E = ROOT / "fixtures" / "jobs" / "CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST"
REQUIREMENT_SCHEMA_PATH = ROOT / "schemas" / "requirement.schema.json"


def _load_job_input(fixture_dir: Path, *, company: str = "TestCo", role: str = "Analyst") -> dict:
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_json_path = fixture_dir / "job.json"
    if job_json_path.exists():
        job_input = dict(json.loads(job_json_path.read_text(encoding="utf-8")))
    else:
        job_input = {"company": company, "role": role}
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    job_input["fixture_key"] = fixture_dir.name
    return job_input


def _row(req_id: str, text: str, location: str, *, importance: str = "MANDATORY", relevance: str = "HIGH") -> dict:
    return {
        "requirement_id": req_id,
        "job_id": "JOB_SYNTH",
        "text": text,
        "category": "TEST",
        "importance": importance,
        "seniority_implication": None,
        "technology": [],
        "experience_level": None,
        "domain": None,
        "relevance": relevance,
        "source_text": text,
        "source_location": location,
    }


# ======================================================================
# A. Classification truth table -- direct classifier unit tests.
# ======================================================================
truth_table = [
    ("REQ_1", "Get hands-on with customer data, configuring and implementing them.", "What You'll Be Doing", "ROLE_RESPONSIBILITY"),
    ("REQ_2", "Bachelor's Degree (or higher) from top-tier university", "Requirements", "ENTRY_QUALIFICATION"),
    ("REQ_3", "Maintains a set of regression test scenarios/scripts, performs testing", "Primary Duties -- Systems Upgrade", "ROLE_RESPONSIBILITY"),
    ("REQ_4", "7+ years of SAP FI/CO experience in requirements gathering, deployment and support", "Minimum / Required Qualifications", "ENTRY_QUALIFICATION"),
    ("REQ_5", "US citizenship required to obtain and maintain a security clearance.", "Citizenship / Security Clearance", "APPLICATION_OR_LEGAL_GATE"),
    ("REQ_6", "Strong Microsoft Office proficiency (Word, Excel, Outlook, PowerPoint, Teams).", "Required Skills", "ENTRY_QUALIFICATION"),
]
truth_requirements = [_row(rid, text, loc) for rid, text, loc, _expected in truth_table]
truth_classified = classify_source_semantic_roles(truth_requirements)
for (rid, _text, _loc, expected), classification in zip(truth_table, truth_classified):
    assert_true(
        classification["source_semantic_role"] == expected,
        f"{rid}: expected source_semantic_role={expected}, got {classification['source_semantic_role']} "
        f"(basis: {classification['source_semantic_role_basis']})",
    )
print("PASS A: classification truth table (real-fixture-shaped rows) resolves as expected.")


# ======================================================================
# B. Adversarial case 1 -- Responsibilities, no prerequisite language.
# ======================================================================
case1 = _row("REQ_ADV_1", "Configure customer platforms.", "Responsibilities")
c1 = classify_source_semantic_roles([case1])[0]
assert_true(c1["source_semantic_role"] == "ROLE_RESPONSIBILITY", f"case 1 expected ROLE_RESPONSIBILITY, got {c1}")
assert_true(derive_qualification_gate(c1["source_semantic_role"]) == "NO", "case 1: qualification_gate must be NO")
print("PASS B (case 1): 'Responsibilities: Configure customer platforms.' -> ROLE_RESPONSIBILITY, no blocker eligibility.")


# ======================================================================
# C. Adversarial case 2 -- Responsibilities + explicit prerequisite language.
# ======================================================================
case2 = _row("REQ_ADV_2", "Must have 5 years of SAP experience.", "Responsibilities")
c2 = classify_source_semantic_roles([case2])[0]
assert_true(c2["source_semantic_role"] == "ENTRY_QUALIFICATION", f"case 2 expected ENTRY_QUALIFICATION (override), got {c2}")
assert_true(c2["explicit_prerequisite_language_present"] is True, "case 2: prerequisite language must be recorded True")
assert_true(derive_qualification_gate(c2["source_semantic_role"]) == "YES", "case 2: qualification_gate must be YES (override)")
merged_row_2 = dict(case2, **{k: v for k, v in c2.items() if not k.startswith("_")})
assert_true(
    derive_human_review_required(merged_row_2) is True,
    "case 2: human_review_required must be True -- an override, not the ordinary default, produced this classification",
)
print("PASS C (case 2): 'Responsibilities: Must have 5 years of SAP experience.' -> ENTRY_QUALIFICATION via prerequisite override, human review flagged.")


# ======================================================================
# D. Adversarial case 3 -- Requirements section, duty-shaped, no prerequisite.
# ======================================================================
case3 = _row("REQ_ADV_3", "Will configure customer platforms.", "Requirements")
c3 = classify_source_semantic_roles([case3])[0]
assert_true(c3["source_semantic_role"] == "AMBIGUOUS", f"case 3 expected AMBIGUOUS, got {c3}")
assert_true(derive_qualification_gate(c3["source_semantic_role"]) == "AMBIGUOUS", "case 3: qualification_gate must be AMBIGUOUS, never YES or NO")
merged_row_3 = dict(case3, **{k: v for k, v in c3.items() if not k.startswith("_")})
assert_true(derive_human_review_required(merged_row_3) is True, "case 3: human review must be required")
print("PASS D (case 3): 'Requirements: Will configure customer platforms.' -> AMBIGUOUS, no independent blocker, human review required.")


# ======================================================================
# E. Adversarial case 4 -- duplication under Minimum Qualifications.
# ======================================================================
dup_resp = _row("REQ_ADV_4A", "QA testing for new product features and bug fixes.", "Responsibilities")
dup_qual = _row("REQ_ADV_4B", "QA testing for new product features and bug fixes.", "Minimum Qualifications")
c4a, c4b = classify_source_semantic_roles([dup_resp, dup_qual])
assert_true(c4a["duplicated_under_requirements"] is True, f"case 4: duplication must be detected, got {c4a}")
assert_true(c4a["source_semantic_role"] == "ENTRY_QUALIFICATION", f"case 4: duplication override must promote to ENTRY_QUALIFICATION, got {c4a}")
merged_row_4a = dict(dup_resp, **{k: v for k, v in c4a.items() if not k.startswith("_")})
assert_true(derive_human_review_required(merged_row_4a) is True, "case 4: human review must be required for a duplication override")
assert_true(c4b["source_semantic_role"] == "ENTRY_QUALIFICATION", "case 4: the genuine Minimum Qualifications row itself must remain ENTRY_QUALIFICATION")
print("PASS E (case 4): duty duplicated under Responsibilities and Minimum Qualifications -> entry-relevant override recorded.")


# ======================================================================
# F. Adversarial case A (SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1) --
# explicit professional license/certification prerequisite, no dedicated
# consumer -- must route ENTRY_QUALIFICATION with prerequisite provenance
# preserved, never silently discarded merely because it is legal/licensing.
# ======================================================================
case_license = _row("REQ_ADV_LICENSE", "Must hold a valid professional engineering license.", "Legal Requirements")
c_license = classify_source_semantic_roles([case_license])[0]
assert_true(
    c_license["source_semantic_role"] == "ENTRY_QUALIFICATION",
    f"license prerequisite (case A) expected ENTRY_QUALIFICATION, got {c_license}",
)
assert_true(derive_qualification_gate(c_license["source_semantic_role"]) == "YES", "license case: qualification_gate must be YES")
merged_license = dict(case_license, **{k: v for k, v in c_license.items() if not k.startswith("_")})
assert_true(derive_human_review_required(merged_license) is True, "license case: an override (legal-heading promoted to entry) must flag human review")
print("PASS F (case A): explicit professional license prerequisite -> ENTRY_QUALIFICATION, prerequisite provenance preserved, not discarded as legal.")


# ======================================================================
# G. Adversarial case B -- unresolved clearance/access prerequisite with NO
# proven dedicated consumer (paraphrased away from the named consumer's
# vocabulary) -- must resolve AMBIGUOUS, never a silently-uncovered
# APPLICATION_OR_LEGAL_GATE, and must surface in unresolved_gate_observations.
# ======================================================================
case_unresolved = _row(
    "REQ_ADV_UNRESOLVED_GATE",
    "Candidate must be eligible to obtain government facility access authorization.",
    "Additional Requirements",
)
assert_true(
    not is_covered_by_citizenship_clearance_consumer(case_unresolved["source_text"]),
    "test setup: this paraphrase must NOT overlap the named consumer's vocabulary",
)
c_unresolved = classify_source_semantic_roles([case_unresolved])[0]
assert_true(
    c_unresolved["source_semantic_role"] == "AMBIGUOUS",
    f"case B expected AMBIGUOUS (no proven consumer), got {c_unresolved}",
)
assert_true(
    "UNRESOLVED_LEGAL_OR_ACCESS_GATE" in c_unresolved["source_semantic_role_basis"],
    f"case B: basis must be marked as an unresolved legal/access gate, got {c_unresolved['source_semantic_role_basis']}",
)
assert_true(derive_qualification_gate(c_unresolved["source_semantic_role"]) == "AMBIGUOUS", "case B: no silent hard blocker")
merged_unresolved = dict(case_unresolved, **{k: v for k, v in c_unresolved.items() if not k.startswith("_")})
assert_true(derive_human_review_required(merged_unresolved) is True, "case B: human review required")

# Runtime no longer classifies inline -- simulate ingestion-time
# classification (exactly what the backfill process does) before handing
# the row to analyze_job(), which only ever CONSUMES a persisted role.
ingested_row = dict(case_unresolved, requirement_id="REQ_ADV_UNRESOLVED_GATE", **{
    k: v for k, v in c_unresolved.items() if not k.startswith("_")
})
analysis_unresolved = analyze_job(
    {
        "company": "TestCo",
        "role": "Analyst",
        "jd_text": case_unresolved["source_text"],
        "structured_extraction": {"requirements": [ingested_row]},
    }
)["analysis"]
unresolved_ids = {o["requirement_id"] for o in analysis_unresolved["unresolved_gate_observations"]}
assert_true(
    "REQ_ADV_UNRESOLVED_GATE" in unresolved_ids,
    f"case B: must surface in unresolved_gate_observations, got {analysis_unresolved['unresolved_gate_observations']}",
)
assert_true(
    not any("REQ_ADV_UNRESOLVED_GATE" in b for b in analysis_unresolved.get("gaps", []) + analysis_unresolved.get("qualification_gaps", [])),
    "case B: must never appear in qualification_gaps",
)
print("PASS G (case B): unresolved clearance/access prerequisite with no proven consumer -> AMBIGUOUS, no silent blocker, surfaced in unresolved_gate_observations.")


# ======================================================================
# H. Adversarial case D -- descriptive legal/compliance language, no
# prerequisite framing -- must NOT become an entry gate.
# ======================================================================
case_descriptive = _row(
    "REQ_ADV_DESCRIPTIVE",
    "This role complies with all applicable licensing and clearance regulations.",
    "Responsibilities",
)
c_descriptive = classify_source_semantic_roles([case_descriptive])[0]
assert_true(
    c_descriptive["source_semantic_role"] != "ENTRY_QUALIFICATION",
    f"case D: descriptive legal language must never become an entry gate, got {c_descriptive}",
)
print(f"PASS H (case D): descriptive legal/compliance language -> {c_descriptive['source_semantic_role']} (not converted into an entry gate).")


# ======================================================================
# I. Real MIT citizenship/clearance row -- proven named-consumer coverage,
# tested directly (not merely asserted): constructing jd_text from EXACTLY
# this row's source_text and confirming job_decision.detect_hard_blockers()
# fires on it.
# ======================================================================
mit_struct = json.loads((FIXTURE_C / "structured_extraction.json").read_text(encoding="utf-8"))
mit_citizenship_row = next(r for r in mit_struct["requirements"] if r["requirement_id"] == "REQ_C_CITIZENSHIP_CLEARANCE")
assert_true(
    mit_citizenship_row["source_semantic_role"] == "APPLICATION_OR_LEGAL_GATE",
    f"MIT citizenship row must be persisted as APPLICATION_OR_LEGAL_GATE, got {mit_citizenship_row.get('source_semantic_role')}",
)
proof_blockers = detect_hard_blockers(
    requirements=[],
    matches=[],
    seniority=None,
    role=None,
    jd_text=mit_citizenship_row["source_text"],
)
assert_true(
    any("Citizenship or clearance" in b for b in proof_blockers),
    f"the named dedicated consumer must fire when given ONLY this row's own source_text as jd_text, got {proof_blockers}",
)
assert_true(
    is_covered_by_citizenship_clearance_consumer(mit_citizenship_row["source_text"]),
    "is_covered_by_citizenship_clearance_consumer must independently confirm coverage for this exact row",
)
print("PASS I: MIT citizenship/clearance row's named dedicated consumer is directly proven to evaluate this exact requirement's semantics.")


# ======================================================================
# J. Persistence -- changing classifier behavior after a fixture is
# persisted does not change that fixture's consumed source_semantic_role;
# provenance and raw source text/location remain unchanged.
# ======================================================================
import requirement_source_role as rsr  # noqa: E402
import re as _re  # noqa: E402

atominvest_struct_before = json.loads((FIXTURE_A / "structured_extraction.json").read_text(encoding="utf-8"))
config_row_disk = next(r for r in atominvest_struct_before["requirements"] if r["requirement_id"] == "REQ_A_CONFIG_IMPLEMENTATION")
assert_true(
    config_row_disk["source_semantic_role"] == "ROLE_RESPONSIBILITY",
    f"REQ_A_CONFIG_IMPLEMENTATION must be persisted as ROLE_RESPONSIBILITY on disk, got {config_row_disk.get('source_semantic_role')}",
)
persisted_basis = config_row_disk["source_semantic_role_basis"]
persisted_version = config_row_disk["source_semantic_role_classifier_version"]
persisted_source_text = config_row_disk["source_text"]
persisted_source_location = config_row_disk["source_location"]

before_result = analyze_job(_load_job_input(FIXTURE_A))
role_before = next(r for r in before_result["analysis"]["requirements"] if r["requirement_id"] == "REQ_A_CONFIG_IMPLEMENTATION")["source_semantic_role"]

_orig_pattern = rsr._RESPONSIBILITY_HEADING_CUES
rsr._RESPONSIBILITY_HEADING_CUES = _re.compile(r"NEVER_MATCHES_ANYTHING_AT_ALL")
try:
    after_result = analyze_job(_load_job_input(FIXTURE_A))
    role_after = next(r for r in after_result["analysis"]["requirements"] if r["requirement_id"] == "REQ_A_CONFIG_IMPLEMENTATION")["source_semantic_role"]
finally:
    rsr._RESPONSIBILITY_HEADING_CUES = _orig_pattern

assert_true(
    role_before == role_after == "ROLE_RESPONSIBILITY",
    f"changing classifier code must NOT change a persisted fixture's consumed role: before={role_before}, after={role_after}",
)

atominvest_struct_after = json.loads((FIXTURE_A / "structured_extraction.json").read_text(encoding="utf-8"))
config_row_disk_after = next(r for r in atominvest_struct_after["requirements"] if r["requirement_id"] == "REQ_A_CONFIG_IMPLEMENTATION")
assert_true(config_row_disk_after["source_semantic_role_basis"] == persisted_basis, "persisted basis must remain unchanged on disk")
assert_true(config_row_disk_after["source_semantic_role_classifier_version"] == persisted_version, "persisted classifier version must remain unchanged on disk")
assert_true(config_row_disk_after["source_text"] == persisted_source_text, "raw source_text must remain unchanged")
assert_true(config_row_disk_after["source_location"] == persisted_source_location, "raw source_location must remain unchanged")
print("PASS J: persisted classification survives a classifier-code change; provenance and raw source text/location remain unchanged on disk.")


# ======================================================================
# K. Missing/null/invalid role safety -- for every caller, including one
# that bypasses normalize_structured_requirements()/schema validation.
# ======================================================================
for label, role_value, present in [
    ("MISSING (key absent)", None, False),
    ("NULL (key present, None)", None, True),
    ("INVALID enum (garbage string)", "NOT_A_REAL_ROLE", True),
]:
    req = _row("REQ_SAFETY_TEST", "some text", "some location")
    if present:
        req["source_semantic_role"] = role_value
    resolved = resolve_persisted_or_fallback(req)
    assert_true(resolved["source_semantic_role"] == "AMBIGUOUS", f"{label}: resolve_persisted_or_fallback must derive AMBIGUOUS, got {resolved}")
    gate = derive_qualification_gate(req.get("source_semantic_role"))
    assert_true(gate != "YES", f"{label}: qualification_gate must never be YES for a missing/invalid role, got {gate}")
    assert_true(gate == "AMBIGUOUS", f"{label}: qualification_gate must be AMBIGUOUS, got {gate}")
    merged = dict(req, **resolved)
    assert_true(derive_human_review_required(merged) is True, f"{label}: human review must be required")

    # Direct caller bypassing normalize_structured_requirements() entirely.
    match = {"requirement_id": "REQ_SAFETY_TEST", "result": "NONE"}
    blockers = detect_hard_blockers(
        requirements=[dict(req, importance="MANDATORY", relevance="HIGH")],
        matches=[match],
        seniority=None,
        role=None,
        jd_text="",
    )
    assert_true(
        not any("REQ_SAFETY_TEST" in b for b in blockers),
        f"{label}: must never independently hard-block even for a direct caller, got {blockers}",
    )
print("PASS K: missing/null/invalid role never independently hard-blocks, for direct callers too; qualification_gate is never a silent YES.")

# Schema validation: an invalid enum value must fail schema validation
# where validation is invoked.
schema_validator = build_draft202012_validator(REQUIREMENT_SCHEMA_PATH)
invalid_schema_row = dict(
    _row("REQ_SCHEMA_INVALID", "some text", "some location"),
    source_semantic_role="NOT_A_REAL_ROLE",
    source_semantic_role_basis="x",
    explicit_prerequisite_language_present=False,
    duplicated_under_requirements=False,
    source_semantic_role_classifier_version="v1",
)
schema_errors = [e.message for e in schema_validator.iter_errors(invalid_schema_row)]
assert_true(bool(schema_errors), "an invalid source_semantic_role enum value must fail requirement.schema.json validation")
print("PASS K2: an invalid source_semantic_role enum value fails schema validation where validation is invoked.")


# ======================================================================
# L. Responsibility evidence wording -- exact bounded phrasing, structured
# capability_inference_state, no unadjudicated claims.
# ======================================================================
result_a = analyze_job(_load_job_input(FIXTURE_A))
assert_true(result_a["valid"] is True, f"Atominvest analysis must be valid: {result_a['errors']}")
analysis_a = result_a["analysis"]
resp_by_id = {o["requirement_id"]: o for o in analysis_a["responsibility_observations"]}

for req_id in ("REQ_A_CONFIG_IMPLEMENTATION", "REQ_A_QA_TROUBLESHOOTING", "REQ_A_DOCUMENTATION"):
    obs = resp_by_id[req_id]
    assert_true(obs["result"] == "NONE", f"{req_id} must appear with result=NONE")
    assert_true(
        obs["capability_inference_state"] == "NO_CAPABILITIES_INFERRED",
        f"{req_id}: capability_inference_state must be NO_CAPABILITIES_INFERRED, got {obs['capability_inference_state']}",
    )
evidence_unknowns_text = " ".join(analysis_a["responsibility_evidence_unknowns"])
assert_true(
    "no established current approved match for this responsibility" in evidence_unknowns_text,
    f"exact bounded wording must be used, got {analysis_a['responsibility_evidence_unknowns']}",
)
assert_true(
    "no adjacent evidence" not in evidence_unknowns_text,
    "the old, overclaiming 'no adjacent evidence' phrasing must not appear",
)
for forbidden in ("qualification gap", "development need", "candidate lacks", "unsupported"):
    assert_true(
        forbidden not in evidence_unknowns_text.lower(),
        f"responsibility_evidence_unknowns must never use deficiency language ({forbidden!r})",
    )
assert_true(
    resp_by_id["REQ_A_ONBOARDING_MIGRATION_UAT"]["result"] == "PARTIAL"
    and resp_by_id["REQ_A_ONBOARDING_MIGRATION_UAT"]["claim_ids"] == ["CLAIM_WW_005"]
    and resp_by_id["REQ_A_ONBOARDING_MIGRATION_UAT"]["capability_inference_state"] == "APPROVED_MATCH_ESTABLISHED",
    f"REQ_A_ONBOARDING_MIGRATION_UAT must preserve its PARTIAL/cited-Claim/APPROVED_MATCH_ESTABLISHED state, got {resp_by_id['REQ_A_ONBOARDING_MIGRATION_UAT']}",
)
assert_true(
    not any("REQ_A_CONFIG_IMPLEMENTATION" in g for g in analysis_a["qualification_gaps"]),
    "a responsibility row must never appear in qualification_gaps",
)
print("PASS L: Atominvest CONFIG/QA/DOCUMENTATION use exact bounded wording and NO_CAPABILITIES_INFERRED state; UAT preserves PARTIAL/cited Claim; no responsibility emitted as a qualification gap.")


# ======================================================================
# M. Real-fixture regression -- Atominvest (control).
# ======================================================================
expected_blockers_a = {"REQ_A_DEGREE", "REQ_A_EXCEL_DATA"}
actual_blockers_a = {b.rsplit(": ", 1)[-1] for b in result_a["hard_blockers"]}
assert_true(actual_blockers_a == expected_blockers_a, f"Atominvest hard blockers must remain exactly {expected_blockers_a}, got {actual_blockers_a}")
assert_true(analysis_a["decision"] == "REJECT" and analysis_a["lane"] == "LANE_0_REJECT", "Atominvest decision must remain REJECT")
print("PASS M: Atominvest remains REJECT with REQ_A_DEGREE/REQ_A_EXCEL_DATA as the only hard blockers.")


# ======================================================================
# N. Real-fixture regression -- MIT LL (control, with legal-gate proof).
# ======================================================================
result_c = analyze_job(_load_job_input(FIXTURE_C))
assert_true(result_c["valid"] is True, f"MIT LL analysis must be valid: {result_c['errors']}")
analysis_c = result_c["analysis"]
blockers_c = {b.rsplit(": ", 1)[-1] for b in result_c["hard_blockers"]}
assert_true("REQ_C_REGRESSION_TESTING" not in blockers_c, f"MIT LL: REQ_C_REGRESSION_TESTING must not independently hard-block, got {blockers_c}")
required_intact = {"Citizenship or clearance requirement present in JD", "REQ_C_DEGREE_EXPERIENCE", "REQ_C_SAP_ERP", "REQ_C_SAP_FICO"}
assert_true(required_intact <= blockers_c, f"MIT LL: genuine citizenship/clearance, degree/experience and SAP blockers must remain intact, got {blockers_c}")
assert_true(analysis_c["decision"] == "REJECT" and analysis_c["lane"] == "LANE_0_REJECT", "MIT LL decision must remain REJECT")
gate_obs = {o["requirement_id"]: o for o in analysis_c["application_or_legal_gate_observations"]}
assert_true(
    gate_obs["REQ_C_CITIZENSHIP_CLEARANCE"]["consumer_covers_this_row"] is True
    and gate_obs["REQ_C_CITIZENSHIP_CLEARANCE"]["consumer_fired_for_this_job"] is True,
    f"MIT citizenship row must show proven consumer coverage in application_or_legal_gate_observations, got {gate_obs}",
)
print("PASS N: MIT LL remains REJECT with genuine citizenship/degree/SAP blockers intact; citizenship row's consumer coverage is proven in output.")


# ======================================================================
# O. Real-fixture regression -- BSA and MBTA D/E (controls).
# ======================================================================
result_bsa = analyze_job(_load_job_input(FIXTURE_BSA))
assert_true(result_bsa["valid"] is True, f"BSA analysis must be valid: {result_bsa['errors']}")
analysis_bsa = result_bsa["analysis"]
assert_true(analysis_bsa["decision"] == "WATCH" and analysis_bsa["lane"] == "WATCH", f"BSA must remain WATCH, got {analysis_bsa['decision']}/{analysis_bsa['lane']}")
match_bsa_010 = next(m for m in analysis_bsa["evidence_matches"] if m["requirement_id"] == "REQ_BSA_010")
assert_true(match_bsa_010["result"] == "STRONG" and match_bsa_010["claim_ids"] == ["CLAIM_WW_002"], f"BSA REQ_BSA_010 must remain STRONG via CLAIM_WW_002, got {match_bsa_010}")

result_d = analyze_job(_load_job_input(FIXTURE_D))
result_e = analyze_job(_load_job_input(FIXTURE_E))
assert_true(result_d["valid"] is True and result_e["valid"] is True, "MBTA D/E analyses must be valid")
blockers_d = {b.rsplit(": ", 1)[-1] for b in result_d["hard_blockers"]}
blockers_e = {b.rsplit(": ", 1)[-1] for b in result_e["hard_blockers"]}
# DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1 (post-dates this
# milestone): REQ_D/E_SYS_ANALYSIS_EXP no longer independently hard-block
# (resolve UNKNOWN, not NONE); only REQ_D/E_DEGREE remain.
assert_true(blockers_d == {"REQ_D_DEGREE"}, f"MBTA direct blockers must not regress, got {blockers_d}")
assert_true(blockers_e == {"REQ_E_DEGREE"}, f"MBTA contractor blockers must not regress, got {blockers_e}")
assert_true(
    result_d["analysis"]["decision"] == "REJECT" and result_e["analysis"]["decision"] == "REJECT",
    "MBTA D/E decisions must not regress from REJECT",
)
print("PASS O: BSA remains WATCH with its STRONG match intact; MBTA direct/contractor blockers and decisions unchanged.")


# ======================================================================
# P. Schema and migration validation.
# ======================================================================
for job_dir in (FIXTURE_A, FIXTURE_C, FIXTURE_D, FIXTURE_E, FIXTURE_BSA):
    struct = json.loads((job_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    for row in struct["requirements"]:
        for field in (
            "source_semantic_role",
            "source_semantic_role_basis",
            "explicit_prerequisite_language_present",
            "duplicated_under_requirements",
            "source_semantic_role_classifier_version",
        ):
            assert_true(field in row, f"{job_dir.name}/{row['requirement_id']}: migrated field {field!r} must be physically present on disk")
print("PASS P: all 5 fixture files' Requirement rows carry all 5 migrated classification/provenance fields on disk.")


# ======================================================================
# Q. Repository invariants unaffected -- inventory and Claim-approval safety.
# ======================================================================
claim_result = validate_claim_repository(None)
evidence_result = validate_evidence_repository(None)
experience_result = validate_experience_repository(None)
assert_true(len(experience_result["index"]) == 7, f"Experiences must remain 7, got {len(experience_result['index'])}")
assert_true(len(evidence_result["index"]) == 42, f"Evidence must remain 42, got {len(evidence_result['index'])}")
assert_true(len(claim_result["index"]) == 16, f"Claims must remain 16, got {len(claim_result['index'])}")
reusable_count = sum(1 for c in claim_result["index"].values() if c.get("human_approval") is True)
assert_true(reusable_count == 13, f"Reusable claims must remain 13, got {reusable_count}")
for claim_id in ("CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001", "CLAIM_BULMARMA_001"):
    assert_true(
        claim_result["index"][claim_id]["human_approval"] is False,
        f"{claim_id} must remain human_approval=False -- this milestone approves nothing",
    )
print("PASS Q: repository invariants (7/42/16/13 Experiences/Evidence/Claims/reusable) and the three intentionally-unapproved Claims are unaffected.")


# ======================================================================
# R. Consequential-analysis ingestion gate -- a canonical artifact entering
# ordinary analyze_job() production routing must STOP visibly (never
# silently synthesize a classification) when a Requirement carries a
# missing/null/invalid persisted source_semantic_role.
# ======================================================================
unmigrated_row = _row("REQ_UNMIGRATED", "Some genuine skill requirement.", "Requirements")
unmigrated_input = {
    "company": "TestCo",
    "role": "Analyst",
    "jd_text": "Some genuine skill requirement.",
    "structured_extraction": {"requirements": [unmigrated_row]},
    "fixture_key": "UNMIGRATED_TEST",
}
unmigrated_result = analyze_job(unmigrated_input)
assert_true(
    unmigrated_result["valid"] is False,
    f"an unmigrated canonical artifact must stop before consequential routing, got valid={unmigrated_result['valid']}",
)
assert_true(
    unmigrated_result["analysis"] is None,
    "an unmigrated artifact must produce no consequential decision at all",
)
error_codes = {e.get("code") for e in unmigrated_result["errors"]}
assert_true(
    "SOURCE_SEMANTIC_ROLE_NOT_MIGRATED" in error_codes,
    f"must fail with an explicit classification-required error, got {unmigrated_result['errors']}",
)
migrated_error = next(e for e in unmigrated_result["errors"] if e["code"] == "SOURCE_SEMANTIC_ROLE_NOT_MIGRATED")
assert_true(
    migrated_error["requirement_id"] == "REQ_UNMIGRATED" and "job_id" in migrated_error and migrated_error["missing_fields"],
    f"error must identify artifact/job, requirement_id, and missing fields, got {migrated_error}",
)
print("PASS R: an unmigrated canonical artifact stops visibly before consequential routing, with an explicit, identifying error.")


# ======================================================================
# S. Explicit classification/backfill creates a valid record that passes
# normal analysis (the intended, authorized ingestion pathway).
# ======================================================================
backfilled_row = dict(unmigrated_row)
classification_for_backfill = classify_source_semantic_roles([backfilled_row])[0]
for field in (
    "source_semantic_role",
    "source_semantic_role_basis",
    "explicit_prerequisite_language_present",
    "duplicated_under_requirements",
    "source_semantic_role_classifier_version",
):
    backfilled_row[field] = classification_for_backfill[field]
backfilled_input = dict(unmigrated_input, structured_extraction={"requirements": [backfilled_row]})
backfilled_result = analyze_job(backfilled_input)
assert_true(
    backfilled_result["valid"] is True,
    f"a properly backfilled record must pass ordinary analysis, got {backfilled_result['errors']}",
)
print("PASS S: explicit classification/backfill produces a valid record that passes normal analysis.")


# ======================================================================
# T. Narrow "gain(ing) exposure to" duty-language recognition.
# ======================================================================
gain_positive_cases = [
    "Gain exposure to real fund structures and investor relationships.",
    "Gaining exposure to complex client datasets from day one.",
]
for text in gain_positive_cases:
    row = _row("REQ_GAIN_POS", text, "Responsibilities")
    c = classify_source_semantic_roles([row])[0]
    assert_true(
        c["source_semantic_role"] == "ROLE_RESPONSIBILITY",
        f"gain-exposure positive {text!r} expected ROLE_RESPONSIBILITY under Responsibilities, got {c}",
    )
print("PASS T: 'gain(ing) exposure to' under a Responsibilities heading with no prerequisite language -> ROLE_RESPONSIBILITY.")

gain_negative_cases = [
    ("Must have gained five years of exposure to SAP.", "Responsibilities"),
    ("Requires prior exposure to private markets.", "Responsibilities"),
    ("Proven exposure to regulated reporting.", "Responsibilities"),
]
for text, location in gain_negative_cases:
    row = _row("REQ_GAIN_NEG", text, location)
    c = classify_source_semantic_roles([row])[0]
    assert_true(
        c["source_semantic_role"] != "ROLE_RESPONSIBILITY" or c["explicit_prerequisite_language_present"],
        f"adversarial negative {text!r} must not become ROLE_RESPONSIBILITY via the new gain-exposure rule alone, got {c}",
    )
    if text.startswith("Must have gained"):
        assert_true(
            c["source_semantic_role"] == "ENTRY_QUALIFICATION" and c["explicit_prerequisite_language_present"] is True,
            f"'Must have gained...' explicit prerequisite language must still control, got {c}",
        )
# The phrase under Requirements with conflicting entry language (no "will").
gain_under_requirements = _row("REQ_GAIN_REQ", "Gain exposure to real client data.", "Requirements")
c_req = classify_source_semantic_roles([gain_under_requirements])[0]
assert_true(
    c_req["source_semantic_role"] == "ENTRY_QUALIFICATION",
    f"'gain exposure to' under a Requirements heading (no future marker) is ordinary Requirements-section phrasing, expected ENTRY_QUALIFICATION, got {c_req}",
)
print("PASS T2: adversarial gain-exposure negatives never become ROLE_RESPONSIBILITY merely via the new rule; explicit prerequisite language still controls.")


# ======================================================================
# U. All 15 Job Analysis Golden cases, run directly (not merely via other
# test files) -- confirms the migrated golden corpus produces correct,
# unchanged routing.
# ======================================================================
GOLDEN_DIR = ROOT / "golden-tests" / "job_analysis"
GOLDEN_FIXTURE_IDS = sorted(p.name for p in GOLDEN_DIR.iterdir() if p.is_dir())
assert_true(len(GOLDEN_FIXTURE_IDS) == 15, f"expected 15 golden fixtures, found {len(GOLDEN_FIXTURE_IDS)}: {GOLDEN_FIXTURE_IDS}")


def _load_golden_job_input(fixture_id: str) -> dict:
    fixture_dir = GOLDEN_DIR / fixture_id
    extraction = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    return {
        "company": f"Synthetic Golden Co ({fixture_id})",
        "role": extraction.get("_role_title") or fixture_id,
        "jd_text": jd_text,
        "structured_extraction": extraction,
        "fixture_key": fixture_id,
        "role_status": "VERIFIED_LIVE",
    }


golden_pass_count = 0
for fixture_id in GOLDEN_FIXTURE_IDS:
    expected = json.loads((GOLDEN_DIR / fixture_id / "expected.json").read_text(encoding="utf-8"))
    result = analyze_job(_load_golden_job_input(fixture_id))
    assert_true(result["valid"] is True, f"{fixture_id}: analyze_job must succeed: {result.get('errors')}")
    decision = result["analysis"]["decision"]
    assert_true(
        decision in expected["acceptable_decisions"],
        f"{fixture_id}: decision {decision} not in acceptable_decisions {expected['acceptable_decisions']}",
    )
    assert_true(
        decision not in expected.get("forbidden_decisions", []),
        f"{fixture_id}: decision {decision} is forbidden ({expected.get('forbidden_decisions')})",
    )
    for needle in expected.get("expect_gap_substrings", []):
        assert_true(
            any(needle in g for g in result["analysis"]["gaps"]),
            f"{fixture_id}: expected gap substring {needle!r} not found in gaps {result['analysis']['gaps']}",
        )
    golden_pass_count += 1
assert_true(golden_pass_count == 15, f"all 15 golden cases must pass, only {golden_pass_count} did")
print("PASS U: all 15 Job Analysis Golden cases pass directly against the migrated golden corpus.")


print("ALL source_semantic_role_qualification_view_v1_test CHECKS PASSED")
