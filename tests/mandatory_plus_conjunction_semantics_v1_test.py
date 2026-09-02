"""Regression tests for MANDATORY_PLUS_CONJUNCTION_SEMANTICS_V1.

The bare word "plus" was previously matched by _PREFERRED_CUES in
requirement_normalize.py, intending to catch the bonus idiom ("SQL
experience is a plus"). It also matched "plus" used as a conjunction
("Bachelor's degree plus a minimum of seven years of experience" -- meaning
"and"), which co-occurring mandatory language (e.g. "minimum") then
downgraded to MIXED/UNCLEAR -- silently removing frozen MIT's real,
MANDATORY, HIGH-relevance core qualifications requirement
(REQ_C_DEGREE_EXPERIENCE) from hard-block and gap detection.

The fix anchors the preferred-cue pattern to "a plus" (a bigram) instead of
bare "plus" -- every real bonus-idiom construction has the article "a"
immediately before "plus"; the conjunction use never does.

Exercises real production code (requirement_normalize.py, job_analysis.py)
against the actual frozen MIT and Atominvest fixtures -- no logic is
duplicated here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from job_analysis import analyze_job  # noqa: E402
from requirement_normalize import classify_importance_from_source  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_A = ROOT / "fixtures" / "jobs" / "CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST"
FIXTURE_C = ROOT / "fixtures" / "jobs" / "CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST"


def _load_job_input(fixture_dir: Path) -> dict:
    job = json.loads((fixture_dir / "job.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_input = dict(job)
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    return job_input


# ======================================================================
# A. Conjunction case: "degree plus years" must classify MANDATORY, not
#    UNCLEAR/PREFERRED -- the reproduced core defect.
# ======================================================================
conjunction_text = "Bachelor's degree plus a minimum of seven years of experience"
result_a = classify_importance_from_source(conjunction_text, proposed="MANDATORY", category="EXPERIENCE")
assert_true(
    result_a == "MANDATORY",
    f"conjunction 'plus' construction must classify MANDATORY, got {result_a}",
)
print("PASS A: 'Bachelor's degree plus a minimum of seven years of experience' classifies MANDATORY (not UNCLEAR).")


# ======================================================================
# B. Frozen MIT REQ_C_DEGREE_EXPERIENCE through the real production
#    analyze_job() path: importance is now MANDATORY/HIGH, the
#    requirement correctly appears as a hard blocker (result=NONE,
#    candidate evidence does not support it), and overall MIT routing
#    remains LANE_0_REJECT/REJECT.
# ======================================================================
result_mit = analyze_job(_load_job_input(FIXTURE_C))
assert_true(result_mit["valid"] is True, f"MIT analysis must be valid: {result_mit['errors']}")
analysis_mit = result_mit["analysis"]
req_degree_exp = next(r for r in analysis_mit["requirements"] if r["requirement_id"] == "REQ_C_DEGREE_EXPERIENCE")
assert_true(
    req_degree_exp["importance"] == "MANDATORY" and req_degree_exp["relevance"] == "HIGH",
    f"REQ_C_DEGREE_EXPERIENCE must normalize to MANDATORY/HIGH, got {req_degree_exp['importance']}/{req_degree_exp['relevance']}",
)
match_degree_exp = next(m for m in analysis_mit["evidence_matches"] if m["requirement_id"] == "REQ_C_DEGREE_EXPERIENCE")
assert_true(
    match_degree_exp["result"] == "NONE",
    f"REQ_C_DEGREE_EXPERIENCE must resolve NONE (no candidate evidence), got {match_degree_exp['result']}",
)
assert_true(
    any("REQ_C_DEGREE_EXPERIENCE" in b for b in result_mit["hard_blockers"]),
    f"REQ_C_DEGREE_EXPERIENCE must now appear as a hard blocker; got {result_mit['hard_blockers']}",
)
assert_true(
    analysis_mit["lane"] == "LANE_0_REJECT" and analysis_mit["decision"] == "REJECT",
    f"MIT overall routing must remain LANE_0_REJECT/REJECT, got {analysis_mit['lane']}/{analysis_mit['decision']}",
)
print("PASS B: frozen MIT REQ_C_DEGREE_EXPERIENCE now correctly normalizes MANDATORY/HIGH and appears as a real hard blocker; MIT overall remains LANE_0_REJECT/REJECT.")


# ======================================================================
# C. Preference control: "SQL experience is a plus" must remain PREFERRED.
# ======================================================================
result_c = classify_importance_from_source("SQL experience is a plus")
assert_true(result_c == "PREFERRED", f"'SQL experience is a plus' must remain PREFERRED, got {result_c}")
print("PASS C: 'SQL experience is a plus' remains correctly classified PREFERRED.")


# ======================================================================
# D. Real Atominvest wording control: "... is a plus, not a requirement"
#    must continue classifying as non-mandatory, through both the direct
#    classifier and the real production analyze_job() path.
# ======================================================================
result_d = classify_importance_from_source(
    "SQL or API exposure is a plus, not a requirement", proposed="PREFERRED"
)
assert_true(result_d == "PREFERRED", f"Atominvest's real 'is a plus, not a requirement' wording must remain PREFERRED, got {result_d}")

result_atominvest = analyze_job(_load_job_input(FIXTURE_A))
assert_true(result_atominvest["valid"] is True, f"Atominvest analysis must be valid: {result_atominvest['errors']}")
analysis_a = result_atominvest["analysis"]
for req_id in ("REQ_A_INDUSTRY_EXP_PLUS", "REQ_A_SQL_API_PLUS"):
    req = next(r for r in analysis_a["requirements"] if r["requirement_id"] == req_id)
    assert_true(
        req["importance"] == "PREFERRED",
        f"{req_id} (real Atominvest 'a plus' wording) must remain PREFERRED, got {req['importance']}",
    )
# SOURCE_SEMANTIC_ROLE_QUALIFICATION_VIEW_V1 (post-dates this milestone):
# REQ_A_CONFIG_IMPLEMENTATION and REQ_A_QA_TROUBLESHOOTING are
# responsibility-sourced and no longer independently hard-block; updated
# to the current adjudicated baseline.
expected_blockers = {
    "REQ_A_DEGREE",
    "REQ_A_EXCEL_DATA",
}
actual_blocked_ids = {b.rsplit(": ", 1)[-1] for b in result_atominvest["hard_blockers"]}
assert_true(
    actual_blocked_ids == expected_blockers,
    f"Atominvest hard blockers must remain exactly {expected_blockers}, got {actual_blocked_ids}",
)
assert_true(
    analysis_a["lane"] == "LANE_0_REJECT" and analysis_a["decision"] == "REJECT",
    "Atominvest overall routing must remain LANE_0_REJECT/REJECT",
)
print("PASS D: real Atominvest 'a plus, not a requirement' wording remains PREFERRED; Atominvest blockers and overall routing are unchanged.")


# ======================================================================
# E. Adversarial preference constructions -- must all remain non-MANDATORY
#    (PREFERRED, since none contains a co-occurring mandatory cue).
# ======================================================================
preference_variants = (
    "is a plus",
    "would be a plus",
    "a plus",
    "considered a plus",
    "is a plus, not a requirement",
)
for text in preference_variants:
    result = classify_importance_from_source(text)
    assert_true(
        result == "PREFERRED",
        f"{text!r} must classify PREFERRED, got {result}",
    )
print("PASS E: adversarial bonus-idiom constructions ('is a plus', 'would be a plus', 'a plus', 'considered a plus', 'is a plus, not a requirement') all remain PREFERRED.")


# ======================================================================
# F. Adversarial conjunction constructions -- must never be treated as a
#    preferred cue (no MIXED/PREFERRED downgrade merely because "plus"
#    appears as a conjunction).
# ======================================================================
from requirement_normalize import _PREFERRED_CUES  # noqa: E402

conjunction_variants = (
    "degree plus 2 years of experience",
    "Bachelor's plus relevant experience",
    "education plus experience",
    "3 years of experience plus a bachelor's degree",
)
for text in conjunction_variants:
    assert_true(
        _PREFERRED_CUES.search(text) is None,
        f"{text!r} must NOT match the preferred-cue pattern -- 'plus' is used as a conjunction, not a bonus idiom",
    )
print("PASS F: adversarial conjunction constructions never trigger the preferred-cue pattern.")

print("ALL mandatory_plus_conjunction_semantics_v1_test CHECKS PASSED")
