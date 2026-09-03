"""SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1 -- bounded, deterministic
classification of where and how the employer positioned each Requirement,
separate from (and never a redefinition of) the existing `importance` field.

Root cause this module exists to fix: `job_decision.detect_hard_blockers()`
treats every `importance=MANDATORY, relevance=HIGH, result=NONE` Requirement
identically as a candidate-entry hard blocker, with no distinction between a
genuine entry qualification (e.g. "Bachelor's Degree from top-tier
university", sourced from a JD's "Requirements"/"Minimum Qualifications"
section) and an ordinary post-hire duty (e.g. "configuring and implementing
[customer workflows] within the Atominvest platform", sourced from a JD's
"What You'll Be Doing"/"Responsibilities"/"Primary Duties" section). The
latter never carries prior-possession language -- the employer is describing
what the hired person will do, not what a candidate must already have -- yet
the existing pipeline silently gates candidacy on it. Real, live instances of
this defect were confirmed in `CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST`
(`REQ_A_CONFIG_IMPLEMENTATION`, `REQ_A_QA_TROUBLESHOOTING`) and
`CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST` (`REQ_C_REGRESSION_TESTING`) during
the `ATOMINVEST_REJECT_CAUSALITY_AND_APPLICATION_ACTIONABILITY_AUDIT_V1`
audit chain (see `CURRENT_MILESTONE.md`).

This module classifies each Requirement into exactly one
`source_semantic_role`:

  - ENTRY_QUALIFICATION   -- a genuine candidate-entry gate;
  - ROLE_RESPONSIBILITY   -- an ordinary post-hire duty;
  - APPLICATION_OR_LEGAL_GATE -- citizenship/clearance/license language,
    already independently handled by job_decision.py's existing dedicated
    JD-text-level citizenship/clearance check -- classified here only so a
    Requirement-row-level mechanism never ALSO independently gates on the
    same fact a second time;
  - AMBIGUOUS             -- signals conflict or are insufficient; the safe,
    non-committal default. AMBIGUOUS never independently hard-blocks and is
    never silently resolved either direction -- it always requires human
    review (see `derive_human_review_required`).

Classification uses THREE independent signals, combined by a small,
explicit, auditable truth table -- never a single exact-string match on
`source_location` alone (section headings are evidence, not absolute
truth):

  1. Section-heading category, from `source_location` (heuristic substring
     match, casefolded) -- RESPONSIBILITY_HEADING / REQUIREMENTS_HEADING /
     LEGAL_HEADING / UNRECOGNIZED_HEADING.
  2. Content shape, from the Requirement's own `source_text` -- DUTY_SHAPED
     (leading action verb, or an early "will"/"you'll" future-duty marker;
     evidenced across the actual corpus: every real "What You'll Be
     Doing"/"Primary Duties" bullet in this repository's fixtures begins
     with an imperative or present-tense action verb -- "Get hands-on...",
     "Work alongside...", "Liaise with...", "Identifies, analyzes...",
     "Maintains a set of...", "Develops and delivers...") or
     CREDENTIAL_SHAPED (a noun-phrase credential/skill statement -- "Bachelor's
     Degree...", "7+ years of SAP FI/CO experience...", "Strong Excel
     skills...").
  2. Explicit prerequisite language -- `must have`, `required experience`,
     `demonstrated/proven (prior) ability`, `minimum N years`,
     `prerequisite`, `certification required`, `N years of ... experience`
     -- an OVERRIDE that always promotes a row to ENTRY_QUALIFICATION
     regardless of section heading (a Responsibilities-sourced "Must have 5
     years of SAP experience" remains a genuine entry gate).
  3. Duplication under an actual Requirements/Qualifications-heading row in
     the SAME job (conservative near-exact-wording containment, not
     semantic similarity) -- another OVERRIDE promoting to
     ENTRY_QUALIFICATION.

Both overrides set `human_review_required=True` on the affected row even
though the resulting role is entry-gate eligible (see
`derive_human_review_required`), so a human/ChatGPT adjudicator can see
that an override -- not the ordinary default -- produced the classification.

Downstream derivation (never independently persisted, never hand-editable):

  - `derive_qualification_gate(source_semantic_role)` -> "YES"/"NO"/"AMBIGUOUS"
  - `derive_human_review_required(...)` -> bool

SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1: classification is now a
PERSISTED, adjudicated fact, not a value silently recomputed on every
`analyze_job()` run. `resolve_persisted_or_fallback()` is the only function
`requirement_normalize.py` calls at runtime: it CONSUMES a valid persisted
`source_semantic_role` (and its provenance) unchanged, and never overwrites
it with a fresh classifier run. `classify_source_semantic_roles()` itself is
reserved for extraction/ingestion time (producing the persisted fields for a
new or backfilled Requirement record) and for explicit backfill/drift-
detection tooling (e.g. `scripts`-style one-time migration, or a test
comparing a fixture's persisted role against what the current classifier
would independently produce) -- it is never invoked automatically inside the
ordinary analysis path.

A Requirement reaching runtime WITHOUT a valid persisted `source_semantic_role`
(missing, null, or an invalid/unrecognized value) is treated as genuinely
UNRESOLVED, not as an implicit entry qualification: `resolve_persisted_or_fallback()`
applies the same safe AMBIGUOUS default used for a classified-but-conflicting
row -- never independently hard-blocking, always `human_review_required=True`,
always visibly surfaced. `derive_qualification_gate()` mirrors this: only an
explicit, valid `ENTRY_QUALIFICATION` value derives `"YES"`; anything else
-- including `None` and an invalid string -- derives `"AMBIGUOUS"`, never a
silent `"YES"`. This applies uniformly to every caller, including a direct
caller of `job_decision.detect_hard_blockers()`/`decide_lane_and_decision()`
that bypasses `normalize_structured_requirements()`/schema validation
entirely -- there is no backward-compatibility carve-out.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

CLASSIFIER_VERSION = "SOURCE_SEMANTIC_ROLE_CLASSIFIER_V1"

SOURCE_SEMANTIC_ROLES = frozenset(
    {
        "ENTRY_QUALIFICATION",
        "ROLE_RESPONSIBILITY",
        "APPLICATION_OR_LEGAL_GATE",
        "AMBIGUOUS",
    }
)

# --------------------------------------------------------------------------
# Signal 1: section-heading category (heuristic, not absolute truth).
# --------------------------------------------------------------------------
_RESPONSIBILITY_HEADING_CUES = re.compile(
    r"responsibilit|what\s+you.ll\s+be\s+doing|\bduties\b|primary\s+dut",
    re.IGNORECASE,
)
_LEGAL_HEADING_CUES = re.compile(
    r"citizenship|clearance|\blegal\b|licens", re.IGNORECASE
)
_REQUIREMENTS_HEADING_CUES = re.compile(
    r"requirement|qualification|\brequired\b|\bpreferred\b|"
    r"nice\s+to\s+have|also\s+desired|\bbonus\b",
    re.IGNORECASE,
)

# CANDIDATE_PROFILE_HEADING_SEMANTIC_SCOPE_V1: a bounded, INTERNAL,
# non-persisted heading category, weaker than REQUIREMENTS_HEADING, for a
# heading family that describes the candidate profile without using any of
# _REQUIREMENTS_HEADING_CUES' vocabulary. V1 recognizes ONLY the two
# semantically equivalent variants reproduced against a real, live,
# faithfully-captured source (JD Software Implementation Analyst,
# https://www.jdsoft.com/career-ia.html, fetched 2026-09-03): "What We're
# Looking For" and "What We Are Looking For". The apostrophe is matched
# with `.` (not a literal `'`), mirroring this module's own existing
# _RESPONSIBILITY_HEADING_CUES convention for "what you.ll be doing", since
# the live source uses a curly apostrophe (U+2019), not a straight one.
# Deliberately NOT extended to "What You Bring"/"What You'll Bring"/
# "Who You Are"/"About You"/"Ideal Candidate" or other candidate-profile
# synonyms -- those have not been reproduced against a real defect and, per
# external evidence gathered during CANDIDATE_PROFILE_HEADING_SEMANTIC_SCOPE_V1's
# investigation, "Who You Are" in particular is also used by real employers
# for broad culture/personality content rather than conventional
# qualifications -- generalizing beyond the one reproduced heading family
# is explicitly out of scope for V1.
_CANDIDATE_PROFILE_HEADING_CUES = re.compile(
    r"what\s+we.re\s+looking\s+for|what\s+we\s+are\s+looking\s+for",
    re.IGNORECASE,
)


def _classify_heading(source_location: str | None) -> str:
    text = source_location if isinstance(source_location, str) else ""
    if _LEGAL_HEADING_CUES.search(text):
        return "LEGAL_HEADING"
    if _RESPONSIBILITY_HEADING_CUES.search(text):
        return "RESPONSIBILITY_HEADING"
    if _REQUIREMENTS_HEADING_CUES.search(text):
        return "REQUIREMENTS_HEADING"
    if _CANDIDATE_PROFILE_HEADING_CUES.search(text):
        return "CANDIDATE_PROFILE_HEADING"
    return "UNRECOGNIZED_HEADING"


# --------------------------------------------------------------------------
# Signal 2: content shape -- duty-shaped (action/future) vs credential-shaped
# (noun-phrase). Bounded, explicit verb list evidenced from the real corpus
# (Atominvest "What You'll Be Doing", MIT LL "Primary Duties",
# JOB_FIXTURE_BSA_001 "Responsibilities") -- not a general NLP parser.
# --------------------------------------------------------------------------
_DUTY_LEADING_VERBS = re.compile(
    r"^\s*(?:get|work|analyse|analyze|drive|liaise|field|maintain(?:s)?|"
    r"support(?:s)?|configure(?:s)?|onboard(?:s)?|identif(?:y|ies)|"
    r"develop(?:s)?|deliver(?:s)?|perform(?:s)?|ensure(?:s)?|track(?:s)?|"
    r"categoriz(?:e|es)|collaborat(?:e|es)|help(?:s)?|assist(?:s)?|"
    r"coordinat(?:e|es)|manage(?:s)?|handle(?:s)?|respond(?:s)?|"
    r"monitor(?:s)?|document(?:s)?|prepare(?:s)?|review(?:s)?|"
    r"troubleshoot(?:s)?|resolve(?:s)?|communicat(?:e|es)|creat(?:e|es)|"
    r"build(?:s)?|design(?:s)?)\b",
    re.IGNORECASE,
)
_FUTURE_DUTY_MARKER = re.compile(r"\b(?:you'?ll|you\s+will|will)\b", re.IGNORECASE)

# Narrow "gain(ing) exposure to" duty-language recognition (SOURCE_ROLE_
# IMPLEMENTATION_BOUNDED_CORRECTION_V1, Section 6). Deliberately anchored
# to the exact gerund/present-tense construction "gain(ing) exposure to" --
# NOT a broad standalone "gain" rule. "gain(?:ing)?" followed by required
# whitespace before "exposure" means "gained exposure to..." (past tense)
# never matches (no whitespace immediately follows "gain" in "gained").
# Treated the same as a leading duty verb (contributes to duty_shaped),
# never to future_duty_marker_present -- it must not itself force AMBIGUOUS
# under a Requirements heading, only support ROLE_RESPONSIBILITY under a
# Responsibilities/Duties heading with no prerequisite language.
_GAIN_EXPOSURE_DUTY_MARKER = re.compile(r"\bgain(?:ing)?\s+exposure\s+to\b", re.IGNORECASE)


def _has_gain_exposure_marker(source_text: str) -> bool:
    return bool(_GAIN_EXPOSURE_DUTY_MARKER.search(source_text))


def _has_duty_leading_verb(source_text: str) -> bool:
    stripped = source_text.strip()
    return bool(_DUTY_LEADING_VERBS.match(stripped)) or _has_gain_exposure_marker(stripped)


def _has_future_duty_marker(source_text: str) -> bool:
    # Future-duty marker near the clause start only -- avoids a late "will"
    # deep in an unrelated clause producing a false positive.
    head = source_text.strip()[:50]
    return bool(_FUTURE_DUTY_MARKER.search(head))


def _is_duty_shaped(source_text: str) -> bool:
    """True if EITHER sub-signal fires. Used only where the two signals are
    treated identically (RESPONSIBILITY_HEADING branch); the
    REQUIREMENTS_HEADING branch consults the two sub-signals separately --
    see _resolve_role's rationale for why a bare leading verb ("Document
    requirements...", "Validate CSV imports...") is ordinary, ubiquitous
    Minimum-Qualifications phrasing and must NOT alone force AMBIGUOUS,
    while a genuine future-tense marker ("Will configure...") is a real
    signal conflict worth flagging."""
    return _has_duty_leading_verb(source_text) or _has_future_duty_marker(source_text)


# --------------------------------------------------------------------------
# Override 1: explicit prior-possession / prerequisite language.
# --------------------------------------------------------------------------
_PREREQUISITE_LANGUAGE = re.compile(
    r"\bmust\s+have\b|\brequired\s+experience\b|"
    r"\b(?:demonstrated|proven)\s+(?:prior\s+)?ability\b|"
    r"\bminimum\s+(?:of\s+)?\d+\+?\s*years?\b|\bprerequisite\b|"
    r"\bcertification\s+required\b|\blicens\w*\s+required\b|"
    r"\b\d+\+?\s*years?\s+of\s+[a-z0-9 /,'\-]{0,40}?experience\b",
    re.IGNORECASE,
)


def _has_prerequisite_language(source_text: str) -> bool:
    return bool(_PREREQUISITE_LANGUAGE.search(source_text))


# --------------------------------------------------------------------------
# SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1: legal-flavored language
# is not a single undifferentiated bucket. Three distinct cases, evidenced
# by the adversarial matrix this correction was audited against:
#
#   1. License/certification prerequisite ("Must hold a valid professional
#      engineering license.") -- a genuine, candidate-held, testable
#      credential, no different in kind from a degree requirement. Routes
#      to ENTRY_QUALIFICATION, never silently swallowed into an unresolved
#      legal gate merely because "licens*" appears.
#   2. Citizenship/clearance/work-authorization/facility-access language --
#      NOT an ordinary candidate-suppliable skill/credential fact. Routes
#      to APPLICATION_OR_LEGAL_GATE ONLY when it is provably covered by a
#      named, tested dedicated consumer (currently: job_decision.py's
#      JD-text-level citizenship/clearance check, via
#      CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN below -- the single
#      source of truth both modules use, eliminating drift). When present
#      but NOT provably covered, it resolves to AMBIGUOUS (never silently
#      APPLICATION_OR_LEGAL_GATE with no real consumer) and is separately
#      flagged as an unresolved gate in job_analysis.py's
#      unresolved_gate_observations output -- it must never simply
#      disappear.
#   3. Descriptive legal/compliance language with no prerequisite framing
#      ("This role complies with all applicable licensing and clearance
#      regulations.") -- describes the EMPLOYER's posture, not a candidate
#      prerequisite. Never forced into an entry gate; falls through to
#      ordinary heading/content-shape classification.
# --------------------------------------------------------------------------

# Single source of truth for "does this text express a citizenship/
# clearance/work-authorization/facility-access fact" -- reused verbatim by
# job_decision.py's dedicated JD-text-level check, so classification here
# and blocker evaluation there can never drift apart.
CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN = re.compile(
    r"\b(us\s+citizen|u\.s\.\s+citizen|security clearance|secret clearance|"
    r"top secret|must be a citizen)\b",
    re.IGNORECASE,
)

# Broader topic detection (for classification purposes only -- NOT the
# consumer-coverage test) that also catches paraphrased facility/government
# access wording the narrow consumer pattern above does not.
_CITIZENSHIP_CLEARANCE_TOPIC_CUES = re.compile(
    r"citizenship|security\s+clearance|\bclearance\b|work\s+authoriz\w*|"
    r"authoriz\w*\s+to\s+work|visa\s+sponsor\w*|facility\s+access|"
    r"government\s+access",
    re.IGNORECASE,
)
_MANDATE_CUE = re.compile(r"\bmust\b|\brequired\b", re.IGNORECASE)
_LICENSE_CERTIFICATION_TOPIC_CUES = re.compile(r"\blicens\w*|\bcertificat\w*", re.IGNORECASE)


def _has_citizenship_clearance_topic(source_text: str) -> bool:
    return bool(_CITIZENSHIP_CLEARANCE_TOPIC_CUES.search(source_text))


def _has_citizenship_clearance_prescriptive_language(source_text: str) -> bool:
    """Topic word AND a mandate cue (must/required) present -- a
    self-contained prescriptive citizenship/clearance/authorization
    assertion, not merely descriptive text that happens to mention the
    topic (case D)."""
    return bool(
        _CITIZENSHIP_CLEARANCE_TOPIC_CUES.search(source_text)
        and _MANDATE_CUE.search(source_text)
    )


def is_covered_by_citizenship_clearance_consumer(source_text: str) -> bool:
    """True when source_text overlaps the exact vocabulary
    job_decision.py's dedicated JD-text-level citizenship/clearance check
    uses -- a proxy for "the existing named consumer, scanning the JD this
    row was drawn from, will independently catch this fact." Regression-
    tested directly (see tests/source_semantic_role_qualification_view_v1_test.py)
    by constructing jd_text from exactly this row's source_text and
    confirming job_decision.detect_hard_blockers() fires on it."""
    return bool(CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN.search(source_text))


def _has_license_certification_prerequisite(source_text: str) -> bool:
    """License/certification topic word AND a mandate cue (reusing the
    existing broader prerequisite-language regex, which already covers
    'licens* required', 'must have', 'certification required', etc.) --
    a genuine candidate-held credential prerequisite, case A."""
    return bool(
        _LICENSE_CERTIFICATION_TOPIC_CUES.search(source_text)
        and (_MANDATE_CUE.search(source_text) or _has_prerequisite_language(source_text))
    )


# --------------------------------------------------------------------------
# Override 2: duplication under a Requirements/Qualifications-heading row in
# the same job. Conservative near-exact-wording containment only -- no
# semantic similarity, consistent with this repository's "no generic
# lexical overmatch" precedent (requirement_match.py).
# --------------------------------------------------------------------------
_MIN_DUPLICATE_LEN = 20


def _normalize_for_duplication(text: str) -> str:
    normalized = text.casefold().strip()
    normalized = re.sub(r"[.\-–—;:,]+$", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _is_duplicated_under_requirements(
    source_text: str, requirements_heading_texts: list[str]
) -> bool:
    candidate = _normalize_for_duplication(source_text)
    if len(candidate) < _MIN_DUPLICATE_LEN:
        return False
    for other in requirements_heading_texts:
        other_norm = _normalize_for_duplication(other)
        if len(other_norm) < _MIN_DUPLICATE_LEN:
            continue
        if candidate == other_norm:
            return True
        if candidate in other_norm or other_norm in candidate:
            return True
    return False


def _classify_single_row(
    requirement: Mapping[str, Any],
) -> dict[str, Any]:
    """First pass: everything computable from this one row alone."""
    source_text = requirement.get("source_text")
    source_location = requirement.get("source_location")
    text = source_text if isinstance(source_text, str) else ""

    heading = _classify_heading(source_location)
    duty_shaped = _is_duty_shaped(text)
    prerequisite_present = _has_prerequisite_language(text)

    return {
        "heading": heading,
        "duty_shaped": duty_shaped,
        "future_duty_marker_present": _has_future_duty_marker(text),
        "explicit_prerequisite_language_present": prerequisite_present,
        "license_certification_prerequisite_present": _has_license_certification_prerequisite(text),
        "citizenship_clearance_topic_present": _has_citizenship_clearance_topic(text),
        "citizenship_clearance_prescriptive_present": _has_citizenship_clearance_prescriptive_language(text),
        "citizenship_clearance_consumer_covered": is_covered_by_citizenship_clearance_consumer(text),
    }


def _resolve_role(
    row: dict[str, Any], duplicated_under_requirements: bool
) -> tuple[str, str, bool]:
    """Combine signals into (source_semantic_role, classification_basis,
    override_applied) per the locked truth table. override_applied is True
    only when an override rule (not the ordinary default) decided the role.
    """
    heading = row["heading"]
    duty_shaped = row["duty_shaped"]
    prerequisite = row["explicit_prerequisite_language_present"]
    license_prereq = row["license_certification_prerequisite_present"]
    citizenship_topic = row["citizenship_clearance_topic_present"]
    citizenship_prescriptive = row["citizenship_clearance_prescriptive_present"]
    citizenship_covered = row["citizenship_clearance_consumer_covered"]

    # Case A: explicit professional license/certification prerequisite --
    # a genuine, candidate-held, testable credential. Checked FIRST so it
    # is never swallowed into an unresolved/legal-gate bucket merely
    # because a legal-flavored heading or the word "licens*" is present.
    if license_prereq:
        return (
            "ENTRY_QUALIFICATION",
            f"explicit professional license/certification prerequisite "
            f"language present in source_text (heading={heading}); "
            "OVERRIDE applied -- promoted to ENTRY_QUALIFICATION as a "
            "genuine candidate-held credential, not an unresolved legal gate.",
            heading not in ("REQUIREMENTS_HEADING",),
        )

    # Case B / real MIT precedent: citizenship/clearance/work-authorization/
    # facility-access language. Routed to APPLICATION_OR_LEGAL_GATE ONLY
    # when provably covered by the named, tested JD-text-level consumer
    # (job_decision.detect_hard_blockers()'s citizenship/clearance check,
    # sharing this module's CITIZENSHIP_CLEARANCE_JD_CONSUMER_PATTERN as
    # its single source of truth). A prescriptive citizenship/clearance
    # assertion (topic word + mandate cue) that the named consumer would
    # NOT catch -- or a legal-heading row whose text is not itself
    # consumer-covered -- resolves to AMBIGUOUS instead of a silently
    # uncovered APPLICATION_OR_LEGAL_GATE; job_analysis.py separately
    # surfaces it in unresolved_gate_observations so it is never simply
    # invisible.
    if heading == "LEGAL_HEADING" or citizenship_prescriptive:
        if citizenship_covered:
            return (
                "APPLICATION_OR_LEGAL_GATE",
                f"citizenship/clearance/work-authorization signal present "
                f"(heading={heading}) and provably covered by the named "
                "job_decision.py JD-text-level citizenship/clearance "
                "consumer -- handled there, not by ordinary qualification "
                "blocking.",
                False,
            )
        return (
            "AMBIGUOUS",
            f"citizenship/clearance/work-authorization/legal signal present "
            f"(heading={heading}, prescriptive={citizenship_prescriptive}, "
            f"topic_present={citizenship_topic}) but NOT provably covered by "
            "any named dedicated consumer -- resolved to AMBIGUOUS rather "
            "than an unproven APPLICATION_OR_LEGAL_GATE classification; "
            "UNRESOLVED_LEGAL_OR_ACCESS_GATE requires human adjudication "
            "and is separately surfaced, never silently dropped.",
            False,
        )

    if prerequisite:
        return (
            "ENTRY_QUALIFICATION",
            f"explicit prerequisite/prior-possession language present in "
            f"source_text (heading={heading}); OVERRIDE applied -- promoted "
            "to ENTRY_QUALIFICATION regardless of section heading.",
            heading == "RESPONSIBILITY_HEADING" or heading == "UNRECOGNIZED_HEADING",
        )

    if duplicated_under_requirements:
        return (
            "ENTRY_QUALIFICATION",
            f"near-exact wording duplicated under a Requirements/"
            f"Qualifications-heading row in the same job (heading={heading}); "
            "OVERRIDE applied -- promoted to ENTRY_QUALIFICATION.",
            heading == "RESPONSIBILITY_HEADING" or heading == "UNRECOGNIZED_HEADING",
        )

    if heading == "RESPONSIBILITY_HEADING" and duty_shaped:
        return (
            "ROLE_RESPONSIBILITY",
            "source_location indicates a Responsibilities/Duties section "
            "and source_text is duty-shaped (leading action verb or "
            "future-duty marker) with no prerequisite language and no "
            "duplication under Requirements/Qualifications.",
            False,
        )

    if heading == "REQUIREMENTS_HEADING" and row["future_duty_marker_present"]:
        # Only a genuine future-tense marker ("Will configure customer
        # platforms.") is a real signal conflict under a Requirements
        # heading. A bare leading action verb ("Document requirements
        # after stakeholder workshops.", "Validate CSV imports...",
        # "Manage marketing workflow automation...") is ordinary,
        # ubiquitous Minimum-Qualifications/Required-Skills phrasing --
        # real Requirements-section bullets are ROUTINELY verb-led skill
        # descriptions, not exclusively noun phrases -- and must not alone
        # be read as a duty-vs-qualification conflict.
        return (
            "AMBIGUOUS",
            "source_location indicates a Requirements/Qualifications "
            "section but source_text carries a future-tense duty marker "
            "(will/you'll) -- a genuine signal conflict (a Requirements-"
            "section row should not describe a future duty); resolved to "
            "AMBIGUOUS pending human review, not silently to either role.",
            False,
        )

    if heading == "REQUIREMENTS_HEADING":
        # Ordinary Requirements-section case, whether the bullet is
        # noun-phrase credential-shaped ("Bachelor's Degree...") or
        # verb-led skill-shaped ("Document requirements...",
        # "Validate CSV imports...") -- both are routine ways employers
        # phrase minimum/preferred qualifications; the section heading is
        # the authoritative signal here, not incidental verb choice.
        return (
            "ENTRY_QUALIFICATION",
            "source_location indicates a Requirements/Qualifications "
            "section with no future-tense duty marker; the section "
            f"heading is authoritative (content shape: "
            f"{'duty-verb-led' if duty_shaped else 'credential-shaped'}).",
            False,
        )

    if heading == "RESPONSIBILITY_HEADING":
        # credential-shaped content in a Responsibilities section --
        # unusual/conflicting; do not silently assume either role.
        return (
            "AMBIGUOUS",
            "source_location indicates a Responsibilities/Duties section "
            "but source_text is credential-shaped, not duty-shaped -- "
            "conflicting signals; resolved to AMBIGUOUS pending human "
            "review.",
            False,
        )

    if heading == "CANDIDATE_PROFILE_HEADING":
        # CANDIDATE_PROFILE_HEADING_SEMANTIC_SCOPE_V1: a weaker positive
        # signal than REQUIREMENTS_HEADING -- content shape still gates it.
        # Unlike the REQUIREMENTS_HEADING branch above (which only treats a
        # future-tense marker as a conflict, and lets an ordinary duty-verb
        # lead through as routine Requirements-section phrasing), a
        # candidate-profile heading is a less certain, more heterogeneous
        # label across real employers -- so a duty-SHAPED row here
        # (leading duty verb OR future-duty marker) is deliberately refused
        # promotion and resolves AMBIGUOUS instead, pending human review.
        if duty_shaped:
            return (
                "AMBIGUOUS",
                "source_location indicates a weaker candidate-profile "
                "heading (e.g. \"What We're Looking For\") and source_text "
                "is duty-shaped (leading action verb or future-duty "
                "marker) -- this heading family is a less certain signal "
                "than a literal Requirements/Qualifications heading, so "
                "duty-shaped content is not promoted; resolved to "
                "AMBIGUOUS pending human review.",
                False,
            )
        return (
            "ENTRY_QUALIFICATION",
            "source_location indicates a weaker candidate-profile heading "
            "(e.g. \"What We're Looking For\") with no duty-shaped content "
            "and no future-tense duty marker; the candidate-profile-"
            "heading path is authoritative here (content shape: "
            "credential-shaped) -- distinct from, and weaker than, a "
            "literal Requirements/Qualifications-heading classification.",
            False,
        )

    # UNRECOGNIZED_HEADING with no override: no reliable location signal
    # at all -- conservative fail-safe default.
    return (
        "AMBIGUOUS",
        "source_location did not match any recognized "
        "Responsibilities/Requirements/Legal heading pattern, and no "
        "prerequisite-language or duplication override applied; resolved "
        "to AMBIGUOUS pending human review.",
        False,
    )


def classify_source_semantic_roles(
    requirements: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Classify every Requirement in one job's requirement set.

    Two passes: (1) per-row signals from that row alone; (2) duplication
    detection, which needs every other row in the same job. Returns one
    classification dict per input row, in the same order, each carrying:
    source_semantic_role, source_semantic_role_basis,
    explicit_prerequisite_language_present, duplicated_under_requirements,
    source_semantic_role_classifier_version.
    """
    per_row = [_classify_single_row(r) for r in requirements]

    # (requirement_id, source_text) for every Requirements-heading row --
    # identity-keyed (not text-keyed) so a row is never excluded from being
    # a duplication target merely because its own text happens to be
    # identical to the candidate's (that IS the duplicate case this
    # override exists to detect).
    requirements_heading_entries = [
        (r.get("requirement_id"), r.get("source_text") or "")
        for r, row in zip(requirements, per_row)
        if row["heading"] == "REQUIREMENTS_HEADING"
        and isinstance(r.get("source_text"), str)
    ]

    results: list[dict[str, Any]] = []
    for requirement, row in zip(requirements, per_row):
        source_text = requirement.get("source_text")
        text = source_text if isinstance(source_text, str) else ""
        own_id = requirement.get("requirement_id")

        # A Requirements-heading row is never checked against itself
        # (excluded by requirement_id, not by text) -- only its distinct
        # siblings count as duplication targets.
        duplicated = False
        if row["heading"] != "REQUIREMENTS_HEADING":
            duplicated = _is_duplicated_under_requirements(
                text,
                [other_text for other_id, other_text in requirements_heading_entries if other_id != own_id],
            )

        role, basis, override_applied = _resolve_role(row, duplicated)

        results.append(
            {
                "source_semantic_role": role,
                "source_semantic_role_basis": basis,
                "explicit_prerequisite_language_present": row[
                    "explicit_prerequisite_language_present"
                ],
                "duplicated_under_requirements": duplicated,
                "source_semantic_role_classifier_version": CLASSIFIER_VERSION,
                "_override_applied": override_applied,
            }
        )
    return results


