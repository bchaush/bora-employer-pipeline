"""Unit tests for src/application_gate.py (APPLICATION_GATE_V1_CORRECTED):
ALWAYS_HUMAN answer-policy behavior, unsupported question-type fail-safe,
form-only clause evaluation, and source immutability across reevaluation.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from application_gate import evaluate_application_question, gate_1_5_applicable  # noqa: E402


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


# --- ALWAYS_HUMAN answer-policy behavior ---
sponsorship_question = {
    "application_question_id": "AQ_SPONSORSHIP",
    "application_attempt_id": "ATT_1",
    "question_text": "Will you now, or in the future, require sponsorship for employment visa status?",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [],
    "logic_expression": None,
    "answer_policy": "ALWAYS_HUMAN",
    "screening_materiality": "HIGH",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
evaluation = evaluate_application_question(
    sponsorship_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
assert_true(evaluation["safe_boolean_answer"] == "NOT_APPLICABLE", "ALWAYS_HUMAN questions must never receive a machine-finalized safe_boolean_answer")
assert_true(evaluation["manual_review_required"] is True, "ALWAYS_HUMAN questions must always require manual review")
print("PASS: ALWAYS_HUMAN answer-policy blocks machine-finalized final response.")


# --- Unsupported question-type fail-safe ---
unsupported_question = dict(sponsorship_question)
unsupported_question["application_question_id"] = "AQ_UNSUPPORTED"
unsupported_question["question_type"] = "UNSUPPORTED"
unsupported_question["answer_policy"] = "REVIEW"
unsupported_evaluation = evaluate_application_question(
    unsupported_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
assert_true(unsupported_evaluation["predicate_result"] == "NOT_APPLICABLE", "unsupported question_type must yield NOT_APPLICABLE, never a guessed predicate")
assert_true(unsupported_evaluation["manual_review_required"] is True, "unsupported question_type must require manual review")
assert_true(
    any("UNSUPPORTED_QUESTION_TYPE" in w for w in unsupported_evaluation["warnings"]),
    "must warn about the unsupported question_type",
)
print("PASS: unsupported question_type fails safe to manual review, never modeled as a guessed type.")


# --- Form-only clause (no JD Requirement exists) ---
power_query_question = {
    "application_question_id": "AQ_POWER_QUERY",
    "application_attempt_id": "ATT_1",
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
    "notes": None,
}
pq_evaluation = evaluate_application_question(
    power_query_question, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX, evaluated_at="2026-08-30",
)
assert_true(len(pq_evaluation["clause_evaluations"]) == 1, "form-only clause must still be evaluated")
assert_true(pq_evaluation["clause_evaluations"][0]["clause_id"] == "C1", "clause evaluation must reference the clause_id, not a Requirement_id")
assert_true(
    power_query_question["clauses"][0]["mapped_requirement_id"] is None,
    "Power Query clause has no JD Requirement -- mapped_requirement_id stays null",
)
assert_true(pq_evaluation["predicate_result"] in {"FALSE", "UNCERTAIN"}, "no Power Query evidence exists in this repository; predicate must not be fabricated as TRUE")
print("PASS: form-only clause (mapped_requirement_id=null) is evaluable against real evidence without any fake JD Requirement.")


# --- Source immutability across reevaluation ---
process_mapping_question = {
    "application_question_id": "AQ_PROCESS_MAPPING",
    "application_attempt_id": "ATT_1",
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
question_snapshot_before = copy.deepcopy(process_mapping_question)

# "Day 1": simulate a claim index without CLAIM_WW_006 (process_mapping not yet supported).
day1_claim_index = {k: v for k, v in CLAIM_INDEX.items() if k != "CLAIM_WW_006"}
evaluation_day1 = evaluate_application_question(
    process_mapping_question,
    claim_index=day1_claim_index,
    evidence_index=EVIDENCE_INDEX,
    evaluated_at="2026-08-30",
    evaluation_index=1,
)

# "Day 2": the real, full, current trusted Claim index (CLAIM_WW_006 present).
evaluation_day2 = evaluate_application_question(
    process_mapping_question,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    evaluated_at="2026-08-30",
    evaluation_index=2,
)

assert_true(process_mapping_question == question_snapshot_before, "ApplicationQuestion source record must remain byte-identical across reevaluation")
assert_true(
    evaluation_day1["clause_evaluations"][0]["result"] != evaluation_day2["clause_evaluations"][0]["result"],
    "evaluation must actually change once legitimate evidence/claim support becomes available",
)
assert_true(
    evaluation_day2["clause_evaluations"][0]["result"] in {"STRONG", "SUPPORTED"},
    "Day 2 (full trusted Claim index) must find CLAIM_WW_006 process_mapping support",
)
assert_true(
    evaluation_day1["application_question_evaluation_id"] != evaluation_day2["application_question_evaluation_id"],
    "each reevaluation must be its own distinct evaluation record",
)
print("PASS: source immutability -- ApplicationQuestion unchanged across reevaluation; only the derived evaluation changes.")


# --- Gate 1.5 short-circuit predicate ---
assert_true(gate_1_5_applicable({"lane": "APPLY"}) is True, "Gate 1.5 must be applicable for a non-rejected job")
assert_true(gate_1_5_applicable({"lane": "LANE_0_REJECT"}) is False, "Gate 1.5 must not apply to a Gate-0-rejected job")
print("PASS: gate_1_5_applicable short-circuits for LANE_0_REJECT.")

print("ALL application_gate_test CHECKS PASSED")
