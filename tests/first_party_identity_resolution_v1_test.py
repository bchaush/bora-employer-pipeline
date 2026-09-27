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
    build_mutation_plan,
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


def _seed_lead_provenance(
    state: dict | None, request: dict
) -> dict:
    """TEST-ONLY helper: seed a request's durable Slice-1 discovery_lead_id
    provenance into a mutation-plan state dict by reconstructing it from the
    request's own canonical Slice-1 IDENTITY_RESOLUTION/VERIFICATION_REQUIRED
    LOG row via state_from_ledger_rows, preserving existing contents. Does
    not manufacture JOBS rows or resolution fingerprints, and does not
    fabricate eligibility by injecting into state fields directly.
    """
    base = copy.deepcopy(state) if state is not None else {
        "jobs": {},
        "processed_lead_ids": [],
        "gate_match_fingerprints": {},
        "first_party_resolution_fingerprints": [],
        "first_party_eligible_lead_ids": [],
        "first_party_durable_provenance": {},
    }
    reconstructed = state_from_ledger_rows([], [request["discovery_log_record"]])
    processed = set(base.get("processed_lead_ids", []))
    processed.update(reconstructed["processed_lead_ids"])
    base["processed_lead_ids"] = sorted(processed)
    eligible = set(base.get("first_party_eligible_lead_ids", []))
    eligible.update(reconstructed["first_party_eligible_lead_ids"])
    base["first_party_eligible_lead_ids"] = sorted(eligible)
    durable = dict(base.get("first_party_durable_provenance", {}))
    durable.update(reconstructed.get("first_party_durable_provenance", {}))
    base["first_party_durable_provenance"] = durable
    return base

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
seeded_state_all = None
for _seed_request in requests:
    seeded_state_all = _seed_lead_provenance(seeded_state_all, _seed_request)
