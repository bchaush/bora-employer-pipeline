"""Regression tests for QUALIFIED_DEGREE_EXPERIENCE_DURATION_V1.

The closed degree_experience_duration_conjunction capability
(DEGREE_EXPERIENCE_LOCAL_CONJUNCTION_V1) previously recognized only
"minimum N years of experience" / "at least N years of experience" / "N+
years of experience" duration tails -- it missed bare cardinal numbers
("3 years of experience," no framing word) and domain-qualified experience
phrasing ("3 years of system analysis experience," "3 years of related
experience"). A read-only audit (QUALIFIED_DEGREE_EXPERIENCE_DURATION_AUDIT_V1)
proved this reproduces the same false-SUPPORTED defect class through real
MBTA/Coverys-style wording.

This milestone extends the duration-tail grammar to additionally recognize
bare cardinal/word numbers and a small, explicitly enumerated whitelist of
experience-qualifying adjectives (related, relevant, professional, system
analysis, application support) -- NOT an open-ended wildcard. Constructions
that represent a materially different semantic structure (education/
experience combination/substitution clauses, experience/training slash
alternation, numeric ranges) are deliberately excluded and remain open
limitations, not silently absorbed into this capability.

Exercises real production code (requirement_match.py) -- no logic is
duplicated here.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
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


TAG = "degree_experience_duration_conjunction"


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
# A. Required positives -- existing forms must remain covered, and new
#    bare-cardinal / whitelisted-qualifier forms must now be covered.
# ======================================================================
existing_positives = (
    "Bachelor's degree AND minimum 5 years of experience.",
    "Bachelor's degree plus a minimum of seven years of experience.",
    "Bachelor's degree and at least 5 years of experience.",
    "Bachelor's degree plus 5+ years of experience.",
)
new_positives = (
    "Bachelor's degree AND 3 years of experience.",
    "Bachelor's degree AND three years of experience.",
    "Bachelor's degree AND 3 years of system analysis experience.",
    "Bachelor's degree plus 3 years of system analysis experience.",
    "Bachelor's degree AND 3 years of related experience.",
    "Bachelor's degree AND 5 years of relevant experience.",
    "Master's degree AND 1 year of application support experience.",
    "Bachelor's degree plus 5 years of professional experience.",
)
for text in existing_positives + new_positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(TAG in caps, f"{text!r} must infer {TAG}")
print(f"PASS A: all {len(existing_positives)} previously-covered forms and all {len(new_positives)} newly-covered bare-cardinal/whitelisted-qualifier forms emit {TAG}.")


# ======================================================================
# B. OR safety negatives -- the widened grammar must not reintroduce
#    OR-disjoint false-PARTIAL behavior. Local connector anchoring
#    (credential immediately followed by "and"/"plus", never "or")
#    remains the governing safety mechanism, independent of how broad
#    the duration-tail grammar itself is.
# ======================================================================
or_negatives = (
    "Bachelor's degree OR 3 years of experience.",
    "Bachelor's degree OR 3 years of system analysis experience.",
    "Bachelor's degree OR 3 years of related experience.",
    "Bachelor's degree OR 3 years of system analysis experience, AND strong Excel skills.",
    "Bachelor's degree OR 3 years of system analysis experience plus SQL proficiency.",
    "Bachelor's degree OR 3 years of related experience AND strong communication.",
    "Master's degree OR 1 year of application support experience.",
)
for text in or_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(TAG not in caps, f"{text!r} (synthetic adversarial probe) must NOT infer {TAG} -- duration is a separate OR-alternative")
print("PASS B: OR-disjoint adversarial probes (including trailing unrelated AND/PLUS clauses) never trigger the widened grammar.")


# ======================================================================
# C. Semantic-boundary negatives -- constructions that are NOT the same
#    semantic class as "explicit numeric years-of-experience" must never
#    be pulled in merely because they contain numbers + education/
#    experience words. Deliberately excluded: education/experience
#    combination-substitution phrasing, experience/training slash
#    alternation, and numeric ranges (all documented open limitations,
#    not solved here).
# ======================================================================
boundary_negatives = (
    "Bachelor's degree AND 3 years of combined education and experience.",
    "Bachelor's degree AND 3 years of training and experience.",
    "Bachelor's degree AND 3 years of education and experience.",
    "Bachelor's degree AND 3 years of experience/training.",
    "Bachelor's degree or equivalent combination of education and experience.",
    "Bachelor's degree AND equivalent education and experience.",
    "Bachelor's degree AND 3-5+ years of related experience/training.",
)
for text in boundary_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(TAG not in caps, f"{text!r} must NOT infer {TAG} -- a different semantic structure (substitution/combination/range/slash-alternation), not a plain numeric experience-duration condition")
print("PASS C: education/experience-combination, experience/training slash-alternation, and numeric-range constructions remain outside this capability's semantic boundary.")


# ======================================================================
# C2. BOUNDED CORRECTION (independent Cursor review, before commit):
#     training-as-qualification-alternative/composition negatives. The
#     original `(?!/)` lookahead only blocked an immediately-adjacent
#     slash; it missed the spaced slash and the "or"/"and"/"plus" +
#     "training" connector forms. "training" here functions as an
#     alternative/composed *qualification concept*, not as an activity
#     the candidate performed, so the tag must not fire.
# ======================================================================
training_qualification_negatives = (
    "Bachelor's degree AND 3 years of experience / training.",
    "Bachelor's degree AND 3 years of experience or training.",
    "Bachelor's degree AND 3 years of related experience / training.",
    "Bachelor's degree AND 3 years of relevant experience and training.",
    "Bachelor's degree AND 3 years of professional experience plus training.",
)
for text in training_qualification_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        TAG not in caps,
        f"{text!r} must NOT infer {TAG} -- 'training' here is a composed/alternative qualification concept, not an activity",
    )
print("PASS C2: training-as-qualification-alternative/composition forms (slash, spaced slash, or, and, plus) remain outside this capability's semantic boundary.")


# ======================================================================
# C3. Training-as-activity positives -- "training" used as a
#     present-participle verb describing work performed must NOT be
#     excluded merely because it appears after "experience." The
#     correction must be semantic (connector-anchored), not a blanket
#     "training anywhere after experience = no match" rule.
# ======================================================================
training_activity_positives = (
    "Bachelor's degree AND 3 years of experience training users.",
    "Bachelor's degree AND 3 years of experience training staff on the application.",
    "Master's degree AND 1 year of application support experience training end users.",
)
for text in training_activity_positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        TAG in caps,
        f"{text!r} must infer {TAG} -- 'training' here is an activity the candidate performed, not a qualification alternative",
    )
print("PASS C3: training-as-activity forms ('experience training users', 'experience training staff on the application', 'experience training end users') still correctly emit the tag.")


# ======================================================================
# C4. OR safety + training combinations -- the training-boundary
#     correction must not weaken OR-disjoint safety, and vice versa.
# ======================================================================
or_training_negatives = (
    "Bachelor's degree OR 3 years of experience or training.",
    "Bachelor's degree OR 3 years of experience / training.",
    "Bachelor's degree OR 3 years of related experience and training.",
)
for text in or_training_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        TAG not in caps,
        f"{text!r} (OR + training adversarial probe) must NOT infer {TAG}",
    )
print("PASS C4: OR-disjoint + training-boundary combinations never trigger the tag.")


# ======================================================================
# D. MBTA diagnostic (temporary, read-only, in-memory only -- no
#    persistent claim change): "Bachelor's degree AND 3 years of system
#    analysis experience." must resolve PARTIAL, not the previously
#    false SUPPORTED, once a bare bachelor's claim is hypothetically
#    approved. The explanation must never fabricate a claim about
#    candidate duration.
# ======================================================================
claim_index_sim = copy.deepcopy(CLAIM_INDEX)
claim_index_sim["CLAIM_EDU_UNWE_001"]["human_approval"] = True
reusable_sim = load_reusable_claims(claim_index_sim, EVIDENCE_INDEX)

mbta_req = _req("Bachelor's degree AND 3 years of system analysis experience.")
match_mbta = match_requirement(job_id="DIAG_MBTA", requirement=mbta_req, reusable_claims=reusable_sim, evidence_index=EVIDENCE_INDEX, match_index=0)
assert_true(match_mbta["result"] == "PARTIAL", f"MBTA-diagnostic requirement must resolve PARTIAL (not fabricated SUPPORTED), got {match_mbta['result']}")
assert_true(TAG in match_mbta["explanation"], f"explanation must name the missing {TAG} capability")
explanation_lower = match_mbta["explanation"].lower()
assert_true(
    "lacks" not in explanation_lower and "fewer than" not in explanation_lower and "does not meet" not in explanation_lower,
    "explanation must not fabricate a negative claim about candidate duration -- duration remains non-canonical",
)

cl_after = validate_claim_repository()
assert_true(
    cl_after["index"]["CLAIM_EDU_UNWE_001"]["human_approval"] is False,
    "real claim repository on disk must remain unaffected by the in-memory simulation",
)
print("PASS D: MBTA-diagnostic 'Bachelor's degree AND 3 years of system analysis experience' now resolves PARTIAL (not fabricated SUPPORTED); no candidate-duration claim fabricated; disk state unaffected.")


# ======================================================================
# E. No existing approved Claim silently gains
#    degree_experience_duration_conjunction.
# ======================================================================
for claim_id, caps_map in _CLAIM_CAPABILITIES.items():
    assert_true(TAG not in caps_map, f"{claim_id} must not carry {TAG} -- no approved evidence establishes any years-of-experience threshold")
print("PASS E: no existing Claim capability set carries degree_experience_duration_conjunction.")


# ======================================================================
# F. Application Gate reachability -- through the real match_clause()
#    path, the AND-vs-OR distinction is preserved with a bachelor's-only
#    (in-memory) approved claim: AND resolves PARTIAL (duration
#    unsatisfied), OR resolves SUPPORTED (bachelor's alone satisfies the
#    alternative branch). No Application Gate control-flow is touched;
#    this is regression coverage only.
# ======================================================================
from application_clause_match import match_clause  # noqa: E402

clause_and = match_clause(
    clause_id="CLAUSE_AND",
    clause_text="Bachelor's degree AND 3 years of related experience",
    reusable_claims=reusable_sim,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    clause_and["result"] == "PARTIAL",
    f"AND clause through match_clause() must resolve PARTIAL with bachelor-only evidence, got {clause_and['result']}",
)
assert_true(
    TAG in clause_and["explanation"],
    f"AND clause through match_clause() must surface {TAG} in its explanation; got {clause_and['explanation']}",
)

clause_or = match_clause(
    clause_id="CLAUSE_OR",
    clause_text="Bachelor's degree OR 3 years of related experience",
    reusable_claims=reusable_sim,
    evidence_index=EVIDENCE_INDEX,
)
assert_true(
    clause_or["result"] == "SUPPORTED",
    f"OR clause through match_clause() must resolve SUPPORTED with bachelor-only evidence, got {clause_or['result']}",
)
assert_true(
    TAG not in clause_or["explanation"],
    f"OR clause through match_clause() must NOT surface {TAG}; got {clause_or['explanation']}",
)
print("PASS F: Application Clause path (match_clause()) preserves the AND-vs-OR distinction with bachelor-only evidence (AND->PARTIAL, OR->SUPPORTED); no Application Gate control-flow was touched.")

print("ALL qualified_degree_experience_duration_v1_test CHECKS PASSED")
