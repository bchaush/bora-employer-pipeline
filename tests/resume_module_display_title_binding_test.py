"""Adversarial regression tests for module-to-section display title binding (L-1)."""

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
from resume_protected_metadata import validate_protected_metadata_resolved  # noqa: E402
from resume_title_metadata import (  # noqa: E402
    build_experience_section_index,
    validate_module_snapshot_title_binding,
)
from resume_validation import (  # noqa: E402
    approve_derivative_for_export,
    build_resume_derivative,
    validate_resume_master,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def has_code(items: list, code: str) -> bool:
    return any(item.get("code") == code for item in items)


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

APPROVED_DISPLAY_TITLE = "AI Researcher & Developer Intern"

identity_patch = {
    "patch_id": "PATCH_L1_NOOP",
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
    derivative_id="DERIV_L1_WW_001",
)
assert_true(ww_derivative_result["valid"] is True, "WW derivative must build")
WW_DERIVATIVE = ww_derivative_result["derivative"]


def first_visible_module(derivative: dict) -> dict:
    included = derivative.get("included_module_ids", [])
    for module in derivative.get("modules", []):
        if module.get("module_id") in included:
            return module
    raise AssertionError("no visible module found")


# 1. Rogue module title Senior AI Research Lead -> FAIL
rogue = copy.deepcopy(WW_DERIVATIVE)
module = first_visible_module(rogue)
module["immutable_snapshot"]["display_title"] = "Senior AI Research Lead"
rogue["validation_digest"] = compute_derivative_validation_digest(rogue)
rogue_result = validate_protected_metadata_resolved(rogue)
assert_false(rogue_result["valid"], "rogue module title must fail")
assert_true(has_code(rogue_result["errors"], "MODULE_DISPLAY_TITLE_MISMATCH"), "rogue mismatch")
print("PASS 1: rogue module title Senior AI Research Lead fails.")


# 2. Near-match module title -> FAIL
near_match = copy.deepcopy(WW_DERIVATIVE)
first_visible_module(near_match)["immutable_snapshot"]["display_title"] = (
    "AI Researcher & Developer"
)
near_match["validation_digest"] = compute_derivative_validation_digest(near_match)
near_result = validate_protected_metadata_resolved(near_match)
assert_false(near_result["valid"], "near-match module title must fail")
assert_true(has_code(near_result["errors"], "MODULE_DISPLAY_TITLE_MISMATCH"), "near mismatch")
print("PASS 2: near-match module title fails.")


# 3. Missing section approval -> FAIL
no_approval = copy.deepcopy(WW_DERIVATIVE)
no_approval["experience_sections"][0].pop("display_title_approval", None)
no_approval["validation_digest"] = compute_derivative_validation_digest(no_approval)
no_approval_result = validate_protected_metadata_resolved(no_approval)
assert_false(no_approval_result["valid"], "missing section approval must fail")
assert_true(
    has_code(no_approval_result["errors"], "DISPLAY_TITLE_NOT_APPROVED")
    or has_code(no_approval_result["errors"], "MODULE_DISPLAY_TITLE_APPROVAL_UNRESOLVED"),
    "approval unresolved required",
)
print("PASS 3: missing section approval fails.")


# 4. Missing corresponding section -> FAIL
missing_section = copy.deepcopy(WW_DERIVATIVE)
module = first_visible_module(missing_section)
module["experience_id"] = "EXP_DOES_NOT_EXIST"
missing_section["validation_digest"] = compute_derivative_validation_digest(missing_section)
missing_section_result = validate_protected_metadata_resolved(missing_section)
assert_false(missing_section_result["valid"], "missing section must fail")
assert_true(
    has_code(missing_section_result["errors"], "MODULE_DISPLAY_TITLE_SECTION_NOT_FOUND"),
    "section not found required",
)
print("PASS 4: missing corresponding experience section fails.")


# 5. Missing module display title while formal title unresolved -> FAIL
missing_module_title = copy.deepcopy(WW_DERIVATIVE)
snapshot = first_visible_module(missing_module_title)["immutable_snapshot"]
snapshot.pop("display_title", None)
missing_module_title["validation_digest"] = compute_derivative_validation_digest(
    missing_module_title
)
missing_module_result = validate_protected_metadata_resolved(missing_module_title)
assert_false(missing_module_result["valid"], "missing module display title must fail")
assert_true(
    has_code(missing_module_result["errors"], "UNRESOLVED_PROTECTED_METADATA"),
    "unresolved module display title required",
)
print("PASS 5: missing module display title fails.")


# 6. Valid exact section/module title binding -> PASS
section_index = build_experience_section_index(WW_DERIVATIVE.get("experience_sections", []))
included = set(WW_DERIVATIVE.get("included_module_ids", []))
for module in WW_DERIVATIVE.get("modules", []):
    if module.get("module_id") not in included:
        continue
    experience_id = module.get("experience_id")
    section = section_index.get(experience_id) if isinstance(experience_id, str) else None
    binding = validate_module_snapshot_title_binding(
        module,
        section,
        field_prefix=f"modules[{module.get('module_id')}].immutable_snapshot",
    )
    assert_true(binding["valid"] is True, "valid binding should pass title readiness")
print("PASS 6: valid exact section/module title binding passes.")


# 7. Section formal title resolved with source-verbatim path -> preserve behavior
synth_patch = {
    "patch_id": "PATCH_L1_SYNTH",
    "target_master_id": SYNTHETIC_MASTER["master_id"],
    "operations": [
        {"op": "REORDER_MODULES", "module_ids": SYNTHETIC_MASTER["default_module_order"]},
    ],
}
synth_result = build_resume_derivative(
    master=SYNTHETIC_MASTER,
    patch=synth_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_L1_SYNTH_001",
)
assert_true(synth_result["valid"] is True, "synthetic derivative should build")
synth_derivative = synth_result["derivative"]
synth_meta = validate_protected_metadata_resolved(synth_derivative)
assert_true(synth_meta["valid"] is True, "resolved formal title path should pass")
synth_export = approve_derivative_for_export(
    derivative=synth_derivative,
    master=SYNTHETIC_MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_true(synth_export["valid"] is True, "synthetic export should pass")
print("PASS 7: resolved source-verbatim formal title path preserved.")


# 8. Real Winter Walk master blocked only by unresolved contact
ww_export = approve_derivative_for_export(
    derivative=WW_DERIVATIVE,
    master=WW_MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(ww_export["valid"], "WW export must remain blocked")
assert_true(
    any(error.get("field") == "contact.name" for error in ww_export["errors"]),
    "contact must be sole blocker",
)
assert_false(has_code(ww_export["errors"], "MODULE_DISPLAY_TITLE_MISMATCH"), "title binding ok")
master_result = validate_resume_master(
    WW_MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(master_result["valid"] is True, "real WW master must validate")
print("PASS 8: real Winter Walk master blocked only by unresolved contact.")


# 9. Synthetic resolved contact + correct display-title binding -> export PASS
ww_resolved_contact_master = copy.deepcopy(WW_MASTER)
ww_resolved_contact_master["contact"]["name"] = "Synthetic Resolved Applicant"
resolved_build = build_resume_derivative(
    master=ww_resolved_contact_master,
    patch=identity_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_L1_WW_RESOLVED_CONTACT_001",
)
assert_true(resolved_build["valid"] is True, "resolved-contact derivative must build")
resolved_contact = resolved_build["derivative"]
resolved_meta = validate_protected_metadata_resolved(resolved_contact)
assert_true(resolved_meta["valid"] is True, "resolved contact + binding should pass metadata")
resolved_export = approve_derivative_for_export(
    derivative=resolved_contact,
    master=ww_resolved_contact_master,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_true(resolved_export["valid"] is True, "resolved contact + binding should export")
assert_true(
    resolved_export["derivative"]["export_allowed"] is True,
    "export_allowed must become true",
)
print("PASS 9: resolved contact + correct display-title binding exports.")


# 10. Title mutation after derivative build -> blocked
post_build = copy.deepcopy(resolved_contact)
first_visible_module(post_build)["immutable_snapshot"]["display_title"] = (
    "Senior AI Research Lead"
)
post_build["validation_digest"] = compute_derivative_validation_digest(post_build)
post_build_export = approve_derivative_for_export(
    derivative=post_build,
    master=ww_resolved_contact_master,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    human_approval=True,
)
assert_false(post_build_export["valid"], "post-build title mutation must block export")
assert_true(
    has_code(post_build_export["errors"], "MODULE_DISPLAY_TITLE_MISMATCH"),
    "post-build mismatch required",
)
print("PASS 10: title mutation after derivative build blocks export.")

print("PASS: module display title binding adversarial tests complete.")