plan = build_first_party_identity_resolution_mutation_plan(
    requests,
    seeded_state_all,
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
    hold_state = _seed_lead_provenance(None, request)
    hold_plan = build_first_party_identity_resolution_mutation_plan(
        [request],
        hold_state,
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
cross_state = _seed_lead_provenance(plan["next_state"], cross_source)
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
contradiction_state = _seed_lead_provenance(plan["next_state"], contradictory)
contradiction_plan = build_first_party_identity_resolution_mutation_plan(
    [contradictory],
    contradiction_state,
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
mixed_state = _seed_lead_provenance(None, malformed)
mixed_state = _seed_lead_provenance(mixed_state, requests[1])
mixed_plan = build_first_party_identity_resolution_mutation_plan(
    [malformed, requests[1]],
    mixed_state,
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

# 11. Stale/equal-time first-party replay must never regress a durable Official_URL.
newer_official_url = (
    "https://careers.mta.org/jobs/18276348-data-analyst-subway-resource-and-admin-support-"
    "emerging-talent-intern-spring"
)
older_official_url = newer_official_url + "-STALE-MIRROR"
tie_official_url = newer_official_url + "-TIE-MIRROR"

newer_observation = copy.deepcopy(requests[0])
newer_observation["first_party_observation"]["observed_at"] = "2026-09-26T13:00:00-04:00"
newer_observation["first_party_observation"]["official_url"] = newer_official_url
newer_state = _seed_lead_provenance(None, newer_observation)
durable_plan = build_first_party_identity_resolution_mutation_plan(
    [newer_observation],
    newer_state,
    run_id="FPIR_TEMPORAL_DURABLE",
    processed_at="2026-09-26T13:01:00-04:00",
)
assert_true(
    durable_plan["jobs_mutations"][0]["Official_URL"] == newer_official_url
    and durable_plan["jobs_mutations"][0]["Last_Verified"] == "2026-09-26T13:00:00-04:00",
    "durable baseline must record the newer first-party Official_URL/Last_Verified",
)
durable_state = durable_plan["next_state"]

stale_replay = copy.deepcopy(requests[0])
stale_replay["first_party_observation"]["observed_at"] = "2026-09-26T12:00:00-04:00"
stale_replay["first_party_observation"]["official_url"] = older_official_url
stale_plan = build_first_party_identity_resolution_mutation_plan(
    [stale_replay],
    durable_state,
    run_id="FPIR_TEMPORAL_STALE_REPLAY",
    processed_at="2026-09-26T13:02:00-04:00",
)
assert_true(
    len(stale_plan["jobs_mutations"]) == 1,
    "stale replay must still converge on the existing JOBS entity",
)
stale_job_row = stale_plan["jobs_mutations"][0]
assert_true(
    stale_job_row["Job_ID"] == by_id["MTA_17407"]["expected_job_id"],
    "stale replay must resolve to the same exact canonical Job_ID",
)
assert_true(
    stale_job_row["Last_Verified"] == "2026-09-26T13:00:00-04:00",
    "an older first-party observation must never regress Last_Verified",
)
assert_true(
    stale_job_row["Official_URL"] == newer_official_url,
    "an older first-party observation must never overwrite an already-durable, more-recent Official_URL",
)
assert_true(
    len(stale_plan["log_mutations"]) == 1
    and stale_plan["log_mutations"][0]["Job_ID"] == by_id["MTA_17407"]["expected_job_id"],
    "the stale observation must still be auditable in LOG even though it does not win Official_URL",
)

tie_replay = copy.deepcopy(requests[0])
tie_replay["first_party_observation"]["observed_at"] = "2026-09-26T13:00:00-04:00"
tie_replay["first_party_observation"]["official_url"] = tie_official_url
tie_plan = build_first_party_identity_resolution_mutation_plan(
    [tie_replay],
    durable_state,
    run_id="FPIR_TEMPORAL_TIE_REPLAY",
    processed_at="2026-09-26T13:03:00-04:00",
)
tie_job_row = tie_plan["jobs_mutations"][0]
assert_true(
    tie_job_row["Official_URL"] == newer_official_url,
    "an equal-observed_at first-party replay must not arbitrarily overwrite the already-durable Official_URL",
)
print("PASS 11: stale/equal-time first-party replay cannot regress a durable Official_URL or Last_Verified.")

# 12. F1: partial/truncated requisition-ID digits must not satisfy exact requisition identity.
partial_id = copy.deepcopy(requests[0])
partial_id["first_party_observation"]["exact_requisition_id"] = "174"
partial_outcome = evaluate_first_party_identity_request(partial_id)
assert_true(
    partial_outcome["outcome"] != "RESOLVED" and partial_outcome["operational_job_id"] is None,
    "F1: a truncated substring of the true requisition ID must never RESOLVE",
)

partial_id_no_year = copy.deepcopy(requests[1])
partial_id_no_year["first_party_observation"]["exact_requisition_id"] = "171010"
partial_outcome_2 = evaluate_first_party_identity_request(partial_id_no_year)
assert_true(
    partial_outcome_2["outcome"] != "RESOLVED" and partial_outcome_2["operational_job_id"] is None,
    "F1: dropping the year prefix from a composite requisition ID must never RESOLVE",
)
print("PASS 12: partial/truncated requisition-ID fragments cannot satisfy exact requisition identity (F1).")

# 13. F2: a valid first-party verification must coherently establish Official_URL even when
# a preexisting non-first-party JOBS row carries a later timestamp.
existing_non_first_party_job = {
    "Op": "CREATE",
    "Job_ID": "MTA::17407",
    "Company": "Metropolitan Transportation Authority",
    "Role": "Data Analyst, Subway Resource & Admin Support, Emerging Talent Intern (Spring)",
    "Discovery_Source": "GMAIL",
    "Discovery_URL": "https://www.linkedin.com/comm/jobs/view/4470047211/",
    "Official_URL": None,
    "First_Seen": "2026-09-27T00:00:00+00:00",
    "Last_Verified": "2026-09-27T00:00:00+00:00",
    "Pipeline_State": "NORMALIZED",
}
f2_state = _seed_lead_provenance(
    {
        "jobs": {"MTA::17407": existing_non_first_party_job},
        "processed_lead_ids": [],
        "gate_match_fingerprints": {},
        "first_party_resolution_fingerprints": [],
    },
    requests[0],
)
f2_plan = build_first_party_identity_resolution_mutation_plan(
    [requests[0]],
    f2_state,
    run_id="FPIR_TEMPORAL_COHERENCE",
    processed_at="2026-09-27T01:00:00+00:00",
)
assert_true(
    len(f2_plan["jobs_mutations"]) == 1,
    "F2: valid first-party verification must mutate the existing JOBS row",
)
assert_true(
    f2_plan["jobs_mutations"][0]["Official_URL"]
    == requests[0]["first_party_observation"]["official_url"],
    "F2: first-party Official_URL must be established even when a preexisting non-first-party "
    "timestamp is later; silently leaving Official_URL None is not a coherent success",
)
print("PASS 13: first-party verification coherently establishes Official_URL over a stale non-first-party row (F2).")

# 14. F3: contradictory employer binding (claimed employer identity does not match the
# employer named in the original discovery lead) must fail closed, not RESOLVE.
contradictory_employer = copy.deepcopy(requests[3])  # MIDDESK_UNRESOLVED discovery lead
contradictory_employer["first_party_observation"]["requisition_status"] = "EXACT"
contradictory_employer["first_party_observation"]["exact_requisition_id"] = "9999"
contradictory_employer["first_party_observation"]["requisition_evidence"] = (
    "Official posting displays Job ID 9999."
)
contradictory_employer["first_party_observation"]["requisition_authority"] = (
    "EMPLOYER_OR_ATS_FIRST_PARTY"
)
contradictory_employer["first_party_observation"]["observed_employer_name"] = "Acme"
contradictory_employer["first_party_observation"]["exact_employer_identity"] = "ACME"
contradictory_outcome = evaluate_first_party_identity_request(contradictory_employer)
assert_true(
    contradictory_outcome["outcome"] != "RESOLVED"
    and contradictory_outcome["operational_job_id"] is None,
    "F3: an employer identity contradicting the original discovery lead's employer must fail closed",
)
print("PASS 14: contradictory employer binding fails closed instead of resolving (F3).")

# 15. F4: a discovery lead with no durably persisted Slice-1 LOG provenance must produce
# zero JOBS mutations and a visible fail-closed/audit result, not a silent resolve.
unrelated_log_row = {
    "Run_ID": "PROD_UNRELATED",
    "Timestamp": "2026-09-26T16:00:00-04:00",
    "Stage": "IDENTITY_RESOLUTION",
    "Source": "GMAIL",
    "Job_ID": None,
    "Status": "VERIFICATION_REQUIRED",
    "Error_Code": None,
    "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET",
    "Notes": json.dumps({"discovery_lead_id": "LEAD_UNRELATED_999"}),
}
recon_state_missing_provenance = state_from_ledger_rows([], [unrelated_log_row])
f4_plan = build_first_party_identity_resolution_mutation_plan(
    [requests[0]],
    recon_state_missing_provenance,
    run_id="FPIR_MISSING_PROVENANCE",
    processed_at="2026-09-27T01:00:00+00:00",
)
assert_true(
    f4_plan["jobs_mutations"] == [],
    "F4: missing durable Slice-1 lead provenance must produce zero JOBS mutations",
)
assert_true(
    len(f4_plan["log_mutations"]) == 1
    and f4_plan["log_mutations"][0]["Status"] in ("PROCESSING_ERROR", "VERIFICATION_REQUIRED")
    and f4_plan["log_mutations"][0]["Error_Code"] is not None,
    "F4: absence of durable Slice-1 lead provenance must be a visible fail-closed/audit result, "
    "not a silent resolve",
)
print("PASS 15: missing durable Slice-1 lead provenance fails closed with zero JOBS and a visible audit trail (F4).")

# 16. F5: a discovery-platform ID must not become a canonical requisition regardless of
# which source_claims key it is stored under, or if it is only present inside the discovery URL.
arbitrary_key_shortcut = copy.deepcopy(requests[0])
arbitrary_notes = json.loads(arbitrary_key_shortcut["discovery_log_record"]["Notes"])
arbitrary_claims = arbitrary_notes["source_claims"]
del arbitrary_claims["source_job_id"]
arbitrary_claims["linkedin_job_id"] = "4470047211"
arbitrary_notes["source_claims"] = arbitrary_claims
arbitrary_key_shortcut["discovery_log_record"]["Notes"] = json.dumps(arbitrary_notes)
arbitrary_key_shortcut["first_party_observation"]["exact_requisition_id"] = "4470047211"
arbitrary_key_shortcut["first_party_observation"]["requisition_evidence"] = (
    "Official MTA Careers posting displays Job ID 4470047211."
)
arbitrary_key_outcome = evaluate_first_party_identity_request(arbitrary_key_shortcut)
assert_true(
    arbitrary_key_outcome["outcome"] != "RESOLVED",
    "F5: a discovery-platform ID stashed under an unrecognized source_claims key must still be forbidden",
)

url_contained_shortcut = copy.deepcopy(requests[0])
url_contained_notes = json.loads(url_contained_shortcut["discovery_log_record"]["Notes"])
url_contained_notes["source_claims"] = {"source_provider": "LINKEDIN"}
url_contained_shortcut["discovery_log_record"]["Notes"] = json.dumps(url_contained_notes)
url_contained_shortcut["first_party_observation"]["exact_requisition_id"] = "4470047211"
url_contained_shortcut["first_party_observation"]["requisition_evidence"] = (
    "Official MTA Careers posting displays Job ID 4470047211."
)
url_contained_outcome = evaluate_first_party_identity_request(url_contained_shortcut)
assert_true(
    url_contained_outcome["outcome"] != "RESOLVED",
    "F5: a discovery-platform ID present only inside the discovery URL must still be forbidden",
)
print("PASS 16: discovery-platform IDs are forbidden regardless of source_claims key or URL-only presence (F5).")

# 17. F6: a corrected valid request must still execute/audit after a prior malformed attempt
# with the same lead, and must not be silently suppressed as an already-seen fingerprint.
f6_malformed = copy.deepcopy(requests[0])
f6_malformed_notes = json.loads(f6_malformed["discovery_log_record"]["Notes"])
del f6_malformed_notes["role_text"]
f6_malformed["discovery_log_record"]["Notes"] = json.dumps(f6_malformed_notes)
f6_state = _seed_lead_provenance(None, requests[0])
f6_plan_1 = build_first_party_identity_resolution_mutation_plan(
    [f6_malformed],
    f6_state,
    run_id="FPIR_F6_MALFORMED",
    processed_at="2026-09-27T01:00:00+00:00",
)
assert_true(
    f6_plan_1["jobs_mutations"] == [],
    "F6: the malformed attempt itself must not create a JOBS row",
)
f6_plan_2 = build_first_party_identity_resolution_mutation_plan(
    [requests[0]],
    f6_plan_1["next_state"],
    run_id="FPIR_F6_CORRECTED",
    processed_at="2026-09-27T01:05:00-04:00",
)
assert_true(
    len(f6_plan_2["jobs_mutations"]) == 1
    and f6_plan_2["jobs_mutations"][0]["Job_ID"] == by_id["MTA_17407"]["expected_job_id"],
    "F6: a corrected valid request following a malformed attempt must still execute and create the JOBS row",
)
assert_true(
    len(f6_plan_2["log_mutations"]) == 1
    and f6_plan_2["log_mutations"][0]["Status"] == "NORMALIZED",
    "F6: the corrected valid request must still be auditable in LOG, not suppressed",
)
print("PASS 17: a corrected valid request after a malformed attempt still executes and is audited (F6).")

# 18. F7: a known third-party discovery-host URL (e.g. linkedin.com) must never be accepted
# as a first-party Official_URL.
third_party_official_url = copy.deepcopy(requests[0])
third_party_official_url["first_party_observation"]["official_url"] = (
    "https://www.linkedin.com/jobs/view/18276348/"
)
third_party_official_url_outcome = evaluate_first_party_identity_request(third_party_official_url)
assert_true(
    third_party_official_url_outcome["outcome"] != "RESOLVED",
    "F7: a known third-party discovery-host URL must not be accepted as a first-party Official_URL",
)
print("PASS 18: a known third-party discovery-host URL is rejected as Official_URL (F7).")

# 19. F4-STRICT: a LOG row carrying the same discovery_lead_id under the wrong
# stage/status (or the wrong stage entirely) must never retroactively authorize
# first-party JOBS creation. Only a canonical Slice-1 IDENTITY_RESOLUTION /
# VERIFICATION_REQUIRED LOG row establishes durable first-party eligibility;
# loose "any LOG row mentioning this discovery_lead_id" matching must not.
f4_strict_lead_id = json.loads(requests[0]["discovery_log_record"]["Notes"])[
    "discovery_lead_id"
]
wrong_shape_rows = [
    {
        "Run_ID": "PROD_WRONG_SHAPE_NORMALIZED",
        "Timestamp": "2026-09-26T16:00:00-04:00",
        "Stage": "FIRST_PARTY_IDENTITY_RESOLUTION",
        "Source": "FIRST_PARTY_VERIFICATION",
        "Job_ID": "MTA::17407",
        "Status": "NORMALIZED",
        "Error_Code": None,
        "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_FIRST_PARTY_IDENTITY_RESOLUTION",
        "Notes": json.dumps({"discovery_lead_id": f4_strict_lead_id}),
    },
    {
        "Run_ID": "PROD_WRONG_SHAPE_LEDGER_PERSISTENCE",
        "Timestamp": "2026-09-26T16:00:00-04:00",
        "Stage": "LEDGER_PERSISTENCE",
        "Source": "GMAIL",
        "Job_ID": "MTA::17407",
        "Status": "VERIFICATION_REQUIRED",
        "Error_Code": None,
        "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET",
        "Notes": json.dumps({"discovery_lead_id": f4_strict_lead_id}),
    },
    {
        "Run_ID": "PROD_WRONG_SHAPE_PROCESSING_ERROR",
        "Timestamp": "2026-09-26T16:00:00-04:00",
        "Stage": "IDENTITY_RESOLUTION",
        "Source": "GMAIL",
        "Job_ID": None,
        "Status": "PROCESSING_ERROR",
        "Error_Code": "MALFORMED_INPUT",
        "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET",
        "Notes": json.dumps({"discovery_lead_id": f4_strict_lead_id}),
    },
]
for wrong_row in wrong_shape_rows:
    wrong_state = state_from_ledger_rows([], [wrong_row])
    assert_true(
        f4_strict_lead_id not in wrong_state.get("first_party_eligible_lead_ids", []),
        f"F4-STRICT: a {wrong_row['Stage']}/{wrong_row['Status']} LOG row must not "
        "establish durable first-party eligibility",
    )
    wrong_plan = build_first_party_identity_resolution_mutation_plan(
        [requests[0]],
        wrong_state,
        run_id="FPIR_F4_STRICT",
        processed_at="2026-09-27T02:00:00+00:00",
    )
    assert_true(
        wrong_plan["jobs_mutations"] == [],
        f"F4-STRICT: a {wrong_row['Stage']}/{wrong_row['Status']} LOG row must not "
        f"authorize first-party JOBS creation for {f4_strict_lead_id}",
    )
print(
    "PASS 19: wrong-stage/status LOG rows never retroactively authorize "
    "first-party JOBS creation (F4-STRICT)."
)


# 20. R1: durable eligibility must bind to the exact canonical Slice-1 provenance, not lead_id alone.
r1_state = state_from_ledger_rows([], [requests[0]["discovery_log_record"]])
r1_forged = copy.deepcopy(requests[0])
r1_notes = json.loads(r1_forged["discovery_log_record"]["Notes"])
r1_notes["employer_text"] = "Peraton"
r1_notes["role_text"] = "Junior Business Analyst"
r1_notes["observed_at"] = "2026-09-25T18:15:12+00:00"
r1_notes["source_claims"] = {}
r1_notes["discovery_urls"] = []
r1_forged["discovery_log_record"]["Notes"] = json.dumps(r1_notes)
r1_forged["first_party_observation"] = copy.deepcopy(requests[1]["first_party_observation"])
r1_plan = build_first_party_identity_resolution_mutation_plan(
    [r1_forged], r1_state, run_id="FPIR_R1_FORGED", processed_at="2026-09-27T03:00:00+00:00"
)
assert_true(r1_plan["jobs_mutations"] == [], "R1: forged provenance under an eligible lead_id must not create JOBS")
assert_true(
    len(r1_plan["log_mutations"]) == 1
    and r1_plan["log_mutations"][0]["Error_Code"] == "DURABLE_DISCOVERY_PROVENANCE_REQUIRED",
    "R1: forged provenance must fail visibly at the durable-provenance boundary",
)
print("PASS 20: durable Slice-1 eligibility is bound to exact immutable provenance, not lead_id alone (R1).")

# 21. R2: later Slice-1 discovery activity must not outrank newer first-party verification.
r2_state = state_from_ledger_rows([], [requests[0]["discovery_log_record"]])
r2_v1 = copy.deepcopy(requests[0])
r2_v1["first_party_observation"]["observed_at"] = "2026-09-26T12:00:00-04:00"
r2_v1["first_party_observation"]["official_url"] = "https://careers.mta.org/jobs/r2-v1"
r2_p1 = build_first_party_identity_resolution_mutation_plan(
    [r2_v1], r2_state, run_id="FPIR_R2_V1", processed_at="2026-09-26T12:01:00-04:00"
)
r2_job = {k: v for k, v in r2_p1["jobs_mutations"][0].items() if k != "Op"}
r2_later_lead = {
    "discovery_lead_id": "LEAD_R2_LATER",
    "source_message_id": "MSG_R2_LATER",
    "source_thread_id": "MSG_R2_LATER",
    "source": "GMAIL",
    "identity_resolution_status": "RESOLVED",
    "observed_at": "2026-09-26T15:00:00-04:00",
    "discovery_urls": ["https://www.linkedin.com/jobs/view/999"],
    "employer_text": "Metropolitan Transportation Authority",
    "role_text": "Data Analyst, Subway Resource & Admin Support, Emerging Talent Intern (Spring)",
    "requisition_text": "17407",
    "source_claims": {"source_provider": "LINKEDIN", "source_job_id": "999"},
    "exact_employer_identity": "MTA",
    "exact_requisition_id": "17407",
}
r2_slice_state = {
    "jobs": {"MTA::17407": r2_job},
    "processed_lead_ids": r2_state["processed_lead_ids"],
    "gate_match_fingerprints": {},
    "first_party_resolution_fingerprints": r2_p1["next_state"]["first_party_resolution_fingerprints"],
    "first_party_eligible_lead_ids": r2_state["first_party_eligible_lead_ids"],
    "first_party_durable_provenance": r2_state["first_party_durable_provenance"],
}
r2_slice = build_mutation_plan(
    [r2_later_lead], r2_slice_state, run_id="FPIR_R2_SLICE", processed_at="2026-09-26T15:01:00-04:00"
)
r2_after_slice = {k: v for k, v in r2_slice["jobs_mutations"][0].items() if k != "Op"}
assert_true(
    r2_after_slice["Last_Verified"] == "2026-09-26T12:00:00-04:00",
    "R2: third-party Slice-1 observation must not advance the first-party verification clock",
)
r2_v2 = copy.deepcopy(requests[0])
r2_v2["first_party_observation"]["observed_at"] = "2026-09-26T14:00:00-04:00"
r2_v2["first_party_observation"]["official_url"] = "https://careers.mta.org/jobs/r2-v2"
r2_v2_state = dict(r2_slice["next_state"])
r2_v2_state["jobs"] = {"MTA::17407": r2_after_slice}
r2_v2_plan = build_first_party_identity_resolution_mutation_plan(
    [r2_v2], r2_v2_state, run_id="FPIR_R2_V2", processed_at="2026-09-26T15:02:00-04:00"
)
assert_true(
    r2_v2_plan["jobs_mutations"][0]["Official_URL"] == "https://careers.mta.org/jobs/r2-v2"
    and r2_v2_plan["jobs_mutations"][0]["Last_Verified"] == "2026-09-26T14:00:00-04:00",
    "R2: newer first-party v2 must advance URL and verification time despite later discovery activity",
)
print("PASS 21: Slice-1 discovery timestamps cannot outrank the first-party verification clock (R2).")

# 22. R3: platform IDs embedded in known discovery-platform URL slugs remain forbidden.
r3 = copy.deepcopy(requests[1])
r3_notes = json.loads(r3["discovery_log_record"]["Notes"])
r3_notes["source_claims"] = {"source_provider": "LINKEDIN"}
r3_notes["discovery_urls"] = [
    "https://www.linkedin.com/jobs/view/junior-business-analyst-at-peraton-4470043526"
]
r3["discovery_log_record"]["Notes"] = json.dumps(r3_notes)
r3["first_party_observation"]["exact_requisition_id"] = "4470043526"
r3["first_party_observation"]["requisition_evidence"] = "Official Peraton posting displays requisition 4470043526."
r3_outcome = evaluate_first_party_identity_request(r3)
assert_true(r3_outcome["outcome"] != "RESOLVED", "R3: slug-delimited LinkedIn IDs must never become canonical")
print("PASS 22: known discovery-platform URL slugs cannot supply canonical requisition identity (R3).")

# 23. R4: non-null durable discovery exact identity components contradicting first-party identity fail closed.
r4_employer = copy.deepcopy(requests[0])
r4_notes = json.loads(r4_employer["discovery_log_record"]["Notes"])
r4_notes["exact_employer_identity"] = "SOME_OTHER_EMPLOYER"
r4_employer["discovery_log_record"]["Notes"] = json.dumps(r4_notes)
r4_emp_outcome = evaluate_first_party_identity_request(r4_employer)
assert_true(r4_emp_outcome["outcome"] != "RESOLVED", "R4: contradictory durable employer identity must fail closed")
r4_req = copy.deepcopy(requests[0])
r4_req_notes = json.loads(r4_req["discovery_log_record"]["Notes"])
r4_req_notes["exact_requisition_id"] = "OTHER-REQ"
r4_req["discovery_log_record"]["Notes"] = json.dumps(r4_req_notes)
r4_req_outcome = evaluate_first_party_identity_request(r4_req)
assert_true(r4_req_outcome["outcome"] != "RESOLVED", "R4: contradictory durable requisition identity must fail closed")
assert_true(
    evaluate_first_party_identity_request(requests[0])["outcome"] == "RESOLVED",
    "R4: null discovery identity components must remain non-authoritative",
)
print("PASS 23: contradictory durable exact identity components fail closed while null components remain neutral (R4).")

# 24. R5: trailing DNS dot cannot bypass third-party Official_URL host denylist.
r5 = copy.deepcopy(requests[0])
r5["first_party_observation"]["official_url"] = "https://www.linkedin.com./jobs/view/18276348/"
r5_outcome = evaluate_first_party_identity_request(r5)
assert_true(r5_outcome["outcome"] != "RESOLVED", "R5: trailing-dot LinkedIn host must remain forbidden")
print("PASS 24: trailing DNS dot cannot bypass the third-party Official_URL host denylist (R5).")

# 25. R6: missing-provenance hold must not poison a later legitimate retry after durable rehydration.
r6_hold = build_first_party_identity_resolution_mutation_plan(
    [requests[0]], None, run_id="FPIR_R6_HOLD", processed_at="2026-09-27T04:00:00+00:00"
)
r6_rows = [copy.deepcopy(requests[0]["discovery_log_record"])] + [dict(x) for x in r6_hold["log_mutations"]]
r6_rehydrated = state_from_ledger_rows([], r6_rows)
r6_retry = build_first_party_identity_resolution_mutation_plan(
    [requests[0]], r6_rehydrated, run_id="FPIR_R6_RETRY", processed_at="2026-09-27T04:01:00+00:00"
)
assert_true(
    len(r6_retry["jobs_mutations"]) == 1
    and r6_retry["jobs_mutations"][0]["Job_ID"] == "MTA::17407",
    "R6: durable-provenance hold must not suppress a later legitimate retry",
)
assert_true(
    len(r6_retry["log_mutations"]) == 1 and r6_retry["log_mutations"][0]["Status"] == "NORMALIZED",
    "R6: later legitimate retry must remain auditable",
)
print("PASS 25: missing-provenance holds do not poison later legitimate retries (R6).")

# 26. R7: composite continuations are not exact requisition evidence tokens.
for evidence_text, request_index in (
    ("Official MTA posting displays Job ID 17407.2.", 0),
    ("Official MTA posting displays Job ID 17407_old.", 0),
    ("Official OneMain posting displays Job Number R2608-52225.1.", 2),
):
    r7 = copy.deepcopy(requests[request_index])
    r7["first_party_observation"]["requisition_evidence"] = evidence_text
    r7_outcome = evaluate_first_party_identity_request(r7)
    assert_true(r7_outcome["outcome"] != "RESOLVED", f"R7: composite continuation must not prove exact ID: {evidence_text}")
print("PASS 26: composite requisition continuations cannot satisfy exact evidence binding (R7).")


# 27. Final-review HIGH: downstream first-party hold/error LOG rows must not poison Slice-1 idempotency.
fr_hold = build_first_party_identity_resolution_mutation_plan(
    [requests[0]], None, run_id="FPIR_FR_HOLD", processed_at="2026-09-27T10:00:00+00:00"
)
fr_poison_state = state_from_ledger_rows([], [dict(row) for row in fr_hold["log_mutations"]])
fr_notes = json.loads(requests[0]["discovery_log_record"]["Notes"])
fr_slice_lead = {
    "discovery_lead_id": fr_notes["discovery_lead_id"], "source_message_id": fr_notes["source_message_id"],
    "source_thread_id": fr_notes.get("source_thread_id"), "source": "GMAIL",
    "identity_resolution_status": "VERIFICATION_REQUIRED", "observed_at": fr_notes["observed_at"],
    "discovery_urls": fr_notes["discovery_urls"], "employer_text": fr_notes["employer_text"],
    "role_text": fr_notes["role_text"], "requisition_text": fr_notes.get("requisition_text"),
    "source_claims": fr_notes["source_claims"], "exact_employer_identity": fr_notes.get("exact_employer_identity"),
    "exact_requisition_id": fr_notes.get("exact_requisition_id"),
}
assert_true(fr_notes["discovery_lead_id"] not in fr_poison_state["processed_lead_ids"],
    "final HIGH: downstream first-party holds must not become Slice-1 processed lead IDs")
fr_slice_after_hold = build_mutation_plan(
    [fr_slice_lead], fr_poison_state, run_id="FPIR_FR_SLICE", processed_at="2026-09-27T10:01:00+00:00"
)
assert_true(len(fr_slice_after_hold["log_mutations"]) == 1
    and fr_slice_after_hold["log_mutations"][0]["Stage"] == "IDENTITY_RESOLUTION",
    "final HIGH: later legitimate Slice-1 ingestion must still execute after a first-party hold")
print("PASS 27: downstream first-party holds/errors cannot poison Slice-1 processed-lead idempotency.")

# 28. Final-review MEDIUM: composite punctuation and Unicode dashes cannot prove a partial requisition.
for request_index, partial_id, evidence_text in (
    (1, "171010", "Official requisition 2026.171010."),
    (1, "171010", "Official requisition 2026\u2010171010."),
    (0, "17407", "Official Job ID 17407/2."),
):
    fr_req = copy.deepcopy(requests[request_index])
    fr_req["first_party_observation"]["exact_requisition_id"] = partial_id
    fr_req["first_party_observation"]["requisition_evidence"] = evidence_text
    assert_true(evaluate_first_party_identity_request(fr_req)["outcome"] != "RESOLVED",
        f"final MEDIUM: composite evidence must not establish partial requisition {partial_id}")
print("PASS 28: dot/slash/Unicode-dash composites cannot satisfy exact requisition evidence binding.")

# 29. Final-review LOW: encoded/IDNA-equivalent third-party hosts remain forbidden Official_URLs.
for bad_url in (
    "https://www.linked%69n.com/jobs/view/1/",
    "https://www.\uff4c\uff49\uff4e\uff4b\uff45\uff44\uff49\uff4e.com/jobs/view/1/",
):
    fr_url_req = copy.deepcopy(requests[0])
    fr_url_req["first_party_observation"]["official_url"] = bad_url
    assert_true(evaluate_first_party_identity_request(fr_url_req)["outcome"] != "RESOLVED",
        f"final LOW: encoded third-party host must fail: {bad_url}")
print("PASS 29: encoded and IDNA/NFKC-equivalent third-party Official_URL hosts fail visibly.")

# 30. Final-review LOW: non-canonical Unicode requisition IDs cannot create divergent exact-role keys.
fr_nfkc = copy.deepcopy(requests[0])
fr_nfkc["first_party_observation"]["exact_requisition_id"] = "\uff11\uff17\uff14\uff10\uff17"
fr_nfkc_outcome = evaluate_first_party_identity_request(fr_nfkc)
assert_true(fr_nfkc_outcome["outcome"] != "RESOLVED" and fr_nfkc_outcome["operational_job_id"] is None,
    "final LOW: NFKC-equivalent raw requisition IDs must fail closed rather than create divergent Job_IDs")
print("PASS 30: non-canonical Unicode requisition IDs cannot create divergent exact-role keys.")

# 31. Final-review LOW: a discovery-platform ID must not become an authoritative contradiction baseline.
fr_platform_baseline = copy.deepcopy(requests[2])
fr_platform_notes = json.loads(fr_platform_baseline["discovery_log_record"]["Notes"])
fr_platform_notes["exact_requisition_id"] = "9876543"
fr_platform_notes["discovery_urls"] = ["https://app.joinhandshake.com/stu/jobs/9876543"]
fr_platform_baseline["discovery_log_record"]["Notes"] = json.dumps(fr_platform_notes)
fr_platform_outcome = evaluate_first_party_identity_request(fr_platform_baseline)
assert_true(fr_platform_outcome["outcome"] == "RESOLVED"
    and fr_platform_outcome["operational_job_id"] == by_id["ONEMAIN_R2608_52225"]["expected_job_id"],
    "final LOW: discovery-platform requisition IDs must be provenance only, not veto first-party identity")
print("PASS 31: discovery-platform IDs remain provenance-only and cannot veto authoritative first-party identity.")

# 32. Review HIGH-1: backslash-delimited Official_URL hosts (WHATWG-vs-urlparse divergence)
# must fail closed. Python's urlparse does not treat '\' as a netloc/path delimiter the way
# WHATWG-compliant URL parsers (browsers, real employer-site link resolution) do, so a
# backslash-obfuscated linkedin.com Official_URL must not silently bypass the third-party
# discovery-host denylist.
for bad_backslash_url in (
    "https://www.linkedin.com\\jobs/view/4470047211",
    "https://www.linkedin.com\\",
):
    backslash_req = copy.deepcopy(requests[0])
    backslash_req["first_party_observation"]["official_url"] = bad_backslash_url
    backslash_outcome = evaluate_first_party_identity_request(backslash_req)
    assert_true(
        backslash_outcome["outcome"] != "RESOLVED",
        "HIGH-1: a backslash-delimited third-party discovery host must remain forbidden "
        f"as Official_URL, not RESOLVE: {bad_backslash_url!r}",
    )
print("PASS 32: backslash/WHATWG-vs-urlparse Official_URL host bypass fails closed (HIGH-1).")

# 33. Review HIGH-2: one durable discovery lead resolving to conflicting canonical requisitions
# (two different exact_requisition_id values under the same discovery_lead_id/provenance) must
# fail closed rather than create a second, divergent JOBS entity for the same lead -- both when
# the conflicting observations land in the same batch and when the second observation arrives
# after the first resolution has been durably persisted and rehydrated.
conflicting_second_observation = copy.deepcopy(requests[1])
conflicting_second_observation["first_party_observation"]["official_url"] = (
    "https://www.careers.peraton.com/jobs/junior-business-analyst-conflicting-9999"
)
conflicting_second_observation["first_party_observation"]["exact_requisition_id"] = "9999"
conflicting_second_observation["first_party_observation"]["requisition_evidence"] = (
    "Official Peraton Careers posting displays requisition 9999."
)
sanity_conflict_outcome = evaluate_first_party_identity_request(conflicting_second_observation)
assert_true(
    sanity_conflict_outcome["outcome"] == "RESOLVED"
    and sanity_conflict_outcome["operational_job_id"] == "PERATON::9999",
    "sanity: the conflicting second observation must independently satisfy every other exact-identity "
    "gate so the same-lead conflict itself is what is under test",
)

same_batch_state = _seed_lead_provenance(None, requests[1])
same_batch_plan = build_first_party_identity_resolution_mutation_plan(
    [requests[1], conflicting_second_observation],
    same_batch_state,
    run_id="FPIR_CONFLICT_SAME_BATCH",
    processed_at="2026-09-26T14:00:00-04:00",
)
same_batch_job_ids = {row["Job_ID"] for row in same_batch_plan["jobs_mutations"]}
assert_true(
    len(same_batch_job_ids) == 1,
    "HIGH-2: one durable discovery lead resolving to conflicting canonical requisitions in the same "
    f"batch must fail closed to a single Job_ID, not create multiple JOBS rows: {same_batch_job_ids}",
)

initial_conflict_plan = build_first_party_identity_resolution_mutation_plan(
    [requests[1]],
    _seed_lead_provenance(None, requests[1]),
    run_id="FPIR_CONFLICT_INITIAL",
    processed_at="2026-09-26T14:01:00-04:00",
)
assert_true(
    len(initial_conflict_plan["jobs_mutations"]) == 1,
    "sanity: the initial Peraton resolution must create exactly one JOBS row before rehydration",
)
conflict_jobs_rows = [
    {k: v for k, v in row.items() if k != "Op"}
    for row in initial_conflict_plan["jobs_mutations"]
]
conflict_log_rows = [dict(row) for row in initial_conflict_plan["log_mutations"]] + [
    requests[1]["discovery_log_record"]
]
rehydrated_conflict_state = state_from_ledger_rows(conflict_jobs_rows, conflict_log_rows)
after_rehydration_plan = build_first_party_identity_resolution_mutation_plan(
    [conflicting_second_observation],
    rehydrated_conflict_state,
    run_id="FPIR_CONFLICT_AFTER_REHYDRATION",
    processed_at="2026-09-26T14:02:00-04:00",
)
resulting_job_ids = set(rehydrated_conflict_state["jobs"].keys()) | {
    row["Job_ID"] for row in after_rehydration_plan["jobs_mutations"]
}
assert_true(
    len(resulting_job_ids) == 1,
    "HIGH-2: one durable discovery lead resolving to a conflicting canonical requisition after durable "
    f"rehydration must fail closed rather than create a second JOBS entity: {resulting_job_ids}",
)
print(
    "PASS 33: a single durable discovery lead resolving to conflicting canonical requisitions fails "
    "closed rather than creating multiple JOBS rows, in-batch and after durable rehydration (HIGH-2)."
)

# 34. Review HIGH-3: discovery-platform IDs disguised inside source_claims values -- a full
# LinkedIn slug URL stored as a claim value, a hyphen-prefixed platform ID ("LI-<id>"), and a
# JSON numeral ("<id>.0") -- must remain provenance-only and never become the canonical
# exact_requisition_id, regardless of how the identifier is encoded within source_claims.
def _disguised_platform_id_request(source_claims_value: dict) -> dict:
    req = copy.deepcopy(requests[0])
    disguised_notes = json.loads(req["discovery_log_record"]["Notes"])
    disguised_notes["source_claims"] = source_claims_value
    req["discovery_log_record"]["Notes"] = json.dumps(disguised_notes)
    req["first_party_observation"]["exact_requisition_id"] = "4470047211"
    req["first_party_observation"]["requisition_evidence"] = (
        "Official MTA Careers posting displays Job ID 4470047211."
    )
    return req


disguised_source_claims_cases = (
    {"source_provider": "LINKEDIN", "source_url": "https://www.linkedin.com/jobs/view/4470047211/"},
    {"source_provider": "LINKEDIN", "source_ref": "LI-4470047211"},
    {"source_provider": "LINKEDIN", "source_job_id": 4470047211.0},
)
for disguised_claims in disguised_source_claims_cases:
    disguised_outcome = evaluate_first_party_identity_request(
        _disguised_platform_id_request(disguised_claims)
    )
    assert_true(
        disguised_outcome["outcome"] != "RESOLVED",
        "HIGH-3: a discovery-platform ID disguised inside a source_claims value must remain "
        f"provenance-only, never canonical: {disguised_claims!r}",
    )
print(
    "PASS 34: discovery-platform IDs disguised inside source_claims values (slug URL, "
    "hyphen-prefixed, and numeric-float encodings) remain provenance-only (HIGH-3)."
)

# 35. Review MEDIUM-1: incoherent first-party timestamps must fail closed -- a first-party
# observed_at earlier than the discovery lead's own observed_at is temporally impossible
# (the posting cannot have been first-party-verified before it was even discovered), and a
# first-party observed_at far later than the run's own processed_at must not durably lock a
# future-dated Last_Verified into the ledger.
discovery_observed_at = json.loads(requests[0]["discovery_log_record"]["Notes"])["observed_at"]
assert_true(
    discovery_observed_at == "2026-09-26T00:46:12+00:00",
    "sanity: discovery lead's own observed_at must match the fixture baseline",
)
earlier_than_discovery = copy.deepcopy(requests[0])
earlier_than_discovery["first_party_observation"]["observed_at"] = "2026-09-25T00:00:00+00:00"
earlier_than_discovery_outcome = evaluate_first_party_identity_request(earlier_than_discovery)
assert_true(
    earlier_than_discovery_outcome["outcome"] != "RESOLVED",
    "MEDIUM-1: a first-party observed_at earlier than the discovery lead's own observed_at is "
    "temporally incoherent and must fail closed, not RESOLVE",
)

future_timestamp_lock = copy.deepcopy(requests[0])
future_timestamp_lock["first_party_observation"]["observed_at"] = "2099-01-01T00:00:00+00:00"
future_timestamp_lock_state = _seed_lead_provenance(None, future_timestamp_lock)
future_timestamp_lock_plan = build_first_party_identity_resolution_mutation_plan(
    [future_timestamp_lock],
    future_timestamp_lock_state,
    run_id="FPIR_FUTURE_TIMESTAMP_LOCK",
    processed_at="2026-09-26T14:00:00-04:00",
)
assert_true(
    future_timestamp_lock_plan["jobs_mutations"] == [],
    "MEDIUM-1: a first-party observed_at far later than the run's processed_at must fail closed, "
    "not durably lock a future-dated Last_Verified into the ledger",
)
print(
    "PASS 35: first-party timestamps earlier than discovery or later than processed_at fail "
    "closed, including the future-timestamp lock regression (MEDIUM-1)."
)

# 36. Review MEDIUM-2: the same exact ATS posting must converge to the Slice-1 canonical
# employer namespace. A Greenhouse-hosted posting (boards.greenhouse.io/acme/jobs/4012345)
# carries an ATS-qualified canonical identity of GREENHOUSE:ACME under Slice-1's own
# discovery_lead.py parsing convention; a first-party observation supplying the bare employer
# identity "ACME" for the identical posting must not diverge into a separate ACME::4012345
# canonical Job_ID.
greenhouse_discovery_record = {
    "Run_ID": "PROD_GREENHOUSE_NAMESPACE",
    "Timestamp": "2026-09-26T16:00:00-04:00",
    "Stage": "IDENTITY_RESOLUTION",
    "Source": "GMAIL",
    "Job_ID": None,
    "Status": "VERIFICATION_REQUIRED",
    "Error_Code": None,
    "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET",
    "Notes": json.dumps(
        {
            "discovery_lead_id": "LEAD_GREENHOUSE_ACME_4012345",
            "source_message_id": "MSG_GREENHOUSE_ACME",
            "source_thread_id": "MSG_GREENHOUSE_ACME",
            "observed_at": "2026-09-26T00:00:00+00:00",
            "discovery_urls": ["https://boards.greenhouse.io/acme/jobs/4012345"],
            "employer_text": "Acme Corporation",
            "role_text": "Data Analyst",
            "requisition_text": None,
            "source_claims": {"source_provider": "GREENHOUSE"},
            "exact_employer_identity": None,
            "exact_requisition_id": None,
        }
    ),
}
greenhouse_first_party_observation = {
    "observed_at": "2026-09-26T12:00:00-04:00",
    "source_kind": "FIRST_PARTY_DIRECT",
    "official_url": "https://boards.greenhouse.io/acme/jobs/4012345",
    "observed_employer_name": "Acme Corporation",
    "observed_role_title": "Data Analyst",
    "employer_binding_status": "VERIFIED",
    "employer_binding_basis": "Official Acme Greenhouse careers posting for the same role.",
    "exact_employer_identity": "ACME",
    "requisition_status": "EXACT",
    "exact_requisition_id": "4012345",
    "requisition_evidence": "Official Acme Greenhouse posting displays Job ID 4012345.",
    "requisition_authority": "EMPLOYER_OR_ATS_FIRST_PARTY",
}
greenhouse_outcome = evaluate_first_party_identity_request(
    {
        "discovery_log_record": greenhouse_discovery_record,
        "first_party_observation": greenhouse_first_party_observation,
    }
)
assert_true(
    greenhouse_outcome["outcome"] != "RESOLVED"
    or greenhouse_outcome["operational_job_id"] == "GREENHOUSE:ACME::4012345",
    "MEDIUM-2: the same exact ATS posting must converge to the Slice-1 canonical employer namespace "
    "(GREENHOUSE:ACME), not diverge into a bare-employer key: "
    f"{greenhouse_outcome.get('operational_job_id')!r}",
)
print(
    "PASS 36: a bare-employer first-party identity for a Greenhouse-hosted posting must converge to "
    "the Slice-1 canonical ATS-qualified namespace, not diverge into ACME::4012345 (MEDIUM-2)."
)

print("ALL FIRST_PARTY_IDENTITY_RESOLUTION_V1 TESTS PASSED")


# ---------------------------------------------------------------------------
# Regression cases 37-40: production/reviewer-earned regressions.
# These cases must PASS on the repaired runtime. A single aggregate failure
# collector is used instead of assert_true's immediate raise so every
# remaining failure stays visible in one run rather than the script halting
# at the first one.
# ---------------------------------------------------------------------------

_regression_failures: list[str] = []


def regression_check(condition: bool, message: str) -> None:
    if not condition:
        _regression_failures.append(message)


# 37. HIGH: browser/WHATWG authority-parsing bypass. A literal backslash
# immediately after the scheme separator (instead of, or mixed with, the
# ordinary '//') is a synonym for '/' in the WHATWG "special authority
# slashes" state, so real browsers / employer-site link resolution parse
# these forms exactly like the ordinary https://<host>/... authority. The
# runtime's own handling (`official_url.replace("\\", "/")`) does not
# reproduce that: it turns a leading "://\\" into ":///" (an extra empty
# path segment), urlparse then returns hostname=None, and a None hostname is
# silently treated as "not a denied host" instead of a parse failure that
# must fail closed.
for bad_authority_url in (
    "https://\\www.linkedin.com/jobs/view/4470047211",
    "https://\\/linkedin.com/x",
):
    authority_bypass_req = copy.deepcopy(requests[0])
    authority_bypass_req["first_party_observation"]["official_url"] = bad_authority_url
    authority_bypass_outcome = evaluate_first_party_identity_request(authority_bypass_req)
    regression_check(
        authority_bypass_outcome["outcome"] != "RESOLVED",
        "HIGH (37): a browser/WHATWG-equivalent backslash-delimited third-party "
        f"authority must remain forbidden as Official_URL, not RESOLVE: {bad_authority_url!r} "
        f"(got outcome={authority_bypass_outcome['outcome']!r}, "
        f"operational_job_id={authority_bypass_outcome.get('operational_job_id')!r})",
    )
print("PASS 37: browser/WHATWG authority-parsing Official_URL bypass fails closed (HIGH).")


# 38. MEDIUM: ATS namespace consistency for known ATS (Greenhouse) URLs.
def _greenhouse_request(
    *,
    discovery_lead_id: str,
    official_url: str,
    discovery_employer_text: str,
    observed_employer_name: str,
    exact_employer_identity: str,
    exact_requisition_id: str,
    requisition_evidence: str,
) -> dict:
    discovery_log_record = {
        "Run_ID": "PROD_GREENHOUSE_38",
        "Timestamp": "2026-09-26T16:00:00-04:00",
        "Stage": "IDENTITY_RESOLUTION",
        "Source": "GMAIL",
        "Job_ID": None,
        "Status": "VERIFICATION_REQUIRED",
        "Error_Code": None,
        "Engine_Baseline": "SUPERVISED_PRODUCTION_V1_SLICE_1_GMAIL_TO_SHEET",
        "Notes": json.dumps(
            {
                "discovery_lead_id": discovery_lead_id,
                "source_message_id": f"MSG_{discovery_lead_id}",
                "source_thread_id": f"MSG_{discovery_lead_id}",
                "observed_at": "2026-09-26T00:00:00+00:00",
                "discovery_urls": [official_url],
                "employer_text": discovery_employer_text,
                "role_text": "Data Analyst",
                "requisition_text": None,
                "source_claims": {"source_provider": "GREENHOUSE"},
                "exact_employer_identity": None,
                "exact_requisition_id": None,
            }
        ),
    }
    first_party_observation = {
        "observed_at": "2026-09-26T12:00:00-04:00",
        "source_kind": "FIRST_PARTY_DIRECT",
        "official_url": official_url,
        "observed_employer_name": observed_employer_name,
        "observed_role_title": "Data Analyst",
        "employer_binding_status": "VERIFIED",
        "employer_binding_basis": "Official Greenhouse careers posting for the same role.",
        "exact_employer_identity": exact_employer_identity,
        "requisition_status": "EXACT",
        "exact_requisition_id": exact_requisition_id,
        "requisition_evidence": requisition_evidence,
        "requisition_authority": "EMPLOYER_OR_ATS_FIRST_PARTY",
    }
    return {"discovery_log_record": discovery_log_record, "first_party_observation": first_party_observation}


# 38a: a browser-equivalent backslash authority/path variant of a known ATS
# URL must converge to the same ATS-qualified canonical namespace
# (GREENHOUSE:ACME) as the ordinary slash form, not diverge into a bare
# employer key.
greenhouse_slash_outcome = evaluate_first_party_identity_request(
    _greenhouse_request(
        discovery_lead_id="LEAD_GREENHOUSE_38_SLASH",
        official_url="https://boards.greenhouse.io/acme/jobs/4012345",
        discovery_employer_text="Acme Corporation",
        observed_employer_name="Acme Corporation",
        exact_employer_identity="ACME",
        exact_requisition_id="4012345",
        requisition_evidence="Official Acme Greenhouse posting displays Job ID 4012345.",
    )
)
assert_true(
    greenhouse_slash_outcome["outcome"] == "RESOLVED"
    and greenhouse_slash_outcome["operational_job_id"] == "GREENHOUSE:ACME::4012345",
    "sanity (38a): the ordinary slash-form Greenhouse posting must resolve to the "
    f"ATS-qualified namespace, got {greenhouse_slash_outcome!r}",
)
greenhouse_backslash_outcome = evaluate_first_party_identity_request(
    _greenhouse_request(
        discovery_lead_id="LEAD_GREENHOUSE_38_BACKSLASH",
        official_url="https://boards.greenhouse.io\\acme/jobs/4012345",
        discovery_employer_text="Acme Corporation",
        observed_employer_name="Acme Corporation",
        exact_employer_identity="ACME",
        exact_requisition_id="4012345",
        requisition_evidence="Official Acme Greenhouse posting displays Job ID 4012345.",
    )
)
regression_check(
    greenhouse_backslash_outcome["outcome"] != "RESOLVED"
    or greenhouse_backslash_outcome["operational_job_id"] == "GREENHOUSE:ACME::4012345",
    "MEDIUM (38a): a browser-equivalent backslash path/authority variant of a known "
    "Greenhouse ATS URL must converge to the GREENHOUSE:ACME canonical namespace, not "
    f"diverge into a bare-employer key: {greenhouse_backslash_outcome.get('operational_job_id')!r}",
)

# 38b: URL-derived ATS employer identity (GREENHOUSE:ACME, from the 'acme'
# Greenhouse board) conflicting with the supplied verified
# exact_employer_identity/provenance employer identity ("OTHERCORP") must
# fail closed, not silently RESOLVE using the URL-derived identity alone.
greenhouse_employer_conflict_outcome = evaluate_first_party_identity_request(
    _greenhouse_request(
        discovery_lead_id="LEAD_GREENHOUSE_38_EMPLOYER_CONFLICT",
        official_url="https://boards.greenhouse.io/acme/jobs/4012345",
        discovery_employer_text="Othercorp Inc",
        observed_employer_name="Othercorp Inc",
        exact_employer_identity="OTHERCORP",
        exact_requisition_id="4012345",
        requisition_evidence="Official Othercorp posting displays Job ID 4012345.",
    )
)
regression_check(
    greenhouse_employer_conflict_outcome["outcome"] != "RESOLVED",
    "MEDIUM (38b): a URL-derived ATS employer identity (GREENHOUSE:ACME) conflicting "
    "with the supplied verified exact_employer_identity (OTHERCORP) must fail closed, "
    f"not RESOLVE: {greenhouse_employer_conflict_outcome!r}",
)

# 38c: URL-derived ATS requisition ID (4012345, from the Greenhouse posting
# path) conflicting with the supplied exact_requisition_id ("9999999") must
# fail closed, not silently RESOLVE using the supplied requisition alone.
greenhouse_requisition_conflict_outcome = evaluate_first_party_identity_request(
    _greenhouse_request(
        discovery_lead_id="LEAD_GREENHOUSE_38_REQUISITION_CONFLICT",
        official_url="https://boards.greenhouse.io/acme/jobs/4012345",
        discovery_employer_text="Acme Corporation",
        observed_employer_name="Acme Corporation",
        exact_employer_identity="ACME",
        exact_requisition_id="9999999",
        requisition_evidence="Official Acme Greenhouse posting displays Job ID 9999999.",
    )
)
regression_check(
    greenhouse_requisition_conflict_outcome["outcome"] != "RESOLVED",
    "MEDIUM (38c): a URL-derived ATS requisition ID (4012345) conflicting with the "
    "supplied exact_requisition_id (9999999) must fail closed, not RESOLVE: "
    f"{greenhouse_requisition_conflict_outcome!r}",
)
print("PASS 38: ATS namespace consistency (Greenhouse) converges and contradictions fail closed (MEDIUM).")


# 39. MEDIUM: discovery-platform ID leakage via a non-denylisted redirect
# host and via source_claims mapping KEYS (not just values).

# 39a: a Gmail/Google redirect wrapper URL (host is google.com, not a denied
# third-party discovery host) containing a percent-encoded LinkedIn job URL
# with ID 4470047211 must still make that ID provenance-only, never
# canonical -- the identifier must not become the exact_requisition_id
# merely because the wrapping host itself is absent from the denylist.
gmail_redirect_req = copy.deepcopy(requests[0])
gmail_redirect_notes = json.loads(gmail_redirect_req["discovery_log_record"]["Notes"])
gmail_redirect_notes["discovery_urls"] = [
    "https://www.google.com/url?q=https%3A%2F%2Fwww.linkedin.com%2Fjobs%2Fview%2F4470047211%2F&sa=D"
]
gmail_redirect_notes["source_claims"] = {"source_provider": "GMAIL_REDIRECT"}
gmail_redirect_req["discovery_log_record"]["Notes"] = json.dumps(gmail_redirect_notes)
gmail_redirect_req["first_party_observation"]["exact_requisition_id"] = "4470047211"
gmail_redirect_req["first_party_observation"]["requisition_evidence"] = (
    "Official MTA Careers posting displays Job ID 4470047211."
)
gmail_redirect_outcome = evaluate_first_party_identity_request(gmail_redirect_req)
regression_check(
    gmail_redirect_outcome["outcome"] != "RESOLVED",
    "MEDIUM (39a): a discovery-platform ID reachable only through a Gmail/Google "
    "redirect wrapper (non-denylisted host, percent-encoded LinkedIn URL) must remain "
    f"provenance-only, not RESOLVE: {gmail_redirect_outcome!r}",
)

# 39b: source_claims mapping KEYS carrying the discovery-platform ID (not
# just values) must also be scanned and forbidden.
source_claims_key_req = copy.deepcopy(requests[0])
source_claims_key_notes = json.loads(source_claims_key_req["discovery_log_record"]["Notes"])
source_claims_key_notes["source_claims"] = {"ids": {"4470047211": True}}
source_claims_key_notes["discovery_urls"] = []
source_claims_key_req["discovery_log_record"]["Notes"] = json.dumps(source_claims_key_notes)
source_claims_key_req["first_party_observation"]["exact_requisition_id"] = "4470047211"
source_claims_key_req["first_party_observation"]["requisition_evidence"] = (
    "Official MTA Careers posting displays Job ID 4470047211."
)
source_claims_key_outcome = evaluate_first_party_identity_request(source_claims_key_req)
regression_check(
    source_claims_key_outcome["outcome"] != "RESOLVED",
    "MEDIUM (39b): a discovery-platform ID stored as a source_claims mapping KEY (not "
    f"a value) must remain provenance-only, not RESOLVE: {source_claims_key_outcome!r}",
)
print("PASS 39: discovery-platform IDs in redirect wrappers and source_claims keys remain provenance-only (MEDIUM).")


# 40. LOW: Slice-1 build_mutation_plan's own returned next_state must match
# durable rehydration (state_from_ledger_rows) for
# first_party_eligible_lead_ids / first_party_durable_provenance when it
# emits an IDENTITY_RESOLUTION/VERIFICATION_REQUIRED row, and chaining
# first-party resolution directly on that next_state must not be falsely
# held for "missing" durable provenance that in fact was just established.
slice1_notes = json.loads(requests[0]["discovery_log_record"]["Notes"])
slice1_lead = {
    "discovery_lead_id": slice1_notes["discovery_lead_id"],
    "source": "GMAIL",
    "source_message_id": slice1_notes["source_message_id"],
    "source_thread_id": slice1_notes.get("source_thread_id"),
    "observed_at": slice1_notes["observed_at"],
    "discovery_urls": slice1_notes["discovery_urls"],
    "employer_text": slice1_notes["employer_text"],
    "role_text": slice1_notes["role_text"],
    "requisition_text": slice1_notes.get("requisition_text"),
    "source_claims": slice1_notes["source_claims"],
    "exact_employer_identity": slice1_notes.get("exact_employer_identity"),
    "exact_requisition_id": slice1_notes.get("exact_requisition_id"),
    "identity_resolution_status": "VERIFICATION_REQUIRED",
}
slice1_plan = build_mutation_plan(
    [slice1_lead], None, run_id="FPIR_TEST40_SLICE1", processed_at="2026-09-26T16:05:00-04:00"
)
assert_true(
    len(slice1_plan["log_mutations"]) == 1
    and slice1_plan["log_mutations"][0]["Stage"] == "IDENTITY_RESOLUTION"
    and slice1_plan["log_mutations"][0]["Status"] == "VERIFICATION_REQUIRED",
    "sanity (40): the unresolved Slice-1 lead must produce exactly one durable "
    "IDENTITY_RESOLUTION/VERIFICATION_REQUIRED LOG row",
)
slice1_rehydrated = state_from_ledger_rows(
    slice1_plan["jobs_mutations"], slice1_plan["log_mutations"]
)
regression_check(
    slice1_plan["next_state"]["first_party_eligible_lead_ids"]
    == slice1_rehydrated["first_party_eligible_lead_ids"],
    "LOW (40): build_mutation_plan's own returned next_state must match durable "
    "rehydration of the LOG row it just emitted for first_party_eligible_lead_ids; got "
    f"plan={slice1_plan['next_state']['first_party_eligible_lead_ids']!r} vs "
    f"rehydrated={slice1_rehydrated['first_party_eligible_lead_ids']!r}",
)
regression_check(
    slice1_plan["next_state"]["first_party_durable_provenance"]
    == slice1_rehydrated["first_party_durable_provenance"],
    "LOW (40): build_mutation_plan's own returned next_state must match durable "
    "rehydration of the LOG row it just emitted for first_party_durable_provenance; got "
    f"plan keys={sorted(slice1_plan['next_state']['first_party_durable_provenance'])!r} vs "
    f"rehydrated keys={sorted(slice1_rehydrated['first_party_durable_provenance'])!r}",
)

slice1_chained_request = {
    "discovery_log_record": requests[0]["discovery_log_record"],
    "first_party_observation": requests[0]["first_party_observation"],
}
slice1_chained_plan = build_first_party_identity_resolution_mutation_plan(
    [slice1_chained_request],
    slice1_plan["next_state"],
    run_id="FPIR_TEST40_CHAINED",
    processed_at="2026-09-26T16:06:00-04:00",
)
regression_check(
    len(slice1_chained_plan["jobs_mutations"]) == 1
    and slice1_chained_plan["jobs_mutations"][0]["Job_ID"] == by_id["MTA_17407"]["expected_job_id"],
    "LOW (40): chaining first-party resolution directly on build_mutation_plan's own "
    "next_state must not be falsely held for missing durable provenance when that "
    f"provenance was legitimately just established: {slice1_chained_plan!r}",
)
print("PASS 40: build_mutation_plan next_state matches durable rehydration and supports direct chaining (LOW).")


if _regression_failures:
    print(f"REGRESSION FAILURES REPRODUCED (37-40): {len(_regression_failures)}")
    for _failure_message in _regression_failures:
        print(f"  - {_failure_message}")
    raise AssertionError(
        "regression failures remain in independent-review cases 37-40 "
        "(see REGRESSION FAILURES above)"
    )
print("ALL FIRST_PARTY_IDENTITY_RESOLUTION_V1 REGRESSION CASES 37-40 PASSED.")

# ---------------------------------------------------------------------------
# Regression cases 41-46: fresh exact-byte review findings against 6f3bc1f.
# These must fail on the rejected runtime and pass only after causal repair.
# ---------------------------------------------------------------------------
_review2_failures: list[str] = []

def review2_check(condition: bool, message: str) -> None:
    if not condition:
        _review2_failures.append(message)

# 41 HIGH: Official_URL redirect/shortener wrappers must not hide a third-party posting host.
for wrapped_url in (
    "https://www.google.com/url?q=https://www.linkedin.com/jobs/view/4470047211/&sa=D",
    "https://www.google.com/url?q=https%3A%2F%2Fwww.linkedin.com%2Fjobs%2Fview%2F4470047211%2F&sa=D",
    "https://lnkd.in/abc123",
):
    q41 = copy.deepcopy(requests[0])
    q41["first_party_observation"]["official_url"] = wrapped_url
    review2_check(
        evaluate_first_party_identity_request(q41)["outcome"] != "RESOLVED",
        f"HIGH 41: wrapped/shortened third-party Official_URL resolved: {wrapped_url}",
    )
print("CASE 41 exercised: Official_URL wrapper/shortener third-party host handling.")

# 42 HIGH: encoded or path-embedded discovery-platform IDs must remain provenance-only.
for discovery_url in (
    "https://www.linkedin.com/jobs/view/%34%34%37%30%30%34%37%32%31%31/",
    "https://urldefense.com/v3/__https://www.linkedin.com/jobs/view/4470047211/__;!!abc$",
):
    q42 = copy.deepcopy(requests[0])
    q42_notes = json.loads(q42["discovery_log_record"]["Notes"])
    q42_notes["discovery_urls"] = [discovery_url]
    q42_notes["source_claims"] = {}
    q42["discovery_log_record"]["Notes"] = json.dumps(q42_notes)
    q42["first_party_observation"]["exact_requisition_id"] = "4470047211"
    q42["first_party_observation"]["requisition_evidence"] = (
        "Official MTA Careers posting displays Job ID 4470047211."
    )
    review2_check(
        evaluate_first_party_identity_request(q42)["outcome"] != "RESOLVED",
        f"HIGH 42: encoded/path-embedded platform ID became canonical: {discovery_url}",
    )
print("CASE 42 exercised: encoded/path-embedded discovery-platform IDs.")

# 43 HIGH: discovery requisition text must not disable ATS URL requisition contradiction checks.
q43 = copy.deepcopy(requests[0])
q43_notes = json.loads(q43["discovery_log_record"]["Notes"])
q43_notes["requisition_text"] = "Job ID 4470047211"
q43_notes["source_claims"] = {"source_job_id": "4470047211"}
q43["discovery_log_record"]["Notes"] = json.dumps(q43_notes)
q43["first_party_observation"]["official_url"] = "https://boards.greenhouse.io/acme/jobs/4567890"
q43["first_party_observation"]["exact_employer_identity"] = "ACME"
q43["first_party_observation"]["exact_requisition_id"] = "9999999"
q43["first_party_observation"]["requisition_evidence"] = "Official Acme posting displays Job ID 9999999."
review2_check(
    evaluate_first_party_identity_request(q43)["outcome"] != "RESOLVED",
    "HIGH 43: discovery requisition text suppressed ATS URL requisition contradiction",
)
print("CASE 43 exercised: ATS URL requisition contradiction cannot be disabled by discovery text.")

# 44 MEDIUM: query/fragment text must never select an ATS namespace when the host is not that ATS.
q44 = copy.deepcopy(requests[0])
q44["first_party_observation"]["official_url"] = (
    "https://careers.mta.org/x#https://boards.greenhouse.io/mta/jobs/17407"
)
q44["first_party_observation"]["exact_employer_identity"] = "MTA"
q44_outcome = evaluate_first_party_identity_request(q44)
review2_check(
    q44_outcome["outcome"] != "RESOLVED"
    or q44_outcome.get("operational_job_id") == "MTA::17407",
    f"MEDIUM 44: fragment/query text selected foreign ATS namespace: {q44_outcome!r}",
)
print("CASE 44 exercised: ATS namespace derives from authoritative host/path only.")

# 45 MEDIUM: ATS-qualified Slice-1 employer identity must remain resolvable with matching official ATS URL.
for supplied_identity in ("ACME", "GREENHOUSE:ACME"):
    q45 = copy.deepcopy(requests[0])
    q45_notes = json.loads(q45["discovery_log_record"]["Notes"])
    q45_notes["employer_text"] = "Acme Corporation"
    q45_notes["role_text"] = "Data Analyst"
    q45_notes["exact_employer_identity"] = "GREENHOUSE:ACME"
    q45_notes["exact_requisition_id"] = None
    q45_notes["discovery_urls"] = ["https://boards.greenhouse.io/acme/jobs/4012345"]
    q45_notes["source_claims"] = {"source_provider": "GREENHOUSE"}
    q45["discovery_log_record"]["Notes"] = json.dumps(q45_notes)
    q45["first_party_observation"]["observed_employer_name"] = "Acme Corporation"
    q45["first_party_observation"]["observed_role_title"] = "Data Analyst"
    q45["first_party_observation"]["official_url"] = "https://boards.greenhouse.io/acme/jobs/4012345"
    q45["first_party_observation"]["exact_employer_identity"] = supplied_identity
    q45["first_party_observation"]["exact_requisition_id"] = "4012345"
    q45["first_party_observation"]["requisition_evidence"] = "Official Acme posting displays Job ID 4012345."
    q45_outcome = evaluate_first_party_identity_request(q45)
    review2_check(
        q45_outcome["outcome"] == "RESOLVED"
        and q45_outcome.get("operational_job_id") == "GREENHOUSE:ACME::4012345",
        f"MEDIUM 45: matching ATS-qualified lead stuck for supplied identity {supplied_identity}: {q45_outcome!r}",
    )
print("CASE 45 exercised: matching ATS-qualified Slice-1 employer identity remains resolvable.")

# 46 LOW: future-timestamp hold must not poison retry idempotency.
q46 = copy.deepcopy(requests[0])
q46["first_party_observation"]["observed_at"] = "2026-09-26T17:00:00-04:00"
q46_state = state_from_ledger_rows([], [q46["discovery_log_record"]])
q46_hold = build_first_party_identity_resolution_mutation_plan(
    [q46], q46_state, run_id="FPIR_REVIEW2_46_HOLD", processed_at="2026-09-26T16:59:50-04:00"
)
q46_rows = [q46["discovery_log_record"]] + [dict(row) for row in q46_hold["log_mutations"]]
q46_rehydrated = state_from_ledger_rows([], q46_rows)
q46_retry = build_first_party_identity_resolution_mutation_plan(
    [q46], q46_rehydrated, run_id="FPIR_REVIEW2_46_RETRY", processed_at="2026-09-26T17:00:10-04:00"
)
review2_check(
    len(q46_retry["jobs_mutations"]) == 1
    and q46_retry["jobs_mutations"][0]["Job_ID"] == by_id["MTA_17407"]["expected_job_id"],
    f"LOW 46: future-timestamp hold poisoned later valid retry: {q46_retry!r}",
)
print("CASE 46 exercised: future-timestamp hold does not poison a later valid retry.")

if _review2_failures:
    print(f"REVIEW2 REGRESSION FAILURES (41-46): {len(_review2_failures)}")
    for _failure_message in _review2_failures:
        print(f"  - {_failure_message}")
    raise AssertionError(
        "expected RED: fresh independent-review findings 41-46 reproduced "
        "(see REVIEW2 REGRESSION FAILURES above)"
    )
print("ALL FIRST_PARTY_IDENTITY_RESOLUTION_V1 REGRESSION CASES 41-46 PASSED.")
