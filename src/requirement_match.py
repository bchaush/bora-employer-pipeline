"""Deterministic requirement → Evidence/Claim matching for Job Analysis v1.

Uses approved reusable claims and trusted Evidence records only.
Applies bounded semantic-boundary traps (Apps Script ≠ Google Cloud, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from claim_validation import validate_claim
from schema_validation import build_draft202012_validator


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_MATCH_SCHEMA_PATH = ROOT / "schemas" / "evidence_match.schema.json"

MATCH_RESULTS = frozenset({"STRONG", "SUPPORTED", "PARTIAL", "NONE", "UNKNOWN"})

# Bounded trap patterns: (rule_id, claim_pattern, forced_result_if_only_weak_support)
_TRAP_RULES: tuple[tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "google_cloud_vs_apps_script",
        re.compile(r"\bgoogle\s+cloud\b|\bgcp\b|\bcloud\s+engineer", re.I),
        "NONE",
        "Google Cloud / cloud engineering is not supported by Google Apps Script evidence.",
    ),
    (
        "salesforce_unsupported",
        re.compile(r"\bsalesforce\b|\bsfdc\b", re.I),
        "NONE",
        "No approved Evidence/Claim supports Salesforce administration or platform work.",
    ),
    (
        "production_ml",
        re.compile(
            r"\bproduction\s+ml\b|\bmachine\s+learning\b|\bml\s+engineer|"
            r"\bdeep\s+learning\b",
            re.I,
        ),
        "NONE",
        "Production ML / machine learning engineering is unsupported by current Evidence.",
    ),
    (
        "enterprise_qa_ownership",
        re.compile(
            r"\benterprise\s+qa\b|\bqa\s+ownership\b|\bqa\s+engineer|"
            r"\bquality\s+assurance\s+engineer",
            re.I,
        ),
        "NONE",
        "UAT/pilot documentation does not establish enterprise QA ownership.",
    ),
    (
        "us_regulatory",
        re.compile(
            r"\bu\.?s\.?\s+regulator|\bus\s+regulator|\bsec\s+reporting|"
            r"\bsox\b|\bfincen\b",
            re.I,
        ),
        "PARTIAL",
        "Controls/reconciliation-related experience may transfer; "
        "this is not U.S.-specific regulatory expertise.",
    ),
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().replace("-", " ")).strip()


def _support_blob(record: Mapping[str, Any], keys: Sequence[str]) -> str:
    parts: list[str] = []
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(item for item in value if isinstance(item, str))
    return _norm(" ".join(parts))


def load_reusable_claims(
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Return claim records that pass reusable validate_claim against Evidence."""
    reusable: list[Mapping[str, Any]] = []
    for claim in claim_index.values():
        if not isinstance(claim, Mapping):
            continue
        result = validate_claim(claim, evidence_index)
        if result.get("reusable") is True:
            reusable.append(claim)
    return reusable


def _requirement_blob(requirement: Mapping[str, Any]) -> str:
    parts = [
        str(requirement.get("text") or ""),
        str(requirement.get("source_text") or ""),
        str(requirement.get("domain") or ""),
        str(requirement.get("category") or ""),
    ]
    tech = requirement.get("technology")
    if isinstance(tech, list):
        parts.extend(str(item) for item in tech)
    return _norm(" ".join(parts))


