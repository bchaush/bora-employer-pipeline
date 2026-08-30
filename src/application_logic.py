"""Deterministic three-valued logic evaluation for ApplicationQuestion
compound expressions (APPLICATION_GATE_V1_CORRECTED).

Operators supported: ALL_OF, ANY_OF, AT_LEAST_N, NOT. This is deliberately
not a general-purpose logic DSL -- no other operator is implemented, and
none should be added without a real fixture requiring it.

Values are TRUE / FALSE / UNCERTAIN (not Python bool): UNCERTAIN represents
a clause whose evidence support is PARTIAL or UNKNOWN -- genuinely unproven
in either direction, not merely "unknown = false". AI may parse question
text into an expression; this module only evaluates an already-parsed
expression against already-computed leaf values. It never guesses a
missing leaf value and never lets AI decide a logic result.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

TRUE = "TRUE"
FALSE = "FALSE"
UNCERTAIN = "UNCERTAIN"

_VALUES = frozenset({TRUE, FALSE, UNCERTAIN})

# Maps an evidence/clause-match result vocabulary (evidence_match.schema.json)
# onto the three logic values. PARTIAL and UNKNOWN both mean "genuinely
# unproven either way" -- neither is silently treated as FALSE nor as TRUE.
RESULT_TO_LOGIC_VALUE: dict[str, str] = {
    "STRONG": TRUE,
    "SUPPORTED": TRUE,
    "PARTIAL": UNCERTAIN,
    "UNKNOWN": UNCERTAIN,
    "NONE": FALSE,
}


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def result_to_logic_value(result: str) -> str:
    """Map one clause evidence-match result to a TRUE/FALSE/UNCERTAIN value."""
    return RESULT_TO_LOGIC_VALUE.get(result, UNCERTAIN)


def _evaluate(
    expr: Any,
    clause_values: Mapping[str, str],
    errors: list[dict[str, Any]],
) -> str | None:
    # Leaf: a clause_id string.
    if isinstance(expr, str):
        if expr not in clause_values:
            errors.append(
                _error(
                    "INVALID_CLAUSE_REFERENCE",
                    clause_id=expr,
                    detail=f"logic_expression references unknown clause_id {expr!r}",
                )
            )
            return None
        return clause_values[expr]

    if not isinstance(expr, Mapping):
        errors.append(
            _error(
                "MALFORMED_LOGIC_EXPRESSION",
                detail=f"expression node must be a clause_id string or object; got {type(expr).__name__}",
            )
        )
        return None

    op = expr.get("op")
    terms = expr.get("terms")
    if not isinstance(terms, Sequence) or isinstance(terms, (str, bytes)) or not terms:
        errors.append(
            _error(
                "MALFORMED_LOGIC_EXPRESSION",
                detail="expression 'terms' must be a non-empty array",
            )
        )
        return None

    term_values: list[str | None] = [
        _evaluate(term, clause_values, errors) for term in terms
    ]
    if any(value is None for value in term_values):
        return None
    values: list[str] = [v for v in term_values if v is not None]

    if op == "ALL_OF":
        if FALSE in values:
            return FALSE
        if UNCERTAIN in values:
            return UNCERTAIN
        return TRUE

    if op == "ANY_OF":
        if TRUE in values:
            return TRUE
        if UNCERTAIN in values:
            return UNCERTAIN
        return FALSE

    if op == "NOT":
        if len(values) != 1:
            errors.append(
                _error(
                    "MALFORMED_LOGIC_EXPRESSION",
                    detail=f"NOT requires exactly one term; got {len(values)}",
                )
            )
            return None
        value = values[0]
        if value == TRUE:
            return FALSE
        if value == FALSE:
            return TRUE
        return UNCERTAIN

    if op == "AT_LEAST_N":
        n = expr.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            errors.append(
                _error(
                    "INVALID_AT_LEAST_N_THRESHOLD",
                    n=n,
                    detail="AT_LEAST_N requires a positive integer threshold",
                )
            )
            return None
        proven_true_count = sum(1 for v in values if v == TRUE)
        possible_true_count = proven_true_count + sum(1 for v in values if v == UNCERTAIN)
        if proven_true_count >= n:
            return TRUE
        if possible_true_count < n:
            return FALSE
        return UNCERTAIN

    errors.append(
        _error(
            "UNSUPPORTED_LOGIC_OPERATOR",
            op=op,
            detail=f"unsupported logic operator {op!r}",
        )
    )
    return None


def evaluate_expression(
    expr: Mapping[str, Any],
    clause_values: Mapping[str, str],
) -> dict[str, Any]:
    """Evaluate a logic_expression tree against already-computed clause values.

    ``clause_values`` maps clause_id -> TRUE/FALSE/UNCERTAIN. Returns
    ``{"valid": bool, "result": TRUE|FALSE|UNCERTAIN|None, "errors": [...]}``.
    ``result`` is None whenever ``valid`` is False (invalid clause reference,
    malformed expression, or invalid AT_LEAST_N threshold) -- never guessed.
    """
    errors: list[dict[str, Any]] = []
    result = _evaluate(expr, clause_values, errors)
    if errors:
        return {"valid": False, "result": None, "errors": errors}
    assert result in _VALUES
    return {"valid": True, "result": result, "errors": []}
