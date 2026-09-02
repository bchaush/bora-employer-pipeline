"""P0 causal integration invariant tests for
REPRODUCIBLE_CONSEQUENTIAL_ASSURANCE_BASELINE_V1, per
docs/decisions/ADR-REPRODUCIBLE-CONSEQUENTIAL-ASSURANCE-BASELINE-V1.md §7.

This file closes missing INTEGRATION-LEVEL causal-assurance gaps only. It
does not duplicate invariants already directly and adequately defended by
existing closed-milestone tests (posting_state_decision_wiring_v1_test.py,
alternative_qualification_branch_representation_v1_test.py, and others),
which remain mandatory Phase-2 coverage anchors in their own right (see
scripts/verify_assurance_baseline.py). In particular, the following remain
preserved there, not re-authored here: posting-state routing never
rewriting qualification truth; NONE_TRAP as the only gated path to
BLOCKED_BY_MATCHING_POLICY; NO_CAPABILITY_OVERLAP/NO_CAPABILITY_COVERAGE
remaining UNRESOLVED; missing/unrecognized evaluation_path never becoming
favorable.

Sections (ADR §7 A-E):
  A. Gated Requirement leaves cannot independently re-enter hard_blockers,
     qualification_gaps, or qualification_unknowns (a BLOCKED_BY_MATCHING_
     POLICY gate scenario, plus an ungrouped control).
  A2. Gated Requirement leaves cannot independently re-enter the
     mandatory/HIGH-NONE COUNTING path specifically -- an UNRESOLVED (not
     BLOCKED) gate scenario, isolating decide_lane_and_decision()'s own
     gated-exclusion in its `mandatory`/`preferred` list comprehensions
     from detect_hard_blockers()'s separate per-row skip, plus a
     comparable ungrouped control.
  B. Invalid/unavailable trusted Claim or Evidence repository state cannot
     produce or improve a consequential decision.
  C. Invalid qualification-gate Requirement references fail before
     consequential decision/routing.
  D. Invalid qualification-gate source provenance fails before
     consequential decision/routing.
  E. Application Gate truth remains independent from qualification-gate
     result, through existing public interfaces, zero production change.

Tests assert causal state (decision, hard_blockers, qualification_gate_
results, evidence_matches/evaluation_path, absence of forbidden effects),
not only a final enum. No production logic is modified or rewritten to
make any test convenient; no threshold is altered.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_gate import evaluate_application_question  # noqa: E402
from job_analysis import analyze_job  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def _row(
    req_id: str,
    text: str,
    *,
    importance: str = "MANDATORY",
    relevance: str = "HIGH",
) -> dict:
    """A minimal, canonical, ENTRY_QUALIFICATION-classified Requirement row --
    the exact field shape required by requirement_normalize.py's
    SOURCE_SEMANTIC_ROLE_NOT_MIGRATED ingestion gate, mirrored from a real
    fixture row (fixtures/jobs/CASE_D_MBTA_DIRECT_APPLICATION_ANALYST/
    structured_extraction.json, REQ_D_DEGREE)."""
    return {
        "requirement_id": req_id,
        "job_id": "PLACEHOLDER",
        "text": text,
        "category": "OTHER",
        "importance": importance,
        "seniority_implication": None,
        "technology": [],
        "experience_level": None,
        "domain": None,
        "relevance": relevance,
        "source_text": text,
        "source_location": "Minimum Qualifications",
        "source_semantic_role": "ENTRY_QUALIFICATION",
        "source_semantic_role_basis": (
            "P0_CAUSAL_INVARIANTS_V1 synthetic fixture: explicit, "
            "test-authored ENTRY_QUALIFICATION classification."
        ),
        "explicit_prerequisite_language_present": False,
        "duplicated_under_requirements": False,
        "source_semantic_role_classifier_version": "SOURCE_SEMANTIC_ROLE_CLASSIFIER_V1",
    }


def _gate(gate_id: str, expr: dict, source_text: list[str]) -> dict:
    return {
        "qualification_gate_id": gate_id,
        "job_id": "JOB_SYNTH",
        "source_text": source_text,
        "source_location": "Minimum Qualifications",
        "logic_expression": expr,
    }


def _job_input(
    *,
    jd_text: str,
    requirements: list[dict],
    gates: list[dict] | None = None,
    fixture_key: str,
) -> dict:
    return {
        "company": "P0 Synthetic Co",
        "role": "P0 Synthetic Role",
        "jd_text": jd_text,
        "fixture_key": fixture_key,
        "structured_extraction": {
            "requirements": requirements,
            "qualification_gates": gates or [],
        },
    }


# ======================================================================
# A. Gated Requirement leaves cannot independently re-enter
#    hard_blockers / mandatory-NONE counts / qualification_gaps /
#    qualification_unknowns. Two requirements are grouped under one gate
#    (one NONE_TRAP leg, one NO_CAPABILITY_OVERLAP leg -> gate resolves
#    BLOCKED_BY_MATCHING_POLICY); a THIRD, structurally identical
#    ungrouped requirement is left OUTSIDE the gate as a live control,
#    proving the asymmetry (ADR §10) is exactly what is exercised, not
#    accidentally masked by a global change.
# ======================================================================
JD_A = (
    "Minimum Qualifications: Bachelor's degree required. "
    "Salesforce administration experience required. "
    "Additional requirement: Salesforce administration experience required "
    "for reporting."
)

req_g1 = _row("REQ_G1", "Bachelor's degree required")
req_g2 = _row("REQ_G2", "Salesforce administration experience required")
req_ungrouped = _row(
    "REQ_UNGROUPED", "Salesforce administration experience required"
)

gate_a = _gate(
    "GATE_TEST_A",
    {"op": "ALL_OF", "terms": ["REQ_G1", "REQ_G2"]},
    source_text=[
        "Bachelor's degree required.",
        "Salesforce administration experience required.",
    ],
)

result_a = analyze_job(
    _job_input(
        jd_text=JD_A,
        requirements=[req_g1, req_g2, req_ungrouped],
        gates=[gate_a],
        fixture_key="P0_A",
    ),
    claim_index={},
    evidence_index={},
)
assert_true(result_a["valid"], f"A: analyze_job must be valid, errors={result_a['errors']}")
analysis_a = result_a["analysis"]

gate_results_a = {g["qualification_gate_id"]: g for g in analysis_a["qualification_gate_results"]}
assert_true(
    gate_results_a["GATE_TEST_A"]["result"] == "BLOCKED_BY_MATCHING_POLICY",
    f"A: expected gate BLOCKED_BY_MATCHING_POLICY, got {gate_results_a['GATE_TEST_A']['result']!r}",
)

hard_blockers_a = result_a["hard_blockers"]
# A gated leaf may legitimately appear only as leaf-diagnostic content
# INSIDE the gate's own single blocker string (e.g. "branch leaf states:
# {'REQ_G1': ...}") -- it must never independently re-enter as its OWN
# standalone ordinary-blocker entry (the exact wording
# detect_hard_blockers() would have produced had the row not been gated).
assert_true(
    "Unsupported core mandatory HIGH requirement: REQ_G1" not in hard_blockers_a,
    f"A: gated leaf REQ_G1 must never independently re-enter hard_blockers as its own ordinary blocker, got {hard_blockers_a}",
)
assert_true(
    "Unsupported core platform specialization (mandatory HIGH): REQ_G2" not in hard_blockers_a,
    f"A: gated leaf REQ_G2 must never independently re-enter hard_blockers as its own ordinary blocker, got {hard_blockers_a}",
)
assert_true(
    any(b.startswith("GATE_TEST_A:") for b in hard_blockers_a),
    f"A: gate's own single blocker entry must appear in hard_blockers, got {hard_blockers_a}",
)
assert_true(
    any("REQ_UNGROUPED" in b for b in hard_blockers_a),
    f"A: ungrouped control requirement must still independently hard-block, got {hard_blockers_a}",
)
gate_blocker_count = sum(1 for b in hard_blockers_a if b.startswith("GATE_TEST_A:"))
assert_true(
    gate_blocker_count == 1,
    f"A: exactly one blocker entry per gate, never one per underlying leaf, got count={gate_blocker_count}",
)

qual_gaps_a = analysis_a["qualification_gaps"]
assert_true(
    not any(g.startswith("REQ_G1:") for g in qual_gaps_a),
    f"A: REQ_G1 must not independently emit a qualification_gaps entry, got {qual_gaps_a}",
)
assert_true(
    not any(g.startswith("REQ_G2:") for g in qual_gaps_a),
    f"A: REQ_G2 must not independently emit a qualification_gaps entry, got {qual_gaps_a}",
)
qual_unknowns_a = analysis_a["qualification_unknowns"]
assert_true(
    not any(u.startswith("REQ_G1:") for u in qual_unknowns_a),
    f"A: REQ_G1 must not independently emit a qualification_unknowns entry, got {qual_unknowns_a}",
)
assert_true(
    not any(u.startswith("REQ_G2:") for u in qual_unknowns_a),
    f"A: REQ_G2 must not independently emit a qualification_unknowns entry, got {qual_unknowns_a}",
)
assert_true(
    any(g.startswith("REQ_UNGROUPED:") for g in qual_gaps_a),
    f"A: ungrouped control requirement's own independent gap output must be unaffected, got {qual_gaps_a}",
)
assert_true(
    analysis_a["decision"] == "REJECT",
    f"A: decision must be REJECT (via the gate blocker), got {analysis_a['decision']}",
)
print("PASS A: gated Requirement leaves cannot independently re-enter hard_blockers/gaps/unknowns; ungrouped control unaffected.")


# ======================================================================
# A2. Gated Requirement leaves cannot independently re-enter the
#    mandatory/HIGH-NONE COUNTING path specifically (Cursor M-01 narrow
#    correction). Section A's gate resolves BLOCKED_BY_MATCHING_POLICY,
#    so decide_lane_and_decision() exits via `blockers` before the
#    high_none-sensitive branch (job_decision.py's `if high_none >= 1:
#    ... REJECT` check) is ever materially exercised -- a regression
#    isolated to the SEPARATE gated-exclusion inside decide_lane_and_
#    decision()'s own `mandatory`/`preferred` list comprehensions (as
#    distinct from detect_hard_blockers()'s own, separately-tested,
#    per-row gated skip) could escape Section A undetected.
#
#    This gate is deliberately built to resolve UNRESOLVED (a single-leaf
#    ALL_OF over one NO_CAPABILITY_OVERLAP leaf -- never NONE_TRAP), so no
#    BLOCKED_BY_MATCHING_POLICY blocker exists at all; the only other row
#    is PREFERRED (never mandatory-counted), so `mandatory` is empty
#    if-and-only-if the gated leaf is correctly excluded. Execution then
#    genuinely reaches line-437-equivalent high_none logic instead of
#    returning early through `blockers`.
# ======================================================================
JD_A2 = "Minimum Qualifications: Bachelor's degree required. Preferred: Excel skills a plus."

req_g1_a2 = _row("REQ_G1_A2", "Bachelor's degree required")
req_pref_a2 = _row(
    "REQ_PREF_A2", "Excel skills a plus", importance="PREFERRED", relevance="HIGH"
)
gate_a2 = _gate(
    "GATE_TEST_A2",
    {"op": "ALL_OF", "terms": ["REQ_G1_A2"]},
    source_text=["Bachelor's degree required."],
)

result_a2_gated = analyze_job(
    _job_input(
        jd_text=JD_A2,
        requirements=[req_g1_a2, req_pref_a2],
        gates=[gate_a2],
        fixture_key="P0_A2_GATED",
    ),
    claim_index={},
    evidence_index={},
)
assert_true(result_a2_gated["valid"], f"A2: analyze_job must be valid, errors={result_a2_gated['errors']}")
analysis_a2_gated = result_a2_gated["analysis"]

gate_results_a2 = {
    g["qualification_gate_id"]: g for g in analysis_a2_gated["qualification_gate_results"]
}
assert_true(
    gate_results_a2["GATE_TEST_A2"]["result"] == "UNRESOLVED",
    f"A2 setup: gate must resolve UNRESOLVED (not BLOCKED_BY_MATCHING_POLICY), "
    f"got {gate_results_a2['GATE_TEST_A2']['result']!r}",
)
assert_true(
    result_a2_gated["hard_blockers"] == [],
    f"A2 setup: hard_blockers must be empty so execution reaches the "
    f"high_none-sensitive decision branch rather than exiting early via "
    f"`blockers`, got {result_a2_gated['hard_blockers']}",
)
# The airtight causal proof: reaching WATCH via the not-family-fit /
# none==0 / high_none==0 / mandatory-empty branch is only possible if the
# gated leaf was excluded from decide_lane_and_decision()'s own
# `mandatory` list comprehension. Had that specific exclusion regressed,
# REQ_G1_A2 (MANDATORY, relevance HIGH, result NONE) would have pushed
# high_none to 1 and produced REJECT with the exact rationale text below
# instead.
assert_true(
    analysis_a2_gated["decision"] == "WATCH",
    f"A2: gated leaf must not push high_none >= 1; expected WATCH via the "
    f"not-family-fit/no-gap branch, got {analysis_a2_gated['decision']} "
    f"(rationale={analysis_a2_gated['decision_rationale']!r})",
)
assert_true(
    "core mandatory HIGH requirement has NONE coverage" not in analysis_a2_gated["decision_rationale"],
    f"A2: decision_rationale must never cite the high_none-specific REJECT "
    f"rationale for a gated leaf, got {analysis_a2_gated['decision_rationale']!r}",
)
assert_true(
    "outside supported/adjacent families" in analysis_a2_gated["decision_rationale"],
    f"A2: decision_rationale must reflect only the legitimate non-gated "
    f"routing path, got {analysis_a2_gated['decision_rationale']!r}",
)
print("PASS A2 (gated): gated leaf cannot independently push high_none >= 1 in decide_lane_and_decision()'s own mandatory-list counting.")

# Comparable ungrouped control: the SAME requirement (same text, same
# MANDATORY/HIGH/ENTRY_QUALIFICATION shape), with no gate at all, must
# still be causally significant to the ordinary routing path -- proving
# the gate (not some other incidental property of the requirement) is
# what suppressed its effect above.
req_g1_a2_control = _row("REQ_G1_A2", "Bachelor's degree required")
req_pref_a2_control = _row(
    "REQ_PREF_A2", "Excel skills a plus", importance="PREFERRED", relevance="HIGH"
)
result_a2_ungrouped = analyze_job(
    _job_input(
        jd_text=JD_A2,
        requirements=[req_g1_a2_control, req_pref_a2_control],
        gates=[],
        fixture_key="P0_A2_UNGROUPED",
    ),
    claim_index={},
    evidence_index={},
)
assert_true(
    result_a2_ungrouped["valid"], f"A2 control: analyze_job must be valid, errors={result_a2_ungrouped['errors']}"
)
assert_true(
    result_a2_ungrouped["analysis"]["decision"] == "REJECT",
    f"A2 control: the identical requirement, left ungrouped, must be "
    f"causally significant to routing (REJECT), got "
    f"{result_a2_ungrouped['analysis']['decision']!r} -- if this is not "
    f"REJECT, the gated scenario above proves nothing about suppression",
)
print("PASS A2 (ungrouped control): the identical requirement, left ungrouped, is causally significant (REJECT) -- confirming the gate above is what suppressed its effect, not some other property of the requirement.")


# ======================================================================
# B. Invalid/unavailable trusted Claim or Evidence repository state
#    cannot produce or improve a consequential decision -- analyze_job()
#    must fail closed (valid=False, analysis=None, empty hard_blockers),
#    never silently falling back to an empty/optimistic trusted index that
#    could produce or improve a decision.
# ======================================================================
NONEXISTENT_ROOT = ROOT / "this_path_does_not_exist_p0_causal_invariants"
assert_true(not NONEXISTENT_ROOT.exists(), "B: sanity check -- synthetic missing root must not exist")

req_b = _row("REQ_B", "Bachelor's degree required")
job_input_b = _job_input(
    jd_text="Minimum Qualifications: Bachelor's degree required.",
    requirements=[req_b],
    fixture_key="P0_B",
)

result_b_claim = analyze_job(
    job_input_b,
    evidence_index={},
    claim_root=NONEXISTENT_ROOT,
)
assert_true(
    result_b_claim["valid"] is False,
    "B: analyze_job must fail closed when the trusted Claim repository root is invalid",
)
assert_true(
    result_b_claim["analysis"] is None,
    "B: an invalid trusted Claim repository must never produce a partial/optimistic analysis",
)
assert_true(
    result_b_claim.get("hard_blockers", []) == [],
    "B: an invalid trusted Claim repository must never produce a favorable/empty-blocker decision surface",
)
assert_true(
    any(e.get("code") == "CLAIM_REPOSITORY_INVALID" for e in result_b_claim["errors"]),
    f"B: expected CLAIM_REPOSITORY_INVALID error, got {result_b_claim['errors']}",
)

result_b_evidence = analyze_job(
    job_input_b,
    claim_index={},
    evidence_root=NONEXISTENT_ROOT,
)
assert_true(
    result_b_evidence["valid"] is False,
    "B: analyze_job must fail closed when the trusted Evidence repository root is invalid",
)
assert_true(
    result_b_evidence["analysis"] is None,
    "B: an invalid trusted Evidence repository must never produce a partial/optimistic analysis",
)
assert_true(
    any(e.get("code") == "EVIDENCE_REPOSITORY_INVALID" for e in result_b_evidence["errors"]),
    f"B: expected EVIDENCE_REPOSITORY_INVALID error, got {result_b_evidence['errors']}",
)
print("PASS B: invalid/unavailable trusted Claim or Evidence repository state fails closed and cannot produce or improve a decision.")


# ======================================================================
# C. Invalid qualification-gate Requirement references fail before
#    consequential decision/routing -- a gate referencing a
#    requirement_id absent from the job's own Requirement rows must stop
#    the whole analyze_job() call closed (valid=False, analysis=None), not
#    merely omit that one gate from evaluation.
# ======================================================================
req_c = _row("REQ_C_REAL", "Bachelor's degree required")
gate_c = _gate(
    "GATE_TEST_C",
    {"op": "ALL_OF", "terms": ["REQ_C_REAL", "REQ_C_DOES_NOT_EXIST"]},
    source_text=["Bachelor's degree required."],
)
result_c = analyze_job(
    _job_input(
        jd_text="Minimum Qualifications: Bachelor's degree required.",
        requirements=[req_c],
        gates=[gate_c],
        fixture_key="P0_C",
    ),
    claim_index={},
    evidence_index={},
)
assert_true(
    result_c["valid"] is False,
    "C: analyze_job must fail closed when a gate references an unknown requirement_id",
)
assert_true(
    result_c["analysis"] is None,
    "C: an unknown gate requirement reference must never reach consequential decision/routing",
)
assert_true(
    any(e.get("code") == "QUALIFICATION_GATE_UNKNOWN_REQUIREMENT_ID" for e in result_c["errors"]),
    f"C: expected QUALIFICATION_GATE_UNKNOWN_REQUIREMENT_ID, got {result_c['errors']}",
)
print("PASS C: invalid qualification-gate Requirement references fail before consequential decision/routing.")


# ======================================================================
# D. Invalid qualification-gate source provenance fails before
#    consequential decision/routing -- a gate whose source_text excerpt is
#    not an exact whitespace-normalized substring of jd_text must stop the
#    whole analyze_job() call closed, per the ADR §3 deterministic
#    traceability rule.
# ======================================================================
req_d = _row("REQ_D_REAL", "Bachelor's degree required")
gate_d = _gate(
    "GATE_TEST_D",
    {"op": "ALL_OF", "terms": ["REQ_D_REAL"]},
    source_text=["This exact sentence is not present anywhere in the captured jd_text."],
)
result_d = analyze_job(
    _job_input(
        jd_text="Minimum Qualifications: Bachelor's degree required.",
        requirements=[req_d],
        gates=[gate_d],
        fixture_key="P0_D",
    ),
    claim_index={},
    evidence_index={},
)
assert_true(
    result_d["valid"] is False,
    "D: analyze_job must fail closed when a gate's source_text is not traceable to jd_text",
)
assert_true(
    result_d["analysis"] is None,
    "D: untraceable gate source provenance must never reach consequential decision/routing",
)
assert_true(
    any(e.get("code") == "QUALIFICATION_GATE_SOURCE_NOT_TRACEABLE" for e in result_d["errors"]),
    f"D: expected QUALIFICATION_GATE_SOURCE_NOT_TRACEABLE, got {result_d['errors']}",
)
print("PASS D: invalid qualification-gate source provenance fails before consequential decision/routing.")


# ======================================================================
# E. Application Gate truth remains independent from qualification-gate
#    result, through existing public interfaces, with zero production
#    change.
#
#    E1: structural proof -- evaluate_application_question()'s public
#    signature has no parameter through which a qualification_gate_result
#    could be supplied; passing one raises TypeError, proving the function
#    cannot consume it even if a caller tried.
#
#    E2: behavioral proof -- run analyze_job() on a job whose
#    qualification_gate resolves BLOCKED_BY_MATCHING_POLICY (same setup as
#    Section A), then separately evaluate an unrelated synthetic
#    ApplicationQuestion against the SAME trusted indexes; its result is
#    derived independently (via match_clause/evaluate_expression on the
#    question's own clauses) and is untouched by the gate's
#    BLOCKED_BY_MATCHING_POLICY result.
# ======================================================================
try:
    evaluate_application_question(
        {"application_question_id": "AQ_P0", "question_type": "YES_NO", "clauses": []},
        claim_index={},
        evidence_index={},
        evaluated_at="2026-09-02",
        qualification_gate_result="SUPPORTED",  # type: ignore[call-arg]
    )
    assert_true(False, "E1: evaluate_application_question must not accept a qualification_gate_result argument")
except TypeError:
    pass
print("PASS E1: evaluate_application_question() has no parameter through which a qualification_gate_result could be consumed.")

assert_true(
    gate_results_a["GATE_TEST_A"]["result"] == "BLOCKED_BY_MATCHING_POLICY",
    "E2 setup: reusing Section A's BLOCKED_BY_MATCHING_POLICY gate result",
)
synthetic_question = {
    "application_question_id": "AQ_P0_UNRELATED",
    "question_type": "YES_NO",
    "clauses": [
        {
            "clause_id": "C1",
            "clause_text": "Do you have experience with completely unrelated topic XYZ?",
        }
    ],
}
evaluation_e2 = evaluate_application_question(
    synthetic_question,
    claim_index={},
    evidence_index={},
    evaluated_at="2026-09-02",
)
assert_true(
    not any("qualification_gate" in str(k).lower() for k in evaluation_e2.keys()),
    f"E2: ApplicationQuestion evaluation output must carry no qualification_gate-derived field, got keys={list(evaluation_e2.keys())}",
)
assert_true(
    evaluation_e2["predicate_result"] != "FALSE",
    "E2: an unrelated, unsupported clause must resolve UNCERTAIN (no evidence), never a fabricated FALSE borrowed from an unrelated gate's BLOCKED_BY_MATCHING_POLICY result",
)
print("PASS E2: Application Gate evaluation is computed independently of, and unaffected by, an unrelated qualification-gate BLOCKED_BY_MATCHING_POLICY result.")

print("ALL P0 CAUSAL INVARIANT TESTS PASSED")
