"""Regression tests for PROCESS_MAPPING_COMPOUND_COMPLETION_V1.

PROCESS_MAPPING_COMPOUND_READ_ONLY_ADJUDICATION_V1 proved, by direct code
inspection (not assumption), that requirement_match.py's multi-capability
inference and STRONG/SUPPORTED/PARTIAL subset-check (match_requirement())
already correctly demote a Requirement to PARTIAL when its inferred
capability set is not fully covered by the best-overlapping Claim's
capabilities -- no new compound architecture is needed. What was missing
was a truthful capability for CASE_D's distinct second duty ("identify
opportunities for optimization or automation within assigned
applications"), which no existing capability (including the narrow,
operational-governance-scoped workflow_automation) represents.

This milestone adds exactly one new, narrowly-scoped REQUIREMENT
capability, process_optimization_opportunity_identification, meaning only
the explicit analytical act of identifying/evaluating where a process,
workflow, or application could be optimized or automated -- NOT
implementing automation, NOT process mapping alone, NOT generic
improvement language. It is deliberately assigned to ZERO Claims: Bora has
no current evidence establishing this analytical duty, and implementing
automation (CLAIM_WW_002/WW_004) does not prove independently identifying
the opportunity for it.

With this capability added, CASE_D's real Requirement (already frozen,
unmodified) now infers {process_mapping,
process_optimization_opportunity_identification}; the best-overlapping
Claim (CLAIM_WW_006) covers only process_mapping, so the existing,
unmodified subset-check in match_requirement() automatically produces
PARTIAL -- no matcher change, no fixture change, no Claim change.

Exercises real production code (requirement_match.py, job_analysis.py) --
no logic is duplicated here.
"""

from __future__ import annotations

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


NEW_TAG = "process_optimization_opportunity_identification"
PM_TAG = "process_mapping"

ev_result = validate_evidence_repository()
assert_true(ev_result["valid"] is True, "evidence repository must be valid")
cl_result = validate_claim_repository()
assert_true(cl_result["valid"] is True, "claim repository must be valid")
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = cl_result["index"]
REUSABLE = load_reusable_claims(CLAIM_INDEX, EVIDENCE_INDEX)


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


def _match(text: str) -> dict:
    return match_requirement(
        job_id="JOB_X",
        requirement=_req(text),
        reusable_claims=REUSABLE,
        evidence_index=EVIDENCE_INDEX,
        match_index=0,
    )


CASE_D_TEXT = (
    "Proven ability to map and document complex business processes and "
    "identify opportunities for optimization or automation within "
    "assigned applications"
)
CASE_E_TEXT = "Ability to map and document complex business processes"


# ======================================================================
# B. Pre-fix / defect-characterization control -- CASE_D's real text must
#    infer the new tag once implemented, and CASE_E must remain STRONG
#    throughout (control, not expected to change with this milestone).
# ======================================================================
case_e_match = _match(CASE_E_TEXT)
assert_true(
    case_e_match["result"] == "STRONG" and case_e_match.get("claim_ids") == ["CLAIM_WW_006"],
    f"CASE_E control must remain STRONG via CLAIM_WW_006 throughout, got {case_e_match}",
)
print("PASS CONTROL: CASE_E ('Ability to map and document complex business processes') remains STRONG via CLAIM_WW_006, unaffected by this milestone.")


# ======================================================================
# E. Required positive cases -- explicit analytical identification of
#    optimization/automation opportunities.
# ======================================================================
required_positives = (
    # PROCESS_OPTIMIZATION_OPPORTUNITY_GRAMMAR_BOUNDED_CORRECTION_V1: the
    # bare, unanchored phrase "identify opportunities for optimization or
    # automation" (no process/workflow/application anchor, no trailing
    # "within application(s)" tail) is deliberately no longer a positive
    # -- it is exactly the ungrounded shape Cursor's BLOCKING FINDING #1
    # targets. The real CASE_D/component-B wording always carries the
    # "within assigned applications" tail, which is what supplies the
    # required anchor; that tail is now included here explicitly.
    "identify opportunities for optimization or automation within assigned applications",
    "identify opportunities for process optimization",
    "identify opportunities for workflow automation",
    "identify opportunities to optimize or automate business processes",
    "identify areas where business processes can be optimized or automated",
)
for text in required_positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(NEW_TAG in caps, f"{text!r} must infer {NEW_TAG}")
print("PASS E: all 5 required positive phrasings infer process_optimization_opportunity_identification.")


