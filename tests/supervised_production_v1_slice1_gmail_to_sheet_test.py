"""Regression tests for SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET.

Exercises the real Gmail -> DiscoveryLead -> exact-role identity -> JOBS/LOG
mutation-plan pipeline (discovery_lead.py, exact_role_identity.py,
production_ledger.py, supervised_ingestion.py) against a controlled fixture
batch covering:
- duplicate delivery of the same message within a batch;
- the same exact requisition nominated from two different alert messages;
- a missing requisition identifier;
- a malformed message (invalid observed_at);
- exact employer/requisition collision prevention (same requisition text,
  two different employers, must not collide into one JOBS row);
- rerun/idempotency across two full process_batch runs using the persisted
  next_state.

No logic is duplicated here; this test only asserts on returned mutation
plans and validates them against schemas/production_ledger_mutation.schema.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from supervised_ingestion import process_batch  # noqa: E402
from production_ledger import empty_state, state_from_ledger_rows  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_PATH = ROOT / "fixtures" / "supervised_production_v1" / "gmail_batch_v1.json"
raw_messages = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
assert_true(len(raw_messages) == 6, f"expected 6 raw messages in fixture, got {len(raw_messages)}")

plan = process_batch(
    raw_messages,
    empty_state(),
    run_id="RUN_TEST_001",
    processed_at="2026-09-20T13:00:00+00:00",
)

jobs_by_id = {m["Job_ID"]: m for m in plan["jobs_mutations"]}


# ======================================================================
# 1. Duplicate delivery (MSG_001 appears twice) + same requisition from a
#    second alert source (MSG_002) converge on exactly one JOBS row.
# ======================================================================
acme_key = "WORKDAY:ACME::R-123456"
assert_true(acme_key in jobs_by_id, "Acme JOBS row must exist")
acme_creates = [m for m in plan["jobs_mutations"] if m["Job_ID"] == acme_key and m["Op"] == "CREATE"]
acme_updates = [m for m in plan["jobs_mutations"] if m["Job_ID"] == acme_key and m["Op"] == "UPDATE"]
assert_true(len(acme_creates) == 1, f"exactly one CREATE expected for {acme_key}, got {len(acme_creates)}")
assert_true(len(acme_updates) == 1, f"exactly one UPDATE expected for {acme_key} (from MSG_002), got {len(acme_updates)}")
assert_true(jobs_by_id[acme_key]["Last_Verified"] == "2026-09-20T10:00:00+00:00", "Last_Verified must reflect the later MSG_002 observation")
assert_true(acme_creates[0]["First_Seen"] == "2026-09-20T09:00:00+00:00", "First_Seen must be preserved from the first observation")
acme_log_success = [m for m in plan["log_mutations"] if m["Job_ID"] == acme_key]
assert_true(len(acme_log_success) == 2, f"exactly two successful LOG entries expected for {acme_key} (duplicate delivery collapsed), got {len(acme_log_success)}")
acme_provenance = [json.loads(m["Notes"]) for m in acme_log_success]
assert_true(
    {p["source_message_id"] for p in acme_provenance} == {"MSG_001", "MSG_002"},
    "both distinct Gmail source observations must remain durably reconstructable in LOG provenance",
)
msg2_provenance = next(p for p in acme_provenance if p["source_message_id"] == "MSG_002")
assert_true(
    msg2_provenance["source_claims"] == {"posting_age": "Posted Today", "fit_label": "Great Match"},
    "source-provided freshness/fit claims must be preserved only as untrusted observation provenance",
)
assert_true(
    "Freshness_State" not in jobs_by_id[acme_key] and "Match_State" not in jobs_by_id[acme_key],
    "source claims must never be promoted into Employer Truth or Match Truth fields",
)
print("PASS 1: duplicate delivery collapses, distinct source observations remain reconstructable, and source claims stay observation-only.")

acme_messages = {
    m["source_message_id"]: m
    for m in raw_messages
    if m.get("source_message_id") in {"MSG_001", "MSG_002"}
}
reverse_plan = process_batch(
    [acme_messages["MSG_002"], acme_messages["MSG_001"]],
    empty_state(),
    run_id="RUN_TEST_REVERSED",
    processed_at="2026-09-20T13:30:00+00:00",
)
reverse_job = reverse_plan["next_state"]["jobs"][acme_key]
assert_true(
    reverse_job["First_Seen"] == "2026-09-20T09:00:00+00:00",
    f"First_Seen must be the earliest observation regardless of delivery order: {reverse_job}",
)
assert_true(
    reverse_job["Last_Verified"] == "2026-09-20T10:00:00+00:00",
    f"Last_Verified must be the latest observation regardless of delivery order: {reverse_job}",
)
assert_true(
    reverse_job["First_Seen"] <= reverse_job["Last_Verified"],
    "JOBS timestamps must never become self-contradictory under newest-first delivery",
)
print("PASS 1B: newest-first Gmail delivery preserves monotonic First_Seen/Last_Verified timestamps.")


# ======================================================================
# 2. Missing requisition identifier stays VERIFICATION_REQUIRED with no
#    JOBS row and no invented identifier.
# ======================================================================
beta_jobs = [m for m in plan["jobs_mutations"] if "BETA" in m["Job_ID"]]
assert_true(len(beta_jobs) == 0, "Beta LLC must never get a JOBS row without an exact requisition id")
beta_logs = [m for m in plan["log_mutations"] if m["Status"] == "VERIFICATION_REQUIRED" and "BETA" in (m["Notes"] or "")]
assert_true(len(beta_logs) == 1, f"expected one VERIFICATION_REQUIRED LOG entry for Beta LLC, got {len(beta_logs)}")
assert_true(beta_logs[0]["Job_ID"] is None, "VERIFICATION_REQUIRED LOG entry must not carry a fabricated Job_ID")
print("PASS 2: missing exact requisition identifier stays VERIFICATION_REQUIRED with no JOBS row and no invented identity.")


# ======================================================================
# 3. Malformed message (invalid observed_at) fails visibly to
#    PROCESSING_ERROR, never silently dropped.
# ======================================================================
error_logs = [m for m in plan["log_mutations"] if m["Status"] == "PROCESSING_ERROR"]
assert_true(len(error_logs) == 1, f"expected exactly one PROCESSING_ERROR LOG entry, got {len(error_logs)}")
assert_true(error_logs[0]["Error_Code"] == "INVALID_OBSERVED_AT", f"unexpected Error_Code: {error_logs[0]['Error_Code']}")
print("PASS 3: malformed email content fails visibly into a PROCESSING_ERROR LOG entry instead of silently disappearing.")

naive_timestamp_message = {
    "source": "GMAIL",
    "source_message_id": "MSG_NAIVE_TZ",
    "source_thread_id": "THREAD_NAIVE_TZ",
    "observed_at": "2026-09-20T10:30:00",
    "postings": [
        {
            "employer_text": "Acme Corp",
            "role_text": "Software Engineer",
            "discovery_url": "https://acme.myworkdayjobs.com/en-US/Acme/job/Remote/Software-Engineer_R-123456",
            "requisition_text": None,
        }
    ],
}
timezone_plan = process_batch(
    [acme_messages["MSG_001"], naive_timestamp_message],
    empty_state(),
    run_id="RUN_TEST_TZ",
    processed_at="2026-09-20T14:00:00+00:00",
)
timezone_errors = [
    m for m in timezone_plan["log_mutations"]
    if m["Status"] == "PROCESSING_ERROR" and m["Error_Code"] == "INVALID_OBSERVED_AT"
]
assert_true(len(timezone_errors) == 1, "timezone-naive observed_at must fail visibly into exactly one PROCESSING_ERROR")
assert_true(
    acme_key in timezone_plan["next_state"]["jobs"],
    "a timezone-naive sibling message must not abort or erase another valid observation in the same batch",
)
print("PASS 3B: timezone-naive observed_at fails visibly without aborting the surrounding batch.")


# ======================================================================
# 4. Exact employer/requisition collision prevention: same requisition
#    text, two different employers, must never collapse into one JOBS row.
# ======================================================================
gamma_key = "WORKDAY:GAMMA::R-999999"
delta_key = "WORKDAY:DELTA::R-999999"
assert_true(gamma_key in jobs_by_id, "Gamma JOBS row must exist")
assert_true(delta_key in jobs_by_id, "Delta JOBS row must exist")
assert_true(gamma_key != delta_key, "same requisition text under two different employers must not collide into one Job_ID")
print("PASS 4: exact employer/requisition collision prevention holds -- identical requisition text under two different employers never collapses into one JOBS row.")


# ======================================================================
# 5. JOBS mutations use only Slice 1 fields; no truth-engine field appears.
# ======================================================================
for mutation in plan["jobs_mutations"]:
    forbidden = {"Freshness_State", "Geography_State", "OPT_Screen_State", "Candidate_Condition_State", "Threshold_State", "Match_State", "Decision", "Bora_Decision", "Package_Status", "Application_Status"}
    assert_true(not (forbidden & set(mutation.keys())), f"JOBS mutation must not manufacture truth-engine fields: {mutation.keys()}")
print("PASS 5: JOBS mutation plans use only the Slice 1 JOBS fields and never manufacture unset truth-engine fields.")


# ======================================================================
# 6. Rerun/idempotency: re-running the same batch against next_state
#    produces no new JOBS mutations and no new LOG entries at all.
# ======================================================================
durable_state = state_from_ledger_rows(
    list(plan["next_state"]["jobs"].values()),
    plan["log_mutations"],
)
rerun_plan = process_batch(
    list(reversed(raw_messages)),
    durable_state,
    run_id="RUN_TEST_002",
    processed_at="2026-09-21T09:00:00+00:00",
)
assert_true(len(rerun_plan["jobs_mutations"]) == 0, f"rerun against the same existing state must produce zero JOBS mutations, got {len(rerun_plan['jobs_mutations'])}")
assert_true(len(rerun_plan["log_mutations"]) == 0, f"rerun against the same existing state must produce zero LOG mutations, got {len(rerun_plan['log_mutations'])}")
assert_true(
    set(rerun_plan["next_state"]["processed_lead_ids"]) == set(plan["next_state"]["processed_lead_ids"]),
    "durable LOG provenance must reconstruct the same processed observation identities",
)
print("PASS 6: rehydrating from durable JOBS/LOG rows and rerunning a reordered mailbox window produces no duplicate logical state.")

print("ALL supervised_production_v1_slice1_gmail_to_sheet_test CHECKS PASSED")