def _capability_hits(
    req_blob: str,
    claim: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> tuple[list[str], list[str], int]:
    """Return (claim_ids, evidence_ids, score) for lexical/capability overlap."""
    claim_ids: list[str] = []
    evidence_ids: list[str] = []
    score = 0

    claim_blob = _norm(str(claim.get("wording") or ""))
    cited = claim.get("evidence_ids") if isinstance(claim.get("evidence_ids"), list) else []

    evidence_blobs: list[str] = []
    for eid in cited:
        if not isinstance(eid, str):
            continue
        record = evidence_index.get(eid)
        if isinstance(record, Mapping):
            evidence_blobs.append(
                _support_blob(
                    record,
                    (
                        "fact",
                        "capabilities",
                        "technologies",
                        "notes",
                        "workflow_stage",
                        "tests",
                    ),
                )
            )
            evidence_ids.append(eid)

    combined = _norm(claim_blob + " " + " ".join(evidence_blobs))

    # Token overlap on meaningful keywords (length > 3).
    req_tokens = {tok for tok in re.findall(r"[a-z0-9+]{4,}", req_blob)}
    support_tokens = {tok for tok in re.findall(r"[a-z0-9+]{4,}", combined)}
    overlap = req_tokens.intersection(support_tokens)

    # Capability phrase boosts.
    phrases = [
        "requirements",
        "workflow",
        "process",
        "uat",
        "pilot",
        "validation",
        "ingestion",
        "csv",
        "fail closed",
        "approval",
        "audit",
        "import",
        "mapping",
        "stakeholder",
        "google apps script",
        "google sheets",
        "data",
        "controls",
        "reconciliation",
    ]
    for phrase in phrases:
        if phrase in req_blob and phrase in combined:
            score += 3
            overlap.add(phrase.replace(" ", "_"))

    score += len(overlap)
    if score > 0:
        cid = claim.get("claim_id")
        if isinstance(cid, str):
            claim_ids.append(cid)
    return claim_ids, evidence_ids, score


def match_requirement(
    *,
    job_id: str,
    requirement: Mapping[str, Any],
    reusable_claims: Sequence[Mapping[str, Any]],
    evidence_index: Mapping[str, Any],
    match_index: int,
) -> dict[str, Any]:
    """Produce one evidence-match record for a requirement."""
    req_id = str(requirement.get("requirement_id"))
    req_blob = _requirement_blob(requirement)
    match_id = f"MATCH_{job_id}_{req_id}_{match_index:02d}"

    # Trap rules first.
    for rule_id, pattern, forced, explanation in _TRAP_RULES:
        if not pattern.search(req_blob):
            continue

        claim_ids: list[str] = []
        evidence_ids: list[str] = []
        transfer_note = None
        result = forced

        if forced == "PARTIAL":
            # Allow control/audit/fail-closed provenance as transfer signal only.
            for claim in reusable_claims:
                cids, eids, score = _capability_hits(req_blob, claim, evidence_index)
                control_blob = _norm(str(claim.get("wording") or ""))
                if score > 0 and any(
                    token in control_blob
                    for token in ("fail closed", "audit", "control", "approval", "validat")
                ):
                    claim_ids.extend(cids)
                    evidence_ids.extend(eids)
            # Also scan evidence for reconciliation/controls language.
            if not claim_ids:
                for eid, record in evidence_index.items():
                    if not isinstance(record, Mapping):
                        continue
                    blob = _support_blob(
                        record, ("fact", "capabilities", "notes", "limitations")
                    )
                    if any(
                        token in blob
                        for token in (
                            "fail closed",
                            "audit",
                            "control",
                            "reconcil",
                            "validat",
                        )
                    ):
                        evidence_ids.append(eid)
            claim_ids = sorted(set(claim_ids))
            evidence_ids = sorted(set(evidence_ids))
            if not claim_ids and not evidence_ids:
                result = "NONE"
                explanation = (
                    "U.S.-specific regulatory requirement has no transferable "
                    "controls/reconciliation provenance in the Claim/Evidence banks."
                )
            else:
                transfer_note = explanation
                explanation = (
                    "PARTIAL transfer only: related controls/process discipline may "
                    "apply; not U.S. regulatory expertise."
                )
        else:
            # Forced NONE traps: ignore Apps Script / UAT weak support.
            claim_ids = []
            evidence_ids = []

        return {
            "match_id": match_id,
            "job_id": job_id,
            "requirement_id": req_id,
            "result": result,
            "evidence_ids": evidence_ids,
            "claim_ids": claim_ids,
            "explanation": f"[{rule_id}] {explanation}",
            "transfer_note": transfer_note,
        }

    # Ordinary capability matching.
    best: dict[str, Any] | None = None
    best_score = 0
    for claim in reusable_claims:
        cids, eids, score = _capability_hits(req_blob, claim, evidence_index)
        if score > best_score:
            best_score = score
            best = {
                "claim_ids": cids,
                "evidence_ids": sorted(set(eids)),
                "score": score,
                "claim_state": claim.get("evidence_state"),
            }

    if best is None or best_score <= 0:
        relevance = requirement.get("relevance")
        if relevance == "LOW":
            result = "UNKNOWN"
            explanation = (
                "No Evidence/Claim overlap found; requirement relevance is LOW "
                "so match remains UNKNOWN rather than a hard NONE gap."
            )
        else:
            result = "NONE"
            explanation = (
                "No approved Claim or Evidence provenance supports this requirement."
            )
        return {
            "match_id": match_id,
            "job_id": job_id,
            "requirement_id": req_id,
            "result": result,
            "evidence_ids": [],
            "claim_ids": [],
            "explanation": explanation,
            "transfer_note": None,
        }

    # Score thresholds → STRONG / SUPPORTED / PARTIAL
    if best_score >= 10 and best.get("claim_state") in {"VERIFIED", "SUPPORTED"}:
        result = "STRONG"
    elif best_score >= 6:
        result = "SUPPORTED"
    elif best_score >= 3:
        result = "PARTIAL"
    else:
        result = "PARTIAL"

    # Positive matches must expose provenance.
    if result in {"STRONG", "SUPPORTED", "PARTIAL"} and not (
        best["claim_ids"] or best["evidence_ids"]
    ):
        result = "NONE"

    return {
        "match_id": match_id,
        "job_id": job_id,
        "requirement_id": req_id,
        "result": result,
        "evidence_ids": best["evidence_ids"],
        "claim_ids": best["claim_ids"],
        "explanation": (
            f"Matched via approved Claim/Evidence overlap (score={best_score})."
        ),
        "transfer_note": (
            "Related capability overlap only; not full equivalence."
            if result == "PARTIAL"
            else None
        ),
    }


def match_requirements(
    *,
    job_id: str,
    requirements: Sequence[Mapping[str, Any]],
    claim_index: Mapping[str, Any],
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Match all requirements; validate each evidence_match against schema."""
    validator = build_draft202012_validator(EVIDENCE_MATCH_SCHEMA_PATH)
    reusable = load_reusable_claims(claim_index, evidence_index)
    matches: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, Mapping):
            errors.append(
                {
                    "code": "MALFORMED_REQUIREMENT",
                    "index": index,
                    "detail": "requirement must be a mapping",
                }
            )
            continue
        # Skip low-relevance UNCLEAR noise unless technology is present.
        if (
            requirement.get("importance") == "UNCLEAR"
            and requirement.get("relevance") == "LOW"
            and not requirement.get("technology")
        ):
            continue

        match = match_requirement(
            job_id=job_id,
            requirement=requirement,
            reusable_claims=reusable,
            evidence_index=evidence_index,
            match_index=index,
        )
        schema_errors = [err.message for err in validator.iter_errors(match)]
        if schema_errors:
            errors.append(
                {
                    "code": "EVIDENCE_MATCH_SCHEMA_INVALID",
                    "requirement_id": requirement.get("requirement_id"),
                    "details": schema_errors,
                }
            )
            continue
        # Enforce provenance rule for positive matches.
        if match["result"] in {"STRONG", "SUPPORTED", "PARTIAL"} and not (
            match["evidence_ids"] or match["claim_ids"]
        ):
            errors.append(
                {
                    "code": "POSITIVE_MATCH_WITHOUT_PROVENANCE",
                    "requirement_id": requirement.get("requirement_id"),
                    "detail": "positive match requires Evidence_ID and/or Claim_ID",
                }
            )
            continue
        matches.append(match)

    return {
        "valid": len(errors) == 0,
        "matches": matches,
        "errors": errors,
        "reusable_claim_count": len(reusable),
    }
