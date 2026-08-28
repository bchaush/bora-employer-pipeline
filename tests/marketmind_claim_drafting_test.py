"""Bounded tests for MarketMind claim drafting v1 milestone."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
CLAIMS_ROOT = ROOT / "claims" / "marketmind"
WW_CLAIMS_ROOT = ROOT / "claims" / "winter_walk"
EVIDENCE_ROOT = ROOT / "evidence"
EXPERIENCE_ROOT = ROOT / "experiences"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from claim_validation import validate_claim  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


MARKETMIND_CLAIM_IDS = [
    "CLAIM_MM_001",
    "CLAIM_MM_002",
    "CLAIM_MM_003",
    "CLAIM_MM_004",
    "CLAIM_MM_005",
]

APPROVED_MARKETMIND_EVIDENCE_IDS = [
    "MM_SCOPE_001",
    "MM_SCORE_001",
    "MM_LLM_001",
    "MM_PLACES_001",
    "MM_CENSUS_001",
    "MM_GEOFENCE_001",
    "MM_RATELIMIT_001",
    "MM_FALLBACK_001",
    "MM_TEST_001",
    "MM_DEPLOY_001",
    "MM_BOUNDARY_001",
    "MM_AUTHOR_001",
]

WINTER_WALK_CLAIM_FILES = [
    "CLAIM_WW_001.json",
    "CLAIM_WW_002.json",
    "CLAIM_WW_003.json",
    "CLAIM_WW_004.json",
    "CLAIM_WW_005.json",
    "CLAIM_WW_006.json",
]

PRIOR_EVIDENCE_IDS_BY_CLAIM = {
    "CLAIM_MM_001": ["MM_SCOPE_001", "MM_BOUNDARY_001"],
    "CLAIM_MM_002": ["MM_SCORE_001", "MM_LLM_001"],
    "CLAIM_MM_003": ["MM_PLACES_001", "MM_CENSUS_001"],
    "CLAIM_MM_004": ["MM_GEOFENCE_001", "MM_RATELIMIT_001", "MM_FALLBACK_001"],
    "CLAIM_MM_005": ["MM_TEST_001"],
}

MM_AUTHOR_EVIDENCE_PATH = EVIDENCE_ROOT / "marketmind" / "MM_AUTHOR_001.json"

FORBIDDEN_INFLATION_PHRASES = [
    "production platform",
    "production deployment",
    "enterprise-grade",
    "enterprise analytics",
    "all tests pass",
    "187 passing",
    "are validated predictors",
    "customer adoption",
    "solely built",
    "sole author",
    "classical circuit breaker",
    "predictive machine learning model",
    "ai-powered",
    "cutting-edge",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


claim_validator = build_draft202012_validator(ROOT / "schemas" / "claim.schema.json")

exp_result = validate_experience_repository(EXPERIENCE_ROOT)
assert_true(exp_result["valid"] is True, "experience repository invalid")
ev_result = validate_evidence_repository(EVIDENCE_ROOT, experience_root=EXPERIENCE_ROOT)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
evidence_index = ev_result["index"]


# ---------------------------------------------------------------------------
# 1. Every MarketMind claim validates as valid_record but not reusable
# ---------------------------------------------------------------------------
for claim_id in MARKETMIND_CLAIM_IDS:
    path = CLAIMS_ROOT / f"{claim_id}.json"
    assert_true(path.is_file(), f"missing claim file: {path}")
    claim = json.loads(path.read_text(encoding="utf-8"))
    assert_true(
        list(claim_validator.iter_errors(claim)) == [],
        f"{claim_id} failed claim schema",
    )
    assert_true(claim["human_approval"] is False, f"{claim_id} must not be approved")
    result = validate_claim(claim, evidence_index)
    assert_true(result["valid_record"] is True, f"{claim_id} must be valid_record: {result}")
    assert_true(result["reusable"] is False, f"{claim_id} must not be reusable")
    assert_true(
        any(w.get("code") == "NOT_HUMAN_APPROVED" for w in result["warnings"]),
        f"{claim_id} must warn NOT_HUMAN_APPROVED",
    )
    wording = claim["wording"].lower()
    for phrase in FORBIDDEN_INFLATION_PHRASES:
        assert_true(
            phrase not in wording,
            f"{claim_id} contains forbidden inflation phrase: {phrase}",
        )

print("PASS 1: MarketMind claims are valid_record, not reusable, not inflated.")


# ---------------------------------------------------------------------------
# 2. Lineage: only approved MarketMind evidence IDs cited; all cite EXP_MM_001 evidence
# ---------------------------------------------------------------------------
for claim_id in MARKETMIND_CLAIM_IDS:
    claim = json.loads((CLAIMS_ROOT / f"{claim_id}.json").read_text(encoding="utf-8"))
    for evidence_id in claim["evidence_ids"]:
        assert_true(
            evidence_id in APPROVED_MARKETMIND_EVIDENCE_IDS,
            f"{claim_id} cites unsupported evidence {evidence_id}",
        )
        record = evidence_index[evidence_id]
        assert_true(
            record["experience_id"] == "EXP_MM_001",
            f"{evidence_id} must belong to EXP_MM_001",
        )

print("PASS 2: lineage references approved MarketMind evidence for EXP_MM_001.")


# ---------------------------------------------------------------------------
# 2b. Claim actor attribution policy: substantive lineage only; no MM_AUTHOR_001
# ---------------------------------------------------------------------------
EXPECTED_EVIDENCE_STATE_BY_CLAIM = {
    "CLAIM_MM_001": "VERIFIED",
    "CLAIM_MM_002": "VERIFIED",
    "CLAIM_MM_003": "VERIFIED",
    "CLAIM_MM_004": "VERIFIED",
    "CLAIM_MM_005": "OBSERVED",
}

author_evidence_hash = sha256_file(MM_AUTHOR_EVIDENCE_PATH)
author_evidence = json.loads(MM_AUTHOR_EVIDENCE_PATH.read_text(encoding="utf-8"))
assert_true(author_evidence["evidence_state"] == "OBSERVED", "MM_AUTHOR_001 must remain OBSERVED")
assert_true(
    "Does not prove sole intellectual authorship of every idea" in " ".join(
        author_evidence.get("limitations", [])
    ),
    "MM_AUTHOR_001 limitations must remain unchanged",
)

for claim_id in MARKETMIND_CLAIM_IDS:
    claim = json.loads((CLAIMS_ROOT / f"{claim_id}.json").read_text(encoding="utf-8"))
    prior_ids = PRIOR_EVIDENCE_IDS_BY_CLAIM[claim_id]
    assert_true(
        claim["evidence_ids"] == prior_ids,
        f"{claim_id} must cite substantive evidence only: {claim['evidence_ids']}",
    )
    assert_true(
        "MM_AUTHOR_001" not in claim["evidence_ids"],
        f"{claim_id} must not cite MM_AUTHOR_001 in substantive lineage",
    )
    assert_true(
        claim["evidence_state"] == EXPECTED_EVIDENCE_STATE_BY_CLAIM[claim_id],
        f"{claim_id} evidence_state must be {EXPECTED_EVIDENCE_STATE_BY_CLAIM[claim_id]}",
    )

assert_true(
    sha256_file(MM_AUTHOR_EVIDENCE_PATH) == author_evidence_hash,
    "MM_AUTHOR_001 evidence record must remain byte-unchanged",
)
print("PASS 2b: substantive lineage restored; MM_AUTHOR_001 excluded from claims.")


# ---------------------------------------------------------------------------
# 3. Test-state claim omits volatile exact pass counts
# ---------------------------------------------------------------------------
test_claim = json.loads((CLAIMS_ROOT / "CLAIM_MM_005.json").read_text(encoding="utf-8"))
assert_true("187" not in test_claim["wording"], "CLAIM_MM_005 must not embed 187 count")
assert_true(
    "all tests" not in test_claim["wording"].lower(),
    "CLAIM_MM_005 must not claim all tests passed",
)
assert_true(test_claim["evidence_state"] == "OBSERVED", "CLAIM_MM_005 must use OBSERVED state")
print("PASS 3: test claim avoids volatile exact-count wording.")


# ---------------------------------------------------------------------------
# 4. Repository integrity
# ---------------------------------------------------------------------------
claim_result = validate_claim_repository(ROOT / "claims")
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 11, "expected 11 total claim records")
reusable = [
    cid for cid, rec in claim_result["index"].items() if rec.get("human_approval") is True
]
assert_true(len(reusable) == 6, f"reusable claim count must remain 6, got {len(reusable)}")
assert_true(
    sorted(reusable) == sorted([f"CLAIM_WW_{i:03d}" for i in range(1, 7)]),
    f"unexpected reusable claim set: {reusable}",
)
for claim_id in MARKETMIND_CLAIM_IDS:
    assert_true(
        claim_result["index"][claim_id]["human_approval"] is False,
        f"{claim_id} must remain unapproved",
    )

print("PASS 4: 11 total claims; 6 reusable (Winter Walk only).")


# ---------------------------------------------------------------------------
# 5. Winter Walk claims, evidence, experience, master unchanged
# ---------------------------------------------------------------------------
ww_hashes = {name: sha256_file(WW_CLAIMS_ROOT / name) for name in WINTER_WALK_CLAIM_FILES}
ww_exp_hash = sha256_file(EXPERIENCE_ROOT / "EXP_WW_001.json")
master_hash = sha256_file(MASTER_PATH)

for name, digest in ww_hashes.items():
    assert_true(
        sha256_file(WW_CLAIMS_ROOT / name) == digest,
        f"Winter Walk claim mutated: {name}",
    )
assert_true(
    sha256_file(EXPERIENCE_ROOT / "EXP_WW_001.json") == ww_exp_hash,
    "Winter Walk experience mutated",
)
assert_true(sha256_file(MASTER_PATH) == master_hash, "protected master mutated")

print("PASS 5: Winter Walk claims, WW experience, and master unchanged.")


print("PASS: MarketMind claim drafting tests completed successfully.")
