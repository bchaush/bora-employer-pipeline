"""Regression tests for POSTING_STATE_DECISION_WIRING_V1.

POSTING_STATE_WIRING_AUDIT_V1 proved that schemas/job.schema.json already
carries a complete, Blueprint-aligned posting-state vocabulary
(role_status, source_verification_status, date_last_verified, etc. --
Schema Milestone 1, closed architecture) but analyze_job()/
decide_lane_and_decision() never read, preserve, surface, or use any of
it. A synthetic, non-persistent probe proved a job explicitly marked
role_status=CONFIRMED_CLOSED produced an identical APPLY decision to one
marked VERIFIED_LIVE.

This milestone wires the existing vocabulary into decision routing only,
strictly AFTER the existing qualification decision is computed:

  - a qualification REJECT is never touched by posting state (a
    genuinely unqualified role stays REJECT regardless of freshness);
  - VERIFIED_LIVE / LIKELY_LIVE preserve the existing APPLY-like routing
    unchanged (LIKELY_LIVE is surfaced verbatim, never upgraded to
    VERIFIED_LIVE);
  - UNCLEAR / POSSIBLY_STALE / CONFIRMED_CLOSED downgrade an APPLY-like
    routing to WATCH (Blueprint Section 30: WATCH is valid where
    "posting status uncertain" or "potentially excellent job not
    currently active") -- the qualification result itself is never
    rewritten to REJECT;
  - requirement-level matches (STRONG/SUPPORTED/PARTIAL/NONE/UNKNOWN),
    gaps, unknowns, and hard_blockers are never modified by posting
    state -- only lane/decision/decision_rationale may change.

No new lane or decision enum value is introduced. No posting-status
classifier, web verification, or freshness-threshold logic is added --
this milestone only wires an already-known, caller-supplied posting
state into existing decision output.

Exercises real production code (job_analysis.py, job_decision.py) --
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

from job_analysis import analyze_job  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


# ======================================================================
# Fixture loading helpers -- reuse existing production fixtures only.
# No new fixture files are introduced by this milestone.
# ======================================================================
GOLDEN_DIR = ROOT / "golden-tests" / "job_analysis"
JOBS_DIR = ROOT / "fixtures" / "jobs"


def _load_golden_job_input(fixture_id: str) -> dict:
    """Mirror golden-tests/run_job_analysis_golden_set.py's job_input construction."""
    fixture_dir = GOLDEN_DIR / fixture_id
    extraction = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    job_input = {
        "company": f"Synthetic Golden Co ({fixture_id})",
        "role": extraction.get("_role_title") or fixture_id.replace("_", " "),
        "jd_text": jd_text,
        "fixture_key": fixture_id,
        "structured_extraction": {
            k: v for k, v in extraction.items() if not str(k).startswith("_")
        },
    }
    meta_role = extraction.get("_role_title")
    if isinstance(meta_role, str) and meta_role.strip():
        job_input["role"] = meta_role.strip()
    return job_input


