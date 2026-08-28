"""Regression tests for Claim Actor Attribution Policy v1.

Authoritative policy: docs/decisions/ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
CLAIMS_ROOT = ROOT / "claims" / "marketmind"
EVIDENCE_ROOT = ROOT / "evidence" / "marketmind"
ADR_PATH = ROOT / "docs" / "decisions" / "ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_validation import validate_claim  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402


MARKETMIND_CLAIM_IDS = [
    "CLAIM_MM_001",
    "CLAIM_MM_002",
    "CLAIM_MM_003",
    "CLAIM_MM_004",
    "CLAIM_MM_005",
]

SUBSTANTIVE_EVIDENCE_BY_CLAIM = {
    "CLAIM_MM_001": ["MM_SCOPE_001", "MM_BOUNDARY_001"],
    "CLAIM_MM_002": ["MM_SCORE_001", "MM_LLM_001"],
    "CLAIM_MM_003": ["MM_PLACES_001", "MM_CENSUS_001"],
    "CLAIM_MM_004": ["MM_GEOFENCE_001", "MM_RATELIMIT_001", "MM_FALLBACK_001"],
    "CLAIM_MM_005": ["MM_TEST_001"],
}

EXPECTED_STATE_BY_CLAIM = {
    "CLAIM_MM_001": "VERIFIED",
    "CLAIM_MM_002": "VERIFIED",
    "CLAIM_MM_003": "VERIFIED",
    "CLAIM_MM_004": "VERIFIED",
    "CLAIM_MM_005": "OBSERVED",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def has_code(items: list, code: str) -> bool:
    return any(item.get("code") == code for item in items)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_evidence(evidence_id: str, evidence_state: str = "VERIFIED") -> dict:
    return {
        "evidence_id": evidence_id,
        "experience_id": "EXP_TEST_001",
        "fact": f"Synthetic fact for {evidence_id}.",
        "capabilities": ["data analysis"],
        "technologies": ["SQL"],
        "evidence_state": evidence_state,
        "original_source": f"synthetic-fixture://evidence/{evidence_id}",
        "source_location": "tests/claim_actor_attribution_policy_test.py",
        "safe_for_external_use": False,
        "notes": None,
    }


def make_active_voice_claim(
    claim_id: str,
    evidence_ids: list[str],
    evidence_state: str,
    *,
    human_approval: bool,
) -> dict:
    return {
        "claim_id": claim_id,
        "wording": "Implemented a synthetic integration for policy regression testing.",
        "evidence_ids": evidence_ids,
        "evidence_state": evidence_state,
        "allowed_contexts": ["resume"],
        "forbidden_contexts": [],
        "human_approval": human_approval,
        "date": "2026-08-28",
        "version": "1",
    }


# ---------------------------------------------------------------------------
# 1. Governance artifact exists with required invariants
# ---------------------------------------------------------------------------
assert_true(ADR_PATH.is_file(), "ADR-CLAIM-ACTOR-ATTRIBUTION-POLICY-V1.md missing")
adr_text = ADR_PATH.read_text(encoding="utf-8")
for phrase in [
    "Substantive truth",
    "Actor attribution",
    "Human approval can never substitute for substantive Evidence",
    "does **not** establish sole intellectual authorship",
]:
    assert_true(phrase in adr_text, f"ADR missing required phrase: {phrase}")
print("PASS 1: ADR documents claim actor attribution policy.")


# ---------------------------------------------------------------------------
# 2. MarketMind remediation: substantive lineage and states
# ---------------------------------------------------------------------------
exp_result = validate_experience_repository(ROOT / "experiences")
assert_true(exp_result["valid"] is True, "experience repository invalid")
ev_result = validate_evidence_repository(ROOT / "evidence", experience_root=ROOT / "experiences")
assert_true(ev_result["valid"] is True, "evidence repository invalid")
evidence_index = ev_result["index"]

mm_author_hash = sha256_file(EVIDENCE_ROOT / "MM_AUTHOR_001.json")

for claim_id in MARKETMIND_CLAIM_IDS:
    claim = json.loads((CLAIMS_ROOT / f"{claim_id}.json").read_text(encoding="utf-8"))
    expected_ids = SUBSTANTIVE_EVIDENCE_BY_CLAIM[claim_id]
    assert_true(
        claim["evidence_ids"] == expected_ids,
        f"{claim_id} substantive lineage mismatch",
    )
    assert_true(
        "MM_AUTHOR_001" not in claim["evidence_ids"],
        f"{claim_id} must not cite MM_AUTHOR_001",
    )
    assert_true(
        claim["evidence_state"] == EXPECTED_STATE_BY_CLAIM[claim_id],
        f"{claim_id} state must be {EXPECTED_STATE_BY_CLAIM[claim_id]}",
    )
    assert_true(claim["human_approval"] is False, f"{claim_id} must remain unapproved")
    result = validate_claim(claim, evidence_index)
    assert_true(result["valid_record"] is True, f"{claim_id} must validate: {result}")
    assert_true(result["reusable"] is False, f"{claim_id} must not be reusable")

assert_true(
    sha256_file(EVIDENCE_ROOT / "MM_AUTHOR_001.json") == mm_author_hash,
    "MM_AUTHOR_001 must remain byte-unchanged",
)
print("PASS 2: MarketMind claims restored to substantive lineage and states.")


# ---------------------------------------------------------------------------
# 3. Human-approval firewall (synthetic fixtures; no real MarketMind approval)
# ---------------------------------------------------------------------------
supported_index = {
    "EVID_V1": make_evidence("EVID_V1", "VERIFIED"),
}

unapproved = validate_claim(
    make_active_voice_claim(
        "CLAIM_SYN_UNAPPROVED",
        ["EVID_V1"],
        "VERIFIED",
        human_approval=False,
    ),
    supported_index,
)
assert_true(unapproved["valid_record"] is True, "supported unapproved must be valid_record")
assert_false(unapproved["reusable"], "supported unapproved must not be reusable")
assert_true(has_code(unapproved["warnings"], "NOT_HUMAN_APPROVED"), "expected NOT_HUMAN_APPROVED")

approved = validate_claim(
    make_active_voice_claim(
        "CLAIM_SYN_APPROVED",
        ["EVID_V1"],
        "VERIFIED",
        human_approval=True,
    ),
    supported_index,
)
assert_true(approved["valid_record"] is True, "supported approved must be valid_record")
assert_true(approved["reusable"] is True, "supported approved must be reusable")
assert_true(approved["human_approved"] is True, "human_approved must be true")

invalid_with_approval = validate_claim(
    make_active_voice_claim(
        "CLAIM_SYN_INVALID_APPROVED",
        ["EVID_MISSING"],
        "VERIFIED",
        human_approval=True,
    ),
    supported_index,
)
assert_false(
    invalid_with_approval["valid_record"],
    "human approval must not rescue invalid lineage",
)
assert_false(
    invalid_with_approval["reusable"],
    "human approval must not make invalid claim reusable",
)
assert_true(
    has_code(invalid_with_approval["errors"], "MISSING_EVIDENCE_ID"),
    "expected MISSING_EVIDENCE_ID despite human_approval",
)

state_mismatch_with_approval = validate_claim(
    make_active_voice_claim(
        "CLAIM_SYN_STATE_MISMATCH",
        ["EVID_O1"],
        "VERIFIED",
        human_approval=True,
    ),
    {"EVID_O1": make_evidence("EVID_O1", "OBSERVED")},
)
assert_false(
    state_mismatch_with_approval["valid_record"],
    "human approval must not rescue INCOMPATIBLE_EVIDENCE_STATE",
)
assert_false(state_mismatch_with_approval["reusable"], "state mismatch must not be reusable")
assert_true(
    has_code(state_mismatch_with_approval["errors"], "INCOMPATIBLE_EVIDENCE_STATE"),
    "expected INCOMPATIBLE_EVIDENCE_STATE despite human_approval",
)

print("PASS 3: human approval gates actor attribution after substantive validity.")


# ---------------------------------------------------------------------------
# 4. Semantic guard blocks sole/exclusive/unaided-authorship overreach even
#    with valid substantive Evidence and human_approval=true (P-1 remediation)
# ---------------------------------------------------------------------------
FORBIDDEN_ATTRIBUTION_WORDINGS = [
    ("case1_sole_architected", "Solely architected and built the system."),
    ("case2_single_handed", "Single-handedly developed the platform."),
    ("case3_entire_alone", "Built the entire application alone."),
    ("case4_without_ai", "Built the application without any AI assistance."),
    ("case5_all_code_no_ai", "Wrote all code without AI."),
    ("case6_exclusive", "Exclusively implemented the integration."),
    ("case7_no_collaborators", "Built the system with no collaborators."),
    (
        "case8_claude_regression",
        "Solely architected and independently built the entire MarketMind "
        "platform without any AI assistance, integrating Google Places and "
        "Census ACS data feeds.",
    ),
]

for label, wording in FORBIDDEN_ATTRIBUTION_WORDINGS:
    result = validate_claim(
        make_active_voice_claim(
            f"CLAIM_SYN_{label.upper()}",
            ["EVID_V1"],
            "VERIFIED",
            human_approval=True,
        )
        | {"wording": wording},
        supported_index,
    )
    assert_false(
        result["valid_record"],
        f"{label}: sole/exclusive/unaided wording must fail valid_record: {wording!r}",
    )
    assert_false(
        result["reusable"],
        f"{label}: sole/exclusive/unaided wording must not be reusable: {wording!r}",
    )
    assert_true(
        has_code(result["errors"], "FORBIDDEN_SEMANTIC_PATTERN"),
        f"{label}: expected FORBIDDEN_SEMANTIC_PATTERN for {wording!r}",
    )

print("PASS 4: semantic guard blocks all sole/exclusive/unaided-authorship cases.")


# ---------------------------------------------------------------------------
# 5. Safe non-matches: ordinary conventional active-voice wording still
#    validates and remains reusable after human approval.
# ---------------------------------------------------------------------------
SAFE_ATTRIBUTION_WORDINGS = [
    ("safe1", "Built a Python/Streamlit market-screening prototype."),
    ("safe2", "Integrated Google Places and Census ACS data feeds."),
    ("safe3", "Implemented bounded operational controls."),
    ("safe4", "Independently verified the integration behavior."),
    ("safe5", "Independent validation confirmed the expected output."),
    (
        "safe6",
        "Implemented a deterministic scoring layer independently of the "
        "LLM narrative layer.",
    ),
]

for label, wording in SAFE_ATTRIBUTION_WORDINGS:
    result = validate_claim(
        make_active_voice_claim(
            f"CLAIM_SYN_{label.upper()}",
            ["EVID_V1"],
            "VERIFIED",
            human_approval=True,
        )
        | {"wording": wording},
        supported_index,
    )
    assert_true(
        result["valid_record"] is True,
        f"{label}: conventional wording must remain valid_record: {wording!r}",
    )
    assert_true(
        result["reusable"] is True,
        f"{label}: conventional wording must remain reusable: {wording!r}",
    )

print("PASS 5: conventional active-voice wording remains unaffected by the new guard.")


print("PASS: claim actor attribution policy tests completed successfully.")
