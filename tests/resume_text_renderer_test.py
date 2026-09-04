"""Bounded tests for the deterministic TEST-ONLY plain-text résumé renderer
(TEST_ONLY_RESUME_TEXT_RENDERER_V1).

render_resume_text() is a pure text-layout function only: it renders
exactly what the already-valid unified presentation view supplies, adds
no factual content, and performs no export/PDF/DOCX/file-write of any
kind. These tests exercise it against real, unmodified
build_resume_derivative() + build_resume_presentation_view() output plus
synthetic, test-only records for summary/education/failure-path
coverage (no fake production Evidence/Experience/Claim records are
created). Output is explicitly TEST-ONLY, never Bora's approved
résumé.
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
from resume_text_renderer import render_resume_text  # noqa: E402
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
assert_true(len(ev_result["index"]) == 43, "Evidence count must be 43 (37 prior + 3 CANDIDATE_SOURCE_INGESTION_V1 records + 2 human-source-resolution records + 1 Brandeis MSBA awarded attestation record)")
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
APPROVED_WW_WORDING = {m["module_id"]: m["wording"] for m in MASTER["modules"] if m["module_type"] == "BULLET"}
APPROVED_MM_WORDING = {m["module_id"]: m["wording"] for m in MASTER["modules"] if m["module_type"] == "PROJECT_BULLET"}


def build(patch_ops, patch_id):
    patch = {"patch_id": patch_id, "target_master_id": MASTER["master_id"], "operations": patch_ops}
    result = build_resume_derivative(
        master=MASTER, patch=patch, claim_index=CLAIM_INDEX, evidence_index=EVIDENCE_INDEX,
        derivative_id=f"DERIV_{patch_id}",
    )
    assert_true(result["valid"] is True, f"derivative build must succeed for {patch_id}: {result.get('errors')}")
    return result["derivative"]


def present(derivative):
    view = build_resume_presentation_view(derivative, experience_index=EXPERIENCE_INDEX)
    assert_true(view["valid"] is True, f"presentation view must resolve: {view.get('errors')}")
    return view


# 1. Current default derivative (Winter Walk + approved TELUS modules) renders valid text.
default_derivative = build([{"op": "REORDER_MODULES", "module_ids": MASTER["default_module_order"]}], "TXT_DEFAULT")
default_presentation = present(default_derivative)
default_render = render_resume_text(default_presentation)
assert_true(default_render["valid"] is True, f"default render must succeed: {default_render.get('errors')}")
assert_true(isinstance(default_render["text"], str) and default_render["text"], "rendered text must be a non-empty string")
print("PASS 1: default derivative (Winter Walk + TELUS) renders valid text.")


# Byte-for-byte golden-style expected text fixture for the default path.
EXPECTED_DEFAULT_TEXT = "\n\n".join([
    "Bora Chaush | bchaush@brandeis.edu | +1 857 919 8421 | Boston, MA | linkedin.com/in/bora-chaush-msba",
    "\n".join([
        "EDUCATION",
        "Business Analytics (M.S.), Brandeis University, Fall 2025 – Summer 2026",
    ]),
    "\n".join([
        "EXPERIENCE",
        "Winter Walk, AI Researcher & Developer Intern, Jun 2026 – Aug 2026",
        "- " + APPROVED_WW_WORDING["MOD_WW_001_SCOPE"],
        "- " + APPROVED_WW_WORDING["MOD_WW_002_CONTROLS"],
        "- " + APPROVED_WW_WORDING["MOD_WW_003_INTAKE"],
        "- " + APPROVED_WW_WORDING["MOD_WW_004_SYNC"],
        "- " + APPROVED_WW_WORDING["MOD_WW_005_UAT"],
        "- " + APPROVED_WW_WORDING["MOD_WW_006_PROCESS"],
        "TELUS Digital Bulgaria, Digital Trust and Safety Analyst with English, Nov 2024 – May 2025",
        "- Reviewed 500+ user cases weekly against platform policy, identifying violations and behavioral patterns across structured and unstructured data under time-sensitive conditions.",
        "- Tracked and categorized enforcement decisions for trend analysis and consistency, collaborating with policy, operations, and analytics teams to surface recurring risk patterns.",
    ]),
    "\n".join(["SKILLS", ", ".join(MASTER["skills_order"])]),
])
assert_true(
    default_render["text"] == EXPECTED_DEFAULT_TEXT,
    f"default rendered text must match the golden-style fixture exactly, got:\n{default_render['text']!r}",
)
print("PASS: default rendered text matches the byte-for-byte golden-style fixture exactly.")


# 2. Explicit MarketMind selection renders PROJECTS. 3. Unselected MarketMind does not appear (implicit contrast with test 1).
mm_derivative = build([{"op": "INCLUDE_MODULE", "module_id": mid} for mid in MM_IDS], "TXT_MM_INCLUDE")
mm_presentation = present(mm_derivative)
mm_render = render_resume_text(mm_presentation)
assert_true(mm_render["valid"] is True, f"MarketMind-selected render must succeed: {mm_render.get('errors')}")
assert_true("PROJECTS" in mm_render["text"], "PROJECTS heading must appear when MarketMind is explicitly selected")
assert_false("PROJECTS" in default_render["text"], "PROJECTS heading must not appear when no project module is selected")
for wording in APPROVED_MM_WORDING.values():
    assert_true(("- " + wording) in mm_render["text"], f"MarketMind bullet must appear verbatim: {wording}")
print("PASS 2-3: explicit MarketMind selection renders PROJECTS; unselected MarketMind never appears.")


# 4. Excluded Winter Walk bullet does not appear.
excluded_id = "MOD_WW_003_INTAKE"
exclude_derivative = build([{"op": "EXCLUDE_MODULE", "module_id": excluded_id}], "TXT_WW_EXCLUDE")
exclude_render = render_resume_text(present(exclude_derivative))
assert_true(exclude_render["valid"] is True, "exclusion render must succeed")
assert_false(
    ("- " + APPROVED_WW_WORDING[excluded_id]) in exclude_render["text"],
    "excluded Winter Walk bullet must not appear in rendered text",
)
print("PASS 4: excluded Winter Walk bullet does not appear.")


# 5-6. Exact WW and MarketMind wording preserved (checked above via substring; confirm byte-exactness explicitly).
assert_true(
    ("- " + APPROVED_WW_WORDING["MOD_WW_001_SCOPE"]) in default_render["text"],
    "WW wording must be byte-identical in rendered output",
)
assert_true(
    ("- " + APPROVED_MM_WORDING["MOD_MM_001_SCOPE"]) in mm_render["text"],
    "MarketMind wording must be byte-identical in rendered output",
)
print("PASS 5-6: exact WW and MarketMind wording preserved.")


# 7. Employment bullet order preserved.
ww_block_start = default_render["text"].index("EXPERIENCE")
ww_block = default_render["text"][ww_block_start:]
positions = [ww_block.index("- " + APPROVED_WW_WORDING[mid]) for mid in WW_IDS]
assert_true(positions == sorted(positions), "employment bullets must render in exact provided order")
print("PASS 7: employment bullet order preserved.")


# 8. Project bullet order preserved.
custom_order_derivative = build(
    [{"op": "INCLUDE_MODULE", "module_id": mid} for mid in ["MOD_MM_003_INTEGRATION", "MOD_MM_001_SCOPE", "MOD_MM_005_TESTING"]]
    + [{"op": "REORDER_MODULES", "module_ids": ["MOD_MM_003_INTEGRATION", "MOD_MM_001_SCOPE", "MOD_MM_005_TESTING"] + MASTER["default_module_order"]}],
    "TXT_MM_ORDER",
)
custom_order_render = render_resume_text(present(custom_order_derivative))
assert_true(custom_order_render["valid"] is True, "custom project order render must succeed")
proj_block_start = custom_order_render["text"].index("PROJECTS")
proj_block = custom_order_render["text"][proj_block_start:]
custom_positions = [
    proj_block.index("- " + APPROVED_MM_WORDING[mid])
    for mid in ["MOD_MM_003_INTEGRATION", "MOD_MM_001_SCOPE", "MOD_MM_005_TESTING"]
]
assert_true(custom_positions == sorted(custom_positions), "project bullets must render in exact selected order")
print("PASS 8: project bullet order preserved.")


# 9. Skills order preserved.
assert_true(
    ", ".join(MASTER["skills_order"]) in default_render["text"],
    "skills must render exactly in presentation order as a comma-separated line",
)
print("PASS 9: skills order preserved.")


# 10. Contact values preserved.
assert_true(
    "Bora Chaush | bchaush@brandeis.edu | +1 857 919 8421 | Boston, MA | linkedin.com/in/bora-chaush-msba"
    in default_render["text"],
    "contact values must render exactly, in schema field order",
)
print("PASS 10: contact values preserved.")


# 11. Empty education creates no EDUCATION heading (proven via an explicit
#     empty-education derivative, since the real master now carries a
#     verified Brandeis entry and legitimately renders EDUCATION by default).
assert_true("EDUCATION" in default_render["text"], "verified Brandeis education must render an EDUCATION heading by default")
empty_education_derivative = copy.deepcopy(default_derivative)
empty_education_derivative["education"] = []
empty_education_render = render_resume_text(present(empty_education_derivative))
assert_true(empty_education_render["valid"] is True, "empty-education render must succeed")
assert_false(
    "EDUCATION" in empty_education_render["text"],
    "empty education must never render an EDUCATION heading",
)
print("PASS 11: default education renders correctly; empty education creates no EDUCATION heading.")


# 12. Absent summary creates no SUMMARY heading.
assert_false("SUMMARY" in default_render["text"], "absent summary must never render a SUMMARY heading")
print("PASS 12: absent summary creates no SUMMARY heading.")


# 13. Optional synthetic summary renders only when present.
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
summary_render = render_resume_text(present(summary_derivative))
assert_true(summary_render["valid"] is True, "render with a selected summary module must succeed")
assert_true("SUMMARY" in summary_render["text"], "SUMMARY heading must appear when a summary module is selected")
assert_true(
    synthetic_summary_module["wording"] in summary_render["text"],
    "summary wording must render verbatim",
)
print("PASS 13: optional synthetic summary renders only when present.")


# 14. Optional synthetic education renders only when present.
synthetic_education = [{"education_id": "EDU_SYN_001", "school_name": "Synthetic University", "degree_name": "Synthetic Degree"}]
education_derivative = copy.deepcopy(default_derivative)
education_derivative["education"] = synthetic_education
education_render = render_resume_text(present(education_derivative))
assert_true(education_render["valid"] is True, "render with synthetic education must succeed")
assert_true("EDUCATION" in education_render["text"], "EDUCATION heading must appear when education is present")
assert_true(
    "Synthetic Degree, Synthetic University" in education_render["text"],
    "education entry must render only its present fields",
)
print("PASS 14: optional synthetic education renders only when present.")


# 15. No PROJECT_BULLET leaks into EXPERIENCE.
full_derivative = build([{"op": "INCLUDE_MODULE", "module_id": mid} for mid in MM_IDS], "TXT_FULL_CHECK")
full_render = render_resume_text(present(full_derivative))
assert_true(full_render["valid"] is True, "full-selection render must succeed")
exp_start = full_render["text"].index("EXPERIENCE")
proj_start = full_render["text"].index("PROJECTS")
experience_block = full_render["text"][exp_start:proj_start]
for wording in APPROVED_MM_WORDING.values():
    assert_false(("- " + wording) in experience_block, "no MarketMind wording may appear inside the EXPERIENCE block")
print("PASS 15: no PROJECT_BULLET leaks into EXPERIENCE.")


# 16. No employment BULLET leaks into PROJECTS.
project_block = full_render["text"][proj_start:]
for wording in APPROVED_WW_WORDING.values():
    assert_false(("- " + wording) in project_block, "no Winter Walk wording may appear inside the PROJECTS block")
print("PASS 16: no employment BULLET leaks into PROJECTS.")


# 17. No empty section headings anywhere.
assert_false("SUMMARY" in default_render["text"], "SUMMARY must not appear when its content is absent")
assert_false("EDUCATION" in empty_education_render["text"], "EDUCATION must not appear when its content is absent")
print("PASS 17: no empty section headings.")


# 18. Deterministic repeat output.
repeat_render = render_resume_text(default_presentation)
assert_true(repeat_render == default_render, "same input must produce byte-identical output on repeat calls")
print("PASS 18: deterministic repeat output.")


# 19. Input not mutated.
presentation_before = copy.deepcopy(default_presentation)
_ = render_resume_text(default_presentation)
assert_true(default_presentation == presentation_before, "render_resume_text must not mutate its input")
print("PASS 19: input not mutated.")


# 20. Malformed presentation fails explicitly.
malformed_cases = [
    ("not a mapping", "just a string"),
    ("valid=False envelope", {"valid": False, "presentation": None, "errors": []}),
    ("missing presentation", {"valid": True, "presentation": None, "errors": []}),
    (
        "malformed contact (no name)",
        {"valid": True, "presentation": {"contact": {}, "employment_sections": [], "project_sections": [], "skills": []}, "errors": []},
    ),
    (
        "malformed employment section (missing title)",
        {
            "valid": True,
            "presentation": {
                "contact": {"name": "Test Person"},
                "employment_sections": [{"organization": "Acme", "date_range": "2020-2021", "bullets": []}],
                "project_sections": [],
                "skills": [],
            },
            "errors": [],
        },
    ),
    (
        "malformed project section (missing display_name)",
        {
            "valid": True,
            "presentation": {
                "contact": {"name": "Test Person"},
                "employment_sections": [],
                "project_sections": [{"bullets": []}],
                "skills": [],
            },
            "errors": [],
        },
    ),
    (
        "malformed bullet (empty wording)",
        {
            "valid": True,
            "presentation": {
                "contact": {"name": "Test Person"},
                "employment_sections": [],
                "project_sections": [{"display_name": "Test Project", "bullets": [{"module_id": "X", "wording": ""}]}],
                "skills": [],
            },
            "errors": [],
        },
    ),
    (
        "wrong-type skills",
        {
            "valid": True,
            "presentation": {
                "contact": {"name": "Test Person"},
                "employment_sections": [],
                "project_sections": [],
                "skills": "not a list",
            },
            "errors": [],
        },
    ),
]
for label, case in malformed_cases:
    result = render_resume_text(case)
    assert_false(result["valid"], f"{label} must fail rather than render partial content")
    assert_true(result["text"] is None, f"{label} must produce no text output")
    assert_true(len(result["errors"]) >= 1, f"{label} must report at least one deterministic error")
print("PASS 20: malformed presentation input fails explicitly for every adversarial case, never rendering partial content.")


print("PASS: resume text renderer tests completed successfully.")
