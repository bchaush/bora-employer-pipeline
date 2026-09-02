"""EXPERIENCE_RANGE_SEMANTICS_V1 -- bounded, deterministic recognition of
GENERIC numeric experience-range/band requirements.

A requirement like "0-2 years of work experience" is not a missing candidate
*capability* -- it names no skill, tool, or domain -- so the generic
capability matcher (requirement_match.py) correctly infers zero capability
tags for it, and its empty-capability fallback then reports NONE for any
MANDATORY+HIGH requirement. That NONE becomes a hard blocker even though the
requirement's lower bound (0) is trivially satisfied by any candidate. This
module gives that requirement class its own narrow, deterministic evaluator,
invoked instead of (never merged into) the capability matcher, so it can
honestly report UNKNOWN instead of a fabricated NONE.

V1 is deliberately narrow and conservative:

- It recognizes ONLY the "<number(s)> years of work experience" family
  (plain minimum, "+" minimum, "at least" minimum, range, "up to" maximum,
  "no more than" maximum) -- a small, explicitly enumerated, fully
  string-anchored pattern set, not a general natural-language parser.
- It NEVER computes or assumes a candidate's actual years of experience.
  No code in this repository currently derives a canonical years-of-
  experience figure from Experience/Evidence records (see the
  EXPERIENCE_RANGE_SEMANTICS_V1 audit: whether Bulmarma/Winter Walk time
  should count toward such a total is itself an open, unresolved
  classification question). Because no canonical candidate fact exists,
  V1's evaluator always returns UNKNOWN for a recognized generic range --
  never NONE (no fabricated rejection), never SUPPORTED/PARTIAL/STRONG (no
  fabricated pass). This preserves the same NONE != FALSE / missing-
  evidence != contradicted-fact principle already established for
  Application Gate.
- It NEVER routes domain/platform/function-specific years requirements
  (e.g. "5+ years SAP FI/CO experience", "3 years Salesforce
  administration", "2+ years customer-facing implementation experience",
  "3 years UAT experience", or plain-worded text that nonetheless carries
  structured specialization in its ``domain`` field, e.g. "3+ years of
  work experience" with ``domain="Financial Services"``) -- those remain
  entirely owned by the existing capability matcher (including the closed
  named-platform NONE_TRAPS mechanism for SAP/Salesforce/Workday/etc.),
  unchanged. Routing requires the requirement to have (a) no named
  technology, (b) zero capability tags already recognized by the existing
  capability matcher, (c) no structured ``domain`` value (a repository-wide
  fixture survey confirms this field is consistently used for genuine
  specialization -- "CRM", "Finance Systems", "Private Markets", "U.S.
  Regulatory Reporting" -- never generic filler), and (d) text that is an
  exact match for one of this module's narrowly enumerated "years of work
  experience" phrasings -- not merely a substring containing the word
  "years". Any one of these conditions failing keeps the requirement with
  the existing, unmodified capability matcher.
- It NEVER recognizes an inverted range ("3-1 years", "5-0 years") as
  valid. A range is parsed only when lower_bound <= upper_bound; an
  inverted range is malformed text, not a range whose bounds this module
  may silently swap or "correct" -- refusing to recognize it (returning
  None, leaving it with the existing capability matcher) is the truth-
  preserving choice.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

# Fully string-anchored (^...$) patterns only -- a requirement whose text is
# not an exact match for one of these is never routed here, regardless of
# whether it happens to contain the word "years" or "experience" somewhere.
_RANGE = re.compile(
    r"^\s*(\d+)\s*[-–]\s*(\d+)\s*years?\s+of\s+work\s+experience\.?\s*$",
    re.IGNORECASE,
)
_MINIMUM_PLUS = re.compile(
    r"^\s*(\d+)\s*\+\s*years?\s+of\s+work\s+experience\.?\s*$",
    re.IGNORECASE,
)
_AT_LEAST = re.compile(
    r"^\s*at\s+least\s+(\d+)\s*years?\s+of\s+work\s+experience\.?\s*$",
    re.IGNORECASE,
)
_UP_TO = re.compile(
    r"^\s*up\s+to\s+(\d+)\s*years?\s+of\s+work\s+experience\.?\s*$",
    re.IGNORECASE,
)
_NO_MORE_THAN = re.compile(
    r"^\s*no\s+more\s+than\s+(\d+)\s*years?\s+of\s+work\s+experience\.?\s*$",
    re.IGNORECASE,
)


def parse_generic_experience_range(text: str) -> dict[str, Any] | None:
    """Parse a GENERIC "years of work experience" phrase.

    Returns an internal-only structure
    ``{lower_bound, upper_bound, range_type, upper_bound_strength}`` when
    the text is an exact match for one of V1's narrowly supported shapes,
    or ``None`` otherwise. ``None`` means "not a recognized generic range
    shape" -- callers must never guess bounds for unrecognized text.

    ``range_type`` is one of ``RANGE`` / ``MINIMUM`` / ``MAXIMUM``.
    ``upper_bound_strength`` is ``SOFT`` (plain range or "up to" wording,
    no exclusionary language) or ``HARD`` (explicit "no more than" /
    exclusionary wording), and is ``None`` when there is no upper bound at
    all (a bare minimum).
    """
    if not isinstance(text, str):
        return None
    candidate = text.strip()

    match = _RANGE.match(candidate)
    if match:
        lower, upper = int(match.group(1)), int(match.group(2))
        # An inverted range ("3-1 years", "5-0 years") is not a valid range
        # at all -- it is malformed/unparseable text, not a range whose
        # bounds this module may silently swap or "correct". Refusing to
        # recognize it (returning None) is the truth-preserving choice;
        # guessing which bound the author meant would be fabrication.
        if lower > upper:
            return None
        return {
            "lower_bound": lower,
            "upper_bound": upper,
            "range_type": "RANGE",
            "upper_bound_strength": "SOFT",
        }

    match = _MINIMUM_PLUS.match(candidate)
    if match:
        return {
            "lower_bound": int(match.group(1)),
            "upper_bound": None,
            "range_type": "MINIMUM",
            "upper_bound_strength": None,
        }

    match = _AT_LEAST.match(candidate)
    if match:
        return {
            "lower_bound": int(match.group(1)),
            "upper_bound": None,
            "range_type": "MINIMUM",
            "upper_bound_strength": None,
        }

    match = _UP_TO.match(candidate)
    if match:
        return {
            "lower_bound": 0,
            "upper_bound": int(match.group(1)),
            "range_type": "MAXIMUM",
            "upper_bound_strength": "SOFT",
        }

    match = _NO_MORE_THAN.match(candidate)
    if match:
        return {
            "lower_bound": 0,
            "upper_bound": int(match.group(1)),
            "range_type": "MAXIMUM",
            "upper_bound_strength": "HARD",
        }

    return None


def is_generic_experience_range_requirement(
    requirement: Mapping[str, Any],
    *,
    inferred_capabilities: frozenset[str],
) -> bool:
    """True only when a Requirement is safely, narrowly identifiable as a
    GENERIC (context-free) numeric experience-range/band condition that the
    existing capability matcher must NOT evaluate.

    Requires ALL of:
      1. no technology named on the requirement (a named tool/platform
         belongs with the capability matcher, not this evaluator);
      2. the existing capability matcher recognizes nothing for this
         requirement (``inferred_capabilities`` is empty) -- this alone
         already keeps UAT/process-mapping/named-platform requirements,
         which DO have recognized capability tags, out of this routing;
      3. no structured ``domain`` value is present on the requirement --
         ``domain`` is ``requirement.schema.json``'s own dedicated
         "business or technical domain explicitly connected to the
         requirement" field, and a repository-wide survey of every real
         and Golden fixture confirms it is consistently populated with
         genuine specialization values ("CRM", "Finance Systems", "Private
         Markets", "U.S. Regulatory Reporting", "Implementation", etc.),
         never generic filler. A requirement whose raw ``text`` reads as
         plain "N years of work experience" but whose structured ``domain``
         names a specialization (e.g. "Financial Services") is NOT
         context-free -- the specialization lives in metadata the raw text
         alone does not carry, and this evaluator must not ignore it. Other
         optional Requirement fields (``category``, ``experience_level``,
         ``seniority_implication``) were inspected and are NOT guarded
         here: ``category`` is a requirement-type bucket (e.g.
         "EXPERIENCE", "DATA", "TESTING"), not a specialization value, and
         a requirement's own ``category`` being "EXPERIENCE" says nothing
         about what domain the experience is in; ``experience_level``
         mirrors the numeric range itself (the very thing this module
         parses from ``text``), not a separate specialization signal;
         ``seniority_implication`` carries seniority, not domain,
         information and is already handled by the existing, separate
         seniority-detection code in job_decision.py. No blanket
         "all metadata must be null" rule is imposed -- only the one field
         repository semantics actually prove is specialization-bearing;
      4. the requirement's own text is an exact match for one of this
         module's narrowly enumerated "years of work experience"
         phrasings -- this alone already keeps "SAP FI/CO experience",
         "Salesforce administration", "customer-facing implementation
         experience", and "UAT experience" out, since none of them is an
         exact match for the literal phrase "... years of work
         experience".

    Any one of these failing means the requirement stays with the
    existing, unmodified capability matcher.
    """
    technology = requirement.get("technology")
    if isinstance(technology, list) and technology:
        return False
    if inferred_capabilities:
        return False
    domain = requirement.get("domain")
    if isinstance(domain, str) and domain.strip():
        return False
    text = requirement.get("text")
    if parse_generic_experience_range(text if isinstance(text, str) else "") is None:
        return False
    return True


def evaluate_generic_experience_range(
    *,
    job_id: str,
    requirement: Mapping[str, Any],
    match_index: int,
) -> dict[str, Any]:
    """Produce one evidence_match-shaped record for a GENERIC experience-
    range Requirement, honestly reflecting that no canonical candidate
    work-experience-duration fact currently exists in this repository.

    Always returns result=UNKNOWN in V1: parsing identifies the semantic
    class correctly, but does not compare against a candidate number,
    because no code in this repository computes years-of-experience from
    Experience/Evidence dates, and whether Bulmarma/Winter Walk time
    should count toward such a total is an open, unresolved classification
    question this evaluator does not decide (see the
    EXPERIENCE_RANGE_SEMANTICS_V1 audit --
    CANDIDATE_EXPERIENCE_DURATION_NOT_YET_CANONICAL). Manufacturing NONE,
    SUPPORTED, or PARTIAL here would fabricate a comparison that was never
    actually performed. Callers must only invoke this for a requirement
    that ``is_generic_experience_range_requirement`` has already
    confirmed.
    """
    req_id = str(requirement.get("requirement_id"))
    match_id = f"MATCH_{job_id}_{req_id}_{match_index:02d}"
    req_text = str(requirement.get("text") or "")
    parsed = parse_generic_experience_range(req_text)
    parse_detail = (
        f"parsed={parsed}"
        if parsed is not None
        else "UNPARSED_EXPERIENCE_RANGE_VARIANT (routed but not recognized -- should not occur)"
    )
    return {
        "match_id": match_id,
        "job_id": job_id,
        "requirement_id": req_id,
        "result": "UNKNOWN",
        "evidence_ids": [],
        "claim_ids": [],
        "explanation": (
            f"raw={req_text!r}; recognized as a generic numeric experience-range "
            f"condition ({parse_detail}); candidate work-experience duration is "
            "not currently a canonical, computed fact in this repository "
            "(CANDIDATE_EXPERIENCE_DURATION_NOT_YET_CANONICAL); no positive or "
            "negative comparison was performed."
        ),
        "transfer_note": None,
        # ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1: additive
        # Match-truth provenance (see src/qualification_gate.py).
        "evaluation_path": "EXPERIENCE_RANGE_EVALUATOR",
    }
