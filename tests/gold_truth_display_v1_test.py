"""Regression for Bora's approved Gold truth and display choices.

Records and checks, without changing any underlying fact:
- CLAIM_EDU_UNWE_001, CLAIM_DCOMMERCE_001 and the new evidence-backed CLAIM_DCOMMERCE_002 are human-approved while their
  evidence states and source evidence are unchanged;
- the GPA truth stays 3.635 in evidence while the candidate-facing display is 3.64 (presentation rounding only);
- TELUS Digital Bulgaria stays the organization truth while the approved employer display is TELUS Digital;
- the approved links are bound to canonical evidence, not hard-coded into the generic Gold builder;
- the production identity provider cross-checks every overlay entry and fails closed when a binding breaks.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

import pursue_to_gold_package as ptg  # noqa: E402
from claim_lineage import validate_claim_lineage  # noqa: E402
from claim_repository import load_validated_claim_repository  # noqa: E402
from evidence_repository import load_validated_evidence_repository  # noqa: E402
from experience_repository import load_validated_experience_repository  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        sys.stdout.flush()
        raise SystemExit(1)


CLAIMS = load_validated_claim_repository(ROOT / "claims")
EVIDENCE = load_validated_evidence_repository(ROOT / "evidence")
EXPERIENCES = load_validated_experience_repository(ROOT / "experiences")
OVERLAY_PATH = ROOT / "docs" / "resume" / "BORA_GOLD_APPROVED_DISPLAY_V1.json"
OVERLAY = json.loads(OVERLAY_PATH.read_text(encoding="utf-8"))
MASTER = json.loads((ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json").read_text(encoding="utf-8"))
assert_true(CLAIMS["valid"] and EVIDENCE["valid"] and EXPERIENCES.valid, "canonical repositories validate")


def identity(**changes):
    overlay = copy.deepcopy(OVERLAY)
    for path, value in changes.items():
        node = overlay
        keys = path.split("__")
        for key in keys[:-1]:
            node = node[int(key)] if key.isdigit() else node[key]
        last = keys[-1]
        node[int(last) if last.isdigit() else last] = value
    return ptg.approved_identity_from_canonical_records(ROOT, overlay=overlay, claims=CLAIMS["index"], experiences=EXPERIENCES.index, evidence=EVIDENCE["index"])


def refused(**changes) -> str:
    try:
        identity(**changes)
    except ptg.PackageError as error:
        return error.code
    return "ACCEPTED"


# 1. Claim approvals recorded through the existing claim mechanism, provenance retained.
claims = CLAIMS["index"]
for claim_id in ("CLAIM_EDU_UNWE_001", "CLAIM_DCOMMERCE_001", "CLAIM_DCOMMERCE_002"):
    assert_true(claims[claim_id]["human_approval"] is True, f"{claim_id} is human-approved")
    assert_true(validate_claim_lineage(claims[claim_id], EVIDENCE["index"])["valid"], f"{claim_id} lineage stays valid")
assert_true(claims["CLAIM_EDU_UNWE_001"]["evidence_state"] == "OBSERVED" and claims["CLAIM_EDU_UNWE_001"]["evidence_ids"] == ["EDU_UNWE_IDENTITY_001"],
            "UNWE keeps its OBSERVED state and original evidence")
assert_true(claims["CLAIM_DCOMMERCE_001"]["evidence_state"] == "OBSERVED" and claims["CLAIM_DCOMMERCE_001"]["evidence_ids"] == ["DCOMMERCE_EXCEL_001"],
            "D Commerce 001 keeps its OBSERVED state and original evidence")
second = claims["CLAIM_DCOMMERCE_002"]
assert_true(second["evidence_ids"] == ["DCOMMERCE_REFERENCE_001"] and second["evidence_state"] == "VERIFIED", "the new claim is bound to the verified employer reference only")
reference_fact = EVIDENCE["index"]["DCOMMERCE_REFERENCE_001"]["fact"]
for phrase in ("daily, weekly, and monthly reports", "Bulgarian National Bank requirements"):
    assert_true(phrase in reference_fact and phrase in second["wording"], f"the new claim wording is the evidence-faithful phrase {phrase!r}")
for forbidden in ("Excel", "1,000"):
    assert_true(forbidden not in second["wording"], "the new claim asserts nothing the reference letter does not establish")
print("PASS 1: UNWE and D Commerce claims are approved with provenance intact and the second D Commerce claim is evidence-backed only.")

# 2. Truth and display stay separate.
gpa_evidence = EVIDENCE["index"]["EDU_BRANDEIS_GPA_001"]
assert_true("3.635" in json.dumps(gpa_evidence) and "3.64" not in json.dumps(gpa_evidence), "the GPA truth stays 3.635 in evidence (never rewritten to 3.64)")
assert_true(EXPERIENCES.index["EXP_TELUS_001"]["organization"] == "TELUS Digital Bulgaria", "TELUS organization truth is unchanged")
resolved = identity()
assert_true(resolved["education"][0]["degree_line"] == "Master of Science in Business Analytics | GPA: 3.64", "candidate-facing GPA display is 3.64")
assert_true(resolved["experiences"]["EXP_TELUS_001"]["employer"] == "TELUS Digital"
            and resolved["experiences"]["EXP_TELUS_001"]["title"] == "Digital Trust and Safety Analyst with English", "approved TELUS display alias and title")
assert_true(resolved["experiences"]["EXP_DCOMMERCE_001"]["title"] == "Junior Expert" and resolved["experiences"]["EXP_DCOMMERCE_001"]["employer"] == "D Commerce Bank"
            and resolved["experiences"]["EXP_DCOMMERCE_001"]["date_range"] == "Aug 2021 - Sep 2022", "approved D Commerce presentation with the evidenced date range")
assert_true([entry["school"] for entry in resolved["education"]] == ["Brandeis University", "University of National and World Economy"], "two-school education from approved records")
print("PASS 2: truth and display stay separate (GPA 3.635 vs 3.64, TELUS Digital Bulgaria vs TELUS Digital).")

# 3. Links come from the approved record bound to canonical evidence, and the generic builder holds no Bora values.
assert_true([(link["label"], link["url"]) for link in resolved["contact"]["profile_links"]] ==
            [("LinkedIn", "https://www.linkedin.com/in/bora-chaush-msba"), ("GitHub", "https://github.com/bchaush")], "approved profile links")
assert_true(resolved["contact"]["email"] == "bchaush@brandeis.edu" and resolved["project_links"]["EXP_MM_001"] ==
            {"label": "GitHub", "url": "https://github.com/bchaush/marketmind-ai"}, "approved email and MarketMind repository link")
for name in ("gold_resume_docx_builder.py", "gold_resume_qa.py"):
    source = (ROOT / "src" / name).read_text(encoding="utf-8").lower()
    for value in ("bchaush", "brandeis", "telus digital", "github.com/", "3.64", "3.635", "bora-chaush"):
        assert_true(value not in source, f"{name} holds no Bora-specific value: {value}")
print("PASS 3: approved links are canonical records bound to evidence and the generic Gold builder and QA hold no Bora-specific constants.")

# 4. The provider cross-checks bindings and fails closed.
assert_true(refused(education_display__0__gpa__display_value="3.65") == "APPROVED_DISPLAY_BINDING_FAILED", "a wrong GPA display is refused")
assert_true(refused(education_display__0__gpa__truth_value="3.700") == "APPROVED_DISPLAY_BINDING_FAILED", "a GPA truth value not held by evidence is refused")
assert_true(refused(experience_display__1__organization_truth="TELUS Digital") == "APPROVED_DISPLAY_BINDING_FAILED", "an organization truth that differs from the registry is refused")
assert_true(refused(experience_display__1__title="Trust and Safety Analyst") == "APPROVED_DISPLAY_BINDING_FAILED", "a title that differs from the master approval is refused")
assert_true(refused(experience_display__2__title="Senior Expert") == "APPROVED_DISPLAY_BINDING_FAILED", "a title that is not the employer formal position is refused")
assert_true(refused(project_display__0__link={"label": "GitHub", "url": "https://github.com/someone/other", "bound_evidence_id": "MM_AUTHOR_001"})
            == "APPROVED_DISPLAY_BINDING_FAILED", "a repository URL not held by the bound evidence is refused")
assert_true(refused(contact_links__0__url="https://www.linkedin.com/in/someone-else") == "APPROVED_DISPLAY_BINDING_FAILED", "a LinkedIn URL that differs from the master text is refused")
assert_true(refused(approval={"approved": False, "approved_by": "Bora", "approved_on": "2026-10-03", "approval_note": "x"}) == "APPROVED_DISPLAY_INVALID", "an unapproved overlay is refused")
assert_true(refused(extra_field=1) == "APPROVED_DISPLAY_INVALID", "an unknown overlay field is refused")
unapproved = copy.deepcopy(claims)
unapproved["CLAIM_EDU_UNWE_001"]["human_approval"] = False
omitted = ptg.approved_identity_from_canonical_records(ROOT, claims=unapproved, experiences=EXPERIENCES.index, evidence=EVIDENCE["index"])
assert_true([entry["school"] for entry in omitted["education"]] == ["Brandeis University"], "an education entry whose claim is not approved is omitted, so a model using it fails Gold QA")
schema = build_draft202012_validator(ROOT / "schemas" / "gold_approved_display.schema.json", check_schema=True)
assert_true(not list(schema.iter_errors(OVERLAY)), "the overlay validates against its schema")
assert_true(MASTER["version"] == "8", "the protected master is unchanged by this canonicalization")
print("PASS 4: the identity provider cross-checks every overlay binding and fails closed or omits when one breaks.")
print("PASS: gold_truth_display_v1_test")
