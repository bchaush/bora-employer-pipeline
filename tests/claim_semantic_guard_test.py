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


def assert_semantic_blocked(result: dict, label: str) -> None:
    assert_false(result["valid_record"], f"{label}: expected valid_record=false")
    assert_false(result["reusable"], f"{label}: expected reusable=false")
    assert_true(
        "FORBIDDEN_SEMANTIC_PATTERN" in error_codes(result),
        f"{label}: missing FORBIDDEN_SEMANTIC_PATTERN; errors={result['errors']}",
    )


evidence_result = validate_evidence_repository(EVIDENCE_ROOT)
assert_true(evidence_result["valid"] is True, "trusted Evidence repository must be valid")
EVIDENCE_INDEX = evidence_result["index"]
assert_true(EVIDENCE_INDEX is not None, "trusted Evidence index missing")


def load_real_claim(claim_id: str) -> dict:
    path = CLAIMS_ROOT / "winter_walk" / f"{claim_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def base_from(claim_id: str) -> dict:
    claim = copy.deepcopy(load_real_claim(claim_id))
    claim["human_approval"] = True
    return claim


def make_evidence(
    evidence_id: str,
    *,
    fact: str,
    capabilities: list[str] | None = None,
    technologies: list[str] | None = None,
    limitations: list[str] | None = None,
    notes: str | None = None,
    evidence_state: str = "VERIFIED",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "experience_id": "EXP_WW_001",
        "fact": fact,
        "capabilities": capabilities or [],
        "technologies": technologies or [],
        "evidence_state": evidence_state,
        "original_source": f"synthetic-fixture://{evidence_id}",
        "source_location": "tests/claim_semantic_guard_test.py",
        "safe_for_external_use": False,
        "notes": notes,
        "limitations": limitations or [],
    }


def index_with(*records: dict) -> dict:
    """Trusted Winter Walk index plus temporary synthetic Evidence records."""
    merged = dict(EVIDENCE_INDEX)
    for record in records:
        merged[record["evidence_id"]] = record
    return merged


REAL_CLAIM_IDS = [
    "CLAIM_WW_001",
    "CLAIM_WW_002",
    "CLAIM_WW_003",
    "CLAIM_WW_004",
    "CLAIM_WW_005",
]


# ---------------------------------------------------------------------------
# Original six adversarial upgrades / fabricated outcomes
# ---------------------------------------------------------------------------

adv1 = base_from("CLAIM_WW_003")
adv1["claim_id"] = "CLAIM_ADV_GOOGLE_CLOUD"
adv1["wording"] = (
    "Built Google Cloud infrastructure for Drive-folder CSV intake into "
    "Workbook A with automated import logging."
)
r1 = validate_claim(adv1, EVIDENCE_INDEX)
assert_semantic_blocked(r1, "adv1 Google Cloud")
print("PASS 1: Google Cloud upgrade from Apps Script evidence rejected.")

adv2 = base_from("CLAIM_WW_001")
adv2["claim_id"] = "CLAIM_ADV_ENTERPRISE_SAAS"
adv2["wording"] = (
    "Architected an enterprise SaaS platform and enterprise software "
    "architecture for Winter Walk partner support."
)
r2 = validate_claim(adv2, EVIDENCE_INDEX)
assert_semantic_blocked(r2, "adv2 enterprise SaaS")
print("PASS 2: enterprise SaaS / architecture upgrade rejected.")

adv3 = base_from("CLAIM_WW_005")
adv3["claim_id"] = "CLAIM_ADV_ENTERPRISE_QA"
adv3["wording"] = (
    "Owned enterprise QA engineering for Winter Walk Workbook B pilot "
    "and production QA ownership across releases."
)
r3 = validate_claim(adv3, EVIDENCE_INDEX)
assert_semantic_blocked(r3, "adv3 enterprise QA")
print("PASS 3: enterprise QA ownership from UAT/pilot evidence rejected.")

