import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "requirement.schema.json"
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from schema_validation import build_draft202012_validator  # noqa: E402


validator = build_draft202012_validator(SCHEMA_PATH)


# Synthetic fixture only.
# This is NOT a real job requirement.
valid_requirement = {
    "requirement_id": "REQ_TEST_001",
    "job_id": "JOB_TEST_001",
    "text": "Use SQL to analyze structured business data.",
    "category": "DATA",
    "importance": "MANDATORY",
    "seniority_implication": None,
    "technology": ["SQL"],
    "experience_level": None,
    "domain": "Business Analytics",
    "relevance": "HIGH",
    "source_text": "Strong SQL skills required for analysis of structured business data.",
    "source_location": "Qualifications"
}


# Deliberately invalid.
# The Blueprint only permits MANDATORY / PREFERRED / UNCLEAR
# for requirement importance.
invalid_requirement = valid_requirement.copy()
invalid_requirement["requirement_id"] = "REQ_TEST_002"
invalid_requirement["importance"] = "OPTIONAL"


# Deliberately invalid: omit a required field.
missing_required_requirement = valid_requirement.copy()
missing_required_requirement["requirement_id"] = "REQ_TEST_003"
del missing_required_requirement["text"]


# Deliberately invalid: unexpected additional property.
extra_property_requirement = valid_requirement.copy()
extra_property_requirement["requirement_id"] = "REQ_TEST_004"
extra_property_requirement["invented_field"] = "should_be_rejected"


valid_errors = list(validator.iter_errors(valid_requirement))

if valid_errors:
    print("FAIL: known-good requirement was rejected.")
    for error in valid_errors:
        print(f"  - {error.message}")
    raise SystemExit(1)

print("PASS 1: known-good requirement record was accepted.")


invalid_errors = list(validator.iter_errors(invalid_requirement))

if not invalid_errors:
    print("FAIL: deliberately invalid requirement was accepted.")
    raise SystemExit(1)

print("PASS 2: invalid importance state was correctly rejected.")

for error in invalid_errors:
    print(f"  Rejection reason: {error.message}")


missing_required_errors = list(validator.iter_errors(missing_required_requirement))

if not missing_required_errors:
    print("FAIL: requirement missing a required field was accepted.")
    raise SystemExit(1)

print("PASS 3: missing required field was correctly rejected.")

for error in missing_required_errors:
    print(f"  Rejection reason: {error.message}")


extra_property_errors = list(validator.iter_errors(extra_property_requirement))

if not extra_property_errors:
    print("FAIL: requirement with an unexpected additional property was accepted.")
    raise SystemExit(1)

print("PASS 4: unexpected additional property was correctly rejected.")

for error in extra_property_errors:
    print(f"  Rejection reason: {error.message}")


print("PASS: requirement schema behavioral smoke test completed successfully.")
