"""Deterministic tests for repository-wide evidence integrity."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
EVIDENCE_ROOT = ROOT / "evidence"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from evidence_repository import (  # noqa: E402
    EXPERIENCE_REGISTRY_STATUS,
    discover_evidence_files,
    validate_evidence_repository,
)


EXPECTED_WW_IDS = [
    "WW_ADOPT_001",
    "WW_ARCH_001",
    "WW_ARCH_002",
    "WW_CONN_001",
    "WW_CTRL_001",
    "WW_CTRL_002",
    "WW_DATA_001",
    "WW_DATA_002",
    "WW_FUQ_001",
    "WW_MAP_001",
    "WW_SYNC_001",
    "WW_TEST_001",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def make_valid_record(evidence_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "experience_id": "EXP_TEST_001",
        "fact": f"Synthetic repository integrity fact for {evidence_id}.",
        "capabilities": ["data analysis"],
        "technologies": ["SQL"],
        "evidence_state": "SUPPORTED",
        "original_source": f"synthetic-fixture://evidence/{evidence_id}",
        "source_location": "tests/evidence_repository_test.py",
        "safe_for_external_use": False,
        "notes": None,
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def error_codes(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


# ---------------------------------------------------------------------------
# PASS 1 — Current real repository
# ---------------------------------------------------------------------------
real = validate_evidence_repository(EVIDENCE_ROOT)
assert_true(real["valid"] is True, "current Winter Walk evidence repository failed")
assert_true(real["records_checked"] == 12, f"expected 12 records, got {real['records_checked']}")
assert_true(real["index"] is not None, "trusted index missing for valid repository")
assert_true(
    sorted(real["index"].keys()) == EXPECTED_WW_IDS,
    f"unexpected Evidence_ID set: {sorted(real['index'].keys())}",
)
assert_true(
    real["experience_registry_status"] == EXPERIENCE_REGISTRY_STATUS,
    "experience registry status mismatch",
)
print("PASS 1: current real Winter Walk evidence repository (12 records) passed.")


# ---------------------------------------------------------------------------
# PASS 2 — Duplicate ID
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_DUP_001.json", make_valid_record("WW_DUP_001"))
    write_json(root / "subdir" / "WW_DUP_001.json", make_valid_record("WW_DUP_001"))
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "duplicate Evidence_ID was accepted")
    assert_true(result["index"] is None, "trusted index returned despite duplicate ID")
    assert_true(
        "DUPLICATE_EVIDENCE_ID" in error_codes(result),
        f"missing DUPLICATE_EVIDENCE_ID: {result['errors']}",
    )
print("PASS 2: duplicate Evidence_ID failed closed.")


# ---------------------------------------------------------------------------
# PASS 3 — Filename / ID mismatch
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_FAKE_001.json", make_valid_record("WW_FAKE_002"))
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "filename/ID mismatch was accepted")
    assert_true(result["index"] is None, "trusted index returned despite mismatch")
    assert_true(
        "EVIDENCE_FILENAME_ID_MISMATCH" in error_codes(result),
        f"missing EVIDENCE_FILENAME_ID_MISMATCH: {result['errors']}",
    )
print("PASS 3: filename/Evidence_ID mismatch failed closed.")


# ---------------------------------------------------------------------------
# PASS 4 — Invalid evidence state (schema)
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_record("WW_STATE_001")
    bad["evidence_state"] = "PROBABLE"
    write_json(root / "WW_STATE_001.json", bad)
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "PROBABLE evidence_state was accepted")
    assert_true(result["index"] is None, "trusted index returned for schema-invalid state")
    assert_true(
        "EVIDENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing EVIDENCE_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 4: invalid evidence_state failed via canonical schema.")


# ---------------------------------------------------------------------------
# PASS 5 — Missing required field
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_record("WW_MISS_001")
    del bad["fact"]
    write_json(root / "WW_MISS_001.json", bad)
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "missing required field was accepted")
    assert_true(result["index"] is None, "trusted index returned for missing field")
    assert_true(
        "EVIDENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing EVIDENCE_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 5: missing required field failed closed.")


# ---------------------------------------------------------------------------
# PASS 6 — Additional forbidden property
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_record("WW_EXTRA_001")
    bad["invented_field"] = "should_be_rejected"
    write_json(root / "WW_EXTRA_001.json", bad)
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "additionalProperties violation was accepted")
    assert_true(result["index"] is None, "trusted index returned for extra property")
    assert_true(
        "EVIDENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing EVIDENCE_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 6: additional forbidden property failed closed.")


# ---------------------------------------------------------------------------
# PASS 7 — Malformed JSON
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_BADJSON_001.json", '{"evidence_id": "WW_BADJSON_001",')
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "malformed JSON was accepted")
    assert_true(result["index"] is None, "trusted index returned for malformed JSON")
    assert_true(
        "EVIDENCE_JSON_PARSE_ERROR" in error_codes(result),
        f"missing EVIDENCE_JSON_PARSE_ERROR: {result['errors']}",
    )
    assert_true(
        any(error.get("path") == "WW_BADJSON_001.json" for error in result["errors"]),
        f"offending file not identified: {result['errors']}",
    )
print("PASS 7: malformed JSON failed closed with file identity.")


# ---------------------------------------------------------------------------
# PASS 8 — Non-object JSON root
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_ARRAY_001.json", [])
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "array root was accepted")
    assert_true(result["index"] is None, "trusted index returned for non-object root")
    assert_true(
        "EVIDENCE_UNSUPPORTED_RECORD_SHAPE" in error_codes(result),
        f"missing EVIDENCE_UNSUPPORTED_RECORD_SHAPE: {result['errors']}",
    )
print("PASS 8: non-object JSON root failed closed.")


# ---------------------------------------------------------------------------
# PASS 9 — Deterministic discovery / index ordering
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    # Create in reverse alphabetical order to stress filesystem creation order.
    for evidence_id in ["WW_Z_001", "WW_M_001", "WW_A_001"]:
        write_json(root / f"{evidence_id}.json", make_valid_record(evidence_id))
    first = validate_evidence_repository(root)
    second = validate_evidence_repository(root)
    assert_true(first["valid"] and second["valid"], "deterministic fixture failed validation")
    assert_true(
        list(first["index"].keys()) == ["WW_A_001", "WW_M_001", "WW_Z_001"],
        f"index key order not deterministic sorted: {list(first['index'].keys())}",
    )
    assert_true(
        first["discovered_paths"] == second["discovered_paths"],
        "discovered_paths not stable across runs",
    )
    assert_true(
        list(first["index"].keys()) == list(second["index"].keys()),
        "index key order not stable across runs",
    )
    discovered = discover_evidence_files(root)
    assert_true(
        [path.name for path in discovered] == ["WW_A_001.json", "WW_M_001.json", "WW_Z_001.json"],
        f"discovery order not deterministic: {[path.name for path in discovered]}",
    )
print("PASS 9: deterministic discovery and index ordering.")


# ---------------------------------------------------------------------------
# PASS 10 — Fail-closed index with partial invalid set
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for i in range(1, 12):
        evidence_id = f"WW_OK_{i:03d}"
        write_json(root / f"{evidence_id}.json", make_valid_record(evidence_id))
    bad = make_valid_record("WW_BAD_001")
    bad["evidence_state"] = "PROBABLE"
    write_json(root / "WW_BAD_001.json", bad)
    result = validate_evidence_repository(root)
    assert_false(result["valid"], "mixed valid/invalid repository was accepted")
    assert_true(result["records_checked"] == 12, "expected 12 discovered files")
    assert_true(
        result["index"] is None,
        "partial trusted index leaked for invalid repository",
    )
    assert_true(
        "EVIDENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing schema error for bad record: {result['errors']}",
    )
print("PASS 10: fail-closed — no partial trusted index.")


# ---------------------------------------------------------------------------
# PASS 11 — Existing claim validators remain unchanged
# ---------------------------------------------------------------------------
# Executed separately by the milestone runner (all 7 existing suites).
print("PASS 11: deferred to existing claim validation suites (run separately).")


# ---------------------------------------------------------------------------
# PASS 12 — Experience reference boundary (no fake registry)
# ---------------------------------------------------------------------------
assert_true(
    EXPERIENCE_REGISTRY_STATUS == "EXPERIENCE_REGISTRY_DECISION_REQUIRED",
    "experience registry status constant drifted",
)
assert_true(
    real["experience_registry_status"] == "EXPERIENCE_REGISTRY_DECISION_REQUIRED",
    "repository validator falsely claims experience referential integrity",
)
# Valid repository must not invent experience-registry errors.
assert_false(
    any(code.startswith("EXPERIENCE_") and code != EXPERIENCE_REGISTRY_STATUS for code in error_codes(real)),
    "unexpected experience integrity errors without registry",
)
print(
    "PASS 12: experience referential integrity NOT pretended; "
    "EXPERIENCE_REGISTRY_DECISION_REQUIRED surfaced."
)


print("PASS: evidence repository integrity tests completed successfully.")