adv4 = base_from("CLAIM_WW_004")
adv4["claim_id"] = "CLAIM_ADV_PRODUCTION_ML"
adv4["wording"] = (
    "Implemented production ML and machine learning engineering to map "
    "form responses into Evidence_Log."
)
r4 = validate_claim(adv4, EVIDENCE_INDEX)
assert_semantic_blocked(r4, "adv4 production ML")
print("PASS 4: production ML from workflow evidence rejected.")

adv5 = base_from("CLAIM_WW_001")
adv5["claim_id"] = "CLAIM_ADV_FUNDRAISING_PCT"
adv5["wording"] = (
    "Defined Winter Walk scope boundaries and delivered a 37% fundraising "
    "increase for partner adoption."
)
r5 = validate_claim(adv5, EVIDENCE_INDEX)
assert_semantic_blocked(r5, "adv5 37% fundraising")
print("PASS 5: fabricated 37% fundraising increase rejected.")

adv6 = base_from("CLAIM_WW_002")
adv6["claim_id"] = "CLAIM_ADV_HOURS_REDUCTION"
adv6["wording"] = (
    "Implemented fail-closed follow-up send controls that achieved a "
    "200 hours/month reduction in manual follow-up work."
)
r6 = validate_claim(adv6, EVIDENCE_INDEX)
assert_semantic_blocked(r6, "adv6 200 hours/month")
print("PASS 6: fabricated 200 hours/month reduction rejected.")

for label, result in (
    ("adv1", r1),
    ("adv2", r2),
    ("adv3", r3),
    ("adv4", r4),
    ("adv5", r5),
    ("adv6", r6),
):
    assert_true(result["human_approved"] is True, f"{label} approval fixture")
    assert_false(result["reusable"], f"{label}: approval cannot rescue")
print("PASS 6b: human_approval=true does not rescue adversarial claims.")


# ---------------------------------------------------------------------------
# Negation / limitation leakage (six required cases)
# ---------------------------------------------------------------------------

neg_cases = [
    (
        "NEG_ENTERPRISE_ARCH",
        "CLAIM_WW_001",
        "does not demonstrate enterprise architecture",
        "Architected enterprise software.",
    ),
    (
        "NEG_GOOGLE_CLOUD",
        "CLAIM_WW_003",
        "not a Google Cloud implementation",
        "Built Google Cloud infrastructure.",
    ),
    (
        "NEG_PRODUCTION_ML",
        "CLAIM_WW_004",
        "not production ML",
        "Built production ML systems.",
    ),
    (
        "NEG_ENTERPRISE_QA",
        "CLAIM_WW_005",
        "does not establish enterprise QA ownership",
        "Owned enterprise QA.",
    ),
    (
        "NEG_FUNDRAISING",
        "CLAIM_WW_001",
        "no measured fundraising impact of 37 percent",
        "Increased fundraising by 37%.",
    ),
    (
        "NEG_HOURS",
        "CLAIM_WW_002",
        "hours saved were not measured; 200 hours per month was not confirmed",
        "Saved 200 hours per month.",
    ),
]

for eid_suffix, base_id, evidence_fact, claim_wording in neg_cases:
    syn = make_evidence(f"EVID_{eid_suffix}", fact=evidence_fact)
    claim = base_from(base_id)
    claim["claim_id"] = f"CLAIM_{eid_suffix}"
    claim["wording"] = claim_wording
    claim["evidence_ids"] = [syn["evidence_id"]]
    claim["evidence_state"] = "VERIFIED"
    result = validate_claim(claim, index_with(syn))
    assert_semantic_blocked(result, eid_suffix)
    print(f"PASS N: negation leak blocked ({eid_suffix}).")


# ---------------------------------------------------------------------------
# Unrelated-number leakage + unsupported quantified outcomes
# ---------------------------------------------------------------------------

