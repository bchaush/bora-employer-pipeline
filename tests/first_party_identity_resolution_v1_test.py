from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from first_party_identity_resolution import (  # noqa: E402
    evaluate_first_party_identity_request,
)
from production_ledger import (  # noqa: E402
    build_first_party_identity_resolution_mutation_plan,
    state_from_ledger_rows,
)

FIXTURE = (
    ROOT
    / "fixtures"
    / "supervised_production_v1"
    / "first_party_identity_resolution_v1"
    / "production_batch_001.json"
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
requests = [
    {
        "discovery_log_record": case["discovery_log_record"],
        "first_party_observation": case["first_party_observation"],
    }
    for case in cases
]

by_id = {case["case_id"]: case for case in cases}

# 1. Production-earned positive/negative matrix.
for case, request in zip(cases, requests, strict=True):
    outcome = evaluate_first_party_identity_request(request)
    assert_true(
        outcome["outcome"] == case["expected_outcome"],
        f"{case['case_id']}: expected {case['expected_outcome']}, got {outcome}",
    )
    if case["expected_outcome"] == "RESOLVED":
        assert_true(
            outcome["operational_job_id"] == case["expected_job_id"],
            f"{case['case_id']}: exact operational Job_ID mismatch",
        )
        assert_true(
            outcome["official_url"]
            == case["first_party_observation"]["official_url"],
            f"{case['case_id']}: Official_URL must come from first-party evidence",
        )
        assert_true(
            outcome["discovery_url"]
            == json.loads(case["discovery_log_record"]["Notes"])["discovery_urls"][0],
            f"{case['case_id']}: original discovery URL provenance must be preserved",
        )
    else:
        assert_true(
            outcome["operational_job_id"] is None,
            f"{case['case_id']}: unresolved case must not create Job_ID",
        )
        assert_true(
            outcome["error_code"] == case["expected_error_code"],
            f"{case['case_id']}: fail-closed reason mismatch",
        )
print("PASS 1: production-earned MTA/Peraton/OneMain resolve; Middesk/Runlayer remain unresolved.")

# 2. Mutation plan creates exactly the three resolved JOBS rows, all NORMALIZED.
plan = build_first_party_identity_resolution_mutation_plan(
    requests,
    None,
    run_id="FPIR_TEST_001",
    processed_at="2026-09-26T13:45:00-04:00",
)
assert_true(len(plan["jobs_mutations"]) == 3, "exactly three positive JOBS rows expected")
assert_true(len(plan["log_mutations"]) == 5, "every verification attempt must be auditable in LOG")
expected_ids = {
    by_id["MTA_17407"]["expected_job_id"],
    by_id["PERATON_2026_171010"]["expected_job_id"],
    by_id["ONEMAIN_R2608_52225"]["expected_job_id"],
}
assert_true(
    {row["Job_ID"] for row in plan["jobs_mutations"]} == expected_ids,
    "positive JOBS rows must use exact employer/requisition identity only",
)
assert_true(
    all(row["Pipeline_State"] == "NORMALIZED" for row in plan["jobs_mutations"]),
    "first-party identity resolution must not invent a new pipeline state",
)
assert_true(
    all(row["Op"] == "CREATE" for row in plan["jobs_mutations"]),
    "fresh ledger should create exact-role entities",
)
negative_logs = [
    row for row in plan["log_mutations"] if row["Status"] == "VERIFICATION_REQUIRED"
]
assert_true(len(negative_logs) == 2, "Middesk and Runlayer must remain visible verification holds")
print("PASS 2: ledger projection creates only exact resolved JOBS rows and preserves unresolved holds.")

# 3. Discovery-platform IDs cannot substitute for employer requisitions.
platform_shortcut = copy.deepcopy(requests[0])
platform_shortcut["first_party_observation"]["exact_requisition_id"] = "4470047211"
platform_shortcut["first_party_observation"]["requisition_evidence"] = (
    "LinkedIn discovery job ID 4470047211"
)
platform_shortcut["first_party_observation"]["requisition_authority"] = (
    "EMPLOYER_OR_ATS_FIRST_PARTY"
)
shortcut_outcome = evaluate_first_party_identity_request(platform_shortcut)
assert_true(
    shortcut_outcome["outcome"] == "PROCESSING_ERROR"
    and shortcut_outcome["error_code"] == "DISCOVERY_PLATFORM_ID_FORBIDDEN",
    "a discovery-platform ID must never become the employer requisition",
)
third_party_shortcut = copy.deepcopy(requests[0])
third_party_shortcut["first_party_observation"]["source_kind"] = "LINKEDIN"
third_party_outcome = evaluate_first_party_identity_request(third_party_shortcut)
assert_true(
    third_party_outcome["outcome"] == "PROCESSING_ERROR",
    "third-party discovery evidence must not enter the first-party resolver as authoritative",
)
print("PASS 3: discovery-platform IDs and third-party evidence cannot satisfy canonical identity.")

# 4. Exact title binding is case/whitespace/Unicode-normalization only; fuzzy title mismatch holds.
fuzzy = copy.deepcopy(requests[1])
fuzzy["first_party_observation"]["observed_role_title"] = "Jr Business Analyst"
fuzzy_outcome = evaluate_first_party_identity_request(fuzzy)
assert_true(
    fuzzy_outcome["outcome"] == "VERIFICATION_REQUIRED"
    and fuzzy_outcome["error_code"] == "ROLE_BINDING_MISMATCH",
    "abbreviation/fuzzy title matching must fail closed",
)
case_space = copy.deepcopy(requests[1])
case_space["first_party_observation"]["observed_role_title"] = "  junior   business ANALYST  "
case_space_outcome = evaluate_first_party_identity_request(case_space)
assert_true(
    case_space_outcome["outcome"] == "RESOLVED",
    "case/whitespace normalization is allowed",
)
print("PASS 4: title binding permits only bounded normalization and rejects fuzzy/abbreviated roles.")

# 5. First-party role confirmation without requisition never creates JOBS.
for case_id in ("MIDDESK_UNRESOLVED", "RUNLAYER_UNRESOLVED"):
    case = by_id[case_id]
    request = {
        "discovery_log_record": case["discovery_log_record"],
        "first_party_observation": case["first_party_observation"],
    }
    hold_plan = build_first_party_identity_resolution_mutation_plan(
        [request],
        None,
        run_id=f"FPIR_{case_id}",
        processed_at="2026-09-26T13:46:00-04:00",
    )
    assert_true(len(hold_plan["jobs_mutations"]) == 0, f"{case_id}: no JOBS row without requisition")
    assert_true(
        hold_plan["log_mutations"][0]["Status"] == "VERIFICATION_REQUIRED",
        f"{case_id}: must remain visible verification hold",
    )
print("PASS 5: first-party role existence alone is insufficient for canonical identity.")

# 6. Rehydrate the exact first plan from durable JOBS/LOG rows, then rerun byte-equivalent evidence.
jobs_rows = [{k: v for k, v in row.items() if k != "Op"} for row in plan["jobs_mutations"]]
log_rows = [dict(row) for row in plan["log_mutations"]]
rehydrated = state_from_ledger_rows(jobs_rows, log_rows)
rerun = build_first_party_identity_resolution_mutation_plan(
    requests,
    rehydrated,
    run_id="FPIR_TEST_001_RERUN",
    processed_at="2026-09-26T13:47:00-04:00",
)
assert_true(rerun["jobs_mutations"] == [], "byte-equivalent rerun must not duplicate JOBS")
assert_true(rerun["log_mutations"] == [], "byte-equivalent rerun must not duplicate LOG")
print("PASS 6: durable JOBS/LOG rehydration preserves first-party verification idempotency.")

# 7. Cross-source second nomination resolving to an existing exact role updates one JOBS entity
# while retaining its distinct verification attempt in LOG.
cross_source = copy.deepcopy(requests[0])
cross_notes = json.loads(cross_source["discovery_log_record"]["Notes"])
cross_notes["discovery_lead_id"] = "LEAD_MTA_SECOND_SOURCE"
cross_notes["source_message_id"] = "SECOND_SOURCE_MESSAGE"
cross_notes["source_thread_id"] = "SECOND_SOURCE_MESSAGE"
cross_notes["discovery_urls"] = ["https://example.com/third-party/mta-17407"]
cross_notes["source_claims"] = {"source_provider": "OTHER_DISCOVERY"}
cross_source["discovery_log_record"]["Notes"] = json.dumps(cross_notes)
cross_state = plan["next_state"]
cross_plan = build_first_party_identity_resolution_mutation_plan(
    [cross_source],
    cross_state,
    run_id="FPIR_CROSS_SOURCE",
    processed_at="2026-09-26T13:48:00-04:00",
)
assert_true(len(cross_plan["jobs_mutations"]) == 1, "second source should converge on existing JOBS entity")
assert_true(cross_plan["jobs_mutations"][0]["Op"] == "UPDATE", "second source must update, not create")
assert_true(cross_plan["jobs_mutations"][0]["Job_ID"] == "MTA::17407", "exact identity must converge")
assert_true(len(cross_plan["log_mutations"]) == 1, "distinct discovery provenance must remain auditable")
print("PASS 7: cross-source exact identity converges on one JOBS entity while retaining provenance.")

# 8. Requisition evidence must literally support the supplied exact requisition.
bad_evidence = copy.deepcopy(requests[2])
bad_evidence["first_party_observation"]["requisition_evidence"] = (
    "Official OneMain posting, but no job number is visible here."
)
bad_evidence_outcome = evaluate_first_party_identity_request(bad_evidence)
assert_true(
    bad_evidence_outcome["outcome"] == "PROCESSING_ERROR"
    and bad_evidence_outcome["error_code"] == "REQUISITION_EVIDENCE_MISMATCH",
    "supplied requisition must be supported by first-party evidence text",
)
print("PASS 8: contradictory requisition evidence fails visibly.")

# 9. Same exact identity with a contradictory role cannot mutate an existing JOBS row.
contradictory = copy.deepcopy(requests[0])
contradictory_notes = json.loads(contradictory["discovery_log_record"]["Notes"])
contradictory_notes["discovery_lead_id"] = "LEAD_MTA_CONTRADICTORY_ROLE"
contradictory_notes["role_text"] = "Different Role Title"
contradictory["discovery_log_record"]["Notes"] = json.dumps(contradictory_notes)
contradictory["first_party_observation"]["observed_role_title"] = "Different Role Title"
contradiction_plan = build_first_party_identity_resolution_mutation_plan(
    [contradictory],
    plan["next_state"],
    run_id="FPIR_ROLE_CONTRADICTION",
    processed_at="2026-09-26T13:49:00-04:00",
)
assert_true(
    contradiction_plan["jobs_mutations"] == [],
    "contradictory role under the same exact identity must not mutate JOBS",
)
assert_true(
    len(contradiction_plan["log_mutations"]) == 1
    and contradiction_plan["log_mutations"][0]["Status"] == "VERIFICATION_REQUIRED"
    and contradiction_plan["log_mutations"][0]["Error_Code"] == "EXACT_IDENTITY_ROLE_CONTRADICTION",
    "exact-identity role contradiction must fail visibly",
)
print("PASS 9: same exact identity with a contradictory role fails closed with zero JOBS mutation.")

# 10. One malformed request cannot abort or suppress a valid sibling request.
malformed = copy.deepcopy(requests[0])
del malformed["first_party_observation"]["official_url"]
mixed_plan = build_first_party_identity_resolution_mutation_plan(
    [malformed, requests[1]],
    None,
    run_id="FPIR_MIXED_BATCH",
    processed_at="2026-09-26T13:50:00-04:00",
)
assert_true(
    len(mixed_plan["jobs_mutations"]) == 1
    and mixed_plan["jobs_mutations"][0]["Job_ID"] == "PERATON::2026-171010",
    "valid sibling request must survive malformed input in the same batch",
)
assert_true(
    any(
        row["Status"] == "PROCESSING_ERROR"
        and row["Error_Code"] == "FIRST_PARTY_REQUEST_SCHEMA_INVALID"
        for row in mixed_plan["log_mutations"]
    ),
    "malformed request must fail visibly into PROCESSING_ERROR",
)
assert_true(
    any(
        row["Status"] == "NORMALIZED"
        and row["Job_ID"] == "PERATON::2026-171010"
        for row in mixed_plan["log_mutations"]
    ),
    "valid sibling resolution must still be logged",
)
print("PASS 10: malformed first-party input fails visibly without poisoning valid siblings.")

print("ALL FIRST_PARTY_IDENTITY_RESOLUTION_V1 TESTS PASSED")
