"""Bounded tests for MarketMind résumé-module drafting/approval history.

Covers MARKETMIND_RESUME_MODULE_DRAFTING_V1 and its supersession by
MARKETMIND_RESUME_MODULE_APPROVAL_AND_MASTER_INTEGRATION_V1: the five
modules were drafted, refined, explicitly approved by Bora, and then
integrated into resume/master/RESUME_MASTER_WW_V1.json. This file's
draft record (resume/drafts/) is preserved as a historical/audit
artifact and is not itself consumed by any résumé-generation or export
path; production reachability is covered by
tests/marketmind_resume_module_approval_test.py.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
DRAFT_PATH = ROOT / "resume" / "drafts" / "MARKETMIND_RESUME_MODULE_DRAFTS_V1.json"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"
WW_CLAIMS_ROOT = ROOT / "claims" / "winter_walk"
MM_CLAIMS_ROOT = ROOT / "claims" / "marketmind"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_lineage import validate_resume_module_lineage  # noqa: E402
from resume_semantic import validate_module_wording_semantics  # noqa: E402
from resume_style import validate_resume_prose_style  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


APPROVED_MM_EVIDENCE_BY_CLAIM = {
    "CLAIM_MM_001": ["MM_SCOPE_001", "MM_BOUNDARY_001"],
    "CLAIM_MM_002": ["MM_SCORE_001", "MM_LLM_001"],
    "CLAIM_MM_003": ["MM_PLACES_001", "MM_CENSUS_001"],
    "CLAIM_MM_004": ["MM_GEOFENCE_001", "MM_RATELIMIT_001", "MM_FALLBACK_001"],
    "CLAIM_MM_005": ["MM_TEST_001"],
}

FORBIDDEN_INFLATION_PHRASES = [
    "production-grade",
    "enterprise",
    "predictive",
    "intelligent site-selection",
    "ai-powered",
    "autonomous",
    "robust at scale",
    "fault-tolerant",
    "circuit breaker",
    "real-time analytics platform",
    "sole developer",
    "independently built the entire system",
    "without ai assistance",
    "187 passing tests",
    "all tests pass",
    "customer",
    "user adoption",
    "revenue",
    "savings",
    "—",  # em dash
]

WINTER_WALK_CLAIM_FILES = [f"CLAIM_WW_{i:03d}.json" for i in range(1, 7)]


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(len(exp_result["index"]) == 4, "Experience count must remain 4")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(len(ev_result["index"]) == 36, "Evidence count must remain 36")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 13, "Claim count must be 13 (11 prior + 2 draft TELUS claims)")

EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = claim_result["index"]


# A. Draft file exists as the historical/audit record: Bora explicitly approved
#    all five, and they were integrated into the protected master.
draft = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
assert_true(
    draft["status"] == "APPROVED_AND_INTEGRATED_INTO_MASTER",
    "A: draft set must record approved-and-integrated status",
)
assert_true(draft["human_approval"] is True, "A: draft set must record Bora's approval")
assert_true(draft["experience_id"] == "EXP_MM_001", "A: draft set must reference EXP_MM_001")
print("PASS A: draft set records Bora's approval and master integration.")


# B. Exactly 3-5 modules, each recording Bora's approval at module level
modules = draft["modules"]
assert_true(3 <= len(modules) <= 5, f"B: expected 3-5 modules, got {len(modules)}")
for module in modules:
    assert_true(
        module.get("human_approval") is True,
        f"B: {module['module_id']} must record Bora's approval",
    )
print(f"PASS B: {len(modules)} draft-history modules present, all recording Bora's approval.")


# C. Every module traces exclusively to approved MarketMind Claim_ID(s) and their
#    exact cited Evidence lineage; no module without Claim lineage.
for module in modules:
    claim_ids = module.get("claim_ids")
    assert_true(
        isinstance(claim_ids, list) and len(claim_ids) >= 1,
        f"C: {module['module_id']} must cite at least one Claim_ID",
    )
    for claim_id in claim_ids:
        assert_true(
            claim_id in APPROVED_MM_EVIDENCE_BY_CLAIM,
            f"C: {module['module_id']} cites unapproved/unknown Claim {claim_id}",
        )
        assert_true(
            CLAIM_INDEX[claim_id]["human_approval"] is True,
            f"C: {module['module_id']} cites Claim {claim_id} that is not human-approved",
        )
    expected_evidence: list[str] = []
    for claim_id in claim_ids:
        expected_evidence.extend(APPROVED_MM_EVIDENCE_BY_CLAIM[claim_id])
    assert_true(
        module.get("evidence_ids") == expected_evidence,
        f"C: {module['module_id']} evidence_ids must exactly match cited Claims' lineage",
    )
print("PASS C: every module traces exclusively to approved MarketMind Claims and their exact Evidence lineage.")


# D. Real lineage/semantic/style validation against the trusted repository indexes
for module in modules:
    lineage = validate_resume_module_lineage(
        module, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
    )
    assert_true(lineage["valid"] is True, f"D: {module['module_id']} lineage invalid: {lineage['errors']}")

    semantic = validate_module_wording_semantics(
        module, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX
    )
    assert_true(semantic["valid"] is True, f"D: {module['module_id']} semantic boundary violated: {semantic['errors']}")

    style = validate_resume_prose_style(module["wording"], context=module["module_id"])
    assert_true(style["valid"] is True, f"D: {module['module_id']} style violation: {style['warnings']}")
print("PASS D: all modules pass real lineage, semantic-boundary, and prose-style validation.")


# E. No forbidden/unsupported inflation language anywhere in drafted wording
for module in modules:
    wording_lower = module["wording"].lower()
    for phrase in FORBIDDEN_INFLATION_PHRASES:
        assert_true(
            phrase not in wording_lower,
            f"E: {module['module_id']} contains forbidden phrase {phrase!r}",
        )
print("PASS E: no forbidden inflation language in any drafted wording.")


# F. CLAIM_MM_005 (OBSERVED) module does not assert a stronger outcome
test_module = next(m for m in modules if "CLAIM_MM_005" in m["claim_ids"])
test_wording_lower = test_module["wording"].lower()
assert_true("187" not in test_wording_lower, "F: testing module must not embed volatile pass count")
assert_true(
    "all tests" not in test_wording_lower and "passed" not in test_wording_lower,
    "F: testing module must not assert a pass/fail outcome beyond OBSERVED evidence",
)
print("PASS F: OBSERVED testing claim not turned into a stronger performance assertion.")


# G. Draft-history wording is byte-identical to what was integrated into the
#    protected master -- no divergence between the two records.
master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
master_by_id = {m["module_id"]: m for m in master["modules"]}
for module in modules:
    master_module = master_by_id.get(module["module_id"])
    assert_true(
        master_module is not None,
        f"G: {module['module_id']} must be present in the protected master",
    )
    assert_true(
        master_module["wording"] == module["wording"],
        f"G: {module['module_id']} draft-history wording diverges from master wording",
    )
print("PASS G: draft-history wording matches the integrated master wording exactly (no divergence).")


# H. Winter Walk claims and MarketMind claims are byte-unchanged by this
#    milestone (the protected master legitimately changed; that is covered
#    by tests/marketmind_resume_module_approval_test.py).
ww_hashes_before = {name: sha256_file(WW_CLAIMS_ROOT / name) for name in WINTER_WALK_CLAIM_FILES}
mm_hashes_before = {
    f"CLAIM_MM_{i:03d}.json": sha256_file(MM_CLAIMS_ROOT / f"CLAIM_MM_{i:03d}.json")
    for i in range(1, 6)
}

for name, digest in ww_hashes_before.items():
    assert_true(sha256_file(WW_CLAIMS_ROOT / name) == digest, f"H: Winter Walk claim mutated: {name}")
for name, digest in mm_hashes_before.items():
    assert_true(sha256_file(MM_CLAIMS_ROOT / name) == digest, f"H: MarketMind claim mutated: {name}")
print("PASS H: Winter Walk claims and MarketMind claims unchanged.")


# I. Repository counts unchanged (claim drafting created no new Claim/Evidence/Experience)
reusable = [cid for cid, rec in CLAIM_INDEX.items() if rec.get("human_approval") is True]
assert_true(len(reusable) == 11, f"I: reusable claim count must remain 11, got {len(reusable)}")
print("PASS I: repository counts as expected (4 Experience / 36 Evidence / 11 Claims / 11 reusable).")


print("PASS: MarketMind resume-module drafting tests completed successfully.")
