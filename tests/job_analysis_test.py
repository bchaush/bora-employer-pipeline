"""Job Analysis v1 vertical-slice tests (fixture + adversarial cases)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
FIXTURE_DIR = ROOT / "fixtures" / "jobs" / "JOB_FIXTURE_BSA_001"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from job_analysis import analyze_job  # noqa: E402
from requirement_normalize import classify_importance_from_source  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def load_bsa_fixture() -> dict:
    jd_text = (FIXTURE_DIR / "jd.txt").read_text(encoding="utf-8")
    extraction = json.loads(
        (FIXTURE_DIR / "structured_extraction.json").read_text(encoding="utf-8")
    )
    return {
        "company": "Northbridge Civic Ops (Synthetic Fixture)",
        "role": "Business Systems Analyst",
        "jd_text": jd_text,
        "fixture_key": "FIXTURE_BSA_001",
        "structured_extraction": extraction,
    }


# ---------------------------------------------------------------------------
# Repository regression gate
# ---------------------------------------------------------------------------
exp = validate_experience_repository()
ev = validate_evidence_repository()
cl = validate_claim_repository()
assert_true(exp["valid"] is True and exp["records_checked"] == 1, "Experience regression")
assert_true(ev["valid"] is True and ev["records_checked"] == 12, "Evidence regression")
assert_true(
    ev["experience_registry_status"] == "EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED",
    "Evidence Experience integrity",
)
assert_true(cl["valid"] is True and cl["records_checked"] == 5, "Claim regression")
for claim in cl["index"].values():
    assert_true(claim["human_approval"] is True, f"{claim['claim_id']} must stay approved")
print("PASS 0: Experience/Evidence/Claim repositories unchanged and valid.")

EVIDENCE_INDEX = ev["index"]
CLAIM_INDEX = cl["index"]


# ---------------------------------------------------------------------------
# 1. Strong Business Systems / Implementation fit
# ---------------------------------------------------------------------------
fixture = load_bsa_fixture()
result = analyze_job(
    fixture,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(result["valid"] is True, f"BSA analysis failed: {result['errors']}")
analysis = result["analysis"]
assert_true(analysis["job_id"] == "JOB_FIXTURE_BSA_001", analysis["job_id"])
assert_true(
    analysis["decision"] in {"PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"},
    f"unexpected decision {analysis['decision']} / {analysis['decision_rationale']}",
)
assert_true(analysis["lane"] != "LANE_0_REJECT", "BSA fixture should not reject")
print(
    f"PASS 1: strong BSA fit -> decision={analysis['decision']} lane={analysis['lane']}"
)

# Print extract for human review in Cursor report
print("EXTRACTED REQUIREMENTS:")
for req in analysis["requirements"]:
    print(
        f"  {req['requirement_id']} | {req['importance']} | {req['relevance']} | {req['text']}"
    )
print("MATCHES:")
for match in analysis["evidence_matches"]:
    print(
        f"  {match['requirement_id']} -> {match['result']} "
        f"claims={match['claim_ids']} evidence={match['evidence_ids']}"
    )
print("GAPS:", analysis["gaps"])
print("UNKNOWNS:", analysis["unknowns"])
print("RATIONALE:", analysis["decision_rationale"])


# ---------------------------------------------------------------------------
# 2. Preferred skill missing but core role still viable
# ---------------------------------------------------------------------------
salesforce = next(
    m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_BSA_005"
)
assert_true(salesforce["result"] == "NONE", "Salesforce must be NONE")
assert_true(
    analysis["decision"] in {"PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"},
    "preferred Salesforce missing should not auto-reject",
)
print("PASS 2: preferred Salesforce missing; core role still viable.")


# ---------------------------------------------------------------------------
# 3. Unsupported Salesforce/platform requirement (mandatory) -> reject path
# ---------------------------------------------------------------------------
sf_mandatory = copy.deepcopy(fixture)
for req in sf_mandatory["structured_extraction"]["requirements"]:
    if req["requirement_id"] == "REQ_BSA_005":
        req["importance"] = "MANDATORY"
        req["relevance"] = "HIGH"
        req["source_text"] = "Salesforce administration experience is required"
sf_result = analyze_job(
    sf_mandatory,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(sf_result["valid"] is True, sf_result["errors"])
assert_true(
    sf_result["analysis"]["decision"] == "REJECT",
    f"mandatory Salesforce should reject: {sf_result['analysis']['decision_rationale']}",
)
print("PASS 3: unsupported mandatory Salesforce/platform -> REJECT.")


# ---------------------------------------------------------------------------
# 4. Senior-role reject
# ---------------------------------------------------------------------------
senior = copy.deepcopy(fixture)
senior["role"] = "Senior Business Systems Architect"
senior["structured_extraction"]["seniority"] = "SENIOR"
senior["jd_text"] = fixture["jd_text"] + "\nRequires 7+ years leading enterprise programs.\n"
senior["structured_extraction"]["requirements"].append(
    {
        "requirement_id": "REQ_SENIOR_001",
        "job_id": "PLACEHOLDER",
        "text": "7+ years leading enterprise systems programs",
        "category": "SENIORITY",
        "importance": "MANDATORY",
        "seniority_implication": "SENIOR",
        "technology": [],
        "experience_level": "7+ years",
        "domain": None,
        "relevance": "HIGH",
        "source_text": "Requires 7+ years leading enterprise programs",
        "source_location": "Minimum qualifications (required)",
    }
)
senior_result = analyze_job(
    senior,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(senior_result["valid"] is True, senior_result["errors"])
assert_true(
    senior_result["analysis"]["decision"] == "REJECT",
    senior_result["analysis"]["decision_rationale"],
)
print("PASS 4: senior-role reject.")


# ---------------------------------------------------------------------------
# 5. U.S.-regulatory semantic-transfer trap -> PARTIAL (not STRONG/NONE if transfer)
# ---------------------------------------------------------------------------
us_reg = next(
    m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_BSA_006"
)
assert_true(us_reg["result"] == "PARTIAL", f"expected PARTIAL, got {us_reg}")
assert_true(us_reg.get("transfer_note") is not None, "PARTIAL must expose transfer_note")
assert_false(us_reg["result"] == "STRONG", "must not upgrade to STRONG")
print("PASS 5: U.S.-regulatory semantic-transfer trap -> PARTIAL.")


# ---------------------------------------------------------------------------
# 6. UAT != enterprise QA trap
# ---------------------------------------------------------------------------
uat = next(m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_BSA_004")
qa = next(m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_BSA_008")
assert_true(
    uat["result"] in {"STRONG", "SUPPORTED", "PARTIAL"},
    f"UAT should match positively: {uat}",
)
assert_true(qa["result"] == "NONE", f"enterprise QA ownership must be NONE: {qa}")
print("PASS 6: UAT != enterprise QA trap.")


# ---------------------------------------------------------------------------
# 7. Apps Script != Google Cloud trap
# ---------------------------------------------------------------------------
gcloud = next(
    m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_BSA_007"
)
assert_true(gcloud["result"] == "NONE", f"Google Cloud must be NONE: {gcloud}")
print("PASS 7: Apps Script != Google Cloud trap.")


# ---------------------------------------------------------------------------
# 8. production ML unsupported
# ---------------------------------------------------------------------------
ml = copy.deepcopy(fixture)
ml["structured_extraction"]["requirements"] = [
    {
        "requirement_id": "REQ_ML_001",
        "job_id": "PLACEHOLDER",
        "text": "Build production ML systems and machine learning pipelines",
        "category": "ML",
        "importance": "MANDATORY",
        "seniority_implication": None,
        "technology": ["Python", "TensorFlow"],
        "experience_level": None,
        "domain": "Machine Learning",
        "relevance": "HIGH",
        "source_text": "Must build production ML systems",
        "source_location": "Minimum qualifications (required)",
    }
]
ml["structured_extraction"]["role_family"] = "Machine Learning Engineering"
ml["structured_extraction"]["seniority"] = "MID"
ml_result = analyze_job(ml, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_true(ml_result["valid"] is True, ml_result["errors"])
ml_match = ml_result["analysis"]["evidence_matches"][0]
assert_true(ml_match["result"] == "NONE", ml_match)
assert_true(ml_result["analysis"]["decision"] == "REJECT", ml_result["analysis"])
print("PASS 8: production ML unsupported -> NONE + REJECT.")


# ---------------------------------------------------------------------------
# 9. unclear requirement remains UNCLEAR
# ---------------------------------------------------------------------------
assert_true(
    classify_importance_from_source(
        "Team player who thrives in a fast-paced environment"
    )
    == "UNCLEAR",
    "marketing language must stay UNCLEAR",
)
# Preferred cue
assert_true(
    classify_importance_from_source("Salesforce experience is preferred") == "PREFERRED",
    "preferred cue",
)
# Mandatory cue
assert_true(
    classify_importance_from_source("SQL skills are required") == "MANDATORY",
    "mandatory cue",
)
print("PASS 9: unclear requirement remains UNCLEAR; classification cues work.")


# ---------------------------------------------------------------------------
# 10. missing Evidence does not become a match
# ---------------------------------------------------------------------------
orphan_claim_index = {
    "CLAIM_ORPHAN_001": {
        "claim_id": "CLAIM_ORPHAN_001",
        "wording": "Expert Salesforce and Google Cloud architect.",
        "evidence_ids": ["EVID_DOES_NOT_EXIST"],
        "evidence_state": "VERIFIED",
        "allowed_contexts": ["resume"],
        "forbidden_contexts": ["production ML"],
        "human_approval": True,
        "date": "2026-08-27",
        "version": "1",
    }
}
orphan_job = copy.deepcopy(fixture)
orphan_job["structured_extraction"]["requirements"] = [
    {
        "requirement_id": "REQ_ORPHAN_001",
        "job_id": "PLACEHOLDER",
        "text": "Salesforce administration experience",
        "category": "PLATFORM",
        "importance": "MANDATORY",
        "seniority_implication": None,
        "technology": ["Salesforce"],
        "experience_level": None,
        "domain": None,
        "relevance": "HIGH",
        "source_text": "Salesforce administration experience is required",
        "source_location": "Minimum qualifications (required)",
    }
]
orphan_result = analyze_job(
    orphan_job,
    claim_index=orphan_claim_index,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(orphan_result["valid"] is True, orphan_result["errors"])
assert_true(
    orphan_result["analysis"]["evidence_matches"][0]["result"] == "NONE",
    "orphan/non-reusable claim must not create positive Salesforce match",
)
assert_true(
    orphan_result["analysis"]["evidence_matches"][0]["claim_ids"] == [],
    "no provenance from non-reusable claim",
)
print("PASS 10: missing Evidence / non-reusable claim does not become a match.")


# ---------------------------------------------------------------------------
# 11. invalid structured extraction fails schema validation
# ---------------------------------------------------------------------------
bad = copy.deepcopy(fixture)
bad["structured_extraction"]["requirements"][0]["importance"] = "OPTIONAL"
bad_result = analyze_job(bad, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_false(bad_result["valid"], "invalid importance must fail")
assert_true(
    any(err.get("code") == "REQUIREMENT_SCHEMA_INVALID" for err in bad_result["errors"]),
    bad_result["errors"],
)
print("PASS 11: invalid structured extraction fails schema validation.")


# ---------------------------------------------------------------------------
# 12. duplicate Requirement_ID handling
# ---------------------------------------------------------------------------
dup = copy.deepcopy(fixture)
dup["structured_extraction"]["requirements"].append(
    copy.deepcopy(dup["structured_extraction"]["requirements"][0])
)
dup_result = analyze_job(dup, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_false(dup_result["valid"], "duplicate requirement_id must fail")
assert_true(
    any(err.get("code") == "DUPLICATE_REQUIREMENT_ID" for err in dup_result["errors"]),
    dup_result["errors"],
)
print("PASS 12: duplicate Requirement_ID handling.")


# ---------------------------------------------------------------------------
# EXTRACTION_REQUIRED when structured extraction missing
# ---------------------------------------------------------------------------
missing_ext = {
    "company": "Synthetic Co",
    "role": "Analyst",
    "jd_text": "A job description without structured extraction.",
    "fixture_key": "NO_EXTRACTION",
}
missing_result = analyze_job(
    missing_ext,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_false(missing_result["valid"], "missing extraction must fail closed")
assert_true(
    any(err.get("code") == "EXTRACTION_REQUIRED" for err in missing_result["errors"]),
    missing_result["errors"],
)
print("PASS 13: missing structured extraction -> EXTRACTION_REQUIRED.")


# ---------------------------------------------------------------------------
# Analysis result schema smoke
# ---------------------------------------------------------------------------
analysis_validator = build_draft202012_validator(
    ROOT / "schemas" / "job_analysis_result.schema.json"
)
assert_true(
    not list(analysis_validator.iter_errors(analysis)),
    "BSA analysis must satisfy job_analysis_result schema",
)
match_validator = build_draft202012_validator(
    ROOT / "schemas" / "evidence_match.schema.json"
)
for match in analysis["evidence_matches"]:
    errs = list(match_validator.iter_errors(match))
    assert_true(not errs, f"match schema errors for {match}: {errs}")
print("PASS 14: analysis + evidence_match schemas accept real outputs.")

print("PASS: job analysis vertical-slice tests completed successfully.")