unrelated = make_evidence(
    "EVID_UNRELATED_37",
    fact="37 unmapped rows were recalculated during cleanup",
)
claim_unrelated = base_from("CLAIM_WW_001")
claim_unrelated["claim_id"] = "CLAIM_UNRELATED_37"
claim_unrelated["wording"] = "Increased fundraising by 37%."
claim_unrelated["evidence_ids"] = ["EVID_UNRELATED_37"]
claim_unrelated["evidence_state"] = "VERIFIED"
r_unrelated = validate_claim(claim_unrelated, index_with(unrelated))
assert_semantic_blocked(r_unrelated, "unrelated 37 rows")
print("PASS Q1: unrelated-number fundraising claim rejected.")

unsupported_outcomes = [
    ("CLAIM_Q_FUND_37", "CLAIM_WW_001", "Increased fundraising by 37%."),
    ("CLAIM_Q_HOURS_200", "CLAIM_WW_002", "Saved 200 hours/month."),
    ("CLAIM_Q_PROC_50", "CLAIM_WW_002", "Reduced processing time by 50%."),
    ("CLAIM_Q_GEN_25K", "CLAIM_WW_001", "Generated $25,000 in partner value."),
    ("CLAIM_Q_PROD_20", "CLAIM_WW_004", "Improved productivity by 20%."),
]
for claim_id, base_id, wording in unsupported_outcomes:
    claim = base_from(base_id)
    claim["claim_id"] = claim_id
    claim["wording"] = wording
    result = validate_claim(claim, EVIDENCE_INDEX)
    assert_semantic_blocked(result, claim_id)
    print(f"PASS Q2: unsupported quantified outcome rejected ({claim_id}).")


# ---------------------------------------------------------------------------
# Supported factual scope numbers still pass
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

r_pilot = validate_claim(load_real_claim("CLAIM_WW_005"), EVIDENCE_INDEX)
assert_true(r_pilot["valid_record"] is True, "ten pilot test rows claim must pass")
print("PASS 8: ten pilot test rows remains allowed (evidenced factual count).")

partners = make_evidence(
    "EVID_PARTNER_24",
    fact="The inspected workbook tracks 24 partner organizations in the partner roster.",
)
claim_partners = base_from("CLAIM_WW_001")
claim_partners["claim_id"] = "CLAIM_OK_24_PARTNERS"
claim_partners["wording"] = "Tracked 24 partner organizations in the Winter Walk roster."
claim_partners["evidence_ids"] = ["EVID_PARTNER_24"]
claim_partners["evidence_state"] = "VERIFIED"
r_partners = validate_claim(claim_partners, index_with(partners))
assert_true(
    r_partners["valid_record"] is True,
    f"24 partner organizations factual scope must pass: {r_partners['errors']}",
)
print("PASS 8b: factual scope number 24 partner organizations remains allowed.")


# ---------------------------------------------------------------------------
# Genuinely supported measured outcome can pass
# ---------------------------------------------------------------------------

measured = make_evidence(
    "EVID_FUND_12",
    fact="Fundraising increased 12% year over year.",
)
claim_measured = base_from("CLAIM_WW_001")
claim_measured["claim_id"] = "CLAIM_OK_FUND_12"
claim_measured["wording"] = "Increased fundraising by 12%."
claim_measured["evidence_ids"] = ["EVID_FUND_12"]
claim_measured["evidence_state"] = "VERIFIED"
r_measured = validate_claim(claim_measured, index_with(measured))
assert_true(
    r_measured["valid_record"] is True,
    f"genuinely supported 12% fundraising claim must pass: {r_measured['errors']}",
)
assert_true(r_measured["reusable"] is True, "approved measured outcome should be reusable")
print("PASS Q3: genuinely supported measured fundraising outcome allowed.")