# --------------------------------------------------------------------------
# Persistence consumption -- the ONLY function requirement_normalize.py
# calls at runtime. Classification itself (classify_source_semantic_roles,
# above) is reserved for extraction/ingestion-time authoring, explicit
# backfill, and drift-detection tooling -- never invoked automatically
# during ordinary analysis.
# --------------------------------------------------------------------------

FALLBACK_BASIS_MISSING = (
    "no persisted source_semantic_role present on this requirement; safe "
    "fallback applied -- a missing classification is genuinely unresolved, "
    "never an implicit entry-qualification gate."
)
FALLBACK_BASIS_INVALID_TEMPLATE = (
    "persisted source_semantic_role value {value!r} is not a recognized "
    "SOURCE_SEMANTIC_ROLES member; safe fallback applied -- an invalid "
    "classification is genuinely unresolved, never an implicit "
    "entry-qualification gate."
)


def resolve_persisted_or_fallback(requirement: Mapping[str, Any]) -> dict[str, Any]:
    """Consume a Requirement's persisted source_semantic_role/provenance
    unchanged if present and valid; otherwise apply the safe AMBIGUOUS
    fallback (never recomputes via classify_source_semantic_roles(), and
    never derives an implicit entry-qualification gate for a missing or
    invalid value). This is the single function requirement_normalize.py
    calls at runtime -- it never silently overwrites a valid persisted
    classification and never silently classifies an unmigrated one as
    gate-eligible.
    """
    role = requirement.get("source_semantic_role")
    if role in SOURCE_SEMANTIC_ROLES:
        return {
            "source_semantic_role": role,
            "source_semantic_role_basis": (
                requirement.get("source_semantic_role_basis")
                or "(persisted role with no recorded basis)"
            ),
            "explicit_prerequisite_language_present": bool(
                requirement.get("explicit_prerequisite_language_present")
            ),
            "duplicated_under_requirements": bool(
                requirement.get("duplicated_under_requirements")
            ),
            "source_semantic_role_classifier_version": (
                requirement.get("source_semantic_role_classifier_version")
                or "UNKNOWN_UNVERSIONED_PERSISTED_CLASSIFICATION"
            ),
        }

    basis = FALLBACK_BASIS_MISSING if role is None else FALLBACK_BASIS_INVALID_TEMPLATE.format(value=role)
    return {
        "source_semantic_role": "AMBIGUOUS",
        "source_semantic_role_basis": basis,
        "explicit_prerequisite_language_present": False,
        "duplicated_under_requirements": False,
        "source_semantic_role_classifier_version": CLASSIFIER_VERSION,
    }


