"""Smallest possible adapter letting ApplicationQuestion clauses reuse the
existing Gate-1 Evidence/Claim matching primitives (requirement_match.py)
without creating, storing, or schema-validating a JD Requirement record.

An ApplicationQuestion clause is not a JD Requirement: it may exist only on
the application route (mapped_requirement_id = null). This module reuses
the same capability-inference and Claim-matching logic that already backs
`match_requirement()` -- it does not duplicate or reimplement that
capability vocabulary, and it never writes a Requirement to disk or to
`requirements.schema.json`-validated output. The ephemeral dict built here
exists only in memory for the duration of one match call.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from requirement_match import (
    _NONE_TRAPS,
    claim_capabilities,
    infer_requirement_capabilities,
)


def match_clause(
    *,
    clause_id: str,
    clause_text: str,
    reusable_claims: Sequence[Mapping[str, Any]],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Produce one clause-evaluation record (evidence_match-style vocabulary).

    Mirrors `requirement_match.match_requirement()`'s capability-matching
    algorithm exactly, scoped to a single clause's text. Returns
    ``{"clause_id", "result", "evidence_ids", "claim_ids", "explanation"}``
    with ``result`` in {STRONG, SUPPORTED, PARTIAL, NONE, UNKNOWN}.
    """
    pseudo_requirement = {
        "text": clause_text,
        "source_text": clause_text,
        "domain": None,
        "category": None,
        "technology": [],
    }
    caps = infer_requirement_capabilities(pseudo_requirement)

    for rule_id, trap_caps, explanation in _NONE_TRAPS:
        if caps.intersection(trap_caps):
            return {
                "clause_id": clause_id,
                "result": "NONE",
                "evidence_ids": [],
                "claim_ids": [],
                "explanation": (
                    f"[{rule_id}] clause={clause_text!r}; "
                    f"canonical={sorted(caps)}; {explanation}"
                ),
            }

    if not caps:
        return {
            "clause_id": clause_id,
            "result": "NONE",
            "evidence_ids": [],
            "claim_ids": [],
            "explanation": (
                f"clause={clause_text!r}; No specific capability tags inferred; "
                "refusing generic lexical overmatch."
            ),
        }

    best_claim: Mapping[str, Any] | None = None
    best_overlap: frozenset[str] = frozenset()
    for claim in reusable_claims:
        overlap = caps.intersection(claim_capabilities(claim))
        if len(overlap) > len(best_overlap):
            best_overlap = overlap
            best_claim = claim

    if best_claim is None or not best_overlap:
        return {
            "clause_id": clause_id,
            "result": "NONE",
            "evidence_ids": [],
            "claim_ids": [],
            "explanation": (
                f"clause={clause_text!r}; canonical={sorted(caps)}; "
                "No approved Claim capability intersection."
            ),
        }

    claim_id = best_claim.get("claim_id")
    claim_ids = [claim_id] if isinstance(claim_id, str) else []
    evidence_ids: list[str] = []
    cited = best_claim.get("evidence_ids")
    if isinstance(cited, list):
        for eid in cited:
            if isinstance(eid, str) and eid in evidence_index:
                evidence_ids.append(eid)
    evidence_ids = sorted(set(evidence_ids))

    claim_caps = claim_capabilities(best_claim)
    if caps.issubset(claim_caps):
        state = best_claim.get("evidence_state")
        result = "STRONG" if state in {"VERIFIED", "SUPPORTED"} else "SUPPORTED"
        explanation = (
            f"clause={clause_text!r}; canonical={sorted(best_overlap)}; "
            f"provenance claim={claim_id} evidence={evidence_ids}."
        )
    else:
        result = "PARTIAL"
        explanation = (
            f"clause={clause_text!r}; PARTIAL canonical overlap {sorted(best_overlap)}; "
            f"missing {sorted(caps - claim_caps)}; claim={claim_id}."
        )

    if result in {"STRONG", "SUPPORTED", "PARTIAL"} and not (claim_ids or evidence_ids):
        result = "NONE"
        explanation = "Positive match rejected: missing Evidence/Claim provenance."
        claim_ids = []
        evidence_ids = []

    return {
        "clause_id": clause_id,
        "result": result,
        "evidence_ids": evidence_ids,
        "claim_ids": claim_ids,
        "explanation": explanation,
    }
