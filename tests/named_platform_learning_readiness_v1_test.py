"""Regression tests for NAMED_PLATFORM_LEARNING_READINESS_V1.

Mechanically reproduced defect: infer_requirement_capabilities() mapped every
occurrence of Salesforce/SFDC to salesforce_administration, including
explicit employer willingness/readiness/interest/desire-to-learn language
("Willingness to learn Asana and Salesforce"). That false present-capability
inference then fed the pre-existing salesforce_unsupported NONE trap,
converting an employer's willingness to train into a false-NONE result.

Frozen semantic contract under test:

1. Explicit learning/readiness/interest/desire-to-learn language about
   Salesforce must NOT infer salesforce_administration.
2. Genuine present-capability Salesforce/SFDC requirements must continue to
   infer salesforce_administration, unchanged.
3. The existing salesforce_unsupported NONE trap must still fire for genuine
   present-capability requirements, and must NOT fire for learning-language
   requirements.

Exercises real production code (requirement_match.py) -- no logic is
duplicated here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from requirement_match import (  # noqa: E402
    infer_requirement_capabilities,
    match_requirement,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def _req(req_id: str, text: str) -> dict:
    return {
        "requirement_id": req_id,
        "text": text,
        "source_text": text,
        "domain": None,
        "category": None,
        "technology": [],
        "relevance": "HIGH",
        "importance": "MANDATORY",
    }


def _match(req_id: str, text: str) -> dict:
    return match_requirement(
        job_id="JOB_NAMED_PLATFORM_LEARNING_READINESS_V1",
        requirement=_req(req_id, text),
        reusable_claims=[],
        evidence_index={},
        match_index=0,
    )


# ======================================================================
# A. Negative controls -- explicit learning/readiness language must NOT
#    infer salesforce_administration, and must NOT hit the Salesforce
#    NONE trap through the ordinary matcher path.
# ======================================================================
NEGATIVE_CASES = [
    ("REQ_BARR_EXACT", "Willingness to learn Asana and Salesforce"),
    ("REQ_LEARN_SF", "Willingness to learn Salesforce"),
    ("REQ_INTEREST_SF", "Interest in learning Salesforce"),
    ("REQ_DESIRE_SF", "Strong desire to learn Salesforce"),
    ("REQ_LEARN_SFDC", "Willingness to learn SFDC"),
]

for req_id, text in NEGATIVE_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] != "NONE_TRAP"
        or "salesforce_unsupported" not in match["explanation"],
        f"{req_id} ({text!r}) must not hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )

print("PASS A: explicit learning/readiness Salesforce/SFDC language never infers "
      "salesforce_administration and never hits the Salesforce NONE trap.")


# ======================================================================
# B. Positive controls -- genuine present-capability requirements must
#    still infer salesforce_administration and still hit the pre-existing
#    salesforce_unsupported NONE trap (protection preserved, not weakened).
# ======================================================================
POSITIVE_CASES = [
    ("REQ_SF_ADMIN_REQUIRED", "Salesforce administration required"),
    ("REQ_SF_EXPERIENCE_REQUIRED", "Experience with Salesforce required"),
    ("REQ_SF_PROFICIENCY_REQUIRED", "Salesforce proficiency required"),
    ("REQ_SF_HANDSON_REQUIRED", "Hands-on Salesforce experience required"),
    ("REQ_SFDC_REQUIRED", "SFDC administration experience required"),
]

for req_id, text in POSITIVE_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" in caps,
        f"{req_id} ({text!r}) must still infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] == "NONE_TRAP"
        and "salesforce_unsupported" in match["explanation"],
        f"{req_id} ({text!r}) must still hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )
    assert_true(
        match["result"] == "NONE",
        f"{req_id} ({text!r}) must still resolve NONE, got {match['result']}",
    )

print("PASS B: genuine present-capability Salesforce/SFDC requirements still infer "
      "salesforce_administration and still hit the existing salesforce_unsupported NONE trap.")


# ======================================================================
# C. Live Barr phrase end-to-end -- no capability coverage, no NONE trap
#    attributable to Salesforce (may still be NONE/UNKNOWN for other
#    reasons -- e.g. no recognized capability at all -- but never via the
#    Salesforce NONE trap).
# ======================================================================
barr_match = _match("REQ_BARR_LIVE", "Willingness to learn Asana and Salesforce")
assert_true(
    barr_match["evaluation_path"] != "NONE_TRAP",
    f"live Barr phrase must not resolve via any forced NONE trap; "
    f"got evaluation_path={barr_match['evaluation_path']!r}",
)
print("PASS C: live Barr phrase no longer resolves through the Salesforce NONE trap.")


# ======================================================================
# D. Unrelated capability inference and Excel qualifier protections are
#    unaffected by the Salesforce guard.
# ======================================================================
req_excel = _req("REQ_EXCEL", "Strong Excel skills required")
caps_excel = infer_requirement_capabilities(req_excel)
assert_true(
    "excel_proficiency" in caps_excel,
    f"Excel proficiency inference must be unaffected; got {sorted(caps_excel)}",
)
assert_true(
    "salesforce_administration" not in caps_excel,
    f"Excel-only requirement must not gain salesforce_administration; got {sorted(caps_excel)}",
)

req_excel_verb = _req("REQ_EXCEL_VERB", "Willing to excel in a fast-paced environment")
caps_excel_verb = infer_requirement_capabilities(req_excel_verb)
assert_true(
    "excel_proficiency" not in caps_excel_verb,
    f"'excel in' verb usage must remain excluded from excel_proficiency; got {sorted(caps_excel_verb)}",
)

print("PASS D: unrelated capability inference and existing Excel qualifier protections unaffected.")

# ======================================================================
# E. Mixed-sentence repair -- a Salesforce/SFDC mention governed by
#    learning/readiness language must still be suppressed, but a SECOND,
#    independent Salesforce/SFDC mention in the SAME sentence that itself
#    expresses present capability/experience/proficiency/administration
#    must still infer salesforce_administration and still hit the
#    salesforce_unsupported NONE trap. Candidate #1 was rejected because
#    whole-clause suppression let the learning language governing the
#    first mention also wrongly suppress the second, independent mention.
# ======================================================================
MIXED_CASES = [
    (
        "REQ_MIXED_WILLING_EXPERIENCE",
        "Willingness to learn Salesforce and experience with Salesforce required",
    ),
    (
        "REQ_MIXED_INTEREST_HANDSON",
        "Interest in learning Salesforce and hands-on Salesforce experience required",
    ),
    (
        "REQ_MIXED_INTEREST_PROFICIENCY",
        "Interest in learning Salesforce, but Salesforce proficiency is required",
    ),
]

for req_id, text in MIXED_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" in caps,
        f"{req_id} ({text!r}) must infer salesforce_administration from the "
        f"independent present-capability mention; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] == "NONE_TRAP"
        and "salesforce_unsupported" in match["explanation"],
        f"{req_id} ({text!r}) must hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )
    assert_true(
        match["result"] == "NONE",
        f"{req_id} ({text!r}) must resolve NONE, got {match['result']}",
    )

print("PASS E: mixed learning + present-capability Salesforce sentences are "
      "repaired mention-scoped -- the learning-governed mention stays "
      "suppressed and the independent present-capability mention still infers "
      "salesforce_administration.")


# ======================================================================
# F. Structured-technology fallback boundary -- structured
#    `technology=['Salesforce']` metadata must be consulted ONLY when no
#    textual Salesforce/SFDC mention exists at all. It must never
#    re-manufacture a present-capability requirement out of employer text
#    that is only willingness/interest/desire-to-learn language, and it
#    must still preserve the legacy fallback when Salesforce is represented
#    purely by structured metadata with no textual mention.
# ======================================================================
req_tech_only = _req("REQ_TECH_METADATA_ONLY", "Familiarity with common office tools")
req_tech_only["technology"] = ["Salesforce"]
caps_tech_only = infer_requirement_capabilities(req_tech_only)
assert_true(
    "salesforce_administration" in caps_tech_only,
    "Structured technology=['Salesforce'] with no textual Salesforce mention "
    f"must still fall back to inferring salesforce_administration; got {sorted(caps_tech_only)}",
)

req_learning_plus_tech = _req(
    "REQ_LEARNING_TEXT_PLUS_TECH_METADATA", "Willingness to learn Salesforce"
)
req_learning_plus_tech["technology"] = ["Salesforce"]
caps_learning_plus_tech = infer_requirement_capabilities(req_learning_plus_tech)
assert_true(
    "salesforce_administration" not in caps_learning_plus_tech,
    "A trailing structured technology=['Salesforce'] entry must not "
    "re-manufacture a present-capability requirement when the employer text "
    f"itself is only willingness-to-learn language; got {sorted(caps_learning_plus_tech)}",
)

print("PASS F: structured technology metadata is a legacy fallback only when "
      "no textual Salesforce/SFDC mention exists, and never overrides genuine "
      "textual learning language.")


# ======================================================================
# G. Negated/non-required current-possession language -- an explicit
#    employer statement that Salesforce experience is NOT required must
#    never infer salesforce_administration or hit the Salesforce NONE trap.
# ======================================================================
NEGATED_REQUIREMENT_CASES = [
    ("REQ_NO_SF_REQUIRED", "No Salesforce experience required; willingness to learn Salesforce"),
    ("REQ_SF_NOT_REQUIRED", "Salesforce experience is not required"),
    ("REQ_PRIOR_SF_NOT_REQUIRED", "Prior Salesforce experience not required"),
]

for req_id, text in NEGATED_REQUIREMENT_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] != "NONE_TRAP"
        or "salesforce_unsupported" not in match["explanation"],
        f"{req_id} ({text!r}) must not hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )

print("PASS G: explicit negated/non-required Salesforce/SFDC language never infers "
      "salesforce_administration and never hits the Salesforce NONE trap.")


# ======================================================================
# H. Mixed negated-then-genuine-positive control -- an explicit
#    non-required statement followed by an INDEPENDENT genuine
#    present-capability requirement must still infer salesforce_administration
#    from the second, independent clause.
# ======================================================================
req_negated_then_positive = _req(
    "REQ_NEGATED_THEN_POSITIVE",
    "No Salesforce experience required; Salesforce administration required for this function",
)
caps_negated_then_positive = infer_requirement_capabilities(req_negated_then_positive)
assert_true(
    "salesforce_administration" in caps_negated_then_positive,
    "An independent genuine present-capability requirement following a "
    "negated/non-required mention must still infer salesforce_administration; "
    f"got {sorted(caps_negated_then_positive)}",
)
match_negated_then_positive = _match(
    "REQ_NEGATED_THEN_POSITIVE",
    "No Salesforce experience required; Salesforce administration required for this function",
)
assert_true(
    match_negated_then_positive["evaluation_path"] == "NONE_TRAP"
    and "salesforce_unsupported" in match_negated_then_positive["explanation"],
    "Mixed negated-then-genuine-positive requirement must still hit the "
    "salesforce_unsupported NONE trap via the independent second clause; "
    f"got evaluation_path={match_negated_then_positive['evaluation_path']!r} "
    f"explanation={match_negated_then_positive['explanation']!r}",
)

print("PASS H: mixed negated-then-genuine-positive Salesforce sentence still "
      "infers salesforce_administration from the independent second clause.")


# ======================================================================
# I. F1 repair -- an explicit present-capability phrase governing the
#    Salesforce mention ("Salesforce proficiency required", "hands-on
#    Salesforce experience required") must outrank unrelated
#    willingness/interest-to-learn language earlier in the SAME sentence.
#    Cursor-reported UNSAFE: these were false negatives (no capability
#    inferred, no NONE trap hit) because whole-sentence learning language
#    suppressed the mention even though it does not govern it.
# ======================================================================
F1_CASES = [
    (
        "REQ_F1_WILLING_ASANA_SF_PROFICIENCY",
        "Willingness to learn Asana, and Salesforce proficiency required",
    ),
    (
        "REQ_F1_INTEREST_HANDSON_SF",
        "Interest in learning new tools and hands-on Salesforce experience required",
    ),
]

for req_id, text in F1_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" in caps,
        f"{req_id} ({text!r}) must infer salesforce_administration from the "
        f"explicit present-capability phrase governing the mention; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] == "NONE_TRAP"
        and "salesforce_unsupported" in match["explanation"],
        f"{req_id} ({text!r}) must hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )
    assert_true(
        match["result"] == "NONE",
        f"{req_id} ({text!r}) must resolve NONE, got {match['result']}",
    )

print("PASS I: explicit present-capability phrasing governing the Salesforce "
      "mention outranks unrelated earlier learning language in the same sentence.")


# ======================================================================
# J. F2 repair -- explicit employer readiness-to-learn language about
#    Salesforce must NOT infer salesforce_administration, same as
#    willingness/desire/interest/eagerness-to-learn language.
# ======================================================================
F2_CASES = [
    ("REQ_F2_READY_TO_LEARN_SF", "Readiness to learn Salesforce"),
    ("REQ_F2_READY_TO_LEARN_ASANA_SF", "Readiness to learn Asana and Salesforce"),
]

for req_id, text in F2_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] != "NONE_TRAP"
        or "salesforce_unsupported" not in match["explanation"],
        f"{req_id} ({text!r}) must not hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )

print("PASS J: explicit readiness-to-learn Salesforce/SFDC language never infers "
      "salesforce_administration and never hits the Salesforce NONE trap.")


# ======================================================================
# K. F3 repair -- structured technology=['Salesforce'] fallback must not
#    fire when the employer's free text (which itself never names
#    Salesforce/SFDC) is learning-language or a generic negated/non-required
#    statement.
# ======================================================================
req_f3_learning = _req("REQ_F3_WILLING_ASANA_TECH_SF", "Willingness to learn Asana")
req_f3_learning["technology"] = ["Salesforce"]
caps_f3_learning = infer_requirement_capabilities(req_f3_learning)
assert_true(
    "salesforce_administration" not in caps_f3_learning,
    "Structured technology=['Salesforce'] must not fire when the employer's "
    "own text is willingness-to-learn language, even though that text never "
    f"names Salesforce/SFDC directly; got {sorted(caps_f3_learning)}",
)

req_f3_negated = _req("REQ_F3_NO_CRM_TECH_SF", "No CRM experience required")
req_f3_negated["technology"] = ["Salesforce"]
caps_f3_negated = infer_requirement_capabilities(req_f3_negated)
assert_true(
    "salesforce_administration" not in caps_f3_negated,
    "Structured technology=['Salesforce'] must not fire when the employer's "
    "own text is a generic negated/non-required statement, even though that "
    f"text never names Salesforce/SFDC directly; got {sorted(caps_f3_negated)}",
)

print("PASS K: structured technology fallback is withheld when the employer's "
      "own free text is learning-language or a generic negated/non-required "
      "statement, even without naming Salesforce/SFDC directly.")


# ======================================================================
# K2. STRUCTURED_FALLBACK_OVERBROAD_NEGATION_CORRECTION_V1 -- the F3
#    not-required guard must be scoped to CRM/platform-relevant negation,
#    not any "no ... required" statement. An unrelated negated requirement
#    ("No travel required", "No relocation required") must NOT withhold the
#    legacy tech-only Salesforce fallback, because the negation has nothing
#    to do with platform capability.
# ======================================================================
K2_CASES = [
    ("REQ_K2_NO_TRAVEL_TECH_SF", "No travel required"),
    ("REQ_K2_NO_RELOCATION_TECH_SF", "No relocation required"),
]

for req_id, text in K2_CASES:
    req_k2 = _req(req_id, text)
    req_k2["technology"] = ["Salesforce"]
    caps_k2 = infer_requirement_capabilities(req_k2)
    assert_true(
        "salesforce_administration" in caps_k2,
        f"{req_id} ({text!r}) with technology=['Salesforce'] must still "
        "preserve the legacy structured-tech fallback, because the negation "
        f"is unrelated to platform capability; got {sorted(caps_k2)}",
    )

print("PASS K2: unrelated negated requirements (travel, relocation) do not "
      "withhold the structured-tech Salesforce fallback.")


# ======================================================================
# L. Neutral tech-only fallback positive control -- re-affirms (alongside
#    section F) that the legacy structured-technology fallback still fires
#    for genuinely neutral employer text with no learning/negation language
#    and no textual Salesforce/SFDC mention at all.
# ======================================================================
req_l_neutral = _req("REQ_L_NEUTRAL_TECH_ONLY", "Proficient with common business software")
req_l_neutral["technology"] = ["Salesforce"]
caps_l_neutral = infer_requirement_capabilities(req_l_neutral)
assert_true(
    "salesforce_administration" in caps_l_neutral,
    "Neutral employer text plus structured technology=['Salesforce'] with no "
    "textual Salesforce/SFDC mention must still fall back to inferring "
    f"salesforce_administration; got {sorted(caps_l_neutral)}",
)

print("PASS L: neutral tech-only Salesforce fallback remains positive.")


# ======================================================================
# M. Present-capability controls -- additional genuine present-capability
#    phrasings (administration required, explicit "is required" variants)
#    continue to infer salesforce_administration, confirming the F1 local
#    present-capability override does not weaken these forms.
# ======================================================================
M_CASES = [
    ("REQ_M_SF_ADMIN_REQUIRED_IS", "Salesforce administration is required"),
    ("REQ_M_SF_EXPERIENCE_IS_REQUIRED", "Experience with Salesforce is required"),
]

for req_id, text in M_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" in caps,
        f"{req_id} ({text!r}) must infer salesforce_administration; got {sorted(caps)}",
    )

print("PASS M: genuine present-capability Salesforce phrasing controls unaffected.")

# ======================================================================
# N. CRM_PLATFORM_HALF_CONTRACT_FIX_V1 -- the F3 not-required guard must
#    also withhold the legacy tech-only Salesforce fallback for
#    platform-experience non-required language, mirroring the existing
#    CRM coverage. Cursor-reported HIGH finding: "No platform experience
#    required" / "Platform experience is not required" / "Prior platform
#    experience not required" with technology=['Salesforce'] wrongly
#    inferred salesforce_administration because the guard covered only
#    CRM forms.
# ======================================================================
N_CASES = [
    ("REQ_N_NO_PLATFORM_REQUIRED", "No platform experience required"),
    ("REQ_N_PLATFORM_NOT_REQUIRED", "Platform experience is not required"),
    ("REQ_N_PRIOR_PLATFORM_NOT_REQUIRED", "Prior platform experience not required"),
]

for req_id, text in N_CASES:
    req_n = _req(req_id, text)
    req_n["technology"] = ["Salesforce"]
    caps_n = infer_requirement_capabilities(req_n)
    assert_true(
        "salesforce_administration" not in caps_n,
        f"{req_id} ({text!r}) with technology=['Salesforce'] must not infer "
        f"salesforce_administration; got {sorted(caps_n)}",
    )

print("PASS N: platform-experience non-required language withholds the "
      "structured-tech Salesforce fallback, matching the existing CRM coverage.")


# ======================================================================
# N2. Re-affirm the unrelated-negation controls (travel, relocation) and
#    the CRM-not-required control still hold after extending the guard to
#    cover platform language, i.e. the fix did not broaden into a generic
#    "no ... required" match.
# ======================================================================
req_n2_crm = _req("REQ_N2_NO_CRM_TECH_SF", "No CRM experience required")
req_n2_crm["technology"] = ["Salesforce"]
caps_n2_crm = infer_requirement_capabilities(req_n2_crm)
assert_true(
    "salesforce_administration" not in caps_n2_crm,
    "No CRM experience required with technology=['Salesforce'] must still "
    f"withhold salesforce_administration; got {sorted(caps_n2_crm)}",
)

for req_id, text in K2_CASES:
    req_n2 = _req(req_id + "_RECHECK", text)
    req_n2["technology"] = ["Salesforce"]
    caps_n2 = infer_requirement_capabilities(req_n2)
    assert_true(
        "salesforce_administration" in caps_n2,
        f"{text!r} with technology=['Salesforce'] must still preserve the "
        f"legacy structured-tech fallback; got {sorted(caps_n2)}",
    )

print("PASS N2: unrelated-negation controls (travel, relocation) and existing "
      "CRM coverage remain intact after extending the guard to platform language.")


# ======================================================================
# O. SYNONYM_COMENTION_INTENT_REPAIR_V1 -- learning intent must not be lost
#    when Salesforce and its synonym SFDC are BOTH named in the same
#    willingness/readiness clause. Mechanically reproduced defect: the
#    second (SFDC or Salesforce) mention's narrow mention-scoped window did
#    not itself contain the learning-intent phrase, so it defaulted to a
#    bare positive even though it is plainly the same synonym-pair
#    coordinated under the SAME leading learning-intent clause, not an
#    independent present-capability requirement.
# ======================================================================
O_CASES = [
    ("REQ_O_WILLING_SF_AND_SFDC", "Willingness to learn Salesforce and SFDC"),
    ("REQ_O_WILLING_SFDC_AND_SF", "Willingness to learn SFDC and Salesforce"),
    ("REQ_O_READY_SF_OR_SFDC", "Readiness to learn Salesforce or SFDC"),
    (
        "REQ_O_WILLING_SF_ASANA_SFDC",
        "Willingness to learn Salesforce, Asana, and SFDC",
    ),
]

for req_id, text in O_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] != "NONE_TRAP"
        or "salesforce_unsupported" not in match["explanation"],
        f"{req_id} ({text!r}) must not hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )

print("PASS O: Salesforce/SFDC synonym co-mentions under shared learning-intent "
      "language never infer salesforce_administration.")


# ======================================================================
# O2. Positive control re-affirmed alongside O -- a genuine SECOND,
#    independent present-capability mention following willingness-to-learn
#    language must still infer salesforce_administration, confirming the
#    synonym-comention repair did not weaken this existing case.
# ======================================================================
req_o2 = _req(
    "REQ_O2_WILLING_SF_EXPERIENCE_SF_REQUIRED",
    "Willingness to learn Salesforce and experience with Salesforce required",
)
caps_o2 = infer_requirement_capabilities(req_o2)
assert_true(
    "salesforce_administration" in caps_o2,
    "Willingness to learn Salesforce and experience with Salesforce required "
    f"must still infer salesforce_administration; got {sorted(caps_o2)}",
)
match_o2 = _match(
    "REQ_O2_WILLING_SF_EXPERIENCE_SF_REQUIRED",
    "Willingness to learn Salesforce and experience with Salesforce required",
)
assert_true(
    match_o2["evaluation_path"] == "NONE_TRAP"
    and "salesforce_unsupported" in match_o2["explanation"],
    "Positive control must still hit the salesforce_unsupported NONE trap; "
    f"got evaluation_path={match_o2['evaluation_path']!r} "
    f"explanation={match_o2['explanation']!r}",
)

print("PASS O2: genuine second present-capability mention positive control "
      "unaffected by the synonym-comention repair.")


# ======================================================================
# P. DISJUNCTIVE_NEGATION_REPAIR_V1 -- disjunctive/slash Salesforce/SFDC
#    non-required grammar must be recognized. Mechanically reproduced
#    defect: the negated-requirement literal spans only matched a single
#    platform name directly followed by "experience ... required", so "No
#    Salesforce or SFDC experience required" / "No Salesforce/SFDC
#    experience required" fell through to a bare positive instead of being
#    recognized as negated.
# ======================================================================
P_CASES = [
    ("REQ_P_NO_SF_OR_SFDC_REQUIRED", "No Salesforce or SFDC experience required"),
    ("REQ_P_NO_SF_SLASH_SFDC_REQUIRED", "No Salesforce/SFDC experience required"),
]

for req_id, text in P_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] != "NONE_TRAP"
        or "salesforce_unsupported" not in match["explanation"],
        f"{req_id} ({text!r}) must not hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )

print("PASS P: disjunctive/slash Salesforce/SFDC non-required grammar never "
      "infers salesforce_administration.")


# ======================================================================
# P2. Single-name negatives and genuine positives re-affirmed alongside P --
#    the disjunctive-negation regex extension must not weaken the existing
#    single-name negated forms or genuine present-capability positives.
# ======================================================================
P2_NEGATIVE_CASES = [
    ("REQ_P2_NO_SF_REQUIRED_RECHECK", "No Salesforce experience required"),
    ("REQ_P2_NO_SFDC_REQUIRED_RECHECK", "No SFDC experience required"),
]

for req_id, text in P2_NEGATIVE_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )

P2_POSITIVE_CASES = [
    ("REQ_P2_SF_ADMIN_REQUIRED_RECHECK", "Salesforce administration required"),
    ("REQ_P2_SFDC_REQUIRED_RECHECK", "SFDC administration experience required"),
]

for req_id, text in P2_POSITIVE_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" in caps,
        f"{req_id} ({text!r}) must still infer salesforce_administration; got {sorted(caps)}",
    )

print("PASS P2: single-name negated and genuine present-capability Salesforce/"
      "SFDC controls unaffected by the disjunctive-negation repair.")



# ======================================================================
# Q. COMENTION_KEYWORD_ADJACENCY_REPAIR_V1 -- an unrelated governing word
#    that actually governs a DIFFERENT named item earlier in the
#    mention-scoped window must not be credited with freshly governing a
#    LATER Salesforce/SFDC synonym mention. Mechanically reproduced defect:
#    "experience"/"hands-on"/"administration" appearing anywhere in the
#    window (even governing "Asana", not the trailing SFDC mention) caused
#    the later mention to escape inherited learning suppression and default
#    to a bare positive.
# ======================================================================
Q_CASES = [
    (
        "REQ_Q_WILLING_SF_EXPERIENCE_ASANA_SFDC",
        "Willingness to learn Salesforce and experience with Asana and SFDC",
    ),
    (
        "REQ_Q_WILLING_SF_HANDSON_ASANA_SFDC",
        "Willingness to learn Salesforce and hands-on Asana and SFDC",
    ),
    (
        "REQ_Q_WILLING_SF_ADMIN_ASANA_SFDC",
        "Willingness to learn Salesforce and administration of Asana and SFDC",
    ),
]

for req_id, text in Q_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] != "NONE_TRAP"
        or "salesforce_unsupported" not in match["explanation"],
        f"{req_id} ({text!r}) must not hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )

print("PASS Q: unrelated governing words that govern a different named item "
      "earlier in the window do not escape inherited Salesforce/SFDC "
      "co-mention learning suppression.")


# ======================================================================
# R. NAND_CONJUNCTION_NEGATION_REPAIR_V1 -- natural `and` coordination
#    between the two synonym names in non-required grammar must be
#    recognized, alongside the existing single-name, `or`, and `/` forms.
#    Mechanically reproduced defect: "No Salesforce and SFDC experience
#    required" / "Prior Salesforce and SFDC experience not required" fell
#    through to a bare positive because the disjunct connector group only
#    accepted "/" and "or".
# ======================================================================
R_CASES = [
    ("REQ_R_NO_SF_AND_SFDC_REQUIRED", "No Salesforce and SFDC experience required"),
    (
        "REQ_R_PRIOR_SF_AND_SFDC_NOT_REQUIRED",
        "Prior Salesforce and SFDC experience not required",
    ),
]

for req_id, text in R_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" not in caps,
        f"{req_id} ({text!r}) must not infer salesforce_administration; got {sorted(caps)}",
    )
    match = _match(req_id, text)
    assert_true(
        match["evaluation_path"] != "NONE_TRAP"
        or "salesforce_unsupported" not in match["explanation"],
        f"{req_id} ({text!r}) must not hit the salesforce_unsupported NONE trap; "
        f"got evaluation_path={match['evaluation_path']!r} explanation={match['explanation']!r}",
    )

print("PASS R: `and`-coordinated Salesforce/SFDC non-required grammar never "
      "infers salesforce_administration.")


# ======================================================================
# R2. Positive controls re-affirmed alongside Q and R -- the co-mention
#    adjacency repair and the `and`-conjunction negation extension must not
#    weaken existing genuine positives.
# ======================================================================
R2_POSITIVE_CASES = [
    ("REQ_R2_SF_ADMIN_REQUIRED", "Salesforce administration required"),
    ("REQ_R2_SF_EXPERIENCE_REQUIRED", "experience with Salesforce required"),
    ("REQ_R2_SF_PROFICIENCY_REQUIRED", "Salesforce proficiency required"),
    ("REQ_R2_HANDSON_SF_REQUIRED", "hands-on Salesforce experience required"),
    (
        "REQ_R2_WILLING_SF_SFDC_PROFICIENCY_REQUIRED",
        "Willingness to learn Salesforce and SFDC proficiency required",
    ),
    (
        "REQ_R2_WILLING_SF_EXPERIENCE_SFDC_REQUIRED",
        "Willingness to learn Salesforce and experience with SFDC required",
    ),
    (
        "REQ_R2_NO_SF_REQUIRED_THEN_SFDC_PROFICIENCY_REQUIRED",
        "No Salesforce experience required; SFDC proficiency required",
    ),
]

for req_id, text in R2_POSITIVE_CASES:
    caps = infer_requirement_capabilities(_req(req_id, text))
    assert_true(
        "salesforce_administration" in caps,
        f"{req_id} ({text!r}) must still infer salesforce_administration; got {sorted(caps)}",
    )

req_r2_no_travel = _req("REQ_R2_NO_TRAVEL_REQUIRED_TECH_SF", "No travel required")
req_r2_no_travel["technology"] = ["Salesforce"]
caps_r2_no_travel = infer_requirement_capabilities(req_r2_no_travel)
assert_true(
    "salesforce_administration" in caps_r2_no_travel,
    "No travel required with technology=['Salesforce'] must still infer "
    f"salesforce_administration; got {sorted(caps_r2_no_travel)}",
)

req_r2_no_relocation = _req(
    "REQ_R2_NO_RELOCATION_REQUIRED_TECH_SF", "No relocation required"
)
req_r2_no_relocation["technology"] = ["Salesforce"]
caps_r2_no_relocation = infer_requirement_capabilities(req_r2_no_relocation)
assert_true(
    "salesforce_administration" in caps_r2_no_relocation,
    "No relocation required with technology=['Salesforce'] must still infer "
    f"salesforce_administration; got {sorted(caps_r2_no_relocation)}",
)

req_r2_neutral_tech = _req(
    "REQ_R2_NEUTRAL_TEXT_TECH_SF", "Familiarity with common office tools"
)
req_r2_neutral_tech["technology"] = ["Salesforce"]
caps_r2_neutral_tech = infer_requirement_capabilities(req_r2_neutral_tech)
assert_true(
    "salesforce_administration" in caps_r2_neutral_tech,
    "Neutral text with technology=['Salesforce'] must still infer "
    f"salesforce_administration; got {sorted(caps_r2_neutral_tech)}",
)

print("PASS R2: genuine positive controls (including structured-technology "
      "fallback controls) unaffected by the co-mention adjacency repair and "
      "the `and`-conjunction negation extension.")


# ======================================================================
# S. CRM_PLATFORM_COORDINATION_REPAIR_V1 -- bounded coordinated CRM/platform
#    category non-required grammar must withhold the structured-tech
#    Salesforce fallback, mirroring the Salesforce/SFDC synonym-pair
#    disjunctive/conjunctive negation repairs (P/R). Mechanically reproduced
#    defect: with free text "No CRM or platform experience required" and
#    structured technology=['Salesforce'], infer_requirement_capabilities
#    still returned salesforce_administration because the CRM/platform
#    not-required guard only recognized a single CRM/platform name, not the
#    coordinated category form.
# ======================================================================
S_CASES = [
    ("REQ_S_NO_CRM_OR_PLATFORM_REQUIRED", "No CRM or platform experience required"),
    ("REQ_S_NO_CRM_AND_PLATFORM_REQUIRED", "No CRM and platform experience required"),
    ("REQ_S_NO_CRM_SLASH_PLATFORM_REQUIRED", "No CRM/platform experience required"),
    (
        "REQ_S_PRIOR_CRM_OR_PLATFORM_NOT_REQUIRED",
        "Prior CRM or platform experience not required",
    ),
    (
        "REQ_S_PRIOR_CRM_AND_PLATFORM_NOT_REQUIRED",
        "Prior CRM and platform experience not required",
    ),
]

for req_id, text in S_CASES:
    req_s = _req(req_id, text)
    req_s["technology"] = ["Salesforce"]
    caps_s = infer_requirement_capabilities(req_s)
    assert_true(
        "salesforce_administration" not in caps_s,
        f"{req_id} ({text!r}) with technology=['Salesforce'] must not infer "
        f"salesforce_administration; got {sorted(caps_s)}",
    )

print("PASS S: coordinated CRM/platform non-required grammar withholds the "
      "structured-tech Salesforce fallback.")


# ======================================================================
# S2. Positive controls re-affirmed alongside S -- the coordinated
#    CRM/platform repair must remain CRM/platform-specific and must not
#    broaden into a generic "no ... required" match on unrelated subjects,
#    and existing single-name CRM/platform non-required forms and the
#    neutral tech-only fallback must remain unaffected.
# ======================================================================
S2_POSITIVE_CASES = [
    ("REQ_S2_NO_TRAVEL_REQUIRED_TECH_SF", "No travel required"),
    ("REQ_S2_NO_RELOCATION_REQUIRED_TECH_SF", "No relocation required"),
    (
        "REQ_S2_PROFICIENT_COMMON_BUSINESS_SOFTWARE_TECH_SF",
        "Proficient with common business software",
    ),
]

for req_id, text in S2_POSITIVE_CASES:
    req_s2 = _req(req_id, text)
    req_s2["technology"] = ["Salesforce"]
    caps_s2 = infer_requirement_capabilities(req_s2)
    assert_true(
        "salesforce_administration" in caps_s2,
        f"{req_id} ({text!r}) with technology=['Salesforce'] must still "
        f"preserve the legacy structured-tech fallback; got {sorted(caps_s2)}",
    )

S2_NEGATIVE_RECHECK_CASES = [
    ("REQ_S2_NO_CRM_REQUIRED_RECHECK", "No CRM experience required"),
    ("REQ_S2_NO_PLATFORM_REQUIRED_RECHECK", "No platform experience required"),
    (
        "REQ_S2_PRIOR_PLATFORM_NOT_REQUIRED_RECHECK",
        "Prior platform experience not required",
    ),
]

for req_id, text in S2_NEGATIVE_RECHECK_CASES:
    req_s2n = _req(req_id, text)
    req_s2n["technology"] = ["Salesforce"]
    caps_s2n = infer_requirement_capabilities(req_s2n)
    assert_true(
        "salesforce_administration" not in caps_s2n,
        f"{req_id} ({text!r}) with technology=['Salesforce'] must still "
        f"withhold salesforce_administration; got {sorted(caps_s2n)}",
    )

print("PASS S2: positive controls, unrelated-negation controls, and existing "
      "single-name CRM/platform non-required forms remain unaffected by the "
      "coordinated CRM/platform repair.")


print("ALL PASS: NAMED_PLATFORM_LEARNING_READINESS_V1 regression coverage green.")
