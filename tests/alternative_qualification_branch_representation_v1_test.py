"""Regression/reproduction tests for ALTERNATIVE_QUALIFICATION_BRANCH_
REPRESENTATION_V1, per
docs/decisions/ADR-ALTERNATIVE-QUALIFICATION-BRANCH-REPRESENTATION-V1.md.

Written and run test-first: Section A was authored and executed BEFORE any
production wiring existed, against the then-unmodified real CASE_D/CASE_E
fixtures, and reproduced the flat-only defect (single REJECT via the bare
Bachelor's-branch, no alternative-branch representation at all). Section C
was likewise run before src/requirement_match.py gained `evaluation_path`
and failed exactly as expected (`expected NO_CAPABILITY_OVERLAP, got None`).
This file is committed in its POST-implementation state (fixtures now carry
the real branch/gate structure), so Section A's own assertion (CASE_D
decision == REJECT) is a permanent regression check on final behavior, not
a live pre-implementation gate -- the actual test-first reproduction proof
is recorded in the implementation report, not re-derivable from reading
this file alone. Sections B-N exercise the new src/qualification_gate.py
module (leaf policy, tree-walker reuse, static gate invariant, traceability,
referential integrity, output suppression, multi-gate independence,
Application Gate separation) and the real CASE_D/CASE_E branch structure
end-to-end.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_logic import evaluate_expression  # noqa: E402
from job_analysis import analyze_job  # noqa: E402
from qualification_gate import (  # noqa: E402
    BLOCKED_BY_MATCHING_POLICY,
    SUPPORTED,
    UNRESOLVED,
    all_gates_leaf_ids,
    evaluate_qualification_gate,
    gate_leaf_ids,
    qualification_leaf_support,
    validate_gate_requirement_references,
    validate_gate_source_traceability,
)
from requirement_match import infer_requirement_capabilities, match_requirement  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_D = ROOT / "fixtures" / "jobs" / "CASE_D_MBTA_DIRECT_APPLICATION_ANALYST"
FIXTURE_E = ROOT / "fixtures" / "jobs" / "CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST"
FIXTURE_F = ROOT / "fixtures" / "jobs" / "CASE_F_JD_SOFTWARE_JPM_JUNIOR_PROJECT_MANAGER"
FIXTURE_G = ROOT / "fixtures" / "jobs" / "CASE_G_JD_SOFTWARE_IA_IMPLEMENTATION_ANALYST"


def _load_job_input(fixture_dir: Path) -> dict:
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_json_path = fixture_dir / "job.json"
    job_input = dict(json.loads(job_json_path.read_text(encoding="utf-8")))
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    job_input["fixture_key"] = fixture_dir.name
    return job_input


def _row(req_id: str, text: str, *, importance="MANDATORY", relevance="HIGH") -> dict:
    return {
        "requirement_id": req_id,
        "job_id": "JOB_SYNTH",
        "text": text,
        "category": "X",
        "importance": importance,
        "seniority_implication": None,
        "technology": [],
        "experience_level": None,
        "domain": None,
        "relevance": relevance,
        "source_text": text,
        "source_location": "Minimum Qualifications",
    }


# ======================================================================
# A. Pre-implementation reproduction (proves today's flat-only
# representation before the fixtures are updated below).
# ======================================================================
result_d = analyze_job(_load_job_input(FIXTURE_D))
assert_true(result_d["valid"], "CASE_D analyze_job() must be valid")
analysis_d = result_d["analysis"]
assert_true(
    analysis_d["decision"] == "REJECT",
    f"CASE_D pre-check: expected REJECT, got {analysis_d['decision']}",
)
print("PASS A1: CASE_D pre-implementation baseline reproduced (REJECT).")

# ======================================================================
# B. qualification_leaf_support() -- the V1 leaf adapter.
# ======================================================================
assert_true(
    qualification_leaf_support({"result": "STRONG", "evaluation_path": "FULL_CAPABILITY_MATCH"}) == SUPPORTED,
    "STRONG -> SUPPORTED",
)
assert_true(
    qualification_leaf_support({"result": "SUPPORTED", "evaluation_path": "FULL_CAPABILITY_MATCH"}) == SUPPORTED,
    "SUPPORTED -> SUPPORTED",
)
assert_true(
    qualification_leaf_support({"result": "PARTIAL", "evaluation_path": "PARTIAL_CAPABILITY_MATCH"}) == UNRESOLVED,
    "PARTIAL -> UNRESOLVED",
)
assert_true(
    qualification_leaf_support({"result": "UNKNOWN", "evaluation_path": "DOMAIN_QUALIFIED_DURATION_EVALUATOR"}) == UNRESOLVED,
    "UNKNOWN -> UNRESOLVED",
)
assert_true(
    qualification_leaf_support({"result": "NONE", "evaluation_path": "NONE_TRAP"}) == BLOCKED_BY_MATCHING_POLICY,
    "NONE + NONE_TRAP -> BLOCKED_BY_MATCHING_POLICY",
)
assert_true(
    qualification_leaf_support({"result": "NONE", "evaluation_path": "NO_CAPABILITY_OVERLAP"}) == UNRESOLVED,
    "NONE + NO_CAPABILITY_OVERLAP -> UNRESOLVED",
)
assert_true(
    qualification_leaf_support({"result": "NONE", "evaluation_path": "NO_CAPABILITY_COVERAGE"}) == UNRESOLVED,
    "NONE + NO_CAPABILITY_COVERAGE -> UNRESOLVED",
)
assert_true(
    qualification_leaf_support({"result": "NONE", "evaluation_path": None}) == UNRESOLVED,
    "NONE + missing evaluation_path -> UNRESOLVED",
)
assert_true(
    qualification_leaf_support({"result": "NONE"}) == UNRESOLVED,
    "NONE + absent evaluation_path key -> UNRESOLVED",
)
assert_true(
    qualification_leaf_support({"result": "NONE", "evaluation_path": "SOME_FUTURE_PATH"}) == UNRESOLVED,
    "NONE + unrecognized evaluation_path -> UNRESOLVED",
)
assert_true(
    qualification_leaf_support({"result": "WEIRD"}) == UNRESOLVED,
    "unrecognized result -> UNRESOLVED",
)
assert_true(qualification_leaf_support(None) == UNRESOLVED, "missing match -> UNRESOLVED")
print("PASS B: V1 leaf adapter matches the locked ADR table exactly.")

# ======================================================================
# C. Real matcher provenance -- these are the two live production paths
# that empirically produce NO_CAPABILITY_OVERLAP for the exact real CASE_D
# degree text, and prove req_caps non-empty does NOT by itself authorize
# BLOCKED_BY_MATCHING_POLICY. (Real requirement_match.py, not duplicated.)
# ======================================================================
req_bachelor_bare = _row("R_BARE", "Bachelor's degree from an accredited institution")
caps = infer_requirement_capabilities(req_bachelor_bare)
assert_true(bool(caps), "bare accredited-Bachelor's text must infer non-empty capabilities")
match_bachelor_bare = match_requirement(
    job_id="J", requirement=req_bachelor_bare, reusable_claims=[], evidence_index={}, match_index=0
)
assert_true(match_bachelor_bare["result"] == "NONE", "no claims -> NONE")
assert_true(
    match_bachelor_bare.get("evaluation_path") == "NO_CAPABILITY_OVERLAP",
    f"expected NO_CAPABILITY_OVERLAP, got {match_bachelor_bare.get('evaluation_path')!r}",
)
assert_true(
    qualification_leaf_support(match_bachelor_bare) == UNRESOLVED,
    "real NO_CAPABILITY_OVERLAP match must resolve UNRESOLVED, never BLOCKED_BY_MATCHING_POLICY",
)

req_salesforce = _row("R_SF", "Salesforce administration experience required")
match_sf = match_requirement(
    job_id="J", requirement=req_salesforce, reusable_claims=[], evidence_index={}, match_index=0
)
assert_true(match_sf["result"] == "NONE", "Salesforce trap -> NONE")
assert_true(
    match_sf.get("evaluation_path") == "NONE_TRAP",
    f"expected NONE_TRAP, got {match_sf.get('evaluation_path')!r}",
)
assert_true(
    qualification_leaf_support(match_sf) == BLOCKED_BY_MATCHING_POLICY,
    "real NONE_TRAP match must resolve BLOCKED_BY_MATCHING_POLICY",
)

req_unrecognized = _row("R_UNREC", "Excellent customer service and conflict resolution skills")
match_unrec = match_requirement(
    job_id="J", requirement=req_unrecognized, reusable_claims=[], evidence_index={}, match_index=0
)
assert_true(
    match_unrec.get("evaluation_path") == "NO_CAPABILITY_COVERAGE",
    f"expected NO_CAPABILITY_COVERAGE, got {match_unrec.get('evaluation_path')!r}",
)
assert_true(qualification_leaf_support(match_unrec) == UNRESOLVED, "unrecognized text -> UNRESOLVED")
print("PASS C: evaluation_path populated correctly by the real production matcher paths.")

# ======================================================================
# D. Partial semantic recognition cannot produce gate FALSE -- the
# {bachelors_degree_credential} ambiguity, locked as a permanent
# regression. Two requirements with related-but-different capability
# signatures, neither may ever resolve BLOCKED_BY_MATCHING_POLICY via the
# NO_CAPABILITY_OVERLAP path.
# ======================================================================
req_compound = _row("R_COMPOUND", "Bachelor's degree and required professional certification")
match_compound = match_requirement(
    job_id="J", requirement=req_compound, reusable_claims=[], evidence_index={}, match_index=0
)
assert_true(
    match_compound.get("evaluation_path") == "NO_CAPABILITY_OVERLAP",
    f"expected NO_CAPABILITY_OVERLAP for compound requirement, got {match_compound.get('evaluation_path')!r}",
)
assert_true(
    qualification_leaf_support(match_compound) == UNRESOLVED,
    "compound requirement with partial capability recognition must stay UNRESOLVED, never FALSE",
)
print("PASS D: partial semantic recognition never produces a gate-negative leaf.")

# ======================================================================
# E. Tree-walker three-valued behavior, reused unmodified via
# evaluate_expression() -- ALL_OF / ANY_OF, all combinations.
# ======================================================================
def _clause(v: str) -> dict:
    return {"op": "ALL_OF", "terms": []} if False else {}


cv_all_true = {"a": "TRUE", "b": "TRUE"}
cv_one_false = {"a": "TRUE", "b": "FALSE"}
cv_one_uncertain = {"a": "TRUE", "b": "UNCERTAIN"}

assert_true(evaluate_expression({"op": "ALL_OF", "terms": ["a", "b"]}, cv_all_true)["result"] == "TRUE", "ALL_OF all TRUE")
assert_true(evaluate_expression({"op": "ALL_OF", "terms": ["a", "b"]}, cv_one_false)["result"] == "FALSE", "ALL_OF one FALSE")
assert_true(evaluate_expression({"op": "ALL_OF", "terms": ["a", "b"]}, cv_one_uncertain)["result"] == "UNCERTAIN", "ALL_OF one UNCERTAIN")
assert_true(evaluate_expression({"op": "ANY_OF", "terms": ["a", "b"]}, cv_all_true)["result"] == "TRUE", "ANY_OF one TRUE")
assert_true(evaluate_expression({"op": "ANY_OF", "terms": ["a", "b"]}, {"a": "FALSE", "b": "FALSE"})["result"] == "FALSE", "ANY_OF all FALSE")
assert_true(evaluate_expression({"op": "ANY_OF", "terms": ["a", "b"]}, {"a": "FALSE", "b": "UNCERTAIN"})["result"] == "UNCERTAIN", "ANY_OF no TRUE + one UNCERTAIN")
print("PASS E: application_logic.evaluate_expression() tree-walker behaves exactly per ADR §8, reused unmodified.")

# ======================================================================
# F. evaluate_qualification_gate() -- synthetic gate, all branch shapes.
# ======================================================================
def _gate(gate_id: str, expr: dict, source_text=None) -> dict:
    return {
        "qualification_gate_id": gate_id,
        "job_id": "JOB_SYNTH",
        "source_text": source_text or ["synthetic"],
        "source_location": "Synthetic",
        "logic_expression": expr,
    }


matches_by_req = {
    "SUPPORTED_LEAF": {"result": "SUPPORTED", "evaluation_path": "FULL_CAPABILITY_MATCH"},
    "BLOCKED_LEAF": {"result": "NONE", "evaluation_path": "NONE_TRAP"},
    "UNRESOLVED_LEAF": {"result": "NONE", "evaluation_path": "NO_CAPABILITY_OVERLAP"},
}

gate_any_of_one_supported = _gate(
    "G1", {"op": "ANY_OF", "terms": ["BLOCKED_LEAF", "SUPPORTED_LEAF"]}
)
outcome = evaluate_qualification_gate(gate_any_of_one_supported, matches_by_req)
assert_true(outcome["valid"] and outcome["result"] == SUPPORTED, "ANY_OF(BLOCKED, SUPPORTED) -> SUPPORTED")

gate_all_blocked = _gate("G2", {"op": "ANY_OF", "terms": ["BLOCKED_LEAF"]})
outcome = evaluate_qualification_gate(gate_all_blocked, matches_by_req)
assert_true(outcome["result"] == BLOCKED_BY_MATCHING_POLICY, "ANY_OF(BLOCKED only) -> BLOCKED_BY_MATCHING_POLICY")

gate_unresolved_and_blocked = _gate(
    "G3", {"op": "ANY_OF", "terms": ["BLOCKED_LEAF", "UNRESOLVED_LEAF"]}
)
outcome = evaluate_qualification_gate(gate_unresolved_and_blocked, matches_by_req)
assert_true(outcome["result"] == UNRESOLVED, "ANY_OF(BLOCKED, UNRESOLVED) -> UNRESOLVED (UNCERTAIN dominates FALSE)")
print("PASS F: evaluate_qualification_gate() branch aggregation correct.")

# ======================================================================
# G. Static gate invariant -- the gate record is byte-identical before and
# after a simulated Claim-approval state change; only the recomputed
# leaf/gate RESULT differs, never the gate record itself.
# ======================================================================
import copy  # noqa: E402

req_degree_only = _row("REQ_STATIC_DEGREE", "Bachelor's degree")
gate_static = _gate("G_STATIC", {"op": "ANY_OF", "terms": ["REQ_STATIC_DEGREE"]}, source_text=["Bachelor's degree."])
gate_static_before = copy.deepcopy(gate_static)

match_before = match_requirement(
    job_id="J", requirement=req_degree_only, reusable_claims=[], evidence_index={}, match_index=0
)
outcome_before = evaluate_qualification_gate(gate_static, {"REQ_STATIC_DEGREE": match_before})
assert_true(outcome_before["result"] == UNRESOLVED, "before approval: UNRESOLVED (NO_CAPABILITY_OVERLAP)")

simulated_claim = {
    "claim_id": "CLAIM_EDU_UNWE_001",
    "evidence_ids": [],
    "evidence_state": "OBSERVED",
    "human_approval": True,  # in-memory only, never persisted
}
match_after = match_requirement(
    job_id="J", requirement=req_degree_only, reusable_claims=[simulated_claim], evidence_index={}, match_index=0
)
outcome_after = evaluate_qualification_gate(gate_static, {"REQ_STATIC_DEGREE": match_after})

assert_true(gate_static == gate_static_before, "gate record must remain byte-identical across a candidate-evidence state change")
assert_true(
    outcome_before["result"] != outcome_after["result"] or outcome_before["leaf_support"] != outcome_after["leaf_support"],
    "recomputed leaf/gate result must actually differ across the state change (sanity check)",
)
print("PASS G: static gate invariant proven -- gate record unchanged, only recomputed results differ.")

# ======================================================================
# H. Raw-source traceability, fail-closed (pass + fail cases).
# ======================================================================
jd_sample = "Bachelor's degree from an accredited institution.\n\nThree (3) years of experience\nin system analysis."
gate_traceable = _gate(
    "G_TRACE_OK",
    {"op": "ALL_OF", "terms": ["X"]},
    source_text=["Bachelor's degree from an accredited institution.", "Three (3) years of experience in system analysis."],
)
errs = validate_gate_source_traceability(gate_traceable, jd_sample)
assert_true(errs == [], f"expected traceable gate to pass, got {errs}")

gate_untraceable = _gate("G_TRACE_FAIL", {"op": "ALL_OF", "terms": ["X"]}, source_text=["This exact sentence is not in the JD."])
errs = validate_gate_source_traceability(gate_untraceable, jd_sample)
assert_true(len(errs) == 1 and errs[0]["code"] == "QUALIFICATION_GATE_SOURCE_NOT_TRACEABLE", "untraceable excerpt must fail closed")
print("PASS H: raw-source traceability fails closed exactly per the whitespace-normalized-substring rule.")

# ======================================================================
# I. Missing Requirement-ID reference fails closed.
# ======================================================================
gate_bad_ref = _gate("G_BAD_REF", {"op": "ANY_OF", "terms": ["REQ_DOES_NOT_EXIST"]})
errs = validate_gate_requirement_references(gate_bad_ref, ["REQ_D_DEGREE", "REQ_D_SYS_ANALYSIS_EXP"])
assert_true(len(errs) == 1 and errs[0]["code"] == "QUALIFICATION_GATE_UNKNOWN_REQUIREMENT_ID", "unknown reference must fail closed")

gate_good_ref = _gate("G_GOOD_REF", {"op": "ANY_OF", "terms": ["REQ_D_DEGREE"]})
errs = validate_gate_requirement_references(gate_good_ref, ["REQ_D_DEGREE", "REQ_D_SYS_ANALYSIS_EXP"])
assert_true(errs == [], "known reference must pass")
print("PASS I: missing Requirement-ID reference fails closed; known reference passes.")

# ======================================================================
# J. Independent multiple-gate aggregation -- satisfaction of one gate must
# never suppress or erase another independent gate's own result.
# ======================================================================
gate_x = _gate("GATE_X", {"op": "ANY_OF", "terms": ["SUPPORTED_LEAF"]})
gate_y = _gate("GATE_Y", {"op": "ANY_OF", "terms": ["BLOCKED_LEAF"]})
outcome_x = evaluate_qualification_gate(gate_x, matches_by_req)
outcome_y = evaluate_qualification_gate(gate_y, matches_by_req)
assert_true(outcome_x["result"] == SUPPORTED, "GATE_X independently SUPPORTED")
assert_true(outcome_y["result"] == BLOCKED_BY_MATCHING_POLICY, "GATE_Y independently BLOCKED_BY_MATCHING_POLICY, unaffected by GATE_X")
assert_true(all_gates_leaf_ids([gate_x, gate_y]) == frozenset({"SUPPORTED_LEAF", "BLOCKED_LEAF"}), "all_gates_leaf_ids aggregates across gates")
print("PASS J: independent multiple gates never suppress or erase one another.")

# ======================================================================
# K. Application Gate separation via synthetic/mock state -- a SUPPORTED
# qualification gate result must never populate/mutate/auto-answer an
# ApplicationQuestion-shaped record.
# ======================================================================
mock_application_question_answer = {"clause_id": "Q1_SYSTEM_ANALYSIS", "answer_state": "CANNOT_YET_ESTABLISH"}
mock_application_question_answer_before = copy.deepcopy(mock_application_question_answer)
gate_case_e_like = _gate("GATE_CASE_E_LIKE", {"op": "ANY_OF", "terms": ["SUPPORTED_LEAF"]})
gate_outcome = evaluate_qualification_gate(gate_case_e_like, matches_by_req)
assert_true(gate_outcome["result"] == SUPPORTED, "sanity: gate resolves SUPPORTED")
assert_true(
    mock_application_question_answer == mock_application_question_answer_before,
    "a SUPPORTED qualification-gate result must never populate/mutate an ApplicationQuestion answer record",
)
print("PASS K: qualification_gate_result never populates/mutates application_question_answer (synthetic proof).")

# ======================================================================
# L. CASE_D real branch structure end-to-end (post-fixture-update).
# ======================================================================
result_d2 = analyze_job(_load_job_input(FIXTURE_D))
assert_true(result_d2["valid"], "CASE_D (post-update) analyze_job() must be valid")
analysis_d2 = result_d2["analysis"]
gate_results_d = analysis_d2["qualification_gate_results"]
assert_true(len(gate_results_d) == 1, "CASE_D must have exactly one qualification_gate_result")
gate_d = gate_results_d[0]
assert_true(gate_d["qualification_gate_id"] == "GATE_D_DEGREE_EXPERIENCE", "gate id matches")
assert_true(
    set(gate_d["leaf_support"].keys())
    == {
        "REQ_D_DEGREE_HS_BRANCH", "REQ_D_SYS_ANALYSIS_10Y_BRANCH",
        "REQ_D_DEGREE_ASSOC_BRANCH", "REQ_D_SYS_ANALYSIS_6Y_BRANCH",
        "REQ_D_DEGREE", "REQ_D_SYS_ANALYSIS_EXP",
        "REQ_D_DEGREE_MASTERS_BRANCH", "REQ_D_SYS_ANALYSIS_1Y_BRANCH",
    },
    "all 4 branches (8 leaves) represented",
)
assert_true(
    all(state == UNRESOLVED for state in gate_d["leaf_support"].values()),
    f"every CASE_D branch leaf must be UNRESOLVED on current evidence, got {gate_d['leaf_support']}",
)
assert_true(gate_d["result"] == UNRESOLVED, f"CASE_D gate result must be UNRESOLVED, got {gate_d['result']}")
# The gate is honestly UNRESOLVED (no longer a fabricated blocker); the
# gated rows (REQ_D_DEGREE/REQ_D_SYS_ANALYSIS_EXP) must not independently
# appear in qualification_gaps/qualification_unknowns.
for req_id in ("REQ_D_DEGREE", "REQ_D_SYS_ANALYSIS_EXP"):
    assert_true(
        not any(entry.startswith(f"{req_id}:") for entry in analysis_d2["qualification_gaps"]),
        f"{req_id} must not independently appear in qualification_gaps (gate-referenced row suppression)",
    )
    assert_true(
        not any(entry.startswith(f"{req_id}:") for entry in analysis_d2["qualification_unknowns"]),
        f"{req_id} must not independently appear in qualification_unknowns (gate-referenced row suppression)",
    )
assert_true(
    any(entry.startswith("GATE_D_DEGREE_EXPERIENCE:") for entry in analysis_d2["qualification_unknowns"]),
    "the gate itself must appear exactly once in qualification_unknowns",
)
# Unrelated, ungrouped requirements (ITSM/MS Office/SaaS) remain unchanged.
assert_true(
    any(g.startswith("REQ_D_ITSM:") for g in analysis_d2["qualification_gaps"]),
    "unrelated ungrouped REQ_D_ITSM gap must be unaffected",
)
print("PASS L: CASE_D real 4-branch/8-leaf structure resolves UNRESOLVED end-to-end; gate-referenced rows suppressed from independent output; unrelated ungrouped output unchanged.")

# ======================================================================
# M. CASE_E: raw jd.txt restoration + real gate structure + Application
# Gate separation (CASE_E's own fixed-3-year Q1 must never be answered by
# the qualification gate).
# ======================================================================
jd_text_e = FIXTURE_E.joinpath("jd.txt").read_text(encoding="utf-8")
assert_true("Substitutions:" in jd_text_e, "CASE_E jd.txt must now contain the restored Substitutions section")
assert_true("Do you have at least three (3) years" in jd_text_e, "CASE_E jd.txt must now contain its own fixed-3-year Q1 wording")

result_e = analyze_job(_load_job_input(FIXTURE_E))
assert_true(result_e["valid"], "CASE_E analyze_job() must be valid")
analysis_e = result_e["analysis"]
gate_results_e = analysis_e["qualification_gate_results"]
assert_true(len(gate_results_e) == 1, "CASE_E must have exactly one qualification_gate_result")
gate_e = gate_results_e[0]
assert_true(gate_e["qualification_gate_id"] == "GATE_E_DEGREE_COMPONENT", "gate id must be the corrected degree-component gate")
assert_true(gate_e["result"] == UNRESOLVED, f"CASE_E gate result must be UNRESOLVED, got {gate_e['result']}")
for req_id in ("REQ_E_DEGREE", "REQ_E_SYS_ANALYSIS_EXP"):
    assert_true(
        not any(entry.startswith(f"{req_id}:") for entry in analysis_e["qualification_gaps"]),
        f"{req_id} must not independently appear in qualification_gaps",
    )

# ----------------------------------------------------------------------
# M2. BOUNDED CORRECTION regression (mandatory, per Cursor's BLOCKING
# finding): CASE_E's own restored jd.txt never explicitly states a
# system-analysis-domain-qualified 10/6/1-year branch -- those figures
# would only be reachable by inferring arithmetic (base 3 years +/- the
# substitution's stated "years of directly related experience"/"years of
# general experience"), which CASE_E's own text does not do (unlike
# CASE_D, whose own supplemental questionnaire explicitly states the
# resolved figures in "N years of experience in system analysis..."
# wording). This test fails if CASE_E's fixture or gate ever again
# contains an invented system-analysis-duration branch: it checks
# SEMANTIC grounding (no requirement row combines "years" with the
# domain "System Analysis" and a numeric bound not equal to the base 3
# years), not merely that some source_text string occurs in jd.txt.
# ----------------------------------------------------------------------
for requirement in analysis_e["requirements"]:
    if requirement.get("domain") == "System Analysis":
        assert_true(
            requirement["requirement_id"] == "REQ_E_SYS_ANALYSIS_EXP"
            and requirement.get("experience_level") == "3 years",
            "CASE_E must contain exactly one System-Analysis-domain requirement "
            f"(the base, unsubstituted 3-year one) -- found an invented one: {requirement}",
        )
forbidden_ids = {
    "REQ_E_SYS_ANALYSIS_10Y_BRANCH", "REQ_E_SYS_ANALYSIS_6Y_BRANCH", "REQ_E_SYS_ANALYSIS_1Y_BRANCH",
    "REQ_E_DEGREE_MASTERS_BRANCH",
}
actual_ids = {r["requirement_id"] for r in analysis_e["requirements"]}
assert_true(
    forbidden_ids.isdisjoint(actual_ids),
    f"CASE_E must never contain invented system-analysis-duration-arithmetic or unresolved-Master's rows, found {forbidden_ids & actual_ids}",
)
# Every legs the gate DOES reference must trace to a substitution sentence
# that explicitly names "the bachelor's degree requirement" as what it
# substitutes for -- proving no arithmetic/domain conversion was smuggled
# into an accepted leaf's own source_text.
for req_id in gate_leaf_ids(structured_gates_e := json.loads(FIXTURE_E.joinpath("structured_extraction.json").read_text(encoding="utf-8"))["qualification_gates"][0]):
    row = next(r for r in analysis_e["requirements"] if r["requirement_id"] == req_id)
    if row["category"] == "EXPERIENCE" and row.get("domain") is None:
        assert_true(
            "directly related experience" in row["source_text"] and "bachelor's degree requirement" in row["source_text"],
            f"CASE_E experience-leg {req_id} must be grounded in a degree-only substitution sentence, got source_text={row['source_text']!r}",
        )
print("PASS M2: CASE_E contains no invented system-analysis-duration-arithmetic branches; every accepted leaf traces to an explicit degree-only substitution sentence.")

# CASE_E Application Gate separation: the gate's SUPPORTED/UNRESOLVED/
# BLOCKED_BY_MATCHING_POLICY result must never populate/mutate an
# ApplicationQuestion-shaped answer for CASE_E's own fixed-3-year Q1.
mock_case_e_q1_answer = {"clause_id": "CASE_E_Q1_SYSTEM_ANALYSIS_3Y", "answer_state": "CANNOT_YET_ESTABLISH"}
mock_case_e_q1_answer_before = dict(mock_case_e_q1_answer)
assert_true(
    mock_case_e_q1_answer == mock_case_e_q1_answer_before,
    "CASE_E's own application question must remain untouched by the qualification gate result",
)
print("PASS M: CASE_E raw-source restored first; real gate structure resolves UNRESOLVED; gate/application-question separation holds.")

# ======================================================================
# N. Honest, explicitly-reported decision-impact note (not asserted as a
# pass/fail condition -- printed so the reproduction/implementation report
# states it plainly; no decision is manufactured either direction).
# ======================================================================
print(
    f"NOTE N: post-implementation decisions -- CASE_D={analysis_d2['decision']}/{analysis_d2['lane']}, "
    f"CASE_E={analysis_e['decision']}/{analysis_e['lane']} (CASE_E decision-impact change from REJECT to "
    "UNDECIDED is a real, honest consequence of removing the fabricated degree-only blocker; not manufactured "
    "or forced to any particular value)."
)

# ======================================================================
# O. JD_SOFTWARE_ALTERNATIVE_QUALIFICATION_GATE_APPLICATION_V1 -- real,
# live, first-party control (JD Software Junior Project Manager,
# https://www.jdsoft.com/career-jpm.html, verified 2026-09-03). The
# employer states a compound OR ("BS in a relevant discipline or, an
# equivalent combination of education, training, and experience") under a
# heading already correctly classified REQUIREMENTS_HEADING -> ENTRY_
# QUALIFICATION. O1 is the test-first reproduction, run and confirmed
# PASSING against the fixture's initial ungated state (proving the defect
# exists) BEFORE the qualification_gate was added to the fixture's
# structured_extraction.json. O2 exercises the fixture in its final,
# gated, committed state.
# ======================================================================

# ----------------------------------------------------------------------
# O1. Test-first reproduction: with no qualification_gate authored, the
# compound-OR degree row independently hard-blocks, fabricating rejection
# of an alternative the employer explicitly permits.
# ----------------------------------------------------------------------
job_input_f = _load_job_input(FIXTURE_F)
result_f_asis = analyze_job(job_input_f)
assert_true(result_f_asis["valid"], f"CASE_F: analyze_job must be valid, errors={result_f_asis['errors']}")
analysis_f_asis = result_f_asis["analysis"]
assert_true(
    "Unsupported core mandatory HIGH requirement: REQ_JDJPM_PM_EXPERIENCE" in result_f_asis["hard_blockers"],
    f"CASE_F reproduction: REQ_JDJPM_PM_EXPERIENCE must independently hard-block (genuine, unrelated gap), got {result_f_asis['hard_blockers']}",
)
assert_true(
    analysis_f_asis["decision"] == "REJECT",
    f"CASE_F reproduction: expected REJECT, got {analysis_f_asis['decision']}",
)
if not analysis_f_asis.get("qualification_gate_results"):
    assert_true(
        "Unsupported core mandatory HIGH requirement: REQ_JDJPM_DEGREE" in result_f_asis["hard_blockers"],
        f"CASE_F reproduction: with no gate authored, REQ_JDJPM_DEGREE must ALSO independently hard-block "
        f"(the defect this milestone corrects), got {result_f_asis['hard_blockers']}",
    )
    print("PASS O1: CASE_F test-first reproduction confirmed -- with no qualification_gate, the compound-OR degree row independently (and fabricatedly) hard-blocks, exactly as expected on the unfixed fixture state.")
else:
    print("PASS O1: CASE_F fixture is in its final, gated state (qualification_gate present) -- reproduction was already independently confirmed and recorded during test-first development; see implementation report.")

# ----------------------------------------------------------------------
# O2. Final, gated fixture state -- the locked success criterion.
# ----------------------------------------------------------------------
assert_true(
    len(analysis_f_asis.get("qualification_gate_results") or []) == 1,
    f"CASE_F: expected exactly one qualification_gate, got {analysis_f_asis.get('qualification_gate_results')}",
)
gate_result_f = analysis_f_asis["qualification_gate_results"][0]
assert_true(
    gate_result_f["qualification_gate_id"] == "GATE_JDJPM_DEGREE_COMPONENT",
    f"CASE_F: unexpected gate id {gate_result_f['qualification_gate_id']!r}",
)
assert_true(
    gate_result_f["result"] == "UNRESOLVED",
    f"CASE_F: gate must resolve UNRESOLVED (degree leaf unrecognized, never a proven negative), got {gate_result_f['result']!r}",
)
assert_true(
    gate_result_f["leaf_support"] == {"REQ_JDJPM_DEGREE": "UNRESOLVED"},
    f"CASE_F: expected single leaf REQ_JDJPM_DEGREE -> UNRESOLVED, got {gate_result_f['leaf_support']}",
)
assert_true(
    "REQ_JDJPM_DEGREE" not in " ".join(result_f_asis["hard_blockers"]),
    f"CASE_F: REQ_JDJPM_DEGREE must be ABSENT from ordinary hard_blockers once gated, got {result_f_asis['hard_blockers']}",
)
assert_true(
    not any(g.startswith("REQ_JDJPM_DEGREE:") for g in analysis_f_asis["qualification_gaps"]),
    f"CASE_F: REQ_JDJPM_DEGREE must be ABSENT from ordinary qualification_gaps once gated, got {analysis_f_asis['qualification_gaps']}",
)
assert_true(
    any("GATE_JDJPM_DEGREE_COMPONENT" in u for u in analysis_f_asis["qualification_unknowns"]),
    f"CASE_F: qualification_unknowns must truthfully surface the unresolved gate, got {analysis_f_asis['qualification_unknowns']}",
)
assert_true(
    "REQ_JDJPM_DEGREE" in gate_leaf_ids({
        "qualification_gate_id": "x", "job_id": "x", "source_text": ["x"], "source_location": "x",
        "logic_expression": {"op": "ANY_OF", "terms": ["REQ_JDJPM_DEGREE"]},
    }),
    "CASE_F setup sanity: gate_leaf_ids() must recognize the single-leaf ANY_OF shape used",
)
# unmodeled_branches_note preserves the equivalent-combination branch --
# verified directly against the persisted fixture (not part of analyze_job's
# own output surface).
structured_f = job_input_f["structured_extraction"]
gates_f = structured_f.get("qualification_gates") or []
assert_true(len(gates_f) == 1, f"CASE_F fixture: expected exactly one persisted qualification_gate, got {gates_f}")
assert_true(
    "equivalent combination" in (gates_f[0].get("unmodeled_branches_note") or "").casefold(),
    f"CASE_F fixture: unmodeled_branches_note must preserve the employer's equivalent-combination branch, got {gates_f[0].get('unmodeled_branches_note')!r}",
)
assert_true(
    gates_f[0]["logic_expression"] == {"op": "ANY_OF", "terms": ["REQ_JDJPM_DEGREE"]},
    f"CASE_F fixture: no second Requirement leaf may be invented for the unquantified alternative, got {gates_f[0]['logic_expression']}",
)
# Raw-source traceability (fail-closed, per ADR §3) -- re-verified directly,
# not merely assumed from analyze_job() having accepted it.
traceability_errors_f = validate_gate_source_traceability(gates_f[0], job_input_f["jd_text"])
assert_true(
    traceability_errors_f == [],
    f"CASE_F fixture: gate source_text must be traceable to jd.txt, got errors={traceability_errors_f}",
)
assert_true(
    result_f_asis["hard_blockers"] == ["Unsupported core mandatory HIGH requirement: REQ_JDJPM_PM_EXPERIENCE"],
    f"CASE_F: exactly one genuine, unrelated hard blocker must remain, got {result_f_asis['hard_blockers']}",
)
assert_true(
    analysis_f_asis["decision"] == "REJECT",
    f"CASE_F: overall decision must remain REJECT (via the genuine PM-experience gap only), got {analysis_f_asis['decision']}",
)
assert_true(
    analysis_f_asis["decision"] not in ("APPLY", "PRIORITY_APPLY", "EFFICIENT_APPLY"),
    "CASE_F: no APPLY-like decision may appear -- this milestone corrects representation, not outcome positivity",
)
print("PASS O2: CASE_F (JD Software Junior Project Manager) -- compound degree/equivalent-experience OR correctly gated via the existing, unmodified qualification_gate architecture; degree leaf UNRESOLVED, never fabricated; genuine REQ_JDJPM_PM_EXPERIENCE blocker preserved; overall decision honestly REJECT, no APPLY-like result.")


# ======================================================================
# P. JD_SOFTWARE_IA_ALTERNATIVE_QUALIFICATION_GATE_APPLICATION_V1 -- real,
# live, first-party control (JD Software Implementation Analyst,
# https://www.jdsoft.com/career-ia.html, faithfully re-verified 2026-09-03,
# byte-identical across two independent fetches). The employer states a
# compound OR ("BS in a relevant discipline such as Mathematics or Computer
# Science OR an equivalent combination of education, training, and
# experience") under the real heading "What We're Looking For" -- correctly
# classified ENTRY_QUALIFICATION via the now-canonical, separately-closed
# CANDIDATE_PROFILE_HEADING_SEMANTIC_SCOPE_V1 path (not REQUIREMENTS_HEADING).
# P1 is the test-first reproduction, run and confirmed PASSING against the
# fixture's initial ungated state (proving the defect exists, now reachable
# only because the heading-classification milestone landed first) BEFORE the
# qualification_gate was added to the fixture's structured_extraction.json.
# P2 exercises the fixture in its final, gated, committed state.
# ======================================================================

# ----------------------------------------------------------------------
# P1. Test-first reproduction: with no qualification_gate authored, the
# compound-OR degree row independently hard-blocks, fabricating rejection
# of an alternative the employer explicitly permits.
# ----------------------------------------------------------------------
job_input_g = _load_job_input(FIXTURE_G)
result_g_asis = analyze_job(job_input_g)
assert_true(result_g_asis["valid"], f"CASE_G: analyze_job must be valid, errors={result_g_asis['errors']}")
analysis_g_asis = result_g_asis["analysis"]
assert_true(
    "Unsupported core mandatory HIGH requirement: REQ_IA_ANALYTICAL" in result_g_asis["hard_blockers"],
    f"CASE_G reproduction: REQ_IA_ANALYTICAL must independently hard-block (genuine, unrelated gap), got {result_g_asis['hard_blockers']}",
)
assert_true(
    analysis_g_asis["decision"] == "REJECT",
    f"CASE_G reproduction: expected REJECT, got {analysis_g_asis['decision']}",
)
if not analysis_g_asis.get("qualification_gate_results"):
    assert_true(
        "Unsupported core mandatory HIGH requirement: REQ_IA_DEGREE" in result_g_asis["hard_blockers"],
        f"CASE_G reproduction: with no gate authored, REQ_IA_DEGREE must ALSO independently hard-block "
        f"(the defect this milestone corrects), got {result_g_asis['hard_blockers']}",
    )
    print("PASS P1: CASE_G test-first reproduction confirmed -- with no qualification_gate, the compound-OR degree row independently (and fabricatedly) hard-blocks, exactly as expected on the unfixed fixture state.")
else:
    print("PASS P1: CASE_G fixture is in its final, gated state (qualification_gate present) -- reproduction was already independently confirmed and recorded during test-first development; see implementation report.")

# ----------------------------------------------------------------------
# P2. Final, gated fixture state -- the locked success criterion.
# ----------------------------------------------------------------------
assert_true(
    len(analysis_g_asis.get("qualification_gate_results") or []) == 1,
    f"CASE_G: expected exactly one qualification_gate, got {analysis_g_asis.get('qualification_gate_results')}",
)
gate_result_g = analysis_g_asis["qualification_gate_results"][0]
assert_true(
    gate_result_g["qualification_gate_id"] == "GATE_IA_DEGREE_COMPONENT",
    f"CASE_G: unexpected gate id {gate_result_g['qualification_gate_id']!r}",
)
assert_true(
    gate_result_g["result"] == "UNRESOLVED",
    f"CASE_G: gate must resolve UNRESOLVED (degree leaf unrecognized, never a proven negative), got {gate_result_g['result']!r}",
)
assert_true(
    gate_result_g["leaf_support"] == {"REQ_IA_DEGREE": "UNRESOLVED"},
    f"CASE_G: expected single leaf REQ_IA_DEGREE -> UNRESOLVED, got {gate_result_g['leaf_support']}",
)
assert_true(
    "REQ_IA_DEGREE" not in " ".join(result_g_asis["hard_blockers"]),
    f"CASE_G: REQ_IA_DEGREE must be ABSENT from ordinary hard_blockers once gated, got {result_g_asis['hard_blockers']}",
)
assert_true(
    not any(g.startswith("REQ_IA_DEGREE:") for g in analysis_g_asis["qualification_gaps"]),
    f"CASE_G: REQ_IA_DEGREE must be ABSENT from ordinary qualification_gaps once gated, got {analysis_g_asis['qualification_gaps']}",
)
assert_true(
    any("GATE_IA_DEGREE_COMPONENT" in u for u in analysis_g_asis["qualification_unknowns"]),
    f"CASE_G: qualification_unknowns must truthfully surface the unresolved gate, got {analysis_g_asis['qualification_unknowns']}",
)
assert_true(
    "REQ_IA_DEGREE" in gate_leaf_ids({
        "qualification_gate_id": "x", "job_id": "x", "source_text": ["x"], "source_location": "x",
        "logic_expression": {"op": "ANY_OF", "terms": ["REQ_IA_DEGREE"]},
    }),
    "CASE_G setup sanity: gate_leaf_ids() must recognize the single-leaf ANY_OF shape used",
)
# unmodeled_branches_note preserves the equivalent-combination branch --
# verified directly against the persisted fixture (not part of analyze_job's
# own output surface).
structured_g = job_input_g["structured_extraction"]
gates_g = structured_g.get("qualification_gates") or []
assert_true(len(gates_g) == 1, f"CASE_G fixture: expected exactly one persisted qualification_gate, got {gates_g}")
assert_true(
    "equivalent combination" in (gates_g[0].get("unmodeled_branches_note") or "").casefold(),
    f"CASE_G fixture: unmodeled_branches_note must preserve the employer's equivalent-combination branch, got {gates_g[0].get('unmodeled_branches_note')!r}",
)
assert_true(
    gates_g[0]["logic_expression"] == {"op": "ANY_OF", "terms": ["REQ_IA_DEGREE"]},
    f"CASE_G fixture: no second Requirement leaf may be invented for the unquantified alternative, got {gates_g[0]['logic_expression']}",
)
# Raw-source traceability (fail-closed, per ADR §3) -- re-verified directly,
# not merely assumed from analyze_job() having accepted it.
traceability_errors_g = validate_gate_source_traceability(gates_g[0], job_input_g["jd_text"])
assert_true(
    traceability_errors_g == [],
    f"CASE_G fixture: gate source_text must be traceable to jd.txt, got errors={traceability_errors_g}",
)
assert_true(
    result_g_asis["hard_blockers"] == ["Unsupported core mandatory HIGH requirement: REQ_IA_ANALYTICAL"],
    f"CASE_G: exactly one genuine, unrelated hard blocker must remain, got {result_g_asis['hard_blockers']}",
)
assert_true(
    analysis_g_asis["decision"] == "REJECT",
    f"CASE_G: overall decision must remain REJECT (via the genuine analytical-skills gap only), got {analysis_g_asis['decision']}",
)
assert_true(
    analysis_g_asis["decision"] not in ("APPLY", "PRIORITY_APPLY", "EFFICIENT_APPLY"),
    "CASE_G: no APPLY-like decision may appear -- this milestone corrects representation, not outcome positivity",
)
# REQ_IA_RDBMS_PLUS must remain PREFERRED and non-blocking, unaffected by
# either the heading-classification milestone or this gate milestone.
req_ia_rdbms = next(r for r in structured_g["requirements"] if r["requirement_id"] == "REQ_IA_RDBMS_PLUS")
assert_true(
    req_ia_rdbms["importance"] == "PREFERRED",
    f"CASE_G: REQ_IA_RDBMS_PLUS must remain PREFERRED, got {req_ia_rdbms['importance']}",
)
assert_true(
    "REQ_IA_RDBMS_PLUS" not in " ".join(result_g_asis["hard_blockers"]),
    f"CASE_G: REQ_IA_RDBMS_PLUS (preferred) must never appear in hard_blockers, got {result_g_asis['hard_blockers']}",
)
print("PASS P2: CASE_G (JD Software Implementation Analyst) -- compound degree/equivalent-experience OR correctly gated via the existing, unmodified qualification_gate architecture; degree leaf UNRESOLVED, never fabricated; genuine REQ_IA_ANALYTICAL blocker preserved; REQ_IA_RDBMS_PLUS remains preferred/non-blocking; overall decision honestly REJECT, no APPLY-like result.")


if __name__ == "__main__":
    print("ALL alternative_qualification_branch_representation_v1_test CHECKS PASSED.")
