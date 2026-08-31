"""Regression tests for COMPOUND_REQUIREMENT_SEMANTICS_V1.

Frozen Atominvest's REQ_A_ONBOARDING_MIGRATION_UAT ("Work alongside
Implementation Managers to onboard customers onto the platform, supporting
everything from data migration to UAT") previously inferred only
{uat, pilot_testing, test_documentation} -- the onboarding and data-migration
duties were entirely unrepresented, so the existing subset-check saw
req_caps already equal to CLAIM_WW_005's capability set and reported
SUPPORTED, even though CLAIM_WW_005/WW_TEST_001 only ever establish UAT/
pilot-testing documentation for an internal nonprofit operations tool, never
customer-facing platform onboarding or data migration.

Two new, additively-emitted capability tags (customer_platform_onboarding,
data_migration) close this gap through the existing, unmodified
capability-set-completeness (subset-check/PARTIAL) mechanism -- no
Requirement decomposition, no clause arrays, no schema change, no second
EvidenceMatch per Requirement, and no multi-claim composition.

BOUNDED CORRECTION (independent Cursor review, before commit): an earlier
version of the onboarding pattern fired on bare "onboard(ing)
customer(s)/client(s)" with no software/platform context at all, which
over-matched entirely non-software onboarding duties (KYC/compliance,
account opening, wealth-management/consulting/advertising client
onboarding, bare "onboard clients efficiently"). The capability this
milestone actually needs is narrower: onboarding a customer/client *onto a
software platform/system/application/product*, as an implementation duty.
The tag was renamed customer_onboarding -> customer_platform_onboarding to
make that scope explicit, and the pattern now requires an explicit
platform/software/system/application/product object connected via a direct
"onto"/"to" construction, not mere co-occurrence.

Exercises real production code (requirement_match.py, job_analysis.py)
against the actual frozen Atominvest fixture -- no logic is duplicated here.
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
from requirement_match import (  # noqa: E402
    _CLAIM_CAPABILITIES,
    infer_requirement_capabilities,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


FIXTURE_A = ROOT / "fixtures" / "jobs" / "CASE_A_ATOMINVEST_IMPLEMENTATION_ANALYST"


def _load_job_input(fixture_dir: Path) -> dict:
    job = json.loads((fixture_dir / "job.json").read_text(encoding="utf-8"))
    jd_text = (fixture_dir / "jd.txt").read_text(encoding="utf-8")
    structured = json.loads((fixture_dir / "structured_extraction.json").read_text(encoding="utf-8"))
    job_input = dict(job)
    job_input["jd_text"] = jd_text
    job_input["structured_extraction"] = structured
    return job_input


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


# ======================================================================
# A. Frozen Atominvest REQ_A_ONBOARDING_MIGRATION_UAT through the real
#    production analyze_job() path: capability inference now includes
#    customer_platform_onboarding and data_migration in addition to the
#    existing UAT bundle, and the EvidenceMatch becomes PARTIAL, not
#    SUPPORTED. CLAIM_WW_005 remains the cited (partial) provenance.
# ======================================================================
result = analyze_job(_load_job_input(FIXTURE_A))
assert_true(result["valid"] is True, f"Atominvest analysis must be valid: {result['errors']}")
analysis = result["analysis"]
req = next(r for r in analysis["requirements"] if r["requirement_id"] == "REQ_A_ONBOARDING_MIGRATION_UAT")
caps = infer_requirement_capabilities(req)
assert_true(
    caps == frozenset({"customer_platform_onboarding", "data_migration", "uat", "pilot_testing", "test_documentation"}),
    f"REQ_A_ONBOARDING_MIGRATION_UAT must infer all five tags additively; got {sorted(caps)}",
)
match = next(m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_A_ONBOARDING_MIGRATION_UAT")
assert_true(
    match["result"] == "PARTIAL",
    f"REQ_A_ONBOARDING_MIGRATION_UAT must resolve PARTIAL (UAT covered, onboarding/migration not), got {match['result']}",
)
assert_true(
    "customer_platform_onboarding" in match["explanation"] and "data_migration" in match["explanation"],
    "explanation must name both missing capabilities",
)
assert_true(match["claim_ids"] == ["CLAIM_WW_005"], f"must still cite CLAIM_WW_005 as the best-overlap claim, got {match['claim_ids']}")
print("PASS A: frozen Atominvest REQ_A_ONBOARDING_MIGRATION_UAT now infers customer_platform_onboarding + data_migration + UAT bundle additively and resolves PARTIAL, not SUPPORTED.")


# ======================================================================
# B. Software/platform onboarding positives -- the frozen Atominvest
#    wording and close variants requiring an explicit platform/software/
#    system/application/product object.
# ======================================================================
onboarding_positives = (
    "Work alongside Implementation Managers to onboard customers onto the platform, supporting everything from data migration to UAT.",
    "onboard customers onto the platform",
    "onboarding customers onto our platform",
    "onboard clients to the software",
    "customer onboarding onto the system",
)
for text in onboarding_positives:
    onboarding_caps = infer_requirement_capabilities(_req(text))
    assert_true(
        "customer_platform_onboarding" in onboarding_caps,
        f"{text!r} must infer customer_platform_onboarding",
    )
print("PASS B: frozen Atominvest wording and close software/platform-onboarding variants all emit customer_platform_onboarding.")


# ======================================================================
# C. Data-migration-only positive: a narrowly phrased data migration duty
#    emits data_migration. (Pattern unchanged in this correction.)
# ======================================================================
for text in ("data migration", "migrating customer data", "migrate legacy data to the new system"):
    migration_caps = infer_requirement_capabilities(_req(text))
    assert_true(
        "data_migration" in migration_caps,
        f"{text!r} must infer data_migration",
    )
print("PASS C: narrowly phrased data-migration duties emit data_migration.")


# ======================================================================
# D. Combined onboarding + migration + UAT: all three capability groups
#    coexist rather than one replacing another.
# ======================================================================
combined_text = "Onboard customers onto the platform, handle data migration, and support UAT."
combined_caps = infer_requirement_capabilities(_req(combined_text))
assert_true(
    {"customer_platform_onboarding", "data_migration", "uat"}.issubset(combined_caps),
    f"combined onboarding/migration/UAT text must infer all three capability groups; got {sorted(combined_caps)}",
)
print("PASS D: combined onboarding + migration + UAT text infers all three capability groups additively.")


# ======================================================================
# E. Non-software onboarding negatives (Cursor-reproduced overmatch) --
#    the pattern must never fire for onboarding duties with no software/
#    platform object, however customer/client-facing the duty genuinely
#    is (KYC/compliance, account opening, wealth-management, consulting,
#    advertising, generic "onboard clients efficiently"/"onboard new
#    customers"/"customer onboarding process"). These are real,
#    meaningfully different onboarding processes this tag must never
#    represent.
# ======================================================================
non_software_onboarding_negatives = (
    "client onboarding for KYC/compliance",
    "client onboarding documentation at a bank",
    "customer onboarding for account opening",
    "customer onboarding for a nontechnical service",
    "onboarding wealth-management clients",
    "onboarding consulting clients",
    "onboarding advertising clients",
    "onboard clients efficiently",
    "onboard new customers",
    "customer onboarding process",
)
for text in non_software_onboarding_negatives:
    caps_neg = infer_requirement_capabilities(_req(text))
    assert_true(
        "customer_platform_onboarding" not in caps_neg,
        f"{text!r} must NOT trigger customer_platform_onboarding -- no software/platform object is named",
    )
print("PASS E: non-software onboarding duties (KYC/compliance, account opening, wealth-management, consulting, advertising, generic bare onboarding) never trigger customer_platform_onboarding.")


# ======================================================================
# F. Staff-onboarding and non-data-migration negatives -- the new
#    patterns must not fire merely because an unrelated sentence contains
#    "onboard"/"migration" with a different object.
# ======================================================================
staff_onboarding_negatives = (
    "onboard new employees to the team",
    "employee onboarding experience",
    "onboarding process for staff",
    "employee onboarding",
)
for text in staff_onboarding_negatives:
    caps_neg = infer_requirement_capabilities(_req(text))
    assert_true(
        "customer_platform_onboarding" not in caps_neg,
        f"{text!r} must NOT trigger customer_platform_onboarding -- this is staff onboarding, not the customer/platform duty",
    )

migration_negatives = (
    "migrate the application to AWS",
    "system migration to a new server",
    "migrating to a new office",
)
for text in migration_negatives:
    caps_neg = infer_requirement_capabilities(_req(text))
    assert_true(
        "data_migration" not in caps_neg,
        f"{text!r} must NOT trigger data_migration -- no data is named as what is being migrated",
    )
print("PASS F: staff-onboarding and non-data-migration phrasing never trigger the new capability tags.")


# ======================================================================
# G. No existing approved Claim silently gains customer_platform_onboarding
#    or data_migration -- no current evidence establishes either capability.
# ======================================================================
for claim_id, caps_map in _CLAIM_CAPABILITIES.items():
    assert_true(
        "customer_platform_onboarding" not in caps_map,
        f"{claim_id} must not carry customer_platform_onboarding -- no approved evidence establishes it",
    )
    assert_true(
        "data_migration" not in caps_map,
        f"{claim_id} must not carry data_migration -- no approved evidence establishes it",
    )
print("PASS G: no existing Claim capability set carries customer_platform_onboarding or data_migration.")


# ======================================================================
# H. REQ_A_EXCEL_DATA and Atominvest's overall blocker set/lane/decision
#    are unaffected by this milestone -- the PARTIAL result does not
#    create a new hard blocker (Gate 0 fires only on exact NONE).
# ======================================================================
match_excel = next(m for m in analysis["evidence_matches"] if m["requirement_id"] == "REQ_A_EXCEL_DATA")
assert_true(match_excel["result"] == "NONE", f"REQ_A_EXCEL_DATA must remain NONE, unaffected by this milestone; got {match_excel['result']}")
expected_blockers = {
    "REQ_A_CONFIG_IMPLEMENTATION",
    "REQ_A_DEGREE",
    "REQ_A_EXCEL_DATA",
    "REQ_A_QA_TROUBLESHOOTING",
}
actual_blocked_ids = {b.rsplit(": ", 1)[-1] for b in result["hard_blockers"]}
assert_true(
    actual_blocked_ids == expected_blockers,
    f"Atominvest hard blockers must remain exactly {expected_blockers} (PARTIAL never creates a new blocker), got {actual_blocked_ids}",
)
assert_true(
    analysis["lane"] == "LANE_0_REJECT" and analysis["decision"] == "REJECT",
    f"Atominvest overall routing must remain LANE_0_REJECT/REJECT, got {analysis['lane']}/{analysis['decision']}",
)
print("PASS H: REQ_A_EXCEL_DATA is unaffected; Atominvest's hard-blocker set and overall LANE_0_REJECT/REJECT routing are unchanged.")

print("ALL compound_requirement_semantics_v1_test CHECKS PASSED")