def _load_real_job_input(fixture_dir_name: str) -> dict:
    fixture_dir = JOBS_DIR / fixture_dir_name
    job = json.loads((fixture_dir / "job.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_input = dict(job)
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    return job_input


# GT_IMPL_FIT is an existing golden fixture (Implementation fit with a
# material ServiceNow preferred gap) whose expected.json requires
# acceptable_decisions=["APPLY"], forbidden_decisions=["PRIORITY_APPLY",
# "REJECT"]. It is reused here verbatim -- not a new fixture.
QUALIFYING_BASE = _load_golden_job_input("GT_IMPL_FIT")

ATOMINVEST_BASE = _load_real_job_input("CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST")
MIT_LL_BASE = _load_real_job_input("CASE_C_MIT_LL_BUSINESS_SYSTEMS_ANALYST")


def _analyze(job_input: dict) -> dict:
    result = analyze_job(job_input)
    assert_true(result["valid"] is True, f"analyze_job must be valid: {result.get('errors')}")
    return result


def _with_posting_state(base: dict, **posting_fields) -> dict:
    job_input = copy.deepcopy(base)
    job_input.update(posting_fields)
    return job_input


# ======================================================================
# A. VERIFIED_LIVE positive control -- existing APPLY-like routing
#    preserved exactly. Computed first so later sections can assert
#    byte-equivalent qualification structures against it.
# ======================================================================
result_live = _analyze(_with_posting_state(QUALIFYING_BASE, role_status="VERIFIED_LIVE"))
analysis_live = result_live["analysis"]
assert_true(analysis_live["decision"] == "APPLY", f"VERIFIED_LIVE qualifying job must remain APPLY, got {analysis_live['decision']}")
assert_true(analysis_live["lane"] != "WATCH", "VERIFIED_LIVE must not be downgraded")
assert_true(analysis_live["role_status"] == "VERIFIED_LIVE", "VERIFIED_LIVE must be surfaced verbatim")
print("PASS A: role_status=VERIFIED_LIVE preserves existing APPLY-like routing and is surfaced verbatim.")


# ======================================================================
# B. LIKELY_LIVE positive control -- routing preserved; surfaced
#    verbatim; never silently upgraded to VERIFIED_LIVE.
# ======================================================================
result_likely = _analyze(_with_posting_state(QUALIFYING_BASE, role_status="LIKELY_LIVE"))
analysis_likely = result_likely["analysis"]
assert_true(
    analysis_likely["decision"] == "APPLY" and analysis_likely["lane"] == analysis_live["lane"],
    f"LIKELY_LIVE must preserve existing APPLY-like routing, got {analysis_likely['lane']}/{analysis_likely['decision']}",
)
assert_true(
    analysis_likely["role_status"] == "LIKELY_LIVE",
    f"LIKELY_LIVE must be surfaced exactly, not converted to VERIFIED_LIVE; got {analysis_likely['role_status']!r}",
)
print("PASS B: role_status=LIKELY_LIVE preserves existing APPLY-like routing and is surfaced exactly (never upgraded to VERIFIED_LIVE).")


# ======================================================================
# ABSENT. Missing/None role_status must NOT be treated as favorable.
# UNKNOWN/missing posting-state evidence must not silently become an
# actionable state -- absence of any role_status must downgrade an
# APPLY-like qualification result to WATCH exactly like an explicit
# UNCLEAR/POSSIBLY_STALE/CONFIRMED_CLOSED value, while still surfacing
# role_status=null (never coerced to any enum value). This is the
# corrected behavior; it previously (incorrectly) preserved APPLY.
# ======================================================================
result_absent = _analyze(copy.deepcopy(QUALIFYING_BASE))
analysis_absent = result_absent["analysis"]
assert_true(
    analysis_absent["lane"] == "WATCH" and analysis_absent["decision"] == "WATCH",
    f"absent role_status must downgrade an APPLY-like decision to WATCH (missing posting-state evidence is not favorable), got {analysis_absent['lane']}/{analysis_absent['decision']}",
)
assert_true(
    analysis_absent.get("role_status") is None,
    f"absent role_status must surface as null, never coerced to an enum value (not UNCLEAR, not VERIFIED_LIVE), got {analysis_absent.get('role_status')!r}",
)
assert_true(
    "missing" in analysis_absent["decision_rationale"].casefold()
    or "posting" in analysis_absent["decision_rationale"].casefold()
    or "role_status" in analysis_absent["decision_rationale"],
    f"decision_rationale must explicitly identify missing posting-state verification, got {analysis_absent['decision_rationale']!r}",
)
assert_true(
    analysis_absent["requirements"] == analysis_live["requirements"],
    "absent role_status must not alter requirement-level records",
)
assert_true(
    analysis_absent["evidence_matches"] == analysis_live["evidence_matches"],
    "absent role_status must not alter requirement-level evidence matches",
)
assert_true(
    analysis_absent["gaps"] == analysis_live["gaps"] and analysis_absent["unknowns"] == analysis_live["unknowns"],
    "absent role_status must not alter gaps/unknowns",
)
assert_true(
    result_absent["hard_blockers"] == result_live["hard_blockers"],
    "absent role_status must not alter hard_blockers",
)
print("PASS ABSENT: missing/None role_status downgrades an otherwise APPLY-like qualification result to WATCH, surfaces role_status=null (never fabricated), names missing posting-state verification in the rationale, and leaves qualification structures byte-identical to the VERIFIED_LIVE case.")


# ======================================================================
# C/D/E. UNCLEAR / POSSIBLY_STALE / CONFIRMED_CLOSED all downgrade an
#    APPLY-like decision to WATCH. Requirement-level matches/gaps/
#    unknowns must remain byte-equivalent to the VERIFIED_LIVE case --
#    only lane/decision/decision_rationale may differ.
# ======================================================================
for status in ("UNCLEAR", "POSSIBLY_STALE", "CONFIRMED_CLOSED"):
    result_downgrade = _analyze(_with_posting_state(QUALIFYING_BASE, role_status=status))
    analysis_downgrade = result_downgrade["analysis"]
    assert_true(
        analysis_downgrade["lane"] == "WATCH" and analysis_downgrade["decision"] == "WATCH",
        f"role_status={status} must downgrade an APPLY-like decision to WATCH, got {analysis_downgrade['lane']}/{analysis_downgrade['decision']}",
    )
    assert_true(
        analysis_downgrade["decision"] != "REJECT",
        f"role_status={status} must NEVER convert the qualification result to REJECT (posting reality != qualification truth), got {analysis_downgrade['decision']}",
    )
    assert_true(
        analysis_downgrade["requirements"] == analysis_live["requirements"],
        f"role_status={status} must not alter requirement-level records",
    )
    assert_true(
        analysis_downgrade["evidence_matches"] == analysis_live["evidence_matches"],
        f"role_status={status} must not alter requirement-level evidence matches (STRONG/SUPPORTED/PARTIAL/NONE/UNKNOWN)",
    )
    assert_true(
        analysis_downgrade["gaps"] == analysis_live["gaps"] and analysis_downgrade["unknowns"] == analysis_live["unknowns"],
        f"role_status={status} must not alter gaps/unknowns",
    )
    assert_true(
        result_downgrade["hard_blockers"] == result_live["hard_blockers"],
        f"role_status={status} must not alter hard_blockers",
    )
    assert_true(
        analysis_downgrade["role_status"] == status,
        f"role_status must be surfaced verbatim as {status}, got {analysis_downgrade['role_status']!r}",
    )
print("PASS C/D/E: UNCLEAR, POSSIBLY_STALE, and CONFIRMED_CLOSED all downgrade an APPLY-like decision to WATCH (never REJECT) with byte-identical requirements/evidence_matches/gaps/unknowns/hard_blockers to the VERIFIED_LIVE case.")


# ======================================================================
# F. REJECT precedence -- a qualification REJECT (Atominvest, MIT LL)
#    must remain REJECT regardless of posting state, including
#    CONFIRMED_CLOSED and UNCLEAR. No blocker/match regression.
# ======================================================================
for fixture_name, base_input in (
    ("ATOMINVEST", ATOMINVEST_BASE),
    ("MIT_LL", MIT_LL_BASE),
):
    baseline_reject = _analyze(copy.deepcopy(base_input))
    assert_true(
        baseline_reject["analysis"]["decision"] == "REJECT",
        f"{fixture_name} baseline must remain REJECT (regression control), got {baseline_reject['analysis']['decision']}",
    )
    for status in ("VERIFIED_LIVE", "LIKELY_LIVE", "UNCLEAR", "POSSIBLY_STALE", "CONFIRMED_CLOSED"):
        result_reject = _analyze(_with_posting_state(base_input, role_status=status))
        analysis_reject = result_reject["analysis"]
        assert_true(
            analysis_reject["decision"] == "REJECT" and analysis_reject["lane"] == "LANE_0_REJECT",
            f"{fixture_name} with role_status={status} must remain REJECT/LANE_0_REJECT, got {analysis_reject['lane']}/{analysis_reject['decision']}",
        )
        assert_true(
            result_reject["hard_blockers"] == baseline_reject["hard_blockers"],
            f"{fixture_name} with role_status={status} must not alter hard_blockers",
        )
        assert_true(
            analysis_reject["evidence_matches"] == baseline_reject["analysis"]["evidence_matches"],
            f"{fixture_name} with role_status={status} must not alter evidence_matches",
        )
print("PASS F: Atominvest and MIT LL qualification REJECT is preserved under every role_status value, including CONFIRMED_CLOSED and UNCLEAR; hard_blockers and evidence_matches are unchanged.")


# ======================================================================
# G. source_verification_status is surfaced independently of
#    role_status -- neither is derived from the other.
# ======================================================================
result_independent = _analyze(
    _with_posting_state(
        QUALIFYING_BASE,
        role_status="POSSIBLY_STALE",
        source_verification_status="SOURCE_VERIFICATION_REQUIRED",
    )
)
analysis_independent = result_independent["analysis"]
assert_true(
    analysis_independent["role_status"] == "POSSIBLY_STALE",
    f"role_status must survive unchanged alongside source_verification_status, got {analysis_independent['role_status']!r}",
)
assert_true(
    analysis_independent["source_verification_status"] == "SOURCE_VERIFICATION_REQUIRED",
    f"source_verification_status must survive unchanged, got {analysis_independent['source_verification_status']!r}",
)

# source_verification_status alone (no role_status) must not fabricate
# or derive a role_status value, and -- critically -- a direct-source
# verification signal is a separate axis and cannot by itself supply
# posting-freshness evidence: the job must still downgrade to WATCH
# because role_status remains genuinely absent.
result_source_only = _analyze(
    _with_posting_state(QUALIFYING_BASE, source_verification_status="VERIFIED_DIRECT")
)
analysis_source_only = result_source_only["analysis"]
assert_true(
    analysis_source_only.get("role_status") is None,
    f"source_verification_status alone must not derive/fabricate role_status, got {analysis_source_only.get('role_status')!r}",
)
assert_true(
    analysis_source_only["source_verification_status"] == "VERIFIED_DIRECT",
    "source_verification_status must still be surfaced when role_status is absent",
)
assert_true(
    analysis_source_only["lane"] == "WATCH" and analysis_source_only["decision"] == "WATCH",
    f"source_verification_status=VERIFIED_DIRECT alone must NOT make the job actionable -- role_status is still absent, so WATCH must remain WATCH, got {analysis_source_only['lane']}/{analysis_source_only['decision']}",
)
print("PASS G: role_status and source_verification_status are surfaced independently; neither is derived from the other; VERIFIED_DIRECT source verification cannot substitute for missing posting-freshness evidence -- WATCH remains WATCH.")


# ======================================================================
# H. date_last_verified survives into analysis output unchanged. No
#    freshness-threshold or date-arithmetic logic is introduced. A
#    verification date alone (still no role_status) does not make the
#    job actionable either.
# ======================================================================
result_date = _analyze(_with_posting_state(QUALIFYING_BASE, date_last_verified="2026-08-25"))
analysis_date = result_date["analysis"]
assert_true(
    analysis_date["date_last_verified"] == "2026-08-25",
    f"date_last_verified must survive unchanged, got {analysis_date['date_last_verified']!r}",
)
assert_true(
    analysis_date["lane"] == "WATCH" and analysis_date["decision"] == "WATCH",
    f"date_last_verified alone (still no role_status) must not make the job actionable, got {analysis_date['lane']}/{analysis_date['decision']}",
)
print("PASS H: date_last_verified survives into analysis output unchanged; no staleness-threshold logic was introduced; a bare verification date does not substitute for missing role_status.")

# ======================================================================
# I. SECOND BOUNDED CORRECTION -- malformed/invalid role_status values
#    must never crash and must never preserve an APPLY-like decision.
#    Cursor adversarial review found: (1) role_status=123 preserved APPLY
#    while output normalization silently turned it into null, producing
#    a valid=True false-actionable result; (2) role_status=[] raised an
#    uncontrolled TypeError inside posting-state routing (unhashable
#    type in a frozenset membership check). Only a canonical role_status
#    STRING may ever drive routing as a recognized state -- everything
#    else (wrong type, or a string that is not one of the five canonical
#    values) must route exactly like a missing/None value: WATCH for an
#    otherwise APPLY-like qualification, no exception, no fabricated
#    canonical value.
# ======================================================================
for bad_value, label in (
    (123, "int"),
    ([], "list"),
    ("BOGUS", "invalid string"),
    (True, "bool (subclass of int)"),
):
    job_input = _with_posting_state(QUALIFYING_BASE, role_status=bad_value)
    try:
        result = analyze_job(job_input)
    except Exception as exc:  # noqa: BLE001 -- the exact failure mode under test
        assert_true(False, f"role_status={bad_value!r} ({label}) must not raise; got {type(exc).__name__}: {exc}")
        raise

    if result["valid"]:
        analysis_bad = result["analysis"]
        assert_true(
            analysis_bad["decision"] != "APPLY" and analysis_bad["decision"] not in ("PRIORITY_APPLY", "EFFICIENT_APPLY"),
            f"role_status={bad_value!r} ({label}) must NOT preserve an APPLY-like decision when valid=True; got {analysis_bad['decision']}",
        )
        assert_true(
            analysis_bad["lane"] == "WATCH" and analysis_bad["decision"] == "WATCH",
            f"role_status={bad_value!r} ({label}) with valid=True must route WATCH for an otherwise APPLY-like qualification; got {analysis_bad['lane']}/{analysis_bad['decision']}",
        )
    else:
        # A malformed value that additionally fails output schema
        # validation (e.g. an invalid string caught by the role_status
        # enum) is an acceptable, explicitly fail-visible outcome -- as
        # long as it never raised and never reported valid=True with an
        # APPLY-like decision (checked above for the valid=True branch).
        assert_true(
            isinstance(result.get("errors"), list) and len(result["errors"]) > 0,
            f"role_status={bad_value!r} ({label}) with valid=False must carry a diagnosable error, got {result.get('errors')}",
        )
print("PASS I: malformed role_status values (int, list, invalid string, bool) never raise and never preserve an APPLY-like decision -- routing treats them as unverified (WATCH), matching the missing/None case.")


# ======================================================================
# E (restated). Canonical statuses and None still behave identically to
#    the first bounded correction after this second correction.
# ======================================================================
for status in ("VERIFIED_LIVE", "LIKELY_LIVE"):
    r = _analyze(_with_posting_state(QUALIFYING_BASE, role_status=status))
    assert_true(r["analysis"]["decision"] == "APPLY", f"canonical live status {status} regressed: {r['analysis']['decision']}")
for status in ("UNCLEAR", "POSSIBLY_STALE", "CONFIRMED_CLOSED", None):
    ji = _with_posting_state(QUALIFYING_BASE, role_status=status) if status is not None else copy.deepcopy(QUALIFYING_BASE)
    r = _analyze(ji)
    assert_true(r["analysis"]["decision"] == "WATCH", f"canonical/absent WATCH-triggering status {status!r} regressed: {r['analysis']['decision']}")
print("PASS E (restated): all five canonical role_status values plus None continue to route exactly as specified after the second bounded correction.")


# ======================================================================
# J. WATCH-base regression -- a qualification result that is ALREADY
#    WATCH (for reasons unrelated to posting state, e.g. information
#    deficit) must remain WATCH under every role_status value, and the
#    original WATCH rationale must not be erased/overwritten.
# ======================================================================
WATCH_BASE = _load_golden_job_input("GT_VAGUE_JD")
watch_baseline = _analyze(copy.deepcopy(WATCH_BASE))
assert_true(
    watch_baseline["analysis"]["decision"] == "WATCH",
    f"GT_VAGUE_JD baseline must already be WATCH (unrelated to posting state), got {watch_baseline['analysis']['decision']}",
)
original_rationale = watch_baseline["analysis"]["decision_rationale"]
for status in ("VERIFIED_LIVE", "CONFIRMED_CLOSED", None):
    ji = _with_posting_state(WATCH_BASE, role_status=status) if status is not None else copy.deepcopy(WATCH_BASE)
    r = _analyze(ji)
    assert_true(
        r["analysis"]["decision"] == "WATCH" and r["analysis"]["lane"] == "WATCH",
        f"WATCH-base job with role_status={status!r} must remain WATCH, got {r['analysis']['lane']}/{r['analysis']['decision']}",
    )
    assert_true(
        r["analysis"]["decision_rationale"] == original_rationale,
        f"WATCH-base decision_rationale must not be altered by posting-state routing (posting routing only applies to APPLY-like decisions) for role_status={status!r}; got {r['analysis']['decision_rationale']!r}",
    )
print("PASS J: a qualification result that is already WATCH for unrelated reasons (information deficit) remains WATCH under every role_status value, and its original rationale is never overwritten by posting-state routing.")

print("ALL posting_state_decision_wiring_v1_test CHECKS PASSED")
