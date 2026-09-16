"""Regression matrix for JIT_PRE_SURFACING_VERIFICATION_GATE_V1.

Real failure provenance: September 15 Personal-v1 operating runs repeatedly showed
indexed/cached discovery evidence diverging from exact current requisition state.
This test exercises production analyze_job(); it does not duplicate gate logic.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from job_analysis import analyze_job  # noqa: E402
from jit_pre_surfacing_verification import evaluate_pre_surfacing_verification  # noqa: E402

GOLDEN = ROOT / "golden-tests" / "job_analysis" / "GT_IMPL_FIT"
extraction = json.loads((GOLDEN / "structured_extraction.json").read_text(encoding="utf-8"))
BASE = {
    "company": "Synthetic Golden Co (GT_IMPL_FIT)",
    "role": extraction.get("_role_title") or "Implementation Analyst",
    "official_url": "https://careers.example.test/jobs/REQ-123",
    "operation_run_id": "RUN_JIT_TEST_CURRENT",
    "date_last_verified": "2026-09-15",
    "role_status": "VERIFIED_LIVE",
    "source_verification_status": "VERIFIED_DIRECT",
    "jd_text": (GOLDEN / "jd.txt").read_text(encoding="utf-8"),
    "structured_extraction": {k: v for k, v in extraction.items() if not str(k).startswith("_")},
}


def check(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def analyze(extra: dict | None = None) -> dict:
    job = copy.deepcopy(BASE)
    if extra:
        job.update(copy.deepcopy(extra))
    result = analyze_job(job)
    check(result["valid"] is True, f"analysis invalid: {result.get('errors')}")
    return result


def packet(**overrides) -> dict:
    value = {
        "verification_kind": "JIT_PRE_SURFACING_VERIFICATION_V1",
        "operation_run_id": "RUN_JIT_TEST_CURRENT",
        "observed_at": "2026-09-15T21:35:00-04:00",
        "source_kind": "FIRST_PARTY_DIRECT",
        "exact_url": BASE["official_url"],
        "observed_company": BASE["company"],
        "observed_role": BASE["role"],
        "substantive_role_content_present": True,
        "application_route_status": "ACTIONABLE",
        "recency_observation": {
            "state": "AUTHORITATIVE_LIVE_RELATIVE_AGE",
            "source_kind": "FIRST_PARTY_DIRECT",
            "observed_at": "2026-09-15T21:35:00-04:00",
            "posted_age_days": 2,
        },
        "material_conflicts": [],
        "resolved_conflicts": [],
    }
    value.update(overrides)
    return value
# 1. Pre-fix causal reproduction: favorable strings alone must no longer pass.
missing = analyze()
check(missing["analysis"]["decision"] == "WATCH", "favorable strings without verification envelope must WATCH")
check(
    any("CURRENT_VERIFICATION_EVIDENCE_MISSING" in w for w in missing["analysis"]["warnings"]),
    "missing packet must surface CURRENT_VERIFICATION_EVIDENCE_MISSING",
)
print("PASS 1: favorable caller strings alone cannot establish current actionability.")

# 2. Genuine exact-current positive control must still pass.
positive = analyze({"pre_surfacing_verification": packet()})
check(positive["analysis"]["decision"] == "APPLY", "valid current-run direct packet must preserve APPLY")
check(positive["analysis"]["lane"] != "WATCH", "positive control must not be downgraded")
print("PASS 2: genuine current-run first-party positive control still passes.")

# 3. Dead exact requisition cannot promote.
dead = packet(substantive_role_content_present=False, application_route_status="UNAVAILABLE")
r = analyze({"pre_surfacing_verification": dead})
check(r["analysis"]["decision"] == "WATCH", "dead exact requisition must WATCH")
print("PASS 3: dead/error exact requisition fails closed.")
# 4. Same-title / sibling identity contamination cannot promote.
sibling = packet(exact_url="https://careers.example.test/jobs/REQ-999")
r = analyze({"pre_surfacing_verification": sibling})
check(r["analysis"]["decision"] == "WATCH", "evidence for sibling requisition must not authorize this job")
print("PASS 4: sibling/exact-URL identity mismatch fails closed.")

# 5. Verification from another operating run is stale for this run.
stale_run = packet(operation_run_id="RUN_OLD_CAPTURE")
r = analyze({"pre_surfacing_verification": stale_run})
check(r["analysis"]["decision"] == "WATCH", "old-run verification must not authorize current promotion")
print("PASS 5: stale prior-run verification cannot masquerade as current.")

# 6. Third-party-only evidence may nominate but cannot establish direct verification.
third_party = packet(source_kind="THIRD_PARTY_DISCOVERY")
r = analyze({"pre_surfacing_verification": third_party})
check(r["analysis"]["decision"] == "WATCH", "third-party-only packet must not establish VERIFIED_DIRECT")
print("PASS 6: third-party-only discovery evidence fails the direct-verification gate.")
# 7. Material current-source conflict must fail closed.
conflicted = packet(material_conflicts=["CURRENT_ACTIONABILITY_CONFLICT"])
r = analyze({"pre_surfacing_verification": conflicted})
check(r["analysis"]["decision"] == "WATCH", "unresolved current-source conflict must WATCH")
print("PASS 7: unresolved material source conflict fails closed.")

# 8. Search-recency conflict may be explicitly resolved by authoritative employer evidence.
resolved = packet(
    resolved_conflicts=["SEARCH_RECENCY_OVERRIDDEN_BY_CURRENT_FIRST_PARTY_RECENCY"],
)
r = analyze({"pre_surfacing_verification": resolved})
check(r["analysis"]["decision"] == "APPLY", "resolved weaker-source recency conflict must not block")
print("PASS 8: authoritative first-party recency may resolve weaker discovery recency conflict.")

# 9. Missing authoritative recency provenance remains unknown/fail-closed for promotion.
unknown_recency = packet(recency_observation={"state": "UNKNOWN"})
r = analyze({"pre_surfacing_verification": unknown_recency})
check(r["analysis"]["decision"] == "WATCH", "unknown authoritative recency must not promote")
print("PASS 9: unknown recency stays unknown and blocks serious promotion.")
# 10. Actionability verification must not alter qualification truth.
positive_analysis = positive["analysis"]
failed_analysis = analyze({"pre_surfacing_verification": conflicted})["analysis"]
for key in ("requirements", "evidence_matches", "gaps", "unknowns", "qualification_gaps", "qualification_unknowns"):
    check(failed_analysis[key] == positive_analysis[key], f"verification gate must not alter {key}")
check(failed_analysis["decision"] == "WATCH", "conflict may downgrade pursuit only")
print("PASS 10: verification gate is qualification-independent and downgrade-only.")

# 11. Input/historical snapshot facts are not rewritten by analysis.
historical = copy.deepcopy(BASE)
historical["jd_snapshot"] = "Historical JD snapshot must remain untouched."
historical["application_status"] = "SUBMITTED"
historical["pre_surfacing_verification"] = dead
before = copy.deepcopy(historical)
_ = analyze_job(historical)
check(historical == before, "analyze_job must not mutate historical input truth")
print("PASS 11: later non-actionability does not rewrite historical input/application truth.")

# 12. Recency state name alone is insufficient; provenance/value are required.
bad_recency = packet(recency_observation={"state": "AUTHORITATIVE_LIVE_RELATIVE_AGE"})
r = analyze({"pre_surfacing_verification": bad_recency})
check(r["analysis"]["decision"] == "WATCH", "recency state without source/timestamp/value must WATCH")
print("PASS 12: recency provenance cannot be asserted by state name alone.")

# 13. Verification date must agree with the current-run observation date.
r = analyze({"date_last_verified": "2026-09-14", "pre_surfacing_verification": packet()})
check(r["analysis"]["decision"] == "WATCH", "date_last_verified mismatch must WATCH")
print("PASS 13: stale/mismatched verification date fails closed.")

# 14. Absolute employer-authored posting date is a valid authoritative recency shape.
absolute = packet(recency_observation={"state": "AUTHORITATIVE_ABSOLUTE_DATE", "source_kind": "FIRST_PARTY_DIRECT", "observed_at": "2026-09-15T21:35:00-04:00", "posted_date": "2026-09-10"})
r = analyze({"pre_surfacing_verification": absolute})
check(r["analysis"]["decision"] == "APPLY", "valid employer absolute-date recency must preserve APPLY")
print("PASS 14: authoritative employer absolute date is accepted without search-date substitution.")

# 15. A current authoritative application window is valid without inventing a posting date.
window = packet(recency_observation={"state": "AUTHORITATIVE_APPLICATION_WINDOW", "source_kind": "FIRST_PARTY_DIRECT", "observed_at": "2026-09-15T21:35:00-04:00", "opened_date": "2026-09-10", "close_date": "2026-09-20"})
r = analyze({"pre_surfacing_verification": window})
check(r["analysis"]["decision"] == "APPLY", "current authoritative application window must preserve APPLY")
print("PASS 15: current authoritative application window is accepted without inferring a posting date.")

# 16-18. Application windows must be temporally meaningful at observation time.
for label, recency in (
    ("expired close", {"state": "AUTHORITATIVE_APPLICATION_WINDOW", "source_kind": "FIRST_PARTY_DIRECT", "observed_at": "2026-09-15T21:35:00-04:00", "close_date": "2026-09-14"}),
    ("future open", {"state": "AUTHORITATIVE_APPLICATION_WINDOW", "source_kind": "FIRST_PARTY_DIRECT", "observed_at": "2026-09-15T21:35:00-04:00", "opened_date": "2026-09-16"}),
    ("inverted bounds", {"state": "AUTHORITATIVE_APPLICATION_WINDOW", "source_kind": "FIRST_PARTY_DIRECT", "observed_at": "2026-09-15T21:35:00-04:00", "opened_date": "2026-09-20", "close_date": "2026-09-10"}),
):
    r = analyze({"pre_surfacing_verification": packet(recency_observation=recency)})
    check(r["analysis"]["decision"] == "WATCH", f"{label} application window must WATCH")
print("PASS 16-18: expired, future-only, and inverted application windows fail closed.")

# 19. Material conflicts cannot be laundered into resolved_conflicts.
laundered = packet(material_conflicts=[], resolved_conflicts=["CURRENT_ACTIONABILITY_CONFLICT"])
r = analyze({"pre_surfacing_verification": laundered})
check(r["analysis"]["decision"] == "WATCH", "material conflict parked in resolved_conflicts must WATCH")
print("PASS 19: resolved_conflicts cannot launder a material actionability conflict.")

# 20. Malformed material_conflicts shape fails closed.
malformed_conflicts = packet(material_conflicts=None)
r = analyze({"pre_surfacing_verification": malformed_conflicts})
check(r["analysis"]["decision"] == "WATCH", "non-list material_conflicts must WATCH")
print("PASS 20: malformed material_conflicts fails closed.")

# 21. Provenance timestamp must be timezone-aware.
naive = packet(observed_at="2026-09-15T21:35:00", recency_observation={"state": "AUTHORITATIVE_LIVE_RELATIVE_AGE", "source_kind": "FIRST_PARTY_DIRECT", "observed_at": "2026-09-15T21:35:00", "posted_age_days": 2})
r = analyze({"pre_surfacing_verification": naive})
check(r["analysis"]["decision"] == "WATCH", "timezone-naive observed_at must WATCH")
print("PASS 21: timezone-naive verification provenance fails closed.")

# 22. Blank identity cannot validate even at the helper boundary.
blank_job = copy.deepcopy(BASE)
blank_job["company"] = "   "
blank_job["role"] = ""
blank_packet = packet(observed_company="   ", observed_role="")
blank_job["pre_surfacing_verification"] = blank_packet
helper_eval = evaluate_pre_surfacing_verification(job_input=blank_job)
check(helper_eval["valid"] is False, "blank company/role identity must fail verification helper")
print("PASS 22: blank company/role identity fails at the verification boundary.")

# 23. Malformed resolved_conflicts shape fails closed symmetrically.
malformed_resolved = packet(resolved_conflicts=None)
r = analyze({"pre_surfacing_verification": malformed_resolved})
check(r["analysis"]["decision"] == "WATCH", "non-list resolved_conflicts must WATCH")
check(any("VERIFICATION_PACKET_MALFORMED: resolved_conflicts" in w for w in r["analysis"]["warnings"]), "malformed resolved_conflicts must surface explicit diagnostic")
print("PASS 23: malformed resolved_conflicts fails closed.")

print("ALL JIT_PRE_SURFACING_VERIFICATION_GATE_V1 CHECKS PASSED")
