import json
from pathlib import Path
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "job.schema.json"


with SCHEMA_PATH.open(encoding="utf-8") as f:
    schema = json.load(f)


# jsonschema's default FormatChecker omits "uri" unless optional format
# extras are installed. Register a stdlib checker so format: "uri" on
# official_url / discovery_url is actually enforced in this smoke test.
format_checker = FormatChecker()


@format_checker.checks("uri")
def is_uri(instance):
    if not isinstance(instance, str):
        return True
    parsed = urlparse(instance)
    return bool(parsed.scheme and parsed.scheme.isalpha() and (parsed.netloc or parsed.path))


validator = Draft202012Validator(
    schema,
    format_checker=format_checker
)


# Synthetic fixture only.
# This is NOT a real employer or job posting.
valid_job = {
    "job_id": "JOB_TEST_001",
    "company": "Synthetic Test Company",
    "role": "Implementation Analyst",
    "official_url": None,
    "discovery_url": None,
    "location": "Boston, MA",
    "work_arrangement": "HYBRID",
    "employment_type": "FULL_TIME",
    "discovered_date": "2026-08-24",
    "date_first_seen": "2026-08-25",
    "date_last_verified": "2026-08-25",
    "role_status": "UNCLEAR",
    "source_verification_status": "UNKNOWN",
    "role_family": "Implementation",
    "seniority": "Entry / Early Career",
    "jd_snapshot": "Synthetic job-description text used only to test schema behavior.",
    "work_authorization_wording": None,
    "opt_flag": "UNKNOWN",
    "e_verify_result": "UNKNOWN",
    "evidence_matches": [],
    "major_gaps": [],
    "lane": "UNASSIGNED",
    "decision": "UNDECIDED",
    "resume_version": None,
    "network_action": None,
    "application_status": "NOT_STARTED",
    "outcome": "UNKNOWN"
}


# Deliberately invalid.
# "NOT_ENROLLED" is intentionally forbidden because absence from the
# public E-Verify search must never be converted into a claim that an
# employer is not enrolled.
invalid_e_verify_job = valid_job.copy()
invalid_e_verify_job["job_id"] = "JOB_TEST_002"
invalid_e_verify_job["e_verify_result"] = "NOT_ENROLLED"


# Deliberately invalid: omit a required field.
missing_required_job = valid_job.copy()
missing_required_job["job_id"] = "JOB_TEST_003"
del missing_required_job["discovered_date"]


# Deliberately invalid: unexpected additional property.
extra_property_job = valid_job.copy()
extra_property_job["job_id"] = "JOB_TEST_004"
extra_property_job["invented_field"] = "should_be_rejected"


# Deliberately invalid: official_url / discovery_url must be URI or null.
invalid_url_job = valid_job.copy()
invalid_url_job["job_id"] = "JOB_TEST_005"
invalid_url_job["official_url"] = "not-a-valid-uri"
invalid_url_job["discovery_url"] = "also-not-a-valid-uri"


# Deliberately invalid: date fields must use YYYY-MM-DD.
invalid_date_job = valid_job.copy()
invalid_date_job["job_id"] = "JOB_TEST_006"
invalid_date_job["discovered_date"] = "08/24/2026"
invalid_date_job["date_first_seen"] = "25-08-2026"
invalid_date_job["date_last_verified"] = "August 25, 2026"


# Independent axes: source verification and role freshness must both be
# independently valid. This combination is intentionally allowed.
independent_axes_job = valid_job.copy()
independent_axes_job["job_id"] = "JOB_TEST_007"
independent_axes_job["source_verification_status"] = "SOURCE_VERIFICATION_REQUIRED"
independent_axes_job["role_status"] = "POSSIBLY_STALE"


# Deliberately invalid: SOURCE_VERIFICATION_REQUIRED belongs on
# source_verification_status, not role_status.
invalid_role_status_job = valid_job.copy()
invalid_role_status_job["job_id"] = "JOB_TEST_008"
invalid_role_status_job["role_status"] = "SOURCE_VERIFICATION_REQUIRED"


valid_errors = list(validator.iter_errors(valid_job))

if valid_errors:
    print("FAIL: known-good job was rejected.")
    for error in valid_errors:
        print(f"  - {error.message}")
    raise SystemExit(1)

print("PASS 1: known-good job record was accepted.")


invalid_e_verify_errors = list(validator.iter_errors(invalid_e_verify_job))

if not invalid_e_verify_errors:
    print("FAIL: deliberately invalid E-Verify state was accepted.")
    raise SystemExit(1)

print("PASS 2: invalid E-Verify state was correctly rejected.")

for error in invalid_e_verify_errors:
    print(f"  Rejection reason: {error.message}")


missing_required_errors = list(validator.iter_errors(missing_required_job))

if not missing_required_errors:
    print("FAIL: job missing a required field was accepted.")
    raise SystemExit(1)

print("PASS 3: missing required field was correctly rejected.")

for error in missing_required_errors:
    print(f"  Rejection reason: {error.message}")


extra_property_errors = list(validator.iter_errors(extra_property_job))

if not extra_property_errors:
    print("FAIL: job with an unexpected additional property was accepted.")
    raise SystemExit(1)

print("PASS 4: unexpected additional property was correctly rejected.")

for error in extra_property_errors:
    print(f"  Rejection reason: {error.message}")


invalid_url_errors = list(validator.iter_errors(invalid_url_job))

if not invalid_url_errors:
    print("FAIL: job with invalid official_url/discovery_url format was accepted.")
    raise SystemExit(1)

print("PASS 5: invalid official_url/discovery_url format was correctly rejected.")

for error in invalid_url_errors:
    print(f"  Rejection reason: {error.message}")


invalid_date_errors = list(validator.iter_errors(invalid_date_job))

if not invalid_date_errors:
    print("FAIL: job with invalid date format was accepted.")
    raise SystemExit(1)

print("PASS 6: invalid date format was correctly rejected.")

for error in invalid_date_errors:
    print(f"  Rejection reason: {error.message}")


independent_axes_errors = list(validator.iter_errors(independent_axes_job))

if independent_axes_errors:
    print("FAIL: independent source-verification and role-status combination was rejected.")
    for error in independent_axes_errors:
        print(f"  - {error.message}")
    raise SystemExit(1)

print("PASS 7: SOURCE_VERIFICATION_REQUIRED with POSSIBLY_STALE was accepted.")


invalid_role_status_errors = list(validator.iter_errors(invalid_role_status_job))

if not invalid_role_status_errors:
    print("FAIL: SOURCE_VERIFICATION_REQUIRED in role_status was accepted.")
    raise SystemExit(1)

print("PASS 8: SOURCE_VERIFICATION_REQUIRED in role_status was correctly rejected.")

for error in invalid_role_status_errors:
    print(f"  Rejection reason: {error.message}")


print("PASS: job schema behavioral smoke test completed successfully.")
