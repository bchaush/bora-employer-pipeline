"""ApplicationAnswer construction and exploratory-safety enforcement
(APPLICATION_GATE_V1_CORRECTED).

EXPLORATORY_CAPTURE, INTENDED_ANSWER, and SUBMITTED_ANSWER are materially
different states. This module makes it structurally impossible for an
exploratory click (e.g. the Youth Enrichment Brands Easy Apply exploration,
where Bora selected YES only to reveal later screens) to be treated as
applicant history, a submitted answer, evidence, or a reusable/truthful
candidate assertion: `select_submitted_history` only ever returns
SUBMITTED_ANSWER records, and `build_application_answer` always returns a
new, independent record rather than mutating a prior one -- correcting an
exploratory or intended value means recording a new answer event.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
ANSWER_SCHEMA_PATH = ROOT / "schemas" / "application_answer.schema.json"

HISTORY_ELIGIBLE_STATUS = "SUBMITTED_ANSWER"


def build_application_answer(
    *,
    application_answer_id: str,
    application_question_id: str,
    answer_value: Any,
    answer_status: str,
    recorded_at: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Construct one new, independent ApplicationAnswer event.

    Never mutates any previously returned answer dict. Correcting an
    exploratory or intended answer must call this again with a new
    ``application_answer_id`` and the new ``answer_status`` -- it must
    never reach back and edit the prior event.
    """
    answer = {
        "application_answer_id": application_answer_id,
        "application_question_id": application_question_id,
        "answer_value": answer_value,
        "answer_status": answer_status,
        "recorded_at": recorded_at,
        "notes": notes,
    }
    validator = build_draft202012_validator(ANSWER_SCHEMA_PATH)
    errors = [err.message for err in validator.iter_errors(answer)]
    if errors:
        raise ValueError(f"ApplicationAnswer failed schema validation: {errors}")
    return answer


def is_history_eligible(answer: Mapping[str, Any]) -> bool:
    """True only for a SUBMITTED_ANSWER record.

    EXPLORATORY_CAPTURE and INTENDED_ANSWER are never history-eligible,
    regardless of their answer_value.
    """
    return answer.get("answer_status") == HISTORY_ELIGIBLE_STATUS


def select_submitted_history(
    answers: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """Return only SUBMITTED_ANSWER records, in input order.

    EXPLORATORY_CAPTURE and INTENDED_ANSWER records are silently and
    structurally excluded -- never raised as an error, never included --
    so an exploratory click can never contaminate applicant history simply
    by being present in the same answer list.
    """
    return [answer for answer in answers if is_history_eligible(answer)]
