import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "claim.schema.json"
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from schema_validation import build_draft202012_validator  # noqa: E402


validator = build_draft202012_validator(SCHEMA_PATH)


# Synthetic fixture only.
# This is NOT a real approved claim about Bora.
valid_claim = {
    "claim_id": "CLAIM_TEST_001",
    "wording": "Used SQL to analyze structured tables for an internal synthetic report.",
    "evidence_ids": ["EVID_TEST_001"],
    "evidence_state": "SUPPORTED",
    "allowed_contexts": ["resume"],
    "forbidden_contexts": [],
    "human_approval": True,
    "date": "2026-08-26",
    "version": "1"
}


# Deliberately invalid: Evidence_ID list omitted.
missing_evidence_ids_claim = valid_claim.copy()
missing_evidence_ids_claim["claim_id"] = "CLAIM_TEST_002"
del missing_evidence_ids_claim["evidence_ids"]


# Deliberately invalid: empty Evidence_ID list is forbidden.
empty_evidence_ids_claim = valid_claim.copy()
empty_evidence_ids_claim["claim_id"] = "CLAIM_TEST_003"
empty_evidence_ids_claim["evidence_ids"] = []


# Deliberately invalid: evidence_state must use locked Blueprint states only.
invalid_evidence_state_claim = valid_claim.copy()
invalid_evidence_state_claim["claim_id"] = "CLAIM_TEST_004"
invalid_evidence_state_claim["evidence_state"] = "PROBABLE"


# Deliberately invalid: omit a required field.
missing_required_claim = valid_claim.copy()
missing_required_claim["claim_id"] = "CLAIM_TEST_005"
del missing_required_claim["wording"]


# Deliberately invalid: unexpected additional property.
extra_property_claim = valid_claim.copy()
extra_property_claim["claim_id"] = "CLAIM_TEST_006"
extra_property_claim["invented_field"] = "should_be_rejected"


valid_errors = list(validator.iter_errors(valid_claim))

if valid_errors:
    print("FAIL: known-good claim was rejected.")
    for error in valid_errors:
        print(f"  - {error.message}")
    raise SystemExit(1)

print("PASS 1: known-good claim record was accepted.")


missing_evidence_ids_errors = list(validator.iter_errors(missing_evidence_ids_claim))

if not missing_evidence_ids_errors:
    print("FAIL: claim missing Evidence_ID list was accepted.")
    raise SystemExit(1)

print("PASS 2: missing Evidence_ID list was correctly rejected.")

for error in missing_evidence_ids_errors:
    print(f"  Rejection reason: {error.message}")


empty_evidence_ids_errors = list(validator.iter_errors(empty_evidence_ids_claim))

if not empty_evidence_ids_errors:
    print("FAIL: claim with empty Evidence_ID list was accepted.")
    raise SystemExit(1)

print("PASS 3: empty Evidence_ID list was correctly rejected.")

for error in empty_evidence_ids_errors:
    print(f"  Rejection reason: {error.message}")


invalid_evidence_state_errors = list(
    validator.iter_errors(invalid_evidence_state_claim)
)

if not invalid_evidence_state_errors:
    print("FAIL: invalid evidence_state was accepted.")
    raise SystemExit(1)

print("PASS 4: invalid evidence_state was correctly rejected.")

for error in invalid_evidence_state_errors:
    print(f"  Rejection reason: {error.message}")


missing_required_errors = list(validator.iter_errors(missing_required_claim))

if not missing_required_errors:
    print("FAIL: claim missing a required field was accepted.")
    raise SystemExit(1)

print("PASS 5: missing required field was correctly rejected.")

for error in missing_required_errors:
    print(f"  Rejection reason: {error.message}")


extra_property_errors = list(validator.iter_errors(extra_property_claim))

if not extra_property_errors:
    print("FAIL: claim with an unexpected additional property was accepted.")
    raise SystemExit(1)

print("PASS 6: unexpected additional property was correctly rejected.")

for error in extra_property_errors:
    print(f"  Rejection reason: {error.message}")


print("PASS: claim schema behavioral smoke test completed successfully.")
