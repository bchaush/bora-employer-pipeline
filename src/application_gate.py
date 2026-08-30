"""Application Gate (Gate 1.5) evaluation orchestrator
(APPLICATION_GATE_V1_CORRECTED).

Evaluates one immutable ApplicationQuestion record against a trusted
Evidence/Claim index, producing a derived ApplicationQuestionEvaluation.
This module never mutates the ApplicationQuestion it evaluates, never
creates a second job-decision engine, and never runs unless Gate 0/1 have
already cleared for the job in question (see `gate_1_5_applicable`).

Gate ordering preserved:
  Gate 0  -- cheap hard blockers (existing job_decision.detect_hard_blockers)
  Gate 1  -- existing job/JD qualification (job_analysis.analyze_job)
  Gate 1.5 -- this module: application-form representation/evaluation only
  Gate 2  -- existing résumé derivative flow (unchanged)
  Gate 3  -- human submission (unchanged, permanent no-auto-submit)

Gate 1.5 may surface unsupported clauses, uncertain compound questions,
manual-review requirements, and conservative filter-risk state. It must
never silently change the Gate-1 lane/decision -- callers that want both
Gate-1 and Gate-1.5 results keep them as separate fields on separate
records, exactly like `evaluate_application_question` keeps
`support_state`/`predicate_result` separate from any role-level decision.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from application_clause_match import match_clause
from application_logic import evaluate_expression, result_to_logic_value
from requirement_match import load_reusable_claims
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_SCHEMA_PATH = ROOT / "schemas" / "application_question_evaluation.schema.json"

SUPPORTED_QUESTION_TYPES = frozenset(
    {"YES_NO", "SHORT_TEXT", "SELECT", "MULTI_SELECT", "NUMERIC"}
)


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def compute_evaluation_inputs_digest(
    evidence_index: Mapping[str, Any],
    claim_index: Mapping[str, Any],
) -> str:
    """SHA-256 digest of every trusted input evaluate_application_question()
    actually depends on: the trusted Evidence index AND the trusted Claim
    index.

    A digest of evidence_index alone is audit-misleading: `match_clause()`
    is called with `load_reusable_claims(claim_index, evidence_index)`, so
    a Claim-only change (wording, evidence_state, evidence_ids,
    human_approval/reusable state) can change clause_evaluations and
    predicate_result while evidence_index stays byte-identical. Hashing
    the full trusted claim_index (not a hand-selected subset of Claim
    fields) avoids re-introducing that same class of hidden omission for
    any Claim property this evaluator does not yet obviously use.

    Mirrors the existing résumé validation-digest pattern
    (`resume_digest.compute_derivative_validation_digest`) in spirit only:
    a scoped, deterministic content digest over this evaluation's actual
    inputs, not a new global versioning subsystem.
    """
    payload = {"evidence_index": evidence_index, "claim_index": claim_index}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def gate_1_5_applicable(job_analysis: Mapping[str, Any]) -> bool:
    """False when the job already failed Gate 0/1 (LANE_0_REJECT).

    Preserves cheap-before-expensive ordering: Gate 1.5 application
    processing must never run for a job Gate 0/1 has already rejected.
    """
    return job_analysis.get("lane") != "LANE_0_REJECT"


def _rollup_support_state(clause_evaluations: Sequence[Mapping[str, Any]]) -> str:
    if not clause_evaluations:
        return "UNKNOWN"
    results = [c.get("result") for c in clause_evaluations]
    if all(r == "UNKNOWN" for r in results):
        return "UNKNOWN"
    if all(r in {"STRONG", "SUPPORTED"} for r in results):
        return "SUPPORTED"
    if all(r == "NONE" for r in results):
        return "UNSUPPORTED"
    return "PARTIAL"


def evaluate_application_question(
    question: Mapping[str, Any],
    *,
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
    evaluated_at: str,
    evaluation_index: int = 1,
) -> dict[str, Any]:
    """Evaluate one immutable ApplicationQuestion; never mutates ``question``.

    Returns a dict schema-validated against
    application_question_evaluation.schema.json.
    """
    application_question_id = question.get("application_question_id")
    evaluation_id = f"AQE_{application_question_id}_{evaluation_index:02d}"
    warnings: list[str] = []

    evaluation_inputs_digest = compute_evaluation_inputs_digest(evidence_index, claim_index)
    question_type = question.get("question_type")

    if question_type not in SUPPORTED_QUESTION_TYPES:
        evaluation = {
            "application_question_evaluation_id": evaluation_id,
            "application_question_id": application_question_id,
            "evaluated_at": evaluated_at,
            "evaluation_inputs_digest": evaluation_inputs_digest,
            "clause_evaluations": [],
            "support_state": "UNKNOWN",
            "predicate_result": "NOT_APPLICABLE",
            "safe_boolean_answer": "NOT_APPLICABLE",
            "manual_review_required": True,
            "warnings": [
                f"UNSUPPORTED_QUESTION_TYPE: {question_type!r} is not modeled by V1; "
                "manual review required."
            ],
            "notes": None,
        }
        return _validate(evaluation)

    reusable_claims = load_reusable_claims(claim_index, evidence_index)

    clauses = question.get("clauses") or []
    clause_evaluations: list[dict[str, Any]] = []
    clause_values: dict[str, str] = {}
    for clause in clauses:
        clause_id = clause.get("clause_id")
        clause_text = clause.get("clause_text")
        match = match_clause(
            clause_id=clause_id,
            clause_text=clause_text,
            reusable_claims=reusable_claims,
            evidence_index=evidence_index,
        )
        clause_evaluations.append(match)
        clause_values[clause_id] = result_to_logic_value(match["result"])

    support_state = _rollup_support_state(clause_evaluations)

    logic_expression = question.get("logic_expression")
    predicate_result = "NOT_APPLICABLE"
    if logic_expression is not None:
        evaluation_result = evaluate_expression(logic_expression, clause_values)
        if evaluation_result["valid"]:
            predicate_result = evaluation_result["result"]
        else:
            for err in evaluation_result["errors"]:
                warnings.append(f"{err['code']}: {err.get('detail', err)}")
    elif len(clause_values) == 1:
        # Trivial single-clause question: no expression needed.
        predicate_result = next(iter(clause_values.values()))
    elif len(clause_values) > 1:
        warnings.append(
            "MULTIPLE_CLAUSES_WITHOUT_LOGIC_EXPRESSION: refusing to assume "
            "an implicit AND/OR across clauses without an explicit "
            "logic_expression."
        )

    answer_policy = question.get("answer_policy")

    if question_type == "YES_NO":
        safe_boolean_answer = {
            "TRUE": "YES",
            "FALSE": "NO",
            "UNCERTAIN": "UNKNOWN",
            "NOT_APPLICABLE": "NOT_APPLICABLE",
        }[predicate_result]
    else:
        safe_boolean_answer = "NOT_APPLICABLE"

    if answer_policy == "ALWAYS_HUMAN":
        # The evaluator may surface predicate_result/evidence context, but
        # must never produce a machine-authorized final response for a
        # consequential ALWAYS_HUMAN question (work authorization, future
        # sponsorship, visa/immigration, legal/criminal attestations, EEO).
        safe_boolean_answer = "NOT_APPLICABLE"
        manual_review_required = True
    else:
        manual_review_required = predicate_result in {"UNCERTAIN", "NOT_APPLICABLE"}

    evaluation = {
        "application_question_evaluation_id": evaluation_id,
        "application_question_id": application_question_id,
        "evaluated_at": evaluated_at,
        "evaluation_inputs_digest": evaluation_inputs_digest,
        "clause_evaluations": clause_evaluations,
        "support_state": support_state,
        "predicate_result": predicate_result,
        "safe_boolean_answer": safe_boolean_answer,
        "manual_review_required": manual_review_required,
        "warnings": warnings,
        "notes": None,
    }
    return _validate(evaluation)


def _validate(evaluation: dict[str, Any]) -> dict[str, Any]:
    validator = build_draft202012_validator(EVALUATION_SCHEMA_PATH)
    errors = [err.message for err in validator.iter_errors(evaluation)]
    if errors:
        raise ValueError(
            f"ApplicationQuestionEvaluation failed schema validation: {errors}"
        )
    return evaluation