# --------------------------------------------------------------------------
# Derived views (never persisted, never hand-editable).
# --------------------------------------------------------------------------


def derive_qualification_gate(source_semantic_role: Any) -> str:
    """YES / NO / AMBIGUOUS.

    SOURCE_ROLE_IMPLEMENTATION_BOUNDED_CORRECTION_V1: only an explicit,
    valid ENTRY_QUALIFICATION derives YES. A missing role (None), an
    invalid/unrecognized value, ROLE_RESPONSIBILITY, and
    APPLICATION_OR_LEGAL_GATE are all treated as NOT independently
    gate-eligible -- AMBIGUOUS/NO, never a silent YES. This holds for every
    caller, including one that bypasses normalize_structured_requirements()
    and schema validation entirely; there is no backward-compatibility
    carve-out for a missing or malformed classification.
    """
    if source_semantic_role == "ENTRY_QUALIFICATION":
        return "YES"
    if source_semantic_role in ("ROLE_RESPONSIBILITY", "APPLICATION_OR_LEGAL_GATE"):
        return "NO"
    # AMBIGUOUS, None (missing), and any invalid/unrecognized value all
    # resolve to AMBIGUOUS -- genuinely unresolved, never an implicit gate.
    return "AMBIGUOUS"


def derive_human_review_required(requirement: Mapping[str, Any]) -> bool:
    """True when source_semantic_role=AMBIGUOUS, or when a classified
    override condition (explicit_prerequisite_language_present or
    duplicated_under_requirements actually deciding the role) produced an
    entry-gate-eligible classification that would otherwise have read as a
    responsibility. Never independently persisted or hand-editable --
    always recomputed from the persisted classification fields."""
    role = requirement.get("source_semantic_role")
    if role == "AMBIGUOUS":
        return True
    basis = requirement.get("source_semantic_role_basis")
    if isinstance(basis, str) and "OVERRIDE applied" in basis:
        return True
    return False
