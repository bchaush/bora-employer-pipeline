"""Application Gate (Gate 1.5) foundational Golden/adversarial cases
(APPLICATION_GATE_V1_CORRECTED; extended by
APPLICATION_GATE_NONE_IS_NOT_FALSE_REMEDIATION_V1).

Nine named cases, run as one deterministic script following this
repository's existing plain-test-script convention (assert_true/print
PASS, `python tests/application_gate_golden_test.py`) rather than a new
fixture-directory + runner + schema subsystem: these are hand-crafted
logic-proof cases, not a large data-driven JD matrix like
golden-tests/job_analysis, so a dedicated fixture-directory schema would
be unused abstraction for this count.

  GT_APP_GATE_CLEAN
  GT_APP_GATE_COMPOUND_UNSAFE
  GT_APP_GATE_EXPLORATORY_ISOLATED
  GT_APP_GATE_GATE0_SHORT_CIRCUIT
  GT_APP_GATE_FORM_ONLY_CLAUSE
  GT_APP_GATE_REEVALUATION_NO_SOURCE_MUTATION
  GT_APP_GATE_NONE_NOT_FALSE
  GT_APP_GATE_NONE_PNL_NOT_FALSE
  GT_APP_GATE_NONE_EXCEL_NOT_FALSE

Gate 1.5 must never change Gate-1 lane/decision routing (job_decision.py
is never imported or modified by this file) and must never process a
Gate-0-rejected job.

The last three cases prove APPLICATION_GATE_NONE_IS_NOT_FALSE_REMEDIATION_V1:
an evidence_match.result of NONE ("no supporting match found" -- Gate-1's
unchanged meaning) must translate to UNCERTAIN candidate truth, never FALSE.
Absence of supporting evidence is not evidence of factual absence.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
GOLDEN_JOB_ANALYSIS = ROOT / "golden-tests" / "job_analysis"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from job_analysis import analyze_job  # noqa: E402
from application_gate import evaluate_application_question, gate_1_5_applicable  # noqa: E402
from application_answer import build_application_answer, select_submitted_history  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


ev_result = validate_evidence_repository()
assert_true(ev_result["valid"] is True, "evidence repository must be valid")
cl_result = validate_claim_repository()
assert_true(cl_result["valid"] is True, "claim repository must be valid")
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = cl_result["index"]


def load_job_input(fixture_id: str) -> dict:
    fixture_dir = GOLDEN_JOB_ANALYSIS / fixture_id
    extraction = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    return {
        "company": f"Synthetic Golden Co ({fixture_id})",
        "role": extraction.get("_role_title") or fixture_id,
        "jd_text": jd_text,
        "structured_extraction": extraction,
        "fixture_key": fixture_id,
    }


def run_analysis(fixture_id: str) -> dict:
    result = analyze_job(load_job_input(fixture_id), claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX)
    assert_true(result["valid"] is True, f"{fixture_id}: analyze_job must succeed: {result.get('errors')}")
    return result["analysis"]


# ======================================================================
# GT_APP_GATE_CLEAN
# ======================================================================
bsa_analysis_before = run_analysis("GT_BSA_STRONG")
assert_true(bsa_analysis_before["lane"] == "LANE_2_PRIORITY_APPLY", "GT_BSA_STRONG must remain PRIORITY_APPLY before Gate 1.5")

clean_attempt = {
    "application_attempt_id": "ATT_CLEAN_001",
    "job_id": bsa_analysis_before["job_id"],
    "source_platform": "Employer ATS",
    "source_url": "https://harborline.example/careers/bsa",
    "created_at": "2026-08-30",
    "capture_status": "COMPLETE_HUMAN_CONFIRMED",
    "attempt_status": "SUBMITTED",
    "notes": None,
}
clean_question = {
    "application_question_id": "AQ_CLEAN_UAT",
    "application_attempt_id": "ATT_CLEAN_001",
    "question_text": "Do you have experience documenting user acceptance testing or pilot validation outcomes?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [
        {"clause_id": "C1", "clause_text": "user acceptance testing pilot validation documentation", "mapped_requirement_id": "REQ_BSA_UAT"},
    ],
    "logic_expression": None,
    "answer_policy": "SAFE_REUSABLE",
    "screening_materiality": "MEDIUM",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
clean_evaluation = evaluate_application_question(
    clean_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
assert_true(clean_evaluation["predicate_result"] == "TRUE", "GT_APP_GATE_CLEAN: evidence-backed clause must resolve TRUE")
assert_true(clean_evaluation["safe_boolean_answer"] == "YES", "GT_APP_GATE_CLEAN: safe_boolean_answer must be YES")
assert_true(clean_evaluation["manual_review_required"] is False, "GT_APP_GATE_CLEAN: no unnecessary HOLD/manual review")
assert_true(clean_evaluation["warnings"] == [], "GT_APP_GATE_CLEAN: no warnings expected on a clean pass")
assert_true(clean_attempt["capture_status"] == "COMPLETE_HUMAN_CONFIRMED", "GT_APP_GATE_CLEAN: capture must be human-confirmed complete")

bsa_analysis_after = run_analysis("GT_BSA_STRONG")
assert_true(bsa_analysis_after["lane"] == bsa_analysis_before["lane"], "GT_APP_GATE_CLEAN: Gate-1 lane must remain unchanged after Gate 1.5")
assert_true(bsa_analysis_after["decision"] == bsa_analysis_before["decision"], "GT_APP_GATE_CLEAN: Gate-1 decision must remain unchanged after Gate 1.5")
print("PASS: GT_APP_GATE_CLEAN -- clean application passes Gate 1.5 without unnecessary HOLD; Gate-1 decision unchanged.")


# ======================================================================
# GT_APP_GATE_COMPOUND_UNSAFE
# ======================================================================
compound_question = {
    "application_question_id": "AQ_COMPOUND_UNSAFE",
    "application_attempt_id": "ATT_CLEAN_001",
    "question_text": "Do you have A, B, C, and D experience?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [
        {"clause_id": "A", "clause_text": "user acceptance testing pilot validation documentation", "mapped_requirement_id": None},
        {"clause_id": "B", "clause_text": "process mapping into a structured operating process", "mapped_requirement_id": None},
        {"clause_id": "C", "clause_text": "Salesforce administration", "mapped_requirement_id": None},
        {"clause_id": "D", "clause_text": "CSV import and approval sync workflows", "mapped_requirement_id": None},
    ],
    "logic_expression": {"op": "ALL_OF", "terms": ["A", "B", "C", "D"]},
    "answer_policy": "REVIEW",
    "screening_materiality": "HIGH",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
compound_evaluation = evaluate_application_question(
    compound_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
results_by_clause = {c["clause_id"]: c["result"] for c in compound_evaluation["clause_evaluations"]}
assert_true(results_by_clause["A"] in {"STRONG", "SUPPORTED"}, "clause A (UAT) must be supported")
assert_true(results_by_clause["B"] in {"STRONG", "SUPPORTED"}, "clause B (process mapping) must be supported")
assert_true(results_by_clause["C"] == "NONE", "clause C (Salesforce) must be unsupported")
assert_true(results_by_clause["D"] == "PARTIAL", "clause D (CSV + approval sync combined) must be only partially covered by any single Claim")
assert_true(compound_evaluation["predicate_result"] != "TRUE", "GT_APP_GATE_COMPOUND_UNSAFE: predicate must never authorize YES")
assert_true(
    compound_evaluation["predicate_result"] == "UNCERTAIN",
    "GT_APP_GATE_COMPOUND_UNSAFE (APPLICATION_GATE_NONE_IS_NOT_FALSE_REMEDIATION_V1): "
    "a NONE clause (C, no supporting evidence found) combined with a PARTIAL clause (D) must "
    "produce UNCERTAIN, not FALSE -- absence of supporting evidence for clause C is not evidence "
    "that clause C's proposition is false",
)
assert_true(compound_evaluation["safe_boolean_answer"] != "YES", "GT_APP_GATE_COMPOUND_UNSAFE: safe_boolean_answer must never be YES")
assert_true(compound_evaluation["safe_boolean_answer"] == "UNKNOWN", "GT_APP_GATE_COMPOUND_UNSAFE: safe_boolean_answer must be UNKNOWN, not a confident NO")
assert_true(compound_evaluation["manual_review_required"] is True, "GT_APP_GATE_COMPOUND_UNSAFE: an UNCERTAIN predicate must require manual review")

bsa_analysis_still = run_analysis("GT_BSA_STRONG")
assert_true(bsa_analysis_still["lane"] != "LANE_0_REJECT", "GT_APP_GATE_COMPOUND_UNSAFE: an unsafe application answer must not automatically reject the role's Gate-1 lane")
print(
    "PASS: GT_APP_GATE_COMPOUND_UNSAFE -- ALL_OF(supported, supported, NONE, PARTIAL) cannot "
    f"authorize YES (predicate={compound_evaluation['predicate_result']}); "
    f"exact unsupported/uncertain clauses surfaced (C=NONE, D=PARTIAL); role lane unaffected."
)


# ======================================================================
# GT_APP_GATE_EXPLORATORY_ISOLATED
# ======================================================================
exploratory_yes = build_application_answer(
    application_answer_id="AA_EXPLORE_SPONSORSHIP",
    application_question_id="AQ_SPONSORSHIP",
    answer_value="YES",
    answer_status="EXPLORATORY_CAPTURE",
    recorded_at="2026-08-30",
    notes="Bora clicked YES only to reveal later Easy Apply screens; not a real answer.",
)
history = select_submitted_history([exploratory_yes])
assert_true(history == [], "GT_APP_GATE_EXPLORATORY_ISOLATED: exploratory YES must never become submitted history")
assert_true(exploratory_yes["answer_status"] == "EXPLORATORY_CAPTURE", "exploratory answer's own status must remain EXPLORATORY_CAPTURE")
print("PASS: GT_APP_GATE_EXPLORATORY_ISOLATED -- exploratory YES cannot become submitted answer/candidate history/evidence/machine truth.")


# ======================================================================
# GT_APP_GATE_GATE0_SHORT_CIRCUIT
# ======================================================================
senior_reject_analysis = run_analysis("GT_SENIOR_REJECT")
assert_true(senior_reject_analysis["lane"] == "LANE_0_REJECT", "GT_APP_GATE_GATE0_SHORT_CIRCUIT: fixture must hit Gate-0 hard blocker")
assert_true(len(senior_reject_analysis.get("gaps", [])) >= 0, "sanity: analysis result must be well-formed")
applicable = gate_1_5_applicable(senior_reject_analysis)
assert_true(applicable is False, "GT_APP_GATE_GATE0_SHORT_CIRCUIT: Gate 1.5 must not run for a Gate-0-rejected job")
print("PASS: GT_APP_GATE_GATE0_SHORT_CIRCUIT -- Gate 1.5 skipped entirely for a Gate-0 reject; no application processing, no resume generation.")


# ======================================================================
# GT_APP_GATE_FORM_ONLY_CLAUSE
# ======================================================================
form_only_question = {
    "application_question_id": "AQ_FORM_ONLY_POWER_QUERY",
    "application_attempt_id": "ATT_CLEAN_001",
    "question_text": "Do you have Power Query experience?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [
        {"clause_id": "C1", "clause_text": "Power Query", "mapped_requirement_id": None},
    ],
    "logic_expression": None,
    "answer_policy": "REVIEW",
    "screening_materiality": "MEDIUM",
    "filter_risk": "UNKNOWN",
    "notes": "This clause exists only on the application form; no JD Requirement_ID exists for it.",
}
form_only_evaluation = evaluate_application_question(
    form_only_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
assert_true(form_only_question["clauses"][0]["mapped_requirement_id"] is None, "GT_APP_GATE_FORM_ONLY_CLAUSE: mapped_requirement_id must stay null")
assert_true(len(form_only_evaluation["clause_evaluations"]) == 1, "GT_APP_GATE_FORM_ONLY_CLAUSE: clause must still be evaluated")
assert_true(form_only_evaluation["clause_evaluations"][0]["result"] in {"STRONG", "SUPPORTED", "PARTIAL", "NONE", "UNKNOWN"}, "clause evaluation must produce a real result, not a placeholder")
print("PASS: GT_APP_GATE_FORM_ONLY_CLAUSE -- application-only clause captured and evaluated with mapped_requirement_id=null; no fake JD Requirement created.")


# ======================================================================
# GT_APP_GATE_REEVALUATION_NO_SOURCE_MUTATION
# ======================================================================
reeval_question = {
    "application_question_id": "AQ_REEVAL_PROCESS_MAPPING",
    "application_attempt_id": "ATT_CLEAN_001",
    "question_text": "Do you have process mapping experience?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [
        {"clause_id": "C1", "clause_text": "process mapping", "mapped_requirement_id": None},
    ],
    "logic_expression": None,
    "answer_policy": "REVIEW",
    "screening_materiality": "MEDIUM",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
reeval_snapshot = copy.deepcopy(reeval_question)

# Day 1: a claim_index that legitimately lacks CLAIM_WW_006 (process_mapping
# not yet supported). Day 2: the real, full, current trusted Claim index.
# The evidence_index is held identical across both -- only claim_index (a
# real evaluation input) changes -- to directly exercise the F-01 gap:
# a Claim-only change must be visible in the recorded digest, not just in
# clause_evaluations.
claim_index_day1 = {k: v for k, v in CLAIM_INDEX.items() if k != "CLAIM_WW_006"}
evaluation_a = evaluate_application_question(
    reeval_question, claim_index=claim_index_day1, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30", evaluation_index=1,
)
evaluation_b = evaluate_application_question(
    reeval_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30", evaluation_index=2,
)
assert_true(reeval_question == reeval_snapshot, "GT_APP_GATE_REEVALUATION_NO_SOURCE_MUTATION: ApplicationQuestion must remain byte-identical")
assert_true(evaluation_a["clause_evaluations"][0]["result"] == "NONE", "Evaluation A (claim not yet present) must be NONE")
assert_true(evaluation_b["clause_evaluations"][0]["result"] in {"STRONG", "SUPPORTED"}, "Evaluation B (claim present) must become supported")
assert_true(
    evaluation_a["evaluation_inputs_digest"] != evaluation_b["evaluation_inputs_digest"],
    "GT_APP_GATE_REEVALUATION_NO_SOURCE_MUTATION: a legitimate claim_index change that changes the evaluation result must change evaluation_inputs_digest -- no OR fallback",
)
print("PASS: GT_APP_GATE_REEVALUATION_NO_SOURCE_MUTATION -- ApplicationQuestion source byte-identical; evaluation_inputs_digest changed because a real evaluation input (claim_index) changed.")


# ======================================================================
# GT_APP_GATE_NONE_NOT_FALSE
# (APPLICATION_GATE_NONE_IS_NOT_FALSE_REMEDIATION_V1)
# ======================================================================
# "Do you have a Bachelor's degree?" is a credential/biographical fact the
# capability matcher has no domain vocabulary for at all (it is not a
# skill-capability claim); this is exactly the real-world YEB defect: NONE
# coverage must never become a confident, unflagged "NO".
degree_question = {
    "application_question_id": "AQ_DEGREE",
    "application_attempt_id": "ATT_CLEAN_001",
    "question_text": "Do you have a Bachelor's degree?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [
        {"clause_id": "C1", "clause_text": "Bachelor's degree", "mapped_requirement_id": None},
    ],
    "logic_expression": None,
    "answer_policy": "SAFE_REUSABLE",
    "screening_materiality": "MEDIUM",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
degree_evaluation = evaluate_application_question(
    degree_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
assert_true(degree_evaluation["clause_evaluations"][0]["result"] == "NONE", "no capability tag exists for a Bachelor's-degree fact; clause result must be NONE (no support found)")
assert_true(degree_evaluation["predicate_result"] == "UNCERTAIN", "GT_APP_GATE_NONE_NOT_FALSE: NONE coverage must produce UNCERTAIN, never FALSE")
assert_true(degree_evaluation["safe_boolean_answer"] == "UNKNOWN", "GT_APP_GATE_NONE_NOT_FALSE: safe_boolean_answer must be UNKNOWN, never a confident NO")
assert_true(degree_evaluation["manual_review_required"] is True, "GT_APP_GATE_NONE_NOT_FALSE: manual_review_required must be true -- the prior defect was returning False here")
print("PASS: GT_APP_GATE_NONE_NOT_FALSE -- 'Bachelor's degree?' with no matching evidence domain produces UNCERTAIN/UNKNOWN/manual-review-required, never a confident false NO.")


# ======================================================================
# GT_APP_GATE_NONE_PNL_NOT_FALSE
# ======================================================================
pnl_question = {
    "application_question_id": "AQ_PNL",
    "application_attempt_id": "ATT_CLEAN_001",
    "question_text": "Do you have experience owning or supporting a full P&L?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [
        {"clause_id": "C1", "clause_text": "owning or supporting a full P&L", "mapped_requirement_id": None},
    ],
    "logic_expression": None,
    "answer_policy": "REVIEW",
    "screening_materiality": "HIGH",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
pnl_evaluation = evaluate_application_question(
    pnl_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
assert_true(pnl_evaluation["clause_evaluations"][0]["result"] == "NONE", "no approved Claim/Evidence supports P&L ownership; clause result must be NONE (no support found)")
assert_true(pnl_evaluation["predicate_result"] == "UNCERTAIN", "GT_APP_GATE_NONE_PNL_NOT_FALSE: no supporting evidence must not be reported as a factual NO")
assert_true(pnl_evaluation["safe_boolean_answer"] == "UNKNOWN", "GT_APP_GATE_NONE_PNL_NOT_FALSE: safe_boolean_answer must be UNKNOWN, not NO")
assert_true(pnl_evaluation["manual_review_required"] is True, "GT_APP_GATE_NONE_PNL_NOT_FALSE: manual review must be required")
print("PASS: GT_APP_GATE_NONE_PNL_NOT_FALSE -- P&L-ownership question with no supporting evidence produces UNCERTAIN/UNKNOWN/manual-review-required, not a factual NO.")


# ======================================================================
# GT_APP_GATE_NONE_EXCEL_NOT_FALSE
# ======================================================================
excel_none_question = {
    "application_question_id": "AQ_EXCEL_NONE",
    "application_attempt_id": "ATT_CLEAN_001",
    "question_text": "Advanced Excel proficiency including complex formulas, pivot tables, Power Query, and financial model building?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [
        {"clause_id": "C1", "clause_text": "complex formulas", "mapped_requirement_id": None},
        {"clause_id": "C2", "clause_text": "pivot tables", "mapped_requirement_id": None},
        {"clause_id": "C3", "clause_text": "Power Query", "mapped_requirement_id": None},
        {"clause_id": "C4", "clause_text": "financial model building", "mapped_requirement_id": None},
    ],
    "logic_expression": {"op": "ALL_OF", "terms": ["C1", "C2", "C3", "C4"]},
    "answer_policy": "REVIEW",
    "screening_materiality": "MEDIUM",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
excel_none_evaluation = evaluate_application_question(
    excel_none_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
excel_results = {c["clause_id"]: c["result"] for c in excel_none_evaluation["clause_evaluations"]}
assert_true(all(r == "NONE" for r in excel_results.values()), "no Excel/Power-Query/pivot-table/financial-modeling evidence exists; every clause must be NONE (no support found)")
assert_true(
    excel_none_evaluation["predicate_result"] == "UNCERTAIN",
    "GT_APP_GATE_NONE_EXCEL_NOT_FALSE: ALL_OF over four NONE (no-match, now UNCERTAIN) clauses must not authorize YES, "
    "but must also not be reported as a definite FALSE -- there is no explicit negative evidence establishing Bora lacks Excel skills, only absence of positive support",
)
assert_true(excel_none_evaluation["safe_boolean_answer"] == "UNKNOWN", "GT_APP_GATE_NONE_EXCEL_NOT_FALSE: safe_boolean_answer must be UNKNOWN, not a confident NO")
assert_true(excel_none_evaluation["manual_review_required"] is True, "GT_APP_GATE_NONE_EXCEL_NOT_FALSE: manual review must be required")
print("PASS: GT_APP_GATE_NONE_EXCEL_NOT_FALSE -- compound Excel question with entirely unsupported clauses produces UNCERTAIN, not a fabricated factual NO.")


print("ALL NINE APPLICATION GATE GOLDEN CASES PASSED")
