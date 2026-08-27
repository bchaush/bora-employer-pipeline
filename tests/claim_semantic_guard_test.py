"""Focused tests for claim semantic-boundary guard via validate_claim."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
CLAIMS_ROOT = ROOT / "claims"
EVIDENCE_ROOT = ROOT / "evidence"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_validation import validate_claim  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def error_codes(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


evidence_result = validate_evidence_repository(EVIDENCE_ROOT)
assert_true(evidence_result["valid"] is True, "trusted Evidence repository must be valid")
EVIDENCE_INDEX = evidence_result["index"]
assert_true(EVIDENCE_INDEX is not None, "trusted Evidence index missing")


def load_real_claim(claim_id: str) -> dict:
    path = CLAIMS_ROOT / "winter_walk" / f"{claim_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def base_from(claim_id: str) -> dict:
    claim = load_real_claim(claim_id)
    claim = copy.deepcopy(claim)
    claim["human_approval"] = True
    return claim


REAL_CLAIM_IDS = [
    "CLAIM_WW_001",
    "CLAIM_WW_002",
    "CLAIM_WW_003",
    "CLAIM_WW_004",
    "CLAIM_WW_005",
]


# ---------------------------------------------------------------------------
# Adversarial: known forbidden upgrades / fabricated outcomes
# ---------------------------------------------------------------------------

adv1 = base_from("CLAIM_WW_003")
adv1["claim_id"] = "CLAIM_ADV_GOOGLE_CLOUD"
adv1["wording"] = (
    "Built Google Cloud infrastructure for Drive-folder CSV intake into "
    "Workbook A with automated import logging."
)
r1 = validate_claim(adv1, EVIDENCE_INDEX)
assert_false(r1["valid_record"], "Google Cloud upgrade must invalidate record")
assert_false(r1["reusable"], "Google Cloud upgrade must not be reusable")
assert_true("FORBIDDEN_SEMANTIC_PATTERN" in error_codes(r1), f"adv1 errors={r1['errors']}")
print("PASS 1: Google Cloud upgrade from Apps Script evidence rejected.")

adv2 = base_from("CLAIM_WW_001")
adv2["claim_id"] = "CLAIM_ADV_ENTERPRISE_SAAS"
adv2["wording"] = (
    "Architected an enterprise SaaS platform and enterprise software "
    "architecture for Winter Walk partner support."
)
r2 = validate_claim(adv2, EVIDENCE_INDEX)
assert_false(r2["valid_record"], "enterprise SaaS architecture must invalidate")
assert_false(r2["reusable"], "enterprise SaaS must not be reusable")
assert_true("FORBIDDEN_SEMANTIC_PATTERN" in error_codes(r2), f"adv2 errors={r2['errors']}")
print("PASS 2: enterprise SaaS / architecture upgrade rejected.")

adv3 = base_from("CLAIM_WW_005")
adv3["claim_id"] = "CLAIM_ADV_ENTERPRISE_QA"
adv3["wording"] = (
    "Owned enterprise QA engineering for Winter Walk Workbook B pilot "
    "and production QA ownership across releases."
)
r3 = validate_claim(adv3, EVIDENCE_INDEX)
assert_false(r3["valid_record"], "enterprise QA ownership must invalidate")
assert_false(r3["reusable"], "enterprise QA must not be reusable")
assert_true("FORBIDDEN_SEMANTIC_PATTERN" in error_codes(r3), f"adv3 errors={r3['errors']}")
print("PASS 3: enterprise QA ownership from UAT/pilot evidence rejected.")

adv4 = base_from("CLAIM_WW_004")
adv4["claim_id"] = "CLAIM_ADV_PRODUCTION_ML"
adv4["wording"] = (
    "Implemented production ML and machine learning engineering to map "
    "form responses into Evidence_Log."
)
r4 = validate_claim(adv4, EVIDENCE_INDEX)
assert_false(r4["valid_record"], "production ML must invalidate")
assert_false(r4["reusable"], "production ML must not be reusable")
assert_true("FORBIDDEN_SEMANTIC_PATTERN" in error_codes(r4), f"adv4 errors={r4['errors']}")
print("PASS 4: production ML from workflow evidence rejected.")

adv5 = base_from("CLAIM_WW_001")
adv5["claim_id"] = "CLAIM_ADV_FUNDRAISING_PCT"
adv5["wording"] = (
    "Defined Winter Walk scope boundaries and delivered a 37% fundraising "
    "increase for partner adoption."
)
r5 = validate_claim(adv5, EVIDENCE_INDEX)
assert_false(r5["valid_record"], "37% fundraising claim must invalidate")
assert_false(r5["reusable"], "37% fundraising must not be reusable")
assert_true("FORBIDDEN_SEMANTIC_PATTERN" in error_codes(r5), f"adv5 errors={r5['errors']}")
print("PASS 5: fabricated 37% fundraising increase rejected.")

adv6 = base_from("CLAIM_WW_002")
adv6["claim_id"] = "CLAIM_ADV_HOURS_REDUCTION"
adv6["wording"] = (
    "Implemented fail-closed follow-up send controls that achieved a "
    "200 hours/month reduction in manual follow-up work."
)
r6 = validate_claim(adv6, EVIDENCE_INDEX)
assert_false(r6["valid_record"], "200 hours/month reduction must invalidate")
assert_false(r6["reusable"], "200 hours/month must not be reusable")
assert_true("FORBIDDEN_SEMANTIC_PATTERN" in error_codes(r6), f"adv6 errors={r6['errors']}")
print("PASS 6: fabricated 200 hours/month reduction rejected.")

# human_approval=true alone cannot rescue adversarial claims
for label, result in (
    ("adv1", r1),
    ("adv2", r2),
    ("adv3", r3),
    ("adv4", r4),
    ("adv5", r5),
    ("adv6", r6),
):
    assert_true(
        result["human_approved"] is True,
        f"{label} fixture should set human_approval true for override check",
    )
    assert_false(
        result["reusable"],
        f"{label}: human_approval=true must not make semantic-invalid claim reusable",
    )
print("PASS 6b: human_approval=true does not rescue adversarial claims.")


# ---------------------------------------------------------------------------
# Legitimate: real five Winter Walk claims
# ---------------------------------------------------------------------------
for claim_id in REAL_CLAIM_IDS:
    claim = load_real_claim(claim_id)
    assert_true(claim["human_approval"] is False, f"{claim_id} must remain unapproved")
    result = validate_claim(claim, EVIDENCE_INDEX)
    assert_true(result["valid_record"] is True, f"{claim_id} should remain valid_record")
    assert_false(result["reusable"], f"{claim_id} must remain non-reusable")
    assert_true(
        "FORBIDDEN_SEMANTIC_PATTERN" not in error_codes(result),
        f"{claim_id} unexpectedly hit semantic guard: {result['errors']}",
    )
    assert_true(
        any(w.get("code") == "NOT_HUMAN_APPROVED" for w in result["warnings"]),
        f"{claim_id} missing NOT_HUMAN_APPROVED",
    )
    print(f"PASS 7: {claim_id} remains valid_record / not reusable.")


# ---------------------------------------------------------------------------
# Legitimate: evidenced factual number (ten pilot rows)
# ---------------------------------------------------------------------------
pilot = base_from("CLAIM_WW_005")
pilot["claim_id"] = "CLAIM_OK_TEN_ROWS"
# Keep factual descriptor; no impact fabrication.
assert_true(
    "ten pilot test rows" in pilot["wording"].casefold()
    or "ten pilot test rows" in load_real_claim("CLAIM_WW_005")["wording"].casefold(),
    "real CLAIM_WW_005 must retain ten pilot test rows wording",
)
r_pilot = validate_claim(load_real_claim("CLAIM_WW_005"), EVIDENCE_INDEX)
assert_true(r_pilot["valid_record"] is True, "ten pilot test rows claim must pass")
print("PASS 8: ten pilot test rows remains allowed (evidenced factual count).")


# ---------------------------------------------------------------------------
# Legitimate: supported technology already present in cited Evidence
# ---------------------------------------------------------------------------
tech = base_from("CLAIM_WW_003")
tech["claim_id"] = "CLAIM_OK_APPS_SCRIPT_DRIVE"
tech["wording"] = (
    "Built Drive-folder CSV intake into Workbook A using Google Apps Script "
    "and Google Drive with automated import logging that records Success, "
    "Held, and Failed run statuses."
)
r_tech = validate_claim(tech, EVIDENCE_INDEX)
assert_true(
    r_tech["valid_record"] is True,
    f"supported Google Apps Script/Drive wording must pass: {r_tech['errors']}",
)
assert_true(r_tech["reusable"] is True, "approved supported-tech claim should be reusable")
print("PASS 9: supported technology terms already in cited Evidence remain allowed.")

print("PASS: claim semantic-boundary guard tests completed successfully.")
