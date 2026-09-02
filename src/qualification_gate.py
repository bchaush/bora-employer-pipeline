"""ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1 -- deterministic
evaluation of employer-level alternative-qualification-branch records
(``qualification_gate``), per
docs/decisions/ADR-ALTERNATIVE-QUALIFICATION-BRANCH-REPRESENTATION-V1.md.

Architecture (Option B, locked by the ADR):

- Requirement rows remain atomic Employer truth, unmodified by this module.
- A ``qualification_gate`` record is a SEPARATE Employer-truth record
  (``qualification_gate_id``, ``job_id``, ``source_text`` (array of exact
  raw-source excerpts), ``source_location``, ``logic_expression`` (terms
  reference existing ``requirement_id`` values only), optional
  ``unmodeled_branches_note``). It carries NO candidate Evidence/Claim/
  match-specific state -- the gate record is identical regardless of the
  current candidate-evidence state (the "static gate invariant").
- Gate LEAF TRUTH is derived here, at evaluation time, from each
  referenced Requirement's CURRENT ``EvidenceMatch`` (Match truth) via a
  conservative, evaluation_path-keyed policy -- never authored inside the
  gate record itself.

Qualification support states (never a claim about candidate factual
reality -- see ADR §5):

  SUPPORTED                  -- current approved evidence establishes
                                 support.
  BLOCKED_BY_MATCHING_POLICY -- the current deterministic matcher
                                 intentionally refuses this requirement
                                 class/transfer under an explicitly coded
                                 protection rule (NONE_TRAP only in V1).
                                 Does NOT mean "candidate factually lacks
                                 this" and does NOT mean "current evidence
                                 was exhaustively checked and proved
                                 absence."
  UNRESOLVED                  -- current evidence/evaluator coverage
                                 cannot safely establish either state.

V1 leaf adapter (locked, conservative -- ADR §6):

  STRONG / SUPPORTED                              -> SUPPORTED
  PARTIAL / UNKNOWN                                -> UNRESOLVED
  NONE, evaluation_path == NONE_TRAP               -> BLOCKED_BY_MATCHING_POLICY
  NONE, evaluation_path == NO_CAPABILITY_OVERLAP   -> UNRESOLVED
  NONE, evaluation_path == NO_CAPABILITY_COVERAGE  -> UNRESOLVED
  missing/unrecognized evaluation_path             -> UNRESOLVED
  any unrecognized result                          -> UNRESOLVED

``NO_CAPABILITY_OVERLAP`` is deliberately excluded from
``BLOCKED_BY_MATCHING_POLICY``: the identical capability signature
(e.g. ``{bachelors_degree_credential}``) can arise from both a complete,
single-concept requirement ("Bachelor's degree") and an incomplete,
compound one ("Bachelor's degree and required professional
certification") -- no tag-signature-based allowlist can safely
disambiguate these without span-level text-coverage analysis, which this
module does not build (explicit non-goal).

Internal tree-walker adapter (ADR §7): ``application_logic.evaluate_expression()``
is reused UNMODIFIED as the deterministic TRUE/FALSE/UNCERTAIN tree
walker (confirmed leaf-value-agnostic). ``application_logic.RESULT_TO_LOGIC_VALUE``
(Application Gate's own, differently-purposed ``NONE -> UNCERTAIN``
mapping) is NEVER reused here -- shared mechanism does not imply shared
business meaning.

This module does not modify ``requirement_match.py``, ``experience_range.py``,
``domain_qualified_duration.py``, or ``application_logic.py``.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from application_logic import evaluate_expression

SUPPORTED = "SUPPORTED"
BLOCKED_BY_MATCHING_POLICY = "BLOCKED_BY_MATCHING_POLICY"
UNRESOLVED = "UNRESOLVED"

_TRUE = "TRUE"
_FALSE = "FALSE"
_UNCERTAIN = "UNCERTAIN"

_SUPPORT_TO_LOGIC = {
    SUPPORTED: _TRUE,
    BLOCKED_BY_MATCHING_POLICY: _FALSE,
    UNRESOLVED: _UNCERTAIN,
}
_LOGIC_TO_SUPPORT = {
    _TRUE: SUPPORTED,
    _FALSE: BLOCKED_BY_MATCHING_POLICY,
    _UNCERTAIN: UNRESOLVED,
}

# V1 conservative allowlist: the ONLY evaluation_path value whose NONE may
# become BLOCKED_BY_MATCHING_POLICY. A deliberately small, individually-
# reviewed table -- not derived from capability-tag presence, domain/
# experience_level nullness, or explanation text.
_NEGATIVE_SUFFICIENT_EVALUATION_PATHS: frozenset[str] = frozenset({"NONE_TRAP"})


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def qualification_leaf_support(match: Mapping[str, Any] | None) -> str:
    """Derive a qualification-gate leaf's SUPPORTED/BLOCKED_BY_MATCHING_POLICY/
    UNRESOLVED state from its current EvidenceMatch (Match truth).

    A missing match (a referenced requirement_id has no current match at
    all) is treated identically to an unrecognized result -- UNRESOLVED,
    fail-closed, never fabricated.
    """
    if not isinstance(match, Mapping):
        return UNRESOLVED
    result = match.get("result")
    if result in ("STRONG", "SUPPORTED"):
        return SUPPORTED
    if result in ("PARTIAL", "UNKNOWN"):
        return UNRESOLVED
    if result == "NONE":
        evaluation_path = match.get("evaluation_path")
        if evaluation_path in _NEGATIVE_SUFFICIENT_EVALUATION_PATHS:
            return BLOCKED_BY_MATCHING_POLICY
        return UNRESOLVED
    return UNRESOLVED


def _leaf_logic_values(
    requirement_ids: Sequence[str],
    matches_by_req: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    return {
        req_id: _SUPPORT_TO_LOGIC[qualification_leaf_support(matches_by_req.get(req_id))]
        for req_id in requirement_ids
    }


def _collect_leaf_ids(expr: Any, out: set[str]) -> None:
    if isinstance(expr, str):
        out.add(expr)
        return
    if isinstance(expr, Mapping):
        terms = expr.get("terms")
        if isinstance(terms, Sequence) and not isinstance(terms, (str, bytes)):
            for term in terms:
                _collect_leaf_ids(term, out)


def gate_leaf_ids(gate: Mapping[str, Any]) -> frozenset[str]:
    """Every requirement_id referenced anywhere in a gate's logic_expression."""
    out: set[str] = set()
    _collect_leaf_ids(gate.get("logic_expression"), out)
    return frozenset(out)


