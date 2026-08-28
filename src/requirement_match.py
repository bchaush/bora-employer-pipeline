"""Deterministic requirement → Evidence/Claim matching for Job Analysis v1.

Uses approved reusable claims and trusted Evidence records only.
Applies bounded semantic-boundary traps and conservative capability gating.

Generic lexical overlap alone cannot produce STRONG / SUPPORTED / PARTIAL.
JD anchors map only to existing canonical capabilities (no dynamic ontology).
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
    "CLAIM_WW_006": frozenset({"process_mapping"}),
}

# Bounded JD-anchor → existing canonical capability mappings only.
_REQ_CAPABILITY_PATTERNS: tuple[tuple[re.Pattern[str], frozenset[str]], ...] = (
    (
        re.compile(
            r"requirements?\s+(?:gather(?:ing)?|elicitation|definition|collection)|"
            r"(?:gather|collect|clarify|document|elicit|translate|capture|turn|"
            r"convert)(?:ing)?\s+(?:\w+\s+){0,3}(?:requirements?|needs?)\b|"
            r"(?:turn|translate|capture|convert)(?:ing)?\s+"
            r"(?:\w+\s+){0,2}(?:user|stakeholder|business)\s+needs?\s+"
            r"(?:into\s+)?(?:functional\s+)?requirements?\b|"
            r"(?:stakeholder|business)\s+requirements?\b|"
            r"(?:stakeholder|business)\s+needs?\s+into\s+documented\s+requirements?\b|"
            r"clarify(?:ing)?\s+(?:\w+\s+){0,4}(?:requirements?|needs?|scope|changes?)\b|"
            r"scope\s+boundar|clarify(?:ing)?\s+scope",
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
            r"follow[- ]up\s+send\s+control|controlled\s+(?:outbound\s+)?send",
            re.I,
        ),
        frozenset({"fail_closed_controls", "send_controls", "approval_gating"}),
    ),
    (
        re.compile(
            r"\bcsv\b|drive[- ]folder|"
            r"data\s+ingestion|data\s+import|import(?:ing)?\s+data|"
            r"ingest(?:ing)?\s+data|data\s+feeds?|spreadsheet\s+data\s+feeds?|"
            r"spreadsheet\s+feeds?|file\s+import|csv\s+import|import\s+log|"
            r"data\s+(?:intake|validation)\b|"
            r"(?:ingest|load|import)(?:ing)?\s+"
            r"(?:\w+\s+){0,4}"
            r"(?:structured\s+|tabular\s+|source\s+|operational\s+|incoming\s+|recurring\s+)?"
            r"(?:data|files?|datasets?|feeds?|csv|spreadsheets?)\b|"
            r"consolidat(?:e|ing)\s+(?:\w+\s+){0,3}"
            r"(?:incoming\s+)?(?:data|files?|datasets?|feeds?)\b|"
            r"incoming\s+datasets?\b",
            re.I,
        ),
        frozenset({"data_ingestion", "csv_intake", "import_logging"}),
    ),
    (
        re.compile(
            r"\buat\b|user\s+acceptance\s+test(?:ing)?|acceptance\s+testing|"
            r"acceptance[- ]test(?:ing|s| cycles)?|"
            r"pilot\s+test(?:ing)?|pilot\s+validation|pilot\s+result|"
            r"validat(?:e|ing)\s+(?:a\s+)?pilot\b|"
            r"user\s+testing|test\s+documentation",
            re.I,
        ),
        frozenset({"uat", "pilot_testing", "test_documentation"}),
    ),
    # R-7: bare "workflow automation" is insufficient; require operational context.
    (
        re.compile(
            r"(?:"
            r"(?:workflow|process)\s+automation|"
            r"automated\s+(?:workflow|process)"
            r").{0,80}(?:"
            r"evidence|approval|fail[- ]closed|controlled|operational|"
            r"self[- ]report|reconcil|validated\s+data|import\s+log|"
            r"data\s+(?:intake|ingestion|validation)"
            r")"
            r"|"
            r"(?:"
            r"evidence|approval|fail[- ]closed|controlled|operational|"
            r"self[- ]report|reconcil|validated\s+data"
            r").{0,80}(?:"
            r"(?:workflow|process)\s+automation|automated\s+(?:workflow|process)"
            r")",
            re.I,
        ),
        frozenset({"workflow_automation"}),
    ),
    # Process / workflow mapping — bounded; domain text like "Business Process"
    # alone cannot false-fire without mapping/documentation verbs.
    (
        re.compile(
            r"\bprocess\s+map(?:ping)?\b|\bworkflow\s+map(?:ping)?\b|"
            r"\bbusiness[- ]process\s+map(?:ping)?\b|"
            r"\bmap(?:ping)?\s+existing\s+business\s+processes?\b|"
            r"\bmap(?:ping)?\s+current[- ]state\s+workflows?\b|"
            r"\bmap(?:ping)?\s+operational\s+handoffs?\b|"
            r"\bmap(?:ping)?\s+(?:as[- ]is|to[- ]be)\s+processes?\b|"
            r"\bmap(?:ping)?\s+workflows?\b|"
            r"\bcreate(?:ing)?\s+workflow\s+maps?\b|"
            r"\bidentify(?:ing)?\s+process\s+steps?\s+and\s+bottlenecks?\b|"
            r"\bdocument(?:ing)?\s+business\s+processes?\b|"
            r"\bdocument(?:ing)?\s+(?:as[- ]is\s+|to[- ]be\s+|"
            r"current[- ]state\s+and\s+future[- ]state\s+)?"
            r"(?:workflows?|business\s+processes?)\b",
            re.I,
        ),
        frozenset({"process_mapping"}),
    ),
    (
        re.compile(
            r"\bbpmn(?:\s*2(?:\.0)?)?\b|\bbusiness\s+process\s+model(?:ing)?\s+notation\b|"
            r"formal\s+enterprise\s+process\s+model(?:ing)?\b|"
            r"enterprise\s+process\s+architect(?:ure)?\b|"
            r"business[- ]process\s+modeling\s+certification|"
            r"process\s+reengineering\s+leadership|"
            r"enterprise\s+process\s+reengineering",
            re.I,
        ),
        frozenset({"bpmn_modeling"}),
    ),
    (
        re.compile(
            r"\bsix\s+sigma\b|\blean\b|\bvalue\s+stream\s+mapping\b|"
            r"\blean\s+(?:six\s+sigma|process\s+engineering)\b|"
            r"lean\s+certification\b",
            re.I,
        ),
        frozenset({"lean_six_sigma"}),
    ),
    (
        re.compile(
            r"\bcelonis\b|\bui\s*path\s+process\s+mining\b|"
            r"process[- ]min(?:ing|e)(?:\s+telemetry)?\b|"
            r"automated\s+process\s+min(?:ing|e)\b",
            re.I,
        ),
        frozenset({"process_mining_telemetry"}),
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
        re.compile(r"\bworkday\b|\bservicenow\b|\bsnow\b", re.I),
        frozenset({"enterprise_platform_specialization"}),
    ),
    (
        re.compile(r"\bgoogle\s+cloud\b|\bgcp\b|cloud\s+engineer", re.I),
        frozenset({"google_cloud_engineering"}),
    ),
    (
        re.compile(
            r"production\s+ml|machine\s+learning|ml\s+engineer|deep\s+learning|"
            r"\bmlops\b|model\s+deploy",
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
    (
        re.compile(
            r"cybersecurity|security\s+controls?|soc\s*2|infosec|"
            r"penetration\s+test",
            re.I,
        ),
        frozenset({"cybersecurity_controls"}),
    ),
    (
        re.compile(
            r"marketing\s+(?:workflow\s+)?automation|marketing\s+campaign|"
            r"paid\s+media|audience\s+funnel",
            re.I,
        ),
        frozenset({"marketing_automation"}),
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
        "enterprise_platform_unsupported",
        frozenset({"enterprise_platform_specialization"}),
        "No approved Evidence/Claim supports Workday/ServiceNow specialization.",
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
        "bpmn_modeling_unsupported",
        frozenset({"bpmn_modeling"}),
        "No approved Evidence/Claim supports BPMN / formal enterprise process "
        "modeling expertise.",
    ),
    (
        "lean_six_sigma_unsupported",
        frozenset({"lean_six_sigma"}),
        "No approved Evidence/Claim supports Lean / Six Sigma certification or "
        "formal-framework expertise.",
    ),
    (
        "process_mining_unsupported",
        frozenset({"process_mining_telemetry"}),
        "No approved Evidence/Claim supports automated process-mining / telemetry "
        "platforms (e.g. Celonis, UiPath Process Mining).",
    ),
    (
        "cybersecurity_unsupported",
        frozenset({"cybersecurity_controls"}),
        "No approved Evidence/Claim supports cybersecurity / infosec controls expertise.",
    ),
    (
        "marketing_automation_unsupported",
        frozenset({"marketing_automation"}),
        "Marketing automation / paid-media work is outside approved Claim capabilities.",
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
    req_text = str(requirement.get("text") or "")
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
                "explanation": (
                    f"[{rule_id}] raw={req_text!r}; "
                    f"canonical={sorted(req_caps)}; {explanation}"
                ),
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
                f"raw={req_text!r}; No specific capability tags inferred; "
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
                f"raw={req_text!r}; canonical={sorted(req_caps)}; "
                "No approved Claim capability intersection."
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
            f"raw={req_text!r}; canonical={sorted(best_overlap)}; "
            f"provenance claim={claim_id} evidence={evidence_ids}."
        )
    else:
        result = "PARTIAL"
        transfer_note = (
            "Partial capability overlap only; not full equivalence to the "
            f"requested capabilities {sorted(req_caps)}."
        )
        explanation = (
            f"raw={req_text!r}; PARTIAL canonical overlap {sorted(best_overlap)}; "
            f"missing {sorted(req_caps - claim_caps)}; claim={claim_id}."
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
