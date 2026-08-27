"""Deterministic requirement → Evidence/Claim matching for Job Analysis v1.

Uses approved reusable claims and trusted Evidence records only.
Applies bounded semantic-boundary traps and conservative capability gating.

Generic lexical overlap alone cannot produce STRONG / SUPPORTED / PARTIAL.
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

# Known Winter Walk claim capability tags (derived from approved claim wording
# + cited Evidence capabilities). Not a general ontology.
_CLAIM_CAPABILITIES: dict[str, frozenset[str]] = {
    "CLAIM_WW_001": frozenset({"requirements_elicitation", "scope_boundary"}),
    "CLAIM_WW_002": frozenset(
        {"fail_closed_controls", "send_controls", "approval_gating"}
    ),
    "CLAIM_WW_003": frozenset({"data_ingestion", "csv_intake", "import_logging"}),
    "CLAIM_WW_004": frozenset(
        {
            "form_to_evidence_mapping",
            "approval_sync",
            "audit_logging",
            "workflow_automation",
        }
    ),
    "CLAIM_WW_005": frozenset({"uat", "pilot_testing", "test_documentation"}),
}

# Requirement → capability inference. Specific multi-token / domain patterns only.
_REQ_CAPABILITY_PATTERNS: tuple[tuple[re.Pattern[str], frozenset[str]], ...] = (
    (
        re.compile(
            r"requirements?\s+(gather|elicitation|definition)|"
            r"scope\s+boundar|clarifying\s+scope",
            re.I,
        ),
        frozenset({"requirements_elicitation", "scope_boundary"}),
    ),
    (
        re.compile(
            r"form[- ]to[- ]evidence|evidence[_ ]log|approval[- ]?sync|"
            r"approval[- ]synchron|adoption[_ ]matrix|self[- ]report\s+form",
            re.I,
        ),
        frozenset({"form_to_evidence_mapping", "approval_sync"}),
    ),
    (
        re.compile(
            r"fail[- ]closed|kill\s+switch|live\s+(email\s+)?send|"
            r"follow[- ]up\s+send\s+control",
            re.I,
        ),
        frozenset({"fail_closed_controls", "send_controls", "approval_gating"}),
    ),
    (
        re.compile(
            r"\bcsv\b|drive[- ]folder|data\s+ingestion|import\s+log",
            re.I,
        ),
        frozenset({"data_ingestion", "csv_intake", "import_logging"}),
    ),
    (
        re.compile(r"\buat\b|pilot\s+test|pilot\s+result|test\s+documentation", re.I),
        frozenset({"uat", "pilot_testing", "test_documentation"}),
    ),
    (
        re.compile(r"workflow\s+automation|automated\s+workflow", re.I),
        frozenset({"workflow_automation"}),
    ),
    (
        re.compile(
            r"process\s+map|workflow\s+map|business[- ]process\s+map|"
            r"map(?:ping)?\s+existing\s+business\s+process",
            re.I,
        ),
        frozenset({"process_mapping"}),
    ),
    (
        re.compile(
            r"\bu\.?s\.?\s+regulator|us\s+regulator|sec\s+reporting|\bsox\b|"
            r"regulatory\s+reporting|fincen",
            re.I,
        ),
        frozenset({"us_regulatory_reporting"}),
    ),
    (
        re.compile(r"\bsalesforce\b|\bsfdc\b", re.I),
        frozenset({"salesforce_administration"}),
    ),
    (
        re.compile(r"\bgoogle\s+cloud\b|\bgcp\b|cloud\s+engineer", re.I),
        frozenset({"google_cloud_engineering"}),
    ),
    (
        re.compile(
            r"production\s+ml|machine\s+learning|ml\s+engineer|deep\s+learning",
            re.I,
        ),
        frozenset({"production_ml"}),
    ),
    (
        re.compile(
            r"enterprise\s+qa|qa\s+ownership|qa\s+engineer|"
            r"quality\s+assurance\s+engineer",
            re.I,
        ),
        frozenset({"enterprise_qa_ownership"}),
    ),
    (
        re.compile(
            r"people[- ]management|managing\s+a\s+team|lead(?:ing)?\s+a\s+team|"
            r"direct\s+reports",
            re.I,
        ),
        frozenset({"people_management"}),
    ),
)

# Forced NONE traps for known unsupported upgrades (no positive transfer).
_NONE_TRAPS: tuple[tuple[str, frozenset[str], str], ...] = (
    (
        "salesforce_unsupported",
        frozenset({"salesforce_administration"}),
        "No approved Evidence/Claim supports Salesforce administration.",
    ),
    (
        "google_cloud_vs_apps_script",
        frozenset({"google_cloud_engineering"}),
        "Google Cloud / cloud engineering is not supported by Google Apps Script evidence.",
    ),
    (
        "production_ml",
        frozenset({"production_ml"}),
        "Production ML / machine learning engineering is unsupported by current Evidence.",
    ),
    (
        "enterprise_qa_ownership",
        frozenset({"enterprise_qa_ownership"}),
        "UAT/pilot documentation does not establish enterprise QA ownership.",
    ),
    (
        "us_regulatory",
        frozenset({"us_regulatory_reporting"}),
        "Current trusted Claim/Evidence banks do not support U.S. regulatory "
        "reporting / SEC / SOX-style domain expertise. Winter Walk software "
        "controls are not regulatory-domain evidence.",
    ),
    (
        "people_management",
        frozenset({"people_management"}),
        "No approved Evidence/Claim supports people-management / team-leadership.",
    ),
    (
        "process_mapping_unsupported",
        frozenset({"process_mapping"}),
        "No approved Claim establishes business-process mapping as a reusable capability.",
    ),
)


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold().replace("-", " ")).strip()


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


def infer_requirement_capabilities(requirement: Mapping[str, Any]) -> frozenset[str]:
    blob = _requirement_blob(requirement)
    caps: set[str] = set()
    for pattern, tags in _REQ_CAPABILITY_PATTERNS:
        if pattern.search(blob):
            caps.update(tags)
    return frozenset(caps)


def claim_capabilities(claim: Mapping[str, Any]) -> frozenset[str]:
    claim_id = claim.get("claim_id")
    if isinstance(claim_id, str) and claim_id in _CLAIM_CAPABILITIES:
        return _CLAIM_CAPABILITIES[claim_id]
    return frozenset()


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
    match_id = f"MATCH_{job_id}_{req_id}_{match_index:02d}"
    req_caps = infer_requirement_capabilities(requirement)

    # Forced NONE traps (including U.S. regulatory with current repository).
    for rule_id, trap_caps, explanation in _NONE_TRAPS:
        if req_caps.intersection(trap_caps):
            return {
                "match_id": match_id,
                "job_id": job_id,
                "requirement_id": req_id,
                "result": "NONE",
                "evidence_ids": [],
                "claim_ids": [],
                "explanation": f"[{rule_id}] {explanation}",
                "transfer_note": None,
            }

    if not req_caps:
        relevance = requirement.get("relevance")
        result = "UNKNOWN" if relevance == "LOW" else "NONE"
        return {
            "match_id": match_id,
            "job_id": job_id,
            "requirement_id": req_id,
            "result": result,
            "evidence_ids": [],
            "claim_ids": [],
            "explanation": (
                "No specific capability tags inferred for this requirement; "
                "refusing generic lexical overmatch."
            ),
            "transfer_note": None,
        }

    best_claim: Mapping[str, Any] | None = None
    best_overlap: frozenset[str] = frozenset()
    for claim in reusable_claims:
        overlap = req_caps.intersection(claim_capabilities(claim))
        if len(overlap) > len(best_overlap):
            best_overlap = overlap
            best_claim = claim

    if best_claim is None or not best_overlap:
        relevance = requirement.get("relevance")
        result = "UNKNOWN" if relevance == "LOW" else "NONE"
        return {
            "match_id": match_id,
            "job_id": job_id,
            "requirement_id": req_id,
            "result": result,
            "evidence_ids": [],
            "claim_ids": [],
            "explanation": (
                "No approved Claim capability intersection for inferred requirement "
                f"capabilities {sorted(req_caps)}."
            ),
            "transfer_note": None,
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
    # Full coverage of inferred requirement capabilities → STRONG/SUPPORTED.
    # Partial capability intersection → PARTIAL with transfer note.
    if req_caps.issubset(claim_caps):
        state = best_claim.get("evidence_state")
        result = "STRONG" if state in {"VERIFIED", "SUPPORTED"} else "SUPPORTED"
        transfer_note = None
        explanation = (
            f"Capability alignment on {sorted(best_overlap)} via approved claim "
            f"{claim_id}."
        )
    else:
        result = "PARTIAL"
        transfer_note = (
            "Partial capability overlap only; not full equivalence to the "
            f"requested capabilities {sorted(req_caps)}."
        )
        explanation = (
            f"PARTIAL capability overlap {sorted(best_overlap)}; missing "
            f"{sorted(req_caps - claim_caps)}."
        )

    if result in {"STRONG", "SUPPORTED", "PARTIAL"} and not (claim_ids or evidence_ids):
        result = "NONE"
        transfer_note = None
        explanation = "Positive match rejected: missing Evidence/Claim provenance."

    return {
        "match_id": match_id,
        "job_id": job_id,
        "requirement_id": req_id,
        "result": result,
        "evidence_ids": evidence_ids,
        "claim_ids": claim_ids,
        "explanation": explanation,
        "transfer_note": transfer_note,
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
                _error(
                    "MALFORMED_REQUIREMENT",
                    index=index,
                    detail="requirement must be a mapping",
                )
            )
            continue
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
                _error(
                    "EVIDENCE_MATCH_SCHEMA_INVALID",
                    requirement_id=requirement.get("requirement_id"),
                    details=schema_errors,
                )
            )
            continue
        if match["result"] in {"STRONG", "SUPPORTED", "PARTIAL"} and not (
            match["evidence_ids"] or match["claim_ids"]
        ):
            errors.append(
                _error(
                    "POSITIVE_MATCH_WITHOUT_PROVENANCE",
                    requirement_id=requirement.get("requirement_id"),
                    detail="positive match requires Evidence_ID and/or Claim_ID",
                )
            )
            continue
        matches.append(match)

    return {
        "valid": len(errors) == 0,
        "matches": matches,
        "errors": errors,
        "reusable_claim_count": len(reusable),
    }
