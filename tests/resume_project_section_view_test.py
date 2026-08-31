"""Bounded tests for the pure project-section view builder
(PROJECT_SECTION_RENDERING_ALGORITHM_V1).

build_project_section_view() is a derived-view function only: it stores
no new truth, adds no schema, and must never invent presentation
metadata. These tests exercise it against the real repository data plus
synthetic, test-only records for grouping/failure-path coverage (no
fake production Evidence/Experience records are created).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
MASTER_PATH = ROOT / "resume" / "master" / "RESUME_MASTER_WW_V1.json"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from claim_repository import validate_claim_repository  # noqa: E402
from evidence_repository import validate_evidence_repository  # noqa: E402
from experience_repository import validate_experience_repository  # noqa: E402
from resume_project_bullet import build_project_section_view  # noqa: E402
from resume_validation import build_resume_derivative  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(len(exp_result["index"]) == 7, "Experience count must be 7 (4 prior + 3 CANDIDATE_SOURCE_INGESTION_V1 records)")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(len(ev_result["index"]) == 42, "Evidence count must be 42 (37 prior + 3 CANDIDATE_SOURCE_INGESTION_V1 records + 2 human-source-resolution records)")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 16, "Claim count must be 16 (13 prior + 3 CANDIDATE_SOURCE_INGESTION_V1 draft claims)")

EXPERIENCE_INDEX = exp_result["index"]
EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = claim_result["index"]

MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
assert_true(len(MASTER["modules"]) == 13, "master must have 13 modules (6 WW + 5 MM + 2 TELUS)")

WW_MODULES = [m for m in MASTER["modules"] if m.get("experience_id") == "EXP_WW_001"]
MM_MODULES = [m for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"]
assert_true(len(WW_MODULES) == 6, "expected 6 Winter Walk BULLET modules")
assert_true(len(MM_MODULES) == 5, "expected 5 MarketMind PROJECT_BULLET modules")
MM_BY_ID = {m["module_id"]: m for m in MM_MODULES}

APPROVED_WORDING = {
    "MOD_MM_001_SCOPE": (
        "Built a Python/Streamlit prototype for preliminary coffee-shop "
        "market screening using documented heuristic scoring boundaries."
    ),
    "MOD_MM_002_DETERMINISTIC_AI": (
        "Separated deterministic scoring from an optional LLM narrative "
        "layer instructed not to alter scores, thresholds, status, or "
        "scenario calculations."
    ),
    "MOD_MM_003_INTEGRATION": (
        "Integrated Google Places nearby-search and U.S. Census ACS "
        "demographic data into a coffee-shop market-screening workflow."
    ),
    "MOD_MM_004_CONTROLS": (
        "Implemented a 3.5-mile geofence, a local 50-request daily limit, "
        "and retry with degraded stub fallback for failed Places or "
        "Census fetches."
    ),
    "MOD_MM_005_TESTING": (
        "Built an automated pytest suite covering the MarketMind "
        "screening pipeline."
    ),
}


# 1. WW-only selection returns no project groups.
ww_view = build_project_section_view(WW_MODULES, experience_index=EXPERIENCE_INDEX)
assert_true(ww_view["valid"] is True, "WW-only selection must be valid")
assert_true(ww_view["groups"] == [], "WW-only selection must produce zero project groups")
print("PASS 1: Winter Walk BULLET modules produce no project groups.")


# 2. One selected MarketMind PROJECT_BULLET returns one project group.
one_view = build_project_section_view([MM_BY_ID["MOD_MM_003_INTEGRATION"]], experience_index=EXPERIENCE_INDEX)
assert_true(one_view["valid"] is True, "single MarketMind module must resolve")
assert_true(len(one_view["groups"]) == 1, "expected exactly one project group")
assert_true(len(one_view["groups"][0]["bullets"]) == 1, "expected exactly one bullet")
print("PASS 2: one selected PROJECT_BULLET module returns one project group.")


# 3. Multiple MarketMind PROJECT_BULLET modules group under one EXP_MM_001.
all_mm_view = build_project_section_view(MM_MODULES, experience_index=EXPERIENCE_INDEX)
assert_true(all_mm_view["valid"] is True, "all 5 MarketMind modules must resolve")
assert_true(len(all_mm_view["groups"]) == 1, "all 5 MarketMind modules must group into one project")
assert_true(
    all_mm_view["groups"][0]["experience_id"] == "EXP_MM_001",
    "group experience_id must be EXP_MM_001",
)
assert_true(
    len(all_mm_view["groups"][0]["bullets"]) == 5,
    "all 5 MarketMind bullets must appear in the single group",
)
print("PASS 3: multiple PROJECT_BULLET modules group under one EXP_MM_001.")


# 4. Display name resolves exactly to "MarketMind AI" from experience_name.
assert_true(
    all_mm_view["groups"][0]["display_name"] == "MarketMind AI",
    "display_name must resolve exactly to 'MarketMind AI'",
)
print("PASS 4: display name resolves exactly to 'MarketMind AI'.")


# 5. Selected module order is preserved (not alphabetized, not reordered).
custom_order = [
    MM_BY_ID["MOD_MM_003_INTEGRATION"],
    MM_BY_ID["MOD_MM_002_DETERMINISTIC_AI"],
    MM_BY_ID["MOD_MM_005_TESTING"],
]
order_view = build_project_section_view(custom_order, experience_index=EXPERIENCE_INDEX)
assert_true(order_view["valid"] is True, "custom-order selection must resolve")
result_order = [b["module_id"] for b in order_view["groups"][0]["bullets"]]
assert_true(
    result_order == ["MOD_MM_003_INTEGRATION", "MOD_MM_002_DETERMINISTIC_AI", "MOD_MM_005_TESTING"],
    f"bullet order must exactly match input order, got {result_order}",
)
print("PASS 5: selected module order is preserved exactly.")


# 6. Exact approved wording is preserved byte-for-byte.
for group in all_mm_view["groups"]:
    for bullet in group["bullets"]:
        assert_true(
            bullet["wording"] == APPROVED_WORDING[bullet["module_id"]],
            f"{bullet['module_id']} wording must be byte-identical to the approved sentence",
        )
print("PASS 6: exact approved wording preserved byte-for-byte.")


# 7. Non-PROJECT_BULLET modules are excluded even when mixed with PROJECT_BULLET ones.
mixed_view = build_project_section_view(WW_MODULES + MM_MODULES, experience_index=EXPERIENCE_INDEX)
assert_true(mixed_view["valid"] is True, "mixed selection must resolve")
assert_true(len(mixed_view["groups"]) == 1, "mixed selection must still produce exactly one project group")
mixed_ids = {b["module_id"] for b in mixed_view["groups"][0]["bullets"]}
assert_true(mixed_ids == set(MM_BY_ID.keys()), "only PROJECT_BULLET module IDs may appear in the view")
print("PASS 7: non-PROJECT_BULLET modules are excluded from the project-section view.")


# 8. Unresolved experience_id / display name fails explicitly rather than guessing.
missing_experience = {
    "module_id": "MOD_SYN_MISSING_EXP",
    "module_type": "PROJECT_BULLET",
    "wording": "Synthetic bullet for test coverage only.",
    "experience_id": None,
}
unknown_experience = {
    "module_id": "MOD_SYN_UNKNOWN_EXP",
    "module_type": "PROJECT_BULLET",
    "wording": "Synthetic bullet for test coverage only.",
    "experience_id": "EXP_DOES_NOT_EXIST",
}
non_project_experience = {
    "module_id": "MOD_SYN_NON_PROJECT_EXP",
    "module_type": "PROJECT_BULLET",
    "wording": "Synthetic bullet for test coverage only.",
    "experience_id": "EXP_WW_001",
}
for label, synthetic_module in (
    ("missing experience_id", missing_experience),
    ("unknown experience_id", unknown_experience),
    ("PROJECT_BULLET pointing at a non-PERSONAL_PROJECT Experience", non_project_experience),
):
    result = build_project_section_view([synthetic_module], experience_index=EXPERIENCE_INDEX)
    assert_false(result["valid"], f"{label} must fail rather than guess")
    assert_true(result["groups"] == [], f"{label} must produce zero groups, not a guessed one")
    assert_true(
        any(e.get("code") == "PROJECT_DISPLAY_NAME_UNRESOLVED" for e in result["errors"]),
        f"{label} must report PROJECT_DISPLAY_NAME_UNRESOLVED",
    )
print("PASS 8: unresolved identity (including cross-Experience-type) fails explicitly, never guesses.")


# 9. No forbidden presentation fields appear in output, even if present on the source module.
tainted_module = copy.deepcopy(MM_BY_ID["MOD_MM_001_SCOPE"])
tainted_module["date_range"] = "May 2026 - Aug 2026"
tainted_module["location"] = "Boston, MA"
tainted_module["url"] = "https://example.invalid"
tainted_module["formal_title"] = "Founder"
tainted_module["organization"] = "MarketMind AI, Inc."
tainted_view = build_project_section_view([tainted_module], experience_index=EXPERIENCE_INDEX)
assert_true(tainted_view["valid"] is True, "tainted module must still resolve on its real fields")
bullet_keys = set(tainted_view["groups"][0]["bullets"][0].keys())
assert_true(bullet_keys == {"module_id", "wording"}, f"bullet must contain only module_id/wording, got {bullet_keys}")
group_keys = set(tainted_view["groups"][0].keys())
assert_true(
    group_keys == {"experience_id", "display_name", "bullets"},
    f"group must contain only experience_id/display_name/bullets, got {group_keys}",
)
FORBIDDEN_FIELDS = {
    "date_range", "location", "formal_title", "employer", "organization",
    "client", "sponsor", "url", "technology_line", "project_subtitle",
}
assert_true(
    FORBIDDEN_FIELDS.isdisjoint(bullet_keys | group_keys),
    "no forbidden presentation field may appear anywhere in the output",
)
print("PASS 9: no forbidden/invented presentation fields appear in the output.")


# 10. The function does not mutate its inputs.
before = copy.deepcopy(MM_MODULES)
_ = build_project_section_view(MM_MODULES, experience_index=EXPERIENCE_INDEX)
assert_true(MM_MODULES == before, "build_project_section_view must not mutate its input modules")
print("PASS 10: function does not mutate inputs.")


# Duplicate module_id behavior: preserved deterministically, not deduplicated
# (master-level uniqueness and INCLUDE_MODULE's own not-already-included check
# already prevent duplicates from occurring in real derivative-selected input).
dup_view = build_project_section_view(
    [MM_BY_ID["MOD_MM_002_DETERMINISTIC_AI"], MM_BY_ID["MOD_MM_002_DETERMINISTIC_AI"]],
    experience_index=EXPERIENCE_INDEX,
)
assert_true(dup_view["valid"] is True, "duplicate input must still resolve")
assert_true(
    len(dup_view["groups"][0]["bullets"]) == 2,
    "duplicates are preserved in place, not silently deduplicated",
)
print("PASS: duplicate module_id input is preserved deterministically (documented behavior).")


# 11. Existing default derivative behavior remains unchanged.
default_patch = {
    "patch_id": "PATCH_PROJECT_VIEW_DEFAULT",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]}],
}
default_result = build_resume_derivative(
    master=MASTER,
    patch=default_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_PROJECT_VIEW_DEFAULT",
)
assert_true(default_result["valid"] is True, "default derivative must build")
assert_true(
    default_result["derivative"]["included_module_ids"]
    == [m["module_id"] for m in WW_MODULES] + ["MOD_TELUS_001_REVIEW", "MOD_TELUS_002_PATTERN"],
    "default derivative must be exactly the 6 Winter Walk modules plus the 2 approved TELUS modules (MarketMind excluded from default)",
)
print("PASS 11: default derivative behavior unchanged.")


# 12. Explicit MarketMind selection still works before applying the view transform.
include_patch = {
    "patch_id": "PATCH_PROJECT_VIEW_INCLUDE",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "INCLUDE_MODULE", "module_id": mid} for mid in MM_BY_ID],
}
include_result = build_resume_derivative(
    master=MASTER,
    patch=include_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_PROJECT_VIEW_INCLUDE",
)
assert_true(include_result["valid"] is True, "explicit MarketMind selection must still build")
selected = [
    m for m in include_result["derivative"]["modules"]
    if m["module_id"] in include_result["derivative"]["included_module_ids"]
    and m["module_type"] == "PROJECT_BULLET"
]
post_selection_view = build_project_section_view(selected, experience_index=EXPERIENCE_INDEX)
assert_true(post_selection_view["valid"] is True, "view over an explicit-selection derivative must resolve")
assert_true(len(post_selection_view["groups"]) == 1, "expected one project group from the explicit selection")
print("PASS 12: explicit MarketMind selection still works before applying the view transform.")


# 13. Fail-closed remediation: a mix of one valid PERSONAL_PROJECT group and
#     one invalid/unresolved group must yield valid=False and groups=[] --
#     never a partial result containing only the successfully-resolved group.
valid_synthetic_group = {
    "module_id": "MOD_SYN_VALID_MIX",
    "module_type": "PROJECT_BULLET",
    "wording": "Synthetic bullet for test coverage only.",
    "experience_id": "EXP_MM_001",
}
invalid_synthetic_group = {
    "module_id": "MOD_SYN_INVALID_MIX",
    "module_type": "PROJECT_BULLET",
    "wording": "Synthetic bullet for test coverage only.",
    "experience_id": "EXP_DOES_NOT_EXIST",
}
mixed_result = build_project_section_view(
    [MM_BY_ID["MOD_MM_001_SCOPE"], valid_synthetic_group, invalid_synthetic_group],
    experience_index=EXPERIENCE_INDEX,
)
assert_false(mixed_result["valid"], "a mix of valid and invalid groups must be reported invalid overall")
assert_true(
    mixed_result["groups"] == [],
    "an invalid overall view must never return a partial/successful group",
)
assert_true(
    any(
        e.get("code") == "PROJECT_DISPLAY_NAME_UNRESOLVED"
        and e.get("experience_id") == "EXP_DOES_NOT_EXIST"
        for e in mixed_result["errors"]
    ),
    "the specific unresolved-identity error must still be present in errors",
)
print("PASS 13: mixed valid+invalid groups fail closed (valid=False, groups=[], errors preserved).")


# 14. Optional: explicit empty experience_name coverage.
synthetic_experience_index = dict(EXPERIENCE_INDEX)
synthetic_experience_index["EXP_SYN_EMPTY_NAME"] = {
    "experience_id": "EXP_SYN_EMPTY_NAME",
    "experience_name": "",
    "experience_type": "PERSONAL_PROJECT",
}
empty_name_module = {
    "module_id": "MOD_SYN_EMPTY_NAME",
    "module_type": "PROJECT_BULLET",
    "wording": "Synthetic bullet for test coverage only.",
    "experience_id": "EXP_SYN_EMPTY_NAME",
}
empty_name_result = build_project_section_view([empty_name_module], experience_index=synthetic_experience_index)
assert_false(empty_name_result["valid"], "an empty experience_name must not resolve")
assert_true(empty_name_result["groups"] == [], "an empty experience_name must yield no groups")
assert_true(
    any(e.get("code") == "PROJECT_DISPLAY_NAME_UNRESOLVED" for e in empty_name_result["errors"]),
    "empty experience_name must report PROJECT_DISPLAY_NAME_UNRESOLVED",
)
print("PASS 14: empty experience_name is treated as unresolved, not a blank display name.")


print("PASS: project section view builder tests completed successfully.")
