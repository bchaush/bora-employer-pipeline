"""Regression tests for SUPERVISED_PRODUCTION_V1_SLICE_2_GATES_MATCH_TRUTH_TO_SHEET.

Exercises src/supervised_analysis.py + src/production_ledger.py's
build_gate_match_mutation_plan against Slice-1-resolved operational Job_IDs,
explicit verified employer/source input, explicit upstream gate outcomes, and
the real (unmodified) analyze_job() Match Truth core running against real
golden-tests/job_analysis fixtures (GT_BSA_STRONG -> PRIORITY_APPLY,
GT_SWE_REJECT -> REJECT, GT_VAGUE_JD -> WATCH), so the projected Decision
values are genuine analyze_job() output, never fabricated by this test.

Covers: all-PASS -> Match Truth -> REVIEW_READY; upstream REJECT; upstream
HOLD/missing; discovery-claim laundering rejection; stale/mismatched
operational-analysis binding; Official_URL non-promotion; unknown operational
Job_ID; rerun idempotency; and projection of existing WATCH/REJECT/
APPLY-like decisions without reinterpretation.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from production_ledger import (  # noqa: E402
    build_gate_match_mutation_plan,
    empty_state,
    state_from_ledger_rows,
)
from supervised_analysis import GATE_ORDER, compute_employer_input_fingerprint  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


GOLDEN_ROOT = ROOT / "golden-tests" / "job_analysis"

claim_result = validate_claim_repository()
evidence_result = validate_evidence_repository()
assert_true(claim_result.get("valid") is True, f"claim repository must be valid: {claim_result}")
assert_true(evidence_result.get("valid") is True, f"evidence repository must be valid: {evidence_result}")
CLAIM_INDEX = claim_result["index"]
EVIDENCE_INDEX = evidence_result["index"]

RUN_ID = "RUN_SLICE2_TEST_001"
PROCESSED_AT = "2026-09-23T10:00:00+00:00"


def load_golden_employer_input(
    fixture_id: str,
    *,
    official_url: str | None,
    with_pre_surfacing: bool = False,
) -> dict:
    fixture_dir = GOLDEN_ROOT / fixture_id
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    extraction = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    role = extraction.get("_role_title") or fixture_id.replace("_", " ")
    structured_extraction = {k: v for k, v in extraction.items() if not str(k).startswith("_")}

    employer_verified_input = {
        "company": f"Synthetic Golden Co ({fixture_id})",
        "role": role,
        "jd_text": jd_text,
        "structured_extraction": structured_extraction,
        "role_status": "VERIFIED_LIVE",
        "source_verification_status": "VERIFIED_DIRECT",
        "date_last_verified": "2026-09-15",
        "official_url": official_url,
    }

    if with_pre_surfacing:
        observed_at = "2026-09-15T12:00:00-04:00"
        employer_verified_input["pre_surfacing_verification"] = {
            "verification_kind": "JIT_PRE_SURFACING_VERIFICATION_V1",
            "operation_run_id": f"RUN_SLICE2_TEST_{fixture_id}",
            "observed_at": observed_at,
            "source_kind": "FIRST_PARTY_DIRECT",
            "exact_url": official_url,
            "observed_company": employer_verified_input["company"],
            "observed_role": employer_verified_input["role"],
            "substantive_role_content_present": True,
            "application_route_status": "ACTIONABLE",
            "recency_observation": {
                "state": "AUTHORITATIVE_ABSOLUTE_DATE",
                "source_kind": "FIRST_PARTY_DIRECT",
                "observed_at": observed_at,
                "posted_date": "2026-09-14",
            },
            "material_conflicts": [],
            "resolved_conflicts": [],
        }

    return employer_verified_input


def make_existing_job(job_id: str, *, company: str, role: str, discovery_url: str) -> dict:
    return {
        "Op": "CREATE",
        "Job_ID": job_id,
        "Company": company,
        "Role": role,
        "Discovery_Source": "GMAIL",
        "Discovery_URL": discovery_url,
        "Official_URL": None,
        "First_Seen": "2026-09-10T09:00:00+00:00",
        "Last_Verified": "2026-09-10T09:00:00+00:00",
        "Pipeline_State": "NORMALIZED",
    }


def all_pass_gates() -> dict:
    return {
        gate_key: {
            "result": "PASS",
            "reason": f"{gate_key} verified PASS",
            "provenance": f"UPSTREAM_GATE_SYSTEM::{gate_key}",
            "verification_source": "AUTHORITATIVE",
        }
        for gate_key in GATE_ORDER
    }


def make_binding(operational_job_id: str, employer_verified_input: dict) -> dict:
    return {
        "operational_job_id": operational_job_id,
        "content_fingerprint": compute_employer_input_fingerprint(employer_verified_input),
    }


BSA_JOB_ID = "WORKDAY:ACME_BSA::R-100001"
REJECT_JOB_ID = "WORKDAY:ACME_SWE::R-100002"
WATCH_JOB_ID = "WORKDAY:ACME_VAGUE::R-100003"

BASE_JOBS = {
    BSA_JOB_ID: make_existing_job(
        BSA_JOB_ID,
        company="Acme BSA Corp (discovery)",
        role="Business Systems Analyst",
        discovery_url="https://acme.myworkdayjobs.com/en-US/Acme/job/Remote/R-100001",
    ),
    REJECT_JOB_ID: make_existing_job(
        REJECT_JOB_ID,
        company="Acme SWE Corp (discovery)",
        role="Software Engineer",
        discovery_url="https://acme.myworkdayjobs.com/en-US/Acme/job/Remote/R-100002",
    ),
    WATCH_JOB_ID: make_existing_job(
        WATCH_JOB_ID,
        company="Acme Vague Corp (discovery)",
        role="Business Operations Analyst",
        discovery_url="https://acme.myworkdayjobs.com/en-US/Acme/job/Remote/R-100003",
    ),
}


def fresh_state() -> dict:
    state = empty_state()
    state["jobs"] = copy.deepcopy(BASE_JOBS)
    return state


def run_plan(requests: list[dict], existing_state: dict) -> dict:
    return build_gate_match_mutation_plan(
        requests,
        existing_state,
        run_id=RUN_ID,
        processed_at=PROCESSED_AT,
        claim_index=CLAIM_INDEX,
        evidence_index=EVIDENCE_INDEX,
    )


# ======================================================================
# 1. All-upstream-PASS -> existing Match Truth -> REVIEW_READY, with the
#    exact-role operational Job_ID (never analyze_job's internal job_id)
#    projected onto JOBS, and Official_URL sourced only from verified
#    employer input (never the Discovery_URL).
# ======================================================================
bsa_official_url = "https://acme.com/careers/business-systems-analyst-R-100001"
bsa_input = load_golden_employer_input(
    "GT_BSA_STRONG", official_url=bsa_official_url, with_pre_surfacing=True
)
plan1 = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": bsa_input,
            "upstream_gates": all_pass_gates(),
            "analysis_binding": make_binding(BSA_JOB_ID, bsa_input),
        }
    ],
    fresh_state(),
)
assert_true(len(plan1["jobs_mutations"]) == 1, f"expected exactly one JOBS mutation, got {len(plan1['jobs_mutations'])}")
bsa_mutation = plan1["jobs_mutations"][0]
assert_true(bsa_mutation["Job_ID"] == BSA_JOB_ID, "JOBS mutation must key on the operational Job_ID")
assert_true(bsa_mutation["Op"] == "UPDATE", "Slice 2 must never CREATE a JOBS row")
assert_true(bsa_mutation["Pipeline_State"] == "REVIEW_READY", f"expected REVIEW_READY, got {bsa_mutation['Pipeline_State']}")
assert_true(bsa_mutation["Match_State"] == "ANALYZED", f"expected ANALYZED, got {bsa_mutation['Match_State']}")
assert_true(bsa_mutation["Decision"] == "PRIORITY_APPLY", f"expected PRIORITY_APPLY (GT_BSA_STRONG), got {bsa_mutation['Decision']}")
for gate_field in ("Freshness_State", "Geography_State", "OPT_Screen_State", "Candidate_Condition_State", "Threshold_State"):
    assert_true(bsa_mutation[gate_field] == "PASS", f"{gate_field} must be PASS when all upstream gates pass")
assert_true(bsa_mutation["Official_URL"] == bsa_official_url, "Official_URL must come from explicit verified employer input")
assert_true(bsa_mutation["Discovery_URL"] == BASE_JOBS[BSA_JOB_ID]["Discovery_URL"], "Slice 1 Discovery_URL must be preserved unchanged")
assert_true(bsa_mutation["Company"] == BASE_JOBS[BSA_JOB_ID]["Company"], "Slice 1 identity fields must be preserved")
assert_true(bsa_mutation["First_Seen"] == BASE_JOBS[BSA_JOB_ID]["First_Seen"], "Slice 1 First_Seen must be preserved")
forbidden = {"Bora_Decision", "Package_Status", "Application_Status"}
assert_true(not (forbidden & set(bsa_mutation.keys())), f"Slice 2 must never write pursuit/package/application state: {bsa_mutation.keys()}")
review_log = [m for m in plan1["log_mutations"] if m["Job_ID"] == BSA_JOB_ID]
assert_true(len(review_log) == 1 and review_log[0]["Status"] == "REVIEW_READY", "exactly one REVIEW_READY LOG entry expected")
review_notes = json.loads(review_log[0]["Notes"])
assert_true(review_notes["analysis_decision"] == "PRIORITY_APPLY", "LOG must durably preserve the Match Truth decision")
assert_true(
    isinstance(review_notes["analysis_job_id"], str)
    and review_notes["analysis_job_id"]
    and review_notes["analysis_job_id"] != BSA_JOB_ID,
    "analysis-internal job_id must be retained as provenance but must remain distinct from operational exact-role Job_ID",
)
print("PASS 1: all-upstream-PASS reaches existing Match Truth and projects REVIEW_READY without promoting Discovery_URL; LOG preserves the distinct analysis identity and decision.")


# ======================================================================
# 2. Any upstream REJECT terminates before Match Truth -> UPSTREAM_REJECTED.
# ======================================================================
reject_gates = all_pass_gates()
reject_gates["geography"] = {
    "result": "REJECT",
    "reason": "employer geography exclusion",
    "provenance": "UPSTREAM_GATE_SYSTEM::geography",
    "verification_source": "AUTHORITATIVE",
}
plan2 = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": bsa_input,
            "upstream_gates": reject_gates,
            "analysis_binding": make_binding(BSA_JOB_ID, bsa_input),
        }
    ],
    fresh_state(),
)
mutation2 = plan2["jobs_mutations"][0]
assert_true(mutation2["Pipeline_State"] == "UPSTREAM_REJECTED", f"expected UPSTREAM_REJECTED, got {mutation2['Pipeline_State']}")
assert_true(mutation2["Match_State"] == "NOT_REACHED", "Match Truth must not run after an upstream REJECT")
assert_true(mutation2["Decision"] is None, "Decision must not be fabricated when Match Truth did not run")
assert_true(mutation2["Geography_State"] == "REJECT", "the rejecting gate's own state must be projected")
print("PASS 2: an upstream REJECT terminates before Match Truth and produces UPSTREAM_REJECTED.")


# ======================================================================
# 3. Upstream HOLD or a missing/NOT_EVALUATED required gate terminates
#    before Match Truth -> VERIFICATION_REQUIRED (never REJECT).
# ======================================================================
hold_gates = all_pass_gates()
hold_gates["candidate_conditions"] = {
    "result": "HOLD",
    "reason": "candidate condition needs human review",
    "provenance": "UPSTREAM_GATE_SYSTEM::candidate_conditions",
    "verification_source": "AUTHORITATIVE",
}
plan3a = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": bsa_input,
            "upstream_gates": hold_gates,
            "analysis_binding": make_binding(BSA_JOB_ID, bsa_input),
        }
    ],
    fresh_state(),
)
mutation3a = plan3a["jobs_mutations"][0]
assert_true(mutation3a["Pipeline_State"] == "VERIFICATION_REQUIRED", f"expected VERIFICATION_REQUIRED, got {mutation3a['Pipeline_State']}")
assert_true(mutation3a["Match_State"] == "NOT_REACHED", "Match Truth must not run while a required gate is on HOLD")
assert_true(mutation3a["Candidate_Condition_State"] == "HOLD", "the holding gate's own state must be projected")

missing_gates = all_pass_gates()
del missing_gates["threshold_seniority_specialist"]
plan3b = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": bsa_input,
            "upstream_gates": missing_gates,
            "analysis_binding": make_binding(BSA_JOB_ID, bsa_input),
        }
    ],
    fresh_state(),
)
mutation3b = plan3b["jobs_mutations"][0]
assert_true(mutation3b["Pipeline_State"] == "VERIFICATION_REQUIRED", "a missing required gate must fail closed to VERIFICATION_REQUIRED")
assert_true(mutation3b["Threshold_State"] == "NOT_EVALUATED", "a missing gate must project as NOT_EVALUATED, never invented as PASS")
print("PASS 3: upstream HOLD and a missing/NOT_EVALUATED required gate both fail closed to VERIFICATION_REQUIRED without running Match Truth.")


# ======================================================================
# 4. Discovery-claim laundering: a gate claiming PASS without AUTHORITATIVE
#    verification_source (i.e. sourced from an untrusted discovery/platform
#    claim) can never satisfy that gate.
# ======================================================================
laundered_gates = all_pass_gates()
laundered_gates["opt_screen"] = {
    "result": "PASS",
    "reason": "Gmail alert said 'No sponsorship needed, OPT friendly!'",
    "provenance": "GMAIL_ALERT_TEXT",
    "verification_source": "DISCOVERY_CLAIM",
}
plan4 = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": bsa_input,
            "upstream_gates": laundered_gates,
            "analysis_binding": make_binding(BSA_JOB_ID, bsa_input),
        }
    ],
    fresh_state(),
)
mutation4 = plan4["jobs_mutations"][0]
assert_true(mutation4["Pipeline_State"] == "VERIFICATION_REQUIRED", "a discovery-claim-laundered PASS must never unlock Match Truth")
assert_true(mutation4["Match_State"] == "NOT_REACHED", "Match Truth must not run on a laundered gate PASS")
assert_true(mutation4["OPT_Screen_State"] == "NOT_EVALUATED", "a laundered PASS must be downgraded to NOT_EVALUATED, never trusted")
log4 = [m for m in plan4["log_mutations"] if m["Job_ID"] == BSA_JOB_ID][0]
notes4 = json.loads(log4["Notes"])
assert_true(
    notes4["gate_details"]["opt_screen"]["laundering_rejected"] is True,
    "LOG provenance must record that the discovery-claim PASS was rejected as laundering, not silently dropped",
)
print("PASS 4: a discovery/platform claim can never satisfy a gate; PASS is only trusted from AUTHORITATIVE verification_source.")


# ======================================================================
# 5. Stale/mismatched operational-to-analysis binding fails closed even
#    when every upstream gate is PASS.
# ======================================================================
stale_binding_input = load_golden_employer_input("GT_BSA_STRONG", official_url=bsa_official_url)
stale_binding_input["jd_text"] = stale_binding_input["jd_text"] + "\nSTALE_MUTATION_MARKER"
stale_binding = make_binding(BSA_JOB_ID, stale_binding_input)  # fingerprint of the OLD content
plan5 = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": bsa_input,  # current content differs from what stale_binding was computed over
            "upstream_gates": all_pass_gates(),
            "analysis_binding": stale_binding,
        }
    ],
    fresh_state(),
)
assert_true(
    len(plan5["jobs_mutations"]) == 0,
    "a stale/mismatched analysis binding must not mutate the operational JOBS row at all",
)
log5 = [m for m in plan5["log_mutations"] if m["Job_ID"] == BSA_JOB_ID][0]
assert_true(
    log5["Status"] == "VERIFICATION_REQUIRED",
    "a stale/mismatched analysis binding must fail visibly to VERIFICATION_REQUIRED",
)
notes5 = json.loads(log5["Notes"])
assert_true(notes5["binding_ok"] is False, "LOG must record that the analysis binding did not resolve")
print("PASS 5: a stale/mismatched operational-to-analysis binding fails closed with a visible LOG hold and zero JOBS mutation.")


# ======================================================================
# 6. Official_URL non-promotion: Discovery_URL is never silently promoted,
#    and a fabricated discovery_claims value is never consulted either.
# ======================================================================
no_official_input = load_golden_employer_input("GT_BSA_STRONG", official_url=None)
plan6 = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": no_official_input,
            "upstream_gates": all_pass_gates(),
            "analysis_binding": make_binding(BSA_JOB_ID, no_official_input),
            "discovery_claims": {"official_url": "https://not-a-real-employer-source.example/job"},
        }
    ],
    fresh_state(),
)
mutation6 = plan6["jobs_mutations"][0]
assert_true(mutation6["Official_URL"] is None, "Official_URL must stay null, never promoted from Discovery_URL or discovery_claims")
assert_true(mutation6["Discovery_URL"] == BASE_JOBS[BSA_JOB_ID]["Discovery_URL"], "Discovery_URL itself must remain untouched")
print("PASS 6: Official_URL is never silently promoted from Discovery_URL or an untrusted discovery_claims value.")


# ======================================================================
# 7. Unknown operational Job_ID (no Slice-1-resolved row) fails closed
#    without creating a JOBS row.
# ======================================================================
unknown_job_id = "WORKDAY:UNKNOWN_EMPLOYER::R-999999"
plan7 = run_plan(
    [
        {
            "operational_job_id": unknown_job_id,
            "employer_verified_input": bsa_input,
            "upstream_gates": all_pass_gates(),
            "analysis_binding": make_binding(unknown_job_id, bsa_input),
        }
    ],
    fresh_state(),
)
assert_true(len(plan7["jobs_mutations"]) == 0, "Slice 2 must never create a new operational JOBS row")
error_logs7 = [m for m in plan7["log_mutations"] if m["Job_ID"] == unknown_job_id]
assert_true(len(error_logs7) == 1 and error_logs7[0]["Error_Code"] == "UNKNOWN_OPERATIONAL_JOB_ID", "unknown operational Job_ID must fail visibly")
print("PASS 7: an operational Job_ID with no Slice-1-resolved row fails closed without creating a JOBS row.")


# ======================================================================
# 8. Rerun idempotency: reprocessing an unchanged verified employer/gate
#    state produces zero further mutations, including after a full
#    rehydration from durable JOBS/LOG rows.
# ======================================================================
base_state_8 = fresh_state()
request_8 = {
    "operational_job_id": BSA_JOB_ID,
    "employer_verified_input": bsa_input,
    "upstream_gates": all_pass_gates(),
    "analysis_binding": make_binding(BSA_JOB_ID, bsa_input),
}
first_plan8 = run_plan([request_8], base_state_8)
assert_true(len(first_plan8["jobs_mutations"]) == 1, "first run must produce exactly one JOBS mutation")

rerun_plan8 = run_plan([request_8], first_plan8["next_state"])
assert_true(len(rerun_plan8["jobs_mutations"]) == 0, f"rerun of unchanged state must produce zero JOBS mutations, got {len(rerun_plan8['jobs_mutations'])}")
assert_true(len(rerun_plan8["log_mutations"]) == 0, f"rerun of unchanged state must produce zero LOG mutations, got {len(rerun_plan8['log_mutations'])}")

durable_state_8 = state_from_ledger_rows(
    list(first_plan8["next_state"]["jobs"].values()),
    first_plan8["log_mutations"],
)
rehydrated_rerun_8 = run_plan([request_8], durable_state_8)
assert_true(
    len(rehydrated_rerun_8["jobs_mutations"]) == 0,
    "reprocessing the same verified state after a full durable-row rehydration must still converge to zero mutations",
)
print("PASS 8: rerun idempotency holds directly and after full durable JOBS/LOG rehydration.")


# ======================================================================
# 9. Projection of existing WATCH/REJECT/APPLY-like decisions without
#    reinterpretation: Pipeline_State is REVIEW_READY purely because Match
#    Truth was reached, independent of how favorable its decision is.
# ======================================================================
reject_input = load_golden_employer_input("GT_SWE_REJECT", official_url="https://acme.com/careers/swe-R-100002")
plan9_reject = run_plan(
    [
        {
            "operational_job_id": REJECT_JOB_ID,
            "employer_verified_input": reject_input,
            "upstream_gates": all_pass_gates(),
            "analysis_binding": make_binding(REJECT_JOB_ID, reject_input),
        }
    ],
    fresh_state(),
)
reject_mutation = plan9_reject["jobs_mutations"][0]
assert_true(reject_mutation["Decision"] == "REJECT", f"GT_SWE_REJECT must project a verbatim REJECT decision, got {reject_mutation['Decision']}")
assert_true(reject_mutation["Pipeline_State"] == "REVIEW_READY", "Match Truth reaching REJECT is still REVIEW_READY (review eligibility, not automatic pursuit or rerouting)")

watch_input = load_golden_employer_input("GT_VAGUE_JD", official_url="https://acme.com/careers/vague-R-100003")
plan9_watch = run_plan(
    [
        {
            "operational_job_id": WATCH_JOB_ID,
            "employer_verified_input": watch_input,
            "upstream_gates": all_pass_gates(),
            "analysis_binding": make_binding(WATCH_JOB_ID, watch_input),
        }
    ],
    fresh_state(),
)
watch_mutation = plan9_watch["jobs_mutations"][0]
assert_true(watch_mutation["Decision"] == "WATCH", f"GT_VAGUE_JD must project a verbatim WATCH decision, got {watch_mutation['Decision']}")
assert_true(watch_mutation["Pipeline_State"] == "REVIEW_READY", "Match Truth reaching WATCH is still REVIEW_READY")

assert_true(bsa_mutation["Decision"] == "PRIORITY_APPLY", "sanity: PASS 1's APPLY-like PRIORITY_APPLY projection remains verbatim")
print("PASS 9: existing WATCH/REJECT/APPLY-like decisions are projected verbatim under REVIEW_READY, never reinterpreted.")


# ======================================================================
# 10. A later current-state rejection must not erase the earlier Match
#     Truth analysis from durable LOG history. JOBS reflects current
#     actionability; LOG preserves prior analysis identity/decision.
# ======================================================================
later_reject_gates = all_pass_gates()
later_reject_gates["freshness"] = {
    "result": "REJECT",
    "reason": "later authoritative verification found the posting closed",
    "provenance": "EMPLOYER_DIRECT::later_verification",
    "verification_source": "AUTHORITATIVE",
}
later_plan = run_plan(
    [
        {
            "operational_job_id": BSA_JOB_ID,
            "employer_verified_input": bsa_input,
            "upstream_gates": later_reject_gates,
            "analysis_binding": make_binding(BSA_JOB_ID, bsa_input),
        }
    ],
    plan1["next_state"],
)
later_mutation = later_plan["jobs_mutations"][0]
assert_true(later_mutation["Pipeline_State"] == "UPSTREAM_REJECTED", "later verified closure must change current pipeline state")
assert_true(later_mutation["Match_State"] == "NOT_REACHED", "later upstream rejection must not rerun Match Truth")
assert_true(later_mutation["Decision"] is None, "current JOBS decision must not pretend a fresh Match Truth run occurred after upstream rejection")
historical_notes = json.loads(plan1["log_mutations"][0]["Notes"])
assert_true(historical_notes["match_state"] == "ANALYZED", "earlier LOG must preserve that Match Truth was reached")
assert_true(historical_notes["analysis_decision"] == "PRIORITY_APPLY", "earlier LOG must preserve the historical Match Truth decision")
assert_true(isinstance(historical_notes["analysis_job_id"], str) and historical_notes["analysis_job_id"], "earlier LOG must preserve analysis identity")
print("PASS 10: later non-actionability changes current JOBS state without erasing historical Match Truth from durable LOG provenance.")

print("ALL supervised_production_v1_slice2_gates_match_truth_to_sheet_test CHECKS PASSED")
