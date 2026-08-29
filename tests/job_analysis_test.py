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
assert_true(exp["valid"] is True and exp["records_checked"] == 4, "Experience regression")
assert_true(ev["valid"] is True and ev["records_checked"] == 37, "Evidence regression")
assert_true(
    ev["experience_registry_status"] == "EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED",
    "Evidence Experience integrity",
)
assert_true(cl["valid"] is True and cl["records_checked"] == 13, "Claim regression")
reusable_approved = [
    cid for cid, rec in cl["index"].items() if rec.get("human_approval") is True
]
assert_true(len(reusable_approved) == 13, f"expected 13 reusable claims, got {reusable_approved}")
for claim_id, claim in cl["index"].items():
    if claim_id.startswith("CLAIM_WW_") or claim_id.startswith("CLAIM_MM_"):
        assert_true(claim["human_approval"] is True, f"{claim['claim_id']} must be approved")
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
# 5. U.S.-regulatory false PARTIAL removed -> NONE with current repository
# ---------------------------------------------------------------------------
us_reg = next(
    m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_BSA_006"
)
assert_true(us_reg["result"] == "NONE", f"expected NONE, got {us_reg}")
assert_true(us_reg["claim_ids"] == [], "regulatory NONE must have no claim provenance")
assert_true(us_reg["evidence_ids"] == [], "regulatory NONE must have no evidence provenance")
print("PASS 5: U.S.-regulatory requirement -> NONE (no Winter Walk false PARTIAL).")


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
# P-1 / R-1 clause-aware preferred-not-required
p1_cases = [
    ("3 years preferred but not required", "PREFERRED"),
    ("Experience preferred, although not required", "PREFERRED"),
    ("Preferred but not mandatory", "PREFERRED"),
    ("Certification preferred; not required", "PREFERRED"),
    (
        "SQL preferred but not required; Python required",
        "UNCLEAR",
    ),
    (
        "Bachelor's required; Master's preferred but not required",
        "UNCLEAR",
    ),
    (
        "Salesforce preferred but not required for candidates with equivalent CRM experience",
        "PREFERRED",
    ),
    (
        "Bachelor's degree required; Master's degree preferred.",
        "UNCLEAR",
    ),
]
for text, expected in p1_cases:
    got = classify_importance_from_source(text)
    assert_true(
        got == expected,
        f"P-1/R-1 classify {text!r} -> {got!r}, expected {expected!r}",
    )
# Mandatory cue
assert_true(
    classify_importance_from_source("SQL skills are required") == "MANDATORY",
    "mandatory cue",
)
print("PASS 9: unclear + P-1/R-1 clause-aware classification variants.")


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


# ---------------------------------------------------------------------------
# Remediation adversarial coverage
# ---------------------------------------------------------------------------

# R1/R2: generic control/audit wording cannot authorize regulatory expertise
from requirement_match import match_requirement, load_reusable_claims  # noqa: E402

reusable = load_reusable_claims(CLAIM_INDEX, EVIDENCE_INDEX)
reg_req = {
    "requirement_id": "REQ_REG_GENERIC",
    "job_id": "JOB_X",
    "text": "U.S. regulatory reporting and SOX controls experience",
    "category": "DOMAIN",
    "importance": "PREFERRED",
    "seniority_implication": None,
    "technology": [],
    "experience_level": None,
    "domain": "U.S. Regulatory Reporting",
    "relevance": "MEDIUM",
    "source_text": "Familiarity with U.S. regulatory reporting packages (SEC / SOX-style controls)",
    "source_location": "Preferred",
}
reg_match = match_requirement(
    job_id="JOB_X",
    requirement=reg_req,
    reusable_claims=reusable,
    evidence_index=EVIDENCE_INDEX,
    match_index=0,
)
assert_true(reg_match["result"] == "NONE", reg_match)
print("PASS R1: generic control/audit Winter Walk evidence cannot support regulatory expertise.")

