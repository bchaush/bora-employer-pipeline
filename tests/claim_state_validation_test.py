import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_state_validation import (  # noqa: E402
    validate_claim_evidence_state_compatibility,
)


def make_evidence(evidence_id: str, evidence_state: str) -> dict:
    # Synthetic fixture only. Not a real experience or claim.
    return {
        "evidence_id": evidence_id,
        "experience_id": "EXP_TEST_001",
        "fact": f"Synthetic fact for {evidence_id}.",
        "capabilities": ["data analysis"],
        "technologies": ["SQL"],
        "evidence_state": evidence_state,
        "original_source": f"synthetic-fixture://evidence/{evidence_id}",
        "source_location": "tests/claim_state_validation_test.py",
        "safe_for_external_use": False,
        "notes": None,
    }


def make_claim(
    claim_id: str,
    evidence_ids: list,
    evidence_state: str,
    *,
    human_approval: bool = True,
) -> dict:
    # Synthetic fixture only. Not a real approved claim about Bora.
    return {
        "claim_id": claim_id,
        "wording": "Used SQL to analyze structured tables for an internal synthetic report.",
        "evidence_ids": evidence_ids,
        "evidence_state": evidence_state,
        "allowed_contexts": ["resume"],
        "forbidden_contexts": [],
        "human_approval": human_approval,
        "date": "2026-08-26",
        "version": "1",
    }


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def has_code(result: dict, code: str) -> bool:
    return any(error.get("code") == code for error in result["errors"])


# PASS 1: VERIFIED claim + all VERIFIED evidence passes
result_verified_ok = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_001", ["EVID_V1", "EVID_V2"], "VERIFIED"),
    {
        "EVID_V1": make_evidence("EVID_V1", "VERIFIED"),
        "EVID_V2": make_evidence("EVID_V2", "VERIFIED"),
    },
)
assert_true(result_verified_ok["valid"] is True, "VERIFIED+VERIFIED was rejected")
assert_true(result_verified_ok["errors"] == [], "unexpected errors for VERIFIED+VERIFIED")
print("PASS 1: VERIFIED claim + all VERIFIED evidence passed.")


# PASS 2: VERIFIED claim + SUPPORTED evidence fails
result_verified_supported = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_002", ["EVID_S1"], "VERIFIED"),
    {"EVID_S1": make_evidence("EVID_S1", "SUPPORTED")},
)
assert_false(
    result_verified_supported["valid"],
    "VERIFIED claim + SUPPORTED evidence was accepted",
)
assert_true(
    has_code(result_verified_supported, "INCOMPATIBLE_EVIDENCE_STATE"),
    "expected INCOMPATIBLE_EVIDENCE_STATE",
)
print("PASS 2: VERIFIED claim + SUPPORTED evidence failed.")
print(f"  Result: {result_verified_supported}")


# PASS 3: SUPPORTED claim + VERIFIED/SUPPORTED evidence passes
result_supported_ok = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_003", ["EVID_V1", "EVID_S1"], "SUPPORTED"),
    {
        "EVID_V1": make_evidence("EVID_V1", "VERIFIED"),
        "EVID_S1": make_evidence("EVID_S1", "SUPPORTED"),
    },
)
assert_true(
    result_supported_ok["valid"] is True,
    "SUPPORTED + VERIFIED/SUPPORTED was rejected",
)
print("PASS 3: SUPPORTED claim + VERIFIED/SUPPORTED evidence passed.")


# PASS 4: SUPPORTED claim + OBSERVED evidence fails
result_supported_observed = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_004", ["EVID_O1"], "SUPPORTED"),
    {"EVID_O1": make_evidence("EVID_O1", "OBSERVED")},
)
assert_false(
    result_supported_observed["valid"],
    "SUPPORTED claim + OBSERVED evidence was accepted",
)
assert_true(
    has_code(result_supported_observed, "INCOMPATIBLE_EVIDENCE_STATE"),
    "expected INCOMPATIBLE_EVIDENCE_STATE for SUPPORTED+OBSERVED",
)
print("PASS 4: SUPPORTED claim + OBSERVED evidence failed.")
print(f"  Result: {result_supported_observed}")


# PASS 5: OBSERVED claim + OBSERVED evidence passes
result_observed_ok = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_005", ["EVID_O1"], "OBSERVED"),
    {"EVID_O1": make_evidence("EVID_O1", "OBSERVED")},
)
assert_true(result_observed_ok["valid"] is True, "OBSERVED+OBSERVED was rejected")
print("PASS 5: OBSERVED claim + OBSERVED evidence passed.")


