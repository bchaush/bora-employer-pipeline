"""Regression tests for exact-role identity resolution (Slice 1).

Covers:
- resolve_exact_role_key requires both exact employer/system identity and
  exact requisition/opportunity identifier; either missing means unresolved.
- resolve_exact_role_key has no company/role surrogate parameters and never
  imports src/job_id.py.
- discovery_lead.py deterministically parses exact employer identity and
  exact requisition id from known ATS URL shapes and requisition text, and
  never guesses on unknown/ambiguous input.
- malformed raw-message observations raise MalformedMessageError instead of
  silently dropping or fabricating a record.

Exercises real production code -- no logic is duplicated here.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from exact_role_identity import resolve_exact_role_key  # noqa: E402
from discovery_lead import MalformedMessageError, extract_discovery_leads  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


# ======================================================================
# 1. resolve_exact_role_key requires both exact identity components.
# ======================================================================
assert_true(resolve_exact_role_key(None, "R-1") is None, "missing employer identity must stay unresolved")
assert_true(resolve_exact_role_key("WORKDAY:ACME", None) is None, "missing requisition id must stay unresolved")
assert_true(resolve_exact_role_key("", "R-1") is None, "blank employer identity must stay unresolved")
assert_true(resolve_exact_role_key("WORKDAY:ACME", "  ") is None, "blank requisition id must stay unresolved")
key = resolve_exact_role_key("WORKDAY:ACME", "R-123456")
assert_true(key == "WORKDAY:ACME::R-123456", f"unexpected exact-role key: {key!r}")
assert_true(
    resolve_exact_role_key("workday:acme", "r-123456") == key,
    "exact-role key must normalize case so the same identity always converges",
)
print("PASS 1: resolve_exact_role_key requires both exact identity components and stays unresolved otherwise.")


# ======================================================================
# 2. No company/role surrogate parameters; no src/job_id.py dependency.
# ======================================================================
params = set(inspect.signature(resolve_exact_role_key).parameters)
assert_true(
    "company" not in params and "role" not in params and "fixture_key" not in params,
    f"resolve_exact_role_key must not accept company/role/fixture_key surrogate params, got {params}",
)
import exact_role_identity as exact_role_identity_module  # noqa: E402

source_text = Path(exact_role_identity_module.__file__).read_text(encoding="utf-8")
assert_true("import job_id" not in source_text, "exact_role_identity.py must not import src/job_id.py")
assert_true("generate_job_id" not in source_text, "exact_role_identity.py must not call generate_job_id")
assert_true(not hasattr(exact_role_identity_module, "job_id"), "exact_role_identity module must not expose a job_id binding")
print("PASS 2: resolve_exact_role_key carries no company/role surrogate and never depends on src/job_id.py.")


# ======================================================================
# 3. Deterministic ATS identity + requisition parsing from discovery_lead.py.
# ======================================================================
def _one_lead(discovery_url, requisition_text=None, employer_text="Acme Corp", role_text="Engineer"):
    raw_message = {
        "source": "GMAIL",
        "source_message_id": "MSG_TEST_1",
        "source_thread_id": None,
        "observed_at": "2026-09-20T09:00:00+00:00",
        "postings": [
            {
                "employer_text": employer_text,
                "role_text": role_text,
                "discovery_url": discovery_url,
                "requisition_text": requisition_text,
            }
        ],
    }
    leads = extract_discovery_leads(raw_message)
    assert_true(len(leads) == 1, "expected exactly one lead for one posting")
    return leads[0]

workday_lead = _one_lead("https://acme.myworkdayjobs.com/en-US/Acme/job/Remote/Engineer_R-123456")
assert_true(workday_lead["exact_employer_identity"] == "WORKDAY:ACME", workday_lead["exact_employer_identity"])
assert_true(workday_lead["exact_requisition_id"] == "R-123456", workday_lead["exact_requisition_id"])
assert_true(workday_lead["identity_resolution_status"] == "RESOLVED", "well-formed Workday lead must resolve")

greenhouse_lead = _one_lead("https://boards.greenhouse.io/acme/jobs/1234567")
assert_true(greenhouse_lead["exact_employer_identity"] == "GREENHOUSE:ACME", greenhouse_lead["exact_employer_identity"])
assert_true(greenhouse_lead["exact_requisition_id"] == "1234567", greenhouse_lead["exact_requisition_id"])

lever_lead = _one_lead("https://jobs.lever.co/acme/11111111-2222-3333-4444-555555555555")
assert_true(lever_lead["exact_employer_identity"] == "LEVER:ACME", lever_lead["exact_employer_identity"])
assert_true(
    lever_lead["exact_requisition_id"] == "11111111-2222-3333-4444-555555555555",
    lever_lead["exact_requisition_id"],
)

text_only_lead = _one_lead(None, requisition_text="Req ID: R-777777")
assert_true(text_only_lead["exact_requisition_id"] == "R-777777", text_only_lead["exact_requisition_id"])
assert_true(text_only_lead["exact_employer_identity"] is None, "unknown/absent URL must leave employer identity unresolved")
assert_true(text_only_lead["identity_resolution_status"] == "VERIFICATION_REQUIRED", "missing employer identity must stay VERIFICATION_REQUIRED")

required_text_lead = _one_lead(
    "https://beta.myworkdayjobs.com/en-US/Beta/job/Remote/Data-Analyst",
    requisition_text="Required qualifications include SQL and Python",
)
assert_true(required_text_lead["exact_requisition_id"] is None, "ordinary word 'Required' must never fabricate a requisition id")
assert_true(required_text_lead["identity_resolution_status"] == "VERIFICATION_REQUIRED", "ordinary prose must stay unresolved")

job_title_lead = _one_lead(
    "https://beta.myworkdayjobs.com/en-US/Beta/job/Remote/Data-Analyst",
    requisition_text="Job Title: Data Analyst",
)
assert_true(job_title_lead["exact_requisition_id"] is None, "Job Title text must never fabricate a requisition id")

ambiguous_text_lead = _one_lead(
    "https://beta.myworkdayjobs.com/en-US/Beta/job/Remote/Data-Analyst",
    requisition_text="Req ID: R-1111 and Job ID: R-2222",
)
assert_true(ambiguous_text_lead["exact_requisition_id"] is None, "two distinct explicit requisition tokens must stay ambiguous")
assert_true(ambiguous_text_lead["identity_resolution_status"] == "VERIFICATION_REQUIRED", "ambiguous requisition text must stay unresolved")

url_with_prose_lead = _one_lead(
    "https://acme.myworkdayjobs.com/en-US/Acme/job/Remote/Engineer_R-123456",
    requisition_text="Job Title: Engineer; Required qualifications include Python",
)
assert_true(url_with_prose_lead["exact_requisition_id"] == "R-123456", "ordinary prose must not pollute a valid URL requisition")

unknown_ats_lead = _one_lead("https://example.com/careers/engineer")
assert_true(unknown_ats_lead["exact_employer_identity"] is None, "unknown ATS host must never guess an employer identity")
assert_true(unknown_ats_lead["identity_resolution_status"] == "VERIFICATION_REQUIRED", "unknown ATS shape must stay VERIFICATION_REQUIRED")
print("PASS 3: exact identity parsing is fail-closed for ordinary prose, ambiguity, unknown ATS shapes, and polluted text.")


# ======================================================================
# 4. Malformed raw-message observations fail visibly, never silently.
# ======================================================================
try:
    extract_discovery_leads({"source": "GMAIL", "source_message_id": "MSG_BAD", "observed_at": "not-a-date", "postings": [{}]})
    assert_true(False, "invalid observed_at must raise MalformedMessageError")
except MalformedMessageError as exc:
    assert_true(exc.error_code == "INVALID_OBSERVED_AT", f"unexpected error_code: {exc.error_code}")

try:
    extract_discovery_leads({"source": "GMAIL", "source_message_id": "MSG_BAD_TZ", "observed_at": "2026-09-20T09:00:00", "postings": [{}]})
    assert_true(False, "timezone-naive observed_at must raise MalformedMessageError")
except MalformedMessageError as exc:
    assert_true(exc.error_code == "INVALID_OBSERVED_AT", f"unexpected error_code: {exc.error_code}")

try:
    extract_discovery_leads({"source": "GMAIL", "source_message_id": "MSG_BAD2", "observed_at": "2026-09-20T09:00:00+00:00", "postings": []})
    assert_true(False, "empty postings must raise MalformedMessageError")
except MalformedMessageError as exc:
    assert_true(exc.error_code == "UNSUPPORTED_MESSAGE_STRUCTURE", f"unexpected error_code: {exc.error_code}")

try:
    extract_discovery_leads({"source": "UNKNOWN_SOURCE", "source_message_id": "MSG_BAD3", "observed_at": "2026-09-20T09:00:00+00:00", "postings": [{}]})
    assert_true(False, "unsupported source must raise MalformedMessageError")
except MalformedMessageError as exc:
    assert_true(exc.error_code == "UNSUPPORTED_SOURCE", f"unexpected error_code: {exc.error_code}")
print("PASS 4: malformed raw-message observations raise MalformedMessageError with a stable error_code instead of silently dropping input.")

print("ALL exact_role_identity_v1_test CHECKS PASSED")
