"""Bounded tests for Winter Walk protected metadata evidence milestone."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
EVIDENCE_PATH = ROOT / "evidence" / "winter_walk" / "WW_OFFER_001.json"
EXPERIENCE_PATH = ROOT / "experiences" / "EXP_WW_001.json"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from claim_validation import validate_claim  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_validation import build_resume_derivative, validate_resume_master  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


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

BOUNDED_DATE_RANGE = "Jun 2026 – Aug 2026"
FORBIDDEN_COMPOSED_TITLE = "AI Researcher & Developer Intern"


# A. Offer-letter Evidence validates
offer = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
evidence_validator = build_draft202012_validator(ROOT / "schemas" / "evidence.schema.json")
assert_true(
    list(evidence_validator.iter_errors(offer)) == [],
    "WW_OFFER_001 must pass evidence schema",
)
print("PASS A: offer-letter Evidence validates.")


# B. Evidence references EXP_WW_001
assert_true(offer.get("experience_id") == "EXP_WW_001", "WW_OFFER_001 must cite EXP_WW_001")
print("PASS B: Evidence references EXP_WW_001.")


# Load trusted indexes
exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(ev_result["records_checked"] == 42, "expected 42 evidence records")
assert_true("WW_OFFER_001" in ev_result["index"], "WW_OFFER_001 missing from trusted index")


# C. Internship category is supported
fact = offer.get("fact", "")
notes = str(offer.get("notes", ""))
limitations = " ".join(offer.get("limitations", []))
assert_true("unpaid internship" in fact.casefold(), "offer fact must document unpaid internship")
experience = json.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))
exp_notes = str(experience.get("notes", ""))
assert_true("INTERNSHIP" in exp_notes, "experience notes must record internship category")
MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
section = MASTER["experience_sections"][0]
assert_true(section.get("employment_category") == "INTERNSHIP", "master employment_category")
print("PASS C: internship category supported.")


# D. Functional role AI Researcher and Developer is source-supported
assert_true(
    "AI Researcher and Developer" in fact,
    "offer fact must document functional role AI Researcher and Developer",
)
assert_true(
    "AI Researcher and Developer" in exp_notes,
    "experience notes must record functional role",
)
print("PASS D: functional role AI Researcher and Developer source-supported.")


# E. Composed title AI Researcher & Developer Intern is NOT silently created
assert_true(
    section.get("formal_title") == "PENDING_BORA_REVIEW",
    "formal_title sentinel must remain unresolved",
)
assert_true(
    section.get("display_title") == FORBIDDEN_COMPOSED_TITLE,
    "composed title belongs in approved display_title only",
)
for module in MASTER["modules"]:
    if "immutable_snapshot" not in module:
        continue
    if not module["module_id"].startswith("MOD_WW_"):
        # Winter-Walk-specific assertion: only Winter Walk's formal_title is
        # the PENDING_BORA_REVIEW sentinel. Other employment-shaped modules
        # (e.g. TELUS) may legitimately carry a fully resolved formal_title
        # with its own separately-approved display_title; that is a distinct,
        # independently-tested contract, not a Winter Walk regression.
        continue
    assert_true(
        module["immutable_snapshot"]["formal_title"] == "PENDING_BORA_REVIEW",
        f"{module['module_id']} formal_title sentinel must remain unresolved",
    )
    assert_true(
        module["immutable_snapshot"]["display_title"] == FORBIDDEN_COMPOSED_TITLE,
        f"{module['module_id']} display_title must store approved label",
    )
assert_true(
    FORBIDDEN_COMPOSED_TITLE in limitations,
    "limitations must block composed title",
)
print("PASS E: composed title stored only as approved display_title, not formal_title.")


# F. Month-level date range resolves to Jun 2026 – Aug 2026
assert_true(section.get("date_range") == BOUNDED_DATE_RANGE, "master date_range")
for module in MASTER["modules"]:
    if "immutable_snapshot" not in module:
        continue
    if not module["module_id"].startswith("MOD_WW_"):
        # Winter-Walk-specific date range; other employment-shaped modules
        # (e.g. TELUS) legitimately have their own distinct, independently
        # verified/approved date_range -- not a Winter Walk regression.
        continue
    assert_true(
        module["immutable_snapshot"]["date_range"] == BOUNDED_DATE_RANGE,
        f"{module['module_id']} date_range",
    )
print("PASS F: month-level date range Jun 2026 – Aug 2026 stored.")


# G. Aug 21 vs Aug 22 discrepancy remains explicitly unresolved
assert_true("August 21, 2026" in fact, "Aug 21 source observation required")
assert_true("August 22, 2026" in fact, "Aug 22 source observation required")
assert_true(
    "unresolved" in notes.casefold() or "unresolved" in limitations.casefold(),
    "discrepancy must be marked unresolved",
)
assert_true(
    "unresolved" in exp_notes.casefold(),
    "experience notes must mark exact end day unresolved",
)
assert_true(
    "August 21" not in section.get("date_range", ""),
    "exact Aug 21 must not appear in résumé date_range",
)
assert_true(
    "August 22" not in section.get("date_range", ""),
    "exact Aug 22 must not appear in résumé date_range",
)
print("PASS G: Aug 21 vs Aug 22 discrepancy explicitly unresolved.")


# H. No LinkedIn fact ingested
offer_blob = json.dumps(offer) + exp_notes + json.dumps(experience)
assert_true("linkedin" not in offer_blob.casefold(), "LinkedIn must not be ingested")
print("PASS H: no LinkedIn fact ingested.")


# I. Approved six Winter Walk module wordings byte-for-byte unchanged
for module in MASTER["modules"]:
    module_id = module["module_id"]
    if not module_id.startswith("MOD_WW_"):
        continue
    expected = BORA_APPROVED_WORDINGS.get(module_id)
    assert_true(expected is not None, f"missing approved wording fixture for {module_id}")
    assert_true(
        module.get("wording") == expected,
        f"{module_id} wording changed from Bora-approved text",
    )
print("PASS I: all six Bora-approved module wordings unchanged.")


# J. Approval record remains valid because wording did not change
master_notes = str(MASTER.get("notes", ""))
assert_true("WORDING_APPROVED" in master_notes, "WORDING_APPROVED must remain recorded")
assert_true(
    "Bora explicitly approved" in master_notes,
    "explicit Bora approval event must remain",
)
print("PASS J: wording approval record remains valid.")


# K. Winter Walk reusable Claims remain unchanged (6 reusable, lineage untouched)
assert_true(claim_result["records_checked"] == 16, "claim count must be 16 after MarketMind, TELUS, and CANDIDATE_SOURCE_INGESTION_V1 drafting")
ww_claim_ids = [f"CLAIM_WW_{i:03d}" for i in range(1, 7)]
for claim_id in ww_claim_ids:
    claim = claim_result["index"][claim_id]
    assert_true(claim.get("human_approval") is True, f"{claim_id} human_approval")
    validated = validate_claim(claim, ev_result["index"])
    assert_true(validated.get("reusable") is True, f"{claim_id} reusable")
print("PASS K: six reusable Winter Walk Claims unchanged.")


# L. No derivative/export becomes allowed
master_result = validate_resume_master(
    MASTER,
    claim_index=claim_result["index"],
    evidence_index=ev_result["index"],
)
assert_true(master_result["valid"] is True, "master must validate after metadata update")
identity_patch = {
    "patch_id": "PATCH_WW_IDENTITY_NOOP_META",
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
    derivative_id="DERIV_WW_CANDIDATE_META_001",
)
assert_true(derivative_result["valid"] is True, "identity derivative should build")
derivative = derivative_result["derivative"]
assert_true(derivative.get("export_allowed") is False, "export must remain blocked")
print("PASS L: derivative/export remains blocked.")


# Modeling constraint: Experience schema has single organization field (display preserved)
assert_true(experience.get("organization") == "Winter Walk", "display organization preserved")
assert_true("Winter Walk, Inc." in exp_notes, "legal organization documented in notes")
print("PASS: legal vs display organization modeling constraint documented.")

print("PASS: Winter Walk protected metadata evidence tests complete.")