def all_gates_leaf_ids(gates: Sequence[Mapping[str, Any]]) -> frozenset[str]:
    """Every requirement_id referenced by ANY gate in ``gates``.

    Used by callers to exclude gate-referenced rows from ordinary
    ungrouped hard-blocker/gap/unknown handling (ADR §10) -- ungrouped
    requirements not referenced by any gate are completely unaffected.
    """
    out: set[str] = set()
    for gate in gates:
        out.update(gate_leaf_ids(gate))
    return frozenset(out)


def validate_gate_requirement_references(
    gate: Mapping[str, Any],
    known_requirement_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """Fail-closed referential-integrity check: every requirement_id a gate's
    logic_expression references must exist among the job's own Requirement
    rows. Returns a list of errors (empty when valid)."""
    known = set(known_requirement_ids)
    missing = sorted(gate_leaf_ids(gate) - known)
    if not missing:
        return []
    return [
        _error(
            "QUALIFICATION_GATE_UNKNOWN_REQUIREMENT_ID",
            qualification_gate_id=gate.get("qualification_gate_id"),
            missing_requirement_ids=missing,
            detail=(
                "qualification_gate logic_expression references "
                f"requirement_id(s) {missing!r} not present among this "
                "job's Requirement rows."
            ),
        )
    ]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def validate_gate_source_traceability(
    gate: Mapping[str, Any],
    jd_text: str,
) -> list[dict[str, Any]]:
    """Fail-closed raw-source traceability check (ADR §3): every string in
    ``source_text`` must be an exact substring of ``jd_text`` after
    whitespace-only normalization (collapsing runs of whitespace, trimming
    leading/trailing whitespace) and nothing else -- no case-folding, no
    punctuation stripping, no semantic/embedding/model-judgment matching.
    Returns a list of errors (empty when valid)."""
    errors: list[dict[str, Any]] = []
    source_text = gate.get("source_text")
    if not isinstance(source_text, list) or not source_text:
        return [
            _error(
                "QUALIFICATION_GATE_MISSING_SOURCE_TEXT",
                qualification_gate_id=gate.get("qualification_gate_id"),
                detail="qualification_gate.source_text must be a non-empty array of excerpts",
            )
        ]
    normalized_jd = _normalize_whitespace(jd_text if isinstance(jd_text, str) else "")
    for index, excerpt in enumerate(source_text):
        if not isinstance(excerpt, str) or not excerpt.strip():
            errors.append(
                _error(
                    "QUALIFICATION_GATE_INVALID_SOURCE_EXCERPT",
                    qualification_gate_id=gate.get("qualification_gate_id"),
                    index=index,
                    detail="each source_text excerpt must be a non-empty string",
                )
            )
            continue
        normalized_excerpt = _normalize_whitespace(excerpt)
        if normalized_excerpt not in normalized_jd:
            errors.append(
                _error(
                    "QUALIFICATION_GATE_SOURCE_NOT_TRACEABLE",
                    qualification_gate_id=gate.get("qualification_gate_id"),
                    index=index,
                    excerpt=excerpt,
                    detail=(
                        "source_text excerpt is not a whitespace-normalized "
                        "substring of the job's captured jd.txt; gate composition "
                        "must be deterministically traceable back to captured "
                        "raw employer text."
                    ),
                )
            )
    return errors


def evaluate_qualification_gate(
    gate: Mapping[str, Any],
    matches_by_req: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate one qualification_gate against the CURRENT match state.

    Returns:
      {
        "qualification_gate_id": str,
        "result": SUPPORTED | BLOCKED_BY_MATCHING_POLICY | UNRESOLVED,
        "leaf_support": {requirement_id: SUPPORTED|BLOCKED_BY_MATCHING_POLICY|UNRESOLVED, ...},
        "valid": bool,
        "errors": [...],
      }

    Does not mutate ``gate`` or ``matches_by_req``. Re-evaluating the same
    gate against a different (e.g. later, post-Claim-approval) match state
    requires no edit to the gate record itself (the static gate invariant).
    """
    leaf_ids = sorted(gate_leaf_ids(gate))
    leaf_support = {
        req_id: qualification_leaf_support(matches_by_req.get(req_id))
        for req_id in leaf_ids
    }
    clause_values = {req_id: _SUPPORT_TO_LOGIC[state] for req_id, state in leaf_support.items()}

    outcome = evaluate_expression(gate.get("logic_expression"), clause_values)
    if not outcome["valid"]:
        return {
            "qualification_gate_id": gate.get("qualification_gate_id"),
            "result": None,
            "leaf_support": leaf_support,
            "valid": False,
            "errors": outcome["errors"],
        }
    return {
        "qualification_gate_id": gate.get("qualification_gate_id"),
        "result": _LOGIC_TO_SUPPORT[outcome["result"]],
        "leaf_support": leaf_support,
        "valid": True,
        "errors": [],
    }