# R3: Product Management with stakeholder/process vocabulary cannot APPLY
pm = {
    "company": "Synthetic PM Co",
    "role": "Product Manager",
    "jd_text": "Product Manager role. Work with stakeholders and own product process.",
    "fixture_key": "PM_OVERMATCH",
    "structured_extraction": {
        "role_family": "Product Management",
        "seniority": "MID",
        "requirements": [
            {
                "requirement_id": "REQ_PM_001",
                "job_id": "PLACEHOLDER",
                "text": "Partner with stakeholders to drive product process and requirements",
                "category": "PM",
                "importance": "MANDATORY",
                "seniority_implication": None,
                "technology": [],
                "experience_level": None,
                "domain": "Product",
                "relevance": "HIGH",
                "source_text": "Must partner with stakeholders to drive product process and requirements",
                "source_location": "Requirements",
            }
        ],
    },
}
pm_result = analyze_job(pm, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_true(pm_result["valid"] is True, pm_result["errors"])
assert_true(
    pm_result["analysis"]["decision"] not in {
        "PRIORITY_APPLY",
        "APPLY",
        "EFFICIENT_APPLY",
    },
    pm_result["analysis"],
)
assert_true(
    pm_result["analysis"]["evidence_matches"][0]["result"] in {"NONE", "UNKNOWN"},
    pm_result["analysis"]["evidence_matches"][0],
)
print(
    f"PASS R3: Product Management cannot APPLY "
    f"(decision={pm_result['analysis']['decision']})."
)

# R4: generic lexical overlap alone cannot produce PARTIAL
generic_req = {
    "requirement_id": "REQ_GENERIC_WORDS",
    "job_id": "JOB_X",
    "text": "Strong stakeholder process workflow requirements validation data audit control experience",
    "category": "GENERIC",
    "importance": "MANDATORY",
    "seniority_implication": None,
    "technology": [],
    "experience_level": None,
    "domain": None,
    "relevance": "HIGH",
    "source_text": "Strong stakeholder process workflow requirements validation data audit control experience required",
    "source_location": "Requirements",
}
generic_match = match_requirement(
    job_id="JOB_X",
    requirement=generic_req,
    reusable_claims=reusable,
    evidence_index=EVIDENCE_INDEX,
    match_index=1,
)
assert_true(
    generic_match["result"] in {"NONE", "UNKNOWN"},
    f"generic words must not PARTIAL/STRONG: {generic_match}",
)
print("PASS R4: generic lexical overlap alone cannot produce PARTIAL.")

# R5: one central mandatory HIGH NONE blocks positive apply despite minor positives
core_none = copy.deepcopy(fixture)
core_none["structured_extraction"]["requirements"].append(
    {
        "requirement_id": "REQ_PEOPLE_MGMT",
        "job_id": "PLACEHOLDER",
        "text": "Direct people-management experience leading a team of analysts",
        "category": "LEADERSHIP",
        "importance": "MANDATORY",
        "seniority_implication": None,
        "technology": [],
        "experience_level": None,
        "domain": None,
        "relevance": "HIGH",
        "source_text": "Direct people-management experience leading a team of analysts is required",
        "source_location": "Minimum qualifications (required)",
    }
)
core_result = analyze_job(
    core_none,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(core_result["valid"] is True, core_result["errors"])
people = next(
    m
    for m in core_result["analysis"]["evidence_matches"]
    if m["requirement_id"] == "REQ_PEOPLE_MGMT"
)
assert_true(people["result"] == "NONE", people)
assert_true(
    core_result["analysis"]["decision"] not in {
        "PRIORITY_APPLY",
        "APPLY",
        "EFFICIENT_APPLY",
    },
    core_result["analysis"],
)
print(
    f"PASS R5: central mandatory HIGH NONE blocks apply "
    f"(decision={core_result['analysis']['decision']})."
)

# R6: senior title in raw JD/title blocks even if extracted seniority is EARLY_CAREER
mislabeled = copy.deepcopy(fixture)
mislabeled["role"] = "Senior Business Systems Analyst"
mislabeled["structured_extraction"]["seniority"] = "EARLY_CAREER"
mislabeled["jd_text"] = (
    "Senior Business Systems Analyst\n\n" + fixture["jd_text"]
)
mis_result = analyze_job(
    mislabeled,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(mis_result["valid"] is True, mis_result["errors"])
assert_true(
    mis_result["analysis"]["decision"] == "REJECT",
    mis_result["analysis"]["decision_rationale"],
)
print("PASS R6: senior title defense-in-depth blocks mislabeled EARLY_CAREER extraction.")

# R7: Bachelor's required; Master's preferred -> UNCLEAR (not PREFERRED)
assert_true(
    classify_importance_from_source(
        "Bachelor's degree required; Master's degree preferred."
    )
    == "UNCLEAR",
    "mixed degree clauses must not become PREFERRED overall",
)
print("PASS R7: mixed degree clauses classify as UNCLEAR.")

# R8: HR noise with must -> UNCLEAR
assert_true(
    classify_importance_from_source(
        "Must be a self-starter and team player who thrives in a fast-paced environment."
    )
    == "UNCLEAR",
    "HR noise with must must stay UNCLEAR",
)
print("PASS R8: HR noise prefixed with must stays UNCLEAR.")

# R9: ideal candidate cue -> PREFERRED
assert_true(
    classify_importance_from_source(
        "Ideal candidate has Salesforce administration experience"
    )
    == "PREFERRED",
    "ideal candidate cue",
)
print("PASS R9: ideal candidate cue handled as PREFERRED.")

# R10: positive match without provenance fails schema validation
match_validator = build_draft202012_validator(
    ROOT / "schemas" / "evidence_match.schema.json"
)
bad_match = {
    "match_id": "MATCH_BAD",
    "job_id": "JOB_X",
    "requirement_id": "REQ_X",
    "result": "SUPPORTED",
    "evidence_ids": [],
    "claim_ids": [],
    "explanation": "should fail provenance",
    "transfer_note": None,
}
assert_true(
    list(match_validator.iter_errors(bad_match)),
    "positive match without provenance must fail schema",
)
print("PASS R10: positive match without provenance fails schema validation.")

# R11: top-level result schema rejects malformed nested requirement
analysis_validator = build_draft202012_validator(
    ROOT / "schemas" / "job_analysis_result.schema.json"
)
bad_analysis_req = copy.deepcopy(analysis)
bad_analysis_req["requirements"] = [
    {
        "requirement_id": "REQ_BAD",
        "job_id": analysis["job_id"],
        "text": "x",
        "category": "X",
        "importance": "OPTIONAL",
        "seniority_implication": None,
        "technology": [],
        "experience_level": None,
        "domain": None,
        "relevance": "HIGH",
        "source_text": "x",
        "source_location": "x",
    }
]
assert_true(
    list(analysis_validator.iter_errors(bad_analysis_req)),
    "malformed nested requirement must fail top-level schema",
)
print("PASS R11: top-level schema rejects malformed nested requirement.")

# R12: top-level result schema rejects malformed nested evidence match
bad_analysis_match = copy.deepcopy(analysis)
bad_analysis_match["evidence_matches"] = [
    {
        "match_id": "MATCH_BAD2",
        "job_id": analysis["job_id"],
        "requirement_id": "REQ_BSA_001",
        "result": "STRONG",
        "evidence_ids": [],
        "claim_ids": [],
        "explanation": "no provenance",
        "transfer_note": None,
    }
]
assert_true(
    list(analysis_validator.iter_errors(bad_analysis_match)),
    "malformed nested evidence match must fail top-level schema",
)
print("PASS R12: top-level schema rejects malformed nested evidence match.")


# ---------------------------------------------------------------------------
# Golden-set remediation adversarial coverage (R-2..R-7)
# ---------------------------------------------------------------------------
from requirement_match import infer_requirement_capabilities  # noqa: E402

def _mini_req(text, **kwargs):
    payload = {
        "requirement_id": "REQ_TMP",
        "job_id": "JOB_X",
        "text": text,
        "category": kwargs.get("category", "CORE"),
        "importance": kwargs.get("importance", "MANDATORY"),
        "seniority_implication": None,
        "technology": kwargs.get("technology", []),
        "experience_level": None,
        "domain": kwargs.get("domain"),
        "relevance": kwargs.get("relevance", "HIGH"),
        "source_text": kwargs.get("source_text", text),
        "source_location": "test",
    }
    return payload


# Synonym recall (2+ variants) with provenance
synonym_cases = [
    ("Gather business requirements from stakeholders", "requirements_elicitation"),
    ("Collect requirements and clarify scope", "requirements_elicitation"),
    ("Import CSV datasets with validation logging", "data_ingestion"),
    ("Ingest spreadsheet data feeds for recurring packages", "data_ingestion"),
    ("Facilitate user acceptance testing and document outcomes", "uat"),
    ("Run acceptance testing / pilot validation sessions", "uat"),
    ("Support fail-closed outbound send controls", "fail_closed_controls"),
    ("Maintain kill-switch controlled live email send gates", "fail_closed_controls"),
]
for text, needed in synonym_cases:
    caps = infer_requirement_capabilities(_mini_req(text))
    assert_true(
        needed in caps,
        f"synonym {text!r} missing capability {needed}: {caps}",
    )
    m = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(text),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true(
        m["result"] in {"STRONG", "SUPPORTED"},
        f"synonym {text!r} should positively match: {m}",
    )
    assert_true(
        m["claim_ids"] or m["evidence_ids"],
        f"synonym {text!r} missing provenance: {m}",
    )
print("PASS R13: supported capability synonym recall with provenance.")

# Generic non-matches
assert_true(
    "requirements_elicitation"
    not in infer_requirement_capabilities(
        _mini_req("Strong stakeholder management and process ownership")
    ),
    "generic stakeholder management must not map to requirements elicitation",
)
assert_true(
    not infer_requirement_capabilities(_mini_req("Broad data experience across teams"))
    & {"data_ingestion", "csv_intake", "import_logging"},
    "generic data experience must not map to ingestion",
)
print("PASS R14: generic stakeholder/data wording does not overmatch.")

# Marketing workflow automation must not be STRONG workflow_automation
mkt = match_requirement(
    job_id="JOB_X",
    requirement=_mini_req(
        "Manage marketing workflow automation for nurture campaigns",
        category="MARKETING",
    ),
    reusable_claims=reusable,
    evidence_index=EVIDENCE_INDEX,
    match_index=0,
)
assert_true(mkt["result"] == "NONE", f"marketing workflow automation: {mkt}")
assert_true(
    "workflow_automation"
    not in infer_requirement_capabilities(
        _mini_req("Manage marketing workflow automation for nurture campaigns")
    ),
    "bare marketing workflow automation must not infer workflow_automation",
)
print("PASS R15: marketing workflow automation does not gain STRONG.")

# Process mapping positive with provenance (CLAIM_WW_006 reapproved)
pmap = match_requirement(
    job_id="JOB_X",
    requirement=_mini_req(
        "Map existing business processes and produce process maps",
        category="PROCESS",
        domain="Business Process",
    ),
    reusable_claims=reusable,
    evidence_index=EVIDENCE_INDEX,
    match_index=0,
)
assert_true(pmap["result"] in {"STRONG", "SUPPORTED"}, f"P2 process mapping: {pmap}")
assert_true(
    pmap.get("claim_ids") == ["CLAIM_WW_006"],
    f"P2 process mapping provenance: {pmap}",
)
print("PASS R16: process mapping matches with reapproved CLAIM_WW_006 provenance.")

# Trap variants still NONE
for trap_text in [
    "Hands-on SOX / SEC regulatory reporting packages",
    "Enterprise QA engineering ownership",
    "Google Cloud infrastructure engineering",
    "Production MLOps model deployment",
    "Workday administration specialization",
    "Cybersecurity controls and SOC 2 ownership",
    "BPMN 2.0 modeling expertise",
    "Formal enterprise process modeling certification",
    "Enterprise process architecture leadership",
    "Lean process engineering certification",
    "Value stream mapping expertise",
    "Six Sigma Black Belt certification",
    "Celonis process mining platform",
    "UiPath Process Mining telemetry",
]:
    tm = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(trap_text),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true(tm["result"] == "NONE", f"trap {trap_text!r} -> {tm}")
print("PASS R17: unsupported trap variants remain NONE.")

# Routing calibration probes
assert_true(analysis["decision"] == "PRIORITY_APPLY", analysis["decision"])
print("PASS R18: exceptional BSA fixture routes PRIORITY_APPLY.")

# Vague insufficient-information -> WATCH
vague = {
    "company": "Vague Co",
    "role": "Operations Analyst",
    "jd_text": "We are passionate. Thrive in ambiguity.",
    "fixture_key": "UNIT_VAGUE",
    "structured_extraction": {
        "role_family": "Business Operations",
        "seniority": "EARLY_CAREER",
        "requirements": [
            {
                "requirement_id": "REQ_UV1",
                "job_id": "PLACEHOLDER",
                "text": "Self-starter who thrives in a fast-paced environment",
                "category": "HR_NOISE",
                "importance": "UNCLEAR",
                "seniority_implication": None,
                "technology": [],
                "experience_level": None,
                "domain": None,
                "relevance": "LOW",
                "source_text": "Must be a self-starter who thrives in a fast-paced environment",
                "source_location": "About you",
            },
            {
                "requirement_id": "REQ_UV2",
                "job_id": "PLACEHOLDER",
                "text": "Excited about process and impact",
                "category": "CULTURE",
                "importance": "UNCLEAR",
                "seniority_implication": None,
                "technology": [],
                "experience_level": None,
                "domain": None,
                "relevance": "LOW",
                "source_text": "Excited about process and impact",
                "source_location": "About you",
            },
            {
                "requirement_id": "REQ_UV3",
                "job_id": "PLACEHOLDER",
                "text": "Comfortable with vague priorities",
                "category": "AMBIGUOUS",
                "importance": "UNCLEAR",
                "seniority_implication": None,
                "technology": [],
                "experience_level": None,
                "domain": None,
                "relevance": "MEDIUM",
                "source_text": "Comfortable with vague priorities",
                "source_location": "About you",
            },
        ],
    },
}
vague_result = analyze_job(vague, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_true(vague_result["valid"] is True, vague_result["errors"])
assert_true(
    vague_result["analysis"]["decision"] == "WATCH",
    vague_result["analysis"],
)
print("PASS R19: vague insufficient-information role -> WATCH.")

# Confirmed mismatch still REJECT (already covered by PM / Salesforce); assert divergence
assert_true(
    pm_result["analysis"]["decision"] == "REJECT",
    "well-specified unrelated PM must REJECT",
)
print("PASS R20: confirmed mismatch REJECT diverges from vague WATCH.")

# Golden schema rejects catch-all decision lists
golden_validator = build_draft202012_validator(
    ROOT / "schemas" / "job_analysis_golden_case.schema.json"
)
catch_all = {
    "fixture_id": "GT_CATCH_ALL",
    "purpose": "bad",
    "role_family": "Business Systems",
    "acceptable_decisions": [
        "PRIORITY_APPLY",
        "APPLY",
        "EFFICIENT_APPLY",
        "WATCH",
        "REJECT",
        "UNDECIDED",
    ],
    "key_matches": {"REQ_X": {"result": "NONE"}},
    "semantic_boundaries": ["x"],
    "known_limitations": ["NONE"],
}
assert_true(
    list(golden_validator.iter_errors(catch_all)),
    "catch-all acceptable_decisions must fail schema",
)
empty_keys = {
    "fixture_id": "GT_EMPTY_KEYS",
    "purpose": "bad",
    "role_family": "Business Systems",
    "acceptable_decisions": ["APPLY"],
    "key_matches": {},
    "semantic_boundaries": ["x"],
    "known_limitations": ["NONE"],
}
assert_true(
    list(golden_validator.iter_errors(empty_keys)),
    "empty key_matches must fail schema",
)
print("PASS R21: golden schema rejects meaningless catch-all / empty key_matches.")


# ---------------------------------------------------------------------------
# Second Claude re-audit remediation (T-1 / T-2 / T-3)
# ---------------------------------------------------------------------------

# T-1: four near-duplicate HIGH requirements supported by one claim ≠ PRIORITY
dup_job = {
    "company": "Duplicate Split Co",
    "role": "Business Systems Analyst",
    "jd_text": "Business Systems Analyst role with duplicated requirements wording.",
    "fixture_key": "UNIT_PRIORITY_SPLIT",
    "structured_extraction": {
        "role_family": "Business Systems",
        "seniority": "EARLY_CAREER",
        "requirements": [
            {
                "requirement_id": f"REQ_DUP_{i:02d}",
                "job_id": "PLACEHOLDER",
                "text": text,
                "category": "REQUIREMENTS",
                "importance": "MANDATORY",
                "seniority_implication": None,
                "technology": [],
                "experience_level": None,
                "domain": "Business Systems",
                "relevance": "HIGH",
                "source_text": text,
                "source_location": "Required",
            }
            for i, text in enumerate(
                [
                    "Gather business requirements from stakeholders",
                    "Collect requirements and clarify scope boundaries",
                    "Document requirements after stakeholder workshops",
                    "Elicit stakeholder requirements for internal tools",
                ],
                start=1,
            )
        ],
    },
}
dup_result = analyze_job(dup_job, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_true(dup_result["valid"] is True, dup_result["errors"])
assert_true(
    dup_result["analysis"]["decision"] != "PRIORITY_APPLY",
    f"duplicate single-claim splits must not PRIORITY: {dup_result['analysis']}",
)
dup_claims = {
    cid
    for m in dup_result["analysis"]["evidence_matches"]
    for cid in (m.get("claim_ids") or [])
}
assert_true(
    dup_claims <= {"CLAIM_WW_001"},
    f"expected only CLAIM_WW_001 provenance, got {dup_claims}",
)
print(
    f"PASS T1a: requirement-splitting gaming blocked "
    f"(decision={dup_result['analysis']['decision']})."
)

# T-1b: genuine diverse HIGH support can still PRIORITY (BSA fixture)
assert_true(analysis["decision"] == "PRIORITY_APPLY", analysis["decision"])
diverse_claims = {
    cid
    for m in analysis["evidence_matches"]
    if m["result"] in {"STRONG", "SUPPORTED"}
    for cid in (m.get("claim_ids") or [])
}
assert_true(
    len(diverse_claims) >= 4,
    f"BSA PRIORITY should rest on distinct claims, got {diverse_claims}",
)
print(
    f"PASS T1b: genuine diverse PRIORITY retained "
    f"(distinct_claims={sorted(diverse_claims)})."
)

# T-2: new synonym positives
new_synonyms = [
    "Gather business needs from internal teams",
    "Translate stakeholder needs into documented requirements",
    "Load recurring spreadsheet feeds from partner systems",
    "Import operational files from partner teams",
    "Ingest tabular source data for reporting",
    "Consolidate incoming datasets from multiple sources",
    "Support acceptance-test cycles for new releases",
]
for text in new_synonyms:
    m = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(text),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true(
        m["result"] in {"STRONG", "SUPPORTED"},
        f"T-2 synonym should match positively: {text!r} -> {m}",
    )
    assert_true(m["claim_ids"] or m["evidence_ids"], f"missing provenance: {m}")
print("PASS T2a: expanded synonym recall with provenance.")

# T-2 negatives / precision guards
for text in [
    "Strong stakeholder management and cross-functional collaboration",
    "Work with data across teams",
    "Analyze data for insights",
    "Manage information and approvals",
    "Enterprise QA strategy ownership",
    "Software quality engineering leadership",
    "Automated regression architecture ownership",
    "Marketing campaign workflow ownership",
    "Cybersecurity controls administration",
    "Cloud administration for production clusters",
    "MLOps model deployment ownership",
]:
    caps = infer_requirement_capabilities(_mini_req(text))
    # May map to explicit NONE traps, but must not invent positive WW capabilities
    # except trap tags.
    positive_ww = caps & {
        "requirements_elicitation",
        "scope_boundary",
        "data_ingestion",
        "csv_intake",
        "import_logging",
        "uat",
        "pilot_testing",
        "test_documentation",
        "fail_closed_controls",
        "workflow_automation",
        "form_to_evidence_mapping",
        "approval_sync",
    }
    assert_true(
        not positive_ww,
        f"overreach positive caps for {text!r}: {positive_ww}",
    )
    m = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(text),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true(
        m["result"] in {"NONE", "UNKNOWN"},
        f"precision guard failed for {text!r}: {m}",
    )
print("PASS T2b: generic/overreach negatives remain non-positive.")

# T-3: Application Analyst family recognition with strong duties
app_core = [
    (
        "REQ_APP_REQ",
        "Gather business requirements from operations stakeholders",
    ),
    (
        "REQ_APP_DATA",
        "Import CSV datasets with import logging",
    ),
    (
        "REQ_APP_UAT",
        "Document user acceptance testing outcomes",
    ),
    (
        "REQ_APP_CTRL",
        "Support fail-closed outbound send controls",
    ),
    (
        "REQ_APP_WF",
        "Configure operational workflow automation with approval controls",
    ),
]
for family, title in [
    ("Application Analyst", "Application Analyst"),
    ("Application Support", "Application Support Analyst"),
    ("Business Systems", "Business Systems Analyst"),
    ("Implementation", "Implementation Analyst"),
]:
    app_job = {
        "company": f"Family Co {family}",
        "role": title,
        "jd_text": f"{title} supporting internal applications.",
        "fixture_key": f"UNIT_FAMILY_{family.replace(' ', '_').upper()}",
        "structured_extraction": {
            "role_family": family,
            "seniority": "EARLY_CAREER",
            "requirements": [
                {
                    "requirement_id": rid,
                    "job_id": "PLACEHOLDER",
                    "text": text,
                    "category": "CORE",
                    "importance": "MANDATORY",
                    "seniority_implication": None,
                    "technology": ["CSV"] if "CSV" in text else [],
                    "experience_level": None,
                    "domain": family,
                    "relevance": "HIGH",
                    "source_text": text,
                    "source_location": "Required",
                }
                for rid, text in app_core
            ],
        },
    }
    app_result = analyze_job(
        app_job, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
    )
    assert_true(app_result["valid"] is True, app_result["errors"])
    assert_true(
        app_result["analysis"]["decision"]
        in {"PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"},
        f"{family}/{title} disadvantaged: {app_result['analysis']}",
    )
print("PASS T3: Application Analyst / Support families viable with strong duties.")


# ---------------------------------------------------------------------------
# Final Claude re-audit residual findings (N-1 / N-2)
# ---------------------------------------------------------------------------
n1_pos = [
    "Turn user needs into functional requirements",
    "Capture stakeholder needs for a new workflow",
    "Clarify requested workflow changes with users",
    "Ingest structured source files",
    "Load tabular data from partner exports",
    "Validate a pilot with business users",
]
for text in n1_pos:
    m = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(text),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true(
        m["result"] in {"STRONG", "SUPPORTED"},
        f"N-1 positive failed for {text!r}: {m}",
    )
    assert_true(m["claim_ids"] or m["evidence_ids"], f"N-1 missing provenance: {m}")
print("PASS N1a: residual synonym positives with provenance.")

n1_neg = [
    "understand user needs",
    "review files",
    "manage data",
    "validation",
    "work with spreadsheets",
    "analyze datasets",
    "Enterprise QA strategy ownership",
    "Automated regression framework ownership",
    "Software quality engineering",
    "test automation architecture ownership",
]
for text in n1_neg:
    caps = infer_requirement_capabilities(_mini_req(text))
    positive_ww = caps & {
        "requirements_elicitation",
        "scope_boundary",
        "data_ingestion",
        "csv_intake",
        "import_logging",
        "uat",
        "pilot_testing",
        "test_documentation",
        "fail_closed_controls",
        "workflow_automation",
        "form_to_evidence_mapping",
        "approval_sync",
    }
    assert_true(not positive_ww, f"N-1 overreach for {text!r}: {positive_ww}")
    m = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(text),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true(
        m["result"] in {"NONE", "UNKNOWN"},
        f"N-1 precision guard failed for {text!r}: {m}",
    )
print("PASS N1b: residual precision guards remain non-positive.")

# N-2: Business Applications Analyst positive; SWE application titles reject
ba_job = {
    "company": "Apps Analyst Co",
    "role": "Business Applications Analyst",
    "jd_text": "Business Applications Analyst supporting internal apps.",
    "fixture_key": "UNIT_BUSINESS_APPLICATIONS_ANALYST",
    "structured_extraction": {
        "role_family": "Business Applications Analyst",
        "seniority": "EARLY_CAREER",
        "requirements": [
            {
                "requirement_id": rid,
                "job_id": "PLACEHOLDER",
                "text": text,
                "category": "CORE",
                "importance": "MANDATORY",
                "seniority_implication": None,
                "technology": ["CSV"] if "CSV" in text else [],
                "experience_level": None,
                "domain": "Application Analyst",
                "relevance": "HIGH",
                "source_text": text,
                "source_location": "Required",
            }
            for rid, text in app_core
        ],
    },
}
ba_result = analyze_job(ba_job, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
assert_true(ba_result["valid"] is True, ba_result["errors"])
assert_true(
    ba_result["analysis"]["decision"]
    in {"PRIORITY_APPLY", "APPLY", "EFFICIENT_APPLY"},
    ba_result["analysis"],
)
print(
    f"PASS N2a: Business Applications Analyst positive "
    f"(decision={ba_result['analysis']['decision']})."
)

for title, family in [
    ("Application Developer", "Software Engineering"),
    ("Mobile Application Engineer", "Software Engineering"),
    ("Software Application Engineer", "Software Engineering"),
]:
    swe_app = {
        "company": f"SWE App Co {title}",
        "role": title,
        "jd_text": f"{title} building production software services.",
        "fixture_key": f"UNIT_SWE_APP_{title.replace(' ', '_').upper()}",
        "structured_extraction": {
            "role_family": family,
            "seniority": "MID",
            "requirements": [
                {
                    "requirement_id": "REQ_SWE_APP_CORE",
                    "job_id": "PLACEHOLDER",
                    "text": "Build and maintain backend services as a software engineer",
                    "category": "SWE",
                    "importance": "MANDATORY",
                    "seniority_implication": None,
                    "technology": [],
                    "experience_level": None,
                    "domain": "Software Engineering",
                    "relevance": "HIGH",
                    "source_text": (
                        "Build and maintain backend services as a software engineer "
                        "is required"
                    ),
                    "source_location": "Required",
                },
                {
                    "requirement_id": "REQ_SWE_APP_TEST",
                    "job_id": "PLACEHOLDER",
                    "text": "Write automated tests for production services",
                    "category": "TESTING",
                    "importance": "MANDATORY",
                    "seniority_implication": None,
                    "technology": [],
                    "experience_level": None,
                    "domain": "Software Engineering",
                    "relevance": "HIGH",
                    "source_text": "Write automated tests for production services is required",
                    "source_location": "Required",
                },
            ],
        },
    }
    swe_result = analyze_job(
        swe_app, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
    )
    assert_true(swe_result["valid"] is True, swe_result["errors"])
    assert_true(
        swe_result["analysis"]["decision"] == "REJECT",
        f"{title} must REJECT: {swe_result['analysis']}",
    )
print("PASS N2b: Application Developer / Mobile / Software Application Engineer REJECT.")


# ---------------------------------------------------------------------------
# P-2 process_mapping evidence model (WW_PROC_001 / CLAIM_WW_006)
# ---------------------------------------------------------------------------
from claim_validation import validate_claim  # noqa: E402

EVIDENCE_SCHEMA = build_draft202012_validator(ROOT / "schemas" / "evidence.schema.json")
CLAIM_SCHEMA = build_draft202012_validator(ROOT / "schemas" / "claim.schema.json")

ww_proc = json.loads(
    (ROOT / "evidence" / "winter_walk" / "WW_PROC_001.json").read_text(encoding="utf-8")
)
ww_claim = json.loads(
    (ROOT / "claims" / "winter_walk" / "CLAIM_WW_006.json").read_text(encoding="utf-8")
)
assert_true(EVIDENCE_SCHEMA.is_valid(ww_proc), "WW_PROC_001 schema invalid")
assert_true(ww_proc["experience_id"] == "EXP_WW_001", "WW_PROC_001 Experience ref")
assert_true(ww_proc["capabilities"] == ["process_mapping"], ww_proc["capabilities"])
assert_true(
    "Section 1 Executive Summary" in ww_proc["source_location"],
    ww_proc["source_location"],
)
assert_true("WW_PROC_001" in EVIDENCE_INDEX, "WW_PROC_001 in trusted Evidence index")
assert_true(CLAIM_SCHEMA.is_valid(ww_claim), "CLAIM_WW_006 schema invalid")
assert_true(
    ww_claim["wording"]
    == "Documented Winter Walk's manual OP-support workflow and translated it into a structured operating process covering evidence tracking, review, follow-up, and human approval.",
    ww_claim["wording"],
)
assert_true("data intake" not in ww_claim["wording"].casefold(), ww_claim["wording"])
assert_true(ww_claim["evidence_ids"] == ["WW_PROC_001"], ww_claim["evidence_ids"])
assert_true(ww_claim["human_approval"] is True, "CLAIM_WW_006 must be reapproved")
claim_val = validate_claim(ww_claim, EVIDENCE_INDEX)
assert_true(claim_val["valid_record"] is True, claim_val)
assert_true(claim_val["reusable"] is True, claim_val)
assert_true(claim_val["human_approved"] is True, claim_val)
print("PASS P2a: corrected CLAIM_WW_006 reapproved reusable.")

for text in [
    "Map current-state workflows",
    "Document business processes for operations review",
    "Map operational handoffs between teams",
    "Document current-state and future-state workflow",
]:
    m = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(text, category="PROCESS", domain="Business Process"),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true(
        m["result"] in {"STRONG", "SUPPORTED"},
        f"P2 positive failed for {text!r}: {m}",
    )
    assert_true(m.get("claim_ids") == ["CLAIM_WW_006"], m)
print("PASS P2b: bounded process_mapping positives with provenance.")

p2_neg = [
    "process improvement",
    "operations",
    "workflow management",
    "project management",
    "stakeholder management",
    "documentation",
]
for text in p2_neg:
    caps = infer_requirement_capabilities(_mini_req(text))
    m = match_requirement(
        job_id="JOB_X",
        requirement=_mini_req(text),
        reusable_claims=reusable,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )
    assert_true("process_mapping" not in caps, f"generic {text!r} inferred {caps}")
    assert_true(m["result"] == "NONE", f"generic {text!r} -> {m}")
print("PASS P2c: generic process/workflow words remain non-positive.")

p2_fixture = {
    "company": "Process Studio",
    "role": "Business Process Analyst",
    "jd_text": (ROOT / "golden-tests/job_analysis/GT_PROCESS_MAP_P2/jd.txt").read_text(
        encoding="utf-8"
    ),
    "fixture_key": "GT_PROCESS_MAP_P2",
    "structured_extraction": json.loads(
        (
            ROOT / "golden-tests/job_analysis/GT_PROCESS_MAP_P2/structured_extraction.json"
        ).read_text(encoding="utf-8")
    ),
}
p2_result = analyze_job(
    p2_fixture, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
)
assert_true(p2_result["valid"] is True, p2_result["errors"])
assert_true(
    p2_result["analysis"]["decision"] == "APPLY",
    f"GT_PROCESS_MAP_P2 routing: {p2_result['analysis']}",
)
map_match = next(
    m
    for m in p2_result["analysis"]["evidence_matches"]
    if m["requirement_id"] == "REQ_P2_MAP"
)
assert_true(
    map_match["result"] in {"STRONG", "SUPPORTED"},
    f"REQ_P2_MAP match: {map_match}",
)
assert_true("CLAIM_WW_006" in map_match.get("claim_ids", []), map_match)
print("PASS P2d: GT_PROCESS_MAP_P2 routes APPLY with REQ_P2_MAP provenance.")

print("PASS: job analysis vertical-slice tests completed successfully.")
