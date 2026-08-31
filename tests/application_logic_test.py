"""Unit tests for deterministic three-valued logic evaluation
(src/application_logic.py), part of APPLICATION_GATE_V1_CORRECTED
(extended by APPLICATION_GATE_NONE_IS_NOT_FALSE_REMEDIATION_V1).

Covers ALL_OF / ANY_OF / AT_LEAST_N / NOT semantics exactly as specified,
nested expressions, invalid clause references, invalid AT_LEAST_N
thresholds (schema-level), and the evidence-match-result -> logic-value
translation (result_to_logic_value).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_logic import TRUE, FALSE, UNCERTAIN, evaluate_expression, result_to_logic_value  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def ev(expr, values):
    result = evaluate_expression(expr, values)
    assert_true(result["valid"], f"expected valid evaluation, got {result}")
    return result["result"]


# --- ALL_OF ---
assert_true(ev({"op": "ALL_OF", "terms": ["A", "B"]}, {"A": TRUE, "B": TRUE}) == TRUE, "ALL_OF(TRUE,TRUE) must be TRUE")
assert_true(
    ev({"op": "ALL_OF", "terms": ["A", "B", "C", "D"]}, {"A": TRUE, "B": TRUE, "C": FALSE, "D": UNCERTAIN}) == FALSE,
    "ALL_OF(TRUE,TRUE,FALSE,UNCERTAIN) must be FALSE",
)
assert_true(
    ev({"op": "ALL_OF", "terms": ["A", "B", "C"]}, {"A": TRUE, "B": TRUE, "C": UNCERTAIN}) == UNCERTAIN,
    "ALL_OF(TRUE,TRUE,UNCERTAIN) must be UNCERTAIN",
)
print("PASS: ALL_OF TRUE/FALSE/UNCERTAIN behavior.")

# --- ANY_OF ---
assert_true(ev({"op": "ANY_OF", "terms": ["A", "B"]}, {"A": TRUE, "B": UNCERTAIN}) == TRUE, "ANY_OF(TRUE,UNCERTAIN) must be TRUE")
assert_true(ev({"op": "ANY_OF", "terms": ["A", "B"]}, {"A": FALSE, "B": UNCERTAIN}) == UNCERTAIN, "ANY_OF(FALSE,UNCERTAIN) must be UNCERTAIN")
assert_true(ev({"op": "ANY_OF", "terms": ["A", "B"]}, {"A": FALSE, "B": FALSE}) == FALSE, "ANY_OF(FALSE,FALSE) must be FALSE")
print("PASS: ANY_OF TRUE/FALSE/UNCERTAIN behavior.")

# --- NOT ---
assert_true(ev({"op": "NOT", "terms": ["A"]}, {"A": TRUE}) == FALSE, "NOT(TRUE) must be FALSE")
assert_true(ev({"op": "NOT", "terms": ["A"]}, {"A": FALSE}) == TRUE, "NOT(FALSE) must be TRUE")
assert_true(ev({"op": "NOT", "terms": ["A"]}, {"A": UNCERTAIN}) == UNCERTAIN, "NOT(UNCERTAIN) must be UNCERTAIN")
print("PASS: NOT behavior.")

# --- AT_LEAST_N ---
assert_true(
    ev({"op": "AT_LEAST_N", "n": 2, "terms": ["A", "B", "C"]}, {"A": TRUE, "B": UNCERTAIN, "C": FALSE}) == UNCERTAIN,
    "AT_LEAST_N(2, TRUE, UNCERTAIN, FALSE): proven=1 possible=2 -> UNCERTAIN",
)
assert_true(
    ev({"op": "AT_LEAST_N", "n": 2, "terms": ["A", "B", "C"]}, {"A": TRUE, "B": TRUE, "C": FALSE}) == TRUE,
    "AT_LEAST_N(2, TRUE, TRUE, FALSE): proven=2 -> TRUE",
)
assert_true(
    ev({"op": "AT_LEAST_N", "n": 3, "terms": ["A", "B", "C"]}, {"A": TRUE, "B": FALSE, "C": FALSE}) == FALSE,
    "AT_LEAST_N(3, TRUE, FALSE, FALSE): possible=1 < 3 -> FALSE",
)
print("PASS: AT_LEAST_N proven/possible-count behavior.")

# --- Nested expressions ---
nested = {
    "op": "ALL_OF",
    "terms": [
        "A",
        {"op": "ANY_OF", "terms": ["B", "C"]},
    ],
}
assert_true(ev(nested, {"A": TRUE, "B": FALSE, "C": TRUE}) == TRUE, "nested ALL_OF(TRUE, ANY_OF(FALSE,TRUE)) must be TRUE")
assert_true(ev(nested, {"A": TRUE, "B": FALSE, "C": FALSE}) == FALSE, "nested ALL_OF(TRUE, ANY_OF(FALSE,FALSE)) must be FALSE")
print("PASS: nested expressions evaluate recursively.")

# --- Invalid clause reference ---
invalid_ref = evaluate_expression({"op": "ALL_OF", "terms": ["A", "MISSING"]}, {"A": TRUE})
assert_true(invalid_ref["valid"] is False, "unknown clause_id must be invalid")
assert_true(invalid_ref["result"] is None, "invalid evaluation must not guess a result")
assert_true(
    any(e["code"] == "INVALID_CLAUSE_REFERENCE" for e in invalid_ref["errors"]),
    "must report INVALID_CLAUSE_REFERENCE",
)
print("PASS: invalid clause reference detected, no guessed result.")

# --- Invalid AT_LEAST_N threshold (schema-level) ---
validator = build_draft202012_validator(ROOT / "schemas" / "application_question.schema.json")
bad_question = {
    "application_question_id": "AQ_BAD_N",
    "application_attempt_id": "ATT_1",
    "question_text": "x",
    "question_type": "YES_NO",
    "required": True,
    "captured_at": "2026-08-30",
    "clauses": [{"clause_id": "A", "clause_text": "a", "mapped_requirement_id": None}],
    "logic_expression": {"op": "AT_LEAST_N", "n": 0, "terms": ["A"]},
    "answer_policy": "REVIEW",
    "screening_materiality": "UNKNOWN",
    "filter_risk": "UNKNOWN",
    "notes": None,
}
schema_errors = list(validator.iter_errors(bad_question))
assert_true(len(schema_errors) > 0, "AT_LEAST_N with n=0 must fail schema validation")
print("PASS: invalid AT_LEAST_N threshold (n<1) rejected by schema.")

# Runtime-level invalid threshold (non-integer n slipping past a caller that
# skips schema validation) must also fail closed, never silently coerced.
runtime_invalid = evaluate_expression({"op": "AT_LEAST_N", "n": 0, "terms": ["A"]}, {"A": TRUE})
assert_true(runtime_invalid["valid"] is False, "runtime AT_LEAST_N n=0 must be invalid")
assert_true(
    any(e["code"] == "INVALID_AT_LEAST_N_THRESHOLD" for e in runtime_invalid["errors"]),
    "must report INVALID_AT_LEAST_N_THRESHOLD",
)
print("PASS: runtime invalid AT_LEAST_N threshold fails closed.")

# --- result_to_logic_value: evidence-match-result -> logic-value translation
# (APPLICATION_GATE_NONE_IS_NOT_FALSE_REMEDIATION_V1) ---
assert_true(result_to_logic_value("STRONG") == TRUE, "STRONG must map to TRUE")
assert_true(result_to_logic_value("SUPPORTED") == TRUE, "SUPPORTED must map to TRUE")
assert_true(result_to_logic_value("PARTIAL") == UNCERTAIN, "PARTIAL must map to UNCERTAIN")
assert_true(result_to_logic_value("UNKNOWN") == UNCERTAIN, "UNKNOWN must map to UNCERTAIN")
assert_true(
    result_to_logic_value("NONE") == UNCERTAIN,
    "NONE must map to UNCERTAIN, not FALSE: 'no supporting match found' is not the same as "
    "'the proposition is established false' -- absence of supporting evidence is not evidence "
    "of factual absence (APPLICATION_GATE_NONE_IS_NOT_FALSE_REMEDIATION_V1)",
)
print("PASS: result_to_logic_value maps STRONG/SUPPORTED->TRUE, PARTIAL/UNKNOWN/NONE->UNCERTAIN; NONE is never FALSE.")

print("ALL application_logic_test CHECKS PASSED")
