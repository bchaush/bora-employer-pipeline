import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "job.schema.json"
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from schema_validation import build_draft202012_validator  # noqa: E402


# Shared Draft 2020-12 validator always includes job-url format enforcement.
validator = build_draft202012_validator(SCHEMA_PATH)


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


# Deliberately invalid enum values for locked vocabularies.
invalid_source_verification_job = valid_job.copy()
invalid_source_verification_job["job_id"] = "JOB_TEST_009"
invalid_source_verification_job["source_verification_status"] = "UNVERIFIED"

invalid_careers_page_status_job = valid_job.copy()
invalid_careers_page_status_job["job_id"] = "JOB_TEST_010"
invalid_careers_page_status_job["careers_page_status"] = "CHECKED"

invalid_immigration_verification_job = valid_job.copy()
invalid_immigration_verification_job["job_id"] = "JOB_TEST_011"
invalid_immigration_verification_job["immigration_verification_status"] = "HR_CONFIRMATION_NEEDED"

invalid_initial_opt_relevance_job = valid_job.copy()
invalid_initial_opt_relevance_job["job_id"] = "JOB_TEST_012"
invalid_initial_opt_relevance_job["initial_opt_relevance"] = "HIGH"

invalid_future_stem_quality_job = valid_job.copy()
invalid_future_stem_quality_job["job_id"] = "JOB_TEST_013"
invalid_future_stem_quality_job["future_stem_quality"] = "EXCELLENT"

invalid_opt_flag_job = valid_job.copy()
invalid_opt_flag_job["job_id"] = "JOB_TEST_014"
invalid_opt_flag_job["opt_flag"] = "RELEVANT"


# Focused negative URL cases for the shared http/https job URL checker.
invalid_ftp_url_job = valid_job.copy()
invalid_ftp_url_job["job_id"] = "JOB_TEST_015"
invalid_ftp_url_job["official_url"] = "ftp://example.com"

invalid_mailto_url_job = valid_job.copy()
invalid_mailto_url_job["job_id"] = "JOB_TEST_016"
invalid_mailto_url_job["official_url"] = "mailto:hr@example.com"

invalid_javascript_url_job = valid_job.copy()
invalid_javascript_url_job["job_id"] = "JOB_TEST_017"
invalid_javascript_url_job["official_url"] = "javascript:alert(1)"

invalid_whitespace_url_job = valid_job.copy()
invalid_whitespace_url_job["job_id"] = "JOB_TEST_018"
invalid_whitespace_url_job["official_url"] = "https://example.com/careers page"


# Positive: valid percent-encoded path characters remain allowed.
percent_encoded_url_job = valid_job.copy()
percent_encoded_url_job["job_id"] = "JOB_TEST_019"
percent_encoded_url_job["official_url"] = "https://example.com/careers%20page"
percent_encoded_url_job["discovery_url"] = "https://jobs.example.com/search%3Fq%3Danalyst"


# Negative: embedded username/password credentials must be rejected.
credential_url_job = valid_job.copy()
credential_url_job["job_id"] = "JOB_TEST_020"
credential_url_job["official_url"] = "https://user:pass@example.com/careers"


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


invalid_source_verification_errors = list(
    validator.iter_errors(invalid_source_verification_job)
)

if not invalid_source_verification_errors:
    print("FAIL: invalid source_verification_status was accepted.")
    raise SystemExit(1)

print("PASS 9: invalid source_verification_status was correctly rejected.")

for error in invalid_source_verification_errors:
    print(f"  Rejection reason: {error.message}")


invalid_careers_page_status_errors = list(
    validator.iter_errors(invalid_careers_page_status_job)
)

if not invalid_careers_page_status_errors:
    print("FAIL: invalid careers_page_status was accepted.")
    raise SystemExit(1)

print("PASS 10: invalid careers_page_status was correctly rejected.")

for error in invalid_careers_page_status_errors:
    print(f"  Rejection reason: {error.message}")


