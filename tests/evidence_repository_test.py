"""Deterministic tests for repository-wide evidence integrity.

AUTHORITATIVE tests call validate_evidence_repository with a real temporary
Experience Registry root (or the committed registry).

STRUCTURE-ONLY tests call validate_evidence_repository_structure explicitly.
They must never impersonate Experience trust via hand-built indexes.
"""

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
    EXPERIENCE_REFERENCE_CHECK_FAILED,
    EXPERIENCE_REFERENCE_NOT_CHECKED,
    EXPERIENCE_REFERENCE_STATUS,
    EXPERIENCE_REGISTRY_STATUS,
    discover_evidence_files,
    validate_evidence_repository,
    validate_evidence_repository_structure,
)
from experience_repository import validate_experience_repository  # noqa: E402


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
    "WW_OFFER_001",
    "WW_PROC_001",
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


def make_valid_experience(experience_id: str = "EXP_TEST_001") -> dict:
    return {
        "experience_id": experience_id,
        "experience_name": f"Synthetic {experience_id}",
        "experience_type": "OTHER",
        "organization": "Synthetic Org",
        "source_of_truth": "tests/evidence_repository_test.py",
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def error_codes(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


def write_temp_experience_root(base: Path, experience_id: str = "EXP_TEST_001") -> Path:
    exp_root = base / "experiences"
    write_json(exp_root / f"{experience_id}.json", make_valid_experience(experience_id))
    return exp_root


# ---------------------------------------------------------------------------
# PASS 1 — AUTHORITATIVE: current real repository
# ---------------------------------------------------------------------------
real = validate_evidence_repository(EVIDENCE_ROOT)
assert_true(real["valid"] is True, "current Winter Walk evidence repository failed")
assert_true(real["records_checked"] == 14, f"expected 14 records, got {real['records_checked']}")
assert_true(real["index"] is not None, "trusted index missing for valid repository")
assert_true(
    sorted(real["index"].keys()) == EXPECTED_WW_IDS,
    f"unexpected Evidence_ID set: {sorted(real['index'].keys())}",
)
assert_true(
    real["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
    "experience registry status mismatch",
)
assert_true(
    EXPERIENCE_REGISTRY_STATUS == EXPERIENCE_REFERENCE_STATUS,
    "status alias drifted",
)
print("PASS 1 [AUTHORITATIVE]: current real Winter Walk evidence repository (14 records) passed.")


# ---------------------------------------------------------------------------
# PASS 2 — STRUCTURE-ONLY: Duplicate ID
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_DUP_001.json", make_valid_record("WW_DUP_001"))
    write_json(root / "subdir" / "WW_DUP_001.json", make_valid_record("WW_DUP_001"))
    result = validate_evidence_repository_structure(root)
    assert_false(result["valid"], "duplicate Evidence_ID was accepted")
    assert_true(result["index"] is None, "trusted index returned despite duplicate ID")
    assert_true(
        "DUPLICATE_EVIDENCE_ID" in error_codes(result),
        f"missing DUPLICATE_EVIDENCE_ID: {result['errors']}",
    )
    assert_true(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_NOT_CHECKED,
        "structure-only must not claim Experience reference integrity",
    )
print("PASS 2 [STRUCTURE-ONLY]: duplicate Evidence_ID failed closed.")


# ---------------------------------------------------------------------------
# PASS 3 — STRUCTURE-ONLY: Filename / ID mismatch
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_FAKE_001.json", make_valid_record("WW_FAKE_002"))
    result = validate_evidence_repository_structure(root)
    assert_false(result["valid"], "filename/ID mismatch was accepted")
    assert_true(result["index"] is None, "trusted index returned despite mismatch")
    assert_true(
        "EVIDENCE_FILENAME_ID_MISMATCH" in error_codes(result),
        f"missing EVIDENCE_FILENAME_ID_MISMATCH: {result['errors']}",
    )
print("PASS 3 [STRUCTURE-ONLY]: filename/Evidence_ID mismatch failed closed.")


# ---------------------------------------------------------------------------
# PASS 4 — STRUCTURE-ONLY: Invalid evidence state (schema)
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_record("WW_STATE_001")
    bad["evidence_state"] = "PROBABLE"
    write_json(root / "WW_STATE_001.json", bad)
    result = validate_evidence_repository_structure(root)
    assert_false(result["valid"], "PROBABLE evidence_state was accepted")
    assert_true(result["index"] is None, "trusted index returned for schema-invalid state")
    assert_true(
        "EVIDENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing EVIDENCE_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 4 [STRUCTURE-ONLY]: invalid evidence_state failed via canonical schema.")


# ---------------------------------------------------------------------------
# PASS 5 — STRUCTURE-ONLY: Missing required field
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_record("WW_MISS_001")
    del bad["fact"]
    write_json(root / "WW_MISS_001.json", bad)
    result = validate_evidence_repository_structure(root)
    assert_false(result["valid"], "missing required field was accepted")
    assert_true(result["index"] is None, "trusted index returned for missing field")
    assert_true(
        "EVIDENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing EVIDENCE_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 5 [STRUCTURE-ONLY]: missing required field failed closed.")


# ---------------------------------------------------------------------------
# PASS 6 — STRUCTURE-ONLY: Additional forbidden property
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_record("WW_EXTRA_001")
    bad["invented_field"] = "should_be_rejected"
    write_json(root / "WW_EXTRA_001.json", bad)
    result = validate_evidence_repository_structure(root)
    assert_false(result["valid"], "additionalProperties violation was accepted")
    assert_true(result["index"] is None, "trusted index returned for extra property")
    assert_true(
        "EVIDENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing EVIDENCE_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 6 [STRUCTURE-ONLY]: additional forbidden property failed closed.")


# ---------------------------------------------------------------------------
# PASS 7 — STRUCTURE-ONLY: Malformed JSON
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_BADJSON_001.json", '{"evidence_id": "WW_BADJSON_001",')
    result = validate_evidence_repository_structure(root)
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
print("PASS 7 [STRUCTURE-ONLY]: malformed JSON failed closed with file identity.")


# ---------------------------------------------------------------------------
# PASS 8 — STRUCTURE-ONLY: Non-object JSON root
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "WW_ARRAY_001.json", [])
    result = validate_evidence_repository_structure(root)
    assert_false(result["valid"], "array root was accepted")
    assert_true(result["index"] is None, "trusted index returned for non-object root")
    assert_true(
        "EVIDENCE_UNSUPPORTED_RECORD_SHAPE" in error_codes(result),
        f"missing EVIDENCE_UNSUPPORTED_RECORD_SHAPE: {result['errors']}",
    )
print("PASS 8 [STRUCTURE-ONLY]: non-object JSON root failed closed.")


# ---------------------------------------------------------------------------
# PASS 9 — AUTHORITATIVE: Deterministic discovery / index ordering
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = write_temp_experience_root(base)
    root = base / "evidence"
    for evidence_id in ["WW_Z_001", "WW_M_001", "WW_A_001"]:
        write_json(root / f"{evidence_id}.json", make_valid_record(evidence_id))
    first = validate_evidence_repository(root, experience_root=exp_root)
    second = validate_evidence_repository(root, experience_root=exp_root)
    assert_true(first["valid"] and second["valid"], "deterministic fixture failed validation")
    assert_true(
        list(first["index"].keys()) == ["WW_A_001", "WW_M_001", "WW_Z_001"],
        f"index key order not deterministic sorted: {list(first['index'].keys())}",
    )
    assert_true(
        first["discovered_paths"] == second["discovered_paths"],
        "discovered_paths not stable across runs",
    )
    discovered = discover_evidence_files(root)
    assert_true(
        [path.name for path in discovered] == ["WW_A_001.json", "WW_M_001.json", "WW_Z_001.json"],
        f"discovery order not deterministic: {[path.name for path in discovered]}",
    )
    assert_true(
        first["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
        "authoritative success must report ENFORCED",
    )
print("PASS 9 [AUTHORITATIVE]: deterministic discovery and index ordering.")


# ---------------------------------------------------------------------------
# PASS 10 — STRUCTURE-ONLY: Fail-closed index with partial invalid set
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for i in range(1, 12):
        evidence_id = f"WW_OK_{i:03d}"
        write_json(root / f"{evidence_id}.json", make_valid_record(evidence_id))
    bad = make_valid_record("WW_BAD_001")
    bad["evidence_state"] = "PROBABLE"
    write_json(root / "WW_BAD_001.json", bad)
    result = validate_evidence_repository_structure(root)
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
print("PASS 10 [STRUCTURE-ONLY]: fail-closed — no partial trusted index.")


# ---------------------------------------------------------------------------
# PASS 11 — Existing claim validators remain unchanged
# ---------------------------------------------------------------------------
print("PASS 11: deferred to existing claim validation suites (run separately).")


# ---------------------------------------------------------------------------
# PASS 12 — STATUS: authoritative ENFORCED vs structure-only NOT_CHECKED
# ---------------------------------------------------------------------------
assert_true(
    EXPERIENCE_REFERENCE_STATUS == "EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED",
    "experience reference status constant drifted",
)
assert_true(
    real["experience_registry_status"] == "EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED",
    "authoritative Evidence validation does not report Experience reference integrity",
)
structure_only = validate_evidence_repository_structure(EVIDENCE_ROOT)
assert_true(
    structure_only["valid"] is True,
    "structure-only validation unexpectedly failed on real evidence",
)
assert_true(
    structure_only["experience_registry_status"] == EXPERIENCE_REFERENCE_NOT_CHECKED,
    "structure-only falsely advertised Experience reference integrity",
)
assert_false(
    structure_only["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
    "structure-only must never equal ENFORCED",
)
print(
    "PASS 12 [STATUS]: authoritative ENFORCED; structure-only NOT_CHECKED."
)


# ---------------------------------------------------------------------------
# PASS 13 — STRUCTURE-ONLY: Duplicate JSON object key
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    duplicate_state_json = """{
  "evidence_id": "WW_DUPKEY_001",
  "experience_id": "EXP_TEST_001",
  "fact": "Synthetic record with duplicate evidence_state key.",
  "capabilities": ["data analysis"],
  "technologies": ["SQL"],
  "evidence_state": "CONTRADICTED",
  "evidence_state": "VERIFIED",
  "original_source": "synthetic-fixture://evidence/WW_DUPKEY_001",
  "source_location": "tests/evidence_repository_test.py",
  "safe_for_external_use": false,
  "notes": null
}
"""
    write_json(root / "WW_DUPKEY_001.json", duplicate_state_json)
    result = validate_evidence_repository_structure(root)
    assert_false(result["valid"], "duplicate JSON key was accepted")
    assert_true(result["index"] is None, "trusted index returned despite duplicate JSON key")
    assert_true(
        "EVIDENCE_JSON_DUPLICATE_KEY" in error_codes(result),
        f"missing EVIDENCE_JSON_DUPLICATE_KEY: {result['errors']}",
    )
print("PASS 13 [STRUCTURE-ONLY]: duplicate JSON object key failed closed.")


# ---------------------------------------------------------------------------
# PASS 14 — AUTHORITATIVE: Empty evidence + empty Experience registry
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    exp_root.mkdir()
    ev_root.mkdir()
    result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_true(result["valid"] is True, "empty evidence root was not structurally valid")
    assert_true(result["records_checked"] == 0, "empty root should check zero records")
    assert_true(result["index"] == {}, f"expected empty trusted index, got {result['index']!r}")
    assert_true(result["errors"] == [], f"unexpected errors for empty root: {result['errors']}")
    assert_true(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
        "empty authoritative success must still report ENFORCED",
    )
print("PASS 14 [AUTHORITATIVE]: empty evidence repository policy locked.")


# ---------------------------------------------------------------------------
# PASS 15 — AUTHORITATIVE failure status is not ENFORCED
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = write_temp_experience_root(base)
    ev_root = base / "evidence"
    record = make_valid_record("WW_MISSREF_001")
    record["experience_id"] = "EXP_DOES_NOT_EXIST"
    write_json(ev_root / "WW_MISSREF_001.json", record)
    result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_false(result["valid"], "missing Experience reference was accepted")
    assert_true(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_CHECK_FAILED,
        "authoritative failure must not advertise ENFORCED",
    )
print("PASS 15 [STATUS]: authoritative failure uses CHECK_FAILED, not ENFORCED.")


print("PASS: evidence repository integrity tests completed successfully.")
