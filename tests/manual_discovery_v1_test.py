"""Focused regression for MANUAL_DISCOVERY_V1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from manual_discovery import (  # noqa: E402
    MalformedManualDiscoveryError,
    build_manual_discovery_observation,
    process_manual_nomination,
)
from production_ledger import empty_state, state_from_ledger_rows  # noqa: E402
from supervised_ingestion import process_batch  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


WORKDAY_URL = (
    "https://acme.myworkdayjobs.com/en-US/Acme/job/Remote/"
    "Software-Engineer_R-123456"
)
EXPECTED_JOB_ID = "WORKDAY:ACME::R-123456"

# 1. Manual URL uses the existing DiscoveryLead -> ledger conveyor.
manual = build_manual_discovery_observation(
    source="MANUAL_URL",
    observed_at="2026-09-27T20:00:00-04:00",
    discovery_url=WORKDAY_URL,
    employer_text="Acme Corp",
    role_text="Software Engineer",
    source_claims={"source_provider": "DIRECT_URL"},
)
plan = process_manual_nomination(
    existing_state=empty_state(),
    run_id="MANUAL_V1_URL_001",
    processed_at="2026-09-27T20:01:00-04:00",
    source="MANUAL_URL",
    observed_at="2026-09-27T20:00:00-04:00",
    discovery_url=WORKDAY_URL,
    employer_text="Acme Corp",
    role_text="Software Engineer",
    source_claims={"source_provider": "DIRECT_URL"},
)
check(
    EXPECTED_JOB_ID in plan["next_state"]["jobs"],
    "manual URL exact ATS identity must reuse the existing canonical exact-role key",
)
job = plan["next_state"]["jobs"][EXPECTED_JOB_ID]
check(job["Discovery_Source"] == "MANUAL_URL", "manual source provenance must persist")
check(job["Discovery_URL"] == WORKDAY_URL, "manual discovery URL must persist")
for forbidden in (
    "Freshness_State",
    "Geography_State",
    "OPT_Screen_State",
    "Candidate_Condition_State",
    "Threshold_State",
    "Match_State",
    "Decision",
    "Bora_Decision",
    "Package_Status",
    "Application_Status",
):
    check(forbidden not in job, f"manual intake must not manufacture {forbidden}")
print("PASS 1: manual URL enters the existing exact-identity/JOBS conveyor without manufacturing truth.")

# 2. Exact same manual URL is idempotent after durable rehydration.
durable = state_from_ledger_rows(
    list(plan["next_state"]["jobs"].values()),
    plan["log_mutations"],
)
rerun = process_batch(
    [manual],
    durable,
    run_id="MANUAL_V1_URL_002",
    processed_at="2026-09-27T21:00:00-04:00",
)
check(rerun["jobs_mutations"] == [], "same manual URL rerun must not duplicate JOBS")
check(rerun["log_mutations"] == [], "same manual URL rerun must not duplicate LOG")
print("PASS 2: exact repeated manual URL is idempotent.")

# 3. Gmail + manual nomination of the same exact requisition converge.
gmail = {
    "source": "GMAIL",
    "source_message_id": "MANUAL_V1_GMAIL_001",
    "source_thread_id": "MANUAL_V1_GMAIL_THREAD",
    "observed_at": "2026-09-27T19:00:00-04:00",
    "postings": [
        {
            "employer_text": "Acme Corp",
            "role_text": "Software Engineer",
            "requisition_text": None,
            "discovery_url": WORKDAY_URL,
            "source_claims": {"source_provider": "EMAIL_ALERT"},
        }
    ],
}
cross = process_batch(
    [gmail, manual],
    empty_state(),
    run_id="MANUAL_V1_CROSS_SOURCE",
    processed_at="2026-09-27T20:05:00-04:00",
)
same_job_mutations = [
    mutation
    for mutation in cross["jobs_mutations"]
    if mutation["Job_ID"] == EXPECTED_JOB_ID
]
check(
    len(same_job_mutations) == 2
    and {m["Op"] for m in same_job_mutations} == {"CREATE", "UPDATE"},
    "Gmail and manual observations must converge on one existing exact-role entity",
)
check(
    set(cross["next_state"]["jobs"]) == {EXPECTED_JOB_ID},
    "cross-source nomination must not create a parallel manual entity",
)
log_sources = {
    row["Source"]
    for row in cross["log_mutations"]
    if row["Job_ID"] == EXPECTED_JOB_ID
}
check(
    log_sources == {"GMAIL", "MANUAL_URL"},
    f"both source observations must remain auditable, got {log_sources}",
)
print("PASS 3: Gmail and manual nominations converge through the same dedupe path.")

# 4. Screenshot/private-board intake may have no URL and must fail closed to verification.
screenshot = build_manual_discovery_observation(
    source="MANUAL_SCREENSHOT",
    source_reference="sha256:manual-v1-example-image",
    observed_at="2026-09-27T20:10:00-04:00",
    employer_text="Example Employer",
    role_text="Business Analyst",
    source_claims={"source_provider": "PRIVATE_BOARD"},
)
screen_plan = process_batch(
    [screenshot],
    empty_state(),
    run_id="MANUAL_V1_SCREENSHOT",
    processed_at="2026-09-27T20:11:00-04:00",
)
check(screen_plan["jobs_mutations"] == [], "screenshot without exact identity must not create JOBS")
check(len(screen_plan["log_mutations"]) == 1, "screenshot hold must remain visible")
screen_log = screen_plan["log_mutations"][0]
check(screen_log["Status"] == "VERIFICATION_REQUIRED", "screenshot must fail closed")
check(screen_log["Source"] == "MANUAL_SCREENSHOT", "screenshot source must persist")
screen_notes = json.loads(screen_log["Notes"])
check(
    screen_notes["source_claims"] == {
        "source_provider": "PRIVATE_BOARD",
        "manual_source_reference": "sha256:manual-v1-example-image",
    },
    "screenshot source claims must preserve the opaque manual source reference as untrusted provenance",
)
print("PASS 4: screenshot/private-board nomination remains visible, reconstructable, and VERIFICATION_REQUIRED.")

# 5. Same screenshot source reference has stable source identity.
screenshot_again = build_manual_discovery_observation(
    source="MANUAL_SCREENSHOT",
    source_reference="sha256:manual-v1-example-image",
    observed_at="2026-09-27T22:10:00-04:00",
    employer_text="Example Employer",
    role_text="Business Analyst",
)
check(
    screenshot["source_message_id"] == screenshot_again["source_message_id"],
    "same screenshot reference must yield stable source identity",
)
print("PASS 5: screenshot source identity is stable across re-observation.")

# 6. Third-party manual URL remains discovery-only and cannot create canonical identity.
third_party = build_manual_discovery_observation(
    source="MANUAL_URL",
    observed_at="2026-09-27T20:20:00-04:00",
    discovery_url="https://www.linkedin.com/jobs/view/4470043526",
    employer_text="Peraton",
    role_text="Junior Business Analyst",
    requisition_text="Job ID 4470043526",
    source_claims={"source_provider": "LINKEDIN"},
)
third_party_plan = process_batch(
    [third_party],
    empty_state(),
    run_id="MANUAL_V1_THIRD_PARTY",
    processed_at="2026-09-27T20:21:00-04:00",
)
check(
    third_party_plan["jobs_mutations"] == [],
    "third-party URL/platform ID must not directly create canonical JOBS identity",
)
check(
    third_party_plan["log_mutations"][0]["Status"] == "VERIFICATION_REQUIRED",
    "third-party manual nomination must proceed to first-party verification",
)
print("PASS 6: discovery-platform URL/ID remains nomination-only.")

# 7. Malformed bounded manual input retains manual source in visible PROCESSING_ERROR.
bad_time = build_manual_discovery_observation(
    source="MANUAL_URL",
    observed_at="2026-09-27T20:30:00",
    discovery_url=WORKDAY_URL,
)
bad_plan = process_batch(
    [bad_time],
    empty_state(),
    run_id="MANUAL_V1_BAD_TIME",
    processed_at="2026-09-27T20:31:00-04:00",
)
check(
    len(bad_plan["log_mutations"]) == 1
    and bad_plan["log_mutations"][0]["Status"] == "PROCESSING_ERROR"
    and bad_plan["log_mutations"][0]["Error_Code"] == "INVALID_OBSERVED_AT"
    and bad_plan["log_mutations"][0]["Source"] == "MANUAL_URL",
    "malformed manual observation must fail visibly without being relabeled Gmail",
)
print("PASS 7: malformed manual bounded input remains a visible manual-source processing error.")

# 8. Adapter boundary rejects invalid manual URL and missing screenshot reference explicitly.
try:
    build_manual_discovery_observation(
        source="MANUAL_URL",
        observed_at="2026-09-27T20:40:00-04:00",
        discovery_url="javascript:alert(1)",
    )
except MalformedManualDiscoveryError as exc:
    check(exc.error_code == "INVALID_DISCOVERY_URL", f"unexpected error: {exc.error_code}")
else:
    raise AssertionError("invalid manual URL must fail explicitly")

try:
    build_manual_discovery_observation(
        source="MANUAL_SCREENSHOT",
        observed_at="2026-09-27T20:40:00-04:00",
    )
except MalformedManualDiscoveryError as exc:
    check(exc.error_code == "MISSING_SOURCE_REFERENCE", f"unexpected error: {exc.error_code}")
else:
    raise AssertionError("screenshot without stable source_reference must fail explicitly")

print("PASS 8: malformed adapter inputs fail explicitly.")
print("ALL MANUAL_DISCOVERY_V1 CHECKS PASSED")