# PASS 6: OBSERVED claim + UNKNOWN evidence fails
result_observed_unknown = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_006", ["EVID_U1"], "OBSERVED"),
    {"EVID_U1": make_evidence("EVID_U1", "UNKNOWN")},
)
assert_false(
    result_observed_unknown["valid"],
    "OBSERVED claim + UNKNOWN evidence was accepted",
)
assert_true(
    has_code(result_observed_unknown, "INCOMPATIBLE_EVIDENCE_STATE"),
    "expected INCOMPATIBLE_EVIDENCE_STATE for OBSERVED+UNKNOWN",
)
print("PASS 6: OBSERVED claim + UNKNOWN evidence failed.")
print(f"  Result: {result_observed_unknown}")


# PASS 7: UNKNOWN claim + UNKNOWN evidence passes
result_unknown_ok = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_007", ["EVID_U1"], "UNKNOWN"),
    {"EVID_U1": make_evidence("EVID_U1", "UNKNOWN")},
)
assert_true(result_unknown_ok["valid"] is True, "UNKNOWN+UNKNOWN was rejected")
print("PASS 7: UNKNOWN claim + UNKNOWN evidence passed.")


# PASS 8: any claim + CONTRADICTED evidence fails
result_contradicted = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_008", ["EVID_C1"], "SUPPORTED"),
    {"EVID_C1": make_evidence("EVID_C1", "CONTRADICTED")},
)
assert_false(
    result_contradicted["valid"],
    "claim citing CONTRADICTED evidence was accepted",
)
assert_true(
    has_code(result_contradicted, "CONTRADICTED_EVIDENCE"),
    "expected CONTRADICTED_EVIDENCE",
)
print("PASS 8: any claim + CONTRADICTED evidence failed.")
print(f"  Result: {result_contradicted}")


# PASS 9: human_approval=true does not override invalid evidence state
result_approval_no_override = validate_claim_evidence_state_compatibility(
    make_claim(
        "CLAIM_STATE_009",
        ["EVID_S1"],
        "VERIFIED",
        human_approval=True,
    ),
    {"EVID_S1": make_evidence("EVID_S1", "SUPPORTED")},
)
assert_false(
    result_approval_no_override["valid"],
    "human_approval=true overrode incompatible evidence state",
)
assert_true(
    has_code(result_approval_no_override, "INCOMPATIBLE_EVIDENCE_STATE"),
    "expected INCOMPATIBLE_EVIDENCE_STATE despite human_approval=true",
)
print("PASS 9: human_approval=true did not override invalid evidence state.")
print(f"  Result: {result_approval_no_override}")


# PASS 10: malformed input fails closed
malformed_cases = [
    ("malformed claim", "not-a-claim", {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")}),
    (
        "null evidence index",
        make_claim("CLAIM_STATE_010", ["EVID_V1"], "VERIFIED"),
        None,
    ),
    (
        "string evidence index",
        make_claim("CLAIM_STATE_010", ["EVID_V1"], "VERIFIED"),
        "EVID_V1",
    ),
]

for label, claim, index in malformed_cases:
    result_malformed = validate_claim_evidence_state_compatibility(claim, index)
    assert_false(result_malformed["valid"], f"malformed input accepted ({label})")
    assert_true(
        has_code(result_malformed, "MALFORMED_CLAIM")
        or has_code(result_malformed, "MALFORMED_EVIDENCE_INDEX")
        or has_code(result_malformed, "CLAIM_SCHEMA_INVALID"),
        f"expected malformed failure code ({label})",
    )
    print(f"PASS 10 ({label}): malformed input failed closed.")
    print(f"  Result: {result_malformed}")


# PASS 11: unrelated malformed evidence must not invalidate state compatibility
result_unrelated_ok = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_011", ["EVID_V1"], "VERIFIED"),
    {
        "EVID_V1": make_evidence("EVID_V1", "VERIFIED"),
        "EVID_UNRELATED_BAD": "not-a-record",
    },
)
assert_true(
    result_unrelated_ok["valid"] is True,
    "unrelated malformed evidence invalidated state compatibility",
)
print("PASS 11: state compatibility ignored unrelated malformed evidence.")


# PASS 12: malformed cited evidence fails state validation
result_cited_bad = validate_claim_evidence_state_compatibility(
    make_claim("CLAIM_STATE_012", ["EVID_V1"], "VERIFIED"),
    {"EVID_V1": "not-a-record"},
)
assert_false(result_cited_bad["valid"], "cited malformed evidence passed state validation")
assert_true(
    has_code(result_cited_bad, "MALFORMED_EVIDENCE_INDEX"),
    "expected MALFORMED_EVIDENCE_INDEX for cited malformed evidence",
)
print("PASS 12: cited malformed evidence failed state validation.")
print(f"  Result: {result_cited_bad}")


print("PASS: claim evidence-state compatibility tests completed successfully.")
