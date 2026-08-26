import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_lineage import validate_claim_lineage  # noqa: E402


def make_evidence(evidence_id: str) -> dict:
    # Synthetic fixture only. Not a real experience or claim.
    return {
        "evidence_id": evidence_id,
        "experience_id": "EXP_TEST_001",
        "fact": f"Synthetic fact for {evidence_id}.",
        "capabilities": ["data analysis"],
        "technologies": ["SQL"],
        "evidence_state": "SUPPORTED",
        "original_source": f"synthetic-fixture://evidence/{evidence_id}",
        "source_location": "tests/claim_lineage_test.py",
        "safe_for_external_use": False,
        "notes": None,
    }


def make_claim(claim_id: str, evidence_ids: list) -> dict:
    # Synthetic fixture only. Not a real approved claim about Bora.
    return {
        "claim_id": claim_id,
        "wording": "Used SQL to analyze structured tables for an internal synthetic report.",
        "evidence_ids": evidence_ids,
        "evidence_state": "SUPPORTED",
        "allowed_contexts": ["resume"],
        "forbidden_contexts": [],
        "human_approval": True,
        "date": "2026-08-26",
        "version": "1",
    }


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


# PASS 1: valid claim with one Evidence_ID
evidence_one = {
    "EVID_TEST_001": make_evidence("EVID_TEST_001"),
}
result_one = validate_claim_lineage(
    make_claim("CLAIM_TEST_001", ["EVID_TEST_001"]),
    evidence_one,
)
assert_true(result_one["valid"] is True, "valid single-evidence claim was rejected")
assert_true(
    result_one["resolved_evidence_ids"] == ["EVID_TEST_001"],
    "single-evidence resolved IDs mismatch",
)
assert_true(result_one["missing_evidence_ids"] == [], "unexpected missing IDs")
assert_true(result_one["duplicate_evidence_ids"] == [], "unexpected duplicates")
assert_true(result_one["errors"] == [], "unexpected errors for valid claim")
print("PASS 1: valid claim with one Evidence_ID was accepted.")


# PASS 2: valid claim with multiple Evidence_IDs
evidence_multi = {
    "EVID_TEST_001": make_evidence("EVID_TEST_001"),
    "EVID_TEST_002": make_evidence("EVID_TEST_002"),
}
result_multi = validate_claim_lineage(
    make_claim("CLAIM_TEST_002", ["EVID_TEST_001", "EVID_TEST_002"]),
    evidence_multi,
)
assert_true(result_multi["valid"] is True, "valid multi-evidence claim was rejected")
assert_true(
    result_multi["resolved_evidence_ids"] == ["EVID_TEST_001", "EVID_TEST_002"],
    "multi-evidence resolved IDs mismatch",
)
print("PASS 2: valid claim with multiple Evidence_IDs was accepted.")


# PASS 3: missing Evidence_ID rejected
result_missing = validate_claim_lineage(
    make_claim("CLAIM_TEST_003", ["EVID_MISSING_001"]),
    evidence_one,
)
assert_false(result_missing["valid"], "missing Evidence_ID was accepted")
assert_true(
    result_missing["missing_evidence_ids"] == ["EVID_MISSING_001"],
    "missing Evidence_ID not reported",
)
assert_true(
    any(error.get("code") == "MISSING_EVIDENCE_ID" for error in result_missing["errors"]),
    "MISSING_EVIDENCE_ID error not reported",
)
print("PASS 3: missing Evidence_ID was correctly rejected.")
print(f"  Result: {result_missing}")


# PASS 4: one valid + one missing Evidence_ID rejected
result_partial = validate_claim_lineage(
    make_claim("CLAIM_TEST_004", ["EVID_TEST_001", "EVID_MISSING_002"]),
    evidence_one,
)
assert_false(result_partial["valid"], "partially missing lineage was accepted")
assert_true(
    result_partial["resolved_evidence_ids"] == ["EVID_TEST_001"],
    "resolved IDs mismatch for partial miss",
)
assert_true(
    result_partial["missing_evidence_ids"] == ["EVID_MISSING_002"],
    "missing IDs mismatch for partial miss",
)
print("PASS 4: one valid + one missing Evidence_ID was correctly rejected.")
print(f"  Result: {result_partial}")


# PASS 5: duplicate Evidence_ID rejected
# Bypass schema uniqueItems by calling lineage with duplicate list directly;
# schema validation will also fail closed, which is intentional.
result_duplicate = validate_claim_lineage(
    make_claim("CLAIM_TEST_005", ["EVID_TEST_001", "EVID_TEST_001"]),
    evidence_one,
)
assert_false(result_duplicate["valid"], "duplicate Evidence_ID was accepted")
assert_true(
    result_duplicate["duplicate_evidence_ids"] == ["EVID_TEST_001"],
    "duplicate Evidence_ID not reported",
)
assert_true(
    any(
        error.get("code") == "DUPLICATE_EVIDENCE_ID"
        for error in result_duplicate["errors"]
    ),
    "DUPLICATE_EVIDENCE_ID error not reported",
)
print("PASS 5: duplicate Evidence_ID was correctly rejected.")
print(f"  Result: {result_duplicate}")


# PASS 6: case mismatch rejected (exact, case-sensitive matching only)
result_case = validate_claim_lineage(
    make_claim("CLAIM_TEST_006", ["evid_test_001"]),
    evidence_one,
)
assert_false(result_case["valid"], "case-mismatched Evidence_ID was accepted")
assert_true(
    result_case["missing_evidence_ids"] == ["evid_test_001"],
    "case mismatch not treated as missing exact ID",
)
assert_true(
    result_case["resolved_evidence_ids"] == [],
    "case-mismatched ID should not resolve",
)
print("PASS 6: case-mismatched Evidence_ID was correctly rejected.")
print(f"  Result: {result_case}")


