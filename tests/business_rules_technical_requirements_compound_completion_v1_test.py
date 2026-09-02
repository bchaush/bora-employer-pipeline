"""Regression tests for BUSINESS_RULES_TECHNICAL_REQUIREMENTS_COMPOUND_COMPLETION_V1.

BUSINESS_RULES_TECHNICAL_REQUIREMENTS_READ_ONLY_AUDIT_V1 proved, by direct
code inspection, that the real MBTA requirement "Experience identifying
and documenting business rules and technical requirements." currently
infers ZERO capabilities and resolves NONE, even though it is a genuine
compound of two distinct professional duties:

  A. identifying/documenting business rules -- NO existing capability
     represents this anywhere in the repository;
  B. identifying/documenting technical requirements -- the existing
     requirements_elicitation/scope_boundary capability (CLAIM_WW_001,
     approved) already truthfully represents this and resolves STRONG
     when reachable ("documenting technical requirements" alone already
     matches), but the real compound sentence's word-gap defeats the
     existing pattern.

This milestone:
  1. adds one new, narrowly-scoped REQUIREMENT capability,
     business_rule_identification_documentation, requiring an explicit
     identify/document/define/capture verb directly (zero word gap)
     governing "business rules" -- never inferred from the bare noun
     phrase "business rules" alone, and deliberately assigned to ZERO
     Claims (no current approved evidence establishes this distinct
     professional act -- implementing rule-like logic, e.g. CLAIM_WW_002's
     fail-closed controls, is not the same behavior as identifying/
     documenting the rules themselves);
  2. adds one additional, narrow, phrase-aware alternative to the
     EXISTING requirements_elicitation/scope_boundary pattern so it
     reaches "technical requirements" when coordinated with "business
     rules and" in the same sentence -- no new technical_requirements
     capability, no candidate-mapping change, no widening of the
     existing generic {0,3} word-gap globally.

With both pieces in place, the real MBTA requirement infers
{requirements_elicitation, scope_boundary,
business_rule_identification_documentation}; the best-overlapping Claim
(CLAIM_WW_001) covers only the first two, so the existing, unmodified
subset-check in match_requirement() automatically produces PARTIAL -- no
matcher change, no fixture change, no Claim change.

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


NEW_TAG = "business_rule_identification_documentation"
REQ_TAGS = frozenset({"requirements_elicitation", "scope_boundary"})

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


MBTA_TEXT = "Experience identifying and documenting business rules and technical requirements"


# ======================================================================
# B. Pre-fix / control reproduction -- component behavior in isolation.
# ======================================================================
b_alone_caps = infer_requirement_capabilities(_req("documenting technical requirements"))
assert_true(
    REQ_TAGS.issubset(b_alone_caps),
    f"'documenting technical requirements' must infer requirements_elicitation/scope_boundary, got {sorted(b_alone_caps)}",
)
b_alone_match = _match("documenting technical requirements")
assert_true(
    b_alone_match["result"] == "STRONG" and b_alone_match.get("claim_ids") == ["CLAIM_WW_001"],
    f"'documenting technical requirements' must resolve STRONG via CLAIM_WW_001 (control, unchanged), got {b_alone_match}",
)
print("PASS CONTROL-B: 'documenting technical requirements' remains STRONG via CLAIM_WW_001, unaffected by this milestone.")


# ======================================================================
# C/D. New business-rule capability -- required positives. Explicit
#    identify/document/define/capture verb directly governing "business
#    rules" -- never inferred from the bare noun phrase alone.
# ======================================================================
business_rule_positives = (
    "identifying and documenting business rules",
    "identify and document business rules",
    "document business rules",
    "define business rules",
    "capture business rules",
    "documenting business rules",
    "define and document business rules",
    "capture and document business rules",
)
for text in business_rule_positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(NEW_TAG in caps, f"{text!r} must infer {NEW_TAG}")
print("PASS BR-POS: all required business-rule identification/documentation phrasings infer the new capability.")

# Bare noun phrase alone must NOT infer the capability.
assert_true(
    NEW_TAG not in infer_requirement_capabilities(_req("business rules")),
    "'business rules' alone (no verb) must NOT infer the new capability",
)
print("PASS BR-BARE: bare noun phrase 'business rules' alone does not infer the new capability.")


# ======================================================================
# E. Business-rule negative controls.
# ======================================================================
business_rule_negatives = (
    "knowledge of business rules",
    "understanding business rules",
    "follow business rules",
    "adhere to business rules",
    "business rules engine",
    "business rules software",
    "business rules platform",
    "configure a rules engine",
    "implemented validation rules",
    "implemented approval rules",
    "implemented workflow controls",
    "business requirements",
    "technical requirements",
    "functional requirements",
    "process rules engine",
    "regulatory rules",
    "company policies and rules",
    # ChatGPT-suggested adversarial additions: rule USE/implementation is
    # not the same professional act as rule identification/documentation.
    "translate business rules into system logic",
    "implement business rules",
    "configure business rules",
    "enforce business rules",
    "validate against business rules",
)
for text in business_rule_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        NEW_TAG not in caps,
        f"{text!r} must NOT infer {NEW_TAG} -- knowing/following/implementing/using rules is not identifying/documenting them",
    )
print("PASS BR-NEG: all business-rule adversarial negatives (knowledge/following/engine/software/implementation/enforcement) correctly do not infer the new capability.")


# ======================================================================
# BUSINESS_RULE_OBJECT_BOUNDARY_BOUNDED_CORRECTION_V1 (Cursor external-
# review BLOCKING FINDING #1): the verb -> "business rules" grammar
# incorrectly prefix-matched "business rules" when those words are
# actually a modifier inside a longer product/tool/system noun phrase
# ("business rules engine configuration" is about a rules ENGINE, not
# about identifying/documenting the rules themselves). A bounded object-
# boundary exclusion is required directly after "business rules?" for
# concrete product/tool/system noun continuations. "tool"/"tools"/
# "system"/"systems" were only added after an actual probe confirmed
# they produce the same material false-positive pattern as "engine"/
# "software"/"platform"/"application" under the pre-correction grammar
# -- not included by assumption.
# ======================================================================
cursor_object_boundary_negatives = (
    "document business rules engine configuration",
    "identify business rules software vendors",
    "define business rules platform requirements",
    "capture business rules engine errors",
    "document business rules application settings",
    "document business-rules engine settings",
    # Probe-justified equivalents (confirmed to false-fire pre-correction
    # via the same reproduction method as the six Cursor examples above).
    "document business rules tool configuration",
    "identify business rules tools vendors",
    "define business rules system requirements",
    "capture business rules systems errors",
)
for text in cursor_object_boundary_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        NEW_TAG not in caps,
        f"{text!r} must NOT infer {NEW_TAG} -- 'business rules' here modifies a product/tool/system noun phrase, not the rules themselves (Cursor external-review BLOCKING FINDING #1)",
    )
print("PASS BR-OBJECT-BOUNDARY: 'business rules' modifying a longer engine/software/platform/application/tool/system noun phrase no longer infers the capability.")


# ======================================================================
# H. Acceptable bounded undershoots (Cursor-observed, intentionally NOT
#    fixed this pass -- no scope creep). These currently do NOT infer
#    the capability because an adjective sits between the verb and
#    "business rules"; widening that gap is explicitly out of scope for
#    this correction.
# ======================================================================
acceptable_bounded_undershoots = (
    "identify key business rules",
    "document critical business rules",
    "capture applicable business rules",
    "define governing business rules",
    "identify and document relevant business rules",
)
for text in acceptable_bounded_undershoots:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        NEW_TAG not in caps,
        f"{text!r} is an acceptable bounded undershoot and must remain unmatched this pass; if this now matches, scope crept",
    )
print("PASS UNDERSHOOT: acceptable bounded undershoots (adjective between verb and 'business rules') remain intentionally unmatched -- no scope creep.")


# ======================================================================
# F/G. Technical-requirements reachability -- existing capability,
#    reached via a narrow, phrase-aware additional alternative. No new
#    technical_requirements tag; candidate mapping (CLAIM_WW_001)
#    unchanged.
# ======================================================================
technical_requirement_positives = (
    "document technical requirements",
    "documenting technical requirements",
    "identify and document technical requirements",
    "identifying and documenting technical requirements",
    MBTA_TEXT,
)
for text in technical_requirement_positives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        REQ_TAGS.issubset(caps),
        f"{text!r} must infer requirements_elicitation/scope_boundary, got {sorted(caps)}",
    )
print("PASS TR-POS: technical-requirements phrasings, including the real coordinated MBTA sentence, infer the existing requirements_elicitation/scope_boundary capability.")

technical_requirement_negatives = (
    "knowledge of technical requirements",
    "technical requirements software",
    "technical requirements section",
    "read the technical requirements",
    "technical requirements are listed below",
)
for text in technical_requirement_negatives:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        not REQ_TAGS.issubset(caps),
        f"{text!r} must NOT infer requirements_elicitation/scope_boundary -- mere mention/reference is not a requirements-documentation act",
    )
print("PASS TR-NEG: mere mention/reference to 'technical requirements' (no professional act asserted) does not infer requirements_elicitation.")


# ======================================================================
# Existing correct requirements behavior must remain intact -- the new
# branch must not contaminate business/functional/system-functional
# requirements phrasing or any pre-existing recognized form.
# ======================================================================
existing_requirements_controls = (
    "Gather and clarify business requirements with nontechnical stakeholders",
    "Identifies, analyzes, and documents business requirements, system functional requirements",
)
for text in existing_requirements_controls:
    caps = infer_requirement_capabilities(_req(text))
    assert_true(
        REQ_TAGS.issubset(caps),
        f"pre-existing requirements phrasing {text!r} regressed: {sorted(caps)}",
    )
    assert_true(
        NEW_TAG not in caps,
        f"pre-existing requirements phrasing {text!r} must NOT infer {NEW_TAG} (no 'business rules' present)",
    )
print("PASS TR-REGRESSION: pre-existing business/system-functional requirements phrasing remains correctly recognized and is not contaminated by the new business-rule capability.")


# ======================================================================
# H/I/J. Exact compound expectation -- the real MBTA sentence.
# ======================================================================
mbta_caps = infer_requirement_capabilities(_req(MBTA_TEXT))
assert_true(
    REQ_TAGS.union({NEW_TAG}).issubset(mbta_caps),
    f"real MBTA text must infer requirements_elicitation, scope_boundary, and {NEW_TAG}, got {sorted(mbta_caps)}",
)
mbta_match = _match(MBTA_TEXT)
assert_true(
    mbta_match["result"] == "PARTIAL",
    f"real MBTA text must resolve PARTIAL (not STRONG, not NONE), got {mbta_match['result']}",
)
assert_true(
    mbta_match.get("claim_ids") == ["CLAIM_WW_001"],
    f"PARTIAL provenance must cite CLAIM_WW_001, got {mbta_match.get('claim_ids')}",
)
assert_true(
    NEW_TAG in (mbta_match.get("transfer_note") or "") or NEW_TAG in mbta_match.get("explanation", ""),
    f"PARTIAL result must surface the missing {NEW_TAG} capability, got transfer_note={mbta_match.get('transfer_note')!r} explanation={mbta_match.get('explanation')!r}",
)
print("PASS COMPOUND: the real MBTA requirement now resolves PARTIAL via CLAIM_WW_001, with the missing business-rule-identification capability explicitly surfaced.")


# ======================================================================
# I. Isolated business-rule component -- zero candidate support.
# ======================================================================
isolated_br_text = "identifying and documenting business rules"
isolated_br_caps = infer_requirement_capabilities(_req(isolated_br_text))
assert_true(NEW_TAG in isolated_br_caps, f"isolated business-rule text must infer {NEW_TAG}")
isolated_br_match = _match(isolated_br_text)
assert_true(
    isolated_br_match["result"] not in {"STRONG", "SUPPORTED"},
    f"isolated business-rule text must NOT resolve STRONG/SUPPORTED with zero Claim support, got {isolated_br_match['result']}",
)
print(f"PASS ISOLATED-BR: isolated business-rule text infers {NEW_TAG} and resolves {isolated_br_match['result']} (not STRONG/SUPPORTED) with zero current Claim support.")


# ======================================================================
# K. Claim-side safety -- the new capability is assigned to ZERO Claims,
#    including CLAIM_WW_001 (requirements) and CLAIM_WW_002 (fail-closed
#    conditional controls -- implementation, not identification/
#    documentation of the rules themselves).
# ======================================================================
for claim_id, caps_map in _CLAIM_CAPABILITIES.items():
    assert_true(
        NEW_TAG not in caps_map,
        f"{claim_id} must NOT carry {NEW_TAG} -- no current approved evidence establishes independent identification/documentation of business rules",
    )
assert_true(
    "requirements_elicitation" not in _CLAIM_CAPABILITIES.get("CLAIM_WW_002", frozenset())
    and NEW_TAG not in _CLAIM_CAPABILITIES.get("CLAIM_WW_002", frozenset()),
    "CLAIM_WW_002 (fail-closed conditional controls) must not be broadened into requirements or business-rule capabilities",
)
print("PASS CLAIM-SAFETY: no existing Claim (including CLAIM_WW_001 and CLAIM_WW_002) carries the new business-rule-identification capability; CLAIM_WW_002 was not broadened.")


# ======================================================================
# L/M. Real MBTA fixture regression -- requirement-level and
#    final-decision expectations. No blocker weakened to preserve REJECT.
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
direct_br = next(m for m in direct_analysis["evidence_matches"] if m["requirement_id"] == "REQ_D_BUSINESS_RULES")
assert_true(
    direct_br["result"] == "PARTIAL" and direct_br.get("claim_ids") == ["CLAIM_WW_001"],
    f"CASE_D REQ_D_BUSINESS_RULES must resolve PARTIAL via CLAIM_WW_001, got {direct_br}",
)
assert_true(
    "REQ_D_BUSINESS_RULES" not in [b.rsplit(": ", 1)[-1] for b in direct_result["hard_blockers"]],
    "REQ_D_BUSINESS_RULES must no longer appear as a hard blocker (PARTIAL never triggers detect_hard_blockers)",
)
assert_true(
    direct_analysis["decision"] == "REJECT",
    f"CASE_D final decision must remain REJECT (independent blockers persist), got {direct_analysis['decision']}",
)
direct_blockers = sorted(b.rsplit(": ", 1)[-1] for b in direct_result["hard_blockers"])
# ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1 (post-dates and
# SUPERSEDES the DOMAIN_QUALIFIED_EXPERIENCE_DURATION_UNKNOWN_V1 comment
# below): REQ_D_DEGREE is now referenced by GATE_D_DEGREE_EXPERIENCE
# (the employer's real HS/Associate's/Bachelor's/Master's alternative
# branches) and is no longer independently hard-blocked -- the gate
# itself currently resolves UNRESOLVED on current evidence, never a
# blocker. CASE_D remains REJECT via unrelated, unaffected ungrouped
# gaps (ITSM/SaaS/MS Office), so hard_blockers is now empty.
assert_true(
    direct_blockers == [],
    f"CASE_D hard blockers must be exactly empty (degree gated, resolves UNRESOLVED), got {direct_blockers}",
)
print(f"PASS L1: CASE_D (direct) -- REQ_D_BUSINESS_RULES=PARTIAL via CLAIM_WW_001; final decision=REJECT; blockers={direct_blockers}.")

contractor_result = analyze_job(_load_real_job_input("CASE_E_MBTA_CONTRACTOR_APPLICATION_ANALYST"))
assert_true(contractor_result["valid"] is True, f"CASE_E analysis must be valid: {contractor_result.get('errors')}")
contractor_analysis = contractor_result["analysis"]
contractor_br = next(m for m in contractor_analysis["evidence_matches"] if m["requirement_id"] == "REQ_E_BUSINESS_RULES")
assert_true(
    contractor_br["result"] == "PARTIAL" and contractor_br.get("claim_ids") == ["CLAIM_WW_001"],
    f"CASE_E REQ_E_BUSINESS_RULES must resolve PARTIAL via CLAIM_WW_001, got {contractor_br}",
)
assert_true(
    "REQ_E_BUSINESS_RULES" not in [b.rsplit(": ", 1)[-1] for b in contractor_result["hard_blockers"]],
    "REQ_E_BUSINESS_RULES must no longer appear as a hard blocker",
)
# ALTERNATIVE_QUALIFICATION_BRANCH_REPRESENTATION_V1 (post-dates and
# SUPERSEDES the previous REJECT/single-blocker expectation): REQ_E_DEGREE
# is now referenced by GATE_E_DEGREE_EXPERIENCE and no longer
# independently hard-blocks; with that fabricated blocker removed, CASE_E's
# actual underlying state (one genuinely SUPPORTED requirement -- process
# mapping -- alongside unrelated MEDIUM-relevance NONE gaps) does not meet
# any REJECT threshold in the existing, unmodified decision routing --
# decision is now UNDECIDED, an honest consequence, not manufactured.
assert_true(
    contractor_analysis["decision"] == "UNDECIDED",
    f"CASE_E final decision must be UNDECIDED (fabricated degree blocker removed), got {contractor_analysis['decision']}",
)
contractor_blockers = sorted(b.rsplit(": ", 1)[-1] for b in contractor_result["hard_blockers"])
assert_true(
    contractor_blockers == [],
    f"CASE_E hard blockers must be exactly empty (degree gated, resolves UNRESOLVED), got {contractor_blockers}",
)
print(f"PASS L2: CASE_E (contractor) -- REQ_E_BUSINESS_RULES=PARTIAL via CLAIM_WW_001; final decision=UNDECIDED (degree gated, no longer a fabricated blocker); blockers={contractor_blockers}.")


# ======================================================================
# MIT LL real fixture regression -- unrelated requirements-analysis
# requirement must remain unaffected.
# ======================================================================
mit_result = analyze_job(_load_real_job_input("CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST"))
assert_true(mit_result["valid"] is True, f"MIT LL analysis must be valid: {mit_result.get('errors')}")
mit_req_analysis = next(
    m for m in mit_result["analysis"]["evidence_matches"] if m["requirement_id"] == "REQ_C_REQUIREMENTS_ANALYSIS"
)
assert_true(
    mit_req_analysis["result"] == "STRONG" and mit_req_analysis.get("claim_ids") == ["CLAIM_WW_001"],
    f"MIT LL REQ_C_REQUIREMENTS_ANALYSIS must remain STRONG via CLAIM_WW_001 (control, unaffected), got {mit_req_analysis}",
)
print("PASS MIT-REGRESSION: MIT LL's real 'business requirements, system functional requirements' row remains STRONG via CLAIM_WW_001, unaffected by this milestone.")

print("ALL business_rules_technical_requirements_compound_completion_v1_test CHECKS PASSED")
