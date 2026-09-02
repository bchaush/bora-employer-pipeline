"""Regression tests for ACCREDITED_INSTITUTION_QUALIFIER_SEMANTICS_V1.

Real MBTA requirement (CASE_D/CASE_E, both Minimum Qualifications text):
"Bachelor's degree from an accredited institution." currently infers only
{bachelors_degree_credential} -- infer_requirement_capabilities() silently
drops the explicit "from an accredited institution" qualifier entirely.

Repository truth:
- CLAIM_EDU_UNWE_001 (the only candidate degree claim, human_approval=false)
  supports only the bare credential fact; its forbidden_contexts explicitly
  include "institutional ranking or accreditation claim" and
  "credential evaluation"; EDU_UNWE_IDENTITY_001 explicitly documents that
  accreditation is not established.
- No current Claim represents institutional accreditation at all.

This milestone adds one new, narrowly-scoped requirement-side capability,
institutional_accreditation_qualifier, following the exact locality-only
precedent already established by REQUIREMENT_QUALIFIER_SEMANTICS_V1's Q-1
(institutional_quality_qualifier): the credential word must be directly,
immediately followed by "from" (no arbitrary filler window -- Cursor's
FALSE_CREDENTIAL_SOURCE_LINKAGE finding on Q-1 proved any such window can
be filled by real intervening noun phrases that are not the credential's
source), which must in turn be immediately followed by "accredited" and an
institution/university/college/school noun. Emitted ADDITIVELY alongside
bachelors_degree_credential, never instead of it. Assigned to ZERO Claims.

SOURCE-CONSISTENCY SAFETY: the real MBTA direct posting's own supplemental-
questionnaire Bachelor+3yr branch ("A bachelor's degree with three (3) or
more years...") does NOT repeat "accredited institution." This milestone
does not harmonize, infer across, or resolve that discrepancy -- the
questionnaire-branch text is tested separately below and is proven to NOT
carry the new qualifier, exactly as its own wording dictates. No
qualification-branch semantics are touched.

Exercises real production code (requirement_match.py, job_analysis.py) --
no logic is duplicated here.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from job_analysis import analyze_job  # noqa: E402
from requirement_match import (  # noqa: E402
    _CLAIM_CAPABILITIES,
    infer_requirement_capabilities,
    load_reusable_claims,
    match_requirement,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


NEW_TAG = "institutional_accreditation_qualifier"
CREDENTIAL_TAG = "bachelors_degree_credential"
MBTA_DEGREE_TEXT = "Bachelor's degree from an accredited institution"

ev_result = validate_evidence_repository()
assert_true(ev_result["valid"] is True, "evidence repository must be valid")
cl_result = validate_claim_repository()
assert_true(cl_result["valid"] is True, "claim repository must be valid")
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = cl_result["index"]


def _req(text: str) -> dict:
    return {
        "requirement_id": "REQ_TEST",
        "text": text,
        "source_text": text,
        "domain": None,
        "category": None,
        "technology": [],
        "relevance": "HIGH",
        "importance": "MANDATORY",
    }


def _match(text: str, reusable_claims) -> dict:
    return match_requirement(
        job_id="JOB_X",
        requirement=_req(text),
        reusable_claims=reusable_claims,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )


REUSABLE_ACTUAL = load_reusable_claims(CLAIM_INDEX, EVIDENCE_INDEX)


# ======================================================================
# A. Pre-fix reproduction control -- the real MBTA requirement must
#    infer BOTH tags additively.
# ======================================================================
mbta_caps = infer_requirement_capabilities(_req(MBTA_DEGREE_TEXT))
assert_true(
    {CREDENTIAL_TAG, NEW_TAG}.issubset(mbta_caps),
    f"real MBTA degree text must infer both {CREDENTIAL_TAG} and {NEW_TAG}, got {sorted(mbta_caps)}",
)
print("PASS A: real MBTA degree requirement infers bachelors_degree_credential and institutional_accreditation_qualifier additively.")


# ======================================================================
# B. Required positives.
# ======================================================================
positives = (
    "Bachelor's degree from an accredited institution",
    "degree from an accredited university",
    "associate's degree from an accredited college",
    "Bachelor's degree from an accredited institution.",
)
for text in positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(NEW_TAG in caps, f"{text!r} must infer {NEW_TAG}")
print("PASS B: all required positive credential-from-accredited-institution phrasings infer the new capability.")


# ======================================================================
# C. Required negatives -- no proximity matching. The qualifier must
#    never fire merely because "accredited" co-occurs somewhere in the
#    clause; it requires the direct credential-word -> from -> accredited
#    -> institution/university/college construction, immediately adjacent.
# ======================================================================
negatives = (
    "degree required for applicants from an accredited institution",
    "experience working with accredited institutions",
    "accredited educational program",
    "accreditation mentioned elsewhere in the clause",
    "accredited institution",
    # Known accepted locality-only limitation, mirroring Q-1's own
    # documented comma-before-"from" limitation.
    "Bachelor's degree, from an accredited institution",
)
for text in negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        NEW_TAG not in caps,
        f"{text!r} must NOT infer {NEW_TAG} -- proximity/co-occurrence of 'accredited' is not the same as the credential itself being described as from an accredited institution",
    )
print("PASS C: adversarial negatives (proximity co-occurrence, unrelated 'accredited' mentions, comma-locality limitation) correctly do not infer the new capability.")


# ======================================================================
# C2. ACCREDITED_INSTITUTION_QUALIFIER_TEST_COMPLETION_V1 (Cursor
#    adversarial review -- no production defect found; test-only
#    completion). Explicit, table-driven regression coverage for three
#    additional real-shaped negative constructions where "accredited"
#    co-occurs with the credential but is not describing the credential
#    itself as coming from an accredited institution.
# ======================================================================
c2_negatives = (
    ("Bachelor's degree required for candidates from an accredited institution", "credential is not itself described as from the institution -- 'candidates' are"),
    ("Bachelor's degree and experience working with accredited institutions", "'accredited institutions' modifies 'experience working with', not the degree"),
    ("Degree preferred; candidates from accredited universities", "clause break before 'candidates from accredited universities' -- not the degree's source"),
)
for text, reason in c2_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        NEW_TAG not in caps,
        f"{text!r} must NOT infer {NEW_TAG} -- {reason}",
    )
print("PASS C2: additional real-shaped negative constructions (candidates-from, experience-working-with, clause-break-before-candidates) correctly do not infer the new capability.")


# ======================================================================
# D. Additive semantics -- the credential tag is unaffected; both
#    co-exist on the same requirement.
# ======================================================================
assert_true(
    CREDENTIAL_TAG in mbta_caps,
    "bachelors_degree_credential must remain inferred alongside the new qualifier (additive, not replacing)",
)
plain_degree_caps = infer_requirement_capabilities(_req("Bachelor's degree"))
assert_true(
    CREDENTIAL_TAG in plain_degree_caps and NEW_TAG not in plain_degree_caps,
    f"a plain 'Bachelor's degree' requirement (no accreditation language) must infer only {CREDENTIAL_TAG}, got {sorted(plain_degree_caps)}",
)
print("PASS D: additive semantics confirmed -- the new qualifier never replaces bachelors_degree_credential, and a plain degree requirement is unaffected.")


# ======================================================================
# E. Candidate-side safety -- no Claim (including CLAIM_EDU_UNWE_001) is
#    mapped to the new qualifier. No Claim or Evidence file is touched by
#    this milestone.
# ======================================================================
for claim_id, caps_map in _CLAIM_CAPABILITIES.items():
    assert_true(
        NEW_TAG not in caps_map,
        f"{claim_id} must NOT carry {NEW_TAG} -- no current approved evidence establishes institutional accreditation; CLAIM_EDU_UNWE_001's own forbidden_contexts explicitly exclude this",
    )
assert_true(
    CLAIM_INDEX["CLAIM_EDU_UNWE_001"]["human_approval"] is False,
    "CLAIM_EDU_UNWE_001 must remain human_approval=false on disk, untouched by this milestone",
)
print("PASS E: no Claim (including CLAIM_EDU_UNWE_001) carries the new qualifier; CLAIM_EDU_UNWE_001 remains unapproved and unmodified.")


# ======================================================================
# F. Isolated matcher result -- real MBTA degree text, unapproved current
#    Claim state. Must remain NONE (no reusable claim at all today).
# ======================================================================
mbta_match_current = _match(MBTA_DEGREE_TEXT, REUSABLE_ACTUAL)
assert_true(
    mbta_match_current["result"] == "NONE",
    f"real MBTA degree text with CURRENT (unapproved) claim state must remain NONE, got {mbta_match_current['result']}",
)
print("PASS F: real MBTA degree requirement remains NONE under current (unapproved) claim state -- unaffected by this milestone.")


# ======================================================================
# G. In-memory-only counterfactual (never touches disk) -- if
#    CLAIM_EDU_UNWE_001 were hypothetically approved, the requirement
#    must resolve PARTIAL (credential genuinely supported, accreditation
#    qualifier genuinely unsupported), never SUPPORTED/STRONG (would
#    overclaim accreditation) and never NONE (would understate the real
#    partial signal) -- mirroring Q-1's own established PARTIAL pattern.
# ======================================================================
claim_index_sim = copy.deepcopy(CLAIM_INDEX)
claim_index_sim["CLAIM_EDU_UNWE_001"]["human_approval"] = True
reusable_sim = load_reusable_claims(claim_index_sim, EVIDENCE_INDEX)

mbta_match_sim = _match(MBTA_DEGREE_TEXT, reusable_sim)
assert_true(
    mbta_match_sim["result"] == "PARTIAL",
    f"real MBTA degree text with a hypothetically-approved bare credential claim must resolve PARTIAL (not SUPPORTED/STRONG -- accreditation remains unestablished), got {mbta_match_sim['result']}",
)
assert_true(
    mbta_match_sim.get("claim_ids") == ["CLAIM_EDU_UNWE_001"],
    f"PARTIAL provenance must cite CLAIM_EDU_UNWE_001, got {mbta_match_sim.get('claim_ids')}",
)
assert_true(
    NEW_TAG in (mbta_match_sim.get("transfer_note") or "") or NEW_TAG in mbta_match_sim.get("explanation", ""),
    f"PARTIAL result must surface the missing {NEW_TAG}, got transfer_note={mbta_match_sim.get('transfer_note')!r}",
)

cl_after = validate_claim_repository()
assert_true(
    cl_after["index"]["CLAIM_EDU_UNWE_001"]["human_approval"] is False,
    "real claim repository on disk must remain unaffected by the in-memory simulation",
)
print("PASS G: hypothetical (in-memory-only) bare-credential approval resolves the real MBTA degree text to PARTIAL, not SUPPORTED/STRONG; disk state unaffected.")


# ======================================================================
# H. SOURCE-CONSISTENCY SAFETY -- the real MBTA supplemental-
#    questionnaire Bachelor+3yr branch does NOT repeat "accredited
#    institution." This is a genuine, preserved source discrepancy, not
#    harmonized or inferred across in this milestone. The questionnaire
#    text must NOT carry the new qualifier, exactly as its own wording
#    dictates -- no inference that omission cancels or confirms
#    accreditation either way.
# ======================================================================
questionnaire_bachelor_branch_text = (
    "A bachelor's degree with three (3) or more years of experience in "
    "system analysis, including enterprise application design, "
    "configuration / development, implementation, and support."
)
questionnaire_caps = infer_requirement_capabilities(_req(questionnaire_bachelor_branch_text))
assert_true(
    NEW_TAG not in questionnaire_caps,
    f"the questionnaire Bachelor+3yr branch text (no 'accredited institution' wording) must NOT infer {NEW_TAG} -- the source discrepancy between Minimum Qualifications and the questionnaire is preserved, not harmonized",
)
print("PASS H: the real MBTA questionnaire Bachelor+3yr branch (which omits 'accredited institution') correctly does not infer the new qualifier -- the source discrepancy is preserved, not resolved either direction.")


# ======================================================================
# I. Real MBTA fixture regression -- both fixtures' degree requirement
#    and final decision are unaffected by this milestone (current
#    approved Claim state unchanged).
# ======================================================================
def _load_real_job_input(fixture_dir_name: str) -> dict:
    fixture_dir = ROOT / "fixtures" / "jobs" / fixture_dir_name
    job = json.loads((fixture_dir / "job.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_input = dict(job)
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    return job_input


# DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1 (post-dates this
# milestone): REQ_D/E_SYS_ANALYSIS_EXP are domain-qualified duration
# requirements with empty inferred capabilities and no longer
# independently hard-block (they resolve UNKNOWN, not NONE); only the
# genuine REQ_D/E_DEGREE blocker remains. This assertion is about THIS
# milestone (accredited-institution-qualifier semantics) not changing the
# blocker set any further -- updated to the current adjudicated baseline.
for fixture_name, req_id, expected_blockers in (
    ("CASE_D_MBTA_DIRECT_APPLICATION_ANALYST", "REQ_D_DEGREE", ["REQ_D_DEGREE"]),
    ("CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST", "REQ_E_DEGREE", ["REQ_E_DEGREE"]),
):
    result = analyze_job(_load_real_job_input(fixture_name))
    assert_true(result["valid"] is True, f"{fixture_name} analysis must be valid: {result.get('errors')}")
    analysis = result["analysis"]
    degree_match = next(m for m in analysis["evidence_matches"] if m["requirement_id"] == req_id)
    assert_true(
        degree_match["result"] == "NONE",
        f"{fixture_name} {req_id} must remain NONE (current approved Claim state unchanged), got {degree_match['result']}",
    )
    assert_true(
        analysis["decision"] == "REJECT",
        f"{fixture_name} final decision must remain REJECT, got {analysis['decision']}",
    )
    actual_blockers = sorted(b.rsplit(": ", 1)[-1] for b in result["hard_blockers"])
    assert_true(
        actual_blockers == sorted(expected_blockers),
        f"{fixture_name} hard blockers must be exactly {sorted(expected_blockers)} (this milestone must not make any requirement stronger or weaker), got {actual_blockers}",
    )
    req_ids_with_new_tag_requirement = [
        r["requirement_id"] for r in analysis["requirements"] if r["requirement_id"] == req_id
    ]
    assert_true(len(req_ids_with_new_tag_requirement) == 1, f"{fixture_name} must still have exactly one {req_id} row")
print("PASS I: both real MBTA fixtures' degree requirements remain NONE and their final decisions remain REJECT, unaffected by this milestone.")

print("ALL accredited_institution_qualifier_semantics_v1_test CHECKS PASSED")
