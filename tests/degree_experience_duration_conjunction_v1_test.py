"""Regression tests for the degree_experience_duration_conjunction capability
(final, corrected form of EXPERIENCE_DURATION_QUALIFIER_VISIBILITY_V1).

Frozen MIT's REQ_C_DEGREE_EXPERIENCE ("Bachelor's degree plus a minimum of
seven years of experience OR a master's degree and minimum two years of
experience OR equivalent") previously inferred only
{bachelors_degree_credential} -- the "minimum of seven years" duration
condition conjoined to it was entirely invisible, so approving only a bare
bachelor's-degree claim (zero years-of-experience evidence) made the
existing subset-check see req_caps already equal to claim_caps and report
SUPPORTED -- a real false-SUPPORTED defect.

BOUNDED CORRECTION (independent Cursor review, OR_DISJUNCT_FALSE_PARTIAL): a
first version of the fix matched "minimum/at least/N+ years of experience"
ANYWHERE in the requirement text, with no connection to the credential --
which over-fired on the mirror-image case, where a duration condition is a
genuinely separate, independently-sufficient OR-alternative (e.g.
"Bachelor's degree OR 5+ years of experience"), demoting an otherwise fully
satisfied degree branch to a false PARTIAL. A sentence-wide "does AND/plus
appear anywhere" gate would still be unsafe -- a sentence can contain both
OR and AND while the duration stays inside only one alternative branch. The
capability was renamed experience_duration_qualifier ->
degree_experience_duration_conjunction and the pattern now requires the
credential word itself to be directly, locally followed by "and"/"plus"
(never "or", never mere co-occurrence) before the duration phrase.

Exercises real production code (requirement_match.py, job_analysis.py,
application_clause_match.py) against the actual frozen MIT fixture and
synthetic adversarial probes -- no regex logic is duplicated here. Approval
is simulated in-memory only; the real claim repository on disk is never
touched.
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

from application_clause_match import match_clause  # noqa: E402
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


FIXTURE_A = ROOT / "fixtures" / "jobs" / "CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST"
FIXTURE_C = ROOT / "fixtures" / "jobs" / "CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST"
TAG = "degree_experience_duration_conjunction"


def _load_job_input(fixture_dir: Path) -> dict:
    job = json.loads((fixture_dir / "job.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_input = dict(job)
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    return job_input


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


ev_result = validate_evidence_repository()
assert_true(ev_result["valid"] is True, "evidence repository must be valid")
cl_result = validate_claim_repository()
assert_true(cl_result["valid"] is True, "claim repository must be valid")
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = cl_result["index"]


# ======================================================================
# A. Frozen MIT REQ_C_DEGREE_EXPERIENCE through the real production
#    analyze_job() path: capability inference now includes
#    degree_experience_duration_conjunction in addition to
#    bachelors_degree_credential. Real (unapproved-claim) production
#    result remains NONE, unchanged.
# ======================================================================
job_input_c = _load_job_input(FIXTURE_C)
structured_c = job_input_c["structured_extraction"]
req_degree_exp = next(r for r in structured_c["requirements"] if r["requirement_id"] == "REQ_C_DEGREE_EXPERIENCE")
caps = infer_requirement_capabilities(req_degree_exp)
assert_true(
    caps == frozenset({"bachelors_degree_credential", TAG}),
    f"REQ_C_DEGREE_EXPERIENCE must infer both tags additively; got {sorted(caps)}",
)

result_real = analyze_job(job_input_c)
assert_true(result_real["valid"] is True, f"MIT analysis must be valid: {result_real['errors']}")
match_real = next(m for m in result_real["analysis"]["evidence_matches"] if m["requirement_id"] == "REQ_C_DEGREE_EXPERIENCE")
assert_true(
    match_real["result"] == "NONE",
    f"real (unapproved-claim) production result must remain NONE, got {match_real['result']}",
)
print("PASS A: frozen MIT REQ_C_DEGREE_EXPERIENCE infers bachelors_degree_credential + degree_experience_duration_conjunction additively; real production result remains NONE (claims unapproved).")


# ======================================================================
# B. MIT local-conjunction false-SUPPORTED prevention (in-memory-only
#    claim approval, disk never touched): approving only the bare
#    bachelor's-degree claim (zero years-of-experience evidence) must
#    resolve PARTIAL, not the previously-fabricated SUPPORTED.
# ======================================================================
claim_index_sim = copy.deepcopy(CLAIM_INDEX)
claim_index_sim["CLAIM_EDU_UNWE_001"]["human_approval"] = True
result_sim = analyze_job(job_input_c, claim_index=claim_index_sim, evidence_index=EVIDENCE_INDEX)
assert_true(result_sim["valid"] is True, f"MIT hypothetical analysis must be valid: {result_sim['errors']}")
match_sim = next(m for m in result_sim["analysis"]["evidence_matches"] if m["requirement_id"] == "REQ_C_DEGREE_EXPERIENCE")
assert_true(
    match_sim["result"] == "PARTIAL",
    f"hypothetical bachelor's-only approval must resolve PARTIAL (not fabricated SUPPORTED), got {match_sim['result']}",
)
assert_true(TAG in match_sim["explanation"], f"explanation must name the missing {TAG} capability")
assert_true(
    "lacks" not in match_sim["explanation"].lower() and "does not meet" not in match_sim["explanation"].lower(),
    "explanation must not fabricate a negative claim about candidate years -- duration remains non-canonical",
)
explanation_lower = match_sim["explanation"].lower()
assert_true(
    not any(
        phrase in explanation_lower
        for phrase in ("master's branch", "master's path", "master branch failed", "master's failed")
    ),
    "explanation must not evaluatively claim the Master's OR-branch failed -- branch selection remains unsolved/unclaimed "
    "(the word 'master's' legitimately appears only as verbatim echoed raw source text, e.g. raw='...')",
)
hypothetical_blockers = result_sim["hard_blockers"]
assert_true(
    not any("REQ_C_DEGREE_EXPERIENCE" in b for b in hypothetical_blockers),
    f"PARTIAL must not create a new hard blocker (Gate 0 fires only on exact NONE); got {hypothetical_blockers}",
)
assert_true(
    result_sim["analysis"]["lane"] == "LANE_0_REJECT" and result_sim["analysis"]["decision"] == "REJECT",
    "MIT overall routing must remain LANE_0_REJECT/REJECT in the hypothetical scenario (other independent blockers remain)",
)

cl_after = validate_claim_repository()
assert_true(
    cl_after["index"]["CLAIM_EDU_UNWE_001"]["human_approval"] is False,
    "real claim repository on disk must remain unaffected by the in-memory simulation",
)
print("PASS B: hypothetical bachelor's-only claim approval on the frozen MIT requirement now resolves PARTIAL (not fabricated SUPPORTED); disk state unaffected.")


# ======================================================================
# C. Conjunctive positives -- credential directly, locally followed by
#    "and"/"plus" then a duration phrase.
# ======================================================================
conjunctive_positives = (
    "Bachelor's degree plus a minimum of seven years of experience OR a master's degree and minimum two years of experience OR equivalent",
    "Bachelor's degree AND minimum 5 years of experience.",
    "Bachelor's degree plus a minimum of seven years of experience.",
)
for text in conjunctive_positives:
    conj_caps = infer_requirement_capabilities(_req(text))
    assert_true(TAG in conj_caps, f"{text!r} must infer {TAG}")
print("PASS C: frozen MIT text and narrow 'degree AND/plus duration' constructions all emit degree_experience_duration_conjunction.")


# ======================================================================
# D. OR / mixed-logic negatives (Cursor OR_DISJUNCT_FALSE_PARTIAL,
#    synthetic adversarial probes -- NOT real fixtures) -- a duration
#    condition that is a genuinely separate OR-alternative, not
#    conjoined to the credential, must never trigger the tag. This
#    includes a sentence containing BOTH an unrelated OR and an
#    unrelated trailing AND, proving sentence-wide conjunction
#    detection was correctly rejected in favor of local anchoring.
# ======================================================================
or_negatives = (
    "Bachelor's degree OR 5+ years of experience.",
    "Bachelor's degree or minimum five years of experience.",
    "Bachelor's degree OR 5+ years of experience, AND strong Excel skills.",
    "Bachelor's degree or 5+ years of experience and strong communication.",
    "Bachelor's degree or equivalent professional experience.",
    "Master's degree OR 3+ years of experience.",
    # Hardening: an unrelated AND/PLUS occurring AFTER an OR-disjoint
    # experience branch (attached to a trailing, unrelated skill/tool
    # clause -- Excel, communication, SQL, Python -- not to the
    # degree-vs-experience alternative) must not cause the tag to emit.
    # These lock in the already-verified local-anchoring behavior against
    # a slightly different sentence shape than the original OR-negative
    # set above (synthetic adversarial probes -- NOT real fixtures).
    "Bachelor's degree OR 5+ years of experience plus strong Excel skills.",
    "Bachelor's degree OR 5+ years of experience, plus strong communication skills.",
    "Bachelor's degree OR 5+ years of experience AND SQL proficiency.",
    "Bachelor's degree OR 5+ years of experience plus Python knowledge.",
)
for text in or_negatives:
    or_caps = infer_requirement_capabilities(_req(text))
    assert_true(
        TAG not in or_caps,
        f"{text!r} (synthetic adversarial probe) must NOT infer {TAG} -- duration is a separate OR-alternative, not conjoined to the credential",
    )
print("PASS D: synthetic OR-disjoint adversarial probes (including sentences containing an unrelated trailing AND/PLUS attached to a different skill clause) never trigger degree_experience_duration_conjunction.")


# ======================================================================
# E. OR mirror false-PARTIAL prevention: with a bachelor's claim
#    approved, a synthetic OR-disjoint "degree OR N years" requirement
#    must resolve SUPPORTED (the degree branch is fully, independently
#    satisfied), not falsely demoted to PARTIAL by an unrelated
#    duration alternative. This proves only that the visibility guard
#    does not make the flat model worse on the mirror-image case -- it
#    does not prove general OR semantics are solved.
# ======================================================================
reusable_sim = load_reusable_claims(claim_index_sim, EVIDENCE_INDEX)
or_probe_req = _req("Bachelor's degree OR 5+ years of experience.")
match_or = match_requirement(
    job_id="JOB_OR_MIRROR_TEST",
    requirement=or_probe_req,
    reusable_claims=reusable_sim,
    evidence_index=EVIDENCE_INDEX,
    match_index=0,
)
assert_true(
    match_or["result"] == "SUPPORTED",
    f"synthetic OR-disjoint probe with an approved bachelor's claim must resolve SUPPORTED (not falsely demoted to PARTIAL), got {match_or['result']}",
)
print("PASS E: synthetic OR-disjoint probe ('Bachelor's degree OR 5+ years of experience') with an approved bachelor's claim resolves SUPPORTED, not falsely demoted to PARTIAL.")


# ======================================================================
# F. Non-experience-duration negatives -- numbers that are not
#    years-of-experience conditions must never trigger the tag, even
#    when conjoined to a credential word by coincidence of proximity.
# ======================================================================
duration_negatives = (
    "managed seven projects",
    "supported two systems",
    "minimum two certifications",
    "seven years since graduation",
    "$5+ million budget",
    "five years of data retention",
)
for text in duration_negatives:
    caps_neg = infer_requirement_capabilities(_req(text))
    assert_true(TAG not in caps_neg, f"{text!r} must NOT trigger {TAG} -- not a years-of-experience condition")
print("PASS F: non-experience numeric phrases (project counts, certifications, retention periods, budgets, time-since-graduation) never trigger degree_experience_duration_conjunction.")


# ======================================================================
# G. Non-overlap with EXPERIENCE_RANGE_SEMANTICS_V1's generic "years of
#    work experience" phrasing and with SAP-years domain phrasing.
#    experience_range.py itself is untouched; generic range routing is
#    reconfirmed unaffected.
# ======================================================================
from experience_range import is_generic_experience_range_requirement  # noqa: E402

experience_range_negatives = (
    "0-2 years of work experience",
    "0–2 years of work experience",
    "1-3 years of work experience",
    "2+ years of work experience",
    "at least 3 years of work experience",
    "up to 2 years of work experience",
    "no more than 3 years of work experience",
    "5+ years of SAP FI/CO experience",
)
for text in experience_range_negatives:
    caps_neg = infer_requirement_capabilities(_req(text))
    assert_true(TAG not in caps_neg, f"{text!r} must NOT trigger {TAG} -- owned by EXPERIENCE_RANGE_SEMANTICS_V1/SAP protection")

req_generic_range = _req("0-2 years of work experience")
generic_caps = infer_requirement_capabilities(req_generic_range)
assert_true(
    generic_caps == frozenset(),
    f"'0-2 years of work experience' must still infer zero capability tags (unaffected), got {sorted(generic_caps)}",
)
assert_true(
    is_generic_experience_range_requirement(req_generic_range, inferred_capabilities=generic_caps) is True,
    "'0-2 years of work experience' must still route to the generic experience-range evaluator, unaffected by this milestone",
)
print("PASS G: zero overlap with EXPERIENCE_RANGE_SEMANTICS_V1 generic phrasing or SAP-years phrasing; generic experience-range routing is unaffected.")


# ======================================================================
# H. Frozen Atominvest REQ_A_EXPERIENCE_LEVEL remains UNKNOWN, exactly
#    as before this milestone, through the real production analyze_job()
#    path.
# ======================================================================
result_a = analyze_job(_load_job_input(FIXTURE_A))
assert_true(result_a["valid"] is True, f"Atominvest analysis must be valid: {result_a['errors']}")
analysis_a = result_a["analysis"]
match_exp_level = next(m for m in analysis_a["evidence_matches"] if m["requirement_id"] == "REQ_A_EXPERIENCE_LEVEL")
assert_true(
    match_exp_level["result"] == "UNKNOWN",
    f"REQ_A_EXPERIENCE_LEVEL must remain UNKNOWN, unaffected by this milestone; got {match_exp_level['result']}",
)
# SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1 (post-dates this milestone):
# REQ_A_CONFIG_IMPLEMENTATION and REQ_A_QA_TROUBLESHOOTING are
# responsibility-sourced and no longer independently hard-block; updated
# to the current adjudicated baseline -- this assertion is about THIS
# milestone not changing the blocker set any further.
expected_blockers = {
    "REQ_A_DEGREE",
    "REQ_A_EXCEL_DATA",
}
actual_blocked_ids = {b.rsplit(": ", 1)[-1] for b in result_a["hard_blockers"]}
assert_true(
    actual_blocked_ids == expected_blockers,
    f"Atominvest hard blockers must remain exactly {expected_blockers}, got {actual_blocked_ids}",
)
assert_true(
    analysis_a["lane"] == "LANE_0_REJECT" and analysis_a["decision"] == "REJECT",
    "Atominvest overall routing must remain LANE_0_REJECT/REJECT",
)
print("PASS H: Atominvest REQ_A_EXPERIENCE_LEVEL remains UNKNOWN; Atominvest's hard-blocker set and overall routing are unchanged.")


# ======================================================================
# I. No existing approved Claim silently gains
#    degree_experience_duration_conjunction.
# ======================================================================
for claim_id, caps_map in _CLAIM_CAPABILITIES.items():
    assert_true(
        TAG not in caps_map,
        f"{claim_id} must not carry {TAG} -- no approved evidence establishes any years-of-experience threshold",
    )
print("PASS I: no existing Claim capability set carries degree_experience_duration_conjunction.")


# ======================================================================
# J. Application Gate reachability -- through the real match_clause()
#    path, the AND-vs-OR distinction is preserved. No Application Gate
#    control-flow is touched; this is regression coverage only.
# ======================================================================
clause_and = match_clause(
    clause_id="CLAUSE_AND",
    clause_text="Bachelor's degree AND minimum 5 years of experience",
    reusable_claims=reusable_sim,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    TAG in clause_and["explanation"],
    f"AND clause through match_clause() must surface {TAG} in its canonical/explanation output; got {clause_and['explanation']}",
)
clause_or = match_clause(
    clause_id="CLAUSE_OR",
    clause_text="Bachelor's degree OR 5+ years of experience",
    reusable_claims=reusable_sim,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    TAG not in clause_or["explanation"],
    f"OR clause through match_clause() must NOT surface {TAG}; got {clause_or['explanation']}",
)
assert_true(
    clause_or["result"] == "SUPPORTED",
    f"OR clause with an approved bachelor's claim must resolve SUPPORTED through match_clause(), got {clause_or['result']}",
)
print("PASS J: Application Clause path (match_clause()) preserves the same AND-vs-OR distinction as the Job Analysis path; no Application Gate control-flow was touched.")

print("ALL degree_experience_duration_conjunction_v1_test CHECKS PASSED")
