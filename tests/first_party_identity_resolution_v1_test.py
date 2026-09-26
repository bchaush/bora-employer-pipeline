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

print("ALL FIRST_PARTY_IDENTITY_RESOLUTION_V1 TESTS PASSED")
