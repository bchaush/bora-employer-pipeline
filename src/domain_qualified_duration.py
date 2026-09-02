"""DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1 -- bounded, deterministic
recognition of "N years of experience in <domain>" requirements whose
domain concept has no capability pattern at all, so the ordinary matcher's
empty-capability fallback would otherwise fabricate a hard-blocking NONE.

Root cause this module exists to fix: a requirement like "Three (3) years
of experience in system analysis, including enterprise application design,
configuration / development, implementation, and support." (real MBTA
fixtures, CASE_D_MBTA_DIRECT_APPLICATION_ANALYST/
CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST) is domain-qualified, so
experience_range.py's own generic evaluator correctly and deliberately
excludes it (that module's condition 3: no structured `domain` value may be
present, precisely to keep named-platform/domain-specific years
requirements -- SAP, Salesforce, Workday -- owned by the capability
matcher's `_NONE_TRAPS` mechanism, which produces a genuinely disproven
NONE from a real evidence comparison). But `infer_requirement_capabilities()`
recognizes no pattern at all for "system analysis" as a domain concept, so
`req_caps` is empty, and `requirement_match.match_requirement()`'s
empty-capability fallback returns NONE -- a fabricated disproof, since no
domain comparison and no duration comparison were ever actually performed.
This module gives that requirement class its own narrow, deterministic
evaluator, invoked instead of (never merged into) the capability matcher,
so it can honestly report UNKNOWN instead of a fabricated NONE -- the exact
same principle EXPERIENCE_RANGE_SEMANTICS_V1 already established for
domain-*free* duration requirements, applied here to the domain-qualified
case that module explicitly, deliberately left unaddressed.

V1 is deliberately narrow and conservative, per the locked routing
contract (CURRENT_MILESTONE.md, DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1):

A requirement is routed here ONLY when ALL four conditions hold:

  1. structured `domain` is a non-empty string;
  2. structured `technology` is empty (a named technology belongs with the
     capability matcher, exactly like experience_range.py's own rule);
  3. `infer_requirement_capabilities()` (imported, never modified) returns
     EMPTY for this requirement -- this alone already keeps every existing
     named-platform `_NONE_TRAPS` case (SAP FI/CO, Salesforce
     administration, Workday, ServiceNow, Google Cloud, production ML) and
     every already-recognized capability (UAT, requirements elicitation,
     process mapping, etc.) entirely with the ordinary, unmodified
     matcher -- those all have non-empty `req_caps` by construction, so
     this module can never intercept them, and their correctly-disproven
     NONE (or correctly-established positive match) is never weakened;
  4. the requirement's own `text` is an exact structural match for one of
     this module's narrowly enumerated "N years of experience in <domain
     phrase>" grammars -- not merely a substring containing "years" or
     "experience" somewhere, and not the bare presence of a populated
     `domain` field alone.

V1 recognizes ONLY a minimum-bound "N years of experience in <domain>"
family (word-plus-parenthetical-digit, e.g. "Three (3) years...", and bare
digit, e.g. "5 years..." or "5+ years..."), the exact shapes evidenced in
the real fixture corpus. It does NOT recognize a range or maximum-bound
domain-qualified grammar (not evidenced) and does NOT accept "with" in
place of "in" (not evidenced in the real corpus; broadening beyond what is
evidenced is explicitly out of scope for this milestone).

V1 ALWAYS returns UNKNOWN for a recognized domain-qualified duration
requirement -- never NONE (no fabricated disproof of the domain
capability), never SUPPORTED/PARTIAL/STRONG (no fabricated positive
domain match, and no canonical candidate duration figure exists anywhere
in this repository to compare against in the first place). This mirrors
experience_range.py's own honest-UNKNOWN precedent exactly. UNKNOWN here
means "the system has not established whether the candidate satisfies
this domain-qualified duration requirement" -- it does NOT mean "the
candidate lacks the domain capability."

This module does not compute a candidate's years of experience, does not
approve or reference any Claim, does not add a system-analysis (or any
other) capability mapping, and does not modify requirement_match.py,
experience_range.py, job_decision.py, requirement_source_role.py,
requirement_normalize.py, or application_gate.py.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

# Fully string-anchored (^...$) patterns only -- a requirement whose text is
# not an exact match for one of these is never routed here, regardless of
# whether it happens to contain the words "years"/"experience" somewhere,
# and regardless of whether `domain` is populated.
_WORD_TO_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
_WORD_NUM_ALTERNATION = "|".join(_WORD_TO_NUM)

# "Three (3) years of experience in system analysis, including..." -- the
# exact shape used by both real MBTA fixtures.
_WORD_PAREN_DIGIT_MINIMUM = re.compile(
    rf"^\s*(?:{_WORD_NUM_ALTERNATION})\s*\(\s*(\d+)\s*\)\s*years?\s+of\s+experience\s+"
    r"in\s+.+$",
    re.IGNORECASE,
)
# "5 years of experience in financial services" / "5+ years of experience
# in business analysis" -- bare-digit minimum, no parenthetical.
_DIGIT_MINIMUM = re.compile(
    r"^\s*(\d+)\+?\s*years?\s+of\s+experience\s+in\s+.+$",
    re.IGNORECASE,
)


def parse_domain_qualified_duration(text: str) -> dict[str, Any] | None:
    """Parse a "N years of experience in <domain>" phrase.

    Returns an internal-only structure ``{lower_bound, grammar}`` when the
    text is an exact match for one of V1's narrowly supported shapes, or
    ``None`` otherwise. ``None`` means "not a recognized domain-qualified
    duration shape" -- callers must never guess a bound for unrecognized
    text.
    """
    if not isinstance(text, str):
        return None
    candidate = text.strip()

    match = _WORD_PAREN_DIGIT_MINIMUM.match(candidate)
    if match:
        return {"lower_bound": int(match.group(1)), "grammar": "WORD_PAREN_DIGIT_MINIMUM"}

    match = _DIGIT_MINIMUM.match(candidate)
    if match:
        return {"lower_bound": int(match.group(1)), "grammar": "DIGIT_MINIMUM"}

    return None


def is_domain_qualified_duration_requirement(
    requirement: Mapping[str, Any],
    *,
    inferred_capabilities: frozenset[str],
) -> bool:
    """True only when a Requirement is safely, narrowly identifiable as a
    domain-qualified numeric experience-duration condition that the
    existing capability matcher's empty-capability fallback must NOT
    evaluate as an ordinary NONE/positive comparison.

    Requires ALL of:
      1. a non-empty structured ``domain`` value is present;
      2. no technology is named on the requirement (a named tool/platform
         belongs with the capability matcher, not this evaluator);
      3. ``inferred_capabilities`` is empty -- this alone already keeps
         every named-platform NONE_TRAPS case and every already-recognized
         capability (UAT, requirements elicitation, process mapping, etc.)
         entirely with the unmodified capability matcher;
      4. the requirement's own ``text`` is an exact match for one of this
         module's narrowly enumerated "N years of experience in <domain>"
         phrasings.

    Any one of these failing means the requirement stays with the
    existing, unmodified capability matcher (and, before that, with
    experience_range.py's own generic-range check, which this function's
    caller always runs first).
    """
    domain = requirement.get("domain")
    if not isinstance(domain, str) or not domain.strip():
        return False
    technology = requirement.get("technology")
    if isinstance(technology, list) and technology:
        return False
    if inferred_capabilities:
        return False
    text = requirement.get("text")
    if parse_domain_qualified_duration(text if isinstance(text, str) else "") is None:
        return False
    return True


def evaluate_domain_qualified_duration_requirement(
    *,
    job_id: str,
    requirement: Mapping[str, Any],
    match_index: int,
) -> dict[str, Any]:
    """Produce one evidence_match-shaped record for a domain-qualified
    experience-duration Requirement, honestly reflecting that neither the
    domain capability nor the candidate's duration was actually compared.

    Always returns result=UNKNOWN in V1: parsing identifies the semantic
    class correctly, but no capability pattern exists for the named
    domain (that is precisely why req_caps was empty and this evaluator
    was reached), and no code in this repository computes a canonical
    years-of-experience figure from Experience/Evidence dates. Callers
    must only invoke this for a requirement that
    ``is_domain_qualified_duration_requirement`` has already confirmed.
    """
    req_id = str(requirement.get("requirement_id"))
    match_id = f"MATCH_{job_id}_{req_id}_{match_index:02d}"
    req_text = str(requirement.get("text") or "")
    domain = requirement.get("domain")
    parsed = parse_domain_qualified_duration(req_text)
    parse_detail = (
        f"parsed={parsed}"
        if parsed is not None
        else "UNPARSED_DOMAIN_QUALIFIED_DURATION_VARIANT (routed but not recognized -- should not occur)"
    )
    return {
        "match_id": match_id,
        "job_id": job_id,
        "requirement_id": req_id,
        "result": "UNKNOWN",
        "evidence_ids": [],
        "claim_ids": [],
        "explanation": (
            f"raw={req_text!r}; recognized as a domain-qualified "
            f"experience-duration condition (domain={domain!r}, {parse_detail}); "
            "no capability pattern currently represents this domain, so no "
            "domain comparison was performed; candidate work-experience "
            "duration is not currently a canonical, computed fact in this "
            "repository; neither domain support nor duration was established "
            "or disproven for this requirement (DOMAIN_QUALIFIED_EXPERIENCE_"
            "DURATION_UNKNOWN_V1)."
        ),
        "transfer_note": None,
        # ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1: additive
        # Match-truth provenance (see src/qualification_gate.py).
        "evaluation_path": "DOMAIN_QUALIFIED_DURATION_EVALUATOR",
    }
