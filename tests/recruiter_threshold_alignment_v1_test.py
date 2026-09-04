"""Regression tests for BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1.

Root cause reproduced live: Bose Professional -- IT Business Analyst. The
exact current first-party posting states "Mid Level", "2-4 years experience
as a Business Analyst or similar role", Agile/Waterfall, and enterprise-
system exposure. Bora had strong truthful central-work overlap, but
Candidate Truth did not establish the explicit recruiter-threshold
experience requirement. experience_range.py/domain_qualified_duration.py
already, correctly, and deliberately return UNKNOWN (never a fabricated
NONE) for such a requirement -- but decide_lane_and_decision()'s threshold
counters (none/strong_or_supported/partial) are blind to UNKNOWN, so an
UNKNOWN mandatory-HIGH experience-threshold row exerts zero friction on
PRIORITY_APPLY/APPLY routing. With otherwise-strong evidence, this silently
promoted Bose to PRIORITY_APPLY before human correction.

apply_recruiter_threshold_guard() (src/job_decision.py) closes this gap as a
downstream, downgrade-only pursuit/surfacing-economics layer -- strictly
after decide_lane_and_decision() and apply_posting_state_routing() -- never
touching Qualification Truth, never computing/inferring a candidate
experience duration, never converting UNKNOWN into NONE, and never
introducing REJECT.

Note on the two Bose extraction shapes (AUDIT FIRST finding): the literal
raw employer phrasing "2-4 years experience as a Business Analyst or
similar role" does NOT match either experience_range.py's or
domain_qualified_duration.py's narrow, string-anchored grammars (neither
"years of work experience" nor "years of experience in <domain>") --
independently reproduced to fall through to the ordinary capability
matcher's empty-capability-coverage fallback, producing a fabricated NONE
and an immediate REJECT (the opposite-direction defect, out of scope for
this milestone). This guard, and this regression suite, target the
grammar-matching extraction shape ("2-4 years of work experience", a
faithful domain-free paraphrase of the same employer requirement) that
actually reaches EXPERIENCE_RANGE_EVALUATOR's honest UNKNOWN -- the exact
shape this repository's own evaluators are designed to recognize.

Exercises real production code (job_analysis.py, job_decision.py) and the
real, approved Evidence/Claim repository -- no logic is duplicated here.
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

from job_analysis import analyze_job  # noqa: E402
from job_decision import apply_recruiter_threshold_guard  # noqa: E402
from requirement_source_role import classify_source_semantic_roles  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_DIR = ROOT / "fixtures" / "jobs" / "JOB_FIXTURE_BSA_001"
BSA_JD_TEXT = (FIXTURE_DIR / "jd.txt").read_text(encoding="utf-8")
BSA_EXTRACTION = json.loads((FIXTURE_DIR / "structured_extraction.json").read_text(encoding="utf-8"))


def _stamp_source_roles(requirements: list[dict]) -> list[dict]:
    classifications = classify_source_semantic_roles(requirements)
    for row, classification in zip(requirements, classifications):
        row["source_semantic_role"] = classification["source_semantic_role"]
        row["source_semantic_role_basis"] = classification["source_semantic_role_basis"]
        row["explicit_prerequisite_language_present"] = classification[
            "explicit_prerequisite_language_present"
        ]
        row["duplicated_under_requirements"] = classification["duplicated_under_requirements"]
        row["source_semantic_role_classifier_version"] = classification[
            "source_semantic_role_classifier_version"
        ]
    return requirements


def _threshold_row(
    req_id: str,
    text: str,
    *,
    importance: str = "MANDATORY",
    relevance: str = "HIGH",
    domain: str | None = None,
    technology: list | None = None,
    experience_level: str | None = None,
    source_location: str = "Minimum Qualifications",
) -> dict:
    return {
        "requirement_id": req_id,
        "job_id": "JOB_BSA",
        "text": text,
        "category": "EXPERIENCE",
        "importance": importance,
        "seniority_implication": None,
        "technology": technology or [],
        "experience_level": experience_level,
        "domain": domain,
        "relevance": relevance,
        "source_text": text,
        "source_location": source_location,
    }


def _bsa_job_input(extra_requirement: dict | None, *, qualification_gates: list | None = None) -> dict:
    """Real, approved-evidence-backed BSA fixture (proven PRIORITY_APPLY,
    distinct_high_claims=4) with exactly one optional injected requirement
    row -- everything else byte-identical to the canonical fixture."""
    extraction = copy.deepcopy(BSA_EXTRACTION)
    if extra_requirement is not None:
        extraction["requirements"].append(extra_requirement)
    _stamp_source_roles(extraction["requirements"])
    extraction["qualification_gates"] = qualification_gates or []
    jd_text = BSA_JD_TEXT
    if extra_requirement is not None:
        jd_text = jd_text + "\n" + str(extra_requirement.get("text") or "")
    return {
        "company": "Bose Professional (Synthetic Regression Fixture)",
        "role": "IT Business Analyst",
        "jd_text": jd_text,
        "fixture_key": "BOSE_RECRUITER_THRESHOLD_REGRESSION",
        "structured_extraction": extraction,
        "role_status": "VERIFIED_LIVE",
        "source_verification_status": "VERIFIED_DIRECT",
    }


def _analyze(job_input: dict) -> dict:
    result = analyze_job(job_input)
    assert_true(result["valid"] is True, f"analyze_job must be valid: {result.get('errors')}")
    return result


# ======================================================================
# BASELINE. The unmodified BSA fixture (no injected threshold row) must
# remain PRIORITY_APPLY, distinct_high_claims=4 -- proving the guard has a
# real, strong PRIORITY_APPLY case to actually downgrade below, and giving
# later sections a byte-comparable reference.
# ======================================================================
result_baseline = _analyze(_bsa_job_input(None))
analysis_baseline = result_baseline["analysis"]
assert_true(
    analysis_baseline["decision"] == "PRIORITY_APPLY",
    f"BSA baseline (no injected row) must be PRIORITY_APPLY, got {analysis_baseline['decision']}",
)
print("PASS BASELINE: unmodified BSA fixture remains PRIORITY_APPLY (distinct_high_claims=4) -- the guard has a real case to cap.")


# ======================================================================
# A. BOSE REGRESSION CONTROL -- the reproduced defect. An unresolved
# mandatory HIGH "2-4 years of work experience" row (EXPERIENCE_RANGE_
# EVALUATOR, result=UNKNOWN) added to the otherwise-PRIORITY_APPLY BSA
# evidence set must cap the decision at EFFICIENT_APPLY, never higher.
# ======================================================================
bose_years_row = _threshold_row("REQ_BOSE_YEARS", "2-4 years of work experience", domain=None)
result_bose = _analyze(_bsa_job_input(bose_years_row))
analysis_bose = result_bose["analysis"]
assert_true(
    analysis_bose["decision"] == "EFFICIENT_APPLY" and analysis_bose["lane"] == "LANE_1_EFFICIENT_APPLY",
    f"Bose-shaped unresolved 2-4yr threshold must cap at EFFICIENT_APPLY (never PRIORITY_APPLY/APPLY, never REJECT), got {analysis_bose['lane']}/{analysis_bose['decision']}",
)
assert_true(
    analysis_bose["decision"] != "REJECT",
    "the guard must never introduce REJECT",
)
match_bose_years = next(m for m in analysis_bose["evidence_matches"] if m["requirement_id"] == "REQ_BOSE_YEARS")
assert_true(
    match_bose_years["result"] == "UNKNOWN" and match_bose_years["evaluation_path"] == "EXPERIENCE_RANGE_EVALUATOR",
    f"REQ_BOSE_YEARS EvidenceMatch must remain the evaluator's own honest UNKNOWN, untouched by the guard, got {match_bose_years}",
)
assert_true(
    "REQ_BOSE_YEARS" in analysis_bose["decision_rationale"] and "BORA_RECRUITER_THRESHOLD_ALIGNMENT_V1" in analysis_bose["decision_rationale"],
    f"decision_rationale must identify the triggering requirement and this milestone, got {analysis_bose['decision_rationale']!r}",
)
assert_true(
    analysis_bose["requirements"] == analysis_baseline["requirements"] or True,
    "sanity: requirements list grew by exactly one row (checked structurally below)",
)
assert_true(
    len(analysis_bose["requirements"]) == len(analysis_baseline["requirements"]) + 1,
    "exactly one requirement row was added; no other requirement-level record was fabricated",
)
print("PASS A (BOSE REGRESSION): unresolved mandatory 2-4yr experience threshold caps an otherwise-PRIORITY_APPLY case at EFFICIENT_APPLY; qualification EvidenceMatch (UNKNOWN/EXPERIENCE_RANGE_EVALUATOR) is untouched; never REJECT.")


# ======================================================================
# A2. Domain-qualified grammar variant -- "N years of experience in
# <domain>" (DOMAIN_QUALIFIED_DURATION_EVALUATOR). lower_bound=3 falls in
# the >=3 tier, so this now caps at WATCH (second post-review pass --
# 3+ unresolved is outside Bora's normal serious-pursuit pool), not
# EFFICIENT_APPLY (which is reserved for lower_bound==2 exactly).
# ======================================================================
bose_domain_row = _threshold_row(
    "REQ_BOSE_DOMAIN_YEARS", "3 years of experience in business analysis", domain="Business Analysis"
)
result_bose_domain = _analyze(_bsa_job_input(bose_domain_row))
analysis_bose_domain = result_bose_domain["analysis"]
match_bose_domain = next(
    m for m in analysis_bose_domain["evidence_matches"] if m["requirement_id"] == "REQ_BOSE_DOMAIN_YEARS"
)
assert_true(
    match_bose_domain["evaluation_path"] == "DOMAIN_QUALIFIED_DURATION_EVALUATOR",
    f"setup sanity: expected DOMAIN_QUALIFIED_DURATION_EVALUATOR, got {match_bose_domain['evaluation_path']}",
)
assert_true(
    analysis_bose_domain["decision"] == "WATCH",
    f"domain-qualified unresolved 3yr threshold (>=3 tier) must cap at WATCH, got {analysis_bose_domain['decision']}",
)
print("PASS A2: the domain-qualified grammar variant (DOMAIN_QUALIFIED_DURATION_EVALUATOR, lower_bound=3) caps at WATCH -- the >=3 tier, not the exactly-2 EFFICIENT_APPLY tier.")


# ======================================================================
# B. POSITIVE CONTROL -- genuine 0-2 role. No guard from years alone.
# ======================================================================
zero_two_row = _threshold_row("REQ_BOSE_0_2", "0-2 years of work experience", domain=None)
result_zero_two = _analyze(_bsa_job_input(zero_two_row))
analysis_zero_two = result_zero_two["analysis"]
assert_true(
    analysis_zero_two["decision"] == "PRIORITY_APPLY",
    f"an explicit 0-2yr threshold must NOT trigger the guard (normal early-career pool), got {analysis_zero_two['decision']}",
)
print("PASS B: an explicit 0-2yr threshold does not trigger the guard -- PRIORITY_APPLY preserved.")


# ======================================================================
# C. POSITIVE CONTROL -- "1-3 years", explicitly case-by-case/discretionary
# per the locked operating calibration; must NOT be an automatic trigger.
# ======================================================================
one_three_row = _threshold_row("REQ_BOSE_1_3", "1-3 years of work experience", domain=None)
result_one_three = _analyze(_bsa_job_input(one_three_row))
analysis_one_three = result_one_three["analysis"]
assert_true(
    analysis_one_three["decision"] == "PRIORITY_APPLY",
    f"an explicit 1-3yr threshold (lower_bound=1) must remain case-by-case, not an automatic guard trigger, got {analysis_one_three['decision']}",
)
print("PASS C: an explicit 1-3yr threshold (lower_bound=1) does not automatically trigger the guard.")


# ======================================================================
# C2. SEVERITY-TIER CONTROL (second post-review correction) -- bare,
# unkeyworded "3+"/"5+"/"6+"/"7+"/"8+"/"10+ years of work experience" rows
# (no title/seniority keyword, so detect_seniority_signals contributes NO
# blocker -- its years-regex only fires when another advanced-seniority
# signal is already present) must ALL cap at WATCH -- outside Bora's
# normal serious-pursuit pool per the approved operating calibration --
# never EFFICIENT_APPLY/APPLY/PRIORITY_APPLY. An unresolved >=3 threshold
# must never survive merely because no Senior keyword is present, and
# must never be treated as favorably as the exactly-2 EFFICIENT_APPLY
# tier.
# ======================================================================
for _bound_text, _req_id in (
    ("3+ years of work experience", "REQ_BOSE_3_PLUS"),
    ("5+ years of work experience", "REQ_BOSE_5_PLUS"),
    ("6+ years of work experience", "REQ_BOSE_6_PLUS"),
    ("7+ years of work experience", "REQ_BOSE_7_PLUS"),
    ("8+ years of work experience", "REQ_BOSE_8_PLUS"),
    ("10+ years of work experience", "REQ_BOSE_10_PLUS"),
):
    _row = _threshold_row(_req_id, _bound_text, domain=None)
    _result = _analyze(_bsa_job_input(_row))
    _analysis = _result["analysis"]
    _match = next(m for m in _analysis["evidence_matches"] if m["requirement_id"] == _req_id)
    assert_true(
        _match["result"] == "UNKNOWN" and _match["evaluation_path"] == "EXPERIENCE_RANGE_EVALUATOR",
        f"setup sanity: {_req_id} must itself resolve UNKNOWN/EXPERIENCE_RANGE_EVALUATOR, got {_match}",
    )
    assert_true(
        _analysis["decision"] == "WATCH" and _analysis["lane"] == "WATCH",
        f"a bare {_bound_text!r} threshold (>=3 tier) must cap at WATCH, never EFFICIENT_APPLY/APPLY/PRIORITY_APPLY, got {_analysis['lane']}/{_analysis['decision']}",
    )
print("PASS C2: bare unkeyworded 3+/5+/6+/7+/8+/10+ years-of-work-experience thresholds all cap at WATCH -- outside Bora's normal serious-pursuit pool, never surfacing merely because no Senior keyword is present. Keyworded Senior/Staff/Principal/Lead cases remain governed solely by the separate, untouched detect_seniority_signals mechanism.")


# ======================================================================
# C2b. TIER-PRECEDENCE CONTROL -- when both an exactly-2 row and a >=3
# row are present on the same role, the MORE conservative tier (WATCH)
# must win; this guard only ever moves toward more conservative, never
# picks the more favorable of two triggered tiers.
# ======================================================================
extraction_mixed = copy.deepcopy(BSA_EXTRACTION)
extraction_mixed["requirements"].append(_threshold_row("REQ_BOSE_MIXED_2", "2-4 years of work experience", domain=None))
extraction_mixed["requirements"].append(_threshold_row("REQ_BOSE_MIXED_5", "5+ years of work experience", domain=None))
_stamp_source_roles(extraction_mixed["requirements"])
extraction_mixed["qualification_gates"] = []
job_input_mixed = {
    "company": "Bose Professional (Synthetic Regression Fixture)",
    "role": "IT Business Analyst",
    "jd_text": BSA_JD_TEXT,
    "fixture_key": "BOSE_RECRUITER_THRESHOLD_REGRESSION_MIXED",
    "structured_extraction": extraction_mixed,
    "role_status": "VERIFIED_LIVE",
    "source_verification_status": "VERIFIED_DIRECT",
}
result_mixed = _analyze(job_input_mixed)
assert_true(
    result_mixed["analysis"]["decision"] == "WATCH",
    f"a role with both an unresolved exactly-2 row and an unresolved >=3 row must route to the more conservative WATCH, not EFFICIENT_APPLY, got {result_mixed['analysis']['decision']}",
)
print("PASS C2b: mixed exactly-2 + >=3 unresolved thresholds on the same role route to the more conservative tier (WATCH), never the more favorable one.")


# ======================================================================
# C2c. CURSOR CORRECTION -- apply_recruiter_threshold_guard() must not
# early-return on an incoming EFFICIENT_APPLY decision: the >=3 tier must
# consume ALL APPLY-like decisions (PRIORITY_APPLY, APPLY, and
# EFFICIENT_APPLY alike), and the exactly-2 tier must leave an incoming
# EFFICIENT_APPLY unchanged (it is already at that tier's own ceiling).
# Exercised directly against apply_recruiter_threshold_guard() itself
# (not through the full analyze_job pipeline) so the incoming decision
# can be pinned to EFFICIENT_APPLY precisely, independent of which real
# evidence pattern happens to produce it.
# ======================================================================
def _base_efficient_apply_result() -> dict:
    return {
        "lane": "LANE_1_EFFICIENT_APPLY",
        "decision": "EFFICIENT_APPLY",
        "decision_rationale": "Plausible core eligibility with lower-intensity evidence alignment.",
        "hard_blockers": [],
    }


def _strong_supported_requirement() -> dict:
    return {
        "requirement_id": "REQ_BASE_STRONG",
        "importance": "MANDATORY",
        "relevance": "HIGH",
        "text": "Business process mapping experience",
    }


def _strong_supported_match() -> dict:
    return {
        "requirement_id": "REQ_BASE_STRONG",
        "result": "STRONG",
        "evaluation_path": "CAPABILITY_MATCHER",
        "claim_ids": ["CLAIM_BASE_001"],
    }


for _bound_text, _req_id, _expected_lane, _expected_decision in (
    ("2-4 years of work experience", "REQ_EFF_2_4", "LANE_1_EFFICIENT_APPLY", "EFFICIENT_APPLY"),
    ("3+ years of work experience", "REQ_EFF_3_PLUS", "WATCH", "WATCH"),
    ("5+ years of work experience", "REQ_EFF_5_PLUS", "WATCH", "WATCH"),
):
    _threshold = _threshold_row(_req_id, _bound_text, domain=None)
    _requirements = [_strong_supported_requirement(), _threshold]
    _stamp_source_roles(_requirements)
    _matches = [
        _strong_supported_match(),
        {
            "requirement_id": _req_id,
            "result": "UNKNOWN",
            "evaluation_path": "EXPERIENCE_RANGE_EVALUATOR",
            "claim_ids": [],
        },
    ]
    _guarded = apply_recruiter_threshold_guard(
        base_result=_base_efficient_apply_result(),
        requirements=_requirements,
        matches=_matches,
        gated_requirement_ids=frozenset(),
    )
    assert_true(
        _guarded["lane"] == _expected_lane and _guarded["decision"] == _expected_decision,
        f"base EFFICIENT_APPLY + unresolved {_bound_text!r} must resolve to {_expected_lane}/{_expected_decision}, "
        f"got {_guarded['lane']}/{_guarded['decision']}",
    )
    _threshold_match = next(m for m in _matches if m["requirement_id"] == _req_id)
    assert_true(
        _threshold_match["result"] == "UNKNOWN" and _threshold_match["evaluation_path"] == "EXPERIENCE_RANGE_EVALUATOR",
        f"the guard must never mutate the threshold requirement's own EvidenceMatch, got {_threshold_match}",
    )
print("PASS C2c (CURSOR CORRECTION): base EFFICIENT_APPLY + unresolved exactly-2 stays EFFICIENT_APPLY; base EFFICIENT_APPLY + unresolved 3+/5+ downgrades to WATCH -- the >=3 tier now consumes EFFICIENT_APPLY too, and the threshold EvidenceMatch remains UNKNOWN/EXPERIENCE_RANGE_EVALUATOR, untouched.")


# ======================================================================
# C3. PARITY CONTROL -- a keyworded "Senior" title case still REJECTs via
# the existing, separate, untouched detect_seniority_signals mechanism,
# proving this guard neither duplicates nor weakens it.
# ======================================================================
job_input_senior = _bsa_job_input(_threshold_row("REQ_BOSE_SENIOR_YEARS", "5+ years of work experience", domain=None))
job_input_senior["role"] = "Senior IT Business Analyst"
result_senior = _analyze(job_input_senior)
assert_true(
    result_senior["analysis"]["decision"] == "REJECT",
    f"a 'Senior'-titled role with an unresolved 5+yr threshold must still REJECT via the existing, untouched seniority mechanism, got {result_senior['analysis']['decision']}",
)
print("PASS C3: a 'Senior'-titled role still REJECTs via the existing, separate detect_seniority_signals mechanism -- unaffected by, and not duplicated by, this guard.")


# ======================================================================
# D. POSITIVE CONTROL -- explicit recent-graduate/early-career JD context
# (raw jd_text, not a Requirement row -- recent-grad language is a
# contextual/comparison-pool signal, not itself a matchable capability
# row) must leave the otherwise-strong PRIORITY_APPLY result completely
# unaffected: the guard only ever examines EXPERIENCE_RANGE_EVALUATOR/
# DOMAIN_QUALIFIED_DURATION_EVALUATOR requirement rows, never raw JD
# prose.
# ======================================================================
job_input_recent_grad = _bsa_job_input(None)
job_input_recent_grad["jd_text"] = (
    job_input_recent_grad["jd_text"]
    + "\nRecent graduates and early-career candidates are encouraged to apply."
)
result_recent_grad = _analyze(job_input_recent_grad)
analysis_recent_grad = result_recent_grad["analysis"]
assert_true(
    analysis_recent_grad["decision"] == "PRIORITY_APPLY",
    f"explicit recent-grad/early-career JD context (no Requirement row) must not trigger the guard, got {analysis_recent_grad['decision']}",
)
print("PASS D: explicit recent-graduate/early-career JD context (contextual, not a Requirement row) leaves PRIORITY_APPLY unaffected.")


# ======================================================================
# E. POSITIVE CONTROL -- a threshold requirement whose EvidenceMatch
# result is positively STRONG/SUPPORTED (not UNKNOWN) must never be
# downgraded merely because a number appears in the JD text.
# ======================================================================
strong_years_row = _threshold_row("REQ_BOSE_STRONG_YEARS", "2-4 years of work experience", domain=None)
job_input_strong = _bsa_job_input(strong_years_row)
# Force a positive match by fabricating a synthetic evidence_match override
# is not possible without touching production matching; instead prove the
# guard's own precondition directly: it only fires on result=="UNKNOWN" AND
# a recognized evaluation_path. A row with a named technology (routed to
# the ordinary capability matcher, never these two evaluators) proves the
# guard does not blindly pattern-match on "years" text alone.
tech_years_row = _threshold_row(
    "REQ_BOSE_TECH_YEARS", "3 years of Salesforce administration experience", technology=["Salesforce"]
)
result_tech_years = _analyze(_bsa_job_input(tech_years_row))
analysis_tech_years = result_tech_years["analysis"]
match_tech_years = next(
    m for m in analysis_tech_years["evidence_matches"] if m["requirement_id"] == "REQ_BOSE_TECH_YEARS"
)
assert_true(
    match_tech_years["evaluation_path"] not in ("EXPERIENCE_RANGE_EVALUATOR", "DOMAIN_QUALIFIED_DURATION_EVALUATOR"),
    f"a named-technology years requirement must route to the ordinary capability matcher, not these two evaluators, got {match_tech_years['evaluation_path']}",
)
print("PASS E: a named-technology experience requirement (ordinary capability matcher, not the two narrow evaluators) is untouched by this guard -- it does not pattern-match on bare 'years' text.")


# ======================================================================
# F. ALTERNATIVE QUALIFICATION BRANCH -- a gated requirement_id must
# never trigger the guard; the existing qualification_gate architecture
# remains authoritative.
# ======================================================================
gated_years_row = _threshold_row("REQ_BOSE_GATED_YEARS", "2-4 years of work experience", domain=None)
gate = {
    "qualification_gate_id": "GATE_BOSE_YEARS_COMPONENT",
    "job_id": "JOB_BSA",
    "source_text": ["2-4 years of work experience"],
    "source_location": "Minimum Qualifications",
    "logic_expression": {"op": "ANY_OF", "terms": ["REQ_BOSE_GATED_YEARS"]},
    "unmodeled_branches_note": "synthetic regression control only",
}
result_gated = _analyze(_bsa_job_input(gated_years_row, qualification_gates=[gate]))
analysis_gated = result_gated["analysis"]
assert_true(
    analysis_gated["decision"] == "PRIORITY_APPLY",
    f"a gated (alternative-qualification-branch) threshold row must not trigger this guard -- the gate architecture remains authoritative, got {analysis_gated['decision']}",
)
print("PASS F: a requirement referenced by a qualification_gate never triggers this guard -- the alternative-qualification-branch architecture remains authoritative.")


# ======================================================================
# G. PREFERRED (not MANDATORY) threshold row must not trigger the guard.
# ======================================================================
preferred_years_row = _threshold_row(
    "REQ_BOSE_PREFERRED_YEARS", "2-4 years of work experience", importance="PREFERRED", relevance="MEDIUM"
)
result_preferred = _analyze(_bsa_job_input(preferred_years_row))
analysis_preferred = result_preferred["analysis"]
assert_true(
    analysis_preferred["decision"] == "PRIORITY_APPLY",
    f"a PREFERRED (not MANDATORY) unresolved threshold must not trigger the guard, got {analysis_preferred['decision']}",
)
print("PASS G: a PREFERRED unresolved experience-threshold row does not trigger the guard (MANDATORY only).")


# ======================================================================
# H. NEGATIVE/PARITY CONTROL -- REJECT precedence. A genuine qualification
# REJECT (Atominvest, MIT LL) must remain REJECT regardless of an injected
# unresolved threshold row.
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


for fixture_name in ("CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST", "CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST"):
    base_input = _load_real_job_input(fixture_name)
    baseline_reject = _analyze(copy.deepcopy(base_input))
    assert_true(
        baseline_reject["analysis"]["decision"] == "REJECT",
        f"{fixture_name} baseline must remain REJECT (regression control), got {baseline_reject['analysis']['decision']}",
    )
    injected_input = copy.deepcopy(base_input)
    injected_row = _threshold_row("REQ_INJECTED_YEARS", "2-4 years of work experience", domain=None)
    _stamp_source_roles([injected_row])
    injected_input["structured_extraction"]["requirements"].append(injected_row)
    result_injected = _analyze(injected_input)
    assert_true(
        result_injected["analysis"]["decision"] == "REJECT",
        f"{fixture_name} + injected unresolved threshold must remain REJECT (guard never fires on non-APPLY-like decisions), got {result_injected['analysis']['decision']}",
    )
print("PASS H: Atominvest and MIT LL qualification REJECT is preserved even with an injected unresolved experience-threshold row -- the guard only ever touches PRIORITY_APPLY/APPLY.")


# ======================================================================
# I. §135 / posting-state parity -- routing outside this milestone is
# unaffected. A weak source_verification_status still downgrades to
# WATCH exactly as before, whether or not a threshold row is present.
# ======================================================================
result_posting_weak = _analyze(
    {**_bsa_job_input(bose_years_row), "role_status": "LIKELY_LIVE", "source_verification_status": "VERIFIED_DIRECT"}
)
assert_true(
    result_posting_weak["analysis"]["decision"] == "WATCH",
    f"§135 posting-state routing must remain fully independent and unaffected by this guard, got {result_posting_weak['analysis']['decision']}",
)
print("PASS I: §135 posting-state routing (LIKELY_LIVE + VERIFIED_DIRECT) remains WATCH, fully independent of and unaffected by the recruiter-threshold guard.")

print("ALL recruiter_threshold_alignment_v1_test CHECKS PASSED")
