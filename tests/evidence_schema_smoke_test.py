import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "evidence.schema.json"


with SCHEMA_PATH.open(encoding="utf-8") as f:
    schema = json.load(f)


Draft202012Validator.check_schema(schema)
print("PASS 0: evidence.schema.json is a valid Draft 2020-12 JSON Schema.")


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker()
)


# Synthetic fixture only.
# This is NOT a real experience or claim.
valid_evidence = {
    "evidence_id": "EVID_TEST_001",
    "experience_id": "EXP_TEST_001",
    "fact": "Used SQL to query structured tables for a synthetic internal report.",
    "capabilities": ["data analysis"],
    "technologies": ["SQL"],
    "evidence_state": "SUPPORTED",
    "original_source": "synthetic-fixture://evidence/EVID_TEST_001",
    "source_location": "tests/evidence_schema_smoke_test.py:valid_evidence",
    "safe_for_external_use": False,
    "notes": None
}


# Deliberately invalid.
# The Blueprint only permits VERIFIED / SUPPORTED / OBSERVED / UNKNOWN /
# CONTRADICTED for evidence_state. "PROBABLE" must never be accepted.
invalid_state_evidence = valid_evidence.copy()
invalid_state_evidence["evidence_id"] = "EVID_TEST_002"
invalid_state_evidence["evidence_state"] = "PROBABLE"


# Deliberately invalid: omit a required field.
missing_required_evidence = valid_evidence.copy()
missing_required_evidence["evidence_id"] = "EVID_TEST_003"
del missing_required_evidence["fact"]


# Deliberately invalid: unexpected additional property.
extra_property_evidence = valid_evidence.copy()
extra_property_evidence["evidence_id"] = "EVID_TEST_004"
extra_property_evidence["invented_field"] = "should_be_rejected"


valid_errors = list(validator.iter_errors(valid_evidence))

if valid_errors:
    print("FAIL: known-good evidence was rejected.")
    for error in valid_errors:
        print(f"  - {error.message}")
    raise SystemExit(1)

print("PASS 1: known-good evidence record was accepted.")


invalid_state_errors = list(validator.iter_errors(invalid_state_evidence))

if not invalid_state_errors:
    print("FAIL: deliberately invalid evidence_state was accepted.")
    raise SystemExit(1)

print("PASS 2: invalid evidence_state was correctly rejected.")

for error in invalid_state_errors:
    print(f"  Rejection reason: {error.message}")


missing_required_errors = list(validator.iter_errors(missing_required_evidence))

if not missing_required_errors:
    print("FAIL: evidence missing a required field was accepted.")
    raise SystemExit(1)

print("PASS 3: missing required field was correctly rejected.")

for error in missing_required_errors:
    print(f"  Rejection reason: {error.message}")


extra_property_errors = list(validator.iter_errors(extra_property_evidence))

if not extra_property_errors:
    print("FAIL: evidence with an unexpected additional property was accepted.")
    raise SystemExit(1)

print("PASS 4: unexpected additional property was correctly rejected.")

for error in extra_property_errors:
    print(f"  Rejection reason: {error.message}")


print("PASS: evidence schema behavioral smoke test completed successfully.")
