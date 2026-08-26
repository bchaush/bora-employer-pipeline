import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_validation import validate_claim  # noqa: E402


def make_evidence(evidence_id: str, evidence_state: str = "VERIFIED") -> dict:
    # Synthetic fixture only. Not a real experience or claim.
    return {
        "evidence_id": evidence_id,
        "experience_id": "EXP_TEST_001",
        "fact": f"Synthetic fact for {evidence_id}.",
        "capabilities": ["data analysis"],
        "technologies": ["SQL"],
        "evidence_state": evidence_state,
        "original_source": f"synthetic-fixture://evidence/{evidence_id}",
        "source_location": "tests/claim_validation_test.py",
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


def has_code(items: list, code: str) -> bool:
    return any(item.get("code") == code for item in items)


# PASS 1: fully valid approved VERIFIED claim -> reusable true
result_verified = validate_claim(
    make_claim("CLAIM_UNIFIED_001", ["EVID_V1"], "VERIFIED"),
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_true(result_verified["valid_record"] is True, "VERIFIED valid_record false")
assert_true(result_verified["reusable"] is True, "VERIFIED reusable false")
assert_true(result_verified["schema_valid"] is True, "VERIFIED schema_valid false")
assert_true(result_verified["lineage_valid"] is True, "VERIFIED lineage_valid false")
assert_true(result_verified["state_valid"] is True, "VERIFIED state_valid false")
assert_true(result_verified["human_approved"] is True, "VERIFIED human_approved false")
assert_true(result_verified["errors"] == [], "VERIFIED unexpected errors")
print("PASS 1: fully valid approved VERIFIED claim is reusable.")


# PASS 2: fully valid approved SUPPORTED claim -> reusable true
result_supported = validate_claim(
    make_claim("CLAIM_UNIFIED_002", ["EVID_V1", "EVID_S1"], "SUPPORTED"),
    {
        "EVID_V1": make_evidence("EVID_V1", "VERIFIED"),
        "EVID_S1": make_evidence("EVID_S1", "SUPPORTED"),
    },
)
assert_true(result_supported["valid_record"] is True, "SUPPORTED valid_record false")
assert_true(result_supported["reusable"] is True, "SUPPORTED reusable false")
print("PASS 2: fully valid approved SUPPORTED claim is reusable.")


# PASS 3: valid but human_approval=false -> reusable false
result_unapproved = validate_claim(
    make_claim(
        "CLAIM_UNIFIED_003",
        ["EVID_V1"],
        "VERIFIED",
        human_approval=False,
    ),
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_true(result_unapproved["valid_record"] is True, "unapproved valid_record false")
assert_false(result_unapproved["reusable"], "unapproved reusable true")
assert_false(result_unapproved["human_approved"], "unapproved human_approved true")
assert_true(
    has_code(result_unapproved["warnings"], "NOT_HUMAN_APPROVED"),
    "expected NOT_HUMAN_APPROVED warning",
)
print("PASS 3: human_approval=false keeps record valid but not reusable.")
print(f"  Result: {result_unapproved}")


# PASS 4: UNKNOWN claim -> record valid, reusable false
result_unknown = validate_claim(
    make_claim("CLAIM_UNIFIED_004", ["EVID_U1"], "UNKNOWN"),
    {"EVID_U1": make_evidence("EVID_U1", "UNKNOWN")},
)
assert_true(result_unknown["valid_record"] is True, "UNKNOWN valid_record false")
assert_false(result_unknown["reusable"], "UNKNOWN reusable true")
assert_true(
    has_code(result_unknown["warnings"], "CLAIM_STATE_NOT_REUSABLE"),
    "expected CLAIM_STATE_NOT_REUSABLE warning for UNKNOWN",
)
print("PASS 4: UNKNOWN claim is valid_record but not reusable.")
print(f"  Result: {result_unknown}")


# PASS 5: CONTRADICTED claim -> record retained, reusable false
result_contradicted_claim = validate_claim(
    make_claim("CLAIM_UNIFIED_005", ["EVID_V1"], "CONTRADICTED"),
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_true(
    result_contradicted_claim["valid_record"] is True,
    "CONTRADICTED claim valid_record false",
)
assert_false(result_contradicted_claim["reusable"], "CONTRADICTED claim reusable true")
assert_true(
    has_code(result_contradicted_claim["warnings"], "CLAIM_STATE_NOT_REUSABLE"),
    "expected CLAIM_STATE_NOT_REUSABLE warning for CONTRADICTED claim",
)
print("PASS 5: CONTRADICTED claim retained as record but not reusable.")
print(f"  Result: {result_contradicted_claim}")


# PASS 6: missing Evidence_ID -> fail
result_missing = validate_claim(
    make_claim("CLAIM_UNIFIED_006", ["EVID_MISSING"], "VERIFIED"),
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_false(result_missing["valid_record"], "missing Evidence_ID valid_record true")
assert_false(result_missing["reusable"], "missing Evidence_ID reusable true")
assert_false(result_missing["lineage_valid"], "missing Evidence_ID lineage_valid true")
assert_true(
    has_code(result_missing["errors"], "MISSING_EVIDENCE_ID"),
    "expected MISSING_EVIDENCE_ID",
)
print("PASS 6: missing Evidence_ID failed.")
print(f"  Result: {result_missing}")


# PASS 7: duplicate Evidence_ID -> fail
result_duplicate = validate_claim(
    make_claim("CLAIM_UNIFIED_007", ["EVID_V1", "EVID_V1"], "VERIFIED"),
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_false(result_duplicate["valid_record"], "duplicate Evidence_ID valid_record true")
assert_false(result_duplicate["reusable"], "duplicate Evidence_ID reusable true")
assert_true(
    has_code(result_duplicate["errors"], "DUPLICATE_EVIDENCE_ID")
    or has_code(result_duplicate["errors"], "CLAIM_SCHEMA_INVALID"),
    "expected duplicate/schema failure",
)
print("PASS 7: duplicate Evidence_ID failed.")
print(f"  Result: {result_duplicate}")


# PASS 8: incompatible evidence state -> fail
result_incompatible = validate_claim(
    make_claim("CLAIM_UNIFIED_008", ["EVID_S1"], "VERIFIED"),
    {"EVID_S1": make_evidence("EVID_S1", "SUPPORTED")},
)
assert_false(result_incompatible["valid_record"], "incompatible state valid_record true")
assert_false(result_incompatible["reusable"], "incompatible state reusable true")
assert_false(result_incompatible["state_valid"], "incompatible state_valid true")
assert_true(
    has_code(result_incompatible["errors"], "INCOMPATIBLE_EVIDENCE_STATE"),
    "expected INCOMPATIBLE_EVIDENCE_STATE",
)
print("PASS 8: incompatible evidence state failed.")
print(f"  Result: {result_incompatible}")


# PASS 9: malformed claim -> fail closed
result_bad_claim = validate_claim("not-a-claim", {"EVID_V1": make_evidence("EVID_V1")})
assert_false(result_bad_claim["valid_record"], "malformed claim valid_record true")
assert_false(result_bad_claim["reusable"], "malformed claim reusable true")
assert_true(
    has_code(result_bad_claim["errors"], "MALFORMED_CLAIM"),
    "expected MALFORMED_CLAIM",
)
print("PASS 9: malformed claim failed closed.")
print(f"  Result: {result_bad_claim}")


# PASS 10: malformed evidence -> fail closed
result_bad_evidence = validate_claim(
    make_claim("CLAIM_UNIFIED_010", ["EVID_V1"], "VERIFIED"),
    {"EVID_V1": "not-an-evidence-record"},
)
assert_false(result_bad_evidence["valid_record"], "malformed evidence valid_record true")
assert_false(result_bad_evidence["reusable"], "malformed evidence reusable true")
assert_true(
    has_code(result_bad_evidence["errors"], "MALFORMED_EVIDENCE_INDEX")
    or has_code(result_bad_evidence["errors"], "EVIDENCE_SCHEMA_INVALID"),
    "expected malformed evidence failure",
)
print("PASS 10: malformed evidence failed closed.")
print(f"  Result: {result_bad_evidence}")


# PASS 11: human approval cannot rescue invalid lineage
result_approval_lineage = validate_claim(
    make_claim(
        "CLAIM_UNIFIED_011",
        ["EVID_MISSING"],
        "VERIFIED",
        human_approval=True,
    ),
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_false(
    result_approval_lineage["valid_record"],
    "human approval rescued invalid lineage",
)
assert_false(
    result_approval_lineage["reusable"],
    "human approval made invalid lineage reusable",
)
assert_true(
    has_code(result_approval_lineage["errors"], "MISSING_EVIDENCE_ID"),
    "expected MISSING_EVIDENCE_ID despite human_approval",
)
print("PASS 11: human approval cannot rescue invalid lineage.")
print(f"  Result: {result_approval_lineage}")


# PASS 12: human approval cannot rescue state incompatibility
result_approval_state = validate_claim(
    make_claim(
        "CLAIM_UNIFIED_012",
        ["EVID_S1"],
        "VERIFIED",
        human_approval=True,
    ),
    {"EVID_S1": make_evidence("EVID_S1", "SUPPORTED")},
)
assert_false(
    result_approval_state["valid_record"],
    "human approval rescued state incompatibility",
)
assert_false(
    result_approval_state["reusable"],
    "human approval made incompatible state reusable",
)
assert_true(
    has_code(result_approval_state["errors"], "INCOMPATIBLE_EVIDENCE_STATE"),
    "expected INCOMPATIBLE_EVIDENCE_STATE despite human_approval",
)
print("PASS 12: human approval cannot rescue state incompatibility.")
print(f"  Result: {result_approval_state}")


# PASS 13: unrelated malformed evidence must not invalidate unified validation
result_unrelated = validate_claim(
    make_claim("CLAIM_UNIFIED_013", ["EVID_V1"], "VERIFIED"),
    {
        "EVID_V1": make_evidence("EVID_V1", "VERIFIED"),
        "EVID_UNRELATED_BAD": "not-a-record",
    },
)
assert_true(result_unrelated["valid_record"] is True, "unrelated malformed broke valid_record")
assert_true(result_unrelated["reusable"] is True, "unrelated malformed broke reusable")
print("PASS 13: unified validate_claim ignored unrelated malformed evidence.")


# PASS 14: malformed cited evidence fails unified validation
result_cited_bad = validate_claim(
    make_claim("CLAIM_UNIFIED_014", ["EVID_V1"], "VERIFIED"),
    {"EVID_V1": "not-a-record"},
)
assert_false(result_cited_bad["valid_record"], "cited malformed evidence valid_record true")
assert_false(result_cited_bad["reusable"], "cited malformed evidence reusable true")
assert_true(
    has_code(result_cited_bad["errors"], "MALFORMED_EVIDENCE_INDEX")
    or has_code(result_cited_bad["errors"], "EVIDENCE_SCHEMA_INVALID"),
    "expected cited malformed evidence failure",
)
print("PASS 14: unified validate_claim failed on cited malformed evidence.")
print(f"  Result: {result_cited_bad}")


# PASS 15: sequence evidence_index supported by unified validator
result_sequence = validate_claim(
    make_claim("CLAIM_UNIFIED_015", ["EVID_V1"], "VERIFIED"),
    [make_evidence("EVID_V1", "VERIFIED"), "unrelated-malformed"],
)
assert_true(result_sequence["valid_record"] is True, "sequence input valid_record false")
assert_true(result_sequence["reusable"] is True, "sequence input reusable false")
print("PASS 15: unified validate_claim accepted valid sequence evidence_index.")


# PASS 16-18: context conflict blocks reusable use
result_no_overlap = validate_claim(
    make_claim("CLAIM_UNIFIED_016", ["EVID_V1"], "VERIFIED"),
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_true(result_no_overlap["reusable"] is True, "no-overlap claim not reusable")
print("PASS 16: no allowed/forbidden context overlap remains reusable.")


claim_overlap = make_claim("CLAIM_UNIFIED_017", ["EVID_V1"], "VERIFIED")
claim_overlap["allowed_contexts"] = ["resume", "interview"]
claim_overlap["forbidden_contexts"] = ["resume"]
result_overlap = validate_claim(
    claim_overlap,
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_true(result_overlap["valid_record"] is True, "context overlap valid_record false")
assert_false(result_overlap["reusable"], "context overlap reusable true")
assert_true(
    has_code(result_overlap["errors"], "CONTEXT_CONFLICT"),
    "expected CONTEXT_CONFLICT",
)
print("PASS 17: allowed/forbidden context overlap blocks reusable.")
print(f"  Result: {result_overlap}")


claim_overlap_approved = make_claim(
    "CLAIM_UNIFIED_018",
    ["EVID_V1"],
    "VERIFIED",
    human_approval=True,
)
claim_overlap_approved["allowed_contexts"] = ["resume"]
claim_overlap_approved["forbidden_contexts"] = ["resume"]
result_overlap_approved = validate_claim(
    claim_overlap_approved,
    {"EVID_V1": make_evidence("EVID_V1", "VERIFIED")},
)
assert_false(
    result_overlap_approved["reusable"],
    "human_approval overrode CONTEXT_CONFLICT",
)
assert_true(
    has_code(result_overlap_approved["errors"], "CONTEXT_CONFLICT"),
    "expected CONTEXT_CONFLICT despite human_approval",
)
print("PASS 18: human_approval cannot override context overlap.")
print(f"  Result: {result_overlap_approved}")


print("PASS: unified claim validation tests completed successfully.")
