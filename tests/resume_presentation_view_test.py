"""Bounded tests for the pure unified résumé presentation assembler
(UNIFIED_RESUME_PRESENTATION_MODEL_V1).

build_resume_presentation_view() is a derived-view composition function
only: it stores no new truth, adds no schema, duplicates no filtering/
ordering/identity logic already proven in the closed employment- and
project-section transforms, and never invents presentation metadata.
These tests exercise it against real, unmodified `build_resume_derivative()`
output plus synthetic, test-only records for failure-path/summary
coverage (no fake production Evidence/Experience/Claim records are
created).
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
from resume_presentation import build_resume_presentation_view  # noqa: E402
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

WW_IDS = [m["module_id"] for m in MASTER["modules"] if m.get("experience_id") == "EXP_WW_001"]
MM_IDS = [m["module_id"] for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"]
APPROVED_WW_WORDING = {
    m["module_id"]: m["wording"] for m in MASTER["modules"] if m["module_type"] == "BULLET"
}
APPROVED_MM_WORDING = {
    m["module_id"]: m["wording"] for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"
}


def build(patch_ops, patch_id):
    patch = {
        "patch_id": patch_id,
        "target_master_id": MASTER["master_id"],
        "operations": patch_ops,
    }
    result = build_resume_derivative(
        master=MASTER,
        patch=patch,
        claim_index=CLAIM_INDEX,
        evidence_index=EVIDENCE_INDEX,
        derivative_id=f"DERIV_{patch_id}",
    )
    assert_true(result["valid"] is True, f"derivative build must succeed for {patch_id}: {result.get('errors')}")
    return result["derivative"]


# 1. Real current derivative / all-default Winter Walk path.
default_derivative = build([{"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]}], "PRES_DEFAULT")
default_view = build_resume_presentation_view(default_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(default_view["valid"] is True, f"default WW-only view must resolve: {default_view.get('errors')}")
presentation = default_view["presentation"]
assert_true(
    [b["module_id"] for b in presentation["employment_sections"][0]["bullets"]] == WW_IDS,
    "default derivative must present all 6 Winter Walk bullets in order",
)
assert_true(presentation["project_sections"] == [], "default derivative must present zero project sections")
assert_true(
    "education" in presentation and presentation["education"] == MASTER["education"],
    "verified Brandeis education must appear in the unified presentation, copied verbatim",
)
assert_true("summary" not in presentation, "absent summary must be omitted, not fabricated")
print("PASS 1: real default Winter Walk derivative produces a valid, correctly-scoped presentation.")


# 2. Explicit MarketMind selection appears under projects.
mm_derivative = build(
    [{"op": "INCLUDE_MODULE", "module_id": mid} for mid in MM_IDS], "PRES_MM_INCLUDE"
)
mm_view = build_resume_presentation_view(mm_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(mm_view["valid"] is True, f"MarketMind-selected view must resolve: {mm_view.get('errors')}")
mm_presentation = mm_view["presentation"]
assert_true(len(mm_presentation["project_sections"]) == 1, "expected exactly one project group")
assert_true(
    {b["module_id"] for b in mm_presentation["project_sections"][0]["bullets"]} == set(MM_IDS),
    "all 5 explicitly selected MarketMind modules must appear under projects",
)
assert_true(
    [b["module_id"] for b in mm_presentation["employment_sections"][0]["bullets"]] == WW_IDS,
    "Winter Walk employment presentation must remain the full default set",
)
print("PASS 2: explicit MarketMind selection appears correctly under project_sections.")


# 3. Employment exclusion does not leak into presentation.
excluded_id = "MOD_WW_004_SYNC"
exclude_derivative = build([{"op": "EXCLUDE_MODULE", "module_id": excluded_id}], "PRES_WW_EXCLUDE")
exclude_view = build_resume_presentation_view(exclude_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(exclude_view["valid"] is True, "exclusion-derivative view must resolve")
exclude_ids = [b["module_id"] for b in exclude_view["presentation"]["employment_sections"][0]["bullets"]]
assert_true(excluded_id not in exclude_ids, "excluded Winter Walk module must not appear in presentation")
assert_true(len(exclude_ids) == 5, f"expected 5 remaining WW bullets, got {len(exclude_ids)}")
print("PASS 3: employment exclusion does not leak into the unified presentation.")


# 4. Project selection filtering works (one MarketMind module included, not all five).
one_mm_derivative = build([{"op": "INCLUDE_MODULE", "module_id": "MOD_MM_002_DETERMINISTIC_AI"}], "PRES_MM_ONE")
one_mm_view = build_resume_presentation_view(one_mm_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(one_mm_view["valid"] is True, "single-MarketMind-selection view must resolve")
one_mm_bullets = one_mm_view["presentation"]["project_sections"][0]["bullets"]
assert_true(
    [b["module_id"] for b in one_mm_bullets] == ["MOD_MM_002_DETERMINISTIC_AI"],
    "only the single explicitly selected MarketMind module may appear",
)
print("PASS 4: project selection filtering works for a partial MarketMind selection.")


# 5. Exact approved wording preserved (both WW and MM).
for bullet in default_view["presentation"]["employment_sections"][0]["bullets"]:
    assert_true(
        bullet["wording"] == APPROVED_WW_WORDING[bullet["module_id"]],
        f"{bullet['module_id']} WW wording must be byte-identical to approved sentence",
    )
for bullet in mm_presentation["project_sections"][0]["bullets"]:
    assert_true(
        bullet["wording"] == APPROVED_MM_WORDING[bullet["module_id"]],
        f"{bullet['module_id']} MM wording must be byte-identical to approved sentence",
    )
print("PASS 5: exact approved wording preserved byte-for-byte for both employment and project bullets.")


# 6. Skills order preserved exactly.
assert_true(
    presentation["skills"] == MASTER["skills_order"],
    "skills must be copied verbatim from the derivative's skills_order",
)
print("PASS 6: skills order preserved exactly.")


# 7. Contact preserved exactly.
assert_true(presentation["contact"] == MASTER["contact"], "contact must be copied verbatim, never transformed")
print("PASS 7: contact preserved exactly.")


# 8. Verified Brandeis education renders with exact source-supported fields only,
#    and empty education (proven via an explicit empty-education derivative, since
#    the real master now carries a verified entry) is still correctly omitted.
assert_true(
    MASTER["education"] == [
        {
            "education_id": "EDU_BRANDEIS_MSBA",
            "school_name": "Brandeis University",
            "degree_name": "Business Analytics (M.S.)",
            "date_range": "Fall 2025 – Summer 2026",
            "location": None,
        }
    ],
    f"real master education must contain exactly the verified Brandeis entry, got {MASTER['education']}",
)
empty_education_derivative = copy.deepcopy(default_derivative)
empty_education_derivative["education"] = []
empty_education_view = build_resume_presentation_view(empty_education_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(empty_education_view["valid"] is True, "empty-education derivative view must resolve")
assert_true(
    "education" not in empty_education_view["presentation"],
    "empty education must still be omitted from the presentation, never fabricated",
)
print("PASS 8: verified Brandeis education renders truthfully; empty education is still correctly omitted.")


# 9. No summary fabricated when none is selected/present.
assert_true(MASTER.get("summary_module_id") is None, "sanity: real master has no active summary module")
assert_true("summary" not in presentation, "absent summary must be omitted, never fabricated")
print("PASS 9: no summary fabricated when none exists.")


# 10. Employment sub-view invalid -> unified fail-closed, no partial presentation.
bad_derivative = copy.deepcopy(default_derivative)
bad_derivative["experience_sections"][0]["organization"] = "PENDING_BORA_REVIEW"
bad_employment_view = build_resume_presentation_view(bad_derivative, experience_index=EXPERIENCE_INDEX)
assert_false(bad_employment_view["valid"], "invalid employment sub-view must fail the whole unified result")
assert_true(bad_employment_view["presentation"] is None, "no partial presentation may be returned")
assert_true(
    any(e.get("code") == "EMPLOYMENT_VIEW_INVALID" for e in bad_employment_view["errors"]),
    "unified errors must report EMPLOYMENT_VIEW_INVALID",
)
print("PASS 10: employment sub-view invalid correctly fails the unified presentation closed.")


# 11. Project sub-view invalid -> unified fail-closed, no partial presentation.
bad_project_module = {
    "module_id": "MOD_SYN_BAD_PROJECT",
    "module_type": "PROJECT_BULLET",
    "wording": "Synthetic bullet for test coverage only.",
    "claim_ids": ["CLAIM_MM_001"],
    "evidence_ids": [],
    "experience_id": "EXP_DOES_NOT_EXIST",
    "status": "ACTIVE",
}
bad_project_derivative = copy.deepcopy(default_derivative)
bad_project_derivative["modules"] = bad_project_derivative["modules"] + [bad_project_module]
bad_project_derivative["included_module_ids"] = bad_project_derivative["included_module_ids"] + ["MOD_SYN_BAD_PROJECT"]
bad_project_view = build_resume_presentation_view(bad_project_derivative, experience_index=EXPERIENCE_INDEX)
assert_false(bad_project_view["valid"], "invalid project sub-view must fail the whole unified result")
assert_true(bad_project_view["presentation"] is None, "no partial presentation may be returned")
assert_true(
    any(e.get("code") == "PROJECT_VIEW_INVALID" for e in bad_project_view["errors"]),
    "unified errors must report PROJECT_VIEW_INVALID",
)
print("PASS 11: project sub-view invalid correctly fails the unified presentation closed.")


# 12. No mutation of derivative/modules/experience index.
derivative_before = copy.deepcopy(default_derivative)
experience_index_before = copy.deepcopy(EXPERIENCE_INDEX)
_ = build_resume_presentation_view(default_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(default_derivative == derivative_before, "build_resume_presentation_view must not mutate its derivative input")
assert_true(EXPERIENCE_INDEX == experience_index_before, "build_resume_presentation_view must not mutate experience_index")
print("PASS 12: function does not mutate its inputs.")


# 13. Deterministic repeat output.
repeat_view = build_resume_presentation_view(default_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(repeat_view == default_view, "same input must produce byte-identical output on repeat calls")
print("PASS 13: repeat calls with the same input produce identical output.")


# 14. Project bullets never enter employment.
full_derivative = build(
    [{"op": "INCLUDE_MODULE", "module_id": mid} for mid in MM_IDS], "PRES_FULL_CHECK"
)
full_view = build_resume_presentation_view(full_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(full_view["valid"] is True, "full-selection view must resolve")
employment_ids = {b["module_id"] for b in full_view["presentation"]["employment_sections"][0]["bullets"]}
assert_true(employment_ids.isdisjoint(set(MM_IDS)), "no PROJECT_BULLET module may ever appear under employment_sections")
print("PASS 14: project bullets never enter the employment presentation.")


# 15. Employment bullets never enter projects.
project_ids = {b["module_id"] for b in full_view["presentation"]["project_sections"][0]["bullets"]}
assert_true(project_ids.isdisjoint(set(WW_IDS)), "no BULLET module may ever appear under project_sections")
print("PASS 15: employment bullets never enter the project presentation.")


# 16. No unselected modules appear anywhere.
assert_true(employment_ids == set(WW_IDS), "employment presentation must contain exactly the selected WW modules")
assert_true(project_ids == set(MM_IDS), "project presentation must contain exactly the selected MM modules")
print("PASS 16: no unselected module appears anywhere in the unified presentation.")


# Custom module selection/order derivative: exclude one WW bullet, include a partial
# MarketMind selection, and explicitly reorder modules via REORDER_MODULES to prove
# the documented module_order-then-append-leftovers precedence.
custom_patch_ops = [
    {"op": "EXCLUDE_MODULE", "module_id": "MOD_WW_002_CONTROLS"},
    {"op": "INCLUDE_MODULE", "module_id": "MOD_MM_004_CONTROLS"},
    {"op": "INCLUDE_MODULE", "module_id": "MOD_MM_001_SCOPE"},
    {
        "op": "REORDER_MODULES",
        "module_ids": ["MOD_MM_004_CONTROLS"] + [mid for mid in MASTER["default_module_order"] if mid != "MOD_WW_002_CONTROLS"],
    },
]
custom_derivative = build(custom_patch_ops, "PRES_CUSTOM")
custom_view = build_resume_presentation_view(custom_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(custom_view["valid"] is True, f"custom-selection derivative view must resolve: {custom_view.get('errors')}")
custom_presentation = custom_view["presentation"]
custom_employment_ids = [b["module_id"] for b in custom_presentation["employment_sections"][0]["bullets"]]
assert_true("MOD_WW_002_CONTROLS" not in custom_employment_ids, "excluded WW module must be absent")
assert_true(len(custom_employment_ids) == 5, f"expected 5 remaining WW bullets, got {len(custom_employment_ids)}")
custom_project_ids = [b["module_id"] for b in custom_presentation["project_sections"][0]["bullets"]]
assert_true(
    custom_project_ids == ["MOD_MM_004_CONTROLS", "MOD_MM_001_SCOPE"],
    f"MOD_MM_004_CONTROLS (present in module_order) must precede MOD_MM_001_SCOPE "
    f"(included-but-absent-from-module_order, appended in inclusion order), got {custom_project_ids}",
)
print("PASS: custom module selection/order derivative resolves with the documented ordering precedence.")


# Optional summary composition (synthetic-only: no real SUMMARY module exists yet).
synthetic_summary_module = {
    "module_id": "MOD_SYN_SUMMARY",
    "module_type": "SUMMARY",
    "wording": "Synthetic summary for test coverage only.",
    "claim_ids": ["CLAIM_WW_001"],
    "evidence_ids": [],
    "status": "ACTIVE",
}
summary_derivative = copy.deepcopy(default_derivative)
summary_derivative["modules"] = summary_derivative["modules"] + [synthetic_summary_module]
summary_derivative["included_module_ids"] = summary_derivative["included_module_ids"] + ["MOD_SYN_SUMMARY"]
summary_derivative["summary_module_id"] = "MOD_SYN_SUMMARY"
summary_view = build_resume_presentation_view(summary_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(summary_view["valid"] is True, "derivative with a selected summary module must resolve")
assert_true(
    summary_view["presentation"].get("summary") == {"module_id": "MOD_SYN_SUMMARY", "wording": synthetic_summary_module["wording"]},
    "a selected SUMMARY module must appear verbatim as the summary field",
)

# A summary_module_id pointing at a module that is NOT selected must not render
# (same reconciliation principle applied to bullet_module_ids elsewhere).
unselected_summary_derivative = copy.deepcopy(default_derivative)
unselected_summary_derivative["modules"] = unselected_summary_derivative["modules"] + [synthetic_summary_module]
unselected_summary_derivative["summary_module_id"] = "MOD_SYN_SUMMARY"  # never added to included_module_ids
unselected_summary_view = build_resume_presentation_view(unselected_summary_derivative, experience_index=EXPERIENCE_INDEX)
assert_true(unselected_summary_view["valid"] is True, "derivative with an unselected summary_module_id must still resolve")
assert_true(
    "summary" not in unselected_summary_view["presentation"],
    "a summary_module_id that was never actually included must not render",
)
print("PASS: summary is composed only when the summary module is both set and actually selected.")


print("PASS: unified resume presentation view tests completed successfully.")
