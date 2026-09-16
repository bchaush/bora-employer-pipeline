"""RELATED_EXPERIENCE_DURATION_UNKNOWN_V1 -- bounded, deterministic
recognition of employer-stated "N year(s) of RELATED experience"
zero-based maximum/band requirements, so the ordinary capability matcher's
empty-capability fallback does not fabricate a NONE for them.

Root cause this module exists to fix: the real, live Pathward, N.A.
Partner Quality Specialist I posting states
"Typically requires less than one year of related experience." On
untouched canonical this requirement names no technology, no capability
pattern, and no structured domain, so `requirement_match.py`'s
empty-capability fallback returns NONE -- a fabricated disproof, since no
comparison against candidate duration or candidate relatedness was ever
actually performed.

"Related experience" is deliberately NOT treated as a synonym for generic
"work experience" (owned by `experience_range.py`) and is NOT forced into
`domain_qualified_duration.py`'s domain-qualified grammar when the
employer's own text does not name a domain. "Related" carries a real,
employer-stated role-relative qualifier -- it is not semantically empty
like "work" -- but this module does not attempt to resolve what Pathward
means by "related" beyond that qualifier appearing verbatim in the
requirement text; it never infers, fabricates, or structurally derives a
domain from the word "related" itself.

V1 is deliberately narrow and conservative, per the locked routing
contract (PATHWARD_RELATED_EXPERIENCE_MAXIMUM_V1):

A requirement is routed here ONLY when ALL of the following hold:

  1. no technology is named on the requirement;
  2. the existing capability matcher recognizes nothing for this
     requirement (``inferred_capabilities`` is empty);
  3. structured ``domain`` is null/blank;
  4. the requirement's own ``text`` is an exact match for one of this
     module's narrowly enumerated "related experience" maximum/band
     grammars -- not merely a substring containing "related" or
     "experience" somewhere;
  5. the matched grammar itself establishes a zero-based maximum/band
     (lower_bound == 0), never a positive minimum -- a requirement
     phrased as a positive-minimum "related experience" condition (e.g.
     "3+ years of related experience") is out of scope for V1 and is not
     recognized here.

Any one of these failing means the requirement stays with the existing,
unmodified capability matcher (or, for the domain-qualified case, with
`domain_qualified_duration.py`, unchanged, when the employer's text does
name a domain).

V1 recognizes:
  - "less than"/"fewer than" one year of related experience (optionally
    prefixed with "Typically requires"), with an EXCLUSIVE upper bound;
  - "up to" one year of related experience, with an INCLUSIVE upper
    bound;
  - a bare "0-1"/"0–1" years of related experience numeric band, with an
    INCLUSIVE upper bound.

Word-number support is bounded to "one" (and the bare digit "1"), per the
locked contract -- broadening beyond what is evidenced in the real corpus
is explicitly out of scope for this milestone. An inverted or non-zero-
based numeric range (e.g. "1-2 years of related experience") is not a
band this module may silently reinterpret -- refusing to recognize it
(returning None, leaving it with the unmodified capability matcher) is
the truth-preserving choice, mirroring `experience_range.py`'s and
`domain_qualified_duration.py`'s identical precedent.

V1 ALWAYS returns UNKNOWN for a recognized related-experience duration
requirement -- never NONE (no fabricated disproof), never
SUPPORTED/PARTIAL/STRONG (no fabricated positive match). No canonical
candidate years-of-experience figure exists anywhere in this repository,
and this module does not compute one; separately, this module does not
resolve, disprove, or establish role-relative "relatedness" either. Both
open questions are stated explicitly in the returned explanation.

This module does not compute a candidate's years of experience, does not
approve or reference any Claim/Evidence, does not add a related-experience
capability mapping, and does not modify requirement_match.py,
experience_range.py, domain_qualified_duration.py, job_decision.py, or
requirement_source_role.py.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

# Fully string-anchored (^...$) patterns only -- a requirement whose text is
# not an exact match for one of these is never routed here, regardless of
# whether it happens to contain the words "related"/"experience" somewhere.
_ONE = r"(?:1|one)"

_LESS_THAN = re.compile(
    rf"^\s*(?:typically\s+requires\s+)?less\s+than\s+{_ONE}\s*years?\s+of\s+related\s+experience\.?\s*$",
    re.IGNORECASE,
)
_FEWER_THAN = re.compile(
    rf"^\s*(?:typically\s+requires\s+)?fewer\s+than\s+{_ONE}\s*years?\s+of\s+related\s+experience\.?\s*$",
    re.IGNORECASE,
)
_UP_TO = re.compile(
    rf"^\s*up\s+to\s+{_ONE}\s*years?\s+of\s+related\s+experience\.?\s*$",
    re.IGNORECASE,
)
_ZERO_TO_ONE_RANGE = re.compile(
    r"^\s*(\d+)\s*[-–]\s*(\d+)\s*years?\s+of\s+related\s+experience\.?\s*$",
    re.IGNORECASE,
)


def parse_related_experience_duration(text: str) -> dict[str, Any] | None:
    """Parse a "related experience" maximum/band phrase.

    Returns an internal-only structure ``{lower_bound, upper_bound,
    upper_bound_inclusive, range_type, grammar}`` when the text is an
    exact match for one of V1's narrowly supported, zero-based
    maximum/band shapes, or ``None`` otherwise. ``None`` means "not a
    recognized related-experience duration shape" -- callers must never
    guess bounds for unrecognized text.
    """
    if not isinstance(text, str):
        return None
    candidate = text.strip()

    if _LESS_THAN.match(candidate):
        return {
            "lower_bound": 0,
            "upper_bound": 1,
            "upper_bound_inclusive": False,
            "range_type": "MAXIMUM",
            "grammar": "LESS_THAN_ONE_YEAR",
        }

    if _FEWER_THAN.match(candidate):
        return {
            "lower_bound": 0,
            "upper_bound": 1,
            "upper_bound_inclusive": False,
            "range_type": "MAXIMUM",
            "grammar": "FEWER_THAN_ONE_YEAR",
        }

    if _UP_TO.match(candidate):
        return {
            "lower_bound": 0,
            "upper_bound": 1,
            "upper_bound_inclusive": True,
            "range_type": "MAXIMUM",
            "grammar": "UP_TO_ONE_YEAR",
        }

    match = _ZERO_TO_ONE_RANGE.match(candidate)
    if match:
        lower, upper = int(match.group(1)), int(match.group(2))
        # V1 recognizes only a zero-based band (the locked contract's
        # routing invariant 5: the grammar must establish a zero-based
        # maximum/band, never a positive minimum). A non-zero-based or
        # inverted range is not a shape this module may silently
        # reinterpret -- refusing to recognize it (returning None) is the
        # truth-preserving choice, mirroring experience_range.py's and
        # domain_qualified_duration.py's identical precedent.
        if lower != 0 or upper < lower:
            return None
        return {
            "lower_bound": lower,
            "upper_bound": upper,
            "upper_bound_inclusive": True,
            "range_type": "RANGE",
            "grammar": "ZERO_TO_ONE_RANGE",
        }

    return None


def is_related_experience_duration_requirement(
    requirement: Mapping[str, Any],
    *,
    inferred_capabilities: frozenset[str],
) -> bool:
    """True only when a Requirement is safely, narrowly identifiable as an
    employer-stated, zero-based "related experience" maximum/band
    condition that the existing capability matcher's empty-capability
    fallback must NOT evaluate as an ordinary NONE/positive comparison.

    Requires ALL of:
      1. no technology is named on the requirement;
      2. ``inferred_capabilities`` is empty -- this alone already keeps
         every already-recognized capability, and every named-platform
         NONE_TRAPS case, entirely with the unmodified capability
         matcher;
      3. structured ``domain`` is null/blank -- when the employer's text
         does name a domain, that specialization belongs with
         `domain_qualified_duration.py`, unchanged, not here;
      4. the requirement's own ``text`` is an exact match for one of this
         module's narrowly enumerated, zero-based "related experience"
         maximum/band phrasings.

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
    if parse_related_experience_duration(text if isinstance(text, str) else "") is None:
        return False
    return True


