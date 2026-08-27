"""Bounded deterministic claim semantic-boundary guard.

Detects known high-risk unsupported semantic upgrades and fabricated
quantified outcomes by comparing claim wording to cited Evidence records.

This is not general NLP truth verification and not a global keyword
blacklist: a phrase is blocked only when it appears in claim wording and
is not supported by the cited Evidence support corpus.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence


ERROR_CODE = "FORBIDDEN_SEMANTIC_PATTERN"


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _field_strings(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def build_evidence_support_corpus(
    cited_evidence: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
) -> str:
    """Concatenate cited Evidence truth fields into one searchable corpus."""
    parts: list[str] = []
    for record in cited_evidence:
        if not isinstance(record, Mapping):
            continue
        for key in (
            "fact",
            "notes",
            "workflow_stage",
            "capabilities",
            "technologies",
            "limitations",
            "tests",
            "stakeholders",
        ):
            parts.extend(_field_strings(record.get(key)))
    return _normalize(" ".join(parts))


# (rule_id, category, claim_pattern, evidence_support_pattern)
# Claim pattern must match wording; evidence pattern must then also match
# the cited support corpus or the claim is rejected.
_BOUNDARY_RULES: tuple[tuple[str, str, re.Pattern[str], re.Pattern[str]], ...] = (
    # A. Enterprise / platform scope upgrades
    (
        "enterprise_saas",
        "enterprise_platform_scope",
        re.compile(r"\benterprise\s+saas\b", re.IGNORECASE),
        re.compile(r"\benterprise\s+saas\b", re.IGNORECASE),
    ),
    (
        "enterprise_software_architecture",
        "enterprise_platform_scope",
        re.compile(r"\benterprise\s+software\s+architecture\b", re.IGNORECASE),
        re.compile(r"\benterprise\s+software\s+architecture\b", re.IGNORECASE),
    ),
    (
        "enterprise_architecture",
        "enterprise_platform_scope",
        re.compile(r"\benterprise\s+architecture\b", re.IGNORECASE),
        re.compile(r"\benterprise\s+architecture\b", re.IGNORECASE),
    ),
    (
        "saas_platform",
        "enterprise_platform_scope",
        re.compile(r"\bsaas\s+platform\b", re.IGNORECASE),
        re.compile(r"\bsaas\s+platform\b", re.IGNORECASE),
    ),
    # B. Unsupported technology / domain upgrades
    (
        "google_cloud",
        "unsupported_technology",
        re.compile(r"\bgoogle\s+cloud\b", re.IGNORECASE),
        re.compile(r"\bgoogle\s+cloud\b", re.IGNORECASE),
    ),
    (
        "cloud_engineering",
        "unsupported_technology",
        re.compile(r"\bcloud\s+engineering\b", re.IGNORECASE),
        re.compile(r"\bcloud\s+engineering\b", re.IGNORECASE),
    ),
    (
        "production_ml",
        "unsupported_technology",
        re.compile(r"\bproduction\s+ml\b", re.IGNORECASE),
        re.compile(r"\bproduction\s+ml\b", re.IGNORECASE),
    ),
    (
        "machine_learning_engineering",
        "unsupported_technology",
        re.compile(r"\bmachine\s+learning\s+engineering\b", re.IGNORECASE),
        re.compile(r"\bmachine\s+learning\s+engineering\b", re.IGNORECASE),
    ),
    (
        "ml_engineering",
        "unsupported_technology",
        re.compile(r"\bml\s+engineering\b", re.IGNORECASE),
        re.compile(r"\bml\s+engineering\b", re.IGNORECASE),
    ),
    (
        "production_machine_learning",
        "unsupported_technology",
        re.compile(r"\bproduction\s+machine\s+learning\b", re.IGNORECASE),
        re.compile(r"\bproduction\s+machine\s+learning\b", re.IGNORECASE),
    ),
    # C. QA ownership upgrades (UAT/pilot ≠ enterprise QA ownership)
    (
        "enterprise_qa",
        "qa_ownership_upgrade",
        re.compile(r"\benterprise\s+qa\b", re.IGNORECASE),
        re.compile(r"\benterprise\s+qa\b", re.IGNORECASE),
    ),
    (
        "qa_engineering",
        "qa_ownership_upgrade",
        re.compile(r"\bqa\s+engineering\b", re.IGNORECASE),
        re.compile(r"\bqa\s+engineering\b", re.IGNORECASE),
    ),
    (
        "qa_ownership",
        "qa_ownership_upgrade",
        re.compile(r"\bqa\s+ownership\b", re.IGNORECASE),
        re.compile(r"\bqa\s+ownership\b", re.IGNORECASE),
    ),
    (
        "production_qa",
        "qa_ownership_upgrade",
        re.compile(r"\bproduction\s+qa\b", re.IGNORECASE),
        re.compile(r"\bproduction\s+qa\b", re.IGNORECASE),
    ),
    (
        "enterprise_quality_assurance",
        "qa_ownership_upgrade",
        re.compile(r"\benterprise\s+quality\s+assurance\b", re.IGNORECASE),
        re.compile(r"\benterprise\s+quality\s+assurance\b", re.IGNORECASE),
    ),
)


# Quantified outcome / impact patterns. Captured group 1 is the numeric token
# that must appear in the cited Evidence corpus (digit form).
_QUANTIFIED_OUTCOME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "percent_outcome",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*%\s*"
            r"(?:increase|improvement|reduction|decrease|gain|growth|"
            r"fundraising|productivity|revenue|efficiency)",
            re.IGNORECASE,
        ),
    ),
    (
        "outcome_percent",
        re.compile(
            r"(?:increased|improved|reduced|decreased|saved|boosted|"
            r"grew|cut)\b[^.%]{0,40}?(?P<num>\d+(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
    ),
    (
        "fundraising_percent",
        re.compile(
            r"fundraising[^.%]{0,40}?(?P<num>\d+(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
    ),
    (
        "percent_fundraising",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*%[^.]{0,40}?fundraising",
            re.IGNORECASE,
        ),
    ),
    (
        "hours_per_period",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*hours?\s*(?:/|per)\s*"
            r"(?:month|week|day|year)",
            re.IGNORECASE,
        ),
    ),
    (
        "hours_saved_or_reduced",
        re.compile(
            r"(?:reduced|saved|cut|eliminated)\b[^.\d]{0,40}?"
            r"(?P<num>\d+(?:\.\d+)?)\s*hours?",
            re.IGNORECASE,
        ),
    ),
    (
        "hours_reduction_trailing",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*hours?\s*"
            r"(?:/|per)?\s*(?:month|week|day|year)?\s*"
            r"(?:reduction|saved|savings)",
            re.IGNORECASE,
        ),
    ),
    (
        "dollar_outcome",
        re.compile(
            r"\$\s*(?P<num>\d+(?:,\d{3})*(?:\.\d+)?)\b[^.]{0,40}?"
            r"(?:increase|improvement|reduction|decrease|saved|revenue|"
            r"fundraising|productivity)",
            re.IGNORECASE,
        ),
    ),
    (
        "productivity_gain_number",
        re.compile(
            r"productivity\s+(?:gain|increase|improvement)\b[^.\d]{0,40}?"
            r"(?P<num>\d+(?:\.\d+)?)\s*%?",
            re.IGNORECASE,
        ),
    ),
)


def _corpus_contains_number(corpus: str, number_token: str) -> bool:
    """Return True when the numeric token appears as a digit token in corpus."""
    normalized_num = number_token.replace(",", "")
    if not normalized_num:
        return False
    # Require digit form in evidence (e.g. "10" supports "10" / often "ten"
    # is also present for pilot rows; digit check is primary).
    pattern = re.compile(rf"(?<!\d){re.escape(normalized_num)}(?!\d)")
    if pattern.search(corpus):
        return True
    # Common word-number support for small factual counts already in evidence.
    word_map = {
        "10": r"\bten\b",
        "432": r"\bfour\s*hundred\s*(?:and\s*)?thirty[\s-]*two\b",
    }
    word_pat = word_map.get(normalized_num)
    if word_pat and re.search(word_pat, corpus, re.IGNORECASE):
        return True
    return False


def validate_claim_semantic_boundaries(
    claim: Any,
    cited_evidence: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Return blocking semantic-boundary errors for a claim vs cited Evidence.

    Empty list means no known forbidden upgrade / fabricated quantified
    outcome was detected relative to the cited Evidence corpus.
    """
    if not isinstance(claim, Mapping):
        return [
            _error(
                "MALFORMED_CLAIM",
                detail=f"claim must be a mapping; got {type(claim).__name__}",
            )
        ]

    wording = claim.get("wording")
    if not isinstance(wording, str) or not wording.strip():
        # Schema stage owns empty/missing wording; no extra semantic error.
        return []

    claim_id = claim.get("claim_id") if isinstance(claim.get("claim_id"), str) else None
    support = build_evidence_support_corpus(cited_evidence)
    errors: list[dict[str, Any]] = []
    seen_rules: set[str] = set()

    for rule_id, category, claim_pat, evidence_pat in _BOUNDARY_RULES:
        if rule_id in seen_rules:
            continue
        if not claim_pat.search(wording):
            continue
        if evidence_pat.search(support):
            continue
        seen_rules.add(rule_id)
        match = claim_pat.search(wording)
        matched = match.group(0) if match else rule_id
        errors.append(
            _error(
                ERROR_CODE,
                claim_id=claim_id,
                category=category,
                rule_id=rule_id,
                matched_text=matched,
                detail=(
                    f"claim wording introduces unsupported semantic upgrade "
                    f"{matched!r}; cited Evidence does not support this "
                    f"{category} claim"
                ),
            )
        )

    for outcome_id, outcome_pat in _QUANTIFIED_OUTCOME_PATTERNS:
        for match in outcome_pat.finditer(wording):
            number_token = match.group("num")
            if _corpus_contains_number(support, number_token):
                continue
            rule_key = f"quantified:{outcome_id}:{number_token}:{match.start()}"
            if rule_key in seen_rules:
                continue
            seen_rules.add(rule_key)
            errors.append(
                _error(
                    ERROR_CODE,
                    claim_id=claim_id,
                    category="fabricated_quantified_outcome",
                    rule_id=outcome_id,
                    matched_text=match.group(0).strip(),
                    unsupported_number=number_token,
                    detail=(
                        "claim wording introduces a quantified outcome "
                        f"({match.group(0).strip()!r}) that is not supported "
                        "by cited Evidence"
                    ),
                )
            )

    return errors