neg_measured = make_evidence(
    "EVID_FUND_12_NEG",
    fact="A 37% fundraising increase was NOT measured.",
)
claim_neg_measured = base_from("CLAIM_WW_001")
claim_neg_measured["claim_id"] = "CLAIM_NEG_FUND_37_MEASURED"
claim_neg_measured["wording"] = "Increased fundraising by 37%."
claim_neg_measured["evidence_ids"] = ["EVID_FUND_12_NEG"]
claim_neg_measured["evidence_state"] = "VERIFIED"
r_neg_measured = validate_claim(claim_neg_measured, index_with(neg_measured))
assert_semantic_blocked(r_neg_measured, "negated 37% fundraising evidence")
print("PASS Q4: negated measured-outcome evidence cannot authorize quantified claim.")


# ---------------------------------------------------------------------------
# Trivial wording / formatting variants
# ---------------------------------------------------------------------------

variant_cases = [
    ("CLAIM_VAR_ENTERPRISE_SAAS", "CLAIM_WW_001", "Built an Enterprise-SaaS workflow layer."),
    (
        "CLAIM_VAR_ENTERPRISE_ARCHITECT",
        "CLAIM_WW_001",
        "Served as enterprise software architect for Winter Walk.",
    ),
    (
        "CLAIM_VAR_ML_PROD_SYSTEM",
        "CLAIM_WW_004",
        "Delivered a machine-learning production system for form intake.",
    ),
    (
        "CLAIM_VAR_ML_PIPELINE",
        "CLAIM_WW_004",
        "Operated an ML production pipeline for Evidence_Log updates.",
    ),
]
for claim_id, base_id, wording in variant_cases:
    claim = base_from(base_id)
    claim["claim_id"] = claim_id
    claim["wording"] = wording
    result = validate_claim(claim, EVIDENCE_INDEX)
    assert_semantic_blocked(result, claim_id)
    print(f"PASS V: trivial variant blocked ({claim_id}).")


# ---------------------------------------------------------------------------
# Genuine positive support for guarded capabilities still possible
# ---------------------------------------------------------------------------

positive_cases = [
    (
        "EVID_POS_GCLOUD",
        "Built and operated Google Cloud infrastructure for CSV intake.",
        ["Google Cloud"],
        "CLAIM_WW_003",
        "CLAIM_OK_GCLOUD",
        "Built Google Cloud infrastructure for Drive-folder CSV intake.",
    ),
    (
        "EVID_POS_SAAS",
        "Delivered an enterprise SaaS platform and enterprise software architecture.",
        [],
        "CLAIM_WW_001",
        "CLAIM_OK_SAAS",
        "Delivered an enterprise SaaS platform with enterprise software architecture.",
    ),
    (
        "EVID_POS_ML",
        "Built a production ML system and ML production pipeline for scoring.",
        ["production ML"],
        "CLAIM_WW_004",
        "CLAIM_OK_ML",
        "Built production ML systems and an ML production pipeline.",
    ),
    (
        "EVID_POS_QA",
        "Owned enterprise QA engineering and enterprise quality assurance for releases.",
        ["enterprise QA"],
        "CLAIM_WW_005",
        "CLAIM_OK_QA",
        "Owned enterprise QA engineering for release validation.",
    ),
]
for eid, fact, techs, base_id, claim_id, wording in positive_cases:
    syn = make_evidence(eid, fact=fact, technologies=techs)
    claim = base_from(base_id)
    claim["claim_id"] = claim_id
    claim["wording"] = wording
    claim["evidence_ids"] = [eid]
    claim["evidence_state"] = "VERIFIED"
    result = validate_claim(claim, index_with(syn))
    assert_true(
        result["valid_record"] is True,
        f"{claim_id} positively supported claim must pass: {result['errors']}",
    )
    assert_true(result["reusable"] is True, f"{claim_id} should be reusable when approved")
    print(f"PASS P: genuine positive support still allowed ({claim_id}).")


# ---------------------------------------------------------------------------
# Supported technology already present in cited Winter Walk Evidence
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
