import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
FIXTURES = ROOT / "fixtures" / "resume_architecture"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from resume_digest import compute_derivative_validation_digest  # noqa: E402
from schema_validation import build_draft202012_validator  # noqa: E402


MODULE_SCHEMA = ROOT / "schemas" / "resume_module.schema.json"
MASTER_SCHEMA = ROOT / "schemas" / "resume_master.schema.json"
PATCH_SCHEMA = ROOT / "schemas" / "resume_patch.schema.json"
DERIVATIVE_SCHEMA = ROOT / "schemas" / "resume_derivative.schema.json"

module_validator = build_draft202012_validator(MODULE_SCHEMA)
master_validator = build_draft202012_validator(MASTER_SCHEMA)
patch_validator = build_draft202012_validator(PATCH_SCHEMA)
derivative_validator = build_draft202012_validator(DERIVATIVE_SCHEMA)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


master = json.loads((FIXTURES / "synthetic_master.json").read_text(encoding="utf-8"))

valid_module = master["modules"][0]
invalid_module_missing_claims = valid_module.copy()
invalid_module_missing_claims["module_id"] = "MOD_INVALID_NO_CLAIMS"
del invalid_module_missing_claims["claim_ids"]

valid_patch = {
    "patch_id": "PATCH_SMOKE_001",
    "target_master_id": master["master_id"],
    "operations": [
        {"op": "EXCLUDE_MODULE", "module_id": "MOD_OPTIONAL_ARCHIVE"},
        {"op": "REORDER_SKILLS", "skills": ["process mapping", "Google Workspace"]},
    ],
}

invalid_patch_unknown_op = {
    "patch_id": "PATCH_SMOKE_BAD",
    "target_master_id": master["master_id"],
    "operations": [{"op": "SET_FORMAL_TITLE", "formal_title": "CEO"}],
}

valid_derivative = {
    "derivative_id": "DERIV_SMOKE_001",
    "master_id": master["master_id"],
    "master_version": master["version"],
    "patch_id": valid_patch["patch_id"],
    "module_order": master["default_module_order"],
    "included_module_ids": master["default_module_order"],
    "excluded_module_ids": [],
    "skills_order": master["skills_order"],
    "modules": master["modules"],
    "experience_sections": master["experience_sections"],
    "contact": master["contact"],
    "education": master.get("education", []),
    "diff": [
        {
            "change_type": "UNCHANGED",
            "target": "derivative",
            "detail": "smoke fixture",
        }
    ],
    "review_status": "HUMAN_REVIEW_REQUIRED",
    "export_allowed": False,
}
valid_derivative["validation_digest"] = compute_derivative_validation_digest(valid_derivative)

assert_true(module_validator.is_valid(valid_module), "valid module should pass schema")
assert_false(
    module_validator.is_valid(invalid_module_missing_claims),
    "module without claim_ids should fail schema",
)
assert_true(master_validator.is_valid(master), "synthetic master should pass schema")
assert_true(patch_validator.is_valid(valid_patch), "valid patch should pass schema")
assert_false(
    patch_validator.is_valid(invalid_patch_unknown_op),
    "unknown patch op should fail schema",
)
assert_true(
    derivative_validator.is_valid(valid_derivative),
    "valid derivative should pass schema",
)

print("PASS: resume schema smoke tests.")