def evaluate_related_experience_duration_requirement(
    *,
    job_id: str,
    requirement: Mapping[str, Any],
    match_index: int,
) -> dict[str, Any]:
    """Produce one evidence_match-shaped record for a related-experience
    duration Requirement, honestly reflecting that neither the candidate's
    duration nor role-relative relatedness was actually established or
    disproven.

    Always returns result=UNKNOWN in V1: parsing identifies the semantic
    class correctly, but no canonical candidate years-of-experience figure
    exists anywhere in this repository, and this evaluator does not
    resolve, disprove, or establish what "related" means beyond the
    employer's own role-relative qualifier appearing verbatim in the
    requirement text. Callers must only invoke this for a requirement that
    ``is_related_experience_duration_requirement`` has already confirmed.
    """
    req_id = str(requirement.get("requirement_id"))
    match_id = f"MATCH_{job_id}_{req_id}_{match_index:02d}"
    req_text = str(requirement.get("text") or "")
    parsed = parse_related_experience_duration(req_text)
    parse_detail = (
        f"parsed={parsed}"
        if parsed is not None
        else "UNPARSED_RELATED_EXPERIENCE_DURATION_VARIANT (routed but not recognized -- should not occur)"
    )
    return {
        "match_id": match_id,
        "job_id": job_id,
        "requirement_id": req_id,
        "result": "UNKNOWN",
        "evidence_ids": [],
        "claim_ids": [],
        "explanation": (
            f"raw={req_text!r}; recognized as a zero-based related-experience "
            f"duration condition ({parse_detail}); candidate work-experience "
            "duration is not currently a canonical, computed fact in this "
            "repository, and role-relative relatedness was not established or "
            "disproven for this requirement (RELATED_EXPERIENCE_DURATION_"
            "UNKNOWN_V1); no positive or negative comparison was performed."
        ),
        "transfer_note": None,
        # PATHWARD_RELATED_EXPERIENCE_MAXIMUM_V1: additive Match-truth
        # provenance (see src/qualification_gate.py).
        "evaluation_path": "RELATED_EXPERIENCE_DURATION_EVALUATOR",
    }
