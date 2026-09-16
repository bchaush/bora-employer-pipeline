"""EDUCATION_FLOOR_SEMANTICS_V1 -- bounded, deterministic recognition of a
plain, standalone, unqualified minimum-education-level requirement (e.g.
"Bachelor's degree required"), so that a higher awarded education level can
honestly satisfy the stated floor without the existing capability matcher's
strict tag-equality logic forcing an exact-credential-only interpretation,
and without ever asserting literal possession of a lower credential the
candidate was never independently shown to hold.

Root cause this module exists to fix: the real, live Mercer Advisors
Portfolio Operations Specialist posting states "High school diploma
required." The candidate's only trusted awarded-education fact is a
Brandeis University M.S. (EDU_BRANDEIS_AWARDED_ATTESTATION_001,
OBSERVED-tier human attestation) -- an education level well above a high
school diploma, but not literally the same credential. Neither the
unmodified capability matcher (no capability pattern recognizes "high
school diploma" at all, so its empty-capability fallback returns a
fabricated NONE) nor any existing evaluator could honestly resolve this.

V1 is deliberately narrow and conservative, per the locked routing
contract (EDUCATION_FLOOR_SEMANTICS_V1):

A requirement is routed here ONLY when ALL of the following hold:

  1. its own ``text`` is an EXACT match (after semantically inert
     case/punctuation/pluralization normalization only) for one of five
     enumerated plain positive minimum-education-level grammars -- never
     a substring/keyword match;
  2. it is not an explicit qualification-gate leaf (``gated=True``) --
     alternative-qualification-branch OR structures keep their existing
     owner (src/qualification_gate.py + the unmodified capability
     matcher), never this evaluator;
  3. any capability tags the existing capability matcher independently
     infers for the same text are a subset of
     {"bachelors_degree_credential"} -- the one capability tag the
     matcher's own bachelor's-degree pattern always produces for the
     BACHELOR grammar. Any additional inferred tag (institutional-quality/
     accreditation qualifier, degree+experience-duration conjunction,
     etc.) means the text carries more than a plain floor condition and
     must stay with the unmodified capability matcher.

Any one of these failing means the requirement stays with the existing,
unmodified capability matcher (or, for a gate leaf, with
src/qualification_gate.py's leaf-adapter policy over that matcher's
result), unchanged.

Ordered floor (this evaluator only): HIGH_SCHOOL < ASSOCIATE < BACHELOR <
MASTER. Trusted Candidate Truth in V1 is a single canonical evidence
record, EDU_BRANDEIS_AWARDED_ATTESTATION_001, which establishes an awarded
Brandeis M.S. -- the highest level in this ordering -- at OBSERVED
human-attestation tier. CLAIM_EDU_UNWE_001 is never read or cited here: it
is human_approval=false and cannot support U.S.-equivalency/credential-
evaluation inference, and this module performs no such inference at all
(the M.S. satisfies the floor by ORDERED LEVEL, never by claiming
equivalency to a foreign credential).

A satisfied floor match cites ONLY EDU_BRANDEIS_AWARDED_ATTESTATION_001 as
evidence_ids, never any claim_ids, and its explanation states that the
minimum education level is supported -- never that a lower credential
(e.g. a literal high school diploma) is possessed. When the canonical
awarded evidence is absent or malformed, this evaluator never fabricates
support: it returns NONE.

This module does not compute field-of-study, institutional-accreditation/
ranking, U.S./foreign-equivalency, document-production, license/
certification, or doctoral/professional-degree semantics -- those remain
entirely owned by the unmodified capability matcher (or unrecognized by
it, unchanged). It does not modify requirement_match.py, qualification_gate.py,
or any Candidate Truth/Claim/Evidence record.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

EDUCATION_LEVEL_ORDER: dict[str, int] = {
    "HIGH_SCHOOL": 0,
    "ASSOCIATE": 1,
    "BACHELOR": 2,
    "MASTER": 3,
}

# Canonical Candidate Truth: the only trusted awarded-education evidence in
# V1, establishing an awarded Brandeis M.S. (MASTER, the highest level in
# this ordering) at OBSERVED human-attestation tier. CLAIM_EDU_UNWE_001 is
# deliberately never referenced anywhere in this module.
_CANONICAL_AWARDED_EVIDENCE_ID = "EDU_BRANDEIS_AWARDED_ATTESTATION_001"
_CANONICAL_EXPERIENCE_ID = "EXP_EDU_BRANDEIS_001"
_CANONICAL_AWARDED_LEVEL = "MASTER"

# V1 is tied to the current canonical record itself, which is exactly
# OBSERVED-tier. No Candidate Truth upgrade to VERIFIED/SUPPORTED has
# occurred for this record, so this evaluator trusts ONLY an evidence_state
# of exactly OBSERVED -- never VERIFIED, SUPPORTED, UNKNOWN, or CONTRADICTED,
# even though VERIFIED/SUPPORTED are otherwise-affirmative states elsewhere
# in the schema. Accepting them here would let a synthetic/future record
# claiming a higher trust tier than the real canonical record currently
# holds silently satisfy this floor.
_REQUIRED_CANONICAL_EVIDENCE_STATE = "OBSERVED"

# Narrow, deterministic recognition of the ONE bounded canonical atomic fact
# this evaluator is permitted to trust. This is intentionally the full,
# exact ``fact`` string of the current canonical record
# (evidence/education/EDU_BRANDEIS_AWARDED_ATTESTATION_001.json), not a
# keyword or sub-phrase pattern -- it recognizes only this single record's
# exact semantic content, tied to _CANONICAL_AWARDED_EVIDENCE_ID and
# _CANONICAL_EXPERIENCE_ID above, and is never applied to any other
# evidence record or degree.
#
# A whole-fact equality check (after only semantically inert
# case/whitespace normalization -- see _normalize_fact below) is used
# instead of a substring/regex.search proof deliberately: a negated or
# denied wrapper around the same approved phrase ("It is false that ...",
# "... -- this statement is not true.") produces a *different* string from
# this exact canonical sentence and therefore can never satisfy equality,
# with no separate negation-detection logic required. This is not a general
# natural-language negation engine -- it is a fixed-string identity check
# against the one canonical record this evaluator is allowed to trust.
_CANONICAL_ATOMIC_FACT = (
    "Bora directly attested, dated 2026-09-03, that his Brandeis University "
    "Master of Science in Business Analytics is officially completed and "
    "awarded, with all academic requirements complete, and that he is "
    "currently waiting only for receipt of the physical diploma."
)


def _normalize_fact(text: str) -> str:
    """Semantically inert normalization only: case-fold and collapse
    whitespace. Never strips, reorders, or otherwise alters words -- in
    particular this can never remove or neutralize a negation/denial word
    or clause, so it cannot cause a negated/denied fact to falsely equal
    the canonical atomic fact.
    """
    return re.sub(r"\s+", " ", text.strip()).casefold()


_CANONICAL_ATOMIC_FACT_NORMALIZED = _normalize_fact(_CANONICAL_ATOMIC_FACT)

# Fully string-anchored (^...$) grammars only -- a requirement whose text is
# not an exact match (after normalization) for one of these is never
# recognized as a plain education-floor condition, regardless of whether it
# happens to contain a degree-level word somewhere.
_LEVEL_GRAMMARS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^high school diplomas? or ged required\.?$", re.IGNORECASE),
        "HIGH_SCHOOL",
    ),
    (
        re.compile(r"^high school diplomas? required\.?$", re.IGNORECASE),
        "HIGH_SCHOOL",
    ),
    (
        re.compile(r"^associate'?s? degrees? required\.?$", re.IGNORECASE),
        "ASSOCIATE",
    ),
    (
        re.compile(r"^bachelor'?s? degrees? required\.?$", re.IGNORECASE),
        "BACHELOR",
    ),
    (
        re.compile(r"^master'?s? degrees? required\.?$", re.IGNORECASE),
        "MASTER",
    ),
)

# Defense-in-depth: any capability tag inferred for the requirement's text
# beyond this set means the text carries more than a plain floor condition
# (institutional-quality/accreditation qualifier, degree+experience-duration
# conjunction, etc.) and must stay with the unmodified capability matcher.
_ALLOWED_INFERRED_CAPABILITIES: frozenset[str] = frozenset({"bachelors_degree_credential"})


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def parse_education_floor(text: str) -> dict[str, Any] | None:
    """Parse a plain, standalone minimum-education-level grammar.

    Returns ``{"required_level": <HIGH_SCHOOL|ASSOCIATE|BACHELOR|MASTER>}``
    when ``text`` is an exact match (after semantically inert whitespace
    normalization; matching is otherwise case/punctuation/pluralization
    tolerant only through the fixed grammars above) for one of V1's five
    enumerated grammars, or ``None`` otherwise. ``None`` means "not a
    recognized plain education-floor condition" -- callers must never
    guess a level for unrecognized text, and this function never matches
    field-of-study, institutional-quality/accreditation, equivalency,
    document-production, license/certification, doctoral/professional, or
    compound degree+experience phrasing.
    """
    if not isinstance(text, str):
        return None
    candidate = _normalize(text)
    for pattern, level in _LEVEL_GRAMMARS:
        if pattern.match(candidate):
            return {"required_level": level}
    return None


def is_education_floor_requirement(
    requirement: Mapping[str, Any],
    *,
    inferred_capabilities: frozenset[str],
    gated: bool,
) -> bool:
    """True only when a Requirement is safely, narrowly identifiable as a
    plain, standalone, unqualified minimum-education-level condition that
    EDUCATION_FLOOR_EVALUATOR (not the unmodified capability matcher, and
    not an alternative-qualification gate leaf) must own.

    Requires ALL of:
      1. the requirement's own ``text`` is an exact match for one of the
         five enumerated plain education-floor grammars;
      2. ``gated`` is False -- an explicit employer-authored
         alternative-qualification-branch (qualification_gate) leaf always
         keeps its existing owner, never this evaluator;
      3. ``inferred_capabilities`` (as independently computed by the
         existing capability matcher for this same requirement) is a
         subset of {"bachelors_degree_credential"} -- any other inferred
         tag means the text carries more than a plain floor condition;
      4. the requirement's own ``domain`` and ``technology`` metadata are
         both empty -- any non-empty domain or technology specialization
         metadata means the requirement is not a plain, standalone floor
         condition, regardless of what its ``text`` or independently
         inferred capabilities look like, and must stay with the unmodified
         capability matcher.

    Any one of these failing means the requirement stays with the
    existing, unmodified capability matcher.
    """
    if gated:
        return False
    text = requirement.get("text")
    if parse_education_floor(text if isinstance(text, str) else "") is None:
        return False
    if not inferred_capabilities.issubset(_ALLOWED_INFERRED_CAPABILITIES):
        return False
    domain = requirement.get("domain")
    if isinstance(domain, str) and domain.strip():
        return False
    technology = requirement.get("technology")
    if isinstance(technology, list) and len(technology) > 0:
        return False
    return True


def _is_valid_canonical_award_evidence(evidence: Any) -> bool:
    """True only when ``evidence`` is the bounded canonical awarded-education
    record and its own trusted fields deterministically prove the single
    permitted atomic fact -- never on evidence_id presence alone.

    Requires ALL of:
      - ``evidence`` is a Mapping;
      - its own ``evidence_id`` field is exactly
        _CANONICAL_AWARDED_EVIDENCE_ID;
      - its own ``experience_id`` field is exactly
        _CANONICAL_EXPERIENCE_ID;
      - its ``evidence_state`` is exactly _REQUIRED_CANONICAL_EVIDENCE_STATE
        ("OBSERVED"), matching the current canonical record's own tier --
        never silently upgraded/widened to VERIFIED or SUPPORTED, which the
        real canonical record does not currently hold;
      - ``safe_for_external_use`` is True;
      - its own ``fact`` text is, after only semantically inert
        case/whitespace normalization, EXACTLY EQUAL to the current
        canonical record's exact atomic fact sentence (see
        _CANONICAL_ATOMIC_FACT / _normalize_fact) -- a whole-fact identity
        check, never a substring/keyword search. A negated, denied,
        truncated, paraphrased, or otherwise altered fact is a different
        string and therefore never supports, regardless of the record's ID
        or of whether it merely contains the approved phrase.
    """
    if not isinstance(evidence, Mapping):
        return False
    if evidence.get("evidence_id") != _CANONICAL_AWARDED_EVIDENCE_ID:
        return False
    if evidence.get("experience_id") != _CANONICAL_EXPERIENCE_ID:
        return False
    if evidence.get("evidence_state") != _REQUIRED_CANONICAL_EVIDENCE_STATE:
        return False
    if evidence.get("safe_for_external_use") is not True:
        return False
    fact = evidence.get("fact")
    if not isinstance(fact, str):
        return False
    return _normalize_fact(fact) == _CANONICAL_ATOMIC_FACT_NORMALIZED


def evaluate_education_floor_requirement(
    *,
    job_id: str,
    requirement: Mapping[str, Any],
    match_index: int,
    evidence_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Produce one evidence_match-shaped record for a plain education-floor
    Requirement.

    SUPPORTED only when the canonical awarded evidence
    (EDU_BRANDEIS_AWARDED_ATTESTATION_001) is present and valid in
    ``evidence_index`` and its established level (MASTER) meets or exceeds
    the requirement's parsed ``required_level`` under the ordered floor
    HIGH_SCHOOL < ASSOCIATE < BACHELOR < MASTER -- citing ONLY that
    evidence_id, never any claim_id, and never asserting literal
    possession of a lower credential. Otherwise NONE -- this evaluator
    never fabricates support when trusted awarded evidence is
    absent/invalid. Callers must only invoke this for a requirement that
    ``is_education_floor_requirement`` has already confirmed.
    """
    req_id = str(requirement.get("requirement_id"))
    match_id = f"MATCH_{job_id}_{req_id}_{match_index:02d}"
    req_text = str(requirement.get("text") or "")
    parsed = parse_education_floor(req_text)
    required_level = parsed["required_level"] if parsed else None

    evidence = evidence_index.get(_CANONICAL_AWARDED_EVIDENCE_ID)
    evidence_valid = _is_valid_canonical_award_evidence(evidence)

    if (
        evidence_valid
        and required_level is not None
        and EDUCATION_LEVEL_ORDER[_CANONICAL_AWARDED_LEVEL]
        >= EDUCATION_LEVEL_ORDER[required_level]
    ):
        return {
            "match_id": match_id,
            "job_id": job_id,
            "requirement_id": req_id,
            "result": "SUPPORTED",
            "evidence_ids": [_CANONICAL_AWARDED_EVIDENCE_ID],
            "claim_ids": [],
            "explanation": (
                f"raw={req_text!r}; required minimum education level "
                f"{required_level} is supported by canonical awarded "
                f"education evidence {_CANONICAL_AWARDED_EVIDENCE_ID} "
                f"(established level {_CANONICAL_AWARDED_LEVEL} meets or "
                "exceeds the stated floor; this does not assert literal "
                "possession of any lower credential)."
            ),
            "transfer_note": None,
            "evaluation_path": "EDUCATION_FLOOR_EVALUATOR",
        }

    return {
        "match_id": match_id,
        "job_id": job_id,
        "requirement_id": req_id,
        "result": "NONE",
        "evidence_ids": [],
        "claim_ids": [],
        "explanation": (
            f"raw={req_text!r}; required minimum education level "
            f"{required_level}; no valid canonical awarded education "
            f"evidence ({_CANONICAL_AWARDED_EVIDENCE_ID}) available to "
            "support this floor; refusing to fabricate support."
        ),
        "transfer_note": None,
        "evaluation_path": "EDUCATION_FLOOR_EVALUATOR",
    }