# PASS 7: empty evidence_ids fails closed
result_empty = validate_claim_lineage(
    make_claim("CLAIM_TEST_007", []),
    evidence_one,
)
assert_false(result_empty["valid"], "empty evidence_ids was accepted")
assert_true(
    any(error.get("code") == "EMPTY_EVIDENCE_IDS" for error in result_empty["errors"]),
    "EMPTY_EVIDENCE_IDS error not reported",
)
print("PASS 7: empty evidence_ids failed closed.")
print(f"  Result: {result_empty}")


# PASS 8: malformed evidence index/input fails closed
# Note: unrelated non-mapping sequence items are ignored under cited-only
# claim validation (covered by PASS 11). Cited malformed records still fail.
malformed_cases = [
    ("null index", None),
    ("string index", "EVID_TEST_001"),
    ("mapping value not a record", {"EVID_TEST_001": "not-a-record"}),
    (
        "key/record evidence_id mismatch",
        {"EVID_TEST_001": make_evidence("EVID_TEST_OTHER")},
    ),
]

for label, bad_index in malformed_cases:
    result_malformed = validate_claim_lineage(
        make_claim("CLAIM_TEST_008", ["EVID_TEST_001"]),
        bad_index,
    )
    assert_false(
        result_malformed["valid"],
        f"malformed evidence index was accepted ({label})",
    )
    assert_true(
        any(
            error.get("code") in {
                "MALFORMED_EVIDENCE_INDEX",
                "EVIDENCE_SCHEMA_INVALID",
            }
            for error in result_malformed["errors"]
        ),
        f"malformed evidence index error not reported ({label})",
    )
    print(f"PASS 8 ({label}): malformed evidence index failed closed.")
    print(f"  Result: {result_malformed}")


# Also fail closed on malformed claim input.
result_bad_claim = validate_claim_lineage("not-a-claim", evidence_one)
assert_false(result_bad_claim["valid"], "malformed claim was accepted")
assert_true(
    any(error.get("code") == "MALFORMED_CLAIM" for error in result_bad_claim["errors"]),
    "MALFORMED_CLAIM error not reported",
)
print("PASS 8 (malformed claim): malformed claim input failed closed.")
print(f"  Result: {result_bad_claim}")


# PASS 9: unrelated malformed evidence must not invalidate a valid claim
result_unrelated_malformed = validate_claim_lineage(
    make_claim("CLAIM_TEST_009", ["EVID_TEST_001"]),
    {
        "EVID_TEST_001": make_evidence("EVID_TEST_001"),
        "EVID_UNRELATED_BAD": "not-a-record",
    },
)
assert_true(
    result_unrelated_malformed["valid"] is True,
    "unrelated malformed evidence invalidated a valid claim",
)
print("PASS 9: valid claim ignored unrelated malformed evidence.")


# PASS 10: malformed evidence that IS cited fails
result_cited_malformed = validate_claim_lineage(
    make_claim("CLAIM_TEST_010", ["EVID_TEST_001"]),
    {"EVID_TEST_001": "not-a-record"},
)
assert_false(result_cited_malformed["valid"], "cited malformed evidence was accepted")
assert_true(
    any(
        error.get("code") == "MALFORMED_EVIDENCE_INDEX"
        for error in result_cited_malformed["errors"]
    ),
    "expected MALFORMED_EVIDENCE_INDEX for cited malformed evidence",
)
print("PASS 10: cited malformed evidence failed closed.")
print(f"  Result: {result_cited_malformed}")


# PASS 11: sequence/list evidence_index input
result_sequence_ok = validate_claim_lineage(
    make_claim("CLAIM_TEST_011", ["EVID_TEST_001", "EVID_TEST_002"]),
    [
        make_evidence("EVID_TEST_001"),
        make_evidence("EVID_TEST_002"),
        "unrelated-malformed-item",
    ],
)
assert_true(
    result_sequence_ok["valid"] is True,
    "valid sequence evidence_index was rejected",
)
print("PASS 11: valid sequence evidence_index passed.")


result_sequence_duplicate = validate_claim_lineage(
    make_claim("CLAIM_TEST_012", ["EVID_TEST_001"]),
    [
        make_evidence("EVID_TEST_001"),
        make_evidence("EVID_TEST_001"),
    ],
)
assert_false(
    result_sequence_duplicate["valid"],
    "duplicate Evidence_IDs in sequence were accepted",
)
assert_true(
    any(
        error.get("code") == "DUPLICATE_EVIDENCE_ID_IN_INDEX"
        for error in result_sequence_duplicate["errors"]
    ),
    "expected DUPLICATE_EVIDENCE_ID_IN_INDEX",
)
print("PASS 12: duplicate Evidence_IDs in sequence failed closed.")
print(f"  Result: {result_sequence_duplicate}")


result_sequence_cited_missing_due_to_malformed = validate_claim_lineage(
    make_claim("CLAIM_TEST_013", ["EVID_TEST_001"]),
    ["not-a-mapping-item"],
)
assert_false(
    result_sequence_cited_missing_due_to_malformed["valid"],
    "sequence without cited evidence was accepted",
)
assert_true(
    any(
        error.get("code") == "MISSING_EVIDENCE_ID"
        for error in result_sequence_cited_missing_due_to_malformed["errors"]
    ),
    "expected MISSING_EVIDENCE_ID when cited ID absent from sequence",
)
print("PASS 13: malformed sequence without cited evidence failed closed.")
print(f"  Result: {result_sequence_cited_missing_due_to_malformed}")


print("PASS: claim lineage behavioral tests completed successfully.")
