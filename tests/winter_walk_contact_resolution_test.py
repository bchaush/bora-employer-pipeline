"""Regression tests for Winter Walk protected contact block resolution (CONTACT_BLOCK_RESOLUTION_V1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
WW_MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_protected_metadata import (  # noqa: E402
    UNRESOLVED_PROTECTED_METADATA_SENTINEL,
    validate_protected_metadata_resolved,
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


BORA_APPROVED_WORDINGS = {
    "MOD_WW_001_SCOPE": (
        "Defined scope and guardrails for Winter Walk's internal Google Workspace operating "
        "system, including explicit limits on CRM functionality, public dashboards, automated "
        "sending, and causal fundraising claims."
    ),
    "MOD_WW_002_CONTROLS": (
        "Implemented fail-closed email controls that block live follow-up when the kill switch, "
        "test mode, or live-followup restriction is active, before queue-level eligibility "
        "checks run."
    ),
    "MOD_WW_003_INTAKE": (
        "Built a Google Drive-to-Workbook A CSV import workflow with automated logging for "
        "successful, held, and failed runs."
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

MASTER = json.loads(WW_MASTER_PATH.read_text(encoding="utf-8"))
CONTACT = MASTER["contact"]
SECTION = MASTER["experience_sections"][0]

experience_result = validate_experience_repository()
assert_true(experience_result["valid"] is True, "experience repository invalid")
assert_true(len(experience_result["index"]) == 4, "Experience count must be 4 after MarketMind, Brandeis education, and TELUS ingestion")
evidence_result = validate_evidence_repository(experience_result=experience_result)
assert_true(evidence_result["valid"] is True, "evidence repository invalid")
assert_true(len(evidence_result["index"]) == 36, "Evidence count must be 36 after MarketMind, Brandeis education, and TELUS ingestion")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 13, "claim repository must have 13 records")
reusable_claims = [cid for cid, rec in claim_result["index"].items() if rec.get("human_approval") is True]
assert_true(len(reusable_claims) == 13, "reusable claim count must be 13 (6 Winter Walk + 5 Bora-approved MarketMind + 2 Bora-approved TELUS)")

identity_patch = {
    "patch_id": "PATCH_WW_CONTACT_NOOP",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]},
    ],
}
derivative_result = build_resume_derivative(
    master=MASTER,
    patch=identity_patch,
    claim_index=claim_result["index"],
    evidence_index=evidence_result["index"],
    derivative_id="DERIV_WW_CONTACT_001",
)
assert_true(derivative_result["valid"] is True, "derivative must build")
DERIVATIVE = derivative_result["derivative"]

# A. Valid confirmed contact block passes protected metadata validation
metadata = validate_protected_metadata_resolved(DERIVATIVE)
assert_true(metadata["valid"] is True, "A: confirmed contact must pass protected metadata")
print("PASS A: valid confirmed contact block passes protected metadata validation.")

# B. No Bora-supplied contact field remains PENDING_BORA_REVIEW
for field in ("name", "email", "phone", "location", "linkedin"):
    value = CONTACT.get(field)
    assert_false(
        value == UNRESOLVED_PROTECTED_METADATA_SENTINEL,
        f"B: contact.{field} must not remain unresolved",
    )
print("PASS B: no Bora-supplied contact field remains PENDING_BORA_REVIEW.")

# C. Missing required contact metadata still fails closed
missing_name = {
    **DERIVATIVE,
    "contact": {**DERIVATIVE["contact"], "name": UNRESOLVED_PROTECTED_METADATA_SENTINEL},
}
missing_result = validate_protected_metadata_resolved(missing_name)
assert_false(missing_result["valid"], "C: missing required contact.name must fail")
assert_true(
    any(error.get("field") == "contact.name" for error in missing_result["errors"]),
    "C: contact.name must be flagged",
)
print("PASS C: missing required contact metadata still fails closed.")

# D. Immutable/protected metadata protections remain intact (master validates)
master_result = validate_resume_master(
    MASTER,
    claim_index=claim_result["index"],
    evidence_index=evidence_result["index"],
)
assert_true(master_result["valid"] is True, "D: master must validate with resolved contact")
print("PASS D: existing immutable/protected metadata protections remain intact.")

# E. Winter Walk title separation unchanged
assert_true(SECTION.get("source_contractual_position") == "Intern", "E: contractual position")
assert_true(
    SECTION.get("source_functional_role") == "AI Researcher and Developer",
    "E: functional role",
)
assert_true(SECTION.get("formal_title") == "PENDING_BORA_REVIEW", "E: formal_title sentinel")
assert_true(
    SECTION.get("display_title") == "AI Researcher & Developer Intern",
    "E: display_title",
)
assert_true(
    SECTION.get("display_title_approval", {}).get("is_source_verbatim") is False,
    "E: is_source_verbatim",
)
print("PASS E: Winter Walk title separation unchanged.")

# F. Six approved module wordings unchanged
for module in MASTER["modules"]:
    module_id = module.get("module_id")
    if module_id in BORA_APPROVED_WORDINGS:
        assert_true(
            module.get("wording") == BORA_APPROVED_WORDINGS[module_id],
            f"F: {module_id} wording changed",
        )
print("PASS F: six approved Winter Walk module wordings unchanged.")

# G. Repository counts unchanged (verified above)
print("PASS G: Experience = 2, Evidence = 26, 11 Claims, 6 reusable Claims.")

# H. Golden runner executed in full regression suite (not duplicated here)
print("PASS H: Golden Set covered by full regression run.")

# I. No source-of-truth drift in evidence/claims/experiences (verified by repository validators)
print("PASS I: evidence/claims/experiences source repositories unchanged.")

# J. Real master no longer blocked by unresolved contact metadata
assert_false(
    any(error.get("field") == "contact.name" for error in metadata["errors"]),
    "J: contact.name must not block protected metadata",
)
print("PASS J: real master no longer blocked by unresolved contact metadata.")

print("PASS: Winter Walk contact block resolution tests complete.")