# ======================================================================
# F. Required negative controls -- performing/implementing/using
#    optimization or automation, or generic opportunity language, must
#    NOT infer the new analytical-identification capability.
# ======================================================================
required_negatives = (
    "automate business processes",
    "workflow automation",
    "process automation",
    "optimize business processes",
    "process optimization",
    "process improvement",
    "continuous improvement",
    "implemented workflow automation",
    "built an automated workflow",
    "process mapping",
    "map and document complex business processes",
    "automation software",
    "automation platform",
    "optimization tools",
    "identify application issues",
    "identify business opportunities",
    "identify opportunities within assigned applications",
    # Self-directed adversarial probe: a wide "identify areas where ...
    # automation ..." gap without the required "can/could/may/might be"
    # passive-construction anchor must not false-fire on an unrelated
    # noun-phrase mention of "automation".
    "identify areas where the automation platform pricing needs review",
)
for text in required_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        NEW_TAG not in caps,
        f"{text!r} must NOT infer {NEW_TAG} -- performing/implementing/using optimization or automation (or generic opportunity language) is not the same as explicitly identifying the opportunity for it",
    )
print("PASS F: all required negative controls (including a self-directed overmatch probe on the wide 'areas where' construction) correctly do not infer the new capability.")


# ======================================================================
# PROCESS_OPTIMIZATION_OPPORTUNITY_GRAMMAR_BOUNDED_CORRECTION_V1
# (Cursor external-review BLOCKING FINDING #1): the original grammar's
# first branch required only "identify(ing) opportunit(y|ies) for/to
# [<=3 words] optimiz.../automat..." with no requirement that the thing
# being optimized/automated actually be a business process, workflow, or
# application -- generic commercial/financial/unrelated "optimization"
# language false-fired. The correction requires a genuine
# process/workflow/business-process/application anchor: either
# immediately adjacent to the optimiz/automat word (noun-compound form,
# e.g. "process optimization"; or verb-object form, e.g. "optimize or
# automate business processes"), or via an explicit trailing "within
# .../application(s)" tail for the generic "optimization or automation"
# phrasing CASE_D's real sentence actually uses. "business"/"automation"/
# "optimization" alone are NEVER treated as a sufficient anchor.
# ======================================================================
cursor_false_positive_negatives = (
    "identify business opportunities for automation companies",
    "identify sales opportunities for automation software",
    "identify opportunities for customers using automation",
    "identify opportunities for optimization software",
    "identify opportunities for automation platform sales",
    "identify opportunities to optimize revenue",
    "identify opportunities for cost optimization",
    "identify opportunities for workforce optimization",
    "identify opportunities for search engine optimization",
    "identify opportunities for portfolio optimization",
    "identify opportunities for model optimization",
    "identify areas where the automation platform can be optimized",
)
for text in cursor_false_positive_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        NEW_TAG not in caps,
        f"{text!r} must NOT infer {NEW_TAG} -- no genuine business-process/workflow/application anchor is present; a bare 'opportunities for/areas where ... optimization/automation' shape is not sufficient (Cursor external-review BLOCKING FINDING #1)",
    )
print("PASS CURSOR-NEG: all 12 Cursor-identified generic optimization/automation false positives are correctly excluded -- a genuine process/workflow/application anchor is now required.")


