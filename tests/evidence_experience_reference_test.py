"""Deterministic tests for Evidence -> Experience referential integrity."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
EVIDENCE_ROOT = ROOT / "evidence"
EXPERIENCE_ROOT = ROOT / "experiences"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from evidence_repository import (  # noqa: E402
    EXPERIENCE_REFERENCE_STATUS,
    validate_evidence_repository,
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
    "WW_SYNC_001",
    "WW_TEST_001",
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_valid_evidence(evidence_id: str, experience_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "experience_id": experience_id,
        "fact": f"Synthetic referential integrity fact for {evidence_id}.",
        "capabilities": ["data analysis"],
        "technologies": ["SQL"],
        "evidence_state": "SUPPORTED",
        "original_source": f"synthetic-fixture://evidence/{evidence_id}",
        "source_location": "tests/evidence_experience_reference_test.py",
        "safe_for_external_use": False,
        "notes": None,
    }


def make_valid_experience(experience_id: str) -> dict:
    return {
        "experience_id": experience_id,
        "experience_name": f"Synthetic {experience_id}",
        "experience_type": "OTHER",
        "organization": "Synthetic Org",
        "source_of_truth": "tests/evidence_experience_reference_test.py",
    }


def error_codes(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# REF PASS 1 — Real 12 evidence + trusted EXP_WW_001 registry
# ---------------------------------------------------------------------------
exp = validate_experience_repository(EXPERIENCE_ROOT)
assert_true(exp["valid"] is True, "real Experience Registry must be valid for REF PASS 1")
evidence = validate_evidence_repository(EVIDENCE_ROOT, experience_root=EXPERIENCE_ROOT)
assert_true(evidence["valid"] is True, "real Evidence Repository failed with Experience refs")
assert_true(evidence["records_checked"] == 12, f"expected 12 evidence, got {evidence['records_checked']}")
assert_true(evidence["index"] is not None, "trusted Evidence index missing")
assert_true(len(evidence["index"]) == 12, f"trusted Evidence index length {len(evidence['index'])}")
assert_true(
    sorted(evidence["index"].keys()) == EXPECTED_WW_IDS,
    f"unexpected Evidence_ID set: {sorted(evidence['index'].keys())}",
)
assert_true(
    evidence["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
    "experience_registry_status mismatch",
)
print("REF PASS 1: real Evidence + Experience referential integrity passed.")


# ---------------------------------------------------------------------------
# REF PASS 2 — Evidence references nonexistent Experience_ID
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    write_json(exp_root / "EXP_OK_001.json", make_valid_experience("EXP_OK_001"))
    write_json(
        ev_root / "WW_MISSING_001.json",
        make_valid_evidence("WW_MISSING_001", "EXP_DOES_NOT_EXIST"),
    )
    result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_false(result["valid"], "missing Experience_ID was accepted")
    assert_true(result["index"] is None, "trusted Evidence index returned despite missing Experience")
    assert_true(
        "EXPERIENCE_ID_NOT_FOUND" in error_codes(result),
        f"missing EXPERIENCE_ID_NOT_FOUND: {result['errors']}",
    )
    assert_true(
        any(
            error.get("code") == "EXPERIENCE_ID_NOT_FOUND"
            and error.get("experience_id") == "EXP_DOES_NOT_EXIST"
            and error.get("path") == "WW_MISSING_001.json"
            for error in result["errors"]
        ),
        f"missing Experience_ID details incomplete: {result['errors']}",
    )
print("REF PASS 2: nonexistent Experience_ID failed closed.")


# ---------------------------------------------------------------------------
# REF PASS 3 — Experience Registry structurally invalid
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    bad_exp = make_valid_experience("EXP_BAD_001")
    bad_exp["experience_type"] = "ORGANIZATIONAL_PROJECT"
    write_json(exp_root / "EXP_BAD_001.json", bad_exp)
    write_json(ev_root / "WW_OK_001.json", make_valid_evidence("WW_OK_001", "EXP_BAD_001"))
    result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_false(result["valid"], "invalid Experience Registry still produced Evidence trust")
    assert_true(result["index"] is None, "trusted Evidence index returned with invalid Experience Registry")
    assert_true(
        "EXPERIENCE_REGISTRY_INVALID" in error_codes(result),
        f"missing EXPERIENCE_REGISTRY_INVALID: {result['errors']}",
    )
    assert_false(
        "EXPERIENCE_ID_NOT_FOUND" in error_codes(result),
        "registry invalidity should not be reported as per-record EXPERIENCE_ID_NOT_FOUND",
    )
print("REF PASS 3: invalid Experience Registry blocks Evidence trusted index.")


# ---------------------------------------------------------------------------
# REF PASS 4 — Empty Experience Registry + evidence referencing EXP_WW_001
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    exp_root.mkdir()
    write_json(ev_root / "WW_REF_001.json", make_valid_evidence("WW_REF_001", "EXP_WW_001"))
    result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_false(result["valid"], "empty Experience Registry accepted evidence references")
    assert_true(result["index"] is None, "trusted Evidence index returned against empty Experience Registry")
    assert_true(
        "EXPERIENCE_ID_NOT_FOUND" in error_codes(result),
        f"expected EXPERIENCE_ID_NOT_FOUND against empty registry: {result['errors']}",
    )
print("REF PASS 4: empty Experience Registry + referencing evidence failed closed.")


# ---------------------------------------------------------------------------
# REF PASS 5 — Empty Experience + empty Evidence
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    exp_root.mkdir()
    ev_root.mkdir()
    exp_result = validate_experience_repository(exp_root)
    ev_result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_true(exp_result["valid"] is True, "empty Experience Registry not structurally valid")
    assert_true(exp_result["index"] == {}, "empty Experience index should be {}")
    assert_true(ev_result["valid"] is True, "empty Evidence + empty Experience not structurally valid")
    assert_true(ev_result["index"] == {}, "empty Evidence index should be {}")
    assert_true(ev_result["errors"] == [], f"unexpected Evidence errors: {ev_result['errors']}")
print("REF PASS 5: empty Experience + empty Evidence structurally valid.")


# ---------------------------------------------------------------------------
# REF PASS 6 — Current real 12 evidence records remain byte-unchanged
# ---------------------------------------------------------------------------
# Capture hashes now; this test locks the milestone invariant that wiring
# did not rewrite committed Winter Walk evidence files.
expected_hashes = {
    "WW_ADOPT_001.json": None,
    "WW_ARCH_001.json": None,
    "WW_ARCH_002.json": None,
    "WW_CONN_001.json": None,
    "WW_CTRL_001.json": None,
    "WW_CTRL_002.json": None,
    "WW_DATA_001.json": None,
    "WW_DATA_002.json": None,
    "WW_FUQ_001.json": None,
    "WW_MAP_001.json": None,
    "WW_SYNC_001.json": None,
    "WW_TEST_001.json": None,
}
ww_dir = EVIDENCE_ROOT / "winter_walk"
for name in expected_hashes:
    path = ww_dir / name
    assert_true(path.is_file(), f"missing committed evidence file: {path}")
    digest = sha256_file(path)
    expected_hashes[name] = digest
    text = path.read_text(encoding="utf-8")
    assert_true('"experience_id": "EXP_WW_001"' in text, f"{name} missing EXP_WW_001")

# Re-hash immediately (same process) — guards against in-suite mutation.
for name, digest in expected_hashes.items():
    assert_true(
        sha256_file(ww_dir / name) == digest,
        f"evidence file mutated during referential tests: {name}",
    )
print("REF PASS 6: committed Winter Walk evidence files remain byte-unchanged in-suite.")


print("PASS: evidence-experience referential integrity tests completed successfully.")
