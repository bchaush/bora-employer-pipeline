"""Bounded tests for Winter Walk résumé display title resolution."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"
EXPERIENCE_PATH = ROOT / "experiences" / "EXP_WW_001.json"
EVIDENCE_OFFER_PATH = ROOT / "evidence" / "winter_walk" / "WW_OFFER_001.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_protected_metadata import UNRESOLVED_PROTECTED_METADATA_SENTINEL  # noqa: E402
from resume_title_metadata import (  # noqa: E402
    has_approved_display_title,
    is_source_formal_title_unresolved,
    validate_experience_title_metadata,
)
from resume_validation import (  # noqa: E402
    build_resume_derivative,
    validate_resume_master,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


APPROVED_DISPLAY_TITLE = "AI Researcher & Developer Intern"
SOURCE_CONTRACTUAL_POSITION = "Intern"
SOURCE_FUNCTIONAL_ROLE = "AI Researcher and Developer"

BORA_APPROVED_WORDINGS = {
    "MOD_WW_001_SCOPE": (
        "Defined scope and guardrails for Winter Walk's internal Google Workspace "
        "operating system, including explicit limits on CRM functionality, public "
        "dashboards, automated sending, and causal fundraising claims."
    ),
    "MOD_WW_002_CONTROLS": (
        "Implemented fail-closed email controls that block live follow-up when the "
        "kill switch, test mode, or live-followup restriction is active, before "
        "queue-level eligibility checks run."
    ),
    "MOD_WW_003_INTAKE": (
        "Built a Google Drive-to-Workbook A CSV import workflow with automated "
        "logging for successful, held, and failed runs."
    ),
    "MOD_WW_004_SYNC": (
        "Built a self-report evidence workflow that maps form responses into the "
        "Evidence Log and syncs approved updates to the Adoption Matrix with audit "
        "logging."
    ),
    "MOD_WW_005_UAT": (
        "Documented 10 passing pilot/UAT checks covering import validation, PII "
        "absence, applicability checks, and related functional scenarios."
    ),
    "MOD_WW_006_PROCESS": (
        "Mapped Winter Walk's manual OP-support workflow into a structured operating "
        "process covering evidence tracking, review, follow-up, and human approval."
    ),
}


exp_result = validate_experience_repository()
ev_result = validate_evidence_repository(experience_result=exp_result)
claim_result = validate_claim_repository()
assert_true(exp_result["valid"] and ev_result["valid"] and claim_result["valid"], "repos valid")

MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
SECTION = MASTER["experience_sections"][0]
EXPERIENCE = json.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))
OFFER = json.loads(EVIDENCE_OFFER_PATH.read_text(encoding="utf-8"))


# A. Source contractual position remains Intern
assert_true(
    SECTION.get("source_contractual_position") == SOURCE_CONTRACTUAL_POSITION,
    "source contractual position must remain Intern",
)
assert_true("Intern" in str(EXPERIENCE.get("notes", "")), "Experience notes preserve Intern")
print("PASS A: source contractual position remains Intern.")


# B. Source functional role remains AI Researcher and Developer
assert_true(
    SECTION.get("source_functional_role") == SOURCE_FUNCTIONAL_ROLE,
    "source functional role must remain documented",
)
assert_true(SOURCE_FUNCTIONAL_ROLE in OFFER.get("fact", ""), "offer fact preserves functional role")
print("PASS B: source functional role remains AI Researcher and Developer.")


# C. Display title is human-approved presentation label
assert_true(SECTION.get("display_title") == APPROVED_DISPLAY_TITLE, "display title exact match")
assert_true(has_approved_display_title(SECTION), "display title must be approved")
print("PASS C: display title AI Researcher & Developer Intern accepted.")


# D/E. Display title is not treated as source-verbatim formal title
assert_true(
    is_source_formal_title_unresolved(SECTION.get("formal_title")),
    "formal_title must remain unresolved sentinel",
)
assert_true(
    SECTION.get("formal_title") == UNRESOLVED_PROTECTED_METADATA_SENTINEL,
    "formal_title must stay PENDING_BORA_REVIEW",
)
approval = SECTION.get("display_title_approval", {})
assert_true(approval.get("is_source_verbatim") is False, "must not be source-verbatim")
assert_true(
    approval.get("approved_display_title") == APPROVED_DISPLAY_TITLE,
    "approval binding must match display title",
)
print("PASS D/E: display title is human-approved and not source-verbatim formal title.")


# F. Changing display title without approval binding fails validation
mutated_section = copy.deepcopy(SECTION)
mutated_section["display_title"] = "Intern, AI Researcher and Developer"
title_result = validate_experience_title_metadata(
    mutated_section,
    field_prefix="experience_sections[0]",
)
assert_false(title_result["valid"], "unapproved alternate display title must fail")
assert_true(
    any(error.get("code") == "DISPLAY_TITLE_APPROVAL_MISMATCH" for error in title_result["errors"]),
    "approval mismatch required",
)
print("PASS F: unapproved alternate display title fails validation.")


# G. Experience/Evidence records unchanged (no reverse-write)
assert_true("AI Researcher & Developer Intern" not in json.dumps(EXPERIENCE), "no display title in Experience")
assert_true(
    "AI Researcher & Developer Intern" not in OFFER.get("fact", ""),
    "offer evidence must not contain composed display title",
)
print("PASS G: Experience/Evidence records unchanged.")


# H. Six approved Winter Walk module wordings unchanged
for module in MASTER["modules"]:
    if module["module_id"] not in BORA_APPROVED_WORDINGS:
        continue
    expected = BORA_APPROVED_WORDINGS[module["module_id"]]
    assert_true(module.get("wording") == expected, f"{module['module_id']} wording changed")
print("PASS H: six approved module wordings unchanged.")


# I. Contact metadata no longer blocks protected-metadata export readiness
master_result = validate_resume_master(
    MASTER,
    claim_index=claim_result["index"],
    evidence_index=ev_result["index"],
)
assert_true(master_result["valid"] is True, "master must validate with title metadata")
identity_patch = {
    "patch_id": "PATCH_WW_TITLE_NOOP",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]},
    ],
}
derivative_result = build_resume_derivative(
    master=MASTER,
    patch=identity_patch,
    claim_index=claim_result["index"],
    evidence_index=ev_result["index"],
    derivative_id="DERIV_WW_TITLE_001",
)
assert_true(derivative_result["valid"] is True, "derivative should build")
derivative = derivative_result["derivative"]
from resume_protected_metadata import validate_protected_metadata_resolved  # noqa: E402

metadata_result = validate_protected_metadata_resolved(derivative)
assert_true(metadata_result["valid"] is True, "protected metadata must pass with resolved contact")
assert_false(
    any(error.get("field") == "contact.name" for error in metadata_result["errors"]),
    "contact.name must not block protected metadata",
)
assert_true(derivative.get("export_allowed") is False, "export_allowed must remain false before approval")
print("PASS I: contact metadata resolved; protected-metadata export readiness passes.")


print("PASS: Winter Walk resume title resolution tests complete.")
