"""Bounded tests for MarketMind evidence extraction v1 milestone."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
EXPERIENCE_PATH = ROOT / "experiences" / "EXP_MM_001.json"
EVIDENCE_ROOT = ROOT / "evidence" / "marketmind"
WW_EVIDENCE_ROOT = ROOT / "evidence" / "winter_walk"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


MARKETMIND_EVIDENCE_IDS = [
    "MM_AUTHOR_001",
    "MM_BOUNDARY_001",
    "MM_CENSUS_001",
    "MM_DEPLOY_001",
    "MM_FALLBACK_001",
    "MM_GEOFENCE_001",
    "MM_LLM_001",
    "MM_PLACES_001",
    "MM_RATELIMIT_001",
    "MM_SCOPE_001",
    "MM_SCORE_001",
    "MM_TEST_001",
]

WINTER_WALK_EVIDENCE_FILES = [
    "WW_ADOPT_001.json",
    "WW_ARCH_001.json",
    "WW_ARCH_002.json",
    "WW_CONN_001.json",
    "WW_CTRL_001.json",
    "WW_CTRL_002.json",
    "WW_DATA_001.json",
    "WW_DATA_002.json",
    "WW_FUQ_001.json",
    "WW_MAP_001.json",
    "WW_OFFER_001.json",
    "WW_PROC_001.json",
    "WW_SYNC_001.json",
    "WW_TEST_001.json",
]

LEGAL_EVIDENCE_STATES = {"VERIFIED", "SUPPORTED", "OBSERVED", "UNKNOWN", "CONTRADICTED"}

FORBIDDEN_INFLATION_PHRASES = [
    "production platform",
    "enterprise analytics",
    "all tests pass",
    "187 passing",
    "validated predictor of business success",
    "customer usage",
    "revenue",
    "classical circuit-breaker",
    "cloud-provider quota",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


experience_validator = build_draft202012_validator(ROOT / "schemas" / "experience.schema.json")
evidence_validator = build_draft202012_validator(ROOT / "schemas" / "evidence.schema.json")


# ---------------------------------------------------------------------------
# 1. MarketMind Experience record validates
# ---------------------------------------------------------------------------
experience = json.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))
assert_true(
    list(experience_validator.iter_errors(experience)) == [],
    "EXP_MM_001 must pass experience schema",
)
assert_true(experience["experience_id"] == "EXP_MM_001", "experience_id mismatch")
assert_true(
    experience["experience_type"] == "PERSONAL_PROJECT",
    "experience_type must remain PERSONAL_PROJECT without sponsor evidence",
)
print("PASS 1: MarketMind Experience record validates.")


# ---------------------------------------------------------------------------
# 2-7. MarketMind Evidence records
# ---------------------------------------------------------------------------
records: dict[str, dict] = {}
for evidence_id in MARKETMIND_EVIDENCE_IDS:
    path = EVIDENCE_ROOT / f"{evidence_id}.json"
    assert_true(path.is_file(), f"missing evidence file: {path}")
    record = json.loads(path.read_text(encoding="utf-8"))
    assert_true(
        list(evidence_validator.iter_errors(record)) == [],
        f"{evidence_id} failed evidence schema",
    )
    assert_true(record["experience_id"] == "EXP_MM_001", f"{evidence_id} wrong experience_id")
    assert_true(
        record["evidence_state"] in LEGAL_EVIDENCE_STATES,
        f"{evidence_id} illegal evidence_state",
    )
    assert_true(record["original_source"], f"{evidence_id} missing original_source")
    assert_true(record["source_location"], f"{evidence_id} missing source_location")
    fact_lower = record["fact"].lower()
    for phrase in FORBIDDEN_INFLATION_PHRASES:
        assert_true(
            phrase not in fact_lower,
            f"{evidence_id} contains forbidden inflation phrase: {phrase}",
        )
    records[evidence_id] = record

print("PASS 2-7: MarketMind Evidence records validate with legal states and no inflation.")


# ---------------------------------------------------------------------------
# Test-state representation
# ---------------------------------------------------------------------------
test_record = records["MM_TEST_001"]
assert_true("186 passed" in test_record["fact"], "MM_TEST_001 must record 186 passed")
assert_true("1 failed" in test_record["fact"], "MM_TEST_001 must record 1 failed")
assert_true("187 tests collected" in test_record["fact"], "MM_TEST_001 must record 187 collected")
assert_true(
    "test_assemble_top_level_keys_match_mock_contract" in test_record["fact"],
    "MM_TEST_001 must name failing test",
)
assert_true("all tests pass" not in test_record["fact"].lower(), "MM_TEST_001 must not claim all pass")
print("PASS 8: test-state accurately represented as 186 passed / 1 failed.")


# ---------------------------------------------------------------------------
# Fallback wording — not classical circuit breaker
# ---------------------------------------------------------------------------
fallback = records["MM_FALLBACK_001"]
assert_true("retry" in fallback["fact"].lower(), "MM_FALLBACK_001 must describe retry")
assert_true("degraded stub" in fallback["fact"].lower(), "MM_FALLBACK_001 must describe degraded stub")
assert_true(
    "not a classical" in fallback["fact"].lower(),
    "MM_FALLBACK_001 must negate classical circuit-breaker claim",
)
print("PASS 9: fallback evidence uses retry + degraded stub truth.")


# ---------------------------------------------------------------------------
# Repository integrity
# ---------------------------------------------------------------------------
exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(exp_result["records_checked"] == 7, "expected 7 experience records")
assert_true(
    sorted(exp_result["index"].keys()) == [
        "EXP_BULMARMA_001",
        "EXP_DCOMMERCE_001",
        "EXP_EDU_BRANDEIS_001",
        "EXP_EDU_UNWE_001",
        "EXP_MM_001",
        "EXP_TELUS_001",
        "EXP_WW_001",
    ],
    "unexpected experience index",
)

ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(ev_result["records_checked"] == 43, "expected 43 evidence records")
for evidence_id in MARKETMIND_EVIDENCE_IDS:
    assert_true(evidence_id in ev_result["index"], f"{evidence_id} missing from trusted index")

claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 16, "claim repository must have 16 records")
reusable_claims = [cid for cid, rec in claim_result["index"].items() if rec.get("human_approval") is True]
assert_true(len(reusable_claims) == 13, "reusable claim count must be 13 (6 Winter Walk + 5 Bora-approved MarketMind + 2 Bora-approved TELUS)")

print("PASS 10: repository integrity — 4 Experience, 36 Evidence, 6 Claims.")


# ---------------------------------------------------------------------------
# Winter Walk + master unchanged
# ---------------------------------------------------------------------------
ww_hashes_before = {}
for name in WINTER_WALK_EVIDENCE_FILES:
    path = WW_EVIDENCE_ROOT / name
    ww_hashes_before[name] = sha256_file(path)

ww_experience_path = ROOT / "experiences" / "EXP_WW_001.json"
ww_experience_hash = sha256_file(ww_experience_path)
master_hash = sha256_file(MASTER_PATH)

for name, digest in ww_hashes_before.items():
    assert_true(
        sha256_file(WW_EVIDENCE_ROOT / name) == digest,
        f"Winter Walk evidence mutated: {name}",
    )
assert_true(
    sha256_file(ww_experience_path) == ww_experience_hash,
    "Winter Walk experience record mutated",
)
assert_true(sha256_file(MASTER_PATH) == master_hash, "protected master mutated")

print("PASS 11: Winter Walk Experience/Evidence and protected master unchanged.")


print("PASS: MarketMind evidence extraction tests completed successfully.")