invalid_immigration_verification_errors = list(
    validator.iter_errors(invalid_immigration_verification_job)
)

if not invalid_immigration_verification_errors:
    print("FAIL: invalid immigration_verification_status was accepted.")
    raise SystemExit(1)

print("PASS 11: invalid immigration_verification_status was correctly rejected.")

for error in invalid_immigration_verification_errors:
    print(f"  Rejection reason: {error.message}")


invalid_initial_opt_relevance_errors = list(
    validator.iter_errors(invalid_initial_opt_relevance_job)
)

if not invalid_initial_opt_relevance_errors:
    print("FAIL: invalid initial_opt_relevance was accepted.")
    raise SystemExit(1)

print("PASS 12: invalid initial_opt_relevance was correctly rejected.")

for error in invalid_initial_opt_relevance_errors:
    print(f"  Rejection reason: {error.message}")


invalid_future_stem_quality_errors = list(
    validator.iter_errors(invalid_future_stem_quality_job)
)

if not invalid_future_stem_quality_errors:
    print("FAIL: invalid future_stem_quality was accepted.")
    raise SystemExit(1)

print("PASS 13: invalid future_stem_quality was correctly rejected.")

for error in invalid_future_stem_quality_errors:
    print(f"  Rejection reason: {error.message}")


invalid_opt_flag_errors = list(validator.iter_errors(invalid_opt_flag_job))

if not invalid_opt_flag_errors:
    print("FAIL: invalid opt_flag was accepted.")
    raise SystemExit(1)

print("PASS 14: invalid opt_flag was correctly rejected.")

for error in invalid_opt_flag_errors:
    print(f"  Rejection reason: {error.message}")


invalid_ftp_url_errors = list(validator.iter_errors(invalid_ftp_url_job))

if not invalid_ftp_url_errors:
    print("FAIL: ftp URL was accepted.")
    raise SystemExit(1)

print("PASS 15: ftp URL was correctly rejected.")

for error in invalid_ftp_url_errors:
    print(f"  Rejection reason: {error.message}")


invalid_mailto_url_errors = list(validator.iter_errors(invalid_mailto_url_job))

if not invalid_mailto_url_errors:
    print("FAIL: mailto URL was accepted.")
    raise SystemExit(1)

print("PASS 16: mailto URL was correctly rejected.")

for error in invalid_mailto_url_errors:
    print(f"  Rejection reason: {error.message}")


invalid_javascript_url_errors = list(
    validator.iter_errors(invalid_javascript_url_job)
)

if not invalid_javascript_url_errors:
    print("FAIL: javascript URL was accepted.")
    raise SystemExit(1)

print("PASS 17: javascript URL was correctly rejected.")

for error in invalid_javascript_url_errors:
    print(f"  Rejection reason: {error.message}")


invalid_whitespace_url_errors = list(
    validator.iter_errors(invalid_whitespace_url_job)
)

if not invalid_whitespace_url_errors:
    print("FAIL: whitespace-containing URL was accepted.")
    raise SystemExit(1)

print("PASS 18: whitespace-containing URL was correctly rejected.")

for error in invalid_whitespace_url_errors:
    print(f"  Rejection reason: {error.message}")


percent_encoded_url_errors = list(validator.iter_errors(percent_encoded_url_job))

if percent_encoded_url_errors:
    print("FAIL: valid percent-encoded job URL was rejected.")
    for error in percent_encoded_url_errors:
        print(f"  - {error.message}")
    raise SystemExit(1)

print("PASS 19: percent-encoded job URL was accepted.")


credential_url_errors = list(validator.iter_errors(credential_url_job))

if not credential_url_errors:
    print("FAIL: credential-bearing job URL was accepted.")
    raise SystemExit(1)

print("PASS 20: credential-bearing job URL was correctly rejected.")

for error in credential_url_errors:
    print(f"  Rejection reason: {error.message}")


print("PASS: job schema behavioral smoke test completed successfully.")
