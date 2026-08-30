"""Schema smoke tests for the four new Application Gate schemas
(APPLICATION_GATE_V1_CORRECTED): ApplicationAttempt, ApplicationQuestion,
ApplicationAnswer, ApplicationQuestionEvaluation.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from schema_validation import build_draft202012_validator  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def errors_for(schema_path: Path, record: dict) -> list[str]:
    validator = build_draft202012_validator(schema_path)
    return [e.message for e in validator.iter_errors(record)]


SCHEMAS = ROOT / "schemas"

# --- ApplicationAttempt ---
attempt = {
    "application_attempt_id": "ATT_YEB_001",
    "job_id": "JOB_YEB_FPA_0001",
    "source_platform": "LinkedIn Easy Apply",
    "source_url": "https://www.linkedin.com/jobs/view/1234567890/",
    "created_at": "2026-08-30",
    "capture_status": "PARTIAL",
    "attempt_status": "EXPLORATORY",
    "notes": "Exploratory click-through only, to reveal later screens; not a real application.",
}
assert_true(errors_for(SCHEMAS / "application_attempt.schema.json", attempt) == [], "valid ApplicationAttempt must pass")
bad_attempt = dict(attempt)
bad_attempt["capture_status"] = "INFERRED_COMPLETE"
assert_true(
    errors_for(SCHEMAS / "application_attempt.schema.json", bad_attempt) != [],
    "capture_status must reject any value other than PARTIAL/COMPLETE_HUMAN_CONFIRMED",
)
print("PASS: ApplicationAttempt schema smoke.")

# --- ApplicationQuestion: standard case ---
question = {
    "application_question_id": "AQ_YEB_EXCEL",
    "application_attempt_id": "ATT_YEB_001",
    "question_text": (
        "Do you have advanced Excel proficiency including complex formulas, "
        "pivot tables, Power Query, and financial model building?"
    ),
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
assert_true(errors_for(SCHEMAS / "application_question.schema.json", question) == [], "valid ApplicationQuestion must pass")
print("PASS: ApplicationQuestion schema smoke (form-only clauses, mapped_requirement_id=null).")

# --- form-only clause explicitly proven: no fake JD Requirement needed ---
assert_true(
    all(c["mapped_requirement_id"] is None for c in question["clauses"]),
    "form-only clauses must be representable with mapped_requirement_id=null",
)
print("PASS: form-only clause representable without a JD Requirement.")

# --- ApplicationQuestion: unsupported question type must still validate structurally ---
unsupported_type_question = dict(question)
unsupported_type_question["application_question_id"] = "AQ_UNSUPPORTED"
unsupported_type_question["question_type"] = "UNSUPPORTED"
unsupported_type_question["clauses"] = []
unsupported_type_question["logic_expression"] = None
assert_true(
    errors_for(SCHEMAS / "application_question.schema.json", unsupported_type_question) == [],
    "UNSUPPORTED question_type must still be a structurally valid record (fails safe at evaluation, not at capture)",
)
print("PASS: UNSUPPORTED question_type captured safely (evaluation-time manual review, not a capture-time failure).")

# --- ApplicationQuestion: invalid enums must fail ---
bad_question = dict(question)
bad_question["filter_risk"] = "ACTUAL_KNOCKOUT_CONFIGURED"
assert_true(
    errors_for(SCHEMAS / "application_question.schema.json", bad_question) != [],
    "filter_risk must never accept ACTUAL_KNOCKOUT_CONFIGURED or any value beyond UNKNOWN/POTENTIAL_KNOCKOUT",
)
print("PASS: ACTUAL_KNOCKOUT_CONFIGURED is not a representable filter_risk value.")

bad_policy = dict(question)
bad_policy["answer_policy"] = "AUTO_ANSWER"
assert_true(
    errors_for(SCHEMAS / "application_question.schema.json", bad_policy) != [],
    "answer_policy must reject any value outside SAFE_REUSABLE/REVIEW/ALWAYS_HUMAN",
)
print("PASS: answer_policy enum closed to SAFE_REUSABLE/REVIEW/ALWAYS_HUMAN.")

# --- ApplicationQuestion: sponsorship question must use ALWAYS_HUMAN ---
sponsorship_question = {
    "application_question_id": "AQ_YEB_SPONSORSHIP",
    "application_attempt_id": "ATT_YEB_001",
    "question_text": (
        "Will you now, or in the future, require sponsorship for employment "
        "visa status (e.g. H-1B visa status)?"
    ),
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [],
    "logic_expression": None,
    "answer_policy": "ALWAYS_HUMAN",
    "screening_materiality": "HIGH",
    "filter_risk": "UNKNOWN",
    "notes": "Work-authorization/sponsorship question; Bora's exploratory YES click is not a real answer.",
}
assert_true(
    errors_for(SCHEMAS / "application_question.schema.json", sponsorship_question) == [],
    "sponsorship ApplicationQuestion with answer_policy=ALWAYS_HUMAN must validate",
)
print("PASS: sponsorship question representable with answer_policy=ALWAYS_HUMAN.")

# --- ApplicationAnswer ---
exploratory_answer = {
    "application_answer_id": "AA_YEB_SPONSORSHIP_EXPLORE_1",
    "application_question_id": "AQ_YEB_SPONSORSHIP",
    "answer_value": "YES",
    "answer_status": "EXPLORATORY_CAPTURE",
    "recorded_at": "2026-08-30",
    "notes": "Exploratory click only, made to reveal later screens; not Bora's real answer.",
}
assert_true(errors_for(SCHEMAS / "application_answer.schema.json", exploratory_answer) == [], "valid exploratory ApplicationAnswer must pass")
bad_answer = dict(exploratory_answer)
bad_answer["answer_status"] = "APPLICANT_HISTORY"
assert_true(
    errors_for(SCHEMAS / "application_answer.schema.json", bad_answer) != [],
    "answer_status must reject any value outside EXPLORATORY_CAPTURE/INTENDED_ANSWER/SUBMITTED_ANSWER",
)
print("PASS: ApplicationAnswer schema smoke.")

# --- ApplicationQuestionEvaluation ---
evaluation = {
    "application_question_evaluation_id": "AQE_AQ_YEB_EXCEL_01",
    "application_question_id": "AQ_YEB_EXCEL",
    "evaluated_at": "2026-08-30",
    "evidence_version": "a" * 64,
    "clause_evaluations": [
        {"clause_id": "C1", "result": "NONE", "evidence_ids": [], "claim_ids": [], "explanation": "no match"}
    ],
    "support_state": "UNSUPPORTED",
    "predicate_result": "FALSE",
    "safe_boolean_answer": "NO",
    "manual_review_required": False,
    "warnings": [],
    "notes": None,
}
assert_true(errors_for(SCHEMAS / "application_question_evaluation.schema.json", evaluation) == [], "valid ApplicationQuestionEvaluation must pass")
bad_evaluation = dict(evaluation)
bad_evaluation["support_state"] = "YES"
assert_true(
    errors_for(SCHEMAS / "application_question_evaluation.schema.json", bad_evaluation) != [],
    "support_state must never accept YES/NO as universal truth states",
)
print("PASS: ApplicationQuestionEvaluation schema smoke; support_state cannot be YES/NO.")

print("ALL application_schema_smoke_test CHECKS PASSED")
