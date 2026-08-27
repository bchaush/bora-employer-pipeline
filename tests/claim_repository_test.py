"""Deterministic tests for Claim Bank repository identity integrity."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
CLAIMS_ROOT = ROOT / "claims"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import (  # noqa: E402
    discover_claim_files,
    validate_claim_repository,
)


EXPECTED_CLAIM_IDS = [
    "CLAIM_WW_001",
    "CLAIM_WW_002",
    "CLAIM_WW_003",
    "CLAIM_WW_004",
    "CLAIM_WW_005",
    "CLAIM_WW_006",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def error_codes(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


def make_valid_claim(claim_id: str) -> dict:
    return {
        "claim_id": claim_id,
        "wording": f"Synthetic claim wording for {claim_id}.",
        "evidence_ids": ["WW_ARCH_001"],
        "evidence_state": "SUPPORTED",
        "allowed_contexts": ["resume"],
        "forbidden_contexts": ["production ML"],
        "human_approval": False,
        "date": "2026-08-26",
        "version": "1",
    }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# PASS 1 — valid real repository
# ---------------------------------------------------------------------------
real = validate_claim_repository(CLAIMS_ROOT)
assert_true(real["valid"] is True, f"real claim repository failed: {real['errors']}")
assert_true(real["records_checked"] == 6, f"expected 6 claims, got {real['records_checked']}")
assert_true(real["index"] is not None, "trusted index missing for valid repository")
assert_true(
    sorted(real["index"].keys()) == EXPECTED_CLAIM_IDS,
    f"unexpected Claim_ID set: {sorted(real['index'].keys())}",
)
assert_true(
    len(discover_claim_files(CLAIMS_ROOT)) == 6,
    "discover_claim_files should find 6 claim files",
)
print("PASS 1: valid real Winter Walk claim repository (6 records) passed.")


# ---------------------------------------------------------------------------
# PASS 2 — duplicate Claim_ID
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "CLAIM_DUP_001.json", make_valid_claim("CLAIM_DUP_001"))
    write_json(root / "subdir" / "CLAIM_DUP_001.json", make_valid_claim("CLAIM_DUP_001"))
    result = validate_claim_repository(root)
    assert_false(result["valid"], "duplicate Claim_ID was accepted")
    assert_true(result["index"] is None, "trusted index returned despite duplicate ID")
    assert_true(
        "DUPLICATE_CLAIM_ID" in error_codes(result),
        f"missing DUPLICATE_CLAIM_ID: {result['errors']}",
    )
print("PASS 2: duplicate Claim_ID failed closed.")


# ---------------------------------------------------------------------------
# PASS 3 — filename / Claim_ID mismatch
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "CLAIM_WRONG_NAME.json", make_valid_claim("CLAIM_RIGHT_ID"))
    result = validate_claim_repository(root)
    assert_false(result["valid"], "filename/ID mismatch was accepted")
    assert_true(result["index"] is None, "trusted index returned despite mismatch")
    assert_true(
        "CLAIM_FILENAME_ID_MISMATCH" in error_codes(result),
        f"missing CLAIM_FILENAME_ID_MISMATCH: {result['errors']}",
    )
print("PASS 3: filename / Claim_ID mismatch failed closed.")


# ---------------------------------------------------------------------------
# PASS 4 — malformed JSON
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "CLAIM_BAD_JSON.json", "{not-json")
    result = validate_claim_repository(root)
    assert_false(result["valid"], "malformed JSON was accepted")
    assert_true(result["index"] is None, "trusted index returned despite malformed JSON")
    assert_true(
        "CLAIM_JSON_PARSE_ERROR" in error_codes(result),
        f"missing CLAIM_JSON_PARSE_ERROR: {result['errors']}",
    )
print("PASS 4: malformed JSON failed closed.")


# ---------------------------------------------------------------------------
# PASS 5 — schema-invalid claim
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bad = make_valid_claim("CLAIM_SCHEMA_BAD")
    del bad["wording"]
    write_json(root / "CLAIM_SCHEMA_BAD.json", bad)
    result = validate_claim_repository(root)
    assert_false(result["valid"], "schema-invalid claim was accepted")
    assert_true(result["index"] is None, "trusted index returned despite schema invalid")
    assert_true(
        "CLAIM_SCHEMA_INVALID" in error_codes(result),
        f"missing CLAIM_SCHEMA_INVALID: {result['errors']}",
    )
print("PASS 5: schema-invalid claim failed closed.")


# ---------------------------------------------------------------------------
# PASS 6 — mixed valid + invalid fails closed (no partial index)
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(root / "CLAIM_OK_001.json", make_valid_claim("CLAIM_OK_001"))
    write_json(root / "CLAIM_BAD_JSON.json", "{broken")
    result = validate_claim_repository(root)
    assert_false(result["valid"], "mixed valid+invalid repository was accepted")
    assert_true(result["index"] is None, "partial trusted index must not be returned")
    assert_true(
        "CLAIM_JSON_PARSE_ERROR" in error_codes(result),
        f"expected parse error in mixed repo: {result['errors']}",
    )
print("PASS 6: mixed valid + invalid repository failed closed.")


# ---------------------------------------------------------------------------
# PASS 7 — trusted index contains all five real Claim_IDs
# ---------------------------------------------------------------------------
assert_true(real["index"] is not None, "real index required")
for claim_id in EXPECTED_CLAIM_IDS:
    assert_true(claim_id in real["index"], f"missing {claim_id} in trusted index")
    assert_true(
        real["index"][claim_id]["claim_id"] == claim_id,
        f"index record claim_id mismatch for {claim_id}",
    )
print("PASS 7: trusted index contains all six real Claim_IDs.")


# ---------------------------------------------------------------------------
# PASS 8 — no index returned on invalid repository
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    # Copy one real claim then introduce a duplicate ID file.
    src = CLAIMS_ROOT / "winter_walk" / "CLAIM_WW_001.json"
    shutil.copy(src, root / "CLAIM_WW_001.json")
    write_json(root / "other" / "CLAIM_WW_001.json", make_valid_claim("CLAIM_WW_001"))
    result = validate_claim_repository(root)
    assert_false(result["valid"], "invalid repository unexpectedly valid")
    assert_true(result["index"] is None, "index must be None on invalid repository")
print("PASS 8: no index returned on invalid repository.")


# ---------------------------------------------------------------------------
# PASS 9 — duplicate JSON object keys rejected
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write_json(
        root / "CLAIM_DUP_KEY.json",
        '{\n  "claim_id": "CLAIM_DUP_KEY",\n  "claim_id": "CLAIM_DUP_KEY",\n'
        '  "wording": "x",\n  "evidence_ids": ["WW_ARCH_001"],\n'
        '  "evidence_state": "SUPPORTED",\n'
        '  "allowed_contexts": ["resume"],\n'
        '  "forbidden_contexts": ["production ML"],\n'
        '  "human_approval": false,\n'
        '  "date": "2026-08-26",\n'
        '  "version": "1"\n}\n',
    )
    result = validate_claim_repository(root)
    assert_false(result["valid"], "duplicate JSON keys were accepted")
    assert_true(result["index"] is None, "index must be None on duplicate keys")
    assert_true(
        "CLAIM_JSON_DUPLICATE_KEY" in error_codes(result),
        f"missing CLAIM_JSON_DUPLICATE_KEY: {result['errors']}",
    )
print("PASS 9: duplicate JSON object keys failed closed.")

print("PASS: claim repository integrity tests completed successfully.")
