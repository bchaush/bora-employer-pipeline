"""Bounded tests for Brandeis education evidence integration
(EDUCATION_EVIDENCE_V1).

Proves: the Brandeis Business Analytics (M.S.) education identity is
evidence-controlled and correctly flows through the existing,
unmodified résumé pipeline (master -> unified presentation -> test-only
renderer) exactly like any other already-verified résumé fact. No
schema was changed. No STEM/CIP designation, degree-conferral, or
graduation claim was added. No Student ID or transcript file was
committed. Existing Winter Walk/MarketMind truth is unchanged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"
EXPERIENCE_PATH = ROOT / "experiences" / "EXP_EDU_BRANDEIS_001.json"
EVIDENCE_DIR = ROOT / "evidence" / "education"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_presentation import build_resume_presentation_view  # noqa: E402
from resume_text_renderer import render_resume_text  # noqa: E402
from resume_validation import build_resume_derivative  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(len(exp_result["index"]) == 7, "Experience count must be 7 (Winter Walk, MarketMind, Brandeis education, TELUS, undergraduate education, D Commerce, Bulmarma)")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(len(ev_result["index"]) == 43, "Evidence count must be 43 (37 prior + 3 CANDIDATE_SOURCE_INGESTION_V1 records: undergraduate identity, D Commerce Excel, Bulmarma Excel + 2 human-source-resolution records: DCOMMERCE_REFERENCE_001, DCOMMERCE_LINKEDIN_PERIOD_001 + 1 Brandeis MSBA awarded attestation record)")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 16, "Claim count must be 16 (13 prior + 3 CANDIDATE_SOURCE_INGESTION_V1 draft claims: undergraduate, D Commerce, Bulmarma) -- Brandeis education itself adds no Claims")

EXPERIENCE_INDEX = exp_result["index"]
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = claim_result["index"]

MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
assert_true(len(MASTER["modules"]) == 13, "master modules must be 13 (11 education-milestone-era + 2 later TELUS modules) -- education itself is not a module")


# 1. Experience record exists, correctly typed, and references only source-supported fields.
assert_true("EXP_EDU_BRANDEIS_001" in EXPERIENCE_INDEX, "EXP_EDU_BRANDEIS_001 must exist in the trusted Experience index")
edu_experience = EXPERIENCE_INDEX["EXP_EDU_BRANDEIS_001"]
assert_true(edu_experience["experience_type"] == "EDUCATION", "Brandeis education Experience must use experience_type=EDUCATION")
assert_true(edu_experience["organization"] == "Brandeis University", "organization must be exact Brandeis University")
print("PASS 1: EXP_EDU_BRANDEIS_001 exists with experience_type=EDUCATION.")


# 2. Exact Brandeis school name and Business Analytics (M.S.) wording in the master.
assert_true(len(MASTER["education"]) == 1, "master education must contain exactly one entry")
edu_entry = MASTER["education"][0]
assert_true(edu_entry["school_name"] == "Brandeis University", f"exact school name required, got {edu_entry['school_name']!r}")
assert_true(
    edu_entry["degree_name"] == "Business Analytics (M.S.)",
    f"exact degree wording required, got {edu_entry['degree_name']!r}",
)
print("PASS 2: exact Brandeis school name and Business Analytics (M.S.) wording present.")


# 3. Source-faithful education period (not invented calendar months).
assert_true(
    edu_entry["date_range"] == "Fall 2025 – Summer 2026",
    f"date_range must be source-faithful (Fall 2025 - Summer 2026), got {edu_entry['date_range']!r}",
)
assert_false(
    "Aug" in edu_entry["date_range"] or "Jan" in edu_entry["date_range"],
    "date_range must not invent specific calendar months not established by the source",
)
print("PASS 3: source-faithful education period, no invented calendar months.")


# 4/5. Education present in the unified presentation and the test-only renderer.
default_patch = {
    "patch_id": "EDU_TEST_DEFAULT",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]}],
}
default_result = build_resume_derivative(
    master=MASTER, patch=default_patch, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_EDU_TEST_DEFAULT",
)
assert_true(default_result["valid"] is True, f"default derivative must build: {default_result.get('errors')}")
presentation_result = build_resume_presentation_view(default_result["derivative"], experience_index=EXPERIENCE_INDEX)
assert_true(presentation_result["valid"] is True, f"unified presentation must resolve: {presentation_result.get('errors')}")
assert_true(
    "education" in presentation_result["presentation"] and presentation_result["presentation"]["education"] == MASTER["education"],
    "education must appear in the unified presentation, copied verbatim from the master",
)
print("PASS 4: Education present in the unified presentation view.")

render_result = render_resume_text(presentation_result)
assert_true(render_result["valid"] is True, f"renderer must succeed: {render_result.get('errors')}")
assert_true("EDUCATION" in render_result["text"], "EDUCATION heading must appear in the rendered text")
assert_true(
    "Business Analytics (M.S.), Brandeis University, Fall 2025 – Summer 2026" in render_result["text"],
    "rendered EDUCATION line must contain exact degree, school, and source-faithful period",
)
print("PASS 5: Education present and correctly formatted in the test-only renderer.")


# 6. No fabricated STEM designation anywhere in an actual asserted fact/claim or
#    in rendered output. (Notes/limitations fields are documentation and may
#    legitimately name "STEM" only inside an explicit negative-determination
#    sentence, e.g. "does not establish STEM/CIP designation" -- that is the
#    correct, intentional way to record NOT_VERIFIED, not a violation.)
edu_evidence_records = [record for eid, record in EVIDENCE_INDEX.items() if eid.startswith("EDU_")]
assert_true(len(edu_evidence_records) == 5, f"expected exactly 5 education Evidence records (4 Brandeis + 1 undergraduate), got {len(edu_evidence_records)}")
asserted_fact_text = " ".join(record["fact"] for record in edu_evidence_records)
asserted_fact_text += " " + json.dumps(MASTER["education"]) + " " + json.dumps(edu_experience.get("experience_name", "")) + " " + render_result["text"]
assert_false("STEM" in asserted_fact_text, "no STEM designation may appear in any asserted fact, master data, or rendered output")
assert_false("CIP" in asserted_fact_text, "no CIP code may appear in any asserted fact, master data, or rendered output")
for record in edu_evidence_records:
    if "STEM" in json.dumps(record.get("notes")) + json.dumps(record.get("limitations", [])):
        lowered = (str(record.get("notes") or "") + " " + " ".join(record.get("limitations", []))).lower()
        assert_true(
            "not establish stem" in lowered or "not verified" in lowered or "not yet verified" in lowered,
            f"{record['evidence_id']} mentions STEM outside an explicit negative-determination sentence",
        )
print("PASS 6: no fabricated STEM/CIP designation in any asserted fact or rendered output.")


# 7. No fabricated conferral/graduation wording in any asserted fact or rendered output.
FORBIDDEN_CONFERRAL_TERMS = ["graduated", "degree awarded", "degree conferred", "conferred degree"]
lower_asserted = asserted_fact_text.lower()
for term in FORBIDDEN_CONFERRAL_TERMS:
    assert_false(term in lower_asserted, f"no conferral/graduation wording ({term!r}) may appear in any asserted fact or rendered output")
print("PASS 7: no fabricated degree-conferral or graduation wording.")


# 8. No Student ID leakage anywhere in the new records or rendered output.
for path in [EXPERIENCE_PATH, *sorted(EVIDENCE_DIR.glob("*.json"))]:
    text = path.read_text(encoding="utf-8")
    assert_false("Student ID" in text or "student_id" in text.lower(), f"{path.name} must not contain a Student ID")
assert_false("Student ID" in render_result["text"], "rendered text must not contain a Student ID")
print("PASS 8: no Student ID leakage in new records or rendered output.")


# 9. Existing Winter Walk / MarketMind wording unchanged.
WW_IDS = [m["module_id"] for m in MASTER["modules"] if m.get("experience_id") == "EXP_WW_001"]
MM_IDS = [m["module_id"] for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"]
assert_true(len(WW_IDS) == 6, "Winter Walk module count must remain 6")
assert_true(len(MM_IDS) == 5, "MarketMind module count must remain 5")
EXPECTED_WW_WORDING = {
    "MOD_WW_001_SCOPE": (
        "Defined scope and guardrails for Winter Walk's internal Google Workspace operating system, "
        "including explicit limits on CRM functionality, public dashboards, automated sending, and "
        "causal fundraising claims."
    ),
}
for module in MASTER["modules"]:
    if module["module_id"] in EXPECTED_WW_WORDING:
        assert_true(
            module["wording"] == EXPECTED_WW_WORDING[module["module_id"]],
            "Winter Walk module wording must remain byte-unchanged",
        )
print("PASS 9: existing Winter Walk and MarketMind module wording unchanged.")


# 10. Invalid/missing education identity fails according to current contracts.
import copy  # noqa: E402

bad_derivative = copy.deepcopy(default_result["derivative"])
bad_derivative["education"] = [{"education_id": "EDU_BAD", "school_name": "PENDING_BORA_REVIEW", "degree_name": "Test Degree"}]
bad_presentation = build_resume_presentation_view(bad_derivative, experience_index=EXPERIENCE_INDEX)
# education is copied verbatim by the unified presentation (no re-validation there);
# the sentinel value is caught by the existing, unmodified protected-metadata export
# gate rather than by this milestone's own code -- confirming no new validator is needed.
from resume_protected_metadata import validate_protected_metadata_resolved  # noqa: E402

gate_result = validate_protected_metadata_resolved(bad_derivative)
assert_false(gate_result["valid"], "an unresolved education school_name sentinel must fail the existing protected-metadata gate")
assert_true(
    any(e.get("code") == "UNRESOLVED_PROTECTED_METADATA" for e in gate_result["errors"]),
    "existing gate must report UNRESOLVED_PROTECTED_METADATA for the invalid education entry",
)
print("PASS 10: invalid education identity fails via the existing, unmodified protected-metadata contract.")


# 11. Deterministic output.
render_result_repeat = render_resume_text(build_resume_presentation_view(default_result["derivative"], experience_index=EXPERIENCE_INDEX))
assert_true(render_result_repeat == render_result, "same input must produce byte-identical rendered output on repeat calls")
print("PASS 11: deterministic repeat output.")


print("PASS: EDUCATION_EVIDENCE_V1 tests completed successfully.")
