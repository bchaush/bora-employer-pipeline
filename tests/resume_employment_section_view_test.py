"""Bounded tests for the pure employment-section view builder
(EMPLOYMENT_SECTION_PRESENTATION_VIEW_V1).

build_employment_section_view() is a derived-view function only: it
stores no new truth, adds no schema, and must never invent presentation
metadata. These tests exercise it against the real repository data plus
synthetic, test-only records for failure-path coverage (no fake
production Evidence/Experience/Claim records are created). This
milestone does not wire the transform into build_resume_derivative(); a
real derivative is used here only as a realistic input source to prove
the transform composes correctly against production data shapes.
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
from resume_experience_section import build_employment_section_view  # noqa: E402
from resume_validation import build_resume_derivative  # noqa: E402


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAIL: {message}")
        raise SystemExit(1)


def assert_false(condition: bool, message: str) -> None:
    assert_true(not condition, message)


exp_result = validate_experience_repository()
assert_true(exp_result["valid"] is True, "experience repository invalid")
assert_true(len(exp_result["index"]) == 4, "Experience count must remain 4")
ev_result = validate_evidence_repository(experience_result=exp_result)
assert_true(ev_result["valid"] is True, "evidence repository invalid")
assert_true(len(ev_result["index"]) == 36, "Evidence count must remain 36")
claim_result = validate_claim_repository()
assert_true(claim_result["valid"] is True, "claim repository invalid")
assert_true(claim_result["records_checked"] == 11, "Claim count must remain 11")

EVIDENCE_INDEX = ev_result["index"]
CLAIM_INDEX = claim_result["index"]

MASTER = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
assert_true(len(MASTER["modules"]) == 11, "master must have 11 modules")

WW_MODULES = [m for m in MASTER["modules"] if m["module_type"] == "BULLET"]
MM_MODULES = [m for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"]
assert_true(len(WW_MODULES) == 6, "expected 6 Winter Walk BULLET modules")
assert_true(len(MM_MODULES) == 5, "expected 5 MarketMind PROJECT_BULLET modules")
WW_IDS = [m["module_id"] for m in WW_MODULES]
SECTIONS = MASTER["experience_sections"]

APPROVED_WORDING = {m["module_id"]: m["wording"] for m in WW_MODULES}


# A. All selected Winter Walk bullets -> all appropriate employment bullets appear.
all_view = build_employment_section_view(SECTIONS, MASTER["modules"], included_module_ids=WW_IDS)
assert_true(all_view["valid"] is True, "all-WW-selected view must resolve")
assert_true(len(all_view["sections"]) == 1, "expected exactly one employment section")
result_ids = [b["module_id"] for b in all_view["sections"][0]["bullets"]]
assert_true(result_ids == WW_IDS, f"all 6 WW bullets must appear in default order, got {result_ids}")
print("PASS A: all selected Winter Walk bullets appear.")


# B. One Winter Walk BULLET excluded -> excluded module absent from presentation.
excluded_id = "MOD_WW_003_INTAKE"
partial_ids = [mid for mid in WW_IDS if mid != excluded_id]
partial_view = build_employment_section_view(SECTIONS, MASTER["modules"], included_module_ids=partial_ids)
assert_true(partial_view["valid"] is True, "partial-selection view must still resolve")
result_ids = [b["module_id"] for b in partial_view["sections"][0]["bullets"]]
assert_true(excluded_id not in result_ids, "excluded module must not appear in presentation")
assert_true(result_ids == partial_ids, f"remaining bullets must preserve section order, got {result_ids}")
print("PASS B: excluding a module removes it from presentation (bullet_module_ids reconciled against selection).")


# C. Module exists in section bullet_module_ids but is not selected/included -> must not render.
# (Same underlying mechanism as B: bullet_module_ids still lists it, included_module_ids does not.)
empty_selection_view = build_employment_section_view(SECTIONS, MASTER["modules"], included_module_ids=[])
assert_true(empty_selection_view["valid"] is True, "zero-selection view must still resolve (identity is independent of selection)")
assert_true(empty_selection_view["sections"][0]["bullets"] == [], "zero selection must yield zero bullets despite bullet_module_ids listing all 6")
print("PASS C: a module listed in bullet_module_ids but absent from included_module_ids never renders.")


# D. Selected PROJECT_BULLET must not enter employment view, even if adversarially
#    referenced from a section's bullet_module_ids.
tainted_section = copy.deepcopy(SECTIONS[0])
tainted_section["bullet_module_ids"] = list(tainted_section["bullet_module_ids"]) + ["MOD_MM_001_SCOPE"]
tainted_included = WW_IDS + ["MOD_MM_001_SCOPE"]
tainted_view = build_employment_section_view([tainted_section], MASTER["modules"], included_module_ids=tainted_included)
assert_true(tainted_view["valid"] is True, "tainted section must still resolve on its valid bullets")
tainted_ids = [b["module_id"] for b in tainted_view["sections"][0]["bullets"]]
assert_true("MOD_MM_001_SCOPE" not in tainted_ids, "a selected PROJECT_BULLET must never enter the employment view")
assert_true(tainted_ids == WW_IDS, f"only the 6 real BULLET modules may appear, got {tainted_ids}")
print("PASS D: a selected PROJECT_BULLET referenced from bullet_module_ids is excluded, never rendered.")


# E. Selected non-employment module type (SKILLS_BLOCK) referenced from bullet_module_ids
#    must not enter the employment view either.
synthetic_skills_module = {
    "module_id": "MOD_SYN_SKILLS",
    "module_type": "SKILLS_BLOCK",
    "wording": "Synthetic skills block for test coverage only.",
    "claim_ids": ["CLAIM_WW_001"],
    "evidence_ids": [],
    "status": "ACTIVE",
}
non_employment_section = copy.deepcopy(SECTIONS[0])
non_employment_section["bullet_module_ids"] = list(non_employment_section["bullet_module_ids"]) + ["MOD_SYN_SKILLS"]
non_employment_view = build_employment_section_view(
    [non_employment_section],
    MASTER["modules"] + [synthetic_skills_module],
    included_module_ids=WW_IDS + ["MOD_SYN_SKILLS"],
)
assert_true(non_employment_view["valid"] is True, "section with a non-BULLET reference must still resolve on its real bullets")
non_employment_ids = [b["module_id"] for b in non_employment_view["sections"][0]["bullets"]]
assert_true("MOD_SYN_SKILLS" not in non_employment_ids, "a selected SKILLS_BLOCK module must never enter the employment view")
print("PASS E: a selected non-BULLET module type is excluded from the employment view.")


# F. Custom valid bullet order -> presentation preserves that order.
reordered_section = copy.deepcopy(SECTIONS[0])
custom_order = list(reversed(WW_IDS))
reordered_section["bullet_module_ids"] = custom_order
reordered_view = build_employment_section_view([reordered_section], MASTER["modules"], included_module_ids=WW_IDS)
assert_true(reordered_view["valid"] is True, "reordered section must resolve")
reordered_ids = [b["module_id"] for b in reordered_view["sections"][0]["bullets"]]
assert_true(reordered_ids == custom_order, f"bullet order must exactly match section bullet_module_ids order, got {reordered_ids}")
print("PASS F: custom bullet_module_ids order is preserved exactly.")


# G. Duplicate module_id in bullet_module_ids is preserved deterministically, not
#    deduplicated -- no existing validator prevents this, so no new dedup policy is invented.
dup_section = copy.deepcopy(SECTIONS[0])
dup_section["bullet_module_ids"] = ["MOD_WW_001_SCOPE", "MOD_WW_001_SCOPE"]
dup_view = build_employment_section_view([dup_section], MASTER["modules"], included_module_ids=["MOD_WW_001_SCOPE"])
assert_true(dup_view["valid"] is True, "duplicate bullet reference must still resolve")
assert_true(len(dup_view["sections"][0]["bullets"]) == 2, "duplicate module_id must be preserved in place, not deduplicated")
print("PASS G: duplicate module_id in bullet_module_ids is preserved deterministically (documented behavior).")


# Exact wording preserved byte-for-byte.
for bullet in all_view["sections"][0]["bullets"]:
    assert_true(
        bullet["wording"] == APPROVED_WORDING[bullet["module_id"]],
        f"{bullet['module_id']} wording must be byte-identical to the approved sentence",
    )
print("PASS: exact approved wording preserved byte-for-byte.")


# Function does not mutate its inputs.
sections_before = copy.deepcopy(SECTIONS)
modules_before = copy.deepcopy(MASTER["modules"])
_ = build_employment_section_view(SECTIONS, MASTER["modules"], included_module_ids=WW_IDS)
assert_true(SECTIONS == sections_before, "build_employment_section_view must not mutate experience_sections input")
assert_true(MASTER["modules"] == modules_before, "build_employment_section_view must not mutate modules input")
print("PASS: function does not mutate inputs.")


# Malformed/unresolvable presentation identity fails safely rather than guessing.
bad_org_section = copy.deepcopy(SECTIONS[0])
bad_org_section["organization"] = "PENDING_BORA_REVIEW"
bad_org_view = build_employment_section_view([bad_org_section], MASTER["modules"], included_module_ids=WW_IDS)
assert_false(bad_org_view["valid"], "unresolved organization must fail rather than guess")
assert_true(bad_org_view["sections"] == [], "unresolved organization must yield zero sections")
assert_true(
    any(e.get("code") == "UNRESOLVED_PROTECTED_METADATA" and "organization" in e.get("field", "") for e in bad_org_view["errors"]),
    "unresolved organization must report UNRESOLVED_PROTECTED_METADATA",
)
print("PASS: unresolved organization fails explicitly, never guesses.")

bad_title_section = copy.deepcopy(SECTIONS[0])
bad_title_section["display_title_approval"] = {**bad_title_section["display_title_approval"], "approved": False}
bad_title_view = build_employment_section_view([bad_title_section], MASTER["modules"], included_module_ids=WW_IDS)
assert_false(bad_title_view["valid"], "unresolved title (formal unresolved, display not approved) must fail")
assert_true(bad_title_view["sections"] == [], "unresolved title must yield zero sections")
assert_true(
    any(e.get("code") == "UNRESOLVED_PROTECTED_METADATA" and "display_title" in e.get("field", "") for e in bad_title_view["errors"]),
    "unresolved title must report UNRESOLVED_PROTECTED_METADATA on display_title",
)
print("PASS: unresolved title (no approved display title, no resolved formal title) fails explicitly, never guesses.")

dangling_section = copy.deepcopy(SECTIONS[0])
dangling_section["bullet_module_ids"] = list(dangling_section["bullet_module_ids"]) + ["MOD_DOES_NOT_EXIST"]
dangling_view = build_employment_section_view(
    [dangling_section], MASTER["modules"], included_module_ids=WW_IDS + ["MOD_DOES_NOT_EXIST"]
)
assert_false(dangling_view["valid"], "a dangling bullet_module_ids reference must fail rather than be silently dropped")
assert_true(dangling_view["sections"] == [], "a dangling reference must yield zero sections")
assert_true(
    any(e.get("code") == "EMPLOYMENT_BULLET_MODULE_NOT_FOUND" for e in dangling_view["errors"]),
    "dangling reference must report EMPLOYMENT_BULLET_MODULE_NOT_FOUND",
)
print("PASS: a dangling bullet_module_ids reference fails explicitly (EMPLOYMENT_BULLET_MODULE_NOT_FOUND).")


# No partial sections survive invalid output: mix one resolvable section with one
# unresolvable section -> the whole result must be invalid with zero sections.
good_section = copy.deepcopy(SECTIONS[0])
bad_section = copy.deepcopy(SECTIONS[0])
bad_section["section_id"] = "SEC_SYN_BAD"
bad_section["experience_id"] = "EXP_SYN_BAD"
bad_section["organization"] = "PENDING_BORA_REVIEW"
mixed_view = build_employment_section_view(
    [good_section, bad_section], MASTER["modules"], included_module_ids=WW_IDS
)
assert_false(mixed_view["valid"], "a mix of one valid and one invalid section must be reported invalid overall")
assert_true(mixed_view["sections"] == [], "an invalid overall view must never return a partial/successful section")
print("PASS: mixed valid+invalid sections fail closed (valid=False, sections=[], errors preserved).")


# MarketMind PROJECT_BULLET modules never leak into the employment view, even when
# every module in the real master is selected simultaneously.
ALL_IDS = [m["module_id"] for m in MASTER["modules"]]
full_selection_view = build_employment_section_view(SECTIONS, MASTER["modules"], included_module_ids=ALL_IDS)
assert_true(full_selection_view["valid"] is True, "full-selection view over the real master must resolve")
full_ids = {b["module_id"] for b in full_selection_view["sections"][0]["bullets"]}
assert_true(full_ids == set(WW_IDS), "only the 6 real Winter Walk BULLET modules may appear, MarketMind must never leak in")
print("PASS: MarketMind PROJECT_BULLET modules never leak into the employment view.")


# End-to-end composition proof: build a real derivative (unmodified production path)
# and confirm the transform correctly reconciles bullet_module_ids against its
# included_module_ids without requiring any change to build_resume_derivative().
default_patch = {
    "patch_id": "PATCH_EMPLOYMENT_VIEW_DEFAULT",
    "target_master_id": MASTER["master_id"],
    "operations": [{"op": "EXCLUDE_MODULE", "module_id": "MOD_WW_005_UAT"}],
}
default_result = build_resume_derivative(
    master=MASTER,
    patch=default_patch,
    claim_index=CLAIM_INDEX,
    evidence_index=EVIDENCE_INDEX,
    derivative_id="DERIV_EMPLOYMENT_VIEW_DEFAULT",
)
assert_true(default_result["valid"] is True, "derivative with one excluded WW module must still build")
derivative = default_result["derivative"]
deriv_view = build_employment_section_view(
    derivative["experience_sections"], derivative["modules"], included_module_ids=derivative["included_module_ids"]
)
assert_true(deriv_view["valid"] is True, "view over a real derivative must resolve")
deriv_ids = [b["module_id"] for b in deriv_view["sections"][0]["bullets"]]
assert_true("MOD_WW_005_UAT" not in deriv_ids, "module excluded from the derivative must not appear in the employment view")
assert_true(len(deriv_ids) == 5, f"expected 5 remaining bullets, got {len(deriv_ids)}")
print("PASS: transform correctly composes against a real, unmodified build_resume_derivative() output.")


print("PASS: employment section view builder tests completed successfully.")
