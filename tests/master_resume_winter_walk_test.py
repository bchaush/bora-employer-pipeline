import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_semantic import validate_module_wording_semantics  # noqa: E402
from resume_validation import (  # noqa: E402
    build_resume_derivative,
    validate_resume_master,
    validate_resume_module,
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
MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))

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


# Master stores exact Bora-approved wording unchanged
for module in MASTER["modules"]:
    module_id = module["module_id"]
    expected = BORA_APPROVED_WORDINGS.get(module_id)
    assert_true(expected is not None, f"missing approved wording fixture for {module_id}")
    assert_true(
        module.get("wording") == expected,
        f"{module_id} must store exact Bora-approved wording",
    )
print("PASS: exact Bora-approved wordings stored unchanged.")


# Real Winter Walk master content validates through closed architecture
master_result = validate_resume_master(
    MASTER,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(master_result["valid"] is True, "real WW master should validate")
assert_true(MASTER.get("protected") is True, "master must remain protected")
print("PASS: real Winter Walk master validates.")


# Every module resolves to EXP_WW_001 with reusable claim lineage
for module in MASTER["modules"]:
    assert_true(
        module.get("experience_id") == "EXP_WW_001",
        f"{module['module_id']} must reference EXP_WW_001",
    )
    module_result = validate_resume_module(
        module,
        claim_index=CLAIM_INDEX,
        evidence_index=EVIDENCE_INDEX,
    )
    assert_true(module_result["valid"] is True, f"{module['module_id']} should validate")
    assert_true(module_result["factual_valid"] is True, f"{module['module_id']} factual valid")
    assert_true(module_result["style_valid"] is True, f"{module['module_id']} style valid")
print("PASS: all six Winter Walk modules validate with lineage and style.")


# Broadened enterprise SaaS wording fails
broadened = copy.deepcopy(MASTER["modules"][0])
broadened["wording"] = (
    "Architected an enterprise SaaS platform for Winter Walk with public CRM ownership."
)
broadened_result = validate_module_wording_semantics(
    broadened,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_false(broadened_result["valid"], "broadened enterprise SaaS wording should fail")
print("PASS: intentionally broadened WW wording fails semantic guard.")


# CLAIM_WW_006 + BPMN wording fails
bpmn_module = copy.deepcopy(MASTER["modules"][5])
bpmn_module["wording"] = (
    "Documented Winter Walk's manual OP-support workflow using BPMN 2.0 enterprise "
    "process modeling and translated it into a structured operating process."
)
bpmn_result = validate_module_wording_semantics(
    bpmn_module,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_false(bpmn_result["valid"], "BPMN wording on CLAIM_WW_006 should fail")
assert_true(
    has_code(bpmn_result["errors"], "RESUME_FORBIDDEN_CONTEXT_LEAKAGE")
    or has_code(bpmn_result["errors"], "RESUME_WORDING_SEMANTIC_VIOLATION"),
    "BPMN blocked",
)
print("PASS: CLAIM_WW_006 + BPMN wording fails.")


# CLAIM_WW_006 canonical wording must not reintroduce removed "data intake" language
process_module = next(
    m for m in MASTER["modules"] if m["module_id"] == "MOD_WW_006_PROCESS"
)
assert_true(
    "data intake" not in process_module["wording"].casefold(),
    "canonical CLAIM_WW_006 module must not contain data intake",
)
# Adversarial data-intake expansion is not yet a forbidden_context on CLAIM_WW_006;
# governance relies on claim-bounded authoring plus human review for this boundary.
data_intake_module = copy.deepcopy(process_module)
data_intake_module["wording"] = (
    "Documented Winter Walk's manual OP-support workflow and data intake architecture, "
    "translating it into a structured operating process covering evidence tracking."
)
data_intake_result = validate_module_wording_semantics(
    data_intake_module,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
if not data_intake_result["valid"]:
    print("PASS: CLAIM_WW_006 + data intake wording fails under current semantic rules.")
else:
    print(
        "NOTE: data intake boundary not encoded in forbidden_contexts; "
        "canonical module excludes it; human review required."
    )


# Unsupported metric addition fails (fabricated quantified outcome)
metric_module = copy.deepcopy(MASTER["modules"][4])
metric_module["wording"] = (
    "Documented Winter Walk Workbook B pilot and UAT results and increased "
    "fundraising outcomes by 37% across ten pilot test rows."
)
metric_result = validate_module_wording_semantics(
    metric_module,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_false(metric_result["valid"], "unsupported metric should fail")
assert_true(
    has_code(metric_result["errors"], "RESUME_WORDING_SEMANTIC_VIOLATION"),
    "metric semantic violation",
)
print("PASS: unsupported metric addition fails.")


# Unsupported tool addition fails (Google Cloud upgrade on Apps Script evidence)
tool_module = copy.deepcopy(MASTER["modules"][2])
tool_module["wording"] = (
    "Built Google Cloud CSV intake into Workbook A with automated import logging "
    "that records Success, Held, and Failed run statuses."
)
tool_result = validate_module_wording_semantics(
    tool_module,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
)
assert_false(tool_result["valid"], "unsupported Google Cloud tool upgrade should fail")
assert_true(
    has_code(tool_result["errors"], "RESUME_WORDING_SEMANTIC_VIOLATION"),
    "tool semantic violation",
)
print("PASS: unsupported tool addition fails.")


# Candidate master remains human-review-required; export not allowed on identity patch
identity_patch = {
    "patch_id": "PATCH_WW_IDENTITY_NOOP",
    "target_master_id": MASTER["master_id"],
    "operations": [
        {"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]},
    ],
}
derivative_result = build_resume_derivative(
    master=MASTER,
    patch=identity_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_WW_CANDIDATE_001",
)
assert_true(derivative_result["valid"] is True, "identity reorder derivative should build")
derivative = derivative_result["derivative"]
assert_true(derivative.get("export_allowed") is False, "export must remain false")
assert_true(
    derivative.get("review_status") in {"HUMAN_REVIEW_REQUIRED", "NEEDS_SEMANTIC_REVIEW"},
    "human review required",
)
print("PASS: candidate derivative remains human-review-required with export blocked.")


# Bora wording approval recorded; protected metadata still pending
notes = str(MASTER.get("notes", ""))
assert_true("WORDING_APPROVED" in notes, "master notes must record wording approval")
assert_true(
    "Bora explicitly approved" in notes,
    "master notes must record explicit Bora approval event",
)
assert_true(
    MASTER["contact"]["name"] == "PENDING_BORA_REVIEW",
    "contact block must remain unresolved",
)
assert_true(
    MASTER["experience_sections"][0]["formal_title"] == "PENDING_BORA_REVIEW",
    "formal title must remain unresolved",
)
assert_true(
    MASTER["experience_sections"][0]["date_range"] == "PENDING_BORA_REVIEW",
    "date range must remain unresolved",
)
print("PASS: Bora module wording approval recorded; metadata still pending.")

print("PASS: master resume Winter Walk v1 real-content tests complete.")
