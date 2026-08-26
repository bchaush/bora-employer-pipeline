import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "requirement.schema.json"


with SCHEMA_PATH.open(encoding="utf-8") as f:
    schema = json.load(f)


validator = Draft202012Validator(
    schema,
    format_checker=FormatChecker()
)


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


print("PASS: requirement schema behavioral smoke test completed successfully.")