"""Unit tests for src/application_answer.py (APPLICATION_GATE_V1_CORRECTED):
exploratory-answer isolation and submitted-answer immutability-via-new-event
behavior.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_answer import (  # noqa: E402
    build_application_answer,
    is_history_eligible,
    select_submitted_history,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


# --- Exploratory answer isolation ---
exploratory = build_application_answer(
    application_answer_id="AA_1",
    application_question_id="AQ_SPONSORSHIP",
    answer_value="YES",
    answer_status="EXPLORATORY_CAPTURE",
    recorded_at="2026-08-30",
    notes="exploratory click only",
)
intended = build_application_answer(
    application_answer_id="AA_2",
    application_question_id="AQ_SPONSORSHIP",
    answer_value="NO",
    answer_status="INTENDED_ANSWER",
    recorded_at="2026-08-30",
)
submitted = build_application_answer(
    application_answer_id="AA_3",
    application_question_id="AQ_SPONSORSHIP",
    answer_value="NO",
    answer_status="SUBMITTED_ANSWER",
    recorded_at="2026-08-30",
)

assert_false(is_history_eligible(exploratory), "EXPLORATORY_CAPTURE must never be history-eligible")
assert_false(is_history_eligible(intended), "INTENDED_ANSWER must never be history-eligible")
assert_true(is_history_eligible(submitted), "SUBMITTED_ANSWER must be history-eligible")
print("PASS: question/answer separation -- only SUBMITTED_ANSWER is history-eligible.")

history = select_submitted_history([exploratory, intended, submitted])
assert_true(history == [submitted], "select_submitted_history must return exactly the SUBMITTED_ANSWER records")
assert_true(exploratory not in history, "exploratory answer must never appear in applicant history")
print("PASS: exploratory answer isolation -- exploratory click cannot become applicant history/evidence.")

only_exploratory_history = select_submitted_history([exploratory])
assert_true(only_exploratory_history == [], "an all-exploratory answer list must yield empty history, not a guessed fallback")
print("PASS: exploratory-only answer set yields empty history (never coerced into a real answer).")

# --- Submitted-answer immutability-via-new-event behavior ---
exploratory_snapshot = copy.deepcopy(exploratory)
# "Correcting" the exploratory YES with a real submitted NO must create a
# new event, never mutate the exploratory record in place.
corrected = build_application_answer(
    application_answer_id="AA_4",
    application_question_id="AQ_SPONSORSHIP",
    answer_value="NO",
    answer_status="SUBMITTED_ANSWER",
    recorded_at="2026-08-30",
)
assert_true(exploratory == exploratory_snapshot, "building a new answer event must never mutate a prior answer object")
assert_true(corrected is not exploratory, "a corrected answer must be a distinct object, not the same record")
assert_true(corrected["application_answer_id"] != exploratory["application_answer_id"], "a corrected answer must carry a new answer_id")
print("PASS: submitted-answer immutability -- correction creates a new event, never mutates the prior one.")

print("ALL application_answer_test CHECKS PASSED")
