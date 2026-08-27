"""Adversarial trust-boundary tests for Experience → Evidence integrity."""

from __future__ import annotations

import inspect
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
    EXPERIENCE_REFERENCE_CHECK_FAILED,
    EXPERIENCE_REFERENCE_NOT_CHECKED,
    EXPERIENCE_REFERENCE_STATUS,
    validate_evidence_repository,
    validate_evidence_repository_structure,
)
from experience_repository import (  # noqa: E402
    ValidatedExperienceRepository,
    validate_experience_repository,
)


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
        "fact": f"Synthetic trust-boundary fact for {evidence_id}.",
        "capabilities": ["data analysis"],
        "technologies": ["SQL"],
        "evidence_state": "SUPPORTED",
        "original_source": f"synthetic-fixture://evidence/{evidence_id}",
        "source_location": "tests/experience_trust_boundary_test.py",
        "safe_for_external_use": False,
        "notes": None,
    }


def make_valid_experience(experience_id: str) -> dict:
    return {
        "experience_id": experience_id,
        "experience_name": f"Synthetic {experience_id}",
        "experience_type": "OTHER",
        "organization": "Synthetic Org",
        "source_of_truth": "tests/experience_trust_boundary_test.py",
    }


def error_codes(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


# ---------------------------------------------------------------------------
# TRUST TEST 1 — bare dict / raw index is not a public bypass
# ---------------------------------------------------------------------------
sig = inspect.signature(validate_evidence_repository)
assert_false(
    "experience_index" in sig.parameters,
    "public API still exposes experience_index raw-index bypass",
)
assert_true(
    "experience_result" in sig.parameters,
    "public API missing experience_result parameter",
)

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    write_json(exp_root / "EXP_OK_001.json", make_valid_experience("EXP_OK_001"))
    write_json(
        ev_root / "WW_FAKE_001.json",
        make_valid_evidence("WW_FAKE_001", "EXP_FAKE_001"),
    )
    fake_index = {
        "EXP_FAKE_001": {
            "experience_id": "EXP_FAKE_001",
        }
    }
    # Calling with removed parameter must TypeError; also reject dict as result.
    try:
        validate_evidence_repository(ev_root, experience_index=fake_index)  # type: ignore[call-arg]
        raise SystemExit("FAIL: experience_index keyword was accepted")
    except TypeError:
        pass

    result = validate_evidence_repository(ev_root, experience_result=fake_index)  # type: ignore[arg-type]
    assert_false(result["valid"], "raw Mapping was accepted as trusted Experience result")
    assert_true(result["index"] is None, "trusted Evidence index returned for raw Mapping")
    assert_true(
        "EXPERIENCE_REGISTRY_INVALID" in error_codes(result),
        f"expected EXPERIENCE_REGISTRY_INVALID: {result['errors']}",
    )
    assert_true(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_CHECK_FAILED,
        "raw Mapping path must not advertise ENFORCED",
    )
print("TRUST TEST 1: bare dict / raw index bypass rejected.")


# ---------------------------------------------------------------------------
# TRUST TEST 2 — malformed / fake validation-result shapes rejected
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    write_json(exp_root / "EXP_OK_001.json", make_valid_experience("EXP_OK_001"))
    write_json(ev_root / "WW_OK_001.json", make_valid_evidence("WW_OK_001", "EXP_OK_001"))

    spoofed_shapes = [
        {"valid": True, "index": {"EXP_OK_001": make_valid_experience("EXP_OK_001")}, "errors": []},
        {"valid": False, "index": {"EXP_OK_001": make_valid_experience("EXP_OK_001")}, "errors": []},
        {"valid": True, "index": None, "errors": []},
        {"valid": True, "index": ["not", "a", "mapping"], "errors": []},
        {"valid": True, "index": {"EXP_OK_001": make_valid_experience("EXP_OK_001")}, "errors": [{"code": "X"}]},
    ]
    for spoof in spoofed_shapes:
        result = validate_evidence_repository(ev_root, experience_result=spoof)  # type: ignore[arg-type]
        assert_false(result["valid"], f"spoofed result accepted: {spoof!r}")
        assert_true(result["index"] is None, f"trusted index for spoof: {spoof!r}")
        assert_true(
            "EXPERIENCE_REGISTRY_INVALID" in error_codes(result),
            f"missing EXPERIENCE_REGISTRY_INVALID for spoof {spoof!r}: {result['errors']}",
        )

    # Direct construction of ValidatedExperienceRepository must fail.
    try:
        ValidatedExperienceRepository({"valid": True, "index": {}, "errors": []})
        raise SystemExit("FAIL: ValidatedExperienceRepository public construction succeeded")
    except TypeError:
        pass

print("TRUST TEST 2: malformed/fake validation results rejected.")


# ---------------------------------------------------------------------------
# TRUST TEST 3 — genuine validated Experience result works
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    write_json(exp_root / "EXP_OK_001.json", make_valid_experience("EXP_OK_001"))
    write_json(ev_root / "WW_OK_001.json", make_valid_evidence("WW_OK_001", "EXP_OK_001"))
    genuine = validate_experience_repository(exp_root)
    assert_true(isinstance(genuine, ValidatedExperienceRepository), "expected opaque result type")
    assert_true(genuine.valid is True, "fixture Experience Registry invalid")
    result = validate_evidence_repository(ev_root, experience_result=genuine)
    assert_true(result["valid"] is True, "genuine Experience result failed Evidence validation")
    assert_true(result["index"] is not None and "WW_OK_001" in result["index"], "missing Evidence index")
    assert_true(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
        "genuine reuse must report ENFORCED",
    )
print("TRUST TEST 3: genuine ValidatedExperienceRepository reuse works.")


# ---------------------------------------------------------------------------
# TRUST TEST 4 — fake Experience still cannot be minted
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    write_json(exp_root / "EXP_OK_001.json", make_valid_experience("EXP_OK_001"))
    write_json(
        ev_root / "WW_FAKE_001.json",
        make_valid_evidence("WW_FAKE_001", "EXP_FAKE_001"),
    )
    result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_false(result["valid"], "EXP_FAKE_001 was accepted")
    assert_true(result["index"] is None, "trusted Evidence index returned for fake Experience")
    assert_true(
        "EXPERIENCE_ID_NOT_FOUND" in error_codes(result),
        f"missing EXPERIENCE_ID_NOT_FOUND: {result['errors']}",
    )
    assert_true(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_CHECK_FAILED,
        "fake Experience failure must not advertise ENFORCED",
    )
print("TRUST TEST 4: EXP_FAKE_001 cannot be minted.")


# ---------------------------------------------------------------------------
# STATUS TEST 1 — structure-only
# ---------------------------------------------------------------------------
structure = validate_evidence_repository_structure(EVIDENCE_ROOT)
assert_true(structure["valid"] is True, "structure-only failed on real evidence")
assert_true(
    structure["experience_registry_status"] == EXPERIENCE_REFERENCE_NOT_CHECKED,
    f"structure-only status wrong: {structure['experience_registry_status']}",
)
assert_false(
    structure["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
    "structure-only advertised ENFORCED",
)
print("STATUS TEST 1: structure-only reports EXPERIENCE_REFERENCE_NOT_CHECKED.")


# ---------------------------------------------------------------------------
# STATUS TEST 2 — authoritative success
# ---------------------------------------------------------------------------
authoritative = validate_evidence_repository(EVIDENCE_ROOT, experience_root=EXPERIENCE_ROOT)
assert_true(authoritative["valid"] is True, "authoritative real repositories failed")
assert_true(
    authoritative["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
    f"authoritative success status wrong: {authoritative['experience_registry_status']}",
)
print("STATUS TEST 2: authoritative success reports EXPERIENCE_REFERENCE_INTEGRITY_ENFORCED.")


# ---------------------------------------------------------------------------
# STATUS TEST 3 — authoritative failure does not advertise ENFORCED
# ---------------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    exp_root = base / "experiences"
    ev_root = base / "evidence"
    bad = make_valid_experience("EXP_BAD_001")
    bad["experience_type"] = "ORGANIZATIONAL_PROJECT"
    write_json(exp_root / "EXP_BAD_001.json", bad)
    write_json(ev_root / "WW_OK_001.json", make_valid_evidence("WW_OK_001", "EXP_BAD_001"))
    result = validate_evidence_repository(ev_root, experience_root=exp_root)
    assert_false(result["valid"], "invalid Experience Registry still trusted Evidence")
    assert_true(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_CHECK_FAILED,
        f"authoritative failure status wrong: {result['experience_registry_status']}",
    )
    assert_false(
        result["experience_registry_status"] == EXPERIENCE_REFERENCE_STATUS,
        "authoritative failure advertised ENFORCED",
    )
print("STATUS TEST 3: authoritative failure does not advertise ENFORCED.")


print("PASS: experience trust-boundary tests completed successfully.")
