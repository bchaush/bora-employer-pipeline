"""Bounded deterministic claim semantic-boundary guard.

Detects known high-risk unsupported semantic upgrades and fabricated
quantified outcomes by comparing claim wording to cited Evidence records.

This is not general NLP truth verification and not a global keyword
blacklist: a phrase is blocked only when it appears in claim wording and
is not positively supported by the cited Evidence support corpus.

Positive support requires:
- a match in the Evidence corpus for the guarded concept; and
- that match not sitting inside an explicit negated/excluded local window.

Quantified outcomes additionally require the matching number to appear in
Evidence near related outcome-category language (not a bare number alone).

Actor-attribution overreach (sole/exclusive/unaided authorship) is a
separate, unconditional check: per
docs/decisions/ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md, no Evidence record
in this architecture can license sole/exclusive/unaided-authorship wording,
so these patterns are blocked regardless of cited Evidence content and
regardless of human_approval.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence


ERROR_CODE = "FORBIDDEN_SEMANTIC_PATTERN"
ACTOR_ATTRIBUTION_CATEGORY = "sole_exclusive_unaided_authorship_overreach"

# Local window sizes for bounded negation / outcome-context checks.
_NEGATION_BEFORE = 90
_NEGATION_AFTER = 40
_OUTCOME_WINDOW = 80


def _error(code: str, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code}
    payload.update(fields)
    return payload


def _normalize(text: str) -> str:
    """Lowercase, hyphen→space, collapse whitespace."""
    lowered = text.casefold()
    lowered = lowered.replace("-", " ")
    return re.sub(r"\s+", " ", lowered).strip()


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


# Explicit negation / exclusion cues. Applied to a local window around a match.
_NEGATION_CUES: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdoes not\b"),
    re.compile(r"\bdid not\b"),
    re.compile(r"\bis not\b"),
    re.compile(r"\bwas not\b"),
    re.compile(r"\bwere not\b"),
    re.compile(r"\bare not\b"),
    re.compile(r"\bcannot\b"),
    re.compile(r"\bcan'?t\b"),
    re.compile(r"\bnever\b"),
    re.compile(r"\bwithout\b"),
    re.compile(r"\bexcluded\b"),
    re.compile(r"\bout of scope\b"),
    re.compile(r"\bnot confirmed\b"),
    re.compile(r"\bnot measured\b"),
    re.compile(r"\bnot verified\b"),
    re.compile(r"\bdoes not establish\b"),
    re.compile(r"\bdoes not demonstrate\b"),
    re.compile(r"\bexplicitly excluded\b"),
    re.compile(r"\bnot a\b"),
    re.compile(r"\bnot an\b"),
    re.compile(r"\bno measured\b"),
    re.compile(r"\bno\b"),
    re.compile(r"\bnot\b"),
)


def _window_is_negated(text: str, start: int, end: int) -> bool:
    """Return True when an explicit negation cue appears near the match."""
    before = text[max(0, start - _NEGATION_BEFORE) : start]
    after = text[end : min(len(text), end + _NEGATION_AFTER)]
    window = f"{before} {after}"
    return any(cue.search(window) for cue in _NEGATION_CUES)


def _has_positive_pattern_support(corpus: str, pattern: re.Pattern[str]) -> bool:
    """True when pattern matches corpus at least once outside negated context."""
    for match in pattern.finditer(corpus):
        if _window_is_negated(corpus, match.start(), match.end()):
            continue
        return True
    return False


# (rule_id, category, claim_pattern, evidence_support_pattern)
# Patterns operate on normalized text (hyphens already spaces).
_BOUNDARY_RULES: tuple[tuple[str, str, re.Pattern[str], re.Pattern[str]], ...] = (
    # A. Enterprise / platform scope upgrades
    (
        "enterprise_saas",
        "enterprise_platform_scope",
        re.compile(r"\benterprise\s+saas(?:\s+platform)?\b"),
        re.compile(r"\benterprise\s+saas(?:\s+platform)?\b"),
    ),
    (
        "enterprise_software_architecture",
        "enterprise_platform_scope",
        re.compile(r"\benterprise\s+software\s+architect(?:ure|ing)?\b"),
        re.compile(r"\benterprise\s+software\s+architect(?:ure|ing)?\b"),
    ),
    (
        "enterprise_architecture",
        "enterprise_platform_scope",
        re.compile(r"\benterprise\s+architect(?:ure|ing)?\b"),
        re.compile(r"\benterprise\s+architect(?:ure|ing)?\b"),
    ),
    (
        "architected_enterprise_software",
        "enterprise_platform_scope",
        re.compile(
            r"\barchitect(?:ed|ing|ure)?\b[\w\s]{0,40}\benterprise\s+software\b"
            r"|\benterprise\s+software\b[\w\s]{0,40}\barchitect(?:ed|ing|ure)?\b"
        ),
        re.compile(
            r"\benterprise\s+software\s+architect(?:ure|ing)?\b"
            r"|\benterprise\s+architect(?:ure|ing)?\b"
            r"|\barchitect(?:ed|ing|ure)?\b[\w\s]{0,40}\benterprise\s+software\b"
        ),
    ),
    (
        "saas_platform",
        "enterprise_platform_scope",
        re.compile(r"\bsaas\s+platform\b"),
        re.compile(r"\bsaas\s+platform\b"),
    ),
    # B. Unsupported technology / domain upgrades
    (
        "google_cloud",
        "unsupported_technology",
        re.compile(r"\bgoogle\s+cloud\b"),
        re.compile(r"\bgoogle\s+cloud\b"),
    ),
    (
        "cloud_engineering",
        "unsupported_technology",
        re.compile(r"\bcloud\s+engineering\b"),
        re.compile(r"\bcloud\s+engineering\b"),
    ),
    (
        "production_ml",
        "unsupported_technology",
        re.compile(
            r"\bproduction\s+ml(?:\s+(?:pipeline|system|systems))?\b"
            r"|\bml\s+production(?:\s+(?:pipeline|system|systems))?\b"
            r"|\bproduction\s+machine\s+learning(?:\s+(?:pipeline|system|systems))?\b"
            r"|\bmachine\s+learning\s+production(?:\s+(?:pipeline|system|systems))?\b"
        ),
        re.compile(
            r"\bproduction\s+ml(?:\s+(?:pipeline|system|systems))?\b"
            r"|\bml\s+production(?:\s+(?:pipeline|system|systems))?\b"
            r"|\bproduction\s+machine\s+learning(?:\s+(?:pipeline|system|systems))?\b"
            r"|\bmachine\s+learning\s+production(?:\s+(?:pipeline|system|systems))?\b"
        ),
    ),
    (
        "machine_learning_engineering",
        "unsupported_technology",
        re.compile(r"\bmachine\s+learning\s+engineering\b"),
        re.compile(r"\bmachine\s+learning\s+engineering\b"),
    ),
    (
        "ml_engineering",
        "unsupported_technology",
        re.compile(r"\bml\s+engineering\b"),
        re.compile(r"\bml\s+engineering\b"),
    ),
    # C. QA ownership upgrades (UAT/pilot ≠ enterprise QA ownership)
    (
        "enterprise_qa",
        "qa_ownership_upgrade",
        re.compile(
            r"\benterprise\s+qa(?:\s+engineering)?\b"
            r"|\benterprise\s+quality\s+(?:assurance|engineering)\b"
        ),
        re.compile(
            r"\benterprise\s+qa(?:\s+engineering)?\b"
            r"|\benterprise\s+quality\s+(?:assurance|engineering)\b"
        ),
    ),
    (
        "qa_engineering",
        "qa_ownership_upgrade",
        re.compile(r"\bqa\s+engineering(?:\s+ownership)?\b"),
        re.compile(r"\bqa\s+engineering(?:\s+ownership)?\b"),
    ),
    (
        "qa_ownership",
        "qa_ownership_upgrade",
        re.compile(r"\bqa\s+ownership\b"),
        re.compile(r"\bqa\s+ownership\b"),
    ),
    (
        "production_qa",
        "qa_ownership_upgrade",
        re.compile(r"\bproduction\s+qa(?:\s+ownership)?\b"),
        re.compile(r"\bproduction\s+qa(?:\s+ownership)?\b"),
    ),
)


# Actor-attribution overreach: sole / exclusive / unaided-authorship wording.
#
# Unlike _BOUNDARY_RULES, these are NOT evidence-relative. Per
# ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1, human_approval may authorize
# conventional active-voice attribution (Built, Implemented, Integrated,
# Automated, Defined, Documented, Separated) for work substantive Evidence
# supports, but it can never establish sole intellectual authorship,
# exclusive implementation/ownership, absence of AI assistance, or absence
# of collaborators. No Evidence record in this architecture can license
# those stronger propositions, so these patterns are unconditional: they
# block regardless of cited Evidence content and regardless of
# human_approval.
#
# Bounded action-term vocabulary shared by these rules (kept narrow so
# generic words like "independent"/"independently" alone never match).
_ATTRIBUTION_ACTION_TERM = (
    r"(?:built|build|develop(?:ed|ing)?|creat(?:ed|ing)|implement(?:ed|ing)?|"
    r"architect(?:ed|ing)?|design(?:ed|ing)?|author(?:ed|ing)?)"
)

# (rule_id, pattern) — normalized-text patterns, matched unconditionally.
_ACTOR_ATTRIBUTION_OVERREACH_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "sole_authorship_verb",
        re.compile(rf"\bsole(?:ly)?\s+{_ATTRIBUTION_ACTION_TERM}\b"),
    ),
    (
        "sole_authorship_noun",
        re.compile(
            r"\bsole\s+(?:author|creator|developer|architect|designer|owner)\b"
        ),
    ),
    (
        "single_handed_authorship",
        re.compile(
            rf"\bsingle\s?handed(?:ly)?\b[\w\s]{{0,20}}\b{_ATTRIBUTION_ACTION_TERM}\b"
            rf"|\b{_ATTRIBUTION_ACTION_TERM}\b[\w\s]{{0,20}}\bsingle\s?handed(?:ly)?\b"
        ),
    ),
    (
        "exclusive_authorship_verb",
        re.compile(rf"\bexclusive(?:ly)?\s+{_ATTRIBUTION_ACTION_TERM}\b"),
    ),
    (
        "exclusive_authorship_noun",
        re.compile(
            r"\bexclusive\s+(?:author|creator|developer|architect|designer|"
            r"owner|implementation)\b"
        ),
    ),
    (
        "entirely_own_work",
        re.compile(
            r"\bentirely\s+my\s+own\s+(?:implementation|work|code|design)\b"
        ),
    ),
    (
        "action_term_alone",
        re.compile(rf"\b{_ATTRIBUTION_ACTION_TERM}\b[\w\s]{{0,40}}\balone\b"),
    ),
    (
        "no_ai_assistance",
        re.compile(
            r"\bno\s+(?:ai|artificial\s+intelligence)\s+(?:assistance|help|support)\b"
        ),
    ),
    (
        "without_ai_assistance",
        re.compile(
            r"\bwithout\s+(?:any\s+)?(?:ai|artificial\s+intelligence)\s+"
            r"(?:assistance|help|support)\b"
        ),
    ),
    (
        "all_code_without_ai",
        re.compile(r"\bwrote\s+all\s+(?:the\s+)?code\s+without\s+ai\b"),
    ),
    (
        "unaided_implementation",
        re.compile(r"\bunaided\s+implementation\b"),
    ),
    (
        "action_term_without_assistance",
        re.compile(
            rf"\b{_ATTRIBUTION_ACTION_TERM}\b[\w\s]{{0,40}}\bwithout\s+"
            rf"(?:any\s+)?(?:assistance|help)\b"
        ),
    ),
    (
        "no_collaborators",
        re.compile(r"\bno\s+collaborators?\b|\bwithout\s+collaborators?\b"),
    ),
    (
        "entirely_alone",
        re.compile(r"\bentirely\s+alone\b"),
    ),
)


# Quantified outcome patterns on normalized claim text.
# Each entry: (rule_id, pattern with named group "num", outcome category tags)
_QUANTIFIED_OUTCOME_PATTERNS: tuple[
    tuple[str, re.Pattern[str], frozenset[str]],
    ...,
] = (
    (
        "percent_outcome",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*%\s*"
            r"(?:increase|improvement|reduction|decrease|gain|growth|"
            r"fundraising|productivity|revenue|efficiency)"
        ),
        frozenset({"percent", "change"}),
    ),
    (
        "outcome_percent",
        re.compile(
            r"(?:increased|improved|reduced|decreased|saved|boosted|"
            r"grew|cut)\b[^.%]{0,50}?(?P<num>\d+(?:\.\d+)?)\s*%"
        ),
        frozenset({"percent", "change"}),
    ),
    (
        "fundraising_percent",
        re.compile(
            r"fundraising[^.%]{0,50}?(?P<num>\d+(?:\.\d+)?)\s*%"
            r"|(?:increased|improved)\s+fundraising\s+by\s+"
            r"(?P<num2>\d+(?:\.\d+)?)\s*%"
        ),
        frozenset({"fundraising", "percent", "change"}),
    ),
    (
        "percent_fundraising",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*%[^.]{0,50}?fundraising"
        ),
        frozenset({"fundraising", "percent", "change"}),
    ),
    (
        "hours_per_period",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*hours?\s*(?:/|per)\s*"
            r"(?:month|week|day|year)"
        ),
        frozenset({"hours", "change"}),
    ),
    (
        "hours_saved_or_reduced",
        re.compile(
            r"(?:reduced|saved|cut|eliminated)\b[^.\d]{0,50}?"
            r"(?P<num>\d+(?:\.\d+)?)\s*hours?"
        ),
        frozenset({"hours", "change"}),
    ),
    (
        "hours_reduction_trailing",
        re.compile(
            r"(?P<num>\d+(?:\.\d+)?)\s*hours?\s*"
            r"(?:/|per)?\s*(?:month|week|day|year)?\s*"
            r"(?:reduction|saved|savings)"
        ),
        frozenset({"hours", "change"}),
    ),
    (
        "dollar_outcome",
        re.compile(
            r"\$\s*(?P<num>\d+(?:,\d{3})*(?:\.\d+)?)\b[^.]{0,50}?"
            r"(?:increase|improvement|reduction|decrease|saved|revenue|"
            r"fundraising|productivity|generated)"
            r"|(?:generated|raised|earned|saved)\b[^.$]{0,40}?"
            r"\$\s*(?P<num2>\d+(?:,\d{3})*(?:\.\d+)?)"
        ),
        frozenset({"money", "change"}),
    ),
    (
        "productivity_gain_number",
        re.compile(
            r"productivity\s+(?:gain|increase|improvement)\b[^.\d]{0,40}?"
            r"(?P<num>\d+(?:\.\d+)?)\s*%?"
            r"|(?:improved|increased)\s+productivity\s+by\s+"
            r"(?P<num2>\d+(?:\.\d+)?)\s*%?"
        ),
        frozenset({"productivity", "percent", "change"}),
    ),
    (
        "processing_time_reduction",
        re.compile(
            r"(?:reduced|reduce|cut)\s+processing\s+time\s+by\s+"
            r"(?P<num>\d+(?:\.\d+)?)\s*%"
            r"|processing\s+time[^.%]{0,40}?(?P<num2>\d+(?:\.\d+)?)\s*%"
        ),
        frozenset({"hours", "percent", "change"}),
    ),
)


# Outcome-category cues that must appear near a supporting Evidence number.
_OUTCOME_CATEGORY_CUES: dict[str, re.Pattern[str]] = {
    "fundraising": re.compile(r"\bfundrais"),
    "productivity": re.compile(r"\bproductiv"),
    "hours": re.compile(
        r"\bhours?\b|\btime saved\b|\bprocessing time\b|\bsaved\b|\breduction\b"
    ),
    "money": re.compile(r"\$|\bdollars?\b|\brevenue\b|\bcost\b|\bgenerated\b"),
    "percent": re.compile(r"%|\bpercent(?:age)?\b"),
    "change": re.compile(
        r"\bincrease(?:d|s)?\b|\bdecrease(?:d|s)?\b|\breduc(?:e|ed|tion)\b|"
        r"\bimprov(?:e|ed|ement)\b|\bsaved\b|\bgain(?:s|ed)?\b|\bgenerated\b|"
        r"\bgrowth\b"
    ),
}


def _extract_claim_number(match: re.Match[str]) -> str | None:
    for key in ("num", "num2"):
        value = match.groupdict().get(key)
        if value:
            return value.replace(",", "")
    return None


def _infer_extra_tags_from_span(span: str) -> frozenset[str]:
    tags: set[str] = set()
    if re.search(r"\bfundrais", span):
        tags.add("fundraising")
    if re.search(r"\bproductiv", span):
        tags.add("productivity")
    if re.search(r"\bhours?\b|\bprocessing time\b|\btime saved\b", span):
        tags.add("hours")
    if re.search(r"\$|\bdollar|\brevenue|\bgenerated|\bcost", span):
        tags.add("money")
    if re.search(r"%|\bpercent", span):
        tags.add("percent")
    return frozenset(tags)


def _number_occurrences(corpus: str, number_token: str) -> list[re.Match[str]]:
    normalized_num = number_token.replace(",", "")
    if not normalized_num:
        return []
    pattern = re.compile(rf"(?<!\d){re.escape(normalized_num)}(?!\d)")
    matches = list(pattern.finditer(corpus))
    # Word-number aliases for small factual counts already present in Evidence.
    word_map = {
        "10": r"\bten\b",
        "24": r"\btwenty\s+four\b",
        "432": r"\bfour\s*hundred\s*(?:and\s*)?thirty\s*two\b",
    }
    word_pat = word_map.get(normalized_num)
    if word_pat:
        matches.extend(re.finditer(word_pat, corpus))
    return matches


def _evidence_supports_quantified_outcome(
    corpus: str,
    number_token: str,
    category_tags: frozenset[str],
) -> bool:
    """Require number + related outcome cues in a non-negated local window."""
    # Specific domain tags (fundraising/productivity/hours/money) are stronger
    # than generic percent/change alone when present on the claim.
    specific = category_tags.intersection(
        {"fundraising", "productivity", "hours", "money"}
    )
    required_groups = specific if specific else category_tags
    if not required_groups:
        return False

    for match in _number_occurrences(corpus, number_token):
        if _window_is_negated(corpus, match.start(), match.end()):
            continue
        window = corpus[
            max(0, match.start() - _OUTCOME_WINDOW) : min(
                len(corpus), match.end() + _OUTCOME_WINDOW
            )
        ]
        if all(
            _OUTCOME_CATEGORY_CUES[tag].search(window)
            for tag in required_groups
            if tag in _OUTCOME_CATEGORY_CUES
        ):
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
    wording_n = _normalize(wording)
    support = build_evidence_support_corpus(cited_evidence)
    errors: list[dict[str, Any]] = []
    seen_rules: set[str] = set()

    # Actor-attribution overreach is unconditional: no cited Evidence and no
    # human_approval value can license sole/exclusive/unaided-authorship
    # wording, so this check runs regardless of Evidence support.
    for rule_id, pattern in _ACTOR_ATTRIBUTION_OVERREACH_RULES:
        if rule_id in seen_rules:
            continue
        match = pattern.search(wording_n)
        if not match:
            continue
        seen_rules.add(rule_id)
        errors.append(
            _error(
                ERROR_CODE,
                claim_id=claim_id,
                category=ACTOR_ATTRIBUTION_CATEGORY,
                rule_id=rule_id,
                matched_text=match.group(0).strip(),
                detail=(
                    "claim wording asserts unsupported sole/exclusive/unaided "
                    f"authorship {match.group(0).strip()!r}; human_approval "
                    "cannot establish sole intellectual authorship, exclusive "
                    "implementation, absence of AI assistance, or absence of "
                    "collaborators (ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1)"
                ),
            )
        )

    for rule_id, category, claim_pat, evidence_pat in _BOUNDARY_RULES:
        if rule_id in seen_rules:
            continue
        claim_match = claim_pat.search(wording_n)
        if not claim_match:
            continue
        if _has_positive_pattern_support(support, evidence_pat):
            continue
        seen_rules.add(rule_id)
        errors.append(
            _error(
                ERROR_CODE,
                claim_id=claim_id,
                category=category,
                rule_id=rule_id,
                matched_text=claim_match.group(0).strip(),
                detail=(
                    f"claim wording introduces unsupported semantic upgrade "
                    f"{claim_match.group(0).strip()!r}; cited Evidence does not "
                    f"positively support this {category} claim"
                ),
            )
        )

    for outcome_id, outcome_pat, base_tags in _QUANTIFIED_OUTCOME_PATTERNS:
        for match in outcome_pat.finditer(wording_n):
            number_token = _extract_claim_number(match)
            if not number_token:
                continue
            tags = frozenset(set(base_tags) | set(_infer_extra_tags_from_span(match.group(0))))
            if _evidence_supports_quantified_outcome(support, number_token, tags):
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
                        f"({match.group(0).strip()!r}) that is not positively "
                        "supported by cited Evidence in a matching outcome context"
                    ),
                )
            )

    return errors
