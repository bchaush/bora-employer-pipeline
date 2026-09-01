"""Regression tests for PROCESS_MAPPING_REAL_GRAMMAR_V1.

MBTA_REAL_FIXTURE_CAUSALITY_AUDIT_V1 proved that the process_mapping capability
pattern in requirement_match.py only recognized zero-word-gap phrasings
("document business processes", "map existing business processes") and never
recognized real, natural employer wording like MBTA's own "map and document
complex business processes" -- the adjective "complex" and the "map and"
prefix defeated every existing branch. A counterfactual proved that once the
capability tag IS present, the existing capability-set-completeness subset
check already resolves the requirement correctly against the approved
CLAIM_WW_006 (process_mapping) -- this was purely an extraction/regex gap,
not a matching-architecture gap and not a candidate-evidence gap.

This milestone adds one small, additively-scoped grammar branch recognizing:
  map|document|mapping|documenting [+ optional "and document"/"and map"]
  [+ up to two bounded modifier words] + business process(es)
plus a narrow negative lookahead closing a pre-existing false positive
("process mapping software") on the bare "process mapping" branch. No other
capability, matcher, compound-requirement, or evidence logic is touched.

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
    infer_requirement_capabilities,
    load_reusable_claims,
    match_requirement,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


TAG = "process_mapping"

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


# ======================================================================
# A-D, F. Required positive cases -- natural real-world phrasing that the
# closed zero-word-gap grammar previously missed.
# ======================================================================
required_positives = (
    "map and document complex business processes",
    "map business processes",
    "document complex business processes",
    "mapping business processes",
)
for text in required_positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(TAG in caps, f"{text!r} must infer {TAG}")
    m = _match(text)
    assert_true(
        m["result"] in {"STRONG", "SUPPORTED"} and m.get("claim_ids") == ["CLAIM_WW_006"],
        f"{text!r} must resolve STRONG/SUPPORTED via CLAIM_WW_006, got {m['result']} {m.get('claim_ids')}",
    )
print("PASS A-D: natural real-world map/document + business-process phrasing (including the 'complex' adjective and the 'map and document' compound-verb form) now infers process_mapping and resolves STRONG via CLAIM_WW_006.")


# ======================================================================
# F. Real MBTA full requirement text -- must infer process_mapping.
# ======================================================================
real_mbta_texts = (
    # CASE_D (direct) -- compound: mapping/documenting duty + a separate,
    # NOT independently evidenced optimization/automation duty. See the
    # dedicated compound-requirement adjudication section below -- this
    # assertion only proves the tag is now inferred, not that a resulting
    # STRONG on the full compound text is safe to trust as-is.
    "Proven ability to map and document complex business processes and identify opportunities for optimization or automation within assigned applications",
    # CASE_E (contractor) -- atomic, no optimization/automation clause.
    "Ability to map and document complex business processes",
)
for text in real_mbta_texts:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(TAG in caps, f"real MBTA text {text!r} must infer {TAG}")
print("PASS F: both real MBTA requirement texts (direct and contractor) now infer process_mapping.")


# ======================================================================
# E. Existing canonical/synthetic positives (pre-dating this milestone)
#    must remain supported, unchanged.
# ======================================================================
existing_canonical_positives = (
    "Map current-state workflows",
    "Document business processes for operations review",
    "Map operational handoffs between teams",
    "Document current-state and future-state workflow",
    "Map existing business processes and produce process maps",
)
for text in existing_canonical_positives:
    m = _match(text)
    assert_true(
        m["result"] in {"STRONG", "SUPPORTED"} and m.get("claim_ids") == ["CLAIM_WW_006"],
        f"pre-existing canonical positive {text!r} regressed: {m}",
    )
print("PASS E: pre-existing canonical process_mapping positives remain supported via CLAIM_WW_006, unchanged.")


# ======================================================================
# Adversarial negatives -- must NOT infer process_mapping merely because
# process/map/business words appear nearby, and existing distinctions
# from data_mapping / requirements_elicitation / generic process work
# must be preserved.
# ======================================================================
adversarial_negatives = (
    "business process owner",
    "process mapping software",  # pre-existing false positive, closed by this milestone
    "mapped customer data into the system",
    "create geographic maps for business locations",
    "business processes are documented by another team",
    "support process automation tools",
    "map data fields between systems",
    "review existing business processes",
)
for text in adversarial_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        TAG not in caps,
        f"{text!r} must NOT infer {TAG} -- no candidate/employer-required mapping-or-documenting act of a business process is expressed",
    )
print("PASS NEG: all required adversarial negatives (including the pre-existing 'process mapping software' false positive) correctly do not infer process_mapping; data_mapping/requirements_elicitation/generic-process-work distinctions are preserved.")


# ======================================================================
# Existing negative control set (job_analysis_test.py P2c) reconfirmed
# unaffected by this milestone -- generic process/workflow words alone.
# ======================================================================
existing_negatives = (
    "process improvement",
    "operations",
    "workflow management",
    "project management",
    "stakeholder management",
    "documentation",
)
for text in existing_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(TAG not in caps, f"pre-existing negative {text!r} regressed: {caps}")
print("PASS NEG-EXISTING: pre-existing generic process/workflow negative controls remain non-positive.")


# ======================================================================
# G. Real MBTA fixture regression -- full requirement adjudication.
#
# CASE_E (contractor): atomic requirement ("map and document complex
# business processes", no optimization/automation clause) -- STRONG via
# CLAIM_WW_006 is safe and correct.
#
# CASE_D (direct): the frozen Requirement is COMPOUND -- it also contains
# "and identify opportunities for optimization or automation within
# assigned applications", a distinct duty. CLAIM_WW_006's own
# forbidden_contexts explicitly excludes "quantified process-improvement
# outcomes" and "automated process-mining / telemetry tools" -- the
# closest concepts to "optimization or automation opportunities" -- so
# crediting the full compound requirement STRONG via process_mapping
# alone would silently over-credit the unevidenced second duty.
#
# SUPERSEDED BY PROCESS_MAPPING_COMPOUND_COMPLETION_V1: the assertion
# below originally expected STRONG/SUPPORTED here and flagged that result
# as untrusted pending a compound-requirement decision
# (COMPOUND_REQUIREMENT_DECISION_REQUIRED). PROCESS_MAPPING_COMPOUND_
# READ_ONLY_ADJUDICATION_V1 proved the existing subset-check machinery
# already demotes a multi-capability Requirement to PARTIAL when only
# some of its inferred capabilities are Claim-supported -- no compound
# architecture was needed. PROCESS_MAPPING_COMPOUND_COMPLETION_V1 added
# the missing process_optimization_opportunity_identification capability
# (assigned to zero Claims), so this real compound requirement now
# correctly resolves PARTIAL, not STRONG. This is the trusted, final
# result -- see tests/process_mapping_compound_completion_v1_test.py for
# the dedicated coverage of that capability itself.
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
    f"CASE_D REQ_D_PROCESS_MAPPING must resolve PARTIAL via CLAIM_WW_006 (process_optimization_opportunity_identification is inferred but unsupported), got {direct_pm}",
)
assert_true(
    "REQ_D_PROCESS_MAPPING" not in [b.rsplit(": ", 1)[-1] for b in direct_result["hard_blockers"]],
    "REQ_D_PROCESS_MAPPING must no longer appear as a hard blocker (PARTIAL never triggers detect_hard_blockers)",
)
assert_true(
    direct_analysis["decision"] == "REJECT",
    f"CASE_D final decision must remain REJECT (other independent blockers persist -- this milestone must not weaken them), got {direct_analysis['decision']}",
)
print("PASS G1: CASE_D (direct) REQ_D_PROCESS_MAPPING now correctly resolves PARTIAL via CLAIM_WW_006 (not a false STRONG); it is no longer a hard blocker; final decision remains REJECT via other independent blockers, unweakened.")

contractor_result = analyze_job(_load_real_job_input("CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST"))
assert_true(contractor_result["valid"] is True, f"CASE_E analysis must be valid: {contractor_result.get('errors')}")
contractor_analysis = contractor_result["analysis"]
contractor_pm = next(m for m in contractor_analysis["evidence_matches"] if m["requirement_id"] == "REQ_E_PROCESS_MAPPING")
assert_true(
    contractor_pm["result"] in {"STRONG", "SUPPORTED"} and contractor_pm.get("claim_ids") == ["CLAIM_WW_006"],
    f"CASE_E REQ_E_PROCESS_MAPPING (atomic requirement) must resolve STRONG/SUPPORTED via CLAIM_WW_006, got {contractor_pm}",
)
assert_true(
    "REQ_E_PROCESS_MAPPING" not in [b.rsplit(": ", 1)[-1] for b in contractor_result["hard_blockers"]],
    "REQ_E_PROCESS_MAPPING must no longer appear as a hard blocker",
)
assert_true(
    contractor_analysis["decision"] == "REJECT",
    f"CASE_E final decision must remain REJECT (other independent blockers persist), got {contractor_analysis['decision']}",
)
print("PASS G2: CASE_E (contractor) REQ_E_PROCESS_MAPPING (atomic requirement) resolves STRONG via CLAIM_WW_006 safely; final decision remains REJECT via other independent blockers, unweakened.")


# ======================================================================
# No existing approved Claim other than CLAIM_WW_006 silently gains
# process_mapping.
# ======================================================================
from requirement_match import _CLAIM_CAPABILITIES  # noqa: E402

for claim_id, caps_map in _CLAIM_CAPABILITIES.items():
    if claim_id == "CLAIM_WW_006":
        continue
    assert_true(TAG not in caps_map, f"{claim_id} must not carry {TAG}")
print("PASS CLAIM: no Claim other than CLAIM_WW_006 carries process_mapping.")

print("ALL process_mapping_real_grammar_v1_test CHECKS PASSED")
