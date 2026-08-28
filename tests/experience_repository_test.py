"""Deterministic tests for Experience Registry integrity."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
EXPERIENCE_ROOT = ROOT / "experiences"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from experience_repository import (  # noqa: E402
    discover_experience_files,
    validate_experience_repository,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def make_valid_experience(experience_id: str) -> dict:
    return {
        "experience_id": experience_id,
        "experience_name": f"Synthetic {experience_id}",
        "experience_type": "OTHER",
        "organization": "Synthetic Org",
        "source_of_truth": "tests/experience_repository_test.py",
        "notes": None,
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def error_codes(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


# ---------------------------------------------------------------------------
# PASS 1 — Real Experience Registry
# ---------------------------------------------------------------------------
real = validate_experience_repository(EXPERIENCE_ROOT)
assert_true(real["valid"] is True, "real Experience Registry failed")
assert_true(real["records_checked"] == 2, f"expected 2 records, got {real['records_checked']}")
assert_true(real["index"] is not None, "trusted Experience index missing")
assert_true(
    list(real["index"].keys()) == ["EXP_MM_001", "EXP_WW_001"],
    f"unexpected Experience_ID set: {list(real['index'].keys())}",
)
assert_true(
    real["index"]["EXP_WW_001"]["experience_type"] == "ORGANIZATIONAL_ENGAGEMENT",
    "EXP_WW_001 experience_type mismatch",
)
print("PASS 1: real Experience Registry (EXP_MM_001, EXP_WW_001) passed.")


# ---------------------------------------------------------------------------
# PASS 2 — Duplicate Experience_ID
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "EXP_DUP_001.json", make_valid_experience("EXP_DUP_001"))
    write_json(root / "subdir" / "EXP_DUP_001.json", make_valid_experience("EXP_DUP_001"))
    result = validate_experience_repository(root)
    assert_false(result["valid"], "duplicate Experience_ID was accepted")
    assert_true(result["index"] is None, "trusted index returned despite duplicate ID")
    assert_true(
        "DUPLICATE_EXPERIENCE_ID" in error_codes(result),
        f"missing DUPLICATE_EXPERIENCE_ID: {result['errors']}",
    )
print("PASS 2: duplicate Experience_ID failed closed.")


# ---------------------------------------------------------------------------
# PASS 3 — Filename / ID mismatch
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "EXP_FAKE_001.json", make_valid_experience("EXP_FAKE_002"))
    result = validate_experience_repository(root)
    assert_false(result["valid"], "filename/ID mismatch was accepted")
    assert_true(result["index"] is None, "trusted index returned despite mismatch")
    assert_true(
        "EXPERIENCE_FILENAME_ID_MISMATCH" in error_codes(result),
        f"missing EXPERIENCE_FILENAME_ID_MISMATCH: {result['errors']}",
    )
print("PASS 3: filename/Experience_ID mismatch failed closed.")


# ---------------------------------------------------------------------------
# PASS 4 — Schema-invalid Experience
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_experience("EXP_TYPE_001")
    bad["experience_type"] = "ORGANIZATIONAL_PROJECT"
    write_json(root / "EXP_TYPE_001.json", bad)
    result = validate_experience_repository(root)
    assert_false(result["valid"], "invalid experience_type was accepted")
    assert_true(result["index"] is None, "trusted index returned for schema-invalid")
    assert_true(
        "EXPERIENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing EXPERIENCE_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 4: schema-invalid Experience failed via canonical schema.")


# ---------------------------------------------------------------------------
# PASS 5 — Malformed JSON
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "EXP_BADJSON_001.json", '{"experience_id": "EXP_BADJSON_001",')
    result = validate_experience_repository(root)
    assert_false(result["valid"], "malformed JSON was accepted")
    assert_true(result["index"] is None, "trusted index returned for malformed JSON")
    assert_true(
        "EXPERIENCE_JSON_PARSE_ERROR" in error_codes(result),
        f"missing EXPERIENCE_JSON_PARSE_ERROR: {result['errors']}",
    )
print("PASS 5: malformed JSON failed closed.")


# ---------------------------------------------------------------------------
# PASS 6 — Duplicate JSON key (non-identity field)
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    duplicate_json = """{
  "experience_id": "EXP_DUPKEY_001",
  "experience_name": "Dup Key",
  "experience_type": "OTHER",
  "experience_type": "EMPLOYMENT",
  "organization": "Synthetic Org",
  "source_of_truth": "tests/experience_repository_test.py",
  "notes": null
}
"""
    write_json(root / "EXP_DUPKEY_001.json", duplicate_json)
    result = validate_experience_repository(root)
    assert_false(result["valid"], "duplicate JSON key was accepted")
    assert_true(result["index"] is None, "trusted index returned despite duplicate key")
    assert_true(
        "EXPERIENCE_JSON_DUPLICATE_KEY" in error_codes(result),
        f"missing EXPERIENCE_JSON_DUPLICATE_KEY: {result['errors']}",
    )
    assert_true(
        any(
            error.get("code") == "EXPERIENCE_JSON_DUPLICATE_KEY"
            and error.get("key") == "experience_type"
            for error in result["errors"]
        ),
        f"duplicate key not identified: {result['errors']}",
    )
print("PASS 6: duplicate JSON object key failed closed.")


# ---------------------------------------------------------------------------
# PASS 7 — Non-object root
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "EXP_ARRAY_001.json", [])
    result = validate_experience_repository(root)
    assert_false(result["valid"], "array root was accepted")
    assert_true(result["index"] is None, "trusted index returned for non-object root")
    assert_true(
        "EXPERIENCE_UNSUPPORTED_RECORD_SHAPE" in error_codes(result),
        f"missing EXPERIENCE_UNSUPPORTED_RECORD_SHAPE: {result['errors']}",
    )
print("PASS 7: non-object JSON root failed closed.")


# ---------------------------------------------------------------------------
# PASS 8 — Empty Experience Registry
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    result = validate_experience_repository(root)
    assert_true(result["valid"] is True, "empty Experience root was not structurally valid")
    assert_true(result["records_checked"] == 0, "empty root should check zero records")
    assert_true(result["index"] == {}, f"expected empty trusted index, got {result['index']!r}")
    assert_true(result["errors"] == [], f"unexpected errors: {result['errors']}")
print("PASS 8: empty Experience Registry policy locked.")


# ---------------------------------------------------------------------------
# PASS 9 — Missing root
# ---------------------------------------------------------------------------
missing = Path(tempfile.gettempdir()) / "bora_experience_root_does_not_exist_xyz"
if missing.exists():
    # Extremely unlikely; fail loudly if collision.
    raise SystemExit(f"FAIL: unexpected existing path {missing}")
result = validate_experience_repository(missing)
assert_false(result["valid"], "missing Experience root was accepted")
assert_true(result["index"] is None, "trusted index returned for missing root")
assert_true(
    "EXPERIENCE_ROOT_MISSING" in error_codes(result),
    f"missing EXPERIENCE_ROOT_MISSING: {result['errors']}",
)
print("PASS 9: missing Experience root failed closed.")


# ---------------------------------------------------------------------------
# PASS 10 — Root-is-file
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root_file = Path(tmp) / "not_a_directory.json"
    root_file.write_text("{}", encoding="utf-8")
    result = validate_experience_repository(root_file)
    assert_false(result["valid"], "file Experience root was accepted")
    assert_true(result["index"] is None, "trusted index returned for file root")
    assert_true(
        "EXPERIENCE_ROOT_NOT_DIRECTORY" in error_codes(result),
        f"missing EXPERIENCE_ROOT_NOT_DIRECTORY: {result['errors']}",
    )
print("PASS 10: Experience root-is-file failed closed.")


# ---------------------------------------------------------------------------
# PASS 11 — Deterministic ordering
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for experience_id in ["EXP_Z_001", "EXP_M_001", "EXP_A_001"]:
        write_json(root / f"{experience_id}.json", make_valid_experience(experience_id))
    first = validate_experience_repository(root)
    second = validate_experience_repository(root)
    assert_true(first["valid"] and second["valid"], "deterministic fixture failed")
    assert_true(
        list(first["index"].keys()) == ["EXP_A_001", "EXP_M_001", "EXP_Z_001"],
        f"index key order not sorted: {list(first['index'].keys())}",
    )
    assert_true(
        first["discovered_paths"] == second["discovered_paths"],
        "discovered_paths not stable",
    )
    discovered = discover_experience_files(root)
    assert_true(
        [path.name for path in discovered]
        == ["EXP_A_001.json", "EXP_M_001.json", "EXP_Z_001.json"],
        f"discovery order not deterministic: {[path.name for path in discovered]}",
    )
print("PASS 11: deterministic discovery and index ordering.")


# ---------------------------------------------------------------------------
# PASS 12 — Fail-closed index
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "EXP_OK_001.json", make_valid_experience("EXP_OK_001"))
    bad = make_valid_experience("EXP_BAD_001")
    bad["experience_type"] = "ORGANIZATIONAL_PROJECT"
    write_json(root / "EXP_BAD_001.json", bad)
    result = validate_experience_repository(root)
    assert_false(result["valid"], "mixed valid/invalid Experience registry accepted")
    assert_true(result["index"] is None, "partial trusted Experience index leaked")
    assert_true(
        "EXPERIENCE_SCHEMA_INVALID" in error_codes(result),
        f"missing schema error: {result['errors']}",
    )
print("PASS 12: fail-closed — no partial trusted Experience index.")


print("PASS: experience repository integrity tests completed successfully.")