# ======================================================================
# Additional bounded positive variants (Section F of the correction
# instruction) -- must still infer the new capability where a genuine
# anchor is grammatically present.
# ======================================================================
additional_bounded_positives = (
    "identify opportunities to automate workflows",
    "identify areas where the application can be automated",
)
for text in additional_bounded_positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(NEW_TAG in caps, f"{text!r} must infer {NEW_TAG} (genuine workflow/application anchor present)")
print("PASS CURSOR-POS: additional bounded positive variants ('automate workflows', 'the application can be automated') still correctly infer the new capability.")


# ======================================================================
# process_mapping's existing patch/tests remain intact -- unaffected by
# this milestone (no rewrite, no style change).
# ======================================================================
pm_negatives = (
    "process mapping software",
    "process mapping tool",
    "process mapping platform",
    "map data fields between systems",
    "map application dependencies",
    "document software processes",
    "review existing business processes",
    "create geographic maps for business locations",
)
for text in pm_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(PM_TAG not in caps, f"pre-existing process_mapping negative {text!r} regressed: {caps}")
print("PASS PM-REGRESSION: pre-existing process_mapping adversarial controls remain intact, unmodified.")


# ======================================================================
# D. Candidate side must remain empty -- no Claim carries the new tag.
# ======================================================================
for claim_id, caps_map in _CLAIM_CAPABILITIES.items():
    assert_true(
        NEW_TAG not in caps_map,
        f"{claim_id} must NOT carry {NEW_TAG} -- no current approved evidence establishes independent identification of optimization/automation opportunities",
    )
print("PASS D: no existing Claim (including CLAIM_WW_002/CLAIM_WW_004/CLAIM_WW_006) carries the new capability -- candidate-side support remains truthfully empty.")


# ======================================================================
# H. Isolated component-B result -- with the new tag inferred but zero
#    Claim support, the isolated clause must not resolve STRONG.
# ======================================================================
component_b_text = "identify opportunities for optimization or automation within assigned applications"
component_b_caps = infer_requirement_capabilities(_req(component_b_text))
assert_true(NEW_TAG in component_b_caps, f"component-B text must infer {NEW_TAG}, got {component_b_caps}")
component_b_match = _match(component_b_text)
assert_true(
    component_b_match["result"] not in {"STRONG", "SUPPORTED"},
    f"isolated component-B text must NOT resolve STRONG/SUPPORTED with zero Claim support, got {component_b_match['result']}",
)
print(f"PASS H: isolated component-B text infers {NEW_TAG} and resolves {component_b_match['result']} (not STRONG/SUPPORTED) with zero current Claim support.")


# ======================================================================
# G. CASE_D compound requirement -- must resolve PARTIAL via CLAIM_WW_006,
#    with the missing new capability named in the explanation/transfer
#    note, not silently absorbed into a false STRONG.
# ======================================================================
case_d_caps = infer_requirement_capabilities(_req(CASE_D_TEXT))
assert_true(
    {PM_TAG, NEW_TAG}.issubset(case_d_caps),
    f"CASE_D real requirement text must infer both process_mapping and {NEW_TAG}, got {sorted(case_d_caps)}",
)
case_d_match = _match(CASE_D_TEXT)
assert_true(
    case_d_match["result"] == "PARTIAL",
    f"CASE_D real requirement text must resolve PARTIAL (not STRONG -- the optimization/automation-opportunity duty is unsupported), got {case_d_match['result']}",
)
assert_true(
    case_d_match.get("claim_ids") == ["CLAIM_WW_006"],
    f"CASE_D PARTIAL provenance must cite CLAIM_WW_006, got {case_d_match.get('claim_ids')}",
)
assert_true(
    NEW_TAG in (case_d_match.get("transfer_note") or "") or NEW_TAG in case_d_match.get("explanation", ""),
    f"CASE_D PARTIAL result must surface the missing {NEW_TAG} capability, got transfer_note={case_d_match.get('transfer_note')!r} explanation={case_d_match.get('explanation')!r}",
)
print("PASS G: CASE_D's real compound requirement now resolves PARTIAL via CLAIM_WW_006 (not a false STRONG), with the missing optimization/automation-opportunity capability explicitly surfaced.")


