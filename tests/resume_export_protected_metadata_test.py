"""Adversarial regression tests for export-gate protected-metadata blocking (M-1)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
FIXTURES = ROOT / "fixtures" / "resume_architecture"
WW_MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_digest import compute_derivative_validation_digest  # noqa: E402
from resume_protected_metadata import (  # noqa: E402
    UNRESOLVED_PROTECTED_METADATA_SENTINEL,
    validate_protected_metadata_resolved,
)
from resume_validation import (  # noqa: E402
    approve_derivative_for_export,
    build_resume_derivative,
    complete_semantic_review,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def has_code(items: list, code: str) -> bool:
    return any(item.get("code") == code for item in items)


def unresolved_fields(errors: list) -> list[str]:
    return [
        error.get("field")
        for error in errors
        if error.get("code") == "UNRESOLVED_PROTECTED_METADATA"
    ]


def load_trusted_indexes() -> tuple[dict, dict]:
    experience_result = validate_experience_repository()
    assert_true(experience_result["valid"] is True, "experience repository invalid")
    evidence_result = validate_evidence_repository(
        experience_result=experience_result,
    )
    assert_true(evidence_result["valid"] is True, "evidence repository invalid")
    claim_result = validate_claim_repository()
    assert_true(claim_result["valid"] is True, "claim repository invalid")
    return evidence_result["index"], claim_result["index"]


EVIDENCE_INDEX, CLAIM_INDEX = load_trusted_indexes()
SYNTHETIC_MASTER = json.loads((FIXTURES / "synthetic_master.json").read_text(encoding="utf-8"))
WW_MASTER = json.loads(WW_MASTER_PATH.read_text(encoding="utf-8"))

identity_patch = {
    "patch_id": "PATCH_EXPORT_META_NOOP",
    "target_master_id": WW_MASTER["master_id"],
    "operations": [
        {"op": "REORDER_MODULES", "module_ids": WW_MASTER["default_module_order"]},
    ],
}
ww_derivative_result = build_resume_derivative(
    master=WW_MASTER,
    patch=identity_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_WW_EXPORT_META_001",
)
assert_true(ww_derivative_result["valid"] is True, "WW derivative should build")
WW_DERIVATIVE = ww_derivative_result["derivative"]
assert_true(
    WW_DERIVATIVE["experience_sections"][0]["formal_title"]
    == UNRESOLVED_PROTECTED_METADATA_SENTINEL,
    "WW fixture must keep unresolved formal_title",
)


# A. Real Winter Walk derivative with resolved contact + approved display title -> metadata PASS
ww_metadata = validate_protected_metadata_resolved(WW_DERIVATIVE)
assert_true(ww_metadata["valid"] is True, "A: WW derivative protected metadata must pass")
assert_false(
    "contact.name" in unresolved_fields(ww_metadata["errors"]),
    "A: contact.name must not block protected metadata",
)
assert_false(
    "experience_sections[0].formal_title" in unresolved_fields(ww_metadata["errors"]),
    "A: approved display title must satisfy title export readiness",
)
ww_approval = approve_derivative_for_export(
    derivative=WW_DERIVATIVE,
    master=WW_MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_true(ww_approval["valid"] is True, "A: WW derivative export-approval eligible with resolved contact")
print("PASS A: WW derivative protected metadata passes with resolved contact.")


assert_true(
    WW_DERIVATIVE["contact"]["name"] == "Bora Chaush",
    "WW fixture must carry Bora-confirmed contact.name",
)
assert_true(
    WW_DERIVATIVE["experience_sections"][0]["display_title"]
    == "AI Researcher & Developer Intern",
    "WW fixture must carry approved display title",
)
print("PASS B: Bora-confirmed contact.name present on derivative.")


# C. Unresolved contact sentinel reintroduced after build -> FAIL
unresolved_contact = copy.deepcopy(WW_DERIVATIVE)
unresolved_contact["contact"]["name"] = UNRESOLVED_PROTECTED_METADATA_SENTINEL
unresolved_contact["validation_digest"] = compute_derivative_validation_digest(unresolved_contact)
unresolved_metadata = validate_protected_metadata_resolved(unresolved_contact)
assert_false(unresolved_metadata["valid"], "C: unresolved contact sentinel must fail metadata")
assert_true(
    "contact.name" in unresolved_fields(unresolved_metadata["errors"]),
    "C: contact.name must be identified",
)
assert_false(
    "experience_sections[0].formal_title" in unresolved_fields(unresolved_metadata["errors"]),
    "C: formal_title sentinel must not block when display title approved",
)
for expected_field in (
    "modules[MOD_WW_001_SCOPE].immutable_snapshot.formal_title",
):
    assert_false(
        expected_field in unresolved_fields(unresolved_metadata["errors"]),
        f"C: snapshot formal_title must not block when display_title present: {expected_field}",
    )
print("PASS C: unresolved contact sentinel blocks protected metadata; title path still resolved.")


# D. Unresolved sentinel introduced after derivative build -> approval FAIL
synth_patch = {
    "patch_id": "PATCH_SYNTH_EXPORT_META",
    "target_master_id": SYNTHETIC_MASTER["master_id"],
    "operations": [
        {
            "op": "REORDER_MODULES",
            "module_ids": SYNTHETIC_MASTER["default_module_order"],
        }
    ],
}
synth_result = build_resume_derivative(
    master=SYNTHETIC_MASTER,
    patch=synth_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_SYNTH_EXPORT_META_001",
)
assert_true(synth_result["valid"] is True, "synthetic derivative should build")
mutated = copy.deepcopy(synth_result["derivative"])
mutated["contact"]["name"] = UNRESOLVED_PROTECTED_METADATA_SENTINEL
mutated["validation_digest"] = compute_derivative_validation_digest(mutated)
post_build_approval = approve_derivative_for_export(
    derivative=mutated,
    master=SYNTHETIC_MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(post_build_approval["valid"], "D: post-build sentinel must block approval")
assert_true(
    has_code(post_build_approval["errors"], "UNRESOLVED_PROTECTED_METADATA"),
    "D: unresolved protected metadata required",
)
print("PASS D: unresolved sentinel introduced after build blocks export approval.")


# E. Optional nullable location does not fail merely because it is null
resolved_with_null_location = {
    "derivative_id": "DERIV_NULL_LOCATION_OK",
    "master_id": "RESUME_MASTER_TEST",
    "master_version": "1",
    "patch_id": "PATCH_TEST",
    "module_order": [],
    "included_module_ids": [],
    "excluded_module_ids": [],
    "skills_order": [],
    "modules": [],
    "experience_sections": [
        {
            "section_id": "SEC_TEST_001",
            "experience_id": "EXP_TEST_001",
            "organization": "Resolved Org",
            "formal_title": "Resolved Title",
            "employment_category": "INTERNSHIP",
            "date_range": "Jun 2026 – Aug 2026",
            "location": None,
            "bullet_module_ids": [],
        }
    ],
    "contact": {"name": "Resolved Applicant", "email": None, "phone": None, "location": None},
    "education": [],
    "diff": [],
    "review_status": "HUMAN_REVIEW_REQUIRED",
    "export_allowed": False,
    "validation_digest": "0" * 64,
}
null_location_check = validate_protected_metadata_resolved(resolved_with_null_location)
assert_true(null_location_check["valid"] is True, "E: null location must not block")
assert_true(
    "experience_sections[0].location" not in unresolved_fields(null_location_check["errors"]),
    "E: location must not be flagged",
)
print("PASS E: optional nullable location=null does not block export metadata.")


# F. Fully resolved synthetic protected metadata + otherwise valid derivative -> approval PASS
synth_derivative = synth_result["derivative"]
if synth_derivative.get("review_status") == "NEEDS_SEMANTIC_REVIEW":
    cleared = complete_semantic_review(
        derivative=synth_derivative,
        master=SYNTHETIC_MASTER,
        claim_index=CLAIM_INDEX,
        evidence_index=EVIDENCE_INDEX,
    )
    assert_true(cleared["valid"] is True, "semantic review clearance required")
    synth_derivative = cleared["derivative"]

synth_approval = approve_derivative_for_export(
    derivative=synth_derivative,
    master=SYNTHETIC_MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_true(synth_approval["valid"] is True, "F: resolved synthetic derivative should approve")
assert_true(
    synth_approval["derivative"]["export_allowed"] is True,
    "F: export_allowed must become true",
)
print("PASS F: fully resolved synthetic derivative passes export approval.")

print("PASS: export protected-metadata adversarial regression tests complete.")