# ======================================================================
# J. Full real MBTA fixture regression -- requirement-level and
#    final-decision expectations.
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


direct_result = analyze_job(_load_real_job_input("CASE_D_MBTA_DIRECT_APPLICATION_ANALYST"))
assert_true(direct_result["valid"] is True, f"CASE_D analysis must be valid: {direct_result.get('errors')}")
direct_analysis = direct_result["analysis"]
direct_pm = next(m for m in direct_analysis["evidence_matches"] if m["requirement_id"] == "REQ_D_PROCESS_MAPPING")
assert_true(
    direct_pm["result"] == "PARTIAL" and direct_pm.get("claim_ids") == ["CLAIM_WW_006"],
    f"CASE_D REQ_D_PROCESS_MAPPING must resolve PARTIAL via CLAIM_WW_006, got {direct_pm}",
)
assert_true(
    direct_analysis["decision"] == "REJECT",
    f"CASE_D final decision must remain REJECT (independent blockers persist), got {direct_analysis['decision']}",
)
direct_blockers = sorted(b.rsplit(": ", 1)[-1] for b in direct_result["hard_blockers"])
assert_true(
    # SUPERSEDED BY BUSINESS_RULES_TECHNICAL_REQUIREMENTS_COMPOUND_
    # COMPLETION_V1: REQ_D_BUSINESS_RULES now correctly resolves PARTIAL
    # (not NONE), so it no longer appears as a hard blocker. See
    # tests/business_rules_technical_requirements_compound_completion_v1_test.py
    # for dedicated coverage of that capability.
    direct_blockers == ["REQ_D_DEGREE", "REQ_D_SYS_ANALYSIS_EXP"],
    f"CASE_D hard blockers must be exactly the 2 remaining independent ones (degree, sys-analysis duration), got {direct_blockers}",
)
print(f"PASS J1: CASE_D (direct) -- REQ_D_PROCESS_MAPPING=PARTIAL via CLAIM_WW_006; final decision=REJECT; blockers={direct_blockers}.")

contractor_result = analyze_job(_load_real_job_input("CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST"))
assert_true(contractor_result["valid"] is True, f"CASE_E analysis must be valid: {contractor_result.get('errors')}")
contractor_analysis = contractor_result["analysis"]
contractor_pm = next(m for m in contractor_analysis["evidence_matches"] if m["requirement_id"] == "REQ_E_PROCESS_MAPPING")
assert_true(
    contractor_pm["result"] == "STRONG" and contractor_pm.get("claim_ids") == ["CLAIM_WW_006"],
    f"CASE_E REQ_E_PROCESS_MAPPING (atomic requirement) must remain STRONG via CLAIM_WW_006, got {contractor_pm}",
)
assert_true(
    contractor_analysis["decision"] == "REJECT",
    f"CASE_E final decision must remain REJECT (independent blockers persist), got {contractor_analysis['decision']}",
)
contractor_blockers = sorted(b.rsplit(": ", 1)[-1] for b in contractor_result["hard_blockers"])
assert_true(
    # SUPERSEDED BY BUSINESS_RULES_TECHNICAL_REQUIREMENTS_COMPOUND_
    # COMPLETION_V1: REQ_E_BUSINESS_RULES now correctly resolves PARTIAL.
    contractor_blockers == ["REQ_E_DEGREE", "REQ_E_SYS_ANALYSIS_EXP"],
    f"CASE_E hard blockers must be exactly the 2 remaining independent ones, got {contractor_blockers}",
)
print(f"PASS J2: CASE_E (contractor) -- REQ_E_PROCESS_MAPPING=STRONG via CLAIM_WW_006 (atomic requirement, unaffected); final decision=REJECT; blockers={contractor_blockers}.")

print("ALL process_mapping_compound_completion_v1_test CHECKS PASSED")
